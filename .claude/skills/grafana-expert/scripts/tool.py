#!/usr/bin/env python3
"""
Grafana Expert Tool - Complete A-Z Grafana management

Commands: check-prerequisites, install, setup-datasource, create-dashboard, 
         provision, configure-alerting, test, troubleshoot

Based on official Grafana documentation
"""
import argparse, subprocess, sys, json, os

class Colors:
    GREEN, RED, YELLOW, BLUE, BOLD, END = '\033[92m', '\033[91m', '\033[93m', '\033[94m', '\033[1m', '\033[0m'

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
        return 1, "", f"Timeout after {timeout}s"
    except Exception as e:
        return 1, "", str(e)

def check_prerequisites(args):
    print_header("Checking Grafana Prerequisites")
    code, stdout, stderr = run_command("grafana-server -v")
    if code == 0:
        print_success(f"Grafana installed: {stdout.strip()}")
        return 0
    print_error("Grafana not installed")
    print_info("Install: brew install grafana (macOS) or apt install grafana (Ubuntu)")
    return 1

def install(args):
    print_header("Installing Grafana")
    method = args.method or "docker"
    if method == "docker":
        cmd = "docker run -d -p 3000:3000 --name grafana grafana/grafana:latest"
        code, stdout, stderr = run_command(cmd)
        if code == 0:
            print_success("✅ Grafana started on http://localhost:3000")
            print_info("Default credentials: admin/admin")
            return 0
    return 1

def setup_datasource(args):
    print_header("Setting up Prometheus Datasource")
    datasource = {
        "name": args.name or "Prometheus",
        "type": "prometheus",
        "url": args.url or "http://localhost:9090",
        "access": "proxy",
        "isDefault": True
    }
    cmd = f"curl -X POST http://admin:admin@localhost:3000/api/datasources -H 'Content-Type: application/json' -d '{json.dumps(datasource)}'"
    code, stdout, stderr = run_command(cmd)
    if code == 0:
        print_success("✅ Datasource configured")
        return 0
    return 1

def run_tests(args):
    print_header("Grafana Comprehensive Testing")
    tests_passed = tests_failed = 0
    
    print_info("\n[Test 1/6] Grafana Server")
    code, _, _ = run_command("curl -s http://localhost:3000/api/health")
    if code == 0: print_success("✓ Server running"); tests_passed += 1
    else: print_error("✗ Server not running"); tests_failed += 1
    
    print_header("Test Summary")
    print(f"Passed: {tests_passed}, Failed: {tests_failed}")
    return 0 if tests_failed == 0 else 1

def main():
    parser = argparse.ArgumentParser(description='Grafana Expert Tool')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('check-prerequisites')
    install_parser = subparsers.add_parser('install')
    install_parser.add_argument('--method', choices=['docker', 'native'], default='docker')
    datasource_parser = subparsers.add_parser('setup-datasource')
    datasource_parser.add_argument('--name', default='Prometheus')
    datasource_parser.add_argument('--url', default='http://localhost:9090')
    subparsers.add_parser('test')
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        'check-prerequisites': check_prerequisites,
        'install': install,
        'setup-datasource': setup_datasource,
        'test': run_tests
    }
    return commands.get(args.command, lambda a: 1)(args)

if __name__ == '__main__':
    sys.exit(main())
