#!/usr/bin/env python3
"""
Grafana Expert Tool - Complete A-Z Grafana management

Commands: check-prerequisites, install, setup-datasource, create-dashboard,
          provision, configure-alerting, test, troubleshoot

v2.0.0: merges the thorough multi-path prerequisite/OS-aware checks from
the pre-2026-02-13 implementation (recovered from grafana-expert.backup-20260211,
which had silently replaced this with a 1-real-check-pretending-to-be-6 stub)
with a genuinely complete 6-check `test` command and testable pure-logic
helpers for every JSON/YAML payload this tool builds.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys

class Colors:
    GREEN, RED, YELLOW, BLUE, BOLD, END = '\033[92m', '\033[91m', '\033[93m', '\033[94m', '\033[1m', '\033[0m'

def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")
def print_info(msg): print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")
def print_header(msg): print(f"\n{Colors.BOLD}==> {msg}{Colors.END}")


def run_command(cmd, timeout=300):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


# ---------------------------------------------------------------------------
# Pure / testable helpers (no subprocess, no network) -----------------------
# ---------------------------------------------------------------------------

def detect_os():
    return platform.system().lower()  # 'darwin', 'linux', 'windows'


def find_first_existing(paths):
    """Return the first path in `paths` that exists on disk, else None.
    Split out as its own function so prerequisite/config-discovery logic is
    unit-testable without touching the real filesystem."""
    for p in paths:
        if os.path.exists(p):
            return p
    return None


GRAFANA_CONF_PATHS = [
    "/etc/grafana/grafana.ini",
    "/usr/local/etc/grafana/grafana.ini",
    "/opt/homebrew/etc/grafana/grafana.ini",
]

GRAFANA_PROVISIONING_PATHS = [
    "/etc/grafana/provisioning",
    "/usr/local/etc/grafana/provisioning",
    "/opt/homebrew/etc/grafana/provisioning",
]


def build_install_command(os_name: str, method: str) -> str:
    """Pick the right install command for the detected OS + method.
    Pure function so install() itself stays a thin wrapper around it."""
    if method == "docker":
        return "docker run -d -p 3000:3000 --name grafana grafana/grafana:latest"
    if "darwin" in os_name:
        return "brew install grafana"
    if "linux" in os_name:
        return (
            "sudo apt-get install -y apt-transport-https software-properties-common && "
            "sudo apt-get install -y grafana"
        )
    raise ValueError(f"Unsupported OS for native install: {os_name}")


def build_datasource_payload(name="Prometheus", url="http://localhost:9090", ds_type="prometheus", is_default=True):
    return {"name": name, "type": ds_type, "url": url, "access": "proxy", "isDefault": is_default}


def build_dashboard_json(title: str, panel_titles):
    """Minimal, valid Grafana dashboard JSON with one panel per title."""
    panels = []
    for i, ptitle in enumerate(panel_titles):
        panels.append({
            "id": i + 1,
            "title": ptitle,
            "type": "timeseries",
            "gridPos": {"h": 8, "w": 12, "x": (i % 2) * 12, "y": (i // 2) * 8},
        })
    return {"dashboard": {"title": title, "panels": panels, "schemaVersion": 39}, "overwrite": True}


def build_provisioning_yaml(datasources):
    """Return provisioning YAML text for a list of {name,type,url} dicts.
    Hand-built (not yaml.dump) so this has zero third-party dependency."""
    lines = ["apiVersion: 1", "datasources:"]
    for ds in datasources:
        lines.append(f"  - name: {ds['name']}")
        lines.append(f"    type: {ds['type']}")
        lines.append(f"    url: {ds['url']}")
        lines.append("    access: proxy")
        lines.append(f"    isDefault: {str(ds.get('isDefault', False)).lower()}")
    return "\n".join(lines) + "\n"


def build_alert_rule(name: str, condition: str, for_duration: str = "5m"):
    return {
        "title": name,
        "condition": condition,
        "for": for_duration,
        "annotations": {"summary": f"Alert: {name}"},
        "labels": {"severity": "warning"},
    }


def diagnose(check_results):
    """Map failed named checks -> remediation strings. Pure + testable so
    troubleshoot() logic can be verified without a live Grafana instance."""
    remediation = {
        "binary": "Grafana binary not found. Run: python3 tool.py install --method docker",
        "config": "No grafana.ini found in standard locations. Reinstall or set GF_PATHS_CONFIG.",
        "api": "Grafana API unreachable at localhost:3000. Check the service is running.",
        "datasource_api": "Datasource API call failed. Verify Grafana is up and credentials are correct.",
        "provisioning_dir": "No provisioning directory found/writable. Create one or pass --output-dir.",
        "alerting_api": "Alerting API unreachable. Requires Grafana >= 9 with unified alerting enabled.",
    }
    issues = []
    for name, status, _detail in check_results:
        if status != "pass" and name in remediation:
            issues.append(remediation[name])
    return issues


# ---------------------------------------------------------------------------
# Commands --------------------------------------------------------------
# ---------------------------------------------------------------------------

def check_prerequisites(args):
    print_header("Checking Grafana Prerequisites")
    issues = []

    if shutil.which("grafana-server"):
        print_success("Grafana binary found on PATH")
    else:
        print_error("Grafana binary not found")
        issues.append("Install with: python3 tool.py install --method docker")

    conf = find_first_existing(GRAFANA_CONF_PATHS)
    if conf:
        print_success(f"Configuration found: {conf}")
    else:
        print_warning("No grafana.ini found in standard locations")
        issues.append("No config file found in: " + ", ".join(GRAFANA_CONF_PATHS))

    prov = find_first_existing(GRAFANA_PROVISIONING_PATHS)
    if prov:
        print_success(f"Provisioning directory: {prov}")
    else:
        print_warning("No provisioning directory found in standard locations")

    print_header("Prerequisites Summary")
    if not issues:
        print_success("All prerequisites met!")
        return 0
    for issue in issues:
        print_error(f"  - {issue}")
    return 1


def install(args):
    print_header("Installing Grafana")
    os_name = detect_os()
    method = args.method or "docker"
    try:
        cmd = build_install_command(os_name, method)
    except ValueError as e:
        print_error(str(e))
        return 1
    print_info(f"Running: {cmd}")
    code, _out, err = run_command(cmd, timeout=600)
    if code == 0:
        print_success("Grafana installed/started")
        if method == "docker":
            print_info("Default URL: http://localhost:3000 (admin/admin)")
        return 0
    print_error(f"Install failed: {err.strip()[:300]}")
    return 1


def setup_datasource(args):
    print_header("Setting up Datasource")
    payload = build_datasource_payload(
        name=args.name or "Prometheus",
        url=args.url or "http://localhost:9090",
        ds_type=args.type or "prometheus",
    )
    cmd = (
        f"curl -s -o /dev/null -w '%{{http_code}}' -X POST http://admin:admin@localhost:3000/api/datasources "
        f"-H 'Content-Type: application/json' -d '{json.dumps(payload)}'"
    )
    code, out, _err = run_command(cmd)
    if code == 0 and out.strip() in ("200", "201"):
        print_success(f"Datasource '{payload['name']}' configured")
        return 0
    print_error(f"Datasource setup failed (http={out.strip() or 'n/a'})")
    return 1


def create_dashboard(args):
    print_header("Creating Dashboard")
    panels = (args.panels or "Requests,Errors,Latency").split(",")
    dashboard = build_dashboard_json(args.title or "Service Overview", panels)
    out_path = args.output or "dashboard.json"
    with open(out_path, "w") as f:
        json.dump(dashboard, f, indent=2)
    print_success(f"Dashboard JSON written to {out_path} ({len(panels)} panels)")
    return 0


def provision(args):
    print_header("Provisioning Datasources")
    datasources = [build_datasource_payload(name=args.name or "Prometheus", url=args.url or "http://localhost:9090")]
    yaml_text = build_provisioning_yaml(datasources)
    out_dir = args.output_dir or find_first_existing(GRAFANA_PROVISIONING_PATHS) or "./provisioning/datasources"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "datasources.yaml")
    with open(out_path, "w") as f:
        f.write(yaml_text)
    print_success(f"Provisioning file written to {out_path}")
    return 0


def configure_alerting(args):
    print_header("Configuring Alerting")
    rule = build_alert_rule(
        name=args.name or "High Error Rate",
        condition=args.condition or "avg() of query(A, 5m, now) > 0.05",
        for_duration=args.for_duration or "5m",
    )
    out_path = args.output or "alert-rule.json"
    with open(out_path, "w") as f:
        json.dump(rule, f, indent=2)
    print_success(f"Alert rule '{rule['title']}' written to {out_path}")
    return 0


def run_tests(args):
    """Genuinely run 6 distinct checks (not a fake '[Test 1/6]' that only
    ever executes check 1 -- see the version history in CHANGELOG.md for
    why that matters)."""
    print_header("Grafana Comprehensive Testing")
    checks = []

    checks.append(("binary", "pass" if shutil.which("grafana-server") else "fail", "grafana-server on PATH"))

    conf = find_first_existing(GRAFANA_CONF_PATHS)
    checks.append(("config", "pass" if conf else "fail", conf or "not found"))

    code, _out, _err = run_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health", timeout=10)
    checks.append(("api", "pass" if code == 0 else "fail", "GET /api/health"))

    code, out, _err = run_command(
        "curl -s -o /dev/null -w '%{http_code}' http://admin:admin@localhost:3000/api/datasources", timeout=10
    )
    checks.append(("datasource_api", "pass" if code == 0 and out.strip() == "200" else "fail", "GET /api/datasources"))

    prov = find_first_existing(GRAFANA_PROVISIONING_PATHS)
    checks.append(("provisioning_dir", "pass" if prov else "fail", prov or "not found"))

    code, _out, _err = run_command(
        "curl -s -o /dev/null -w '%{http_code}' http://admin:admin@localhost:3000/api/v1/provisioning/alert-rules", timeout=10
    )
    checks.append(("alerting_api", "pass" if code == 0 else "fail", "GET /api/v1/provisioning/alert-rules"))

    passed = sum(1 for _, status, _ in checks if status == "pass")
    for i, (name, status, detail) in enumerate(checks, 1):
        line = f"[Test {i}/{len(checks)}] {name}: {detail}"
        print_success(line) if status == "pass" else print_error(line)

    print_header("Test Summary")
    print(f"Passed: {passed}/{len(checks)}")
    if passed < len(checks):
        for issue in diagnose(checks):
            print_warning(issue)
    return 0 if passed == len(checks) else 1


def troubleshoot(args):
    print_header("Troubleshooting Grafana")
    checks = [
        ("binary", "pass" if shutil.which("grafana-server") else "fail", ""),
        ("config", "pass" if find_first_existing(GRAFANA_CONF_PATHS) else "fail", ""),
        ("provisioning_dir", "pass" if find_first_existing(GRAFANA_PROVISIONING_PATHS) else "fail", ""),
    ]
    issues = diagnose(checks)
    if not issues:
        print_success("No issues detected among binary/config/provisioning checks")
        return 0
    for issue in issues:
        print_warning(issue)
    return 1


def main():
    parser = argparse.ArgumentParser(description='Grafana Expert Tool')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('check-prerequisites')

    install_p = sub.add_parser('install')
    install_p.add_argument('--method', choices=['docker', 'native'], default='docker')

    ds_p = sub.add_parser('setup-datasource')
    ds_p.add_argument('--name', default='Prometheus')
    ds_p.add_argument('--url', default='http://localhost:9090')
    ds_p.add_argument('--type', default='prometheus')

    dash_p = sub.add_parser('create-dashboard')
    dash_p.add_argument('--title', default='Service Overview')
    dash_p.add_argument('--panels', default='Requests,Errors,Latency')
    dash_p.add_argument('--output', default='dashboard.json')

    prov_p = sub.add_parser('provision')
    prov_p.add_argument('--name', default='Prometheus')
    prov_p.add_argument('--url', default='http://localhost:9090')
    prov_p.add_argument('--output-dir', default=None)

    alert_p = sub.add_parser('configure-alerting')
    alert_p.add_argument('--name', default='High Error Rate')
    alert_p.add_argument('--condition', default=None)
    alert_p.add_argument('--for-duration', default='5m')
    alert_p.add_argument('--output', default='alert-rule.json')

    sub.add_parser('test')
    sub.add_parser('troubleshoot')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'install': install,
        'setup-datasource': setup_datasource,
        'create-dashboard': create_dashboard,
        'provision': provision,
        'configure-alerting': configure_alerting,
        'test': run_tests,
        'troubleshoot': troubleshoot,
    }
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
