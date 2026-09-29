import importlib.util as _ilu
import subprocess
import sys as _sys
import json as _json
from pathlib import Path

import pytest

_spec = _ilu.spec_from_file_location(
    "gcp_gke_deploy_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _router(rules, default=None):
    """rules: list of (substring, _Proc). Longest substring match wins."""
    default = default if default is not None else _Proc(0, "", "")
    ordered = sorted(rules, key=lambda r: -len(r[0]))

    def fake_run(cmd, shell=None, capture_output=None, text=None, timeout=None):
        s = cmd if isinstance(cmd, str) else " ".join(cmd)
        for pat, proc in ordered:
            if pat in s:
                return proc
        return default

    return fake_run


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(tool.time, "sleep", lambda *a, **k: None)


ALL_OK_PREREQ = [
    ("which gcloud", _Proc(0)),
    ("gcloud version | head -1", _Proc(0, "Google Cloud SDK 450.0.0")),
    ("gcloud auth list --filter=status:ACTIVE --format=", _Proc(0, "me@example.com")),
    ("which kubectl", _Proc(0)),
    ("kubectl version --client", _Proc(0, "Client Version: v1.29.0")),
    ("which docker", _Proc(0)),
]


# --------------------------------------------------------------------------
# run_command
# --------------------------------------------------------------------------

def test_run_command_returns_code_stdout_stderr(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run", _router([("echo hi", _Proc(0, "hi\n", ""))]))
    code, out, err = tool.run_command("echo hi")
    assert (code, out, err) == (0, "hi\n", "")


def test_run_command_handles_timeout(monkeypatch):
    def raise_timeout(cmd, shell=None, capture_output=None, text=None, timeout=None):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(tool.subprocess, "run", raise_timeout)
    code, out, err = tool.run_command("sleep 999", timeout=5)
    assert code == 1
    assert out == ""
    assert "timed out after 5s" in err


def test_run_command_handles_generic_exception(monkeypatch):
    def raise_boom(cmd, shell=None, capture_output=None, text=None, timeout=None):
        raise OSError("boom")

    monkeypatch.setattr(tool.subprocess, "run", raise_boom)
    code, out, err = tool.run_command("whatever")
    assert code == 1
    assert out == ""
    assert err == "boom"


# --------------------------------------------------------------------------
# check_command_exists
# --------------------------------------------------------------------------

def test_check_command_exists_true(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run", _router([("which foo", _Proc(0))]))
    assert tool.check_command_exists("foo") is True


def test_check_command_exists_false(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run", _router([("which foo", _Proc(1))]))
    assert tool.check_command_exists("foo") is False


# --------------------------------------------------------------------------
# check_prerequisites
# --------------------------------------------------------------------------

def test_check_prerequisites_all_good_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", _router(ALL_OK_PREREQ))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "All prerequisites met" in out
    assert "Authenticated as: me@example.com" in out


def test_check_prerequisites_gcloud_missing_returns_1(monkeypatch, capsys):
    rules = [r for r in ALL_OK_PREREQ if r[0] != "which gcloud"]
    rules.append(("which gcloud", _Proc(1)))
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "gcloud SDK not installed" in out


def test_check_prerequisites_not_authenticated_returns_1(monkeypatch, capsys):
    rules = [r for r in ALL_OK_PREREQ if "format" not in r[0]]
    rules.append(("gcloud auth list --filter=status:ACTIVE --format=", _Proc(0, "")))
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Not authenticated to GCP" in out


def test_check_prerequisites_kubectl_missing_returns_1(monkeypatch, capsys):
    rules = [r for r in ALL_OK_PREREQ if r[0] != "which kubectl"]
    rules.append(("which kubectl", _Proc(1)))
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "kubectl not installed" in out


def test_check_prerequisites_docker_missing_is_only_a_warning(monkeypatch, capsys):
    rules = [r for r in ALL_OK_PREREQ if r[0] != "which docker"]
    rules.append(("which docker", _Proc(1)))
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Docker not installed (optional)" in out
    assert "All prerequisites met" in out


# --------------------------------------------------------------------------
# create_cluster
# --------------------------------------------------------------------------

def test_create_cluster_fails_fast_when_prereqs_missing(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", _router([("which gcloud", _Proc(1))]))
    args = _Args(cluster_name="c1", project="p1", zone="z1", nodes=2,
                 machine_type="e2-small", preemptible=False, dry_run=False)
    rc = tool.create_cluster(args)
    assert rc == 1
    assert "Prerequisites not met" in capsys.readouterr().out


def test_create_cluster_dry_run_with_preemptible_shows_flag(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", _router(ALL_OK_PREREQ))
    args = _Args(cluster_name="c1", project="p1", zone="z1", nodes=2,
                 machine_type="e2-small", preemptible=True, dry_run=True)
    rc = tool.create_cluster(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "--preemptible" in out
    assert "cost savings" in out


def test_create_cluster_dry_run_without_preemptible_omits_flag(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", _router(ALL_OK_PREREQ))
    args = _Args(cluster_name="c1", project="p1", zone="z1", nodes=2,
                 machine_type="e2-small", preemptible=False, dry_run=True)
    rc = tool.create_cluster(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "--preemptible" not in out


def test_create_cluster_success_configures_kubectl(monkeypatch, capsys):
    rules = list(ALL_OK_PREREQ)
    rules.append(("gcloud container clusters create", _Proc(0)))
    rules.append(("gcloud container clusters get-credentials", _Proc(0)))
    rules.append(("kubectl get nodes", _Proc(0, "node-1   Ready")))
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    args = _Args(cluster_name="c1", project="p1", zone="z1", nodes=2,
                 machine_type="e2-small", preemptible=False, dry_run=False)
    rc = tool.create_cluster(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "GKE cluster created successfully" in out
    assert "Connection test passed" in out


def test_create_cluster_failure_reports_stderr(monkeypatch, capsys):
    rules = list(ALL_OK_PREREQ)
    rules.append(("gcloud container clusters create", _Proc(1, "", "quota exceeded")))
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    args = _Args(cluster_name="c1", project="p1", zone="z1", nodes=2,
                 machine_type="e2-small", preemptible=False, dry_run=False)
    rc = tool.create_cluster(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to create GKE cluster" in out
    assert "quota exceeded" in out


# --------------------------------------------------------------------------
# configure_kubectl
# --------------------------------------------------------------------------

def test_configure_kubectl_success(monkeypatch, capsys):
    rules = [
        ("gcloud container clusters get-credentials", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1   Ready")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.configure_kubectl(_Args(cluster_name="c1", zone="z1", project="p1"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "kubectl configured successfully" in out
    assert "node-1" in out


def test_configure_kubectl_get_credentials_fails(monkeypatch, capsys):
    rules = [("gcloud container clusters get-credentials", _Proc(1, "", "not found"))]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.configure_kubectl(_Args(cluster_name="c1", zone="z1", project="p1"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to configure kubectl" in out
    assert "not found" in out


def test_configure_kubectl_connection_test_fails(monkeypatch, capsys):
    rules = [
        ("gcloud container clusters get-credentials", _Proc(0)),
        ("kubectl get nodes", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.configure_kubectl(_Args(cluster_name="c1", zone="z1", project="p1"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Connection test failed" in out


# --------------------------------------------------------------------------
# deploy_application
# --------------------------------------------------------------------------

def test_deploy_application_kubectl_not_configured(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", _router([("kubectl get nodes", _Proc(1))]))
    rc = tool.deploy_application(_Args(manifest_dir="./k8s", namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "kubectl not configured" in out


def test_deploy_application_success_default_namespace(monkeypatch, capsys):
    rules = [
        ("kubectl get nodes", _Proc(0)),
        ("kubectl apply -f ./k8s -n default", _Proc(0, "deployment.apps/x created")),
        ("kubectl get pods -n default", _Proc(0, "pod-1  Running")),
        ("kubectl get svc -n default", _Proc(0, "svc-1")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.deploy_application(_Args(manifest_dir="./k8s", namespace="default"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Application deployed successfully" in out
    assert "created" in out


def test_deploy_application_creates_custom_namespace(monkeypatch, capsys):
    calls = []
    base_rules = [
        ("kubectl get nodes", _Proc(0)),
        ("kubectl apply -f ./k8s -n staging", _Proc(0, "applied")),
    ]
    fake = _router(base_rules)

    def spy(cmd, **kw):
        calls.append(cmd)
        return fake(cmd, **kw)

    monkeypatch.setattr(tool.subprocess, "run", spy)
    rc = tool.deploy_application(_Args(manifest_dir="./k8s", namespace="staging"))
    assert rc == 0
    assert any("kubectl create namespace staging" in c for c in calls)


def test_deploy_application_apply_fails(monkeypatch, capsys):
    rules = [
        ("kubectl get nodes", _Proc(0)),
        ("kubectl apply -f ./k8s -n default", _Proc(1, "", "invalid yaml")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.deploy_application(_Args(manifest_dir="./k8s", namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Deployment failed" in out
    assert "invalid yaml" in out


# --------------------------------------------------------------------------
# run_tests
# --------------------------------------------------------------------------

NODES_READY_JSON = _json.dumps({
    "items": [{"status": {"conditions": [{"type": "Ready", "status": "True"}]}}]
})
NODES_NOT_READY_JSON = _json.dumps({
    "items": [{"status": {"conditions": [{"type": "Ready", "status": "False"}]}}]
})
PODS_RUNNING_JSON = _json.dumps({
    "items": [{"status": {"phase": "Running"}, "metadata": {"name": "pod-a"}}]
})
PODS_PENDING_JSON = _json.dumps({
    "items": [{"status": {"phase": "Pending"}, "metadata": {"name": "pod-b"}}]
})


def test_run_tests_all_pass_returns_0(monkeypatch, capsys):
    rules = list(ALL_OK_PREREQ) + [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes -o json", _Proc(0, NODES_READY_JSON)),
        ("kubectl get pods -n default -o json", _Proc(0, PODS_RUNNING_JSON)),
        ("kubectl get svc -n default", _Proc(0)),
        ("gcloud auth list --filter=status:ACTIVE", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.run_tests(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "All tests passed" in out
    assert "Pod pod-a: Running" in out
    assert "All 1 nodes ready" in out


def test_run_tests_reports_failures_and_issues(monkeypatch, capsys):
    rules = [r for r in ALL_OK_PREREQ if r[0] != "which gcloud"]
    rules.append(("which gcloud", _Proc(1)))
    rules += [
        ("kubectl cluster-info", _Proc(1)),
        ("kubectl get nodes -o json", _Proc(1)),
        ("kubectl get pods -n default -o json", _Proc(1)),
        ("kubectl get svc -n default", _Proc(1)),
        ("gcloud auth list --filter=status:ACTIVE", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.run_tests(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Some tests failed" in out
    assert "Prerequisites missing" in out
    assert "Cluster not accessible" in out
    assert "Cannot retrieve nodes" in out
    assert "GCP credentials invalid" in out
    # pods/svc command failure is treated as a pass in this tool's logic
    assert "Total tests: 6" in out
    assert f"{tool.Colors.GREEN}Passed: 2{tool.Colors.END}" in out
    assert f"{tool.Colors.RED}Failed: 4{tool.Colors.END}" in out


def test_run_tests_detects_not_ready_nodes(monkeypatch, capsys):
    rules = list(ALL_OK_PREREQ) + [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes -o json", _Proc(0, NODES_NOT_READY_JSON)),
        ("kubectl get pods -n default -o json", _Proc(0, PODS_PENDING_JSON)),
        ("kubectl get svc -n default", _Proc(0)),
        ("gcloud auth list --filter=status:ACTIVE", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.run_tests(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Some nodes not ready" in out
    # phase "Pending" is not "Running" so no per-pod success line is printed
    assert "Pod pod-b" not in out


def test_run_tests_handles_malformed_node_json(monkeypatch, capsys):
    rules = list(ALL_OK_PREREQ) + [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes -o json", _Proc(0, "not-json")),
        ("kubectl get pods -n default -o json", _Proc(0, _json.dumps({"items": []}))),
        ("kubectl get svc -n default", _Proc(0)),
        ("gcloud auth list --filter=status:ACTIVE", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.run_tests(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Node parsing failed" in out


def test_run_tests_no_pods_found_still_passes(monkeypatch, capsys):
    rules = list(ALL_OK_PREREQ) + [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes -o json", _Proc(0, NODES_READY_JSON)),
        ("kubectl get pods -n default -o json", _Proc(0, _json.dumps({"items": []}))),
        ("kubectl get svc -n default", _Proc(0)),
        ("gcloud auth list --filter=status:ACTIVE", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.run_tests(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "No pods found" in out


def test_run_tests_namespace_defaults_when_args_has_no_namespace(monkeypatch, capsys):
    rules = list(ALL_OK_PREREQ) + [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes -o json", _Proc(0, NODES_READY_JSON)),
        ("kubectl get pods -n default -o json", _Proc(0, PODS_RUNNING_JSON)),
        ("kubectl get svc -n default", _Proc(0)),
        ("gcloud auth list --filter=status:ACTIVE", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.run_tests(_Args())
    assert rc == 0


# --------------------------------------------------------------------------
# health_check
# --------------------------------------------------------------------------

def test_health_check_all_healthy(monkeypatch, capsys):
    rules = [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1   Ready")),
        ("kubectl get pods -n default", _Proc(0, "pod-1   Running")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.health_check(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cluster is healthy" in out


def test_health_check_cluster_not_responding(monkeypatch, capsys):
    rules = [
        ("kubectl cluster-info", _Proc(1)),
        ("kubectl get nodes", _Proc(0, "node-1   Ready")),
        ("kubectl get pods -n default", _Proc(0, "pod-1   Running")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.health_check(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Cluster not responding" in out
    assert "Some issues detected" in out


def test_health_check_detects_not_ready_node(monkeypatch, capsys):
    rules = [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1   NotReady")),
        ("kubectl get pods -n default", _Proc(0, "pod-1   Running")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.health_check(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Some nodes not ready" in out


def test_health_check_get_nodes_fails(monkeypatch, capsys):
    rules = [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(1)),
        ("kubectl get pods -n default", _Proc(0, "pod-1   Running")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.health_check(_Args(namespace="default"))
    assert rc == 1


def test_health_check_detects_crashing_pods(monkeypatch, capsys):
    rules = [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1   Ready")),
        ("kubectl get pods -n default", _Proc(0, "pod-1   CrashLoopBackOff")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.health_check(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Some pods in error state" in out


# --------------------------------------------------------------------------
# troubleshoot
# --------------------------------------------------------------------------

def test_troubleshoot_no_issues(monkeypatch, capsys):
    rules = [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1   Ready")),
        ("kubectl get pods -n default", _Proc(0, "pod-1   Running")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.troubleshoot(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "No issues detected" in out


def test_troubleshoot_reports_all_issues_with_fixes(monkeypatch, capsys):
    rules = [
        ("kubectl cluster-info", _Proc(1)),
        ("kubectl get nodes", _Proc(0, "node-1   NotReady")),
        ("kubectl get pods -n default", _Proc(0, "pod-1   Error")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.troubleshoot(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "1. Issue: Cannot access cluster" in out
    assert "Fix: Run: gcloud container clusters get-credentials" in out
    assert "2. Issue: Some nodes not ready" in out
    assert "3. Issue: Some pods in error state" in out
    assert "Fix: Check logs: kubectl logs <pod-name> -n default" in out


def test_troubleshoot_namespace_defaults_when_missing(monkeypatch, capsys):
    rules = [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1   Ready")),
        ("kubectl get pods -n default", _Proc(0, "pod-1   Running")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.troubleshoot(_Args())
    assert rc == 0


# --------------------------------------------------------------------------
# cleanup_cluster
# --------------------------------------------------------------------------

def test_cleanup_cluster_cancelled_when_response_not_yes(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda *a, **k: "no")
    rc = tool.cleanup_cluster(_Args(cluster_name="c1", zone="z1", project="p1", force=False, dry_run=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cleanup cancelled" in out


def test_cleanup_cluster_proceeds_on_uppercase_yes(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda *a, **k: "YES")
    monkeypatch.setattr(tool.subprocess, "run", _router([("gcloud container clusters delete", _Proc(0))]))
    rc = tool.cleanup_cluster(_Args(cluster_name="c1", zone="z1", project="p1", force=False, dry_run=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cluster deleted successfully" in out


def test_cleanup_cluster_dry_run_skips_execution(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: calls.append(a) or _Proc(0))
    rc = tool.cleanup_cluster(_Args(cluster_name="c1", zone="z1", project="p1", force=True, dry_run=True))
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY RUN" in out
    assert calls == []


def test_cleanup_cluster_force_skips_prompt_and_deletes(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", _router([("gcloud container clusters delete", _Proc(0))]))
    rc = tool.cleanup_cluster(_Args(cluster_name="c1", zone="z1", project="p1", force=True, dry_run=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Cluster deleted successfully" in out


def test_cleanup_cluster_deletion_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run",
                         _router([("gcloud container clusters delete", _Proc(1, "", "permission denied"))]))
    rc = tool.cleanup_cluster(_Args(cluster_name="c1", zone="z1", project="p1", force=True, dry_run=False))
    out = capsys.readouterr().out
    assert rc == 1
    assert "Failed to delete cluster" in out
    assert "permission denied" in out


# --------------------------------------------------------------------------
# main() / CLI dispatch
# --------------------------------------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_check_prerequisites_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-prerequisites"])
    monkeypatch.setattr(tool.subprocess, "run", _router(ALL_OK_PREREQ))
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "All prerequisites met" in out


def test_main_create_cluster_missing_required_project_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "create-cluster"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_configure_kubectl_missing_required_args_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "configure-kubectl"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_cleanup_missing_required_args_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "cleanup"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_deploy_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "deploy", "--manifest-dir", "./k8s"])
    rules = [
        ("kubectl get nodes", _Proc(0)),
        ("kubectl apply -f ./k8s -n default", _Proc(0, "applied")),
        ("kubectl get pods -n default", _Proc(0)),
        ("kubectl get svc -n default", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.main()
    assert rc == 0


def test_main_health_check_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "health-check"])
    rules = [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1  Ready")),
        ("kubectl get pods -n default", _Proc(0, "pod-1  Running")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.main()
    assert rc == 0


def test_main_troubleshoot_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "troubleshoot"])
    rules = [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1  Ready")),
        ("kubectl get pods -n default", _Proc(0, "pod-1  Running")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.main()
    assert rc == 0


def test_main_cleanup_end_to_end_dry_run(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "cleanup", "--cluster-name", "c1", "--zone", "z1", "--project", "p1",
        "--force", "--dry-run",
    ])
    rc = tool.main()
    assert rc == 0
    assert "DRY RUN" in capsys.readouterr().out


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rules = list(ALL_OK_PREREQ) + [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes -o json", _Proc(0, NODES_READY_JSON)),
        ("kubectl get pods -n default -o json", _Proc(0, PODS_RUNNING_JSON)),
        ("kubectl get svc -n default", _Proc(0)),
        ("gcloud auth list --filter=status:ACTIVE", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.main()
    assert rc == 0


def test_subprocess_cli_smoke_runs_as_main_entrypoint():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "check-prerequisites"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode in (0, 1)
    assert "Checking Prerequisites" in proc.stdout


def test_run_tests_handles_malformed_pods_json(monkeypatch, capsys):
    rules = list(ALL_OK_PREREQ) + [
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes -o json", _Proc(0, NODES_READY_JSON)),
        ("kubectl get pods -n default -o json", _Proc(0, "not-json-either")),
        ("kubectl get svc -n default", _Proc(0)),
        ("gcloud auth list --filter=status:ACTIVE", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", _router(rules))
    rc = tool.run_tests(_Args(namespace="default"))
    out = capsys.readouterr().out
    # malformed pods JSON is swallowed by the except clause (tests_failed += 1,
    # with no explicit message) -- overall run still fails because of it
    assert rc == 1
    assert f"{tool.Colors.RED}Failed: 1{tool.Colors.END}" in out
