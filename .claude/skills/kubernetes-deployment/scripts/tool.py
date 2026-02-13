#!/usr/bin/env python3
"""
Kubernetes Deployment Automation Tool
======================================

Token-efficient executable script for K8s deployments.
Reduces Claude token usage by executing complex operations locally.

Usage:
    python3 tool.py generate --app-name myapp --provider oke --output k8s/
    python3 tool.py deploy --manifests k8s/oke --namespace myapp
    python3 tool.py get-ips --namespace myapp
    python3 tool.py health-check --namespace myapp
"""

import argparse
import subprocess
import sys
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color
    BOLD = '\033[1m'


def print_step(message: str):
    """Print a step message"""
    print(f"{Colors.BLUE}==>{Colors.NC} {message}")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓{Colors.NC} {message}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}✗{Colors.NC} {message}")


def print_warning(message: str):
    """Print a warning message"""
    print(f"{Colors.YELLOW}!{Colors.NC} {message}")


def run_command(cmd: List[str], check: bool = True, capture: bool = True) -> Tuple[int, str, str]:
    """
    Run a shell command and return exit code, stdout, stderr

    Args:
        cmd: Command as list of strings
        check: Raise exception on non-zero exit
        capture: Capture stdout/stderr

    Returns:
        (exit_code, stdout, stderr)
    """
    try:
        if capture:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, check=check)
            return result.returncode, "", ""
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout if hasattr(e, 'stdout') else "", e.stderr if hasattr(e, 'stderr') else str(e)


def check_kubectl():
    """Check if kubectl is installed and configured"""
    code, _, _ = run_command(["kubectl", "version", "--client"], check=False)
    if code != 0:
        print_error("kubectl not found. Please install kubectl first.")
        sys.exit(1)

    # Check cluster connection
    code, _, _ = run_command(["kubectl", "cluster-info"], check=False)
    if code != 0:
        print_warning("kubectl not connected to cluster. Configure kubectl access first.")
        return False

    return True


def generate_namespace(app_name: str, environment: str = "production") -> str:
    """Generate namespace YAML"""
    return f"""apiVersion: v1
kind: Namespace
metadata:
  name: {app_name}
  labels:
    app: {app_name}
    environment: {environment}
    managed-by: kubernetes-deployment-skill
"""


def generate_configmap(app_name: str, config: Dict[str, str]) -> str:
    """Generate ConfigMap YAML"""
    data_lines = "\n".join([f'  {k}: "{v}"' for k, v in config.items()])

    return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {app_name}-config
  namespace: {app_name}
data:
{data_lines}
"""


def generate_secret_template(app_name: str) -> str:
    """Generate Secret YAML template"""
    return f"""apiVersion: v1
kind: Secret
metadata:
  name: {app_name}-secrets
  namespace: {app_name}
type: Opaque
stringData:
  # IMPORTANT: Replace with actual values
  DATABASE_URL: "postgresql://user:password@host:5432/db"
  API_KEY: "your-api-key-here"
  JWT_SECRET: "your-jwt-secret-here"
"""


def generate_deployment(
    app_name: str,
    component: str,
    image: str,
    port: int,
    replicas: int = 2,
    resources_requests_mem: str = "256Mi",
    resources_requests_cpu: str = "250m",
    resources_limits_mem: str = "512Mi",
    resources_limits_cpu: str = "500m",
    health_path: str = "/health"
) -> str:
    """Generate Deployment YAML"""
    return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}-{component}
  namespace: {app_name}
  labels:
    app: {app_name}-{component}
    component: {component}
spec:
  replicas: {replicas}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0  # Zero-downtime deployment
  selector:
    matchLabels:
      app: {app_name}-{component}
  template:
    metadata:
      labels:
        app: {app_name}-{component}
        component: {component}
    spec:
      containers:
      - name: {component}
        image: {image}
        imagePullPolicy: Always
        ports:
        - containerPort: {port}
          name: http
          protocol: TCP

        # Environment variables from ConfigMap
        envFrom:
        - configMapRef:
            name: {app_name}-config

        # Environment variables from Secret
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: {app_name}-secrets
              key: DATABASE_URL
              optional: true
        - name: API_KEY
          valueFrom:
            secretKeyRef:
              name: {app_name}-secrets
              key: API_KEY
              optional: true

        # Health checks
        livenessProbe:
          httpGet:
            path: {health_path}
            port: {port}
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: {health_path}
            port: {port}
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3

        # Resource limits
        resources:
          requests:
            memory: "{resources_requests_mem}"
            cpu: "{resources_requests_cpu}"
          limits:
            memory: "{resources_limits_mem}"
            cpu: "{resources_limits_cpu}"

        # Security context
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          capabilities:
            drop:
            - ALL
"""


