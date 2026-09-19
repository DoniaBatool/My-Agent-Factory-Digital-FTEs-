import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("database_schema_expander_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_check_zero_downtime_flags_not_null_without_default():
    violations = tool.check_zero_downtime_add_column("String", nullable=False, default=None)
    assert len(violations) == 1


def test_check_zero_downtime_ok_when_nullable():
    assert tool.check_zero_downtime_add_column("String", nullable=True, default=None) == []


def test_check_zero_downtime_ok_when_not_null_with_default():
    assert tool.check_zero_downtime_add_column("String", nullable=False, default="medium") == []


def test_generate_add_column_migration_has_upgrade_and_downgrade():
    migration = tool.generate_add_column_migration("r1", "r0", "tasks", "priority", "String")
    assert "def upgrade():" in migration
    assert "def downgrade():" in migration
    assert "op.add_column('tasks'" in migration
    assert "op.drop_column('tasks', 'priority')" in migration


def test_generate_add_column_migration_includes_server_default_when_given():
    migration = tool.generate_add_column_migration("r1", "r0", "tasks", "priority", "String", server_default="medium")
    assert "server_default='medium'" in migration


def test_generate_add_index_migration_default_name():
    migration = tool.generate_add_index_migration("r2", "r1", "tasks", ["user_id", "status"])
    assert "ix_tasks_user_id_status" in migration
    assert "unique=False" in migration


def test_generate_add_index_migration_custom_name_and_unique():
    migration = tool.generate_add_index_migration("r2", "r1", "tasks", ["email"], index_name="uq_users_email", unique=True)
    assert "uq_users_email" in migration
    assert "unique=True" in migration

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import subprocess
import sys as _sys
import pytest


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_cmd_generate_add_column_blocked_when_not_null_no_default(capsys):
    args = _Args(revision="r1", down_revision="r0", table="tasks", column="priority",
                 type="String", nullable=False, default=None, server_default=None, force=False)
    rc = tool.cmd_generate_add_column(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "BLOCKED" in out
    assert "will fail on existing rows" in out


def test_cmd_generate_add_column_force_overrides_block(capsys):
    args = _Args(revision="r1", down_revision="r0", table="tasks", column="priority",
                 type="String", nullable=False, default=None, server_default=None, force=True)
    rc = tool.cmd_generate_add_column(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "op.add_column('tasks'" in out
    assert "nullable=False" in out


def test_cmd_generate_add_column_success_when_nullable(capsys):
    args = _Args(revision="r1", down_revision="r0", table="tasks", column="priority",
                 type="String", nullable=True, default=None, server_default=None, force=False)
    rc = tool.cmd_generate_add_column(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "op.add_column('tasks'" in out


def test_cmd_generate_add_index_prints_migration(capsys):
    args = _Args(revision="r2", down_revision="r1", table="tasks", columns="user_id,status",
                 index_name=None, unique=False)
    rc = tool.cmd_generate_add_index(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "ix_tasks_user_id_status" in out


def test_cmd_check_zero_downtime_ok_path(capsys):
    args = _Args(type="String", nullable=True, default=None)
    rc = tool.cmd_check_zero_downtime(args)
    assert rc == 0
    assert "OK: safe for zero-downtime deploy" in capsys.readouterr().out


def test_cmd_check_zero_downtime_violation_path(capsys):
    args = _Args(type="String", nullable=False, default=None)
    rc = tool.cmd_check_zero_downtime(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "will fail on existing rows" in out


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_generate_add_column_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-column", "--revision", "r1",
                                        "--down-revision", "r0", "--table", "tasks",
                                        "--column", "priority", "--type", "String"])
    rc = tool.main()
    assert rc == 0
    assert "op.add_column('tasks'" in capsys.readouterr().out


def test_main_generate_add_column_not_nullable_flag_blocks(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-column", "--revision", "r1",
                                        "--down-revision", "r0", "--table", "tasks",
                                        "--column", "priority", "--type", "String", "--not-nullable"])
    rc = tool.main()
    assert rc == 1
    assert "BLOCKED" in capsys.readouterr().out


def test_main_generate_add_index_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-index", "--revision", "r2",
                                        "--down-revision", "r1", "--table", "tasks", "--columns", "email",
                                        "--index-name", "uq_users_email", "--unique"])
    rc = tool.main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "uq_users_email" in out
    assert "unique=True" in out


def test_main_check_zero_downtime_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-zero-downtime", "--type", "String", "--not-nullable"])
    rc = tool.main()
    assert rc == 1
    assert "will fail on existing rows" in capsys.readouterr().out


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_missing_required_revision_for_add_column_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-column", "--down-revision", "r0",
                                        "--table", "tasks", "--column", "priority", "--type", "String"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_type_for_add_column_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-column", "--revision", "r1",
                                        "--down-revision", "r0", "--table", "tasks", "--column", "priority"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_columns_for_add_index_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-index", "--revision", "r2",
                                        "--down-revision", "r1", "--table", "tasks"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_type_for_check_zero_downtime_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-zero-downtime"])
    with pytest.raises(SystemExit):
        tool.main()


def test_generate_add_index_multiple_columns_joined_with_commas_in_output():
    migration = tool.generate_add_index_migration("r2", "r1", "tasks", ["a", "b", "c"])
    assert "['a', 'b', 'c']" in migration


def test_subprocess_cli_smoke_runs_as_main_entrypoint():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "check-zero-downtime", "--type", "String"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "OK" in proc.stdout


def test_generate_add_column_migration_defaults_to_nullable_true_when_omitted():
    migration = tool.generate_add_column_migration("r1", "r0", "tasks", "priority", "String")
    assert "nullable=True" in migration


def test_main_missing_required_down_revision_for_add_column_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-column", "--revision", "r1",
                                        "--table", "tasks", "--column", "priority", "--type", "String"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_table_for_add_column_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-column", "--revision", "r1",
                                        "--down-revision", "r0", "--column", "priority", "--type", "String"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_column_for_add_column_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-column", "--revision", "r1",
                                        "--down-revision", "r0", "--table", "tasks", "--type", "String"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_revision_for_add_index_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-index", "--down-revision", "r1",
                                        "--table", "tasks", "--columns", "email"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_down_revision_for_add_index_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-index", "--revision", "r2",
                                        "--table", "tasks", "--columns", "email"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_table_for_add_index_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-add-index", "--revision", "r2",
                                        "--down-revision", "r1", "--columns", "email"])
    with pytest.raises(SystemExit):
        tool.main()
