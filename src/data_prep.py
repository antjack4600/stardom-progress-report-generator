"""Prepare dashboard-ready datasets from extracted Stardom test score data.

Reads `data/processed/test_scores_long.csv` (and students.csv) produced by
`src/extract_test_scores.py`, enriches records with parsed grade/class, subject,
assessment metadata, and derived percentages, then writes consolidated datasets
used by the Streamlit dashboard.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd


def to_numeric_safe(value):
    """Convert a value to float when possible; return None for blanks/NA markers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().replace("%", "")
    if s == "" or s.lower() in {"na", "n/a", "absent", "ab", "-", "none"}:
        return None
    try:
        return float(s)
    except Exception:
        return None


def parse_sheet(sheet: str):
    """Parse class sheet name like 'Grade 4 (Microsoft)' into grade and section."""
    if sheet is None or (isinstance(sheet, float) and pd.isna(sheet)):
        return "", ""
    s = str(sheet).strip()
    m = re.match(r"^(.*?)(?:\s*\(([^)]+)\))?\s*$", s)
    grade = (m.group(1) or s).strip() if m else s
    section = (m.group(2) or "").strip() if m else ""
    # normalize KG
    if grade.upper().startswith("KG") or "KG" in grade.upper():
        if "KG" not in grade:
            grade = "KG"
    return grade, section


def classify_label(label):
    """Classify an assessment column label into subject, assessment, measure kind, max marks."""
    if label is None or (isinstance(label, float) and pd.isna(label)):
        label = ""
    label = str(label)
    l = label.lower()

    subject = "Other/Unspecified"
    for key, name in [
        ("ela", "ELA"),
        ("math", "Math"),
        ("science", "Science"),
        ("social", "Social Studies"),
    ]:
        if key in l:
            subject = name
            break

    m = re.search(r"given marks[^\d]*\(?\s*(\d+(?:\.\d+)?)\s*\)?", l)
    max_marks = float(m.group(1)) if m else None

    kind = "score"
    if "percentage" in l or "marks by" in l:
        kind = "percentage"
    elif "quizz" in l or "quiz" in l:
        kind = "quiz"
    elif "project" in l or "presentation" in l:
        kind = "project"

    # assessment name: first segment before pipe, or cleaned label
    assessment = label.split("|")[0].strip() if label else ""
    assessment = re.sub(r"\s+", " ", assessment)

    # assessment type heuristic
    al = assessment.lower()
    if "diagnostic" in al:
        atype = "Diagnostic"
    elif "benchmark" in al or "mid year" in al or "mid-year" in al or "end of year" in al:
        atype = "Benchmark/Mid/End"
    elif "unit" in al or "chapter" in al or "module" in al:
        atype = "Unit/Chapter/Module"
    elif assessment:
        atype = "Other Assessment"
    else:
        atype = "Unspecified"

    return subject, assessment, atype, kind, max_marks


def derive_percent(row):
    """Derive a 0-100 percentage from a record when possible."""
    v = row.get("value_num")
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    kind = row.get("measure_kind", "")
    max_marks = row.get("max_marks")
    if kind == "percentage":
        return v * 100 if v <= 1.0 else v
    if pd.notna(max_marks) and max_marks and float(max_marks) > 0:
        return (float(v) / float(max_marks)) * 100
    if 0 <= float(v) <= 1.0:
        return float(v) * 100
    return None


def prepare(long_path: Path, students_path: Path, out_dir: Path):
    """Build enriched dashboard datasets."""
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(long_path)
    students = pd.read_csv(students_path)

    grades, sections = zip(*df["sheet"].map(parse_sheet)) if len(df) else ([], [])
    df["grade"] = list(grades)
    df["class_section"] = list(sections)
    df["class_label"] = df.apply(
        lambda r: f"{r['grade']} ({r['class_section']})" if str(r.get('class_section','')).strip() else str(r.get('grade','')),
        axis=1,
    )

    meta = df["assessment_label"].apply(classify_label)
    df["subject"] = meta.apply(lambda x: x[0])
    df["assessment"] = meta.apply(lambda x: x[1])
    df["assessment_type"] = meta.apply(lambda x: x[2])
    df["measure_kind"] = meta.apply(lambda x: x[3])
    df["max_marks"] = meta.apply(lambda x: x[4])
    df["value_num"] = df["value"].apply(to_numeric_safe)
    df["percent"] = df.apply(derive_percent, axis=1)

    # students enriched
    sg, ss = zip(*students["sheet"].map(parse_sheet)) if len(students) else ([], [])
    students = students.copy()
    students["grade"] = list(sg)
    students["class_section"] = list(ss)
    students["class_label"] = students.apply(
        lambda r: f"{r['grade']} ({r['class_section']})" if str(r.get('class_section','')).strip() else str(r.get('grade','')),
        axis=1,
    )

    valid = df.dropna(subset=["percent"]).copy()
    student_perf = (
        valid.groupby(["sheet", "grade", "class_section", "class_label", "student_name"], as_index=False)["percent"]
        .mean()
        .rename(columns={"percent": "avg_percent"})
    )
    student_perf["avg_percent"] = student_perf["avg_percent"].round(2)

    subj_student = (
        valid.groupby(["sheet", "class_label", "student_name", "subject"], as_index=False)["percent"]
        .mean()
        .rename(columns={"percent": "avg_percent"})
    )
    subj_student["avg_percent"] = subj_student["avg_percent"].round(2)

    class_summary = (
        student_perf.groupby(["sheet", "grade", "class_section", "class_label"], as_index=False)["avg_percent"]
        .agg(student_count="count", mean_percent="mean", median_percent="median", min_percent="min", max_percent="max", std_percent="std")
        .round(2)
    )
    subject_summary = (
        valid.groupby(["subject"], as_index=False)["percent"]
        .agg(entry_count="count", mean_percent="mean", median_percent="median", min_percent="min", max_percent="max", std_percent="std")
        .round(2)
    )
    assessment_summary = (
        valid.groupby(["assessment_type"], as_index=False)["percent"]
        .agg(entry_count="count", mean_percent="mean", median_percent="median")
        .round(2)
    )

    df.to_csv(out_dir / "dashboard_records.csv", index=False)
    students.drop_duplicates().to_csv(out_dir / "dashboard_students.csv", index=False)
    student_perf.to_csv(out_dir / "dashboard_student_performance.csv", index=False)
    subj_student.to_csv(out_dir / "dashboard_student_subject_performance.csv", index=False)
    class_summary.to_csv(out_dir / "dashboard_class_summary.csv", index=False)
    subject_summary.to_csv(out_dir / "dashboard_subject_summary.csv", index=False)
    assessment_summary.to_csv(out_dir / "dashboard_assessment_summary.csv", index=False)

    print(f"records={len(df)} students={len(student_perf)} classes={len(class_summary)}")
    return out_dir


def main():
    ap = argparse.ArgumentParser(description="Prepare dashboard datasets")
    ap.add_argument("--long", default="data/processed/test_scores_long.csv")
    ap.add_argument("--students", default="data/processed/students.csv")
    ap.add_argument("--out-dir", default="data/processed")
    args = ap.parse_args()
    prepare(Path(args.long), Path(args.students), Path(args.out_dir))


if __name__ == "__main__":
    main()
