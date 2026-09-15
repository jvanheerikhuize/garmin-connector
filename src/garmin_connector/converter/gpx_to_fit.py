from pathlib import Path
from typing import Optional, Tuple, Union

from garmin_connector.converter.fit_encoder import CourseData, FitCourseEncoder, Sport
from garmin_connector.converter.gpx_parser import parse_gpx_file


def convert_gpx_to_fit(
    gpx_path: Union[str, Path],
    output_fit_path: Optional[Union[str, Path]] = None,
    course_name: Optional[str] = None,
    sport: Sport = Sport.CYCLING,
) -> Tuple[Path, CourseData]:
    source = Path(gpx_path)
    if not source.exists():
        raise FileNotFoundError(f"GPX file not found: {source}")

    output = Path(output_fit_path) if output_fit_path is not None else source.with_suffix(".fit")
    output.parent.mkdir(parents=True, exist_ok=True)

    course = parse_gpx_file(source, course_name=course_name, sport=sport)
    output.write_bytes(FitCourseEncoder(course).encode())
    return output, course
