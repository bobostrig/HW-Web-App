# 02_validation

Store hand calculations, validation scripts, and test cases here.

- `validate_desktop.js`: independent reference checks, including proportionality and symmetry properties for every step and crane mirror and turn properties from step 2 onward; pass the step number (`1`, `2`, or `3`) to run that step's checks and generate its SVG graph in `03_output/`. Step 1 is the default.
- `test_desktop.py`: tests the desktop app's capacity, portable-checkpoint helpers, and selected gameplay flows. Run with `python -m unittest discover -s 02_validation` on a computer with Python 3.10 or later and Tkinter.
- `gui_checks.py`: runs the nine Tkinter acceptance checks, including the live graph, pause, portable save/load in a fresh app instance, hazards, failure, and all five levels. Run with `python 02_validation/gui_checks.py` on a machine with a desktop display.
- `capture_desktop.py`: saves four Step 3 review screenshots in `03_output/`. It requires Tkinter, a desktop display, and Pillow (`PIL`).

On this Windows setup, the plain `python` alias is inaccessible. Use `& "$env:LOCALAPPDATA\Python\bin\python.exe"` in PowerShell in place of `python` for these commands.
