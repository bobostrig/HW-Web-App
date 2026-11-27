# 02_validation

Store hand calculations, validation scripts, and test cases here.

- `validate_desktop.js`: independent capacity and beam-route reference checks; also generates the SVG milestone graphs in `03_output/`.
- `test_desktop.py`: tests the desktop app's capacity and portable-checkpoint helpers. Run with `python -m unittest discover -s 02_validation` on a computer with Python 3 and Tkinter.
