import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("user_isolation_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


# --- core logic: happy path (existing baseline, unchanged) ------------------

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


# --- edge cases: the other owner-column variants, word-boundary correctness,
# multi-statement scans, and the CLI's client-supplied-id detector variants --

def test_has_ownership_filter_recognizes_account_id_variant():
    assert tool.has_ownership_filter("SELECT * FROM invoices WHERE account_id = :aid") is True


def test_has_ownership_filter_recognizes_created_by_variant():
    assert tool.has_ownership_filter("SELECT * FROM notes WHERE created_by = :uid") is True


def test_has_ownership_filter_word_boundary_rejects_substring_match():
    """A column named `power_user_id` must NOT be mistaken for `user_id` --
    the check uses \\b word-boundary matching, not a bare substring search,
    which matters because a naive substring check would produce a false
    'this query is scoped' positive on an unrelated column name."""
    assert tool.has_ownership_filter("SELECT * FROM t WHERE power_user_id = :x") is False


def test_has_ownership_filter_is_case_insensitive():
    assert tool.has_ownership_filter("SELECT * FROM t WHERE USER_ID = :uid") is True


def test_accepts_client_supplied_user_id_flags_params_get():
    assert tool.accepts_client_supplied_user_id("user_id = params.get('user_id')") is True


def test_accepts_client_supplied_user_id_flags_args_variant():
    assert tool.accepts_client_supplied_user_id("user_id = args.user_id") is True


def test_accepts_client_supplied_user_id_flags_body_variant():
    assert tool.accepts_client_supplied_user_id("user_id = body.user_id") is True


def test_accepts_client_supplied_user_id_flags_payload_bracket_variant():
    assert tool.accepts_client_supplied_user_id("user_id = payload['user_id']") is True


def test_accepts_client_supplied_user_id_false_for_unrelated_code():
    assert tool.accepts_client_supplied_user_id("total = sum(values)") is False


def test_build_scoped_query_respects_custom_columns():
    q = tool.build_scoped_query("invoices", id_column="invoice_id", owner_column="account_id")
    assert "invoice_id = :resource_id" in q
    assert "account_id = :current_user_id" in q


def test_scan_source_flags_multiple_unscoped_statements():
    code = (
        "a = db.execute('SELECT * FROM tasks WHERE id = :id')\n"
        "b = db.execute('UPDATE tasks SET done = 1 WHERE id = :id')\n"
    )
    findings = tool.scan_source(code)
    issues = [f["issue"] for f in findings]
    assert issues.count("missing ownership filter") == 2


def test_scan_source_flags_delete_without_ownership_filter():
    findings = tool.scan_source("db.execute('DELETE FROM tasks WHERE id = :id')")
    assert any(f["issue"] == "missing ownership filter" for f in findings)


def test_scan_source_returns_empty_list_for_code_with_no_sql_and_no_red_flags():
    findings = tool.scan_source("x = 1 + 1\nprint(x)")
    assert findings == []


def test_scan_source_statement_text_is_truncated_to_120_chars():
    long_stmt = "SELECT * FROM tasks WHERE id = :id AND " + "x" * 200
    findings = tool.scan_source(long_stmt)
    missing = [f for f in findings if f["issue"] == "missing ownership filter"]
    assert missing
    assert len(missing[0]["statement"]) <= 120


def test_scan_source_client_supplied_finding_has_none_statement():
    findings = tool.scan_source("user_id = request.json['user_id']")
    red_flag = [f for f in findings if f["issue"] == "accepts client-supplied user_id as authority"]
    assert red_flag
    assert red_flag[0]["statement"] is None


# --- CLI layer: previously completely untested (0% of cmd_*/main) ----------

class _Args:
    """Minimal stand-in for an argparse.Namespace."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_cmd_check_query_scoped_prints_ok_and_returns_0(capsys):
    rc = tool.cmd_check_query(_Args(sql="SELECT * FROM tasks WHERE user_id = :uid"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_cmd_check_query_unscoped_prints_fail_and_returns_1(capsys):
    rc = tool.cmd_check_query(_Args(sql="SELECT * FROM tasks WHERE id = :id"))
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAIL" in out


def test_cmd_scaffold_query_prints_scoped_query(capsys):
    rc = tool.cmd_scaffold_query(_Args(table="tasks", id_column="id", owner_column="user_id"))
    out = capsys.readouterr().out
    assert rc == 0
    assert "FROM tasks" in out
    assert "user_id = :current_user_id" in out


def test_cmd_scan_file_ok_when_no_issues(tmp_path, capsys):
    f = tmp_path / "clean.py"
    f.write_text("db.execute('SELECT * FROM tasks WHERE user_id = :uid')")
    rc = tool.cmd_scan_file(_Args(path=str(f)))
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_cmd_scan_file_reports_issues_and_returns_1(tmp_path, capsys):
    f = tmp_path / "leaky.py"
    f.write_text("db.execute('SELECT * FROM tasks WHERE id = :id')")
    rc = tool.cmd_scan_file(_Args(path=str(f)))
    out = capsys.readouterr().out
    assert rc == 1
    assert "missing ownership filter" in out


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_with_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    assert rc == 1


def test_main_dispatches_check_query_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-query", "SELECT * FROM t WHERE user_id = :uid"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "OK" in out


def test_main_dispatches_scaffold_query_with_default_columns(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "scaffold-query", "tasks"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "FROM tasks" in out
    assert "user_id = :current_user_id" in out


def test_main_dispatches_scaffold_query_with_custom_columns(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv",
        ["tool.py", "scaffold-query", "invoices", "--id-column", "invoice_id", "--owner-column", "account_id"],
    )
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "invoice_id = :resource_id" in out
    assert "account_id = :current_user_id" in out


def test_main_dispatches_scan_file_end_to_end(monkeypatch, tmp_path, capsys):
    f = tmp_path / "leaky.py"
    f.write_text("db.execute('SELECT * FROM tasks WHERE id = :id')")
    monkeypatch.setattr(sys, "argv", ["tool.py", "scan-file", str(f)])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "missing ownership filter" in out


def test_main_dispatches_test_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_check_query_missing_required_sql_exits_with_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "check-query"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required positional 'sql'"
    except SystemExit as e:
        assert e.code != 0


def test_main_scaffold_query_missing_required_table_exits_with_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "scaffold-query"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required positional 'table'"
    except SystemExit as e:
        assert e.code != 0


def test_main_scan_file_missing_required_path_exits_with_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "scan-file"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required positional 'path'"
    except SystemExit as e:
        assert e.code != 0


def test_script_runs_as_main_entrypoint_via_subprocess():
    import subprocess
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(script), "check-query", "SELECT * FROM t WHERE user_id = :uid"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout
