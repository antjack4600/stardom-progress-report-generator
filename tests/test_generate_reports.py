"""Unit tests for src/generate_reports.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_reports import safe_name  # noqa: E402


def test_safe_name():
    assert safe_name("Alice") == "Alice"
    assert safe_name("a b") == "a_b"
    assert safe_name("x/y:z") == "x_y_z"
    assert safe_name("Alice<45") == "Alice_45"


def test_safe_name_blocks_path_escapes():
    # No leading/trailing dots, no '..' runs, no separators left behind.
    assert not safe_name("..").startswith(".")
    assert not safe_name("../etc/passwd").startswith(".")
    assert "/" not in safe_name("../../etc/passwd")
    assert safe_name("..") == "_"
    assert safe_name("") == "_"
