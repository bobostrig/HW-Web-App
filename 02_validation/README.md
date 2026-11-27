# 02_validation

Store hand calculations, validation scripts, and test cases here.

- `validate_desktop.js`: independent reference checks; pass the step number (`1`, `2`, or `3`) to run that step's checks and generate its SVG graph in `03_output/`. Step 1 is the default.
- `test_desktop.py`: tests the desktop app's capacity and portable-checkpoint helpers. Run with `python -m unittest discover -s 02_validation` on a computer with Python 3 and Tkinter.
