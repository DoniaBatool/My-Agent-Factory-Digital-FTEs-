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
