from pathlib import Path
from typing import Optional, Tuple
from .fit_encoder import FitCourseEncoder, CourseData, Sport
from .gpx_parser import parse_gpx_file

def convert_gpx_to_fit(gpx_path: str | Path, output_fit_path: Optional[str | Path] = None, course_name: Optional[str] = None, sport: Sport = Sport.CYCLING) -> Tuple[Path, CourseData]:
    gpx_path = Path(gpx_path)
    if not gpx_path.exists():
        raise FileNotFoundError(f"{gpx_path} does not exist")
        
    if output_fit_path is None:
        output_fit_path = gpx_path.with_suffix('.fit')
    else:
        output_fit_path = Path(output_fit_path)
        
    output_fit_path.parent.mkdir(parents=True, exist_ok=True)
    
    course_data = parse_gpx_file(gpx_path, course_name, sport)
    encoder = FitCourseEncoder(course_data)
    fit_bytes = encoder.encode()
    
    output_fit_path.write_bytes(fit_bytes)
    return output_fit_path, course_data
