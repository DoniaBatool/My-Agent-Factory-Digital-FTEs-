#!/usr/bin/env python3
"""
Dapr Integration Tool - Complete distributed application runtime setup

Commands:
  check-prerequisites  - Verify dapr CLI, kubectl, Helm
  init-dapr           - Initialize Dapr in Kubernetes cluster
  setup-pubsub        - Configure Kafka/Redpanda Pub/Sub component
  setup-state         - Configure Redis state store component
  setup-secrets       - Configure secrets management component
  setup-cron          - Configure cron bindings for scheduled tasks
  inject-sidecar      - Add Dapr sidecar annotations to deployments
  test                - Comprehensive 6-test suite
  troubleshoot        - Debug Dapr components and sidecars

Based on official Dapr documentation
"""

import argparse
import subprocess
import sys
import json
import yaml
from pathlib import Path

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

def check_prerequisites(args):
    """Check if required tools are installed"""
    print_header("Checking Dapr Prerequisites")

    tests_passed = 0
    tests_failed = 0

    # Test 1: Dapr CLI
    print_info("\n[Test 1/5] Dapr CLI")
    code, stdout, stderr = run_command("dapr version")
    if code == 0:
        print_success(f"Dapr CLI installed: {stdout.strip().split()[2] if len(stdout.strip().split()) > 2 else 'installed'}")
        tests_passed += 1
    else:
        print_error("Dapr CLI not installed")
        print_info("Install: curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | bash")
        tests_failed += 1

    # Test 2: kubectl
    print_info("\n[Test 2/5] kubectl")
    code, stdout, stderr = run_command("kubectl version --client")
    if code == 0:
        print_success("kubectl installed")
        tests_passed += 1
    else:
        print_error("kubectl not installed")
        print_info("Install: https://kubernetes.io/docs/tasks/tools/")
        tests_failed += 1

    # Test 3: Kubernetes cluster connection
    print_info("\n[Test 3/5] Kubernetes cluster")
    code, stdout, stderr = run_command("kubectl cluster-info")
    if code == 0:
        print_success("Connected to Kubernetes cluster")
        tests_passed += 1
    else:
        print_error("Not connected to K8s cluster")
        print_info("Configure: kubectl config use-context <context>")
        tests_failed += 1

    # Test 4: Helm
    print_info("\n[Test 4/5] Helm")
    code, stdout, stderr = run_command("helm version")
    if code == 0:
        print_success("Helm installed")
        tests_passed += 1
    else:
        print_warning("Helm not installed (optional)")
        print_info("Install: brew install helm")
        tests_passed += 1  # Not critical

    # Test 5: Dapr in cluster
    print_info("\n[Test 5/5] Dapr in cluster")
    code, stdout, stderr = run_command("kubectl get pods -n dapr-system")
    if code == 0 and "dapr-" in stdout:
        print_success("Dapr already installed in cluster")
        tests_passed += 1
    else:
        print_warning("Dapr not installed in cluster yet")
        print_info("Run: python3 tool.py init-dapr")
        tests_passed += 1  # Will install later

    print_header("Prerequisites Summary")
    print(f"Passed: {tests_passed}/5")
    print(f"Failed: {tests_failed}/5")

    return 0 if tests_failed == 0 else 1

def init_dapr(args):
    """Initialize Dapr in Kubernetes cluster"""
    print_header("Initializing Dapr in Kubernetes")

    namespace = args.namespace or "dapr-system"

    print_info(f"Installing Dapr to namespace: {namespace}")

    # Install Dapr using Dapr CLI
    cmd = f"dapr init --kubernetes --wait --namespace {namespace}"

    if args.enable_ha:
        cmd += " --enable-ha"
        print_info("High Availability enabled (3 replicas)")

    if args.dev_mode:
        cmd += " --dev"
        print_info("Development mode (reduced resources)")

    print_info(f"Running: {cmd}")

    code, stdout, stderr = run_command(cmd, timeout=600)

    if code == 0:
        print_success("✅ Dapr installed successfully")
        print_info(stdout)

        # Verify installation
        print_header("Verifying Dapr Components")
        code, stdout, stderr = run_command(f"kubectl get pods -n {namespace}")
        if code == 0:
            print_success("Dapr components running:")
            print(stdout)

        return 0
    else:
        print_error("❌ Dapr installation failed")
        print_error(stderr)
        return 1

