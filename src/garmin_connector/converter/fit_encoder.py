from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional
from datetime import datetime
import struct

GARMIN_EPOCH = 631065600

def calculate_crc(data: bytes, initial_crc: int = 0) -> int:
    crc_table = [
        0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
        0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400
    ]
    crc = initial_crc
    for byte in data:
        # compute for lower nibble
        tmp = crc_table[crc & 0x0F]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ crc_table[byte & 0x0F]
        # compute for upper nibble
        tmp = crc_table[crc & 0x0F]
        crc = (crc >> 4) & 0x0FFF
        crc = crc ^ tmp ^ crc_table[(byte >> 4) & 0x0F]
    return crc

def deg_to_semicircles(deg: float) -> int:
    return int(deg * (2**31 / 180.0))

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

class FitCourseEncoder:
    def __init__(self, course: CourseData):
        self.course = course
        self.time_created = self._garmin_ts(self.course.created_at) if self.course.created_at else self._garmin_ts(datetime.utcnow())
        self.avg_speed = 5.5 if self.course.sport == Sport.CYCLING else 1.25
        if self.avg_speed < 0.1:
            self.avg_speed = 0.1
        self.est_duration_s = int(self.course.total_distance / self.avg_speed)
        
    def _garmin_ts(self, dt: Optional[datetime]) -> int:
        if not dt:
            return 0
        unix_seconds = dt.timestamp()
        return max(0, int(unix_seconds - GARMIN_EPOCH))

    def _pack_string(self, s: str, max_len: int) -> bytes:
        b = s.encode('utf-8')[:max_len-1]
        return b.ljust(max_len, b'\x00')

    def encode(self) -> bytes:
        payload = bytearray()

        # 1. File ID
        payload.extend(struct.pack("<BBBHB", 0x40, 0, 0, 0, 5))
        payload.extend(struct.pack("<BBB", 0, 1, 0x00)) # type
        payload.extend(struct.pack("<BBB", 1, 2, 0x84)) # manufacturer
        payload.extend(struct.pack("<BBB", 2, 2, 0x84)) # product
        payload.extend(struct.pack("<BBB", 3, 4, 0x8C)) # serial
        payload.extend(struct.pack("<BBB", 4, 4, 0x86)) # time_created
        payload.extend(struct.pack("<B", 0))
        payload.extend(struct.pack("<BHHII", 6, 1, 0, 0, self.time_created))

        # 2. Course
        encoded_name = self.course.name.encode('utf-8')[:15] + b'\x00'
        name_len = len(encoded_name)
        payload.extend(struct.pack("<BBBHB", 0x41, 0, 0, 31, 2))
        payload.extend(struct.pack("<BBB", 4, 1, 0x00)) # sport
        payload.extend(struct.pack("<BBB", 5, name_len, 0x07)) # name
        payload.extend(struct.pack("<B", 1))
        payload.extend(struct.pack(f"<B{name_len}s", self.course.sport.value, encoded_name))

        # 3. Lap
        payload.extend(struct.pack("<BBBHB", 0x42, 0, 0, 19, 11))
        payload.extend(struct.pack("<BBB", 253, 4, 0x86)) # timestamp
        payload.extend(struct.pack("<BBB", 0, 4, 0x86)) # start_time
        payload.extend(struct.pack("<BBB", 3, 4, 0x85)) # start_lat
        payload.extend(struct.pack("<BBB", 4, 4, 0x85)) # start_lon
        payload.extend(struct.pack("<BBB", 5, 4, 0x85)) # end_lat
        payload.extend(struct.pack("<BBB", 6, 4, 0x85)) # end_lon
        payload.extend(struct.pack("<BBB", 7, 4, 0x86)) # total_elapsed
        payload.extend(struct.pack("<BBB", 8, 4, 0x86)) # total_timer
        payload.extend(struct.pack("<BBB", 9, 4, 0x86)) # total_distance
        payload.extend(struct.pack("<BBB", 21, 2, 0x84)) # total_ascent
        payload.extend(struct.pack("<BBB", 22, 2, 0x84)) # total_descent

        start_lat = deg_to_semicircles(self.course.points[0].lat) if self.course.points else 0
        start_lon = deg_to_semicircles(self.course.points[0].lon) if self.course.points else 0
        end_lat = deg_to_semicircles(self.course.points[-1].lat) if self.course.points else 0
        end_lon = deg_to_semicircles(self.course.points[-1].lon) if self.course.points else 0
        
        payload.extend(struct.pack("<B", 2))
        payload.extend(struct.pack("<IIiiiiIIIHH",
            self.time_created + self.est_duration_s,
            self.time_created,
            start_lat, start_lon, end_lat, end_lon,
            self.est_duration_s * 1000,
            self.est_duration_s * 1000,
            int(self.course.total_distance * 100),
            max(0, min(65535, int(self.course.total_ascent))),
            max(0, min(65535, int(self.course.total_descent)))
        ))

        # 4. Record
        if self.course.points:
            payload.extend(struct.pack("<BBBHB", 0x43, 0, 0, 20, 5))
            payload.extend(struct.pack("<BBB", 253, 4, 0x86))
            payload.extend(struct.pack("<BBB", 0, 4, 0x85))
            payload.extend(struct.pack("<BBB", 1, 4, 0x85))
            payload.extend(struct.pack("<BBB", 2, 2, 0x84))
            payload.extend(struct.pack("<BBB", 5, 4, 0x86))
            
            for pt in self.course.points:
                payload.extend(struct.pack("<B", 3))
                if pt.timestamp:
                    t = self._garmin_ts(pt.timestamp) - self.time_created
                else:
                    t = int(pt.distance / self.avg_speed)
                t = max(0, t)
                
                alt = 0xFFFF
                if pt.elevation is not None:
                    alt = max(0, min(65534, int((pt.elevation + 500) * 5)))
                    
                payload.extend(struct.pack("<IiiHI",
                    self.time_created + t,
                    deg_to_semicircles(pt.lat),
                    deg_to_semicircles(pt.lon),
                    alt,
                    int(pt.distance * 100)
                ))

        # 5. Course Point
        if self.course.course_points:
            payload.extend(struct.pack("<BBBHB", 0x44, 0, 0, 32, 6))
            payload.extend(struct.pack("<BBB", 253, 4, 0x86))
            payload.extend(struct.pack("<BBB", 1, 4, 0x85))
            payload.extend(struct.pack("<BBB", 2, 4, 0x85))
            payload.extend(struct.pack("<BBB", 3, 4, 0x86))
            payload.extend(struct.pack("<BBB", 4, 1, 0x00))
            payload.extend(struct.pack("<BBB", 5, 16, 0x07))
            
            for cp in self.course.course_points:
                payload.extend(struct.pack("<B", 4))
                ts = self._garmin_ts(cp.timestamp) if cp.timestamp else self.time_created
                
                name_bytes = self._pack_string(cp.name, 16)
                payload.extend(struct.pack(f"<IiiIB16s",
                    ts,
                    deg_to_semicircles(cp.lat),
                    deg_to_semicircles(cp.lon),
                    int(cp.distance * 100),
                    cp.point_type.value,
                    name_bytes
                ))

        # Header
        header = struct.pack("<BBHI4s", 14, 0x20, 2100, len(payload), b'.FIT')
        header_crc = calculate_crc(header)
        header_full = header + struct.pack("<H", header_crc)
        
        # File CRC
        file_crc = calculate_crc(payload, calculate_crc(header_full))
        
        return header_full + payload + struct.pack("<H", file_crc)
