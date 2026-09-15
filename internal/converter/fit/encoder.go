package fit

import (
	"bytes"
	"encoding/binary"
	"math"

	"github.com/tormoder/fit"
	"garmin-connector/internal/converter/types"
)

func degreesToSemicircles(deg float64) int32 {
	return int32(deg * (float64(math.MaxInt32) / 180.0))
}

func EncodeFIT(course *types.CourseData) ([]byte, error) {
	header := fit.NewHeader(fit.V20, true)
	fitFile, err := fit.NewFile(fit.FileTypeCourse, header)
	if err != nil {
		return nil, err
	}

	// 1. FileId
	fitFile.FileId.Manufacturer = fit.ManufacturerGarmin
	fitFile.FileId.TimeCreated = course.CreatedAt

	// 2. Course
	courseFile, err := fitFile.Course()
	if err != nil {
		return nil, err
	}

	courseMsg := fit.CourseMsg{
		Name:  course.Name,
		Sport: fit.Sport(course.Sport),
	}
	courseFile.Course = &courseMsg

	// 3. Lap
	var estDuration uint32
	speed := 1.25
	if course.Sport == types.SportCycling {
		speed = 5.5
	}
	estDuration = uint32(course.TotalDistance / speed)

	lap := fit.LapMsg{
		TotalElapsedTime: estDuration * 1000,
		TotalDistance:    uint32(course.TotalDistance * 100), // cm
		TotalAscent:      uint16(course.TotalAscent), // this expects meters
		TotalDescent:     uint16(course.TotalDescent),
	}
	
	if len(course.Points) > 0 {
		lap.StartTime = course.CreatedAt // simplified
		lap.StartPositionLat = fit.NewLatitudeDegrees(course.Points[0].Lat)
		lap.StartPositionLong = fit.NewLongitudeDegrees(course.Points[0].Lon)
		lap.EndPositionLat = fit.NewLatitudeDegrees(course.Points[len(course.Points)-1].Lat)
		lap.EndPositionLong = fit.NewLongitudeDegrees(course.Points[len(course.Points)-1].Lon)
	}
	courseFile.Laps = append(courseFile.Laps, &lap)

	// 4. Records
	for _, pt := range course.Points {
		record := fit.RecordMsg{
			PositionLat:  fit.NewLatitudeDegrees(pt.Lat),
			PositionLong: fit.NewLongitudeDegrees(pt.Lon),
			Distance:     uint32(pt.Distance * 100),
		}
		if pt.Elevation != nil {
			record.Altitude = uint16(*pt.Elevation*5 + 500)
		}
		if pt.Timestamp != nil {
			record.Timestamp = *pt.Timestamp
		} else {
			record.Timestamp = course.CreatedAt
		}
		courseFile.Records = append(courseFile.Records, &record)
	}

	// 5. Course Points
	for _, cp := range course.CoursePoints {
		cpm := fit.CoursePointMsg{
			PositionLat:  fit.NewLatitudeDegrees(cp.Lat),
			PositionLong: fit.NewLongitudeDegrees(cp.Lon),
			Distance:     uint32(cp.Distance * 100),
			Type:         fit.CoursePoint(cp.PointType),
			Name:         cp.Name,
		}
		if cp.Timestamp != nil {
			cpm.Timestamp = *cp.Timestamp
		}
		courseFile.CoursePoints = append(courseFile.CoursePoints, &cpm)
	}

	var buf bytes.Buffer
	if err := fit.Encode(&buf, fitFile, binary.LittleEndian); err != nil {
		return nil, err
	}

	return buf.Bytes(), nil
}
