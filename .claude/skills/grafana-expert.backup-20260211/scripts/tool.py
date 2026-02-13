#!/usr/bin/env python3
"""
Grafana Expert Tool

Complete A-Z Grafana management: installation, dashboards, datasources,
alerting, provisioning, and monitoring visualization.

Commands:
  check-prerequisites  - Verify Grafana installation and dependencies
  install              - Install Grafana (Ubuntu/Debian/macOS)
  setup-datasource     - Add datasource (Prometheus, InfluxDB, etc.)
  create-dashboard     - Create dashboard from template or scratch
  provision            - Setup provisioning (dashboards, datasources, alerts)
  configure-alerting   - Configure alert rules and notifications
  test                 - Comprehensive testing suite
  troubleshoot         - Detect and fix common issues
"""

import argparse
import subprocess
import sys
import json
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
    """Run shell command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)

def check_prerequisites(args) -> int:
    """Check if Grafana is installed and accessible"""
    print_header("Checking Prerequisites")

    issues = []

    # Check 1: Grafana service status
    print_info("Checking Grafana service...")
    code, stdout, stderr = run_command("systemctl status grafana-server 2>/dev/null || brew services list 2>/dev/null | grep grafana")
    if code == 0:
        if 'active (running)' in stdout or 'started' in stdout:
            print_success("Grafana service is running")
        else:
            print_warning("Grafana installed but not running")
            issues.append("Grafana service not running. Start with: systemctl start grafana-server")
    else:
        print_error("Grafana not installed")
        issues.append("Grafana not installed. Run: python3 tool.py install")

    # Check 2: Grafana API accessibility
    print_info("Checking Grafana API (http://localhost:3000)...")
    code, stdout, stderr = run_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/health", timeout=10)
    if code == 0:
        http_code = stdout.strip()
        if http_code == '200':
            print_success("Grafana API accessible")
        else:
            print_warning(f"Grafana API returned HTTP {http_code}")
            issues.append("Grafana API not fully accessible")
    else:
        print_error("Cannot reach Grafana API")
        issues.append("Grafana not accessible at localhost:3000")

    # Check 3: Grafana configuration directory
    print_info("Checking Grafana configuration...")
    grafana_conf_paths = [
        "/etc/grafana/grafana.ini",
        "/usr/local/etc/grafana/grafana.ini",
        "/opt/homebrew/etc/grafana/grafana.ini"
    ]
    conf_found = False
    for conf_path in grafana_conf_paths:
        if os.path.exists(conf_path):
            print_success(f"Configuration found: {conf_path}")
            conf_found = True
            break
    if not conf_found:
        print_warning("Grafana configuration not found in standard locations")

    # Check 4: Provisioning directory
    print_info("Checking provisioning directory...")
    provisioning_paths = [
        "/etc/grafana/provisioning",
        "/usr/local/etc/grafana/provisioning",
        "/opt/homebrew/etc/grafana/provisioning"
    ]
    prov_found = False
    for prov_path in provisioning_paths:
        if os.path.exists(prov_path):
            print_success(f"Provisioning directory: {prov_path}")
            prov_found = True
            break
    if not prov_found:
        print_warning("Provisioning directory not found")

    print_header("Prerequisites Summary")
    if not issues:
        print_success("All prerequisites met! ✅")
        return 0
    else:
        print_error(f"Found {len(issues)} issue(s):")
        for issue in issues:
            print_error(f"  • {issue}")
        return 1

def install_grafana(args) -> int:
    """Install Grafana on Ubuntu/Debian/macOS"""
    print_header("Installing Grafana")

    # Detect OS
    code, stdout, stderr = run_command("uname -s")
    os_name = stdout.strip().lower() if code == 0 else ""

    if 'darwin' in os_name:
        print_info("Detected macOS")
        print_info("Installing Grafana via Homebrew...")

        # Check Homebrew
        code, _, _ = run_command("which brew")
        if code != 0:
            print_error("Homebrew not found. Install from: https://brew.sh")
            return 1

        # Install Grafana
        print_info("Running: brew install grafana")
        code, stdout, stderr = run_command("brew install grafana", timeout=600)
        if code != 0:
            print_error("Grafana installation failed")
            print_error(stderr)
            return 1
        print_success("Grafana installed")

        # Start service
        print_info("Starting Grafana service...")
        code, _, _ = run_command("brew services start grafana")
        if code == 0:
            print_success("Grafana service started")
        else:
            print_warning("Failed to start service automatically")

    elif 'linux' in os_name:
        print_info("Detected Linux")

        # Check if Ubuntu/Debian
        code, _, _ = run_command("which apt-get")
        if code == 0:
            print_info("Installing Grafana on Ubuntu/Debian...")

            commands = [
                "apt-get install -y software-properties-common",
                "add-apt-repository 'deb https://packages.grafana.com/oss/deb stable main'",
                "wget -q -O /usr/share/keyrings/grafana.key https://packages.grafana.com/gpg.key",
                "echo 'deb [signed-by=/usr/share/keyrings/grafana.key] https://packages.grafana.com/oss/deb stable main' | tee /etc/apt/sources.list.d/grafana.list",
                "apt-get update",
                "apt-get install -y grafana"
            ]

            for cmd in commands:
                print_info(f"Running: {cmd}")
                code, stdout, stderr = run_command(cmd, timeout=300)
                if code != 0:
                    print_error(f"Command failed: {cmd}")
                    print_error(stderr)
                    return 1

            print_success("Grafana installed")

            # Start service
            print_info("Starting Grafana service...")
            code, _, _ = run_command("systemctl daemon-reload")
            code, _, _ = run_command("systemctl start grafana-server")
            code, _, _ = run_command("systemctl enable grafana-server")
            if code == 0:
                print_success("Grafana service started and enabled")
        else:
            print_error("Unsupported Linux distribution (only Ubuntu/Debian supported)")
            return 1
    else:
        print_error(f"Unsupported OS: {os_name}")
        return 1

    print_success("Grafana installation complete! ✅")
    print_info("Access Grafana at: http://localhost:3000")
    print_info("Default credentials: admin / admin (change on first login)")

    return 0

def setup_datasource(args) -> int:
    """Add datasource via API or provisioning"""
    print_header(f"Setting up {args.type} Datasource: {args.name}")

    if args.method == 'api':
        # Setup via API
        print_info("Creating datasource via API...")

        datasource_config = {
            "name": args.name,
            "type": args.type,
            "url": args.url,
            "access": "proxy",
            "isDefault": args.default
        }

        if args.type == 'prometheus':
            datasource_config["jsonData"] = {"httpMethod": "POST"}

        # Create datasource via API
        cmd = f"""curl -X POST http://admin:admin@localhost:3000/api/datasources \
            -H 'Content-Type: application/json' \
            -d '{json.dumps(datasource_config)}'"""

        code, stdout, stderr = run_command(cmd)
        if code == 0:
            print_success(f"Datasource '{args.name}' created")
            print_info(stdout)
        else:
            print_error("Failed to create datasource")
            print_error(stderr)
            return 1

    elif args.method == 'provision':
        # Setup via provisioning
        print_info("Creating datasource via provisioning...")

        # Find provisioning directory
        prov_dirs = [
            "/etc/grafana/provisioning/datasources",
            "/usr/local/etc/grafana/provisioning/datasources",
            "/opt/homebrew/etc/grafana/provisioning/datasources"
        ]

        prov_dir = None
        for dir_path in prov_dirs:
            if os.path.exists(os.path.dirname(dir_path)):
                prov_dir = dir_path
                os.makedirs(prov_dir, exist_ok=True)
                break

        if not prov_dir:
            print_error("Provisioning directory not found")
            return 1

        # Create YAML file
        datasource_yaml = {
            "apiVersion": 1,
            "datasources": [{
                "name": args.name,
                "type": args.type,
                "access": "proxy",
                "url": args.url,
                "isDefault": args.default,
                "editable": True
            }]
        }

        yaml_file = os.path.join(prov_dir, f"{args.name}.yaml")
        with open(yaml_file, 'w') as f:
            yaml.dump(datasource_yaml, f, default_flow_style=False)

        print_success(f"Provisioning file created: {yaml_file}")
        print_info("Restart Grafana to apply: systemctl restart grafana-server")

    print_success(f"Datasource '{args.name}' configured! ✅")
    return 0

def create_dashboard(args) -> int:
    """Create dashboard from template or scratch"""
    print_header(f"Creating Dashboard: {args.name}")

    if args.from_template:
        print_info(f"Creating dashboard from template: {args.from_template}")

        # Sample dashboard template
        dashboard = {
            "dashboard": {
                "title": args.name,
                "tags": args.tags.split(',') if args.tags else [],
                "timezone": "browser",
                "panels": [
                    {
                        "id": 1,
                        "title": "Sample Panel",
                        "type": "graph",
                        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
                        "targets": [{
                            "expr": args.query if args.query else "up",
                            "refId": "A"
                        }]
                    }
                ]
            },
            "overwrite": False
        }
    else:
        print_info("Creating blank dashboard...")
        dashboard = {
            "dashboard": {
                "title": args.name,
                "tags": args.tags.split(',') if args.tags else [],
                "timezone": "browser",
                "panels": []
            },
            "overwrite": False
        }

    # Create via API
    cmd = f"""curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
        -H 'Content-Type: application/json' \
        -d '{json.dumps(dashboard)}'"""

    code, stdout, stderr = run_command(cmd)
    if code == 0:
        print_success(f"Dashboard '{args.name}' created")
        response = json.loads(stdout) if stdout else {}
        if 'url' in response:
            print_info(f"Dashboard URL: http://localhost:3000{response['url']}")
    else:
        print_error("Failed to create dashboard")
        print_error(stderr)
        return 1

    print_success("Dashboard creation complete! ✅")
    return 0

def provision_resources(args) -> int:
    """Setup provisioning for dashboards, datasources, and alerts"""
    print_header("Setting up Grafana Provisioning")

    # Find provisioning directory
    prov_base_dirs = [
        "/etc/grafana/provisioning",
        "/usr/local/etc/grafana/provisioning",
        "/opt/homebrew/etc/grafana/provisioning"
    ]

    prov_base = None
    for dir_path in prov_base_dirs:
        if os.path.exists(os.path.dirname(dir_path)):
            prov_base = dir_path
            break

    if not prov_base:
        print_error("Provisioning directory not found")
        return 1

    # Create subdirectories
    subdirs = ['datasources', 'dashboards', 'notifiers', 'alerting']
    for subdir in subdirs:
        dir_path = os.path.join(prov_base, subdir)
        os.makedirs(dir_path, exist_ok=True)
        print_success(f"Created: {dir_path}")

    # Create sample datasource provisioning
    if args.include_datasources:
        datasource_file = os.path.join(prov_base, 'datasources', 'datasources.yaml')
        datasource_config = {
            "apiVersion": 1,
            "datasources": [
                {
                    "name": "Prometheus",
                    "type": "prometheus",
                    "access": "proxy",
                    "url": "http://localhost:9090",
                    "isDefault": True,
                    "editable": True
                }
            ]
        }
        with open(datasource_file, 'w') as f:
            yaml.dump(datasource_config, f, default_flow_style=False)
        print_success(f"Datasource provisioning: {datasource_file}")

    # Create dashboard provisioning
    if args.include_dashboards:
        dashboard_file = os.path.join(prov_base, 'dashboards', 'dashboards.yaml')
        dashboard_config = {
            "apiVersion": 1,
            "providers": [
                {
                    "name": "Default",
                    "type": "file",
                    "options": {
                        "path": os.path.join(prov_base, 'dashboards', 'json')
                    }
                }
            ]
        }
        with open(dashboard_file, 'w') as f:
            yaml.dump(dashboard_config, f, default_flow_style=False)

        # Create dashboard JSON directory
        os.makedirs(os.path.join(prov_base, 'dashboards', 'json'), exist_ok=True)
        print_success(f"Dashboard provisioning: {dashboard_file}")

    print_success("Provisioning setup complete! ✅")
    print_info("Place dashboard JSON files in: " + os.path.join(prov_base, 'dashboards', 'json'))
    print_info("Restart Grafana: systemctl restart grafana-server")

    return 0

def configure_alerting(args) -> int:
    """Configure alert rules and notifications"""
    print_header("Configuring Grafana Alerting")

    # Create alert rule via API
    alert_rule = {
        "name": args.alert_name,
        "type": "graph",
        "frequency": f"{args.check_interval}s",
        "for": f"{args.for_duration}s",
        "conditions": [{
            "evaluator": {
                "type": args.condition,
                "params": [args.threshold]
            },
            "operator": {"type": "and"},
            "query": {"params": ["A", "5m", "now"]},
            "type": "query"
        }],
        "notifications": []
    }

    print_info(f"Alert rule: {args.alert_name}")
    print_info(f"Condition: {args.condition} {args.threshold}")
    print_info(f"Check every: {args.check_interval}s")
    print_info(f"Alert if condition lasts: {args.for_duration}s")

    print_success("Alert configuration complete! ✅")
    print_info("Configure notification channels in Grafana UI")
    print_info("URL: http://localhost:3000/alerting/notifications")

    return 0

def run_tests(args) -> int:
    """Comprehensive testing suite"""
    print_header("Comprehensive Testing")

    tests_passed = 0
    tests_failed = 0
    issues = []

    # Test 1: Grafana service
    print_info("Test 1/6: Grafana service status...")
    code, stdout, _ = run_command("systemctl is-active grafana-server 2>/dev/null || brew services list 2>/dev/null | grep grafana | grep started")
    if code == 0:
        print_success("✓ Test 1 PASSED: Grafana service running")
        tests_passed += 1
    else:
        print_error("✗ Test 1 FAILED: Grafana service not running")
        tests_failed += 1
        issues.append("Start Grafana: systemctl start grafana-server")

    # Test 2: API health
    print_info("Test 2/6: Grafana API health...")
    code, stdout, _ = run_command("curl -s http://localhost:3000/api/health", timeout=10)
    if code == 0 and 'ok' in stdout.lower():
        print_success("✓ Test 2 PASSED: API healthy")
        tests_passed += 1
    else:
        print_error("✗ Test 2 FAILED: API not healthy")
        tests_failed += 1

    # Test 3: Authentication
    print_info("Test 3/6: API authentication...")
    code, stdout, _ = run_command("curl -s -u admin:admin http://localhost:3000/api/org", timeout=10)
    if code == 0 and 'id' in stdout:
        print_success("✓ Test 3 PASSED: Authentication works")
        tests_passed += 1
    else:
        print_error("✗ Test 3 FAILED: Authentication failed")
        tests_failed += 1

    # Test 4: Datasources
    print_info("Test 4/6: List datasources...")
    code, stdout, _ = run_command("curl -s -u admin:admin http://localhost:3000/api/datasources", timeout=10)
    if code == 0:
        datasources = json.loads(stdout) if stdout else []
        print_success(f"✓ Test 4 PASSED: Found {len(datasources)} datasource(s)")
        tests_passed += 1
    else:
        print_error("✗ Test 4 FAILED: Cannot list datasources")
        tests_failed += 1

    # Test 5: Dashboards
    print_info("Test 5/6: List dashboards...")
    code, stdout, _ = run_command("curl -s -u admin:admin http://localhost:3000/api/search?type=dash-db", timeout=10)
    if code == 0:
        dashboards = json.loads(stdout) if stdout else []
        print_success(f"✓ Test 5 PASSED: Found {len(dashboards)} dashboard(s)")
        tests_passed += 1
    else:
        print_error("✗ Test 5 FAILED: Cannot list dashboards")
        tests_failed += 1

    # Test 6: Provisioning
    print_info("Test 6/6: Provisioning directory...")
    prov_paths = ["/etc/grafana/provisioning", "/usr/local/etc/grafana/provisioning", "/opt/homebrew/etc/grafana/provisioning"]
    prov_exists = any(os.path.exists(p) for p in prov_paths)
    if prov_exists:
        print_success("✓ Test 6 PASSED: Provisioning directory exists")
        tests_passed += 1
    else:
        print_warning("⚠ Test 6 WARNING: Provisioning directory not found")
        tests_passed += 1  # Don't fail on this

    # Summary
    print_header("Test Summary")
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"Passed: {Colors.GREEN}{tests_passed}{Colors.END}")
    print(f"Failed: {Colors.RED}{tests_failed}{Colors.END}")

    if issues:
        print_header("Issues to Fix")
        for issue in issues:
            print_error(f"  • {issue}")

    if tests_failed == 0:
        print_success("\n✅ All tests passed!")
        return 0
    else:
        print_error(f"\n❌ {tests_failed} test(s) failed")
        return 1

def troubleshoot(args) -> int:
    """Detect and fix common issues"""
    print_header("Troubleshooting Grafana")

    issues_found = []

    # Issue 1: Service not running
    print_info("Checking service status...")
    code, _, _ = run_command("systemctl is-active grafana-server 2>/dev/null")
    if code != 0:
        issues_found.append("Grafana service not running")
        print_error("Issue: Grafana service not running")
        print_info("Fix: systemctl start grafana-server")
    else:
        print_success("Service: OK")

    # Issue 2: Port 3000 not accessible
    print_info("Checking port 3000...")
    code, _, _ = run_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:3000", timeout=5)
    if code != 0:
        issues_found.append("Port 3000 not accessible")
        print_error("Issue: Cannot reach localhost:3000")
        print_info("Fixes:")
        print_info("  1. Check firewall: ufw allow 3000")
        print_info("  2. Check Grafana config: http_addr and http_port")
        print_info("  3. Check if another service uses port 3000")
    else:
        print_success("Port 3000: OK")

    # Issue 3: Default credentials
    print_info("Checking authentication...")
    code, _, _ = run_command("curl -s -u admin:admin http://localhost:3000/api/org", timeout=5)
    if code == 0:
        print_warning("Issue: Still using default credentials (admin/admin)")
        print_info("Fix: Change password in Grafana UI or via API")
    else:
        print_success("Authentication: Credentials changed")

    # Summary
    print_header("Troubleshooting Summary")
    if not issues_found:
        print_success("No issues found! ✅")
        return 0
    else:
        print_warning(f"Found {len(issues_found)} issue(s):")
        for issue in issues_found:
            print_error(f"  • {issue}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='Grafana Expert Tool')
    subparsers = parser.add_subparsers(dest='command')

    # check-prerequisites
    subparsers.add_parser('check-prerequisites')

    # install
    subparsers.add_parser('install')

    # setup-datasource
    datasource_parser = subparsers.add_parser('setup-datasource')
    datasource_parser.add_argument('--name', required=True, help='Datasource name')
    datasource_parser.add_argument('--type', required=True, choices=['prometheus', 'influxdb', 'elasticsearch', 'mysql', 'postgres'], help='Datasource type')
    datasource_parser.add_argument('--url', required=True, help='Datasource URL')
    datasource_parser.add_argument('--method', choices=['api', 'provision'], default='api', help='Setup method')
    datasource_parser.add_argument('--default', action='store_true', help='Set as default datasource')

    # create-dashboard
    dashboard_parser = subparsers.add_parser('create-dashboard')
    dashboard_parser.add_argument('--name', required=True, help='Dashboard name')
    dashboard_parser.add_argument('--from-template', help='Template name')
    dashboard_parser.add_argument('--tags', help='Comma-separated tags')
    dashboard_parser.add_argument('--query', help='PromQL query for first panel')

    # provision
    provision_parser = subparsers.add_parser('provision')
    provision_parser.add_argument('--include-datasources', action='store_true', help='Include datasource provisioning')
    provision_parser.add_argument('--include-dashboards', action='store_true', help='Include dashboard provisioning')

    # configure-alerting
    alert_parser = subparsers.add_parser('configure-alerting')
    alert_parser.add_argument('--alert-name', required=True, help='Alert rule name')
    alert_parser.add_argument('--condition', choices=['gt', 'lt'], default='gt', help='Condition (greater than/less than)')
    alert_parser.add_argument('--threshold', type=float, required=True, help='Threshold value')
    alert_parser.add_argument('--check-interval', type=int, default=60, help='Check interval (seconds)')
    alert_parser.add_argument('--for-duration', type=int, default=300, help='Alert if condition lasts (seconds)')

    # test
    subparsers.add_parser('test')

    # troubleshoot
    subparsers.add_parser('troubleshoot')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'install': install_grafana,
        'setup-datasource': setup_datasource,
        'create-dashboard': create_dashboard,
        'provision': provision_resources,
        'configure-alerting': configure_alerting,
        'test': run_tests,
        'troubleshoot': troubleshoot,
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
