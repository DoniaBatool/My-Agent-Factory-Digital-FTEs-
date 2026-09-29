#!/usr/bin/env python3
"""
Docker Expert Tool

Complete Docker management - No Docker specialist needed!

Commands:
  check-prerequisites  - Verify Docker installation and setup
  build-image         - Build optimized Docker images with best practices
  run-container       - Run containers with production configurations
  compose-up          - Multi-container orchestration with Docker Compose
  optimize            - Analyze and optimize Dockerfiles for size and performance
  test                - Comprehensive Docker testing suite (6+ tests)
  troubleshoot        - Auto-detect and fix common Docker issues
  cleanup             - Clean unused images, containers, volumes

Based on official Docker documentation:
- https://docs.docker.com/
- https://docs.docker.com/build/building/best-practices/
- https://docs.docker.com/build/building/multi-stage/
"""

import argparse
import subprocess
import sys
import json
import os
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

def check_prerequisites(args) -> int:
    """Check if Docker and Docker Compose are installed"""
    print_header("Checking Docker Prerequisites")

    issues = []

    # Check Docker
    code, stdout, stderr = run_command("docker --version")
    if code == 0:
        print_success(f"Docker installed: {stdout.strip()}")
    else:
        print_error("Docker not installed")
        issues.append("Docker")

    # Check Docker daemon
    code, stdout, stderr = run_command("docker info")
    if code == 0:
        print_success("Docker daemon is running")
    else:
        print_error("Docker daemon not running")
        issues.append("Docker daemon")

    # Check Docker Compose
    code, stdout, stderr = run_command("docker compose version")
    if code == 0:
        print_success(f"Docker Compose installed: {stdout.strip()}")
    else:
        print_warning("Docker Compose not found (using legacy docker-compose)")
        code2, stdout2, stderr2 = run_command("docker-compose --version")
        if code2 == 0:
            print_success(f"Legacy docker-compose found: {stdout2.strip()}")
        else:
            issues.append("Docker Compose")

    # Check BuildKit
    code, stdout, stderr = run_command("docker buildx version")
    if code == 0:
        print_success(f"Docker BuildKit available: {stdout.strip()}")
    else:
        print_warning("Docker BuildKit not available (optional for advanced builds)")

    if issues:
        print_error(f"\nMissing requirements: {', '.join(issues)}")
        print_info("\nInstallation instructions:")
        print_info("macOS: brew install docker docker-compose")
        print_info("Ubuntu: apt-get install docker.io docker-compose-plugin")
        print_info("See: https://docs.docker.com/get-docker/")
        return 1

    print_success("\n✅ All Docker prerequisites satisfied")
    return 0

def build_image(args) -> int:
    """Build Docker image with optimization"""
    print_header(f"Building Docker Image: {args.image_name}")

    # Validate Dockerfile exists
    dockerfile = args.dockerfile or "Dockerfile"
    if not os.path.exists(dockerfile):
        print_error(f"Dockerfile not found: {dockerfile}")
        return 1

    print_info(f"Using Dockerfile: {dockerfile}")

    # Build command with best practices
    cmd = "docker build"

    # Add BuildKit for better performance
    cmd = f"DOCKER_BUILDKIT=1 {cmd}"

    # Add context and Dockerfile
    cmd += f" -f {dockerfile} -t {args.image_name}"

    # Add build args if provided
    if args.build_args:
        for arg in args.build_args.split(','):
            cmd += f" --build-arg {arg}"

    # Add target for multi-stage builds
    if args.target:
        cmd += f" --target {args.target}"

    # No cache option
    if args.no_cache:
        cmd += " --no-cache"

    # Context directory
    context = args.context or "."
    cmd += f" {context}"

    print_info(f"Running: {cmd}")

    code, stdout, stderr = run_command(cmd, timeout=600)

    if code == 0:
        print_success(f"\n✅ Image built successfully: {args.image_name}")

        # Show image size
        code2, stdout2, stderr2 = run_command(f"docker images {args.image_name} --format '{{{{.Size}}}}'")
        if code2 == 0:
            print_info(f"Image size: {stdout2.strip()}")

        return 0
    else:
        print_error("\n❌ Build failed")
        print_error(stderr)
        return 1

