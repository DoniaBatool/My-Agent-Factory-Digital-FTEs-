#!/usr/bin/env python3
"""
Edge Case Tester Tool - real boundary-value + date edge-case generation

Commands: boundary-values, date-edge-cases, build-matrix, test
"""
import argparse
import calendar
import datetime
import json
import sys

BOUNDARY_VALUES = {
    "int": [0, 1, -1, 2**31 - 1, -(2**31)],
    "string": ["", "a", "a" * 10000, "unicode-\U0001F600", " leading/trailing "],
    "float": [0.0, -0.0, 1e-10, 1e308, float("nan")],
    "list": [[], [None], list(range(10000))],
    "email": ["", "a@b.co", "not-an-email", "a" * 250 + "@example.com"],
}


def boundary_values_for_type(type_name: str):
    if type_name not in BOUNDARY_VALUES:
        raise ValueError(f"Unknown type '{type_name}'. Known: {sorted(BOUNDARY_VALUES)}")
    return BOUNDARY_VALUES[type_name]


def date_edge_cases(year: int = 2028):
    """Real calendar-aware edge cases: leap year Feb 29, month-end
    rollovers, year boundary. `year` should default to a real leap year
    (2028 is one) so this doesn't bit-rot into a non-leap year silently."""
    is_leap = calendar.isleap(year)
    cases = [
        {"name": "jan_31_plus_1_month", "date": datetime.date(year, 1, 31), "note": "Jan 31 + 1 month has no Feb 31"},
        {"name": "feb_29_leap_year", "date": datetime.date(year, 2, 29) if is_leap else None, "note": f"{year} is leap" if is_leap else f"{year} is not leap, no Feb 29"},
        {"name": "dec_31_year_boundary", "date": datetime.date(year, 12, 31), "note": "next day rolls into new year"},
        {"name": "feb_last_day_non_leap", "date": datetime.date(year + 1, 2, 28) if not calendar.isleap(year + 1) else datetime.date(year + 1, 2, 29), "note": f"last day of Feb in {year + 1}"},
    ]
    return cases


def add_months(d: datetime.date, months: int) -> datetime.date:
    """Calendar-correct month addition, clamped to the target month's last
    valid day (Jan 31 + 1 month -> Feb 28 or Feb 29, never a ValueError)."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(d.day, last_day))


def build_edge_case_matrix(fields):
    """fields: [{"name": str, "type": str}]. Returns a flat list of
    {field, type, edge_case, expected_status} rows -- the markdown table
    the skill's docs describe, but as real structured data."""
    rows = []
    for field in fields:
        try:
            values = boundary_values_for_type(field["type"])
        except ValueError:
            values = []
        for v in values:
            rows.append({"field": field["name"], "type": field["type"], "value": repr(v)})
    return rows


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_boundary_values(args):
    print(json.dumps([repr(v) for v in boundary_values_for_type(args.type)], indent=2))
    return 0


def cmd_date_edge_cases(args):
    cases = date_edge_cases(args.year)
    for c in cases:
        print(f"  {c['name']}: {c['date']} - {c['note']}")
    return 0


def cmd_build_matrix(args):
    fields = json.loads(args.fields)
    matrix = build_edge_case_matrix(fields)
    print(json.dumps(matrix, indent=2))
    return 0


def cmd_test(args):
    ok = 0 in boundary_values_for_type("int")
    ok = ok and "" in boundary_values_for_type("string")
    ok = ok and add_months(datetime.date(2028, 1, 31), 1) == datetime.date(2028, 2, 29)
    ok = ok and add_months(datetime.date(2027, 1, 31), 1) == datetime.date(2027, 2, 28)
    cases = date_edge_cases(2028)
    ok = ok and cases[1]["date"] == datetime.date(2028, 2, 29)
    matrix = build_edge_case_matrix([{"name": "age", "type": "int"}])
    ok = ok and len(matrix) == len(BOUNDARY_VALUES["int"])
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Edge Case Tester Tool")
    sub = parser.add_subparsers(dest="command")

    bv_p = sub.add_parser("boundary-values")
    bv_p.add_argument("type")

    date_p = sub.add_parser("date-edge-cases")
    date_p.add_argument("--year", type=int, default=2028)

    matrix_p = sub.add_parser("build-matrix")
    matrix_p.add_argument("--fields", required=True, help='JSON list of {"name","type"}')

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "boundary-values": cmd_boundary_values,
        "date-edge-cases": cmd_date_edge_cases,
        "build-matrix": cmd_build_matrix,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
