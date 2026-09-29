import os
import subprocess
import sys
from pathlib import Path

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "digitalocean_deploy_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
INFO_FILE = ".digitalocean-droplet-info"


import pytest


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    # Several tool.py code paths call time.sleep(10) in a retry loop. A
    # mutation to the loop's exit condition (or a bug) could turn a
    # should-break-immediately path into dozens of real 10s sleeps. Every
    # test gets this defensively so a mutant can never hang the suite.
    monkeypatch.setattr(tool.time, "sleep", lambda seconds: None)


def make_fake_run_command(responses, calls=None):
    """responses: list of (substring, (code, stdout, stderr)) checked in order.
    calls: optional list that records every cmd string passed in.
    Unmatched commands raise, so a test notices when it exercises an
    unexpected code path instead of silently returning a default.
    """
    def fake(cmd, timeout=300):
        if calls is not None:
            calls.append(cmd)
        for substr, resp in responses:
            if substr in (cmd or ""):
                return resp
        raise AssertionError(f"unexpected run_command call: {cmd!r}")
    return fake


# --------------------------------------------------------------------------
# print helpers + run_command
# --------------------------------------------------------------------------

def test_print_success_prints_message(capsys):
    tool.print_success("ok")
    out = capsys.readouterr().out
    assert "ok" in out and "✓" in out


def test_print_error_prints_message(capsys):
    tool.print_error("bad")
    out = capsys.readouterr().out
    assert "bad" in out and "✗" in out


def test_print_warning_prints_message(capsys):
    tool.print_warning("careful")
    out = capsys.readouterr().out
    assert "careful" in out and "⚠" in out


def test_print_info_prints_message(capsys):
    tool.print_info("fyi")
    assert "fyi" in capsys.readouterr().out


def test_print_header_prints_arrow(capsys):
    tool.print_header("Section")
    assert "==> Section" in capsys.readouterr().out


def test_run_command_success():
    code, out, err = tool.run_command("echo hi")
    assert code == 0
    assert out.strip() == "hi"
    assert err == ""


def test_run_command_nonzero_exit():
    code, out, err = tool.run_command("exit 5")
    assert code == 5


def test_run_command_timeout_returns_1_with_message():
    code, out, err = tool.run_command("sleep 5", timeout=0.05)
    assert code == 1
    assert out == ""
    assert "timed out after 0.05s" in err


def test_run_command_generic_exception_returns_1_with_str():
    code, out, err = tool.run_command(None)
    assert code == 1
    assert out == ""
    assert err != ""


# --------------------------------------------------------------------------
# check_prerequisites
# --------------------------------------------------------------------------