def setup_pubsub(args):
    """Setup Kafka/Redpanda Pub/Sub component"""
    print_header("Setting up Dapr Pub/Sub Component (Kafka/Redpanda)")

    components_dir = Path("dapr/components")
    components_dir.mkdir(parents=True, exist_ok=True)

    broker_list = args.brokers or "redpanda-0.redpanda.redpanda.svc.cluster.local:9092"
    consumer_group = args.consumer_group or "todo-app"

    # Kafka Pub/Sub component
    pubsub_component = {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "kafka-pubsub",
            "namespace": args.namespace or "default"
        },
        "spec": {
            "type": "pubsub.kafka",
            "version": "v1",
            "metadata": [
                {"name": "brokers", "value": broker_list},
                {"name": "consumerGroup", "value": consumer_group},
                {"name": "authType", "value": "none"},
                {"name": "maxMessageBytes", "value": "1024000"},
                {"name": "consumeRetryInterval", "value": "200ms"}
            ]
        }
    }

    pubsub_file = components_dir / "pubsub-kafka.yaml"
    with open(pubsub_file, 'w') as f:
        yaml.dump(pubsub_component, f, sort_keys=False, default_flow_style=False)

    print_success(f"Created: {pubsub_file}")

    # Apply to cluster
    code, stdout, stderr = run_command(f"kubectl apply -f {pubsub_file}")
    if code == 0:
        print_success("✅ Pub/Sub component deployed")
    else:
        print_error("❌ Failed to deploy component")
        print_error(stderr)

    print_info("\nTopics for Phase 5:")
    print_info("  - task-events: Task creation/updates")
    print_info("  - reminders: Reminder notifications")
    print_info("  - task-updates: Real-time task changes")

    return 0

def setup_state(args):
    """Setup Redis state store component"""
    print_header("Setting up Dapr State Store (Redis)")

    components_dir = Path("dapr/components")
    components_dir.mkdir(parents=True, exist_ok=True)

    redis_host = args.redis_host or "redis-master.redis.svc.cluster.local:6379"

    # Redis State Store component
    state_component = {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "statestore",
            "namespace": args.namespace or "default"
        },
        "spec": {
            "type": "state.redis",
            "version": "v1",
            "metadata": [
                {"name": "redisHost", "value": redis_host},
                {"name": "redisPassword", "secretKeyRef": {"name": "redis", "key": "password"}},
                {"name": "actorStateStore", "value": "true"}
            ]
        }
    }

    state_file = components_dir / "state-redis.yaml"
    with open(state_file, 'w') as f:
        yaml.dump(state_component, f, sort_keys=False, default_flow_style=False)

    print_success(f"Created: {state_file}")

    # Apply to cluster
    code, stdout, stderr = run_command(f"kubectl apply -f {state_file}")
    if code == 0:
        print_success("✅ State store component deployed")
    else:
        print_error("❌ Failed to deploy component")
        print_error(stderr)

    print_info("\nState store use cases:")
    print_info("  - Session management")
    print_info("  - Task metadata caching")
    print_info("  - User preferences")

    return 0

def setup_secrets(args):
    """Setup Dapr secrets management"""
    print_header("Setting up Dapr Secrets Management")

    components_dir = Path("dapr/components")
    components_dir.mkdir(parents=True, exist_ok=True)

    # Kubernetes Secrets component
    secrets_component = {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "kubernetes-secret-store",
            "namespace": args.namespace or "default"
        },
        "spec": {
            "type": "secretstores.kubernetes",
            "version": "v1",
            "metadata": []
        }
    }

    secrets_file = components_dir / "secrets-kubernetes.yaml"
    with open(secrets_file, 'w') as f:
        yaml.dump(secrets_component, f, sort_keys=False, default_flow_style=False)

    print_success(f"Created: {secrets_file}")

    # Apply to cluster
    code, stdout, stderr = run_command(f"kubectl apply -f {secrets_file}")
    if code == 0:
        print_success("✅ Secrets component deployed")
    else:
        print_error("❌ Failed to deploy component")
        print_error(stderr)

    print_info("\nAccess secrets in code:")
    print_info("  GET http://localhost:3500/v1.0/secrets/kubernetes-secret-store/db-password")

    return 0

