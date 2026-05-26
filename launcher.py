import subprocess
import sys
import os
import webbrowser
import time

base_dir = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(base_dir, "app.py")

cmd = [
    sys.executable,
    "-m",
    "streamlit",
    "run",
    app_path,
    "--server.headless=true",
    "--server.port=8501"
]

process = subprocess.Popen(cmd)

time.sleep(8)
webbrowser.open("http://localhost:8501")

process.wait()