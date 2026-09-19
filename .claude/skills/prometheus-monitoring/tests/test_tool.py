import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("prometheus_monitoring_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_find_first_existing_returns_first_match(tmp_path):
    a = tmp_path / "a.yml"
    b = tmp_path / "b.yml"
    b.write_text("x")
    assert tool.find_first_existing([str(a), str(b)]) == str(b)


def test_build_install_command_docker_ignores_os():
    assert "docker run" in tool.build_install_command("darwin", "docker")


def test_build_install_command_macos_native_uses_brew():
    assert tool.build_install_command("darwin", "native") == "brew install prometheus"


def test_build_install_command_linux_native_uses_apt():
    cmd = tool.build_install_command("linux", "native")
    assert "apt-get install" in cmd and "prometheus" in cmd


def test_build_install_command_rejects_unknown_os():
    try:
        tool.build_install_command("plan9", "native")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_build_scrape_config_defaults():
    config = tool.build_scrape_config()
    assert config["global"]["scrape_interval"] == "15s"
    assert config["scrape_configs"][0]["job_name"] == "app"
    assert config["scrape_configs"][0]["static_configs"][0]["targets"] == ["localhost:8080"]


def test_build_scrape_config_is_additive_with_existing_jobs():
    existing = [{"job_name": "prometheus", "static_configs": [{"targets": ["localhost:9090"]}]}]
    config = tool.build_scrape_config(job_name="app", target="localhost:8080", existing_jobs=existing)
    job_names = [j["job_name"] for j in config["scrape_configs"]]
    assert job_names == ["prometheus", "app"]


def test_dict_to_yaml_renders_nested_structure():
    yaml_text = tool.dict_to_yaml({"global": {"scrape_interval": "15s"}})
    assert "global:" in yaml_text
    assert "scrape_interval: 15s" in yaml_text


def test_build_exporter_command_known_type():
    cmd = tool.build_exporter_command("node")
    assert "9100:9100" in cmd
    assert "prom/node-exporter" in cmd


def test_build_exporter_command_rejects_unknown_type():
    try:
        tool.build_exporter_command("bogus")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_build_query_url_instant_query():
    url = tool.build_query_url("http://localhost:9090", "up", instant=True)
    assert url == "http://localhost:9090/api/v1/query?query=up"


def test_build_query_url_range_query_uses_query_range_endpoint():
    url = tool.build_query_url("http://localhost:9090", "up", instant=False)
    assert "/api/v1/query_range?query=up" in url


def test_diagnose_flags_only_failed_checks():
    checks = [("binary", "pass", ""), ("config", "fail", ""), ("api", "fail", "")]
    assert len(tool.diagnose(checks)) == 2


def test_run_tests_performs_six_distinct_checks_not_a_fake_one(monkeypatch):
    """Regression test for the exact bug fixed here: a previous version's
    `test` command printed "[Test 1/6]" but only ever executed one check."""
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
    assert rc == 1
    assert len(calls) == 4  # api, targets_api, node_exporter, alertmanager each issue one real call

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import subprocess as _subprocess
import pytest


class _Args:
    """Minimal argparse.Namespace stand-in: attributes are set explicitly
    per test so each cmd_* function under test gets exactly the inputs it
    reads (mirroring what argparse would produce, including None for an
    omitted optional so the `args.x or default` fallback branches run)."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_detect_os_lowercases_platform_system(monkeypatch):
    monkeypatch.setattr(tool.platform, "system", lambda: "Darwin")
    assert tool.detect_os() == "darwin"


def test_dict_to_yaml_handles_list_of_dicts():
    yaml_text = tool.dict_to_yaml({"scrape_configs": [{"job_name": "app", "static_configs": [{"targets": ["x:1"]}]}]})
    assert "- job_name: app" in yaml_text
    assert "targets:" in yaml_text


def test_build_query_url_encodes_special_characters():
    url = tool.build_query_url("http://localhost:9090", 'rate(x{job="app"}[5m])', instant=True)
    assert "{" not in url
    assert "%7B" in url
    assert "app" in url


def test_check_prerequisites_all_met(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/prometheus")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: "/etc/prometheus/prometheus.yml")
    rc = tool.check_prerequisites(_Args())
    assert rc == 0
    assert "All prerequisites met" in capsys.readouterr().out


def test_check_prerequisites_missing_binary_reports_issue(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: None)
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: None)
    rc = tool.check_prerequisites(_Args())
    assert rc == 1
    out = capsys.readouterr().out
    assert "Install with: python3 tool.py install" in out


def test_install_success_docker_prints_default_url(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "darwin")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "ok", ""))
    rc = tool.install(_Args(method="docker"))
    assert rc == 0
    assert "Default URL: http://localhost:9090" in capsys.readouterr().out


def test_install_failure_reports_stderr(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "linux")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", "boom"))
    rc = tool.install(_Args(method="native"))
    assert rc == 1
    assert "Install failed: boom" in capsys.readouterr().out


def test_install_unsupported_os_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "plan9")
    rc = tool.install(_Args(method="native"))
    assert rc == 1
    assert "Unsupported OS" in capsys.readouterr().out


def test_install_method_none_defaults_to_docker(monkeypatch):
    monkeypatch.setattr(tool, "detect_os", lambda: "linux")
    captured = {}

    def fake_run(cmd, timeout=300):
        captured["cmd"] = cmd
        return 0, "", ""

    monkeypatch.setattr(tool, "run_command", fake_run)
    rc = tool.install(_Args(method=None))
    assert rc == 0
    assert "docker run" in captured["cmd"]


def test_configure_scrape_writes_expected_yaml(tmp_path):
    out_file = tmp_path / "prom.yml"
    args = _Args(job_name="myapp", target="localhost:9999", interval="30s", output=str(out_file))
    rc = tool.configure_scrape(args)
    assert rc == 0
    content = out_file.read_text()
    assert "job_name: myapp" in content
    assert "localhost:9999" in content


def test_configure_scrape_defaults_when_args_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    args = _Args(job_name=None, target=None, interval=None, output=None)
    rc = tool.configure_scrape(args)
    assert rc == 0
    content = (tmp_path / "prometheus.yml").read_text()
    assert "job_name: app" in content


def test_add_exporter_success(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    rc = tool.add_exporter(_Args(type="blackbox"))
    assert rc == 0
    assert "started on port 9115" in capsys.readouterr().out


def test_add_exporter_unknown_type_returns_1(capsys):
    rc = tool.add_exporter(_Args(type="bogus"))
    assert rc == 1
    assert "Unknown exporter type" in capsys.readouterr().out


def test_add_exporter_failure_reports_stderr(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", "docker not found"))
    rc = tool.add_exporter(_Args(type="node"))
    assert rc == 1
    assert "Failed to start exporter: docker not found" in capsys.readouterr().out


def test_add_exporter_type_none_defaults_to_node(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=300):
        captured["cmd"] = cmd
        return 0, "", ""

    monkeypatch.setattr(tool, "run_command", fake_run)
    rc = tool.add_exporter(_Args(type=None))
    assert rc == 0
    assert "node_exporter" in captured["cmd"]


def test_query_metrics_success_prints_output(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=15: (0, '{"status":"success"}', ""))
    rc = tool.query_metrics(_Args(url=None, query="up", range=False))
    assert rc == 0
    assert '"status":"success"' in capsys.readouterr().out


def test_query_metrics_empty_output_is_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=15: (0, "   ", ""))
    rc = tool.query_metrics(_Args(url="http://localhost:9090", query="up", range=False))
    assert rc == 1
    assert "Query failed" in capsys.readouterr().out


def test_query_metrics_nonzero_exit_reports_stderr(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=15: (1, "", "connection refused"))
    rc = tool.query_metrics(_Args(url="http://localhost:9090", query="up", range=False))
    assert rc == 1
    assert "connection refused" in capsys.readouterr().out


def test_query_metrics_no_response_message_when_stderr_empty(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=15: (1, "", ""))
    rc = tool.query_metrics(_Args(url="http://localhost:9090", query="up", range=False))
    assert rc == 1
    assert "no response" in capsys.readouterr().out


def test_query_metrics_range_flag_uses_query_range_endpoint(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=15):
        captured["cmd"] = cmd
        return 0, "data", ""

    monkeypatch.setattr(tool, "run_command", fake_run)
    tool.query_metrics(_Args(url="http://localhost:9090", query="up", range=True))
    assert "query_range" in captured["cmd"]


def test_run_tests_all_six_checks_pass(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/prometheus")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: "/etc/prometheus/prometheus.yml")

    def fake_run(cmd, timeout=300):
        if "targets" in cmd:
            return 0, "200", ""
        return 0, "", ""

    monkeypatch.setattr(tool, "run_command", fake_run)
    rc = tool.run_tests(_Args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "Passed: 6/6" in out
    # every individual check line must be marked as a pass (checkmark), never a
    # failure marker -- guards the status == "pass" branch in the per-line printer
    assert out.count("\u2713") == 6
    assert "\u2717" not in out


def test_run_tests_targets_api_fails_on_wrong_http_code(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/prometheus")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: "/etc/prometheus/prometheus.yml")

    def fake_run(cmd, timeout=300):
        if "targets" in cmd:
            return 0, "500", ""
        return 0, "", ""

    monkeypatch.setattr(tool, "run_command", fake_run)
    rc = tool.run_tests(_Args())
    assert rc == 1
    out = capsys.readouterr().out
    # exactly one of the six checks (targets_api) is marked failed, and the
    # summary's diagnose() call must actually fire and print its remediation --
    # guards both the `passed < len(checks)` gate and the per-line status marking
    assert out.count("\u2713") == 5
    assert out.count("\u2717") == 1
    assert "Targets API call failed" in out


def test_troubleshoot_no_issues(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/prometheus")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: "/etc/prometheus/prometheus.yml")
    rc = tool.troubleshoot(_Args())
    assert rc == 0
    assert "No issues detected" in capsys.readouterr().out


def test_troubleshoot_reports_issues(monkeypatch, capsys):
    monkeypatch.setattr(tool.shutil, "which", lambda name: None)
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: None)
    rc = tool.troubleshoot(_Args())
    assert rc == 1
    assert "binary not found" in capsys.readouterr().out.lower()


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_rejects_invalid_method_choice(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "install", "--method", "bogus"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_rejects_invalid_exporter_type_choice(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "add-exporter", "--type", "bogus"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_dispatches_check_prerequisites(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-prerequisites"])
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/prometheus")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: "/etc/prometheus/prometheus.yml")
    rc = tool.main()
    assert rc == 0
    assert "All prerequisites met" in capsys.readouterr().out


def test_main_install_end_to_end(monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "", ""))
    monkeypatch.setattr(sys, "argv", ["tool.py", "install", "--method", "docker"])
    rc = tool.main()
    assert rc == 0


def test_main_configure_scrape_end_to_end(monkeypatch, tmp_path):
    out_file = tmp_path / "out.yml"
    monkeypatch.setattr(sys, "argv", ["tool.py", "configure-scrape", "--job-name", "svc", "--output", str(out_file)])
    rc = tool.main()
    assert rc == 0
    assert "job_name: svc" in out_file.read_text()


def test_main_add_exporter_end_to_end(monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    monkeypatch.setattr(sys, "argv", ["tool.py", "add-exporter", "--type", "pushgateway"])
    rc = tool.main()
    assert rc == 0


def test_main_query_metrics_end_to_end(monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=15: (0, "data", ""))
    monkeypatch.setattr(sys, "argv", ["tool.py", "query-metrics", "--query", "up"])
    rc = tool.main()
    assert rc == 0


def test_main_test_command_end_to_end(monkeypatch):
    monkeypatch.setattr(tool.shutil, "which", lambda name: None)
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: None)
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", ""))
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 1


def test_main_troubleshoot_end_to_end(monkeypatch):
    monkeypatch.setattr(tool.shutil, "which", lambda name: "/usr/bin/prometheus")
    monkeypatch.setattr(tool, "find_first_existing", lambda paths: "/etc/prometheus/prometheus.yml")
    monkeypatch.setattr(sys, "argv", ["tool.py", "troubleshoot"])
    rc = tool.main()
    assert rc == 0


def test_script_runs_as_main_via_subprocess():
    script = str(Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
    result = _subprocess.run(
        [sys.executable, script, "check-prerequisites"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode in (0, 1)
    assert "Prerequisites" in result.stdout


def test_run_command_real_success_returns_stdout():
    code, out, err = tool.run_command("echo hello")
    assert code == 0
    assert out.strip() == "hello"


def test_run_command_real_timeout_expired():
    code, out, err = tool.run_command("sleep 2", timeout=0.05)
    assert code == 1
    assert "Timeout after" in err


def test_run_command_real_exception_path():
    # shell=True requires a string command; passing None makes subprocess.run
    # raise a TypeError, which run_command's generic except must catch.
    code, out, err = tool.run_command(None)
    assert code == 1
    assert err  # exception message captured, not raised


def test_find_first_existing_returns_none_when_nothing_exists(tmp_path):
    missing_a = tmp_path / "missing_a.yml"
    missing_b = tmp_path / "missing_b.yml"
    assert tool.find_first_existing([str(missing_a), str(missing_b)]) is None


def test_dict_to_yaml_empty_list_produces_no_item_lines():
    yaml_text = tool.dict_to_yaml({"empty_list_key": []})
    assert "empty_list_key:" in yaml_text
    assert "-" not in yaml_text.split("empty_list_key:")[1]


def test_install_native_success_does_not_print_docker_url(monkeypatch, capsys):
    monkeypatch.setattr(tool, "detect_os", lambda: "linux")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=600: (0, "ok", ""))
    rc = tool.install(_Args(method="native"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "installed/started" in out
    assert "Default URL" not in out


def test_dict_to_yaml_scalar_input_returns_empty_string():
    """dict_to_yaml is only ever called on dict/list nodes in this tool's
    real call paths, but as a standalone exported helper it should not
    crash on an unexpected scalar leaf -- it degrades to an empty string
    rather than raising."""
    assert tool.dict_to_yaml(42) == ""
    assert tool.dict_to_yaml("just a string") == ""


def test_build_query_url_default_instant_is_true():
    url = tool.build_query_url("http://localhost:9090", "up")
    assert "/api/v1/query?" in url
    assert "query_range" not in url


def test_main_query_metrics_without_explicit_query_uses_default(monkeypatch):
    captured = {}

    def fake_run(cmd, timeout=15):
        captured["cmd"] = cmd
        return 0, "data", ""

    monkeypatch.setattr(tool, "run_command", fake_run)
    monkeypatch.setattr(sys, "argv", ["tool.py", "query-metrics"])
    rc = tool.main()
    assert rc == 0
    assert "query=up" in captured["cmd"]
