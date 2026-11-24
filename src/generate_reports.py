"""Generate class and student progress reports from prepared assessment data."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from quality_checks import run_quality_checks

sns.set_theme(style='whitegrid')


def ensure_dirs(out_dir: Path):
    (out_dir / 'classes').mkdir(parents=True, exist_ok=True)
    (out_dir / 'students').mkdir(parents=True, exist_ok=True)
    (out_dir / 'figures').mkdir(parents=True, exist_ok=True)


def safe_name(s: str) -> str:
    """Sanitize a string for use as a filename.

    Keeps letters/digits and a few safe punctuation characters; replaces path
    separators and other unsafe characters with '_'; collapses repeated dots;
    and strips leading/trailing dots so '..' or '.hidden' style names cannot
    escape the output directory.
    """
    cleaned = ''.join(c if c.isalnum() or c in ' _-.()' else '_' for c in str(s)).strip()
    cleaned = re.sub(r'\.{2,}', '.', cleaned)  # collapse '..' style runs
    cleaned = cleaned.strip(' .')               # no leading/trailing dots
    cleaned = re.sub(r'\s+', '_', cleaned)
    return cleaned or '_'


def student_report_md(sheet, student, student_rows, subj_perf, overall_avg, class_avg):
    lines = []
    lines.append(f"# Student Progress Report: {student}")
    lines.append("")
    lines.append(f"- **Class/Sheet:** {sheet}")
    lines.append(f"- **Student average (derived %):** {overall_avg:.2f}%" if overall_avg is not None else "- **Student average (derived %):** N/A")
    lines.append(f"- **Class average (derived %):** {class_avg:.2f}%" if class_avg is not None else "- **Class average (derived %):** N/A")
    if overall_avg is not None and class_avg is not None:
        diff = overall_avg - class_avg
        pos = "above" if diff >= 0 else "below"
        lines.append(f"- **Compared to class:** {abs(diff):.2f} percentage points {pos} class average")
    lines.append("")
    lines.append("## Subject performance (average derived %)")
    if len(subj_perf):
        lines.append(subj_perf[['subject','avg_percent']].to_markdown(index=False))
    else:
        lines.append("No subject-level derived percentages available.")
    lines.append("")
    lines.append("## Recorded assessment entries (sample)")
    cols = [c for c in ['subject','assessment','assessment_type','value','percent'] if c in student_rows.columns]
    sample = student_rows[cols].head(20)
    if len(sample):
        lines.append(sample.to_markdown(index=False))
        if len(student_rows) > 20:
            lines.append(f"\n*Showing 20 of {len(student_rows)} entries.*")
    else:
        lines.append("No entries available.")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Percentages are derived from available given marks/max marks or percentage/ratio fields; missing/non-derivable entries are excluded from percent averages.")
    lines.append("- This report reflects recorded assessment patterns, not causal conclusions.")
    return "\n".join(lines)


def class_report_md(sheet, students_df, student_perf_class, subj_summary, quality_summary):
    lines = []
    lines.append(f"# Class Progress Report: {sheet}")
    lines.append("")
    n_students = students_df[students_df['sheet']==sheet]['student_name'].nunique() if len(students_df) else 0
    lines.append(f"- **Students (listed):** {n_students}")
    if len(student_perf_class):
        lines.append(f"- **Class mean student avg %:** {student_perf_class['avg_percent'].mean():.2f}%")
        lines.append(f"- **Median:** {student_perf_class['avg_percent'].median():.2f}%")
        lines.append(f"- **Min/Max:** {student_perf_class['avg_percent'].min():.2f}% / {student_perf_class['avg_percent'].max():.2f}%")
    lines.append("")
    lines.append("## Student performance (average derived %)")
    if len(student_perf_class):
        lines.append(student_perf_class[['student_name','avg_percent']].sort_values('avg_percent', ascending=False).to_markdown(index=False))
    else:
        lines.append("No derived student performance available.")
    lines.append("")
    lines.append("## Subject summary (entries with derived %)")
    if len(subj_summary):
        lines.append(subj_summary.to_markdown(index=False))
    else:
        lines.append("No subject summary available.")
    lines.append("")
    lines.append("## Data quality (dataset-level)")
    lines.append(f"- Total records: {quality_summary.get('total_records')}")
    lines.append(f"- Records with derived %: {quality_summary.get('records_with_derived_percent')}")
    for iss in quality_summary.get('issues', []):
        lines.append(f"- {iss['check']}: {iss['count']} ({iss['severity']})")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Averages use only records where a percentage could be derived; coverage varies by class/subject/assessment.")
    lines.append("- Descriptive patterns only; not causal conclusions.")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--records', default='data/processed/dashboard_records.csv')
    ap.add_argument('--students', default='data/processed/dashboard_students.csv')
    ap.add_argument('--student-perf', default='data/processed/dashboard_student_performance.csv')
    ap.add_argument('--subj-student', default='data/processed/dashboard_student_subject_performance.csv')
    ap.add_argument('--out-dir', default='reports/output')
    ap.add_argument('--focus-class', default='Grade 4 (Microsoft)', help='Generate per-student reports for this class (and class report for all)')
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    ensure_dirs(out_dir)
    records = pd.read_csv(args.records)
    students = pd.read_csv(args.students)
    student_perf = pd.read_csv(args.student_perf)
    subj_student = pd.read_csv(args.subj_student)

    q = run_quality_checks(records, students)
    (out_dir / 'data_quality_summary.json').write_text(json.dumps(q, indent=2), encoding='utf-8')

    # class figures and reports
    for sheet in sorted(student_perf['sheet'].unique()):
        spc = student_perf[student_perf['sheet']==sheet].copy()
        rec_c = records[records['sheet']==sheet]
        valid_c = rec_c.dropna(subset=['percent']) if 'percent' in rec_c.columns else rec_c.iloc[0:0]
        subj_sum = valid_c.groupby('subject', as_index=False)['percent'].agg(entries='count', mean_percent='mean', median_percent='median').round(2) if len(valid_c) else pd.DataFrame()
        md = class_report_md(sheet, students, spc, subj_sum, q)
        (out_dir / 'classes' / f"{safe_name(sheet)}.md").write_text(md, encoding='utf-8')
        if len(spc):
            plt.figure(figsize=(8, max(3, len(spc)*0.35)))
            tmp = spc.sort_values('avg_percent', ascending=True)
            plt.barh(tmp['student_name'], tmp['avg_percent'], color='#4C78A8')
            plt.xlabel('Average derived %')
            plt.title(f'Student average performance — {sheet}')
            plt.tight_layout()
            plt.savefig(out_dir / 'figures' / f"class_{safe_name(sheet)}.png", dpi=150)
            plt.close()

    # per-student reports for focus class
    focus = args.focus_class
    sp_focus = student_perf[student_perf['sheet']==focus]
    class_avg = sp_focus['avg_percent'].mean() if len(sp_focus) else None
    for _, row in sp_focus.iterrows():
        student = row['student_name']
        srows = records[(records['sheet']==focus) & (records['student_name']==student)]
        ssubj = subj_student[(subj_student['sheet']==focus) & (subj_student['student_name']==student)]
        overall = row['avg_percent']
        md = student_report_md(focus, student, srows, ssubj, overall, class_avg)
        (out_dir / 'students' / f"{safe_name(focus)}__{safe_name(student)}.md").write_text(md, encoding='utf-8')

    # index
    idx = ["# Progress Reports Index", "", f"- Focus class for individual reports: **{focus}**", f"- Class reports: {student_perf['sheet'].nunique()}", f"- Student reports (focus class): {len(sp_focus)}", "", "## Class reports"]
    for sheet in sorted(student_perf['sheet'].unique()):
        idx.append(f"- [classes/{safe_name(sheet)}.md](classes/{safe_name(sheet)}.md)")
    idx.append("")
    idx.append("## Student reports (focus class)")
    for _, row in sp_focus.sort_values('student_name').iterrows():
        s=row['student_name']
        idx.append(f"- [students/{safe_name(focus)}__{safe_name(s)}.md](students/{safe_name(focus)}__{safe_name(s)}.md)")
    idx.append("")
    idx.append(f"## Data quality\nSee [data_quality_summary.json](data_quality_summary.json).")
    (out_dir / 'INDEX.md').write_text('\n'.join(idx), encoding='utf-8')

    print(f"class_reports={student_perf['sheet'].nunique()} student_reports={len(sp_focus)} out={out_dir}")


if __name__ == '__main__':
    main()
