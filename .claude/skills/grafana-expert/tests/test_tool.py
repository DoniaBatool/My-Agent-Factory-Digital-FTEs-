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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import subprocess as _subprocess


class _Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# -- run_command: real subprocess behavior (shell/capture/text flags) --

def test_run_command_executes_shell_command_and_captures_text_output():
    code, out, err = tool.run_command("echo hello_grafana_test")
    assert code == 0
    assert isinstance(out, str)
    assert "hello_grafana_test" in out


def test_run_command_handles_timeout():
    code, out, err = tool.run_command("sleep 2", timeout=0.2)
    assert code == 1
    assert out == ""
    assert "Timeout after 0.2s" in err


def test_run_command_handles_generic_exception_gracefully():
    code, out, err = tool.run_command(None)
    assert code == 1
    assert out == ""
    assert err  # some exception message was captured, not raised


# -- pure helpers: boolean-literal edge cases --

def test_build_dashboard_json_sets_overwrite_true_and_schema_version():
    dashboard = tool.build_dashboard_json("T", ["A"])
    assert dashboard["overwrite"] is True
    assert dashboard["dashboard"]["schemaVersion"] == 39


def test_build_provisioning_yaml_defaults_isdefault_false_when_key_absent():
    yaml_text = tool.build_provisioning_yaml([{"name": "X", "type": "prometheus", "url": "http://x"}])
    assert "isDefault: false" in yaml_text


# -- check_prerequisites --

def test_check_prerequisites_all_present_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/grafana-server")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "All prerequisites met" in out


def test_check_prerequisites_missing_binary_returns_1(monkeypatch):
    monkeypatch.setattr(tool.shutil, "which", lambda name: None)
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])
    rc = tool.check_prerequisites(_Args())
    assert rc == 1


def test_check_prerequisites_missing_provisioning_only_still_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/grafana-server")

    def fake_ffe(paths):
        return paths[0] if paths == tool.GRAFANA_CONF_PATHS else None

    monkeypatch.setattr(tool, "find_first_existing", fake_ffe)
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0  # a missing provisioning dir alone must not fail prerequisites
    assert "No provisioning directory found" in out


def test_check_prerequisites_missing_config_returns_1(monkeypatch):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/grafana-server")

    def fake_ffe(paths):
        return paths[0] if paths == tool.GRAFANA_PROVISIONING_PATHS else None

    monkeypatch.setattr(tool, "find_first_existing", fake_ffe)
    rc = tool.check_prerequisites(_Args())
    assert rc == 1


# -- install --

def test_install_docker_success_prints_default_url(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "darwin")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    rc = tool.install(_Args(method="docker"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Default URL" in out


def test_install_native_darwin_success_no_default_url(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "darwin")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    rc = tool.install(_Args(method="native"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "brew install grafana" in out
    assert "Default URL" not in out


def test_install_defaults_method_to_docker_when_none(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "linux")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    rc = tool.install(_Args(method=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "docker run" in out


def test_install_unsupported_os_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "plan9")
    rc = tool.install(_Args(method="native"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Unsupported OS" in out


def test_install_run_command_failure_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "darwin")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", "boom"))
    rc = tool.install(_Args(method="docker"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Install failed" in out


# -- setup_datasource --

def test_setup_datasource_success_returns_0(monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "201", ""))
    rc = tool.setup_datasource(_Args(name=None, url=None, type=None))
    assert rc == 0


def test_setup_datasource_bad_http_code_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "500", ""))
    rc = tool.setup_datasource(_Args(name=None, url=None, type=None))
    out = capsys.readouterr().out
    assert rc == 1
    assert "http=500" in out


def test_setup_datasource_run_command_nonzero_returns_1(monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", "conn refused"))
    rc = tool.setup_datasource(_Args(name="Loki", url="http://x", type="loki"))
    assert rc == 1


# -- create_dashboard --

def test_create_dashboard_writes_expected_json_custom_panels(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = tool.create_dashboard(_Args(panels="A,B,C", title="Custom", output=None))
    assert rc == 0
    data = json.loads((tmp_path / "dashboard.json").read_text())
    assert data["dashboard"]["title"] == "Custom"
    assert len(data["dashboard"]["panels"]) == 3


def test_create_dashboard_defaults_to_three_standard_panels(tmp_path):
    out_path = tmp_path / "out.json"
    rc = tool.create_dashboard(_Args(panels=None, title=None, output=str(out_path)))
    assert rc == 0
    data = json.loads(out_path.read_text())
    assert data["dashboard"]["title"] == "Service Overview"
    assert len(data["dashboard"]["panels"]) == 3


# -- provision --

def test_provision_writes_yaml_to_explicit_output_dir(tmp_path):
    out_dir = tmp_path / "prov"
    rc = tool.provision(_Args(name=None, url=None, output_dir=str(out_dir)))
    assert rc == 0
    content = (out_dir / "datasources.yaml").read_text()
    assert "name: Prometheus" in content


def test_provision_falls_back_to_relative_dir_when_none_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: None)
    rc = tool.provision(_Args(name="X", url="http://y", output_dir=None))
    assert rc == 0
    content = (tmp_path / "provisioning" / "datasources" / "datasources.yaml").read_text()
    assert "name: X" in content


# -- configure_alerting --

def test_configure_alerting_writes_expected_json_custom(tmp_path):
    out_path = tmp_path / "a.json"
    rc = tool.configure_alerting(_Args(name="MyAlert", condition="foo>1", for_duration="15m", output=str(out_path)))
    assert rc == 0
    data = json.loads(out_path.read_text())
    assert data["title"] == "MyAlert"
    assert data["for"] == "15m"
    assert data["condition"] == "foo>1"


def test_configure_alerting_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = tool.configure_alerting(_Args(name=None, condition=None, for_duration=None, output=None))
    assert rc == 0
    data = json.loads((tmp_path / "alert-rule.json").read_text())
    assert data["title"] == "High Error Rate"
    assert data["for"] == "5m"
    assert "avg() of query" in data["condition"]


# -- run_tests: all-pass branch (complements the existing all-fail regression test) --

def test_run_tests_all_pass_returns_0(monkeypatch):
    monkeypatch.setattr(tool.shutil, "which", lambda n: "/usr/bin/grafana-server")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=10: (0, "200", ""))
    rc = tool.run_tests(_Args())
    assert rc == 0


# -- troubleshoot --

def test_troubleshoot_all_present_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda n: "/usr/bin/grafana-server")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "No issues detected" in out


def test_troubleshoot_missing_everything_returns_1_with_remediation(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda n: None)
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: None)
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Grafana binary not found" in out


# -- main(): CLI dispatch + argparse validation --

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_check_prerequisites_dispatch(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-prerequisites"])
    monkeypatch.setattr(tool.shutil, "which", lambda n: "/usr/bin/grafana-server")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])
    assert tool.main() == 0


def test_main_install_invalid_method_choice_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "install", "--method", "bogus"])
    try:
        tool.main()
        assert False, "expected SystemExit from argparse choices validation"
    except SystemExit as e:
        assert e.code == 2


