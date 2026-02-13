#!/usr/bin/env python3
"""
kubectl Configuration & Management Tool
========================================

Token-efficient executable for kubectl setup and management.
Supports OKE, GKE, AKS, EKS, Minikube, and generic Kubernetes clusters.

Usage:
    python3 tool.py check           # Check kubectl installation
    python3 tool.py install         # Install kubectl
    python3 tool.py setup-oke       # Setup for Oracle Cloud OKE
    python3 tool.py setup-gke       # Setup for Google Cloud GKE
    python3 tool.py contexts        # List all contexts
    python3 tool.py switch CONTEXT  # Switch context
    python3 tool.py verify          # Verify connection
"""

import argparse
import subprocess
import sys
import json
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Colors:
    """ANSI color codes"""
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'
    BOLD = '\033[1m'


def print_step(msg: str):
    print(f"{Colors.BLUE}==>{Colors.NC} {msg}")


def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.NC} {msg}")


def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.NC} {msg}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}!{Colors.NC} {msg}")


def run_cmd(cmd: List[str], check: bool = True, capture: bool = True) -> Tuple[int, str, str]:
    """Run shell command"""
    try:
        if capture:
            result = subprocess.run(cmd, check=check, capture_output=True, text=True)
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode, "", ""
    except subprocess.CalledProcessError as e:
        return e.returncode, getattr(e, 'stdout', ''), getattr(e, 'stderr', str(e))
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"


