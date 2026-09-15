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

`internal/converter/` (packages `gpx`, `fit`, `types`)

## Purpose

Parse GPX route/track files into an internal Go struct representation (`types.CourseData`), and encode that representation into a Garmin-native binary `.FIT` course file. We will use a reliable Go library for FIT encoding/decoding (e.g., `github.com/tormoder/fit`) and stdlib `encoding/xml` for GPX parsing.

## `internal/converter/gpx` requirements

### Distance/elevation math
- `HaversineDistance(lat1, lon1, lat2, lon2 float64) float64`: standard great-circle formula, Earth radius `6371000.0` m.
- Elevation noise filter: a step is counted toward `TotalAscent`/`TotalDescent` only if the absolute elevation delta between consecutive points exceeds `0.3` m.

### GPX parsing (`ParseGPX(content []byte, courseName string, sport types.Sport) (*types.CourseData, error)`)
- Unmarshal GPX XML using Go `encoding/xml`.
- Course name resolution: explicit `courseName` → `<trk><name>` → `<name>` → literal `"Course"`. Final name is trimmed and truncated to **15 bytes** (Garmin field limit).
- Point source: prefer `<trkpt>` elements; if none exist, fall back to `<rtept>` elements. If neither, return error.
- Points are emitted in document order with cumulative haversine distance.
- Waypoints (`<wpt>`) become `CoursePointData`: matched to the *nearest* track point by straight-line distance; name truncated to 15 bytes; type inferred via `matchCoursePointType`.

## `internal/converter/fit` requirements

### Encoding rules
We use a standard Go library to generate the FIT payload. The encoder must produce the following messages in order:
1. **File ID**: type=Course, manufacturer=Garmin, time_created=now.
2. **Course**: sport, name.
3. **Lap**: start_time, start/end positions, total elapsed time, total distance (cm), total ascent/descent.
   - `est_duration_s = int(total_distance_m / avg_speed)` where avg_speed = 5.5 m/s for CYCLING, 1.25 m/s otherwise.
4. **Record (per track point)**: timestamp, lat/lon (semicircles), altitude (if known), distance (cm).
5. **Course Point (per cue)**: timestamp, lat/lon, distance, type, name (15 bytes).

### Conversions
- Semicircles: `int32(degrees * (math.MaxInt32 / 180.0))`

### `Sport` enum
```go
type Sport uint8
const (
    SportGeneric Sport = 0
    SportRunning Sport = 1
    SportCycling Sport = 2
    SportHiking  Sport = 11
)
```

## Data Shapes / Interfaces

`internal/converter/types/course.go`:
```go
type TrackPoint struct {
    Lat       float64
    Lon       float64
    Elevation *float64
    Distance  float64
    Timestamp *time.Time
}

type CoursePointData struct {
    Lat       float64
    Lon       float64
    Distance  float64
    PointType uint8
    Name      string
    Timestamp *time.Time
}

type CourseData struct {
    Name          string
    Sport         Sport
    Points        []TrackPoint
    CoursePoints  []CoursePointData
    TotalDistance float64
    TotalAscent   float64
    TotalDescent  float64
    CreatedAt     time.Time
}
```

`internal/converter/converter.go`:
```go
func ConvertGPXToFIT(gpxBytes []byte, courseName string, sport types.Sport) ([]byte, *types.CourseData, error)
```

## Non-Goals
- No elevation enrichment (DEM).
- No multi-lap support.
