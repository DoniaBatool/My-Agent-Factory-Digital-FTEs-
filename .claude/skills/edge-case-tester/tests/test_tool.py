import datetime
import sys
from pathlib import Path

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("edge_case_tester_tool", Path(__file__).resolve().parent.parent / "scripts" / "tool.py")
tool = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(tool)  # unique module name avoids cross-skill "tool" collisions in combined pytest runs


def test_boundary_values_for_int_includes_zero_and_extremes():
    values = tool.boundary_values_for_type("int")
    assert 0 in values and -1 in values


def test_boundary_values_unknown_type_raises():
    try:
        tool.boundary_values_for_type("bogus")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_date_edge_cases_feb_29_present_on_leap_year():
    cases = tool.date_edge_cases(2028)
    feb29 = next(c for c in cases if c["name"] == "feb_29_leap_year")
    assert feb29["date"] == datetime.date(2028, 2, 29)


def test_date_edge_cases_feb_29_none_on_non_leap_year():
    cases = tool.date_edge_cases(2027)
    feb29 = next(c for c in cases if c["name"] == "feb_29_leap_year")
    assert feb29["date"] is None


def test_add_months_handles_jan_31_into_leap_feb():
    assert tool.add_months(datetime.date(2028, 1, 31), 1) == datetime.date(2028, 2, 29)


def test_add_months_handles_jan_31_into_non_leap_feb():
    assert tool.add_months(datetime.date(2027, 1, 31), 1) == datetime.date(2027, 2, 28)


def test_add_months_never_raises_valueerror_for_month_end_rollover():
    d = datetime.date(2026, 1, 31)
    for i in range(1, 13):
        tool.add_months(d, i)  # must not raise


def test_build_edge_case_matrix_produces_one_row_per_boundary_value():
    matrix = tool.build_edge_case_matrix([{"name": "age", "type": "int"}])
    assert len(matrix) == len(tool.BOUNDARY_VALUES["int"])
    assert all(row["field"] == "age" for row in matrix)


def test_build_edge_case_matrix_skips_unknown_type_gracefully():
    matrix = tool.build_edge_case_matrix([{"name": "x", "type": "bogus"}])
    assert matrix == []

# --- edge cases + CLI layer (added for bulletproofing pass) ---
import json as _json
import subprocess


class _Args:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_date_edge_cases_feb_last_day_non_leap_case():
    # year=2028 -> year+1=2029 is not leap, so feb_last_day_non_leap should be Feb 28, 2029
    cases = tool.date_edge_cases(2028)
    last_day = next(c for c in cases if c["name"] == "feb_last_day_non_leap")
    assert last_day["date"] == datetime.date(2029, 2, 28)


def test_date_edge_cases_feb_last_day_leap_case():
    # year=2027 -> year+1=2028 IS leap, so feb_last_day_non_leap should be Feb 29, 2028
    cases = tool.date_edge_cases(2027)
    last_day = next(c for c in cases if c["name"] == "feb_last_day_non_leap")
    assert last_day["date"] == datetime.date(2028, 2, 29)


def test_date_edge_cases_default_year_is_2028():
    cases = tool.date_edge_cases()
    jan31 = next(c for c in cases if c["name"] == "jan_31_plus_1_month")
    assert jan31["date"] == datetime.date(2028, 1, 31)


def test_boundary_values_string_includes_empty_and_unicode():
    values = tool.boundary_values_for_type("string")
    assert "" in values
    assert any("\U0001F600" in v for v in values)


def test_boundary_values_float_includes_nan():
    values = tool.boundary_values_for_type("float")
    assert any(v != v for v in values)  # nan != nan


def test_build_edge_case_matrix_multiple_fields_accumulates_rows():
    matrix = tool.build_edge_case_matrix([
        {"name": "age", "type": "int"},
        {"name": "email", "type": "email"},
    ])
    assert len(matrix) == len(tool.BOUNDARY_VALUES["int"]) + len(tool.BOUNDARY_VALUES["email"])
    assert {row["field"] for row in matrix} == {"age", "email"}


def test_build_edge_case_matrix_empty_fields_returns_empty_list():
    assert tool.build_edge_case_matrix([]) == []


def test_cmd_boundary_values_prints_json_list_and_returns_0(capsys):
    args = _Args(type="int")
    rc = tool.cmd_boundary_values(args)
    out = capsys.readouterr().out
    assert rc == 0
    parsed = _json.loads(out)
    assert "0" in parsed


def test_cmd_boundary_values_unknown_type_propagates_valueerror():
    args = _Args(type="bogus")
    try:
        tool.cmd_boundary_values(args)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_cmd_date_edge_cases_prints_each_case_and_returns_0(capsys):
    args = _Args(year=2028)
    rc = tool.cmd_date_edge_cases(args)
    out = capsys.readouterr().out
    assert rc == 0
    assert "feb_29_leap_year" in out
    assert "jan_31_plus_1_month" in out


def test_cmd_build_matrix_parses_json_fields_and_prints_matrix(capsys):
    args = _Args(fields=_json.dumps([{"name": "age", "type": "int"}]))
    rc = tool.cmd_build_matrix(args)
    out = capsys.readouterr().out
    assert rc == 0
    parsed = _json.loads(out)
    assert len(parsed) == len(tool.BOUNDARY_VALUES["int"])


def test_cmd_build_matrix_malformed_json_raises():
    args = _Args(fields="not-json{{{")
    try:
        tool.cmd_build_matrix(args)
        assert False, "expected a JSON decode error"
    except _json.JSONDecodeError:
        pass


def test_cmd_test_self_test_passes(capsys):
    rc = tool.cmd_test(_Args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_no_command_prints_help_and_returns_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "usage" in out.lower()


def test_main_boundary_values_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "boundary-values", "string"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    parsed = _json.loads(out)
    assert "''" in parsed


def test_main_date_edge_cases_end_to_end_with_year_flag(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "date-edge-cases", "--year", "2000"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "2000-02-29" in out  # 2000 is a leap year (divisible by 400)


def test_main_build_matrix_end_to_end(monkeypatch, capsys):
    fields = _json.dumps([{"name": "age", "type": "int"}])
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-matrix", "--fields", fields])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    parsed = _json.loads(out)
    assert len(parsed) == len(tool.BOUNDARY_VALUES["int"])


def test_main_test_command_end_to_end(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["tool.py", "test"])
    rc = tool.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "SELF-TEST PASS" in out


def test_main_build_matrix_missing_required_fields_flag_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "build-matrix"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing required --fields"
    except SystemExit as e:
        assert e.code == 2


def test_main_boundary_values_missing_positional_raises_systemexit(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["tool.py", "boundary-values"])
    try:
        tool.main()
        assert False, "expected SystemExit for missing positional type"
    except SystemExit as e:
        assert e.code == 2


def test_subprocess_runs_as_script_and_exercises_main_guard():
    script = Path(__file__).resolve().parent.parent / "scripts" / "tool.py"
    result = subprocess.run(
        [sys.executable, str(script), "boundary-values", "int"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "0" in result.stdout
