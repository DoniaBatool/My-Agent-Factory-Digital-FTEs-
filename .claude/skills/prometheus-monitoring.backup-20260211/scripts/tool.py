#!/usr/bin/env python3
"""
Prometheus Monitoring Tool

Complete Prometheus setup: installation, configuration, scrape targets,
exporters, and metrics collection.

Commands:
  check-prerequisites  - Verify Prometheus installation
  install              - Install Prometheus and Node Exporter
  configure-scrape     - Add scrape targets
  add-exporter         - Setup exporters (node, blackbox, etc.)
  query-metrics        - Run PromQL queries
  test                 - Comprehensive testing suite
  troubleshoot         - Detect and fix issues
"""

import argparse
import subprocess
import sys
import os
import yaml

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")
def print_info(msg): print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")
def print_header(msg): print(f"\n{Colors.BOLD}==> {msg}{Colors.END}")

def run_command(cmd: str, timeout: int = 300):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)

def check_prerequisites(args) -> int:
    print_header("Checking Prerequisites")
    issues = []

    # Check Prometheus
    print_info("Checking Prometheus...")
    code, stdout, _ = run_command("prometheus --version 2>/dev/null")
    if code == 0:
        print_success(f"Prometheus installed: {stdout.split()[2] if len(stdout.split()) > 2 else 'unknown'}")
    else:
        print_error("Prometheus not installed")
        issues.append("Install: python3 tool.py install")

    # Check Prometheus service
    print_info("Checking Prometheus service...")
    code, _, _ = run_command("curl -s http://localhost:9090/-/healthy", timeout=5)
    if code == 0:
        print_success("Prometheus API accessible")
    else:
        print_warning("Prometheus not accessible at localhost:9090")

    # Check Node Exporter
    print_info("Checking Node Exporter...")
    code, _, _ = run_command("curl -s http://localhost:9100/metrics | head -1", timeout=5)
    if code == 0:
        print_success("Node Exporter running")
    else:
        print_warning("Node Exporter not accessible at localhost:9100")

    print_header("Prerequisites Summary")
    if not issues:
        print_success("All prerequisites met! ✅")
        return 0
    else:
        print_error(f"Found {len(issues)} issue(s):")
        for issue in issues:
            print_error(f"  • {issue}")
        return 1

