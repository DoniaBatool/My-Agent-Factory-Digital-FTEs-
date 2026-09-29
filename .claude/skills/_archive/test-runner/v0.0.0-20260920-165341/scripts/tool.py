#!/usr/bin/env python3
"""
Test Runner Tool

Automated test execution for Python projects with pytest.
Supports unit, integration, E2E tests, coverage reports, and parallel execution.

Commands:
  check-prerequisites  - Check if pytest and required tools are installed
  run-all             - Run all tests (unit + integration + e2e)
  run-unit            - Run unit tests only
  run-integration     - Run integration tests only
  run-e2e             - Run end-to-end tests only
  run-coverage        - Run tests with coverage report
  run-specific        - Run specific test file or test function
  run-parallel        - Run tests in parallel (faster)
  watch               - Run tests in watch mode (re-run on file changes)
  test                - Comprehensive testing (check prerequisites + run all)
"""

import argparse
import subprocess
import sys
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

def run_command(cmd: str, timeout: int = 600):
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

def check_tool(tool_name: str, check_cmd: str) -> bool:
    """Check if a tool is installed"""
    code, stdout, stderr = run_command(check_cmd)
    if code == 0:
        version = stdout.strip().split('\n')[0] if stdout else "installed"
        print_success(f"{tool_name}: {version}")
        return True
    else:
        print_error(f"{tool_name}: Not found")
        return False

def check_prerequisites(args) -> int:
    """Check if pytest and required tools are installed"""
    print_header("Checking Prerequisites for Test Runner")

    all_good = True

    # Check Python
    if not check_tool("Python", "python3 --version"):
        all_good = False
        print_info("Install: brew install python (macOS) or apt-get install python3 (Linux)")

    # Check pytest
    if not check_tool("pytest", "pytest --version"):
        all_good = False
        print_info("Install: pip install pytest")

    # Check pytest-cov (optional but recommended)
    if not check_tool("pytest-cov", "pytest --version 2>/dev/null && pip show pytest-cov >/dev/null 2>&1 && echo 'installed'"):
        print_warning("pytest-cov not found (optional for coverage reports)")
        print_info("Install: pip install pytest-cov")

    # Check pytest-xdist (optional for parallel execution)
    if not check_tool("pytest-xdist", "pip show pytest-xdist >/dev/null 2>&1 && echo 'installed'"):
        print_warning("pytest-xdist not found (optional for parallel execution)")
        print_info("Install: pip install pytest-xdist")

    # Check for tests directory
    if os.path.exists("tests"):
        print_success("tests/ directory found")
    else:
        print_error("tests/ directory not found")
        all_good = False
        print_info("Create tests directory: mkdir tests")

    if all_good:
        print_success("\n✅ All prerequisites met!")
        return 0
    else:
        print_error("\n❌ Some prerequisites missing")
        return 1

def run_all(args) -> int:
    """Run all tests (unit + integration + e2e)"""
    print_header("Running All Tests")

    cmd = "pytest tests/ -v"
    if args.verbose:
        cmd += " -vv"
    if args.show_output:
        cmd += " -s"
    if args.stop_on_first:
        cmd += " -x"

    print_info(f"Command: {cmd}")
    code, stdout, stderr = run_command(cmd, timeout=600)

    print(stdout)
    if stderr:
        print(stderr)

    if code == 0:
        print_success("\n✅ All tests passed!")
        return 0
    else:
        print_error("\n❌ Some tests failed")
        return code

def run_unit(args) -> int:
    """Run unit tests only"""
    print_header("Running Unit Tests")

    cmd = "pytest tests/unit/ -v"
    if args.verbose:
        cmd += " -vv"
    if args.show_output:
        cmd += " -s"

    print_info(f"Command: {cmd}")
    code, stdout, stderr = run_command(cmd, timeout=300)

    print(stdout)
    if stderr:
        print(stderr)

    if code == 0:
        print_success("\n✅ Unit tests passed!")
        return 0
    else:
        print_error("\n❌ Unit tests failed")
        return code

def run_integration(args) -> int:
    """Run integration tests only"""
    print_header("Running Integration Tests")

    cmd = "pytest tests/integration/ -v"
    if args.verbose:
        cmd += " -vv"
    if args.show_output:
        cmd += " -s"

    print_info(f"Command: {cmd}")
    code, stdout, stderr = run_command(cmd, timeout=600)

    print(stdout)
    if stderr:
        print(stderr)

    if code == 0:
        print_success("\n✅ Integration tests passed!")
        return 0
    else:
        print_error("\n❌ Integration tests failed")
        return code

def run_e2e(args) -> int:
    """Run end-to-end tests only"""
    print_header("Running E2E Tests")

    cmd = "pytest tests/e2e/ -v"
    if args.verbose:
        cmd += " -vv"
    if args.show_output:
        cmd += " -s"

    print_info(f"Command: {cmd}")
    code, stdout, stderr = run_command(cmd, timeout=600)

    print(stdout)
    if stderr:
        print(stderr)

    if code == 0:
        print_success("\n✅ E2E tests passed!")
        return 0
    else:
        print_error("\n❌ E2E tests failed")
        return code

def run_coverage(args) -> int:
    """Run tests with coverage report"""
    print_header("Running Tests with Coverage")

    cmd = "pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -v"
    if args.min_coverage:
        cmd += f" --cov-fail-under={args.min_coverage}"

    print_info(f"Command: {cmd}")
    code, stdout, stderr = run_command(cmd, timeout=600)

    print(stdout)
    if stderr:
        print(stderr)

    if code == 0:
        print_success("\n✅ Tests passed with coverage!")
        print_info("HTML coverage report: htmlcov/index.html")
        return 0
    else:
        print_error("\n❌ Tests failed or coverage below threshold")
        return code

