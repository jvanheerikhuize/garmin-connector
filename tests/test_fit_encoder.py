import struct
import datetime
import unittest
from garmin_connector.converter.fit_encoder import (
    FitCourseEncoder,
    CourseData,
    TrackPoint,
    CoursePointData,
    Sport,
    CoursePointType,
    calculate_crc,
    deg_to_semicircles,
)


class TestFitEncoder(unittest.TestCase):
    def test_deg_to_semicircles(self):
        # 0 deg -> 0
        self.assertEqual(deg_to_semicircles(0.0), 0)
        # 180 deg -> 2^31 - 1
        self.assertLessEqual(abs(deg_to_semicircles(180.0) - (2**31)), 1)
        # -180 deg -> -2^31
        self.assertLessEqual(abs(deg_to_semicircles(-180.0) - (-2**31)), 1)

    def test_fit_encoder_basic(self):
        pts = [
            TrackPoint(lat=52.3676, lon=4.9041, elevation=10.0, distance=0.0),
            TrackPoint(lat=52.3700, lon=4.9100, elevation=12.0, distance=500.0),
            TrackPoint(lat=52.3750, lon=4.9200, elevation=15.0, distance=1500.0),
        ]
        c_pts = [
            CoursePointData(lat=52.3700, lon=4.9100, distance=500.0, point_type=CoursePointType.RIGHT, name="Turn Right"),
        ]
        course = CourseData(
            name="Amsterdam Ride",
            sport=Sport.CYCLING,
            points=pts,
            course_points=c_pts,
            total_distance=1500.0,
            total_ascent=5.0,
            total_descent=0.0,
            created_at=datetime.datetime(2026, 9, 4, 12, 0, 0, tzinfo=datetime.timezone.utc),
        )

        encoder = FitCourseEncoder(course)
        encoded = encoder.encode()

        self.assertGreater(len(encoded), 50)
        self.assertEqual(encoded[8:12], b".FIT")
        header_size = encoded[0]
        self.assertEqual(header_size, 14)

        # Validate header CRC
        header_data = encoded[:12]
        expected_header_crc = struct.unpack("<H", encoded[12:14])[0]
        self.assertEqual(calculate_crc(header_data), expected_header_crc)

        # Validate file CRC
        file_content = encoded[:-2]
        expected_file_crc = struct.unpack("<H", encoded[-2:])[0]
        self.assertEqual(calculate_crc(file_content), expected_file_crc)


if __name__ == "__main__":
    unittest.main()
