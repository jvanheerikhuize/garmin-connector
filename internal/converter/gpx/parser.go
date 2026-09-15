package gpx

import (
	"encoding/xml"
	"math"
	"strings"
	"time"

	"garmin-connector/internal/converter/types"
)

type GPX struct {
	Trk []Trk `xml:"trk"`
	Rte []Rte `xml:"rte"`
	Wpt []Wpt `xml:"wpt"`
}

type Trk struct {
	Name   string   `xml:"name"`
	TrkSeg []TrkSeg `xml:"trkseg"`
}

type TrkSeg struct {
	TrkPt []Pt `xml:"trkpt"`
}

type Rte struct {
	Name  string `xml:"name"`
	RtePt []Pt   `xml:"rtept"`
}

type Pt struct {
	Lat  float64 `xml:"lat,attr"`
	Lon  float64 `xml:"lon,attr"`
	Ele  *float64 `xml:"ele"`
	Time *string  `xml:"time"`
}

type Wpt struct {
	Lat  float64 `xml:"lat,attr"`
	Lon  float64 `xml:"lon,attr"`
	Name string  `xml:"name"`
	Sym  string  `xml:"sym"`
}

func HaversineDistance(lat1, lon1, lat2, lon2 float64) float64 {
	const r = 6371000.0 // meters
	rad := math.Pi / 180.0
	dlat := (lat2 - lat1) * rad
	dlon := (lon2 - lon1) * rad
	a := math.Sin(dlat/2)*math.Sin(dlat/2) +
		math.Cos(lat1*rad)*math.Cos(lat2*rad)*math.Sin(dlon/2)*math.Sin(dlon/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return r * c
}

func parseTime(t *string) *time.Time {
	if t == nil {
		return nil
	}
	parsed, err := time.Parse(time.RFC3339, *t)
	if err != nil {
		return nil
	}
	return &parsed
}

func truncateName(name string, length int) string {
	name = strings.TrimSpace(name)
	if len(name) > length {
		// Just truncate bytes for now, avoiding breaking UTF-8 if possible, but keeping it simple
		runes := []rune(name)
		res := ""
		for _, r := range runes {
			if len(res)+len(string(r)) > length {
				break
			}
			res += string(r)
		}
		return res
	}
	return name
}

func ParseGPX(content []byte, defaultName string, sport types.Sport) (*types.CourseData, error) {
	var gpx GPX
	if err := xml.Unmarshal(content, &gpx); err != nil {
		return nil, err
	}

	var rawPts []Pt
	courseName := defaultName

	if len(gpx.Trk) > 0 {
		if gpx.Trk[0].Name != "" {
			courseName = gpx.Trk[0].Name
		}
		for _, seg := range gpx.Trk[0].TrkSeg {
			rawPts = append(rawPts, seg.TrkPt...)
		}
	} else if len(gpx.Rte) > 0 {
		if gpx.Rte[0].Name != "" {
			courseName = gpx.Rte[0].Name
		}
		rawPts = append(rawPts, gpx.Rte[0].RtePt...)
	} else {
		// No track or route
		rawPts = []Pt{}
	}

	if courseName == "" {
		courseName = "Course"
	}
	courseName = truncateName(courseName, 15)

	course := &types.CourseData{
		Name:      courseName,
		Sport:     sport,
		CreatedAt: time.Now(),
	}

	var lastPt *Pt
	var currentDist float64

	for _, pt := range rawPts {
		if lastPt != nil {
			dist := HaversineDistance(lastPt.Lat, lastPt.Lon, pt.Lat, pt.Lon)
			currentDist += dist
			if pt.Ele != nil && lastPt.Ele != nil {
				delta := *pt.Ele - *lastPt.Ele
				if math.Abs(delta) > 0.3 {
					if delta > 0 {
						course.TotalAscent += delta
					} else {
						course.TotalDescent -= delta
					}
				}
			}
		}
		
		tp := types.TrackPoint{
			Lat:       pt.Lat,
			Lon:       pt.Lon,
			Elevation: pt.Ele,
			Distance:  currentDist,
			Timestamp: parseTime(pt.Time),
		}
		course.Points = append(course.Points, tp)
		lastPt = &pt // shallow copy is fine for our use
	}
	course.TotalDistance = currentDist

	// process waypoints
	for _, w := range gpx.Wpt {
		// find nearest track point
		var minDt float64 = math.MaxFloat64
		var nearestDist float64
		for _, tp := range course.Points {
			dt := HaversineDistance(w.Lat, w.Lon, tp.Lat, tp.Lon)
			if dt < minDt {
				minDt = dt
				nearestDist = tp.Distance
			}
		}

		cp := types.CoursePointData{
			Lat:       w.Lat,
			Lon:       w.Lon,
			Distance:  nearestDist,
			PointType: 0, // Generic
			Name:      truncateName(w.Name, 15),
		}
		course.CoursePoints = append(course.CoursePoints, cp)
	}

	return course, nil
}
