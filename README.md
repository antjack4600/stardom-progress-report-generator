# Stardom Assessment Progress Report Generator

An ed-tech data pipeline that turns Stardom school assessment spreadsheets into automated, documented progress reports with built-in data quality checks. It extracts and normalizes test-score data, computes performance metrics, and generates per-class and per-student reports as Markdown, plus visualizations.

> **Data/privacy note:** This project uses real student names and scores (school permission was stated by the project owner). The source Google Drive data was accessed read-only during preparation. Handle and share repository data responsibly.

## What it does
- Extracts assessment records from `2026-2027 Test Scores for Diagnostic Tests and Unit Tests .xlsx` (15 class sheets, KG-Grade 7).
- Normalizes and enriches data: grade and section, subject, assessment type, derived percentages.
- Runs data quality checks and saves `reports/output/data_quality_summary.json`.
- Generates 15 class progress reports in `reports/output/classes/` (class stats, student rankings, subject summaries, charts).
- Generates per-student progress reports for a focus class (default: Grade 4 Microsoft, 20 students) in `reports/output/students/`.
- Produces an index at `reports/output/INDEX.md` and figures in `reports/output/figures/`.

## Repository structure
```text
stardom-progress-report-generator/
├─ data/
│  ├─ raw/                         # source workbook (read-only copy)
│  └─ processed/                   # extracted and enriched datasets
├─ docs/
│  ├─ data-dictionary.md
│  ├─ methodology.md
│  └─ usage.md
├─ reports/
│  └─ output/
│     ├─ INDEX.md
│     ├─ data_quality_summary.json
│     ├─ classes/
│     ├─ students/
│     └─ figures/
├─ src/
│  ├─ extract_test_scores.py
│  ├─ data_prep.py
│  ├─ quality_checks.py
│  ├─ generate_reports.py
│  └─ run_pipeline.py
├─ .gitignore
├─ pyproject.toml
├─ uv.lock
└─ README.md
```

## Setup
Python 3.12+ and [uv](https://github.com/astral-sh/uv):

```bash
cd stardom-progress-report-generator
uv sync
```

Dependencies: `pandas`, `openpyxl`, `matplotlib`, `seaborn`, `jinja2`, `tabulate` (see `pyproject.toml`).

## Quick start (run the full pipeline)
```bash
uv run python src/run_pipeline.py
```
Steps:
1. Extract records from `data/raw/2026-2027_Test_Scores.xlsx`.
2. Prepare and enrich the dashboard-ready datasets in `data/processed/`.
3. Run quality checks and generate reports in `reports/output/`.

Open `reports/output/INDEX.md` to browse class and student reports.

## Desktop app (Linux / Kubuntu)

Run the pipeline from a native desktop window — pick the workbook, choose the
focus class, run, and browse the generated reports with charts:

```bash
uv run python desktop_app.py
```

To build a standalone desktop app and install a launcher into your app menu
(no sudo needed):

```bash
bash build_desktop.sh
```

This produces `dist/stardom-progress-report-generator/` and installs a `.desktop`
entry + icon under `~/.local`. Reports are written next to the bundle. See
[`SECURITY.md`](SECURITY.md) for the security review of this project.

## Run steps individually
```bash
# 1) Extract
uv run python src/extract_test_scores.py \
  --input data/raw/2026-2027_Test_Scores.xlsx \
  --out-long data/processed/test_scores_long.csv \
  --out-students data/processed/students.csv \
  --out-labels data/processed/column_labels.json

# 2) Prepare and enrich
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
- Processed data in `data/processed/` (long-form records, enriched records, per-student, class, and subject aggregates).
- Quality summary: `reports/output/data_quality_summary.json`.
- Class reports: `reports/output/classes/<Class>.md` plus figures in `reports/output/figures/`.
- Student reports: `reports/output/students/<Class>__<Student>.md` (for the focus class).
- Index: `reports/output/INDEX.md`.

## Data quality checks
Implemented in `src/quality_checks.py`. Examples: missing student or sheet fields, duplicate student rows, derived-percent coverage, out-of-range percentages (0-100), and non-numeric or non-derivable entry counts. Results are saved per run in `data_quality_summary.json` and summarized in the class reports.

## Methodology summary
- **Extraction:** parses multi-row headers and labels from the wide sheets into assessment-level records (student, class or sheet, assessment label, value).
- **Enrichment:** classifies grade and section, subject, assessment type, and measure kind; derives numeric values and percentages from given marks over max marks or percentage and ratio fields where available.
- **Metrics:** per-student and per-class average derived percentages, subject summaries, and comparisons to class averages where available.
- **Interpretation:** descriptive patterns in the recorded assessments, not causal conclusions. Missing or non-derivable entries are excluded from percent averages and surfaced through coverage and quality reporting.

See [`docs/methodology.md`](docs/methodology.md) and [`docs/data-dictionary.md`](docs/data-dictionary.md).

## Documentation
- [`docs/data-dictionary.md`](docs/data-dictionary.md): dataset and field definitions
- [`docs/methodology.md`](docs/methodology.md): parsing, classification, metrics, and assumptions
- [`docs/usage.md`](docs/usage.md): usage, configuration, and extension guide
- Inline docstrings and comments in `src/`

## Limitations and next steps
- Source layouts vary by class and assessment; extraction and classification use heuristics that may need tuning for new formats.
- Not all assessments and subjects are recorded for every student or class; missing values are not treated as zeros.
- Percent metrics depend on derivable fields (max marks, percent, ratio).

Next steps: per-student reports for all classes, HTML or PDF export, longitudinal term-over-term tracking, richer validation rules, integration of 26-27 class records and grading and progress folders, and configurable report templates.

## Source data
- `data/raw/2026-2027_Test_Scores.xlsx` (read-only copy of the Stardom Drive file). Google Drive was accessed read-only during project preparation.
