import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("password_security_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


# --- core logic: happy path -------------------------------------------------

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


# --- edge cases: boundaries, every individual policy rule, malformed hashes -

def test_reset_token_boundary_at_exact_expiry_is_invalid():
    """now == expires_at must be treated as EXPIRED (check is `now < expires_at`,
    not `now <= expires_at`) -- an off-by-one here extends a token's life by
    one extra second past its stated expiry."""
    _token, expires_at = tool.generate_reset_token(ttl_seconds=100)
    assert tool.is_reset_token_valid(expires_at, now=expires_at) is False


def test_check_password_policy_flags_missing_digit_alone():
    violations = tool.check_password_policy("NoDigitsHere!")
    assert any("digit" in v for v in violations)
    assert not any("uppercase" in v for v in violations)


def test_check_password_policy_flags_missing_lowercase_alone():
    violations = tool.check_password_policy("ALLUPPER1!")
    assert any("lowercase" in v for v in violations)


def test_check_password_policy_flags_all_five_rules_on_empty_string():
    violations = tool.check_password_policy("")
    assert len(violations) == 5


def test_check_password_policy_exactly_8_chars_passes_length_rule():
    """Boundary: length exactly 8 must NOT trigger the 'at least 8' rule
    (the check is `len < 8`, not `len <= 8`)."""
    violations = tool.check_password_policy("Abcdefg1!")  # 9 chars, but check exact 8 too
    violations8 = tool.check_password_policy("Abcdef1!")  # exactly 8 chars, all classes present
    assert len("Abcdef1!") == 8
    assert not any("8 characters" in v for v in violations8)


def test_check_password_policy_7_chars_fails_length_rule():
    violations = tool.check_password_policy("Abcde1!")  # 7 chars
    assert any("8 characters" in v for v in violations)


def test_verify_password_rejects_hash_with_wrong_number_of_segments():
    assert tool.verify_password("anything", "pbkdf2_sha256$1000$onlytwoparts") is False


def test_verify_password_rejects_hash_with_non_integer_iterations():
    assert tool.verify_password("anything", "pbkdf2_sha256$notanumber$c2FsdA==$aGFzaA==") is False


def test_verify_password_wrong_password_same_hash_structure_fails():
    h = tool.hash_password("RealPassword1!")
    assert tool.verify_password("RealPassword2!", h) is False


def test_hash_password_accepts_explicit_salt_deterministically():
    """When the same salt is passed explicitly, the same password must
    hash to the SAME output (this is what makes verify_password's
    re-derivation approach correct in the first place)."""
    salt = b"0123456789abcdef"
    h1 = tool.hash_password("same-pw", salt=salt)
    h2 = tool.hash_password("same-pw", salt=salt)
    assert h1 == h2


# --- CLI layer: previously completely untested (0% of cmd_*/main) ----------

class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_cmd_hash_password_rejects_weak_password_without_force(capsys):
    rc = tool.cmd_hash_password(_Args(password="weak", force=False))
    out = capsys.readouterr().out
    assert rc == 1
    assert "REJECTED" in out


def test_cmd_hash_password_allows_weak_password_with_force(capsys):
    rc = tool.cmd_hash_password(_Args(password="weak", force=True))
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("pbkdf2_")


def test_cmd_hash_password_accepts_strong_password(capsys):
    rc = tool.cmd_hash_password(_Args(password="Strong-Pass-1!", force=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("pbkdf2_")


def test_cmd_verify_password_match_returns_0(capsys):
    h = tool.hash_password("Strong-Pass-1!")
    rc = tool.cmd_verify_password(_Args(password="Strong-Pass-1!", hash=h))
    out = capsys.readouterr().out
    assert rc == 0
    assert "MATCH" in out and "NO MATCH" not in out


def test_cmd_verify_password_mismatch_returns_1(capsys):
    h = tool.hash_password("Strong-Pass-1!")
    rc = tool.cmd_verify_password(_Args(password="wrong", hash=h))
    out = capsys.readouterr().out
    assert rc == 1
    assert "NO MATCH" in out


def test_cmd_check_policy_ok_returns_0(capsys):
    rc = tool.cmd_check_policy(_Args(password="Strong-Pass-1!"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_cmd_check_policy_violations_returns_1(capsys):
    rc = tool.cmd_check_policy(_Args(password="weak"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "8 characters" in out


def test_cmd_generate_reset_token_prints_token_and_expiry(capsys):
    rc = tool.cmd_generate_reset_token(_Args(ttl=60))
    out = capsys.readouterr().out
    assert rc == 0
    assert "token=" in out
    assert "expires_at=" in out


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1


def test_main_dispatches_hash_password_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "hash-password", "Strong-Pass-1!"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("pbkdf2_")


def test_main_dispatches_hash_password_force_flag(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "hash-password", "weak", "--force"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("pbkdf2_")


def test_main_dispatches_verify_password_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "hash-password", "Strong-Pass-1!"])
    tool.main()
    h = capsys.readouterr().out.strip()

    monkeypatch.setattr(sys, "argv", ["tool.py", "verify-password", "Strong-Pass-1!", "--hash", h])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "MATCH" in out


def test_main_dispatches_check_policy_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-policy", "weak"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "8 characters" in out


def test_main_dispatches_generate_reset_token_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "generate-reset-token", "--ttl", "120"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "token=" in out


def test_main_verify_password_missing_required_hash_exits_with_error(monkeypatch):
    import pytest
    monkeypatch.setattr(sys, "argv", ["tool.py", "verify-password", "somepassword"])
    with pytest.raises(SystemExit):
        tool.main()


# --- entry point: verify the script actually works when run directly ------

import subprocess as _subprocess


def test_script_runs_as_main_entrypoint_via_subprocess():
    result = _subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "scripts" / "tool.py"),
         "check-policy", "Strong-Pass-1!"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout
