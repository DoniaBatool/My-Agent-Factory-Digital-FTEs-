import builtins
import importlib.util as _ilu
import os
import runpy
import socket as _socket_mod
import subprocess as _subprocess_mod
import sys as _sys
import platform as _platform_mod
from pathlib import Path

import pytest

_TOOL_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"

_spec = _ilu.spec_from_file_location("homelab_setup_tool", _TOOL_PATH)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


@pytest.fixture(autouse=True)
def _restore_cwd():
    """Several functions under test (install_docker_compose, troubleshoot) call
    os.chdir() with no restore. Keep that side effect from leaking between tests."""
    cwd = os.getcwd()
    yield
    os.chdir(cwd)


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """install_docker_compose calls time.sleep(5); never actually wait in tests."""
    monkeypatch.setattr(tool.time, "sleep", lambda *_a, **_kw: None)


def _rules_runner(rules, default=(1, "", "")):
    """Build a run_command stand-in. `rules` is a list of
    (predicate(cmd) -> bool, response) pairs checked in order."""
    def _runner(cmd, check=True, capture=False):
        for pred, resp in rules:
            if pred(cmd):
                return resp
        return default
    return _runner


def _starts_with(*prefix):
    prefix = list(prefix)
    return lambda cmd: list(cmd[:len(prefix)]) == prefix


# ---------------------------------------------------------------------------
# print_* helpers - genuine content assertions (symbols + message pass-through)
# ---------------------------------------------------------------------------

def test_print_header_includes_arrow_and_message(capsys):
    tool.print_header("Section Title")
    out = capsys.readouterr().out
    assert "==>" in out
    assert "Section Title" in out


def test_print_success_uses_check_symbol(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "✓" in out
    assert "all good" in out


def test_print_warning_uses_warning_symbol(capsys):
    tool.print_warning("careful")
    out = capsys.readouterr().out
    assert "⚠" in out
    assert "careful" in out


def test_print_error_uses_cross_symbol(capsys):
    tool.print_error("bad thing")
    out = capsys.readouterr().out
    assert "✗" in out
    assert "bad thing" in out


def test_print_info_uses_arrow_symbol(capsys):
    tool.print_info("fyi")
    out = capsys.readouterr().out
    assert "→" in out
    assert "fyi" in out


# ---------------------------------------------------------------------------
# run_command - real subprocess exercised directly, every branch
# ---------------------------------------------------------------------------

def test_run_command_capture_success_returns_stdout():
    code, out, err = tool.run_command(["python3", "-c", "print('hello')"], capture=True)
    assert code == 0
    assert out.strip() == "hello"
    assert err == ""


def test_run_command_capture_check_false_nonzero_returns_code():
    code, out, err = tool.run_command(
        ["python3", "-c", "import sys; sys.exit(3)"], check=False, capture=True
    )
    assert code == 3
    assert out == ""
    assert err == ""


def test_run_command_capture_check_true_raises_is_caught():
    code, out, err = tool.run_command(
        ["python3", "-c", "import sys; print('o'); sys.stderr.write('e'); sys.exit(5)"],
        capture=True,
    )
    assert code == 5
    assert out.strip() == "o"
    assert err == "e"


def test_run_command_no_capture_check_false_returns_empty_strings():
    code, out, err = tool.run_command(
        ["python3", "-c", "import sys; sys.exit(0)"], check=False, capture=False
    )
    assert code == 0
    assert out == ""
    assert err == ""


def test_run_command_no_capture_checked_raises_is_caught_returns_code():
    code, out, err = tool.run_command(
        ["python3", "-c", "import sys; sys.exit(4)"], check=True, capture=False
    )
    assert code == 4
    assert out == ""
    assert err == ""


def test_run_command_file_not_found_returns_1_and_message(capsys):
    code, out, err = tool.run_command(
        ["definitely_not_a_real_binary_xyz_123"], check=False, capture=True
    )
    assert code == 1
    assert out == ""
    assert "Command not found: definitely_not_a_real_binary_xyz_123" in err
    printed = capsys.readouterr().out
    assert "✗" in printed


# ---------------------------------------------------------------------------
# check_prerequisites - every branch, run_command mocked so nothing real runs
# ---------------------------------------------------------------------------

def _prereq_rules(docker=True, compose_which=True, compose_fallback=True,
                  curl=True, wget=True, systemd=True, network=True,
                  df_ok=True):
    docker_version = (0, "Docker version 24.0.0", "") if docker else (1, "", "")
    rules = [
        (_starts_with("which", "docker"), (0, "/usr/bin/docker", "") if docker else (1, "", "")),
        (_starts_with("docker", "--version"), docker_version),
        (_starts_with("which", "docker-compose"),
         (0, "/usr/bin/docker-compose", "") if compose_which else (1, "", "")),
        (_starts_with("docker", "compose", "version"),
         (0, "Docker Compose 2.0", "") if compose_fallback else (1, "", "")),
        (_starts_with("which", "curl"), (0, "/usr/bin/curl", "") if curl else (1, "", "")),
        (_starts_with("which", "wget"), (0, "/usr/bin/wget", "") if wget else (1, "", "")),
        (_starts_with("which", "systemctl"), (0, "/usr/bin/systemctl", "") if systemd else (1, "", "")),
        (_starts_with("df", "-h", "."),
         (0, "Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 53% /", "")
         if df_ok else (1, "", "")),
        (_starts_with("ping", "-c", "1", "docs.pangolin.net"), (0, "", "") if network else (1, "", "")),
    ]
    return rules


def test_check_prerequisites_all_present_linux(monkeypatch):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(tool, "run_command", _rules_runner(_prereq_rules()))
    checks = tool.check_prerequisites()
    assert checks["os_supported"] is True
    assert checks["docker"] is True
    assert checks["docker_compose"] is True
    assert checks["curl"] is True
    assert checks["systemd"] is True
    assert checks["network"] is True


def test_check_prerequisites_unsupported_os(monkeypatch, capsys):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Windows")
    monkeypatch.setattr(tool, "run_command", _rules_runner(_prereq_rules()))
    checks = tool.check_prerequisites()
    assert checks["os_supported"] is False
    assert "systemd" not in checks  # only checked when os_type == 'Linux'
    assert "not supported" in capsys.readouterr().out.lower()


def test_check_prerequisites_darwin_skips_systemd_check(monkeypatch):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Darwin")
    monkeypatch.setattr(tool, "run_command", _rules_runner(_prereq_rules()))
    checks = tool.check_prerequisites()
    assert checks["os_supported"] is True
    assert "systemd" not in checks


def test_check_prerequisites_docker_missing_is_warning(monkeypatch, capsys):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(tool, "run_command", _rules_runner(_prereq_rules(docker=False)))
    checks = tool.check_prerequisites()
    assert checks["docker"] is False
    assert "Docker not found" in capsys.readouterr().out


def test_check_prerequisites_compose_missing_falls_back_to_plugin(monkeypatch):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_prereq_rules(compose_which=False, compose_fallback=True)),
    )
    checks = tool.check_prerequisites()
    assert checks["docker_compose"] is True


