"""
Garmin Connect Cloud Integration.
Allows uploading GPX/FIT courses directly to Garmin Connect account for wireless sync to the watch via Garmin Connect Mobile (phone).
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional


class GarminCloudSync:
    """Handles wireless course syncing through Garmin Connect."""

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        self.email = email or os.environ.get("GARMIN_EMAIL")
        self.password = password or os.environ.get("GARMIN_PASSWORD")
        self._client = None

    def _ensure_authenticated(self):
        if self._client is not None:
            return

        try:
            from garminconnect import Garmin
        except ImportError:
            raise ImportError(
                "The 'garminconnect' package is required for cloud synchronization. "
                "Install it with: pip install 'garmin-connector[cloud]'"
            )

        if not self.email or not self.password:
            raise ValueError(
                "Garmin credentials required. Set GARMIN_EMAIL and GARMIN_PASSWORD environment "
                "variables or pass them to the command."
            )

        self._client = Garmin(self.email, self.password)
        self._client.login()

    def upload_activity_or_course(self, file_path: str | Path) -> dict:
        """Uploads a FIT or GPX file to Garmin Connect."""
        self._ensure_authenticated()
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(path, "rb") as f:
            data = f.read()

        # Garmin Connect upload
        res = self._client.upload_activity(str(path))
        return res
