"""
Directory Watcher Service.
Monitors an export folder (e.g. ~/Downloads or custom route app folder) and automatically sideloads routes onto Garmin watch.
"""

from __future__ import annotations
import time
from pathlib import Path
from typing import Callable, Optional

from ..converter.fit_encoder import Sport
from ..device.detector import GarminDeviceDetector
from ..device.manager import GarminDeviceManager


class DirectoryWatcher:
    """Monitors local directory and automatically sideloads incoming GPX/FIT files."""

    def __init__(
        self,
        watch_dir: str | Path,
        sport: Sport = Sport.CYCLING,
        on_sideload_callback: Optional[Callable[[Path, Path], None]] = None,
        custom_mount: Optional[str | Path] = None,
    ):
        self.watch_dir = Path(watch_dir).expanduser().resolve()
        self.sport = sport
        self.on_sideload_callback = on_sideload_callback
        self.custom_mount = custom_mount
        self._processed_files: set[str] = set()

    def _process_file(self, file_path: Path):
        if not file_path.is_file() or file_path.name.startswith("."):
            return
        if file_path.suffix.lower() not in [".gpx", ".fit"]:
            return

        stat = file_path.stat()
        file_sig = f"{file_path.name}_{stat.st_mtime}_{stat.st_size}"
        if file_sig in self._processed_files:
            return

        device = GarminDeviceDetector.get_first_device(self.custom_mount)
        if not device:
            # Device not connected, will wait for next loop
            return

        try:
            manager = GarminDeviceManager(device=device)
            dest = manager.sideload_route(file_path, sport=self.sport)
            self._processed_files.add(file_sig)
            if self.on_sideload_callback:
                self.on_sideload_callback(file_path, dest)
        except Exception as e:
            print(f"[Watcher] Error sideloading {file_path.name}: {e}")

    def scan_once(self):
        """Scans directory once for unprocessed route files."""
        if not self.watch_dir.exists():
            return
        for item in self.watch_dir.iterdir():
            if item.is_file() and item.suffix.lower() in [".gpx", ".fit"]:
                self._process_file(item)

    def run_polling_loop(self, poll_interval: float = 2.0):
        """Runs continuous polling loop for changes."""
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        print(f"[Watcher] Monitoring directory: {self.watch_dir}")
        print(f"[Watcher] Plug in your Garmin watch to auto-sideload incoming GPX/FIT routes.")

        while True:
            try:
                self.scan_once()
                time.sleep(poll_interval)
            except KeyboardInterrupt:
                print("\n[Watcher] Stopped.")
                break
