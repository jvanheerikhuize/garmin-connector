"""
Route & Course file converter module (GPX, FIT).
"""

from .fit_encoder import FitCourseEncoder, CourseData, TrackPoint, CoursePointData, Sport, CoursePointType
from .gpx_parser import parse_gpx_file, parse_gpx_string
from .gpx_to_fit import convert_gpx_to_fit
from .elevation import enrich_course_elevation

__all__ = [
    "FitCourseEncoder",
    "CourseData",
    "TrackPoint",
    "CoursePointData",
    "Sport",
    "CoursePointType",
    "parse_gpx_file",
    "parse_gpx_string",
    "convert_gpx_to_fit",
    "enrich_course_elevation",
]
