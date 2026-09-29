#!/usr/bin/env python3
"""
Pangolin Homelab Setup Automation Tool

Comprehensive automation for Pangolin homelab deployment, configuration,
testing, and troubleshooting across all scenarios.

Documentation: https://docs.pangolin.net/
"""

import argparse
import subprocess
import sys
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ANSI color codes for terminal output
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text: str):
    """Print colored header"""
    print(f"\n{Colors.BLUE}==>{Colors.RESET} {text}")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BOLD}→{Colors.RESET} {text}")

def run_command(cmd: List[str], check: bool = True, capture: bool = False) -> Tuple[int, str, str]:
    """
    Execute shell command and return (returncode, stdout, stderr)

    Args:
        cmd: Command as list of strings
        check: Raise exception on non-zero exit
        capture: Capture output instead of printing

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        if capture:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode, "", ""
    except subprocess.CalledProcessError as e:
        if capture:
            return e.returncode, e.stdout if e.stdout else "", e.stderr if e.stderr else ""
        return e.returncode, "", ""
    except FileNotFoundError:
        print_error(f"Command not found: {cmd[0]}")
        return 1, "", f"Command not found: {cmd[0]}"

def check_prerequisites() -> Dict[str, bool]:
    """Check system prerequisites for Pangolin installation"""
    print_header("Checking prerequisites")

    checks = {}

    # Check OS
    import platform
    os_type = platform.system()
    print_info(f"Operating System: {os_type}")
    checks['os_supported'] = os_type in ['Linux', 'Darwin']  # Linux or macOS

    if checks['os_supported']:
        print_success(f"OS supported: {os_type}")
    else:
        print_error(f"OS not supported: {os_type}")

    # Check Docker
    returncode, stdout, _ = run_command(['which', 'docker'], check=False, capture=True)
    checks['docker'] = returncode == 0

    if checks['docker']:
        returncode, version, _ = run_command(['docker', '--version'], check=False, capture=True)
        print_success(f"Docker installed: {version.strip()}")
    else:
        print_warning("Docker not found (optional, required for container deployment)")

    # Check Docker Compose
    returncode, stdout, _ = run_command(['which', 'docker-compose'], check=False, capture=True)
    if returncode != 0:
        returncode, stdout, _ = run_command(['docker', 'compose', 'version'], check=False, capture=True)

    checks['docker_compose'] = returncode == 0

    if checks['docker_compose']:
        print_success("Docker Compose available")
    else:
        print_warning("Docker Compose not found (optional)")

    # Check curl/wget
    returncode, _, _ = run_command(['which', 'curl'], check=False, capture=True)
    checks['curl'] = returncode == 0

    if checks['curl']:
        print_success("curl installed")
    else:
        returncode, _, _ = run_command(['which', 'wget'], check=False, capture=True)
        checks['wget'] = returncode == 0
        if checks['wget']:
            print_success("wget installed")
        else:
            print_error("Neither curl nor wget found (required)")

    # Check systemd (Linux only)
    if os_type == 'Linux':
        returncode, _, _ = run_command(['which', 'systemctl'], check=False, capture=True)
        checks['systemd'] = returncode == 0

        if checks['systemd']:
            print_success("systemd available")
        else:
            print_warning("systemd not found (may limit service management)")

    # Check available disk space
    returncode, stdout, _ = run_command(['df', '-h', '.'], check=False, capture=True)
    if returncode == 0:
        lines = stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 4:
                print_info(f"Available disk space: {parts[3]}")

    # Check network connectivity
    print_info("Checking network connectivity...")
    returncode, _, _ = run_command(['ping', '-c', '1', 'docs.pangolin.net'], check=False, capture=True)
    checks['network'] = returncode == 0

    if checks['network']:
        print_success("Network connectivity OK")
    else:
        print_error("Cannot reach docs.pangolin.net (check internet connection)")

    return checks

def install_pangolin_server(args):
    """Install Pangolin self-hosted server"""
    print_header("Installing Pangolin Self-Hosted Server")

    # Check prerequisites first
    checks = check_prerequisites()

    if not checks.get('os_supported'):
        print_error("Unsupported operating system. Pangolin requires Linux or macOS.")
        sys.exit(1)

    if not (checks.get('curl') or checks.get('wget')):
        print_error("curl or wget required for installation")
        sys.exit(1)

    # Determine installation method
    if args.method == 'docker' and not checks.get('docker'):
        print_error("Docker not found. Install Docker or use --method binary")
        sys.exit(1)

    if args.method == 'auto':
        if checks.get('docker'):
            install_method = 'docker'
        else:
            install_method = 'binary'
    else:
        install_method = args.method

    print_info(f"Installation method: {install_method}")

    if install_method == 'docker':
        install_docker_compose(args)
    elif install_method == 'binary':
        install_binary(args)
    else:
        print_error(f"Unknown installation method: {install_method}")
        sys.exit(1)

def install_docker_compose(args):
    """Install Pangolin using Docker Compose"""
    print_header("Installing Pangolin with Docker Compose")

    # Create installation directory
    install_dir = Path(args.install_dir).expanduser()
    install_dir.mkdir(parents=True, exist_ok=True)

    print_info(f"Installation directory: {install_dir}")

    # Create docker-compose.yml
    compose_file = install_dir / "docker-compose.yml"

    compose_content = f"""version: '3.8'

