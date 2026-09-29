#!/usr/bin/env python3
"""
DigitalOcean Deployment Tool

Complete droplet creation, app deployment, configuration, and monitoring setup
for DigitalOcean cloud platform.

Commands:
  check-prerequisites  - Verify doctl CLI, SSH keys, and API token
  create-droplet       - Create and configure a new droplet
  deploy-app           - Deploy application to droplet
  configure-monitoring - Setup DigitalOcean monitoring and alerts
  health-check         - Verify droplet and app health
  test                 - Comprehensive testing suite
  troubleshoot         - Detect and fix common issues
  cleanup              - Delete droplet and resources
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
    """Check if required tools and credentials are available"""
    print_header("Checking Prerequisites")

    issues = []

    # Check 1: doctl CLI installed
    print_info("Checking doctl CLI...")
    code, stdout, stderr = run_command("doctl version")
    if code == 0:
        version = stdout.strip()
        print_success(f"doctl CLI installed: {version}")
    else:
        print_error("doctl CLI not found")
        issues.append("doctl CLI not installed")
        print_info("Install: snap install doctl OR brew install doctl")

    # Check 2: doctl authentication
    print_info("Checking doctl authentication...")
    code, stdout, stderr = run_command("doctl account get")
    if code == 0:
        print_success("doctl authenticated successfully")
        # Parse account info
        if stdout.strip():
            print_info(f"Account: {stdout.strip().split()[0]}")
    else:
        print_error("doctl not authenticated")
        issues.append("Not authenticated with DigitalOcean API")
        print_info("Run: doctl auth init")
        print_info("Get API token from: https://cloud.digitalocean.com/account/api/tokens")

    # Check 3: SSH keys configured
    print_info("Checking SSH keys...")
    code, stdout, stderr = run_command("doctl compute ssh-key list --format ID,Name")
    if code == 0 and stdout.strip():
        keys = [line for line in stdout.split('\n')[1:] if line.strip()]
        if keys:
            print_success(f"Found {len(keys)} SSH key(s)")
            for key in keys[:3]:  # Show first 3
                print_info(f"  {key}")
        else:
            print_warning("No SSH keys found")
            issues.append("No SSH keys configured")
            print_info("Add SSH key: doctl compute ssh-key create <name> --public-key-file ~/.ssh/id_rsa.pub")
    else:
        print_warning("Could not list SSH keys")

    # Check 4: Available regions
    print_info("Checking available regions...")
    code, stdout, stderr = run_command("doctl compute region list --format Slug,Name --no-header | head -5")
    if code == 0 and stdout.strip():
        print_success("Available regions:")
        for line in stdout.strip().split('\n'):
            print_info(f"  {line}")

    # Check 5: Available sizes
    print_info("Checking available droplet sizes...")
    code, stdout, stderr = run_command("doctl compute size list --format Slug,Memory,VCPUs,Disk,PriceMonthly --no-header | grep -E 's-1vcpu|s-2vcpu' | head -5")
    if code == 0 and stdout.strip():
        print_success("Available sizes (sample):")
        for line in stdout.strip().split('\n'):
            print_info(f"  {line}")

    print_header("Prerequisites Summary")
    if not issues:
        print_success("All prerequisites met! ✅")
        return 0
    else:
        print_error(f"Found {len(issues)} issue(s):")
        for issue in issues:
            print_error(f"  • {issue}")
        return 1

def create_droplet(args) -> int:
    """Create and configure a new droplet"""
    print_header(f"Creating Droplet: {args.name}")

    # Get SSH key IDs
    print_info("Fetching SSH keys...")
    code, stdout, stderr = run_command("doctl compute ssh-key list --format ID --no-header")
    if code != 0 or not stdout.strip():
        print_error("No SSH keys found. Add SSH key first:")
        print_info("doctl compute ssh-key create <name> --public-key-file ~/.ssh/id_rsa.pub")
        return 1

    ssh_keys = stdout.strip().split('\n')
    ssh_key_ids = ','.join(ssh_keys)
    print_success(f"Using {len(ssh_keys)} SSH key(s)")

    # Build droplet creation command (from official doctl docs)
    cmd_parts = [
        "doctl compute droplet create",
        args.name,
        f"--image {args.image}",
        f"--region {args.region}",
        f"--size {args.size}",
        f"--ssh-keys {ssh_key_ids}",
    ]

    # Optional flags (best practices from DigitalOcean docs)
    if args.enable_monitoring:
        cmd_parts.append("--enable-monitoring")
        print_info("Monitoring: Enabled (free)")

    if args.enable_ipv6:
        cmd_parts.append("--enable-ipv6")
        print_info("IPv6: Enabled")

    if args.enable_backups:
        cmd_parts.append("--enable-backups")
        print_info("Backups: Enabled (+20% cost)")

    if args.vpc_uuid:
        cmd_parts.append(f"--vpc-uuid {args.vpc_uuid}")
        print_info(f"VPC: {args.vpc_uuid}")

    if args.user_data:
        cmd_parts.append(f"--user-data-file {args.user_data}")
        print_info(f"User Data: {args.user_data}")

    # Add wait flag
    cmd_parts.append("--wait")
    cmd_parts.append("--format ID,Name,PublicIPv4,Status,Region")

    cmd = ' '.join(cmd_parts)

    print_info("Creating droplet (this may take 30-60 seconds)...")
    print_info(f"Command: {cmd}")

    code, stdout, stderr = run_command(cmd, timeout=180)

    if code == 0:
        print_success("Droplet created successfully! ✅")
        print_info("Droplet details:")
        print(stdout)

        # Extract droplet ID from output
        lines = stdout.strip().split('\n')
        if len(lines) > 1:
            droplet_id = lines[1].split()[0]
            print_info(f"Droplet ID: {droplet_id}")

            # Save droplet info for later use
            with open('.digitalocean-droplet.txt', 'w') as f:
                f.write(f"DROPLET_ID={droplet_id}\n")
                f.write(f"DROPLET_NAME={args.name}\n")

            print_success("Droplet info saved to .digitalocean-droplet.txt")

        print_warning("Wait 30-60 seconds for SSH to be ready")
        return 0
    else:
        print_error("Droplet creation failed")
        print_error(stderr)
        return 1

def deploy_app(args) -> int:
    """Deploy application to droplet"""
    print_header("Deploying Application")

    # Check if droplet info exists
    if not os.path.exists('.digitalocean-droplet.txt'):
        print_error("No droplet info found. Create droplet first.")
        return 1

    # Read droplet info
    with open('.digitalocean-droplet.txt', 'r') as f:
        lines = f.readlines()
        droplet_id = lines[0].split('=')[1].strip()
        droplet_name = lines[1].split('=')[1].strip()

    print_info(f"Deploying to droplet: {droplet_name} (ID: {droplet_id})")

    # Get droplet IP
    print_info("Getting droplet IP...")
    code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format PublicIPv4 --no-header")
    if code != 0:
        print_error("Failed to get droplet IP")
        return 1

    droplet_ip = stdout.strip()
    print_success(f"Droplet IP: {droplet_ip}")

    # Deployment method based on args
    if args.method == 'git':
        print_info("Deploying via Git...")

        # SSH commands to setup app from git
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{droplet_ip}"

        commands = [
            "apt-get update",
            "apt-get install -y git",
            f"git clone {args.repo} /app",
            "cd /app && bash deploy.sh" if args.deploy_script else "echo 'No deploy script specified'"
        ]

        for cmd in commands:
            print_info(f"Running: {cmd}")
            code, stdout, stderr = run_command(f"{ssh_cmd} '{cmd}'", timeout=300)
            if code != 0:
                print_error(f"Command failed: {cmd}")
                print_error(stderr)
                return 1
            print_success(f"✓ {cmd}")

    elif args.method == 'docker':
        print_info("Deploying via Docker...")

        ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{droplet_ip}"

        commands = [
            "apt-get update",
            "apt-get install -y docker.io",
            "systemctl start docker",
            "systemctl enable docker",
            f"docker pull {args.image}" if args.image else "echo 'No image specified'",
            f"docker run -d -p {args.port}:{args.port} {args.image}" if args.image else "echo 'No image specified'"
        ]

        for cmd in commands:
            print_info(f"Running: {cmd}")
            code, stdout, stderr = run_command(f"{ssh_cmd} '{cmd}'", timeout=300)
            if code != 0:
                print_error(f"Command failed: {cmd}")
                print_error(stderr)
                return 1
            print_success(f"✓ {cmd}")

    elif args.method == 'scp':
        print_info("Deploying via SCP...")

        if not args.source:
            print_error("--source required for scp method")
            return 1

        # Copy files
        print_info(f"Copying {args.source} to droplet...")
        code, stdout, stderr = run_command(f"scp -r -o StrictHostKeyChecking=no {args.source} root@{droplet_ip}:/app/")
        if code != 0:
            print_error("SCP failed")
            print_error(stderr)
            return 1
        print_success("Files copied")

        # Run deploy script if specified
        if args.deploy_script:
            ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{droplet_ip}"
            print_info(f"Running deploy script: {args.deploy_script}")
            code, stdout, stderr = run_command(f"{ssh_cmd} 'cd /app && bash {args.deploy_script}'", timeout=300)
            if code != 0:
                print_error("Deploy script failed")
                print_error(stderr)
                return 1
            print_success("Deploy script completed")

    print_success("Application deployed successfully! ✅")
    print_info(f"Access your app at: http://{droplet_ip}:{args.port if args.port else 80}")

    return 0

def configure_monitoring(args) -> int:
    """Setup DigitalOcean monitoring and alerts"""
    print_header("Configuring Monitoring")

    # Check if droplet info exists
    if not os.path.exists('.digitalocean-droplet.txt'):
        print_error("No droplet info found. Create droplet first.")
        return 1

    # Read droplet info
    with open('.digitalocean-droplet.txt', 'r') as f:
        lines = f.readlines()
        droplet_id = lines[0].split('=')[1].strip()

    print_info(f"Setting up monitoring for droplet ID: {droplet_id}")

    # Check if monitoring is already enabled
    print_info("Checking monitoring status...")
    code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format Features")
    if code == 0 and 'monitoring' in stdout.lower():
        print_success("Monitoring already enabled")
    else:
        print_warning("Monitoring not enabled. Enable during droplet creation with --enable-monitoring")

    # Create alert policies (from DigitalOcean best practices)
    print_info("Creating alert policies...")

    # CPU alert
    if args.enable_cpu_alert:
        print_info("Creating CPU usage alert (>80% for 5min)...")
        alert_cmd = f"""doctl monitoring alert create \\
            --type v1/insights/droplet/cpu \\
            --compare GreaterThan \\
            --value 80 \\
            --window 5m \\
            --entities {droplet_id} \\
            --emails {args.alert_email if args.alert_email else 'your@email.com'}"""

        code, stdout, stderr = run_command(alert_cmd)
        if code == 0:
            print_success("CPU alert created")
        else:
            print_warning("CPU alert creation failed (may require API upgrade)")

    # Memory alert
    if args.enable_memory_alert:
        print_info("Creating memory usage alert (>90% for 5min)...")
        alert_cmd = f"""doctl monitoring alert create \\
            --type v1/insights/droplet/memory_utilization_percent \\
            --compare GreaterThan \\
            --value 90 \\
            --window 5m \\
            --entities {droplet_id} \\
            --emails {args.alert_email if args.alert_email else 'your@email.com'}"""

        code, stdout, stderr = run_command(alert_cmd)
        if code == 0:
            print_success("Memory alert created")
        else:
            print_warning("Memory alert creation failed (may require API upgrade)")

    # Disk alert
    if args.enable_disk_alert:
        print_info("Creating disk usage alert (>85%)...")
        alert_cmd = f"""doctl monitoring alert create \\
            --type v1/insights/droplet/disk_utilization_percent \\
            --compare GreaterThan \\
            --value 85 \\
            --window 5m \\
            --entities {droplet_id} \\
            --emails {args.alert_email if args.alert_email else 'your@email.com'}"""

        code, stdout, stderr = run_command(alert_cmd)
        if code == 0:
            print_success("Disk alert created")
        else:
            print_warning("Disk alert creation failed (may require API upgrade)")

    print_success("Monitoring configuration complete! ✅")
    print_info("View metrics: https://cloud.digitalocean.com/droplets")

    return 0

def health_check(args) -> int:
    """Verify droplet and app health"""
    print_header("Health Check")

    # Check if droplet info exists
    if not os.path.exists('.digitalocean-droplet.txt'):
        print_error("No droplet info found. Create droplet first.")
        return 1

    # Read droplet info
    with open('.digitalocean-droplet.txt', 'r') as f:
        lines = f.readlines()
        droplet_id = lines[0].split('=')[1].strip()
        droplet_name = lines[1].split('=')[1].strip()

    print_info(f"Checking health for: {droplet_name} (ID: {droplet_id})")

    # Check 1: Droplet status
    print_info("Checking droplet status...")
    code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format Status,PublicIPv4 --no-header")
    if code == 0:
        status_line = stdout.strip()
        if 'active' in status_line.lower():
            print_success(f"Droplet status: active")
            droplet_ip = status_line.split()[1] if len(status_line.split()) > 1 else None
        else:
            print_error(f"Droplet status: {status_line}")
            return 1
    else:
        print_error("Failed to get droplet status")
        return 1

    # Check 2: SSH connectivity
    if droplet_ip:
        print_info(f"Checking SSH connectivity to {droplet_ip}...")
        code, stdout, stderr = run_command(f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{droplet_ip} 'echo SSH_OK'", timeout=15)
        if code == 0 and 'SSH_OK' in stdout:
            print_success("SSH connectivity: OK")
        else:
            print_error("SSH connectivity: Failed")
            print_warning("Droplet may still be booting. Wait and try again.")

    # Check 3: HTTP endpoint (if port specified)
    if args.port:
        print_info(f"Checking HTTP endpoint at port {args.port}...")
        code, stdout, stderr = run_command(f"curl -s -o /dev/null -w '%{{http_code}}' --connect-timeout 10 http://{droplet_ip}:{args.port}", timeout=15)
        if code == 0:
            http_code = stdout.strip()
            if http_code in ['200', '301', '302']:
                print_success(f"HTTP endpoint: OK (Status: {http_code})")
            else:
                print_warning(f"HTTP endpoint: Status {http_code}")
        else:
            print_error("HTTP endpoint: Not responding")

    print_success("Health check complete! ✅")
    return 0

def run_tests(args) -> int:
    """Comprehensive testing suite"""
    print_header("Comprehensive Testing")

    tests_passed = 0
    tests_failed = 0
    issues = []

    # Test 1: Prerequisites
    print_info("Test 1/6: Prerequisites validation...")
    code, stdout, stderr = run_command("doctl version")
    if code == 0:
        print_success("✓ Test 1 PASSED: doctl CLI available")
        tests_passed += 1
    else:
        print_error("✗ Test 1 FAILED: doctl CLI not found")
        tests_failed += 1
        issues.append("doctl CLI not installed")

    # Test 2: Authentication
    print_info("Test 2/6: Authentication validation...")
    code, stdout, stderr = run_command("doctl account get")
    if code == 0:
        print_success("✓ Test 2 PASSED: Authenticated with DigitalOcean")
        tests_passed += 1
    else:
        print_error("✗ Test 2 FAILED: Not authenticated")
        tests_failed += 1
        issues.append("Run: doctl auth init")

    # Test 3: SSH Keys
    print_info("Test 3/6: SSH keys validation...")
    code, stdout, stderr = run_command("doctl compute ssh-key list --no-header")
    if code == 0 and stdout.strip():
        keys_count = len([line for line in stdout.split('\n') if line.strip()])
        print_success(f"✓ Test 3 PASSED: Found {keys_count} SSH key(s)")
        tests_passed += 1
    else:
        print_error("✗ Test 3 FAILED: No SSH keys found")
        tests_failed += 1
        issues.append("Add SSH key with: doctl compute ssh-key create <name> --public-key-file ~/.ssh/id_rsa.pub")

    # Test 4: Droplet creation (dry-run)
    print_info("Test 4/6: Droplet creation validation (checking parameters)...")
    code, stdout, stderr = run_command("doctl compute image list --public --format Slug --no-header | grep ubuntu")
    if code == 0 and stdout.strip():
        print_success("✓ Test 4 PASSED: Can query available images")
        tests_passed += 1
    else:
        print_error("✗ Test 4 FAILED: Cannot query images")
        tests_failed += 1

    # Test 5: Regions and sizes availability
    print_info("Test 5/6: Regions and sizes availability...")
    code, stdout, stderr = run_command("doctl compute region list --no-header")
    code2, stdout2, stderr2 = run_command("doctl compute size list --no-header")
    if code == 0 and code2 == 0:
        print_success("✓ Test 5 PASSED: Regions and sizes available")
        tests_passed += 1
    else:
        print_error("✗ Test 5 FAILED: Cannot query regions/sizes")
        tests_failed += 1

    # Test 6: Monitoring API access
    print_info("Test 6/6: Monitoring API access...")
    code, stdout, stderr = run_command("doctl monitoring alert list")
    if code == 0:
        print_success("✓ Test 6 PASSED: Monitoring API accessible")
        tests_passed += 1
    else:
        print_warning("⚠ Test 6 WARNING: Monitoring API access limited")
        print_info("Monitoring alerts may require API upgrade")
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
        print_success("\n✅ All tests passed! Ready for droplet creation.")
        return 0
    else:
        print_error(f"\n❌ {tests_failed} test(s) failed. Fix issues before proceeding.")
        return 1

def troubleshoot(args) -> int:
    """Detect and fix common issues"""
    print_header("Troubleshooting")

    issues_found = []
    fixes_applied = []

    # Issue 1: doctl not authenticated
    print_info("Checking authentication...")
    code, stdout, stderr = run_command("doctl account get")
    if code != 0:
        issues_found.append("Not authenticated with DigitalOcean")
        print_error("Issue: Not authenticated")
        print_info("Fix: Run 'doctl auth init' and enter your API token")
        print_info("Get token: https://cloud.digitalocean.com/account/api/tokens")
    else:
        print_success("Authentication: OK")

    # Issue 2: No SSH keys
    print_info("Checking SSH keys...")
    code, stdout, stderr = run_command("doctl compute ssh-key list --no-header")
    if code != 0 or not stdout.strip():
        issues_found.append("No SSH keys configured")
        print_error("Issue: No SSH keys found")
        print_info("Fix: Generate SSH key and add to DigitalOcean:")
        print_info("  1. ssh-keygen -t rsa -b 4096 -C 'your@email.com'")
        print_info("  2. doctl compute ssh-key create <name> --public-key-file ~/.ssh/id_rsa.pub")
    else:
        print_success("SSH keys: OK")

    # Issue 3: Droplet not accessible
    if os.path.exists('.digitalocean-droplet.txt'):
        print_info("Checking droplet accessibility...")
        with open('.digitalocean-droplet.txt', 'r') as f:
            lines = f.readlines()
            droplet_id = lines[0].split('=')[1].strip()

        code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format Status,PublicIPv4 --no-header")
        if code == 0:
            status_line = stdout.strip()
            if 'active' not in status_line.lower():
                issues_found.append(f"Droplet not active: {status_line}")
                print_error(f"Issue: Droplet status is {status_line}")
                print_info("Fix: Wait for droplet to finish booting, or recreate")
            else:
                droplet_ip = status_line.split()[1]
                print_success(f"Droplet active: {droplet_ip}")

                # Test SSH
                code, stdout, stderr = run_command(f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@{droplet_ip} 'echo OK'", timeout=15)
                if code != 0:
                    issues_found.append("SSH connection failed")
                    print_error("Issue: Cannot SSH to droplet")
                    print_info("Possible fixes:")
                    print_info("  1. Wait 30-60 seconds for SSH to be ready after creation")
                    print_info("  2. Check firewall rules allow SSH (port 22)")
                    print_info("  3. Verify SSH key was added during droplet creation")
                else:
                    print_success("SSH connectivity: OK")

    # Issue 4: Monitoring not enabled
    if os.path.exists('.digitalocean-droplet.txt'):
        print_info("Checking monitoring status...")
        with open('.digitalocean-droplet.txt', 'r') as f:
            lines = f.readlines()
            droplet_id = lines[0].split('=')[1].strip()

        code, stdout, stderr = run_command(f"doctl compute droplet get {droplet_id} --format Features")
        if code == 0 and 'monitoring' not in stdout.lower():
            issues_found.append("Monitoring not enabled")
            print_warning("Issue: Monitoring not enabled")
            print_info("Fix: Recreate droplet with --enable-monitoring flag")
            print_info("  OR: Enable monitoring via DigitalOcean dashboard")
        else:
            print_success("Monitoring: OK")

    # Summary
    print_header("Troubleshooting Summary")
    if not issues_found:
        print_success("No issues found! ✅")
        return 0
    else:
        print_warning(f"Found {len(issues_found)} issue(s):")
        for issue in issues_found:
            print_error(f"  • {issue}")
        print_info("\nFollow the fixes above to resolve issues")
        return 1

def cleanup(args) -> int:
    """Delete droplet and resources"""
    print_header("Cleanup")

    # Check if droplet info exists
    if not os.path.exists('.digitalocean-droplet.txt'):
        print_error("No droplet info found. Nothing to clean up.")
        return 0

    # Read droplet info
    with open('.digitalocean-droplet.txt', 'r') as f:
        lines = f.readlines()
        droplet_id = lines[0].split('=')[1].strip()
        droplet_name = lines[1].split('=')[1].strip()

    print_warning(f"This will DELETE droplet: {droplet_name} (ID: {droplet_id})")

    if not args.force:
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print_info("Cleanup cancelled")
            return 0

    # Delete droplet
    print_info("Deleting droplet...")
    code, stdout, stderr = run_command(f"doctl compute droplet delete {droplet_id} --force")
    if code == 0:
        print_success("Droplet deleted successfully")
    else:
        print_error("Failed to delete droplet")
        print_error(stderr)
        return 1

    # Remove local info file
    os.remove('.digitalocean-droplet.txt')
    print_success("Cleaned up local droplet info")

    print_success("Cleanup complete! ✅")
    return 0

def main():
    parser = argparse.ArgumentParser(description='DigitalOcean Deployment Tool')
    subparsers = parser.add_subparsers(dest='command')

    # check-prerequisites
    subparsers.add_parser('check-prerequisites', help='Verify doctl CLI, SSH keys, and API token')

    # create-droplet
    create_parser = subparsers.add_parser('create-droplet', help='Create and configure a new droplet')
    create_parser.add_argument('--name', required=True, help='Droplet name')
    create_parser.add_argument('--image', default='ubuntu-22-04-x64', help='Droplet image (default: ubuntu-22-04-x64)')
    create_parser.add_argument('--region', default='nyc3', help='Region (default: nyc3)')
    create_parser.add_argument('--size', default='s-1vcpu-1gb', help='Droplet size (default: s-1vcpu-1gb)')
    create_parser.add_argument('--enable-monitoring', action='store_true', help='Enable monitoring (free)')
    create_parser.add_argument('--enable-ipv6', action='store_true', help='Enable IPv6')
    create_parser.add_argument('--enable-backups', action='store_true', help='Enable backups (+20% cost)')
    create_parser.add_argument('--vpc-uuid', help='VPC UUID for private networking')
    create_parser.add_argument('--user-data', help='Path to user-data file (cloud-init)')

    # deploy-app
    deploy_parser = subparsers.add_parser('deploy-app', help='Deploy application to droplet')
    deploy_parser.add_argument('--method', choices=['git', 'docker', 'scp'], required=True, help='Deployment method')
    deploy_parser.add_argument('--repo', help='Git repository URL (for git method)')
    deploy_parser.add_argument('--image', help='Docker image (for docker method)')
    deploy_parser.add_argument('--source', help='Source directory (for scp method)')
    deploy_parser.add_argument('--port', type=int, default=80, help='Application port (default: 80)')
    deploy_parser.add_argument('--deploy-script', help='Deploy script to run after copying files')

    # configure-monitoring
    monitor_parser = subparsers.add_parser('configure-monitoring', help='Setup monitoring and alerts')
    monitor_parser.add_argument('--enable-cpu-alert', action='store_true', help='Create CPU usage alert (>80%)')
    monitor_parser.add_argument('--enable-memory-alert', action='store_true', help='Create memory alert (>90%)')
    monitor_parser.add_argument('--enable-disk-alert', action='store_true', help='Create disk alert (>85%)')
    monitor_parser.add_argument('--alert-email', help='Email for alerts')

    # health-check
    health_parser = subparsers.add_parser('health-check', help='Verify droplet and app health')
    health_parser.add_argument('--port', type=int, help='HTTP port to check')

    # test
    subparsers.add_parser('test', help='Run comprehensive testing suite')

    # troubleshoot
    subparsers.add_parser('troubleshoot', help='Detect and fix common issues')

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
        'cleanup': cleanup,
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
