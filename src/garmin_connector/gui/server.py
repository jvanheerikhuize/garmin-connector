import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional

from garmin_connector.device.detector import GarminDeviceDetector

STATIC_DIR = Path(__file__).parent / "static"


class GarminRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int) -> None:
        self._send_json({"success": False, "error": message}, status)

    def _send_static(self, relative: str) -> None:
        target = (STATIC_DIR / relative).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            self._send_error_json("Not found", 404)
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length > 0 else b""

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        try:
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send_static("index.html")
            elif path.startswith("/static/"):
                self._send_static(path[len("/static/"):])
            elif path == "/api/device":
                self._handle_device()
            else:
                self._send_error_json("Not found", 404)
        except Exception as exc:
            self._send_error_json(str(exc), 500)

    def _handle_device(self) -> None:
        try:
            device = GarminDeviceDetector.get_first_device()
        except Exception:
            device = None
        if device is None:
            self._send_json({"connected": False, "model_name": None})
            return
        self._send_json(
            {
                "connected": True,
                "model_name": device.model_name,
                "unit_id": device.unit_id,
                "mount_point": str(device.mount_point),
            }
        )


def run_gui_server(host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    server = HTTPServer((host, port), GarminRequestHandler)
    server.daemon_threads = True
    return server