def test_check_prerequisites_all_pass(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.100", "")),
        ("doctl account get", (0, "abc123", "")),
        ("ssh-key list", (0, "111\tkey1", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "All DigitalOcean prerequisites satisfied" in out


def test_check_prerequisites_doctl_missing(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (1, "", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "doctl not installed" in out
    assert "Missing requirements: doctl" in out


def test_check_prerequisites_not_authenticated(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.100", "")),
        ("doctl account get", (1, "", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Not authenticated with DigitalOcean" in out


def test_check_prerequisites_no_ssh_keys_only_warns(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.100", "")),
        ("doctl account get", (0, "abc123", "")),
        ("ssh-key list", (1, "", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0  # SSH-key absence is only a warning, not a blocking issue
    assert "No SSH keys found" in out


# --------------------------------------------------------------------------
# create_droplet
# --------------------------------------------------------------------------

def _droplet_args(**overrides):
    base = dict(
        name="mydroplet", region=None, size=None, image=None, ssh_keys=None,
        tags=None, user_data_file=None, enable_monitoring=False, enable_ipv6=False,
    )
    base.update(overrides)
    return _Args(**base)


def test_create_droplet_missing_name_returns_1(capsys):
    rc = tool.create_droplet(_droplet_args(name=""))
    assert rc == 1
    assert "Droplet name is required" in capsys.readouterr().out


def test_create_droplet_success_autoselects_ssh_keys_and_writes_info(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    calls = []
    header = "ID\tName\tPublicIPv4\tStatus\tRegion"
    data_row = "12345\tmydroplet\t1.2.3.4\tactive\tnyc3"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "111\n222", "")),
        ("droplet create", (0, f"{header}\n{data_row}", "")),
    ], calls))

    rc = tool.create_droplet(_droplet_args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet created successfully" in out
    assert "Droplet ID: 12345" in out
    assert "Public IP: 1.2.3.4" in out

    create_cmd = next(c for c in calls if "droplet create" in c)
    assert "--ssh-keys 111,222" in create_cmd
    assert "--region nyc3" in create_cmd
    assert "--size s-1vcpu-1gb" in create_cmd
    assert "--image ubuntu-22-04-x64" in create_cmd

    info = (tmp_path / INFO_FILE).read_text()
    assert "DROPLET_ID=12345" in info
    assert "DROPLET_IP=1.2.3.4" in info
    assert "DROPLET_NAME=mydroplet" in info


def test_create_droplet_explicit_ssh_keys_skips_lookup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    header = "ID\tName\tPublicIPv4\tStatus\tRegion"
    data_row = "1\tx\t9.9.9.9\tactive\tnyc3"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet create", (0, f"{header}\n{data_row}", "")),
    ], calls))

    rc = tool.create_droplet(_droplet_args(ssh_keys="999"))

    assert rc == 0
    assert not any("ssh-key list" in c for c in calls)
    create_cmd = next(c for c in calls if "droplet create" in c)
    assert "--ssh-keys 999" in create_cmd


def test_create_droplet_custom_region_size_image_tags_userdata_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []
    header = "ID\tName\tPublicIPv4\tStatus\tRegion"
    data_row = "1\tx\t9.9.9.9\tactive\tsfo3"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet create", (0, f"{header}\n{data_row}", "")),
    ], calls))

    rc = tool.create_droplet(_droplet_args(
        ssh_keys="1", region="sfo3", size="s-2vcpu-4gb", image="debian-12-x64",
        tags="prod,web", user_data_file="cloud-init.yml",
        enable_monitoring=True, enable_ipv6=True,
    ))

    assert rc == 0
    create_cmd = next(c for c in calls if "droplet create" in c)
    assert "--region sfo3" in create_cmd
    assert "--size s-2vcpu-4gb" in create_cmd
    assert "--image debian-12-x64" in create_cmd
    assert "--tag-names prod,web" in create_cmd
    assert "--user-data-file cloud-init.yml" in create_cmd
    assert "--enable-monitoring" in create_cmd
    assert "--enable-ipv6" in create_cmd
    assert "--wait" in create_cmd


def test_create_droplet_no_ssh_keys_available_warns_and_uses_password(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    header = "ID\tName\tPublicIPv4\tStatus\tRegion"
    data_row = "1\tx\t9.9.9.9\tactive\tnyc3"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (1, "", "")),
        ("droplet create", (0, f"{header}\n{data_row}", "")),
    ]))

    rc = tool.create_droplet(_droplet_args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "No SSH keys found - droplet will use password authentication" in out


def test_create_droplet_creation_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "111", "")),
        ("droplet create", (1, "", "quota exceeded")),
    ]))

    rc = tool.create_droplet(_droplet_args())

    out = capsys.readouterr().out
    assert rc == 1
    assert "Droplet creation failed" in out
    assert "quota exceeded" in out
    assert not (tmp_path / INFO_FILE).exists()


def test_create_droplet_success_but_no_data_row_skips_info_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    header_only = "ID\tName\tPublicIPv4\tStatus\tRegion"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "111", "")),
        ("droplet create", (0, header_only, "")),
    ]))

    rc = tool.create_droplet(_droplet_args())

    assert rc == 0
    assert not (tmp_path / INFO_FILE).exists()


def test_create_droplet_success_but_data_row_too_short_skips_info_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    header = "ID\tName\tPublicIPv4\tStatus\tRegion"
    short_row = "1 x"  # fewer than 4 fields
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "111", "")),
        ("droplet create", (0, f"{header}\n{short_row}", "")),
    ]))

    rc = tool.create_droplet(_droplet_args())

    assert rc == 0
    assert not (tmp_path / INFO_FILE).exists()


