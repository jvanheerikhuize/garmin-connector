"""
Pure Python Garmin FIT Course Encoder.
Converts track points, waypoints, and course metadata into binary Garmin .FIT course format.
"""

from __future__ import annotations
import struct
import datetime
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional

GARMIN_EPOCH = 631065600  # 1989-12-31 00:00:00 UTC in unix timestamp seconds

# FIT Base Types
BASE_TYPE_ENUM = 0x00
BASE_TYPE_SINT8 = 0x01
BASE_TYPE_UINT8 = 0x02
BASE_TYPE_SINT16 = 0x83
BASE_TYPE_UINT16 = 0x84
BASE_TYPE_SINT32 = 0x85
BASE_TYPE_UINT32 = 0x86
BASE_TYPE_STRING = 0x07
BASE_TYPE_UINT32Z = 0x8C

# Global FIT Message Numbers
MESG_NUM_FILE_ID = 0
MESG_NUM_COURSE = 31
MESG_NUM_LAP = 19
MESG_NUM_RECORD = 20
MESG_NUM_COURSE_POINT = 32

# FIT CRC-16 Table
CRC_TABLE = [
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400
]


def update_crc(crc: int, byte: int) -> int:
    """Updates 16-bit CRC with one byte according to FIT specification."""
    tmp = CRC_TABLE[crc & 0xF]
    crc = (crc >> 4) & 0x0FFF
    crc = crc ^ tmp ^ CRC_TABLE[byte & 0xF]

    tmp = CRC_TABLE[crc & 0xF]
    crc = (crc >> 4) & 0x0FFF
    crc = crc ^ tmp ^ CRC_TABLE[(byte >> 4) & 0xF]
    return crc


def calculate_crc(data: bytes, initial_crc: int = 0) -> int:
    """Calculates FIT CRC-16 over a byte sequence."""
    crc = initial_crc
    for b in data:
        crc = update_crc(crc, b)
    return crc


def deg_to_semicircles(deg: float) -> int:
    """Converts degrees to Garmin 32-bit semicircles (-180..180 -> -2^31..2^31-1)."""
    return int(deg * (2**31 / 180.0))


class Sport(IntEnum):
    GENERIC = 0
    RUNNING = 1
    CYCLING = 2
    HIKING = 11
    WALKING = 11
    TRANSITION = 3
    FITNESS_EQUIPMENT = 4
    SWIMMING = 5
    BASKETBALL = 6
    SOCCER = 7
    TENNIS = 8


class CoursePointType(IntEnum):
    GENERIC = 0
    SUMMIT = 1
    VALLEY = 2
    WATER = 3
    FOOD = 4
    DANGER = 5
    LEFT = 6
    RIGHT = 7
    STRAIGHT = 8
    FIRST_AID = 9
    FOURTH_CATEGORY = 10
    THIRD_CATEGORY = 11
    SECOND_CATEGORY = 12
    FIRST_CATEGORY = 13
    HORS_CATEGORY = 14
    SPRINT = 15
    LEFT_FORK = 16
    RIGHT_FORK = 17
    MIDDLE_FORK = 18
    SLIGHT_LEFT = 19
    SHARP_LEFT = 20
    SLIGHT_RIGHT = 21
    SHARP_RIGHT = 22
    U_TURN = 23
    SEGMENT_START = 24
    SEGMENT_END = 25


@dataclass
class TrackPoint:
    lat: float
    lon: float
    elevation: Optional[float] = None
    distance: float = 0.0  # cumulative meters
    timestamp: Optional[datetime.datetime] = None


@dataclass
class CoursePointData:
    lat: float
    lon: float
    distance: float  # cumulative meters
    point_type: CoursePointType = CoursePointType.GENERIC
    name: str = ""
    timestamp: Optional[datetime.datetime] = None


@dataclass
class CourseData:
    name: str
    sport: Sport = Sport.CYCLING
    points: List[TrackPoint] = field(default_factory=list)
    course_points: List[CoursePointData] = field(default_factory=list)
    total_distance: float = 0.0  # meters
    total_ascent: float = 0.0  # meters
    total_descent: float = 0.0  # meters
    created_at: Optional[datetime.datetime] = None


