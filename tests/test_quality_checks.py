"""Unit tests for src/quality_checks.py."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quality_checks import run_quality_checks  # noqa: E402


def _records():
    return pd.DataFrame([
        {"student_name": "Alice", "sheet": "Grade 1 (Koala)", "value": "85", "percent": 85.0, "value_num": 85.0},
        {"student_name": "Bob", "sheet": "Grade 1 (Koala)", "value": "", "percent": None, "value_num": None},
        {"student_name": "", "sheet": "Grade 1 (Koala)", "value": "75", "percent": 75.0, "value_num": 75.0},
    ])


def _students():
    return pd.DataFrame([
        {"sheet": "Grade 1 (Koala)", "student_name": "Alice"},
        {"sheet": "Grade 1 (Koala)", "student_name": "Alice"},
        {"sheet": "Grade 1 (Koala)", "student_name": "Bob"},
    ])


def test_run_quality_checks_counts():
    summary = run_quality_checks(_records(), _students())
    checks = {issue["check"]: issue for issue in summary["issues"]}
    assert checks["missing_student_name"]["count"] == 1
    assert "missing_sheet" not in checks
    assert checks["duplicate_student_rows_in_sheet"]["count"] == 2
    assert "percent_out_of_range_0_100" not in checks


def test_run_quality_checks_summary():
    summary = run_quality_checks(_records(), _students())
    assert summary["total_records"] == 3
    assert summary["records_missing_value"] == 1
