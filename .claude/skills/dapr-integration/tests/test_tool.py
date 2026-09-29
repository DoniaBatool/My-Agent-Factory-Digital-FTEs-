import importlib.util as _ilu
import json
import subprocess
import sys as _sys
from pathlib import Path

import pytest
import yaml

_spec = _ilu.spec_from_file_location(
    "dapr_integration_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
)
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)


class _Args:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class RecordingRunner:
    """Stand-in for tool.run_command that records every cmd it is asked to run
    and returns a canned (code, stdout, stderr) based on the first matching
    substring key in `mapping` (dict order matters), or `default` otherwise."""

    def __init__(self, mapping=None, default=(0, "", "")):
        self.calls = []
        self.mapping = mapping or {}
        self.default = default

    def __call__(self, cmd, timeout=300):
        self.calls.append(cmd)
        for key, resp in self.mapping.items():
            if key in cmd:
                return resp
        return self.default


# ---------------------------------------------------------------------------
# print_* helpers
# ---------------------------------------------------------------------------

def test_print_success_contains_message_and_checkmark(capsys):
    tool.print_success("hello")
    out = capsys.readouterr().out
    assert "hello" in out
    assert "✓" in out


def test_print_error_contains_message_and_x(capsys):
    tool.print_error("bad thing")
    out = capsys.readouterr().out
    assert "bad thing" in out
    assert "✗" in out


def test_print_warning_contains_message_and_symbol(capsys):
    tool.print_warning("watch out")
    out = capsys.readouterr().out
    assert "watch out" in out
    assert "⚠" in out


def test_print_info_contains_message(capsys):
    tool.print_info("fyi")
    out = capsys.readouterr().out
    assert "fyi" in out


def test_print_header_contains_arrow_and_message(capsys):
    tool.print_header("Section Title")
    out = capsys.readouterr().out
    assert "==>" in out
    assert "Section Title" in out


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------

def test_run_command_returns_real_subprocess_output(monkeypatch):
    code, out, err = tool.run_command("echo hi")
    assert code == 0
    assert out.strip() == "hi"
    assert err == ""


def test_run_command_returns_nonzero_on_failing_shell_command():
    code, out, err = tool.run_command("exit 3")
    assert code == 3


def test_run_command_handles_timeout(monkeypatch):
    def fake_run(cmd, shell=True, capture_output=True, text=True, timeout=300):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("sleep 100", timeout=5)
    assert code == 1
    assert out == ""
    assert "timed out after 5s" in err


def test_run_command_handles_generic_exception(monkeypatch):
    def fake_run(cmd, shell=True, capture_output=True, text=True, timeout=300):
        raise OSError("boom")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    code, out, err = tool.run_command("whatever")
    assert code == 1
    assert out == ""
    assert err == "boom"


# ---------------------------------------------------------------------------
# check_prerequisites
# ---------------------------------------------------------------------------

def test_check_prerequisites_all_pass_returns_0(monkeypatch, capsys):
    runner = RecordingRunner({
        "dapr version": (0, "CLI version 1.10.0 linux/amd64", ""),
        "kubectl version --client": (0, "Client Version: v1.28", ""),
        "kubectl cluster-info": (0, "Kubernetes control plane is running", ""),
        "helm version": (0, "version.BuildInfo{Version:v3.12}", ""),
        "kubectl get pods -n dapr-system": (0, "dapr-operator-xxx  1/1  Running", ""),
    })
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Passed: 5/5" in out
    assert "Failed: 0/5" in out
    assert "1.10.0" in out


def test_check_prerequisites_version_string_fallback_when_too_short(monkeypatch, capsys):
    runner = RecordingRunner({
        "dapr version": (0, "dapr", ""),
        "kubectl version --client": (0, "ok", ""),
        "kubectl cluster-info": (0, "ok", ""),
        "helm version": (0, "ok", ""),
        "kubectl get pods -n dapr-system": (0, "dapr-x Running", ""),
    })
    monkeypatch.setattr(tool, "run_command", runner)
    tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert "Dapr CLI installed: installed" in out