def test_main_install_dispatch(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "install", "--method", "docker"])
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    assert tool.main() == 0


def test_main_setup_datasource_dispatch(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "setup-datasource"])
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "200", ""))
    assert tool.main() == 0


def test_main_create_dashboard_dispatch(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-dashboard", "--title", "X"])
    assert tool.main() == 0
    assert (tmp_path / "dashboard.json").exists()


def test_main_provision_dispatch(monkeypatch, tmp_path):
    out_dir = tmp_path / "d"
    monkeypatch.setattr(sys, "argv", ["tool.py", "provision", "--output-dir", str(out_dir)])
    assert tool.main() == 0
    assert (out_dir / "datasources.yaml").exists()


def test_main_configure_alerting_dispatch(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["tool.py", "configure-alerting"])
    assert tool.main() == 0
    assert (tmp_path / "alert-rule.json").exists()


def test_main_test_dispatch(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    monkeypatch.setattr(tool.shutil, "which", lambda n: "/usr/bin/grafana-server")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=10: (0, "200", ""))
    assert tool.main() == 0


def test_main_troubleshoot_dispatch(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "troubleshoot"])
    monkeypatch.setattr(tool.shutil, "which", lambda n: "/usr/bin/grafana-server")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])
    assert tool.main() == 0


def test_subprocess_runs_as_script_check_prerequisites():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = _subprocess.run(
        [sys.executable, str(script), "check-prerequisites"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode in (0, 1)
    assert "Prerequisites" in result.stdout


def test_run_tests_partial_failure_prints_remediation_warning(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda n: None)  # binary check fails
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])  # config/provisioning pass
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=10: (0, "200", ""))  # api checks pass
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    # the one failing check's remediation text must actually be printed --
    # this only happens on the "not everything passed" branch
    assert "Grafana binary not found" in out


def test_run_tests_uses_correct_success_and_error_icon_per_check(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda n: None)  # binary fails
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: paths[0])  # config/provisioning pass
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=10: (0, "200", ""))  # api checks pass
    tool.run_tests(_Args())
    out = capsys.readouterr().out
    lines = out.splitlines()
    binary_line = next(l for l in lines if "binary:" in l)
    config_line = next(l for l in lines if "config:" in l)
    assert "✗" in binary_line  # failing check must print with the cross mark
    assert "✓" in config_line  # passing check must print with the check mark


def test_provision_writing_to_already_existing_dir_does_not_raise(tmp_path):
    out_dir = tmp_path / "prov"
    out_dir.mkdir()  # pre-create so os.makedirs must tolerate an existing directory
    rc = tool.provision(_Args(name=None, url=None, output_dir=str(out_dir)))
    assert rc == 0
    assert (out_dir / "datasources.yaml").exists()
