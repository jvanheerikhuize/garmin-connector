"""
Embedded HTTP Server for the Garmin Connector GUI (Lean MVP).
"""

from __future__ import annotations
import json
import mimetypes
import urllib.parse
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

from ..converter.fit_encoder import Sport
from ..converter.gpx_parser import parse_gpx_string
from ..converter.gpx_to_fit import convert_gpx_to_fit
from ..device.detector import GarminDeviceDetector
from ..device.manager import GarminDeviceManager
import fitparse
import io


STATIC_DIR = Path(__file__).parent / "static"


class GarminGUIRequestHandler(BaseHTTPRequestHandler):

    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(HTTPStatus.NO_CONTENT)

    def _send_json(self, data: dict | list, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self._set_headers(status, "application/json")
        self.wfile.write(body)

    def _send_error_json(self, msg: str, status: int = 400):
        self._send_json({"success": False, "error": msg}, status)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            index_file = STATIC_DIR / "index.html"
            if index_file.exists():
                content = index_file.read_bytes()
                self._set_headers(200, "text/html; charset=utf-8")
                self.wfile.write(content)
            else:
                self._send_error_json("index.html not found", 404)
            return

        # Static assets
        if path.startswith("/static/"):
            rel_name = path[len("/static/"):]
            asset_path = (STATIC_DIR / rel_name).resolve()
            if asset_path.exists() and asset_path.is_file() and STATIC_DIR in asset_path.parents:
                mime_type, _ = mimetypes.guess_type(str(asset_path))
                self._set_headers(200, mime_type or "application/octet-stream")
                self.wfile.write(asset_path.read_bytes())
            else:
                self._send_error_json("Asset not found", 404)
            return

        # API: Device Status
        if path == "/api/device":
            device = GarminDeviceDetector.get_first_device()
            if device:
                self._send_json({
                    "connected": True,
                    "model_name": device.model_name,
                    "unit_id": device.unit_id,
                    "mount_point": str(device.mount_point),
                })
            else:
                self._send_json({
                    "connected": False,
                    "model_name": None,
                })
            return

        # API: List Courses
        if path == "/api/courses":
            device = GarminDeviceDetector.get_first_device()
            if not device:
                self._send_json({"connected": False, "courses": []})
                return

            try:
                manager = GarminDeviceManager(device=device)
                courses = manager.list_courses()
                c_list = [
                    {
                        "filename": c.filename,
                        "full_path": str(c.full_path),
                        "watch_path": f"/GARMIN/{'NewFiles' if 'NEWFILES' in c.location.upper() else 'Courses'}/{c.filename}",
                        "size_bytes": c.size_bytes,
                        "location": c.location,
                        "modified_at": c.modified_at.isoformat(),
                    }
                    for c in courses
                ]
                self._send_json({"connected": True, "courses": c_list})
            except Exception as e:
                self._send_error_json(str(e), 500)
            return

                # API: Fetch Course for mapping (New MVP feature)
        if path.startswith("/api/fetch-course/"):
            filename = urllib.parse.unquote(path[len("/api/fetch-course/"):])
            device = GarminDeviceDetector.get_first_device()
            if not device:
                self._send_error_json("No Garmin device connected", 503)
                return
            
            try:
                manager = GarminDeviceManager(device=device)
                courses = manager.list_courses()
                course = next((c for c in courses if c.filename == filename), None)
                if not course:
                    self._send_error_json("Course not found on watch", 404)
                    return
                
                course_path = course.full_path
                if not course_path.exists():
                    self._send_error_json("File missing from watch storage", 404)
                    return
                
                points = []
                if filename.lower().endswith(".fit"):
                    fitfile = fitparse.FitFile(course_path.read_bytes())
                    for record in fitfile.get_messages('record'):
                        lat = None
                        lon = None
                        for data in record:
                            if data.name == 'position_lat' and data.value is not None:
                                lat = data.value * (180.0 / (2**31))
                            elif data.name == 'position_long' and data.value is not None:
                                lon = data.value * (180.0 / (2**31))
                        if lat is not None and lon is not None:
                            points.append([lat, lon])
                elif filename.lower().endswith(".gpx"):
                    from ..converter.gpx_parser import parse_gpx_file
                    cdata = parse_gpx_file(course_path)
                    for pt in cdata.points:
                        if pt.lat is not None and pt.lon is not None:
                            points.append([pt.lat, pt.lon])
                
                self._send_json({"success": True, "points": points})
            except Exception as e:
                self._send_error_json(str(e), 500)
            return

        self._send_error_json("Not found", 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/sideload":
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_error_json("Empty request", 400)
                return

            body = self.rfile.read(content_length).decode("utf-8")
            device = GarminDeviceDetector.get_first_device()
            if not device:
                self._send_error_json("No Garmin device connected", 503)
                return

            try:
                payload = json.loads(body)
                gpx_content = payload.get("gpx_content")
                course_name = payload.get("course_name", "MVP_Course")
                sport_str = payload.get("sport", "cycling")

                if not gpx_content:
                    self._send_error_json("Missing gpx_content", 400)
                    return

                sport_enum = Sport.CYCLING
                if sport_str == "hiking":
                    sport_enum = Sport.HIKING
                elif sport_str == "running":
                    sport_enum = Sport.RUNNING

                # Parse GPX
                course_data = parse_gpx_string(gpx_content, course_name=course_name, sport=sport_enum)

                # Write to temp file with proper name
                import tempfile
                import re
                
                # Create a safe filename from the course name
                safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', course_name)
                if not safe_name:
                    safe_name = "Course"
                
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_fit_path = Path(tmp_dir) / f"{safe_name}.fit"
                    from ..converter.fit_encoder import FitCourseEncoder
                    encoder = FitCourseEncoder(course=course_data)
                    fit_bytes = encoder.encode()
                    tmp_fit_path.write_bytes(fit_bytes)
                    
                    # Sideload
                    manager = GarminDeviceManager(device=device)
                    dest = manager.sideload_route(tmp_fit_path)

                self._send_json({
                    "success": True,
                    "filename": dest.name,
                    "course_name": course_data.name,
                    "distance_meters": course_data.total_distance,
                })
            except Exception as e:
                self._send_error_json(str(e), 500)
            return

        self._send_error_json("Not found", 404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/courses/"):
            filename = path[len("/api/courses/"):]
            device = GarminDeviceDetector.get_first_device()
            if not device:
                self._send_error_json("No Garmin device connected", 503)
                return

            manager = GarminDeviceManager(device=device)
            deleted = manager.delete_course(filename)
            if deleted:
                self._send_json({"success": True, "filename": filename})
            else:
                self._send_error_json(f"Course '{filename}' not found", 404)
            return

        self._send_error_json("Not found", 404)

    def log_message(self, format, *args):
        # Quiet standard HTTP logs
        return

def run_gui_server(host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    server_address = (host, port)
    httpd = HTTPServer(server_address, GarminGUIRequestHandler)
    return httpd
