#!/usr/bin/env python3
"""
Performance Logger Tool - real structured timing/log helpers with redaction and rate limiting.
"""
import argparse
import json
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


_SENSITIVE_KEYS = {"password", "token", "secret", "authorization", "api_key", "apikey", "access_token"}


def redact_sensitive(fields: dict) -> dict:
    """Return a copy of fields with sensitive keys masked (case-insensitive substring match)."""
    redacted = {}
    for key, value in fields.items():
        if any(s in key.lower() for s in _SENSITIVE_KEYS):
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted


def format_log_line(level: str, message: str, **fields) -> str:
    """Build a single structured 'level=... message=... key=value ...' log line."""
    safe_fields = redact_sensitive(fields)
    parts = [f"level={level}", f"message={message!r}"]
    for key in sorted(safe_fields):
        parts.append(f"{key}={safe_fields[key]!r}")
    return " ".join(parts)


def compute_duration_ms(start: float, end: float) -> float:
    if end < start:
        raise ValueError("end must not precede start")
    return (end - start) * 1000.0


def is_slow(duration_ms: float, threshold_ms: float = 200.0) -> bool:
    return duration_ms > threshold_ms


def _percentile(sorted_values: list, pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    frac = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * frac


def aggregate_timings(timings: list) -> dict:
    if not timings:
        return {"count": 0, "avg_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
    ordered = sorted(timings)
    return {
        "count": len(ordered),
        "avg_ms": sum(ordered) / len(ordered),
        "p95_ms": _percentile(ordered, 95),
        "p99_ms": _percentile(ordered, 99),
    }


def rate_limited_logger(state: dict, key: str, max_per_window: int, window_seconds: float, now: float) -> bool:
    """Sliding-window rate limiter. `state` is mutated in place to track timestamps per key.

    Returns True if this call should be logged (i.e. is within the allowed rate).
    """
    bucket = state.setdefault(key, [])
    cutoff = now - window_seconds
    bucket[:] = [t for t in bucket if t > cutoff]
    if len(bucket) >= max_per_window:
        return False
    bucket.append(now)
    return True


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Performance Logger Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