services:
  pangolin:
    image: {args.image}
    container_name: pangolin-server
    restart: unless-stopped
    ports:
      - "{args.port}:443"
      - "{args.admin_port}:8080"
    volumes:
      - ./data:/data
      - ./config:/config
    environment:
      - PANGOLIN_DOMAIN={args.domain}
      - PANGOLIN_ADMIN_EMAIL={args.admin_email}
    networks:
      - pangolin_network

networks:
  pangolin_network:
    driver: bridge
"""

    print_info("Creating docker-compose.yml...")
    with open(compose_file, 'w') as f:
        f.write(compose_content)

    print_success(f"Created: {compose_file}")

    # Create directories
    (install_dir / "data").mkdir(exist_ok=True)
    (install_dir / "config").mkdir(exist_ok=True)

    # Create default config.yml
    config_file = install_dir / "config" / "config.yml"

    config_content = f"""# Pangolin Configuration
server:
  domain: {args.domain}
  port: 443

admin:
  email: {args.admin_email}

database:
  type: sqlite
  path: /data/pangolin.db

logging:
  level: info
  format: json
"""

    print_info("Creating config.yml...")
    with open(config_file, 'w') as f:
        f.write(config_content)

    print_success(f"Created: {config_file}")

    # Pull Docker image
    print_header("Pulling Docker image")
    returncode, _, _ = run_command(['docker', 'pull', args.image], check=False)

    if returncode != 0:
        print_error("Failed to pull Docker image")
        sys.exit(1)

    print_success("Docker image pulled successfully")

    # Start services
    print_header("Starting Pangolin services")
    os.chdir(install_dir)
    returncode, _, _ = run_command(['docker-compose', 'up', '-d'], check=False)

    if returncode != 0:
        # Try docker compose (newer syntax)
        returncode, _, _ = run_command(['docker', 'compose', 'up', '-d'], check=False)

    if returncode != 0:
        print_error("Failed to start services")
        sys.exit(1)

    print_success("Pangolin services started successfully!")

    # Wait for service to be ready
    print_info("Waiting for service to be ready...")
    time.sleep(5)

    # Print access information
    print_header("Installation Complete!")
    print_success(f"Pangolin server: https://{args.domain}:{args.port}")
    print_success(f"Admin console: http://localhost:{args.admin_port}")
    print_info(f"Configuration: {config_file}")
    print_info(f"Data directory: {install_dir / 'data'}")

    print_info("\nNext steps:")
    print_info("1. Complete setup wizard at admin console")
    print_info("2. Configure identity provider")
    print_info("3. Deploy remote nodes if needed")

def install_binary(args):
    """Install Pangolin as standalone binary"""
    print_header("Installing Pangolin Binary")

    install_dir = Path(args.install_dir).expanduser()
    install_dir.mkdir(parents=True, exist_ok=True)

    print_info(f"Installation directory: {install_dir}")

    # Determine architecture
    import platform
    arch = platform.machine()
    os_type = platform.system().lower()

    print_info(f"Detected: {os_type} {arch}")

    # Download binary (placeholder - actual URL would come from Pangolin)
    binary_url = f"https://downloads.pangolin.net/latest/pangolin-server-{os_type}-{arch}"

    print_info(f"Downloading from: {binary_url}")

    binary_path = install_dir / "pangolin-server"

    # Download using curl or wget
    if Path('/usr/bin/curl').exists() or Path('/usr/local/bin/curl').exists():
        returncode, _, _ = run_command(
            ['curl', '-L', '-o', str(binary_path), binary_url],
            check=False
        )
    else:
        returncode, _, _ = run_command(
            ['wget', '-O', str(binary_path), binary_url],
            check=False
        )

    if returncode != 0:
        print_error("Failed to download binary")
        print_warning("Note: This is a placeholder URL. Check https://docs.pangolin.net/ for actual download link")
        sys.exit(1)

    # Make executable
    os.chmod(binary_path, 0o755)
    print_success(f"Binary installed: {binary_path}")

    # Create systemd service (Linux only)
    if platform.system() == 'Linux':
        create_systemd_service(binary_path, args)

def create_systemd_service(binary_path: Path, args):
    """Create systemd service for Pangolin"""
    print_header("Creating systemd service")

    service_content = f"""[Unit]
