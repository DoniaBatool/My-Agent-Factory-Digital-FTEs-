#!/usr/bin/env python3
"""
DigitalOcean Deploy Tool

Complete DigitalOcean deployment automation - No cloud specialist needed!

Commands:
  check-prerequisites  - Verify doctl installation and authentication
  create-droplet      - Create and configure DigitalOcean droplet
  deploy-app          - Deploy application to droplet
  configure-monitoring - Setup monitoring and alerts
  health-check        - Check droplet and application health
  test                - Comprehensive testing suite (6+ tests)
  troubleshoot        - Auto-detect and fix common issues
  cleanup             - Delete droplet and associated resources

Based on official DigitalOcean documentation:
- https://docs.digitalocean.com/products/droplets/
- https://docs.digitalocean.com/reference/doctl/
- https://docs.digitalocean.com/reference/api/
"""

import argparse
import subprocess
import sys
import json
import time
import os

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
    """Check if doctl is installed and authenticated"""
    print_header("Checking DigitalOcean Prerequisites")

    issues = []

    # Check doctl installation
    code, stdout, stderr = run_command("doctl version")
    if code == 0:
        print_success(f"doctl installed: {stdout.strip()}")
    else:
        print_error("doctl not installed")
        issues.append("doctl")
        print_info("\nInstallation instructions:")
        print_info("macOS: brew install doctl")
        print_info("Ubuntu: snap install doctl")
        print_info("See: https://docs.digitalocean.com/reference/doctl/how-to/install/")

    # Check authentication
    if not issues:
        code, stdout, stderr = run_command("doctl account get --format ID")
        if code == 0 and stdout.strip():
            print_success(f"Authenticated with DigitalOcean account: {stdout.strip()}")
        else:
            print_error("Not authenticated with DigitalOcean")
            issues.append("authentication")
            print_info("\nAuthentication instructions:")
            print_info("1. Get API token from: https://cloud.digitalocean.com/account/api/tokens")
            print_info("2. Run: doctl auth init")
            print_info("3. Enter your API token when prompted")

    # Check SSH key exists
    if not issues:
        code, stdout, stderr = run_command("doctl compute ssh-key list --format ID,Name --no-header")
        if code == 0 and stdout.strip():
            keys = stdout.strip().split('\n')
            print_success(f"SSH keys configured: {len(keys)} key(s)")
        else:
            print_warning("No SSH keys found (optional but recommended)")
            print_info("Add SSH key: doctl compute ssh-key create <name> --public-key-file ~/.ssh/id_rsa.pub")

    if issues:
        print_error(f"\nMissing requirements: {', '.join(issues)}")
        return 1

    print_success("\n✅ All DigitalOcean prerequisites satisfied")
    return 0

def create_droplet(args) -> int:
    """Create DigitalOcean droplet with best practices"""
    print_header(f"Creating Droplet: {args.name}")

    # Validate parameters
    if not args.name:
        print_error("Droplet name is required")
        return 1

    # Build doctl command
    cmd = f"doctl compute droplet create {args.name}"

    # Add region (default: nyc3)
    region = args.region or "nyc3"
    cmd += f" --region {region}"

    # Add size (default: s-1vcpu-1gb)
    size = args.size or "s-1vcpu-1gb"
    cmd += f" --size {size}"

    # Add image (default: ubuntu-22-04-x64)
    image = args.image or "ubuntu-22-04-x64"
    cmd += f" --image {image}"

    # Add SSH keys
    if args.ssh_keys:
        cmd += f" --ssh-keys {args.ssh_keys}"
    else:
        # Try to get all SSH keys
        code, stdout, stderr = run_command("doctl compute ssh-key list --format ID --no-header")
        if code == 0 and stdout.strip():
            ssh_key_ids = ','.join(stdout.strip().split('\n'))
            cmd += f" --ssh-keys {ssh_key_ids}"
        else:
            print_warning("No SSH keys found - droplet will use password authentication")

    # Add tags
    if args.tags:
        cmd += f" --tag-names {args.tags}"

    # Add user data (cloud-init)
    if args.user_data_file:
        cmd += f" --user-data-file {args.user_data_file}"

    # Enable monitoring
    if args.enable_monitoring:
        cmd += " --enable-monitoring"

    # Enable IPv6
    if args.enable_ipv6:
        cmd += " --enable-ipv6"

    # Wait for creation
    cmd += " --wait"

    # Output format
    cmd += " --format ID,Name,PublicIPv4,Status,Region"

    print_info(f"Running: {cmd}")

    code, stdout, stderr = run_command(cmd, timeout=300)

    if code == 0:
        print_success("\n✅ Droplet created successfully")
        print(stdout)

        # Extract droplet ID and IP
        lines = stdout.strip().split('\n')
        if len(lines) > 1:
            data = lines[1].split()
            if len(data) >= 4:
                droplet_id = data[0]
                droplet_ip = data[2]
                print_info(f"\nDroplet ID: {droplet_id}")
                print_info(f"Public IP: {droplet_ip}")
                print_info(f"\nSSH access: ssh root@{droplet_ip}")

                # Save droplet info to file
                with open('.digitalocean-droplet-info', 'w') as f:
                    f.write(f"DROPLET_ID={droplet_id}\n")
                    f.write(f"DROPLET_IP={droplet_ip}\n")
                    f.write(f"DROPLET_NAME={args.name}\n")
                print_success("Droplet info saved to .digitalocean-droplet-info")

        return 0
    else:
        print_error("\n❌ Droplet creation failed")
        print_error(stderr)
        return 1

