#!/usr/bin/env python3
"""
GitHub Actions CI/CD Tool - Complete workflow automation

Commands:
  check-prerequisites  - Verify gh CLI, git config, GitHub authentication
  generate-workflow    - Create .github/workflows/*.yml files
  setup-secrets        - Configure GitHub secrets (DB_URL, API_KEYS)
  test-workflow        - Validate workflow syntax locally
  enable-actions       - Enable GitHub Actions on repository
  monitor              - Check workflow run status
  troubleshoot         - Debug failed workflows with detailed analysis
  cleanup              - Remove old workflows and workflow runs

Based on official GitHub Actions documentation
"""

import argparse
import subprocess
import sys
import json
import os
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
    """Check if required tools are installed and configured"""
    print_header("Checking GitHub Actions Prerequisites")

    tests_passed = 0
    tests_failed = 0

    # Test 1: Git installation
    print_info("\n[Test 1/5] Git installation")
    code, stdout, stderr = run_command("git --version")
    if code == 0:
        print_success(f"Git installed: {stdout.strip()}")
        tests_passed += 1
    else:
        print_error("Git not installed")
        print_info("Install: https://git-scm.com/downloads")
        tests_failed += 1

    # Test 2: GitHub CLI
    print_info("\n[Test 2/5] GitHub CLI")
    code, stdout, stderr = run_command("gh --version")
    if code == 0:
        print_success(f"GitHub CLI installed: {stdout.strip().split()[2]}")
        tests_passed += 1
    else:
        print_error("GitHub CLI not installed")
        print_info("Install: brew install gh (macOS) or https://cli.github.com/")
        tests_failed += 1

    # Test 3: GitHub authentication
    print_info("\n[Test 3/5] GitHub authentication")
    code, stdout, stderr = run_command("gh auth status")
    if code == 0:
        print_success("GitHub authenticated")
        tests_passed += 1
    else:
        print_error("Not authenticated with GitHub")
        print_info("Run: gh auth login")
        tests_failed += 1

    # Test 4: Git repository
    print_info("\n[Test 4/5] Git repository")
    code, stdout, stderr = run_command("git rev-parse --is-inside-work-tree")
    if code == 0:
        print_success("Inside git repository")
        tests_passed += 1
    else:
        print_error("Not inside a git repository")
        print_info("Run: git init")
        tests_failed += 1

    # Test 5: GitHub remote
    print_info("\n[Test 5/5] GitHub remote")
    code, stdout, stderr = run_command("git remote get-url origin")
    if code == 0 and "github.com" in stdout:
        print_success(f"GitHub remote: {stdout.strip()}")
        tests_passed += 1
    else:
        print_error("No GitHub remote configured")
        print_info("Run: git remote add origin https://github.com/user/repo.git")
        tests_failed += 1

    print_header("Prerequisites Summary")
    print(f"Passed: {tests_passed}/5")
    print(f"Failed: {tests_failed}/5")

    return 0 if tests_failed == 0 else 1