def test_check_prerequisites_compose_missing_entirely(monkeypatch):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_prereq_rules(compose_which=False, compose_fallback=False)),
    )
    checks = tool.check_prerequisites()
    assert checks["docker_compose"] is False


def test_check_prerequisites_curl_missing_wget_present(monkeypatch):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(
        tool, "run_command", _rules_runner(_prereq_rules(curl=False, wget=True))
    )
    checks = tool.check_prerequisites()
    assert checks["curl"] is False
    assert checks["wget"] is True


def test_check_prerequisites_curl_and_wget_both_missing(monkeypatch, capsys):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(
        tool, "run_command", _rules_runner(_prereq_rules(curl=False, wget=False))
    )
    checks = tool.check_prerequisites()
    assert checks["curl"] is False
    assert checks["wget"] is False
    assert "Neither curl nor wget" in capsys.readouterr().out


def test_check_prerequisites_systemd_missing_on_linux(monkeypatch):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(tool, "run_command", _rules_runner(_prereq_rules(systemd=False)))
    checks = tool.check_prerequisites()
    assert checks["systemd"] is False


def test_check_prerequisites_network_unreachable(monkeypatch, capsys):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(tool, "run_command", _rules_runner(_prereq_rules(network=False)))
    checks = tool.check_prerequisites()
    assert checks["network"] is False
    assert "Cannot reach docs.pangolin.net" in capsys.readouterr().out


def test_check_prerequisites_disk_space_line_printed(monkeypatch, capsys):
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(tool, "run_command", _rules_runner(_prereq_rules(df_ok=True)))
    tool.check_prerequisites()
    assert "Available disk space: 45G" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# install_pangolin_server - orchestrator; sub-installers mocked
# ---------------------------------------------------------------------------

def _setup_args(**overrides):
    base = dict(
        method="auto", install_dir="~/pangolin", domain="pangolin.local",
        admin_email="admin@pangolin.local", port=443, admin_port=8080,
        image="pangolin/server:latest",
    )
    base.update(overrides)
    return _Args(**base)


def test_install_pangolin_server_unsupported_os_exits_1(monkeypatch):
    monkeypatch.setattr(tool, "check_prerequisites", lambda: {"os_supported": False})
    with pytest.raises(SystemExit) as excinfo:
        tool.install_pangolin_server(_setup_args())
    assert excinfo.value.code == 1


def test_install_pangolin_server_no_curl_or_wget_exits_1(monkeypatch):
    monkeypatch.setattr(
        tool, "check_prerequisites",
        lambda: {"os_supported": True, "curl": False, "wget": False, "docker": True},
    )
    with pytest.raises(SystemExit) as excinfo:
        tool.install_pangolin_server(_setup_args())
    assert excinfo.value.code == 1


def test_install_pangolin_server_docker_method_without_docker_exits_1(monkeypatch):
    monkeypatch.setattr(
        tool, "check_prerequisites",
        lambda: {"os_supported": True, "curl": True, "docker": False},
    )
    with pytest.raises(SystemExit) as excinfo:
        tool.install_pangolin_server(_setup_args(method="docker"))
    assert excinfo.value.code == 1


def test_install_pangolin_server_auto_with_docker_calls_docker_installer(monkeypatch):
    monkeypatch.setattr(
        tool, "check_prerequisites",
        lambda: {"os_supported": True, "curl": True, "docker": True},
    )
    called = {}
    monkeypatch.setattr(tool, "install_docker_compose", lambda a: called.setdefault("docker", a))
    monkeypatch.setattr(tool, "install_binary", lambda a: called.setdefault("binary", a))
    tool.install_pangolin_server(_setup_args(method="auto"))
    assert "docker" in called
    assert "binary" not in called


def test_install_pangolin_server_auto_without_docker_calls_binary_installer(monkeypatch):
    monkeypatch.setattr(
        tool, "check_prerequisites",
        lambda: {"os_supported": True, "curl": True, "docker": False},
    )
    called = {}
    monkeypatch.setattr(tool, "install_docker_compose", lambda a: called.setdefault("docker", a))
    monkeypatch.setattr(tool, "install_binary", lambda a: called.setdefault("binary", a))
    tool.install_pangolin_server(_setup_args(method="auto"))
    assert "binary" in called
    assert "docker" not in called


def test_install_pangolin_server_explicit_binary_method(monkeypatch):
    monkeypatch.setattr(
        tool, "check_prerequisites",
        lambda: {"os_supported": True, "curl": True, "docker": False},
    )
    called = {}
    monkeypatch.setattr(tool, "install_binary", lambda a: called.setdefault("binary", a))
    tool.install_pangolin_server(_setup_args(method="binary"))
    assert "binary" in called


def test_install_pangolin_server_unknown_method_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(
        tool, "check_prerequisites",
        lambda: {"os_supported": True, "curl": True, "docker": True},
    )
    with pytest.raises(SystemExit) as excinfo:
        tool.install_pangolin_server(_setup_args(method="bogus"))
    assert excinfo.value.code == 1
    assert "Unknown installation method" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# install_docker_compose - real file writes into tmp_path, run_command mocked
# ---------------------------------------------------------------------------

def test_install_docker_compose_success_writes_files(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    args = _setup_args(install_dir=str(install_dir))
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([
            (_starts_with("docker", "pull"), (0, "", "")),
            (_starts_with("docker-compose", "up", "-d"), (0, "", "")),
        ]),
    )
    tool.install_docker_compose(args)

    compose_content = (install_dir / "docker-compose.yml").read_text()
    assert "pangolin/server:latest" in compose_content
    assert '"443:443"' in compose_content
    assert '"8080:8080"' in compose_content
    assert "PANGOLIN_DOMAIN=pangolin.local" in compose_content
    assert "PANGOLIN_ADMIN_EMAIL=admin@pangolin.local" in compose_content

    config_content = (install_dir / "config" / "config.yml").read_text()
    assert "domain: pangolin.local" in config_content
    assert "email: admin@pangolin.local" in config_content

    assert (install_dir / "data").is_dir()
    assert (install_dir / "config").is_dir()
    out = capsys.readouterr().out
    assert "Pangolin services started successfully!" in out


def test_install_docker_compose_pull_failure_exits_1(tmp_path, monkeypatch):
    args = _setup_args(install_dir=str(tmp_path / "pangolin"))
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([(_starts_with("docker", "pull"), (1, "", ""))]),
    )
    with pytest.raises(SystemExit) as excinfo:
        tool.install_docker_compose(args)
    assert excinfo.value.code == 1


def test_install_docker_compose_falls_back_to_docker_compose_plugin(tmp_path, monkeypatch):
    args = _setup_args(install_dir=str(tmp_path / "pangolin"))
    calls = []

    def _runner(cmd, check=True, capture=False):
        calls.append(cmd)
        if cmd[:2] == ["docker", "pull"]:
            return (0, "", "")
        if cmd[:3] == ["docker-compose", "up", "-d"]:
            return (1, "", "")
        if cmd[:3] == ["docker", "compose", "up"]:
            return (0, "", "")
        return (1, "", "")

    monkeypatch.setattr(tool, "run_command", _runner)
    tool.install_docker_compose(args)
    assert ["docker", "compose", "up", "-d"] in calls


def test_install_docker_compose_both_start_attempts_fail_exits_1(tmp_path, monkeypatch):
    args = _setup_args(install_dir=str(tmp_path / "pangolin"))
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([(_starts_with("docker", "pull"), (0, "", ""))], default=(1, "", "")),
    )
    with pytest.raises(SystemExit) as excinfo:
        tool.install_docker_compose(args)
    assert excinfo.value.code == 1


# ---------------------------------------------------------------------------
# install_binary - Path.exists() patched for the hardcoded curl/wget probes
# ---------------------------------------------------------------------------

_REAL_PATH_EXISTS = Path.exists


def _fake_exists_factory(curl_present):
    def _fake(self):
        s = str(self)
        if s in ("/usr/bin/curl", "/usr/local/bin/curl"):
            return curl_present
        return _REAL_PATH_EXISTS(self)
    return _fake


def _download_writing_runner(returncode=0):
    def _runner(cmd, check=True, capture=False):
        if "-o" in cmd:
            out_path = cmd[cmd.index("-o") + 1]
        elif "-O" in cmd:
            out_path = cmd[cmd.index("-O") + 1]
        else:
            return (returncode, "", "")
        if returncode == 0:
            Path(out_path).write_bytes(b"fake-binary")
        return (returncode, "", "")
    return _runner


def test_install_binary_curl_present_success_linux_creates_systemd(tmp_path, monkeypatch):
    args = _setup_args(install_dir=str(tmp_path / "pangolin"))
    monkeypatch.setattr(tool.Path, "exists", _fake_exists_factory(curl_present=True))
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(_platform_mod, "machine", lambda: "x86_64")
    monkeypatch.setattr(tool, "run_command", _download_writing_runner(0))
    called = {}
    monkeypatch.setattr(
        tool, "create_systemd_service",
        lambda binary_path, a: called.setdefault("binary_path", binary_path),
    )
    tool.install_binary(args)
    assert called["binary_path"] == tmp_path / "pangolin" / "pangolin-server"
    assert (tmp_path / "pangolin" / "pangolin-server").exists()


