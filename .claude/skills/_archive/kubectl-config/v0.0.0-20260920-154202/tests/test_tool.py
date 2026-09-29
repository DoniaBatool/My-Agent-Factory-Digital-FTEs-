import importlib.util as _ilu
import json as _json
import subprocess
import sys as _sys
from pathlib import Path

import pytest

_spec = _ilu.spec_from_file_location(
    "kubectl_config_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
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
    pass


def make_fake_run(rules, default=None):
    """Emulates real subprocess.run(list_cmd, check=, capture_output=, text=)
    semantics: on failure with check=True it raises CalledProcessError with
    .stdout/.stderr populated only when capture_output was requested (exactly
    like the real subprocess module); otherwise returns a CompletedProcess-like
    object."""
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
# run_cmd
# --------------------------------------------------------------------------

def test_run_cmd_capture_true_success(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("kubectl foo", _Proc(0, "out", ""))]))
    code, out, err = tool.run_cmd(["kubectl", "foo"])
    assert (code, out, err) == (0, "out", "")


def test_run_cmd_capture_false_returns_empty_strings(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("kubectl foo", _Proc(0, "ignored"))]))
    code, out, err = tool.run_cmd(["kubectl", "foo"], capture=False)
    assert (code, out, err) == (0, "", "")


def test_run_cmd_called_process_error_returns_captured_output(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl bad", _Proc(1, "partial", "boom"))]))
    code, out, err = tool.run_cmd(["kubectl", "bad"])
    assert code == 1
    assert out == "partial"
    assert err == "boom"


def test_run_cmd_check_false_suppresses_exception_on_uncaptured_failure(monkeypatch):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl fails", _Proc(3, "x", "y"))]))
    code, out, err = tool.run_cmd(["kubectl", "fails"], check=False, capture=False)
    assert (code, out, err) == (3, "", "")


def test_run_cmd_file_not_found_returns_127(monkeypatch):
    def raise_fnf(cmd, check=True, capture_output=False, text=False):
        raise FileNotFoundError()
    monkeypatch.setattr(tool.subprocess, "run", raise_fnf)
    code, out, err = tool.run_cmd(["ocinotinstalled", "--version"])
    assert code == 127
    assert out == ""
    assert err == "Command not found: ocinotinstalled"


# --------------------------------------------------------------------------
# get_os
# --------------------------------------------------------------------------

def test_get_os_darwin_maps_to_macos(monkeypatch):
    monkeypatch.setattr(tool.platform, "system", lambda: "Darwin")
    assert tool.get_os() == "macos"


def test_get_os_linux(monkeypatch):
    monkeypatch.setattr(tool.platform, "system", lambda: "Linux")
    assert tool.get_os() == "linux"


def test_get_os_windows(monkeypatch):
    monkeypatch.setattr(tool.platform, "system", lambda: "Windows")
    assert tool.get_os() == "windows"


def test_get_os_unknown_platform_returns_unknown(monkeypatch):
    monkeypatch.setattr(tool.platform, "system", lambda: "PlayStationOS")
    assert tool.get_os() == "unknown"


# --------------------------------------------------------------------------
# cmd_check
# --------------------------------------------------------------------------

def test_cmd_check_kubectl_not_installed_returns_false(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl version --client --output=json", _Proc(1))]))
    result = tool.cmd_check(_Args())
    out = capsys.readouterr().out
    assert result is False
    assert "kubectl not installed" in out


def test_cmd_check_valid_json_prints_version(monkeypatch, capsys):
    version_json = _json.dumps({"clientVersion": {"gitVersion": "v1.29.1"}})
    rules = [
        ("kubectl version --client --output=json", _Proc(0, version_json)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl config current-context", _Proc(0, "my-context\n")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    result = tool.cmd_check(_Args())
    out = capsys.readouterr().out
    assert result is True
    assert "kubectl installed: v1.29.1" in out
    assert "Connected to Kubernetes cluster" in out
    assert "my-context" in out


def test_cmd_check_malformed_json_falls_back_to_generic_message(monkeypatch, capsys):
    rules = [
        ("kubectl version --client --output=json", _Proc(0, "not-json")),
        ("kubectl cluster-info", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    result = tool.cmd_check(_Args())
    out = capsys.readouterr().out
    assert result is True
    assert "kubectl installed" in out
    assert "v1." not in out


def test_cmd_check_cluster_not_connected_warns_but_still_returns_true(monkeypatch, capsys):
    version_json = _json.dumps({"clientVersion": {"gitVersion": "v1.30.0"}})
    rules = [
        ("kubectl version --client --output=json", _Proc(0, version_json)),
        ("kubectl cluster-info", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    result = tool.cmd_check(_Args())
    out = capsys.readouterr().out
    assert result is True
    assert "Not connected to any cluster" in out


def test_cmd_check_connected_but_current_context_lookup_fails(monkeypatch, capsys):
    version_json = _json.dumps({"clientVersion": {"gitVersion": "v1.30.0"}})
    rules = [
        ("kubectl version --client --output=json", _Proc(0, version_json)),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl config current-context", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    result = tool.cmd_check(_Args())
    out = capsys.readouterr().out
    assert result is True
    assert "Current context" not in out


# --------------------------------------------------------------------------
# cmd_install
# --------------------------------------------------------------------------

def test_cmd_install_macos_no_homebrew(monkeypatch, capsys):
    monkeypatch.setattr(tool, "get_os", lambda: "macos")
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("brew --version", _Proc(1))]))
    tool.cmd_install(_Args())
    out = capsys.readouterr().out
    assert "Homebrew not installed" in out


def test_cmd_install_macos_success(monkeypatch, capsys):
    monkeypatch.setattr(tool, "get_os", lambda: "macos")
    rules = [("brew --version", _Proc(0)), ("brew install kubectl", _Proc(0))]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_install(_Args())
    out = capsys.readouterr().out
    assert "kubectl installed successfully" in out


def test_cmd_install_macos_brew_install_fails(monkeypatch, capsys):
    monkeypatch.setattr(tool, "get_os", lambda: "macos")
    rules = [("brew --version", _Proc(0)), ("brew install kubectl", _Proc(1))]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_install(_Args())
    out = capsys.readouterr().out
    assert "Failed to install kubectl" in out


def test_cmd_install_linux_prints_instructions(monkeypatch, capsys):
    monkeypatch.setattr(tool, "get_os", lambda: "linux")
    tool.cmd_install(_Args())
    out = capsys.readouterr().out
    assert "dl.k8s.io" in out


def test_cmd_install_windows_prints_instructions(monkeypatch, capsys):
    monkeypatch.setattr(tool, "get_os", lambda: "windows")
    tool.cmd_install(_Args())
    out = capsys.readouterr().out
    assert "choco install kubernetes-cli" in out


def test_cmd_install_unknown_os_prints_error(monkeypatch, capsys):
    monkeypatch.setattr(tool, "get_os", lambda: "unknown")
    tool.cmd_install(_Args())
    out = capsys.readouterr().out
    assert "Unsupported OS: unknown" in out


# --------------------------------------------------------------------------
# cmd_setup_oke
# --------------------------------------------------------------------------

def test_cmd_setup_oke_without_oci_cli(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("oci --version", _Proc(1))]))
    tool.cmd_setup_oke(_Args())
    out = capsys.readouterr().out
    assert "OCI CLI not installed" in out


def test_cmd_setup_oke_success_after_input(monkeypatch, capsys):
    rules = [("oci --version", _Proc(0)), ("kubectl get nodes", _Proc(0, "node-1  Ready"))]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    tool.cmd_setup_oke(_Args())
    out = capsys.readouterr().out
    assert "successfully configured for OKE" in out
    assert "node-1" in out


def test_cmd_setup_oke_kubectl_verification_fails(monkeypatch, capsys):
    rules = [("oci --version", _Proc(0)), ("kubectl get nodes", _Proc(1, "", "no route"))]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    monkeypatch.setattr("builtins.input", lambda *a, **k: "")
    tool.cmd_setup_oke(_Args())
    out = capsys.readouterr().out
    assert "Failed to connect to cluster" in out
    assert "no route" in out


# --------------------------------------------------------------------------
# cmd_setup_gke / cmd_setup_aks / cmd_setup_eks
# --------------------------------------------------------------------------

def test_cmd_setup_gke_without_cli(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("gcloud --version", _Proc(1))]))
    tool.cmd_setup_gke(_Args())
    out = capsys.readouterr().out
    assert "gcloud CLI not installed" in out


def test_cmd_setup_gke_with_cli(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("gcloud --version", _Proc(0))]))
    tool.cmd_setup_gke(_Args())
    out = capsys.readouterr().out
    assert "gcloud CLI installed" in out
    assert "get-credentials" in out