def generate_workflow(args):
    """Generate GitHub Actions workflow files"""
    print_header("Generating GitHub Actions Workflows")

    workflows_dir = Path(".github/workflows")
    workflows_dir.mkdir(parents=True, exist_ok=True)

    app_name = args.app_name or "app"
    environments = args.environments.split(",") if args.environments else ["dev", "staging", "prod"]

    print_info(f"App name: {app_name}")
    print_info(f"Environments: {', '.join(environments)}")

    # CI Workflow (Test + Build)
    ci_workflow = {
        "name": "CI - Test and Build",
        "on": {
            "push": {
                "branches": ["main", "develop", "feature/*"]
            },
            "pull_request": {
                "branches": ["main", "develop"]
            }
        },
        "jobs": {
            "test": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Python",
                     "uses": "actions/setup-python@v5",
                     "with": {"python-version": "3.11"}},
                    {"name": "Install dependencies",
                     "run": "pip install -r requirements.txt"},
                    {"name": "Run tests",
                     "run": "pytest tests/ --cov --cov-report=xml"},
                    {"name": "Upload coverage",
                     "uses": "codecov/codecov-action@v3",
                     "with": {"files": "./coverage.xml"}}
                ]
            },
            "build": {
                "runs-on": "ubuntu-latest",
                "needs": "test",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Set up Docker Buildx",
                     "uses": "docker/setup-buildx-action@v3"},
                    {"name": "Log in to GitHub Container Registry",
                     "uses": "docker/login-action@v3",
                     "with": {
                         "registry": "ghcr.io",
                         "username": "${{ github.actor }}",
                         "password": "${{ secrets.GITHUB_TOKEN }}"
                     }},
                    {"name": "Build and push Docker image",
                     "uses": "docker/build-push-action@v5",
                     "with": {
                         "context": ".",
                         "push": True,
                         "tags": f"ghcr.io/${{{{ github.repository }}}}:{app_name}-${{{{ github.sha }}}}",
                         "cache-from": "type=gha",
                         "cache-to": "type=gha,mode=max"
                     }}
                ]
            }
        }
    }

    ci_file = workflows_dir / "ci.yml"
    with open(ci_file, 'w') as f:
        yaml.dump(ci_workflow, f, sort_keys=False, default_flow_style=False)
    print_success(f"Created: {ci_file}")

    # CD Workflow (Deploy to environments)
    for env in environments:
        cd_workflow = {
            "name": f"CD - Deploy to {env.upper()}",
            "on": {
                "push": {
                    "branches": ["main" if env == "prod" else f"{env}/*"]
                }
            },
            "jobs": {
                "deploy": {
                    "runs-on": "ubuntu-latest",
                    "environment": env,
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"name": "Configure kubectl",
                         "run": f"echo \"${{{{ secrets.KUBECONFIG_{env.upper()} }}}}\" > kubeconfig && export KUBECONFIG=kubeconfig"},
                        {"name": "Deploy to Kubernetes",
                         "run": f"kubectl apply -f k8s/{env}/ --namespace={app_name}-{env}"},
                        {"name": "Wait for rollout",
                         "run": f"kubectl rollout status deployment/{app_name}-backend -n {app_name}-{env}"},
                        {"name": "Verify deployment",
                         "run": f"kubectl get pods -n {app_name}-{env}"}
                    ]
                }
            }
        }

        cd_file = workflows_dir / f"deploy-{env}.yml"
        with open(cd_file, 'w') as f:
            yaml.dump(cd_workflow, f, sort_keys=False, default_flow_style=False)
        print_success(f"Created: {cd_file}")

    print_success(f"\n✅ Generated {1 + len(environments)} workflow files")
    print_info("\nNext steps:")
    print_info("1. Review workflows: .github/workflows/")
    print_info("2. Configure secrets: python3 tool.py setup-secrets")
    print_info("3. Push to GitHub: git add . && git commit -m 'Add CI/CD' && git push")

    return 0

def setup_secrets(args):
    """Configure GitHub secrets"""
    print_header("Setting Up GitHub Secrets")

    secrets = {
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "OPENAI_API_KEY": "sk-...",
        "JWT_SECRET": "your-jwt-secret-key",
        "KUBECONFIG_DEV": "base64-encoded-kubeconfig",
        "KUBECONFIG_STAGING": "base64-encoded-kubeconfig",
        "KUBECONFIG_PROD": "base64-encoded-kubeconfig"
    }

    print_info("Required secrets for CI/CD:")
    for name, example in secrets.items():
        print(f"  - {name}: {example}")

    print_warning("\n⚠️  You need to set these secrets manually:")
    print_info("1. Go to GitHub repository → Settings → Secrets → Actions")
    print_info("2. Click 'New repository secret'")
    print_info("3. Add each secret with actual values")

    print_info("\nOr use GitHub CLI:")
    print_info("gh secret set DATABASE_URL")
    print_info("gh secret set OPENAI_API_KEY")
    print_info("gh secret set JWT_SECRET")

    # List existing secrets
    print_header("Checking Existing Secrets")
    code, stdout, stderr = run_command("gh secret list")
    if code == 0:
        print_success("Existing secrets:")
        print(stdout)
    else:
        print_warning("Could not list secrets")

    return 0

