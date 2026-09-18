#!/usr/bin/env python3
"""
User Isolation Tool - real static checks for ownership-scoped queries

Commands: check-query, scaffold-query, scan-file, test

Detects the exact bug class this skill exists to prevent (IDOR / missing
ownership filter) via real regex-based static analysis, instead of the
previous TODO stub.
"""
import argparse
import re
import sys

OWNER_COLUMN_CANDIDATES = ("user_id", "owner_id", "account_id", "created_by")


def has_ownership_filter(sql: str) -> bool:
    """True if the query filters on a known owner column, e.g.
    'WHERE user_id = :current_user_id' or 'AND owner_id = ?'."""
    sql_lower = sql.lower()
    return any(re.search(rf"\b{col}\s*=", sql_lower) for col in OWNER_COLUMN_CANDIDATES)


def accepts_client_supplied_user_id(code: str) -> bool:
    """Heuristic: flags patterns like `user_id = request.json['user_id']` or
    `user_id = params.get('user_id')` -- trusting a client-supplied user id
    as authority, which this skill's core rule forbids."""
    pattern = r"user_id\s*=\s*(request\.|params\.|args\.|body\.|payload\[)"
    return bool(re.search(pattern, code, re.IGNORECASE))


def build_scoped_query(table: str, id_column: str = "id", owner_column: str = "user_id") -> str:
    return (
        f"SELECT * FROM {table} WHERE {id_column} = :resource_id "
        f"AND {owner_column} = :current_user_id"
    )


def scan_source(code: str):
    """Scan a chunk of source for SQL-like SELECT/UPDATE/DELETE statements
    (very small embedded-SQL heuristic) and report which lack an ownership
    filter, plus any client-supplied-user_id red flags."""
    findings = []
    for match in re.finditer(r"(SELECT|UPDATE|DELETE)\b[^;\"']{0,300}", code, re.IGNORECASE):
        stmt = match.group(0)
        if not has_ownership_filter(stmt):
            findings.append({"statement": stmt.strip()[:120], "issue": "missing ownership filter"})
    if accepts_client_supplied_user_id(code):
        findings.append({"statement": None, "issue": "accepts client-supplied user_id as authority"})
    return findings


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_check_query(args):
    ok = has_ownership_filter(args.sql)
    print("OK: ownership-scoped" if ok else "FAIL: no ownership filter found")
    return 0 if ok else 1


def cmd_scaffold_query(args):
    print(build_scoped_query(args.table, args.id_column, args.owner_column))
    return 0


def cmd_scan_file(args):
    with open(args.path) as f:
        code = f.read()
    findings = scan_source(code)
    if not findings:
        print(f"OK: no ownership issues found in {args.path}")
        return 0
    for f_ in findings:
        print(f"  - {f_['issue']}: {f_['statement']}")
    return 1


def cmd_test(args):
    ok = has_ownership_filter("SELECT * FROM tasks WHERE user_id = :uid")
    ok = ok and not has_ownership_filter("SELECT * FROM tasks WHERE id = :id")
    ok = ok and accepts_client_supplied_user_id("user_id = request.json['user_id']")
    ok = ok and not accepts_client_supplied_user_id("user_id = current_user.id")
    findings = scan_source("SELECT * FROM tasks WHERE id = :id")
    ok = ok and len(findings) == 1
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="User Isolation Tool")
    sub = parser.add_subparsers(dest="command")

    q_p = sub.add_parser("check-query")
    q_p.add_argument("sql")

    s_p = sub.add_parser("scaffold-query")
    s_p.add_argument("table")
    s_p.add_argument("--id-column", default="id")
    s_p.add_argument("--owner-column", default="user_id")

    f_p = sub.add_parser("scan-file")
    f_p.add_argument("path")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "check-query": cmd_check_query,
        "scaffold-query": cmd_scaffold_query,
        "scan-file": cmd_scan_file,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
