package types

import "time"

type Sport uint8
const (
    SportGeneric Sport = 0
    SportRunning Sport = 1
    SportCycling Sport = 2
    SportHiking  Sport = 11
)

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