class FitCourseEncoder:
    """Encodes a CourseData structure into standard Garmin FIT binary format."""

    def __init__(self, course: CourseData):
        self.course = course
        self.epoch_time = self._to_garmin_timestamp(self.course.created_at or datetime.datetime.now(datetime.timezone.utc))

    @staticmethod
    def _to_garmin_timestamp(dt: datetime.datetime) -> int:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        unix_ts = dt.timestamp()
        return max(0, int(unix_ts - GARMIN_EPOCH))

    def _build_field_def(self, field_num: int, size: int, base_type: int) -> bytes:
        return struct.pack("<BBB", field_num, size, base_type)

    def _build_file_id_mesg(self, local_num: int = 0) -> tuple[bytes, bytes]:
        # Definition Message: 0=type(1B enum), 1=manufacturer(2B uint16), 2=product(2B uint16), 3=serial_num(4B uint32z), 4=time_created(4B uint32)
        fields = [
            self._build_field_def(0, 1, BASE_TYPE_ENUM),
            self._build_field_def(1, 2, BASE_TYPE_UINT16),
            self._build_field_def(2, 2, BASE_TYPE_UINT16),
            self._build_field_def(3, 4, BASE_TYPE_UINT32Z),
            self._build_field_def(4, 4, BASE_TYPE_UINT32),
        ]
        def_mesg = struct.pack("<BBBHB", 0x40 | local_num, 0, 0, MESG_NUM_FILE_ID, len(fields)) + b"".join(fields)
        # Data: header(1B), type=6(1B), manufacturer=1(2B), product=0(2B), serial_num=0(4B), time_created=self.epoch_time(4B)
        data_mesg = struct.pack("<BBHHII", local_num, 6, 1, 0, 0, self.epoch_time)
        return def_mesg, data_mesg

    def _build_course_mesg(self, local_num: int = 1) -> tuple[bytes, bytes]:
        # Course Message: 4=sport(1B enum), 5=name(16B string)
        name_bytes = self.course.name.encode("utf-8")[:15] + b"\x00"
        name_len = len(name_bytes)
        fields = [
            self._build_field_def(4, 1, BASE_TYPE_ENUM),
            self._build_field_def(5, name_len, BASE_TYPE_STRING),
        ]
        def_mesg = struct.pack("<BBBHB", 0x40 | local_num, 0, 0, MESG_NUM_COURSE, len(fields)) + b"".join(fields)
        data_mesg = struct.pack(f"<BB{name_len}s", local_num, int(self.course.sport), name_bytes)
        return def_mesg, data_mesg

    def _build_lap_mesg(self, local_num: int = 2) -> tuple[bytes, bytes]:
        # Lap Message:
        # 253=timestamp(4B), 0=start_time(4B), 3=start_lat(4B sint32), 4=start_lon(4B sint32),
        # 5=end_lat(4B sint32), 6=end_lon(4B sint32), 7=total_elapsed_time(4B uint32, ms),
        # 8=total_timer_time(4B uint32, ms), 9=total_distance(4B uint32, cm), 21=total_ascent(2B uint16), 22=total_descent(2B uint16)
        fields = [
            self._build_field_def(253, 4, BASE_TYPE_UINT32),
            self._build_field_def(0, 4, BASE_TYPE_UINT32),
            self._build_field_def(3, 4, BASE_TYPE_SINT32),
            self._build_field_def(4, 4, BASE_TYPE_SINT32),
            self._build_field_def(5, 4, BASE_TYPE_SINT32),
            self._build_field_def(6, 4, BASE_TYPE_SINT32),
            self._build_field_def(7, 4, BASE_TYPE_UINT32),
            self._build_field_def(8, 4, BASE_TYPE_UINT32),
            self._build_field_def(9, 4, BASE_TYPE_UINT32),
            self._build_field_def(21, 2, BASE_TYPE_UINT16),
            self._build_field_def(22, 2, BASE_TYPE_UINT16),
        ]
        def_mesg = struct.pack("<BBBHB", 0x40 | local_num, 0, 0, MESG_NUM_LAP, len(fields)) + b"".join(fields)

        first_pt = self.course.points[0] if self.course.points else TrackPoint(0, 0)
        last_pt = self.course.points[-1] if self.course.points else first_pt

        # Estimate time based on speed if timestamps missing: cycling ~20 km/h (5.5 m/s), hiking ~4.5 km/h (1.25 m/s)
        avg_speed = 5.5 if self.course.sport == Sport.CYCLING else 1.25
        est_duration = int(self.course.total_distance / max(avg_speed, 0.1))
        est_duration_ms = est_duration * 1000

        data_mesg = struct.pack(
            "<BIIiiiiIIIHH",
            local_num,
            self.epoch_time + est_duration,
            self.epoch_time,
            deg_to_semicircles(first_pt.lat),
            deg_to_semicircles(first_pt.lon),
            deg_to_semicircles(last_pt.lat),
            deg_to_semicircles(last_pt.lon),
            est_duration_ms,
            est_duration_ms,
            int(self.course.total_distance * 100),  # cm
            int(min(65535, max(0, self.course.total_ascent))),
            int(min(65535, max(0, self.course.total_descent))),
        )
        return def_mesg, data_mesg

    def _build_record_def(self, local_num: int = 3) -> bytes:
        # Record Message:
        # 253=timestamp(4B), 0=lat(4B sint32), 1=lon(4B sint32), 2=altitude(2B uint16, scale 5, offset 500), 5=distance(4B uint32, cm)
        fields = [
            self._build_field_def(253, 4, BASE_TYPE_UINT32),
            self._build_field_def(0, 4, BASE_TYPE_SINT32),
            self._build_field_def(1, 4, BASE_TYPE_SINT32),
            self._build_field_def(2, 2, BASE_TYPE_UINT16),
            self._build_field_def(5, 4, BASE_TYPE_UINT32),
        ]
        return struct.pack("<BBBHB", 0x40 | local_num, 0, 0, MESG_NUM_RECORD, len(fields)) + b"".join(fields)

    def _build_record_data(self, pt: TrackPoint, cumulative_time: int, local_num: int = 3) -> bytes:
        alt_raw = 0xFFFF
        if pt.elevation is not None:
            # Altitude = (elevation_m + 500) * 5
            alt_calc = int((pt.elevation + 500.0) * 5.0)
            alt_raw = max(0, min(65534, alt_calc))

        dist_cm = int(pt.distance * 100)
        return struct.pack(
            "<BIiiHI",
            local_num,
            self.epoch_time + cumulative_time,
            deg_to_semicircles(pt.lat),
            deg_to_semicircles(pt.lon),
            alt_raw,
            dist_cm,
        )

    def _build_course_point_def(self, local_num: int = 4, name_len: int = 16) -> bytes:
        # CoursePoint:
        # 253=timestamp(4B), 1=lat(4B sint32), 2=lon(4B sint32), 3=distance(4B uint32, cm), 4=type(1B enum), 5=name(NB string)
        fields = [
            self._build_field_def(253, 4, BASE_TYPE_UINT32),
            self._build_field_def(1, 4, BASE_TYPE_SINT32),
            self._build_field_def(2, 4, BASE_TYPE_SINT32),
            self._build_field_def(3, 4, BASE_TYPE_UINT32),
            self._build_field_def(4, 1, BASE_TYPE_ENUM),
            self._build_field_def(5, name_len, BASE_TYPE_STRING),
        ]
        return struct.pack("<BBBHB", 0x40 | local_num, 0, 0, MESG_NUM_COURSE_POINT, len(fields)) + b"".join(fields)

    def _build_course_point_data(self, cp: CoursePointData, name_len: int = 16, local_num: int = 4) -> bytes:
        name_bytes = cp.name.encode("utf-8")[: name_len - 1] + b"\x00"
        name_bytes = name_bytes.ljust(name_len, b"\x00")
        ts = self._to_garmin_timestamp(cp.timestamp) if cp.timestamp else self.epoch_time
        return struct.pack(
            f"<BIiiIB{name_len}s",
            local_num,
            ts,
            deg_to_semicircles(cp.lat),
            deg_to_semicircles(cp.lon),
            int(cp.distance * 100),
            int(cp.point_type),
            name_bytes,
        )

    def encode(self) -> bytes:
        """Encodes course into complete FIT binary bytes."""
        payload = bytearray()

        # 1. File ID message
        fid_def, fid_data = self._build_file_id_mesg(0)
        payload.extend(fid_def)
        payload.extend(fid_data)

        # 2. Course message
        crs_def, crs_data = self._build_course_mesg(1)
        payload.extend(crs_def)
        payload.extend(crs_data)

        # 3. Lap message
        lap_def, lap_data = self._build_lap_mesg(2)
        payload.extend(lap_def)
        payload.extend(lap_data)

        # 4. Record messages
        if self.course.points:
            rec_def = self._build_record_def(3)
            payload.extend(rec_def)

            avg_speed = 5.5 if self.course.sport == Sport.CYCLING else 1.25
            for pt in self.course.points:
                if pt.timestamp:
                    cur_time = self._to_garmin_timestamp(pt.timestamp) - self.epoch_time
                else:
                    cur_time = int(pt.distance / max(avg_speed, 0.1))
                payload.extend(self._build_record_data(pt, max(0, cur_time), 3))

        # 5. Course Points (waypoint cues)
        if self.course.course_points:
            cp_name_len = 16
            cp_def = self._build_course_point_def(4, cp_name_len)
            payload.extend(cp_def)
            for cp in self.course.course_points:
                payload.extend(self._build_course_point_data(cp, cp_name_len, 4))

        # 6. Construct 14-byte Header
        data_size = len(payload)
        header_without_crc = struct.pack(
            "<BBHI4s",
            14,      # Header size
            0x20,    # FIT protocol version 2.0
            2100,    # Profile version 21.00
            data_size,
            b".FIT",
        )
        header_crc = calculate_crc(header_without_crc)
        header = header_without_crc + struct.pack("<H", header_crc)

        # 7. File CRC (over header + payload)
        file_crc = calculate_crc(header + payload)
        crc_bytes = struct.pack("<H", file_crc)

        return bytes(header + payload + crc_bytes)