def test_cmd_setup_aks_without_cli(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("az --version", _Proc(1))]))
    tool.cmd_setup_aks(_Args())
    out = capsys.readouterr().out
    assert "Azure CLI not installed" in out


def test_cmd_setup_aks_with_cli(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("az --version", _Proc(0))]))
    tool.cmd_setup_aks(_Args())
    out = capsys.readouterr().out
    assert "Azure CLI installed" in out
    assert "aks get-credentials" in out


def test_cmd_setup_eks_without_cli(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("aws --version", _Proc(1))]))
    tool.cmd_setup_eks(_Args())
    out = capsys.readouterr().out
    assert "AWS CLI not installed" in out


def test_cmd_setup_eks_with_cli(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("aws --version", _Proc(0))]))
    tool.cmd_setup_eks(_Args())
    out = capsys.readouterr().out
    assert "AWS CLI installed" in out
    assert "update-kubeconfig" in out


# --------------------------------------------------------------------------
# cmd_contexts
# --------------------------------------------------------------------------

def test_cmd_contexts_success(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl config get-contexts", _Proc(0, "CURRENT   NAME\n*         ctx-a"))]))
    tool.cmd_contexts(_Args())
    out = capsys.readouterr().out
    assert "ctx-a" in out
    assert "Switch context" in out


def test_cmd_contexts_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl config get-contexts", _Proc(1, "", "no config"))]))
    tool.cmd_contexts(_Args())
    out = capsys.readouterr().out
    assert "Failed to get contexts" in out
    assert "no config" in out


# --------------------------------------------------------------------------
# cmd_switch
# --------------------------------------------------------------------------

def test_cmd_switch_success_and_connected(monkeypatch, capsys):
    rules = [
        ("kubectl config use-context prod", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_switch(_Args(context="prod"))
    out = capsys.readouterr().out
    assert "Switched to context: prod" in out
    assert "Connected to cluster" in out


def test_cmd_switch_success_but_cluster_unreachable(monkeypatch, capsys):
    rules = [
        ("kubectl config use-context prod", _Proc(0)),
        ("kubectl cluster-info", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_switch(_Args(context="prod"))
    out = capsys.readouterr().out
    assert "Context switched but cluster not reachable" in out


def test_cmd_switch_failure(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl config use-context prod", _Proc(1, "", "no such context"))]))
    tool.cmd_switch(_Args(context="prod"))
    out = capsys.readouterr().out
    assert "Failed to switch context" in out
    assert "no such context" in out


# --------------------------------------------------------------------------
# cmd_verify
# --------------------------------------------------------------------------

def test_cmd_verify_no_current_context_returns_early(monkeypatch, capsys):
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl config current-context", _Proc(1))]))
    tool.cmd_verify(_Args())
    out = capsys.readouterr().out
    assert "No current context" in out
    assert "Cluster info" not in out


def test_cmd_verify_cluster_unreachable_returns_early(monkeypatch, capsys):
    rules = [
        ("kubectl config current-context", _Proc(0, "ctx-a")),
        ("kubectl cluster-info", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_verify(_Args())
    out = capsys.readouterr().out
    assert "Cannot connect to cluster" in out
    assert "Cluster nodes" not in out


def test_cmd_verify_full_success(monkeypatch, capsys):
    rules = [
        ("kubectl config current-context", _Proc(0, "ctx-a")),
        ("kubectl cluster-info", _Proc(0, "Kubernetes control plane is running")),
        ("kubectl get nodes", _Proc(0, "node-1  Ready")),
        ("kubectl get namespaces", _Proc(0, "default  Active")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_verify(_Args())
    out = capsys.readouterr().out
    assert "verification complete" in out
    assert "node-1" in out
    assert "default" in out


def test_cmd_verify_nodes_and_namespaces_unavailable_still_completes(monkeypatch, capsys):
    rules = [
        ("kubectl config current-context", _Proc(0, "ctx-a")),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(1)),
        ("kubectl get namespaces", _Proc(1)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_verify(_Args())
    out = capsys.readouterr().out
    assert "Cannot get nodes" in out
    assert "Cannot get namespaces" in out
    assert "verification complete" in out


# --------------------------------------------------------------------------
# cmd_kubeconfig_info
# --------------------------------------------------------------------------

def test_cmd_kubeconfig_info_missing_file(monkeypatch, tmp_path, capsys):
    missing = tmp_path / "does-not-exist" / "config"
    monkeypatch.setenv("KUBECONFIG", str(missing))
    tool.cmd_kubeconfig_info(_Args())
    out = capsys.readouterr().out
    assert "Kubeconfig file not found" in out


def test_cmd_kubeconfig_info_existing_file(monkeypatch, tmp_path, capsys):
    kc = tmp_path / "config"
    kc.write_text("apiVersion: v1\nkind: Config\n")
    monkeypatch.setenv("KUBECONFIG", str(kc))
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl config view --minify", _Proc(0, "current-context: ctx-a"))]))
    tool.cmd_kubeconfig_info(_Args())
    out = capsys.readouterr().out
    assert "Kubeconfig file:" in out
    assert "Size:" in out
    assert "ctx-a" in out


# --------------------------------------------------------------------------
# cmd_troubleshoot
# --------------------------------------------------------------------------

def test_cmd_troubleshoot_no_issues(monkeypatch, tmp_path, capsys):
    kc = tmp_path / "config"
    kc.write_text("kind: Config\n")
    monkeypatch.setenv("KUBECONFIG", str(kc))
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl config current-context", _Proc(0, "ctx-a")),
        ("kubectl cluster-info", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_troubleshoot(_Args())
    out = capsys.readouterr().out
    assert "No issues found" in out


def test_cmd_troubleshoot_reports_all_issues(monkeypatch, tmp_path, capsys):
    missing_kc = tmp_path / "nope" / "config"
    monkeypatch.setenv("KUBECONFIG", str(missing_kc))
    rules = [
        ("kubectl version --client", _Proc(1)),
        ("kubectl config current-context", _Proc(1)),
        ("kubectl cluster-info", _Proc(1, "", "Connection refused")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_troubleshoot(_Args())
    out = capsys.readouterr().out
    assert "kubectl not installed" in out
    assert "Kubeconfig not found" in out
    assert "No current context" in out
    assert "Cannot connect to cluster" in out
    assert "VPN required but not connected" in out
    assert "Issues found:" in out
    assert "Suggested fixes:" in out


def test_cmd_troubleshoot_connection_failure_without_refused_keyword_skips_causes(monkeypatch, tmp_path, capsys):
    kc = tmp_path / "config"
    kc.write_text("kind: Config\n")
    monkeypatch.setenv("KUBECONFIG", str(kc))
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl config current-context", _Proc(0, "ctx-a")),
        ("kubectl cluster-info", _Proc(1, "", "some other network error")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.cmd_troubleshoot(_Args())
    out = capsys.readouterr().out
    assert "Cannot connect to cluster" in out
    assert "Possible causes" not in out


# --------------------------------------------------------------------------
# main() / CLI dispatch
# --------------------------------------------------------------------------

def test_main_no_command_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py"])
    with pytest.raises(SystemExit) as exc:
        tool.main()
    assert exc.value.code == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_switch_missing_positional_context_exits(monkeypatch):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "switch"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_check_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "check"])
    rules = [
        ("kubectl version --client --output=json", _Proc(0, _json.dumps({"clientVersion": {"gitVersion": "v1.29.0"}}))),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl config current-context", _Proc(0, "ctx-a")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.main()
    assert "v1.29.0" in capsys.readouterr().out


def test_main_contexts_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "contexts"])
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl config get-contexts", _Proc(0, "ctx-a"))]))
    tool.main()
    assert "ctx-a" in capsys.readouterr().out


def test_main_switch_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "switch", "staging"])
    rules = [
        ("kubectl config use-context staging", _Proc(0)),
        ("kubectl cluster-info", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.main()
    assert "Switched to context: staging" in capsys.readouterr().out


def test_main_verify_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "verify"])
    rules = [
        ("kubectl config current-context", _Proc(0, "ctx-a")),
        ("kubectl cluster-info", _Proc(0)),
        ("kubectl get nodes", _Proc(0, "node-1")),
        ("kubectl get namespaces", _Proc(0, "default")),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.main()
    assert "verification complete" in capsys.readouterr().out


def test_main_info_dispatch(monkeypatch, tmp_path, capsys):
    kc = tmp_path / "config"
    kc.write_text("kind: Config\n")
    monkeypatch.setenv("KUBECONFIG", str(kc))
    monkeypatch.setattr(_sys, "argv", ["tool.py", "info"])
    monkeypatch.setattr(tool.subprocess, "run",
                         make_fake_run([("kubectl config view --minify", _Proc(0, "ctx info"))]))
    tool.main()
    assert "Kubeconfig file:" in capsys.readouterr().out


def test_main_troubleshoot_dispatch(monkeypatch, tmp_path, capsys):
    kc = tmp_path / "config"
    kc.write_text("kind: Config\n")
    monkeypatch.setenv("KUBECONFIG", str(kc))
    monkeypatch.setattr(_sys, "argv", ["tool.py", "troubleshoot"])
    rules = [
        ("kubectl version --client", _Proc(0)),
        ("kubectl config current-context", _Proc(0, "ctx-a")),
        ("kubectl cluster-info", _Proc(0)),
    ]
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run(rules))
    tool.main()
    assert "No issues found" in capsys.readouterr().out


def test_main_setup_oke_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-oke"])
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("oci --version", _Proc(1))]))
    tool.main()
    assert "OCI CLI not installed" in capsys.readouterr().out


def test_main_setup_gke_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-gke"])
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("gcloud --version", _Proc(0))]))
    tool.main()
    assert "gcloud CLI installed" in capsys.readouterr().out


def test_main_setup_aks_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-aks"])
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("az --version", _Proc(0))]))
    tool.main()
    assert "Azure CLI installed" in capsys.readouterr().out


def test_main_setup_eks_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "setup-eks"])
    monkeypatch.setattr(tool.subprocess, "run", make_fake_run([("aws --version", _Proc(0))]))
    tool.main()
    assert "AWS CLI installed" in capsys.readouterr().out


def test_main_install_dispatch(monkeypatch, capsys):
    monkeypatch.setattr(_sys, "argv", ["tool.py", "install"])
    monkeypatch.setattr(tool, "get_os", lambda: "linux")
    tool.main()
    assert "dl.k8s.io" in capsys.readouterr().out


def test_subprocess_cli_smoke_runs_as_main_entrypoint():
    # "contexts" only reads the local kubeconfig (no network call to a real
    # cluster, no mutation of kubectl state), so it is safe to run for real.
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    proc = subprocess.run(
        [_sys.executable, str(script), "contexts"],
        capture_output=True, text=True, timeout=30,
    )
    assert proc.returncode == 0
    assert "Listing kubectl contexts" in proc.stdout
