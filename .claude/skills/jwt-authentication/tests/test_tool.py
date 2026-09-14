import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("jwt_authentication_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


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
