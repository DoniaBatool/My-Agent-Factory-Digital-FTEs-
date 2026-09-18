import base64
import json
import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("jwt_authentication_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


# --- crypto / core logic: happy path ---------------------------------------

def test_encode_requires_sub():
    try:
        tool.encode_jwt({}, "secret")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_encode_decode_roundtrip():
    token = tool.encode_jwt({"sub": "u1"}, "topsecret", expires_in=300)
    payload = tool.decode_jwt(token, "topsecret")
    assert payload["sub"] == "u1"
    assert payload["exp"] == payload["iat"] + 300


def test_decode_rejects_wrong_secret():
    token = tool.encode_jwt({"sub": "u1"}, "secret-a")
    try:
        tool.decode_jwt(token, "secret-b")
        assert False, "expected JWTError"
    except tool.JWTError as e:
        assert "signature" in str(e)


def test_decode_rejects_expired_token():
    token = tool.encode_jwt({"sub": "u1"}, "secret", expires_in=10, issued_at=1000)
    try:
        tool.decode_jwt(token, "secret", now=1011)
        assert False, "expected JWTError"
    except tool.JWTError as e:
        assert "expired" in str(e)


def test_decode_rejects_malformed_token():
    try:
        tool.decode_jwt("not-a-jwt", "secret")
        assert False, "expected JWTError"
    except tool.JWTError as e:
        assert "malformed" in str(e)


def test_decode_does_not_leak_which_check_failed_via_type():
    """Both a bad signature and a malformed token raise the SAME exception
    type (JWTError) -- callers must map both to a generic 401, never
    branch on the reason in a way that leaks info to the client."""
    token = tool.encode_jwt({"sub": "u1"}, "secret-a")
    errors = []
    for bad_token, bad_secret in [(token, "wrong"), ("garbage", "secret")]:
        try:
            tool.decode_jwt(bad_token, bad_secret)
        except tool.JWTError as e:
            errors.append(type(e))
    assert errors == [tool.JWTError, tool.JWTError]


def test_check_claims_flags_missing():
    assert tool.check_claims({"sub": "u1"}) == ["iat", "exp"]


def test_check_claims_ok_when_all_present():
    assert tool.check_claims({"sub": "u1", "iat": 1, "exp": 2}) == []


def test_generate_secret_is_random_and_hex():
    a, b = tool.generate_secret(), tool.generate_secret()
    assert a != b
    int(a, 16)  # raises if not valid hex


# --- edge cases: exact boundaries, malformed pieces the happy-path never hits --

def test_generate_secret_respects_byte_length():
    short = tool.generate_secret(num_bytes=4)
    long = tool.generate_secret(num_bytes=64)
    # token_hex(n) produces 2n hex chars
    assert len(short) == 8
    assert len(long) == 128


def test_decode_expiry_boundary_at_exact_exp_is_expired():
    """now == exp must be treated as expired (the check is `now >= exp`,
    not `now > exp`) -- an off-by-one here is a real security bug: it
    would accept a token for one extra second past its stated expiry."""
    token = tool.encode_jwt({"sub": "u1"}, "secret", expires_in=10, issued_at=1000)
    try:
        tool.decode_jwt(token, "secret", now=1010)  # now == exp exactly
        assert False, "token at exact exp boundary must be rejected as expired"
    except tool.JWTError as e:
        assert "expired" in str(e)


def test_decode_one_second_before_expiry_is_still_valid():
    token = tool.encode_jwt({"sub": "u1"}, "secret", expires_in=10, issued_at=1000)
    payload = tool.decode_jwt(token, "secret", now=1009)  # one second before exp
    assert payload["sub"] == "u1"


def test_decode_rejects_malformed_signature_segment():
    """A token with a valid header/payload shape but a signature segment
    that isn't valid base64 must be rejected as malformed, not crash with
    an uncaught exception."""
    token = tool.encode_jwt({"sub": "u1"}, "secret")
    header_b64, payload_b64, _sig = token.split(".")
    bad_token = f"{header_b64}.{payload_b64}.not!!valid!!base64!!"
    try:
        tool.decode_jwt(bad_token, "secret")
        assert False, "expected JWTError"
    except tool.JWTError as e:
        assert "malformed" in str(e) or "signature" in str(e)


def test_decode_rejects_payload_missing_exp_claim():
    """A token whose payload lacks 'exp' entirely (not expired -- simply
    never had an expiry) must be rejected, not treated as eternally valid."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload_no_exp = {"sub": "u1", "iat": 1000}  # deliberately no "exp"
    import hmac as _hmac
    import hashlib as _hashlib

    def b64(d):
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode("ascii")

    segments = [
        b64(json.dumps(header, separators=(",", ":")).encode()),
        b64(json.dumps(payload_no_exp, separators=(",", ":")).encode()),
    ]
    signing_input = ".".join(segments).encode()
    sig = _hmac.new(b"secret", signing_input, _hashlib.sha256).digest()
    segments.append(b64(sig))
    token = ".".join(segments)

    try:
        tool.decode_jwt(token, "secret", now=2000)
        assert False, "expected JWTError for missing exp claim"
    except tool.JWTError as e:
        assert "exp" in str(e)


def test_decode_rejects_payload_that_is_not_valid_json():
    """A token whose payload segment decodes as valid base64 but is not
    valid JSON must be rejected as malformed, not crash."""
    header = {"alg": "HS256", "typ": "JWT"}
    import hmac as _hmac
    import hashlib as _hashlib

    def b64(d):
        return base64.urlsafe_b64encode(d).rstrip(b"=").decode("ascii")

    header_b64 = b64(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64(b"not-json-at-all")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    sig = _hmac.new(b"secret", signing_input, _hashlib.sha256).digest()
    token = f"{header_b64}.{payload_b64}.{b64(sig)}"

    try:
        tool.decode_jwt(token, "secret")
        assert False, "expected JWTError for non-JSON payload"
    except tool.JWTError as e:
        assert "malformed" in str(e) or "payload" in str(e)


def test_check_claims_returns_empty_list_type_not_falsy_none():
    """check_claims must return an empty LIST (not None or False) when
    nothing is missing, so callers can safely do `if missing:`."""
    result = tool.check_claims({"sub": "u1", "iat": 1, "exp": 2})
    assert result == []
    assert isinstance(result, list)


# --- CLI layer: previously completely untested (0% of cmd_*/main) ----------

class _Args:
    """Minimal stand-in for an argparse.Namespace."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_cmd_generate_secret_prints_valid_hex(capsys):
    rc = tool.cmd_generate_secret(_Args(bytes=16))
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert len(out) == 32
    int(out, 16)  # raises if not valid hex


def test_cmd_issue_token_then_cmd_verify_token_roundtrip(capsys):
    rc = tool.cmd_issue_token(_Args(sub="user-42", secret="s3cr3t", claims=None, expires_in=300))
    token = capsys.readouterr().out.strip()
    assert rc == 0

    rc2 = tool.cmd_verify_token(_Args(token=token, secret="s3cr3t"))
    out = capsys.readouterr().out
    assert rc2 == 0
    payload = json.loads(out)
    assert payload["sub"] == "user-42"


def test_cmd_issue_token_merges_extra_claims(capsys):
    rc = tool.cmd_issue_token(
        _Args(sub="user-1", secret="s", claims=json.dumps({"role": "admin"}), expires_in=60)
    )
    token = capsys.readouterr().out.strip()
    assert rc == 0
    payload = tool.decode_jwt(token, "s")
    assert payload["role"] == "admin"
    assert payload["sub"] == "user-1"


def test_cmd_verify_token_invalid_prints_invalid_and_returns_1(capsys):
    rc = tool.cmd_verify_token(_Args(token="garbage-not-a-jwt", secret="s"))
    out = capsys.readouterr().out
    assert rc == 1
    assert out.startswith("INVALID:")


def test_cmd_check_claims_missing_prints_missing_and_returns_1(capsys):
    rc = tool.cmd_check_claims(_Args(payload=json.dumps({"sub": "u1"})))
    out = capsys.readouterr().out
    assert rc == 1
    assert "MISSING" in out
    assert "iat" in out and "exp" in out


def test_cmd_check_claims_ok_prints_ok_and_returns_0(capsys):
    rc = tool.cmd_check_claims(_Args(payload=json.dumps({"sub": "u1", "iat": 1, "exp": 2})))
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1


def test_main_dispatches_generate_secret_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "generate-secret", "--bytes", "8"])
    rc = tool.main()
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert len(out) == 16
    int(out, 16)


