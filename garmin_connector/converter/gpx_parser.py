"""
GPX Parser for Garmin Course Generation.
Parses GPX tracks, routes, and waypoints with distance and elevation calculations.
Supports standard XML parsing (zero heavy external dependency required) and gpxpy fallback.
"""

from __future__ import annotations
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from .fit_encoder import (
    CourseData,
    TrackPoint,
    CoursePointData,
    CoursePointType,
    Sport,
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Parses ISO 8601 datetime strings with timezone support."""
    if not dt_str:
        return None
    try:
        # Normalize trailing Z to +00:00
        clean_str = dt_str.strip()
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None


def match_course_point_type(name: str, sym: str = "", desc: str = "") -> CoursePointType:
    """Guesses Garmin CoursePointType from waypoint name, symbol, or description."""
    text = f"{name} {sym} {desc}".lower()

    if re.search(r"\b(left fork|fork left)\b", text):
        return CoursePointType.LEFT_FORK
    if re.search(r"\b(right fork|fork right)\b", text):
        return CoursePointType.RIGHT_FORK
    if re.search(r"\b(sharp left)\b", text):
        return CoursePointType.SHARP_LEFT
    if re.search(r"\b(sharp right)\b", text):
        return CoursePointType.SHARP_RIGHT
    if re.search(r"\b(slight left)\b", text):
        return CoursePointType.SLIGHT_LEFT
    if re.search(r"\b(slight right)\b", text):
        return CoursePointType.SLIGHT_RIGHT
    if re.search(r"\b(turn left|left)\b", text):
        return CoursePointType.LEFT
    if re.search(r"\b(turn right|right)\b", text):
        return CoursePointType.RIGHT
    if re.search(r"\b(straight|continue|ahead)\b", text):
        return CoursePointType.STRAIGHT
    if re.search(r"\b(u[- ]turn)\b", text):
        return CoursePointType.U_TURN
    if re.search(r"\b(summit|peak|top|mountain)\b", text):
        return CoursePointType.SUMMIT
    if re.search(r"\b(water|drink|fountain|tap)\b", text):
        return CoursePointType.WATER
    if re.search(r"\b(food|restaurant|cafe|bakery|lunch)\b", text):
        return CoursePointType.FOOD
    if re.search(r"\b(danger|warning|caution|steep)\b", text):
        return CoursePointType.DANGER
    if re.search(r"\b(first aid|hospital|medical)\b", text):
        return CoursePointType.FIRST_AID

    return CoursePointType.GENERIC


def parse_gpx_string(
    xml_content: str,
    course_name: Optional[str] = None,
    sport: Sport = Sport.CYCLING,
) -> CourseData:
    """Parses GPX XML string into CourseData."""
    root = ET.fromstring(xml_content)

    # Strip XML namespaces for uniform querying
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]

    # Course Name extraction
    extracted_name = None
    for tag in [".//trk/name", ".//rte/name", ".//metadata/name", ".//name"]:
        name_tag = root.find(tag)
        if name_tag is not None and name_tag.text and name_tag.text.strip():
            extracted_name = name_tag.text.strip()
            break

    final_name = (course_name or extracted_name or "Course").strip()[:15]

    # Collect raw track / route points
    raw_points: List[Tuple[float, float, Optional[float], Optional[datetime]]] = []

    # 1. Look for <trkpt> points
    for trkpt in root.findall(".//trkpt"):
        lat = float(trkpt.attrib.get("lat", 0))
        lon = float(trkpt.attrib.get("lon", 0))
        ele_elem = trkpt.find("ele")
        ele = float(ele_elem.text) if ele_elem is not None and ele_elem.text else None
        time_elem = trkpt.find("time")
        dt = parse_iso_datetime(time_elem.text) if time_elem is not None and time_elem.text else None
        raw_points.append((lat, lon, ele, dt))

    # 2. If no track points, look for <rtept> points
    if not raw_points:
        for rtept in root.findall(".//rtept"):
            lat = float(rtept.attrib.get("lat", 0))
            lon = float(rtept.attrib.get("lon", 0))
            ele_elem = rtept.find("ele")
            ele = float(ele_elem.text) if ele_elem is not None and ele_elem.text else None
            time_elem = rtept.find("time")
            dt = parse_iso_datetime(time_elem.text) if time_elem is not None and time_elem.text else None
            raw_points.append((lat, lon, ele, dt))

    if not raw_points:
        raise ValueError("No track points (<trkpt>) or route points (<rtept>) found in GPX file.")

    # Calculate cumulative distances and elevation profiles
    points: List[TrackPoint] = []
    total_distance = 0.0
    total_ascent = 0.0
    total_descent = 0.0

    prev_lat, prev_lon, prev_ele = None, None, None
    for lat, lon, ele, dt in raw_points:
        if prev_lat is not None and prev_lon is not None:
            dist_step = haversine_distance(prev_lat, prev_lon, lat, lon)
            total_distance += dist_step

            if prev_ele is not None and ele is not None:
                diff = ele - prev_ele
                if diff > 0.3:  # noise filter
                    total_ascent += diff
                elif diff < -0.3:
                    total_descent += abs(diff)

        points.append(
            TrackPoint(
                lat=lat,
                lon=lon,
                elevation=ele,
                distance=total_distance,
                timestamp=dt,
            )
        )
        prev_lat, prev_lon, prev_ele = lat, lon, ele

    # Collect waypoints (<wpt>) and match to course points
    course_points: List[CoursePointData] = []
    for wpt in root.findall(".//wpt"):
        w_lat = float(wpt.attrib.get("lat", 0))
        w_lon = float(wpt.attrib.get("lon", 0))
        w_name_elem = wpt.find("name")
        w_name = w_name_elem.text.strip() if w_name_elem is not None and w_name_elem.text else "Point"
        w_sym_elem = wpt.find("sym")
        w_sym = w_sym_elem.text.strip() if w_sym_elem is not None and w_sym_elem.text else ""
        w_desc_elem = wpt.find("desc")
        w_desc = w_desc_elem.text.strip() if w_desc_elem is not None and w_desc_elem.text else ""

        # Find closest track point distance along route
        best_dist_along = 0.0
        min_dist_to_route = float("inf")
        for pt in points:
            d = haversine_distance(w_lat, w_lon, pt.lat, pt.lon)
            if d < min_dist_to_route:
                min_dist_to_route = d
                best_dist_along = pt.distance

        point_type = match_course_point_type(w_name, w_sym, w_desc)
        course_points.append(
            CoursePointData(
                lat=w_lat,
                lon=w_lon,
                distance=best_dist_along,
                point_type=point_type,
                name=w_name[:15],
            )
        )

    # Sort course points by distance
    course_points.sort(key=lambda cp: cp.distance)

    return CourseData(
        name=final_name,
        sport=sport,
        points=points,
        course_points=course_points,
        total_distance=total_distance,
        total_ascent=total_ascent,
        total_descent=total_descent,
        created_at=datetime.now(timezone.utc),
    )


def parse_gpx_file(
    file_path: str | Path,
    course_name: Optional[str] = None,
    sport: Sport = Sport.CYCLING,
) -> CourseData:
    """Reads a GPX file from disk and parses it into CourseData."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"GPX file not found: {file_path}")

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    res = parse_gpx_string(content, course_name=course_name, sport=sport)
    if not course_name and res.name == "Course":
        res.name = path.stem.replace("_", " ").replace("-", " ")[:15]
    return res
