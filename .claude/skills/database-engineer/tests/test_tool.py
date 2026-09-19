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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json as _json
import subprocess
import sys as _sys
import pytest


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_check_migration_safety_drop_table_if_exists_is_not_flagged():
    risks = tool.check_migration_safety("DROP TABLE IF EXISTS legacy_reports;")
    assert not any(r["risk"] == "drop_table" for r in risks)


def test_check_migration_safety_drop_table_without_if_exists_is_flagged():
    risks = tool.check_migration_safety("DROP TABLE legacy_reports;")
    assert any(r["risk"] == "drop_table" for r in risks)


def test_check_migration_safety_flags_rename_column():
    risks = tool.check_migration_safety("ALTER TABLE t RENAME COLUMN old_name TO new_name;")
    assert any(r["risk"] == "rename_column" for r in risks)


def test_check_migration_safety_flags_alter_column_type():
    risks = tool.check_migration_safety("ALTER TABLE t ALTER COLUMN age TYPE BIGINT;")
    assert any(r["risk"] == "alter_column_type" for r in risks)


def test_check_migration_safety_detects_multiple_risks_at_once():
    sql = "ALTER TABLE t DROP COLUMN a; ALTER TABLE t RENAME COLUMN b TO c;"
    risks = tool.check_migration_safety(sql)
    risk_names = {r["risk"] for r in risks}
    assert {"drop_column", "rename_column"} <= risk_names


def test_suggest_indexes_matches_like_case_insensitively():
    clauses = ["WHERE name like '%a%'", "WHERE name LIKE '%b%'"]
    result = tool.suggest_indexes(clauses)
    assert "name" in result


def test_suggest_indexes_handles_all_comparator_operators():
    clauses = [
        "WHERE age >= 18",
        "WHERE age <= 65",
    ]
    result = tool.suggest_indexes(clauses)
    assert "age" in result


def test_suggest_indexes_captures_column_after_table_prefix_dot():
    clauses = ["WHERE a.user_id = 1", "WHERE a.user_id = 2"]
    result = tool.suggest_indexes(clauses)
    assert "user_id" in result
    assert "a" not in result


def test_check_constraints_varchar_type_is_never_flagged_due_to_trailing_boundary():
    # Documents an actual regex quirk in check_constraints: the VARCHAR(\d+)
    # alternative ends in a literal closing paren, so the trailing \b anchor
    # can never be satisfied (a ")" is non-word, and nothing valid can follow
    # it in real SQL that would also be a word character) -- VARCHAR columns
    # are therefore silently never flagged as missing NOT NULL, unlike
    # INTEGER/TEXT/BOOLEAN/TIMESTAMP columns which do get flagged.
    warnings = tool.check_constraints("CREATE TABLE t (id INTEGER PRIMARY KEY, email VARCHAR(255));")
    assert not any("email" in w for w in warnings)


def test_check_constraints_does_not_flag_inline_not_null_column():
    warnings = tool.check_constraints("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT NOT NULL);")
    assert not any("name" in w for w in warnings)


def test_check_constraints_handles_multiline_sql():
    sql = """CREATE TABLE t (
        id INTEGER PRIMARY KEY,
        name TEXT
    );"""
    warnings = tool.check_constraints(sql)
    assert any("name" in w for w in warnings)


def test_check_constraints_no_parenthesised_column_list_only_reports_missing_pk():
    warnings = tool.check_constraints("CREATE TABLE t")
    assert warnings == ["no PRIMARY KEY defined"]


def test_cmd_suggest_indexes_prints_json(capsys):
    args = _Args(where="WHERE user_id = 1;WHERE user_id = 2")
    rc = tool.cmd_suggest_indexes(args)
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert data == ["user_id"]


def test_cmd_check_migration_safety_reads_file_and_reports_risks(tmp_path, capsys):
    sql_file = tmp_path / "migration.sql"
    sql_file.write_text("ALTER TABLE t DROP COLUMN old;")
    rc = tool.cmd_check_migration_safety(_Args(path=str(sql_file)))
    assert rc == 1
    out = capsys.readouterr().out
    assert "drop_column" in out


def test_cmd_check_migration_safety_clean_file_returns_ok(tmp_path, capsys):
    sql_file = tmp_path / "migration.sql"
    sql_file.write_text("ALTER TABLE t ADD COLUMN x TEXT DEFAULT 'y';")
    rc = tool.cmd_check_migration_safety(_Args(path=str(sql_file)))
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cmd_check_constraints_reads_file_and_reports_warnings(tmp_path, capsys):
    sql_file = tmp_path / "schema.sql"
    sql_file.write_text("CREATE TABLE t (id INTEGER, name TEXT);")
    rc = tool.cmd_check_constraints(_Args(path=str(sql_file)))
    assert rc == 1
    out = capsys.readouterr().out
    assert "PRIMARY KEY" in out


def test_cmd_check_constraints_clean_file_returns_ok(tmp_path, capsys):
    sql_file = tmp_path / "schema.sql"
    sql_file.write_text("CREATE TABLE t (id INTEGER PRIMARY KEY NOT NULL);")
    rc = tool.cmd_check_constraints(_Args(path=str(sql_file)))
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_suggest_indexes_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "suggest-indexes", "--where", "WHERE user_id = 1;WHERE user_id = 2"])
    rc = tool.main()
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert data == ["user_id"]


def test_main_check_migration_safety_end_to_end(monkeypatch, capsys, tmp_path):
    sql_file = tmp_path / "m.sql"
    sql_file.write_text("DROP TABLE t;")
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-migration-safety", str(sql_file)])
    rc = tool.main()
    assert rc == 1
    assert "drop_table" in capsys.readouterr().out


def test_main_check_constraints_end_to_end(monkeypatch, capsys, tmp_path):
    sql_file = tmp_path / "s.sql"
    sql_file.write_text("CREATE TABLE t (id INTEGER PRIMARY KEY NOT NULL);")
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-constraints", str(sql_file)])
    rc = tool.main()
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_missing_required_where_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "suggest-indexes"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_path_positional_for_migration_safety_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-migration-safety"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_path_positional_for_constraints_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-constraints"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_cli_smoke_runs_as_main_entrypoint():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "suggest-indexes", "--where", "WHERE user_id = 1;WHERE user_id = 2"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "user_id" in proc.stdout
