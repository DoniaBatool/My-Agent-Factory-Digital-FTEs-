import json
import subprocess
import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("aws_eks_deploy_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


class _Args:
    """Minimal stand-in for an argparse.Namespace."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Router:
    """Fake for tool.run_command: routes on a substring match against the
    command string (first match wins), falling back to `fallback` (another
    callable with the same signature) or a fixed `default` tuple. Records
    every command it was asked to run so tests can assert on call shape."""
    def __init__(self, rules=None, fallback=None, default=(0, "", "")):
        self.rules = list(rules or [])
        self.fallback = fallback
        self.default = default
        self.calls = []

    def __call__(self, cmd, capture_output=True, timeout=300):
        self.calls.append(cmd)
        for substr, result in self.rules:
            if substr in cmd:
                return result
        if self.fallback is not None:
            return self.fallback(cmd, capture_output=capture_output, timeout=timeout)
        return self.default


def _prereq_fake(which_ok=("aws", "kubectl", "eksctl", "docker"), aws_creds_ok=True):
    """A realistic run_command fake for check_prerequisites: every command
    the real function issues gets a plausible, non-empty answer so downstream
    string parsing (e.g. `stdout.strip().split()[0]`) never chokes on an
    empty default."""
    which_ok = set(which_ok)

    def fake(cmd, capture_output=True, timeout=300):
        if cmd.startswith("which "):
            name = cmd.split()[1]
            return (0, f"/usr/bin/{name}", "") if name in which_ok else (1, "", "not found")
        if cmd == "aws --version":
            return (0, "aws-cli/2.15.0 Python/3.11", "")
        if cmd == "aws sts get-caller-identity":
            return (0, "{}", "") if aws_creds_ok else (1, "", "Unable to locate credentials")
        if "kubectl version" in cmd:
            return (0, "Client Version: v1.28.0", "")
        if cmd == "eksctl version":
            return (0, "0.150.0", "")
        if cmd == "docker --version":
            return (0, "Docker version 24.0.0", "")
        return (0, "", "")

    return fake


class _FakeFile:
    """Stand-in for the file object `open(path, 'w')` returns, so tests
    never touch the real filesystem when create_cluster writes its
    eksctl config."""
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def write(self, s):
        self.sink.append(s)


def _no_disk_open(monkeypatch):
    written = []
    monkeypatch.setattr(tool, "open", lambda path, mode="r": _FakeFile(written), raising=False)
    return written


# ---------------------------------------------------------------------------
# print_* helpers
# ---------------------------------------------------------------------------

def test_print_success_includes_message(capsys):
    tool.print_success("cluster ready")
    assert "cluster ready" in capsys.readouterr().out


def test_print_error_includes_message(capsys):
    tool.print_error("boom")
    assert "boom" in capsys.readouterr().out


def test_print_warning_includes_message(capsys):
    tool.print_warning("careful")
    assert "careful" in capsys.readouterr().out


def test_print_info_includes_message(capsys):
    tool.print_info("fyi")
    assert "fyi" in capsys.readouterr().out


def test_print_header_includes_message(capsys):
    tool.print_header("Section")
    assert "Section" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# run_command: the actual subprocess boundary
# ---------------------------------------------------------------------------

class _FakeCompleted:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_command_success_returns_tuple(monkeypatch):
    monkeypatch.setattr(
        tool.subprocess, "run",
        lambda *a, **k: _FakeCompleted(0, "hello\n", ""),
    )
    assert tool.run_command("echo hello") == (0, "hello\n", "")


def test_run_command_forwards_default_capture_output_true(monkeypatch):
    """Kills the mutant that flips run_command's `capture_output: bool = True`
    default to False: without this test, a call site that relies on the
    default (like check_command_exists) would silently start streaming
    subprocess output to the terminal instead of capturing it, and nothing
    would fail."""
    captured = {}

    def fake_run(cmd, shell, capture_output, text, timeout):
        captured.update(cmd=cmd, shell=shell, capture_output=capture_output, text=text, timeout=timeout)
        return _FakeCompleted(0, "", "")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    tool.run_command("echo hi")
    assert captured == {"cmd": "echo hi", "shell": True, "capture_output": True, "text": True, "timeout": 300}


def test_run_command_forwards_explicit_capture_output_false(monkeypatch):
    captured = {}

    def fake_run(cmd, shell, capture_output, text, timeout):
        captured["capture_output"] = capture_output
        return _FakeCompleted(0, "", "")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    tool.run_command("echo hi", capture_output=False, timeout=5)
    assert captured["capture_output"] is False


def test_run_command_timeout_returns_error_tuple(monkeypatch):
    def fake_run(*a, **k):
        raise subprocess.TimeoutExpired(cmd="sleep 100", timeout=7)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("sleep 100", timeout=7)
    assert code == 1
    assert out == ""
    assert "Command timed out after 7 seconds" == err


def test_run_command_generic_exception_returns_error_tuple(monkeypatch):
    def fake_run(*a, **k):
        raise OSError("no such file")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("bogus")
    assert code == 1
    assert out == ""
    assert err == "no such file"


# ---------------------------------------------------------------------------
# check_command_exists
# ---------------------------------------------------------------------------

def test_check_command_exists_true_when_found(monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda cmd, **k: (0, "/usr/bin/aws", ""))
    assert tool.check_command_exists("aws") is True


def test_check_command_exists_false_when_not_found(monkeypatch):
    monkeypatch.setattr(tool, "run_command", lambda cmd, **k: (1, "", ""))
    assert tool.check_command_exists("nope") is False


def test_check_command_exists_builds_which_command(monkeypatch):
    captured = {}

    def fake(cmd, **k):
        captured["cmd"] = cmd
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    tool.check_command_exists("eksctl")
    assert captured["cmd"] == "which eksctl"


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

def test_check_prerequisites_all_good_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _prereq_fake())
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "All prerequisites met" in out


def test_check_prerequisites_aws_missing_returns_1(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(which_ok=("kubectl", "eksctl", "docker")))
    assert tool.check_prerequisites(_Args()) == 1


def test_check_prerequisites_aws_creds_invalid_returns_1(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(aws_creds_ok=False))
    assert tool.check_prerequisites(_Args()) == 1


def test_check_prerequisites_kubectl_missing_returns_1(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(which_ok=("aws", "eksctl", "docker")))
    assert tool.check_prerequisites(_Args()) == 1


def test_check_prerequisites_eksctl_missing_returns_1(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(which_ok=("aws", "kubectl", "docker")))
    assert tool.check_prerequisites(_Args()) == 1


def test_check_prerequisites_docker_missing_is_optional_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(which_ok=("aws", "kubectl", "eksctl")))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Docker not installed (optional)" in out


# ---------------------------------------------------------------------------
# create_cluster
# ---------------------------------------------------------------------------

def test_create_cluster_returns_1_when_prerequisites_fail(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(which_ok=()))
    args = _Args(cluster_name="demo", region="us-east-1", nodes=2, node_type="t3.small",
                 k8s_version="1.28", dry_run=False)
    assert tool.create_cluster(args) == 1


def test_create_cluster_dry_run_writes_config_and_skips_execution(monkeypatch):
    written = _no_disk_open(monkeypatch)
    fake = _prereq_fake()
    calls = []
    monkeypatch.setattr(tool, "run_command", lambda cmd, **k: (calls.append(cmd), fake(cmd, **k))[1])
    args = _Args(cluster_name="demo", region="us-west-2", nodes=2, node_type="t3.small",
                 k8s_version="1.28", dry_run=True)
    rc = tool.create_cluster(args)
    content = "".join(written)
    assert rc == 0
    assert "name: demo" in content
    assert "region: us-west-2" in content
    assert "instanceType: t3.small" in content
    assert "maxSize: 4" in content  # nodes(2) + 2
    assert not any(c.startswith("eksctl create cluster") for c in calls)


def test_create_cluster_full_success_configures_kubectl(monkeypatch):
    _no_disk_open(monkeypatch)
    fake = Router(
        rules=[
            ("eksctl create cluster", (0, "cluster created", "")),
            ("aws eks update-kubeconfig", (0, "Updated context", "")),
            ("kubectl get nodes", (0, "NAME\nnode1  Ready\n", "")),
        ],
        fallback=_prereq_fake(),
    )
    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(cluster_name="demo", region="us-east-1", nodes=1, node_type="t3.small",
                 k8s_version="1.28", dry_run=False)
    rc = tool.create_cluster(args)
    assert rc == 0
    assert any(c.startswith("eksctl create cluster") for c in fake.calls)


def test_create_cluster_eksctl_failure_returns_1(monkeypatch):
    _no_disk_open(monkeypatch)
    fake = Router(rules=[("eksctl create cluster", (1, "", "quota exceeded"))], fallback=_prereq_fake())
    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(cluster_name="demo", region="us-east-1", nodes=1, node_type="t3.small",
                 k8s_version="1.28", dry_run=False)
    assert tool.create_cluster(args) == 1


# ---------------------------------------------------------------------------
# configure_kubectl
# ---------------------------------------------------------------------------

def test_configure_kubectl_success(monkeypatch):
    fake = Router(rules=[
        ("aws eks update-kubeconfig", (0, "Updated context arn:aws:eks", "")),
        ("kubectl get nodes", (0, "NAME\nnode1  Ready\n", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.configure_kubectl(_Args(cluster_name="c", region="us-east-1")) == 0


def test_configure_kubectl_update_kubeconfig_failure(monkeypatch):
    fake = Router(rules=[("aws eks update-kubeconfig", (1, "", "cluster not found"))])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.configure_kubectl(_Args(cluster_name="c", region="us-east-1")) == 1


def test_configure_kubectl_connection_test_failure(monkeypatch):
    fake = Router(rules=[
        ("aws eks update-kubeconfig", (0, "Updated context", "")),
        ("kubectl get nodes", (1, "", "connection refused")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.configure_kubectl(_Args(cluster_name="c", region="us-east-1")) == 1


# ---------------------------------------------------------------------------
# deploy_application
# ---------------------------------------------------------------------------

def test_deploy_application_kubectl_not_configured_returns_1(monkeypatch):
    fake = Router(rules=[("kubectl get nodes", (1, "", "unauthorized"))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.deploy_application(_Args(manifest_dir="/nonexistent", namespace="default"))
    assert rc == 1


def test_deploy_application_manifest_path_not_found_returns_1(monkeypatch, tmp_path):
    fake = Router(rules=[("kubectl get nodes", (0, "node1 Ready", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    missing = tmp_path / "does-not-exist"
    rc = tool.deploy_application(_Args(manifest_dir=str(missing), namespace="default"))
    assert rc == 1


def test_deploy_application_success_with_directory_manifest(monkeypatch, tmp_path):
    manifest_dir = tmp_path / "k8s"
    manifest_dir.mkdir()
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl apply -f", (0, "deployment.apps/app created", "")),
        ("kubectl get pods", (0, "pod1 Running", "")),
        ("kubectl get svc", (0, "svc1 ClusterIP", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    rc = tool.deploy_application(_Args(manifest_dir=str(manifest_dir), namespace="default"))
    assert rc == 0


def test_deploy_application_success_with_file_manifest_and_custom_namespace(monkeypatch, tmp_path):
    manifest_file = tmp_path / "app.yaml"
    manifest_file.write_text("kind: Deployment")
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl create namespace", (0, "namespace/prod created", "")),
        ("kubectl apply -f", (0, "deployment.apps/app created", "")),
        ("kubectl get pods", (0, "pod1 Running", "")),
        ("kubectl get svc", (0, "svc1 ClusterIP", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    rc = tool.deploy_application(_Args(manifest_dir=str(manifest_file), namespace="prod"))
    assert rc == 0
    assert any("kubectl create namespace" in c for c in fake.calls)


def test_deploy_application_apply_failure_returns_1(monkeypatch, tmp_path):
    manifest_dir = tmp_path / "k8s"
    manifest_dir.mkdir()
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl apply -f", (1, "", "error validating data")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    rc = tool.deploy_application(_Args(manifest_dir=str(manifest_dir), namespace="default"))
    assert rc == 1


# ---------------------------------------------------------------------------
# run_tests (the `test` CLI command)
# ---------------------------------------------------------------------------

def _all_good_run_tests_fake():
    nodes_json = json.dumps({"items": [
        {"metadata": {"name": "node1"}, "status": {"conditions": [{"type": "Ready", "status": "True"}]}},
    ]})
    pods_json = json.dumps({"items": [
        {"metadata": {"name": "pod1"}, "status": {"phase": "Running"}},
    ]})
    svc_json = json.dumps({"items": [
        {"metadata": {"name": "svc1"}, "spec": {"type": "ClusterIP"}},
    ]})
    return Router(
        rules=[
            ("kubectl cluster-info", (0, "Kubernetes control plane", "")),
            ("kubectl get nodes -o json", (0, nodes_json, "")),
            ("kubectl get pods -n default -o json", (0, pods_json, "")),
            ("kubectl get svc -n default -o json", (0, svc_json, "")),
        ],
        fallback=_prereq_fake(),
    )


def test_run_tests_all_pass_returns_0(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    assert tool.run_tests(_Args(namespace="default")) == 0


def test_run_tests_prereqs_fail_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("which aws", (1, "", "not found")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 1


def test_run_tests_cluster_not_accessible_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl cluster-info", (1, "", "refused")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 1


def test_run_tests_node_not_ready_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    bad_nodes = json.dumps({"items": [
        {"metadata": {"name": "node1"}, "status": {"conditions": [{"type": "Ready", "status": "False"}]}},
    ]})
    fake.rules.insert(0, ("kubectl get nodes -o json", (0, bad_nodes, "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 1


def test_run_tests_get_nodes_failure_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get nodes -o json", (1, "", "denied")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 1


def test_run_tests_nodes_json_parse_error_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get nodes -o json", (0, "not-json", "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 1


def test_run_tests_no_pods_found_is_not_a_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get pods -n default -o json", (0, json.dumps({"items": []}), "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 0


def test_run_tests_pod_not_running_is_not_critical(monkeypatch):
    fake = _all_good_run_tests_fake()
    pods_json = json.dumps({"items": [{"metadata": {"name": "pod1"}, "status": {"phase": "Pending"}}]})
    fake.rules.insert(0, ("kubectl get pods -n default -o json", (0, pods_json, "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 0


def test_run_tests_pods_get_failure_is_not_critical(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get pods -n default -o json", (1, "", "denied")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 0


def test_run_tests_pods_json_parse_error_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get pods -n default -o json", (0, "not-json", "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 1


def test_run_tests_no_services_is_not_a_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get svc -n default -o json", (0, json.dumps({"items": []}), "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 0


def test_run_tests_services_get_failure_is_not_critical(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get svc -n default -o json", (1, "", "denied")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 0


def test_run_tests_services_json_parse_error_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get svc -n default -o json", (0, "not-json", "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 1


def test_run_tests_aws_credentials_invalid_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("aws sts get-caller-identity", (1, "", "expired")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(namespace="default")) == 1


def test_run_tests_defaults_namespace_when_missing_attr(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    assert tool.run_tests(_Args()) == 0


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------

def test_health_check_all_healthy_returns_0(monkeypatch):
    fake = Router(rules=[
        ("kubectl cluster-info", (0, "Kubernetes control plane", "")),
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods -n", (0, "pod1 Running", "")),
        ("kubectl get svc -n", (0, "svc1 ClusterIP", "")),
        ("kubectl get events", (0, "Normal Scheduled", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.health_check(_Args(namespace="default")) == 0


def test_health_check_cluster_not_responding_returns_1(monkeypatch):
    fake = Router(rules=[
        ("kubectl cluster-info", (1, "", "refused")),
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods -n", (0, "pod1 Running", "")),
        ("kubectl get svc -n", (0, "svc1", "")),
        ("kubectl get events", (0, "", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.health_check(_Args(namespace="default")) == 1


def test_health_check_notready_nodes_and_error_pods_returns_1(monkeypatch):
    fake = Router(rules=[
        ("kubectl cluster-info", (0, "ok", "")),
        ("kubectl get nodes", (0, "node1 NotReady", "")),
        ("kubectl get pods -n", (0, "pod1 CrashLoopBackOff", "")),
        ("kubectl get svc -n", (1, "", "denied")),
        ("kubectl get events", (1, "", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.health_check(_Args(namespace="default")) == 1


def test_health_check_get_nodes_failure_returns_1(monkeypatch):
    fake = Router(rules=[
        ("kubectl cluster-info", (0, "ok", "")),
        ("kubectl get nodes", (1, "", "timeout")),
        ("kubectl get pods -n", (0, "pod1 Running", "")),
        ("kubectl get svc -n", (0, "svc1", "")),
        ("kubectl get events", (0, "", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.health_check(_Args(namespace="default")) == 1


def test_health_check_pods_retrieval_failure_only_warns(monkeypatch, capsys):
    """A pods-fetch failure alone (cluster/nodes fine) must not flip the
    overall verdict to unhealthy -- the function only warns for pods, it
    never sets all_healthy=False on that branch."""
    fake = Router(rules=[
        ("kubectl cluster-info", (0, "ok", "")),
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods -n", (1, "", "denied")),
        ("kubectl get svc -n", (0, "svc1", "")),
        ("kubectl get events", (0, "", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.health_check(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cannot retrieve pods" in out


def test_health_check_defaults_namespace_when_missing_attr(monkeypatch):
    fake = Router(rules=[("kubectl", (0, "ok", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.health_check(_Args())
    assert rc == 0
    assert any(" -n default" in c for c in fake.calls)


# ---------------------------------------------------------------------------
# troubleshoot
# ---------------------------------------------------------------------------

def _troubleshoot_ok_rules():
    return [
        ("kubectl cluster-info", (0, "ok", "")),
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods -n", (0, "pod1 Running", "")),
        ("aws sts get-caller-identity", (0, "{}", "")),
    ]


def test_troubleshoot_no_issues_returns_0(monkeypatch):
    monkeypatch.setattr(tool, "run_command", Router(rules=_troubleshoot_ok_rules()))
    assert tool.troubleshoot(_Args(namespace="default")) == 0


def test_troubleshoot_cluster_inaccessible_reported(monkeypatch, capsys):
    rules = [("kubectl cluster-info", (1, "", "refused"))] + _troubleshoot_ok_rules()[1:]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    rc = tool.troubleshoot(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Cannot access cluster" in out


def test_troubleshoot_nodes_not_ready_reported(monkeypatch):
    rules = [("kubectl get nodes", (0, "node1 NotReady", ""))] + [r for r in _troubleshoot_ok_rules() if "get nodes" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args(namespace="default")) == 1


def test_troubleshoot_get_nodes_failure_reported(monkeypatch):
    rules = [("kubectl get nodes", (1, "", "boom"))] + [r for r in _troubleshoot_ok_rules() if "get nodes" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args(namespace="default")) == 1


def test_troubleshoot_pods_crashloop_reported(monkeypatch):
    rules = [("kubectl get pods -n", (0, "pod1 CrashLoopBackOff", ""))] + [r for r in _troubleshoot_ok_rules() if "get pods" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args(namespace="default")) == 1


def test_troubleshoot_pods_image_pull_backoff_reported(monkeypatch):
    rules = [("kubectl get pods -n", (0, "pod1 ImagePullBackOff", ""))] + [r for r in _troubleshoot_ok_rules() if "get pods" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args(namespace="default")) == 1


def test_troubleshoot_aws_credentials_invalid_reported(monkeypatch):
    rules = [("aws sts get-caller-identity", (1, "", "expired"))] + [r for r in _troubleshoot_ok_rules() if "sts" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args(namespace="default")) == 1


def test_troubleshoot_defaults_namespace_when_missing_attr(monkeypatch):
    fake = Router(rules=_troubleshoot_ok_rules())
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.troubleshoot(_Args())
    assert rc == 0
    assert any(" -n default" in c for c in fake.calls)


# ---------------------------------------------------------------------------
# cleanup_cluster
# ---------------------------------------------------------------------------

def test_cleanup_cluster_force_success(monkeypatch):
    fake = Router(rules=[("eksctl delete cluster", (0, "deleted", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.cleanup_cluster(_Args(cluster_name="c", region="us-east-1", force=True, dry_run=False))
    assert rc == 0


def test_cleanup_cluster_force_failure(monkeypatch):
    fake = Router(rules=[("eksctl delete cluster", (1, "", "denied"))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.cleanup_cluster(_Args(cluster_name="c", region="us-east-1", force=True, dry_run=False))
    assert rc == 1


def test_cleanup_cluster_dry_run_skips_execution(monkeypatch):
    fake = Router(rules=[])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.cleanup_cluster(_Args(cluster_name="c", region="us-east-1", force=True, dry_run=True))
    assert rc == 0
    assert fake.calls == []


def test_cleanup_cluster_confirmation_declined_returns_0(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")
    rc = tool.cleanup_cluster(_Args(cluster_name="c", region="us-east-1", force=False, dry_run=False))
    assert rc == 0


def test_cleanup_cluster_confirmation_accepted_proceeds(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes")
    fake = Router(rules=[("eksctl delete cluster", (0, "deleted", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.cleanup_cluster(_Args(cluster_name="c", region="us-east-1", force=False, dry_run=False))
    assert rc == 0


# ---------------------------------------------------------------------------
# main() dispatch
# ---------------------------------------------------------------------------

def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_dispatches_check_prerequisites(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake())
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-prerequisites"])
    assert tool.main() == 0


def test_main_dispatches_create_cluster_dry_run(monkeypatch):
    _no_disk_open(monkeypatch)
    monkeypatch.setattr(tool, "run_command", _prereq_fake())
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-cluster", "--cluster-name", "demo", "--dry-run"])
    assert tool.main() == 0


def test_main_configure_kubectl_missing_required_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "configure-kubectl"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing --cluster-name"
    except SystemExit as e:
        assert e.code != 0


def test_main_dispatches_configure_kubectl(monkeypatch):
    fake = Router(rules=[
        ("aws eks update-kubeconfig", (0, "ok", "")),
        ("kubectl get nodes", (0, "node1 Ready", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "configure-kubectl", "--cluster-name", "demo"])
    assert tool.main() == 0


def test_main_deploy_missing_required_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing --manifest-dir"
    except SystemExit as e:
        assert e.code != 0


def test_main_dispatches_deploy(monkeypatch, tmp_path):
    manifest_dir = tmp_path / "k8s"
    manifest_dir.mkdir()
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl apply -f", (0, "created", "")),
        ("kubectl get pods", (0, "pod1 Running", "")),
        ("kubectl get svc", (0, "svc1", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy", "--manifest-dir", str(manifest_dir)])
    assert tool.main() == 0


def test_main_dispatches_test(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    assert tool.main() == 0


def test_main_dispatches_health_check(monkeypatch):
    fake = Router(rules=[("kubectl", (0, "ok", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "health-check"])
    assert tool.main() == 0


def test_main_dispatches_troubleshoot(monkeypatch):
    monkeypatch.setattr(tool, "run_command", Router(rules=_troubleshoot_ok_rules()))
    monkeypatch.setattr(sys, "argv", ["tool.py", "troubleshoot"])
    assert tool.main() == 0


def test_main_cleanup_missing_required_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "cleanup"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing --cluster-name"
    except SystemExit as e:
        assert e.code != 0


def test_main_dispatches_cleanup(monkeypatch):
    fake = Router(rules=[("eksctl delete cluster", (0, "deleted", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "cleanup", "--cluster-name", "demo", "--force"])
    assert tool.main() == 0


def test_script_runs_as_main_entrypoint_via_subprocess():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "usage" in result.stdout.lower()
