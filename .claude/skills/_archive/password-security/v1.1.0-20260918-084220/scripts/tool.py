#!/usr/bin/env python3
"""
Password Security Tool - real salted PBKDF2 hashing (stdlib only)

Commands: hash-password, verify-password, check-policy, generate-reset-token, test

Uses hashlib.pbkdf2_hmac (stdlib, no bcrypt/argon2 dependency needed to be
a genuinely slow, salted, constant-time-verified hash) instead of the
previous TODO stub that unconditionally printed success.
"""
import argparse
import base64
import hashlib
import hmac
import os
import re
import secrets
import sys
import time

ITERATIONS = 200_000
ALGO = "sha256"


def hash_password(password: str, salt: bytes = None, iterations: int = ITERATIONS) -> str:
    """Return 'pbkdf2_sha256$<iterations>$<salt-b64>$<hash-b64>'."""
    salt = salt or os.urandom(16)
    derived = hashlib.pbkdf2_hmac(ALGO, password.encode(), salt, iterations)
    return f"pbkdf2_{ALGO}${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(derived).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo_tag, iterations, salt_b64, hash_b64 = stored_hash.split("$")
        iterations = int(iterations)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (ValueError, TypeError):
        return False
    algo = algo_tag.replace("pbkdf2_", "")
    actual = hashlib.pbkdf2_hmac(algo, password.encode(), salt, iterations)
    return hmac.compare_digest(actual, expected)


def check_password_policy(password: str):
    """Return a list of violated rules (empty list = policy satisfied)."""
    violations = []
    if len(password) < 8:
        violations.append("must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        violations.append("must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        violations.append("must contain a lowercase letter")
    if not re.search(r"\d", password):
        violations.append("must contain a digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        violations.append("must contain a special character")
    return violations


def generate_reset_token(ttl_seconds: int = 3600):
    """Return (token, expires_at_epoch). The token itself carries no user
    info -- callers must store a hash of it mapped to a user id + expiry,
    never the raw token, per 'time-limited token; invalidate after use'."""
    token = secrets.token_urlsafe(32)
    expires_at = int(time.time()) + ttl_seconds
    return token, expires_at


def is_reset_token_valid(expires_at: int, now: int = None) -> bool:
    now = now if now is not None else int(time.time())
    return now < expires_at


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_hash_password(args):
    violations = check_password_policy(args.password)
    if violations and not args.force:
        print("REJECTED (policy):")
        for v in violations:
            print(f"  - {v}")
        return 1
    print(hash_password(args.password))
    return 0


def cmd_verify_password(args):
    ok = verify_password(args.password, args.hash)
    print("MATCH" if ok else "NO MATCH")
    return 0 if ok else 1


def cmd_check_policy(args):
    violations = check_password_policy(args.password)
    if not violations:
        print("OK: policy satisfied")
        return 0
    for v in violations:
        print(f"  - {v}")
    return 1


def cmd_generate_reset_token(args):
    token, expires_at = generate_reset_token(args.ttl)
    print(f"token={token}")
    print(f"expires_at={expires_at}")
    return 0


def cmd_test(args):
    h = hash_password("Correct-Horse-1!")
    ok = verify_password("Correct-Horse-1!", h) and not verify_password("wrong", h)
    ok = ok and check_password_policy("weak") != []
    ok = ok and check_password_policy("Correct-Horse-1!") == []
    token, exp = generate_reset_token(ttl_seconds=1)
    ok = ok and is_reset_token_valid(exp, now=exp - 1) and not is_reset_token_valid(exp, now=exp + 1)
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Password Security Tool")
    sub = parser.add_subparsers(dest="command")

    hash_p = sub.add_parser("hash-password")
    hash_p.add_argument("password")
    hash_p.add_argument("--force", action="store_true", help="hash even if policy fails")

    verify_p = sub.add_parser("verify-password")
    verify_p.add_argument("password")
    verify_p.add_argument("--hash", required=True)

    policy_p = sub.add_parser("check-policy")
    policy_p.add_argument("password")

    reset_p = sub.add_parser("generate-reset-token")
    reset_p.add_argument("--ttl", type=int, default=3600)

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "hash-password": cmd_hash_password,
        "verify-password": cmd_verify_password,
        "check-policy": cmd_check_policy,
        "generate-reset-token": cmd_generate_reset_token,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