def test_install_binary_wget_used_when_curl_absent(tmp_path, monkeypatch):
    args = _setup_args(install_dir=str(tmp_path / "pangolin"))
    monkeypatch.setattr(tool.Path, "exists", _fake_exists_factory(curl_present=False))
    monkeypatch.setattr(_platform_mod, "system", lambda: "Darwin")
    monkeypatch.setattr(_platform_mod, "machine", lambda: "arm64")
    seen = {}

    def _runner(cmd, check=True, capture=False):
        seen["cmd"] = cmd
        out_path = cmd[cmd.index("-O") + 1]
        Path(out_path).write_bytes(b"fake-binary")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", _runner)
    tool.install_binary(args)
    assert seen["cmd"][0] == "wget"
    assert (tmp_path / "pangolin" / "pangolin-server").exists()


def test_install_binary_darwin_does_not_create_systemd_service(tmp_path, monkeypatch):
    args = _setup_args(install_dir=str(tmp_path / "pangolin"))
    monkeypatch.setattr(tool.Path, "exists", _fake_exists_factory(curl_present=True))
    monkeypatch.setattr(_platform_mod, "system", lambda: "Darwin")
    monkeypatch.setattr(_platform_mod, "machine", lambda: "arm64")
    monkeypatch.setattr(tool, "run_command", _download_writing_runner(0))
    called = {}
    monkeypatch.setattr(
        tool, "create_systemd_service",
        lambda binary_path, a: called.setdefault("called", True),
    )
    tool.install_binary(args)
    assert "called" not in called


def test_install_binary_download_failure_exits_1(tmp_path, monkeypatch, capsys):
    args = _setup_args(install_dir=str(tmp_path / "pangolin"))
    monkeypatch.setattr(tool.Path, "exists", _fake_exists_factory(curl_present=True))
    monkeypatch.setattr(_platform_mod, "system", lambda: "Linux")
    monkeypatch.setattr(_platform_mod, "machine", lambda: "x86_64")
    monkeypatch.setattr(tool, "run_command", _download_writing_runner(1))
    with pytest.raises(SystemExit) as excinfo:
        tool.install_binary(args)
    assert excinfo.value.code == 1
    assert "Failed to download binary" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# create_systemd_service
# ---------------------------------------------------------------------------

def test_create_systemd_service_success_runs_reload_and_enable(tmp_path, monkeypatch, capsys):
    args = _setup_args()
    calls = []

    def _runner(cmd, check=True, capture=False):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", _runner)
    tool.create_systemd_service(tmp_path / "pangolin-server", args)
    assert ["sudo", "tee", "/etc/systemd/system/pangolin.service"] == calls[0]
    assert ["sudo", "systemctl", "daemon-reload"] in calls
    assert ["sudo", "systemctl", "enable", "pangolin"] in calls
    assert "Systemd service created and enabled" in capsys.readouterr().out


def test_create_systemd_service_tee_failure_skips_reload(tmp_path, monkeypatch, capsys):
    args = _setup_args()
    calls = []

    def _runner(cmd, check=True, capture=False):
        calls.append(cmd)
        return (1, "", "")

    monkeypatch.setattr(tool, "run_command", _runner)
    tool.create_systemd_service(tmp_path / "pangolin-server", args)
    assert len(calls) == 1  # only the tee call, reload/enable never ran
    assert "Failed to create systemd service" in capsys.readouterr().out


def test_create_systemd_service_exception_is_caught(tmp_path, monkeypatch, capsys):
    args = _setup_args()

    def _raiser(cmd, check=True, capture=False):
        raise OSError("no sudo")

    monkeypatch.setattr(tool, "run_command", _raiser)
    tool.create_systemd_service(tmp_path / "pangolin-server", args)
    assert "Could not create systemd service: no sudo" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# deploy_remote_node
# ---------------------------------------------------------------------------

def _node_args(**overrides):
    base = dict(server_url="https://pangolin.local", node_name="home-node", auth_token=None)
    base.update(overrides)
    return _Args(**base)


def test_deploy_remote_node_download_failure_exits_1(monkeypatch):
    monkeypatch.setattr(
        tool, "run_command",
        lambda *a, **kw: (1, "", "download failed"),
    )
    called = {}
    monkeypatch.setattr(tool.subprocess, "call", lambda *a, **kw: called.setdefault("hit", True))
    with pytest.raises(SystemExit) as excinfo:
        tool.deploy_remote_node(_node_args())
    assert excinfo.value.code == 1
    assert "hit" not in called


def test_deploy_remote_node_success_sets_env_and_reports_success(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(tool, "run_command", lambda *a, **kw: (0, "#!/bin/sh\necho hi\n", ""))
    captured_env = {}

    def _fake_call(cmd, env=None):
        captured_env.update(env or {})
        return 0

    monkeypatch.setattr(tool.subprocess, "call", _fake_call)
    try:
        tool.deploy_remote_node(_node_args(auth_token="tok-123"))
    finally:
        installer = Path("/tmp/pangolin-node-installer.sh")
        if installer.exists():
            installer.unlink()
    assert captured_env["PANGOLIN_SERVER_URL"] == "https://pangolin.local"
    assert captured_env["PANGOLIN_NODE_NAME"] == "home-node"
    assert captured_env["PANGOLIN_AUTH_TOKEN"] == "tok-123"
    assert "Remote node deployed successfully!" in capsys.readouterr().out


def test_deploy_remote_node_no_auth_token_omits_env_var(monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda *a, **kw: (0, "#!/bin/sh\n", ""))
    captured_env = {}

    def _fake_call(cmd, env=None):
        captured_env.update(env or {})
        return 0

    monkeypatch.setattr(tool.subprocess, "call", _fake_call)
    try:
        tool.deploy_remote_node(_node_args(auth_token=None))
    finally:
        installer = Path("/tmp/pangolin-node-installer.sh")
        if installer.exists():
            installer.unlink()
    assert "PANGOLIN_AUTH_TOKEN" not in captured_env


def test_deploy_remote_node_installer_failure_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda *a, **kw: (0, "#!/bin/sh\n", ""))
    monkeypatch.setattr(tool.subprocess, "call", lambda *a, **kw: 1)
    try:
        with pytest.raises(SystemExit) as excinfo:
            tool.deploy_remote_node(_node_args())
    finally:
        installer = Path("/tmp/pangolin-node-installer.sh")
        if installer.exists():
            installer.unlink()
    assert excinfo.value.code == 1
    assert "Deployment failed" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# verify_installation
