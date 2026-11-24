"""Desktop app for the Stardom Progress Report Generator (PySide6 native GUI).

A desktop window for the report pipeline:
  * Home        — visual overview of what the app does (cards + sample chart)
  * Run         — pick the workbook / focus class, run extract → enrich → reports
  * Reports     — browse generated Markdown class & student reports with figures
  * Data quality — summary of the last run's quality checks

Run from the project root:
    uv run python desktop_app.py

Useful flags:
    --smoke           Headless smoke test: open the app, screenshot, exit
    --smoke-out PATH  Where to write the smoke screenshot (PNG)
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def resource_root() -> Path:
    """Project resources: repo root normally, bundle dir when frozen by PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return ROOT


SRC = resource_root() / "src"
ICON_SVG = resource_root() / "assets" / "icon.svg"
PROC_DIR = resource_root() / "data" / "processed"
OUT_DIR = resource_root() / "reports" / "output"


# --------------------------------------------------------------------------
# Pipeline runner (runs the existing scripts in-process on a worker thread)
# --------------------------------------------------------------------------

STEPS = [
    ("Extract records from workbook", "extract_test_scores.py"),
    ("Prepare / enrich datasets", "data_prep.py"),
    ("Generate reports + quality checks", "generate_reports.py"),
]


def _run_script(script: Path, args: list[str], log_cb) -> None:
    """Run a src/ script as __main__ with the given argv (captures stdout)."""
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    old_argv = sys.argv
    buf = io.StringIO()
    try:
        sys.argv = [str(script), *args]
        log_cb(f"$ {script.name} {' '.join(args)}")
        with contextlib.redirect_stdout(buf):
            runpy.run_path(str(script), run_name="__main__")
        for line in buf.getvalue().splitlines():
            if line.strip():
                log_cb(line)
    finally:
        sys.argv = old_argv


def pipeline_steps(workbook: Path, out_dir: Path, focus_class: str):
    proc = PROC_DIR
    yield ("extract_test_scores.py", "Extract records from workbook", [
        "--input", str(workbook),
        "--out-long", str(proc / "test_scores_long.csv"),
        "--out-students", str(proc / "students.csv"),
        "--out-labels", str(proc / "column_labels.json"),
    ])
    yield ("data_prep.py", "Prepare / enrich datasets", [
        "--long", str(proc / "test_scores_long.csv"),
        "--students", str(proc / "students.csv"),
        "--out-dir", str(proc),
    ])
    yield ("generate_reports.py", "Generate reports + quality checks", [
        "--records", str(proc / "dashboard_records.csv"),
        "--students", str(proc / "dashboard_students.csv"),
        "--student-perf", str(proc / "dashboard_student_performance.csv"),
        "--subj-student", str(proc / "dashboard_student_subject_performance.csv"),
        "--out-dir", str(out_dir),
        "--focus-class", focus_class,
    ])


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------

def _markdown_to_html(md_text: str, base_dir: Path) -> str:
    import markdown as md_lib

    html = md_lib.markdown(md_text, extensions=["tables", "fenced_code"])
    # Rewrite relative links/images to absolute file:// URLs so Qt can resolve them
    import re
    import urllib.parse

    def _abs(m: re.Match) -> str:
        url = m.group(2)
        if url.startswith(("http://", "https://", "file://", "#")):
            return m.group(0)
        target = (base_dir / url).resolve()
        return f"{m.group(1)}file://{urllib.parse.quote(str(target))}"

    html = re.sub(r'(src|href)="([^"]+)"', _abs, html)
    return html


