import argparse
import sys

from garmin_connector.gui.launcher import launch_gui


def _run_gui(args: argparse.Namespace) -> None:
    launch_gui(host=args.host, port=args.port, open_browser=not args.no_browser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garmin-connector",
        description="Garmin Venu course uploader with a local web GUI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    gui = subparsers.add_parser("gui", help="Launch the local web GUI")
    gui.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    gui.add_argument("--port", "-p", type=int, default=8080, help="Port to listen on (default: 8080)")
    gui.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    gui.set_defaults(func=_run_gui)

    return parser


def main() -> None:
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return
    func(args)


if __name__ == "__main__":
    main()
