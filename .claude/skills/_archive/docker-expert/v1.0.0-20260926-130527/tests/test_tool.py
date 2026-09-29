import importlib.util as _ilu
from pathlib import Path
import subprocess as _subprocess_mod
import sys as _sys
import pytest
import runpy

_TOOL_PATH = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"

_spec = _ilu.spec_from_file_location("docker_expert_tool", _TOOL_PATH)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _fake_run_command(responses, default=(0, "", "")):
    """Build a run_command stand-in that matches by substring, in order."""
    def _runner(cmd, timeout=300):
        for key, val in responses:
            if key in cmd:
                return val
        return default
    return _runner


# ---------------------------------------------------------------------------
# print_* helpers - genuine content assertions (symbols + message pass-through)
# ---------------------------------------------------------------------------

def test_print_success_uses_check_symbol(capsys):
    tool.print_success("all good")
    out = capsys.readouterr().out
    assert "✓" in out
    assert "all good" in out


def test_print_error_uses_cross_symbol(capsys):
    tool.print_error("bad thing")
    out = capsys.readouterr().out
    assert "✗" in out
    assert "bad thing" in out


def test_print_warning_uses_warning_symbol(capsys):
    tool.print_warning("careful")
    out = capsys.readouterr().out
    assert "⚠" in out
    assert "careful" in out


def test_print_info_uses_info_symbol(capsys):
    tool.print_info("fyi")
    out = capsys.readouterr().out
    assert "ℹ" in out
    assert "fyi" in out


def test_print_header_includes_arrow_and_message(capsys):
    tool.print_header("Section Title")
    out = capsys.readouterr().out
    assert "==>" in out
    assert "Section Title" in out


# ---------------------------------------------------------------------------
# run_command - real subprocess exercised directly (no docker involved)
# ---------------------------------------------------------------------------

def test_run_command_success_returns_stdout():
    code, out, err = tool.run_command("echo hello")
    assert code == 0
    assert out.strip() == "hello"


def test_run_command_nonzero_exit_returns_code():
    code, out, err = tool.run_command("python3 -c \"import sys; sys.exit(3)\"")
    assert code == 3


def test_run_command_stderr_is_captured():
    code, out, err = tool.run_command("python3 -c \"import sys; sys.stderr.write('oops'); sys.exit(2)\"")
    assert code == 2
    assert "oops" in err


def test_run_command_timeout_expired(monkeypatch):
    def _raise_timeout(*a, **kw):
        raise _subprocess_mod.TimeoutExpired(cmd="sleep", timeout=1)

    monkeypatch.setattr(tool.subprocess, "run", _raise_timeout)
    code, out, err = tool.run_command("sleep 5", timeout=1)
    assert code == 1
    assert out == ""
    assert "timed out after 1s" in err


def test_run_command_generic_exception_handled(monkeypatch):
    def _raise(*a, **kw):
        raise OSError("boom")

    monkeypatch.setattr(tool.subprocess, "run", _raise)
    code, out, err = tool.run_command("whatever")
    assert code == 1
    assert out == ""
    assert err == "boom"


def test_run_command_uses_shell_and_default_timeout(monkeypatch):
    captured = {}

    class _Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(cmd, shell, capture_output, text, timeout):
        captured['cmd'] = cmd
        captured['shell'] = shell
        captured['timeout'] = timeout
        return _Result()

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("docker info")
    assert captured['cmd'] == "docker info"
    assert captured['shell'] is True
    assert captured['timeout'] == 300
    assert code == 0 and out == "ok"


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

def test_check_prerequisites_all_present_returns_0(monkeypatch, capsys):
    responses = [
        ("docker --version", (0, "Docker version 24.0.0", "")),
        ("docker info", (0, "", "")),
        ("docker compose version", (0, "Docker Compose version v2.20", "")),
        ("docker buildx version", (0, "github.com/docker/buildx v0.11", "")),
    ]
    monkeypatch.setattr(tool, "run_command", _fake_run_command(responses))
    rc = tool.check_prerequisites(_Args())
    assert rc == 0
    assert "All Docker prerequisites satisfied" in capsys.readouterr().out


