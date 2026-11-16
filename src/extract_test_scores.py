import argparse
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

NS = {
    'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}


def read_xlsx_sheets(path: Path):
    with zipfile.ZipFile(path) as z:
        sst = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('a:si', NS):
                texts = [t.text or '' for t in si.findall('.//a:t', NS)]
                sst.append(''.join(texts))
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        rid_to_target = {r.attrib['Id']: r.attrib['Target'] for r in rels}
        sheets = []
        for sh in wb.findall('a:sheets/a:sheet', NS):
            name = sh.attrib['name']
            rid = sh.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            target = rid_to_target.get(rid, '')
            if target.startswith('/'):
                target = target.lstrip('/')
            if not target.startswith('xl/'):
                target = 'xl/' + target
            sheets.append((name, target))
        data = {}
        for name, target in sheets:
            if target not in z.namelist():
                # fallback: find by basename
                base = target.split('/')[-1]
                cand = [n for n in z.namelist() if n.endswith('/'+base) or n == base]
                if cand:
                    target = cand[0]
            try:
                root = ET.fromstring(z.read(target))
            except Exception:
                data[name] = []
                continue
            rows = []
            for row in root.findall('.//a:sheetData/a:row', NS):
                cells = {}
                for c in row.findall('a:c', NS):
                    ref = c.attrib.get('r', '')
                    m = re.match(r'([A-Z]+)', ref)
                    col = m.group(1) if m else ''
                    t = c.attrib.get('t')
                    v = c.find('a:v', NS)
                    is_node = c.find('a:is/a:t', NS)
                    if t == 's' and v is not None and v.text is not None:
                        idx = int(v.text)
                        val = sst[idx] if idx < len(sst) else v.text
                    elif t == 'inlineStr' and is_node is not None:
                        val = is_node.text or ''
                    elif v is not None:
                        val = v.text
                    else:
                        val = None
                    cells[col] = val
                if cells:
                    rows.append(cells)
            data[name] = rows
    return data


def col_letters_to_index(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord('A') + 1)
    return n


def extract_sheet(sheet_name: str, rows):
    # Identify header rows: look for row containing 'Student Name' or similar in col B
    header_row_idx = None
    for i, r in enumerate(rows[:12]):
        b = (r.get('B') or '').strip().lower()
        if 'student' in b and 'name' in b:
            header_row_idx = i
            break
    if header_row_idx is None:
        # fallback: row 4 (index 3) common
        header_row_idx = 3 if len(rows) > 3 else 0

    # Build column labels by scanning a few header rows above/at header
    # collect labels per column from header_row_idx-2 .. header_row_idx
    start = max(0, header_row_idx - 2)
    labels = {}
    all_cols = set()
    for r in rows[start:header_row_idx + 1]:
        all_cols.update(r.keys())
    for col in all_cols:
        parts = []
        for i in range(start, header_row_idx + 1):
            val = rows[i].get(col) if i < len(rows) else None
            if val is None:
                continue
            s = str(val).strip()
            if s:
                parts.append(re.sub(r'\s+', ' ', s))
        # de-dup consecutive
        dedup = []
        for p in parts:
            if not dedup or dedup[-1] != p:
                dedup.append(p)
        labels[col] = ' | '.join(dedup)

    records = []
    for r in rows[header_row_idx + 1:]:
        a = r.get('A')
        b = r.get('B')
        if b is None:
            continue
        name = str(b).strip()
        if not name:
            continue
        # student rows usually have numeric index in A
        try:
            idx_num = float(str(a).strip()) if a is not None and str(a).strip() != '' else None
        except Exception:
            idx_num = None
        if idx_num is None:
            # skip non-student rows
            continue
        base = {
            'sheet': sheet_name,
            'student_no': int(idx_num) if idx_num.is_integer() else idx_num,
            'student_name': name,
        }
        # include all other columns as assessment values
        for col, val in r.items():
            if col in ('A', 'B'):
                continue
            if val is None or str(val).strip() == '':
                continue
            label = labels.get(col, col)
            records.append({
                **base,
                'column': col,
                'assessment_label': label,
                'value': str(val).strip(),
            })
    return records, labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out-long', required=True)
    ap.add_argument('--out-students', required=True)
    ap.add_argument('--out-labels', required=True)
    args = ap.parse_args()

    sheets = read_xlsx_sheets(Path(args.input))
    all_records = []
    all_students = []
    labels_out = {}
    for sheet_name, rows in sheets.items():
        recs, labels = extract_sheet(sheet_name, rows)
        for rec in recs:
            all_records.append(rec)
        labels_out[sheet_name] = labels
        # unique students per sheet
        seen = set()
        for r in rows:
            a = r.get('A'); b = r.get('B')
            if b is None:
                continue
            try:
                if a is None or str(a).strip() == '':
                    continue
                float(str(a))
            except Exception:
                continue
            name = str(b).strip()
            if name and name.lower() not in ('student name',):
                key = (sheet_name, name)
                if key not in seen:
                    seen.add(key)
                    all_students.append({'sheet': sheet_name, 'student_no': a, 'student_name': name})

    pd.DataFrame(all_records).to_csv(args.out_long, index=False)
    pd.DataFrame(all_students).drop_duplicates().to_csv(args.out_students, index=False)
    with open(args.out_labels, 'w', encoding='utf-8') as f:
        json.dump(labels_out, f, ensure_ascii=False, indent=2)
    print(f'sheets={len(sheets)} records={len(all_records)} students_rows={len(all_students)}')


if __name__ == '__main__':
    main()