# --------------------------------------------------------------------------
# deploy_app
# --------------------------------------------------------------------------

def _write_info(tmp_path, ip="1.2.3.4", droplet_id="12345", name="mydroplet"):
    (tmp_path / INFO_FILE).write_text(
        f"DROPLET_ID={droplet_id}\nDROPLET_IP={ip}\nDROPLET_NAME={name}\n"
    )


def test_deploy_app_no_info_file_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.deploy_app(_Args(method=None, docker_image=None, git_repo=None))
    assert rc == 1
    assert "Droplet info not found. Create droplet first." in capsys.readouterr().out


def test_deploy_app_docker_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
        ("get-docker.sh", (0, "Docker installed successfully", "")),
        ("docker run", (0, "Application deployed", "")),
    ]))

    rc = tool.deploy_app(_Args(method="docker", docker_image="myrepo/app:latest", git_repo=None))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Application deployed successfully" in out
    assert "Access your app at: http://1.2.3.4" in out


def test_deploy_app_docker_missing_image_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
        ("get-docker.sh", (0, "Docker installed successfully", "")),
    ]))

    rc = tool.deploy_app(_Args(method="docker", docker_image=None, git_repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "--docker-image required for Docker deployment" in out


def test_deploy_app_docker_install_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
        ("get-docker.sh", (1, "", "install failed")),
    ]))

    rc = tool.deploy_app(_Args(method="docker", docker_image="x", git_repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to install Docker" in out


def test_deploy_app_git_missing_repo_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
    ]))

    rc = tool.deploy_app(_Args(method="git", docker_image=None, git_repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "--git-repo required for Git deployment" in out


def test_deploy_app_git_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
        ("git clone", (0, "Application deployed from Git", "")),
    ]))

    rc = tool.deploy_app(_Args(method="git", docker_image=None, git_repo="https://example.com/repo.git"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Application deployed from Git" in out


def test_deploy_app_git_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
        ("git clone", (1, "", "clone failed")),
    ]))

    rc = tool.deploy_app(_Args(method="git", docker_image=None, git_repo="bad"))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to deploy from Git" in out


def test_deploy_app_unknown_method_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
    ]))

    rc = tool.deploy_app(_Args(method="ftp", docker_image=None, git_repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Unknown deployment method: ftp" in out


def test_deploy_app_defaults_to_docker_method_when_none(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
        ("get-docker.sh", (0, "ok", "")),
    ]))

    rc = tool.deploy_app(_Args(method=None, docker_image=None, git_repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Deploying with Docker" in out


def test_deploy_app_missing_droplet_ip_in_info_file_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / INFO_FILE).write_text("DROPLET_ID=1\nDROPLET_NAME=x\n")

    rc = tool.deploy_app(_Args(method="docker", docker_image=None, git_repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Droplet IP not found" in out


def test_deploy_app_ssh_never_ready_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (1, "", "")),
    ]))

    rc = tool.deploy_app(_Args(method="docker", docker_image="x", git_repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "SSH not ready after 5 minutes" in out


# --------------------------------------------------------------------------
# configure_monitoring
# --------------------------------------------------------------------------

def test_configure_monitoring_no_info_file_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.configure_monitoring(_Args())
    assert rc == 1
    assert "Droplet info not found. Create droplet first." in capsys.readouterr().out


def test_configure_monitoring_already_enabled(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet get", (0, "monitoring,private_networking", "")),
        ("install.sh", (0, "Monitoring agent installed", "")),
    ]))

    rc = tool.configure_monitoring(_Args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Monitoring already enabled" in out
    assert "Monitoring agent installed" in out


def test_configure_monitoring_not_enabled_warns_but_still_installs_agent(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet get", (0, "private_networking", "")),
        ("install.sh", (0, "ok", "")),
    ]))

    rc = tool.configure_monitoring(_Args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "not enabled - enable during droplet creation" in out


def test_configure_monitoring_features_check_failure_still_installs_agent(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet get", (1, "", "")),
        ("install.sh", (0, "ok", "")),
    ]))

    rc = tool.configure_monitoring(_Args())

    assert rc == 0


