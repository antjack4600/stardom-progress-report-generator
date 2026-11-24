# Security Review & Posture — Stardom Assessment Progress Report Generator

Reviewed: 2026-11-24 (full codebase review of this repository).

## Threat model

- **Local, offline** data pipeline: reads a local `.xlsx` workbook, writes local
  CSV/Markdown/PNG reports.
- No network calls, no authentication, no database, no shell usage (`shell=False`).
- Inputs come from files chosen by the operator (trusted local user).

## Findings & fixes

| Severity | Finding | Status |
|---|---|---|
| 🟠 HIGH | Real student PII (names + scores) committed to a **public** GitHub repo | Owner decision: make the repo private, or remove `data/` and `reports/` from public history |
| 🟡 MEDIUM | `safe_name()` allowed leading/trailing dots and `..` runs in output filenames (theoretically allowing odd file names) | **Fixed** in `src/generate_reports.py` — collapses dot runs, strips leading/trailing dots, returns `_` for empty results |
| 🔵 LOW | Console-script entry point was a placeholder (`Hello from …`) | Fixed: launches the desktop app |
| ⚪ INFO | No CI test workflow | Added: GitHub Actions runs `pytest` on push/PR |

No critical vulnerabilities were found:

- No `eval` / `exec` / `os.system` / `shell=True`, no deserialization of untrusted
  data, no secrets or credentials in code, no SSRF, no auth surface.
- The single `subprocess` use (`src/run_pipeline.py`) runs a fixed argument list.
- `uv.lock` pins all dependencies.

## Handling student data

- Treat `data/raw/`, `data/processed/`, and `reports/output/` as **confidential**.
- Reports contain real student names — share only with authorized staff.
- Do not commit future workbooks containing real student names to a public repo.

## Reporting issues

Report security issues privately to the repository owner.
