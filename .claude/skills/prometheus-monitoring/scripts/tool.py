#!/usr/bin/env python3
"""
Prometheus Monitoring Tool - Complete Prometheus setup

Commands: check-prerequisites, install, configure-scrape, add-exporter,
          query-metrics, test, troubleshoot

v2.0.0: same fix as grafana-expert -- the previous `test` command printed
"[Test 1/6]" but only ever ran one real check. This version runs six
distinct real checks and every JSON/YAML-building helper is pure and unit
tested (see tests/test_tool.py) so a future "improvement" can't silently
shrink coverage again without failing the version gate.
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
# Pure / testable helpers -----------------------------------------------
# ---------------------------------------------------------------------------

def detect_os():
    return platform.system().lower()


def find_first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


PROMETHEUS_CONF_PATHS = [
    "/etc/prometheus/prometheus.yml",
    "/usr/local/etc/prometheus/prometheus.yml",
    "/opt/homebrew/etc/prometheus.yml",
]


def build_install_command(os_name: str, method: str) -> str:
    if method == "docker":
        return "docker run -d -p 9090:9090 --name prometheus prom/prometheus:latest"
    if "darwin" in os_name:
        return "brew install prometheus"
    if "linux" in os_name:
        return "sudo apt-get update && sudo apt-get install -y prometheus"
    raise ValueError(f"Unsupported OS for native install: {os_name}")


def build_scrape_config(job_name="app", target="localhost:8080", interval="15s", existing_jobs=None):
    """Return a full prometheus.yml scrape config dict. If `existing_jobs`
    (a list of scrape_config dicts) is given, the new job is appended
    rather than replacing the file, so repeated calls are additive."""
    jobs = list(existing_jobs or [])
    jobs.append({"job_name": job_name, "static_configs": [{"targets": [target]}]})
    return {
        "global": {"scrape_interval": interval, "evaluation_interval": interval},
        "scrape_configs": jobs,
    }


def dict_to_yaml(data, indent=0):
    """Minimal hand-rolled YAML writer (no PyYAML dependency) sufficient
    for the nested dict/list shapes this tool builds."""
    lines = []
    pad = "  " * indent
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}{k}:")
                lines.append(dict_to_yaml(v, indent + 1))
            else:
                lines.append(f"{pad}{k}: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                sub = dict_to_yaml(item, indent + 1).lstrip()
                lines.append(f"{pad}- {sub}")
            else:
                lines.append(f"{pad}- {item}")
    return "\n".join(lines)


EXPORTER_PORTS = {"node": 9100, "blackbox": 9115, "pushgateway": 9091}


def build_exporter_command(exporter_type: str) -> str:
    if exporter_type not in EXPORTER_PORTS:
        raise ValueError(f"Unknown exporter type: {exporter_type}. Known: {sorted(EXPORTER_PORTS)}")
    port = EXPORTER_PORTS[exporter_type]
    return f"docker run -d -p {port}:{port} --name {exporter_type}_exporter prom/{exporter_type}-exporter:latest"


def build_query_url(base_url: str, promql: str, instant=True) -> str:
    endpoint = "query" if instant else "query_range"
    from urllib.parse import quote
    return f"{base_url.rstrip('/')}/api/v1/{endpoint}?query={quote(promql)}"


def diagnose(check_results):
    remediation = {
        "binary": "Prometheus binary not found. Run: python3 tool.py install --method docker",
        "config": "No prometheus.yml found in standard locations.",
        "api": "Prometheus API unreachable at localhost:9090. Check the service is running.",
        "targets_api": "Targets API call failed -- scrape targets may not be configured.",
        "node_exporter": "Node Exporter not reachable at localhost:9100.",
        "alertmanager": "Alertmanager unreachable at localhost:9093 (optional unless alerting is used).",
    }
    return [remediation[name] for name, status, _ in check_results if status != "pass" and name in remediation]


# ---------------------------------------------------------------------------
# Commands ----------------------------------------------------------------
# ---------------------------------------------------------------------------

def check_prerequisites(args):
    print_header("Checking Prometheus Prerequisites")
    issues = []

    if shutil.which("prometheus"):
        print_success("Prometheus binary found on PATH")
    else:
        print_error("Prometheus binary not found")
        issues.append("Install with: python3 tool.py install --method docker")

    conf = find_first_existing(PROMETHEUS_CONF_PATHS)
    if conf:
        print_success(f"Configuration found: {conf}")
    else:
        print_warning("No prometheus.yml found in standard locations")

    print_header("Prerequisites Summary")
    if not issues:
        print_success("All prerequisites met!")
        return 0
    for issue in issues:
        print_error(f"  - {issue}")
    return 1


def install(args):
    print_header("Installing Prometheus")
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
        print_success("Prometheus installed/started")
        if method == "docker":
            print_info("Default URL: http://localhost:9090")
        return 0
    print_error(f"Install failed: {err.strip()[:300]}")
    return 1


def configure_scrape(args):
    print_header("Configuring Scrape Targets")
    config = build_scrape_config(
        job_name=args.job_name or "app",
        target=args.target or "localhost:8080",
        interval=args.interval or "15s",
    )
    out_path = args.output or "prometheus.yml"
    with open(out_path, "w") as f:
        f.write(dict_to_yaml(config) + "\n")
    print_success(f"Configuration written to {out_path} (job: {config['scrape_configs'][-1]['job_name']})")
    return 0


def add_exporter(args):
    print_header("Adding Exporter")
    exporter_type = args.type or "node"
    try:
        cmd = build_exporter_command(exporter_type)
    except ValueError as e:
        print_error(str(e))
        return 1
    print_info(f"Running: {cmd}")
    code, _out, err = run_command(cmd)
    if code == 0:
        print_success(f"{exporter_type} exporter started on port {EXPORTER_PORTS[exporter_type]}")
        return 0
    print_error(f"Failed to start exporter: {err.strip()[:300]}")
    return 1


def query_metrics(args):
    print_header("Querying Metrics")
    base_url = args.url or "http://localhost:9090"
    url = build_query_url(base_url, args.query, instant=not args.range)
    code, out, err = run_command(f"curl -s '{url}'", timeout=15)
    if code == 0 and out.strip():
        print_success("Query executed")
        print(out)
        return 0
    print_error(f"Query failed: {err.strip()[:300] or 'no response'}")
    return 1


def run_tests(args):
    print_header("Prometheus Comprehensive Testing")
    checks = []

    checks.append(("binary", "pass" if shutil.which("prometheus") else "fail", "prometheus on PATH"))

    conf = find_first_existing(PROMETHEUS_CONF_PATHS)
    checks.append(("config", "pass" if conf else "fail", conf or "not found"))

    code, _out, _err = run_command("curl -s http://localhost:9090/-/healthy", timeout=10)
    checks.append(("api", "pass" if code == 0 else "fail", "GET /-/healthy"))

    code, out, _err = run_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:9090/api/v1/targets", timeout=10)
    checks.append(("targets_api", "pass" if code == 0 and out.strip() == "200" else "fail", "GET /api/v1/targets"))

    code, _out, _err = run_command("curl -s http://localhost:9100/metrics", timeout=10)
    checks.append(("node_exporter", "pass" if code == 0 else "fail", "GET :9100/metrics"))

    code, _out, _err = run_command("curl -s http://localhost:9093/-/healthy", timeout=10)
    checks.append(("alertmanager", "pass" if code == 0 else "fail", "GET :9093/-/healthy"))

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
    print_header("Troubleshooting Prometheus")
    checks = [
        ("binary", "pass" if shutil.which("prometheus") else "fail", ""),
        ("config", "pass" if find_first_existing(PROMETHEUS_CONF_PATHS) else "fail", ""),
    ]
    issues = diagnose(checks)
    if not issues:
        print_success("No issues detected among binary/config checks")
        return 0
    for issue in issues:
        print_warning(issue)
    return 1


def main():
    parser = argparse.ArgumentParser(description='Prometheus Monitoring Tool')
    sub = parser.add_subparsers(dest='command')

    sub.add_parser('check-prerequisites')

    install_p = sub.add_parser('install')
    install_p.add_argument('--method', choices=['docker', 'native'], default='docker')

    scrape_p = sub.add_parser('configure-scrape')
    scrape_p.add_argument('--job-name', default='app')
    scrape_p.add_argument('--target', default='localhost:8080')
    scrape_p.add_argument('--interval', default='15s')
    scrape_p.add_argument('--output', default='prometheus.yml')

    exp_p = sub.add_parser('add-exporter')
    exp_p.add_argument('--type', choices=sorted(EXPORTER_PORTS), default='node')

    query_p = sub.add_parser('query-metrics')
    query_p.add_argument('--query', required=False, default='up')
    query_p.add_argument('--url', default='http://localhost:9090')
    query_p.add_argument('--range', action='store_true')

    sub.add_parser('test')
    sub.add_parser('troubleshoot')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'install': install,
        'configure-scrape': configure_scrape,
        'add-exporter': add_exporter,
        'query-metrics': query_metrics,
        'test': run_tests,
        'troubleshoot': troubleshoot,
    }
    return commands[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
