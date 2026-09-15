import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from garmin_connector.converter.fit_encoder import (
    CourseData,
    CoursePointData,
    CoursePointType,
    Sport,
    TrackPoint,
)

EARTH_RADIUS_M = 6371000.0
ELEVATION_NOISE_THRESHOLD_M = 0.3
NAME_MAX_CHARS = 15
DEFAULT_COURSE_NAME = "Course"

_COURSE_POINT_PHRASES = (
    (CoursePointType.LEFT_FORK, ("left fork",)),
    (CoursePointType.RIGHT_FORK, ("right fork",)),
    (CoursePointType.SHARP_LEFT, ("sharp left",)),
    (CoursePointType.SHARP_RIGHT, ("sharp right",)),
    (CoursePointType.SLIGHT_LEFT, ("slight left",)),
    (CoursePointType.SLIGHT_RIGHT, ("slight right",)),
    (CoursePointType.LEFT, ("left",)),
    (CoursePointType.RIGHT, ("right",)),
    (CoursePointType.STRAIGHT, ("straight", "continue", "ahead")),
    (CoursePointType.U_TURN, ("u-turn", "u turn", "uturn")),
    (CoursePointType.SUMMIT, ("summit", "peak", "top", "mountain")),
    (CoursePointType.WATER, ("water", "drink", "fountain", "tap")),
    (CoursePointType.FOOD, ("food", "restaurant", "cafe", "bakery", "lunch")),
    (CoursePointType.DANGER, ("danger", "warning", "caution", "steep")),
    (CoursePointType.FIRST_AID, ("first aid", "hospital", "medical")),
)

_COURSE_POINT_PATTERNS = [
    (point_type, re.compile(r"\b(?:" + "|".join(re.escape(p) for p in phrases) + r")\b"))
    for point_type, phrases in _COURSE_POINT_PHRASES
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    text = dt_str.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def match_course_point_type(name: str, sym: str = "", desc: str = "") -> CoursePointType:
    text = " ".join(part for part in (name, sym, desc) if part).lower()
    for point_type, pattern in _COURSE_POINT_PATTERNS:
        if pattern.search(text):
            return point_type
    return CoursePointType.GENERIC


def _strip_namespaces(root: ET.Element) -> None:
    for elem in root.iter():
        if isinstance(elem.tag, str) and "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]


def _child_text(elem: ET.Element, tag: str) -> Optional[str]:
    child = elem.find(tag)
    if child is not None and child.text and child.text.strip():
        return child.text.strip()
    return None


def _resolve_name(root: ET.Element, course_name: Optional[str]) -> str:
    if course_name and course_name.strip():
        name = course_name
    else:
        name = None
        for path in ("trk/name", "rte/name", "metadata/name", "name"):
            node = root.find(path)
            if node is not None and node.text and node.text.strip():
                name = node.text
                break
        if name is None:
            name = DEFAULT_COURSE_NAME
    return name.strip()[:NAME_MAX_CHARS]


def _float_attr(elem: ET.Element, attr: str) -> Optional[float]:
    value = elem.get(attr)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _optional_float(text: Optional[str]) -> Optional[float]:
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_gpx_string(xml_content: str, course_name: Optional[str] = None, sport: Sport = Sport.CYCLING) -> CourseData:
    root = ET.fromstring(xml_content)
    _strip_namespaces(root)

    name = _resolve_name(root, course_name)

    raw_points = root.findall(".//trkpt")
    if not raw_points:
        raw_points = root.findall(".//rtept")
    if not raw_points:
        raise ValueError("GPX contains no track points (<trkpt>) or route points (<rtept>)")

    points: List[TrackPoint] = []
    total_distance = 0.0
    total_ascent = 0.0
    total_descent = 0.0
    prev: Optional[TrackPoint] = None
    for elem in raw_points:
        lat = _float_attr(elem, "lat")
        lon = _float_attr(elem, "lon")
        if lat is None or lon is None:
            continue
        elevation = _optional_float(_child_text(elem, "ele"))
        timestamp = parse_iso_datetime(_child_text(elem, "time") or "")

        if prev is not None:
            total_distance += haversine_distance(prev.lat, prev.lon, lat, lon)
            if prev.elevation is not None and elevation is not None:
                delta = elevation - prev.elevation
                if abs(delta) > ELEVATION_NOISE_THRESHOLD_M:
                    if delta > 0:
                        total_ascent += delta
                    else:
                        total_descent += -delta

        point = TrackPoint(lat=lat, lon=lon, elevation=elevation, distance=total_distance, timestamp=timestamp)
        points.append(point)
        prev = point

    if not points:
        raise ValueError("GPX contains no points with valid lat/lon")

    course_points: List[CoursePointData] = []
    for wpt in root.findall(".//wpt"):
        lat = _float_attr(wpt, "lat")
        lon = _float_attr(wpt, "lon")
        if lat is None or lon is None:
            continue
        wpt_name = _child_text(wpt, "name") or ""
        wpt_sym = _child_text(wpt, "sym") or ""
        wpt_desc = _child_text(wpt, "desc") or ""
        nearest = min(points, key=lambda p: haversine_distance(p.lat, p.lon, lat, lon))
        course_points.append(
            CoursePointData(
                lat=lat,
                lon=lon,
                distance=nearest.distance,
                point_type=match_course_point_type(wpt_name, wpt_sym, wpt_desc),
                name=wpt_name[:NAME_MAX_CHARS],
                timestamp=parse_iso_datetime(_child_text(wpt, "time") or ""),
            )
        )
    course_points.sort(key=lambda cp: cp.distance)

    return CourseData(
        name=name,
        sport=sport,
        points=points,
        course_points=course_points,
        total_distance=total_distance,
        total_ascent=total_ascent,
        total_descent=total_descent,
        created_at=datetime.now(timezone.utc),
    )


def parse_gpx_file(file_path: Union[str, Path], course_name: Optional[str] = None, sport: Sport = Sport.CYCLING) -> CourseData:
    path = Path(file_path)
    course = parse_gpx_string(path.read_text(encoding="utf-8"), course_name=course_name, sport=sport)
    if course_name is None and course.name == DEFAULT_COURSE_NAME:
        course.name = re.sub(r"[_-]+", " ", path.stem).strip()[:NAME_MAX_CHARS]
    return course
