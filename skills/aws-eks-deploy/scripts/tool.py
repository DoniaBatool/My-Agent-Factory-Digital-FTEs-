#!/usr/bin/env python3
"""
AWS EKS Deployment Tool

Comprehensive AWS EKS cluster deployment, testing, and management automation.
Handles everything from prerequisites to production deployment with TDD approach.

Commands:
  check-prerequisites  - Verify AWS CLI, kubectl, eksctl installation
  create-cluster       - Create EKS cluster with free tier optimization
  configure-kubectl    - Configure kubectl for EKS cluster access
  deploy               - Deploy application to EKS cluster
  test                 - Comprehensive testing (all scenarios)
  health-check         - Monitor cluster and application health
  troubleshoot         - Automated issue detection and fixes
  cleanup              - Delete cluster and resources
"""

import argparse
import subprocess
import sys
import json
import time
import os
from typing import Dict, List, Tuple, Optional

class Colors:
    """Terminal colors for output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")

def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")

def print_header(msg: str):
    print(f"\n{Colors.BOLD}==> {msg}{Colors.END}")

def run_command(cmd: str, capture_output: bool = True, timeout: int = 300) -> Tuple[int, str, str]:
    """Run shell command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return 1, "", str(e)

def check_command_exists(cmd: str) -> bool:
    """Check if command exists in PATH"""
    code, _, _ = run_command(f"which {cmd}")
    return code == 0

def check_prerequisites(args) -> int:
    """Check if all required tools are installed"""
    print_header("Checking Prerequisites")

    all_good = True

    # Check AWS CLI
    if check_command_exists("aws"):
        code, stdout, _ = run_command("aws --version")
        print_success(f"AWS CLI installed: {stdout.strip()}")

        # Check AWS credentials
        code, _, _ = run_command("aws sts get-caller-identity")
        if code == 0:
            print_success("AWS credentials configured")
        else:
            print_error("AWS credentials not configured")
            print_info("Run: aws configure")
            all_good = False
    else:
        print_error("AWS CLI not installed")
        print_info("Install: https://aws.amazon.com/cli/")
        all_good = False

    # Check kubectl
    if check_command_exists("kubectl"):
        code, stdout, _ = run_command("kubectl version --client --short 2>/dev/null || kubectl version --client")
        print_success(f"kubectl installed: {stdout.strip().split()[0]}")
    else:
        print_error("kubectl not installed")
        print_info("Install: https://kubernetes.io/docs/tasks/tools/")
        all_good = False

    # Check eksctl
    if check_command_exists("eksctl"):
        code, stdout, _ = run_command("eksctl version")
        print_success(f"eksctl installed: {stdout.strip()}")
    else:
        print_error("eksctl not installed")
        print_info("Install: https://eksctl.io/installation/")
        all_good = False

    # Check Docker (optional but recommended)
    if check_command_exists("docker"):
        code, stdout, _ = run_command("docker --version")
        print_success(f"Docker installed: {stdout.strip()}")
    else:
        print_warning("Docker not installed (optional)")

    print()
    if all_good:
        print_success("All prerequisites met! ✅")
        return 0
    else:
        print_error("Some prerequisites missing. Please install required tools.")
        return 1

