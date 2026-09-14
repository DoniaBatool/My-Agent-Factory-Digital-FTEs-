import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("user_isolation_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_has_ownership_filter_true_for_scoped_query():
    assert tool.has_ownership_filter("SELECT * FROM tasks WHERE user_id = :uid") is True


def test_has_ownership_filter_false_for_unscoped_query():
    assert tool.has_ownership_filter("SELECT * FROM tasks WHERE id = :id") is False


def test_has_ownership_filter_recognizes_owner_id_variant():
    assert tool.has_ownership_filter("DELETE FROM docs WHERE owner_id = ?") is True


def test_accepts_client_supplied_user_id_flags_request_json():
    assert tool.accepts_client_supplied_user_id("user_id = request.json['user_id']") is True


def test_accepts_client_supplied_user_id_false_for_server_derived_value():
    assert tool.accepts_client_supplied_user_id("user_id = current_user.id") is False


def test_build_scoped_query_includes_both_filters():
    q = tool.build_scoped_query("tasks")
    assert "id = :resource_id" in q
    assert "user_id = :current_user_id" in q


def test_scan_source_flags_unscoped_select():
    findings = tool.scan_source("result = db.execute('SELECT * FROM tasks WHERE id = :id')")
    assert any(f["issue"] == "missing ownership filter" for f in findings)


def test_scan_source_does_not_flag_scoped_select():
    findings = tool.scan_source("result = db.execute('SELECT * FROM tasks WHERE user_id = :uid')")
    assert findings == []


def test_scan_source_flags_client_supplied_user_id_red_flag():
    findings = tool.scan_source("user_id = request.json['user_id']\nfoo = 1")
    assert any(f["issue"] == "accepts client-supplied user_id as authority" for f in findings)