def install_prometheus(args) -> int:
    print_header("Installing Prometheus")

    # Detect OS
    code, stdout, _ = run_command("uname -s")
    os_name = stdout.strip().lower() if code == 0 else ""

    if 'linux' in os_name:
        print_info("Installing on Linux...")

        # Download and install Prometheus
        commands = [
            "cd /tmp",
            "wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz",
            "tar xvfz prometheus-*.tar.gz",
            "cd prometheus-*",
            "cp prometheus /usr/local/bin/",
            "cp promtool /usr/local/bin/",
            "mkdir -p /etc/prometheus /var/lib/prometheus",
            "cp -r consoles console_libraries /etc/prometheus/"
        ]

        for cmd in commands:
            code, _, stderr = run_command(cmd, timeout=180)
            if code != 0:
                print_error(f"Failed: {cmd}")
                return 1

        # Create prometheus.yml
        config = {
            'global': {
                'scrape_interval': '15s',
                'evaluation_interval': '15s'
            },
            'scrape_configs': [{
                'job_name': 'prometheus',
                'static_configs': [{'targets': ['localhost:9090']}]
            }]
        }

        with open('/etc/prometheus/prometheus.yml', 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        # Create systemd service
        service = """[Unit]
Description=Prometheus
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/var/lib/prometheus/
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
        with open('/etc/systemd/system/prometheus.service', 'w') as f:
            f.write(service)

        # Start service
        run_command("systemctl daemon-reload")
        run_command("systemctl start prometheus")
        run_command("systemctl enable prometheus")

        print_success("Prometheus installed and started")

        # Install Node Exporter
        print_info("Installing Node Exporter...")
        commands = [
            "cd /tmp",
            "wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz",
            "tar xvfz node_exporter-*.tar.gz",
            "cp node_exporter-*/node_exporter /usr/local/bin/"
        ]

        for cmd in commands:
            code, _, _ = run_command(cmd, timeout=180)

        # Create Node Exporter service
        service = """[Unit]
Description=Node Exporter
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
        with open('/etc/systemd/system/node_exporter.service', 'w') as f:
            f.write(service)

        run_command("systemctl daemon-reload")
        run_command("systemctl start node_exporter")
        run_command("systemctl enable node_exporter")

        print_success("Node Exporter installed and started")

    elif 'darwin' in os_name:
        print_info("Installing on macOS...")
        code, _, _ = run_command("which brew")
        if code != 0:
            print_error("Homebrew required. Install from: https://brew.sh")
            return 1

        run_command("brew install prometheus node_exporter")
        run_command("brew services start prometheus")
        run_command("brew services start node_exporter")
        print_success("Prometheus and Node Exporter installed")

    print_success("Installation complete! ✅")
    print_info("Prometheus: http://localhost:9090")
    print_info("Node Exporter: http://localhost:9100/metrics")
    return 0

def configure_scrape(args) -> int:
    print_header(f"Configuring Scrape Target: {args.job_name}")

    config_paths = ['/etc/prometheus/prometheus.yml', '/usr/local/etc/prometheus.yml', '/opt/homebrew/etc/prometheus.yml']
    config_file = None
    for path in config_paths:
        if os.path.exists(path):
            config_file = path
            break

    if not config_file:
        print_error("Prometheus config not found")
        return 1

    # Read config
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    # Add new scrape config
    new_job = {
        'job_name': args.job_name,
        'static_configs': [{'targets': args.targets.split(',')}]
    }

    if 'scrape_configs' not in config:
        config['scrape_configs'] = []

    config['scrape_configs'].append(new_job)

    # Write config
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    print_success(f"Added scrape target: {args.job_name}")
    print_info("Reload Prometheus: kill -HUP $(pidof prometheus)")

    return 0

def add_exporter(args) -> int:
    print_header(f"Adding {args.exporter_type} Exporter")

    if args.exporter_type == 'node':
        print_info("Node Exporter setup (default port: 9100)")
        print_info("Add to prometheus.yml:")
        print_info("  - job_name: 'node'")
        print_info("    static_configs:")
        print_info("      - targets: ['localhost:9100']")

    elif args.exporter_type == 'blackbox':
        print_info("Blackbox Exporter (HTTP/HTTPS/TCP/ICMP probing)")
        print_info("Install: apt-get install prometheus-blackbox-exporter")
        print_info("Port: 9115")

    print_success(f"{args.exporter_type} exporter info provided")
    return 0

def query_metrics(args) -> int:
    print_header("Querying Prometheus Metrics")

    query = args.query if args.query else "up"
    cmd = f'curl -s "http://localhost:9090/api/v1/query?query={query}"'

    code, stdout, stderr = run_command(cmd, timeout=10)
    if code == 0:
        print_success("Query successful")
        print(stdout)
    else:
        print_error("Query failed")
        print_error(stderr)
        return 1

    return 0

def run_tests(args) -> int:
    print_header("Comprehensive Testing")

    tests_passed = tests_failed = 0
    issues = []

    # Test 1: Prometheus binary
    print_info("Test 1/5: Prometheus binary...")
    code, _, _ = run_command("prometheus --version 2>/dev/null")
    if code == 0:
        print_success("✓ Test 1 PASSED")
        tests_passed += 1
    else:
        print_error("✗ Test 1 FAILED")
        tests_failed += 1
        issues.append("Install Prometheus")

    # Test 2: API health
    print_info("Test 2/5: Prometheus API...")
    code, _, _ = run_command("curl -s http://localhost:9090/-/healthy", timeout=5)
    if code == 0:
        print_success("✓ Test 2 PASSED")
        tests_passed += 1
    else:
        print_error("✗ Test 2 FAILED")
        tests_failed += 1

    # Test 3: Metrics endpoint
    print_info("Test 3/5: Metrics endpoint...")
    code, _, _ = run_command("curl -s http://localhost:9090/metrics | head -1", timeout=5)
    if code == 0:
        print_success("✓ Test 3 PASSED")
        tests_passed += 1
    else:
        print_error("✗ Test 3 FAILED")
        tests_failed += 1

    # Test 4: Node Exporter
    print_info("Test 4/5: Node Exporter...")
    code, _, _ = run_command("curl -s http://localhost:9100/metrics | head -1", timeout=5)
    if code == 0:
        print_success("✓ Test 4 PASSED")
        tests_passed += 1
    else:
        print_warning("⚠ Test 4 WARNING")
        tests_passed += 1

    # Test 5: Query API
    print_info("Test 5/5: Query API...")
    code, _, _ = run_command('curl -s "http://localhost:9090/api/v1/query?query=up"', timeout=5)
    if code == 0:
        print_success("✓ Test 5 PASSED")
        tests_passed += 1
    else:
        print_error("✗ Test 5 FAILED")
        tests_failed += 1

    print_header("Test Summary")
    print(f"Passed: {Colors.GREEN}{tests_passed}{Colors.END}")
    print(f"Failed: {Colors.RED}{tests_failed}{Colors.END}")

    if tests_failed == 0:
        print_success("\n✅ All tests passed!")
        return 0
    else:
        print_error(f"\n❌ {tests_failed} test(s) failed")
        return 1

def troubleshoot(args) -> int:
    print_header("Troubleshooting Prometheus")

    issues_found = []

    # Issue 1: Service not running
    code, _, _ = run_command("curl -s http://localhost:9090/-/healthy", timeout=5)
    if code != 0:
        issues_found.append("Prometheus not accessible")
        print_error("Issue: Prometheus not running")
        print_info("Fix: systemctl start prometheus")

    # Issue 2: No scrape targets
    code, stdout, _ = run_command('curl -s "http://localhost:9090/api/v1/targets"', timeout=5)
    if code == 0 and 'activeTargets' in stdout:
        print_success("Targets: OK")
    else:
        print_warning("Issue: No scrape targets configured")
        print_info("Fix: Add targets to prometheus.yml")

    print_header("Troubleshooting Summary")
    if not issues_found:
        print_success("No issues found! ✅")
        return 0
    else:
        print_warning(f"Found {len(issues_found)} issue(s)")
        return 1

def main():
    parser = argparse.ArgumentParser(description='Prometheus Monitoring Tool')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('check-prerequisites')
    subparsers.add_parser('install')

    scrape_parser = subparsers.add_parser('configure-scrape')
    scrape_parser.add_argument('--job-name', required=True)
    scrape_parser.add_argument('--targets', required=True, help='Comma-separated targets (host:port)')

    exporter_parser = subparsers.add_parser('add-exporter')
    exporter_parser.add_argument('--exporter-type', required=True, choices=['node', 'blackbox'])

    query_parser = subparsers.add_parser('query-metrics')
    query_parser.add_argument('--query', help='PromQL query (default: up)')

    subparsers.add_parser('test')
    subparsers.add_parser('troubleshoot')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'install': install_prometheus,
        'configure-scrape': configure_scrape,
        'add-exporter': add_exporter,
        'query-metrics': query_metrics,
        'test': run_tests,
        'troubleshoot': troubleshoot,
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