# ---------------------------------------------------------------------------

def _verify_args(install_dir):
    return _Args(install_dir=str(install_dir))


def test_verify_installation_no_install_dir_service_ok_returns_0(tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "run_command", _rules_runner([(_starts_with("curl"), (0, "200", ""))]))
    rc = tool.verify_installation(_verify_args(tmp_path / "missing"))
    assert rc == 0


def test_verify_installation_not_docker_install_returns_0(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    monkeypatch.setattr(tool, "run_command", _rules_runner([(_starts_with("curl"), (0, "200", ""))]))
    rc = tool.verify_installation(_verify_args(install_dir))
    assert rc == 0
    assert "Not a Docker installation" in capsys.readouterr().out


def test_verify_installation_containers_up_and_service_ok_returns_0(tmp_path, monkeypatch):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "docker-compose.yml").write_text("services: {}")
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([
            (_starts_with("docker-compose", "ps"), (0, "pangolin-server   Up 5 minutes", "")),
            (_starts_with("curl"), (0, "200", "")),
        ]),
    )
    rc = tool.verify_installation(_verify_args(install_dir))
    assert rc == 0


def test_verify_installation_compose_ps_fallback_to_plugin(tmp_path, monkeypatch):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "docker-compose.yml").write_text("services: {}")
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([
            (_starts_with("docker-compose", "ps"), (1, "", "")),
            (_starts_with("docker", "compose", "ps"), (0, "pangolin-server   running", "")),
            (_starts_with("curl"), (0, "200", "")),
        ]),
    )
    rc = tool.verify_installation(_verify_args(install_dir))
    assert rc == 0


def test_verify_installation_containers_not_running_returns_1(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "docker-compose.yml").write_text("services: {}")
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([
            (_starts_with("docker-compose", "ps"), (0, "pangolin-server   Exited (1)", "")),
            (_starts_with("curl"), (0, "200", "")),
        ]),
    )
    rc = tool.verify_installation(_verify_args(install_dir))
    assert rc == 1
    assert "Docker containers not running" in capsys.readouterr().out


def test_verify_installation_cannot_check_container_status(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "docker-compose.yml").write_text("services: {}")
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([
            (_starts_with("docker-compose", "ps"), (1, "", "")),
            (_starts_with("docker", "compose", "ps"), (1, "", "")),
            (_starts_with("curl"), (0, "200", "")),
        ]),
    )
    rc = tool.verify_installation(_verify_args(install_dir))
    assert rc == 1
    assert "Could not check container status" in capsys.readouterr().out


def test_verify_installation_service_not_responding_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _rules_runner([(_starts_with("curl"), (1, "", ""))]))
    rc = tool.verify_installation(_verify_args(tmp_path / "missing"))
    assert rc == 1
    assert "Service not responding on localhost" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------

def _health_args(install_dir):
    return _Args(install_dir=str(install_dir))


def _health_rules(container_line=None, endpoints_ok=True, df_line=None, meminfo=None):
    rules = []
    if container_line is not None:
        rules.append((_starts_with("docker", "ps", "--filter", "name=pangolin"),
                       (0, container_line, "")))
    else:
        rules.append((_starts_with("docker", "ps", "--filter", "name=pangolin"), (0, "", "")))
    code = "200" if endpoints_ok else "500"
    rules.append((_starts_with("curl"), (0, code, "")))
    if df_line is not None:
        rules.append((_starts_with("df", "-h"), (0, df_line, "")))
    return rules


def _no_meminfo(monkeypatch):
    def _fake(self):
        if str(self) == "/proc/meminfo":
            return False
        return _REAL_PATH_EXISTS(self)
    monkeypatch.setattr(tool.Path, "exists", _fake)


def _with_meminfo(monkeypatch, mem_available_kb):
    def _fake(self):
        if str(self) == "/proc/meminfo":
            return True
        return _REAL_PATH_EXISTS(self)
    monkeypatch.setattr(tool.Path, "exists", _fake)

    real_open = builtins.open
    content = f"MemTotal:       16000000 kB\nMemAvailable:   {mem_available_kb} kB\n"

    def _fake_open(path, *a, **kw):
        if str(path) == "/proc/meminfo":
            import io
            return io.StringIO(content)
        return real_open(path, *a, **kw)

    monkeypatch.setattr(builtins, "open", _fake_open)


def test_health_check_no_install_dir_healthy_returns_0(tmp_path, monkeypatch):
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 50% /")),
    )
    rc = tool.health_check(_health_args(tmp_path / "missing"))
    assert rc == 0


def test_health_check_container_running_and_healthy(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "config").mkdir()
    (install_dir / "config" / "config.yml").write_text("server: {}")
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            container_line="pangolin-server\tUp 5 minutes",
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 50% /",
        )),
    )
    rc = tool.health_check(_health_args(install_dir))
    assert rc == 0
    assert "Config file found" in capsys.readouterr().out


