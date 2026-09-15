import socket
import webbrowser

from garmin_connector.gui.server import run_gui_server


def find_free_port(start_port: int = 8080) -> int:
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    raise RuntimeError(f"No free port found from {start_port} upwards")


def open_desktop_window(url: str) -> None:
    try:
        webbrowser.open(url, new=1)
    except Exception:
        pass


def launch_gui(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True) -> None:
    port = find_free_port(port)
    server = run_gui_server(host, port)
    url = f"http://{host}:{port}/"
    print(f"Garmin Course Uploader running at {url}", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    if open_browser:
        open_desktop_window(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
