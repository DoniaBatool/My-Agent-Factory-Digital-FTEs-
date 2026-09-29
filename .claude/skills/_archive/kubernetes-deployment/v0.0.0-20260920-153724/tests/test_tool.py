import importlib.util as _ilu
import json as _json
import subprocess
import sys as _sys
from pathlib import Path

import pytest

_spec = _ilu.spec_from_file_location(
    "kubernetes_deployment_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
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


class _CP:
    """Stand-in for subprocess.CompletedProcess."""
    pass


def make_fake_run(rules, default=None):
    """Emulates real subprocess.run(list_cmd, check=, capture_output=, text=)
    semantics closely enough that the `check` flag's effect is genuinely
    observable: on failure with check=True it raises CalledProcessError
    (with .stdout/.stderr populated only when capture_output was requested,
    exactly like the real subprocess module), and with check=False (or on
    success) it returns a CompletedProcess-like object."""
    default = default if default is not None else _Proc(0, "", "")
    ordered = sorted(rules, key=lambda r: -len(r[0]))

    def fake_run(cmd, check=True, capture_output=False, text=False, timeout=None):
        s = cmd if isinstance(cmd, str) else " ".join(cmd)
        matched = default
        for pat, proc in ordered:
            if pat in s:
                matched = proc
                break
        if check and matched.returncode != 0:
            if capture_output:
                raise subprocess.CalledProcessError(
                    matched.returncode, cmd, output=matched.stdout, stderr=matched.stderr
                )
            raise subprocess.CalledProcessError(matched.returncode, cmd)
        cp = _CP()
        cp.returncode = matched.returncode
        cp.stdout = matched.stdout if capture_output else ""
        cp.stderr = matched.stderr if capture_output else ""
        return cp

    return fake_run


# --------------------------------------------------------------------------
# pure YAML generator functions
# --------------------------------------------------------------------------

def test_generate_namespace_default_environment():
    yaml = tool.generate_namespace("myapp")
    assert "kind: Namespace" in yaml
    assert "name: myapp" in yaml
    assert "environment: production" in yaml


def test_generate_namespace_custom_environment():
    yaml = tool.generate_namespace("myapp", environment="staging")
    assert "environment: staging" in yaml


def test_generate_configmap_shape():
    yaml = tool.generate_configmap("myapp", {"KEY_A": "1", "KEY_B": "two"})
    assert "name: myapp-config" in yaml
    assert 'KEY_A: "1"' in yaml
    assert 'KEY_B: "two"' in yaml


def test_generate_configmap_empty_config_has_no_data_lines():
    yaml = tool.generate_configmap("myapp", {})
    assert "data:" in yaml
    assert "KEY" not in yaml


def test_generate_secret_template_shape():
    yaml = tool.generate_secret_template("myapp")
    assert "kind: Secret" in yaml
    assert "name: myapp-secrets" in yaml
    assert "DATABASE_URL" in yaml
    assert "type: Opaque" in yaml


def test_generate_deployment_defaults():
    yaml = tool.generate_deployment("myapp", "backend", "myimage:1.0", 8000)
    assert "name: myapp-backend" in yaml
    assert "image: myimage:1.0" in yaml
    assert "replicas: 2" in yaml
    assert "containerPort: 8000" in yaml
    assert 'path: /health' in yaml
    assert "runAsNonRoot: true" in yaml


def test_generate_deployment_custom_replicas_and_resources_and_health_path():
    yaml = tool.generate_deployment(
        "myapp", "api", "myimage:2.0", 9000, replicas=5,
        resources_requests_mem="512Mi", resources_requests_cpu="500m",
        resources_limits_mem="1Gi", resources_limits_cpu="1",
        health_path="/healthz",
    )
    assert "replicas: 5" in yaml
    assert 'memory: "512Mi"' in yaml
    assert 'cpu: "500m"' in yaml
    assert 'memory: "1Gi"' in yaml
    assert 'path: /healthz' in yaml


def test_generate_service_default_generic_no_annotations():
    yaml = tool.generate_service("myapp", "backend", 80, 8000)
    assert "kind: Service" in yaml
    assert "type: LoadBalancer" in yaml
    assert "targetPort: 8000" in yaml
    assert "annotations" not in yaml


def test_generate_service_oke_loadbalancer_adds_annotations():
    yaml = tool.generate_service("myapp", "backend", 80, 8000, service_type="LoadBalancer", provider="oke")
    assert "oci-load-balancer-shape" in yaml
    assert "annotations:" in yaml


def test_generate_service_oke_but_clusterip_omits_annotations():
    yaml = tool.generate_service("myapp", "backend", 80, 8000, service_type="ClusterIP", provider="oke")
    assert "annotations" not in yaml
    assert "type: ClusterIP" in yaml


def test_generate_service_loadbalancer_but_generic_provider_omits_annotations():
    yaml = tool.generate_service("myapp", "backend", 80, 8000, service_type="LoadBalancer", provider="generic")
    assert "annotations" not in yaml


def test_generate_service_nodeport():
    yaml = tool.generate_service("myapp", "frontend", 80, 3000, service_type="NodePort")
    assert "type: NodePort" in yaml


# --------------------------------------------------------------------------
# run_command
# --------------------------------------------------------------------------

def test_run_command_capture_true_success(monkeypatch):
    def fake(cmd, check=True, capture_output=False, text=False):
        cp = _CP()
        cp.returncode, cp.stdout, cp.stderr = 0, "hello\n", ""
        return cp
    monkeypatch.setattr(tool.subprocess, "run", fake)
    code, out, err = tool.run_command(["echo", "hello"])
    assert (code, out, err) == (0, "hello\n", "")


def test_run_command_capture_false_returns_empty_strings(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl logs", _Proc(0, "should not appear"))]))
    code, out, err = tool.run_command(["kubectl", "logs"], capture=False)
    assert (code, out, err) == (0, "", "")


def test_run_command_called_process_error_with_captured_output(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl bad", _Proc(1, "partial out", "boom"))]))
    code, out, err = tool.run_command(["kubectl", "bad"])
    assert code == 1
    assert out == "partial out"
    assert err == "boom"


def test_run_command_default_check_true_on_uncaptured_failure_returns_none_not_empty(monkeypatch):
    # With capture=False and the default check=True, a failing command raises
    # CalledProcessError with no captured output attached (real subprocess
    # semantics), so run_command's except branch returns None -- distinctly
    # different from the (rc, "", "") a non-raising path would give. This
    # exercises (and kills mutants on) run_command's `check: bool = True`
    # default parameter.
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl fails", _Proc(2, "out", "err"))]))
    code, out, err = tool.run_command(["kubectl", "fails"], capture=False)
    assert code == 2
    assert out is None
    assert err is None


def test_run_command_check_false_on_uncaptured_failure_returns_empty_strings(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl fails", _Proc(2, "out", "err"))]))
    code, out, err = tool.run_command(["kubectl", "fails"], check=False, capture=False)
    assert (code, out, err) == (2, "", "")


# --------------------------------------------------------------------------
# check_kubectl
# --------------------------------------------------------------------------

def test_check_kubectl_not_installed_exits(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("kubectl version --client", _Proc(1))]))
    with pytest.raises(SystemExit):
        tool.check_kubectl()


def test_check_kubectl_installed_but_not_connected_returns_false(monkeypatch, capsys):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    assert tool.check_kubectl() is False
    assert "not connected to cluster" in capsys.readouterr().out


def test_check_kubectl_installed_and_connected_returns_true(monkeypatch):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    assert tool.check_kubectl() is True


# --------------------------------------------------------------------------
# cmd_generate
# --------------------------------------------------------------------------

def test_cmd_generate_backend_and_frontend(tmp_path):
    out_dir = tmp_path / "k8s"
    args = _Args(app_name="myapp", backend_image="be:1.0", frontend_image="fe:1.0",
                 provider="generic", free_tier=False,
                 backend_service_type="LoadBalancer", frontend_service_type="LoadBalancer",
                 replicas=2, output=str(out_dir))
    tool.cmd_generate(args)
    assert (out_dir / "namespace.yaml").exists()
    assert (out_dir / "backend-deployment.yaml").exists()
    assert (out_dir / "backend-service.yaml").exists()
    assert (out_dir / "frontend-deployment.yaml").exists()
    assert (out_dir / "frontend-service.yaml").exists()
    assert "myapp-backend" in (out_dir / "backend-deployment.yaml").read_text()


def test_cmd_generate_backend_only_skips_frontend_files(tmp_path):
    out_dir = tmp_path / "k8s"
    args = _Args(app_name="myapp", backend_image="be:1.0", frontend_image=None,
                 provider="generic", free_tier=False,
                 backend_service_type="LoadBalancer", frontend_service_type="LoadBalancer",
                 replicas=2, output=str(out_dir))
    tool.cmd_generate(args)
    assert (out_dir / "backend-deployment.yaml").exists()
    assert not (out_dir / "frontend-deployment.yaml").exists()
    assert not (out_dir / "frontend-service.yaml").exists()


def test_cmd_generate_free_tier_oke_forces_backend_clusterip(tmp_path):
    out_dir = tmp_path / "k8s"
    args = _Args(app_name="myapp", backend_image="be:1.0", frontend_image="fe:1.0",
                 provider="oke", free_tier=True,
                 backend_service_type="LoadBalancer", frontend_service_type="LoadBalancer",
                 replicas=2, output=str(out_dir))
    tool.cmd_generate(args)
    backend_svc = (out_dir / "backend-service.yaml").read_text()
    frontend_svc = (out_dir / "frontend-service.yaml").read_text()
    assert "type: ClusterIP" in backend_svc
    assert "type: LoadBalancer" in frontend_svc


def test_cmd_generate_free_tier_ignored_on_non_oke_provider(tmp_path):
    out_dir = tmp_path / "k8s"
    args = _Args(app_name="myapp", backend_image="be:1.0", frontend_image="fe:1.0",
                 provider="gke", free_tier=True,
                 backend_service_type="LoadBalancer", frontend_service_type="LoadBalancer",
                 replicas=2, output=str(out_dir))
    tool.cmd_generate(args)
    backend_svc = (out_dir / "backend-service.yaml").read_text()
    # free_tier optimization only applies for provider == "oke"; gke keeps
    # the originally requested service type
    assert "type: LoadBalancer" in backend_svc


def test_cmd_generate_creates_output_dir_when_missing(tmp_path):
    out_dir = tmp_path / "nested" / "k8s"
    assert not out_dir.exists()
    args = _Args(app_name="myapp", backend_image="be:1.0", frontend_image=None,
                 provider="generic", free_tier=False,
                 backend_service_type="LoadBalancer", frontend_service_type="LoadBalancer",
                 replicas=1, output=str(out_dir))
    tool.cmd_generate(args)
    assert out_dir.exists()
    assert (out_dir / "backend-secret.yaml").exists()


# --------------------------------------------------------------------------
# cmd_deploy
# --------------------------------------------------------------------------

def test_cmd_deploy_not_connected_returns_early(monkeypatch, tmp_path, capsys):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_deploy(_Args(manifests=str(tmp_path), namespace="default"))
    assert "not connected to cluster" in capsys.readouterr().out


def test_cmd_deploy_missing_manifests_dir_exits(monkeypatch, tmp_path):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    missing = tmp_path / "does-not-exist"
    with pytest.raises(SystemExit):
        tool.cmd_deploy(_Args(manifests=str(missing), namespace="default"))


def test_cmd_deploy_applies_in_dependency_order(monkeypatch, tmp_path, capsys):
    manifests_dir = tmp_path / "k8s"
    manifests_dir.mkdir()
    for name in ["frontend-service.yaml", "namespace.yaml", "backend-deployment.yaml",
                 "backend-configmap.yaml", "backend-secret.yaml"]:
        (manifests_dir / name).write_text("kind: X\n")

    applied_order = []

    def fake_run(cmd, check=True, capture_output=False, text=False):
        applied_order.append(cmd[-1])
        cp = _CP()
        cp.returncode, cp.stdout, cp.stderr = 0, "", ""
        return cp

    def dispatch(cmd, check=True, capture_output=False, text=False):
        s = " ".join(cmd)
        if "version --client" in s or "cluster-info" in s:
            cp = _CP()
            cp.returncode, cp.stdout, cp.stderr = 0, "", ""
            return cp
        return fake_run(cmd, check=check, capture_output=capture_output, text=text)

    monkeypatch.setattr(tool.subprocess, "run", dispatch)
    tool.cmd_deploy(_Args(manifests=str(manifests_dir), namespace="default"))

    # namespace must be applied before configmap/secret before deployment
    # before service, regardless of directory listing order
    assert applied_order.index(str(manifests_dir / "namespace.yaml")) < \
        applied_order.index(str(manifests_dir / "backend-configmap.yaml"))
    assert applied_order.index(str(manifests_dir / "backend-configmap.yaml")) < \
        applied_order.index(str(manifests_dir / "backend-deployment.yaml"))
    assert applied_order.index(str(manifests_dir / "backend-deployment.yaml")) < \
        applied_order.index(str(manifests_dir / "frontend-service.yaml"))
    assert "Deployment complete!" in capsys.readouterr().out


def test_cmd_deploy_reports_apply_failure(monkeypatch, tmp_path, capsys):
    manifests_dir = tmp_path / "k8s"
    manifests_dir.mkdir()
    (manifests_dir / "namespace.yaml").write_text("kind: Namespace\n")

    def dispatch(cmd, check=True, capture_output=False, text=False):
        s = " ".join(cmd)
        if "version --client" in s or "cluster-info" in s:
            cp = _CP(); cp.returncode, cp.stdout, cp.stderr = 0, "", ""; return cp
        cp = _CP(); cp.returncode, cp.stdout, cp.stderr = 1, "", "server error"; return cp

    monkeypatch.setattr(tool.subprocess, "run", dispatch)
    tool.cmd_deploy(_Args(manifests=str(manifests_dir), namespace="default"))
    out = capsys.readouterr().out
    assert "Failed to apply namespace.yaml" in out
    assert "server error" in out


# --------------------------------------------------------------------------
# cmd_get_ips
# --------------------------------------------------------------------------

def test_cmd_get_ips_not_connected_returns_early(monkeypatch, capsys):
    rules = [("kubectl version --client", _Proc(0)), ("kubectl cluster-info", _Proc(1))]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_get_ips(_Args(namespace="default"))
    assert "not connected to cluster" in capsys.readouterr().out


def test_cmd_get_ips_get_svc_fails(monkeypatch, capsys):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get svc", _Proc(1, "", "forbidden")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_get_ips(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert "Failed to get services" in out
    assert "forbidden" in out


def test_cmd_get_ips_prints_ip_hostname_and_pending(monkeypatch, capsys):
    services = _json.dumps({"items": [
        {"metadata": {"name": "svc-ip"}, "spec": {"type": "LoadBalancer"},
         "status": {"loadBalancer": {"ingress": [{"ip": "1.2.3.4"}]}}},
        {"metadata": {"name": "svc-host"}, "spec": {"type": "LoadBalancer"},
         "status": {"loadBalancer": {"ingress": [{"hostname": "x.example.com"}]}}},
        {"metadata": {"name": "svc-pending"}, "spec": {"type": "LoadBalancer"},
         "status": {"loadBalancer": {}}},
        {"metadata": {"name": "svc-cluster"}, "spec": {"type": "ClusterIP"},
         "status": {}},
    ]})
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get svc", _Proc(0, services)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_get_ips(_Args(namespace="default"))
    out = capsys.readouterr().out
    assert "svc-ip" in out and "http://1.2.3.4" in out
    assert "svc-host" in out and "http://x.example.com" in out
    assert "svc-pending" in out and "<pending>" in out
    assert "svc-cluster" not in out


# --------------------------------------------------------------------------
# cmd_health_check
# --------------------------------------------------------------------------

def test_cmd_health_check_not_connected_returns_early(monkeypatch, capsys):
    rules = [("kubectl version --client", _Proc(0)), ("kubectl cluster-info", _Proc(1))]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_health_check(_Args(namespace="default"))
    assert "not connected to cluster" in capsys.readouterr().out


def test_cmd_health_check_namespace_not_found(monkeypatch, capsys):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get namespace", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_health_check(_Args(namespace="ghost"))
    out = capsys.readouterr().out
    assert "Namespace: ghost (Not found)" in out


def test_cmd_health_check_all_pods_ready_and_all_lbs_ready(monkeypatch, capsys):
    pods = _json.dumps({"items": [
        {"status": {"containerStatuses": [{"ready": True}]}},
        {"status": {"containerStatuses": [{"ready": True}]}},
    ]})
    svcs = _json.dumps({"items": [
        {"spec": {"type": "LoadBalancer"}, "status": {"loadBalancer": {"ingress": [{"ip": "1.1.1.1"}]}}},
    ]})
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get namespace", _Proc(0)),
        ("kubectl get pods", _Proc(0, pods)),
        ("kubectl get svc", _Proc(0, svcs)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_health_check(_Args(namespace="default"))
    out = capsys.readouterr().out
    # must be the SUCCESS marker (green check), not the warning marker, to
    # genuinely exercise "ready_pods == total_pods and total_pods > 0"
    assert f"{tool.Colors.GREEN}\u2713{tool.Colors.NC} Pods: 2/2 running" in out
    assert "LoadBalancers: 1/1 have external IPs" in out


def test_cmd_health_check_some_pods_not_ready_and_lb_pending(monkeypatch, capsys):
    pods = _json.dumps({"items": [
        {"status": {"containerStatuses": [{"ready": True}]}},
        {"status": {"containerStatuses": [{"ready": False}]}},
    ]})
    svcs = _json.dumps({"items": [
        {"spec": {"type": "LoadBalancer"}, "status": {"loadBalancer": {}}},
    ]})
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get namespace", _Proc(0)),
        ("kubectl get pods", _Proc(0, pods)),
        ("kubectl get svc", _Proc(0, svcs)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_health_check(_Args(namespace="default"))
    out = capsys.readouterr().out
    # must be the WARNING marker (not success) since ready_pods != total_pods
    assert f"{tool.Colors.YELLOW}!{tool.Colors.NC} Pods: 1/2 running" in out
    assert "waiting..." in out


def test_cmd_health_check_no_pods_and_no_loadbalancers(monkeypatch, capsys):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get namespace", _Proc(0)),
        ("kubectl get pods", _Proc(0, _json.dumps({"items": []}))),
        ("kubectl get svc", _Proc(0, _json.dumps({"items": []}))),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_health_check(_Args(namespace="default"))
    out = capsys.readouterr().out
    # 0 pods total means ready == total (0 == 0) but "total_pods > 0" is False,
    # so the overall `and` must still be False -> warning marker, not success
    assert f"{tool.Colors.YELLOW}!{tool.Colors.NC} Pods: 0/0 running" in out
    assert "LoadBalancers" not in out


# --------------------------------------------------------------------------
# cmd_logs
# --------------------------------------------------------------------------

def test_cmd_logs_not_connected_returns_early(monkeypatch, capsys):
    rules = [("kubectl version --client", _Proc(0)), ("kubectl cluster-info", _Proc(1))]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_logs(_Args(namespace="default", app="backend", tail=50, follow=False))
    assert "not connected to cluster" in capsys.readouterr().out


def test_cmd_logs_builds_expected_command_without_follow(monkeypatch):
    calls = []

    def dispatch(cmd, check=True, capture_output=False, text=False):
        calls.append((list(cmd), capture_output, text))
        cp = _CP()
        cp.returncode = 0
        cp.stdout = ""
        cp.stderr = ""
        return cp

    monkeypatch.setattr(tool.subprocess, "run", dispatch)
    tool.cmd_logs(_Args(namespace="default", app="backend", tail=25, follow=False))
    log_call, capture_output, text = calls[-1]
    assert log_call == ["kubectl", "logs", "-n", "default", "-l", "app=default-backend", "--tail", "25"]
    # cmd_logs must stream output live (capture=False), never swallow it, so
    # subprocess.run must NOT be asked to capture stdout/stderr here
    assert capture_output is False
    assert text is False


def test_cmd_logs_appends_follow_flag(monkeypatch):
    calls = []

    def dispatch(cmd, check=True, capture_output=False, text=False):
        calls.append(list(cmd))
        cp = _CP(); cp.returncode, cp.stdout, cp.stderr = 0, "", ""
        return cp

    monkeypatch.setattr(tool.subprocess, "run", dispatch)
    tool.cmd_logs(_Args(namespace="default", app="backend", tail=10, follow=True))
    assert calls[-1][-1] == "-f"


# --------------------------------------------------------------------------
# cmd_scale
# --------------------------------------------------------------------------

def test_cmd_scale_not_connected_returns_early(monkeypatch, capsys):
    rules = [("kubectl version --client", _Proc(0)), ("kubectl cluster-info", _Proc(1))]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_scale(_Args(namespace="default", deployment="api", replicas=3))
    assert "not connected to cluster" in capsys.readouterr().out


def test_cmd_scale_success(monkeypatch, capsys):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl scale deployment", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_scale(_Args(namespace="default", deployment="api", replicas=3))
    out = capsys.readouterr().out
    assert "Scaled api to 3 replicas" in out


def test_cmd_scale_failure(monkeypatch, capsys):
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl scale deployment", _Proc(1, "", "not found")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_scale(_Args(namespace="default", deployment="api", replicas=3))
    out = capsys.readouterr().out
    assert "Failed to scale deployment" in out
    assert "not found" in out


# --------------------------------------------------------------------------
# main() / CLI dispatch
# --------------------------------------------------------------------------

def test_main_no_command_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_generate_missing_required_app_name_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_deploy_missing_required_args_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "deploy"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_get_ips_missing_namespace_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "get-ips"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_scale_missing_replicas_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "scale", "--namespace", "default", "--deployment", "api",
    ])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_generate_end_to_end(monkeypatch, tmp_path):
    out_dir = tmp_path / "out"
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "generate", "--app-name", "myapp", "--backend-image", "be:1.0",
        "--output", str(out_dir),
    ])
    tool.main()
    assert (out_dir / "namespace.yaml").exists()


