import pytest
import threading
import time
import requests
from garmin_connector.gui.server import run_gui_server
from garmin_connector.gui.launcher import find_free_port

def test_skeleton():
    port = find_free_port(8080)
    server = run_gui_server(port=port)
    
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(0.5)
    
    try:
        # 1. GET /api/device
        resp = requests.get(f"http://127.0.0.1:{port}/api/device")
        assert resp.status_code == 200
        data = resp.json()
        assert "connected" in data
        
        # 2. GET / (index.html)
        resp2 = requests.get(f"http://127.0.0.1:{port}/")
        assert resp2.status_code == 200
        assert "Garmin Course Uploader" in resp2.text
        assert "text/html" in resp2.headers["Content-Type"]
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1.0)
