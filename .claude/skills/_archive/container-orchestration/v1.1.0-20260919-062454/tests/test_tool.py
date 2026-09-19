import importlib.util as _ilu
from pathlib import Path

_spec = _ilu.spec_from_file_location("container_orchestration_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


def test_validate_k8s_quantity_accepts_valid_forms():
    assert tool.validate_k8s_quantity("250m")
    assert tool.validate_k8s_quantity("512Mi")
    assert tool.validate_k8s_quantity("2Gi")


def test_validate_k8s_quantity_rejects_invalid():
    assert not tool.validate_k8s_quantity("lots")
    assert not tool.validate_k8s_quantity("")


def test_build_deployment_manifest_shape():
    manifest = tool.build_deployment_manifest("todo-api", "todo-api:1.0.0", replicas=3, port=8000)
    assert manifest["kind"] == "Deployment"
    assert manifest["spec"]["replicas"] == 3
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["image"] == "todo-api:1.0.0"
    assert container["ports"][0]["containerPort"] == 8000


def test_build_deployment_manifest_includes_liveness_and_readiness_probes():
    manifest = tool.build_deployment_manifest("x", "x:1.0", health_path="/healthz")
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["livenessProbe"]["httpGet"]["path"] == "/healthz"
    assert container["readinessProbe"]["httpGet"]["path"] == "/healthz"


def test_build_deployment_manifest_rejects_invalid_resource_quantity():
    try:
        tool.build_deployment_manifest("x", "y", cpu_request="not-a-quantity")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_build_deployment_manifest_uses_given_resource_requests():
    manifest = tool.build_deployment_manifest("x", "y", cpu_request="100m", mem_request="128Mi")
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    assert container["resources"]["requests"] == {"cpu": "100m", "memory": "128Mi"}
