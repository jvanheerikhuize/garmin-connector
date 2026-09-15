---
id: gpx-fit-conversion
title: GPX <-> FIT Conversion
tier: feature
status: implemented
owners: [jerry]
depends_on: []
last_updated: 2026-09-15
---

# GPX ↔ FIT Conversion

`src/garmin_connector/converter/{gpx_parser,fit_encoder,gpx_to_fit}.py`

## Purpose

Parse GPX route/track files into an internal course representation, and encode that representation into a Garmin-native binary `.FIT` course file — both implemented from scratch with only stdlib (`xml.etree.ElementTree`, `struct`), no third-party FIT/GPX library involved in the write path.

## `gpx_parser.py` requirements

### Distance/elevation math
- `haversine_distance(lat1, lon1, lat2, lon2) -> meters`: standard great-circle formula, Earth radius `6371000.0` m.
- Elevation noise filter: a step is counted toward `total_ascent`/`total_descent` only if the absolute elevation delta between consecutive points exceeds `0.3` m; smaller deltas are ignored as noise.

### Course point (cue) type inference (`match_course_point_type`)
- Given a waypoint's `name`, `sym`, `desc` (concatenated, lowercased), regex-match against an **ordered** list of phrase categories and return the first match: left fork → right fork → sharp left → sharp right → slight left → slight right → left → right → straight/continue/ahead → u-turn → summit/peak/top/mountain → water/drink/fountain/tap → food/restaurant/cafe/bakery/lunch → danger/warning/caution/steep → first aid/hospital/medical → else `GENERIC`.
- Order matters: more specific phrases (e.g. "sharp left") MUST be checked before the generic "left" to avoid misclassification.
- Matches are whole-word (`\b`-bounded regex), so e.g. "Trailhead" does not match "ahead" and "Leftover" does not match "left". The u-turn category also accepts `u turn` and `uturn`.

### GPX parsing (`parse_gpx_string` / `parse_gpx_file`)
- Strips XML namespaces from all elements before querying (namespace-agnostic).
- Course name resolution order: explicit `course_name` argument → first non-empty text found at `trk/name`, `rte/name`, `metadata/name`, `name` (in that order) → literal `"Course"`. Final name is trimmed and truncated to **15 characters** (Garmin field limit).
- `parse_gpx_file` additionally: if no `course_name` was given AND the resolved name is still the literal `"Course"` (i.e. nothing better was found), derive a name from the filename stem (underscores/hyphens replaced with spaces, truncated to 15 chars) instead.
- Point source: prefer `<trkpt>` elements; if none exist, fall back to `<rtept>` elements. If neither exists, raise `ValueError`.
- Each point captures `lat`, `lon`, optional `ele`, optional parsed `<time>` (ISO 8601, trailing `Z` normalized to `+00:00`; unparseable text yields `None`, not an error).
- Points are emitted in document order with cumulative haversine distance from the previous point (`TrackPoint.distance`), and running totals for `total_distance`, `total_ascent`, `total_descent`.
- Waypoints (`<wpt>`) become `CoursePointData`: matched to the *nearest* track point by straight-line haversine distance (not necessarily the nearest *along-route* point), inheriting that point's cumulative distance; name truncated to 15 chars; type inferred via `match_course_point_type`. Final list sorted by distance ascending.
- `created_at` is always "now" (UTC), not derived from GPX content.

## `fit_encoder.py` requirements

### Encoding rules (summary — the byte-exact layout follows)
- Garmin epoch offset is `631065600` (1989-12-31T00:00:00Z as a Unix timestamp); all FIT timestamps are seconds since this epoch, floored at 0.
- Lat/lon are 32-bit semicircles; altitude is `(elevation_m + 500) * 5` with `0xFFFF` as the unknown sentinel; distances are centimeters; ascent/descent clamp to `uint16`.
- The file's `time_created` is `CourseData.created_at` if set, else now (UTC). It is the base for every relative timestamp below.

### Binary layout (byte-exact — a regenerated encoder MUST produce identical bytes for identical input)

**File header (14 bytes, little-endian):**
```
u8   header_size      = 14
u8   protocol_version = 0x20
u16  profile_version  = 2100
u32  data_size        = len(payload)   # bytes between header and trailing CRC
4s   magic            = ".FIT"
u16  header_crc       = crc16(first 12 header bytes)
```
**Trailer:** `u16 file_crc = crc16(header[14 bytes incl. header_crc] + payload)`.

**CRC-16** is the FIT nibble-table algorithm, seed 0, processing low nibble then high nibble of each byte, with table:
```
0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400
```

**Definition message:** `u8 (0x40 | local_num)`, `u8 reserved=0`, `u8 architecture=0` (little-endian), `u16 global_mesg_num`, `u8 field_count`, then `field_count × (u8 field_def_num, u8 size_bytes, u8 base_type)`.
**Data message:** `u8 local_num`, then the field values packed little-endian in definition order.

