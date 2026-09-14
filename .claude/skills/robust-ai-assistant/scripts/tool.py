#!/usr/bin/env python3
"""
Robust AI Assistant Tool - real retry/backoff, fallback-chain and response-validation helpers.
"""
import argparse
import re
import sys
import time


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def retry_with_backoff(fn, max_retries: int = 3, base_delay: float = 0.5,
                        exceptions=(Exception,), sleep_fn=time.sleep):
    """Call fn() with exponential backoff on failure. Raises the last exception if all attempts fail."""
    last_exc = None
    for attempt in range(max_retries):
        try:
            return fn()
        except exceptions as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                sleep_fn(base_delay * (2 ** attempt))
    raise last_exc


def fallback_chain(primary_fn, fallback_fns: list):
    """Try primary_fn, then each fallback in order, returning the first success.
    Raises the primary's exception if every option fails."""
    fns = [primary_fn] + list(fallback_fns)
    first_exc = None
    for fn in fns:
        try:
            return fn()
        except Exception as exc:
            if first_exc is None:
                first_exc = exc
            continue
    raise first_exc


def validate_ai_response_schema(response: dict, required_keys: list) -> list:
    """Return a list of missing/invalid keys in an AI response payload (empty = valid)."""
    errors = []
    if not isinstance(response, dict):
        return ["response must be a JSON object"]
    for key in required_keys:
        if key not in response:
            errors.append(f"missing required key: {key}")
    return errors


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_user_input(text: str, max_len: int = 4000) -> str:
    """Strip control characters and enforce a max length on user-supplied text."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    cleaned = _CONTROL_CHARS.sub("", text)
    cleaned = cleaned.strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned


def should_allow_request(breaker_state: dict, now: float, cooldown_seconds: float = 30.0) -> bool:
    """Simple circuit-breaker gate: if tripped, block requests until cooldown elapses."""
    if not breaker_state.get("tripped"):
        return True
    tripped_at = breaker_state.get("tripped_at", 0)
    if now - tripped_at >= cooldown_seconds:
        breaker_state["tripped"] = False
        return True
    return False


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Robust AI Assistant Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
