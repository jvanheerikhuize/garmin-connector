import http.server
import json
import mimetypes
import urllib.parse
from pathlib import Path

from ..device.detector import GarminDeviceDetector
from ..device.manager import GarminDeviceManager
from ..converter import parse_gpx_string, Sport

STATIC_DIR = Path(__file__).parent / "static"

class GarminGUIRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass # Suppress logging

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def _send_json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_error(self, code, message):
        self._send_json_response(code, {"success": False, "error": message})

    def do_GET(self):
        try:
            if self.path == "/" or self.path == "/index.html":
                self.serve_static_file("index.html")
            elif self.path.startswith("/static/"):
                self.serve_static_file(self.path[len("/static/"):])
            elif self.path == "/api/device":
                self.handle_api_device()
            elif self.path == "/api/courses":
                self.handle_api_courses()
            elif self.path.startswith("/api/fetch-course/"):
                filename = urllib.parse.unquote(self.path[len("/api/fetch-course/"):])
                self.handle_fetch_course(filename)
            else:
                self._send_error(404, "Not found")
        except Exception as e:
            self._send_error(500, str(e))

    def do_POST(self):
        try:
            if self.path == "/api/sideload":
                self.handle_api_sideload()
            else:
                self._send_error(404, "Not found")
        except Exception as e:
            self._send_error(500, str(e))

    def do_DELETE(self):
        try:
            if self.path.startswith("/api/courses/"):
                filename = urllib.parse.unquote(self.path[len("/api/courses/"):])
                self.handle_delete_course(filename)
            else:
                self._send_error(404, "Not found")
        except Exception as e:
            self._send_error(500, str(e))

    def serve_static_file(self, filename):
        target = (STATIC_DIR / filename).resolve()
        if not target.is_relative_to(STATIC_DIR) or not target.is_file():
            self._send_error(404, "Not found")
            return
        
        mime_type, _ = mimetypes.guess_type(str(target))
        if mime_type is None:
            if target.suffix == ".css":
                mime_type = "text/css"
            elif target.suffix == ".js":
                mime_type = "application/javascript"
            elif target.suffix == ".html":
                mime_type = "text/html; charset=utf-8"
            else:
                mime_type = "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-type", mime_type)
        self.end_headers()
        with open(target, "rb") as f:
            self.wfile.write(f.read())

    def handle_api_device(self):
        device = GarminDeviceDetector.get_first_device()
        if device:
            self._send_json_response(200, {
                "connected": True,
                "model_name": device.model_name,
                "unit_id": device.unit_id,
                "mount_point": str(device.mount_point),
                "is_mtp": device.is_mtp,
                "mounting": False
            })
            return

        raw_usb = GarminDeviceDetector.check_raw_usb()
        if raw_usb.get("detected", False):
            self._send_json_response(200, {
                "connected": False,
                "mounting": True,
                "model_name": None
            })
        else:
            self._send_json_response(200, {
                "connected": False,
                "mounting": False,
                "model_name": None
            })

    def handle_api_courses(self):
        device = GarminDeviceDetector.get_first_device()
        if not device:
            self._send_json_response(200, {"connected": False, "courses": []})
            return
            
        manager = GarminDeviceManager(device=device)
        courses = manager.list_courses()
        
        c_list = []
        for c in courses:
            dir_name = "NewFiles" if "NEWFILES" in c.location.upper() else "Courses"
            c_list.append({
                "filename": c.filename,
                "full_path": str(c.full_path),
                "watch_path": f"/GARMIN/{dir_name}/{c.filename}",
                "size_bytes": c.size_bytes,
                "location": c.location,
                "modified_at": c.modified_at.isoformat()
            })
            
        self._send_json_response(200, {"connected": True, "courses": c_list})

    def handle_fetch_course(self, filename: str):
        device = GarminDeviceDetector.get_first_device()
        if not device:
            self._send_error(503, "No Garmin device connected")
            return
            
        manager = GarminDeviceManager(device=device)
        courses = manager.list_courses()
        c = next((x for x in courses if x.filename == filename), None)
        if not c:
            self._send_error(404, "Course not found on watch")
            return
            
        if not c.full_path.exists():
            self._send_error(404, "File missing from watch storage")
            return
            
        points = []
        if filename.lower().endswith(".fit"):
            try:
                import fitparse
            except ImportError:
                self._send_error(500, "fitparse is required for reading FIT files")
                return
                
            fitfile = fitparse.FitFile(str(c.full_path))
            for record in fitfile.get_messages('record'):
                lat = record.get_value('position_lat')
                lon = record.get_value('position_long')
                if lat is not None and lon is not None:
                    # convert semicircles to degrees
                    lat_deg = lat * (180.0 / (2**31))
                    lon_deg = lon * (180.0 / (2**31))
                    points.append([lat_deg, lon_deg])
        elif filename.lower().endswith(".gpx"):
            from ..converter import parse_gpx_file
            course_data = parse_gpx_file(c.full_path)
            for pt in course_data.points:
                points.append([pt.lat, pt.lon])
                
        self._send_json_response(200, {"success": True, "points": points})

    def handle_api_sideload(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self._send_error(400, "Empty request")
            return
            
        body = self.rfile.read(content_length)
        data = json.loads(body.decode('utf-8'))
        
        gpx_content = data.get("gpx_content")
        if not gpx_content:
            self._send_error(400, "Missing gpx_content")
            return
            
        device = GarminDeviceDetector.get_first_device()
        if not device:
            self._send_error(503, "No Garmin device connected")
            return
            
        course_name_in = data.get("course_name", "MVP_Course")
        sport_str = data.get("sport", "cycling").lower()
        
        sport = Sport.CYCLING
        if sport_str == "hiking":
            sport = Sport.HIKING
        elif sport_str == "running":
            sport = Sport.RUNNING
            
        # Parse GPX
        course = parse_gpx_string(gpx_content, course_name_in, sport)
        
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', course_name_in)
        if not safe_name:
            safe_name = "Course"
            
        manager = GarminDeviceManager(device=device)
        
        import tempfile
        from ..converter import FitCourseEncoder
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_fit = Path(tmpdir) / f"{safe_name}.fit"
            encoder = FitCourseEncoder(course)
            tmp_fit.write_bytes(encoder.encode())
            
            dest = manager.sideload_route(tmp_fit)
            
        self._send_json_response(200, {
            "success": True,
            "filename": dest.name,
            "course_name": course.name,
            "distance_meters": course.total_distance
        })

    def handle_delete_course(self, filename: str):
        device = GarminDeviceDetector.get_first_device()
        if not device:
            self._send_error(503, "No Garmin device connected")
            return
            
        manager = GarminDeviceManager(device=device)
        success = manager.delete_course(filename)
        
        if success:
            self._send_json_response(200, {"success": True, "filename": filename})
        else:
            self._send_error(404, f"Course '{filename}' not found")

def run_gui_server(host: str = "127.0.0.1", port: int = 8080) -> http.server.HTTPServer:
    return http.server.HTTPServer((host, port), GarminGUIRequestHandler)
