# Usage

## Prerequisites
- Python 3.12+, [uv](https://github.com/astral-sh/uv)
- `uv sync`

## End-to-end
```bash
uv run python src/run_pipeline.py
```
Outputs: `data/processed/` and `reports/output/` (see `reports/output/INDEX.md`).

## Customize focus class for per-student reports
```bash
uv run python src/generate_reports.py --focus-class "Grade 5 (Amazon)" \
  --records data/processed/dashboard_records.csv \
  --students data/processed/dashboard_students.csv \
  --student-perf data/processed/dashboard_student_performance.csv \
  --subj-student data/processed/dashboard_student_subject_performance.csv \
  --out-dir reports/output
```

## Extend
- Add new raw sources in `data/raw/` and extend extraction/prep to normalize schemas.
- Add report templates (e.g. Jinja2/HTML/PDF), generate reports for all classes, or integrate longitudinal data.
- Tune classification/derivation heuristics in `src/data_prep.py` for new header formats.
