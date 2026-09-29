import json
import subprocess
import sys
from pathlib import Path

import pytest

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("azure_aks_deploy_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


@pytest.fixture(autouse=True)
def _never_really_sleep(monkeypatch):
    """Safety net for the whole suite: configure_kubectl and setup_ingress
    both retry with a real time.sleep() between attempts. No test should
    ever wait on a real clock (or a mutated comparison that reroutes a
    fast-fail path into a real 6s/backoff retry loop should fail fast
    instead of hanging for tens of seconds)."""
    monkeypatch.setattr(tool.time, "sleep", lambda seconds: None)


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

    def __call__(self, cmd, timeout=300):
        self.calls.append(cmd)
        for substr, result in self.rules:
            if substr in cmd:
                return result
        if self.fallback is not None:
            return self.fallback(cmd, timeout=timeout)
        return self.default


def _prereq_fake(az_ok=True, az_login_ok=True, kubectl_ok=True, docker_ok=True):
    """Realistic run_command fake for check_prerequisites: every command the
    real function issues gets a plausible answer, including valid JSON for
    `az account show` (the real code does json.loads(stdout) on it)."""
    def fake(cmd, timeout=300):
        if cmd == "az --version":
            return (0, "azure-cli 2.55.0\n", "") if az_ok else (1, "", "not found")
        if cmd == "az account show":
            return (0, json.dumps({"user": {"name": "dev@example.com"}, "name": "Pay-As-You-Go"}), "") if az_login_ok else (1, "", "not logged in")
        if "kubectl version" in cmd:
            return (0, "Client Version: v1.28.0", "") if kubectl_ok else (1, "", "not found")
        if cmd == "docker --version":
            return (0, "Docker version 24.0.0", "") if docker_ok else (1, "", "not found")
        return (0, "", "")

    return fake


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
    monkeypatch.setattr(tool.subprocess, "run", lambda *a, **k: _FakeCompleted(0, "hello\n", ""))
    assert tool.run_command("echo hello") == (0, "hello\n", "")


def test_run_command_forwards_shell_and_timeout(monkeypatch):
    captured = {}

    def fake_run(cmd, shell, capture_output, text, timeout):
        captured.update(cmd=cmd, shell=shell, capture_output=capture_output, text=text, timeout=timeout)
        return _FakeCompleted(0, "", "")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    tool.run_command("echo hi", timeout=42)
    assert captured == {"cmd": "echo hi", "shell": True, "capture_output": True, "text": True, "timeout": 42}


def test_run_command_timeout_returns_error_tuple(monkeypatch):
    def fake_run(*a, **k):
        raise subprocess.TimeoutExpired(cmd="sleep 100", timeout=7)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("sleep 100", timeout=7)
    assert code == 1
    assert out == ""
    assert err == "Command timed out after 7s"


def test_run_command_generic_exception_returns_error_tuple(monkeypatch):
    def fake_run(*a, **k):
        raise OSError("no such file")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("bogus")
    assert code == 1
    assert out == ""
    assert err == "no such file"


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

def test_check_prerequisites_all_good_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _prereq_fake())
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "All required tools are installed and configured!" in out


def test_check_prerequisites_az_cli_missing_returns_1(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(az_ok=False))
    assert tool.check_prerequisites(_Args()) == 1


def test_check_prerequisites_not_logged_in_returns_1(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(az_login_ok=False))
    assert tool.check_prerequisites(_Args()) == 1


def test_check_prerequisites_kubectl_missing_returns_1(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(kubectl_ok=False))
    assert tool.check_prerequisites(_Args()) == 1


def test_check_prerequisites_docker_missing_is_optional_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _prereq_fake(docker_ok=False))
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Docker not installed (optional)" in out


def test_check_prerequisites_prints_logged_in_account_details(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _prereq_fake())
    tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert "dev@example.com" in out
    assert "Pay-As-You-Go" in out


# ---------------------------------------------------------------------------
# create_cluster
# ---------------------------------------------------------------------------

def test_create_cluster_resource_group_failure_returns_1(monkeypatch):
    fake = Router(rules=[("az group create", (1, "", "quota exceeded"))])
    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(cluster_name="demo", resource_group=None, location=None, nodes=None, node_size=None)
    assert tool.create_cluster(args) == 1


