import unittest
from pathlib import Path
from garmin_connector.converter.gpx_parser import parse_gpx_file, parse_gpx_string
from garmin_connector.converter.fit_encoder import Sport, CoursePointType


class TestGpxParser(unittest.TestCase):
    def test_parse_sample_gpx(self):
        example_path = Path(__file__).parent.parent / "examples" / "sample_hiking_route.gpx"
        course = parse_gpx_file(example_path, sport=Sport.HIKING)

        self.assertEqual(course.name, "Alps High Trail")
        self.assertEqual(course.sport, Sport.HIKING)
        self.assertEqual(len(course.points), 6)
        self.assertGreater(course.total_distance, 1000)  # meters
        self.assertGreaterEqual(course.total_ascent, 300)  # 2100m -> 2450m

        # Check waypoints / course points
        self.assertEqual(len(course.course_points), 3)
        # Summit waypoint
        summit_cp = next((cp for cp in course.course_points if "Peak" in cp.name), None)
        self.assertIsNotNone(summit_cp)
        self.assertEqual(summit_cp.point_type, CoursePointType.SUMMIT)


if __name__ == "__main__":
    unittest.main()