def test_configure_monitoring_agent_install_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet get", (0, "monitoring", "")),
        ("install.sh", (1, "", "network error")),
    ]))

    rc = tool.configure_monitoring(_Args())

    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to install monitoring agent" in out


# --------------------------------------------------------------------------
# health_check
# --------------------------------------------------------------------------

def test_health_check_no_info_file_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.health_check(_Args(health_endpoint=None))
    assert rc == 1
    assert "Droplet info not found" in capsys.readouterr().out


def test_health_check_droplet_not_active_returns_1_immediately(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status --no-header", (0, "off", "")),
    ]))

    rc = tool.health_check(_Args(health_endpoint=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Droplet is not active" in out


def test_health_check_ssh_not_accessible_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status --no-header", (0, "active", "")),
        ("echo ok", (1, "", "")),
    ]))

    rc = tool.health_check(_Args(health_endpoint=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "SSH is not accessible" in out


def test_health_check_full_pass_with_high_disk_usage_and_running_app(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status --no-header", (0, "active", "")),
        ("echo ok", (0, "ok", "")),
        ("df -h", (0, "/dev/vda1  20G  19G  1G  95% /", "")),
        ("free -h", (0, "Mem: 1G 500M 500M", "")),
        ("docker ps", (0, "CONTAINER  myapp  running", "")),
        ("curl -f -s", (0, "OK", "")),
    ]))

    rc = tool.health_check(_Args(health_endpoint="/health"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Disk usage is high: 95%" in out
    assert "Application container is running" in out
    assert "Health endpoint responding" in out
    assert "Health check complete" in out


def test_health_check_low_disk_usage_no_warning(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status --no-header", (0, "active", "")),
        ("echo ok", (0, "ok", "")),
        ("df -h", (0, "/dev/vda1  20G  2G  18G  10% /", "")),
        ("free -h", (0, "Mem: 1G", "")),
        ("docker ps", (1, "", "")),
    ]))

    rc = tool.health_check(_Args(health_endpoint=None))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Disk usage is high" not in out
    assert "Docker not installed or application not containerized" in out


def test_health_check_docker_running_but_no_myapp_warns(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status --no-header", (0, "active", "")),
        ("echo ok", (0, "ok", "")),
        ("df -h", (1, "", "")),
        ("free -h", (1, "", "")),
        ("docker ps", (0, "CONTAINER  otherapp", "")),
    ]))

    rc = tool.health_check(_Args(health_endpoint=None))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Application container not found" in out
    assert "Cannot check disk space" in out


