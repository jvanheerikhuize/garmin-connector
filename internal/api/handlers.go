package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"path/filepath"
	"strings"

	"github.com/tormoder/fit"

	"garmin-connector/internal/converter/gpx"
	"garmin-connector/internal/converter/types"
	"garmin-connector/internal/device"
)

func writeJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]interface{}{
		"success": false,
		"error":   msg,
	})
}

func handleGetCourses(w http.ResponseWriter, r *http.Request) {
	dev, _ := device.GetFirstDevice("")
	if dev == nil {
		writeJSON(w, 200, map[string]interface{}{
			"connected": false,
			"courses":   []interface{}{},
		})
		return
	}

	summaries, err := device.ListCourses(dev)
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}

	var courses []map[string]interface{}
	for _, s := range summaries {
		watchPath := strings.Replace(s.FullPath, dev.GarminDir, "/GARMIN", 1)
		courses = append(courses, map[string]interface{}{
			"filename":    s.Filename,
			"full_path":   s.FullPath,
			"watch_path":  watchPath,
			"size_bytes":  s.SizeBytes,
			"location":    s.Location,
			"modified_at": s.ModifiedAt.Format("2006-01-02T15:04:05Z"),
		})
	}

	writeJSON(w, 200, map[string]interface{}{
		"connected": true,
		"courses":   courses,
	})
}

func handleDeleteCourse(w http.ResponseWriter, r *http.Request) {
	dev, _ := device.GetFirstDevice("")
	if dev == nil {
		writeError(w, 503, "No Garmin device connected")
		return
	}

	filename := strings.TrimPrefix(r.URL.Path, "/api/courses/")
	if filename == "" {
		writeError(w, 400, "Missing filename")
		return
	}

	deleted, err := device.DeleteCourse(dev, filename)
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}

	if !deleted {
		writeError(w, 404, fmt.Sprintf("Course '%s' not found", filename))
		return
	}

	writeJSON(w, 200, map[string]interface{}{
		"success":  true,
		"filename": filename,
	})
}

type SideloadRequest struct {
	GpxContent string `json:"gpx_content"`
	CourseName string `json:"course_name"`
	Sport      string `json:"sport"`
}

func handleSideload(w http.ResponseWriter, r *http.Request) {
	dev, _ := device.GetFirstDevice("")
	if dev == nil {
		writeError(w, 503, "No Garmin device connected")
		return
	}

	var req SideloadRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, 400, "Invalid JSON")
		return
	}

	if req.GpxContent == "" {
		writeError(w, 400, "Missing gpx_content")
		return
	}

	sportType := types.SportGeneric
	switch strings.ToLower(req.Sport) {
	case "cycling":
		sportType = types.SportCycling
	case "hiking":
		sportType = types.SportHiking
	case "running":
		sportType = types.SportRunning
	}

	cName := req.CourseName
	if cName == "" {
		cName = "MVP_Course"
	}

	destPath, err := device.SideloadRoute(dev, []byte(req.GpxContent), ".gpx", sportType, cName)
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}

	writeJSON(w, 200, map[string]interface{}{
		"success":         true,
		"filename":        filepath.Base(destPath),
		"course_name":     cName,
		"distance_meters": 0, // distance can be calculated from converter, omitting for brevity
	})
}

func handleFetchCourse(w http.ResponseWriter, r *http.Request) {
	dev, _ := device.GetFirstDevice("")
	if dev == nil {
		writeError(w, 503, "No Garmin device connected")
		return
	}

	filename := strings.TrimPrefix(r.URL.Path, "/api/fetch-course/")
	if filename == "" {
		writeError(w, 400, "Missing filename")
		return
	}

	summaries, err := device.ListCourses(dev)
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}

	var fullPath string
	for _, s := range summaries {
		if s.Filename == filename {
			fullPath = s.FullPath
			break
		}
	}

	if fullPath == "" {
		writeError(w, 404, "Course not found on watch")
		return
	}

	content, err := device.FetchCourseBytes(dev, filename, fullPath)
	if err != nil {
		writeError(w, 500, err.Error())
		return
	}

	var points [][]float64
	ext := strings.ToLower(filepath.Ext(filename))

	if ext == ".fit" {
		fitFile, err := fit.Decode(bytes.NewReader(content))
		if err != nil {
			writeError(w, 500, "FIT decode error: "+err.Error())
			return
		}
		cf, err := fitFile.Course()
		if err == nil && cf != nil {
			for _, rec := range cf.Records {
				if rec.PositionLat.Invalid() || rec.PositionLong.Invalid() {
					continue
				}
				points = append(points, []float64{
					rec.PositionLat.Degrees(),
					rec.PositionLong.Degrees(),
				})
			}
		}
	} else if ext == ".gpx" {
		course, err := gpx.ParseGPX(content, "tmp", types.SportGeneric)
		if err == nil {
			for _, pt := range course.Points {
				points = append(points, []float64{pt.Lat, pt.Lon})
			}
		}
	}

	writeJSON(w, 200, map[string]interface{}{
		"success": true,
		"points":  points,
	})
}
