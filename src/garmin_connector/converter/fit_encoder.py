import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import List, Optional

GARMIN_EPOCH: int = 631065600

_CRC_TABLE = (
    0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
    0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400,
)

_BASE_ENUM = 0x00
_BASE_STRING = 0x07
_BASE_UINT16 = 0x84
_BASE_SINT32 = 0x85
_BASE_UINT32 = 0x86
_BASE_UINT32Z = 0x8C

_MESG_FILE_ID = 0
_MESG_LAP = 19
_MESG_RECORD = 20
_MESG_COURSE = 31
_MESG_COURSE_POINT = 32

_ALTITUDE_UNKNOWN = 0xFFFF
_NAME_MAX_BYTES = 15
_CYCLING_SPEED = 5.5
_DEFAULT_SPEED = 1.25


def calculate_crc(data: bytes, initial_crc: int = 0) -> int:
    crc = initial_crc
    for byte in data:
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[byte & 0xF]
        tmp = _CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ _CRC_TABLE[(byte >> 4) & 0xF]
    return crc


def deg_to_semicircles(deg: float) -> int:
    return int(deg * (2**31 / 180.0))


def garmin_timestamp(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, int(dt.timestamp() - GARMIN_EPOCH))


class Sport(IntEnum):
    GENERIC = 0
    RUNNING = 1
    CYCLING = 2
    TRANSITION = 3
    FITNESS_EQUIPMENT = 4
    SWIMMING = 5
    BASKETBALL = 6
    SOCCER = 7
    TENNIS = 8
    HIKING = 11
    WALKING = 11


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
    distance: float = 0.0
    timestamp: Optional[datetime] = None


@dataclass
class CoursePointData:
    lat: float
    lon: float
    distance: float
    point_type: CoursePointType = CoursePointType.GENERIC
    name: str = ""
    timestamp: Optional[datetime] = None


@dataclass
class CourseData:
    name: str
    sport: Sport = Sport.CYCLING
    points: List[TrackPoint] = field(default_factory=list)
    course_points: List[CoursePointData] = field(default_factory=list)
    total_distance: float = 0.0
    total_ascent: float = 0.0
    total_descent: float = 0.0
    created_at: Optional[datetime] = None


def _truncate_utf8(text: str, max_bytes: int) -> bytes:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return encoded
    encoded = encoded[:max_bytes]
    while encoded:
        try:
            encoded.decode("utf-8")
            return encoded
        except UnicodeDecodeError:
            encoded = encoded[:-1]
    return b""


def _name_field(name: str) -> bytes:
    return _truncate_utf8(name, _NAME_MAX_BYTES) + b"\x00"


def _clamp(value: float, low: int, high: int) -> int:
    return int(max(low, min(high, value)))


