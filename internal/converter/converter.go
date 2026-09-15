package converter

import (
	"garmin-connector/internal/converter/fit"
	"garmin-connector/internal/converter/gpx"
	"garmin-connector/internal/converter/types"
)

func ConvertGPXToFIT(gpxBytes []byte, courseName string, sport types.Sport) ([]byte, *types.CourseData, error) {
	course, err := gpx.ParseGPX(gpxBytes, courseName, sport)
	if err != nil {
		return nil, nil, err
	}
	
	fitBytes, err := fit.EncodeFIT(course)
	if err != nil {
		return nil, nil, err
	}
	
	return fitBytes, course, nil
}