def test_main_health_check_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "health-check", "--namespace", "default"])
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get namespace", _Proc(0)),
        ("kubectl get pods", _Proc(0, _json.dumps({"items": []}))),
        ("kubectl get svc", _Proc(0, _json.dumps({"items": []}))),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.main()
    assert "Health check for namespace: default" in capsys.readouterr().out


def test_subprocess_cli_smoke_runs_as_main_entrypoint(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    out_dir = tmp_path / "smoke-out"
    proc = subprocess.run(
        [_sys.executable, str(script), "generate", "--app-name", "smokeapp",
         "--backend-image", "smoke:1.0", "--output", str(out_dir)],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert (out_dir / "namespace.yaml").exists()
    assert "smokeapp" in (out_dir / "namespace.yaml").read_text()


def test_check_kubectl_invokes_run_command_with_check_false(monkeypatch):
    # check_kubectl deliberately suppresses run_command's own check=True
    # default so a failed command is inspected via its return code instead
    # of raising -- verify the actual call contract directly (spying on
    # run_command's arguments), since run_command's own return-value
    # symmetry between check=True/False (see run_command tests above) makes
    # this otherwise unobservable from check_kubectl's return value alone.
    calls = []

    def spy(cmd, check=True, capture=True):
        calls.append((list(cmd), check))
        return (0, "ok", "")

    monkeypatch.setattr(tool, "run_command", spy)
    tool.check_kubectl()
    assert calls[0] == (["kubectl", "version", "--client"], False)
    assert calls[1] == (["kubectl", "cluster-info"], False)


def test_cmd_health_check_invokes_run_command_with_check_false(monkeypatch):
    calls = []

    def spy(cmd, check=True, capture=True):
        calls.append((list(cmd), check))
        joined = " ".join(cmd)
        if "namespace" in joined and "get" in joined:
            return (0, "", "")
        if "pods" in joined:
            return (0, _json.dumps({"items": []}), "")
        if "svc" in joined:
            return (0, _json.dumps({"items": []}), "")
        return (0, "", "")

    monkeypatch.setattr(tool, "run_command", spy)
    tool.cmd_health_check(_Args(namespace="default"))

    ns_call = next(c for c in calls if "namespace" in c[0])
    pods_call = next(c for c in calls if "pods" in c[0])
    svc_call = next(c for c in calls if "svc" in c[0])
    assert ns_call[1] is False
    assert pods_call[1] is False
    assert svc_call[1] is False