def run_container(args) -> int:
    """Run container with best practices"""
    print_header(f"Running Container: {args.container_name}")

    # Check if image exists
    code, stdout, stderr = run_command(f"docker images -q {args.image_name}")
    if not stdout.strip():
        print_error(f"Image not found: {args.image_name}")
        print_info("Build the image first: python3 tool.py build-image --image-name {args.image_name}")
        return 1

    # Build run command
    cmd = "docker run -d"

    # Add name
    if args.container_name:
        cmd += f" --name {args.container_name}"

    # Add ports
    if args.ports:
        for port in args.ports.split(','):
            cmd += f" -p {port}"

    # Add volumes
    if args.volumes:
        for volume in args.volumes.split(','):
            cmd += f" -v {volume}"

    # Add environment variables
    if args.env_file:
        cmd += f" --env-file {args.env_file}"
    elif args.env:
        for env in args.env.split(','):
            cmd += f" -e {env}"

    # Add network
    if args.network:
        cmd += f" --network {args.network}"

    # Add restart policy
    restart_policy = args.restart or "unless-stopped"
    cmd += f" --restart {restart_policy}"

    # Add resource limits
    if args.memory:
        cmd += f" --memory {args.memory}"
    if args.cpus:
        cmd += f" --cpus {args.cpus}"

    # Add image
    cmd += f" {args.image_name}"

    # Add command override
    if args.command:
        cmd += f" {args.command}"

    print_info(f"Running: {cmd}")

    code, stdout, stderr = run_command(cmd)

    if code == 0:
        container_id = stdout.strip()
        print_success(f"\n✅ Container started: {container_id[:12]}")

        # Show container status
        code2, stdout2, stderr2 = run_command(f"docker ps --filter id={container_id}")
        print_info("\nContainer status:")
        print(stdout2)

        return 0
    else:
        print_error("\n❌ Container failed to start")
        print_error(stderr)
        return 1

def compose_up(args) -> int:
    """Start multi-container application with Docker Compose"""
    print_header("Starting Docker Compose Application")

    # Validate compose file
    compose_file = args.compose_file or "docker-compose.yml"
    if not os.path.exists(compose_file):
        print_error(f"Compose file not found: {compose_file}")
        return 1

    print_info(f"Using compose file: {compose_file}")

    # Build command
    cmd = f"docker compose -f {compose_file}"

    # Add build option
    if args.build:
        cmd += " up -d --build"
    else:
        cmd += " up -d"

    # Add remove orphans
    if args.remove_orphans:
        cmd += " --remove-orphans"

    print_info(f"Running: {cmd}")

    code, stdout, stderr = run_command(cmd, timeout=600)

    if code == 0:
        print_success("\n✅ Compose application started")

        # Show services status
        code2, stdout2, stderr2 = run_command(f"docker compose -f {compose_file} ps")
        print_info("\nServices status:")
        print(stdout2)

        return 0
    else:
        print_error("\n❌ Compose failed")
        print_error(stderr)
        return 1

