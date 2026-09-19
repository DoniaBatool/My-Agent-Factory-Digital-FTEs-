#!/usr/bin/env python3
"""
Chatbot Endpoint Tool - real helpers for a stateless chat endpoint.

Commands:
  new-conversation-id   - print a fresh conversation id
  validate-payload      - validate a chat request payload (JSON on stdin/--payload)
  classify-intent       - classify an action intent from a message
  test                  - run the test suite
"""
import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone


class Colors:
    GREEN, RED, YELLOW, BLUE, BOLD, END = '\033[92m', '\033[91m', '\033[93m', '\033[94m', '\033[1m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def new_conversation_id() -> str:
    return str(uuid.uuid4())


def validate_message_payload(payload: dict) -> None:
    """Raise ValueError with a clear reason if the payload is not a valid chat request."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("field 'message' is required and must be a non-empty string")
    if len(message) > 8000:
        raise ValueError("field 'message' exceeds the 8000 character limit")
    conv_id = payload.get("conversation_id")
    if conv_id is not None and not isinstance(conv_id, str):
        raise ValueError("field 'conversation_id' must be a string when present")


_ACTION_PATTERNS = [
    ("delete", re.compile(r"\b(delete|remove|erase)\b", re.I)),
    ("complete", re.compile(r"\b(complete|finish|mark.*done|check off)\b", re.I)),
    ("update", re.compile(r"\b(update|edit|change|rename)\b", re.I)),
    ("add", re.compile(r"\b(add|create|new task|insert)\b", re.I)),
    ("list", re.compile(r"\b(list|show|what are|display)\b", re.I)),
]

_BULK_PATTERN = re.compile(r"\ball\b|\beveryth?ing\b", re.I)
_QUOTED_TARGET = re.compile(r"['\"]([^'\"]+)['\"]")


def classify_action_intent(message: str) -> dict:
    """Classify a chat message into an action intent.

    Returns a dict with: action, needs_confirmation, target_hint.
    Destructive bulk actions (e.g. "delete all tasks") require confirmation.
    """
    if not isinstance(message, str):
        raise ValueError("message must be a string")
    action = "chat"
    for name, pattern in _ACTION_PATTERNS:
        if pattern.search(message):
            action = name
            break

    target_match = _QUOTED_TARGET.search(message)
    target_hint = target_match.group(1) if target_match else None

    is_bulk = bool(_BULK_PATTERN.search(message))
    needs_confirmation = action in ("delete", "complete") and (is_bulk or target_hint is None)

    return {
        "action": action,
        "needs_confirmation": needs_confirmation,
        "target_hint": target_hint,
        "is_bulk": is_bulk,
    }


def build_response_envelope(conversation_id: str, role: str, content: str, tool_calls=None) -> dict:
    if role not in ("user", "assistant", "system", "tool"):
        raise ValueError(f"invalid role: {role}")
    return {
        "id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "tool_calls": tool_calls or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def trim_history_for_context(messages: list, max_messages: int = 10) -> list:
    """Keep only the most recent max_messages, always preserving order."""
    if max_messages <= 0:
        return []
    return messages[-max_messages:]


def cmd_new_conversation_id(args):
    print(new_conversation_id())
    return 0


def cmd_validate_payload(args):
    try:
        payload = json.loads(args.payload)
        validate_message_payload(payload)
    except (ValueError, json.JSONDecodeError) as exc:
        print_error(str(exc))
        return 1
    print_success("payload is valid")
    return 0


def cmd_classify_intent(args):
    result = classify_action_intent(args.message)
    print(json.dumps(result, indent=2))
    return 0


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Chatbot Endpoint Tool")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("new-conversation-id").set_defaults(func=cmd_new_conversation_id)

    p = sub.add_parser("validate-payload")
    p.add_argument("--payload", required=True)
    p.set_defaults(func=cmd_validate_payload)

    p = sub.add_parser("classify-intent")
    p.add_argument("--message", required=True)
    p.set_defaults(func=cmd_classify_intent)

    sub.add_parser("test").set_defaults(func=cmd_test)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
