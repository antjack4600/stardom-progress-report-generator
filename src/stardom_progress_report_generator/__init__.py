def main() -> None:
    """Launch the desktop app (PySide6 GUI for the report pipeline)."""
    import runpy
    from pathlib import Path

    app = Path(__file__).resolve().parents[2] / "desktop_app.py"
    runpy.run_path(str(app), run_name="__main__")
