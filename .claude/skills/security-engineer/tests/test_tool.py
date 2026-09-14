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
