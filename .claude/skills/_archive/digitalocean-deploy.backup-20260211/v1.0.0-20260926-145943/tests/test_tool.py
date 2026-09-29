import os
import subprocess
import sys
from pathlib import Path

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "digitalocean_deploy_backup_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
INFO_FILE = ".digitalocean-droplet.txt"

import pytest


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    # tool.py imports `time` but (unlike the sibling digitalocean-deploy skill)
    # this backup implementation has no retry/polling loop that calls
    # time.sleep. Patched anyway, defensively, so any future mutant that
    # introduces a sleep-based retry can never hang this suite.
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
        ("doctl version", (0, "doctl version 1.98.0", "")),
        ("doctl account get", (0, "user@example.com Active", "")),
        ("ssh-key list", (0, "ID\tName\n111\tkey1", "")),
        ("region list", (0, "nyc3\tNew York 3", "")),
        ("size list", (0, "s-1vcpu-1gb\t1024\t1\t25\t6.00", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "doctl CLI installed: doctl version 1.98.0" in out
    assert "doctl authenticated successfully" in out
    assert "Account: user@example.com" in out
    assert "Found 1 SSH key(s)" in out
    # Checks 4 and 5 (regions/sizes) print their success block only when the
    # command itself succeeded with non-empty output.
    assert "Available regions:" in out
    assert "nyc3\tNew York 3" in out
    assert "Available sizes (sample):" in out
    assert "s-1vcpu-1gb\t1024\t1\t25\t6.00" in out
    assert "All prerequisites met!" in out


def test_check_prerequisites_doctl_missing(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (1, "", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list", (0, "ID\tName\n1\tk", "")),
        ("region list", (0, "nyc3", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "doctl CLI not found" in out
    assert "Found 1 issue(s):" in out
    assert "doctl CLI not installed" in out


def test_check_prerequisites_not_authenticated(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.98.0", "")),
        ("doctl account get", (1, "", "")),
        ("ssh-key list", (0, "ID\tName\n1\tk", "")),
        ("region list", (0, "nyc3", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "doctl not authenticated" in out
    assert "Not authenticated with DigitalOcean API" in out


def test_check_prerequisites_no_ssh_keys_after_header_is_an_issue(monkeypatch, capsys):
    # code==0 but only the header row remains after stripping it -> counted
    # as a real issue (differs from the sibling skill, where a missing SSH
    # key is only ever a warning and never fails the check).
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.98.0", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list", (0, "ID\tName", "")),
        ("region list", (0, "nyc3", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No SSH keys found" in out
    assert "No SSH keys configured" in out


def test_check_prerequisites_ssh_key_command_failure_is_only_a_warning(monkeypatch, capsys):
    # When the ssh-key list command itself fails (code != 0), the tool only
    # warns "Could not list SSH keys" and does NOT add it to `issues`, so it
    # never affects the return code -- unlike the empty-keys-list case above.
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.98.0", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list", (1, "", "")),
        ("region list", (0, "nyc3", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Could not list SSH keys" in out


def test_check_prerequisites_shows_up_to_three_keys(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.98.0", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list", (0, "ID\tName\n1\ta\n2\tb\n3\tc\n4\td", "")),
        ("region list", (0, "nyc3", "")),
        ("size list", (0, "s-1vcpu-1gb", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Found 4 SSH key(s)" in out
    assert "1\ta" in out and "2\tb" in out and "3\tc" in out
    assert "4\td" not in out  # only first 3 are printed


def test_check_prerequisites_regions_and_sizes_failure_is_silent(monkeypatch, capsys):
    # Checks 4 and 5 have no failure branch at all: a non-zero exit code is
    # simply not reported, and does not affect the overall result.
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "doctl 1.98.0", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list", (0, "ID\tName\n1\ta", "")),
        ("region list", (1, "", "")),
        ("size list", (1, "", "")),
    ]))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Available regions" not in out
    assert "Available sizes" not in out


# --------------------------------------------------------------------------
# create_droplet
# --------------------------------------------------------------------------

def _droplet_args(**overrides):
    base = dict(
        name="mydroplet", image="ubuntu-22-04-x64", region="nyc3", size="s-1vcpu-1gb",
        enable_monitoring=False, enable_ipv6=False, enable_backups=False,
        vpc_uuid=None, user_data=None,
    )
    base.update(overrides)
    return _Args(**base)


def test_create_droplet_no_ssh_keys_returns_1(capsys, monkeypatch):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (1, "", "")),
    ]))
    rc = tool.create_droplet(_droplet_args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No SSH keys found. Add SSH key first:" in out


def test_create_droplet_ssh_key_command_succeeds_but_empty_output_returns_1(capsys, monkeypatch):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "", "")),
    ]))
    rc = tool.create_droplet(_droplet_args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "No SSH keys found" in out


def test_create_droplet_success_writes_info_file_without_ip(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    calls = []
    header = "ID\tName\tPublic IPv4\tStatus\tRegion"
    data_row = "123456789\tmydroplet\t203.0.113.45\tactive\tnyc3"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "111\n222", "")),
        ("droplet create", (0, f"{header}\n{data_row}", "")),
    ], calls))

    rc = tool.create_droplet(_droplet_args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Using 2 SSH key(s)" in out
    assert "Droplet created successfully! ✅" in out
    assert "Droplet ID: 123456789" in out
    assert "Droplet info saved to .digitalocean-droplet.txt" in out
    assert "Wait 30-60 seconds for SSH to be ready" in out

    create_cmd = next(c for c in calls if "droplet create" in c)
    assert "--ssh-keys 111,222" in create_cmd
    assert "--region nyc3" in create_cmd
    assert "--size s-1vcpu-1gb" in create_cmd
    assert "--image ubuntu-22-04-x64" in create_cmd
    assert "--wait" in create_cmd
    assert "--format ID,Name,PublicIPv4,Status,Region" in create_cmd

    info = (tmp_path / INFO_FILE).read_text()
    assert "DROPLET_ID=123456789" in info
    assert "DROPLET_NAME=mydroplet" in info
    # This implementation, unlike the sibling skill, never records the IP
    # in the saved info file at all.
    assert "DROPLET_IP" not in info


def test_create_droplet_all_optional_flags_included_in_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    calls = []
    header = "ID\tName\tPublic IPv4\tStatus\tRegion"
    data_row = "1\tx\t9.9.9.9\tactive\tsfo3"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "111", "")),
        ("droplet create", (0, f"{header}\n{data_row}", "")),
    ], calls))

    rc = tool.create_droplet(_droplet_args(
        region="sfo3", size="s-2vcpu-4gb", image="debian-12-x64",
        enable_monitoring=True, enable_ipv6=True, enable_backups=True,
        vpc_uuid="vpc-abc", user_data="cloud-init.yml",
    ))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Monitoring: Enabled (free)" in out
    assert "IPv6: Enabled" in out
    assert "Backups: Enabled (+20% cost)" in out
    assert "VPC: vpc-abc" in out
    assert "User Data: cloud-init.yml" in out

    create_cmd = next(c for c in calls if "droplet create" in c)
    assert "--enable-monitoring" in create_cmd
    assert "--enable-ipv6" in create_cmd
    assert "--enable-backups" in create_cmd
    assert "--vpc-uuid vpc-abc" in create_cmd
    assert "--user-data-file cloud-init.yml" in create_cmd


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


