"""
Garmin Connector GUI Module.
Provides modern web-based desktop GUI with interactive GPS map preview, elevation charts,
device discovery, and course management.
"""

from .launcher import launch_gui
from .server import run_gui_server

__all__ = ["launch_gui", "run_gui_server"]
