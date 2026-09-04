"""
FastAPI REST Service for Garmin Connector.
Allows external route building apps (like web apps) to directly push GPX/FIT routes to the watch.
"""

from __future__ import annotations
import tempfile
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:
    FastAPI = None

from ..converter.fit_encoder import Sport
from ..device.detector import GarminDeviceDetector
from ..device.manager import GarminDeviceManager


def create_app(custom_mount: Optional[str | Path] = None) -> FastAPI:
    """Creates FastAPI application."""
    if FastAPI is None:
        raise ImportError(
            "FastAPI is required for the REST service. Install with: pip install 'garmin-connector[api]'"
        )

    app = FastAPI(
        title="Garmin Connector API",
        description="Local REST API for sideloading and managing Garmin routes",
        version="0.1.0",
    )

    # Allow cross-origin requests so local web applications can directly POST routes
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def root():
        device = GarminDeviceDetector.get_first_device(custom_mount)
        return {
            "status": "online",
            "device_connected": device is not None,
            "device_model": device.model_name if device else None,
        }

    @app.get("/api/device")
    def get_device():
        device = GarminDeviceDetector.get_first_device(custom_mount)
        if not device:
            raise HTTPException(status_code=404, detail="No Garmin device connected")
        return {
            "model_name": device.model_name,
            "unit_id": device.unit_id,
            "software_version": device.software_version,
            "part_number": device.part_number,
            "mount_point": str(device.mount_point),
            "is_mtp": device.is_mtp,
        }

    @app.get("/api/courses")
    def list_courses():
        try:
            manager = GarminDeviceManager(custom_mount=custom_mount)
            courses = manager.list_courses()
            return [
                {
                    "filename": c.filename,
                    "size_bytes": c.size_bytes,
                    "modified_at": c.modified_at.isoformat(),
                    "location": c.location,
                }
                for c in courses
            ]
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=str(e))

    @app.post("/api/upload")
    async def upload_route(
        file: UploadFile = File(...),
        sport: str = Form("cycling"),
        course_name: Optional[str] = Form(None),
    ):
        try:
            manager = GarminDeviceManager(custom_mount=custom_mount)
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=str(e))

        sport_enum = Sport.CYCLING
        if sport.lower() in ["hiking", "walk", "walking", "hike"]:
            sport_enum = Sport.HIKING
        elif sport.lower() in ["running", "run"]:
            sport_enum = Sport.RUNNING

        suffix = Path(file.filename).suffix.lower() if file.filename else ".gpx"
        if suffix not in [".gpx", ".fit"]:
            raise HTTPException(status_code=400, detail="Only .gpx and .fit files are supported")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = Path(tmp.name)
            content = await file.read()
            tmp_path.write_bytes(content)

        try:
            dest = manager.sideload_route(tmp_path, sport=sport_enum, course_name=course_name)
            return {
                "success": True,
                "filename": dest.name,
                "message": f"Successfully sideloaded to {dest.name} on watch",
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @app.delete("/api/courses/{filename}")
    def delete_course(filename: str):
        try:
            manager = GarminDeviceManager(custom_mount=custom_mount)
            deleted = manager.delete_course(filename)
            if not deleted:
                raise HTTPException(status_code=404, detail=f"Course '{filename}' not found on device")
            return {"success": True, "deleted": filename}
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=str(e))

    return app