def test_health_check_endpoint_failure_reports_not_responding(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status --no-header", (0, "active", "")),
        ("echo ok", (0, "ok", "")),
        ("df -h", (1, "", "")),
        ("free -h", (1, "", "")),
        ("docker ps", (1, "", "")),
        ("curl -f -s", (1, "", "")),
    ]))

    rc = tool.health_check(_Args(health_endpoint="/health"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Health endpoint not responding" in out


# --------------------------------------------------------------------------
# run_tests ('test' subcommand)
# --------------------------------------------------------------------------

def test_run_tests_all_pass(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.100", "")),
        ("doctl account get", (0, "abc", "")),
        ("region list", (0, "nyc3", "")),
        ("ssh-key list", (0, "111", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Total tests: 6" in out
    assert "All tests passed" in out


def test_run_tests_doctl_missing_fails_but_continues_other_checks(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (1, "", "")),
        ("doctl account get", (0, "abc", "")),
        ("region list", (0, "nyc3", "")),
        ("ssh-key list", (0, "111", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "doctl not installed" in out
    assert "1 test(s) failed" in out


def test_run_tests_test6_no_info_file_counts_as_pass(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("region list", (0, "nyc3", "")),
        ("ssh-key list", (0, "111", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "No droplet info file" in out


def test_run_tests_test6_with_info_file_droplet_exists(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("region list", (0, "nyc3", "")),
        ("ssh-key list", (0, "111", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
        ("droplet get", (0, "active", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet exists: active" in out


def test_run_tests_test6_with_info_file_droplet_not_found(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("region list", (0, "nyc3", "")),
        ("ssh-key list", (0, "111", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
        ("droplet get", (1, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Droplet not found" in out


def test_run_tests_no_ssh_keys_counts_as_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("region list", (0, "nyc3", "")),
        ("ssh-key list", (1, "", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No SSH keys configured" in out


# --------------------------------------------------------------------------
# troubleshoot
# --------------------------------------------------------------------------

def test_troubleshoot_no_issues_returns_0(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ratelimit", (0, "1000 remaining", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "No issues found - DigitalOcean is healthy!" in out


def test_troubleshoot_auth_failure_reports_issue_and_fixes(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (1, "", "")),
        ("ratelimit", (0, "1000 remaining", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Not authenticated with DigitalOcean" in out
    assert "Common fixes" in out


def test_troubleshoot_with_info_file_inactive_droplet_and_ssh_down(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("Status --no-header", (0, "new", "")),
        ("echo ok", (1, "", "")),
        ("ratelimit", (0, "ok", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Droplet status: new" in out
    assert "Cannot connect via SSH" in out


def test_troubleshoot_ratelimit_check_failure_warns_but_no_issue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ratelimit", (1, "", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cannot check rate limits" in out


# --------------------------------------------------------------------------
# cleanup
# --------------------------------------------------------------------------

def test_cleanup_no_info_file_returns_0(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.cleanup(_Args(force=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Nothing to clean up" in out


def test_cleanup_force_success_removes_info_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet delete", (0, "", "")),
    ]))

    rc = tool.cleanup(_Args(force=True))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet deleted" in out
    assert not (tmp_path / INFO_FILE).exists()


def test_cleanup_force_failure_keeps_info_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet delete", (1, "", "denied")),
    ]))

    rc = tool.cleanup(_Args(force=True))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to delete droplet" in out
    assert (tmp_path / INFO_FILE).exists()


def test_cleanup_prompt_declined_cancels_without_deleting(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)

    def fail_if_called(cmd, timeout=300):
        raise AssertionError("should not attempt delete when cancelled")
    monkeypatch.setattr(tool, "run_command", fail_if_called)
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")

    rc = tool.cleanup(_Args(force=False))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Cleanup cancelled" in out
    assert (tmp_path / INFO_FILE).exists()


def test_cleanup_prompt_accepted_case_insensitive_proceeds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet delete", (0, "", "")),
    ]))
    monkeypatch.setattr("builtins.input", lambda prompt="": "YES")

    rc = tool.cleanup(_Args(force=False))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet deleted" in out


def test_cleanup_prompt_accepts_short_y(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet delete", (0, "", "")),
    ]))
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    rc = tool.cleanup(_Args(force=False))

    assert rc == 0


# --------------------------------------------------------------------------
# main() dispatch
# --------------------------------------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def _stub_dispatch(monkeypatch, func_name, capture_key="called"):
    captured = {}
    def fake(args):
        captured[capture_key] = args
        return 0
    monkeypatch.setattr(tool, func_name, fake)
    return captured


def test_main_dispatches_check_prerequisites(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "check_prerequisites")
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-prerequisites"])
    rc = tool.main()
    assert rc == 0
    assert "called" in captured


def test_main_dispatches_create_droplet_with_defaults(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "create_droplet")
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-droplet", "--name", "d1"])
    rc = tool.main()
    assert rc == 0
    args = captured["called"]
    assert args.name == "d1"
    assert args.region == "nyc3"
    assert args.size == "s-1vcpu-1gb"
    assert args.image == "ubuntu-22-04-x64"
    assert args.enable_monitoring is False
    assert args.enable_ipv6 is False


def test_main_create_droplet_missing_name_exits(monkeypatch):
    import pytest
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-droplet"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_dispatches_deploy_app_default_method_docker(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "deploy_app")
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy-app"])
    rc = tool.main()
    assert rc == 0
    assert captured["called"].method == "docker"


def test_main_deploy_app_invalid_method_choice_exits(monkeypatch):
    import pytest
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy-app", "--method", "ftp"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_dispatches_configure_monitoring(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "configure_monitoring")
    monkeypatch.setattr(sys, "argv", ["tool.py", "configure-monitoring"])
    rc = tool.main()
    assert rc == 0
    assert "called" in captured


def test_main_dispatches_health_check(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "health_check")
    monkeypatch.setattr(sys, "argv", ["tool.py", "health-check", "--health-endpoint", "/h"])
    rc = tool.main()
    assert rc == 0
    assert captured["called"].health_endpoint == "/h"


def test_main_dispatches_test_subcommand(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "run_tests")
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "called" in captured


def test_main_dispatches_troubleshoot(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "troubleshoot")
    monkeypatch.setattr(sys, "argv", ["tool.py", "troubleshoot"])
    rc = tool.main()
    assert rc == 0
    assert "called" in captured


def test_main_dispatches_cleanup_default_force_false(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "cleanup")
    monkeypatch.setattr(sys, "argv", ["tool.py", "cleanup"])
    rc = tool.main()
    assert rc == 0
    assert captured["called"].force is False


def test_main_dispatches_cleanup_force_flag(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "cleanup")
    monkeypatch.setattr(sys, "argv", ["tool.py", "cleanup", "--force"])
    rc = tool.main()
    assert rc == 0
    assert captured["called"].force is True


def test_subprocess_check_prerequisites_smoke(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check-prerequisites"],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode in (0, 1)
    assert "Checking DigitalOcean Prerequisites" in result.stdout


def test_subprocess_no_args_exits_nonzero(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "usage" in result.stdout.lower()


# --------------------------------------------------------------------------
# extra coverage: individual failing branches not yet exercised
# --------------------------------------------------------------------------

def test_deploy_app_docker_run_failure_after_successful_install(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("echo ready", (0, "ready", "")),
        ("get-docker.sh", (0, "ok", "")),
        ("docker run", (1, "", "port already in use")),
    ]))

    rc = tool.deploy_app(_Args(method="docker", docker_image="myrepo/app:latest", git_repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to deploy application" in out


def test_run_tests_auth_only_fails(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (1, "", "")),
        ("region list", (0, "nyc3", "")),
        ("ssh-key list", (0, "111", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Not authenticated" in out
    assert "Not authenticated with DigitalOcean" in out  # from issues list in summary


def test_run_tests_api_connectivity_only_fails(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("region list", (1, "", "")),
        ("ssh-key list", (0, "111", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Cannot connect to API" in out
    assert "Cannot connect to DigitalOcean API" in out


def test_run_tests_droplet_sizes_query_only_fails(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("region list", (0, "nyc3", "")),
        ("ssh-key list", (0, "111", "")),
        ("size list", (1, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Cannot query droplet sizes" in out


def test_troubleshoot_fully_healthy_with_active_droplet_and_ssh_up(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("Status --no-header", (0, "active", "")),
        ("echo ok", (0, "ok", "")),
        ("ratelimit", (0, "ok", "")),
    ]))

    rc = tool.troubleshoot(_Args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet is active" in out
    assert "SSH is accessible" in out
    assert "No issues found" in out


def test_health_check_memory_output_printed_when_check_succeeds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status --no-header", (0, "active", "")),
        ("echo ok", (0, "ok", "")),
        ("df -h", (1, "", "")),
        ("free -h", (0, "Mem:  1.9G  700M  1.2G", "")),
        ("docker ps", (1, "", "")),
    ]))

    rc = tool.health_check(_Args(health_endpoint=None))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Mem:  1.9G  700M  1.2G" in out


def test_health_check_memory_output_not_printed_when_check_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status --no-header", (0, "active", "")),
        ("echo ok", (0, "ok", "")),
        ("df -h", (1, "", "")),
        ("free -h", (1, "should-not-appear", "")),
        ("docker ps", (1, "", "")),
    ]))

    rc = tool.health_check(_Args(health_endpoint=None))

    out = capsys.readouterr().out
    assert rc == 0
    assert "should-not-appear" not in out
