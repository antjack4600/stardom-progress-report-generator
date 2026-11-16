"""End-to-end pipeline: extract -> prepare -> quality/report generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd):
    print('+', ' '.join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main():
    root = Path(__file__).resolve().parents[1]
    raw = root / 'data/raw/2026-2027_Test_Scores.xlsx'
    proc = root / 'data/processed'
    proc.mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(root/'src/extract_test_scores.py'), '--input', str(raw),
         '--out-long', str(proc/'test_scores_long.csv'), '--out-students', str(proc/'students.csv'),
         '--out-labels', str(proc/'column_labels.json')])
    run([sys.executable, str(root/'src/data_prep.py'), '--long', str(proc/'test_scores_long.csv'),
         '--students', str(proc/'students.csv'), '--out-dir', str(proc)])
    run([sys.executable, str(root/'src/generate_reports.py'),
         '--records', str(proc/'dashboard_records.csv'), '--students', str(proc/'dashboard_students.csv'),
         '--student-perf', str(proc/'dashboard_student_performance.csv'),
         '--subj-student', str(proc/'dashboard_student_subject_performance.csv'),
         '--out-dir', str(root/'reports/output'), '--focus-class', 'Grade 4 (Microsoft)'])
    print('Pipeline complete.')


if __name__ == '__main__':
    main()
