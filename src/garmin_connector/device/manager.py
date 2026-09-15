import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .detector import GarminDeviceDetector, GarminDeviceInfo
from ..converter import convert_gpx_to_fit, Sport

@dataclass
class CourseFileSummary:
    filename: str
    full_path: Path
    size_bytes: int
    modified_at: datetime
    location: str

class GarminDeviceManager:
    def __init__(self, device: Optional[GarminDeviceInfo] = None, custom_mount: Optional[str | Path] = None):
        if device:
            self.device = device
        else:
            self.device = GarminDeviceDetector.get_first_device(custom_mount)
            if not self.device:
                raise ConnectionError("No Garmin device detected. Please connect via USB or provide --mount path.")

    def sideload_route(self, source_path: str | Path, sport: Sport = Sport.CYCLING, course_name: Optional[str] = None) -> Path:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        suffix = source.suffix.lower()
        if suffix not in ['.gpx', '.fit']:
            raise ValueError(f"Unsupported format: {suffix}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            if suffix == '.gpx':
                fit_path, _ = convert_gpx_to_fit(source, tmp_path / (source.stem + '.fit'), course_name, sport)
                transfer_src = fit_path
            else:
                transfer_src = source

            return self._transfer_to_newfiles(transfer_src)

    def _transfer_to_newfiles(self, src: Path) -> Path:
        target_dir = self.device.newfiles_dir or (self.device.garmin_dir / "NEWFILES")
        filename = src.name
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename
            target_file.write_bytes(src.read_bytes())
            return target_file
        except OSError as e:
            raise RuntimeError(f"Transfer failed: {e}") from e

    def list_courses(self) -> List[CourseFileSummary]:
        results = []
        
        def process_dir(d: Optional[Path], loc: str):
            if not d or not d.exists() or not d.is_dir():
                return []
            
            entries = []
            for child in sorted(d.iterdir()):
                if child.is_file() and child.suffix.lower() in ['.fit', '.gpx']:
                    try:
                        mtime = child.stat().st_mtime
                        dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                    except Exception:
                        dt = datetime.now(timezone.utc)
                    
                    entries.append(CourseFileSummary(
                        filename=child.name,
                        full_path=child,
                        size_bytes=child.stat().st_size,
                        modified_at=dt,
                        location=loc
                    ))
            return entries

        results.extend(process_dir(self.device.courses_dir, "COURSES"))
        results.extend(process_dir(self.device.newfiles_dir, "NEWFILES (Pending Sync)"))
        return results

    def delete_course(self, filename: str) -> bool:
        deleted = False
        
        for d in [self.device.courses_dir, self.device.newfiles_dir]:
            if d and d.exists() and d.is_dir():
                target = d / filename
                if target.exists():
                    try:
                        target.unlink()
                        deleted = True
                    except Exception:
                        pass
        return deleted
