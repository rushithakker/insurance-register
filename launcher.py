import os
import sys
import subprocess
import time
import webbrowser

base_dir = os.path.dirname(os.path.abspath(__file__))
app_path = os.path.join(base_dir, "app.py")

streamlit_cmd = [
    sys.executable,
    "-m",
    "streamlit",
    "run",
    app_path,
    "--server.port=8501",
    "--server.address=127.0.0.1",
    "--server.headless=true",
    "--browser.gatherUsageStats=false"
]

subprocess.Popen(streamlit_cmd, cwd=base_dir)

time.sleep(20)

webbrowser.open("http://127.0.0.1:8501")