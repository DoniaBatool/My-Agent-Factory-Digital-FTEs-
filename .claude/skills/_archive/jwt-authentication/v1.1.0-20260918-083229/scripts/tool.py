#!/usr/bin/env python3
"""
JWT Authentication Tool - real HS256 JWT encode/verify (stdlib only)

Commands: generate-secret, issue-token, verify-token, check-claims, test

Implements the actual token design/verification rules this skill's
SKILL.md prescribes (exp/iat validation, deny-by-default, no plaintext
secrets) rather than a generic TODO stub. Uses only hmac/hashlib/base64/
json/time from the standard library, so it needs no third-party
dependency to be real and testable.
"""
import argparse
import base64
import hashlib
import hmac
import json
import secrets
import sys
import time


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def generate_secret(num_bytes: int = 32) -> str:
    return secrets.token_hex(num_bytes)


def encode_jwt(payload: dict, secret: str, expires_in: int = 900, issued_at=None) -> str:
    """HS256-sign a JWT. `sub` must already be in payload; exp/iat are set here."""
    if "sub" not in payload:
        raise ValueError("payload must include 'sub' (subject/user id)")
    now = int(issued_at if issued_at is not None else time.time())
    full_payload = {**payload, "iat": now, "exp": now + expires_in}
    header = {"alg": "HS256", "typ": "JWT"}
    segments = [
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode()),
        _b64url_encode(json.dumps(full_payload, separators=(",", ":")).encode()),
    ]
    signing_input = ".".join(segments).encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url_encode(signature))
    return ".".join(segments)


class JWTError(Exception):
    pass


def decode_jwt(token: str, secret: str, now=None) -> dict:
    """Verify signature + exp, return the payload dict. Raises JWTError
    (with a specific reason) on any failure -- callers should map this to
    a 401, never leak whether the failure was signature vs expiry vs
    malformed token, per the skill's 'consistent 401 vs 403' rule."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise JWTError("malformed token")

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        raise JWTError("malformed signature")

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise JWTError("invalid signature")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise JWTError("malformed payload")

    now = int(now if now is not None else time.time())
    if "exp" not in payload:
        raise JWTError("missing exp claim")
    if now >= payload["exp"]:
        raise JWTError("token expired")

    return payload


REQUIRED_CLAIMS = ("sub", "iat", "exp")


def check_claims(payload: dict):
    """Return list of missing required claims (empty list = ok)."""
    return [c for c in REQUIRED_CLAIMS if c not in payload]


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_generate_secret(args):
    print(generate_secret(args.bytes))
    return 0


def cmd_issue_token(args):
    payload = json.loads(args.claims) if args.claims else {}
    payload["sub"] = args.sub
    token = encode_jwt(payload, args.secret, expires_in=args.expires_in)
    print(token)
    return 0


def cmd_verify_token(args):
    try:
        payload = decode_jwt(args.token, args.secret)
    except JWTError as e:
        print(f"INVALID: {e}")
        return 1
    print(json.dumps(payload, indent=2))
    return 0


def cmd_check_claims(args):
    payload = json.loads(args.payload)
    missing = check_claims(payload)
    if missing:
        print(f"MISSING: {', '.join(missing)}")
        return 1
    print("OK: all required claims present")
    return 0


def cmd_test(args):
    secret = generate_secret()
    token = encode_jwt({"sub": "user-1", "role": "admin"}, secret, expires_in=60)
    payload = decode_jwt(token, secret)
    ok = payload["sub"] == "user-1" and not check_claims(payload)
    try:
        decode_jwt(token, "wrong-secret")
        ok = False
    except JWTError:
        pass
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="JWT Authentication Tool")
    sub = parser.add_subparsers(dest="command")

    gen_p = sub.add_parser("generate-secret")
    gen_p.add_argument("--bytes", type=int, default=32)

    issue_p = sub.add_parser("issue-token")
    issue_p.add_argument("--sub", required=True)
    issue_p.add_argument("--secret", required=True)
    issue_p.add_argument("--claims", default=None, help="extra claims as JSON object")
    issue_p.add_argument("--expires-in", type=int, default=900)

    verify_p = sub.add_parser("verify-token")
    verify_p.add_argument("--token", required=True)
    verify_p.add_argument("--secret", required=True)

    claims_p = sub.add_parser("check-claims")
    claims_p.add_argument("--payload", required=True, help="JSON object")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "generate-secret": cmd_generate_secret,
        "issue-token": cmd_issue_token,
        "verify-token": cmd_verify_token,
        "check-claims": cmd_check_claims,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
