#!/usr/bin/env python3
"""
Vercel Deployer Tool - real vercel.json validation, env var diffing and deploy command building.
"""
import argparse
import re
import sys


class Colors:
    GREEN, RED, END = '\033[92m', '\033[91m', '\033[0m'


def print_success(msg): print(f"{Colors.GREEN}✓{Colors.END} {msg}")
def print_error(msg): print(f"{Colors.RED}✗{Colors.END} {msg}")


def parse_vercel_json(config: dict) -> list:
    """Validate a vercel.json-style config dict, return a list of error strings."""
    errors = []
    if "version" in config and config["version"] not in (1, 2, 3):
        errors.append("'version' must be 1, 2, or 3")
    if "builds" in config and not isinstance(config["builds"], list):
        errors.append("'builds' must be a list")
    if "routes" in config and not isinstance(config["routes"], list):
        errors.append("'routes' must be a list")
    if "env" in config and not isinstance(config["env"], dict):
        errors.append("'env' must be an object")
    return errors


def build_env_var_diff(current: dict, desired: dict) -> dict:
    """Compute add/remove/update sets to reconcile current env vars with desired."""
    add = {k: v for k, v in desired.items() if k not in current}
    remove = [k for k in current if k not in desired]
    update = {k: v for k, v in desired.items() if k in current and current[k] != v}
    return {"add": add, "remove": remove, "update": update}


def generate_deploy_command(project: str, prod: bool = False, env_file: str = None) -> str:
    if not project or not re.match(r"^[a-zA-Z0-9._-]+$", project):
        raise ValueError("invalid project name")
    parts = ["vercel", "deploy", "--yes"]
    if prod:
        parts.append("--prod")
    if env_file:
        parts.extend(["--env-file", env_file])
    parts.extend(["--name", project])
    return " ".join(parts)


_EXPECTED_OUTPUT_DIRS = {
    "nextjs": ".next",
    "vite": "dist",
    "create-react-app": "build",
    "static": "public",
}


def check_build_output_dir(files: list, framework: str) -> bool:
    """Heuristic: does the given file listing contain the expected build output directory?"""
    expected = _EXPECTED_OUTPUT_DIRS.get(framework)
    if expected is None:
        raise ValueError(f"unknown framework: {framework}")
    return any(f == expected or f.startswith(expected + "/") for f in files)


_DOMAIN_REGEX = re.compile(
    r"^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))+$"
)


def validate_domain_name(domain: str) -> bool:
    return bool(_DOMAIN_REGEX.match(domain))


def cmd_test(args):
    import subprocess
    from pathlib import Path
    tests_dir = Path(__file__).resolve().parent.parent / "tests"
    result = subprocess.run([sys.executable, "-m", "pytest", "--import-mode=importlib", str(tests_dir), "-q"])
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Vercel Deployer Tool")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("test").set_defaults(func=cmd_test)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
