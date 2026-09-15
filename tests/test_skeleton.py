import json
import socket
import threading
import unittest
import urllib.request
from unittest import mock

from garmin_connector.device.detector import GarminDeviceDetector
from garmin_connector.gui.server import run_gui_server


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class TestWalkingSkeleton(unittest.TestCase):
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

    def _get_json(self, path):
        with urllib.request.urlopen(self.base + path) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
            return json.loads(resp.read().decode("utf-8"))

    def test_device_endpoint_is_well_formed(self):
        data = self._get_json("/api/device")
        self.assertIn("connected", data)
        self.assertIn("model_name", data)
        self.assertIsInstance(data["connected"], bool)
        if data["connected"]:
            self.assertIsInstance(data["model_name"], str)
            self.assertIn("mount_point", data)
        else:
            self.assertIsNone(data["model_name"])

    def test_device_endpoint_without_watch(self):
        with mock.patch.object(GarminDeviceDetector, "get_first_device", return_value=None):
            data = self._get_json("/api/device")
        self.assertEqual(data, {"connected": False, "model_name": None})

    def test_index_page_served(self):
        with urllib.request.urlopen(self.base + "/") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("Garmin Course Uploader", resp.read().decode("utf-8"))

    def test_static_app_js_served(self):
        with urllib.request.urlopen(self.base + "/static/app.js") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("checkDeviceStatus", resp.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