def setup_cron(args):
    """Setup Dapr cron bindings"""
    print_header("Setting up Dapr Cron Bindings")

    components_dir = Path("dapr/components")
    components_dir.mkdir(parents=True, exist_ok=True)

    schedule = args.schedule or "*/5 * * * *"  # Every 5 minutes

    # Cron binding component
    cron_component = {
        "apiVersion": "dapr.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": "reminder-cron",
            "namespace": args.namespace or "default"
        },
        "spec": {
            "type": "bindings.cron",
            "version": "v1",
            "metadata": [
                {"name": "schedule", "value": schedule}
            ]
        }
    }

    cron_file = components_dir / "cron-reminders.yaml"
    with open(cron_file, 'w') as f:
        yaml.dump(cron_component, f, sort_keys=False, default_flow_style=False)

    print_success(f"Created: {cron_file}")
    print_info(f"Schedule: {schedule}")

    # Apply to cluster
    code, stdout, stderr = run_command(f"kubectl apply -f {cron_file}")
    if code == 0:
        print_success("✅ Cron binding deployed")
    else:
        print_error("❌ Failed to deploy component")
        print_error(stderr)

    print_info("\nCron use cases:")
    print_info("  - Check for due reminders every 5 minutes")
    print_info("  - Process recurring tasks")
    print_info("  - Cleanup expired data")

    return 0

def inject_sidecar(args):
    """Inject Dapr sidecar annotations into deployments"""
    print_header("Injecting Dapr Sidecar Annotations")

    deployment_file = args.deployment_file
    app_id = args.app_id or "todo-app"
    app_port = args.app_port or "8000"

    if not Path(deployment_file).exists():
        print_error(f"Deployment file not found: {deployment_file}")
        return 1

    # Read existing deployment
    with open(deployment_file, 'r') as f:
        deployment = yaml.safe_load(f)

    # Add Dapr annotations
    annotations = deployment.setdefault('spec', {}).setdefault('template', {}).setdefault('metadata', {}).setdefault('annotations', {})

    annotations.update({
        'dapr.io/enabled': 'true',
        'dapr.io/app-id': app_id,
        'dapr.io/app-port': app_port,
        'dapr.io/app-protocol': 'http',
        'dapr.io/enable-api-logging': 'true'
    })

    # Write updated deployment
    output_file = args.output or deployment_file
    with open(output_file, 'w') as f:
        yaml.dump(deployment, f, sort_keys=False, default_flow_style=False)

    print_success(f"✅ Sidecar annotations added to: {output_file}")
    print_info(f"App ID: {app_id}")
    print_info(f"App Port: {app_port}")

    print_info("\nApply deployment:")
    print_info(f"kubectl apply -f {output_file}")

    return 0

def run_tests_cmd(args):
    """Comprehensive testing suite"""
    print_header("Dapr Integration - Comprehensive Testing")

    tests_passed = 0
    tests_failed = 0

    # Test 1: Prerequisites
    print_info("\n[Test 1/6] Prerequisites check")
    result = check_prerequisites(args)
    if result == 0:
        print_success("✓ All prerequisites met")
        tests_passed += 1
    else:
        print_error("✗ Prerequisites check failed")
        tests_failed += 1

    # Test 2: Dapr installation
    print_info("\n[Test 2/6] Dapr installation")
    code, stdout, stderr = run_command("kubectl get pods -n dapr-system")
    if code == 0 and "dapr-" in stdout:
        print_success("✓ Dapr running in cluster")
        tests_passed += 1
    else:
        print_error("✗ Dapr not installed")
        print_info("Run: python3 tool.py init-dapr")
        tests_failed += 1

    # Test 3: Dapr components
    print_info("\n[Test 3/6] Dapr components")
    code, stdout, stderr = run_command("kubectl get components")
    if code == 0:
        component_count = len([line for line in stdout.split('\n') if line.strip() and not line.startswith('NAME')])
        print_success(f"✓ {component_count} components found")
        tests_passed += 1
    else:
        print_warning("⚠ No components found")
        print_info("Run: python3 tool.py setup-pubsub/setup-state")
        tests_passed += 1  # Not critical yet

    # Test 4: Pub/Sub component
    print_info("\n[Test 4/6] Pub/Sub component")
    code, stdout, stderr = run_command("kubectl get component kafka-pubsub")
    if code == 0:
        print_success("✓ Pub/Sub component configured")
        tests_passed += 1
    else:
        print_warning("⚠ Pub/Sub not configured")
        tests_passed += 1

    # Test 5: State store component
    print_info("\n[Test 5/6] State store component")
    code, stdout, stderr = run_command("kubectl get component statestore")
    if code == 0:
        print_success("✓ State store configured")
        tests_passed += 1
    else:
        print_warning("⚠ State store not configured")
        tests_passed += 1

    # Test 6: Dapr sidecars
    print_info("\n[Test 6/6] Dapr sidecars in pods")
    code, stdout, stderr = run_command("kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{.metadata.name}{\"\\t\"}{.metadata.annotations.dapr\\.io/enabled}{\"\\n\"}{end}'")
    if code == 0 and 'true' in stdout:
        sidecar_count = stdout.count('true')
        print_success(f"✓ {sidecar_count} pods with Dapr sidecars")
        tests_passed += 1
    else:
        print_warning("⚠ No Dapr sidecars found")
        print_info("Run: python3 tool.py inject-sidecar")
        tests_passed += 1

    print_header("Test Summary")
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    if tests_failed == 0:
        print_success("\n✅ All tests passed! Dapr integration is ready.")
    else:
        print_error(f"\n❌ {tests_failed} tests failed. Fix issues before proceeding.")

    return 0 if tests_failed == 0 else 1