def generate_service(
    app_name: str,
    component: str,
    port: int,
    target_port: int,
    service_type: str = "LoadBalancer",
    provider: str = "generic"
) -> str:
    """Generate Service YAML"""

    annotations = ""
    if service_type == "LoadBalancer" and provider == "oke":
        annotations = """  annotations:
    service.beta.kubernetes.io/oci-load-balancer-shape: "flexible"
    service.beta.kubernetes.io/oci-load-balancer-shape-flex-min: "10"
    service.beta.kubernetes.io/oci-load-balancer-shape-flex-max: "100"
"""

    return f"""apiVersion: v1
kind: Service
metadata:
  name: {app_name}-{component}
  namespace: {app_name}
  labels:
    app: {app_name}-{component}
{annotations}spec:
  type: {service_type}
  selector:
    app: {app_name}-{component}
  ports:
  - name: http
    protocol: TCP
    port: {port}
    targetPort: {target_port}
  sessionAffinity: None
"""


def cmd_generate(args):
    """Generate K8s manifests"""
    print_step(f"Generating Kubernetes manifests for {args.app_name}")

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Default configurations
    backend_port = 8000
    frontend_port = 3000

    # Backend service type (ClusterIP for cost optimization in free tier)
    backend_service_type = args.backend_service_type
    frontend_service_type = args.frontend_service_type

    if args.free_tier and args.provider == "oke":
        print_step("Optimizing for Oracle Cloud free tier")
        backend_service_type = "ClusterIP"  # Save LoadBalancer cost
        frontend_service_type = "LoadBalancer"  # Only frontend public

    # Generate manifests
    manifests = {
        "namespace.yaml": generate_namespace(args.app_name),
        "backend-configmap.yaml": generate_configmap(args.app_name, {
            "APP_NAME": args.app_name,
            "ENVIRONMENT": "production",
            "DEBUG": "false"
        }),
        "backend-secret.yaml": generate_secret_template(args.app_name),
    }

    # Backend deployment
    if args.backend_image:
        manifests["backend-deployment.yaml"] = generate_deployment(
            args.app_name,
            "backend",
            args.backend_image,
            backend_port,
            replicas=args.replicas
        )
        manifests["backend-service.yaml"] = generate_service(
            args.app_name,
            "backend",
            80,
            backend_port,
            service_type=backend_service_type,
            provider=args.provider
        )

    # Frontend deployment
    if args.frontend_image:
        manifests["frontend-deployment.yaml"] = generate_deployment(
            args.app_name,
            "frontend",
            args.frontend_image,
            frontend_port,
            replicas=args.replicas
        )
        manifests["frontend-service.yaml"] = generate_service(
            args.app_name,
            "frontend",
            80,
            frontend_port,
            service_type=frontend_service_type,
            provider=args.provider
        )

    # Write manifests
    for filename, content in manifests.items():
        filepath = output_dir / filename
        filepath.write_text(content)
        print_success(f"Generated {filepath}")

    print()
    print_success(f"Manifests generated in {output_dir}")
    print()
    print(f"{Colors.YELLOW}Next steps:{Colors.NC}")
    print(f"1. Edit {output_dir}/backend-secret.yaml with actual secrets")
    print(f"2. Run: python3 {__file__} deploy --manifests {output_dir} --namespace {args.app_name}")


