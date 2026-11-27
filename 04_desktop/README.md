# Desktop app

Run the native Tkinter version from the project root with:

```powershell
python app.py
```

Python 3.10 or later with Tkinter is required. The desktop app uses the PNG scene backgrounds in `assets/`; regenerate them from the current `index.html` with `powershell -ExecutionPolicy Bypass -File 04_desktop/render_scenes.ps1` on Windows with Microsoft Edge installed.

On this Windows setup, the plain `python` alias is inaccessible. Launch the app with `& "$env:LOCALAPPDATA\Python\bin\python.exe" app.py` in PowerShell. On a computer where Python is on PATH, use `python app.py`.

To run the web version, use `python web.py` from the project root. It serves the unchanged `index.html` locally and opens it in a browser. Press Ctrl+C in the terminal to stop the web server.
