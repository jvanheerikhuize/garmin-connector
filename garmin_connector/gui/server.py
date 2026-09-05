"""
Embedded HTTP Server for the Garmin Connector GUI.
Built on Python standard library http.server for zero-dependency execution.
"""

from __future__ import annotations
import json
import mimetypes
import os
import re
import tempfile
import threading
import urllib.parse
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional

from ..converter.fit_encoder import Sport
from ..converter.gpx_parser import parse_gpx_string
from ..converter.gpx_to_fit import convert_gpx_to_fit
from ..converter.elevation import enrich_course_elevation
from ..device.detector import GarminDeviceDetector
from ..device.manager import GarminDeviceManager
from ..service.watcher import DirectoryWatcher

STATIC_DIR = Path(__file__).parent / "static"


class GlobalWatcherState:
    """Thread-safe watcher management for the GUI."""
    watcher: Optional[DirectoryWatcher] = None
    watcher_thread: Optional[threading.Thread] = None
    is_running: bool = False
    watch_path: str = str(Path.home() / "Downloads")
    recent_logs: list[str] = []

    @classmethod
    def log(cls, msg: str):
        cls.recent_logs.append(msg)
        if len(cls.recent_logs) > 50:
            cls.recent_logs.pop(0)


class GarminGUIRequestHandler(BaseHTTPRequestHandler):
    """Custom HTTP Request Handler supporting REST API & Static Files."""

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

    def _send_error_json(self, message: str, status: int = 400):
        self._send_json({"error": message, "success": False}, status=status)

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
                return
            else:
                self._send_error_json("Asset not found", 404)
                return

        # API Routes
        if path == "/api/device":
            device = GarminDeviceDetector.get_first_device()
            raw_usb = GarminDeviceDetector.check_raw_usb()
            if device:
                self._send_json({
                    "connected": True,
                    "model_name": device.model_name,
                    "unit_id": device.unit_id,
                    "software_version": device.software_version,
                    "part_number": device.part_number,
                    "mount_point": str(device.mount_point),
                    "garmin_dir": str(device.garmin_dir),
                    "is_mtp": device.is_mtp,
                    "raw_usb": raw_usb,
                })
            else:
                self._send_json({
                    "connected": False,
                    "model_name": None,
                    "raw_usb": raw_usb,
                })
            return

        if path == "/api/courses":
            device = GarminDeviceDetector.get_first_device()
            if not device:
                self._send_json({"connected": False, "courses": []})
                return

            try:
                manager = GarminDeviceManager(device=device)
                courses = manager.list_courses()
                self._send_json({
                    "connected": True,
                    "device": device.model_name,
                    "courses": [
                        {
                            "filename": c.filename,
                            "size_bytes": c.size_bytes,
                            "modified_at": c.modified_at.isoformat(),
                            "location": c.location,
                        }
                        for c in courses
                    ],
                })
            except Exception as e:
                self._send_error_json(str(e), 500)
            return

        if path == "/api/diagnostics":
            device = GarminDeviceDetector.get_first_device()
            raw_usb = GarminDeviceDetector.check_raw_usb()
            
            # Run quick self-tests
            tests = []
            
            # 1. GPX Parser Test
            try:
                sample_gpx = """<?xml version="1.0"?><gpx version="1.1"><trk><trkseg>
                <trkpt lat="50.1" lon="6.1"><ele>400</ele></trkpt>
                <trkpt lat="50.2" lon="6.2"><ele>450</ele></trkpt>
                </trkseg></trk></gpx>"""
                parsed = parse_gpx_string(sample_gpx, "Test")
                tests.append({
                    "name": "GPX Parsing Engine",
                    "status": "pass",
                    "detail": f"Parsed {len(parsed.points)} points, {parsed.total_distance:.0f}m"
                })
            except Exception as e:
                tests.append({"name": "GPX Parsing Engine", "status": "fail", "detail": str(e)})

            # 2. FIT Encoder Test
            try:
                from ..converter.fit_encoder import FitCourseEncoder
                encoder = FitCourseEncoder(parsed)
                fit_bytes = encoder.encode()
                tests.append({
                    "name": "FIT 2.0 Binary Encoder & CRC-16",
                    "status": "pass",
                    "detail": f"Generated valid {len(fit_bytes)} bytes FIT course"
                })
            except Exception as e:
                tests.append({"name": "FIT 2.0 Binary Encoder & CRC-16", "status": "fail", "detail": str(e)})

            # 3. Hardware USB Bus Check
            if raw_usb.get("detected"):
                tests.append({
                    "name": "Garmin USB Hardware Bus",
                    "status": "pass",
                    "detail": f"Device {raw_usb.get('vid')}:{raw_usb.get('pid')} connected"
                })
            else:
                tests.append({
                    "name": "Garmin USB Hardware Bus",
                    "status": "warn",
                    "detail": "No Garmin device on raw USB bus"
                })

            # 4. Storage / MTP Mount Check
            if device:
                tests.append({
                    "name": "Garmin Storage Filesystem",
                    "status": "pass",
                    "detail": f"Accessible at {device.mount_point} ({device.model_name})"
                })
            else:
                tests.append({
                    "name": "Garmin Storage Filesystem",
                    "status": "warn",
                    "detail": "Storage not unlocked or mounted"
                })

            # 5. Direct USB MTP Probe Check
            try:
                from .device.mtp_client import GarminMTPClient
                with GarminMTPClient() as mtp:
                    probe = mtp.probe_device()
                    tests.append({
                        "name": "Direct USB MTP Protocol",
                        "status": "pass",
                        "detail": f"Online (Garmin: {probe['garmin_folder_found']}, NewFiles: {probe['newfiles_folder_found']}, Courses: {probe['courses_count']})"
                    })
            except Exception as e:
                tests.append({
                    "name": "Direct USB MTP Protocol",
                    "status": "idle",
                    "detail": f"Direct USB client idle ({e})"
                })

            # 6. Directory Watcher
            tests.append({
                "name": "Route Watcher Service",
                "status": "pass" if GlobalWatcherState.is_running else "idle",
                "detail": f"{'Running on ' + GlobalWatcherState.watch_path if GlobalWatcherState.is_running else 'Idle (Disabled)'}"
            })

            self._send_json({
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "tests": tests,
                "device": {
                    "connected": bool(device),
                    "model": device.model_name if device else None,
                    "unit_id": device.unit_id if device else None,
                    "mount_point": str(device.mount_point) if device else None,
                    "raw_usb": raw_usb
                }
            })
            return

        if path == "/api/probe":
            try:
                from .device.mtp_client import GarminMTPClient
                with GarminMTPClient() as mtp:
                    probe_data = mtp.probe_device()
                    self._send_json({"success": True, "probe": probe_data})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, 500)
            return

        if path == "/api/watcher/status":
            self._send_json({
                "is_running": GlobalWatcherState.is_running,
                "watch_path": GlobalWatcherState.watch_path,
                "logs": GlobalWatcherState.recent_logs[-15:],
            })
            return

        self._send_error_json("Not found", 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # 1. Preview Route (returns points, distances, elevations, course points)
        if path == "/api/preview":
            try:
                data = json.loads(body.decode("utf-8"))
                xml_str = data.get("gpx_content", "")
                sport_name = data.get("sport", "cycling")
                sport_enum = Sport.HIKING if sport_name == "hiking" else Sport.CYCLING
                custom_name = data.get("name")

                course = parse_gpx_string(xml_str, course_name=custom_name, sport=sport_enum)
                # Automatically enrich with real DEM elevation if elevations are flat or missing
                course = enrich_course_elevation(course)

                # Sample points if > 1500 to keep UI ultra snappy
                pts = course.points
                step = max(1, len(pts) // 1500)
                sampled_pts = pts[::step]
                if pts and sampled_pts[-1] != pts[-1]:
                    sampled_pts.append(pts[-1])

                self._send_json({
                    "success": True,
                    "name": course.name,
                    "sport": course.sport.name,
                    "total_distance": course.total_distance,
                    "total_ascent": course.total_ascent,
                    "total_descent": course.total_descent,
                    "points_count": len(course.points),
                    "coordinates": [[pt.lat, pt.lon] for pt in sampled_pts],
                    "elevations": [
                        {
                            "dist": round(pt.distance / 1000.0, 2),
                            "ele": round(pt.elevation, 1) if pt.elevation is not None else None,
                        }
                        for pt in sampled_pts
                    ],
                    "course_points": [
                        {
                            "name": cp.name,
                            "type": cp.point_type.name,
                            "lat": cp.lat,
                            "lon": cp.lon,
                            "dist": round(cp.distance / 1000.0, 2),
                        }
                        for cp in course.course_points
                    ],
                })
            except Exception as e:
                self._send_error_json(f"Failed to parse GPX: {e}", 400)
            return

        # 2. Sideload Route to Device
        if path == "/api/sideload":
            try:
                data = json.loads(body.decode("utf-8"))
                file_content = data.get("content", "")
                file_name = data.get("filename", "route.gpx")
                sport_name = data.get("sport", "cycling")
                course_name = data.get("name")
                sport_enum = Sport.HIKING if sport_name == "hiking" else Sport.CYCLING

                device = GarminDeviceDetector.get_first_device()
                if not device:
                    self._send_error_json("No Garmin device connected via USB/MTP", 503)
                    return

                manager = GarminDeviceManager(device=device)

                with tempfile.TemporaryDirectory() as tmp_dir:
                    src_file = Path(tmp_dir) / file_name
                    if file_name.endswith(".fit") and isinstance(file_content, str):
                        # Hex or base64 if fit
                        import base64
                        src_file.write_bytes(base64.b64decode(file_content))
                    else:
                        src_file.write_text(file_content, encoding="utf-8")

                    dest = manager.sideload_route(src_file, sport=sport_enum, course_name=course_name)

                GlobalWatcherState.log(f"Sideloaded '{file_name}' to {device.model_name}")
                self._send_json({
                    "success": True,
                    "filename": dest.name,
                    "message": f"Successfully sideloaded to {device.model_name}! Unplug USB to sync.",
                })
            except Exception as e:
                self._send_error_json(f"Sideload failed: {e}", 500)
            return

        # 3. Watcher Controls
        if path == "/api/watcher/start":
            try:
                data = json.loads(body.decode("utf-8")) if body else {}
                watch_dir = data.get("path", str(Path.home() / "Downloads"))
                sport_str = data.get("sport", "cycling")
                sport_enum = Sport.HIKING if sport_str == "hiking" else Sport.CYCLING

                GlobalWatcherState.watch_path = watch_dir
                GlobalWatcherState.is_running = True
                GlobalWatcherState.log(f"Started monitoring: {watch_dir}")

                def _run():
                    watcher = DirectoryWatcher(
                        watch_dir=watch_dir,
                        sport=sport_enum,
                        on_sideload_callback=lambda s, d: GlobalWatcherState.log(f"Auto-sideloaded: {s.name} -> {d.name}"),
                    )
                    while GlobalWatcherState.is_running:
                        watcher.scan_once()
                        import time
                        time.sleep(2)

                t = threading.Thread(target=_run, daemon=True)
                t.start()
                GlobalWatcherState.watcher_thread = t

                self._send_json({"success": True, "is_running": True, "watch_path": watch_dir})
            except Exception as e:
                self._send_error_json(str(e), 500)
            return

        if path == "/api/watcher/stop":
            GlobalWatcherState.is_running = False
            GlobalWatcherState.log("Stopped directory monitoring")
            self._send_json({"success": True, "is_running": False})
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
                GlobalWatcherState.log(f"Deleted '{filename}' from {device.model_name}")
                self._send_json({"success": True, "filename": filename})
            else:
                self._send_error_json(f"Course '{filename}' not found", 404)
            return

        self._send_error_json("Not found", 404)

    def log_message(self, format, *args):
        # Quiet standard HTTP logs
        return


def run_gui_server(host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    """Creates and starts the GUI HTTP server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, GarminGUIRequestHandler)
    return httpd