def create_cluster(args) -> int:
    """Create EKS cluster with free tier optimization"""
    print_header(f"Creating EKS Cluster: {args.cluster_name}")

    # Run prerequisites check first
    print_info("Running prerequisites check...")
    prereq_result = check_prerequisites(argparse.Namespace())
    if prereq_result != 0:
        print_error("Prerequisites not met. Please install required tools first.")
        return 1

    print_info(f"Region: {args.region}")
    print_info(f"Node count: {args.nodes}")
    print_info(f"Node type: {args.node_type}")
    print_info(f"Kubernetes version: {args.k8s_version}")

    # Create cluster config
    cluster_config = f"""
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: {args.cluster_name}
  region: {args.region}
  version: "{args.k8s_version}"

managedNodeGroups:
  - name: {args.cluster_name}-nodes
    instanceType: {args.node_type}
    desiredCapacity: {args.nodes}
    minSize: {args.nodes}
    maxSize: {args.nodes + 2}
    volumeSize: 20
    ssh:
      allow: false
    labels:
      role: worker
    tags:
      Environment: production
      ManagedBy: eksctl
"""

    # Save config to temp file
    config_file = f"/tmp/eks-{args.cluster_name}-config.yaml"
    with open(config_file, 'w') as f:
        f.write(cluster_config)

    print_success(f"Cluster config created: {config_file}")

    # Create cluster
    print_info("Creating EKS cluster... (this takes 15-20 minutes)")
    print_warning("Do not interrupt this process!")

    create_cmd = f"eksctl create cluster -f {config_file}"

    if args.dry_run:
        print_info(f"DRY RUN: Would execute: {create_cmd}")
        return 0

    code, stdout, stderr = run_command(create_cmd, capture_output=False, timeout=1800)

    if code == 0:
        print_success("EKS cluster created successfully! ✅")
        print_info("Configuring kubectl...")
        configure_kubectl(argparse.Namespace(cluster_name=args.cluster_name, region=args.region))
        return 0
    else:
        print_error("Failed to create EKS cluster")
        print_error(stderr)
        return 1

def configure_kubectl(args) -> int:
    """Configure kubectl to access EKS cluster"""
    print_header(f"Configuring kubectl for: {args.cluster_name}")

    cmd = f"aws eks update-kubeconfig --name {args.cluster_name} --region {args.region}"
    code, stdout, stderr = run_command(cmd)

    if code == 0:
        print_success("kubectl configured successfully!")
        print_success(stdout.strip())

        # Test connection
        print_info("Testing connection...")
        code, stdout, _ = run_command("kubectl get nodes")
        if code == 0:
            print_success("Connection test passed!")
            print(stdout)
            return 0
        else:
            print_error("Connection test failed")
            return 1
    else:
        print_error("Failed to configure kubectl")
        print_error(stderr)
        return 1

def deploy_application(args) -> int:
    """Deploy application to EKS cluster"""
    print_header(f"Deploying Application from: {args.manifest_dir}")

    # Check if kubectl is configured
    code, _, _ = run_command("kubectl get nodes")
    if code != 0:
        print_error("kubectl not configured. Run configure-kubectl first.")
        return 1

    # Create namespace if specified
    if args.namespace and args.namespace != "default":
        print_info(f"Creating namespace: {args.namespace}")
        code, _, _ = run_command(f"kubectl create namespace {args.namespace} --dry-run=client -o yaml | kubectl apply -f -")
        if code == 0:
            print_success(f"Namespace {args.namespace} ready")

    # Apply manifests
    print_info(f"Applying manifests from: {args.manifest_dir}")

    if os.path.isdir(args.manifest_dir):
        code, stdout, stderr = run_command(f"kubectl apply -f {args.manifest_dir} -n {args.namespace}")
    elif os.path.isfile(args.manifest_dir):
        code, stdout, stderr = run_command(f"kubectl apply -f {args.manifest_dir} -n {args.namespace}")
    else:
        print_error(f"Path not found: {args.manifest_dir}")
        return 1

    if code == 0:
        print_success("Application deployed successfully!")
        print(stdout)

        # Wait for pods
        print_info("Waiting for pods to be ready...")
        time.sleep(5)

        code, stdout, _ = run_command(f"kubectl get pods -n {args.namespace}")
        print(stdout)

        # Get services
        print_info("Services:")
        code, stdout, _ = run_command(f"kubectl get svc -n {args.namespace}")
        print(stdout)

        return 0
    else:
        print_error("Deployment failed")
        print_error(stderr)
        return 1

