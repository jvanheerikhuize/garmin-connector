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


def cmd_probe(args):
    """Directly probes the connected Garmin watch via filesystem, GIO MTP, and USB."""
    print_info("Probing connected Garmin device...")

    fs_devices = GarminDeviceDetector.detect_devices(args.mount)
    if not fs_devices:
        print_error("No Garmin device detected via filesystem or MTP mounts.")
        return

    dev = fs_devices[0]
    manager = GarminDeviceManager(device=dev)
    courses = manager.list_courses()
    staged = [c for c in courses if "NEWFILES" in c.location.upper()]
    active = [c for c in courses if "COURSES" in c.location.upper()]

    # Hardware probe via direct MTP client if possible
    mtp_result = None
    try:
        from .device.mtp_client import GarminMTPClient
        with GarminMTPClient() as mtp:
            mtp_result = mtp.probe_device()
    except Exception as e:
        mtp_note = f"MTP In-Use ({e})"
    else:
        mtp_note = "Online"

    if console:
        table = Table(title=f"Garmin Watch Functional Probe: {dev.model_name}")
        table.add_column("Parameter", style="bold cyan")
        table.add_column("Status / Value")

        table.add_row("Model Name", dev.model_name)
        table.add_row("Unit ID", dev.unit_id or "Unknown")
        table.add_row("Firmware Version", dev.software_version or "Unknown")
        table.add_row("Mount Point", str(dev.mount_point))
        table.add_row("GARMIN Directory", str(dev.garmin_dir))
        table.add_row("Transport Mode", "MTP (GNOME GVFS)" if dev.is_mtp else "USB Mass Storage")
        if dev.gio_newfiles_uri:
            table.add_row("GIO Ingest URI", dev.gio_newfiles_uri)
        table.add_row("Direct USB MTP", mtp_note)
        table.add_row("Staged in NewFiles", f"[bold yellow]{len(staged)}[/bold yellow] file(s)")
        table.add_row("Installed Courses", f"[bold green]{len(active)}[/bold green] course(s)")

        console.print(table)

        if staged:
            staged_table = Table(title="Files Staged in GARMIN/NewFiles (Pending Watch Sync)")
            staged_table.add_column("Filename", style="bold yellow")
            staged_table.add_column("Size", justify="right")
            staged_table.add_column("Modified", style="dim")
            for s in staged:
                staged_table.add_row(s.filename, f"{s.size_bytes} B", s.modified_at.strftime("%Y-%m-%d %H:%M"))
            console.print(staged_table)
    else:
        print(f"=== Watch Probe: {dev.model_name} ===")
        print(f"Unit ID: {dev.unit_id} | Firmware: {dev.software_version}")
        print(f"Mount: {dev.mount_point}")
        print(f"Ingest URI: {dev.gio_newfiles_uri}")
        print(f"Staged in NewFiles: {len(staged)}")
        print(f"Courses in Courses: {len(active)}")

    print_success("Watch probe completed successfully.")


def cmd_test_watch(args):
    """Performs an autonomous end-to-end functional smoke test against the connected Garmin watch."""
    print_info("Starting autonomous Garmin watch functional smoke test...")

    # 1. Connect & detect
    try:
        manager = GarminDeviceManager(custom_mount=args.mount)
        print_success(f"Detected watch: {manager.device.model_name} (Unit ID: {manager.device.unit_id})")
    except Exception as e:
        print_error(f"Cannot connect to watch: {e}")
        return

    # 2. Synthesize a minimal valid FIT course
    import tempfile
    from datetime import datetime, timezone
    from .converter.fit_encoder import FitCourseEncoder, CourseData, TrackPoint, Sport

    course_data = CourseData(
        name="SelfTest",
        sport=Sport.CYCLING,
        points=[
            TrackPoint(lat=50.2500, lon=6.1000, elevation=450.0, distance=0.0, timestamp=datetime.now(timezone.utc)),
            TrackPoint(lat=50.2510, lon=6.1010, elevation=455.0, distance=100.0, timestamp=datetime.now(timezone.utc)),
            TrackPoint(lat=50.2520, lon=6.1020, elevation=460.0, distance=200.0, timestamp=datetime.now(timezone.utc)),
        ],
        total_distance=200.0,
        total_ascent=10.0,
        created_at=datetime.now(timezone.utc),
    )
    encoder = FitCourseEncoder(course=course_data)
    fit_bytes = encoder.encode()

    test_filename = "selftest_route.fit"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_fit = Path(tmp_dir) / test_filename
        tmp_fit.write_bytes(fit_bytes)

        # 3. Sideload to watch
        print_info(f"Sideloading test course ({len(fit_bytes)} bytes) to watch's GARMIN/NewFiles...")
        try:
            dest = manager.sideload_route(tmp_fit)
            print_success(f"File staged at: {dest}")
        except Exception as e:
            print_error(f"Sideload failed: {e}")
            return

        # 4. Probe and verify staged status on watch
        verify_status = manager.verify_staged_course(test_filename)
        if verify_status.get("verified"):
            print_success(f"Verified staged file on watch: {verify_status['filename']} ({verify_status['size_bytes']} bytes)")
        else:
            print_error(f"Verification failed: {test_filename} was not found in watch's NewFiles!")
            return

        # 5. Cleanup unless --keep
        if not getattr(args, "keep", False):
            cleaned = manager.delete_course(test_filename)
            if cleaned:
                print_success("Autonomous cleanup: Test course removed from watch.")
            else:
                print_info("Cleanup notice: Test course could not be unlinked automatically.")
        else:
            print_info("Flag --keep set: Left test course on watch for manual inspection.")

    print_success("Watch functional smoke test PASSED 100%!")


def cmd_gui(args):
    """Launches the interactive desktop GUI dashboard."""
    from .gui.launcher import launch_gui
    launch_gui(host=args.host, port=args.port, open_browser=not args.no_browser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="garmin-connector",
        description="Sideload and manage hiking & cycling routes on Garmin Venu and other Garmin watches.",
    )
    parser.add_argument("--mount", "-m", help="Explicit Garmin mount point or GARMIN directory path")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # gui
    p_gui = subparsers.add_parser("gui", help="Launch interactive desktop GUI dashboard")
    p_gui.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    p_gui.add_argument("--port", "-p", type=int, default=8080, help="Port (default: 8080)")
    p_gui.add_argument("--no-browser", action="store_true", help="Do not auto-open browser / app window")
    p_gui.set_defaults(func=cmd_gui)

    # detect
    p_detect = subparsers.add_parser("detect", help="Scan and show connected Garmin watch details")
    p_detect.set_defaults(func=cmd_detect)

    # probe
    p_probe = subparsers.add_parser("probe", help="Directly probe and functionally test connected watch via USB/MTP")
    p_probe.set_defaults(func=cmd_probe)

    # test-watch
    p_test = subparsers.add_parser("test-watch", help="Run automated functional smoke test against connected watch")
    p_test.add_argument("--keep", "-k", action="store_true", help="Keep test course on watch instead of cleaning up")
    p_test.set_defaults(func=cmd_test_watch)

    # list
    p_list = subparsers.add_parser("list", aliases=["ls"], help="List stored courses on watch")
    p_list.set_defaults(func=cmd_list)

    # push / sideload
    p_push = subparsers.add_parser("push", aliases=["sideload"], help="Convert & sideload GPX/FIT routes to watch")
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
