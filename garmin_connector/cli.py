"""
Garmin Connector CLI.
Command-line interface to sideload and manage routes on Garmin Venu and other watches.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Optional

from .converter.fit_encoder import Sport
from .converter.gpx_to_fit import convert_gpx_to_fit
from .device.detector import GarminDeviceDetector
from .device.manager import GarminDeviceManager
from .service.watcher import DirectoryWatcher

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
except ImportError:
    console = None


def print_info(msg: str):
    if console:
        console.print(f"[bold cyan]ℹ[/bold cyan] {msg}")
    else:
        print(f"[*] {msg}")


def print_success(msg: str):
    if console:
        console.print(f"[bold green]✔[/bold green] {msg}")
    else:
        print(f"[+] {msg}")


def print_error(msg: str):
    if console:
        console.print(f"[bold red]✖ Error:[/bold red] {msg}")
    else:
        print(f"[-] Error: {msg}", file=sys.stderr)


def cmd_detect(args):
    """Detects and displays information about connected Garmin devices."""
    devices = GarminDeviceDetector.detect_devices(args.mount)
    if not devices:
        print_info("No Garmin device currently detected via USB or MTP.")
        print_info("Tips:")
        print_info("  1. Connect your Garmin watch using the USB cable.")
        print_info("  2. If using MTP mode, ensure your file manager / GVFS mounted the device.")
        print_info("  3. Or specify mount path manually with: garmin-connector detect --mount /path/to/GARMIN")
        return

    for dev in devices:
        if console:
            table = Table(title=f"Garmin Device: {dev.model_name}", show_header=False)
            table.add_column("Property", style="bold green")
            table.add_column("Value")
            table.add_row("Model", dev.model_name)
            if dev.unit_id:
                table.add_row("Unit ID", dev.unit_id)
            if dev.software_version:
                table.add_row("Software Version", dev.software_version)
            if dev.part_number:
                table.add_row("Part Number", dev.part_number)
            table.add_row("Mount Point", str(dev.mount_point))
            table.add_row("GARMIN Directory", str(dev.garmin_dir))
            table.add_row("NEWFILES (Ingest)", str(dev.newfiles_dir) if dev.newfiles_dir else "None")
            table.add_row("COURSES", str(dev.courses_dir) if dev.courses_dir else "None")
            table.add_row("MTP Device", "Yes" if dev.is_mtp else "No")
            console.print(table)
        else:
            print(f"--- Device: {dev.model_name} ---")
            print(f"Unit ID: {dev.unit_id}")
            print(f"Software: {dev.software_version}")
            print(f"Mount: {dev.mount_point}")
            print(f"GARMIN: {dev.garmin_dir}")
            print(f"NEWFILES: {dev.newfiles_dir}")
            print(f"COURSES: {dev.courses_dir}")


def cmd_list(args):
    """Lists courses stored on the watch."""
    try:
        manager = GarminDeviceManager(custom_mount=args.mount)
    except Exception as e:
        print_error(str(e))
        return

    courses = manager.list_courses()
    if not courses:
        print_info(f"No courses found on {manager.device.model_name}.")
        return

    if console:
        table = Table(title=f"Courses on {manager.device.model_name}")
        table.add_column("Filename", style="bold cyan")
        table.add_column("Size", justify="right")
        table.add_column("Status / Location", style="yellow")
        table.add_column("Modified", style="dim")

        for c in courses:
            size_kb = f"{c.size_bytes / 1024:.1f} KB"
            table.add_row(c.filename, size_kb, c.location, c.modified_at.strftime("%Y-%m-%d %H:%M"))
        console.print(table)
    else:
        print(f"Courses on {manager.device.model_name}:")
        for c in courses:
            print(f"  - {c.filename:<30} {c.size_bytes:>8} B  [{c.location}]  {c.modified_at}")


def cmd_push(args):
    """Pushes a GPX or FIT route to the watch."""
    try:
        manager = GarminDeviceManager(custom_mount=args.mount)
    except Exception as e:
        print_error(str(e))
        return

    sport_map = {
        "cycling": Sport.CYCLING,
        "bike": Sport.CYCLING,
        "hiking": Sport.HIKING,
        "hike": Sport.HIKING,
        "walking": Sport.WALKING,
        "running": Sport.RUNNING,
        "run": Sport.RUNNING,
    }
    sport_enum = sport_map.get(args.sport.lower(), Sport.CYCLING)

    for file_str in args.files:
        path = Path(file_str)
        if not path.exists():
            print_error(f"File not found: {file_str}")
            continue

        print_info(f"Processing '{path.name}' (Sport: {sport_enum.name})...")
        try:
            dest = manager.sideload_route(path, sport=sport_enum, course_name=args.name)
            print_success(f"Sideloaded '{path.name}' -> {dest} on {manager.device.model_name}")
            print_info("Unplug your watch (or safe-eject) to let Garmin OS process the course!")
        except Exception as e:
            print_error(f"Failed to sideload '{path.name}': {e}")


def cmd_convert(args):
    """Converts a GPX route into a standalone FIT course file."""
    sport_map = {
        "cycling": Sport.CYCLING,
        "hiking": Sport.HIKING,
        "running": Sport.RUNNING,
    }
    sport_enum = sport_map.get(args.sport.lower(), Sport.CYCLING)

    for gpx_file in args.files:
        try:
            out_fit, course_data = convert_gpx_to_fit(
                gpx_path=gpx_file,
                output_fit_path=args.output,
                course_name=args.name,
                sport=sport_enum,
            )
            dist_km = course_data.total_distance / 1000.0
            print_success(f"Converted '{gpx_file}' -> '{out_fit}'")
            print_info(
                f"Course: '{course_data.name}' | Sport: {course_data.sport.name} | "
                f"Distance: {dist_km:.2f} km | Points: {len(course_data.points)} | "
                f"Ascent: {course_data.total_ascent:.0f}m"
            )
        except Exception as e:
            print_error(f"Failed to convert '{gpx_file}': {e}")


def cmd_delete(args):
    """Deletes a course file from the watch."""
    try:
        manager = GarminDeviceManager(custom_mount=args.mount)
    except Exception as e:
        print_error(str(e))
        return

    for filename in args.filenames:
        deleted = manager.delete_course(filename)
        if deleted:
            print_success(f"Deleted '{filename}' from {manager.device.model_name}")
        else:
            print_error(f"Course '{filename}' not found on device.")


def cmd_backup(args):
    """Backs up courses from the watch to a local folder."""
    try:
        manager = GarminDeviceManager(custom_mount=args.mount)
    except Exception as e:
        print_error(str(e))
        return

    dest = Path(args.dest)
    backed_up = manager.backup_courses(dest)
    print_success(f"Backed up {len(backed_up)} course(s) to '{dest.resolve()}'")


def cmd_watch(args):
    """Watches a directory for new GPX/FIT files and auto-sideloads them."""
    sport_map = {
        "cycling": Sport.CYCLING,
        "hiking": Sport.HIKING,
        "running": Sport.RUNNING,
    }
    sport_enum = sport_map.get(args.sport.lower(), Sport.CYCLING)

    def on_sideload(src: Path, dest: Path):
        print_success(f"Auto-sideloaded new route: '{src.name}' -> {dest.name}")

    watcher = DirectoryWatcher(
        watch_dir=args.directory,
        sport=sport_enum,
        on_sideload_callback=on_sideload,
        custom_mount=args.mount,
    )
    watcher.run_polling_loop(poll_interval=args.interval)


def cmd_serve(args):
    """Starts local REST API service."""
    try:
        import uvicorn
        from .service.api import create_app
    except ImportError:
        print_error("REST API requires fastapi and uvicorn. Install with: pip install 'garmin-connector[api]'")
        return

    app = create_app(custom_mount=args.mount)
    print_info(f"Starting Garmin Connector API server on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garmin-connector",
        description="Sideload and manage hiking & cycling routes on Garmin Venu and other Garmin watches.",
    )
    parser.add_argument("--mount", "-m", help="Explicit Garmin mount point or GARMIN directory path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # detect
    p_detect = subparsers.add_parser("detect", help="Scan and show connected Garmin watch details")
    p_detect.set_defaults(func=cmd_detect)

    # list
    p_list = subparsers.add_parser("list", aliases=["ls"], help="List stored courses on watch")
    p_list.set_defaults(func=cmd_list)

    # push
    p_push = subparsers.add_parser("push", help="Convert & sideload GPX/FIT routes to watch")
    p_push.add_argument("files", nargs="+", help="GPX or FIT route files to sideload")
    p_push.add_argument("--sport", "-s", default="cycling", choices=["cycling", "hiking", "walking", "running"], help="Sport type")
    p_push.add_argument("--name", "-n", help="Custom course name (up to 15 chars)")
    p_push.set_defaults(func=cmd_push)

    # convert
    p_conv = subparsers.add_parser("convert", help="Convert GPX to Garmin FIT course locally")
    p_conv.add_argument("files", nargs="+", help="GPX files to convert")
    p_conv.add_argument("--output", "-o", help="Custom output .fit path (single file only)")
    p_conv.add_argument("--sport", "-s", default="cycling", choices=["cycling", "hiking", "running"], help="Sport type")
    p_conv.add_argument("--name", "-n", help="Custom course name")
    p_conv.set_defaults(func=cmd_convert)

    # delete
    p_del = subparsers.add_parser("delete", aliases=["rm"], help="Delete course from watch")
    p_del.add_argument("filenames", nargs="+", help="Course filename(s) to remove (e.g. course.fit)")
    p_del.set_defaults(func=cmd_delete)

    # backup
    p_bak = subparsers.add_parser("backup", help="Backup all courses from watch")
    p_bak.add_argument("--dest", "-d", default="./courses_backup", help="Destination backup directory")
    p_bak.set_defaults(func=cmd_backup)

    # watch
    p_watch = subparsers.add_parser("watch", help="Monitor folder and auto-sideload incoming GPX/FIT files")
    p_watch.add_argument("directory", help="Folder to watch (e.g. ~/Downloads or export dir)")
    p_watch.add_argument("--sport", "-s", default="cycling", choices=["cycling", "hiking", "running"], help="Sport type")
    p_watch.add_argument("--interval", "-i", type=float, default=2.0, help="Polling interval in seconds")
    p_watch.set_defaults(func=cmd_watch)

    # serve
    p_srv = subparsers.add_parser("serve", help="Run local REST API server for direct route app integration")
    p_srv.add_argument("--host", default="127.0.0.1", help="Host interface")
    p_srv.add_argument("--port", "-p", type=int, default=8080, help="Port")
    p_srv.set_defaults(func=cmd_serve)

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
