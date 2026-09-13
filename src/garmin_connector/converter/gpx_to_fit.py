"""
GPX to Garmin FIT Course Converter.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from .fit_encoder import FitCourseEncoder, CourseData, Sport
from .gpx_parser import parse_gpx_file, parse_gpx_string


def convert_gpx_to_fit(
    gpx_path: str | Path,
    output_fit_path: Optional[str | Path] = None,
    course_name: Optional[str] = None,
    sport: Sport = Sport.CYCLING,
    enrich_dem: bool = True,
) -> tuple[Path, CourseData]:
    """
    Converts a GPX file into a Garmin .FIT course file.

    Args:
        gpx_path: Path to input .gpx file.
        output_fit_path: Destination path for .fit file. Defaults to same directory and stem.
        course_name: Optional custom course name (truncated to 15 chars for Garmin).
        sport: Sport type (Sport.CYCLING, Sport.HIKING, Sport.RUNNING).
        enrich_dem: Automatically fetch DEM topography if GPX elevation is missing/flat.

    Returns:
        tuple[Path, CourseData]: The written .FIT file path and parsed CourseData.
    """
    in_path = Path(gpx_path)
    if not in_path.exists():
        raise FileNotFoundError(f"Input GPX file does not exist: {gpx_path}")

    if output_fit_path is None:
        out_path = in_path.with_suffix(".fit")
    else:
        out_path = Path(output_fit_path)

    course_data = parse_gpx_file(in_path, course_name=course_name, sport=sport)

    encoder = FitCourseEncoder(course_data)
    fit_bytes = encoder.encode()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(fit_bytes)

    return out_path, course_data
