import json
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from garmin_connector.gui.server import run_gui_server


class TestGUIServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 8991
        cls.server = run_gui_server("127.0.0.1", cls.port)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_gui_index_page(self):
        url = f"http://127.0.0.1:{self.port}/"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        content = req.read().decode("utf-8")
        self.assertIn("Garmin Connector", content)

    def test_api_device_status(self):
        url = f"http://127.0.0.1:{self.port}/api/device"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("connected", data)

    def test_api_preview_gpx(self):
        example_gpx = Path(__file__).parent.parent / "examples" / "sample_hiking_route.gpx"
        gpx_content = example_gpx.read_text(encoding="utf-8")

        url = f"http://127.0.0.1:{self.port}/api/preview"
        req_body = json.dumps({"gpx_content": gpx_content, "sport": "hiking"}).encode("utf-8")
        req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req)

        self.assertEqual(resp.status, 200)
        data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data["success"])
        self.assertEqual(data["name"], "Alps High Trail")
        self.assertGreater(len(data["coordinates"]), 0)
        self.assertGreater(len(data["elevations"]), 0)
        self.assertEqual(len(data["course_points"]), 3)

    def test_api_watcher_status(self):
        url = f"http://127.0.0.1:{self.port}/api/watcher/status"
        req = urllib.request.urlopen(url)
        self.assertEqual(req.status, 200)
        data = json.loads(req.read().decode("utf-8"))
        self.assertIn("is_running", data)


if __name__ == "__main__":
    unittest.main()