def test_create_droplet_header_only_output_skips_info_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    header_only = "ID\tName\tPublic IPv4\tStatus\tRegion"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "111", "")),
        ("droplet create", (0, header_only, "")),
    ]))

    rc = tool.create_droplet(_droplet_args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Wait 30-60 seconds for SSH to be ready" in out
    assert not (tmp_path / INFO_FILE).exists()


def test_create_droplet_blank_data_row_crashes_with_indexerror(tmp_path, monkeypatch, capsys):
    # FIXED: a blank second line no longer crashes with IndexError. The
    # blank-row guard (`len(lines) > 1 and lines[1].split()`) now falls
    # through to a warning, and the droplet info file is not written --
    # while the function still returns 0 (the droplet WAS created; only
    # parsing its ID from the table output failed).
    monkeypatch.chdir(tmp_path)
    header = "ID\tName\tPublic IPv4\tStatus\tRegion"
    stdout = f"{header}\n\ndata-that-is-never-reached"
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("ssh-key list", (0, "111", "")),
        ("droplet create", (0, stdout, "")),
    ]))

    rc = tool.create_droplet(_droplet_args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Could not parse droplet ID from output; droplet info not saved" in out
    assert "Droplet ID:" not in out
    assert not (tmp_path / INFO_FILE).exists()


# --------------------------------------------------------------------------
# deploy_app
# --------------------------------------------------------------------------

def _write_info(tmp_path, droplet_id="12345", name="mydroplet"):
    (tmp_path / INFO_FILE).write_text(f"DROPLET_ID={droplet_id}\nDROPLET_NAME={name}\n")


def _deploy_args(**overrides):
    base = dict(method="docker", repo=None, image=None, source=None, port=8000, deploy_script=None)
    base.update(overrides)
    return _Args(**base)


def test_deploy_app_no_info_file_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.deploy_app(_deploy_args())
    assert rc == 1
    assert "No droplet info found. Create droplet first." in capsys.readouterr().out


def test_deploy_app_ip_lookup_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (1, "", "")),
    ]))
    rc = tool.deploy_app(_deploy_args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to get droplet IP" in out


def test_deploy_app_git_success_with_deploy_script(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    calls = []
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "203.0.113.45", "")),
        ("apt-get update", (0, "", "")),
        ("apt-get install -y git", (0, "", "")),
        ("git clone", (0, "", "")),
        ("bash deploy.sh", (0, "", "")),
    ], calls))

    rc = tool.deploy_app(_deploy_args(method="git", repo="https://example.com/repo.git", deploy_script="deploy.sh"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Deploying via Git..." in out
    assert "Application deployed successfully! ✅" in out
    assert "Access your app at: http://203.0.113.45:8000" in out
    clone_cmd = next(c for c in calls if "git clone" in c)
    assert "git clone https://example.com/repo.git /app" in clone_cmd


def test_deploy_app_git_no_deploy_script_uses_echo_placeholder(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    calls = []
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("apt-get update", (0, "", "")),
        ("apt-get install -y git", (0, "", "")),
        ("git clone", (0, "", "")),
        ("No deploy script specified", (0, "", "")),
    ], calls))

    rc = tool.deploy_app(_deploy_args(method="git", repo="https://example.com/repo.git"))

    assert rc == 0
    assert any("No deploy script specified" in c for c in calls)


