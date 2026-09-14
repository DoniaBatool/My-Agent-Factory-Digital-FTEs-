#!/usr/bin/env python3
"""
Conversation Manager Tool - real helpers for conversation persistence & retrieval.
"""
import argparse
import json
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def assert_owns_conversation(user_id: str, owner_id: str) -> None:
    """Raise PermissionError if the requesting user does not own the conversation."""
    if user_id != owner_id:
        raise PermissionError("user does not own this conversation")


def latest_message_preview(messages: list, max_len: int = 80) -> str:
    if not messages:
        return ""
    content = messages[-1].get("content", "")
    content = " ".join(content.split())
    if len(content) <= max_len:
        return content
    return content[: max_len - 1].rstrip() + "…"


def build_conversation_list(conversations: list, messages_by_conv: dict) -> list:
    """Return conversations sorted by most-recent-activity desc, each annotated with a preview."""
    out = []
    for conv in conversations:
        msgs = messages_by_conv.get(conv["id"], [])
        last_ts = msgs[-1]["created_at"] if msgs else conv.get("created_at", "")
        out.append({
            **conv,
            "preview": latest_message_preview(msgs),
            "message_count": len(msgs),
            "last_activity_at": last_ts,
        })
    out.sort(key=lambda c: c["last_activity_at"], reverse=True)
    return out


def paginate_messages(messages: list, limit: int = 20, before_id: str = None) -> dict:
    """Cursor-based pagination over an ordered (oldest-first) message list.

    before_id, when given, returns the `limit` messages immediately before that id.
    """
    if limit <= 0:
        raise ValueError("limit must be positive")
    if before_id is None:
        page = messages[-limit:]
    else:
        idx = next((i for i, m in enumerate(messages) if m["id"] == before_id), None)
        if idx is None:
            raise ValueError(f"unknown message id: {before_id}")
        start = max(0, idx - limit)
        page = messages[start:idx]
    has_more = bool(page) and messages.index(page[0]) > 0
    return {"messages": page, "has_more": has_more}


def cascade_delete_plan(conversation_id: str, messages: list) -> dict:
    """Compute what a cascade delete of a conversation removes."""
    message_ids = [m["id"] for m in messages if m.get("conversation_id") == conversation_id]
    return {"conversation_id": conversation_id, "delete_message_ids": message_ids, "count": len(message_ids)}


def scoped_conversations_for_user(conversations: list, user_id: str) -> list:
    """Filter conversations to those owned by user_id -- the isolation boundary for list endpoints."""
    return [c for c in conversations if c.get("user_id") == user_id]


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Conversation Manager Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
