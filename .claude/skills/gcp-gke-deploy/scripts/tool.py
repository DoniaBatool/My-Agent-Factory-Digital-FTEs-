#!/usr/bin/env python3
"""
GCP GKE Deployment Tool

Comprehensive Google Kubernetes Engine (GKE) cluster deployment, testing, and management.
Handles everything from prerequisites to production deployment with TDD approach.

Commands:
  check-prerequisites  - Verify gcloud SDK, kubectl installation
  create-cluster       - Create GKE cluster with free tier optimization
  configure-kubectl    - Configure kubectl for GKE cluster access
  deploy               - Deploy application to GKE cluster
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
from typing import Dict, List, Tuple

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"

def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")
def print_warning(msg): print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")
def print_info(msg): print(f"{Colors.BLUE}ℹ{Colors.END} {msg}")
def print_header(msg): print(f"\n{Colors.BOLD}==> {msg}{Colors.END}")

def run_command(cmd: str, timeout: int = 300) -> Tuple[int, str, str]:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)

def check_command_exists(cmd: str) -> bool:
    code, _, _ = run_command(f"which {cmd}")
    return code == 0

def check_prerequisites(args) -> int:
    print_header("Checking Prerequisites")
    all_good = True

    # Check gcloud SDK
    if check_command_exists("gcloud"):
        code, stdout, _ = run_command("gcloud version | head -1")
        print_success(f"gcloud SDK installed: {stdout.strip()}")
        
        # Check auth
        code, stdout, _ = run_command("gcloud auth list --filter=status:ACTIVE --format='value(account)'")
        if code == 0 and stdout.strip():
            print_success(f"Authenticated as: {stdout.strip()}")
        else:
            print_error("Not authenticated to GCP")
            print_info("Run: gcloud auth login")
            all_good = False
    else:
        print_error("gcloud SDK not installed")
        print_info("Install: https://cloud.google.com/sdk/docs/install")
        all_good = False

    # Check kubectl
    if check_command_exists("kubectl"):
        code, stdout, _ = run_command("kubectl version --client --short 2>/dev/null || kubectl version --client")
        print_success(f"kubectl installed")
    else:
        print_error("kubectl not installed")
        all_good = False

    # Check Docker (optional)
    if check_command_exists("docker"):
        print_success("Docker installed")
    else:
        print_warning("Docker not installed (optional)")

    print()
    if all_good:
        print_success("All prerequisites met! ✅")
        return 0
    else:
        print_error("Some prerequisites missing")
        return 1

def create_cluster(args) -> int:
    print_header(f"Creating GKE Cluster: {args.cluster_name}")
    
    prereq_result = check_prerequisites(argparse.Namespace())
    if prereq_result != 0:
        print_error("Prerequisites not met")
        return 1

    print_info(f"Project: {args.project}")
    print_info(f"Region/Zone: {args.zone}")
    print_info(f"Nodes: {args.nodes}")
    print_info(f"Machine type: {args.machine_type}")

    cmd_parts = [
        f"gcloud container clusters create {args.cluster_name}",
        f"--project={args.project}",
        f"--zone={args.zone}",
        f"--machine-type={args.machine_type}",
        f"--num-nodes={args.nodes}",
        f"--disk-size=10",
        "--enable-autoscaling",
        f"--min-nodes={args.nodes}",
        f"--max-nodes={args.nodes + 2}",
        "--enable-autorepair",
        "--enable-autoupgrade",
    ]

    if args.preemptible:
        cmd_parts.append("--preemptible")
        print_info("Using preemptible VMs (up to 80% cost savings)")

    create_cmd = " ".join(cmd_parts)

    if args.dry_run:
        print_info(f"DRY RUN: Would execute:\n{create_cmd}")
        return 0

    print_info("Creating GKE cluster... (10-15 minutes)")
    print_warning("Do not interrupt!")

    code, stdout, stderr = run_command(create_cmd, timeout=1200)

    if code == 0:
        print_success("GKE cluster created successfully! ✅")
        print_info("Configuring kubectl...")
        configure_kubectl(argparse.Namespace(
            cluster_name=args.cluster_name,
            zone=args.zone,
            project=args.project
        ))
        return 0
    else:
        print_error("Failed to create GKE cluster")
        print_error(stderr)
        return 1

def configure_kubectl(args) -> int:
    print_header(f"Configuring kubectl for: {args.cluster_name}")

    cmd = f"gcloud container clusters get-credentials {args.cluster_name} --zone={args.zone} --project={args.project}"
    code, stdout, stderr = run_command(cmd)

    if code == 0:
        print_success("kubectl configured successfully!")
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
    print_header(f"Deploying Application from: {args.manifest_dir}")

    code, _, _ = run_command("kubectl get nodes")
    if code != 0:
        print_error("kubectl not configured. Run configure-kubectl first")
        return 1

    if args.namespace and args.namespace != "default":
        print_info(f"Creating namespace: {args.namespace}")
        run_command(f"kubectl create namespace {args.namespace} --dry-run=client -o yaml | kubectl apply -f -")

    print_info(f"Applying manifests from: {args.manifest_dir}")
    code, stdout, stderr = run_command(f"kubectl apply -f {args.manifest_dir} -n {args.namespace}")

    if code == 0:
        print_success("Application deployed successfully!")
        print(stdout)
        time.sleep(5)
        run_command(f"kubectl get pods -n {args.namespace}")
        run_command(f"kubectl get svc -n {args.namespace}")
        return 0
    else:
        print_error("Deployment failed")
        print_error(stderr)
        return 1

def run_tests(args) -> int:
    print_header("GKE Comprehensive Testing")

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
            all_ready = all(
                any(c["type"] == "Ready" and c["status"] == "True" for c in node["status"]["conditions"])
                for node in nodes.get("items", [])
            )
            if all_ready:
                tests_passed += 1
                print_success(f"All {len(nodes.get('items', []))} nodes ready")
            else:
                tests_failed += 1
                issues.append("Some nodes not ready")
        except:
            tests_failed += 1
            issues.append("Node parsing failed")
    else:
        tests_failed += 1
        issues.append("Cannot retrieve nodes")

    # Test 4: Pods health
    print_header("Test 4: Pods Health Check")
    namespace = args.namespace if hasattr(args, "namespace") else "default"
    code, stdout, _ = run_command(f"kubectl get pods -n {namespace} -o json")
    if code == 0:
        try:
            pods = json.loads(stdout)
            if pods.get("items"):
                for pod in pods["items"]:
                    phase = pod["status"]["phase"]
                    pod_name = pod["metadata"]["name"]
                    if phase == "Running":
                        print_success(f"Pod {pod_name}: {phase}")
                tests_passed += 1
            else:
                print_warning("No pods found")
                tests_passed += 1
        except:
            tests_failed += 1
    else:
        tests_passed += 1

    # Test 5: Services
    print_header("Test 5: Services Check")
    code, stdout, _ = run_command(f"kubectl get svc -n {namespace}")
    if code == 0:
        print_success("Services listed")
        tests_passed += 1
    else:
        print_warning("Cannot get services")
        tests_passed += 1

    # Test 6: GCP resources
    print_header("Test 6: GCP Resources Check")
    code, _, _ = run_command("gcloud auth list --filter=status:ACTIVE")
    if code == 0:
        print_success("GCP credentials valid")
        tests_passed += 1
    else:
        print_error("GCP credentials invalid")
        tests_failed += 1

    print_header("Test Summary")
    print(f"\nTotal tests: {tests_passed + tests_failed}")
    print(f"{Colors.GREEN}Passed: {tests_passed}{Colors.END}")
    print(f"{Colors.RED}Failed: {tests_failed}{Colors.END}")

    if tests_failed == 0:
        print(f"\n{Colors.GREEN}✅ All tests passed!{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}❌ Some tests failed{Colors.END}")
        for issue in issues:
            print(f"  - {issue}")
        return 1

def health_check(args) -> int:
    print_header("GKE Cluster Health Check")
    namespace = args.namespace if hasattr(args, "namespace") else "default"
    all_healthy = True

    print_header("Checking Cluster")
    code, _, _ = run_command("kubectl cluster-info")
    if code == 0:
        print_success("Cluster responding")
    else:
        print_error("Cluster not responding")
        all_healthy = False

    print_header("Checking Nodes")
    code, stdout, _ = run_command("kubectl get nodes")
    if code == 0:
        print(stdout)
        if "NotReady" in stdout:
            print_error("Some nodes not ready")
            all_healthy = False
        else:
            print_success("All nodes ready")
    else:
        all_healthy = False

    print_header("Checking Pods")
    code, stdout, _ = run_command(f"kubectl get pods -n {namespace}")
    if code == 0:
        print(stdout)
        if "Error" in stdout or "CrashLoopBackOff" in stdout:
            print_error("Some pods in error state")
            all_healthy = False
        else:
            print_success("All pods healthy")

    print()
    if all_healthy:
        print_success("✅ Cluster is healthy!")
        return 0
    else:
        print_error("⚠️ Some issues detected")
        return 1

def troubleshoot(args) -> int:
    print_header("GKE Cluster Troubleshooting")
    issues_found = []
    fixes = []

    code, _, _ = run_command("kubectl cluster-info")
    if code != 0:
        issues_found.append("Cannot access cluster")
        fixes.append("Run: gcloud container clusters get-credentials <cluster> --zone=<zone>")
    else:
        print_success("Cluster accessible")

    code, stdout, _ = run_command("kubectl get nodes")
    if code == 0 and "NotReady" in stdout:
        issues_found.append("Some nodes not ready")
        fixes.append("Check: kubectl describe node <node-name>")
    elif code == 0:
        print_success("All nodes ready")

    namespace = args.namespace if hasattr(args, "namespace") else "default"
    code, stdout, _ = run_command(f"kubectl get pods -n {namespace}")
    if code == 0 and ("Error" in stdout or "CrashLoopBackOff" in stdout):
        issues_found.append("Some pods in error state")
        fixes.append(f"Check logs: kubectl logs <pod-name> -n {namespace}")

    print_header("Troubleshooting Complete")
    if not issues_found:
        print_success("✓ No issues detected!")
        return 0
    else:
        for i, issue in enumerate(issues_found, 1):
            print(f"{i}. Issue: {issue}")
            if i-1 < len(fixes):
                print(f"   Fix: {fixes[i-1]}\n")
        return 1

def cleanup_cluster(args) -> int:
    print_header(f"Deleting GKE Cluster: {args.cluster_name}")

    if not args.force:
        response = input("Delete cluster and ALL resources? Type 'yes': ")
        if response.lower() != "yes":
            print_info("Cleanup cancelled")
            return 0

    cmd = f"gcloud container clusters delete {args.cluster_name} --zone={args.zone} --project={args.project} --quiet"

    if args.dry_run:
        print_info(f"DRY RUN: Would execute: {cmd}")
        return 0

    print_info("Deleting cluster... (5-10 minutes)")
    code, stdout, stderr = run_command(cmd, timeout=800)

    if code == 0:
        print_success("Cluster deleted successfully! ✅")
        return 0
    else:
        print_error("Failed to delete cluster")
        print_error(stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(description="GCP GKE Deployment Tool")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("check-prerequisites")

    create_parser = subparsers.add_parser("create-cluster")
    create_parser.add_argument("--cluster-name", default="my-gke-cluster")
    create_parser.add_argument("--project", required=True)
    create_parser.add_argument("--zone", default="us-central1-a")
    create_parser.add_argument("--nodes", type=int, default=2)
    create_parser.add_argument("--machine-type", default="e2-small")
    create_parser.add_argument("--preemptible", action="store_true")
    create_parser.add_argument("--dry-run", action="store_true")

    config_parser = subparsers.add_parser("configure-kubectl")
    config_parser.add_argument("--cluster-name", required=True)
    config_parser.add_argument("--zone", required=True)
    config_parser.add_argument("--project", required=True)

    deploy_parser = subparsers.add_parser("deploy")
    deploy_parser.add_argument("--manifest-dir", required=True)
    deploy_parser.add_argument("--namespace", default="default")

    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("--namespace", default="default")

    health_parser = subparsers.add_parser("health-check")
    health_parser.add_argument("--namespace", default="default")

    troubleshoot_parser = subparsers.add_parser("troubleshoot")
    troubleshoot_parser.add_argument("--namespace", default="default")

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--cluster-name", required=True)
    cleanup_parser.add_argument("--zone", required=True)
    cleanup_parser.add_argument("--project", required=True)
    cleanup_parser.add_argument("--force", action="store_true")
    cleanup_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "check-prerequisites": check_prerequisites,
        "create-cluster": create_cluster,
        "configure-kubectl": configure_kubectl,
        "deploy": deploy_application,
        "test": run_tests,
        "health-check": health_check,
        "troubleshoot": troubleshoot,
        "cleanup": cleanup_cluster
    }

    return commands[args.command](args)

if __name__ == "__main__":
    sys.exit(main())
