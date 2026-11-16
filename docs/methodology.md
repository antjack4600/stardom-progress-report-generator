# Methodology

## 1. Extraction
- Read `.xlsx` sheets and shared strings; detect header/student-name rows and parse multi-row column labels.
- Emit one long-form record per non-empty assessment cell for student rows (`sheet, student_no, student_name, column, assessment_label, value`).

## 2. Enrichment & metrics
- Parse `sheet` into `grade`, `class_section`, `class_label`.
- Classify `subject` (ELA/Math/Science/Social Studies/Other), `assessment` and `assessment_type` (Diagnostic, Unit/Chapter/Module, Benchmark/Mid/End, etc.), and `measure_kind` from header labels (heuristics).
- Parse numeric values and `max_marks`; derive `percent` (0–100) from explicit percentages/ratios or `value/max_marks` when available.
- Compute per-student, per-student-subject, per-class, and per-subject aggregates over records with derivable percent.

## 3. Data quality checks
- Missing student/sheet fields, duplicate student rows per sheet, out-of-range percents, missing values, and non-numeric/non-derivable entry counts; summarized in JSON and included in reports.

## 4. Report generation
- **Class reports:** roster size, class mean/median/min/max, ranked student averages, subject summary, quality summary, and a bar chart.
- **Student reports (focus class):** student vs class average, subject averages, and a sample of recorded entries.
- Percent-based metrics exclude missing/non-derivable entries; outputs are descriptive (not causal).
