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

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json as _json
import subprocess
import sys as _sys
import pytest


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_validate_k8s_quantity_accepts_bare_integer_with_no_suffix():
    assert tool.validate_k8s_quantity("0")
    assert tool.validate_k8s_quantity("128")


def test_validate_k8s_quantity_accepts_decimal_with_gi_suffix():
    assert tool.validate_k8s_quantity("1.5Gi")


def test_validate_k8s_quantity_is_case_sensitive_for_suffix():
    # lowercase "gi" is not a valid k8s suffix (only Gi, Mi, Ki, m, G, M, K are)
    assert not tool.validate_k8s_quantity("1gi")


def test_validate_k8s_quantity_rejects_negative_values():
    assert not tool.validate_k8s_quantity("-5m")


def test_validate_k8s_quantity_rejects_trailing_garbage():
    # anchored regex must reject extra characters after a valid-looking prefix
    assert not tool.validate_k8s_quantity("250mm")
    assert not tool.validate_k8s_quantity("250m ")


def test_validate_k8s_quantity_rejects_leading_garbage():
    assert not tool.validate_k8s_quantity("m250")


def test_cmd_generate_deployment_success_prints_manifest(capsys):
    args = _Args(name="svc", image="svc:1.0", replicas=2, port=9000,
                 cpu_request="250m", cpu_limit="500m", mem_request="256Mi",
                 mem_limit="512Mi", health_path="/health")
    rc = tool.cmd_generate_deployment(args)
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["metadata"]["name"] == "svc"
    assert data["spec"]["replicas"] == 2


def test_cmd_generate_deployment_invalid_quantity_returns_1(capsys):
    args = _Args(name="svc", image="svc:1.0", replicas=2, port=9000,
                 cpu_request="garbage", cpu_limit="500m", mem_request="256Mi",
                 mem_limit="512Mi", health_path="/health")
    rc = tool.cmd_generate_deployment(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "invalid k8s resource quantity" in out


def test_cmd_validate_resources_valid_prints_ok(capsys):
    rc = tool.cmd_validate_resources(_Args(value="250m"))
    assert rc == 0
    assert capsys.readouterr().out.strip() == "OK"


def test_cmd_validate_resources_invalid_prints_invalid_message(capsys):
    rc = tool.cmd_validate_resources(_Args(value="nope"))
    assert rc == 1
    out = capsys.readouterr().out
    assert "INVALID" in out
    assert "nope" in out


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_generate_deployment_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-deployment", "--name", "svc", "--image", "svc:2.0"])
    rc = tool.main()
    assert rc == 0
    data = _json.loads(capsys.readouterr().out)
    assert data["metadata"]["name"] == "svc"
    assert data["spec"]["template"]["spec"]["containers"][0]["image"] == "svc:2.0"


def test_main_validate_resources_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "validate-resources", "512Mi"])
    rc = tool.main()
    assert rc == 0
    assert capsys.readouterr().out.strip() == "OK"


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_main_missing_required_name_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-deployment", "--image", "svc:1.0"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_missing_required_image_arg_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "generate-deployment", "--name", "svc"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_validate_resources_missing_positional_value_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "validate-resources"])
    with pytest.raises(SystemExit):
        tool.main()


def test_subprocess_cli_smoke_runs_as_main_entrypoint():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "validate-resources", "250m"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "OK"
