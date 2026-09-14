---
id: gpx-fit-conversion
title: GPX <-> FIT Conversion
tier: feature
status: implemented
owners: [jerry]
depends_on: []
last_updated: 2026-09-14
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

### Binary format
- Produces a valid Garmin `.FIT` file: 14-byte header (size=14, protocol version `0x20`, profile version `2100`, data size, `.FIT` magic, header CRC) + concatenated definition/data message pairs + trailing 2-byte file CRC (CRC-16 per the FIT spec's nibble-table algorithm, computed over header+payload).
- Garmin epoch offset is `631065600` (1989-12-31T00:00:00Z as a Unix timestamp); all FIT timestamps are seconds since this epoch, floored at 0.
- Lat/lon are encoded as 32-bit semicircles: `degrees * (2^31 / 180)`.
- Altitude is encoded per FIT convention: `(elevation_m + 500) * 5`, clamped to `[0, 65534]`; missing elevation encodes as `0xFFFF` (invalid/unknown sentinel).
- Distance fields are centimeters (`meters * 100`); total ascent/descent are clamped to `uint16` range `[0, 65535]`.

### Messages emitted, in order
1. **File ID** (`local 0`): type=6 (course file), manufacturer=1 (garmin), product=0, serial=0, time_created=now.
2. **Course** (`local 1`): sport enum, name (UTF-8, ≤15 bytes + null terminator).
3. **Lap** (`local 2`): start/end lat-lon (first/last track point), total elapsed/timer time, total distance, ascent, descent.
   - If no track points exist, start/end default to `(0, 0)`.
   - Duration is *estimated* from distance and an assumed average speed when timestamps aren't otherwise used here: **5.5 m/s (~20 km/h) for cycling, 1.25 m/s (~4.5 km/h) for every other sport** (including hiking/running/walking — this is a known simplification, not per-sport-accurate).
4. **Record** definition + one Record data message per track point (only emitted if `course.points` is non-empty): per-point timestamp is the point's own GPX timestamp if present, else estimated the same way as the lap duration (distance / avg_speed).
5. **Course Point** definition + one data message per course point (only emitted if `course.course_points` is non-empty): 16-byte name field (padded, null-terminated), timestamp from the course point if present else the file's creation time.

### `Sport` enum values (must match Garmin FIT profile)
`GENERIC=0, RUNNING=1, CYCLING=2, TRANSITION=3, FITNESS_EQUIPMENT=4, SWIMMING=5, BASKETBALL=6, SOCCER=7, TENNIS=8, HIKING=11, WALKING=11` (hiking and walking intentionally share value 11).

### `CoursePointType` enum
26 values matching the Garmin FIT `course_point` profile (`GENERIC=0` through `SEGMENT_END=25`) — see source for the full table; must stay byte-for-byte aligned with Garmin's profile since the watch firmware interprets these as fixed enums.

## `gpx_to_fit.py` requirements
- `convert_gpx_to_fit(gpx_path, output_fit_path=None, course_name=None, sport=CYCLING) -> (Path, CourseData)`.
- Raises `FileNotFoundError` if `gpx_path` doesn't exist.
- Default output path: same directory/stem as input with `.fit` extension.
- Creates parent directories for the output path if needed.
- Returns both the written path and the parsed `CourseData` (callers use the latter for summary info like distance).

## Non-Goals
- No FIT → GPX conversion (one-directional GPX→FIT only for writing; FIT reading for the map-preview feature uses the third-party `fitparse` library instead, see [course-management-api](course-management-api.md)).
- No elevation enrichment (DEM or otherwise) — cut from v1. GPX-supplied elevation is used as-is; a future DEM-enrichment feature would need its own spec (data source, offline vs. API, caching) rather than a silent flag.
- No multi-lap or multi-segment course support — always exactly one lap.
- No power/heart-rate/cadence fields — course files carry only position, altitude, distance, timing, and course-point cues.