def test_check_prerequisites_missing_docker_falls_back_to_legacy_compose(monkeypatch, capsys):
    responses = [
        ("docker --version", (1, "", "not found")),
        ("docker info", (1, "", "cannot connect")),
        ("docker compose version", (1, "", "not found")),
        ("docker-compose --version", (0, "docker-compose version 1.29", "")),
        ("docker buildx version", (1, "", "not found")),
    ]
    monkeypatch.setattr(tool, "run_command", _fake_run_command(responses))
    rc = tool.check_prerequisites(_Args())
    assert rc == 1
    out = capsys.readouterr().out
    assert "Docker" in out
    assert "Docker daemon" in out
    assert "Legacy docker-compose found" in out


def test_check_prerequisites_missing_compose_entirely(monkeypatch, capsys):
    responses = [
        ("docker --version", (0, "Docker version X", "")),
        ("docker info", (0, "", "")),
        ("docker compose version", (1, "", "")),
        ("docker-compose --version", (1, "", "")),
        ("docker buildx version", (0, "buildx", "")),
    ]
    monkeypatch.setattr(tool, "run_command", _fake_run_command(responses))
    rc = tool.check_prerequisites(_Args())
    assert rc == 1
    out = capsys.readouterr().out
    assert "Missing requirements" in out
    assert "Docker Compose" in out


def test_check_prerequisites_buildkit_missing_is_only_a_warning(monkeypatch, capsys):
    responses = [
        ("docker --version", (0, "Docker version X", "")),
        ("docker info", (0, "", "")),
        ("docker compose version", (0, "Docker Compose version v2", "")),
        ("docker buildx version", (1, "", "not found")),
    ]
    monkeypatch.setattr(tool, "run_command", _fake_run_command(responses))
    rc = tool.check_prerequisites(_Args())
    assert rc == 0
    out = capsys.readouterr().out
    assert "Docker BuildKit not available" in out
    assert "All Docker prerequisites satisfied" in out


# ---------------------------------------------------------------------------
# build_image
# ---------------------------------------------------------------------------

def test_build_image_missing_dockerfile_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    args = _Args(image_name="myapp:latest", dockerfile=None, context=None, target=None,
                 build_args=None, no_cache=False)
    rc = tool.build_image(args)
    assert rc == 1
    assert "Dockerfile not found" in capsys.readouterr().out