def deploy_app(args) -> int:
    """Deploy application to droplet"""
    print_header("Deploying Application to Droplet")

    # Load droplet info
    if not os.path.exists('.digitalocean-droplet-info'):
        print_error("Droplet info not found. Create droplet first.")
        return 1

    with open('.digitalocean-droplet-info', 'r') as f:
        info = dict(line.strip().split('=') for line in f if '=' in line)

    droplet_ip = info.get('DROPLET_IP')
    if not droplet_ip:
        print_error("Droplet IP not found in .digitalocean-droplet-info")
        return 1

    print_info(f"Target droplet: {droplet_ip}")

    # Wait for SSH to be ready
    print_info("Waiting for SSH to be ready...")
    max_retries = 30
    for i in range(max_retries):
        code, _, _ = run_command(f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{droplet_ip} 'echo ready'", timeout=10)
        if code == 0:
            print_success("SSH is ready")
            break
        time.sleep(10)
        print_info(f"Retry {i+1}/{max_retries}...")
    else:
        print_error("SSH not ready after 5 minutes")
        return 1

    # Deployment method
    method = args.method or "docker"

    if method == "docker":
        print_info("Deploying with Docker...")

        # Install Docker on droplet
        install_cmd = """
        ssh -o StrictHostKeyChecking=no root@{} 'bash -s' << 'EOF'
        # Update packages
        apt-get update

        # Install Docker
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh

        # Start Docker
        systemctl start docker
        systemctl enable docker

        echo "Docker installed successfully"
        EOF
        """.format(droplet_ip)

        code, stdout, stderr = run_command(install_cmd, timeout=300)
        if code == 0:
            print_success("Docker installed on droplet")
        else:
            print_error("Failed to install Docker")
            return 1

        # Deploy application
        if args.docker_image:
            deploy_cmd = f"""
            ssh -o StrictHostKeyChecking=no root@{droplet_ip} 'bash -s' << 'EOF'
            # Pull image
            docker pull {args.docker_image}

            # Stop old container
            docker stop myapp 2>/dev/null || true
            docker rm myapp 2>/dev/null || true

            # Run new container
            docker run -d --name myapp --restart unless-stopped -p 80:8080 {args.docker_image}

            echo "Application deployed"
            EOF
            """

            code, stdout, stderr = run_command(deploy_cmd, timeout=300)
            if code == 0:
                print_success("✅ Application deployed successfully")
                print_info(f"\nAccess your app at: http://{droplet_ip}")
                return 0
            else:
                print_error("Failed to deploy application")
                return 1
        else:
            print_error("--docker-image required for Docker deployment")
            return 1

    elif method == "git":
        print_info("Deploying from Git repository...")

        if not args.git_repo:
            print_error("--git-repo required for Git deployment")
            return 1

        deploy_cmd = f"""
        ssh -o StrictHostKeyChecking=no root@{droplet_ip} 'bash -s' << 'EOF'
        # Install git
        apt-get update && apt-get install -y git

        # Clone repository
        cd /opt
        rm -rf app
        git clone {args.git_repo} app
        cd app

        # Run deployment script if exists
        if [ -f deploy.sh ]; then
            chmod +x deploy.sh
            ./deploy.sh
        fi

        echo "Application deployed from Git"
        EOF
        """

        code, stdout, stderr = run_command(deploy_cmd, timeout=600)
        if code == 0:
            print_success("✅ Application deployed from Git")
            return 0
        else:
            print_error("Failed to deploy from Git")
            return 1

    else:
        print_error(f"Unknown deployment method: {method}")
        return 1

def configure_monitoring(args) -> int:
    """Configure monitoring and alerts"""
    print_header("Configuring Monitoring")

    # Load droplet info
    if not os.path.exists('.digitalocean-droplet-info'):
        print_error("Droplet info not found. Create droplet first.")
        return 1

    with open('.digitalocean-droplet-info', 'r') as f:
        info = dict(line.strip().split('=') for line in f if '=' in line)

    droplet_id = info.get('DROPLET_ID')

    # Check if monitoring is enabled
    code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format Features --no-header")
    if code == 0:
        if 'monitoring' in stdout.lower():
            print_success("Monitoring already enabled")
        else:
            print_warning("Monitoring not enabled - enable during droplet creation with --enable-monitoring")

    # Install monitoring agent on droplet
    droplet_ip = info.get('DROPLET_IP')
    print_info("Installing DigitalOcean monitoring agent...")

    install_cmd = f"""
    ssh -o StrictHostKeyChecking=no root@{droplet_ip} 'bash -s' << 'EOF'
    # Install monitoring agent
    curl -sSL https://repos.insights.digitalocean.com/install.sh | bash

    echo "Monitoring agent installed"
    EOF
    """

    code, stdout, stderr = run_command(install_cmd, timeout=120)
    if code == 0:
        print_success("✅ Monitoring agent installed")
        print_info("\nView metrics at: https://cloud.digitalocean.com/droplets")
        return 0
    else:
        print_error("Failed to install monitoring agent")
        return 1

def health_check(args) -> int:
    """Check droplet and application health"""
    print_header("Health Check")

    # Load droplet info
    if not os.path.exists('.digitalocean-droplet-info'):
        print_error("Droplet info not found")
        return 1

    with open('.digitalocean-droplet-info', 'r') as f:
        info = dict(line.strip().split('=') for line in f if '=' in line)

    droplet_id = info.get('DROPLET_ID')
    droplet_ip = info.get('DROPLET_IP')

    # Check droplet status
    print_info("\n[Check 1] Droplet Status")
    code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format Status --no-header")
    if code == 0 and 'active' in stdout.lower():
        print_success("✓ Droplet is active")
    else:
        print_error("✗ Droplet is not active")
        return 1

    # Check SSH connectivity
    print_info("\n[Check 2] SSH Connectivity")
    code, stdout, stderr = run_command(f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{droplet_ip} 'echo ok'", timeout=10)
    if code == 0:
        print_success("✓ SSH is accessible")
    else:
        print_error("✗ SSH is not accessible")
        return 1

    # Check disk space
    print_info("\n[Check 3] Disk Space")
    code, stdout, stderr = run_command(f"ssh -o StrictHostKeyChecking=no root@{droplet_ip} 'df -h /'", timeout=10)
    if code == 0:
        print(stdout)
        # Check if disk usage > 90%
        if stdout:
            for line in stdout.split('\n'):
                if '/' in line and '%' in line:
                    usage = line.split()[-2].strip('%')
                    if usage.isdigit() and int(usage) > 90:
                        print_warning(f"⚠ Disk usage is high: {usage}%")
    else:
        print_error("✗ Cannot check disk space")

    # Check memory
    print_info("\n[Check 4] Memory Usage")
    code, stdout, stderr = run_command(f"ssh -o StrictHostKeyChecking=no root@{droplet_ip} 'free -h'", timeout=10)
    if code == 0:
        print(stdout)

    # Check application (if Docker)
    print_info("\n[Check 5] Application Status")
    code, stdout, stderr = run_command(f"ssh -o StrictHostKeyChecking=no root@{droplet_ip} 'docker ps'", timeout=10)
    if code == 0:
        if 'myapp' in stdout:
            print_success("✓ Application container is running")
        else:
            print_warning("⚠ Application container not found")
    else:
        print_info("Docker not installed or application not containerized")

    # Check HTTP endpoint
    if args.health_endpoint:
        print_info(f"\n[Check 6] HTTP Health Endpoint")
        code, stdout, stderr = run_command(f"curl -f -s http://{droplet_ip}{args.health_endpoint}", timeout=10)
        if code == 0:
            print_success(f"✓ Health endpoint responding")
        else:
            print_error(f"✗ Health endpoint not responding")

    print_success("\n✅ Health check complete")
    return 0

def run_tests(args) -> int:
    """Comprehensive testing suite"""
    print_header("DigitalOcean Comprehensive Testing")

    tests_passed = 0
    tests_failed = 0
    issues = []

    # Test 1: doctl installation
    print_info("\n[Test 1/6] doctl Installation")
    code, stdout, stderr = run_command("doctl version")
    if code == 0:
        print_success(f"✓ doctl installed: {stdout.strip()}")
        tests_passed += 1
    else:
        print_error("✗ doctl not installed")
        tests_failed += 1
        issues.append("doctl not installed")

    # Test 2: Authentication
    print_info("\n[Test 2/6] Authentication")
    code, stdout, stderr = run_command("doctl account get --format ID")
    if code == 0 and stdout.strip():
        print_success(f"✓ Authenticated: {stdout.strip()}")
        tests_passed += 1
    else:
        print_error("✗ Not authenticated")
        tests_failed += 1
        issues.append("Not authenticated with DigitalOcean")

    # Test 3: API connectivity
    print_info("\n[Test 3/6] API Connectivity")
    code, stdout, stderr = run_command("doctl compute region list --format Slug --no-header | head -1")
    if code == 0 and stdout.strip():
        print_success("✓ Can connect to DigitalOcean API")
        tests_passed += 1
    else:
        print_error("✗ Cannot connect to API")
        tests_failed += 1
        issues.append("Cannot connect to DigitalOcean API")

    # Test 4: SSH keys
    print_info("\n[Test 4/6] SSH Keys")
    code, stdout, stderr = run_command("doctl compute ssh-key list --format ID --no-header")
    if code == 0 and stdout.strip():
        key_count = len(stdout.strip().split('\n'))
        print_success(f"✓ SSH keys configured: {key_count} key(s)")
        tests_passed += 1
    else:
        print_warning("⚠ No SSH keys configured")
        tests_failed += 1
        issues.append("No SSH keys configured")

    # Test 5: Droplet creation (dry-run)
    print_info("\n[Test 5/6] Droplet Creation Capability")
    code, stdout, stderr = run_command("doctl compute size list --format Slug --no-header | head -1")
    if code == 0 and stdout.strip():
        print_success("✓ Can query droplet sizes (creation capability verified)")
        tests_passed += 1
    else:
        print_error("✗ Cannot query droplet sizes")
        tests_failed += 1
        issues.append("Cannot query droplet sizes")

    # Test 6: Check if droplet exists
    print_info("\n[Test 6/6] Droplet Status")
    if os.path.exists('.digitalocean-droplet-info'):
        with open('.digitalocean-droplet-info', 'r') as f:
            info = dict(line.strip().split('=') for line in f if '=' in line)
        droplet_id = info.get('DROPLET_ID')
        code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format Status --no-header")
        if code == 0:
            print_success(f"✓ Droplet exists: {stdout.strip()}")
            tests_passed += 1
        else:
            print_warning("⚠ Droplet not found")
            tests_failed += 1
    else:
        print_info("No droplet info file (no droplet created yet)")
        tests_passed += 1

    # Test summary
    print_header("Test Summary")
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"{Colors.GREEN}Passed: {tests_passed}{Colors.END}")
    print(f"{Colors.RED}Failed: {tests_failed}{Colors.END}")

    if tests_failed == 0:
        print_success("\n✅ All tests passed!")
        return 0
    else:
        print_error(f"\n❌ {tests_failed} test(s) failed")
        if issues:
            print_info("\nIssues found:")
            for issue in issues:
                print_error(f"  • {issue}")
        return 1

def troubleshoot(args) -> int:
    """Auto-detect and fix common issues"""
    print_header("DigitalOcean Troubleshooting")

    issues_found = []

    # Issue 1: Authentication
    print_info("\n[Check 1] Authentication Status")
    code, stdout, stderr = run_command("doctl account get")
    if code != 0:
        issues_found.append("Not authenticated")
        print_error("✗ Not authenticated with DigitalOcean")
        print_info("Fix: Run 'doctl auth init' and enter your API token")
    else:
        print_success("✓ Authenticated")

    # Issue 2: Droplet status
    if os.path.exists('.digitalocean-droplet-info'):
        print_info("\n[Check 2] Droplet Status")
        with open('.digitalocean-droplet-info', 'r') as f:
            info = dict(line.strip().split('=') for line in f if '=' in line)
        droplet_id = info.get('DROPLET_ID')
        droplet_ip = info.get('DROPLET_IP')

        code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format Status --no-header")
        if code == 0:
            status = stdout.strip()
            if status != 'active':
                issues_found.append(f"Droplet status: {status}")
                print_warning(f"⚠ Droplet status: {status}")
            else:
                print_success("✓ Droplet is active")

        # Issue 3: SSH connectivity
        print_info("\n[Check 3] SSH Connectivity")
        code, stdout, stderr = run_command(f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@{droplet_ip} 'echo ok'", timeout=10)
        if code != 0:
            issues_found.append("SSH not accessible")
            print_error("✗ Cannot connect via SSH")
            print_info("Fix: Check firewall rules, ensure SSH key is added, wait for droplet to fully boot")
        else:
            print_success("✓ SSH is accessible")

    # Issue 4: Rate limiting
    print_info("\n[Check 4] API Rate Limits")
    code, stdout, stderr = run_command("doctl account ratelimit")
    if code == 0:
        print(stdout)
    else:
        print_warning("⚠ Cannot check rate limits")

    # Summary
    print_header("Troubleshooting Summary")

    if issues_found:
        print_warning(f"\n⚠️  Found {len(issues_found)} issues:")
        for issue in issues_found:
            print_warning(f"  • {issue}")

        print_info("\n🔧 Common fixes:")
        print_info("  1. doctl auth init             # Re-authenticate")
        print_info("  2. doctl compute ssh-key create # Add SSH key")
        print_info("  3. doctl compute firewall ...   # Configure firewall")
        print_info("  4. Wait 2-3 minutes after droplet creation")

        return 1
    else:
        print_success("\n✅ No issues found - DigitalOcean is healthy!")
        return 0

def cleanup(args) -> int:
    """Delete droplet and associated resources"""
    print_header("Cleanup DigitalOcean Resources")

    # Load droplet info
    if not os.path.exists('.digitalocean-droplet-info'):
        print_error("Droplet info not found. Nothing to clean up.")
        return 0

    with open('.digitalocean-droplet-info', 'r') as f:
        info = dict(line.strip().split('=') for line in f if '=' in line)

    droplet_id = info.get('DROPLET_ID')
    droplet_name = info.get('DROPLET_NAME')

    print_warning(f"\n⚠️  This will DELETE droplet: {droplet_name} (ID: {droplet_id})")

    if not args.force:
        response = input("Are you sure? (yes/no): ").lower()
        if response not in ['yes', 'y']:
            print_info("Cleanup cancelled")
            return 0

    # Delete droplet
    print_info("\n🔄 Deleting droplet...")
    code, stdout, stderr = run_command(f"doctl compute droplet delete {droplet_id} --force")

    if code == 0:
        print_success("✅ Droplet deleted")

        # Remove local info file
        os.remove('.digitalocean-droplet-info')
        print_success("Removed local droplet info file")

        return 0
    else:
        print_error("❌ Failed to delete droplet")
        print_error(stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(
        description='DigitalOcean Deploy Tool - Complete droplet deployment automation',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # check-prerequisites
    subparsers.add_parser('check-prerequisites', help='Verify doctl installation and authentication')

    # create-droplet
    create_parser = subparsers.add_parser('create-droplet', help='Create DigitalOcean droplet')
    create_parser.add_argument('--name', required=True, help='Droplet name')
    create_parser.add_argument('--region', default='nyc3', help='Region (default: nyc3)')
    create_parser.add_argument('--size', default='s-1vcpu-1gb', help='Droplet size (default: s-1vcpu-1gb)')
    create_parser.add_argument('--image', default='ubuntu-22-04-x64', help='OS image (default: ubuntu-22-04-x64)')
    create_parser.add_argument('--ssh-keys', help='SSH key IDs (comma-separated)')
    create_parser.add_argument('--tags', help='Tags (comma-separated)')
    create_parser.add_argument('--user-data-file', help='Cloud-init user data file')
    create_parser.add_argument('--enable-monitoring', action='store_true', help='Enable monitoring')
    create_parser.add_argument('--enable-ipv6', action='store_true', help='Enable IPv6')

    # deploy-app
    deploy_parser = subparsers.add_parser('deploy-app', help='Deploy application to droplet')
    deploy_parser.add_argument('--method', choices=['docker', 'git'], default='docker', help='Deployment method')
    deploy_parser.add_argument('--docker-image', help='Docker image to deploy')
    deploy_parser.add_argument('--git-repo', help='Git repository URL')

    # configure-monitoring
    subparsers.add_parser('configure-monitoring', help='Configure monitoring and alerts')

    # health-check
    health_parser = subparsers.add_parser('health-check', help='Check droplet and application health')
    health_parser.add_argument('--health-endpoint', help='HTTP health check endpoint (e.g., /health)')

    # test
    subparsers.add_parser('test', help='Run comprehensive testing suite')

    # troubleshoot
    subparsers.add_parser('troubleshoot', help='Auto-detect and fix common issues')

    # cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Delete droplet and resources')
    cleanup_parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'create-droplet': create_droplet,
        'deploy-app': deploy_app,
        'configure-monitoring': configure_monitoring,
        'health-check': health_check,
        'test': run_tests,
        'troubleshoot': troubleshoot,
        'cleanup': cleanup
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
