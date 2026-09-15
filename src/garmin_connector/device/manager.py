import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from garmin_connector.converter.fit_encoder import Sport
from garmin_connector.converter.gpx_to_fit import convert_gpx_to_fit
from garmin_connector.device.detector import GarminDeviceDetector, GarminDeviceInfo

LOCATION_COURSES = "COURSES"
LOCATION_NEWFILES = "NEWFILES (Pending Sync)"
_COURSE_EXTENSIONS = (".fit", ".gpx")


@dataclass
class CourseFileSummary:
    filename: str
    full_path: Path
    size_bytes: int
    modified_at: datetime
    location: str


class GarminDeviceManager:
    def __init__(self, device: Optional[GarminDeviceInfo] = None, custom_mount: Optional[Union[str, Path]] = None):
        if device is None:
            device = GarminDeviceDetector.get_first_device(custom_mount)
        if device is None:
            raise ConnectionError(
                "No Garmin device found. Connect the watch via USB and wait for it to mount, "
                "or pass --mount with the path to its storage."
            )
        self.device = device

    def sideload_route(
        self,
        source_path: Union[str, Path],
        sport: Sport = Sport.CYCLING,
        course_name: Optional[str] = None,
    ) -> Path:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Route file not found: {source}")

        suffix = source.suffix.lower()
        if suffix == ".gpx":
            with tempfile.TemporaryDirectory() as tmp_dir:
                fit_path, _ = convert_gpx_to_fit(
                    source,
                    output_fit_path=Path(tmp_dir) / source.with_suffix(".fit").name,
                    course_name=course_name,
                    sport=sport,
                )
                return self._transfer_to_newfiles(fit_path)
        if suffix == ".fit":
            return self._transfer_to_newfiles(source)
        raise ValueError(f"Unsupported route format '{source.suffix}': only .gpx and .fit are supported")

    def _newfiles_dir(self) -> Path:
        return self.device.newfiles_dir or (self.device.garmin_dir / "NEWFILES")

    def _transfer_to_newfiles(self, source: Path) -> Path:
        target_dir = self._newfiles_dir()
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            destination = target_dir / source.name
            destination.write_bytes(source.read_bytes())
        except OSError as exc:
            raise RuntimeError(f"Failed to write {source.name} to {target_dir}: {exc}") from exc
        return destination

    @staticmethod
    def _scan_dir(directory: Optional[Path], location: str) -> List[CourseFileSummary]:
        if directory is None or not directory.is_dir():
            return []
        entries: List[CourseFileSummary] = []
        for path in directory.iterdir():
            if not path.is_file() or path.suffix.lower() not in _COURSE_EXTENSIONS:
                continue
            stat = path.stat()
            entries.append(
                CourseFileSummary(
                    filename=path.name,
                    full_path=path,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    location=location,
                )
            )
        entries.sort(key=lambda e: e.filename)
        return entries

    def list_courses(self) -> List[CourseFileSummary]:
        return self._scan_dir(self.device.courses_dir, LOCATION_COURSES) + self._scan_dir(
            self._newfiles_dir(), LOCATION_NEWFILES
        )

    def delete_course(self, filename: str) -> bool:
        deleted = False
        for directory in (self.device.courses_dir, self._newfiles_dir()):
            if directory is None:
                continue
            candidate = directory / filename
            try:
                if candidate.is_file():
                    candidate.unlink()
                    deleted = True
            except OSError:
                continue
        return deleted
