"""
GUI Launcher for Garmin Connector.
Runs embedded HTTP server and opens GUI in a desktop app window or default browser.
"""

from __future__ import annotations
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from .server import run_gui_server


def find_free_port(start_port: int = 8080) -> int:
    """Finds an available local port starting from start_port."""
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


def open_desktop_window(url: str):
    """Attempts to open in dedicated app window (Chrome/Chromium app mode) or system browser."""
    # Try Google Chrome / Chromium app mode
    for browser_cmd in ["google-chrome", "chromium-browser", "chromium", "brave-browser"]:
        if shutil.which(browser_cmd):
            try:
                subprocess.Popen([browser_cmd, f"--app={url}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass

    # Fallback to standard browser
    webbrowser.open(url)


def launch_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    """Launches the Garmin Connector GUI application."""
    actual_port = find_free_port(port)
    url = f"http://{host}:{actual_port}"

    server = run_gui_server(host, actual_port)

    print(f"\n=======================================================")
    print(f"🚀 Garmin Connector GUI running at: {url}")
    print(f"=======================================================\n")

    if open_browser:
        # Launch browser in separate thread after server starts
        threading.Thread(target=lambda: (time.sleep(0.4), open_desktop_window(url)), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[GUI] Shutting down server...")
        server.server_close()
        print("[GUI] Closed.")


if __name__ == "__main__":
    launch_gui()
