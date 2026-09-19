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