def test_main_dispatches_issue_and_verify_token_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "issue-token", "--sub", "u9", "--secret", "topsecret"])
    rc = tool.main()
    token = capsys.readouterr().out.strip()
    assert rc == 0

    monkeypatch.setattr(sys, "argv", ["tool.py", "verify-token", "--token", token, "--secret", "topsecret"])
    rc2 = tool.main()
    out = capsys.readouterr().out
    assert rc2 == 0
    assert '"sub": "u9"' in out


def test_main_dispatches_check_claims_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "check-claims", "--payload", json.dumps({"sub": "u1"})],
    )
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "MISSING" in out


# --- argparse required-flag enforcement: missing a required CLI arg must
# hard-fail (SystemExit via argparse), never silently proceed with None ---

import pytest


def test_main_issue_token_missing_sub_exits_with_error(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "issue-token", "--secret", "s"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_issue_token_missing_secret_exits_with_error(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "issue-token", "--sub", "u1"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_verify_token_missing_token_exits_with_error(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "verify-token", "--secret", "s"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_verify_token_missing_secret_exits_with_error(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "verify-token", "--token", "x.y.z"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_check_claims_missing_payload_exits_with_error(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-claims"])
    with pytest.raises(SystemExit):
        tool.main()


# --- entry point: verify the script actually works when run directly,
# not just when imported (this is how a real user invokes it) ---

import subprocess as _subprocess


def test_script_runs_as_main_entrypoint_via_subprocess():
    result = _subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "scripts" / "tool.py"),
         "generate-secret", "--bytes", "8"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    out = result.stdout.strip()
    assert len(out) == 16
    int(out, 16)