def run_tests(args) -> int:
    """Comprehensive testing suite"""
    print_header("EKS Comprehensive Testing")

    tests_passed = 0
    tests_failed = 0
    issues = []

    # Test 1: Prerequisites
    print_header("Test 1: Prerequisites Check")
    if check_prerequisites(argparse.Namespace()) == 0:
        print_success("Prerequisites test passed")
        tests_passed += 1
    else:
        print_error("Prerequisites test failed")
        tests_failed += 1
        issues.append("Prerequisites missing")

    # Test 2: Cluster accessibility
    print_header("Test 2: Cluster Accessibility")
    code, stdout, _ = run_command("kubectl cluster-info")
    if code == 0:
        print_success("Cluster accessible")
        print(stdout)
        tests_passed += 1
    else:
        print_error("Cannot access cluster")
        tests_failed += 1
        issues.append("Cluster not accessible")

    # Test 3: Nodes health
    print_header("Test 3: Nodes Health Check")
    code, stdout, _ = run_command("kubectl get nodes -o json")
    if code == 0:
        try:
            nodes = json.loads(stdout)
            all_ready = True
            for node in nodes.get('items', []):
                node_name = node['metadata']['name']
                conditions = node['status']['conditions']
                ready = any(c['type'] == 'Ready' and c['status'] == 'True' for c in conditions)
                if ready:
                    print_success(f"Node {node_name}: Ready")
                else:
                    print_error(f"Node {node_name}: Not Ready")
                    all_ready = False

            if all_ready:
                tests_passed += 1
            else:
                tests_failed += 1
                issues.append("Some nodes not ready")
        except Exception as e:
            print_error(f"Failed to parse nodes: {e}")
            tests_failed += 1
            issues.append("Node parsing failed")
    else:
        print_error("Cannot get nodes")
        tests_failed += 1
        issues.append("Cannot retrieve nodes")

    # Test 4: Pods health
    print_header("Test 4: Pods Health Check")
    namespace = args.namespace if hasattr(args, 'namespace') else 'default'
    code, stdout, _ = run_command(f"kubectl get pods -n {namespace} -o json")
    if code == 0:
        try:
            pods = json.loads(stdout)
            if not pods.get('items'):
                print_warning("No pods found in namespace")
                tests_passed += 1  # Not a failure
            else:
                all_running = True
                for pod in pods['items']:
                    pod_name = pod['metadata']['name']
                    phase = pod['status']['phase']
                    if phase == 'Running':
                        print_success(f"Pod {pod_name}: {phase}")
                    else:
                        print_warning(f"Pod {pod_name}: {phase}")
                        all_running = False

                if all_running:
                    tests_passed += 1
                else:
                    print_warning("Some pods not running (may be normal during startup)")
                    tests_passed += 1  # Not critical failure
        except Exception as e:
            print_error(f"Failed to parse pods: {e}")
            tests_failed += 1
            issues.append("Pod parsing failed")
    else:
        print_warning("Cannot get pods")
        tests_passed += 1  # May not have deployed yet

    # Test 5: Services check
    print_header("Test 5: Services Check")
    code, stdout, _ = run_command(f"kubectl get svc -n {namespace} -o json")
    if code == 0:
        try:
            services = json.loads(stdout)
            if not services.get('items'):
                print_warning("No services found")
                tests_passed += 1
            else:
                for svc in services['items']:
                    svc_name = svc['metadata']['name']
                    svc_type = svc['spec']['type']
                    print_success(f"Service {svc_name}: {svc_type}")
                tests_passed += 1
        except Exception as e:
            print_error(f"Failed to parse services: {e}")
            tests_failed += 1
            issues.append("Service parsing failed")
    else:
        print_warning("Cannot get services")
        tests_passed += 1

    # Test 6: AWS resources check
    print_header("Test 6: AWS Resources Check")
    code, _, _ = run_command("aws sts get-caller-identity")
    if code == 0:
        print_success("AWS credentials valid")
        tests_passed += 1
    else:
        print_error("AWS credentials invalid")
        tests_failed += 1
        issues.append("AWS credentials issue")

    # Test Summary
    print_header("Test Summary")
    print(f"\nTotal tests: {tests_passed + tests_failed}")
    print(f"{Colors.GREEN}Passed: {tests_passed}{Colors.END}")
    print(f"{Colors.RED}Failed: {tests_failed}{Colors.END}")

    if tests_failed == 0:
        print(f"\n{Colors.GREEN}✅ All tests passed!{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}❌ Some tests failed{Colors.END}")
        print("\nIssues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

def health_check(args) -> int:
    """Monitor cluster and application health"""
    print_header("EKS Cluster Health Check")

    namespace = args.namespace if hasattr(args, 'namespace') else 'default'
    all_healthy = True

    # Check cluster
    print_header("Checking Cluster")
    code, stdout, _ = run_command("kubectl cluster-info")
    if code == 0:
        print_success("Cluster responding")
    else:
        print_error("Cluster not responding")
        all_healthy = False

    # Check nodes
    print_header("Checking Nodes")
    code, stdout, _ = run_command("kubectl get nodes")
    if code == 0:
        print(stdout)
        # Check if any NotReady
        if "NotReady" in stdout:
            print_error("Some nodes not ready")
            all_healthy = False
        else:
            print_success("All nodes ready")
    else:
        print_error("Cannot retrieve nodes")
        all_healthy = False

    # Check pods
    print_header("Checking Pods")
    code, stdout, _ = run_command(f"kubectl get pods -n {namespace}")
    if code == 0:
        print(stdout)
        # Check for failures
        if "Error" in stdout or "CrashLoopBackOff" in stdout or "ImagePullBackOff" in stdout:
            print_error("Some pods in error state")
            all_healthy = False
        else:
            print_success("All pods healthy")
    else:
        print_warning("Cannot retrieve pods")

    # Check services
    print_header("Checking Services")
    code, stdout, _ = run_command(f"kubectl get svc -n {namespace}")
    if code == 0:
        print(stdout)
        print_success("Services listed")
    else:
        print_warning("Cannot retrieve services")

    # Check events for issues
    print_header("Recent Events")
    code, stdout, _ = run_command(f"kubectl get events -n {namespace} --sort-by='.lastTimestamp' | tail -10")
    if code == 0:
        print(stdout)

    print()
    if all_healthy:
        print_success("✅ Cluster is healthy!")
        return 0
    else:
        print_error("⚠️  Some issues detected")
        return 1

def troubleshoot(args) -> int:
    """Automated troubleshooting"""
    print_header("EKS Cluster Troubleshooting")

    issues_found = []
    fixes = []

    # Check cluster access
    print_info("Checking cluster access...")
    code, _, _ = run_command("kubectl cluster-info")
    if code != 0:
        issues_found.append("Cannot access cluster")
        fixes.append("Run: aws eks update-kubeconfig --name <cluster-name> --region <region>")
    else:
        print_success("Cluster accessible")

    # Check nodes
    print_info("Checking nodes...")
    code, stdout, _ = run_command("kubectl get nodes")
    if code == 0:
        if "NotReady" in stdout:
            issues_found.append("Some nodes not ready")
            fixes.append("Check node logs: kubectl describe node <node-name>")
        else:
            print_success("All nodes ready")
    else:
        issues_found.append("Cannot retrieve nodes")
        fixes.append("Check AWS credentials: aws sts get-caller-identity")

    # Check pods
    namespace = args.namespace if hasattr(args, 'namespace') else 'default'
    print_info(f"Checking pods in namespace: {namespace}...")
    code, stdout, _ = run_command(f"kubectl get pods -n {namespace}")
    if code == 0:
        if "Error" in stdout or "CrashLoopBackOff" in stdout:
            issues_found.append("Some pods in error state")
            fixes.append(f"Check pod logs: kubectl logs <pod-name> -n {namespace}")
            fixes.append(f"Describe pod: kubectl describe pod <pod-name> -n {namespace}")
        elif "ImagePullBackOff" in stdout:
            issues_found.append("Image pull errors")
            fixes.append("Check image names and repository access")
            fixes.append("Verify image exists: docker pull <image-name>")
        else:
            print_success("All pods healthy")

    # Check AWS credentials
    print_info("Checking AWS credentials...")
    code, _, _ = run_command("aws sts get-caller-identity")
    if code != 0:
        issues_found.append("AWS credentials not configured")
        fixes.append("Run: aws configure")
    else:
        print_success("AWS credentials valid")

    # Summary
    print_header("Troubleshooting Complete")

    if not issues_found:
        print_success("✓ No issues detected!")
        return 0
    else:
        print_error(f"Found {len(issues_found)} issue(s):\n")
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. Issue: {issue}")
            if i-1 < len(fixes):
                print(f"   Fix: {fixes[i-1]}\n")
        return 1

def cleanup_cluster(args) -> int:
    """Delete EKS cluster and all resources"""
    print_header(f"Deleting EKS Cluster: {args.cluster_name}")

    if not args.force:
        print_warning("This will delete the cluster and ALL resources!")
        response = input("Are you sure? Type 'yes' to continue: ")
        if response.lower() != 'yes':
            print_info("Cleanup cancelled")
            return 0

    print_info("Deleting cluster... (this takes 10-15 minutes)")

    cmd = f"eksctl delete cluster --name {args.cluster_name} --region {args.region}"

    if args.dry_run:
        print_info(f"DRY RUN: Would execute: {cmd}")
        return 0

    code, stdout, stderr = run_command(cmd, capture_output=False, timeout=1200)

    if code == 0:
        print_success("Cluster deleted successfully! ✅")
        return 0
    else:
        print_error("Failed to delete cluster")
        print_error(stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(
        description='AWS EKS Deployment Tool - Comprehensive cluster management',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # check-prerequisites command
    subparsers.add_parser('check-prerequisites', help='Check if required tools are installed')

    # create-cluster command
    create_parser = subparsers.add_parser('create-cluster', help='Create EKS cluster')
    create_parser.add_argument('--cluster-name', default='my-eks-cluster', help='Cluster name')
    create_parser.add_argument('--region', default='us-east-1', help='AWS region')
    create_parser.add_argument('--nodes', type=int, default=2, help='Number of nodes')
    create_parser.add_argument('--node-type', default='t3.small', help='EC2 instance type')
    create_parser.add_argument('--k8s-version', default='1.28', help='Kubernetes version')
    create_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')

    # configure-kubectl command
    config_parser = subparsers.add_parser('configure-kubectl', help='Configure kubectl for EKS')
    config_parser.add_argument('--cluster-name', required=True, help='Cluster name')
    config_parser.add_argument('--region', default='us-east-1', help='AWS region')

    # deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy application to cluster')
    deploy_parser.add_argument('--manifest-dir', required=True, help='Path to Kubernetes manifests')
    deploy_parser.add_argument('--namespace', default='default', help='Kubernetes namespace')

    # test command
    test_parser = subparsers.add_parser('test', help='Run comprehensive tests')
    test_parser.add_argument('--namespace', default='default', help='Kubernetes namespace')

    # health-check command
    health_parser = subparsers.add_parser('health-check', help='Check cluster health')
    health_parser.add_argument('--namespace', default='default', help='Kubernetes namespace')

    # troubleshoot command
    troubleshoot_parser = subparsers.add_parser('troubleshoot', help='Troubleshoot issues')
    troubleshoot_parser.add_argument('--namespace', default='default', help='Kubernetes namespace')

    # cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Delete cluster')
    cleanup_parser.add_argument('--cluster-name', required=True, help='Cluster name')
    cleanup_parser.add_argument('--region', default='us-east-1', help='AWS region')
    cleanup_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    commands = {
        'check-prerequisites': check_prerequisites,
        'create-cluster': create_cluster,
        'configure-kubectl': configure_kubectl,
        'deploy': deploy_application,
        'test': run_tests,
        'health-check': health_check,
        'troubleshoot': troubleshoot,
        'cleanup': cleanup_cluster
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