def optimize(args) -> int:
    """Analyze and optimize Dockerfile"""
    print_header("Analyzing Dockerfile for Optimization")

    dockerfile = args.dockerfile or "Dockerfile"
    if not os.path.exists(dockerfile):
        print_error(f"Dockerfile not found: {dockerfile}")
        return 1

    with open(dockerfile, 'r') as f:
        content = f.read()

    lines = content.split('\n')
    issues = []
    recommendations = []

    # Check 1: Multi-stage build
    if content.count('FROM ') == 1:
        recommendations.append("Consider using multi-stage builds to reduce image size")
    else:
        print_success("✓ Using multi-stage build")

    # Check 2: Layer caching
    apt_install_lines = [i for i, line in enumerate(lines) if 'apt-get install' in line.lower()]
    if apt_install_lines:
        for line_num in apt_install_lines:
            if '--no-install-recommends' not in lines[line_num]:
                issues.append(f"Line {line_num + 1}: Add --no-install-recommends to apt-get install")
            if 'apt-get update' in lines[line_num]:
                issues.append(f"Line {line_num + 1}: Combine apt-get update && apt-get install in single RUN")

    # Check 3: COPY vs ADD
    if 'ADD ' in content and '.tar' not in content:
        recommendations.append("Use COPY instead of ADD (unless extracting archives)")

    # Check 4: .dockerignore
    if not os.path.exists('.dockerignore'):
        issues.append("Missing .dockerignore file")
        recommendations.append("Create .dockerignore to exclude unnecessary files")
    else:
        print_success("✓ .dockerignore file exists")

    # Check 5: Non-root user
    if 'USER ' not in content:
        issues.append("Running as root user (security risk)")
        recommendations.append("Add USER directive to run as non-root")
    else:
        print_success("✓ Using non-root user")

    # Check 6: WORKDIR
    if 'WORKDIR ' not in content:
        recommendations.append("Use WORKDIR instead of cd commands")
    else:
        print_success("✓ Using WORKDIR")

    # Check 7: Specific versions
    from_lines = [line for line in lines if line.strip().startswith('FROM ')]
    for line in from_lines:
        if ':latest' in line or ':' not in line:
            issues.append(f"Using :latest tag: {line.strip()}")
            recommendations.append("Pin specific image versions (e.g., node:18-alpine)")

    # Summary
    print_header("Optimization Report")

    if issues:
        print_error(f"\n⚠️  Found {len(issues)} issues:")
        for issue in issues:
            print_error(f"  • {issue}")
    else:
        print_success("\n✅ No critical issues found")

    if recommendations:
        print_info(f"\n💡 Recommendations ({len(recommendations)}):")
        for rec in recommendations:
            print_info(f"  • {rec}")

    # Best practices guide
    print_info("\n📚 Docker Best Practices:")
    print_info("  1. Use multi-stage builds")
    print_info("  2. Minimize layers (combine RUN commands)")
    print_info("  3. Use .dockerignore")
    print_info("  4. Run as non-root user")
    print_info("  5. Pin specific versions")
    print_info("  6. Use COPY instead of ADD")
    print_info("  7. Order layers by change frequency")
    print_info("\nSee: https://docs.docker.com/build/building/best-practices/")

    return 0

def run_tests(args) -> int:
    """Comprehensive Docker testing suite"""
    print_header("Docker Comprehensive Testing")

    tests_passed = 0
    tests_failed = 0
    issues = []

    # Test 1: Docker installation
    print_info("\n[Test 1/6] Docker Installation")
    code, stdout, stderr = run_command("docker --version")
    if code == 0:
        print_success(f"✓ Docker installed: {stdout.strip()}")
        tests_passed += 1
    else:
        print_error("✗ Docker not installed")
        tests_failed += 1
        issues.append("Docker not installed")

    # Test 2: Docker daemon
    print_info("\n[Test 2/6] Docker Daemon")
    code, stdout, stderr = run_command("docker info")
    if code == 0:
        print_success("✓ Docker daemon running")
        tests_passed += 1
    else:
        print_error("✗ Docker daemon not running")
        tests_failed += 1
        issues.append("Docker daemon not running")

    # Test 3: Docker Compose
    print_info("\n[Test 3/6] Docker Compose")
    code, stdout, stderr = run_command("docker compose version")
    if code == 0:
        print_success(f"✓ Docker Compose available: {stdout.strip()}")
        tests_passed += 1
    else:
        print_warning("⚠ Docker Compose not available")
        tests_failed += 1
        issues.append("Docker Compose not available")

    # Test 4: Docker network
    print_info("\n[Test 4/6] Docker Networking")
    code, stdout, stderr = run_command("docker network ls")
    if code == 0:
        print_success("✓ Docker networking functional")
        tests_passed += 1
    else:
        print_error("✗ Docker networking issues")
        tests_failed += 1
        issues.append("Docker networking issues")

    # Test 5: Docker storage
    print_info("\n[Test 5/6] Docker Storage")
    code, stdout, stderr = run_command("docker volume ls")
    if code == 0:
        print_success("✓ Docker storage functional")
        tests_passed += 1
    else:
        print_error("✗ Docker storage issues")
        tests_failed += 1
        issues.append("Docker storage issues")

    # Test 6: Image pull test
    print_info("\n[Test 6/6] Image Pull Test")
    code, stdout, stderr = run_command("docker pull hello-world:latest", timeout=60)
    if code == 0:
        print_success("✓ Can pull images from Docker Hub")
        tests_passed += 1
        # Cleanup
        run_command("docker rmi hello-world:latest")
    else:
        print_error("✗ Cannot pull images")
        tests_failed += 1
        issues.append("Cannot pull images from Docker Hub")

    # Test summary
    print_header("Test Summary")
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"{Colors.GREEN}Passed: {tests_passed}{Colors.END}")
    print(f"{Colors.RED}Failed: {tests_failed}{Colors.END}")

    if tests_failed == 0:
        print_success("\n✅ All Docker tests passed!")
        return 0
    else:
        print_error(f"\n❌ {tests_failed} test(s) failed")
        print_info("\nIssues found:")
        for issue in issues:
            print_error(f"  • {issue}")
        return 1