**Base type codes used:** `ENUM=0x00`, `UINT16=0x84`, `SINT32=0x85`, `UINT32=0x86`, `STRING=0x07`, `UINT32Z=0x8C`.

### Messages emitted, in order (each definition immediately followed by its data message(s))

**1. File ID** — global `0`, local `0`, exactly one data message:
| field | name | size | base type | value |
|---|---|---|---|---|
| 0 | type | 1 | ENUM | `6` (course) |
| 1 | manufacturer | 2 | UINT16 | `1` (garmin) |
| 2 | product | 2 | UINT16 | `0` |
| 3 | serial_number | 4 | UINT32Z | `0` |
| 4 | time_created | 4 | UINT32 | file creation time (Garmin epoch) |

**2. Course** — global `31`, local `1`, one data message:
| field | name | size | base type | value |
|---|---|---|---|---|
| 4 | sport | 1 | ENUM | `Sport` value |
| 5 | name | N | STRING | UTF-8 name truncated to 15 bytes + `\x00`; N = actual length (≤16) |

**3. Lap** — global `19`, local `2`, one data message:
| field | name | size | base type | value |
|---|---|---|---|---|
| 253 | timestamp | 4 | UINT32 | `time_created + est_duration_s` |
| 0 | start_time | 4 | UINT32 | `time_created` |
| 3 | start_position_lat | 4 | SINT32 | first point lat, semicircles |
| 4 | start_position_long | 4 | SINT32 | first point lon, semicircles |
| 5 | end_position_lat | 4 | SINT32 | last point lat, semicircles |
| 6 | end_position_long | 4 | SINT32 | last point lon, semicircles |
| 7 | total_elapsed_time | 4 | UINT32 | `est_duration_s * 1000` (ms) |
| 8 | total_timer_time | 4 | UINT32 | `est_duration_s * 1000` (ms) |
| 9 | total_distance | 4 | UINT32 | `int(total_distance_m * 100)` (cm) |
| 21 | total_ascent | 2 | UINT16 | `int(clamp(total_ascent_m, 0, 65535))` |
| 22 | total_descent | 2 | UINT16 | `int(clamp(total_descent_m, 0, 65535))` |
- If there are no track points, start/end positions are `(0, 0)`.
- `est_duration_s = int(total_distance_m / avg_speed)` where **avg_speed = 5.5 m/s for `Sport.CYCLING`, else 1.25 m/s** (applies to hiking/running/walking alike — a known simplification, not per-sport-accurate). Guard: `avg_speed` is never below 0.1.

**4. Record** — global `20`, local `3`, one definition then one data message **per track point** (section omitted entirely if there are no points):
| field | name | size | base type | value |
|---|---|---|---|---|
| 253 | timestamp | 4 | UINT32 | `time_created + t`, see below |
| 0 | position_lat | 4 | SINT32 | semicircles |
| 1 | position_long | 4 | SINT32 | semicircles |
| 2 | altitude | 2 | UINT16 | `clamp(int((elevation_m + 500) * 5), 0, 65534)`, or `0xFFFF` if elevation is unknown |
| 5 | distance | 4 | UINT32 | `int(cumulative_m * 100)` (cm) |
- `t` = `garmin_ts(point.timestamp) - time_created` if the point has a GPX timestamp, else `int(point.distance_m / avg_speed)` (same avg_speed rule as Lap); floored at 0.

**5. Course Point** — global `32`, local `4`, one definition then one data message **per course point** (section omitted entirely if there are none):
| field | name | size | base type | value |
|---|---|---|---|---|
| 1 | timestamp | 4 | UINT32 | `garmin_ts(cp.timestamp)` if present, else `time_created` |
| 2 | position_lat | 4 | SINT32 | semicircles |
| 3 | position_long | 4 | SINT32 | semicircles |
| 4 | distance | 4 | UINT32 | `int(cp.distance_m * 100)` (cm) |
| 5 | type | 1 | ENUM | `CoursePointType` value |
| 6 | name | 16 | STRING | UTF-8 name truncated to 15 bytes + `\x00`, right-padded with `\x00` to exactly 16 |
- Field numbers follow Garmin's published `course_point` profile (note: unlike `record`/`lap`, this message's timestamp is field `1`, not `253`). A third-party reader such as `fitparse` MUST decode `timestamp`, `position_lat`, `position_long`, `distance`, `type` and `name` by name from the emitted file.

**Conversions:**
- `garmin_ts(dt)`: naive datetimes are treated as UTC; `max(0, int(unix_seconds - 631065600))`.
- Semicircles: `int(degrees * (2**31 / 180.0))` — truncation toward zero via `int()`, not rounding.

