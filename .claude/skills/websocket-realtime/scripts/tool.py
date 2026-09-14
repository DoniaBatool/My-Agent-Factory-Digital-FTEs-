#!/usr/bin/env python3
"""
WebSocket Realtime Tool - real room broadcast targeting, message validation,
heartbeat expiry and sliding-window rate limiting helpers.
"""
import argparse
import json
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def build_room_key(namespace: str, room_id: str) -> str:
    if not namespace or not room_id:
        raise ValueError("namespace and room_id are required")
    return f"{namespace}:{room_id}"


def broadcast_targets(connections: dict, room_id: str, exclude_conn_id: str = None) -> list:
    """connections: {conn_id: {"room_id": ..., ...}}. Return conn_ids in room_id, sender excluded."""
    return [
        conn_id
        for conn_id, meta in connections.items()
        if meta.get("room_id") == room_id and conn_id != exclude_conn_id
    ]


_REQUIRED_MESSAGE_FIELDS = ("type", "data")
_ALLOWED_TYPES = {"chat", "join", "leave", "ping", "pong", "event"}


def validate_ws_message(payload: dict) -> list:
    errors = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]
    for field in _REQUIRED_MESSAGE_FIELDS:
        if field not in payload:
            errors.append(f"missing required field: {field}")
    msg_type = payload.get("type")
    if msg_type is not None and msg_type not in _ALLOWED_TYPES:
        errors.append(f"unknown message type: {msg_type}")
    return errors


def heartbeat_expired(last_ping_ts: float, now_ts: float, timeout: float = 30.0) -> bool:
    return (now_ts - last_ping_ts) > timeout


def rate_limit_check(state: dict, conn_id: str, now: float, max_msgs: int = 10, window: float = 1.0) -> bool:
    """Sliding-window rate limiter. Returns True if the message is allowed."""
    bucket = state.setdefault(conn_id, [])
    cutoff = now - window
    bucket[:] = [t for t in bucket if t > cutoff]
    if len(bucket) >= max_msgs:
        return False
    bucket.append(now)
    return True


def serialize_event(event_type: str, data) -> str:
    return json.dumps({"type": event_type, "data": data})


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="WebSocket Realtime Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