def run_specific(args) -> int:
    """Run specific test file or test function"""
    print_header(f"Running Specific Test: {args.test_path}")

    cmd = f"pytest {args.test_path} -v"
    if args.verbose:
        cmd += " -vv"
    if args.show_output:
        cmd += " -s"

    print_info(f"Command: {cmd}")
    code, stdout, stderr = run_command(cmd, timeout=300)

    print(stdout)
    if stderr:
        print(stderr)

    if code == 0:
        print_success("\n✅ Test(s) passed!")
        return 0
    else:
        print_error("\n❌ Test(s) failed")
        return code

def run_parallel(args) -> int:
    """Run tests in parallel (faster)"""
    print_header("Running Tests in Parallel")

    # Check if pytest-xdist is installed
    code, _, _ = run_command("pip show pytest-xdist >/dev/null 2>&1")
    if code != 0:
        print_error("pytest-xdist not installed")
        print_info("Install: pip install pytest-xdist")
        return 1

    workers = args.workers or "auto"
    cmd = f"pytest tests/ -n {workers} -v"
    if args.verbose:
        cmd += " -vv"

    print_info(f"Command: {cmd}")
    code, stdout, stderr = run_command(cmd, timeout=600)

    print(stdout)
    if stderr:
        print(stderr)

    if code == 0:
        print_success("\n✅ All tests passed (parallel execution)!")
        return 0
    else:
        print_error("\n❌ Some tests failed")
        return code

def watch(args) -> int:
    """Run tests in watch mode (re-run on file changes)"""
    print_header("Running Tests in Watch Mode")

    # Check if pytest-watch is installed
    code, _, _ = run_command("pip show pytest-watch >/dev/null 2>&1")
    if code != 0:
        print_warning("pytest-watch not installed, using simple watch loop")
        print_info("For better watch mode, install: pip install pytest-watch")

        # Simple watch implementation
        print_info("\nWatching for changes... (Ctrl+C to stop)")
        print_info("Running tests every 2 seconds\n")

        import time
        while True:
            try:
                code, stdout, stderr = run_command("pytest tests/ -v --tb=short", timeout=120)
                print("\n" + "="*80)
                print(stdout)
                if stderr:
                    print(stderr)
                print("="*80 + "\n")
                time.sleep(2)
            except KeyboardInterrupt:
                print_info("\n\nStopped watching")
                return 0
    else:
        cmd = "ptw tests/ -- -v"
        print_info(f"Command: {cmd}")
        print_info("Press Ctrl+C to stop\n")

        # Run in interactive mode
        os.system(cmd)
        return 0

def run_tests(args) -> int:
    """Comprehensive testing - check prerequisites + run all tests"""
    print_header("Comprehensive Testing")

    # Step 1: Check prerequisites
    prereq_code = check_prerequisites(args)
    if prereq_code != 0:
        print_error("\n❌ Prerequisites check failed")
        return prereq_code

    # Step 2: Run all tests
    return run_all(args)

def main():
    parser = argparse.ArgumentParser(
        description='Test Runner Tool - Automated pytest execution',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # check-prerequisites command
    subparsers.add_parser('check-prerequisites', help='Check if pytest and tools are installed')

    # run-all command
    run_all_parser = subparsers.add_parser('run-all', help='Run all tests')
    run_all_parser.add_argument('--verbose', action='store_true', help='Verbose output (-vv)')
    run_all_parser.add_argument('--show-output', action='store_true', help='Show print statements (-s)')
    run_all_parser.add_argument('--stop-on-first', action='store_true', help='Stop on first failure (-x)')

    # run-unit command
    run_unit_parser = subparsers.add_parser('run-unit', help='Run unit tests only')
    run_unit_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    run_unit_parser.add_argument('--show-output', action='store_true', help='Show print statements')

    # run-integration command
    run_integration_parser = subparsers.add_parser('run-integration', help='Run integration tests only')
    run_integration_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    run_integration_parser.add_argument('--show-output', action='store_true', help='Show print statements')

    # run-e2e command
    run_e2e_parser = subparsers.add_parser('run-e2e', help='Run E2E tests only')
    run_e2e_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    run_e2e_parser.add_argument('--show-output', action='store_true', help='Show print statements')

    # run-coverage command
    run_coverage_parser = subparsers.add_parser('run-coverage', help='Run tests with coverage report')
    run_coverage_parser.add_argument('--min-coverage', type=int, help='Minimum coverage percentage required')

    # run-specific command
    run_specific_parser = subparsers.add_parser('run-specific', help='Run specific test file or function')
    run_specific_parser.add_argument('test_path', help='Path to test file or test::function')
    run_specific_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    run_specific_parser.add_argument('--show-output', action='store_true', help='Show print statements')

    # run-parallel command
    run_parallel_parser = subparsers.add_parser('run-parallel', help='Run tests in parallel (faster)')
    run_parallel_parser.add_argument('--workers', help='Number of workers (default: auto)')
    run_parallel_parser.add_argument('--verbose', action='store_true', help='Verbose output')

    # watch command
    subparsers.add_parser('watch', help='Run tests in watch mode')

    # test command
    subparsers.add_parser('test', help='Comprehensive testing (prerequisites + all tests)')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'check-prerequisites': check_prerequisites,
        'run-all': run_all,
        'run-unit': run_unit,
        'run-integration': run_integration,
        'run-e2e': run_e2e,
        'run-coverage': run_coverage,
        'run-specific': run_specific,
        'run-parallel': run_parallel,
        'watch': watch,
        'test': run_tests
    }

    return commands[args.command](args)

if __name__ == '__main__':
    sys.exit(main())
