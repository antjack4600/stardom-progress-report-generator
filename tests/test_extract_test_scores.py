"""Unit tests for src/extract_test_scores.py."""

import sys
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import extract_test_scores as ets  # noqa: E402


def _make_xlsx(path, sheet_name="Test Sheet"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws["A1"] = "1"
    ws["B1"] = "Alice"
    ws["A2"] = "2"
    ws["B2"] = "Bob"
    wb.save(path)


def test_read_xlsx_sheets_returns_rows(tmp_path):
    xlsx = tmp_path / "in.xlsx"
    _make_xlsx(xlsx)
    data = ets.read_xlsx_sheets(xlsx)
    assert "Test Sheet" in data
    rows = data["Test Sheet"]
    assert len(rows) == 2
    assert rows[0]["A"] == "1"
    assert rows[0]["B"] == "Alice"


def test_extract_sheet_returns_records_and_labels():
    rows = [
        {"A": "1", "B": "Student Name", "C": "Test"},
        {"A": "1", "B": "Alice", "C": "85"},
    ]
    records, labels = ets.extract_sheet("Test Sheet", rows)
    assert records
    rec0 = records[0]
    assert rec0["sheet"] == "Test Sheet"
    assert rec0["student_no"] == 1
    assert rec0["student_name"] == "Alice"
    assert rec0["column"] == "C"
    assert rec0["assessment_label"] == "Test"
    assert rec0["value"] == "85"
    assert "B" in labels
