"""
Garmin Device File & Course Manager.
Handles sideloading routes (GPX/FIT) to GARMIN/NEWFILES and managing GARMIN/COURSES.
"""

from __future__ import annotations
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

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

        target_newfiles_dir = self.device.newfiles_dir
        if not target_newfiles_dir:
            target_newfiles_dir = self.device.garmin_dir / "NEWFILES"

        target_newfiles_dir.mkdir(parents=True, exist_ok=True)

        suffix = src.suffix.lower()

        if suffix == ".gpx":
            # Convert GPX to FIT in a temporary directory, then copy to watch
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_fit_path = Path(tmp_dir) / f"{src.stem}.fit"
                convert_gpx_to_fit(
                    gpx_path=src,
                    output_fit_path=tmp_fit_path,
                    course_name=course_name,
                    sport=sport,
                )
                dest_file = target_newfiles_dir / tmp_fit_path.name
                dest_file.write_bytes(tmp_fit_path.read_bytes())
        elif suffix == ".fit":
            dest_file = target_newfiles_dir / src.name
            dest_file.write_bytes(src.read_bytes())
        else:
            raise ValueError(f"Unsupported file format '{suffix}'. Supported formats: .gpx, .fit")

        return dest_file

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
                    target.unlink()
                    deleted = True

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