class FitCourseEncoder:
    def __init__(self, course: CourseData):
        self.course = course

    def encode(self) -> bytes:
        payload = self._encode_payload()
        header = struct.pack("<BBHI4s", 14, 0x20, 2100, len(payload), b".FIT")
        header += struct.pack("<H", calculate_crc(header))
        body = header + payload
        return body + struct.pack("<H", calculate_crc(body))

    def _avg_speed(self) -> float:
        speed = _CYCLING_SPEED if self.course.sport == Sport.CYCLING else _DEFAULT_SPEED
        return max(0.1, speed)

    def _encode_payload(self) -> bytes:
        course = self.course
        created = course.created_at or datetime.now(timezone.utc)
        time_created = garmin_timestamp(created)
        avg_speed = self._avg_speed()
        est_duration_s = int(course.total_distance / avg_speed)

        out = bytearray()

        out += self._definition(0, _MESG_FILE_ID, [(0, 1, _BASE_ENUM), (1, 2, _BASE_UINT16), (2, 2, _BASE_UINT16), (3, 4, _BASE_UINT32Z), (4, 4, _BASE_UINT32)])
        out += self._data(0, struct.pack("<BHHII", 6, 1, 0, 0, time_created))

        name_bytes = _name_field(course.name)
        out += self._definition(1, _MESG_COURSE, [(4, 1, _BASE_ENUM), (5, len(name_bytes), _BASE_STRING)])
        out += self._data(1, struct.pack("<B", int(course.sport)) + name_bytes)

        points = course.points
        if points:
            start_lat, start_lon = deg_to_semicircles(points[0].lat), deg_to_semicircles(points[0].lon)
            end_lat, end_lon = deg_to_semicircles(points[-1].lat), deg_to_semicircles(points[-1].lon)
        else:
            start_lat = start_lon = end_lat = end_lon = 0
        elapsed_ms = est_duration_s * 1000
        out += self._definition(
            2,
            _MESG_LAP,
            [
                (253, 4, _BASE_UINT32),
                (0, 4, _BASE_UINT32),
                (3, 4, _BASE_SINT32),
                (4, 4, _BASE_SINT32),
                (5, 4, _BASE_SINT32),
                (6, 4, _BASE_SINT32),
                (7, 4, _BASE_UINT32),
                (8, 4, _BASE_UINT32),
                (9, 4, _BASE_UINT32),
                (21, 2, _BASE_UINT16),
                (22, 2, _BASE_UINT16),
            ],
        )
        out += self._data(
            2,
            struct.pack(
                "<IIiiiiIIIHH",
                time_created + est_duration_s,
                time_created,
                start_lat,
                start_lon,
                end_lat,
                end_lon,
                elapsed_ms,
                elapsed_ms,
                int(course.total_distance * 100),
                _clamp(course.total_ascent, 0, 65535),
                _clamp(course.total_descent, 0, 65535),
            ),
        )

        if points:
            out += self._definition(
                3,
                _MESG_RECORD,
                [(253, 4, _BASE_UINT32), (0, 4, _BASE_SINT32), (1, 4, _BASE_SINT32), (2, 2, _BASE_UINT16), (5, 4, _BASE_UINT32)],
            )
            for point in points:
                if point.timestamp is not None:
                    t = garmin_timestamp(point.timestamp) - time_created
                else:
                    t = int(point.distance / avg_speed)
                t = max(0, t)
                if point.elevation is None:
                    altitude = _ALTITUDE_UNKNOWN
                else:
                    altitude = _clamp(int((point.elevation + 500) * 5), 0, 65534)
                out += self._data(
                    3,
                    struct.pack(
                        "<IiiHI",
                        time_created + t,
                        deg_to_semicircles(point.lat),
                        deg_to_semicircles(point.lon),
                        altitude,
                        int(point.distance * 100),
                    ),
                )

        if course.course_points:
            out += self._definition(
                4,
                _MESG_COURSE_POINT,
                [(253, 4, _BASE_UINT32), (1, 4, _BASE_SINT32), (2, 4, _BASE_SINT32), (3, 4, _BASE_UINT32), (4, 1, _BASE_ENUM), (5, 16, _BASE_STRING)],
            )
            for cp in course.course_points:
                ts = garmin_timestamp(cp.timestamp) if cp.timestamp is not None else time_created
                out += self._data(
                    4,
                    struct.pack(
                        "<IiiIB16s",
                        ts,
                        deg_to_semicircles(cp.lat),
                        deg_to_semicircles(cp.lon),
                        int(cp.distance * 100),
                        int(cp.point_type),
                        _name_field(cp.name).ljust(16, b"\x00"),
                    ),
                )

        return bytes(out)

    @staticmethod
    def _definition(local_num: int, global_num: int, fields: List[tuple]) -> bytes:
        out = struct.pack("<BBBHB", 0x40 | local_num, 0, 0, global_num, len(fields))
        for field_num, size, base_type in fields:
            out += struct.pack("<BBB", field_num, size, base_type)
        return out

    @staticmethod
    def _data(local_num: int, packed: bytes) -> bytes:
        return struct.pack("<B", local_num) + packed
