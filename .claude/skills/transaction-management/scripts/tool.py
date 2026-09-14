#!/usr/bin/env python3
"""
Transaction Management Tool - a real in-memory transaction log with rollback,
plus a genuine wait-for-graph deadlock detector.
"""
import argparse
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


_VALID_ISOLATION_LEVELS = {"READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"}


def validate_isolation_level(level: str) -> bool:
    return level.upper() in _VALID_ISOLATION_LEVELS


class Transaction:
    """A minimal ACID-style transaction: each op carries its own inverse for rollback."""

    def __init__(self):
        self.applied = []  # list of (description, inverse_fn)
        self.committed = False
        self.rolled_back = False

    def execute(self, apply_fn, inverse_fn, description: str = ""):
        if self.committed or self.rolled_back:
            raise RuntimeError("cannot execute on a finished transaction")
        apply_fn()
        self.applied.append((description, inverse_fn))

    def commit(self):
        if self.rolled_back:
            raise RuntimeError("cannot commit a rolled-back transaction")
        self.committed = True

    def rollback(self):
        if self.committed:
            raise RuntimeError("cannot roll back a committed transaction")
        for _, inverse_fn in reversed(self.applied):
            inverse_fn()
        self.rolled_back = True


def detect_deadlock_risk(lock_order: list) -> bool:
    """Given a list of (tx_id, resource_id) acquisition-order pairs (in the order each
    tx *waits for* a resource held by another tx as (waiting_tx, holding_tx) edges),
    build a wait-for graph and detect a cycle -> deadlock risk.

    lock_order: list of (waiting_tx, holding_tx) tuples.
    """
    graph = {}
    for waiting, holding in lock_order:
        graph.setdefault(waiting, set()).add(holding)
        graph.setdefault(holding, set())

    visiting = set()
    visited = set()

    def has_cycle(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbor in graph.get(node, ()):
            if has_cycle(neighbor):
                return True
        visiting.discard(node)
        visited.add(node)
        return False

    return any(has_cycle(node) for node in graph)


def retry_on_serialization_failure(fn, max_retries: int = 3, exceptions=(Exception,), sleep_fn=None):
    """Retry fn() up to max_retries times on a serialization/conflict failure."""
    last_exc = None
    for _ in range(max_retries):
        try:
            return fn()
        except exceptions as exc:
            last_exc = exc
            if sleep_fn:
                sleep_fn(0)
    raise last_exc


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Transaction Management Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
