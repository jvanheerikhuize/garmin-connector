import argparse
import sys
from .gui.launcher import launch_gui

def main():
    parser = argparse.ArgumentParser(prog="garmin-connector")
    subparsers = parser.add_subparsers(dest="command")

    gui_parser = subparsers.add_parser("gui", help="Launch the GUI")
    gui_parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    gui_parser.add_argument("-p", "--port", type=int, default=8080, help="Port to bind to")
    gui_parser.add_argument("--no-browser", action="store_true", help="Do not automatically open a browser")
    gui_parser.set_defaults(func=lambda args: launch_gui(host=args.host, port=args.port, open_browser=not args.no_browser))

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
