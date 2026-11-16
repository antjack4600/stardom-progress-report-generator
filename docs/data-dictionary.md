# Data Dictionary

## Raw
- **`data/raw/2026-2027_Test_Scores.xlsx`**: Read-only copy of Stardom workbook with 15 class sheets (KG–Grade 7). Multi-row headers, student rows (index/name) and assessment values (given marks, max marks, percentages/ratios, quizzes/projects where present).

## Extracted (`src/extract_test_scores.py`)
- **`test_scores_long.csv`**: `sheet`, `student_no`, `student_name`, `column`, `assessment_label`, `value` (assessment-level long-form records).
- **`students.csv`**: `sheet`, `student_no`, `student_name` (detected student rows per sheet).
- **`column_labels.json`**: sheet -> column -> combined header label mapping.

## Enriched/prepared (`src/data_prep.py`)
- **`dashboard_records.csv`**: extracted fields plus `grade`, `class_section`, `class_label`, `subject`, `assessment`, `assessment_type`, `measure_kind`, `max_marks`, `value_num`, `percent` (derived 0–100 when possible).
- **`dashboard_students.csv`**: students with parsed grade/class labels.
- **`dashboard_student_performance.csv`**: per-student mean `avg_percent` (over derivable-percent entries).
- **`dashboard_student_subject_performance.csv`**: per-student, per-subject mean `avg_percent`.
- **`dashboard_class_summary.csv`**, **`dashboard_subject_summary.csv`**, **`dashboard_assessment_summary.csv`**: aggregate statistics.

## Generated outputs (`src/generate_reports.py`)
- **`reports/output/data_quality_summary.json`**: record counts, coverage, and issue list (check, count, severity).
- **`reports/output/classes/*.md`**: per-class progress reports (stats, student ranking, subject summary, quality summary).
- **`reports/output/students/*.md`**: per-student reports for focus class (averages, subject breakdown, sample entries).
- **`reports/output/figures/class_*.png`**: class student-average bar charts.
- **`reports/output/INDEX.md`**: index of generated reports.