def test_build_image_builds_full_command_and_reports_size(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM alpine\n")
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        if cmd.startswith("DOCKER_BUILDKIT=1 docker build"):
            return (0, "", "")
        if "docker images" in cmd and "--format" in cmd:
            return (0, "150MB", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(image_name="myapp:latest", dockerfile=None, context=None, target="production",
                 build_args="KEY=VAL,KEY2=VAL2", no_cache=True)
    rc = tool.build_image(args)
    assert rc == 0
    build_cmd = calls[0]
    assert "-f Dockerfile -t myapp:latest" in build_cmd
    assert "--build-arg KEY=VAL" in build_cmd
    assert "--build-arg KEY2=VAL2" in build_cmd
    assert "--target production" in build_cmd
    assert "--no-cache" in build_cmd
    assert build_cmd.strip().endswith(".")
    assert "Image size: 150MB" in capsys.readouterr().out


def test_build_image_failure_returns_1_and_prints_stderr(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM alpine\n")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", "build error XYZ"))
    args = _Args(image_name="myapp:latest", dockerfile=None, context=None, target=None,
                 build_args=None, no_cache=False)
    rc = tool.build_image(args)
    assert rc == 1
    assert "build error XYZ" in capsys.readouterr().out


def test_build_image_custom_context_and_dockerfile_no_extra_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Dockerfile.prod").write_text("FROM alpine\n")
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(image_name="x:1", dockerfile="Dockerfile.prod", context="./app", target=None,
                 build_args=None, no_cache=False)
    tool.build_image(args)
    assert "-f Dockerfile.prod" in calls[0]
    assert calls[0].strip().endswith("./app")
    assert "--no-cache" not in calls[0]
    assert "--target" not in calls[0]
    assert "--build-arg" not in calls[0]


def test_build_image_size_lookup_failure_skips_size_line(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM alpine\n")

    def fake(cmd, timeout=300):
        if "docker images" in cmd:
            return (1, "", "no such image")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(image_name="myapp:latest", dockerfile=None, context=None, target=None,
                 build_args=None, no_cache=False)
    rc = tool.build_image(args)
    assert rc == 0
    assert "Image size" not in capsys.readouterr().out


# ---------------------------------------------------------------------------
# run_container
# ---------------------------------------------------------------------------

def _run_container_args(**overrides):
    base = dict(image_name="myapp:latest", container_name="c1", ports=None, volumes=None,
                env=None, env_file=None, network=None, restart=None, memory=None, cpus=None,
                override_command=None)
    base.update(overrides)
    return _Args(**base)


def test_run_container_image_not_found_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    rc = tool.run_container(_run_container_args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Image not found" in out
    # Fixed bug: the "build the image first" hint is now an f-string, so it
    # interpolates the actual image name instead of printing a literal
    # "{args.image_name}" placeholder.
    assert "{args.image_name}" not in out
    assert "Build the image first: python3 tool.py build-image --image-name myapp:latest" in out


def test_run_container_image_found_ignores_nonzero_exit_code_when_stdout_present(monkeypatch):
    # Real behavior: only stdout emptiness gates the "not found" check,
    # the exit code of `docker images -q` is not consulted.
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        if cmd.startswith("docker images -q"):
            return (1, "abc123", "")
        return (0, "runid", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.run_container(_run_container_args())
    assert rc == 0


def test_run_container_builds_full_command_and_succeeds(monkeypatch, capsys):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        if cmd.startswith("docker images -q"):
            return (0, "abc123imageid", "")
        if cmd.startswith("docker run"):
            return (0, "deadbeefcafedeadbeefcafedeadbeefcafedeadbeefcafedeadbeefcafe", "")
        if cmd.startswith("docker ps --filter"):
            return (0, "CONTAINER STATUS", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    args = _run_container_args(container_name="myapp-c", ports="8080:80,443:443",
                                volumes="/host:/container", env_file=".env", network="mynet",
                                memory="512m", cpus="0.5", override_command="node app.js")
    rc = tool.run_container(args)
    assert rc == 0
    run_cmd = [c for c in calls if c.startswith("docker run")][0]
    assert "--name myapp-c" in run_cmd
    assert "-p 8080:80" in run_cmd and "-p 443:443" in run_cmd
    assert "-v /host:/container" in run_cmd
    assert "--env-file .env" in run_cmd
    assert "--network mynet" in run_cmd
    assert "--restart unless-stopped" in run_cmd
    assert "--memory 512m" in run_cmd
    assert "--cpus 0.5" in run_cmd
    assert run_cmd.strip().endswith("node app.js")
    out = capsys.readouterr().out
    assert "Container started: deadbeefcafe" in out


def test_run_container_uses_env_list_when_no_env_file(monkeypatch):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        if cmd.startswith("docker images -q"):
            return (0, "abc123", "")
        if cmd.startswith("docker run"):
            return (0, "cid", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    args = _run_container_args(env="A=1,B=2", env_file=None)
    tool.run_container(args)
    run_cmd = [c for c in calls if c.startswith("docker run")][0]
    assert "-e A=1" in run_cmd
    assert "-e B=2" in run_cmd
    assert "--env-file" not in run_cmd


def test_run_container_no_name_no_extras_uses_defaults(monkeypatch):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        if cmd.startswith("docker images -q"):
            return (0, "abc123", "")
        if cmd.startswith("docker run"):
            return (0, "cid", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    args = _run_container_args(container_name=None, restart="always")
    tool.run_container(args)
    run_cmd = [c for c in calls if c.startswith("docker run")][0]
    assert "--name" not in run_cmd
    assert "--restart always" in run_cmd
    assert "-p" not in run_cmd
    assert "-v" not in run_cmd
    assert "--memory" not in run_cmd
    assert "--cpus" not in run_cmd


def test_run_container_run_command_failure_returns_1(monkeypatch, capsys):
    def fake(cmd, timeout=300):
        if cmd.startswith("docker images -q"):
            return (0, "abc123", "")
        if cmd.startswith("docker run"):
            return (1, "", "port already in use")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.run_container(_run_container_args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Container failed to start" in out
    assert "port already in use" in out


# ---------------------------------------------------------------------------
# compose_up
# ---------------------------------------------------------------------------

def test_compose_up_missing_file_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    args = _Args(compose_file=None, build=False, remove_orphans=False)
    rc = tool.compose_up(args)
    assert rc == 1
    assert "Compose file not found" in capsys.readouterr().out


def test_compose_up_with_build_and_remove_orphans(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        if "ps" in cmd:
            return (0, "app  Up", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(compose_file=None, build=True, remove_orphans=True)
    rc = tool.compose_up(args)
    assert rc == 0
    up_cmd = calls[0]
    assert "up -d --build" in up_cmd
    assert "--remove-orphans" in up_cmd
    assert "Compose application started" in capsys.readouterr().out


def test_compose_up_without_build_uses_plain_up(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(compose_file=None, build=False, remove_orphans=False)
    tool.compose_up(args)
    assert "up -d --build" not in calls[0]
    assert "up -d" in calls[0]
    assert "--remove-orphans" not in calls[0]


def test_compose_up_custom_file_and_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "custom.yml").write_text("services: {}\n")
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", "compose broke"))
    args = _Args(compose_file="custom.yml", build=False, remove_orphans=False)
    rc = tool.compose_up(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "Compose failed" in out
    assert "compose broke" in out
    assert "custom.yml" in out


# ---------------------------------------------------------------------------
# optimize
# ---------------------------------------------------------------------------

def test_optimize_missing_dockerfile_returns_1(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    args = _Args(dockerfile=None)
    rc = tool.optimize(args)
    assert rc == 1
    assert "Dockerfile not found" in capsys.readouterr().out


def test_optimize_single_stage_recommends_multistage(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dockerignore").write_text("node_modules\n")
    (tmp_path / "Dockerfile").write_text(
        "FROM node:18-alpine\nWORKDIR /app\nUSER node\nCOPY . .\n"
    )
    rc = tool.optimize(_Args(dockerfile=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Consider using multi-stage builds" in out
    assert "No critical issues found" in out


def test_optimize_multistage_and_all_good_has_no_issues(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dockerignore").write_text("node_modules\n")
    (tmp_path / "Dockerfile").write_text(
        "FROM node:18-alpine AS build\n"
        "WORKDIR /app\n"
        "RUN apt-get update\n"
        "RUN apt-get install --no-install-recommends -y curl\n"
        "COPY . .\n"
        "FROM node:18-alpine\n"
        "WORKDIR /app\n"
        "USER node\n"
        "COPY --from=build /app /app\n"
    )
    rc = tool.optimize(_Args(dockerfile=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Using multi-stage build" in out
    assert ".dockerignore file exists" in out
    assert "Using non-root user" in out
    assert "Using WORKDIR" in out
    assert "No critical issues found" in out
    # apt-get install line already has --no-install-recommends and update is
    # combined in the same RUN, so neither apt issue should be raised.
    assert "Add --no-install-recommends" not in out
    assert "Combine apt-get update" not in out


def test_optimize_apt_get_issues_report_correct_line_numbers(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dockerignore").write_text("x\n")
    (tmp_path / "Dockerfile").write_text(
        "FROM node:18-alpine\n"
        "RUN apt-get update && apt-get install -y curl\n"
        "USER node\n"
        "WORKDIR /app\n"
    )
    rc = tool.optimize(_Args(dockerfile=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Line 2: Add --no-install-recommends to apt-get install" in out
    assert "Line 2: Combine apt-get update && apt-get install in single RUN" in out


def test_optimize_add_without_tar_recommends_copy(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dockerignore").write_text("x\n")
    (tmp_path / "Dockerfile").write_text(
        "FROM node:18-alpine\nADD app.js /app/app.js\nUSER node\nWORKDIR /app\n"
    )
    rc = tool.optimize(_Args(dockerfile=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Use COPY instead of ADD" in out


def test_optimize_add_with_tar_does_not_recommend_copy(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dockerignore").write_text("x\n")
    (tmp_path / "Dockerfile").write_text(
        "FROM node:18-alpine\nADD app.tar.gz /app\nUSER node\nWORKDIR /app\n"
    )
    rc = tool.optimize(_Args(dockerfile=None))
    out = capsys.readouterr().out
    # The static "Docker Best Practices" footer always prints a generic
    # "Use COPY instead of ADD" bullet, so check the specific recommendation
    # text instead, which only fires for ADD without a .tar archive.
    assert "Use COPY instead of ADD (unless extracting archives)" not in out


def test_optimize_missing_dockerignore_and_user_and_workdir(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Dockerfile").write_text("FROM node:18-alpine\nCOPY . .\n")
    rc = tool.optimize(_Args(dockerfile=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Missing .dockerignore file" in out
    assert "Running as root user (security risk)" in out
    assert "Use WORKDIR instead of cd commands" in out


def test_optimize_latest_tag_and_missing_tag_flagged(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".dockerignore").write_text("x\n")
    (tmp_path / "Dockerfile").write_text(
        "FROM node:latest AS build\n"
        "USER node\n"
        "WORKDIR /app\n"
        "FROM ubuntu\n"
    )
    rc = tool.optimize(_Args(dockerfile=None))
    out = capsys.readouterr().out
    assert "Using :latest tag: FROM node:latest AS build" in out
    assert "Using :latest tag: FROM ubuntu" in out
    assert "Pin specific image versions" in out


def test_optimize_custom_dockerfile_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "Dockerfile.dev").write_text("FROM alpine:3.18\nUSER app\nWORKDIR /x\n")
    (tmp_path / ".dockerignore").write_text("x\n")
    rc = tool.optimize(_Args(dockerfile="Dockerfile.dev"))
    assert rc == 0


# ---------------------------------------------------------------------------
# run_tests (the `test` subcommand)
# ---------------------------------------------------------------------------

def test_run_tests_all_pass_returns_0(monkeypatch, capsys):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        return (0, "ok", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Total tests: 6" in out
    assert "Passed: 6" in out
    assert "Failed: 0" in out
    assert "All Docker tests passed" in out
    # image-pull cleanup should have been attempted
    assert any("docker rmi hello-world:latest" in c for c in calls)


def test_run_tests_all_fail_returns_1_and_lists_issues(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", "err"))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Total tests: 6" in out
    assert "Passed: 0" in out
    assert "Failed: 6" in out
    assert "Docker not installed" in out
    assert "Cannot pull images from Docker Hub" in out


def test_run_tests_partial_failure_compose_missing(monkeypatch, capsys):
    responses = [
        ("docker --version", (0, "v", "")),
        ("docker info", (0, "", "")),
        ("docker compose version", (1, "", "")),
        ("docker network ls", (0, "", "")),
        ("docker volume ls", (0, "", "")),
        ("docker pull", (0, "", "")),
    ]
    monkeypatch.setattr(tool, "run_command", _fake_run_command(responses))
    rc = tool.run_tests(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Passed: 5" in out
    assert "Failed: 1" in out
    assert "Docker Compose not available" in out


# ---------------------------------------------------------------------------
# troubleshoot
# ---------------------------------------------------------------------------

def test_troubleshoot_no_issues_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (0, "", ""))
    rc = tool.troubleshoot(_Args(auto_fix=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "No issues found - Docker is healthy" in out


def test_troubleshoot_daemon_not_running(monkeypatch, capsys):
    def fake(cmd, timeout=300):
        if cmd == "docker info":
            return (1, "", "cannot connect")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.troubleshoot(_Args(auto_fix=False))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Docker daemon not running" in out
    assert "Start Docker Desktop" in out


def test_troubleshoot_reclaimable_space_warns_without_adding_issue(monkeypatch, capsys):
    def fake(cmd, timeout=300):
        if cmd == "docker system df":
            return (0, "TYPE  SIZE  RECLAIMABLE\nImages 1GB 500MB (50%)", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.troubleshoot(_Args(auto_fix=False))
    out = capsys.readouterr().out
    # reclaimable space alone does not count as an "issue" for return code
    assert rc == 0
    assert "Reclaimable space available" in out


def test_troubleshoot_counts_dangling_images_and_recommends_fix(monkeypatch, capsys):
    def fake(cmd, timeout=300):
        if "dangling=true' -q" in cmd:
            return (0, "id1\nid2\nid3", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.troubleshoot(_Args(auto_fix=False))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Found 3 dangling images" in out
    assert "docker image prune -f" in out


def test_troubleshoot_counts_stopped_containers(monkeypatch, capsys):
    def fake(cmd, timeout=300):
        if "status=exited" in cmd:
            return (0, "c1\nc2", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.troubleshoot(_Args(auto_fix=False))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Found 2 stopped containers" in out
    assert "docker container prune -f" in out


def test_troubleshoot_counts_unused_networks(monkeypatch, capsys):
    def fake(cmd, timeout=300):
        if cmd.startswith("docker network ls --filter"):
            return (0, "net1", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.troubleshoot(_Args(auto_fix=False))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Found 1 unused networks" in out
    assert "docker network prune -f" in out


def test_troubleshoot_counts_unused_volumes(monkeypatch, capsys):
    def fake(cmd, timeout=300):
        if cmd.startswith("docker volume ls -qf"):
            return (0, "vol1\nvol2\nvol3\nvol4", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.troubleshoot(_Args(auto_fix=False))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Found 4 unused volumes" in out
    assert "docker volume prune -f" in out


def test_troubleshoot_auto_fix_runs_system_prune(monkeypatch, capsys):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        if "status=exited" in cmd:
            return (0, "c1", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.troubleshoot(_Args(auto_fix=True))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Auto-fix applied" in out
    assert any(c == "docker system prune -f" for c in calls)


def test_troubleshoot_no_auto_fix_does_not_run_system_prune(monkeypatch):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        if "status=exited" in cmd:
            return (0, "c1", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    tool.troubleshoot(_Args(auto_fix=False))
    assert not any(c == "docker system prune -f" for c in calls)


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

def test_cleanup_force_skips_prompt_and_uses_f_flag(monkeypatch, capsys):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        return (0, "cleaned up", "")

    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.cleanup(_Args(all=False, force=True))
    out = capsys.readouterr().out
    assert rc == 0
    prune_cmd = [c for c in calls if "prune" in c][0]
    assert prune_cmd == "docker system prune --volumes -f"
    assert "Cleanup complete" in out


def test_cleanup_all_flag_builds_prune_dash_a(monkeypatch):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    tool.cleanup(_Args(all=True, force=True))
    prune_cmd = [c for c in calls if "prune" in c][0]
    assert prune_cmd == "docker system prune -a --volumes -f"


def test_cleanup_all_no_force_warns_about_all_images_then_cancels(monkeypatch, capsys):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")
    rc = tool.cleanup(_Args(all=True, force=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "All unused images (not just dangling)" in out
    assert not any("prune" in c for c in calls)


def test_cleanup_prompt_declined_cancels(monkeypatch, capsys):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")
    rc = tool.cleanup(_Args(all=False, force=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cleanup cancelled" in out
    assert not any("prune" in c for c in calls)


def test_cleanup_prompt_accepted_short_form_proceeds(monkeypatch, capsys):
    calls = []

    def fake(cmd, timeout=300):
        calls.append(cmd)
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")
    rc = tool.cleanup(_Args(all=False, force=False))
    assert rc == 0
    assert any("prune" in c for c in calls)


def test_cleanup_failure_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", lambda cmd, timeout=300: (1, "", "cleanup boom"))
    rc = tool.cleanup(_Args(all=False, force=True))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Cleanup failed" in out
    assert "cleanup boom" in out


# ---------------------------------------------------------------------------
# main() - CLI dispatch layer
# ---------------------------------------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def _assert_main_dispatches(monkeypatch, cli_name, func_name):
    called = {}

    def fake(args):
        called['args'] = args
        return 42

    monkeypatch.setattr(tool, func_name, fake)
    monkeypatch.setattr(_sys, "argv", ["tool.py", cli_name])
    rc = tool.main()
    assert rc == 42
    assert 'args' in called


def test_main_dispatches_check_prerequisites(monkeypatch):
    _assert_main_dispatches(monkeypatch, "check-prerequisites", "check_prerequisites")


def test_main_dispatches_compose_up(monkeypatch):
    _assert_main_dispatches(monkeypatch, "compose-up", "compose_up")


def test_main_dispatches_test_subcommand(monkeypatch):
    _assert_main_dispatches(monkeypatch, "test", "run_tests")


def test_main_dispatches_troubleshoot(monkeypatch):
    _assert_main_dispatches(monkeypatch, "troubleshoot", "troubleshoot")


def test_main_dispatches_cleanup(monkeypatch):
    _assert_main_dispatches(monkeypatch, "cleanup", "cleanup")


def test_main_dispatches_build_image_with_required_arg(monkeypatch):
    called = {}

    def fake(args):
        called['image_name'] = args.image_name
        return 0

    monkeypatch.setattr(tool, "build_image", fake)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "build-image", "--image-name", "app:1"])
    rc = tool.main()
    assert rc == 0
    assert called['image_name'] == "app:1"


def test_main_run_container_command_option_no_longer_collides_with_dispatch(monkeypatch):
    # Fixed bug: run_parser's own "--command" option (the container command
    # override) used to share its attribute name with the top-level
    # subparsers dest="command" used for dispatch, so passing --command
    # clobbered args.command right after it was set to "run-container" and
    # broke dispatch. The option's dest is now "override_command", so
    # args.command still holds "run-container" and main() correctly
    # dispatches to run_container even when --command is passed.
    called = {}

    def fake(args):
        called['image_name'] = args.image_name
        called['override_command'] = args.override_command
        return 0

    monkeypatch.setattr(tool, "run_container", fake)
    monkeypatch.setattr(
        _sys, "argv",
        ["tool.py", "run-container", "--image-name", "app:1", "--command", "echo hi"],
    )
    rc = tool.main()
    assert rc == 0
    assert called == {"image_name": "app:1", "override_command": "echo hi"}


def test_main_run_container_with_command_dispatches_and_builds_docker_command(monkeypatch):
    # Regression test: calling main() with a real run-container invocation
    # that includes --command must dispatch to run_container (not fall
    # through to the "no command" branch / raise a KeyError on
    # commands[args.command]) and the docker run command it builds must
    # include the overridden command.
    def fake_run_command(cmd, timeout=300):
        if cmd.startswith("docker images -q"):
            return (0, "abc123imageid", "")
        if cmd.startswith("docker run"):
            return (0, "deadbeefcafe", "")
        return (0, "", "")

    calls = []

    def recording_run_command(cmd, timeout=300):
        calls.append(cmd)
        return fake_run_command(cmd, timeout=timeout)

    monkeypatch.setattr(tool, "run_command", recording_run_command)
    monkeypatch.setattr(
        _sys, "argv",
        ["tool.py", "run-container", "--image-name", "x", "--container-name", "y",
         "--command", "echo hello"],
    )
    rc = tool.main()
    assert rc == 0
    run_cmd = [c for c in calls if c.startswith("docker run")][0]
    assert "echo hello" in run_cmd
    assert run_cmd.strip().endswith("echo hello")


def test_main_dispatches_optimize_with_dockerfile_option(monkeypatch):
    called = {}

    def fake(args):
        called['dockerfile'] = args.dockerfile
        return 0

    monkeypatch.setattr(tool, "optimize", fake)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "optimize", "--dockerfile", "Dockerfile.x"])
    rc = tool.main()
    assert rc == 0
    assert called['dockerfile'] == "Dockerfile.x"


def test_main_build_image_missing_required_arg_exits(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "build-image"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 2
    assert "required" in capsys.readouterr().err.lower()


def test_main_run_container_missing_required_arg_exits(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "run-container"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 2


def test_main_unknown_command_exits_with_argparse_error(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "not-a-real-command"])
    with pytest.raises(SystemExit) as excinfo:
        tool.main()
    assert excinfo.value.code == 2


def test_main_troubleshoot_auto_fix_flag_parsed(monkeypatch):
    called = {}

    def fake(args):
        called['auto_fix'] = args.auto_fix
        return 0

    monkeypatch.setattr(tool, "troubleshoot", fake)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "troubleshoot", "--auto-fix"])
    tool.main()
    assert called['auto_fix'] is True


def test_main_cleanup_all_and_force_flags_parsed(monkeypatch):
    called = {}

    def fake(args):
        called['all'] = args.all
        called['force'] = args.force
        return 0

    monkeypatch.setattr(tool, "cleanup", fake)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "cleanup", "--all", "--force"])
    tool.main()
    assert called['all'] is True
    assert called['force'] is True


# ---------------------------------------------------------------------------
# Real subprocess smoke tests of the __main__ entrypoint (no docker involved)
# ---------------------------------------------------------------------------

def test_cli_entrypoint_no_args_exits_1():
    result = _subprocess_mod.run(
        [_sys.executable, str(_TOOL_PATH)],
        capture_output=True, text=True, timeout=30,
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


def test_cli_entrypoint_build_image_missing_required_exits_2():
    result = _subprocess_mod.run(
        [_sys.executable, str(_TOOL_PATH), "build-image"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
    assert "--image-name" in result.stderr


# ---------------------------------------------------------------------------
# __main__ guard - executed in-process (via runpy) so it is coverage-visible
# ---------------------------------------------------------------------------

def test_dunder_main_guard_calls_main_and_exits_with_its_return_code(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(_TOOL_PATH), run_name="__main__")
    assert excinfo.value.code == 1
