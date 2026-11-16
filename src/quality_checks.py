"""Data quality checks for extracted Stardom assessment records."""

from __future__ import annotations

import pandas as pd


def run_quality_checks(records: pd.DataFrame, students: pd.DataFrame) -> dict:
    """Run basic data quality checks and return a summary dict + issue frames."""
    issues = []
    total = len(records)
    missing_name = records['student_name'].isna() | (records['student_name'].astype(str).str.strip() == '')
    missing_sheet = records['sheet'].isna() | (records['sheet'].astype(str).str.strip() == '')
    missing_value = records['value'].isna() | (records['value'].astype(str).str.strip() == '')
    if missing_name.any():
        issues.append({'check': 'missing_student_name', 'count': int(missing_name.sum()), 'severity': 'high'})
    if missing_sheet.any():
        issues.append({'check': 'missing_sheet', 'count': int(missing_sheet.sum()), 'severity': 'high'})

    # duplicate student entries per sheet+student_no+name (student list)
    dup_students = students.duplicated(subset=['sheet', 'student_name'], keep=False)
    if dup_students.any():
        issues.append({'check': 'duplicate_student_rows_in_sheet', 'count': int(dup_students.sum()), 'severity': 'medium'})

    # percent derivability and out-of-range
    has_percent = records['percent'].notna() if 'percent' in records.columns else pd.Series([False]*len(records))
    out_of_range = pd.Series([False]*len(records))
    if 'percent' in records.columns:
        p = pd.to_numeric(records['percent'], errors='coerce')
        out_of_range = (p < 0) | (p > 100)
        if out_of_range.fillna(False).any():
            issues.append({'check': 'percent_out_of_range_0_100', 'count': int(out_of_range.fillna(False).sum()), 'severity': 'medium'})

    # numeric parse issues for non-empty values
    non_empty = records['value'].notna() & (records['value'].astype(str).str.strip() != '')
    if 'value_num' in records.columns:
        num = pd.to_numeric(records['value_num'], errors='coerce')
        # non-empty but not derivable as percent and not numeric -> potential format issue (informational)
        not_numeric = non_empty & num.isna() & ~has_percent
        if not_numeric.any():
            issues.append({'check': 'non_numeric_or_non_derivable_entries', 'count': int(not_numeric.sum()), 'severity': 'info'})

    summary = {
        'total_records': int(total),
        'total_students_rows': int(len(students)),
        'unique_students': int(students[['sheet','student_name']].drop_duplicates().shape[0]) if len(students) else 0,
        'records_with_derived_percent': int(has_percent.sum()) if len(has_percent) else 0,
        'records_missing_value': int(missing_value.sum()),
        'percent_out_of_range_count': int(out_of_range.fillna(False).sum()) if len(out_of_range) else 0,
        'issue_count_types': len(issues),
        'issues': issues,
    }
    return summary