def test_check_prerequisites_dapr_cli_missing_fails(monkeypatch, capsys):
    runner = RecordingRunner({
        "dapr version": (1, "", "not found"),
        "kubectl version --client": (0, "ok", ""),
        "kubectl cluster-info": (0, "ok", ""),
        "helm version": (0, "ok", ""),
        "kubectl get pods -n dapr-system": (0, "dapr-x", ""),
    })
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Passed: 4/5" in out
    assert "Failed: 1/5" in out
    assert "Dapr CLI not installed" in out


def test_check_prerequisites_kubectl_missing_fails(monkeypatch, capsys):
    runner = RecordingRunner({
        "dapr version": (0, "CLI version 1.0.0", ""),
        "kubectl version --client": (1, "", "not found"),
        "kubectl cluster-info": (0, "ok", ""),
        "helm version": (0, "ok", ""),
        "kubectl get pods -n dapr-system": (0, "dapr-x", ""),
    })
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Passed: 4/5" in out
    assert "Failed: 1/5" in out
    assert "kubectl not installed" in out


def test_check_prerequisites_cluster_not_connected_fails(monkeypatch, capsys):
    runner = RecordingRunner({
        "dapr version": (0, "CLI version 1.0.0", ""),
        "kubectl version --client": (0, "ok", ""),
        "kubectl cluster-info": (1, "", "connection refused"),
        "helm version": (0, "ok", ""),
        "kubectl get pods -n dapr-system": (0, "dapr-x", ""),
    })
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Not connected to K8s cluster" in out


def test_check_prerequisites_helm_missing_is_not_fatal(monkeypatch, capsys):
    runner = RecordingRunner({
        "dapr version": (0, "CLI version 1.0.0", ""),
        "kubectl version --client": (0, "ok", ""),
        "kubectl cluster-info": (0, "ok", ""),
        "helm version": (1, "", "not found"),
        "kubectl get pods -n dapr-system": (0, "dapr-x", ""),
    })
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Passed: 5/5" in out
    assert "Helm not installed (optional)" in out