Description=Pangolin Server
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'pangolin')}
ExecStart={binary_path} serve
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
"""

    service_file = Path("/etc/systemd/system/pangolin.service")

    print_info("Creating systemd service file (requires sudo)...")

    try:
        # Write service file (requires sudo)
        returncode, _, _ = run_command(
            ['sudo', 'tee', str(service_file)],
            check=False
        )

        if returncode == 0:
            # Reload systemd
            run_command(['sudo', 'systemctl', 'daemon-reload'], check=False)
            run_command(['sudo', 'systemctl', 'enable', 'pangolin'], check=False)

            print_success("Systemd service created and enabled")
            print_info("Start service: sudo systemctl start pangolin")
        else:
            print_warning("Failed to create systemd service (continuing without it)")
    except Exception as e:
        print_warning(f"Could not create systemd service: {e}")

def deploy_remote_node(args):
    """Deploy Pangolin remote node"""
    print_header("Deploying Pangolin Remote Node")

    print_info("Using automated installer...")
    print_info(f"Node name: {args.node_name}")
    print_info(f"Server URL: {args.server_url}")

    # Download and run installer
    installer_url = "https://install.pangolin.net/node.sh"

    print_info(f"Downloading installer from: {installer_url}")

    # Download installer
    returncode, stdout, _ = run_command(
        ['curl', '-fsSL', installer_url],
        check=False,
        capture=True
    )

    if returncode != 0:
        print_error("Failed to download installer")
        print_warning("Note: Check https://docs.pangolin.net/ for actual installer URL")
        sys.exit(1)

    # Save installer
    installer_path = Path("/tmp/pangolin-node-installer.sh")
    with open(installer_path, 'w') as f:
        f.write(stdout)

    os.chmod(installer_path, 0o755)

    # Run installer
    print_header("Running installer")

    env = os.environ.copy()
    env['PANGOLIN_SERVER_URL'] = args.server_url
    env['PANGOLIN_NODE_NAME'] = args.node_name
    if args.auth_token:
        env['PANGOLIN_AUTH_TOKEN'] = args.auth_token

    returncode = subprocess.call(
        [str(installer_path)],
        env=env
    )

    if returncode == 0:
        print_success("Remote node deployed successfully!")
    else:
        print_error("Deployment failed")
        sys.exit(1)

def verify_installation(args):
    """Verify Pangolin installation"""
    print_header("Verifying Pangolin Installation")

    checks = {}

    # Check if Docker containers are running
    if Path(args.install_dir).exists():
        compose_file = Path(args.install_dir) / "docker-compose.yml"

        if compose_file.exists():
            print_info("Checking Docker containers...")
            returncode, stdout, _ = run_command(
                ['docker-compose', 'ps'],
                check=False,
                capture=True
            )

            if returncode != 0:
                returncode, stdout, _ = run_command(
                    ['docker', 'compose', 'ps'],
                    check=False,
                    capture=True
                )

            if returncode == 0:
                if 'Up' in stdout or 'running' in stdout.lower():
                    print_success("Docker containers running")
                    checks['containers'] = True
                else:
                    print_error("Docker containers not running")
                    checks['containers'] = False
            else:
                print_warning("Could not check container status")
                checks['containers'] = False
        else:
            print_info("Not a Docker installation")

    # Check if service is responding
    print_info("Checking service connectivity...")

    # Try localhost first
    returncode, _, _ = run_command(
        ['curl', '-k', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'https://localhost'],
        check=False,
        capture=True
    )

    if returncode == 0:
        print_success("Service responding on localhost")
        checks['service'] = True
    else:
        print_warning("Service not responding on localhost")
        checks['service'] = False

    # Summary
    print_header("Verification Summary")

    all_passed = all(checks.values())

    if all_passed:
        print_success("All checks passed! ✅")
        return 0
    else:
        print_warning("Some checks failed")
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
        return 1

def health_check(args):
    """Comprehensive health check of Pangolin homelab"""
    print_header("Pangolin Homelab Health Check")

    results = {
        'services': {},
        'connectivity': {},
        'resources': {},
        'configuration': {}
    }

    # Check services
    print_header("Checking Services")

    # Docker containers
    if Path(args.install_dir).exists():
        os.chdir(args.install_dir)
        returncode, stdout, _ = run_command(
            ['docker', 'ps', '--filter', 'name=pangolin', '--format', '{{.Names}}\t{{.Status}}'],
            check=False,
            capture=True
        )

        if returncode == 0 and stdout.strip():
            for line in stdout.strip().split('\n'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    container_name = parts[0]
                    status = parts[1]
                    is_running = 'Up' in status

                    results['services'][container_name] = is_running

                    if is_running:
                        print_success(f"{container_name}: {status}")
                    else:
                        print_error(f"{container_name}: {status}")
        else:
            print_info("No Docker containers found")

    # Check connectivity
    print_header("Checking Connectivity")

    endpoints = [
        ('localhost', 'https://localhost'),
        ('admin', 'http://localhost:8080'),
    ]

    for name, url in endpoints:
        returncode, stdout, _ = run_command(
            ['curl', '-k', '-s', '-o', '/dev/null', '-w', '%{http_code}', url, '--connect-timeout', '5'],
            check=False,
            capture=True
        )

        if returncode == 0:
            status_code = stdout.strip()
            is_ok = status_code.startswith('2') or status_code.startswith('3')

            results['connectivity'][name] = is_ok

            if is_ok:
                print_success(f"{name}: HTTP {status_code}")
            else:
                print_warning(f"{name}: HTTP {status_code}")
        else:
            results['connectivity'][name] = False
            print_error(f"{name}: Connection failed")

    # Check resources
    print_header("Checking Resources")

    # Disk space
    returncode, stdout, _ = run_command(['df', '-h', args.install_dir], check=False, capture=True)
    if returncode == 0:
        lines = stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            if len(parts) >= 5:
                used_percent = parts[4].rstrip('%')
                avail = parts[3]

                results['resources']['disk_used_percent'] = int(used_percent)
                results['resources']['disk_available'] = avail

                if int(used_percent) < 80:
                    print_success(f"Disk space: {avail} available ({used_percent}% used)")
                else:
                    print_warning(f"Disk space: {avail} available ({used_percent}% used)")

    # Memory (if on Linux)
    if Path('/proc/meminfo').exists():
        with open('/proc/meminfo') as f:
            meminfo = f.read()

        for line in meminfo.split('\n'):
            if line.startswith('MemAvailable'):
                parts = line.split()
                if len(parts) >= 2:
                    avail_kb = int(parts[1])
                    avail_gb = avail_kb / 1024 / 1024

                    results['resources']['memory_available_gb'] = round(avail_gb, 2)

                    if avail_gb > 1:
                        print_success(f"Memory: {avail_gb:.1f} GB available")
                    else:
                        print_warning(f"Memory: {avail_gb:.1f} GB available (low)")
                break

    # Configuration check
    print_header("Checking Configuration")

    config_file = Path(args.install_dir) / "config" / "config.yml"
    if config_file.exists():
        print_success(f"Config file found: {config_file}")
        results['configuration']['config_exists'] = True
    else:
        print_warning(f"Config file not found: {config_file}")
        results['configuration']['config_exists'] = False

    # Overall health
    print_header("Health Summary")

    all_services_ok = all(results['services'].values()) if results['services'] else True
    all_connectivity_ok = all(results['connectivity'].values()) if results['connectivity'] else True
    disk_ok = results['resources'].get('disk_used_percent', 0) < 90

    if all_services_ok and all_connectivity_ok and disk_ok:
        print_success("✅ Homelab is healthy!")
        return 0
    else:
        print_warning("⚠️ Some issues detected")
        if not all_services_ok:
            print_warning("  - Some services not running properly")
        if not all_connectivity_ok:
            print_warning("  - Some endpoints not accessible")
        if not disk_ok:
            print_warning("  - Disk space running low")
        return 1

def test_homelab(args):
    """Comprehensive testing of Pangolin homelab"""
    print_header("Pangolin Homelab Comprehensive Testing")

    test_results = []

    # Test 1: Prerequisites
    print_header("Test 1: Prerequisites")
    checks = check_prerequisites()
    test_results.append(('prerequisites', all(checks.values())))

    # Test 2: Installation verification
    print_header("Test 2: Installation Verification")
    result = verify_installation(args)
    test_results.append(('installation', result == 0))

    # Test 3: Health check
    print_header("Test 3: Health Check")
    result = health_check(args)
    test_results.append(('health', result == 0))

    # Test 4: Service response
    print_header("Test 4: Service Response Test")

    endpoints = [
        'https://localhost',
        'http://localhost:8080'
    ]

    service_ok = True
    for endpoint in endpoints:
        returncode, _, _ = run_command(
            ['curl', '-k', '-s', '-o', '/dev/null', '-w', '%{http_code}', endpoint, '--connect-timeout', '10'],
            check=False,
            capture=True
        )

        if returncode != 0:
            service_ok = False
            print_error(f"Failed to connect to: {endpoint}")
        else:
            print_success(f"Connected to: {endpoint}")

    test_results.append(('service_response', service_ok))

    # Test 5: Configuration validation
    print_header("Test 5: Configuration Validation")

    config_file = Path(args.install_dir) / "config" / "config.yml"
    config_valid = config_file.exists()

    if config_valid:
        print_success("Configuration file exists")
    else:
        print_error("Configuration file missing")

    test_results.append(('configuration', config_valid))

    # Test 6: Data persistence
    print_header("Test 6: Data Persistence Check")

    data_dir = Path(args.install_dir) / "data"
    data_ok = data_dir.exists() and data_dir.is_dir()

    if data_ok:
        print_success("Data directory exists")

        # Check if writable
        test_file = data_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()
            print_success("Data directory is writable")
        except Exception as e:
            print_error(f"Data directory not writable: {e}")
            data_ok = False
    else:
        print_error("Data directory missing")

    test_results.append(('data_persistence', data_ok))

    # Summary
    print_header("Test Summary")

    total_tests = len(test_results)
    passed_tests = sum(1 for _, passed in test_results if passed)

    print(f"\nTotal tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")

    print("\nDetailed Results:")
    for test_name, passed in test_results:
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"  {status} {test_name}")

    if passed_tests == total_tests:
        print(f"\n{Colors.GREEN}✅ All tests passed!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}⚠️ {total_tests - passed_tests} test(s) failed{Colors.RESET}")
        return 1

def troubleshoot(args):
    """Troubleshoot Pangolin homelab issues"""
    print_header("Pangolin Homelab Troubleshooting")

    issues_found = []

    # Check if installation exists
    install_dir = Path(args.install_dir).expanduser()

    if not install_dir.exists():
        issues_found.append({
            'issue': 'Installation directory not found',
            'fix': f'Run: python3 tool.py setup --install-dir {args.install_dir}'
        })
        print_error(f"Installation directory not found: {install_dir}")
    else:
        print_success(f"Installation directory exists: {install_dir}")

    # Check Docker
    if (install_dir / "docker-compose.yml").exists():
        print_info("Docker installation detected")

        # Check if containers are running
        returncode, stdout, _ = run_command(
            ['docker', 'ps', '--filter', 'name=pangolin', '--format', '{{.Names}}\t{{.Status}}'],
            check=False,
            capture=True
        )

        if returncode == 0:
            if not stdout.strip():
                issues_found.append({
                    'issue': 'No Pangolin containers running',
                    'fix': f'Run: cd {install_dir} && docker-compose up -d'
                })
                print_error("No Pangolin containers running")
            else:
                print_success("Containers found:")
                for line in stdout.strip().split('\n'):
                    print(f"  {line}")
        else:
            issues_found.append({
                'issue': 'Cannot query Docker containers',
                'fix': 'Check if Docker is running: docker ps'
            })

    # Check logs
    print_header("Checking Recent Logs")

    if (install_dir / "docker-compose.yml").exists():
        os.chdir(install_dir)
        print_info("Recent Docker logs:")
        run_command(['docker-compose', 'logs', '--tail=20'], check=False)

    # Check ports
    print_header("Checking Ports")

    import socket
    ports_to_check = [443, 8080]

    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()

        if result == 0:
            print_success(f"Port {port} is open")
        else:
            print_warning(f"Port {port} is not accessible")
            issues_found.append({
                'issue': f'Port {port} not accessible',
                'fix': f'Check if service is running and firewall allows port {port}'
            })

    # Print fixes
    if issues_found:
        print_header("Issues Found & Recommended Fixes")

        for i, issue_info in enumerate(issues_found, 1):
            print(f"\n{i}. {Colors.RED}Issue:{Colors.RESET} {issue_info['issue']}")
            print(f"   {Colors.GREEN}Fix:{Colors.RESET} {issue_info['fix']}")

        return 1
    else:
        print_header("Troubleshooting Complete")
        print_success("No issues detected!")
        return 0

def main():
    parser = argparse.ArgumentParser(
        description="Pangolin Homelab Setup & Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup Pangolin homelab with Docker
  python3 tool.py setup --method docker --domain pangolin.local

  # Deploy remote node
  python3 tool.py deploy-node --server-url https://pangolin.local --node-name home-node

  # Verify installation
  python3 tool.py verify

  # Run comprehensive tests
  python3 tool.py test

  # Health check
  python3 tool.py health-check

  # Troubleshoot issues
  python3 tool.py troubleshoot

Documentation: https://docs.pangolin.net/
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Install Pangolin homelab')
    setup_parser.add_argument('--method', choices=['auto', 'docker', 'binary'], default='auto',
                             help='Installation method (default: auto)')
    setup_parser.add_argument('--install-dir', default='~/pangolin',
                             help='Installation directory (default: ~/pangolin)')
    setup_parser.add_argument('--domain', default='pangolin.local',
                             help='Pangolin domain (default: pangolin.local)')
    setup_parser.add_argument('--admin-email', default='admin@pangolin.local',
                             help='Admin email (default: admin@pangolin.local)')
    setup_parser.add_argument('--port', type=int, default=443,
                             help='HTTPS port (default: 443)')
    setup_parser.add_argument('--admin-port', type=int, default=8080,
                             help='Admin console port (default: 8080)')
    setup_parser.add_argument('--image', default='pangolin/server:latest',
                             help='Docker image (default: pangolin/server:latest)')

    # Deploy node command
    node_parser = subparsers.add_parser('deploy-node', help='Deploy Pangolin remote node')
    node_parser.add_argument('--server-url', required=True,
                            help='Pangolin server URL')
    node_parser.add_argument('--node-name', required=True,
                            help='Node name')
    node_parser.add_argument('--auth-token',
                            help='Authentication token (optional)')

    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify installation')
    verify_parser.add_argument('--install-dir', default='~/pangolin',
                              help='Installation directory (default: ~/pangolin)')

    # Test command
    test_parser = subparsers.add_parser('test', help='Run comprehensive tests')
    test_parser.add_argument('--install-dir', default='~/pangolin',
                            help='Installation directory (default: ~/pangolin)')

    # Health check command
    health_parser = subparsers.add_parser('health-check', help='Check homelab health')
    health_parser.add_argument('--install-dir', default='~/pangolin',
                              help='Installation directory (default: ~/pangolin)')

    # Troubleshoot command
    troubleshoot_parser = subparsers.add_parser('troubleshoot', help='Troubleshoot issues')
    troubleshoot_parser.add_argument('--install-dir', default='~/pangolin',
                                    help='Installation directory (default: ~/pangolin)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    try:
        if args.command == 'setup':
            install_pangolin_server(args)
        elif args.command == 'deploy-node':
            deploy_remote_node(args)
        elif args.command == 'verify':
            sys.exit(verify_installation(args))
        elif args.command == 'test':
            sys.exit(test_homelab(args))
        elif args.command == 'health-check':
            sys.exit(health_check(args))
        elif args.command == 'troubleshoot':
            sys.exit(troubleshoot(args))
        else:
            parser.print_help()
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
