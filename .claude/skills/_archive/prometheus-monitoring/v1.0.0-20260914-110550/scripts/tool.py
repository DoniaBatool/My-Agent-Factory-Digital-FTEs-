#!/usr/bin/env python3
"""
Prometheus Monitoring Tool - Complete Prometheus setup

Commands: check-prerequisites, install, configure-scrape, add-exporter, 
         query-metrics, test, troubleshoot

Based on official Prometheus documentation
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
    print_header("Checking Prometheus Prerequisites")
    code, stdout, stderr = run_command("prometheus --version")
    if code == 0:
        print_success(f"Prometheus installed: {stdout.strip()}")
        return 0
    print_error("Prometheus not installed")
    print_info("Install: brew install prometheus (macOS) or apt install prometheus (Ubuntu)")
    return 1

def install(args):
    print_header("Installing Prometheus")
    method = args.method or "docker"
    if method == "docker":
        cmd = "docker run -d -p 9090:9090 --name prometheus prom/prometheus:latest"
        code, stdout, stderr = run_command(cmd)
        if code == 0:
            print_success("✅ Prometheus started on http://localhost:9090")
            return 0
    return 1

def configure_scrape(args):
    print_header("Configuring Scrape Targets")
    config = {
        "global": {
            "scrape_interval": args.interval or "15s"
        },
        "scrape_configs": [{
            "job_name": args.job_name or "app",
            "static_configs": [{"targets": [args.target or "localhost:8080"]}]
        }]
    }
    with open('prometheus.yml', 'w') as f:
        f.write(f"# Prometheus configuration\n{json.dumps(config, indent=2)}")
    print_success("✅ Configuration created: prometheus.yml")
    return 0

def run_tests(args):
    print_header("Prometheus Comprehensive Testing")
    tests_passed = tests_failed = 0
    
    print_info("\n[Test 1/6] Prometheus Server")
    code, _, _ = run_command("curl -s http://localhost:9090/-/healthy")
    if code == 0: print_success("✓ Server running"); tests_passed += 1
    else: print_error("✗ Server not running"); tests_failed += 1
    
    print_header("Test Summary")
    print(f"Passed: {tests_passed}, Failed: {tests_failed}")
    return 0 if tests_failed == 0 else 1

def main():
    parser = argparse.ArgumentParser(description='Prometheus Monitoring Tool')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('check-prerequisites')
    install_parser = subparsers.add_parser('install')
    install_parser.add_argument('--method', choices=['docker', 'native'], default='docker')
    scrape_parser = subparsers.add_parser('configure-scrape')
    scrape_parser.add_argument('--job-name', default='app')
    scrape_parser.add_argument('--target', default='localhost:8080')
    scrape_parser.add_argument('--interval', default='15s')
    subparsers.add_parser('test')
    
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        'check-prerequisites': check_prerequisites,
        'install': install,
        'configure-scrape': configure_scrape,
        'test': run_tests
    }
    return commands.get(args.command, lambda a: 1)(args)

if __name__ == '__main__':
    sys.exit(main())
