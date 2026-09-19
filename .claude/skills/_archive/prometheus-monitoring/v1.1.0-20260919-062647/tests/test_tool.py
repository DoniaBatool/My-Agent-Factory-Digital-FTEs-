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