def build_gui(app) -> "QMainWindow":
    from PySide6.QtCore import Qt, QThread, Signal
    from PySide6.QtGui import QAction, QIcon, QPixmap, QKeySequence
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QDialog,
        QFileDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QTabWidget,
        QTextBrowser,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    class PipelineThread(QThread):
        log = Signal(str)
        done = Signal(bool, str)

        def __init__(self, workbook: Path, out_dir: Path, focus_class: str):
            super().__init__()
            self.workbook = workbook
            self.out_dir = out_dir
            self.focus_class = focus_class

        def run(self) -> None:
            try:
                for script_name, human_name, args in pipeline_steps(
                    self.workbook, self.out_dir, self.focus_class
                ):
                    self.log.emit(f"\n=== {human_name} ===")
                    _run_script(SRC / script_name, args, self.log.emit)
                self.log.emit("\nPipeline complete.")
                self.done.emit(True, "")
            except Exception as exc:  # noqa: BLE001
                self.log.emit(f"\nERROR: {exc}")
                self.done.emit(False, str(exc))

    window = QMainWindow()
    window.setWindowTitle("Stardom Progress Report Generator")
    if ICON_SVG.exists():
        window.setWindowIcon(QIcon(str(ICON_SVG)))
    window.resize(1180, 800)

    tabs = QTabWidget()
    window.setCentralWidget(tabs)

    # ---- Tab 1: Home (visual overview) ----
    home = QWidget()
    home_layout = QVBoxLayout(home)
    header = QLabel(
        "<h1>Stardom Progress Report Generator</h1>"
        "<p>Turns the school's assessment spreadsheet into documented per-class and "
        "per-student progress reports — with data quality checks and charts.</p>"
    )
    header.setWordWrap(True)
    home_layout.addWidget(header)

    cards = QGridLayout()
    card_data = [
        ("1. Extract", "Reads the raw .xlsx workbook (one sheet per class) into "
                       "assessment-level records."),
        ("2. Enrich", "Parses grades, subjects, assessment types and derives "
                      "percentages from marks/max marks."),
        ("3. Quality checks", "Flags missing names, duplicates, out-of-range "
                              "percentages and non-numeric entries."),
        ("4. Reports", "Generates Markdown class reports, per-student reports, "
                       "charts, and an index to browse them."),
    ]
    for i, (title, body) in enumerate(card_data):
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card_layout = QVBoxLayout(card)
        card_layout.addWidget(QLabel(f"<b>{title}</b>"))
        body_label = QLabel(body)
        body_label.setWordWrap(True)
        card_layout.addWidget(body_label)
        cards.addWidget(card, i // 2, i % 2)
    home_layout.addLayout(cards)

    preview_row = QHBoxLayout()
    preview = QLabel()
    figs = sorted((OUT_DIR / "figures").glob("*.png")) if (OUT_DIR / "figures").exists() else []
    if figs:
        pix = QPixmap(str(figs[0]))
        preview.setPixmap(pix.scaledToWidth(560, Qt.SmoothTransformation))
        preview_label = QLabel("<b>Sample chart from the last run</b>")
        preview_col = QVBoxLayout()
        preview_col.addWidget(preview_label)
        preview_col.addWidget(preview)
        preview_row.addLayout(preview_col)
    else:
        preview_row.addWidget(QLabel("<i>No charts yet — run the pipeline first.</i>"))
    home_layout.addLayout(preview_row)

    stats = QLabel(_home_stats())
    stats.setWordWrap(True)
    home_layout.addWidget(stats)
    home_layout.addStretch(1)
    tabs.addTab(home, "Home")

    # ---- Tab 2: Run pipeline ----
    run_tab = QWidget()
    run_layout = QVBoxLayout(run_tab)

    form = QGridLayout()
    wb_edit = QLineEdit(str(resource_root() / "data" / "raw" / "2026-2027_Test_Scores.xlsx"))
    out_edit = QLineEdit(str(OUT_DIR))
    focus_combo = QComboBox()
    focus_combo.setEditable(True)

    def _refresh_focus_classes():
        focus_combo.clear()
        students_csv = PROC_DIR / "dashboard_students.csv"
        if students_csv.exists():
            import pandas as pd

            df = pd.read_csv(students_csv)
            if "sheet" in df.columns:
                for sheet in sorted(df["sheet"].dropna().unique()):
                    focus_combo.addItem(sheet)

    _refresh_focus_classes()

    def _browse_wb():
        path, _ = QFileDialog.getOpenFileName(window, "Choose workbook", str(wb_edit.text()), "Excel (*.xlsx)")
        if path:
            wb_edit.setText(path)

    def _browse_out():
        path = QFileDialog.getExistingDirectory(window, "Choose output folder", str(out_edit.text()))
        if path:
            out_edit.setText(path)

    form.addWidget(QLabel("Workbook (.xlsx):"), 0, 0)
    form.addWidget(wb_edit, 0, 1)
    wb_browse = QPushButton("Browse…")
    wb_browse.clicked.connect(_browse_wb)
    form.addWidget(wb_browse, 0, 2)

    form.addWidget(QLabel("Output folder:"), 1, 0)
    form.addWidget(out_edit, 1, 1)
    out_browse = QPushButton("Browse…")
    out_browse.clicked.connect(_browse_out)
    form.addWidget(out_browse, 1, 2)

    form.addWidget(QLabel("Focus class (per-student reports):"), 2, 0)
    form.addWidget(focus_combo, 2, 1, 1, 2)
    run_layout.addLayout(form)

    run_btn = QPushButton("Run pipeline")
    run_btn.setStyleSheet("font-weight: bold; padding: 8px;")
    run_layout.addWidget(run_btn)

    log_view = QTextEdit()
    log_view.setReadOnly(True)
    log_view.setFontFamily("Monospace")
    run_layout.addWidget(log_view, 1)

    worker: list[PipelineThread] = []

    def _run():
        log_view.clear()
        wb = Path(wb_edit.text().strip())
        out = Path(out_edit.text().strip())
        if not wb.exists():
            QMessageBox.warning(window, "Missing workbook", f"Workbook not found:\n{wb}")
            return
        focus = focus_combo.currentText().strip() or "Grade 4 (Microsoft)"
        t = PipelineThread(wb, out, focus)
        t.log.connect(log_view.append)
        t.done.connect(_done)
        worker.clear()
        worker.append(t)
        run_btn.setEnabled(False)
        t.start()

    def _done(ok: bool, err: str):
        run_btn.setEnabled(True)
        _refresh_reports()
        _refresh_focus_classes()
        if ok:
            QMessageBox.information(window, "Done", "Pipeline finished — see the Reports tab.")
        else:
            QMessageBox.warning(window, "Pipeline failed", err)

    run_btn.clicked.connect(_run)
    tabs.addTab(run_tab, "Run pipeline")

    # ---- Tab 3: Reports browser ----
    reports_tab = QWidget()
    rep_layout = QHBoxLayout(reports_tab)
    left_col = QVBoxLayout()
    refresh_btn = QPushButton("Refresh list")
    report_list = QListWidget()
    left_col.addWidget(refresh_btn)
    left_col.addWidget(report_list)
    rep_layout.addLayout(left_col)
    report_view = QTextBrowser()
    report_view.setOpenExternalLinks(True)
    rep_layout.addWidget(report_view, 1)

    def _refresh_reports():
        report_list.clear()
        classes = sorted((OUT_DIR / "classes").glob("*.md")) if (OUT_DIR / "classes").exists() else []
        students = sorted((OUT_DIR / "students").glob("*.md")) if (OUT_DIR / "students").exists() else []
        for p in classes:
            item = QListWidgetItem(f"📄 {p.stem}")
            item.setData(Qt.UserRole, p)
            report_list.addItem(item)
        for p in students:
            item = QListWidgetItem(f"👤 {p.stem}")
            item.setData(Qt.UserRole, p)
            report_list.addItem(item)
        if report_list.count():
            report_list.setCurrentRow(0)

    def _show_report(item: QListWidgetItem):
        path: Path = item.data(Qt.UserRole)
        report_view.setHtml(
            f"<html><body style='font-family: sans-serif;'>"
            + _markdown_to_html(path.read_text(encoding="utf-8"), path.parent)
            + "</body></html>"
        )

    report_list.currentItemChanged.connect(lambda cur, _prev: _show_report(cur) if cur else None)
    refresh_btn.clicked.connect(_refresh_reports)
    tabs.addTab(reports_tab, "Reports")

    # ---- Tab 4: Data quality ----
    quality_tab = QWidget()
    qual_layout = QVBoxLayout(quality_tab)
    quality_label = QLabel("<i>Loading quality summary…</i>")
    quality_label.setWordWrap(True)
    qual_layout.addWidget(quality_label)

    def _refresh_quality():
        qpath = OUT_DIR / "data_quality_summary.json"
        if not qpath.exists():
            quality_label.setText("<i>No quality summary yet — run the pipeline first.</i>")
            return
        q = json.loads(qpath.read_text(encoding="utf-8"))
        lines = [
            f"<b>Total records:</b> {q.get('total_records')} &nbsp; "
            f"<b>Records with derived %:</b> {q.get('records_with_derived_percent')} &nbsp; "
            f"<b>Unique students:</b> {q.get('unique_students')}",
            "",
            "<table cellpadding='6' cellspacing='0' border='1' style='border-collapse: collapse;'>",
            "<tr><th>Check</th><th>Count</th><th>Severity</th></tr>",
        ]
        for iss in q.get("issues", []):
            lines.append(f"<tr><td>{iss['check']}</td><td>{iss['count']}</td><td>{iss['severity']}</td></tr>")
        if not q.get("issues"):
            lines.append("<tr><td colspan='3'>No issues found 🎉</td></tr>")
        lines.append("</table>")
        quality_label.setText("".join(lines))

    _refresh_quality()
    tabs.addTab(quality_tab, "Data quality")

    # ---- Menu ----
    menu = window.menuBar()
    file_menu = menu.addMenu("&File")
    open_folder = QAction("Open output folder", window)
    open_folder.triggered.connect(lambda: _open_url(OUT_DIR))
    file_menu.addAction(open_folder)
    help_menu = menu.addMenu("&Help")
    about = QAction("About", window)
    about.triggered.connect(lambda: _about(window))
    help_menu.addAction(about)

    _refresh_reports()
    return window


def _home_stats() -> str:
    qpath = OUT_DIR / "data_quality_summary.json"
    if not qpath.exists():
        return "<i>Run the pipeline to see dataset statistics here.</i>"
    q = json.loads(qpath.read_text(encoding="utf-8"))
    return (
        f"<b>Last run:</b> {q.get('total_records')} records · "
        f"{q.get('unique_students')} students · "
        f"{q.get('records_with_derived_percent')} with derived % · "
        f"{q.get('issue_count_types', 0)} issue types flagged."
    )


def _open_url(path: Path) -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def _about(parent) -> None:
    from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

    dialog = QDialog(parent)
    dialog.setWindowTitle("About")
    dialog.resize(560, 380)
    layout = QVBoxLayout(dialog)
    label = QLabel(
        "<h2>Stardom Progress Report Generator</h2>"
        "<p><b>What this app is for:</b> turning Stardom school's 2026-2027 assessment "
        "workbook into ready-to-share progress reports.</p>"
        "<ol>"
        "<li><b>Extract</b> — reads each class sheet into assessment records.</li>"
        "<li><b>Enrich</b> — classifies subjects/types and derives percentages.</li>"
        "<li><b>Quality checks</b> — flags missing/duplicate/out-of-range data.</li>"
        "<li><b>Reports</b> — Markdown class & student reports with charts.</li>"
        "</ol>"
        "<p>Use the <b>Run pipeline</b> tab to regenerate reports, then browse them in "
        "the <b>Reports</b> tab.</p>"
        "<p><i>Privacy:</i> reports contain real student names — handle with care.</p>"
    )
    label.setWordWrap(True)
    layout.addWidget(label)
    dialog.exec()


def main() -> int:
    ap = argparse.ArgumentParser(description="Stardom Progress Report Generator desktop app")
    ap.add_argument("--smoke", action="store_true", help="Headless smoke test (screenshot + exit)")
    ap.add_argument("--smoke-out", default=str(ROOT / "smoke_screenshot.png"), help="Smoke screenshot path")
    args = ap.parse_args()

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = build_gui(app)

    if args.smoke:
        from PySide6.QtCore import QTimer

        results = {"done": False}

        def _shot():
            window.grab().save(args.smoke_out)
            print(f"smoke screenshot: {args.smoke_out}")
            results["done"] = True
            app.quit()

        QTimer.singleShot(1500, _shot)
        QTimer.singleShot(30000, app.quit)
        window.show()
        app.exec()
        return 0 if results["done"] else 2

    window.show()
    return int(app.exec())


if __name__ == "__main__":
    sys.exit(main())
