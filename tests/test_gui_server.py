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
        self.assertIn("Garmin Course Uploader", content)