### `Sport` enum (must match Garmin FIT profile)
```
GENERIC=0  RUNNING=1  CYCLING=2  TRANSITION=3  FITNESS_EQUIPMENT=4  SWIMMING=5
BASKETBALL=6  SOCCER=7  TENNIS=8  HIKING=11  WALKING=11
```
`HIKING` and `WALKING` intentionally share value 11. Only `CYCLING`, `HIKING`, `RUNNING` are selectable from the GUI; the rest exist so the enum matches Garmin's profile.

### `CoursePointType` enum (must match Garmin FIT `course_point` profile byte-for-byte — the watch firmware interprets these as fixed values)
```
GENERIC=0        SUMMIT=1          VALLEY=2          WATER=3           FOOD=4
DANGER=5         LEFT=6            RIGHT=7           STRAIGHT=8        FIRST_AID=9
FOURTH_CATEGORY=10  THIRD_CATEGORY=11  SECOND_CATEGORY=12  FIRST_CATEGORY=13  HORS_CATEGORY=14
SPRINT=15        LEFT_FORK=16      RIGHT_FORK=17     MIDDLE_FORK=18    SLIGHT_LEFT=19
SHARP_LEFT=20    SLIGHT_RIGHT=21   SHARP_RIGHT=22    U_TURN=23         SEGMENT_START=24
SEGMENT_END=25
```

## `gpx_to_fit.py` requirements
- `convert_gpx_to_fit(gpx_path, output_fit_path=None, course_name=None, sport=CYCLING) -> (Path, CourseData)`.
- Raises `FileNotFoundError` if `gpx_path` doesn't exist.
- Default output path: same directory/stem as input with `.fit` extension.
- Creates parent directories for the output path if needed.
- Returns both the written path and the parsed `CourseData` (callers use the latter for summary info like distance).

## Data Shapes / Interfaces

Module public API — these exact names are imported by the regression tests in `tests/` and by `device/manager.py` and `gui/server.py`:

`converter/fit_encoder.py`:
```
GARMIN_EPOCH: int = 631065600
calculate_crc(data: bytes, initial_crc: int = 0) -> int
deg_to_semicircles(deg: float) -> int
class Sport(IntEnum)              # table above
class CoursePointType(IntEnum)    # table above

@dataclass TrackPoint:
    lat: float
    lon: float
    elevation: Optional[float] = None
    distance: float = 0.0                       # cumulative meters from the first point
    timestamp: Optional[datetime] = None

@dataclass CoursePointData:
    lat: float
    lon: float
    distance: float                             # cumulative meters along the route
    point_type: CoursePointType = CoursePointType.GENERIC
    name: str = ""
    timestamp: Optional[datetime] = None

@dataclass CourseData:
    name: str
    sport: Sport = Sport.CYCLING
    points: List[TrackPoint] = []
    course_points: List[CoursePointData] = []
    total_distance: float = 0.0                 # meters
    total_ascent: float = 0.0                   # meters
    total_descent: float = 0.0                  # meters
    created_at: Optional[datetime] = None

class FitCourseEncoder:
    __init__(self, course: CourseData)
    encode(self) -> bytes                       # the complete .FIT file bytes
```

`converter/gpx_parser.py`:
```
haversine_distance(lat1, lon1, lat2, lon2) -> float          # meters
parse_iso_datetime(dt_str: str) -> Optional[datetime]
match_course_point_type(name: str, sym: str = "", desc: str = "") -> CoursePointType
parse_gpx_string(xml_content: str, course_name: Optional[str] = None, sport: Sport = Sport.CYCLING) -> CourseData
parse_gpx_file(file_path: str | Path, course_name: Optional[str] = None, sport: Sport = Sport.CYCLING) -> CourseData
```

`converter/gpx_to_fit.py`:
```
convert_gpx_to_fit(gpx_path, output_fit_path=None, course_name=None, sport=Sport.CYCLING) -> tuple[Path, CourseData]
```

`converter/__init__.py` re-exports: `FitCourseEncoder, CourseData, TrackPoint, CoursePointData, Sport, CoursePointType, parse_gpx_file, parse_gpx_string, convert_gpx_to_fit`.

## Non-Goals
- No FIT → GPX conversion (one-directional GPX→FIT only for writing; FIT reading for the map-preview feature uses the third-party `fitparse` library instead, see [course-management-api](course-management-api.md)).
- No elevation enrichment (DEM or otherwise) — cut from v1. GPX-supplied elevation is used as-is; a future DEM-enrichment feature would need its own spec (data source, offline vs. API, caching) rather than a silent flag.
- No multi-lap or multi-segment course support — always exactly one lap.
- No power/heart-rate/cadence fields — course files carry only position, altitude, distance, timing, and course-point cues.
