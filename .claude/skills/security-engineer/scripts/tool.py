#!/usr/bin/env python3
"""
Security Engineer Tool - real secret scanning + security-header checks

Commands: scan-secrets, check-headers, threat-model, test
"""
import argparse
import json
import re
import sys

SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_api_key": re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]"),
    "private_key_block": re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----"),
    "hardcoded_password": re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]{4,}['\"]"),
    "slack_token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
}

REQUIRED_SECURITY_HEADERS = (
    "Strict-Transport-Security",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Content-Security-Policy",
)

OWASP_TOP10_2021 = [
    "A01: Broken Access Control",
    "A02: Cryptographic Failures",
    "A03: Injection",
    "A04: Insecure Design",
    "A05: Security Misconfiguration",
    "A06: Vulnerable and Outdated Components",
    "A07: Identification and Authentication Failures",
    "A08: Software and Data Integrity Failures",
    "A09: Security Logging and Monitoring Failures",
    "A10: Server-Side Request Forgery",
]


def scan_secrets(text: str):
    """Return [{category, match, line}] for every likely-secret pattern
    found. `match` is truncated so a real secret is never printed in full."""
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for category, pattern in SECRET_PATTERNS.items():
            m = pattern.search(line)
            if m:
                snippet = m.group(0)
                masked = snippet[:6] + "..." if len(snippet) > 6 else "***"
                findings.append({"category": category, "match": masked, "line": lineno})
    return findings


def check_headers(headers: dict):
    """headers: case-sensitive dict of header name -> value. Returns list
    of missing required security headers."""
    present = {h.lower() for h in headers}
    return [h for h in REQUIRED_SECURITY_HEADERS if h.lower() not in present]


def build_threat_model(assets, entry_points):
    """Very small STRIDE-flavoured threat list: pair every entry point with
    the asset categories it can reach and a generic threat per asset."""
    threats = []
    generic_threats = {
        "auth": "Authentication bypass / credential stuffing",
        "token": "Token theft / replay",
        "data": "IDOR (horizontal privilege escalation)",
        "input": "Injection (SQL/command/path)",
    }
    for entry in entry_points:
        for asset in assets:
            for key, threat in generic_threats.items():
                if key in asset.lower() or key in entry.lower():
                    threats.append({"entry_point": entry, "asset": asset, "threat": threat})
    return threats


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_scan_secrets(args):
    with open(args.path) as f:
        text = f.read()
    findings = scan_secrets(text)
    if not findings:
        print(f"OK: no likely secrets found in {args.path}")
        return 0
    for f_ in findings:
        print(f"  line {f_['line']}: {f_['category']} ({f_['match']})")
    return 1


def cmd_check_headers(args):
    headers = json.loads(args.headers)
    missing = check_headers(headers)
    if not missing:
        print("OK: all required security headers present")
        return 0
    print("MISSING: " + ", ".join(missing))
    return 1


def cmd_threat_model(args):
    assets = args.assets.split(",")
    entry_points = args.entry_points.split(",")
    threats = build_threat_model(assets, entry_points)
    print(json.dumps(threats, indent=2))
    return 0


def cmd_test(args):
    findings = scan_secrets('API_KEY = "sk_live_abcdef1234567890"\npassword = "hunters2"\n')
    ok = len(findings) == 2
    ok = ok and check_headers({"Content-Security-Policy": "default-src 'self'"}) == [
        "Strict-Transport-Security", "X-Content-Type-Options", "X-Frame-Options",
    ]
    ok = ok and check_headers({h: "x" for h in REQUIRED_SECURITY_HEADERS}) == []
    threats = build_threat_model(["user tokens"], ["/api/login"])
    ok = ok and len(threats) > 0
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Security Engineer Tool")
    sub = parser.add_subparsers(dest="command")

    scan_p = sub.add_parser("scan-secrets")
    scan_p.add_argument("path")

    headers_p = sub.add_parser("check-headers")
    headers_p.add_argument("--headers", required=True, help="JSON object of response headers")

    tm_p = sub.add_parser("threat-model")
    tm_p.add_argument("--assets", required=True, help="comma-separated asset list")
    tm_p.add_argument("--entry-points", required=True, help="comma-separated entry point list")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "scan-secrets": cmd_scan_secrets,
        "check-headers": cmd_check_headers,
        "threat-model": cmd_threat_model,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
