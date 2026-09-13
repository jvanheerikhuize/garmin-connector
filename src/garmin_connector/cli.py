"""
Garmin Connector CLI.
Lean MVP version.
"""

from __future__ import annotations
import argparse
import sys
from .device.detector import GarminDeviceDetector
from .gui.launcher import launch_gui

def cmd_gui(args):
    launch_gui(host=args.host, port=args.port, open_browser=not args.no_browser)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garmin-connector",
        description="Sideload and manage hiking & cycling routes on Garmin Venu and other watches (Lean MVP).",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    p_gui = subparsers.add_parser("gui", help="Launch interactive desktop GUI dashboard")
    p_gui.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    p_gui.add_argument("--port", "-p", type=int, default=8080, help="Port (default: 8080)")
    p_gui.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    p_gui.set_defaults(func=cmd_gui)

    return parser

def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
