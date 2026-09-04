"""
DEM Terrain Elevation Enrichment Module.
Automatically enriches GPX track points with real-world topography (SRTM / Copernicus DEM)
when GPX exports contain missing or flat 0.0m elevation data.
"""

from __future__ import annotations
import json
import urllib.request
from typing import List, Optional

from .fit_encoder import CourseData, TrackPoint


def has_meaningful_elevation(points: List[TrackPoint]) -> bool:
    """Checks if track points already have valid, non-zero varying elevation data."""
    valid_eles = [p.elevation for p in points if p.elevation is not None]
    if len(valid_eles) < 2:
        return False
    # If all elevations are exactly 0.0 or variance is negligible (< 1m across whole track)
    min_e = min(valid_eles)
    max_e = max(valid_eles)
    if min_e == 0.0 and max_e == 0.0:
        return False
    return (max_e - min_e) >= 1.0


def fetch_dem_elevations(lat_lons: List[tuple[float, float]], timeout: float = 10.0) -> Optional[List[float]]:
    """
    Fetches real elevation (in meters) for a list of (lat, lon) coordinates
    using the global Open-Elevation DEM service.
    """
    if not lat_lons:
        return None

    locations = [{"latitude": round(lat, 6), "longitude": round(lon, 6)} for lat, lon in lat_lons]
    payload = json.dumps({"locations": locations}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.open-elevation.com/api/v1/lookup",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "GarminConnector/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if len(results) == len(lat_lons):
                return [r.get("elevation", 0.0) for r in results]
    except Exception as e:
        print(f"[ElevationEnrichment] Warning: Could not fetch DEM elevation: {e}")

    return None


def enrich_course_elevation(course: CourseData, force: bool = False) -> CourseData:
    """
    Enriches CourseData with DEM elevations if elevations are missing or flat 0.0.
    Recalculates total_ascent and total_descent.
    """
    if not course.points:
        return course

    if not force and has_meaningful_elevation(course.points):
        # Already has meaningful elevation data
        return course

    lat_lons = [(p.lat, p.lon) for p in course.points]
    # Fetch in batches if > 1500 points
    batch_size = 1000
    all_elevations: List[float] = []

    for i in range(0, len(lat_lons), batch_size):
        chunk = lat_lons[i : i + batch_size]
        chunk_eles = fetch_dem_elevations(chunk)
        if chunk_eles is None:
            # Fallback failed, retain original
            return course
        all_elevations.extend(chunk_eles)

    if len(all_elevations) != len(course.points):
        return course

    # Apply elevations and recalculate ascent / descent with smoothing
    total_ascent = 0.0
    total_descent = 0.0
    prev_ele = None

    for i, pt in enumerate(course.points):
        ele = all_elevations[i]
        pt.elevation = ele
        if prev_ele is not None:
            diff = ele - prev_ele
            if diff > 0.5:
                total_ascent += diff
            elif diff < -0.5:
                total_descent += abs(diff)
        prev_ele = ele

    course.total_ascent = total_ascent
    course.total_descent = total_descent
    return course