def test_deploy_app_git_missing_repo_is_not_validated_bug(tmp_path, monkeypatch, capsys):
    # FIXED: a missing --repo for the git method is now validated up front
    # (matching the existing guard for --source in the scp branch), instead
    # of silently becoming the literal string "None" in the git clone
    # command. No SSH/git commands should even be attempted.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    calls = []
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
    ], calls))

    rc = tool.deploy_app(_deploy_args(method="git", repo=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "--repo required for git method" in out
    assert not any("git clone" in c for c in calls)


def test_deploy_app_git_command_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("apt-get update", (0, "", "")),
        ("apt-get install -y git", (0, "", "")),
        ("git clone", (1, "", "repo not found")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="git", repo="bad"))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Command failed: " in out
    assert "repo not found" in out


def test_deploy_app_docker_success(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("apt-get update", (0, "", "")),
        ("apt-get install -y docker.io", (0, "", "")),
        ("systemctl start docker", (0, "", "")),
        ("systemctl enable docker", (0, "", "")),
        ("docker pull", (0, "", "")),
        ("docker run", (0, "", "")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="docker", image="nginx:latest", port=80))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Deploying via Docker..." in out
    assert "Access your app at: http://1.2.3.4:80" in out


def test_deploy_app_docker_missing_image_uses_echo_placeholder_but_reports_success(tmp_path, monkeypatch, capsys):
    # GENUINE BUG / design gap: with no --image, both the pull and run steps
    # degrade to a harmless echo, yet the function still prints "Application
    # deployed successfully!" -- nothing was actually deployed.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    calls = []
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("apt-get update", (0, "", "")),
        ("apt-get install -y docker.io", (0, "", "")),
        ("systemctl start docker", (0, "", "")),
        ("systemctl enable docker", (0, "", "")),
        ("No image specified", (0, "", "")),
    ], calls))

    rc = tool.deploy_app(_deploy_args(method="docker", image=None))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Application deployed successfully! ✅" in out
    assert sum(1 for c in calls if "No image specified" in c) == 2


def test_deploy_app_docker_run_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("apt-get update", (0, "", "")),
        ("apt-get install -y docker.io", (0, "", "")),
        ("systemctl start docker", (0, "", "")),
        ("systemctl enable docker", (0, "", "")),
        ("docker pull", (0, "", "")),
        ("docker run", (1, "", "port already in use")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="docker", image="nginx:latest"))

    out = capsys.readouterr().out
    assert rc == 1
    assert "port already in use" in out


def test_deploy_app_scp_missing_source_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="scp", source=None))

    out = capsys.readouterr().out
    assert rc == 1
    assert "--source required for scp method" in out


