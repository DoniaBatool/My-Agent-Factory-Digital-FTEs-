#!/usr/bin/env python3
"""
Observability & APM Tool - real span parsing, aggregation and alerting helpers.
"""
import argparse
import json
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def parse_trace_span(span: dict) -> dict:
    """Validate a raw span dict and return it annotated with duration_ms."""
    required = ("trace_id", "span_id", "name", "start_time", "end_time")
    missing = [f for f in required if f not in span]
    if missing:
        raise ValueError(f"span missing required fields: {', '.join(missing)}")
    duration_ms = (span["end_time"] - span["start_time"]) * 1000.0
    if duration_ms < 0:
        raise ValueError("end_time must not precede start_time")
    return {**span, "duration_ms": duration_ms}


def build_span_tree(spans: list) -> dict:
    """Build a nested tree of spans keyed by parent_id (root spans have parent_id None)."""
    by_parent = {}
    for span in spans:
        by_parent.setdefault(span.get("parent_id"), []).append(span)

    def attach(node):
        children = by_parent.get(node["span_id"], [])
        return {**node, "children": [attach(c) for c in children]}

    roots = by_parent.get(None, [])
    return {"roots": [attach(r) for r in roots]}


def detect_slow_spans(spans: list, threshold_ms: float = 500.0) -> list:
    """Return spans exceeding threshold_ms, sorted slowest-first."""
    parsed = [parse_trace_span(s) if "duration_ms" not in s else s for s in spans]
    slow = [s for s in parsed if s["duration_ms"] > threshold_ms]
    return sorted(slow, key=lambda s: s["duration_ms"], reverse=True)


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


def aggregate_metrics(samples: list) -> dict:
    """Compute min/max/avg/p50/p95/p99 for a list of numeric samples, no numpy required."""
    if not samples:
        return {"count": 0, "min": 0.0, "max": 0.0, "avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}
    ordered = sorted(samples)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "avg": sum(ordered) / len(ordered),
        "p50": _percentile(ordered, 50),
        "p95": _percentile(ordered, 95),
        "p99": _percentile(ordered, 99),
    }


def check_error_rate(total: int, errors: int, threshold: float = 0.05) -> dict:
    if total < 0 or errors < 0:
        raise ValueError("total and errors must be non-negative")
    if errors > total:
        raise ValueError("errors cannot exceed total")
    rate = (errors / total) if total > 0 else 0.0
    return {"rate": rate, "alert": rate > threshold, "total": total, "errors": errors}


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Observability & APM Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
