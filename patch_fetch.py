import re
with open("garmin_connector/gui/server.py", "r") as f:
    content = f.read()

import_statement = """from ..device.manager import GarminDeviceManager
import fitparse
import io
"""

content = content.replace("from ..device.manager import GarminDeviceManager", import_statement)

new_endpoint = """        # API: Fetch Course for mapping (New MVP feature)
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
                
                course_path = device.mount_point / course.location / filename
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
            return"""

content = re.sub(r'# API: Fetch Course for mapping.*?return', new_endpoint, content, flags=re.DOTALL)

with open("garmin_connector/gui/server.py", "w") as f:
    f.write(content)