def test_deploy_app_scp_success_with_deploy_script(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("scp -r", (0, "", "")),
        ("bash setup.sh", (0, "", "")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="scp", source="./dist", deploy_script="setup.sh"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Files copied" in out
    assert "Deploy script completed" in out


def test_deploy_app_scp_without_deploy_script_still_succeeds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("scp -r", (0, "", "")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="scp", source="./dist", deploy_script=None))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Files copied" in out
    assert "Deploy script completed" not in out


def test_deploy_app_scp_copy_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("scp -r", (1, "", "connection refused")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="scp", source="./dist"))

    out = capsys.readouterr().out
    assert rc == 1
    assert "SCP failed" in out
    assert "connection refused" in out


def test_deploy_app_scp_deploy_script_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
        ("scp -r", (0, "", "")),
        ("bash setup.sh", (1, "", "script error")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="scp", source="./dist", deploy_script="setup.sh"))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Deploy script failed" in out


def test_deploy_app_unknown_method_falls_through_and_reports_success_bug(tmp_path, monkeypatch, capsys):
    # FIXED: unlike before (where there was no final `else` branch, so an
    # unrecognized --method fell straight through to the success message),
    # deploy_app now explicitly rejects it. Only reachable by calling
    # deploy_app directly, since argparse's `choices` blocks it from the CLI.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("PublicIPv4 --no-header", (0, "1.2.3.4", "")),
    ]))

    rc = tool.deploy_app(_deploy_args(method="ftp"))

    out = capsys.readouterr().out
    assert rc == 1
    assert "Unknown deployment method: ftp" in out
    assert "Supported methods: git, docker, scp" in out
    assert "Application deployed successfully! ✅" not in out


# --------------------------------------------------------------------------
# configure_monitoring
# --------------------------------------------------------------------------

def _monitor_args(**overrides):
    base = dict(enable_cpu_alert=False, enable_memory_alert=False, enable_disk_alert=False, alert_email=None)
    base.update(overrides)
    return _Args(**base)


def test_configure_monitoring_no_info_file_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.configure_monitoring(_monitor_args())
    assert rc == 1
    assert "No droplet info found. Create droplet first." in capsys.readouterr().out


def test_configure_monitoring_already_enabled_no_alerts(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (0, "monitoring,backups", "")),
    ]))

    rc = tool.configure_monitoring(_monitor_args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Monitoring already enabled" in out
    assert "Monitoring configuration complete! ✅" in out


def test_configure_monitoring_not_enabled_warns_but_returns_0(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (0, "backups", "")),
    ]))

    rc = tool.configure_monitoring(_monitor_args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Monitoring not enabled. Enable during droplet creation with --enable-monitoring" in out


def test_configure_monitoring_features_check_failure_still_says_not_enabled(tmp_path, monkeypatch, capsys):
    # FIXED: when the Features lookup itself fails (code != 0), the function
    # now reports that the check could not be performed, distinct from a
    # genuine "not enabled" negative, instead of collapsing both into the
    # same "not enabled" warning.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (1, "", "")),
    ]))

    rc = tool.configure_monitoring(_monitor_args())

    out = capsys.readouterr().out
    assert rc == 0
    assert "Could not verify monitoring status" in out
    assert "Monitoring not enabled. Enable during droplet creation with --enable-monitoring" not in out
    assert "Monitoring already enabled" not in out


def test_configure_monitoring_cpu_alert_created(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (0, "monitoring", "")),
        ("droplet/cpu", (0, "", "")),
    ]))

    rc = tool.configure_monitoring(_monitor_args(enable_cpu_alert=True, alert_email="ops@example.com"))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Creating CPU usage alert (>80% for 5min)..." in out
    assert "CPU alert created" in out


def test_configure_monitoring_memory_alert_created(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (0, "monitoring", "")),
        ("memory_utilization_percent", (0, "", "")),
    ]))

    rc = tool.configure_monitoring(_monitor_args(enable_memory_alert=True))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Memory alert created" in out


def test_configure_monitoring_disk_alert_created(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (0, "monitoring", "")),
        ("disk_utilization_percent", (0, "", "")),
    ]))

    rc = tool.configure_monitoring(_monitor_args(enable_disk_alert=True))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Disk alert created" in out


def test_configure_monitoring_all_alerts_fail_but_function_still_returns_0(tmp_path, monkeypatch, capsys):
    # FIXED: when every enabled alert fails to create, configure_monitoring
    # now surfaces that as a failure (return 1) via the new `alerts_failed`
    # tracking, instead of silently reporting success.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (0, "monitoring", "")),
        ("droplet/cpu", (1, "", "")),
        ("memory_utilization_percent", (1, "", "")),
        ("disk_utilization_percent", (1, "", "")),
    ]))

    rc = tool.configure_monitoring(_monitor_args(
        enable_cpu_alert=True, enable_memory_alert=True, enable_disk_alert=True,
    ))

    out = capsys.readouterr().out
    assert rc == 1
    assert "CPU alert creation failed (may require API upgrade)" in out
    assert "Memory alert creation failed (may require API upgrade)" in out
    assert "Disk alert creation failed (may require API upgrade)" in out
    assert "Monitoring configuration completed with some alert failures" in out
    assert "Monitoring configuration complete!" not in out


