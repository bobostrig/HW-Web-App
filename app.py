"""Start the native High Steel desktop app with ``python app.py``."""

from pathlib import Path
import runpy


if __name__ == "__main__":
    desktop_app = Path(__file__).resolve().parent / "04_desktop" / "app.py"
    runpy.run_path(str(desktop_app), run_name="__main__")
