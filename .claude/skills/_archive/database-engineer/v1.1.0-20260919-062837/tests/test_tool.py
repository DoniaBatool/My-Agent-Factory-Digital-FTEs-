import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("database_engineer_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_check_migration_safety_flags_drop_column():
    risks = tool.check_migration_safety("ALTER TABLE t DROP COLUMN old_field;")
    assert any(r["risk"] == "drop_column" for r in risks)


def test_check_migration_safety_flags_not_null_without_default():
    risks = tool.check_migration_safety("ALTER TABLE t ADD COLUMN priority TEXT NOT NULL;")
    assert any(r["risk"] == "not_null_no_default" for r in risks)


def test_check_migration_safety_clean_migration_has_no_risks():
    risks = tool.check_migration_safety("ALTER TABLE t ADD COLUMN priority TEXT DEFAULT 'medium';")
    assert risks == []


def test_suggest_indexes_ranks_most_frequent_column_first():
    clauses = ["WHERE user_id = 1", "WHERE user_id = 2 AND status = 'open'", "WHERE status = 'closed'"]
    result = tool.suggest_indexes(clauses)
    assert result[0] == "user_id"
    assert "status" in result


def test_suggest_indexes_ignores_columns_seen_only_once():
    result = tool.suggest_indexes(["WHERE rarely_used = 1"])
    assert result == []


def test_check_constraints_flags_missing_primary_key():
    warnings = tool.check_constraints("CREATE TABLE t (id INTEGER, name TEXT);")
    assert any("PRIMARY KEY" in w for w in warnings)


def test_check_constraints_flags_nullable_column():
    warnings = tool.check_constraints("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT);")
    assert any("name" in w for w in warnings)
