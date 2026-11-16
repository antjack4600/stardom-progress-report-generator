# Stardom Assessment Progress Report Generator

An ed-tech data pipeline that turns Stardom school assessment spreadsheets into **automated, documented progress reports** with built-in **data quality checks**. It extracts and normalizes test-score data, computes performance metrics, and generates per-class and per-student reports (Markdown) with visualizations.

> **Data/privacy note:** This project uses real student names and scores (school permission stated by project owner). The source Google Drive data was accessed **read-only** during preparation. Handle and share repository data responsibly.

## Why this project (resume value)
- **Data engineering & ETL:** parses complex, wide/multi-header Excel sheets into a clean, analysis-ready dataset.
- **Data quality:** runs validation/quality checks (missing fields, duplicates, derivability, out-of-range values) and outputs a quality summary.
- **Analytics & reporting automation:** computes per-student/class/subject metrics and generates reproducible, templated progress reports at scale.
- **Ed-tech domain:** translates assessment records into actionable class and student progress views.
- **Reproducible workflow:** scripted end-to-end pipeline with clear documentation.

## Features
- Extracts assessment records from `2026-2027 Test Scores for Diagnostic Tests and Unit Tests .xlsx` (15 class sheets, KG–Grade 7).
- Normalizes and enriches data (grade/section, subject, assessment type, derived percentages).
- Runs data quality checks and saves `reports/output/data_quality_summary.json`.
- Generates **15 class progress reports** (`reports/output/classes/`) with class stats, student rankings, subject summaries, and charts.
- Generates **per-student progress reports** for a focus class (default: Grade 4 Microsoft, 20 students) in `reports/output/students/`.
- Produces an index at `reports/output/INDEX.md` and figures in `reports/output/figures/`.

## Repository structure
```text
stardom-progress-report-generator/
├─ data/
│  ├─ raw/                         # source workbook (read-only copy)
│  └─ processed/                   # extracted & enriched datasets
├─ docs/
│  ├─ data-dictionary.md
│  ├─ methodology.md
│  └─ usage.md
├─ reports/
│  └─ output/
│     ├─ INDEX.md                  # report index
│     ├─ data_quality_summary.json
│     ├─ classes/                  # per-class Markdown reports
│     ├─ students/                 # per-student Markdown reports (focus class)
│     └─ figures/                  # class performance charts
├─ src/
│  ├─ extract_test_scores.py       # workbook extraction (wide/multi-header parsing)
│  ├─ data_prep.py                 # enrichment, classification, percent derivation, aggregates
│  ├─ quality_checks.py            # data quality validation checks
│  ├─ generate_reports.py          # report and chart generation
│  └─ run_pipeline.py              # end-to-end pipeline
├─ .gitignore
├─ pyproject.toml
├─ uv.lock
└─ README.md
```

## Setup
**Requirements:** Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
cd stardom-progress-report-generator
uv sync
```

Dependencies: `pandas`, `openpyxl`, `matplotlib`, `seaborn`, `jinja2`, `tabulate` (see `pyproject.toml`).

## Quick start (run the full pipeline)
```bash
uv run python src/run_pipeline.py
```
This will:
1. Extract records from `data/raw/2026-2027_Test_Scores.xlsx`
2. Prepare/enrich dashboard-ready datasets in `data/processed/`
3. Run quality checks and generate reports in `reports/output/`

Open `reports/output/INDEX.md` to browse class and student reports.

## Run steps individually
```bash
# 1) Extract
uv run python src/extract_test_scores.py \
  --input data/raw/2026-2027_Test_Scores.xlsx \
  --out-long data/processed/test_scores_long.csv \
  --out-students data/processed/students.csv \
  --out-labels data/processed/column_labels.json

# 2) Prepare/enrich
uv run python src/data_prep.py \
  --long data/processed/test_scores_long.csv \
  --students data/processed/students.csv \
  --out-dir data/processed

# 3) Generate reports (change --focus-class as needed)
uv run python src/generate_reports.py \
  --records data/processed/dashboard_records.csv \
  --students data/processed/dashboard_students.csv \
  --student-perf data/processed/dashboard_student_performance.csv \
  --subj-student data/processed/dashboard_student_subject_performance.csv \
  --out-dir reports/output \
  --focus-class "Grade 4 (Microsoft)"
```

## Outputs
- **Processed data:** `data/processed/` (long-form records, enriched records, per-student/class/subject aggregates)
- **Quality summary:** `reports/output/data_quality_summary.json`
- **Class reports:** `reports/output/classes/<Class>.md` + figures in `reports/output/figures/`
- **Student reports:** `reports/output/students/<Class>__<Student>.md` (for focus class)
- **Index:** `reports/output/INDEX.md`

## Data quality checks
Implemented in `src/quality_checks.py` (examples): missing student/sheet fields, duplicate student rows, derived-percent coverage, out-of-range percentages (0–100), and non-numeric/non-derivable entry counts. Results are reported per run in `data_quality_summary.json` and summarized in class reports.

## Methodology (summary)
- **Extraction:** parses multi-row headers/labels from wide sheets into assessment-level records (student, class/sheet, assessment label, value).
- **Enrichment:** classifies grade/section, subject, assessment type, and measure kind; derives numeric values and percentages from given marks/max marks or percentage/ratio fields when available.
- **Metrics:** per-student and per-class average derived percentages, subject summaries, and comparisons to class averages (where available).
- **Interpretation:** descriptive patterns in recorded assessments (not causal). Missing/non-derivable entries are excluded from percent averages and surfaced via coverage/quality reporting.

See [`docs/methodology.md`](docs/methodology.md) and [`docs/data-dictionary.md`](docs/data-dictionary.md).

## Documentation
- [`docs/data-dictionary.md`](docs/data-dictionary.md) — dataset and field definitions
- [`docs/methodology.md`](docs/methodology.md) — parsing, classification, metrics, and assumptions
- [`docs/usage.md`](docs/usage.md) — usage, configuration, and extension guide
- Inline docstrings/comments in `src/`

## Limitations & next steps
- Source layouts vary by class/assessment; extraction/classification uses heuristics that may need tuning for new formats.
- Not all assessments/subjects are recorded for every student/class; missing values are not treated as zeros.
- Percent metrics depend on derivable fields (max marks/percent/ratio).
- **Next steps:** add per-student reports for all classes, HTML/PDF export, longitudinal term-over-term tracking, richer validation rules, integration of 26-27 class records and grading/progress folders, and configurable report templates.

## Source data
- `data/raw/2026-2027_Test_Scores.xlsx` (read-only copy of Stardom Drive file). Google Drive was accessed read-only during project preparation.