def get_os() -> str:
    """Get operating system"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'linux':
        return 'linux'
    elif system == 'windows':
        return 'windows'
    return 'unknown'


def cmd_check(args):
    """Check kubectl installation"""
    print_step("Checking kubectl installation")

    # Check kubectl
    code, stdout, stderr = run_cmd(["kubectl", "version", "--client", "--output=json"], check=False)

    if code == 0:
        try:
            version_info = json.loads(stdout)
            version = version_info.get('clientVersion', {}).get('gitVersion', 'unknown')
            print_success(f"kubectl installed: {version}")
        except:
            print_success("kubectl installed")
    else:
        print_error("kubectl not installed")
        print()
        print(f"{Colors.YELLOW}Install kubectl:{Colors.NC}")
        print(f"  Run: python3 {__file__} install")
        print(f"  Or visit: https://kubernetes.io/docs/tasks/tools/")
        return False

    # Check cluster connection
    print_step("Checking cluster connection")
    code, stdout, stderr = run_cmd(["kubectl", "cluster-info"], check=False)

    if code == 0:
        print_success("Connected to Kubernetes cluster")
        # Get current context
        code, stdout, _ = run_cmd(["kubectl", "config", "current-context"], check=False)
        if code == 0:
            context = stdout.strip()
            print(f"  Current context: {Colors.BOLD}{context}{Colors.NC}")
    else:
        print_warning("Not connected to any cluster")
        print(f"  Configure kubectl using: python3 {__file__} setup-[oke|gke|aks|eks]")

    return True


def cmd_install(args):
    """Install kubectl"""
    print_step("Installing kubectl")

    os_type = get_os()

    if os_type == 'macos':
        print("Installing kubectl on macOS using Homebrew...")
        code, _, stderr = run_cmd(["brew", "--version"], check=False)
        if code != 0:
            print_error("Homebrew not installed. Install from https://brew.sh")
            return

        code, _, _ = run_cmd(["brew", "install", "kubectl"], check=False, capture=False)
        if code == 0:
            print_success("kubectl installed successfully")
        else:
            print_error("Failed to install kubectl")

    elif os_type == 'linux':
        print("Installing kubectl on Linux...")
        print()
        print("Run these commands:")
        print()
        print("  curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl")
        print("  chmod +x kubectl")
        print("  sudo mv kubectl /usr/local/bin/")
        print()

    elif os_type == 'windows':
        print("Installing kubectl on Windows...")
        print()
        print("Using Chocolatey:")
        print("  choco install kubernetes-cli")
        print()
        print("Or download from:")
        print("  https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/")

    else:
        print_error(f"Unsupported OS: {os_type}")


def cmd_setup_oke(args):
    """Setup kubectl for Oracle Cloud OKE"""
    print_step("Setting up kubectl for Oracle Cloud OKE")
    print()

    # Check if OCI CLI is installed
    print_step("Checking OCI CLI installation")
    code, _, _ = run_cmd(["oci", "--version"], check=False)

    if code != 0:
        print_warning("OCI CLI not installed")
        print()
        print(f"{Colors.YELLOW}Install OCI CLI:{Colors.NC}")
        print("  bash -c \"$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)\"")
        print()
        print("Then run:")
        print("  oci setup config")
        print()
        return

    print_success("OCI CLI installed")
    print()

    # Guide user through OCI setup
    print(f"{Colors.YELLOW}Steps to configure kubectl for OKE:{Colors.NC}")
    print()
    print("1. Go to Oracle Cloud Console:")
    print("   https://cloud.oracle.com")
    print()
    print("2. Navigate to your OKE cluster:")
    print("   Menu → Developer Services → Kubernetes Clusters (OKE)")
    print()
    print("3. Click on your cluster name")
    print()
    print("4. Click 'Access Cluster' button")
    print()
    print("5. Copy the 'Local Access' command (looks like):")
    print("   oci ce cluster create-kubeconfig --cluster-id ocid1.cluster... \\")
    print("     --file $HOME/.kube/config --region us-ashburn-1 \\")
    print("     --token-version 2.0.0 --kube-endpoint PUBLIC_ENDPOINT")
    print()
    print("6. Paste and run that command here:")
    print()

    # Wait for user to run command
    input(f"{Colors.YELLOW}Press Enter after running the command...{Colors.NC}")
    print()

    # Verify
    print_step("Verifying kubectl connection")
    code, stdout, stderr = run_cmd(["kubectl", "get", "nodes"], check=False)

    if code == 0:
        print_success("kubectl successfully configured for OKE!")
        print()
        print("Cluster nodes:")
        print(stdout)
    else:
        print_error("Failed to connect to cluster")
        print(stderr)


def cmd_setup_gke(args):
    """Setup kubectl for Google Cloud GKE"""
    print_step("Setting up kubectl for Google Cloud GKE")
    print()

    # Check gcloud
    print_step("Checking gcloud CLI")
    code, _, _ = run_cmd(["gcloud", "--version"], check=False)

    if code != 0:
        print_warning("gcloud CLI not installed")
        print()
        print(f"{Colors.YELLOW}Install gcloud CLI:{Colors.NC}")
        print("  https://cloud.google.com/sdk/docs/install")
        print()
        return

    print_success("gcloud CLI installed")
    print()

    # Guide user
    print(f"{Colors.YELLOW}Configure kubectl for GKE:{Colors.NC}")
    print()
    print("1. List your GKE clusters:")
    print("   gcloud container clusters list")
    print()
    print("2. Get credentials for your cluster:")
    print("   gcloud container clusters get-credentials CLUSTER_NAME --region REGION")
    print()
    print("   Example:")
    print("   gcloud container clusters get-credentials my-cluster --region us-central1")
    print()


def cmd_setup_aks(args):
    """Setup kubectl for Azure AKS"""
    print_step("Setting up kubectl for Azure AKS")
    print()

    # Check az CLI
    print_step("Checking Azure CLI")
    code, _, _ = run_cmd(["az", "--version"], check=False)

    if code != 0:
        print_warning("Azure CLI not installed")
        print()
        print(f"{Colors.YELLOW}Install Azure CLI:{Colors.NC}")
        print("  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        print()
        return

    print_success("Azure CLI installed")
    print()

    print(f"{Colors.YELLOW}Configure kubectl for AKS:{Colors.NC}")
    print()
    print("1. Login to Azure:")
    print("   az login")
    print()
    print("2. Get AKS credentials:")
    print("   az aks get-credentials --resource-group RESOURCE_GROUP --name CLUSTER_NAME")
    print()
    print("   Example:")
    print("   az aks get-credentials --resource-group myResourceGroup --name myAKSCluster")
    print()


def cmd_setup_eks(args):
    """Setup kubectl for AWS EKS"""
    print_step("Setting up kubectl for AWS EKS")
    print()

    # Check aws CLI
    print_step("Checking AWS CLI")
    code, _, _ = run_cmd(["aws", "--version"], check=False)

    if code != 0:
        print_warning("AWS CLI not installed")
        print()
        print(f"{Colors.YELLOW}Install AWS CLI:{Colors.NC}")
        print("  https://aws.amazon.com/cli/")
        print()
        return

    print_success("AWS CLI installed")
    print()

    print(f"{Colors.YELLOW}Configure kubectl for EKS:{Colors.NC}")
    print()
    print("1. Update kubeconfig:")
    print("   aws eks update-kubeconfig --region REGION --name CLUSTER_NAME")
    print()
    print("   Example:")
    print("   aws eks update-kubeconfig --region us-west-2 --name my-cluster")
    print()


def cmd_contexts(args):
    """List kubectl contexts"""
    print_step("Listing kubectl contexts")
    print()

    code, stdout, stderr = run_cmd(["kubectl", "config", "get-contexts"], check=False)

    if code == 0:
        print(stdout)
        print()
        print(f"{Colors.YELLOW}Switch context:{Colors.NC}")
        print(f"  python3 {__file__} switch CONTEXT_NAME")
    else:
        print_error("Failed to get contexts")
        print(stderr)


def cmd_switch(args):
    """Switch kubectl context"""
    print_step(f"Switching to context: {args.context}")

    code, stdout, stderr = run_cmd(["kubectl", "config", "use-context", args.context], check=False)

    if code == 0:
        print_success(f"Switched to context: {args.context}")

        # Verify
        code, _, _ = run_cmd(["kubectl", "cluster-info"], check=False)
        if code == 0:
            print_success("Connected to cluster")
        else:
            print_warning("Context switched but cluster not reachable")
    else:
        print_error("Failed to switch context")
        print(stderr)


def cmd_verify(args):
    """Verify kubectl connection"""
    print_step("Verifying kubectl connection")
    print()

    # Current context
    code, stdout, _ = run_cmd(["kubectl", "config", "current-context"], check=False)
    if code == 0:
        print(f"Current context: {Colors.BOLD}{stdout.strip()}{Colors.NC}")
    else:
        print_error("No current context")
        return

    print()

    # Cluster info
    print_step("Cluster info")
    code, stdout, _ = run_cmd(["kubectl", "cluster-info"], check=False)
    if code == 0:
        print(stdout)
    else:
        print_error("Cannot connect to cluster")
        return

    print()

    # Nodes
    print_step("Cluster nodes")
    code, stdout, _ = run_cmd(["kubectl", "get", "nodes"], check=False)
    if code == 0:
        print(stdout)
    else:
        print_warning("Cannot get nodes")

    print()

    # Namespaces
    print_step("Namespaces")
    code, stdout, _ = run_cmd(["kubectl", "get", "namespaces"], check=False)
    if code == 0:
        print(stdout)
    else:
        print_warning("Cannot get namespaces")

    print()
    print_success("kubectl verification complete")


def cmd_kubeconfig_info(args):
    """Show kubeconfig file information"""
    print_step("Kubeconfig file information")
    print()

    # Get kubeconfig path
    kubeconfig = os.environ.get('KUBECONFIG', os.path.expanduser('~/.kube/config'))
    kubeconfig_path = Path(kubeconfig)

    if kubeconfig_path.exists():
        print_success(f"Kubeconfig file: {kubeconfig_path}")
        print(f"  Size: {kubeconfig_path.stat().st_size} bytes")
        print()

        # Read and parse
        code, stdout, _ = run_cmd(["kubectl", "config", "view", "--minify"], check=False)
        if code == 0:
            print("Current context configuration:")
            print(stdout)
    else:
        print_warning(f"Kubeconfig file not found: {kubeconfig_path}")
        print()
        print("Create it by configuring kubectl for your cluster:")
        print(f"  python3 {__file__} setup-[oke|gke|aks|eks]")


def cmd_troubleshoot(args):
    """Troubleshoot kubectl issues"""
    print_step("Troubleshooting kubectl")
    print()

    issues_found = []

    # Check kubectl
    code, _, _ = run_cmd(["kubectl", "version", "--client"], check=False)
    if code != 0:
        issues_found.append("kubectl not installed")
        print_error("kubectl not installed")
    else:
        print_success("kubectl installed")

    # Check kubeconfig
    kubeconfig = os.environ.get('KUBECONFIG', os.path.expanduser('~/.kube/config'))
    if not Path(kubeconfig).exists():
        issues_found.append("kubeconfig file not found")
        print_error(f"Kubeconfig not found: {kubeconfig}")
    else:
        print_success(f"Kubeconfig exists: {kubeconfig}")

    # Check current context
    code, stdout, _ = run_cmd(["kubectl", "config", "current-context"], check=False)
    if code != 0:
        issues_found.append("No current context set")
        print_error("No current context")
    else:
        print_success(f"Current context: {stdout.strip()}")

    # Check cluster connection
    code, _, stderr = run_cmd(["kubectl", "cluster-info"], check=False)
    if code != 0:
        issues_found.append("Cannot connect to cluster")
        print_error("Cannot connect to cluster")
        if "connection refused" in stderr.lower():
            print("  Possible causes:")
            print("  - Cluster is not running")
            print("  - Network connectivity issues")
            print("  - VPN required but not connected")
    else:
        print_success("Connected to cluster")

    print()

    if issues_found:
        print(f"{Colors.YELLOW}Issues found:{Colors.NC}")
        for issue in issues_found:
            print(f"  - {issue}")
        print()
        print(f"{Colors.YELLOW}Suggested fixes:{Colors.NC}")
        print(f"  1. Install kubectl: python3 {__file__} install")
        print(f"  2. Configure kubectl: python3 {__file__} setup-[oke|gke|aks|eks]")
        print(f"  3. Verify connection: python3 {__file__} verify")
    else:
        print_success("No issues found! kubectl is properly configured.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="kubectl Configuration & Management Tool")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Commands
    subparsers.add_parser("check", help="Check kubectl installation")
    subparsers.add_parser("install", help="Install kubectl")
    subparsers.add_parser("setup-oke", help="Setup kubectl for Oracle Cloud OKE")
    subparsers.add_parser("setup-gke", help="Setup kubectl for Google Cloud GKE")
    subparsers.add_parser("setup-aks", help="Setup kubectl for Azure AKS")
    subparsers.add_parser("setup-eks", help="Setup kubectl for AWS EKS")
    subparsers.add_parser("contexts", help="List all kubectl contexts")

    switch_parser = subparsers.add_parser("switch", help="Switch kubectl context")
    switch_parser.add_argument("context", help="Context name to switch to")

    subparsers.add_parser("verify", help="Verify kubectl connection")
    subparsers.add_parser("info", help="Show kubeconfig file information")
    subparsers.add_parser("troubleshoot", help="Troubleshoot kubectl issues")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handler
    commands = {
        "check": cmd_check,
        "install": cmd_install,
        "setup-oke": cmd_setup_oke,
        "setup-gke": cmd_setup_gke,
        "setup-aks": cmd_setup_aks,
        "setup-eks": cmd_setup_eks,
        "contexts": cmd_contexts,
        "switch": cmd_switch,
        "verify": cmd_verify,
        "info": cmd_kubeconfig_info,
        "troubleshoot": cmd_troubleshoot,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
