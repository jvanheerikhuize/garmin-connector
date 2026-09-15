import json
import mimetypes
import re
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import unquote

from fitparse import FitFile

from garmin_connector.converter.fit_encoder import FitCourseEncoder, Sport
from garmin_connector.converter.gpx_parser import parse_gpx_file, parse_gpx_string
from garmin_connector.device.detector import GarminDeviceDetector, GarminDeviceInfo
from garmin_connector.device.manager import GarminDeviceManager

STATIC_DIR = Path(__file__).parent / "static"
NO_DEVICE_ERROR = "No Garmin device connected"
DEFAULT_SIDELOAD_COURSE_NAME = "MVP_Course"
SEMICIRCLES_TO_DEGREES = 180.0 / 2**31

_SPORT_BY_NAME = {
    "cycling": Sport.CYCLING,
    "hiking": Sport.HIKING,
    "running": Sport.RUNNING,
}


def _watch_path(location: str, filename: str) -> str:
    folder = "NewFiles" if "NEWFILES" in location.upper() else "Courses"
    return f"/GARMIN/{folder}/{filename}"


def _safe_course_filename(course_name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", course_name) or "Course"


def _extract_fit_points(path: Path) -> List[List[float]]:
    points: List[List[float]] = []
    for record in FitFile(str(path)).get_messages("record"):
        lat = record.get_value("position_lat")
        lon = record.get_value("position_long")
        if lat is None or lon is None:
            continue
        points.append([lat * SEMICIRCLES_TO_DEGREES, lon * SEMICIRCLES_TO_DEGREES])
    return points


def _extract_gpx_points(path: Path) -> List[List[float]]:
    course = parse_gpx_file(path)
    return [[p.lat, p.lon] for p in course.points if p.lat is not None and p.lon is not None]


class GarminRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int) -> None:
        self._send_json({"success": False, "error": message}, status)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

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
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length > 0 else b""

    @staticmethod
    def _detect_device() -> Optional[GarminDeviceInfo]:
        try:
            return GarminDeviceDetector.get_first_device()
        except Exception:
            return None

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
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
            elif path == "/api/courses":
                self._handle_list_courses()
            elif path.startswith("/api/fetch-course/"):
                self._handle_fetch_course(unquote(path[len("/api/fetch-course/"):]))
            else:
                self._send_error_json("Not found", 404)
        except Exception as exc:
            self._send_error_json(str(exc), 500)

    def do_POST(self) -> None:
        try:
            path = self.path.split("?", 1)[0]
            if path == "/api/sideload":
                self._handle_sideload()
            else:
                self._send_error_json("Not found", 404)
        except Exception as exc:
            self._send_error_json(str(exc), 500)

    def do_DELETE(self) -> None:
        try:
            path = self.path.split("?", 1)[0]
            if path.startswith("/api/courses/"):
                self._handle_delete_course(unquote(path[len("/api/courses/"):]))
            else:
                self._send_error_json("Not found", 404)
        except Exception as exc:
            self._send_error_json(str(exc), 500)

    def _handle_device(self) -> None:
        device = self._detect_device()
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

    def _handle_list_courses(self) -> None:
        device = self._detect_device()
        if device is None:
            self._send_json({"connected": False, "courses": []})
            return
        try:
            courses = GarminDeviceManager(device=device).list_courses()
        except Exception as exc:
            self._send_error_json(str(exc), 500)
            return
        self._send_json(
            {
                "connected": True,
                "courses": [
                    {
                        "filename": c.filename,
                        "full_path": str(c.full_path),
                        "watch_path": _watch_path(c.location, c.filename),
                        "size_bytes": c.size_bytes,
                        "location": c.location,
                        "modified_at": c.modified_at.isoformat(),
                    }
                    for c in courses
                ],
            }
        )

    def _handle_fetch_course(self, filename: str) -> None:
        device = self._detect_device()
        if device is None:
            self._send_error_json(NO_DEVICE_ERROR, 503)
            return
        try:
            courses = GarminDeviceManager(device=device).list_courses()
            match = next((c for c in courses if c.filename == filename), None)
            if match is None:
                self._send_error_json("Course not found on watch", 404)
                return
            if not match.full_path.is_file():
                self._send_error_json("File missing from watch storage", 404)
                return
            if match.full_path.suffix.lower() == ".fit":
                points = _extract_fit_points(match.full_path)
            else:
                points = _extract_gpx_points(match.full_path)
        except Exception as exc:
            self._send_error_json(str(exc), 500)
            return
        self._send_json({"success": True, "points": points})

    def _handle_sideload(self) -> None:
        body = self._read_body()
        if not body:
            self._send_error_json("Empty request", 400)
            return
        device = self._detect_device()
        if device is None:
            self._send_error_json(NO_DEVICE_ERROR, 503)
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            self._send_error_json(f"Invalid JSON body: {exc}", 400)
            return
        gpx_content = payload.get("gpx_content") if isinstance(payload, dict) else None
        if not gpx_content:
            self._send_error_json("Missing gpx_content", 400)
            return
        course_name = payload.get("course_name") or DEFAULT_SIDELOAD_COURSE_NAME
        sport = _SPORT_BY_NAME.get(str(payload.get("sport", "cycling")).lower(), Sport.CYCLING)
        try:
            course = parse_gpx_string(gpx_content, course_name=course_name, sport=sport)
            with tempfile.TemporaryDirectory() as tmp_dir:
                fit_path = Path(tmp_dir) / f"{_safe_course_filename(course_name)}.fit"
                fit_path.write_bytes(FitCourseEncoder(course).encode())
                destination = GarminDeviceManager(device=device).sideload_route(fit_path, sport=sport, course_name=course_name)
        except Exception as exc:
            self._send_error_json(str(exc), 500)
            return
        self._send_json(
            {
                "success": True,
                "filename": destination.name,
                "course_name": course.name,
                "distance_meters": course.total_distance,
            }
        )

    def _handle_delete_course(self, filename: str) -> None:
        device = self._detect_device()
        if device is None:
            self._send_error_json(NO_DEVICE_ERROR, 503)
            return
        try:
            deleted = GarminDeviceManager(device=device).delete_course(filename)
        except Exception as exc:
            self._send_error_json(str(exc), 500)
            return
        if not deleted:
            self._send_error_json(f"Course '{filename}' not found", 404)
            return
        self._send_json({"success": True, "filename": filename})


def run_gui_server(host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    server = HTTPServer((host, port), GarminRequestHandler)
    server.daemon_threads = True
    return server