def troubleshoot(args) -> int:
    """Auto-detect and fix common Docker issues"""
    print_header("Docker Troubleshooting")

    issues_found = []
    fixes_applied = []

    # Issue 1: Docker daemon not running
    print_info("\n[Check 1] Docker Daemon Status")
    code, stdout, stderr = run_command("docker info")
    if code != 0:
        issues_found.append("Docker daemon not running")
        print_error("✗ Docker daemon not running")
        print_info("Fix: Start Docker Desktop or run 'sudo systemctl start docker'")
    else:
        print_success("✓ Docker daemon running")

    # Issue 2: Disk space
    print_info("\n[Check 2] Disk Space")
    code, stdout, stderr = run_command("docker system df")
    if code == 0:
        print(stdout)
        # Parse output to check for high usage
        if "reclaimable" in stdout.lower():
            print_warning("⚠ Reclaimable space available")
            print_info("Fix: Run 'docker system prune -a' to free space")

    # Issue 3: Dangling images
    print_info("\n[Check 3] Dangling Images")
    code, stdout, stderr = run_command("docker images -f 'dangling=true' -q")
    if stdout.strip():
        count = len(stdout.strip().split('\n'))
        issues_found.append(f"{count} dangling images")
        print_warning(f"⚠ Found {count} dangling images")
        print_info("Fix: Run 'docker image prune -f'")
    else:
        print_success("✓ No dangling images")

    # Issue 4: Stopped containers
    print_info("\n[Check 4] Stopped Containers")
    code, stdout, stderr = run_command("docker ps -aq -f 'status=exited'")
    if stdout.strip():
        count = len(stdout.strip().split('\n'))
        issues_found.append(f"{count} stopped containers")
        print_warning(f"⚠ Found {count} stopped containers")
        print_info("Fix: Run 'docker container prune -f'")
    else:
        print_success("✓ No stopped containers")

    # Issue 5: Unused networks
    print_info("\n[Check 5] Unused Networks")
    code, stdout, stderr = run_command("docker network ls --filter 'dangling=true' -q")
    if stdout.strip():
        count = len(stdout.strip().split('\n'))
        issues_found.append(f"{count} unused networks")
        print_warning(f"⚠ Found {count} unused networks")
        print_info("Fix: Run 'docker network prune -f'")
    else:
        print_success("✓ No unused networks")

    # Issue 6: Unused volumes
    print_info("\n[Check 6] Unused Volumes")
    code, stdout, stderr = run_command("docker volume ls -qf 'dangling=true'")
    if stdout.strip():
        count = len(stdout.strip().split('\n'))
        issues_found.append(f"{count} unused volumes")
        print_warning(f"⚠ Found {count} unused volumes")
        print_info("Fix: Run 'docker volume prune -f'")
    else:
        print_success("✓ No unused volumes")

    # Summary
    print_header("Troubleshooting Summary")

    if issues_found:
        print_warning(f"\n⚠️  Found {len(issues_found)} issues:")
        for issue in issues_found:
            print_warning(f"  • {issue}")

        print_info("\n🔧 Recommended actions:")
        print_info("  1. docker system prune -a    # Clean all unused resources")
        print_info("  2. docker volume prune       # Remove unused volumes")
        print_info("  3. docker network prune      # Remove unused networks")

        if args.auto_fix:
            print_info("\n🔄 Auto-fixing issues...")
            run_command("docker system prune -f")
            print_success("✅ Auto-fix applied")

        return 1
    else:
        print_success("\n✅ No issues found - Docker is healthy!")
        return 0