def cmd_deploy(args):
    """Deploy to Kubernetes cluster"""
    print_step(f"Deploying to namespace: {args.namespace}")

    if not check_kubectl():
        return

    manifests_dir = Path(args.manifests)
    if not manifests_dir.exists():
        print_error(f"Manifests directory not found: {manifests_dir}")
        sys.exit(1)

    # Get all YAML files
    yaml_files = sorted(manifests_dir.glob("*.yaml"))

    # Apply in order: namespace first, then configs, then deployments, then services
    order = ["namespace", "configmap", "secret", "deployment", "service"]

    for pattern in order:
        matching_files = [f for f in yaml_files if pattern in f.name.lower()]
        for filepath in matching_files:
            print_step(f"Applying {filepath.name}")
            code, stdout, stderr = run_command(["kubectl", "apply", "-f", str(filepath)])
            if code != 0:
                print_error(f"Failed to apply {filepath.name}")
                print(stderr)
            else:
                print_success(f"Applied {filepath.name}")

    print()
    print_success("Deployment complete!")
    print()
    print(f"{Colors.YELLOW}Next steps:{Colors.NC}")
    print(f"1. Wait for pods to be ready: kubectl get pods -n {args.namespace} -w")
    print(f"2. Get LoadBalancer IPs: python3 {__file__} get-ips --namespace {args.namespace}")


def cmd_get_ips(args):
    """Get LoadBalancer external IPs"""
    print_step(f"Getting LoadBalancer IPs for namespace: {args.namespace}")

    if not check_kubectl():
        return

    code, stdout, stderr = run_command([
        "kubectl", "get", "svc",
        "-n", args.namespace,
        "-o", "json"
    ])

    if code != 0:
        print_error("Failed to get services")
        print(stderr)
        return

    services = json.loads(stdout)

    print()
    for svc in services.get("items", []):
        if svc["spec"]["type"] == "LoadBalancer":
            name = svc["metadata"]["name"]
            ingress = svc.get("status", {}).get("loadBalancer", {}).get("ingress", [])

            if ingress:
                ip = ingress[0].get("ip", ingress[0].get("hostname", "pending"))
                print(f"{Colors.GREEN}✓{Colors.NC} {Colors.BOLD}{name}{Colors.NC}: http://{ip}")
            else:
                print(f"{Colors.YELLOW}⏳{Colors.NC} {name}: <pending>")

    print()


def cmd_health_check(args):
    """Check deployment health"""
    print_step(f"Health check for namespace: {args.namespace}")

    if not check_kubectl():
        return

    # Check namespace
    code, _, _ = run_command(["kubectl", "get", "namespace", args.namespace], check=False)
    if code == 0:
        print_success(f"Namespace: {args.namespace} (Active)")
    else:
        print_error(f"Namespace: {args.namespace} (Not found)")
        return

    # Check pods
    code, stdout, _ = run_command([
        "kubectl", "get", "pods",
        "-n", args.namespace,
        "-o", "json"
    ], check=False)

    if code == 0:
        pods = json.loads(stdout)
        total_pods = len(pods.get("items", []))
        ready_pods = sum(
            1 for pod in pods.get("items", [])
            if all(c["ready"] for c in pod.get("status", {}).get("containerStatuses", []))
        )

        if ready_pods == total_pods and total_pods > 0:
            print_success(f"Pods: {ready_pods}/{total_pods} running")
        else:
            print_warning(f"Pods: {ready_pods}/{total_pods} running")

    # Check services
    code, stdout, _ = run_command([
        "kubectl", "get", "svc",
        "-n", args.namespace,
        "-o", "json"
    ], check=False)

    if code == 0:
        services = json.loads(stdout)
        lb_count = sum(
            1 for svc in services.get("items", [])
            if svc["spec"]["type"] == "LoadBalancer"
        )

        lb_ready = sum(
            1 for svc in services.get("items", [])
            if svc["spec"]["type"] == "LoadBalancer"
            and svc.get("status", {}).get("loadBalancer", {}).get("ingress")
        )

        if lb_ready == lb_count and lb_count > 0:
            print_success(f"LoadBalancers: {lb_ready}/{lb_count} have external IPs")
        elif lb_count > 0:
            print_warning(f"LoadBalancers: {lb_ready}/{lb_count} have external IPs (waiting...)")

    print()


def cmd_logs(args):
    """View pod logs"""
    print_step(f"Fetching logs for {args.app} in namespace: {args.namespace}")

    if not check_kubectl():
        return

    cmd = [
        "kubectl", "logs",
        "-n", args.namespace,
        "-l", f"app={args.namespace}-{args.app}",
        "--tail", str(args.tail)
    ]

    if args.follow:
        cmd.append("-f")

    run_command(cmd, capture=False)


def cmd_scale(args):
    """Scale deployment"""
    print_step(f"Scaling {args.deployment} to {args.replicas} replicas")

    if not check_kubectl():
        return

    code, stdout, stderr = run_command([
        "kubectl", "scale", "deployment",
        "-n", args.namespace,
        args.deployment,
        f"--replicas={args.replicas}"
    ])

    if code == 0:
        print_success(f"Scaled {args.deployment} to {args.replicas} replicas")
    else:
        print_error(f"Failed to scale deployment")
        print(stderr)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Kubernetes Deployment Automation Tool"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate K8s manifests")
    generate_parser.add_argument("--app-name", required=True, help="Application name")
    generate_parser.add_argument("--backend-image", help="Backend Docker image")
    generate_parser.add_argument("--frontend-image", help="Frontend Docker image")
    generate_parser.add_argument("--provider", default="generic", choices=["oke", "gke", "aks", "eks", "generic"], help="Cloud provider")
    generate_parser.add_argument("--free-tier", action="store_true", help="Optimize for free tier")
    generate_parser.add_argument("--backend-service-type", default="LoadBalancer", choices=["LoadBalancer", "ClusterIP", "NodePort"])
    generate_parser.add_argument("--frontend-service-type", default="LoadBalancer", choices=["LoadBalancer", "ClusterIP", "NodePort"])
    generate_parser.add_argument("--replicas", type=int, default=2, help="Number of replicas")
    generate_parser.add_argument("--output", default="k8s", help="Output directory")

    # Deploy command
    deploy_parser = subparsers.add_parser("deploy", help="Deploy to cluster")
    deploy_parser.add_argument("--manifests", required=True, help="Manifests directory")
    deploy_parser.add_argument("--namespace", required=True, help="Kubernetes namespace")

    # Get IPs command
    ips_parser = subparsers.add_parser("get-ips", help="Get LoadBalancer IPs")
    ips_parser.add_argument("--namespace", required=True, help="Kubernetes namespace")

    # Health check command
    health_parser = subparsers.add_parser("health-check", help="Check deployment health")
    health_parser.add_argument("--namespace", required=True, help="Kubernetes namespace")

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View pod logs")
    logs_parser.add_argument("--namespace", required=True, help="Kubernetes namespace")
    logs_parser.add_argument("--app", required=True, help="App name (backend/frontend)")
    logs_parser.add_argument("--tail", type=int, default=50, help="Number of lines to show")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow logs")

    # Scale command
    scale_parser = subparsers.add_parser("scale", help="Scale deployment")
    scale_parser.add_argument("--namespace", required=True, help="Kubernetes namespace")
    scale_parser.add_argument("--deployment", required=True, help="Deployment name")
    scale_parser.add_argument("--replicas", type=int, required=True, help="Number of replicas")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to command handler
    commands = {
        "generate": cmd_generate,
        "deploy": cmd_deploy,
        "get-ips": cmd_get_ips,
        "health-check": cmd_health_check,
        "logs": cmd_logs,
        "scale": cmd_scale,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
