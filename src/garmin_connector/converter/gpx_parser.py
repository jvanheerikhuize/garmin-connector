import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .fit_encoder import CourseData, TrackPoint, CoursePointData, Sport, CoursePointType

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi/2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        dt_str = dt_str.strip().replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None

def match_course_point_type(name: str, sym: str = "", desc: str = "") -> CoursePointType:
    text = f"{name} {sym} {desc}".lower()
    
    categories = [
        (r'left fork', CoursePointType.LEFT_FORK),
        (r'right fork', CoursePointType.RIGHT_FORK),
        (r'sharp left', CoursePointType.SHARP_LEFT),
        (r'sharp right', CoursePointType.SHARP_RIGHT),
        (r'slight left', CoursePointType.SLIGHT_LEFT),
        (r'slight right', CoursePointType.SLIGHT_RIGHT),
        (r'\bleft\b', CoursePointType.LEFT),
        (r'\bright\b', CoursePointType.RIGHT),
        (r'straight|continue|ahead', CoursePointType.STRAIGHT),
        (r'u-turn|uturn', CoursePointType.U_TURN),
        (r'summit|peak|top|mountain', CoursePointType.SUMMIT),
        (r'water|drink|fountain|tap', CoursePointType.WATER),
        (r'food|restaurant|cafe|bakery|lunch', CoursePointType.FOOD),
        (r'danger|warning|caution|steep', CoursePointType.DANGER),
        (r'first aid|hospital|medical', CoursePointType.FIRST_AID),
    ]
    
    for pattern, cp_type in categories:
        if re.search(pattern, text):
            return cp_type
    return CoursePointType.GENERIC

def _strip_namespaces(xml_content: str) -> str:
    return re.sub(r'\sxmlns="[^"]+"', '', xml_content, count=1)

def parse_gpx_string(xml_content: str, course_name: Optional[str] = None, sport: Sport = Sport.CYCLING) -> CourseData:
    xml_content = _strip_namespaces(xml_content)
    root = ET.fromstring(xml_content)
    
    if not course_name:
        for path in ["trk/name", "rte/name", "metadata/name", "name"]:
            el = root.find(path)
            if el is not None and el.text and el.text.strip():
                course_name = el.text.strip()
                break
        if not course_name:
            course_name = "Course"
            
    course_name = course_name[:15]
    course = CourseData(name=course_name, sport=sport, created_at=datetime.now(timezone.utc))
    
    pts = root.findall(".//trkpt")
    if not pts:
        pts = root.findall(".//rtept")
    if not pts:
        raise ValueError("No track points or route points found in GPX")
        
    last_lat = None
    last_lon = None
    last_ele = None
    
    for pt in pts:
        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])
        
        ele_el = pt.find("ele")
        ele = float(ele_el.text) if ele_el is not None and ele_el.text else None
        
        time_el = pt.find("time")
        timestamp = parse_iso_datetime(time_el.text) if time_el is not None else None
        
        if last_lat is not None and last_lon is not None:
            dist = haversine_distance(last_lat, last_lon, lat, lon)
            course.total_distance += dist
        
        if last_ele is not None and ele is not None:
            delta = ele - last_ele
            if abs(delta) > 0.3:
                if delta > 0:
                    course.total_ascent += delta
                else:
                    course.total_descent -= delta
                last_ele = ele
        elif ele is not None:
            last_ele = ele
            
        course.points.append(TrackPoint(lat=lat, lon=lon, elevation=ele, distance=course.total_distance, timestamp=timestamp))
        last_lat, last_lon = lat, lon

    wpts = root.findall(".//wpt")
    for wpt in wpts:
        lat = float(wpt.attrib["lat"])
        lon = float(wpt.attrib["lon"])
        name_el = wpt.find("name")
        name = name_el.text[:15] if name_el is not None and name_el.text else ""
        sym_el = wpt.find("sym")
        sym = sym_el.text if sym_el is not None else ""
        desc_el = wpt.find("desc")
        desc = desc_el.text if desc_el is not None else ""
        
        cp_type = match_course_point_type(name, sym, desc)
        
        # Match to nearest track point by straight-line distance
        nearest_dist = float('inf')
        matched_tp = course.points[0]
        for tp in course.points:
            d = haversine_distance(lat, lon, tp.lat, tp.lon)
            if d < nearest_dist:
                nearest_dist = d
                matched_tp = tp
                
        course.course_points.append(CoursePointData(
            lat=lat, lon=lon,
            distance=matched_tp.distance,
            point_type=cp_type,
            name=name,
            timestamp=matched_tp.timestamp
        ))
        
    course.course_points.sort(key=lambda cp: cp.distance)
    return course

def parse_gpx_file(file_path: str | Path, course_name: Optional[str] = None, sport: Sport = Sport.CYCLING) -> CourseData:
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    
    try:
        course = parse_gpx_string(content, course_name, sport)
        if not course_name and course.name == "Course":
            stem = path.stem.replace('_', ' ').replace('-', ' ')
            course.name = stem[:15]
        return course
    except ValueError as e:
        raise ValueError(f"Error parsing {path}: {str(e)}")
