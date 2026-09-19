import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("connection_pooling_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_calculate_pool_size_divides_evenly_across_instances():
    result = tool.calculate_pool_size(num_instances=4, db_max_connections=100, reserved_for_admin=10)
    assert result["per_instance_total"] == 22


def test_calculate_pool_size_never_exceeds_db_budget_across_all_instances():
    result = tool.calculate_pool_size(num_instances=4, db_max_connections=100, reserved_for_admin=10)
    total = (result["pool_size"] + result["max_overflow"]) * 4
    assert total <= 90


def test_calculate_pool_size_minimum_one_per_instance():
    result = tool.calculate_pool_size(num_instances=50, db_max_connections=100, reserved_for_admin=10)
    assert result["pool_size"] >= 1


def test_calculate_pool_size_rejects_zero_instances():
    try:
        tool.calculate_pool_size(0, 100)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_generate_sqlalchemy_config_defaults():
    config = tool.generate_sqlalchemy_config(10, 5)
    assert config["pool_pre_ping"] is True
    assert config["pool_recycle"] == 1800


def test_generate_sqlalchemy_config_respects_overrides():
    config = tool.generate_sqlalchemy_config(10, 5, pool_recycle=600, pool_pre_ping=False)
    assert config["pool_recycle"] == 600
    assert config["pool_pre_ping"] is False