def test_configure_monitoring_one_alert_fails_others_succeed_returns_1(tmp_path, monkeypatch, capsys):
    # New coverage for the alerts_failed fix: even a single failed alert
    # among several enabled ones must flip the overall result to failure --
    # this isn'"'"'t only an all-or-nothing check.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (0, "monitoring", "")),
        ("droplet/cpu", (0, "", "")),
        ("memory_utilization_percent", (1, "", "")),
    ]))

    rc = tool.configure_monitoring(_monitor_args(
        enable_cpu_alert=True, enable_memory_alert=True,
    ))

    out = capsys.readouterr().out
    assert rc == 1
    assert "CPU alert created" in out
    assert "Memory alert creation failed (may require API upgrade)" in out
    assert "Monitoring configuration completed with some alert failures" in out


def test_configure_monitoring_alert_email_defaults_when_not_given(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    calls = []
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Features", (0, "monitoring", "")),
        ("droplet/cpu", (0, "", "")),
    ], calls))

    rc = tool.configure_monitoring(_monitor_args(enable_cpu_alert=True, alert_email=None))

    assert rc == 0
    alert_cmd = next(c for c in calls if "droplet/cpu" in c)
    assert "your@email.com" in alert_cmd


# --------------------------------------------------------------------------
# health_check
# --------------------------------------------------------------------------

def _health_args(**overrides):
    base = dict(port=None)
    base.update(overrides)
    return _Args(**base)


def test_health_check_no_info_file_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.health_check(_health_args())
    assert rc == 1
    assert "No droplet info found. Create droplet first." in capsys.readouterr().out


def test_health_check_status_command_failure_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status,PublicIPv4 --no-header", (1, "", "")),
    ]))
    rc = tool.health_check(_health_args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to get droplet status" in out


def test_health_check_droplet_not_active_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status,PublicIPv4 --no-header", (0, "off", "")),
    ]))
    rc = tool.health_check(_health_args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Droplet status: off" in out


def test_health_check_full_pass_ssh_and_http_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status,PublicIPv4 --no-header", (0, "active 203.0.113.45", "")),
        ("SSH_OK", (0, "SSH_OK", "")),
        ("http_code", (0, "200", "")),
    ]))
    rc = tool.health_check(_health_args(port=8000))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet status: active" in out
    assert "SSH connectivity: OK" in out
    assert "HTTP endpoint: OK (Status: 200)" in out
    assert "Health check complete! ✅" in out


def test_health_check_ssh_failure_is_only_a_warning_rc_still_0(tmp_path, monkeypatch, capsys):
    # SSH failure never fails health_check as a whole -- unlike the sibling
    # skill, which returns 1 on SSH failure.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status,PublicIPv4 --no-header", (0, "active 203.0.113.45", "")),
        ("SSH_OK", (1, "", "")),
    ]))
    rc = tool.health_check(_health_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SSH connectivity: Failed" in out
    assert "Droplet may still be booting. Wait and try again." in out
    assert "Health check complete! ✅" in out


def test_health_check_status_line_without_ip_skips_ssh_check(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    calls = []
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status,PublicIPv4 --no-header", (0, "active", "")),
    ], calls))
    rc = tool.health_check(_health_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Checking SSH connectivity" not in out
    assert not any("ssh " in c for c in calls)


def test_health_check_http_endpoint_non_success_code_warns(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status,PublicIPv4 --no-header", (0, "active 203.0.113.45", "")),
        ("SSH_OK", (0, "SSH_OK", "")),
        ("http_code", (0, "404", "")),
    ]))
    rc = tool.health_check(_health_args(port=8000))
    out = capsys.readouterr().out
    assert rc == 0
    assert "HTTP endpoint: Status 404" in out


def test_health_check_http_endpoint_command_failure_reports_not_responding(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status,PublicIPv4 --no-header", (0, "active 203.0.113.45", "")),
        ("SSH_OK", (0, "SSH_OK", "")),
        ("http_code", (1, "", "")),
    ]))
    rc = tool.health_check(_health_args(port=8000))
    out = capsys.readouterr().out
    assert rc == 0
    assert "HTTP endpoint: Not responding" in out


