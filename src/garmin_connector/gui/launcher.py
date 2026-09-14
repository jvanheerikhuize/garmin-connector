import socket
import subprocess
import webbrowser
import threading
import time
from .server import run_gui_server

def find_free_port(start_port: int = 8080) -> int:
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return start_port

def open_desktop_window(url: str) -> None:
    browsers = ["google-chrome", "chromium-browser", "chromium", "brave-browser"]
    for browser in browsers:
        try:
            # We don't want to wait for the process to exit
            subprocess.Popen([browser, f"--app={url}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            continue
    webbrowser.open(url)

def launch_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True) -> None:
    actual_port = find_free_port(port)
    server = run_gui_server(host, actual_port)
    url = f"http://{host}:{actual_port}"
    print(f"Server started at {url}")

    if open_browser:
        def deferred_open():
            time.sleep(0.4)
            open_desktop_window(url)
        threading.Thread(target=deferred_open, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()
