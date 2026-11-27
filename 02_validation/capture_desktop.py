"""Capture the Step 3 desktop scenes for visual review on Windows."""

import importlib.util
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from PIL import ImageGrab


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "03_output"
SPEC = importlib.util.spec_from_file_location("high_steel_desktop_capture", ROOT / "04_desktop" / "app.py")
APP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(APP)


def capture(root: tk.Tk, name: str) -> None:
    root.update_idletasks()
    root.lift()
    root.update()
    time.sleep(0.2)
    left, top = root.winfo_rootx(), root.winfo_rooty()
    width, height = root.winfo_width(), root.winfo_height()
    screen = ImageGrab.grab()
    scale_x = screen.width / root.winfo_screenwidth()
    scale_y = screen.height / root.winfo_screenheight()
    if width < 800 or height < 500:
        raise RuntimeError(f"Desktop window has unexpected dimensions: {width}x{height}")
    image = ImageGrab.grab(bbox=(round(left * scale_x), round(top * scale_y),
                                round((left + width) * scale_x), round((top + height) * scale_y)))
    path = OUTPUT / name
    image.save(path)
    print(f"Saved {path.name}: {image.width}x{image.height}")


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        root = tk.Tk()
        try:
            with patch.object(APP.HighSteelApp, "_high_score_path", return_value=Path(temp_dir) / "high_score.json"):
                app = APP.HighSteelApp(root)
            capture(root, "desktop-step-3-start.png")
            app.start_game()
            app._cancel_tick()
            app.running = False
            app.turn_from, app.turn_to = 1, -1
            app.turn_started = time.monotonic() - 0.8
            app._draw_scene()
            app._draw_graph()
            capture(root, "desktop-step-3-turn.png")
            app.turn_started = 0.0
            app.orientation = -1
            app.trolley_x = 465
            app._draw_scene()
            app._draw_graph()
            app._update_hud()
            capture(root, "desktop-step-3-left.png")
        finally:
            root.destroy()


if __name__ == "__main__":
    main()