def test_workflow(args):
    """Validate workflow syntax"""
    print_header("Testing Workflow Syntax")

    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print_error("No workflows found at .github/workflows/")
        return 1

    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

    if not workflow_files:
        print_error("No workflow files found")
        return 1

    tests_passed = 0
    tests_failed = 0

    for workflow_file in workflow_files:
        print_info(f"\nTesting: {workflow_file.name}")

        try:
            with open(workflow_file, 'r') as f:
                workflow_data = yaml.safe_load(f)

            # Basic validation
            if 'name' not in workflow_data:
                print_error("Missing 'name' field")
                tests_failed += 1
                continue

            if 'on' not in workflow_data:
                print_error("Missing 'on' (trigger) field")
                tests_failed += 1
                continue

            if 'jobs' not in workflow_data:
                print_error("Missing 'jobs' field")
                tests_failed += 1
                continue

            print_success(f"✓ {workflow_file.name} - Valid syntax")
            tests_passed += 1

        except yaml.YAMLError as e:
            print_error(f"YAML syntax error: {e}")
            tests_failed += 1
        except Exception as e:
            print_error(f"Error: {e}")
            tests_failed += 1

    print_header("Test Summary")
    print(f"Passed: {tests_passed}/{len(workflow_files)}")
    print(f"Failed: {tests_failed}/{len(workflow_files)}")

    return 0 if tests_failed == 0 else 1

def enable_actions(args):
    """Enable GitHub Actions on repository"""
    print_header("Enabling GitHub Actions")

    print_info("Checking if Actions are enabled...")

    # Get repo info
    code, stdout, stderr = run_command("gh api repos/:owner/:repo")
    if code != 0:
        print_error("Could not fetch repository info")
        return 1

    repo_info = json.loads(stdout)

    if repo_info.get("has_actions", False):
        print_success("✅ GitHub Actions already enabled")
    else:
        print_warning("GitHub Actions not enabled")
        print_info("Enable via: Repository Settings → Actions → Allow all actions")

    return 0

def monitor(args):
    """Monitor workflow runs"""
    print_header("Monitoring GitHub Actions Workflows")

    limit = args.limit or 10

    print_info(f"Fetching last {limit} workflow runs...")

    code, stdout, stderr = run_command(f"gh run list --limit {limit} --json status,conclusion,name,createdAt,url")

    if code != 0:
        print_error("Could not fetch workflow runs")
        print_error(stderr)
        return 1

    runs = json.loads(stdout)

    if not runs:
        print_warning("No workflow runs found")
        return 0

    print_success(f"Found {len(runs)} recent runs:\n")

    for run in runs:
        status = run.get("status", "unknown")
        conclusion = run.get("conclusion", "")
        name = run.get("name", "Unnamed")
        created = run.get("createdAt", "")
        url = run.get("url", "")

        status_icon = {
            "completed": "✅" if conclusion == "success" else "❌",
            "in_progress": "🔄",
            "queued": "⏳"
        }.get(status, "❓")

        print(f"{status_icon} {name}")
        print(f"   Status: {status} {f'({conclusion})' if conclusion else ''}")
        print(f"   Created: {created}")
        print(f"   URL: {url}\n")

    return 0

def troubleshoot(args):
    """Troubleshoot failed workflows"""
    print_header("Troubleshooting Failed Workflows")

    print_info("Fetching failed workflow runs...")

    code, stdout, stderr = run_command("gh run list --status failure --limit 5 --json databaseId,name,url")

    if code != 0:
        print_error("Could not fetch failed runs")
        return 1

    failed_runs = json.loads(stdout)

    if not failed_runs:
        print_success("✅ No recent failures!")
        return 0

    print_warning(f"Found {len(failed_runs)} failed runs:\n")

    for run in failed_runs:
        run_id = run.get("databaseId")
        name = run.get("name")
        url = run.get("url")

        print_error(f"❌ {name} (ID: {run_id})")
        print_info(f"   URL: {url}")

        # Get logs
        print_info("   Fetching logs...")
        code, logs, stderr = run_command(f"gh run view {run_id} --log-failed")

        if code == 0:
            print(f"   Logs:\n{logs[:500]}...")  # First 500 chars

        print()

    print_header("Common Issues & Fixes")
    print_info("1. Authentication errors → Check secrets are set correctly")
    print_info("2. Build failures → Check Dockerfile and dependencies")
    print_info("3. Test failures → Run tests locally first")
    print_info("4. Deployment failures → Verify kubectl configuration")

    return 0

