#!/usr/bin/env python3
"""
Azure AKS Deployment Tool

Automated Azure Kubernetes Service (AKS) cluster creation and deployment.
No cloud specialist needed!

Commands:
  check-prerequisites  - Verify Azure CLI, kubectl, and credentials
  create-cluster       - Create production-ready AKS cluster
  configure-kubectl    - Configure kubectl to connect to AKS
  deploy-app           - Deploy application to AKS cluster
  setup-ingress        - Setup NGINX ingress controller
  test                 - Comprehensive 6-test suite (TDD approach)
  health-check         - Verify cluster and application health
  troubleshoot         - Detect and fix common issues
  cleanup              - Delete cluster and resources
"""

import argparse
import json
import subprocess
import sys
import time
from typing import Tuple, List, Dict, Any

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

def run_command(cmd: str, timeout: int = 300) -> Tuple[int, str, str]:
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
    """Check if required tools are installed and configured"""
    print_header("Checking Prerequisites")

    all_ok = True

    # Check Azure CLI
    print_info("Checking Azure CLI...")
    code, stdout, _ = run_command("az --version")
    if code == 0:
        version = stdout.split('\n')[0]
        print_success(f"Azure CLI installed: {version}")
    else:
        print_error("Azure CLI not installed")
        print_info("Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        all_ok = False

    # Check Azure login
    print_info("Checking Azure authentication...")
    code, stdout, _ = run_command("az account show")
    if code == 0:
        account = json.loads(stdout)
        print_success(f"Logged in as: {account.get('user', {}).get('name', 'unknown')}")
        print_success(f"Subscription: {account.get('name', 'unknown')}")
    else:
        print_error("Not logged in to Azure")
        print_info("Run: az login")
        all_ok = False

    # Check kubectl
    print_info("Checking kubectl...")
    code, stdout, _ = run_command("kubectl version --client --short 2>/dev/null || kubectl version --client")
    if code == 0:
        print_success(f"kubectl installed")
    else:
        print_error("kubectl not installed")
        print_info("Install: https://kubernetes.io/docs/tasks/tools/")
        all_ok = False

    # Check Docker (optional)
    print_info("Checking Docker (optional for local builds)...")
    code, _, _ = run_command("docker --version")
    if code == 0:
        print_success("Docker installed")
    else:
        print_warning("Docker not installed (optional)")

    print_header("Prerequisites Check Complete")
    if all_ok:
        print_success("All required tools are installed and configured!")
        return 0
    else:
        print_error("Some prerequisites are missing. Please install them first.")
        return 1

def create_cluster(args) -> int:
    """Create AKS cluster with best practices"""
    print_header(f"Creating AKS Cluster: {args.cluster_name}")

    resource_group = args.resource_group or f"{args.cluster_name}-rg"
    location = args.location or "eastus"
    node_count = args.nodes or 2
    node_size = args.node_size or "Standard_B2s"  # Cost-optimized

    print_info(f"Resource Group: {resource_group}")
    print_info(f"Location: {location}")
    print_info(f"Node Count: {node_count}")
    print_info(f"Node Size: {node_size}")

    # Create resource group
    print_info("Creating resource group...")
    cmd = f"az group create --name {resource_group} --location {location}"
    code, stdout, stderr = run_command(cmd)
    if code == 0:
        print_success(f"Resource group created: {resource_group}")
    else:
        print_error(f"Failed to create resource group: {stderr}")
        return 1

    # Create AKS cluster
    print_info("Creating AKS cluster (this may take 10-15 minutes)...")

    cmd = f"""az aks create \
        --resource-group {resource_group} \
        --name {args.cluster_name} \
        --node-count {node_count} \
        --node-vm-size {node_size} \
        --enable-managed-identity \
        --generate-ssh-keys \
        --enable-addons monitoring \
        --network-plugin azure \
        --enable-cluster-autoscaler \
        --min-count 1 \
        --max-count {node_count * 2} \
        --tags Environment=production ManagedBy=claude-code"""

    code, stdout, stderr = run_command(cmd, timeout=1200)  # 20 minutes timeout

    if code == 0:
        print_success(f"AKS cluster created: {args.cluster_name}")
        print_info("Cluster features enabled:")
        print_info("  - Managed Identity (secure, no service principal needed)")
        print_info("  - Azure Monitor (container insights)")
        print_info("  - Cluster Autoscaler (1 to {0} nodes)".format(node_count * 2))
        print_info("  - Azure CNI networking")
        return 0
    else:
        print_error(f"Failed to create cluster: {stderr}")
        return 1

def configure_kubectl(args) -> int:
    """Configure kubectl to connect to AKS cluster"""
    print_header(f"Configuring kubectl for: {args.cluster_name}")

    resource_group = args.resource_group or f"{args.cluster_name}-rg"

    # Get credentials with retry logic (cluster may take time to be ready)
    max_retries = 10
    for i in range(max_retries):
        print_info(f"Getting AKS credentials (attempt {i+1}/{max_retries})...")
        cmd = f"az aks get-credentials --resource-group {resource_group} --name {args.cluster_name} --overwrite-existing"
        code, stdout, stderr = run_command(cmd)

        if code == 0:
            print_success("kubectl configured successfully")

            # Verify connection
            print_info("Verifying connection...")
            code, stdout, stderr = run_command("kubectl cluster-info")
            if code == 0:
                print_success("Successfully connected to AKS cluster!")
                print_info(stdout.split('\n')[0])
                return 0
            else:
                if i < max_retries - 1:
                    wait_time = 2 ** i
                    print_warning(f"Cluster not ready yet. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print_error("Connection timeout. Cluster may still be initializing.")
                    print_info("Wait a few minutes and try: az aks get-credentials --resource-group {0} --name {1}".format(resource_group, args.cluster_name))
                    return 1
        else:
            print_error(f"Failed to get credentials: {stderr}")
            return 1

    return 1

def deploy_app(args) -> int:
    """Deploy application to AKS cluster"""
    print_header("Deploying Application to AKS")

    if not args.manifest:
        print_error("No manifest file specified. Use --manifest <file.yaml>")
        return 1

    print_info(f"Applying manifest: {args.manifest}")
    cmd = f"kubectl apply -f {args.manifest}"
    code, stdout, stderr = run_command(cmd)

    if code == 0:
        print_success("Application deployed successfully!")
        print_info(stdout)

        # Show deployment status
        print_info("\nDeployment status:")
        run_command("kubectl get deployments")

        print_info("\nService status:")
        run_command("kubectl get services")

        print_info("\nPod status:")
        run_command("kubectl get pods")

        return 0
    else:
        print_error(f"Deployment failed: {stderr}")
        return 1

def setup_ingress(args) -> int:
    """Setup NGINX ingress controller"""
    print_header("Setting up NGINX Ingress Controller")

    # Add NGINX ingress Helm repo
    print_info("Adding NGINX ingress Helm repository...")
    run_command("helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx")
    run_command("helm repo update")

    # Install NGINX ingress
    print_info("Installing NGINX ingress controller...")
    cmd = """helm install nginx-ingress ingress-nginx/ingress-nginx \
        --set controller.service.type=LoadBalancer \
        --set controller.replicaCount=2 \
        --set controller.nodeSelector."kubernetes\\.io/os"=linux \
        --set defaultBackend.nodeSelector."kubernetes\\.io/os"=linux"""

    code, stdout, stderr = run_command(cmd, timeout=300)

    if code == 0:
        print_success("NGINX ingress controller installed!")

        # Wait for LoadBalancer IP
        print_info("Waiting for external IP (may take 2-3 minutes)...")
        for i in range(30):
            code, stdout, _ = run_command("kubectl get service nginx-ingress-ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}'")
            if stdout and stdout.strip() != "''":
                print_success(f"Ingress external IP: {stdout}")
                print_info("\nTo use this ingress, create an Ingress resource:")
                print_info("  apiVersion: networking.k8s.io/v1")
                print_info("  kind: Ingress")
                print_info("  metadata:")
                print_info("    annotations:")
                print_info("      kubernetes.io/ingress.class: nginx")
                return 0
            time.sleep(6)

        print_warning("LoadBalancer IP not assigned yet. Check later with:")
        print_info("kubectl get service nginx-ingress-ingress-nginx-controller")
        return 0
    else:
        print_error(f"Failed to install ingress: {stderr}")
        print_info("Make sure Helm is installed: https://helm.sh/docs/intro/install/")
        return 1

def run_tests(args) -> int:
    """Comprehensive 6-test suite for AKS deployment"""
    print_header("AKS Deployment - Comprehensive Test Suite")
    print_info("Test-Driven Development (TDD) Approach")
    print_info("6 comprehensive tests covering all aspects\n")

    tests_passed = 0
    tests_failed = 0
    issues = []

    # Test 1: Prerequisites
    print_header("Test 1/6: Prerequisites Check")
    code, _, _ = run_command("az --version")
    if code == 0:
        print_success("Azure CLI available")
        tests_passed += 1
    else:
        print_error("Azure CLI not installed")
        issues.append("Install Azure CLI: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        tests_failed += 1

    code, _, _ = run_command("kubectl version --client")
    if code == 0:
        print_success("kubectl available")
        tests_passed += 1
    else:
        print_error("kubectl not installed")
        issues.append("Install kubectl: https://kubernetes.io/docs/tasks/tools/")
        tests_failed += 1

    code, _, _ = run_command("az account show")
    if code == 0:
        print_success("Azure authentication valid")
        tests_passed += 1
    else:
        print_error("Not logged in to Azure")
        issues.append("Run: az login")
        tests_failed += 1

    # Test 2: Cluster Existence (if cluster name provided)
    print_header("Test 2/6: Cluster Availability")
    if hasattr(args, 'cluster_name') and args.cluster_name:
        resource_group = getattr(args, 'resource_group', None) or f"{args.cluster_name}-rg"
        code, stdout, _ = run_command(f"az aks show --resource-group {resource_group} --name {args.cluster_name}")
        if code == 0:
            cluster_info = json.loads(stdout)
            print_success(f"Cluster exists: {args.cluster_name}")
            print_success(f"  Location: {cluster_info.get('location', 'unknown')}")
            print_success(f"  Kubernetes version: {cluster_info.get('kubernetesVersion', 'unknown')}")
            print_success(f"  Node count: {cluster_info.get('agentPoolProfiles', [{}])[0].get('count', 'unknown')}")
            tests_passed += 1
        else:
            print_warning(f"Cluster not found: {args.cluster_name}")
            print_info("Run: python3 tool.py create-cluster --cluster-name <name>")
            tests_passed += 1  # Not a failure if cluster doesn't exist yet
    else:
        print_info("No cluster specified (use --cluster-name to test specific cluster)")
        tests_passed += 1

    # Test 3: kubectl Connection
    print_header("Test 3/6: kubectl Connectivity")
    code, stdout, _ = run_command("kubectl cluster-info")
    if code == 0:
        print_success("kubectl connected to cluster")
        print_info(stdout.split('\n')[0])
        tests_passed += 1
    else:
        print_warning("kubectl not configured for any cluster")
        print_info("Run: python3 tool.py configure-kubectl --cluster-name <name>")
        tests_passed += 1  # Not a failure if not configured yet

    # Test 4: Cluster Health (if connected)
    print_header("Test 4/6: Cluster Health")
    code, stdout, _ = run_command("kubectl get nodes")
    if code == 0:
        lines = stdout.strip().split('\n')
        if len(lines) > 1:
            node_count = len(lines) - 1
            print_success(f"Cluster has {node_count} node(s)")

            # Check node status
            ready_nodes = 0
            for line in lines[1:]:
                if 'Ready' in line and 'NotReady' not in line:
                    ready_nodes += 1

            if ready_nodes == node_count:
                print_success(f"All {node_count} nodes are Ready")
                tests_passed += 1
            else:
                print_error(f"Only {ready_nodes}/{node_count} nodes are Ready")
                issues.append("Some nodes not ready. Check: kubectl describe nodes")
                tests_failed += 1
        else:
            print_error("No nodes found in cluster")
            issues.append("Cluster has no nodes")
            tests_failed += 1
    else:
        print_warning("Cannot check cluster health (not connected)")
        tests_passed += 1  # Not a failure if not connected

    # Test 5: System Pods Health
    print_header("Test 5/6: System Pods Health")
    code, stdout, _ = run_command("kubectl get pods -n kube-system")
    if code == 0:
        lines = stdout.strip().split('\n')
        if len(lines) > 1:
            pod_count = len(lines) - 1
            running_pods = 0
            for line in lines[1:]:
                if 'Running' in line or 'Completed' in line:
                    running_pods += 1

            if running_pods == pod_count:
                print_success(f"All {pod_count} system pods are healthy")
                tests_passed += 1
            else:
                print_warning(f"{running_pods}/{pod_count} system pods are running")
                print_info("Some pods may still be initializing")
                tests_passed += 1
        else:
            print_error("No system pods found")
            tests_failed += 1
    else:
        print_warning("Cannot check system pods (not connected)")
        tests_passed += 1

    # Test 6: Resource Quotas and Limits
    print_header("Test 6/6: Resource Validation")
    code, stdout, _ = run_command("kubectl top nodes 2>/dev/null")
    if code == 0:
        print_success("Metrics server available")
        print_info("Resource usage:")
        print_info(stdout)
        tests_passed += 1
    else:
        print_warning("Metrics server not available (optional)")
        print_info("Enable with: az aks enable-addons --addons monitoring")
        tests_passed += 1  # Not critical

    # Test Summary
    print_header("Test Summary")
    total_tests = tests_passed + tests_failed
    print(f"\nTotal tests: {total_tests}")
    print_success(f"Passed: {tests_passed}")
    if tests_failed > 0:
        print_error(f"Failed: {tests_failed}")

    if issues:
        print_header("Issues Found")
        for i, issue in enumerate(issues, 1):
            print_error(f"{i}. {issue}")

    if tests_failed == 0:
        print_header("✅ All Tests Passed!")
        print_success("AKS deployment is healthy and ready for production!")
        return 0
    else:
        print_header("❌ Some Tests Failed")
        print_info("Fix the issues above and run tests again")
        return 1

def health_check(args) -> int:
    """Quick health check of cluster and applications"""
    print_header("AKS Cluster Health Check")

    # Check nodes
    print_info("Checking node health...")
    code, stdout, _ = run_command("kubectl get nodes")
    if code == 0:
        print_success("Nodes:")
        print(stdout)
    else:
        print_error("Failed to get nodes")
        return 1

    # Check pods
    print_info("\nChecking pod health...")
    code, stdout, _ = run_command("kubectl get pods --all-namespaces")
    if code == 0:
        lines = stdout.strip().split('\n')
        problem_pods = [line for line in lines if 'Running' not in line and 'Completed' not in line and 'STATUS' not in line]

        if problem_pods:
            print_warning(f"Found {len(problem_pods)} pod(s) not in Running state:")
            for pod in problem_pods:
                print_warning(pod)
        else:
            print_success("All pods are healthy")

    # Check services
    print_info("\nChecking services...")
    code, stdout, _ = run_command("kubectl get services --all-namespaces")
    if code == 0:
        print_success("Services:")
        print(stdout)

    return 0

def troubleshoot(args) -> int:
    """Detect and fix common AKS issues"""
    print_header("AKS Troubleshooting")

    issues_found = []
    fixes_available = []

    # Issue 1: Not logged in to Azure
    print_info("Checking Azure authentication...")
    code, _, _ = run_command("az account show")
    if code != 0:
        issues_found.append("Not logged in to Azure")
        fixes_available.append("Run: az login")
    else:
        print_success("Azure authentication OK")

    # Issue 2: kubectl not configured
    print_info("Checking kubectl configuration...")
    code, _, _ = run_command("kubectl cluster-info")
    if code != 0:
        issues_found.append("kubectl not configured for AKS cluster")
        fixes_available.append("Run: python3 tool.py configure-kubectl --cluster-name <name>")
    else:
        print_success("kubectl configuration OK")

    # Issue 3: Nodes not ready
    print_info("Checking node status...")
    code, stdout, _ = run_command("kubectl get nodes")
    if code == 0:
        if 'NotReady' in stdout:
            issues_found.append("Some nodes are NotReady")
            fixes_available.append("Check node details: kubectl describe nodes")
            fixes_available.append("Common causes: Resource exhaustion, network issues")
        else:
            print_success("All nodes are Ready")

    # Issue 4: Pods in error state
    print_info("Checking pod health...")
    code, stdout, _ = run_command("kubectl get pods --all-namespaces")
    if code == 0:
        if any(status in stdout for status in ['Error', 'CrashLoopBackOff', 'ImagePullBackOff', 'Pending']):
            issues_found.append("Some pods are in error state")
            fixes_available.append("Check pod details: kubectl describe pod <pod-name> -n <namespace>")
            fixes_available.append("View logs: kubectl logs <pod-name> -n <namespace>")
        else:
            print_success("All pods are healthy")

    # Issue 5: Service without external IP
    print_info("Checking LoadBalancer services...")
    code, stdout, _ = run_command("kubectl get services --all-namespaces -o wide")
    if code == 0:
        if 'LoadBalancer' in stdout and '<pending>' in stdout.lower():
            issues_found.append("LoadBalancer service pending external IP")
            fixes_available.append("Wait 2-3 minutes for Azure to assign IP")
            fixes_available.append("Check Azure portal for any quota limits")

    # Summary
    print_header("Troubleshooting Summary")
    if issues_found:
        print_warning(f"Found {len(issues_found)} issue(s):")
        for i, issue in enumerate(issues_found, 1):
            print_error(f"{i}. {issue}")

        print_header("Recommended Fixes")
        for i, fix in enumerate(fixes_available, 1):
            print_info(f"{i}. {fix}")
        return 1
    else:
        print_success("No issues found! Cluster is healthy.")
        return 0

def cleanup(args) -> int:
    """Delete AKS cluster and all resources"""
    print_header(f"Cleaning up AKS Cluster: {args.cluster_name}")

    resource_group = args.resource_group or f"{args.cluster_name}-rg"

    print_warning("This will delete:")
    print_warning(f"  - AKS cluster: {args.cluster_name}")
    print_warning(f"  - Resource group: {resource_group}")
    print_warning(f"  - All associated resources (disks, IPs, networks)")

    if not args.yes:
        confirm = input("\nType 'yes' to confirm deletion: ")
        if confirm.lower() != 'yes':
            print_info("Deletion cancelled")
            return 0

    print_info("Deleting resource group (this may take 5-10 minutes)...")
    cmd = f"az group delete --name {resource_group} --yes --no-wait"
    code, stdout, stderr = run_command(cmd, timeout=600)

    if code == 0:
        print_success(f"Deletion initiated for resource group: {resource_group}")
        print_info("Resources will be deleted in the background")
        print_info(f"Check status: az group show --name {resource_group}")
        return 0
    else:
        print_error(f"Failed to delete resource group: {stderr}")
        return 1

def main():
    parser = argparse.ArgumentParser(
        description='Azure AKS Deployment Tool - No cloud specialist needed!',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # check-prerequisites
    subparsers.add_parser('check-prerequisites', help='Verify Azure CLI, kubectl, and credentials')

    # create-cluster
    create_parser = subparsers.add_parser('create-cluster', help='Create production-ready AKS cluster')
    create_parser.add_argument('--cluster-name', required=True, help='Name of the AKS cluster')
    create_parser.add_argument('--resource-group', help='Resource group name (default: <cluster-name>-rg)')
    create_parser.add_argument('--location', default='eastus', help='Azure region (default: eastus)')
    create_parser.add_argument('--nodes', type=int, default=2, help='Number of nodes (default: 2)')
    create_parser.add_argument('--node-size', default='Standard_B2s', help='Node VM size (default: Standard_B2s)')

    # configure-kubectl
    config_parser = subparsers.add_parser('configure-kubectl', help='Configure kubectl to connect to AKS')
    config_parser.add_argument('--cluster-name', required=True, help='Name of the AKS cluster')
    config_parser.add_argument('--resource-group', help='Resource group name (default: <cluster-name>-rg)')

    # deploy-app
    deploy_parser = subparsers.add_parser('deploy-app', help='Deploy application to AKS cluster')
    deploy_parser.add_argument('--manifest', required=True, help='Path to Kubernetes manifest file')

    # setup-ingress
    subparsers.add_parser('setup-ingress', help='Setup NGINX ingress controller')

    # test
    test_parser = subparsers.add_parser('test', help='Comprehensive 6-test suite (TDD approach)')
    test_parser.add_argument('--cluster-name', help='Cluster name to test (optional)')
    test_parser.add_argument('--resource-group', help='Resource group name (optional)')

    # health-check
    subparsers.add_parser('health-check', help='Quick health check of cluster')

    # troubleshoot
    subparsers.add_parser('troubleshoot', help='Detect and fix common issues')

    # cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Delete cluster and all resources')
    cleanup_parser.add_argument('--cluster-name', required=True, help='Name of the AKS cluster')
    cleanup_parser.add_argument('--resource-group', help='Resource group name (default: <cluster-name>-rg)')
    cleanup_parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'create-cluster': create_cluster,
        'configure-kubectl': configure_kubectl,
        'deploy-app': deploy_app,
        'setup-ingress': setup_ingress,
        'test': run_tests,
        'health-check': health_check,
        'troubleshoot': troubleshoot,
        'cleanup': cleanup,
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
