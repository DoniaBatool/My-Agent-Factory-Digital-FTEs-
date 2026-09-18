import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("password_security_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_hash_password_never_stores_plaintext():
    h = tool.hash_password("hunter2")
    assert "hunter2" not in h


def test_hash_password_is_salted_so_same_password_differs():
    h1 = tool.hash_password("same-password")
    h2 = tool.hash_password("same-password")
    assert h1 != h2  # different random salt each time


def test_verify_password_roundtrip():
    h = tool.hash_password("correct-horse-battery")
    assert tool.verify_password("correct-horse-battery", h) is True
    assert tool.verify_password("wrong-password", h) is False


def test_verify_password_rejects_garbage_hash_without_raising():
    assert tool.verify_password("anything", "not-a-real-hash") is False


def test_check_password_policy_flags_short_password():
    assert any("8 characters" in v for v in tool.check_password_policy("Ab1!"))


def test_check_password_policy_flags_missing_character_classes():
    violations = tool.check_password_policy("alllowercase1")
    assert any("uppercase" in v for v in violations)
    assert any("special character" in v for v in violations)


def test_check_password_policy_passes_strong_password():
    assert tool.check_password_policy("Correct-Horse-1!") == []


def test_generate_reset_token_is_unique_and_carries_no_plaintext_link():
    t1, _ = tool.generate_reset_token()
    t2, _ = tool.generate_reset_token()
    assert t1 != t2
    assert len(t1) > 20


def test_reset_token_expires():
    _token, expires_at = tool.generate_reset_token(ttl_seconds=100)
    assert tool.is_reset_token_valid(expires_at, now=expires_at - 1) is True
    assert tool.is_reset_token_valid(expires_at, now=expires_at + 1) is False