def test_create_cluster_full_success(monkeypatch):
    fake = Router(rules=[
        ("az group create", (0, "created", "")),
        ("az aks create", (0, "cluster created", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(cluster_name="demo", resource_group=None, location=None, nodes=None, node_size=None)
    rc = tool.create_cluster(args)
    assert rc == 0
    assert any("demo-rg" in c for c in fake.calls)  # default resource group derived from cluster name
    assert any("eastus" in c for c in fake.calls)  # default location
    assert any("--node-count 2" in c for c in fake.calls)  # default node count


def test_create_cluster_aks_create_failure_returns_1(monkeypatch):
    fake = Router(rules=[
        ("az group create", (0, "created", "")),
        ("az aks create", (1, "", "insufficient quota")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(cluster_name="demo", resource_group=None, location=None, nodes=None, node_size=None)
    assert tool.create_cluster(args) == 1


def test_create_cluster_uses_explicit_overrides(monkeypatch):
    fake = Router(rules=[
        ("az group create", (0, "created", "")),
        ("az aks create", (0, "created", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    args = _Args(cluster_name="demo", resource_group="custom-rg", location="westus",
                 nodes=5, node_size="Standard_D4s_v3")
    tool.create_cluster(args)
    assert any("custom-rg" in c and "westus" in c for c in fake.calls)
    assert any("--node-count 5" in c and "Standard_D4s_v3" in c and "--max-count 10" in c for c in fake.calls)


# ---------------------------------------------------------------------------
# configure_kubectl
# ---------------------------------------------------------------------------

def test_configure_kubectl_success_first_try(monkeypatch):
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)  # defensive: see note above
    fake = Router(rules=[
        ("az aks get-credentials", (0, "Merged", "")),
        ("kubectl cluster-info", (0, "Kubernetes control plane", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.configure_kubectl(_Args(cluster_name="c", resource_group=None))
    assert rc == 0


def test_configure_kubectl_get_credentials_failure_returns_1(monkeypatch):
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)  # defensive: see note above
    fake = Router(rules=[("az aks get-credentials", (1, "", "cluster not found"))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.configure_kubectl(_Args(cluster_name="c", resource_group=None))
    assert rc == 1


def test_configure_kubectl_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake(cmd, timeout=300):
        if cmd.startswith("az aks get-credentials"):
            return (0, "Merged", "")
        if cmd == "kubectl cluster-info":
            calls["n"] += 1
            if calls["n"] < 3:
                return (1, "", "not ready")
            return (0, "Kubernetes control plane", "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    rc = tool.configure_kubectl(_Args(cluster_name="c", resource_group=None))
    assert rc == 0
    assert calls["n"] == 3


def test_configure_kubectl_exhausts_retries_returns_1(monkeypatch):
    fake = Router(rules=[
        ("az aks get-credentials", (0, "Merged", "")),
        ("kubectl cluster-info", (1, "", "still not ready")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    rc = tool.configure_kubectl(_Args(cluster_name="c", resource_group=None))
    assert rc == 1


# ---------------------------------------------------------------------------
# deploy_app
# ---------------------------------------------------------------------------

def test_deploy_app_no_manifest_returns_1():
    rc = tool.deploy_app(_Args(manifest=None))
    assert rc == 1


def test_deploy_app_success(monkeypatch, tmp_path):
    fake = Router(rules=[
        ("kubectl apply -f", (0, "deployment.apps/app created", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.deploy_app(_Args(manifest="k8s/app.yaml"))
    assert rc == 0
    assert any(c == "kubectl get deployments" for c in fake.calls)
    assert any(c == "kubectl get services" for c in fake.calls)
    assert any(c == "kubectl get pods" for c in fake.calls)


def test_deploy_app_failure_returns_1(monkeypatch):
    fake = Router(rules=[("kubectl apply -f", (1, "", "error validating data"))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.deploy_app(_Args(manifest="k8s/app.yaml"))
    assert rc == 1


# ---------------------------------------------------------------------------
# setup_ingress
# ---------------------------------------------------------------------------

def test_setup_ingress_helm_install_failure_returns_1(monkeypatch):
    # time.sleep is mocked defensively here too: if a future change (or a
    # mutation of the `if code == 0` success check) ever routed this
    # failure into the polling loop below, this must fail fast rather than
    # actually sleeping 30 * 6s.
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    fake = Router(rules=[("helm install nginx-ingress", (1, "", "helm not found"))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.setup_ingress(_Args())
    assert rc == 1


def test_setup_ingress_success_gets_external_ip_immediately(monkeypatch):
    fake = Router(rules=[
        ("helm install nginx-ingress", (0, "installed", "")),
        ("kubectl get service nginx-ingress", (0, "10.0.0.5", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    rc = tool.setup_ingress(_Args())
    assert rc == 0


def test_setup_ingress_success_but_ip_not_yet_assigned(monkeypatch):
    fake = Router(rules=[
        ("helm install nginx-ingress", (0, "installed", "")),
        ("kubectl get service nginx-ingress", (0, "''", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    rc = tool.setup_ingress(_Args())
    assert rc == 0  # not a failure, just still pending


# ---------------------------------------------------------------------------
# run_tests (the `test` CLI command)
# ---------------------------------------------------------------------------

def _all_good_run_tests_fake():
    cluster_json = json.dumps({
        "location": "eastus",
        "kubernetesVersion": "1.28",
        "agentPoolProfiles": [{"count": 2}],
    })
    return Router(
        rules=[
            ("az aks show", (0, cluster_json, "")),
            ("kubectl cluster-info", (0, "Kubernetes control plane", "")),
            ("kubectl get nodes", (0, "NAME\nnode1  Ready\n", "")),
            ("kubectl get pods -n kube-system", (0, "NAME\npod1  1/1  Running\n", "")),
            ("kubectl top nodes", (0, "NAME  CPU\nnode1  10%\n", "")),
        ],
        fallback=_prereq_fake(),
    )


def test_run_tests_all_pass_returns_0(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    assert tool.run_tests(_Args(cluster_name="demo", resource_group=None)) == 0


def test_run_tests_all_pass_does_not_print_failed_count(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    tool.run_tests(_Args(cluster_name="demo", resource_group=None))
    out = capsys.readouterr().out
    assert "Failed:" not in out


def test_run_tests_some_failures_prints_failed_count(monkeypatch, capsys):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("az --version", (1, "", "not found")))
    monkeypatch.setattr(tool, "run_command", fake)
    tool.run_tests(_Args(cluster_name=None, resource_group=None))
    out = capsys.readouterr().out
    assert "Failed:" in out


def test_run_tests_az_cli_missing_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("az --version", (1, "", "not found")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 1


def test_run_tests_kubectl_missing_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl version --client", (1, "", "not found")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 1


def test_run_tests_not_logged_in_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("az account show", (1, "", "not logged in")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 1


def test_run_tests_no_cluster_name_skips_cluster_check(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 0


def test_run_tests_cluster_not_found_is_not_a_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("az aks show", (1, "", "not found")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name="demo", resource_group=None)) == 0


def test_run_tests_cluster_found_reports_details(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    tool.run_tests(_Args(cluster_name="demo", resource_group=None))
    out = capsys.readouterr().out
    assert "eastus" in out
    assert "Cluster exists: demo" in out


def test_run_tests_kubectl_not_connected_is_not_a_failure(monkeypatch, capsys):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl cluster-info", (1, "", "refused")))
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.run_tests(_Args(cluster_name=None, resource_group=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "kubectl not configured for any cluster" in out


def test_run_tests_kubectl_connected_reports_connected_message(monkeypatch, capsys):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    tool.run_tests(_Args(cluster_name=None, resource_group=None))
    out = capsys.readouterr().out
    assert "kubectl connected to cluster" in out


def test_run_tests_nodes_not_ready_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get nodes", (0, "NAME\nnode1  NotReady\n", "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 1


def test_run_tests_no_nodes_found_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get nodes", (0, "NAME\n", "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 1


def test_run_tests_cannot_check_cluster_health_is_not_a_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get nodes", (1, "", "not connected")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 0


def test_run_tests_no_system_pods_counts_as_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get pods -n kube-system", (0, "NAME\n", "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 1


def test_run_tests_some_system_pods_not_running_is_not_critical(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get pods -n kube-system", (0, "NAME\npod1  0/1  Pending\n", "")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 0


def test_run_tests_cannot_check_system_pods_is_not_a_failure(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl get pods -n kube-system", (1, "", "not connected")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 0


def test_run_tests_metrics_server_unavailable_is_not_critical(monkeypatch):
    fake = _all_good_run_tests_fake()
    fake.rules.insert(0, ("kubectl top nodes", (1, "", "metrics-server not found")))
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.run_tests(_Args(cluster_name=None, resource_group=None)) == 0


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------

def test_health_check_get_nodes_failure_returns_1(monkeypatch):
    fake = Router(rules=[("kubectl get nodes", (1, "", "unreachable"))])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.health_check(_Args()) == 1


def test_health_check_all_healthy_returns_0(monkeypatch, capsys):
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods --all-namespaces", (0, "NAMESPACE POD STATUS\nkube-system pod1 Running", "")),
        ("kubectl get services --all-namespaces", (0, "svc1 ClusterIP", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.health_check(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "All pods are healthy" in out


def test_health_check_reports_problem_pods_but_still_returns_0(monkeypatch, capsys):
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods --all-namespaces", (0, "NAMESPACE POD STATUS\nkube-system pod1 CrashLoopBackOff", "")),
        ("kubectl get services --all-namespaces", (0, "svc1 ClusterIP", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.health_check(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "pod(s) not in Running state" in out


def test_health_check_pods_fetch_failure_is_silent_and_returns_0(monkeypatch):
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods --all-namespaces", (1, "", "denied")),
        ("kubectl get services --all-namespaces", (0, "svc1 ClusterIP", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    assert tool.health_check(_Args()) == 0


def test_health_check_services_fetch_failure_is_silent_and_returns_0(monkeypatch, capsys):
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods --all-namespaces", (0, "NAMESPACE POD STATUS\nkube-system pod1 Running", "")),
        ("kubectl get services --all-namespaces", (1, "", "denied")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.health_check(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Services:" not in out


# ---------------------------------------------------------------------------
# troubleshoot
# ---------------------------------------------------------------------------

def _troubleshoot_ok_rules():
    return [
        ("az account show", (0, "{}", "")),
        ("kubectl cluster-info", (0, "ok", "")),
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods --all-namespaces", (0, "NAMESPACE\nkube-system pod1 Running", "")),
        ("kubectl get services --all-namespaces -o wide", (0, "svc1 ClusterIP", "")),
    ]


def test_troubleshoot_no_issues_returns_0(monkeypatch):
    monkeypatch.setattr(tool, "run_command", Router(rules=_troubleshoot_ok_rules()))
    assert tool.troubleshoot(_Args()) == 0


def test_troubleshoot_not_logged_in_reported(monkeypatch, capsys):
    rules = [("az account show", (1, "", "expired"))] + _troubleshoot_ok_rules()[1:]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Not logged in to Azure" in out


def test_troubleshoot_kubectl_not_configured_reported(monkeypatch):
    rules = [("kubectl cluster-info", (1, "", "refused"))] + [r for r in _troubleshoot_ok_rules() if "cluster-info" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args()) == 1


def test_troubleshoot_nodes_not_ready_reported(monkeypatch):
    rules = [("kubectl get nodes", (0, "node1 NotReady", ""))] + [r for r in _troubleshoot_ok_rules() if "get nodes" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args()) == 1


def test_troubleshoot_pods_in_error_state_reported(monkeypatch):
    rules = [("kubectl get pods --all-namespaces", (0, "NAMESPACE\nkube-system pod1 CrashLoopBackOff", ""))] + \
        [r for r in _troubleshoot_ok_rules() if r[0] != "kubectl get pods --all-namespaces"]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args()) == 1


def test_troubleshoot_loadbalancer_pending_reported(monkeypatch):
    rules = [("kubectl get services --all-namespaces -o wide", (0, "svc1 LoadBalancer <pending>", ""))] + \
        [r for r in _troubleshoot_ok_rules() if "wide" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args()) == 1


def test_troubleshoot_get_nodes_failure_is_not_an_issue_by_itself(monkeypatch):
    """troubleshoot only inspects node output when the command succeeds
    (`if code == 0`); a failed `kubectl get nodes` call is silently
    skipped rather than counted as its own issue."""
    rules = [("kubectl get nodes", (1, "", "boom"))] + [r for r in _troubleshoot_ok_rules() if "get nodes" not in r[0]]
    monkeypatch.setattr(tool, "run_command", Router(rules=rules))
    assert tool.troubleshoot(_Args()) == 0


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

def test_cleanup_yes_flag_success(monkeypatch):
    fake = Router(rules=[("az group delete", (0, "started", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.cleanup(_Args(cluster_name="c", resource_group=None, yes=True))
    assert rc == 0


def test_cleanup_yes_flag_failure(monkeypatch):
    fake = Router(rules=[("az group delete", (1, "", "denied"))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.cleanup(_Args(cluster_name="c", resource_group=None, yes=True))
    assert rc == 1


def test_cleanup_confirmation_declined_returns_0(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "no")
    rc = tool.cleanup(_Args(cluster_name="c", resource_group=None, yes=False))
    assert rc == 0


def test_cleanup_confirmation_accepted_proceeds(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "yes")
    fake = Router(rules=[("az group delete", (0, "started", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    rc = tool.cleanup(_Args(cluster_name="c", resource_group=None, yes=False))
    assert rc == 0


def test_cleanup_uses_explicit_resource_group(monkeypatch):
    fake = Router(rules=[("az group delete", (0, "started", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    tool.cleanup(_Args(cluster_name="c", resource_group="custom-rg", yes=True))
    assert any("custom-rg" in c for c in fake.calls)


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


def test_main_create_cluster_missing_required_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-cluster"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing --cluster-name"
    except SystemExit as e:
        assert e.code != 0


def test_main_dispatches_create_cluster(monkeypatch):
    fake = Router(rules=[
        ("az group create", (0, "created", "")),
        ("az aks create", (0, "created", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "create-cluster", "--cluster-name", "demo"])
    assert tool.main() == 0


def test_main_configure_kubectl_missing_required_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "configure-kubectl"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing --cluster-name"
    except SystemExit as e:
        assert e.code != 0


def test_main_dispatches_configure_kubectl(monkeypatch):
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)  # defensive: see note above
    fake = Router(rules=[
        ("az aks get-credentials", (0, "ok", "")),
        ("kubectl cluster-info", (0, "ok", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "configure-kubectl", "--cluster-name", "demo"])
    assert tool.main() == 0


def test_main_deploy_app_missing_required_arg_exits(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy-app"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing --manifest"
    except SystemExit as e:
        assert e.code != 0


def test_main_dispatches_deploy_app(monkeypatch):
    fake = Router(rules=[("kubectl apply -f", (0, "created", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "deploy-app", "--manifest", "app.yaml"])
    assert tool.main() == 0


def test_main_dispatches_setup_ingress(monkeypatch):
    fake = Router(rules=[
        ("helm install nginx-ingress", (0, "installed", "")),
        ("kubectl get service nginx-ingress", (0, "1.2.3.4", "")),
    ])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(tool.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["tool.py", "setup-ingress"])
    assert tool.main() == 0


def test_main_dispatches_test(monkeypatch):
    monkeypatch.setattr(tool, "run_command", _all_good_run_tests_fake())
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    assert tool.main() == 0


def test_main_dispatches_health_check(monkeypatch):
    fake = Router(rules=[
        ("kubectl get nodes", (0, "node1 Ready", "")),
        ("kubectl get pods --all-namespaces", (0, "pod1 Running", "")),
        ("kubectl get services --all-namespaces", (0, "svc1", "")),
    ])
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
    fake = Router(rules=[("az group delete", (0, "started", ""))])
    monkeypatch.setattr(tool, "run_command", fake)
    monkeypatch.setattr(sys, "argv", ["tool.py", "cleanup", "--cluster-name", "demo", "--yes"])
    assert tool.main() == 0


def test_script_runs_as_main_entrypoint_via_subprocess():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 1
    assert "usage" in result.stdout.lower()
