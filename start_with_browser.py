#!/usr/bin/env python3
"""
Helper to run `python manage.py runserver` and open the default browser
to http://127.0.0.1:8000/ once Django reports the server is listening.
Run with: python start_with_browser.py
"""
import sys
import subprocess
import threading
import webbrowser

URL = "http://127.0.0.1:8000/server-output/"

# Ensure logs directory exists and open the log file for appending
import os
os.makedirs("logs", exist_ok=True)
log_file_path = os.path.join("logs", "server_output.log")

proc = subprocess.Popen([sys.executable, "manage.py", "runserver"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

def monitor_output(pipe):
    for line in pipe:
        # Append to a file that the web viewer will tail (do not echo to terminal)
        try:
            with open(log_file_path, "a", encoding="utf-8", errors="replace") as lf:
                lf.write(line)
        except Exception:
            pass
        # When Django starts the server, open the browser once
        if "Starting development server at" in line or "http://127.0.0.1:8000/" in line:
            try:
                webbrowser.open_new_tab(URL)
            except Exception:
                pass

thread = threading.Thread(target=monitor_output, args=(proc.stdout,))
thread.daemon = True
thread.start()

# Wait for server process to exit
proc.wait()
thread.join()
