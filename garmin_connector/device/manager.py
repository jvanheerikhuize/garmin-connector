"""
Garmin Device File & Course Manager.
Handles sideloading routes (GPX/FIT) to GARMIN/NEWFILES and managing GARMIN/COURSES.
"""

from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Ensure GIO loads GVFS MTP modules on Linux
for _gio_cand in [
    "/usr/lib/x86_64-linux-gnu/gio/modules",
    "/usr/lib/aarch64-linux-gnu/gio/modules",
    "/usr/lib/gio/modules",
    "/usr/lib64/gio/modules",
]:
    if os.path.exists(os.path.join(_gio_cand, "libgvfsdbus.so")):
        os.environ["GIO_MODULE_DIR"] = _gio_cand
        break

from ..converter.fit_encoder import Sport
from ..converter.gpx_to_fit import convert_gpx_to_fit
from .detector import GarminDeviceDetector, GarminDeviceInfo


@dataclass
class CourseFileSummary:
    filename: str
    full_path: Path
    size_bytes: int
    modified_at: datetime
    location: str  # "COURSES" or "NEWFILES (staged)"


class GarminDeviceManager:
    """Manages course files and sideloading operations for Garmin devices."""

    def __init__(self, device: Optional[GarminDeviceInfo] = None, custom_mount: Optional[str | Path] = None):
        if device is not None:
            self.device = device
        else:
            detected = GarminDeviceDetector.get_first_device(custom_mount)
            if not detected:
                raise ConnectionError(
                    "No Garmin device detected. Please connect your Garmin watch via USB, "
                    "or specify the mount path explicitly using --mount /path/to/GARMIN"
                )
            self.device = detected

    def _transfer_to_newfiles(self, src_fit_path: Path, target_filename: str) -> Path:
        """
        Transfers a local FIT file to the watch's GARMIN/NEWFILES folder.
        Uses native GIO MTP push for MTP mounts, with fallback to POSIX write_bytes.
        """
        target_newfiles_dir = self.device.newfiles_dir
        if not target_newfiles_dir:
            target_newfiles_dir = self.device.garmin_dir / "NEWFILES"

        dest_file = target_newfiles_dir / target_filename

        # Strategy 1: Native GIO MTP Transfer (when device is MTP / GVFS)
        if self.device.is_mtp and self.device.gio_newfiles_uri:
            quoted_filename = urllib.parse.quote(target_filename)
            target_gio_uri = f"{self.device.gio_newfiles_uri.rstrip('/')}/{quoted_filename}"
            copied = False
            last_err = None

            # Try PyGObject Gio
            try:
                import gi
                gi.require_version('Gio', '2.0')
                from gi.repository import Gio
                src_gfile = Gio.File.new_for_path(str(src_fit_path))
                dst_gfile = Gio.File.new_for_uri(target_gio_uri)
                src_gfile.copy(dst_gfile, Gio.FileCopyFlags.OVERWRITE, None, None)
                copied = True
            except Exception as e:
                last_err = e

            # Fallback to gio copy CLI
            if not copied:
                env = os.environ.copy()
                if "GIO_MODULE_DIR" not in env:
                    for cand in ["/usr/lib/x86_64-linux-gnu/gio/modules", "/usr/lib/gio/modules"]:
                        if os.path.isdir(cand):
                            env["GIO_MODULE_DIR"] = cand
                            break
                cmd = ["gio", "copy", "--default-permissions", str(src_fit_path), target_gio_uri]
                res = subprocess.run(cmd, capture_output=True, text=True, env=env)
                if res.returncode == 0:
                    copied = True
                else:
                    last_err = RuntimeError(f"GIO transfer failed: {res.stderr.strip() or last_err}")

            if copied:
                return dest_file
            elif last_err:
                raise last_err

        # Strategy 2: Direct POSIX filesystem write (for USB Mass Storage / local mocks)
        target_newfiles_dir.mkdir(parents=True, exist_ok=True)
        try:
            dest_file.write_bytes(src_fit_path.read_bytes())
            return dest_file
        except OSError as err:
            if err.errno == 95:
                # If POSIX write fails with Errno 95, try CLI gio copy as fallback
                if self.device.gio_newfiles_uri:
                    quoted_filename = urllib.parse.quote(target_filename)
                    target_gio_uri = f"{self.device.gio_newfiles_uri.rstrip('/')}/{quoted_filename}"
                    cmd = ["gio", "copy", "--default-permissions", str(src_fit_path), target_gio_uri]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode == 0:
                        return dest_file
                raise RuntimeError(
                    f"Direct file write failed with [Errno 95] on '{dest_file}'. "
                    f"GIO native URI: {self.device.gio_newfiles_uri}"
                ) from err
            raise

    def sideload_route(
        self,
        source_path: str | Path,
        sport: Sport = Sport.CYCLING,
        course_name: Optional[str] = None,
    ) -> Path:
        """
        Sideloads a GPX or FIT route file directly to the watch's GARMIN/NEWFILES folder.

        If the file is a GPX file, it is automatically converted into a native Garmin .FIT
        course before being transferred.
        """
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Source route file not found: {source_path}")

        suffix = src.suffix.lower()

        if suffix == ".gpx":
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_fit_path = Path(tmp_dir) / f"{src.stem}.fit"
                convert_gpx_to_fit(
                    gpx_path=src,
                    output_fit_path=tmp_fit_path,
                    course_name=course_name,
                    sport=sport,
                )
                dest_file = self._transfer_to_newfiles(tmp_fit_path, tmp_fit_path.name)
        elif suffix == ".fit":
            dest_file = self._transfer_to_newfiles(src, src.name)
        else:
            raise ValueError(f"Unsupported file format '{suffix}'. Supported formats: .gpx, .fit")

        return dest_file

    def verify_staged_course(self, filename: str) -> dict:
        """Verifies if a specific course file is staged in NEWFILES and checks its status."""
        for c in self.list_courses():
            if c.filename.lower() == filename.lower():
                return {
                    "verified": True,
                    "filename": c.filename,
                    "size_bytes": c.size_bytes,
                    "location": c.location,
                    "modified_at": c.modified_at.isoformat(),
                }
        return {"verified": False, "filename": filename}

    def list_courses(self) -> List[CourseFileSummary]:
        """Lists all courses currently installed in COURSES/ or staged in NEWFILES/."""
        results: List[CourseFileSummary] = []

        # 1. Check existing courses
        if self.device.courses_dir and self.device.courses_dir.exists():
            for f in sorted(self.device.courses_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in [".fit", ".gpx"]:
                    stat = f.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    results.append(
                        CourseFileSummary(
                            filename=f.name,
                            full_path=f,
                            size_bytes=stat.st_size,
                            modified_at=mtime,
                            location="COURSES",
                        )
                    )

        # 2. Check staged new files
        if self.device.newfiles_dir and self.device.newfiles_dir.exists():
            for f in sorted(self.device.newfiles_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in [".fit", ".gpx"]:
                    stat = f.stat()
                    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    results.append(
                        CourseFileSummary(
                            filename=f.name,
                            full_path=f,
                            size_bytes=stat.st_size,
                            modified_at=mtime,
                            location="NEWFILES (Pending Sync)",
                        )
                    )

        return results

    def delete_course(self, filename: str) -> bool:
        """Deletes a course file from COURSES or NEWFILES by filename."""
        deleted = False
        dirs_to_check = [self.device.courses_dir, self.device.newfiles_dir]

        for d in dirs_to_check:
            if d and d.exists():
                target = d / filename
                if target.exists() and target.is_file():
                    try:
                        target.unlink()
                        deleted = True
                    except Exception:
                        pass

        # If not deleted via POSIX and device is MTP, try GIO removal
        if not deleted and self.device.is_mtp:
            for uri in [self.device.gio_courses_uri, self.device.gio_newfiles_uri]:
                if uri:
                    target_uri = f"{uri.rstrip('/')}/{filename}"
                    cmd = ["gio", "remove", target_uri]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode == 0:
                        deleted = True
                        break

        return deleted

    def backup_courses(self, destination_dir: str | Path) -> List[Path]:
        """Backs up all course files from the watch to a local folder."""
        dest = Path(destination_dir)
        dest.mkdir(parents=True, exist_ok=True)
        backed_up: List[Path] = []

        for course in self.list_courses():
            dest_file = dest / course.filename
            dest_file.write_bytes(course.full_path.read_bytes())
            backed_up.append(dest_file)

        return backed_up