def test_health_check_no_port_skips_http_check(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    calls = []
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("Status,PublicIPv4 --no-header", (0, "active 203.0.113.45", "")),
        ("SSH_OK", (0, "SSH_OK", "")),
    ], calls))
    rc = tool.health_check(_health_args(port=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Checking HTTP endpoint" not in out
    assert not any("curl" in c for c in calls)


# --------------------------------------------------------------------------
# run_tests ('test' subcommand)
# --------------------------------------------------------------------------

def test_run_tests_all_pass(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "111\tk", "")),
        ("image list --public", (0, "ubuntu-22-04-x64", "")),
        ("region list --no-header", (0, "nyc3", "")),
        ("size list --no-header", (0, "s-1vcpu-1gb", "")),
        ("monitoring alert list", (0, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Total tests: 6" in out
    assert "All tests passed! Ready for droplet creation." in out


def test_run_tests_doctl_missing_fails_test1_only(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (1, "", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "111\tk", "")),
        ("image list --public", (0, "ubuntu-22-04-x64", "")),
        ("region list --no-header", (0, "nyc3", "")),
        ("size list --no-header", (0, "s-1vcpu-1gb", "")),
        ("monitoring alert list", (0, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Test 1 FAILED: doctl CLI not found" in out
    assert "doctl CLI not installed" in out
    assert "1 test(s) failed" in out


def test_run_tests_auth_failure_fails_test2_only(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (1, "", "")),
        ("ssh-key list --no-header", (0, "111\tk", "")),
        ("image list --public", (0, "ubuntu-22-04-x64", "")),
        ("region list --no-header", (0, "nyc3", "")),
        ("size list --no-header", (0, "s-1vcpu-1gb", "")),
        ("monitoring alert list", (0, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Test 2 FAILED: Not authenticated" in out
    assert "Run: doctl auth init" in out


def test_run_tests_no_ssh_keys_fails_test3_only(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (1, "", "")),
        ("image list --public", (0, "ubuntu-22-04-x64", "")),
        ("region list --no-header", (0, "nyc3", "")),
        ("size list --no-header", (0, "s-1vcpu-1gb", "")),
        ("monitoring alert list", (0, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Test 3 FAILED: No SSH keys found" in out
    assert "Add SSH key with: doctl compute ssh-key create" in out


def test_run_tests_image_query_fails_test4_only_no_issue_listed(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "111\tk", "")),
        ("image list --public", (1, "", "")),
        ("region list --no-header", (0, "nyc3", "")),
        ("size list --no-header", (0, "s-1vcpu-1gb", "")),
        ("monitoring alert list", (0, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Test 4 FAILED: Cannot query images" in out
    # Test 4 failures are never added to the printed "Issues to Fix" list.
    assert "Issues to Fix" not in out


def test_run_tests_regions_or_sizes_fail_test5_only(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "111\tk", "")),
        ("image list --public", (0, "ubuntu-22-04-x64", "")),
        ("region list --no-header", (1, "", "")),
        ("size list --no-header", (0, "s-1vcpu-1gb", "")),
        ("monitoring alert list", (0, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Test 5 FAILED: Cannot query regions/sizes" in out


def test_run_tests_monitoring_api_failure_never_fails_overall(monkeypatch, capsys):
    # Test 6 always counts as a pass (tests_passed += 1 even in its "else"
    # branch), so a monitoring-API failure alone can never make run_tests
    # return non-zero.
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl version", (0, "v", "")),
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "111\tk", "")),
        ("image list --public", (0, "ubuntu-22-04-x64", "")),
        ("region list --no-header", (0, "nyc3", "")),
        ("size list --no-header", (0, "s-1vcpu-1gb", "")),
        ("monitoring alert list", (1, "", "")),
    ]))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Test 6 WARNING: Monitoring API access limited" in out
    assert "All tests passed! Ready for droplet creation." in out


# --------------------------------------------------------------------------
# troubleshoot
# --------------------------------------------------------------------------

def test_troubleshoot_no_info_file_only_checks_auth_and_ssh(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Authentication: OK" in out
    assert "SSH keys: OK" in out
    assert "No issues found! ✅" in out
    assert "Checking droplet accessibility" not in out


def test_troubleshoot_auth_failure_reports_issue_and_fix(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (1, "", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Issue: Not authenticated" in out
    assert "Fix: Run 'doctl auth init' and enter your API token" in out
    assert "Found 1 issue(s):" in out


def test_troubleshoot_no_ssh_keys_reports_issue_and_fix(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (1, "", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Issue: No SSH keys found" in out
    assert "Fix: Generate SSH key and add to DigitalOcean:" in out


def test_troubleshoot_with_info_file_fully_healthy(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
        ("Status,PublicIPv4 --no-header", (0, "active 203.0.113.45", "")),
        ("echo OK", (0, "OK", "")),
        ("Features", (0, "monitoring", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet active: 203.0.113.45" in out
    assert "SSH connectivity: OK" in out
    assert "Monitoring: OK" in out
    assert "No issues found! ✅" in out


def test_troubleshoot_droplet_not_active_reports_issue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
        ("Status,PublicIPv4 --no-header", (0, "new 1.2.3.4", "")),
        ("Features", (0, "monitoring", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Issue: Droplet status is new 1.2.3.4" in out
    assert "Fix: Wait for droplet to finish booting, or recreate" in out


def test_troubleshoot_ssh_connection_fails_reports_issue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
        ("Status,PublicIPv4 --no-header", (0, "active 1.2.3.4", "")),
        ("echo OK", (1, "", "")),
        ("Features", (0, "monitoring", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Issue: Cannot SSH to droplet" in out
    assert "Possible fixes:" in out


def test_troubleshoot_droplet_get_failure_is_silently_skipped(tmp_path, monkeypatch, capsys):
    # FIXED: when the droplet-accessibility `droplet get` call itself fails
    # (code != 0), the new `else` branch now records and reports the
    # failure instead of silently skipping it.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
        ("Status,PublicIPv4 --no-header", (1, "", "")),
        ("Features", (0, "monitoring", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Droplet active:" not in out
    assert "Droplet status is" not in out
    assert "Issue: Failed to query droplet status via doctl" in out
    assert "Fix: Verify droplet ID is correct and doctl is authenticated" in out
    assert "• Could not query droplet status" in out


def test_troubleshoot_monitoring_check_failure_still_reports_ok_bug(tmp_path, monkeypatch, capsys):
    # FIXED: the monitoring-status check is now a 3-way branch. When the
    # Features lookup itself fails (code != 0), it no longer falls through
    # to "Monitoring: OK" -- it reports that the check could not be
    # performed, and this is not counted as an issue either.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
        ("Status,PublicIPv4 --no-header", (0, "active 1.2.3.4", "")),
        ("echo OK", (0, "OK", "")),
        ("Features", (1, "", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Could not verify monitoring status" in out
    assert "Monitoring: OK" not in out


def test_troubleshoot_active_status_with_no_ip_token_crashes_with_indexerror(tmp_path, monkeypatch, capsys):
    # FIXED: `status_line.split()[1]` assuming a second (IP) token no longer
    # raises an uncaught IndexError for a status line of just "active" (no
    # IP). The guarded fallback now reports it as an unexpected status
    # format and troubleshooting continues on to the remaining checks
    # (monitoring) instead of crashing outright.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
        ("Status,PublicIPv4 --no-header", (0, "active", "")),
        ("Features", (0, "monitoring", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Issue: Unexpected droplet status format: active" in out
    assert "Fix: Run 'doctl compute droplet get <id>' manually to inspect output" in out
    assert "Monitoring: OK" in out


def test_troubleshoot_monitoring_not_enabled_reports_issue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("doctl account get", (0, "abc", "")),
        ("ssh-key list --no-header", (0, "1\tk", "")),
        ("Status,PublicIPv4 --no-header", (0, "active 1.2.3.4", "")),
        ("echo OK", (0, "OK", "")),
        ("Features", (0, "backups", "")),
    ]))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Issue: Monitoring not enabled" in out
    assert "Fix: Recreate droplet with --enable-monitoring flag" in out


# --------------------------------------------------------------------------
# cleanup
# --------------------------------------------------------------------------

def test_cleanup_no_info_file_returns_0(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = tool.cleanup(_Args(force=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "No droplet info found. Nothing to clean up." in out


def test_cleanup_force_success_removes_info_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet delete", (0, "", "")),
    ]))
    rc = tool.cleanup(_Args(force=True))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet deleted successfully" in out
    assert "Cleanup complete! ✅" in out
    assert not (tmp_path / INFO_FILE).exists()


def test_cleanup_force_failure_keeps_info_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet delete", (1, "", "access denied")),
    ]))
    rc = tool.cleanup(_Args(force=True))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to delete droplet" in out
    assert "access denied" in out
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


def test_cleanup_prompt_accepted_case_insensitive_yes_proceeds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)
    monkeypatch.setattr(tool, "run_command", make_fake_run_command([
        ("droplet delete", (0, "", "")),
    ]))
    monkeypatch.setattr("builtins.input", lambda prompt="": "YES")

    rc = tool.cleanup(_Args(force=False))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Droplet deleted successfully" in out


def test_cleanup_prompt_short_y_is_rejected_unlike_sibling_skill(tmp_path, monkeypatch, capsys):
    # Behavioral difference from the sibling digitalocean-deploy skill:
    # that one accepts a short "y" as confirmation. This implementation
    # requires the exact word "yes" (case-insensitive); "y" alone cancels.
    monkeypatch.chdir(tmp_path)
    _write_info(tmp_path)

    def fail_if_called(cmd, timeout=300):
        raise AssertionError("should not attempt delete for a bare 'y'")
    monkeypatch.setattr(tool, "run_command", fail_if_called)
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    rc = tool.cleanup(_Args(force=False))

    out = capsys.readouterr().out
    assert rc == 0
    assert "Cleanup cancelled" in out
    assert (tmp_path / INFO_FILE).exists()


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


def test_main_create_droplet_missing_name_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-droplet"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_dispatches_create_droplet_with_defaults(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "create_droplet")
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-droplet", "--name", "d1"])
    rc = tool.main()
    assert rc == 0
    args = captured["called"]
    assert args.name == "d1"
    assert args.image == "ubuntu-22-04-x64"
    assert args.region == "nyc3"
    assert args.size == "s-1vcpu-1gb"
    assert args.enable_monitoring is False
    assert args.enable_ipv6 is False
    assert args.enable_backups is False
    assert args.vpc_uuid is None
    assert args.user_data is None


def test_main_dispatches_create_droplet_with_all_flags(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "create_droplet")
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "create-droplet", "--name", "prod",
        "--image", "debian-12-x64", "--region", "sfo3", "--size", "s-2vcpu-4gb",
        "--enable-monitoring", "--enable-ipv6", "--enable-backups",
        "--vpc-uuid", "vpc-1", "--user-data", "cloud-init.yml",
    ])
    rc = tool.main()
    assert rc == 0
    args = captured["called"]
    assert args.image == "debian-12-x64"
    assert args.region == "sfo3"
    assert args.size == "s-2vcpu-4gb"
    assert args.enable_monitoring is True
    assert args.enable_ipv6 is True
    assert args.enable_backups is True
    assert args.vpc_uuid == "vpc-1"
    assert args.user_data == "cloud-init.yml"


def test_main_deploy_app_missing_method_exits(monkeypatch):
    # --method is required=True in this implementation (unlike the sibling
    # skill, where it defaults to "docker").
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy-app"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_deploy_app_invalid_method_choice_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy-app", "--method", "ftp"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_dispatches_deploy_app_with_options(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "deploy_app")
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "deploy-app", "--method", "docker",
        "--image", "nginx:latest", "--port", "9000", "--deploy-script", "run.sh",
    ])
    rc = tool.main()
    assert rc == 0
    args = captured["called"]
    assert args.method == "docker"
    assert args.image == "nginx:latest"
    assert args.port == 9000
    assert args.deploy_script == "run.sh"


def test_main_dispatches_deploy_app_default_port_80(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "deploy_app")
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy-app", "--method", "git", "--repo", "x"])
    rc = tool.main()
    assert rc == 0
    assert captured["called"].port == 80


def test_main_dispatches_configure_monitoring(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "configure_monitoring")
    monkeypatch.setattr(sys, "argv", [
        "tool.py", "configure-monitoring", "--enable-cpu-alert",
        "--enable-memory-alert", "--enable-disk-alert", "--alert-email", "a@b.com",
    ])
    rc = tool.main()
    assert rc == 0
    args = captured["called"]
    assert args.enable_cpu_alert is True
    assert args.enable_memory_alert is True
    assert args.enable_disk_alert is True
    assert args.alert_email == "a@b.com"


def test_main_dispatches_health_check_with_port(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "health_check")
    monkeypatch.setattr(sys, "argv", ["tool.py", "health-check", "--port", "8080"])
    rc = tool.main()
    assert rc == 0
    assert captured["called"].port == 8080


def test_main_dispatches_health_check_no_port_defaults_none(monkeypatch):
    captured = _stub_dispatch(monkeypatch, "health_check")
    monkeypatch.setattr(sys, "argv", ["tool.py", "health-check"])
    rc = tool.main()
    assert rc == 0
    assert captured["called"].port is None


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
    assert "Checking Prerequisites" in result.stdout


def test_subprocess_no_args_exits_nonzero(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(tmp_path), capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "usage" in result.stdout.lower()