def test_check_prerequisites_dapr_not_yet_in_cluster_is_not_fatal(monkeypatch, capsys):
    runner = RecordingRunner({
        "dapr version": (0, "CLI version 1.0.0", ""),
        "kubectl version --client": (0, "ok", ""),
        "kubectl cluster-info": (0, "ok", ""),
        "helm version": (0, "ok", ""),
        "kubectl get pods -n dapr-system": (1, "", "not found"),
    })
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.check_prerequisites(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Passed: 5/5" in out
    assert "Dapr not installed in cluster yet" in out


# ---------------------------------------------------------------------------
# init_dapr
# ---------------------------------------------------------------------------

def test_init_dapr_default_namespace_and_flags(monkeypatch, capsys):
    runner = RecordingRunner(default=(0, "installed ok", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    args = _Args(namespace=None, enable_ha=False, dev_mode=False)
    rc = tool.init_dapr(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "dapr-system" in runner.calls[0]
    assert "--enable-ha" not in runner.calls[0]
    assert "--dev" not in runner.calls[0]
    assert "Dapr installed successfully" in out


def test_init_dapr_enable_ha_and_dev_mode_flags_added(monkeypatch, capsys):
    runner = RecordingRunner(default=(0, "ok", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    args = _Args(namespace="custom-ns", enable_ha=True, dev_mode=True)
    tool.init_dapr(args)
    out = capsys.readouterr().out
    assert "custom-ns" in runner.calls[0]
    assert "--enable-ha" in runner.calls[0]
    assert "--dev" in runner.calls[0]
    assert "High Availability enabled" in out
    assert "Development mode" in out


def test_init_dapr_failure_returns_1(monkeypatch, capsys):
    runner = RecordingRunner(default=(1, "", "install failed"))
    monkeypatch.setattr(tool, "run_command", runner)
    args = _Args(namespace=None, enable_ha=False, dev_mode=False)
    rc = tool.init_dapr(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "installation failed" in out
    assert "install failed" in out


# ---------------------------------------------------------------------------
# setup_pubsub / setup_state / setup_secrets / setup_cron
# (all write real YAML files under ./dapr/components -- always run inside
# a monkeypatched cwd so nothing touches the real repo)
# ---------------------------------------------------------------------------

def test_setup_pubsub_writes_expected_yaml_with_defaults(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    runner = RecordingRunner(default=(0, "applied", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    args = _Args(brokers=None, consumer_group=None, namespace=None)
    rc = tool.setup_pubsub(args)
    assert rc == 0
    yaml_file = tmp_path / "dapr" / "components" / "pubsub-kafka.yaml"
    assert yaml_file.exists()
    doc = yaml.safe_load(yaml_file.read_text())
    assert doc["metadata"]["name"] == "kafka-pubsub"
    assert doc["metadata"]["namespace"] == "default"
    assert doc["spec"]["type"] == "pubsub.kafka"
    meta = {m["name"]: m["value"] for m in doc["spec"]["metadata"]}
    assert meta["brokers"] == "redpanda-0.redpanda.redpanda.svc.cluster.local:9092"
    assert meta["consumerGroup"] == "todo-app"
    assert meta["authType"] == "none"
    assert meta["maxMessageBytes"] == "1024000"
    assert "kubectl apply -f" in runner.calls[0]
    assert "dapr/components/pubsub-kafka.yaml" in runner.calls[0]


def test_setup_pubsub_yaml_is_block_style_with_insertion_order_preserved(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    tool.setup_pubsub(_Args(brokers=None, consumer_group=None, namespace=None))
    text = (tmp_path / "dapr" / "components" / "pubsub-kafka.yaml").read_text()
    assert text.count("\n") >= 5  # block style (default_flow_style=False), not a single flow line
    first_md = text.find("metadata:")
    second_md = text.find("metadata:", first_md + 1)
    type_idx = text.find("type: pubsub.kafka")
    assert first_md != -1 and second_md != -1 and type_idx != -1
    assert type_idx < second_md  # spec keys keep dict insertion order (type, version, metadata)


def test_setup_pubsub_is_idempotent_when_run_twice(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    args = _Args(brokers=None, consumer_group=None, namespace=None)
    assert tool.setup_pubsub(args) == 0
    assert tool.setup_pubsub(args) == 0  # components_dir.mkdir must tolerate already existing
    assert (tmp_path / "dapr" / "components" / "pubsub-kafka.yaml").exists()


def test_setup_pubsub_honors_custom_args(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    args = _Args(brokers="broker1:9092,broker2:9092", consumer_group="my-group", namespace="ns1")
    tool.setup_pubsub(args)
    doc = yaml.safe_load((tmp_path / "dapr" / "components" / "pubsub-kafka.yaml").read_text())
    meta = {m["name"]: m["value"] for m in doc["spec"]["metadata"]}
    assert meta["brokers"] == "broker1:9092,broker2:9092"
    assert meta["consumerGroup"] == "my-group"
    assert doc["metadata"]["namespace"] == "ns1"


def test_setup_pubsub_returns_0_even_when_apply_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "apply error")))
    args = _Args(brokers=None, consumer_group=None, namespace=None)
    rc = tool.setup_pubsub(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Failed to deploy component" in out
    assert "apply error" in out


def test_setup_state_writes_expected_yaml_with_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    args = _Args(redis_host=None, namespace=None)
    rc = tool.setup_state(args)
    assert rc == 0
    doc = yaml.safe_load((tmp_path / "dapr" / "components" / "state-redis.yaml").read_text())
    assert doc["metadata"]["name"] == "statestore"
    assert doc["metadata"]["namespace"] == "default"
    assert doc["spec"]["type"] == "state.redis"
    meta_by_name = {m["name"]: m for m in doc["spec"]["metadata"]}
    assert meta_by_name["redisHost"]["value"] == "redis-master.redis.svc.cluster.local:6379"
    assert meta_by_name["redisPassword"]["secretKeyRef"] == {"name": "redis", "key": "password"}
    assert meta_by_name["actorStateStore"]["value"] == "true"


def test_setup_state_yaml_is_block_style_with_insertion_order_preserved(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    tool.setup_state(_Args(redis_host=None, namespace=None))
    text = (tmp_path / "dapr" / "components" / "state-redis.yaml").read_text()
    assert text.count("\n") >= 5
    first_md = text.find("metadata:")
    second_md = text.find("metadata:", first_md + 1)
    type_idx = text.find("type: state.redis")
    assert first_md != -1 and second_md != -1 and type_idx != -1
    assert type_idx < second_md


def test_setup_state_is_idempotent_when_run_twice(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    args = _Args(redis_host=None, namespace=None)
    assert tool.setup_state(args) == 0
    assert tool.setup_state(args) == 0
    assert (tmp_path / "dapr" / "components" / "state-redis.yaml").exists()


def test_setup_state_honors_custom_redis_host_and_namespace(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    args = _Args(redis_host="myredis:6380", namespace="prod")
    tool.setup_state(args)
    doc = yaml.safe_load((tmp_path / "dapr" / "components" / "state-redis.yaml").read_text())
    meta_by_name = {m["name"]: m for m in doc["spec"]["metadata"]}
    assert meta_by_name["redisHost"]["value"] == "myredis:6380"
    assert doc["metadata"]["namespace"] == "prod"


def test_setup_state_returns_0_even_when_apply_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "boom")))
    rc = tool.setup_state(_Args(redis_host=None, namespace=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "boom" in out


def test_setup_secrets_writes_expected_yaml(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    rc = tool.setup_secrets(_Args(namespace=None))
    assert rc == 0
    doc = yaml.safe_load((tmp_path / "dapr" / "components" / "secrets-kubernetes.yaml").read_text())
    assert doc["metadata"]["name"] == "kubernetes-secret-store"
    assert doc["metadata"]["namespace"] == "default"
    assert doc["spec"]["type"] == "secretstores.kubernetes"
    assert doc["spec"]["metadata"] == []


def test_setup_secrets_returns_0_even_when_apply_fails(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "secret apply err")))
    rc = tool.setup_secrets(_Args(namespace=None))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Failed to deploy component" in out
    assert "secret apply err" in out


def test_setup_secrets_yaml_is_block_style_with_insertion_order_preserved(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    tool.setup_secrets(_Args(namespace=None))
    text = (tmp_path / "dapr" / "components" / "secrets-kubernetes.yaml").read_text()
    assert text.count("\n") >= 4
    first_md = text.find("metadata:")
    second_md = text.find("metadata:", first_md + 1)
    type_idx = text.find("type: secretstores.kubernetes")
    assert first_md != -1 and second_md != -1 and type_idx != -1
    assert type_idx < second_md


def test_setup_secrets_is_idempotent_when_run_twice(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    args = _Args(namespace=None)
    assert tool.setup_secrets(args) == 0
    assert tool.setup_secrets(args) == 0
    assert (tmp_path / "dapr" / "components" / "secrets-kubernetes.yaml").exists()


def test_setup_secrets_honors_custom_namespace(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    tool.setup_secrets(_Args(namespace="secure-ns"))
    doc = yaml.safe_load((tmp_path / "dapr" / "components" / "secrets-kubernetes.yaml").read_text())
    assert doc["metadata"]["namespace"] == "secure-ns"


def test_setup_cron_writes_expected_yaml_with_default_schedule(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    rc = tool.setup_cron(_Args(schedule=None, namespace=None))
    out = capsys.readouterr().out
    assert rc == 0
    doc = yaml.safe_load((tmp_path / "dapr" / "components" / "cron-reminders.yaml").read_text())
    assert doc["metadata"]["name"] == "reminder-cron"
    assert doc["spec"]["type"] == "bindings.cron"
    assert doc["spec"]["metadata"][0] == {"name": "schedule", "value": "*/5 * * * *"}
    assert "*/5 * * * *" in out


def test_setup_cron_yaml_is_block_style_with_insertion_order_preserved(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    tool.setup_cron(_Args(schedule=None, namespace=None))
    text = (tmp_path / "dapr" / "components" / "cron-reminders.yaml").read_text()
    assert text.count("\n") >= 4
    first_md = text.find("metadata:")
    second_md = text.find("metadata:", first_md + 1)
    type_idx = text.find("type: bindings.cron")
    assert first_md != -1 and second_md != -1 and type_idx != -1
    assert type_idx < second_md


def test_setup_cron_is_idempotent_when_run_twice(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    args = _Args(schedule=None, namespace=None)
    assert tool.setup_cron(args) == 0
    assert tool.setup_cron(args) == 0
    assert (tmp_path / "dapr" / "components" / "cron-reminders.yaml").exists()


def test_setup_cron_honors_custom_schedule(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(0, "", "")))
    tool.setup_cron(_Args(schedule="0 0 * * *", namespace="ns2"))
    doc = yaml.safe_load((tmp_path / "dapr" / "components" / "cron-reminders.yaml").read_text())
    assert doc["spec"]["metadata"][0]["value"] == "0 0 * * *"
    assert doc["metadata"]["namespace"] == "ns2"


def test_setup_cron_returns_0_even_when_apply_fails(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(tool, "run_command", RecordingRunner(default=(1, "", "err")))
    rc = tool.setup_cron(_Args(schedule=None, namespace=None))
    assert rc == 0


# ---------------------------------------------------------------------------
# inject_sidecar
# ---------------------------------------------------------------------------

def test_inject_sidecar_missing_file_returns_1(tmp_path, capsys):
    missing = tmp_path / "nope.yaml"
    args = _Args(deployment_file=str(missing), app_id="foo", app_port="8000", output=None)
    rc = tool.inject_sidecar(args)
    out = capsys.readouterr().out
    assert rc == 1
    assert "not found" in out


def test_inject_sidecar_adds_annotations_and_overwrites_input_by_default(tmp_path, capsys):
    dep_file = tmp_path / "deploy.yaml"
    dep_file.write_text(yaml.dump({
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "spec": {"template": {"metadata": {"annotations": {"existing": "keep"}}}},
    }))
    args = _Args(deployment_file=str(dep_file), app_id="my-app", app_port="9000", output=None)
    rc = tool.inject_sidecar(args)
    out = capsys.readouterr().out
    assert rc == 0
    doc = yaml.safe_load(dep_file.read_text())
    ann = doc["spec"]["template"]["metadata"]["annotations"]
    assert ann["existing"] == "keep"
    assert ann["dapr.io/enabled"] == "true"
    assert ann["dapr.io/app-id"] == "my-app"
    assert ann["dapr.io/app-port"] == "9000"
    assert ann["dapr.io/app-protocol"] == "http"
    assert "my-app" in out


def test_inject_sidecar_yaml_is_block_style_with_insertion_order_preserved(tmp_path):
    dep_file = tmp_path / "deploy.yaml"
    dep_file.write_text(yaml.dump({
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "spec": {"template": {"metadata": {"annotations": {"existing": "keep"}}}},
    }))
    args = _Args(deployment_file=str(dep_file), app_id="my-app", app_port="9000", output=None)
    tool.inject_sidecar(args)
    text = dep_file.read_text()
    assert text.count("\n") >= 5  # block style, not a single flow-style line
    idx_enabled = text.find("dapr.io/enabled")
    idx_appid = text.find("dapr.io/app-id")
    assert idx_enabled != -1 and idx_appid != -1
    assert idx_enabled < idx_appid  # dict insertion order preserved (enabled set before app-id)


def test_inject_sidecar_writes_to_separate_output_leaving_input_untouched(tmp_path):
    dep_file = tmp_path / "deploy.yaml"
    out_file = tmp_path / "deploy.out.yaml"
    original = {"apiVersion": "apps/v1", "kind": "Deployment"}
    dep_file.write_text(yaml.dump(original))
    args = _Args(deployment_file=str(dep_file), app_id="svc", app_port="8000", output=str(out_file))
    tool.inject_sidecar(args)
    assert yaml.safe_load(dep_file.read_text()) == original
    out_doc = yaml.safe_load(out_file.read_text())
    assert out_doc["spec"]["template"]["metadata"]["annotations"]["dapr.io/app-id"] == "svc"


def test_inject_sidecar_builds_missing_nested_keys_from_empty_deployment(tmp_path):
    dep_file = tmp_path / "empty.yaml"
    dep_file.write_text(yaml.dump({}))
    args = _Args(deployment_file=str(dep_file), app_id=None, app_port=None, output=None)
    rc = tool.inject_sidecar(args)
    assert rc == 0
    doc = yaml.safe_load(dep_file.read_text())
    ann = doc["spec"]["template"]["metadata"]["annotations"]
    assert ann["dapr.io/app-id"] == "todo-app"
    assert ann["dapr.io/app-port"] == "8000"


# ---------------------------------------------------------------------------
# run_tests_cmd
# ---------------------------------------------------------------------------

def test_run_tests_cmd_all_healthy_returns_0(monkeypatch, capsys):
    monkeypatch.setattr(tool, "check_prerequisites", lambda a: 0)
    runner = RecordingRunner({
        "kubectl get pods -n dapr-system": (0, "dapr-operator Running", ""),
        "kubectl get components": (0, "NAME\ncomp1\ncomp2\n", ""),
        "kubectl get component kafka-pubsub": (0, "kafka-pubsub", ""),
        "kubectl get component statestore": (0, "statestore", ""),
    }, default=(0, "pod1\ttrue\npod2\ttrue\npod3\tfalse\n", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Total tests: 6" in out
    assert "Passed: 6" in out
    assert "All tests passed" in out
    assert "2 components found" in out
    assert "2 pods with Dapr sidecars" in out


def test_run_tests_cmd_prerequisites_failure_causes_overall_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool, "check_prerequisites", lambda a: 1)
    runner = RecordingRunner(default=(0, "dapr-operator Running", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "tests failed" in out


def test_run_tests_cmd_components_command_failure_warns_but_still_passes(monkeypatch, capsys):
    monkeypatch.setattr(tool, "check_prerequisites", lambda a: 0)
    runner = RecordingRunner({
        "kubectl get pods -n dapr-system": (0, "dapr-x", ""),
        "kubectl get components": (1, "", "no such resource"),
    }, default=(0, "", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "No components found" in out


def test_run_tests_cmd_dapr_not_installed_causes_overall_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool, "check_prerequisites", lambda a: 0)
    runner = RecordingRunner({
        "kubectl get pods -n dapr-system": (1, "", "not found"),
    }, default=(0, "", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 1
    assert "Dapr not installed" in out


def test_run_tests_cmd_pubsub_and_statestore_not_configured_still_passes(monkeypatch, capsys):
    monkeypatch.setattr(tool, "check_prerequisites", lambda a: 0)
    runner = RecordingRunner({
        "kubectl get pods -n dapr-system": (0, "dapr-x", ""),
        "kubectl get components": (0, "", ""),
        "kubectl get component kafka-pubsub": (1, "", ""),
        "kubectl get component statestore": (1, "", ""),
    }, default=(1, "", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.run_tests_cmd(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "Pub/Sub not configured" in out
    assert "State store not configured" in out
    assert "No Dapr sidecars found" in out


# ---------------------------------------------------------------------------
# troubleshoot
# ---------------------------------------------------------------------------

def test_troubleshoot_prints_stdout_and_common_issues(monkeypatch, capsys):
    runner = RecordingRunner(default=(0, "pod-a\tRunning", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    rc = tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "pod-a" in out
    assert "Common Issues & Fixes" in out
    assert "CrashLoopBackOff" in out


def test_troubleshoot_warns_when_no_sidecars_found(monkeypatch, capsys):
    runner = RecordingRunner({
        "jsonpath": (0, "   ", ""),
    }, default=(0, "some output", ""))
    monkeypatch.setattr(tool, "run_command", runner)
    tool.troubleshoot(_Args())
    out = capsys.readouterr().out
    assert "No pods with Dapr sidecars found" in out


# ---------------------------------------------------------------------------
# main() / CLI dispatch
# ---------------------------------------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_dispatches_check_prerequisites(monkeypatch):
    called = {}

    def fake_check(a):
        called["hit"] = True
        return 0

    monkeypatch.setattr(tool, "check_prerequisites", fake_check)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check-prerequisites"])
    rc = tool.main()
    assert rc == 0
    assert called.get("hit")


def test_main_dispatches_init_dapr_with_parsed_flags(monkeypatch):
    captured = {}

    def fake_init(a):
        captured["namespace"] = a.namespace
        captured["enable_ha"] = a.enable_ha
        captured["dev_mode"] = a.dev_mode
        return 0

    monkeypatch.setattr(tool, "init_dapr", fake_init)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "init-dapr", "--namespace", "foo", "--enable-ha", "--dev-mode"])
    rc = tool.main()
    assert rc == 0
    assert captured == {"namespace": "foo", "enable_ha": True, "dev_mode": True}


def test_main_dispatches_setup_pubsub_with_parsed_flags(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "setup_pubsub", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "setup-pubsub", "--brokers", "b:9092", "--consumer-group", "g", "--namespace", "ns",
    ])
    tool.main()
    assert captured["brokers"] == "b:9092"
    assert captured["consumer_group"] == "g"
    assert captured["namespace"] == "ns"


def test_main_dispatches_setup_state_with_parsed_flags(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "setup_state", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-state", "--redis-host", "h:1", "--namespace", "ns"])
    tool.main()
    assert captured["redis_host"] == "h:1"
    assert captured["namespace"] == "ns"


def test_main_dispatches_setup_secrets_with_parsed_flags(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "setup_secrets", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-secrets", "--namespace", "ns"])
    tool.main()
    assert captured["namespace"] == "ns"


def test_main_dispatches_setup_cron_with_parsed_flags(monkeypatch):
    captured = {}
    monkeypatch.setattr(tool, "setup_cron", lambda a: captured.update(vars(a)) or 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-cron", "--schedule", "0 0 * * *", "--namespace", "ns"])
    tool.main()
    assert captured["schedule"] == "0 0 * * *"
    assert captured["namespace"] == "ns"


def test_main_dispatches_test_subcommand(monkeypatch):
    monkeypatch.setattr(tool, "run_tests_cmd", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "test"])
    assert tool.main() == 0


def test_main_dispatches_troubleshoot_subcommand(monkeypatch):
    monkeypatch.setattr(tool, "troubleshoot", lambda a: 0)
    monkeypatch.setattr(_sys, "argv", ["tool.py", "troubleshoot"])
    assert tool.main() == 0


def test_main_inject_sidecar_end_to_end_real_function(monkeypatch, tmp_path):
    dep_file = tmp_path / "deploy.yaml"
    dep_file.write_text(yaml.dump({"apiVersion": "apps/v1"}))
    monkeypatch.setattr(_sys, "argv", [
        "tool.py", "inject-sidecar", "--deployment-file", str(dep_file), "--app-id", "abc",
    ])
    rc = tool.main()
    assert rc == 0
    doc = yaml.safe_load(dep_file.read_text())
    assert doc["spec"]["template"]["metadata"]["annotations"]["dapr.io/app-id"] == "abc"


def test_main_inject_sidecar_missing_required_deployment_file_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "inject-sidecar", "--app-id", "abc"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_inject_sidecar_missing_required_app_id_exits(monkeypatch, tmp_path):
    dep_file = tmp_path / "deploy.yaml"
    dep_file.write_text(yaml.dump({}))
    monkeypatch.setattr(_sys, "argv", ["tool.py", "inject-sidecar", "--deployment-file", str(dep_file)])
    with pytest.raises(SystemExit):
        tool.main()


# ---------------------------------------------------------------------------
# subprocess smoke test (real __main__ entrypoint, no cluster/network touched)
# ---------------------------------------------------------------------------

def test_cli_subprocess_smoke_no_command_prints_usage_and_exits_1():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run([_sys.executable, str(script)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 1
    assert "usage" in proc.stdout.lower()


def test_cli_subprocess_smoke_inject_sidecar_end_to_end(tmp_path):
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    dep_file = tmp_path / "deploy.yaml"
    dep_file.write_text(yaml.dump({"apiVersion": "apps/v1"}))
    proc = subprocess.run(
        [_sys.executable, str(script), "inject-sidecar", "--deployment-file", str(dep_file), "--app-id", "svc-x"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    doc = yaml.safe_load(dep_file.read_text())
    assert doc["spec"]["template"]["metadata"]["annotations"]["dapr.io/app-id"] == "svc-x"
