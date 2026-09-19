import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("security_engineer_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_scan_secrets_finds_aws_key():
    findings = tool.scan_secrets("aws_key = 'AKIAABCDEFGHIJKLMNOP'")
    assert any(f["category"] == "aws_access_key" for f in findings)


def test_scan_secrets_finds_private_key_block():
    findings = tool.scan_secrets("-----BEGIN RSA PRIVATE KEY-----\nMIIB...\n")
    assert any(f["category"] == "private_key_block" for f in findings)


def test_scan_secrets_masks_the_actual_secret_value():
    findings = tool.scan_secrets('password = "supersecret123"')
    assert all("supersecret123" not in f["match"] for f in findings)


def test_scan_secrets_clean_text_has_no_findings():
    assert tool.scan_secrets("x = 1\ny = compute(x)\n") == []


def test_scan_secrets_reports_correct_line_number():
    findings = tool.scan_secrets("a = 1\nb = 2\npassword = \"abcd1234\"\n")
    assert findings[0]["line"] == 3


def test_check_headers_flags_all_missing():
    assert set(tool.check_headers({})) == set(tool.REQUIRED_SECURITY_HEADERS)


def test_check_headers_case_insensitive_match():
    headers = {h.lower(): "x" for h in tool.REQUIRED_SECURITY_HEADERS}
    assert tool.check_headers(headers) == []


def test_build_threat_model_pairs_matching_entry_and_asset():
    threats = tool.build_threat_model(["user auth tokens"], ["/api/login"])
    assert any("Authentication bypass" in t["threat"] for t in threats)


def test_owasp_top10_has_ten_categories():
    assert len(tool.OWASP_TOP10_2021) == 10

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json
import re
import subprocess as _subprocess
import pytest


class _Args:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# --- scan_secrets edge cases --------------------------------------------------

def test_scan_secrets_masks_exact_six_char_match_with_asterisks(monkeypatch):
    # len(snippet) > 6 is the masking condition -- a match of exactly 6
    # chars must fall into the "***" branch, not the truncate-and-append one.
    monkeypatch.setattr(tool, "SECRET_PATTERNS", {"short6": re.compile(r"ABCDEF")})
    findings = tool.scan_secrets("ABCDEF")
    assert findings[0]["match"] == "***"


def test_scan_secrets_masks_seven_char_match_with_truncation(monkeypatch):
    monkeypatch.setattr(tool, "SECRET_PATTERNS", {"short7": re.compile(r"ABCDEFG")})
    findings = tool.scan_secrets("ABCDEFG")
    assert findings[0]["match"] == "ABCDEF..."


def test_scan_secrets_multiple_categories_on_same_line():
    findings = tool.scan_secrets('aws_key = "AKIAABCDEFGHIJKLMNOP" password = "abcd1234"')
    categories = {f["category"] for f in findings}
    assert {"aws_access_key", "hardcoded_password"} <= categories


def test_scan_secrets_tracks_line_numbers_for_multiple_occurrences():
    text = 'x = 1\npassword = "abcd1234"\ny = 2\npassword = "efgh5678"\n'
    findings = tool.scan_secrets(text)
    lines = sorted(f["line"] for f in findings if f["category"] == "hardcoded_password")
    assert lines == [2, 4]


# --- check_headers edge cases --------------------------------------------------

def test_check_headers_partial_missing():
    headers = {"Strict-Transport-Security": "x", "X-Content-Type-Options": "x"}
    missing = tool.check_headers(headers)
    assert set(missing) == {"X-Frame-Options", "Content-Security-Policy"}


# --- build_threat_model edge cases ---------------------------------------------

def test_build_threat_model_matches_via_entry_point_keyword_alone():
    # the asset name itself contains none of the generic-threat keywords;
    # only the entry point does, so this must still produce a match.
    threats = tool.build_threat_model(["some resource"], ["/auth/callback"])
    assert any(t["threat"] == "Authentication bypass / credential stuffing" for t in threats)


def test_build_threat_model_no_keyword_match_returns_empty_list():
    assert tool.build_threat_model(["widget"], ["/home"]) == []


# --- CLI layer: cmd_* functions -------------------------------------------------

def test_cmd_scan_secrets_returns_0_for_clean_file(tmp_path, capsys):
    f = tmp_path / "clean.py"
    f.write_text("x = 1\n")
    rc = tool.cmd_scan_secrets(_Args(path=str(f)))
    assert rc == 0
    assert "OK: no likely secrets found" in capsys.readouterr().out


def test_cmd_scan_secrets_returns_1_and_lists_findings(tmp_path, capsys):
    f = tmp_path / "dirty.py"
    f.write_text('password = "abcd1234"\n')
    rc = tool.cmd_scan_secrets(_Args(path=str(f)))
    assert rc == 1
    assert "hardcoded_password" in capsys.readouterr().out


def test_cmd_check_headers_all_present_returns_0(capsys):
    headers_json = json.dumps({h: "x" for h in tool.REQUIRED_SECURITY_HEADERS})
    rc = tool.cmd_check_headers(_Args(headers=headers_json))
    assert rc == 0
    assert "OK: all required security headers present" in capsys.readouterr().out


def test_cmd_check_headers_missing_returns_1(capsys):
    rc = tool.cmd_check_headers(_Args(headers="{}"))
    assert rc == 1
    out = capsys.readouterr().out
    assert "MISSING:" in out
    assert "Strict-Transport-Security" in out


def test_cmd_check_headers_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        tool.cmd_check_headers(_Args(headers="not json"))


def test_cmd_threat_model_splits_comma_separated_args(capsys):
    rc = tool.cmd_threat_model(_Args(assets="user tokens,widget", entry_points="/api/login,/home"))
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert any(t["asset"] == "user tokens" for t in data)


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_cmd_test_reports_fail_when_scan_secrets_broken(monkeypatch, capsys):
    monkeypatch.setattr(tool, "scan_secrets", lambda text: [])
    rc = tool.cmd_test(_Args())
    assert rc == 1
    assert "SELF-TEST FAIL" in capsys.readouterr().out


# --- main(): required-arg enforcement ------------------------------------------

def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_main_scan_secrets_requires_path_positional(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "scan-secrets"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_check_headers_requires_headers_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-headers"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_threat_model_requires_assets_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "threat-model", "--entry-points", "/x"])
    with pytest.raises(SystemExit):
        tool.main()


def test_main_threat_model_requires_entry_points_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "threat-model", "--assets", "x"])
    with pytest.raises(SystemExit):
        tool.main()


# --- main(): end-to-end dispatch ------------------------------------------------

def test_main_scan_secrets_end_to_end(monkeypatch, tmp_path, capsys):
    f = tmp_path / "clean.py"
    f.write_text("x = 1\n")
    monkeypatch.setattr(sys, "argv", ["tool.py", "scan-secrets", str(f)])
    rc = tool.main()
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_main_check_headers_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-headers", "--headers", "{}"])
    rc = tool.main()
    assert rc == 1
    assert "MISSING" in capsys.readouterr().out


def test_main_threat_model_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "threat-model", "--assets", "user tokens", "--entry-points", "/api/auth"])
    rc = tool.main()
    assert rc == 0
    assert "Authentication bypass" in capsys.readouterr().out


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    assert rc == 0
    assert "SELF-TEST PASS" in capsys.readouterr().out


def test_script_runs_as_main_via_subprocess(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("x = 1\n")
    script = str(Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
    result = _subprocess.run(
        [sys.executable, script, "scan-secrets", str(f)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout
