#!/usr/bin/env python3
"""
Database Engineer Tool - real index suggestion + migration safety checks

Commands: suggest-indexes, check-migration-safety, check-constraints, test
"""
import argparse
import json
import re
import sys

RISKY_MIGRATION_PATTERNS = {
    "drop_column": re.compile(r"(?i)DROP\s+COLUMN"),
    "drop_table": re.compile(r"(?i)DROP\s+TABLE(?!\s+IF\s+EXISTS)"),
    "not_null_no_default": re.compile(r"(?i)ADD\s+COLUMN\s+\w+\s+\w+\s+NOT\s+NULL(?!.*DEFAULT)"),
    "rename_column": re.compile(r"(?i)RENAME\s+COLUMN"),
    "alter_column_type": re.compile(r"(?i)ALTER\s+COLUMN\s+\w+\s+TYPE"),
}

RISK_ADVICE = {
    "drop_column": "Dropping a column is irreversible without a backup; add a deprecation window first.",
    "drop_table": "DROP TABLE without IF EXISTS will fail on repeat runs and can't be made idempotent easily.",
    "not_null_no_default": "Adding a NOT NULL column with no DEFAULT will fail on a non-empty table.",
    "rename_column": "Renaming breaks any code still reading the old name during a rolling deploy.",
    "alter_column_type": "Changing a column's type can lock the table on large datasets.",
}


def check_migration_safety(sql: str):
    """Return list of {risk, advice} for every risky pattern found."""
    return [
        {"risk": name, "advice": RISK_ADVICE[name]}
        for name, pattern in RISKY_MIGRATION_PATTERNS.items()
        if pattern.search(sql)
    ]


def suggest_indexes(where_clauses):
    """where_clauses: list of SQL WHERE-clause strings from real hot
    queries. Returns columns that appear in an equality/range/LIKE filter
    often enough (>=2 occurrences) to be worth an index, most-frequent
    first."""
    counts = {}
    for clause in where_clauses:
        for col in re.findall(r"\b(\w+)\s*(?:=|>=|<=|>|<)", clause):
            counts[col] = counts.get(col, 0) + 1
        for col in re.findall(r"\b(\w+)\s+LIKE\b", clause, re.IGNORECASE):
            counts[col] = counts.get(col, 0) + 1
    return sorted((c for c, n in counts.items() if n >= 2), key=lambda c: -counts[c])


def check_constraints(create_table_sql: str):
    """Return list of missing-constraint warnings for a CREATE TABLE
    statement: columns with no NOT NULL, and absence of any PRIMARY KEY.
    Works for single-line or multi-line CREATE TABLE bodies by parsing the
    parenthesised column list directly rather than anchoring on line
    starts."""
    warnings = []
    if not re.search(r"(?i)PRIMARY\s+KEY", create_table_sql):
        warnings.append("no PRIMARY KEY defined")
    match = re.search(r"\((.*)\)\s*;?\s*$", create_table_sql, re.DOTALL)
    if not match:
        return warnings
    for col_def in match.group(1).split(","):
        col_def = col_def.strip()
        m = re.match(r"(\w+)\s+(INTEGER|TEXT|VARCHAR\(\d+\)|BOOLEAN|TIMESTAMP)\b", col_def, re.IGNORECASE)
        if m and "PRIMARY KEY" not in col_def.upper() and "NOT NULL" not in col_def.upper():
            warnings.append(f"column '{m.group(1)}' has no NOT NULL constraint")
    return warnings


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_suggest_indexes(args):
    clauses = args.where.split(";")
    print(json.dumps(suggest_indexes(clauses), indent=2))
    return 0


def cmd_check_migration_safety(args):
    with open(args.path) as f:
        sql = f.read()
    risks = check_migration_safety(sql)
    if not risks:
        print("OK: no risky patterns found")
        return 0
    for r in risks:
        print(f"  - [{r['risk']}] {r['advice']}")
    return 1


def cmd_check_constraints(args):
    with open(args.path) as f:
        sql = f.read()
    warnings = check_constraints(sql)
    if not warnings:
        print("OK: no constraint issues found")
        return 0
    for w in warnings:
        print(f"  - {w}")
    return 1


def cmd_test(args):
    risks = check_migration_safety("ALTER TABLE tasks DROP COLUMN legacy_field;")
    ok = any(r["risk"] == "drop_column" for r in risks)
    idx = suggest_indexes(["WHERE user_id = 1 AND status = 'open'", "WHERE user_id = 2"])
    ok = ok and idx[0] == "user_id"
    warnings = check_constraints("CREATE TABLE t (id INTEGER, name TEXT);")
    ok = ok and any("PRIMARY KEY" in w for w in warnings)
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Database Engineer Tool")
    sub = parser.add_subparsers(dest="command")

    idx_p = sub.add_parser("suggest-indexes")
    idx_p.add_argument("--where", required=True, help="semicolon-separated WHERE clauses")

    mig_p = sub.add_parser("check-migration-safety")
    mig_p.add_argument("path")

    con_p = sub.add_parser("check-constraints")
    con_p.add_argument("path")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "suggest-indexes": cmd_suggest_indexes,
        "check-migration-safety": cmd_check_migration_safety,
        "check-constraints": cmd_check_constraints,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
