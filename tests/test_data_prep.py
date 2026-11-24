"""Unit tests for src/data_prep.py."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from data_prep import to_numeric_safe, parse_sheet, classify_label, derive_percent  # noqa: E402


def test_to_numeric_safe():
    assert to_numeric_safe("85") == 85.0
    assert to_numeric_safe("75.5") == 75.5
    assert to_numeric_safe("80%") == 80.0
    assert to_numeric_safe(None) is None
    assert to_numeric_safe("absent") is None
    assert to_numeric_safe("") is None
    assert to_numeric_safe("-") is None


def test_parse_sheet():
    assert parse_sheet("Grade 4 (Microsoft)") == ("Grade 4", "Microsoft")
    assert parse_sheet("KG (Panda)") == ("KG", "Panda")


def test_classify_label():
    subject, assessment, atype, kind, max_marks = classify_label("ELA Quiz")
    assert subject == "ELA"
    assert assessment == "ELA Quiz"
    assert atype == "Other Assessment"
    assert kind == "quiz"
    assert max_marks is None

    subject, _, atype, kind, _ = classify_label("Diagnostic")
    assert subject == "Other/Unspecified"
    assert atype == "Diagnostic"

    subject, assessment, atype, kind, max_marks = classify_label("Math Unit Test | given marks (20/20)")
    assert subject == "Math"
    assert assessment == "Math Unit Test"
    assert atype == "Unit/Chapter/Module"
    assert kind == "score"
    assert max_marks == 20.0


def test_derive_percent():
    assert derive_percent({"value_num": 85.0, "measure_kind": "score", "max_marks": 100}) == pytest.approx(85.0)
    assert derive_percent({"value_num": 0.85, "measure_kind": "percentage"}) == pytest.approx(85.0)
    assert derive_percent({"value_num": 90, "measure_kind": "score", "max_marks": None}) is None
    assert derive_percent({"value_num": None}) is None