def cleanup(args) -> int:
    """Clean unused Docker resources"""
    print_header("Docker Cleanup")

    # Show current usage
    print_info("Current disk usage:")
    code, stdout, stderr = run_command("docker system df")
    if code == 0:
        print(stdout)

    if not args.force:
        print_warning("\n⚠️  This will remove:")
        print_warning("  • All stopped containers")
        print_warning("  • All unused networks")
        print_warning("  • All dangling images")
        print_warning("  • All unused build cache")

        if args.all:
            print_warning("  • All unused images (not just dangling)")

        response = input("\nProceed? (yes/no): ").lower()
        if response not in ['yes', 'y']:
            print_info("Cleanup cancelled")
            return 0

    # Run cleanup
    print_info("\n🔄 Cleaning up...")

    if args.all:
        cmd = "docker system prune -a --volumes"
    else:
        cmd = "docker system prune --volumes"

    if args.force:
        cmd += " -f"

    code, stdout, stderr = run_command(cmd, timeout=120)

    if code == 0:
        print_success("\n✅ Cleanup complete")
        print(stdout)

        # Show new usage
        print_info("\nNew disk usage:")
        code2, stdout2, stderr2 = run_command("docker system df")
        if code2 == 0:
            print(stdout2)

        return 0
    else:
        print_error("\n❌ Cleanup failed")
        print_error(stderr)
        return 1

def main():
    parser = argparse.ArgumentParser(
        description='Docker Expert Tool - Complete Docker management',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # check-prerequisites
    subparsers.add_parser('check-prerequisites', help='Verify Docker installation')

    # build-image
    build_parser = subparsers.add_parser('build-image', help='Build Docker image')
    build_parser.add_argument('--image-name', required=True, help='Image name and tag (e.g., myapp:latest)')
    build_parser.add_argument('--dockerfile', help='Path to Dockerfile (default: Dockerfile)')
    build_parser.add_argument('--context', help='Build context directory (default: .)')
    build_parser.add_argument('--target', help='Target stage in multi-stage build')
    build_parser.add_argument('--build-args', help='Build arguments (comma-separated: KEY=VALUE,KEY2=VALUE2)')
    build_parser.add_argument('--no-cache', action='store_true', help='Do not use cache')

    # run-container
    run_parser = subparsers.add_parser('run-container', help='Run Docker container')
    run_parser.add_argument('--image-name', required=True, help='Image name to run')
    run_parser.add_argument('--container-name', help='Container name')
    run_parser.add_argument('--ports', help='Port mappings (comma-separated: 8080:80,443:443)')
    run_parser.add_argument('--volumes', help='Volume mounts (comma-separated: /host:/container)')
    run_parser.add_argument('--env', help='Environment variables (comma-separated: KEY=VALUE)')
    run_parser.add_argument('--env-file', help='Environment file path')
    run_parser.add_argument('--network', help='Network name')
    run_parser.add_argument('--restart', help='Restart policy (default: unless-stopped)')
    run_parser.add_argument('--memory', help='Memory limit (e.g., 512m, 1g)')
    run_parser.add_argument('--cpus', help='CPU limit (e.g., 0.5, 2)')
    run_parser.add_argument('--command', help='Command to override')

    # compose-up
    compose_parser = subparsers.add_parser('compose-up', help='Start Docker Compose application')
    compose_parser.add_argument('--compose-file', help='Compose file path (default: docker-compose.yml)')
    compose_parser.add_argument('--build', action='store_true', help='Build images before starting')
    compose_parser.add_argument('--remove-orphans', action='store_true', help='Remove orphaned containers')

    # optimize
    optimize_parser = subparsers.add_parser('optimize', help='Analyze Dockerfile for optimization')
    optimize_parser.add_argument('--dockerfile', help='Path to Dockerfile (default: Dockerfile)')

    # test
    subparsers.add_parser('test', help='Run comprehensive testing suite')

    # troubleshoot
    troubleshoot_parser = subparsers.add_parser('troubleshoot', help='Auto-detect and fix issues')
    troubleshoot_parser.add_argument('--auto-fix', action='store_true', help='Automatically fix issues')

    # cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean unused resources')
    cleanup_parser.add_argument('--all', action='store_true', help='Remove all unused images')
    cleanup_parser.add_argument('--force', action='store_true', help='Do not prompt for confirmation')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'build-image': build_image,
        'run-container': run_container,
        'compose-up': compose_up,
        'optimize': optimize,
        'test': run_tests,
        'troubleshoot': troubleshoot,
        'cleanup': cleanup
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
