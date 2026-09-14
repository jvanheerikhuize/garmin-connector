import os
import shutil
import tempfile
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import subprocess

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
        
        if self.device.is_mtp and self.device.gio_newfiles_uri:
            # GIO path
            target_uri = f"{self.device.gio_newfiles_uri}/{urllib.parse.quote(filename)}"
            try:
                import gi
                gi.require_version('Gio', '2.0')
                from gi.repository import Gio
                g_src = Gio.File.new_for_path(str(src))
                g_dest = Gio.File.new_for_uri(target_uri)
                g_src.copy(g_dest, Gio.FileCopyFlags.OVERWRITE, None, None, None)
                return target_dir / filename
            except Exception as e:
                # Fallback to gio CLI
                try:
                    subprocess.run(["gio", "copy", "--default-permissions", str(src), target_uri], check=True, capture_output=True)
                    return target_dir / filename
                except subprocess.CalledProcessError as sub_e:
                    raise RuntimeError(f"GIO transfer failed: {sub_e.stderr.decode('utf-8', errors='ignore')}") from e
                except Exception as sub_e:
                    raise RuntimeError(f"GIO transfer failed: {e}") from sub_e
        
        # POSIX path
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename
            target_file.write_bytes(src.read_bytes())
            return target_file
        except OSError as e:
            if e.errno == 95 and self.device.is_mtp and self.device.gio_newfiles_uri:
                target_uri = f"{self.device.gio_newfiles_uri}/{urllib.parse.quote(filename)}"
                try:
                    subprocess.run(["gio", "copy", "--default-permissions", str(src), target_uri], check=True, capture_output=True)
                    return target_file
                except subprocess.CalledProcessError as sub_e:
                    raise RuntimeError(f"Fallback GIO transfer failed: {sub_e.stderr.decode('utf-8', errors='ignore')}") from e
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
        
        if not deleted and self.device.is_mtp:
            uris = []
            if self.device.gio_courses_uri:
                uris.append(f"{self.device.gio_courses_uri}/{urllib.parse.quote(filename)}")
            if self.device.gio_newfiles_uri:
                uris.append(f"{self.device.gio_newfiles_uri}/{urllib.parse.quote(filename)}")
                
            for uri in uris:
                try:
                    subprocess.run(["gio", "remove", uri], check=True, capture_output=True)
                    deleted = True
                    break
                except Exception:
                    pass
                    
        return deleted