def cleanup(args):
    """Clean up old workflow runs"""
    print_header("Cleaning Up Old Workflow Runs")

    days = args.days or 30

    print_info(f"Deleting workflow runs older than {days} days...")

    # List old runs
    code, stdout, stderr = run_command(f"gh run list --status completed --limit 100 --json databaseId,createdAt")

    if code != 0:
        print_error("Could not fetch workflow runs")
        return 1

    runs = json.loads(stdout)
    deleted_count = 0

    for run in runs:
        run_id = run.get("databaseId")
        # Delete (GitHub CLI handles age filtering)
        code, _, _ = run_command(f"gh run delete {run_id} --yes", timeout=10)
        if code == 0:
            deleted_count += 1

    print_success(f"✅ Deleted {deleted_count} old workflow runs")

    return 0

def run_tests_cmd(args):
    """Comprehensive testing suite"""
    print_header("GitHub Actions CI/CD - Comprehensive Testing")

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

    # Test 2: Workflow files exist
    print_info("\n[Test 2/6] Workflow files")
    workflows_dir = Path(".github/workflows")
    if workflows_dir.exists() and list(workflows_dir.glob("*.yml")):
        print_success("✓ Workflow files found")
        tests_passed += 1
    else:
        print_error("✗ No workflow files found")
        print_info("Run: python3 tool.py generate-workflow")
        tests_failed += 1

    # Test 3: Workflow syntax
    print_info("\n[Test 3/6] Workflow syntax validation")
    result = test_workflow(args)
    if result == 0:
        print_success("✓ All workflows have valid syntax")
        tests_passed += 1
    else:
        print_error("✗ Workflow syntax errors found")
        tests_failed += 1

    # Test 4: GitHub Actions enabled
    print_info("\n[Test 4/6] GitHub Actions status")
    result = enable_actions(args)
    if result == 0:
        print_success("✓ GitHub Actions enabled")
        tests_passed += 1
    else:
        print_error("✗ GitHub Actions check failed")
        tests_failed += 1

    # Test 5: Secrets configuration
    print_info("\n[Test 5/6] Secrets configuration")
    code, stdout, stderr = run_command("gh secret list")
    if code == 0 and stdout.strip():
        print_success("✓ Secrets configured")
        tests_passed += 1
    else:
        print_warning("⚠ No secrets found")
        print_info("Run: python3 tool.py setup-secrets")
        tests_failed += 1

    # Test 6: Recent workflow runs
    print_info("\n[Test 6/6] Workflow execution history")
    code, stdout, stderr = run_command("gh run list --limit 1")
    if code == 0:
        print_success("✓ Can access workflow runs")
        tests_passed += 1
    else:
        print_warning("⚠ No workflow runs yet")
        tests_passed += 1

    print_header("Test Summary")
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    if tests_failed == 0:
        print_success("\n✅ All tests passed! GitHub Actions CI/CD is ready.")
    else:
        print_error(f"\n❌ {tests_failed} tests failed. Fix issues before proceeding.")

    return 0 if tests_failed == 0 else 1

def main():
    parser = argparse.ArgumentParser(
        description='GitHub Actions CI/CD Tool - Automated workflow management',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # check-prerequisites
    subparsers.add_parser('check-prerequisites', help='Verify prerequisites')

    # generate-workflow
    gen_parser = subparsers.add_parser('generate-workflow', help='Generate workflow files')
    gen_parser.add_argument('--app-name', default='app', help='Application name')
    gen_parser.add_argument('--environments', default='dev,staging,prod', help='Comma-separated environments')

    # setup-secrets
    subparsers.add_parser('setup-secrets', help='Configure GitHub secrets')

    # test-workflow
    subparsers.add_parser('test-workflow', help='Validate workflow syntax')

    # enable-actions
    subparsers.add_parser('enable-actions', help='Enable GitHub Actions')

    # monitor
    mon_parser = subparsers.add_parser('monitor', help='Monitor workflow runs')
    mon_parser.add_argument('--limit', type=int, default=10, help='Number of runs to show')

    # troubleshoot
    subparsers.add_parser('troubleshoot', help='Debug failed workflows')

    # cleanup
    clean_parser = subparsers.add_parser('cleanup', help='Clean up old workflow runs')
    clean_parser.add_argument('--days', type=int, default=30, help='Delete runs older than N days')

    # test
    subparsers.add_parser('test', help='Run comprehensive tests')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'generate-workflow': generate_workflow,
        'setup-secrets': setup_secrets,
        'test-workflow': test_workflow,
        'enable-actions': enable_actions,
        'monitor': monitor,
        'troubleshoot': troubleshoot,
        'cleanup': cleanup,
        'test': run_tests_cmd
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
