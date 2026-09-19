import json
import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("grafana_expert_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_find_first_existing_returns_first_match(tmp_path):
    a = tmp_path / "a.ini"
    b = tmp_path / "b.ini"
    b.write_text("x")
    assert tool.find_first_existing([str(a), str(b)]) == str(b)


def test_find_first_existing_returns_none_when_nothing_exists(tmp_path):
    assert tool.find_first_existing([str(tmp_path / "nope1"), str(tmp_path / "nope2")]) is None


def test_build_install_command_docker_ignores_os():
    assert "docker run" in tool.build_install_command("darwin", "docker")
    assert "docker run" in tool.build_install_command("linux", "docker")


def test_build_install_command_macos_native_uses_brew():
    assert tool.build_install_command("darwin", "native") == "brew install grafana"


def test_build_install_command_linux_native_uses_apt():
    cmd = tool.build_install_command("linux", "native")
    assert "apt-get install" in cmd and "grafana" in cmd


def test_build_install_command_rejects_unknown_os():
    try:
        tool.build_install_command("plan9", "native")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_build_datasource_payload_defaults():
    payload = tool.build_datasource_payload()
    assert payload["name"] == "Prometheus"
    assert payload["type"] == "prometheus"
    assert payload["isDefault"] is True


def test_build_datasource_payload_custom():
    payload = tool.build_datasource_payload(name="Loki", url="http://x:3100", ds_type="loki", is_default=False)
    assert payload == {"name": "Loki", "type": "loki", "url": "http://x:3100", "access": "proxy", "isDefault": False}


def test_build_dashboard_json_creates_one_panel_per_title():
    dashboard = tool.build_dashboard_json("My Dash", ["Requests", "Errors"])
    panels = dashboard["dashboard"]["panels"]
    assert dashboard["dashboard"]["title"] == "My Dash"
    assert len(panels) == 2
    assert {p["title"] for p in panels} == {"Requests", "Errors"}


def test_build_provisioning_yaml_contains_datasource_fields():
    yaml_text = tool.build_provisioning_yaml([{"name": "Prometheus", "type": "prometheus", "url": "http://x:9090", "isDefault": True}])
    assert "name: Prometheus" in yaml_text
    assert "type: prometheus" in yaml_text
    assert "isDefault: true" in yaml_text


def test_build_alert_rule_structure():
    rule = tool.build_alert_rule("High Errors", "avg() > 0.05", "10m")
    assert rule["title"] == "High Errors"
    assert rule["for"] == "10m"
    assert rule["labels"]["severity"] == "warning"


def test_diagnose_flags_only_failed_checks():
    checks = [("binary", "pass", ""), ("config", "fail", ""), ("api", "fail", "")]
    issues = tool.diagnose(checks)
    assert len(issues) == 2
    assert any("config" in i.lower() or "grafana.ini" in i.lower() for i in issues)


def test_diagnose_returns_empty_when_all_pass():
    checks = [("binary", "pass", ""), ("config", "pass", "")]
    assert tool.diagnose(checks) == []


def test_run_tests_performs_six_distinct_checks_not_a_fake_one(monkeypatch, tmp_path):
    """Regression test for the exact bug this rewrite fixes: a previous
    version's `test` command printed "[Test 1/6]" but only ever executed
    one real check. This asserts all six named checks actually run."""
    calls = []

    def fake_run_command(cmd, timeout=300):
        calls.append(cmd)
        return 1, "", "not running in test env"

    monkeypatch.setattr(tool, "run_command", fake_run_command)
    monkeypatch.setattr(tool.shutil, "which", lambda _: None)
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: None)

    class Args:
        pass

    rc = tool.run_tests(Args())
    assert rc == 1  # nothing available in the mocked env -> honest failure, not a fake pass
    assert len(calls) == 3  # api, datasource_api, alerting_api each issue one real subprocess call