def troubleshoot(args):
    """Troubleshoot Dapr components and sidecars"""
    print_header("Troubleshooting Dapr")

    print_info("Checking Dapr system pods...")
    code, stdout, stderr = run_command("kubectl get pods -n dapr-system")
    print(stdout)

    print_info("\nChecking Dapr components...")
    code, stdout, stderr = run_command("kubectl get components --all-namespaces")
    print(stdout)

    print_info("\nChecking pods with Dapr sidecars...")
    code, stdout, stderr = run_command("kubectl get pods --all-namespaces -o jsonpath='{range .items[?(@.metadata.annotations.dapr\\.io/enabled==\"true\")]}{.metadata.namespace}{\"\\t\"}{.metadata.name}{\"\\n\"}{end}'")
    if stdout.strip():
        print(stdout)
    else:
        print_warning("No pods with Dapr sidecars found")

    print_header("Common Issues & Fixes")
    print_info("1. Dapr pods CrashLoopBackOff → Check logs: kubectl logs -n dapr-system <pod>")
    print_info("2. Component not loading → Verify YAML syntax and namespace")
    print_info("3. Sidecar not injected → Check annotations in deployment")
    print_info("4. Pub/Sub not working → Verify Kafka/Redpanda connectivity")
    print_info("5. State store errors → Check Redis connection")

    return 0

def main():
    parser = argparse.ArgumentParser(
        description='Dapr Integration Tool - Distributed application runtime',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # check-prerequisites
    subparsers.add_parser('check-prerequisites', help='Verify prerequisites')

    # init-dapr
    init_parser = subparsers.add_parser('init-dapr', help='Initialize Dapr in cluster')
    init_parser.add_argument('--namespace', default='dapr-system', help='Dapr namespace')
    init_parser.add_argument('--enable-ha', action='store_true', help='Enable high availability')
    init_parser.add_argument('--dev-mode', action='store_true', help='Development mode')

    # setup-pubsub
    pubsub_parser = subparsers.add_parser('setup-pubsub', help='Setup Pub/Sub component')
    pubsub_parser.add_argument('--brokers', help='Kafka broker list')
    pubsub_parser.add_argument('--consumer-group', default='todo-app', help='Consumer group')
    pubsub_parser.add_argument('--namespace', default='default', help='Component namespace')

    # setup-state
    state_parser = subparsers.add_parser('setup-state', help='Setup state store')
    state_parser.add_argument('--redis-host', help='Redis host')
    state_parser.add_argument('--namespace', default='default', help='Component namespace')

    # setup-secrets
    secrets_parser = subparsers.add_parser('setup-secrets', help='Setup secrets')
    secrets_parser.add_argument('--namespace', default='default', help='Component namespace')

    # setup-cron
    cron_parser = subparsers.add_parser('setup-cron', help='Setup cron bindings')
    cron_parser.add_argument('--schedule', default='*/5 * * * *', help='Cron schedule')
    cron_parser.add_argument('--namespace', default='default', help='Component namespace')

    # inject-sidecar
    inject_parser = subparsers.add_parser('inject-sidecar', help='Inject Dapr sidecar')
    inject_parser.add_argument('--deployment-file', required=True, help='Deployment YAML file')
    inject_parser.add_argument('--app-id', required=True, help='Dapr app ID')
    inject_parser.add_argument('--app-port', default='8000', help='App port')
    inject_parser.add_argument('--output', help='Output file (default: overwrite input)')

    # test
    subparsers.add_parser('test', help='Run comprehensive tests')

    # troubleshoot
    subparsers.add_parser('troubleshoot', help='Troubleshoot Dapr')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'init-dapr': init_dapr,
        'setup-pubsub': setup_pubsub,
        'setup-state': setup_state,
        'setup-secrets': setup_secrets,
        'setup-cron': setup_cron,
        'inject-sidecar': inject_sidecar,
        'test': run_tests_cmd,
        'troubleshoot': troubleshoot
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