def test_health_check_container_down_is_unhealthy(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            container_line="pangolin-server\tExited (1) 2 minutes ago",
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 50% /",
        )),
    )
    rc = tool.health_check(_health_args(install_dir))
    assert rc == 1
    assert "Some services not running properly" in capsys.readouterr().out


def test_health_check_no_containers_found_prints_info(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 50% /",
        )),
    )
    tool.health_check(_health_args(install_dir))
    assert "No Docker containers found" in capsys.readouterr().out


def test_health_check_connectivity_bad_status_is_unhealthy(tmp_path, monkeypatch, capsys):
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            endpoints_ok=False,
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 50% /",
        )),
    )
    rc = tool.health_check(_health_args(tmp_path / "missing"))
    assert rc == 1
    assert "Some endpoints not accessible" in capsys.readouterr().out


def test_health_check_connection_failed_prints_error(tmp_path, monkeypatch, capsys):
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([
            (_starts_with("docker", "ps"), (0, "", "")),
            (_starts_with("curl"), (1, "", "")),
        ]),
    )
    rc = tool.health_check(_health_args(tmp_path / "missing"))
    assert rc == 1
    assert "Connection failed" in capsys.readouterr().out


def test_health_check_high_disk_usage_is_unhealthy(tmp_path, monkeypatch, capsys):
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 95G 5G 95% /",
        )),
    )
    rc = tool.health_check(_health_args(tmp_path / "missing"))
    assert rc == 1
    assert "Disk space running low" in capsys.readouterr().out


def test_health_check_disk_between_80_and_90_warns_but_stays_healthy(tmp_path, monkeypatch, capsys):
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 85G 15G 85% /",
        )),
    )
    rc = tool.health_check(_health_args(tmp_path / "missing"))
    out = capsys.readouterr().out
    assert "85% used" in out
    assert rc == 0  # disk_ok threshold is <90, print threshold is <80 - different!


def test_health_check_memory_high_prints_success(tmp_path, monkeypatch, capsys):
    _with_meminfo(monkeypatch, mem_available_kb=4 * 1024 * 1024)  # 4 GB
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 50% /",
        )),
    )
    tool.health_check(_health_args(tmp_path / "missing"))
    assert "Memory: 4.0 GB available" in capsys.readouterr().out


def test_health_check_memory_low_prints_warning(tmp_path, monkeypatch, capsys):
    _with_meminfo(monkeypatch, mem_available_kb=512 * 1024)  # 0.5 GB
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 50% /",
        )),
    )
    tool.health_check(_health_args(tmp_path / "missing"))
    assert "Memory: 0.5 GB available (low)" in capsys.readouterr().out


def test_health_check_config_missing_warns(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    _no_meminfo(monkeypatch)
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner(_health_rules(
            df_line="Filesystem Size Used Avail Use% Mounted\n/dev/x 100G 50G 45G 50% /",
        )),
    )
    tool.health_check(_health_args(install_dir))
    assert "Config file not found" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# test_homelab - the 'test' subcommand; sub-checks mocked, fs bits use tmp_path
# ---------------------------------------------------------------------------

def _th_args(install_dir):
    return _Args(install_dir=str(install_dir))


def _mock_all_ok(monkeypatch, curl_ok=True):
    monkeypatch.setattr(tool, "check_prerequisites", lambda: {"a": True, "b": True})
    monkeypatch.setattr(tool, "verify_installation", lambda a: 0)
    monkeypatch.setattr(tool, "health_check", lambda a: 0)
    code = "200" if curl_ok else "000"
    rc = 0 if curl_ok else 1
    monkeypatch.setattr(tool, "run_command", lambda *a, **kw: (rc, code, ""))


def _full_install(tmp_path):
    install_dir = tmp_path / "pangolin"
    (install_dir / "config").mkdir(parents=True)
    (install_dir / "config" / "config.yml").write_text("server: {}")
    (install_dir / "data").mkdir(parents=True)
    return install_dir


def test_test_homelab_all_pass_returns_0(tmp_path, monkeypatch, capsys):
    install_dir = _full_install(tmp_path)
    _mock_all_ok(monkeypatch)
    rc = tool.test_homelab(_th_args(install_dir))
    assert rc == 0
    assert "All tests passed!" in capsys.readouterr().out


def test_test_homelab_prerequisites_fail_returns_1(tmp_path, monkeypatch):
    install_dir = _full_install(tmp_path)
    _mock_all_ok(monkeypatch)
    monkeypatch.setattr(tool, "check_prerequisites", lambda: {"a": True, "b": False})
    rc = tool.test_homelab(_th_args(install_dir))
    assert rc == 1


def test_test_homelab_installation_check_fail_returns_1(tmp_path, monkeypatch):
    install_dir = _full_install(tmp_path)
    _mock_all_ok(monkeypatch)
    monkeypatch.setattr(tool, "verify_installation", lambda a: 1)
    rc = tool.test_homelab(_th_args(install_dir))
    assert rc == 1


def test_test_homelab_health_check_fail_returns_1(tmp_path, monkeypatch):
    install_dir = _full_install(tmp_path)
    _mock_all_ok(monkeypatch)
    monkeypatch.setattr(tool, "health_check", lambda a: 1)
    rc = tool.test_homelab(_th_args(install_dir))
    assert rc == 1


