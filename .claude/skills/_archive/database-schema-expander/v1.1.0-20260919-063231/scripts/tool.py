#!/usr/bin/env python3
"""
Database Schema Expander Tool - real Alembic migration generation + zero-downtime checks

Commands: generate-add-column, generate-add-index, check-zero-downtime, test
"""
import argparse
import re
import sys


def check_zero_downtime_add_column(column_type: str, nullable: bool, default) -> list:
    violations = []
    if not nullable and default is None:
        violations.append("NOT NULL column with no default will fail on existing rows -- add a default or make it nullable first")
    return violations


def generate_add_column_migration(revision: str, down_revision: str, table: str, column: str, col_type: str, nullable=True, default=None, server_default=None):
    nullable_str = "True" if nullable else "False"
    default_kwarg = f", server_default='{server_default}'" if server_default is not None else ""
    upgrade = (
        f"    op.add_column('{table}', sa.Column('{column}', sa.{col_type}(), "
        f"nullable={nullable_str}{default_kwarg}))"
    )
    downgrade = f"    op.drop_column('{table}', '{column}')"
    return _render_migration(revision, down_revision, upgrade, downgrade)


def generate_add_index_migration(revision: str, down_revision: str, table: str, columns, index_name=None, unique=False):
    index_name = index_name or f"ix_{table}_{'_'.join(columns)}"
    cols_repr = ", ".join(f"'{c}'" for c in columns)
    upgrade = f"    op.create_index('{index_name}', '{table}', [{cols_repr}], unique={unique})"
    downgrade = f"    op.drop_index('{index_name}', table_name='{table}')"
    return _render_migration(revision, down_revision, upgrade, downgrade)


def _render_migration(revision, down_revision, upgrade_body, downgrade_body):
    return (
        f'"""auto-generated migration"""\n'
        f"revision = '{revision}'\n"
        f"down_revision = '{down_revision}'\n\n"
        f"from alembic import op\nimport sqlalchemy as sa\n\n\n"
        f"def upgrade():\n{upgrade_body}\n\n\n"
        f"def downgrade():\n{downgrade_body}\n"
    )


def cmd_generate_add_column(args):
    violations = check_zero_downtime_add_column(args.type, args.nullable, args.default)
    if violations and not args.force:
        print("BLOCKED (zero-downtime check):")
        for v in violations:
            print(f"  - {v}")
        return 1
    migration = generate_add_column_migration(
        args.revision, args.down_revision, args.table, args.column, args.type,
        nullable=args.nullable, default=args.default, server_default=args.server_default,
    )
    print(migration)
    return 0


def cmd_generate_add_index(args):
    migration = generate_add_index_migration(
        args.revision, args.down_revision, args.table, args.columns.split(","),
        index_name=args.index_name, unique=args.unique,
    )
    print(migration)
    return 0


def cmd_check_zero_downtime(args):
    violations = check_zero_downtime_add_column(args.type, args.nullable, args.default)
    if not violations:
        print("OK: safe for zero-downtime deploy")
        return 0
    for v in violations:
        print(f"  - {v}")
    return 1


def cmd_test(args):
    violations = check_zero_downtime_add_column("String", nullable=False, default=None)
    ok = len(violations) == 1
    ok = ok and check_zero_downtime_add_column("String", nullable=True, default=None) == []
    migration = generate_add_column_migration("abc123", "xyz789", "tasks", "priority", "String", nullable=True)
    ok = ok and "op.add_column('tasks'" in migration and "def downgrade" in migration
    idx_migration = generate_add_index_migration("abc124", "abc123", "tasks", ["user_id", "status"])
    ok = ok and "op.create_index('ix_tasks_user_id_status'" in idx_migration
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Database Schema Expander Tool")
    sub = parser.add_subparsers(dest="command")

    col_p = sub.add_parser("generate-add-column")
    col_p.add_argument("--revision", required=True)
    col_p.add_argument("--down-revision", required=True)
    col_p.add_argument("--table", required=True)
    col_p.add_argument("--column", required=True)
    col_p.add_argument("--type", required=True)
    col_p.add_argument("--nullable", action="store_true", default=True)
    col_p.add_argument("--not-nullable", dest="nullable", action="store_false")
    col_p.add_argument("--default", default=None)
    col_p.add_argument("--server-default", default=None)
    col_p.add_argument("--force", action="store_true")

    idx_p = sub.add_parser("generate-add-index")
    idx_p.add_argument("--revision", required=True)
    idx_p.add_argument("--down-revision", required=True)
    idx_p.add_argument("--table", required=True)
    idx_p.add_argument("--columns", required=True, help="comma-separated")
    idx_p.add_argument("--index-name", default=None)
    idx_p.add_argument("--unique", action="store_true")

    zd_p = sub.add_parser("check-zero-downtime")
    zd_p.add_argument("--type", required=True)
    zd_p.add_argument("--nullable", action="store_true", default=True)
    zd_p.add_argument("--not-nullable", dest="nullable", action="store_false")
    zd_p.add_argument("--default", default=None)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "generate-add-column": cmd_generate_add_column,
        "generate-add-index": cmd_generate_add_index,
        "check-zero-downtime": cmd_check_zero_downtime,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
