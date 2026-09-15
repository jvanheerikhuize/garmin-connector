import json
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from garmin_connector.device.detector import GarminDeviceDetector
from garmin_connector.gui.server import run_gui_server

EXAMPLE_GPX = Path(__file__).parent.parent / "examples" / "sample_hiking_route.gpx"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestCourseManagementApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.server = run_gui_server("127.0.0.1", cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.garmin_dir = root / "GARMIN"
        (self.garmin_dir / "NEWFILES").mkdir(parents=True)
        (self.garmin_dir / "COURSES").mkdir()
        device = GarminDeviceDetector.get_first_device(custom_path=root)
        self.patcher = mock.patch.object(GarminDeviceDetector, "get_first_device", return_value=device)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def _request(self, method, path, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    def test_device_reports_connected(self):
        status, data = self._request("GET", "/api/device")
        self.assertEqual(status, 200)
        self.assertTrue(data["connected"])
        self.assertEqual(data["model_name"], "Garmin Generic")
        self.assertEqual(data["mount_point"], self.tmp.name)

    def test_sideload_list_fetch_delete_roundtrip(self):
        status, data = self._request("GET", "/api/courses")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"connected": True, "courses": []})

        gpx_content = EXAMPLE_GPX.read_text(encoding="utf-8")
        status, data = self._request(
            "POST", "/api/sideload", {"gpx_content": gpx_content, "course_name": "Alps Trail!", "sport": "hiking"}
        )
        self.assertEqual(status, 200, data)
        self.assertTrue(data["success"])
        self.assertEqual(data["filename"], "Alps_Trail_.fit")
        self.assertEqual(data["course_name"], "Alps Trail!")
        self.assertGreater(data["distance_meters"], 1000)
        self.assertTrue((self.garmin_dir / "NEWFILES" / "Alps_Trail_.fit").is_file())

        status, data = self._request("GET", "/api/courses")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["courses"]), 1)
        course = data["courses"][0]
        self.assertEqual(course["filename"], "Alps_Trail_.fit")
        self.assertEqual(course["location"], "NEWFILES (Pending Sync)")
        self.assertEqual(course["watch_path"], "/GARMIN/NewFiles/Alps_Trail_.fit")
        self.assertIn("modified_at", course)

        status, data = self._request("GET", "/api/fetch-course/Alps_Trail_.fit")
        self.assertEqual(status, 200, data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["points"]), 6)
        self.assertAlmostEqual(data["points"][0][0], 46.5196, places=4)
        self.assertAlmostEqual(data["points"][0][1], 8.5601, places=4)

        status, data = self._request("DELETE", "/api/courses/Alps_Trail_.fit")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"success": True, "filename": "Alps_Trail_.fit"})
        self.assertFalse((self.garmin_dir / "NEWFILES" / "Alps_Trail_.fit").exists())

    def test_fetch_course_from_gpx_in_courses_dir(self):
        target = self.garmin_dir / "COURSES" / "trail.gpx"
        target.write_text(EXAMPLE_GPX.read_text(encoding="utf-8"), encoding="utf-8")
        status, data = self._request("GET", "/api/courses")
        self.assertEqual(data["courses"][0]["watch_path"], "/GARMIN/Courses/trail.gpx")
        status, data = self._request("GET", "/api/fetch-course/trail.gpx")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["points"]), 6)

    def test_error_paths(self):
        status, data = self._request("GET", "/api/fetch-course/missing.fit")
        self.assertEqual((status, data), (404, {"success": False, "error": "Course not found on watch"}))

        status, data = self._request("DELETE", "/api/courses/missing.fit")
        self.assertEqual((status, data), (404, {"success": False, "error": "Course 'missing.fit' not found"}))

        status, data = self._request("POST", "/api/sideload", {"course_name": "x"})
        self.assertEqual((status, data), (400, {"success": False, "error": "Missing gpx_content"}))

        req = urllib.request.Request(self.base + "/api/sideload", data=b"", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req)
        self.assertEqual(ctx.exception.code, 400)
        self.assertEqual(json.loads(ctx.exception.read()), {"success": False, "error": "Empty request"})

        status, data = self._request("POST", "/api/sideload", {"gpx_content": "<gpx></gpx>"})
        self.assertEqual(status, 500)
        self.assertFalse(data["success"])

    def test_no_device_degrades_gracefully(self):
        with mock.patch.object(GarminDeviceDetector, "get_first_device", return_value=None):
            status, data = self._request("GET", "/api/courses")
            self.assertEqual((status, data), (200, {"connected": False, "courses": []}))
            status, data = self._request("POST", "/api/sideload", {"gpx_content": "<gpx/>"})
            self.assertEqual((status, data), (503, {"success": False, "error": "No Garmin device connected"}))
            status, data = self._request("DELETE", "/api/courses/x.fit")
            self.assertEqual((status, data), (503, {"success": False, "error": "No Garmin device connected"}))
            status, data = self._request("GET", "/api/fetch-course/x.fit")
            self.assertEqual((status, data), (503, {"success": False, "error": "No Garmin device connected"}))


if __name__ == "__main__":
    unittest.main()