def test_test_homelab_service_response_fail_returns_1(tmp_path, monkeypatch, capsys):
    install_dir = _full_install(tmp_path)
    _mock_all_ok(monkeypatch, curl_ok=False)
    rc = tool.test_homelab(_th_args(install_dir))
    assert rc == 1
    assert "Failed to connect to" in capsys.readouterr().out


def test_test_homelab_configuration_missing_returns_1(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "data").mkdir()
    _mock_all_ok(monkeypatch)
    rc = tool.test_homelab(_th_args(install_dir))
    assert rc == 1
    assert "Configuration file missing" in capsys.readouterr().out


def test_test_homelab_data_dir_missing_returns_1(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    (install_dir / "config").mkdir(parents=True)
    (install_dir / "config" / "config.yml").write_text("server: {}")
    _mock_all_ok(monkeypatch)
    rc = tool.test_homelab(_th_args(install_dir))
    assert rc == 1
    assert "Data directory missing" in capsys.readouterr().out


def test_test_homelab_data_dir_not_writable_returns_1(tmp_path, monkeypatch, capsys):
    install_dir = _full_install(tmp_path)
    _mock_all_ok(monkeypatch)
    data_dir = install_dir / "data"
    os.chmod(data_dir, 0o500)
    try:
        rc = tool.test_homelab(_th_args(install_dir))
        out = capsys.readouterr().out
    finally:
        os.chmod(data_dir, 0o700)
    if rc == 0:
        pytest.skip("filesystem permits writes to a read-only dir for this user (e.g. root)")
    assert rc == 1
    assert "Data directory not writable" in out


# ---------------------------------------------------------------------------
# troubleshoot - install dir / docker-compose.yml / docker ps / ports
# ---------------------------------------------------------------------------

def _ts_args(install_dir):
    return _Args(install_dir=str(install_dir))


def _fake_connect_ex_factory(open_ports):
    def _fake(self, addr):
        _, port = addr
        return 0 if port in open_ports else 1
    return _fake


def test_troubleshoot_missing_install_dir_reports_issue(tmp_path, monkeypatch):
    monkeypatch.setattr(_socket_mod.socket, "connect_ex", _fake_connect_ex_factory({443, 8080}))
    monkeypatch.setattr(tool, "run_command", lambda *a, **kw: (0, "", ""))
    rc = tool.troubleshoot(_ts_args(tmp_path / "missing"))
    assert rc == 1


def test_troubleshoot_no_compose_file_skips_docker_section(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    monkeypatch.setattr(_socket_mod.socket, "connect_ex", _fake_connect_ex_factory({443, 8080}))
    monkeypatch.setattr(tool, "run_command", lambda *a, **kw: (0, "", ""))
    rc = tool.troubleshoot(_ts_args(install_dir))
    assert rc == 0
    assert "Docker installation detected" not in capsys.readouterr().out


def test_troubleshoot_containers_running_no_issues(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "docker-compose.yml").write_text("services: {}")
    monkeypatch.setattr(_socket_mod.socket, "connect_ex", _fake_connect_ex_factory({443, 8080}))
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([
            (_starts_with("docker", "ps"), (0, "pangolin-server\tUp 5 minutes", "")),
        ], default=(0, "", "")),
    )
    rc = tool.troubleshoot(_ts_args(install_dir))
    assert rc == 0
    assert "No issues detected!" in capsys.readouterr().out


def test_troubleshoot_no_containers_running_reports_issue(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "docker-compose.yml").write_text("services: {}")
    monkeypatch.setattr(_socket_mod.socket, "connect_ex", _fake_connect_ex_factory({443, 8080}))
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([(_starts_with("docker", "ps"), (0, "", ""))], default=(0, "", "")),
    )
    rc = tool.troubleshoot(_ts_args(install_dir))
    assert rc == 1
    assert "No Pangolin containers running" in capsys.readouterr().out


def test_troubleshoot_cannot_query_docker_reports_issue(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    (install_dir / "docker-compose.yml").write_text("services: {}")
    monkeypatch.setattr(_socket_mod.socket, "connect_ex", _fake_connect_ex_factory({443, 8080}))
    monkeypatch.setattr(
        tool, "run_command",
        _rules_runner([(_starts_with("docker", "ps"), (1, "", ""))], default=(0, "", "")),
    )
    rc = tool.troubleshoot(_ts_args(install_dir))
    assert rc == 1
    assert "Cannot query Docker containers" in capsys.readouterr().out


def test_troubleshoot_closed_port_reports_issue(tmp_path, monkeypatch, capsys):
    install_dir = tmp_path / "pangolin"
    install_dir.mkdir()
    monkeypatch.setattr(_socket_mod.socket, "connect_ex", _fake_connect_ex_factory({443}))
    monkeypatch.setattr(tool, "run_command", lambda *a, **kw: (0, "", ""))
    rc = tool.troubleshoot(_ts_args(install_dir))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Port 8080 not accessible" in out
    assert "Port 443 is open" in out


# ---------------------------------------------------------------------------
# main() - argparse wiring and dispatch
# ---------------------------------------------------------------------------

def test_main_no_command_exits_1_and_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_setup_dispatches_with_defaults(monkeypatch):
    called = {}
    monkeypatch.setattr(tool, "install_pangolin_server", lambda a: called.setdefault("args", a))
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup"])
    tool.main()  # no sys.exit for 'setup' on the normal-return path
    args = called["args"]
    assert args.method == "auto"
    assert args.install_dir == "~/pangolin"
    assert args.domain == "pangolin.local"
    assert args.admin_email == "admin@pangolin.local"
    assert args.port == 443
    assert args.admin_port == 8080
    assert args.image == "pangolin/server:latest"


def test_main_setup_dispatches_with_overrides(monkeypatch):
    called = {}
    monkeypatch.setattr(tool, "install_pangolin_server", lambda a: called.setdefault("args", a))
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "setup", "--method", "docker", "--domain", "my.lab",
        "--admin-email", "a@b.co", "--install-dir", "/opt/pangolin",
        "--port", "8443", "--admin-port", "9090", "--image", "custom:tag",
    ])
    tool.main()
    args = called["args"]
    assert args.method == "docker"
    assert args.domain == "my.lab"
    assert args.admin_email == "a@b.co"
    assert args.install_dir == "/opt/pangolin"
    assert args.port == 8443
    assert args.admin_port == 9090
    assert args.image == "custom:tag"


