#!/usr/bin/env python3
"""
API Docs Generator Tool - real FastAPI route extraction + markdown doc generation

Commands: extract-routes, generate-docs, test
"""
import argparse
import re
import sys

ROUTE_RE = re.compile(r"@\w+\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']")
FUNC_DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\(")


def extract_routes(source_code: str):
    """Real regex-based extraction of FastAPI-style route decorators paired
    with the function they decorate. Returns [{method, path, handler}]."""
    routes = []
    lines = source_code.splitlines()
    for i, line in enumerate(lines):
        m = ROUTE_RE.search(line)
        if not m:
            continue
        method, path = m.group(1), m.group(2)
        handler = None
        for j in range(i + 1, min(i + 5, len(lines))):
            fm = FUNC_DEF_RE.match(lines[j])
            if fm:
                handler = fm.group(1)
                break
        routes.append({"method": method.upper(), "path": path, "handler": handler})
    return routes


def generate_markdown_docs(routes):
    lines = ["# API Reference", "", "| Method | Path | Handler |", "|---|---|---|"]
    for r in routes:
        lines.append(f"| {r['method']} | `{r['path']}` | `{r['handler'] or '(unknown)'}` |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_extract_routes(args):
    import json
    with open(args.path) as f:
        source = f.read()
    routes = extract_routes(source)
    print(json.dumps(routes, indent=2))
    return 0 if routes else 1


def cmd_generate_docs(args):
    with open(args.path) as f:
        source = f.read()
    routes = extract_routes(source)
    docs = generate_markdown_docs(routes)
    if args.output:
        with open(args.output, "w") as f:
            f.write(docs)
        print(f"Wrote {args.output} ({len(routes)} routes)")
    else:
        print(docs)
    return 0


def cmd_test(args):
    source = (
        "@app.get('/tasks')\n"
        "async def list_tasks():\n"
        "    return []\n\n"
        "@app.post('/tasks')\n"
        "async def create_task(payload: TaskCreate):\n"
        "    return payload\n"
    )
    routes = extract_routes(source)
    ok = len(routes) == 2
    ok = ok and routes[0] == {"method": "GET", "path": "/tasks", "handler": "list_tasks"}
    docs = generate_markdown_docs(routes)
    ok = ok and "list_tasks" in docs and "| GET | `/tasks` |" in docs
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="API Docs Generator Tool")
    sub = parser.add_subparsers(dest="command")

    ex_p = sub.add_parser("extract-routes")
    ex_p.add_argument("path")

    gen_p = sub.add_parser("generate-docs")
    gen_p.add_argument("path")
    gen_p.add_argument("--output", default=None)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "extract-routes": cmd_extract_routes,
        "generate-docs": cmd_generate_docs,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
