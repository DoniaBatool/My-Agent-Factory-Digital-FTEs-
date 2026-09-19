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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json as _json
import subprocess
import sys as _sys
import pytest


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_cmd_calculate_pool_size_success_prints_json(capsys):
    args = _Args(instances=4, db_max_connections=100, reserved=10)
    rc = tool.cmd_calculate_pool_size(args)
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["per_instance_total"] == 22


def test_cmd_calculate_pool_size_invalid_instances_returns_1_and_prints_message(capsys):
    args = _Args(instances=0, db_max_connections=100, reserved=5)
    rc = tool.cmd_calculate_pool_size(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "positive" in out


def test_cmd_generate_config_no_pre_ping_flag_disables_pre_ping(capsys):
    args = _Args(pool_size=10, max_overflow=5, pool_recycle=900, no_pre_ping=True)
    rc = tool.cmd_generate_config(args)
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["pool_pre_ping"] is False
    assert data["pool_recycle"] == 900


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "usage" in out.lower()


def test_main_calculate_pool_size_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "calculate-pool-size", "--instances", "4",
                                        "--db-max-connections", "100", "--reserved", "10"])
    rc = tool.main()
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["per_instance_total"] == 22


def test_main_generate_config_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-config", "--pool-size", "10", "--max-overflow", "5"])
    rc = tool.main()
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["pool_size"] == 10


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_missing_required_instances_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "calculate-pool-size", "--db-max-connections", "100"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_pool_size_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-config", "--max-overflow", "5"])
    with pytest.raises(SystemExit):
        tool.main()


def test_calculate_pool_size_reserved_default_is_five():
    result = tool.calculate_pool_size(num_instances=2, db_max_connections=100)
    assert result["per_instance_total"] == 47


def test_calculate_pool_size_available_floors_at_num_instances_when_budget_too_small():
    result = tool.calculate_pool_size(num_instances=10, db_max_connections=5, reserved_for_admin=3)
    assert result["per_instance_total"] == 1
    assert result["pool_size"] == 1
    assert result["max_overflow"] == 0


def test_subprocess_cli_smoke_runs_as_main_entrypoint():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "calculate-pool-size", "--instances", "2", "--db-max-connections", "50"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "pool_size" in proc.stdout


def test_main_missing_required_max_overflow_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-config", "--pool-size", "10"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_db_max_connections_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "calculate-pool-size", "--instances", "4"])
    with pytest.raises(SystemExit):
        tool.main()