def test_main_deploy_node_dispatches_required_args(monkeypatch):
    called = {}
    monkeypatch.setattr(tool, "deploy_remote_node", lambda a: called.setdefault("args", a))
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "deploy-node", "--server-url", "https://x", "--node-name", "n1",
    ])
    tool.main()
    args = called["args"]
    assert args.server_url == "https://x"
    assert args.node_name == "n1"
    assert args.auth_token is None


def test_main_deploy_node_missing_required_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "deploy-node"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 2
    assert "required" in capsys.readouterr().err.lower()


def test_main_verify_dispatches_and_exits_with_return_code(monkeypatch):
    monkeypatch.setattr(tool, "verify_installation", lambda a: 7)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "verify"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 7


def test_main_test_dispatches_and_exits_with_return_code(monkeypatch):
    monkeypatch.setattr(tool, "test_homelab", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test", "--install-dir", "/tmp/x"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 0


def test_main_health_check_dispatches_and_exits_with_return_code(monkeypatch):
    monkeypatch.setattr(tool, "health_check", lambda a: 1)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "health-check"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 1


def test_main_troubleshoot_dispatches_and_exits_with_return_code(monkeypatch):
    monkeypatch.setattr(tool, "troubleshoot", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "troubleshoot", "--install-dir", "/tmp/y"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 0


def test_main_unknown_command_argparse_exits_2(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "not-a-real-command"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 2


def test_main_keyboard_interrupt_exits_130(monkeypatch, capsys):
    def _raise(a):
        raise KeyboardInterrupt()

    monkeypatch.setattr(tool, "verify_installation", _raise)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "verify"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 130
    assert "Interrupted by user" in capsys.readouterr().out


def test_main_unexpected_exception_exits_1(monkeypatch, capsys):
    def _raise(a):
        raise ValueError("boom")

    monkeypatch.setattr(tool, "health_check", _raise)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "health-check"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 1
    assert "Unexpected error: boom" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Real subprocess smoke tests of the __main__ entrypoint (nothing mocked)
# ---------------------------------------------------------------------------

def test_cli_entrypoint_no_args_exits_1():
    result = _subprocess_mod.run(
        [_sys.executable, str(_TOOL_PATH)], capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "usage" in result.stdout.lower()


def test_cli_entrypoint_unknown_command_exits_2():
    result = _subprocess_mod.run(
        [_sys.executable, str(_TOOL_PATH), "bogus-command"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
    assert "invalid choice" in result.stderr.lower()


def test_cli_entrypoint_deploy_node_missing_required_exits_2():
    result = _subprocess_mod.run(
        [_sys.executable, str(_TOOL_PATH), "deploy-node"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
    assert "--server-url" in result.stderr


def test_cli_entrypoint_verify_runs_and_exits_0_or_1(tmp_path):
    # Real end-to-end run against a directory with no Pangolin install -
    # only asserts the process behaves (valid exit code), no docker involved.
    result = _subprocess_mod.run(
        [_sys.executable, str(_TOOL_PATH), "verify", "--install-dir", str(tmp_path / "nope")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode in (0, 1)
    assert "Verifying Pangolin Installation" in result.stdout


# ---------------------------------------------------------------------------
# __main__ guard - executed in-process (via runpy) so it is coverage-visible
# ---------------------------------------------------------------------------

def test_dunder_main_guard_calls_main_and_exits_with_its_code(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(_TOOL_PATH), run_name="__main__")
    assert excinfo.value.code == 1


# ---------------------------------------------------------------------------
# main()'s final "else" dispatch branch (parser.print_help(); sys.exit(1)) is
# unreachable through real argparse: the subparsers only ever produce
# args.command in {None, 'setup', 'deploy-node', 'verify', 'test',
# 'health-check', 'troubleshoot'}, None is handled earlier, and any other
# string is rejected by argparse itself (SystemExit(2), covered by
# test_main_unknown_command_argparse_exits_2). We force it here only to
# exercise that dead branch for coverage, by forging the parsed Namespace.
# ---------------------------------------------------------------------------

def test_main_dispatch_else_branch_via_forged_namespace(monkeypatch, capsys):
    class _FakeNamespace:
        command = "no-such-real-subcommand"

    monkeypatch.setattr(tool.argparse.ArgumentParser, "parse_args", lambda self: _FakeNamespace())
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 1
    assert "usage" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# run_command - defaults (check=True, capture=False) exercised with no kwargs
# ---------------------------------------------------------------------------

def test_run_command_default_capture_false_does_not_capture_output():
    # Calling with only `cmd` relies on the real default capture=False: even
    # though the subprocess prints output, run_command must not capture it.
    code, out, err = tool.run_command(["python3", "-c", "print('leak-if-captured')"])
    assert code == 0
    assert out == ""
    assert err == ""
