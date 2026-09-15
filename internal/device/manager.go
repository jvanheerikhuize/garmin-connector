package device

import (
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"garmin-connector/internal/converter"
	"garmin-connector/internal/converter/types"
)

type CourseFileSummary struct {
	Filename   string    `json:"filename"`
	FullPath   string    `json:"full_path"`
	SizeBytes  int64     `json:"size_bytes"`
	ModifiedAt time.Time `json:"modified_at"` // UTC
	Location   string    `json:"location"`    // "COURSES" | "NEWFILES (Pending Sync)"
}

func SideloadRoute(device *GarminDeviceInfo, source []byte, ext string, sport types.Sport, courseName string) (string, error) {
	if device == nil {
		return "", errors.New("no Garmin device connected")
	}

	ext = strings.ToLower(ext)
	var finalBytes []byte

	if ext == ".gpx" {
		fitBytes, _, err := converter.ConvertGPXToFIT(source, courseName, sport)
		if err != nil {
			return "", err
		}
		finalBytes = fitBytes
	} else if ext == ".fit" {
		finalBytes = source
	} else {
		return "", fmt.Errorf("unsupported format: %s", ext)
	}

	targetDir := device.NewFilesDir
	if targetDir == "" {
		targetDir = filepath.Join(device.GarminDir, "NEWFILES")
	}
	
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		return "", err
	}

	// Always write as .fit if we converted
	outExt := ext
	if ext == ".gpx" {
		outExt = ".fit"
	}
	if courseName == "" {
		courseName = "Course"
	}
	destPath := filepath.Join(targetDir, courseName+outExt)
	
	if err := os.WriteFile(destPath, finalBytes, 0644); err != nil {
		return "", err
	}
	
	return destPath, nil
}

func listFilesInDir(dirPath string, locationLabel string) ([]CourseFileSummary, error) {
	var list []CourseFileSummary
	entries, err := ioutil.ReadDir(dirPath)
	if err != nil {
		if os.IsNotExist(err) {
			return list, nil
		}
		return nil, err
	}
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		ext := strings.ToLower(filepath.Ext(e.Name()))
		if ext == ".fit" || ext == ".gpx" {
			list = append(list, CourseFileSummary{
				Filename:   e.Name(),
				FullPath:   filepath.Join(dirPath, e.Name()),
				SizeBytes:  e.Size(),
				ModifiedAt: e.ModTime().UTC(),
				Location:   locationLabel,
			})
		}
	}
	sort.Slice(list, func(i, j int) bool {
		return list[i].Filename < list[j].Filename
	})
	return list, nil
}

func ListCourses(device *GarminDeviceInfo) ([]CourseFileSummary, error) {
	if device == nil {
		return nil, errors.New("no Garmin device connected")
	}

	var all []CourseFileSummary

	coursesDir := device.CoursesDir
	if coursesDir == "" {
		coursesDir = filepath.Join(device.GarminDir, "COURSES")
	}
	cList, err := listFilesInDir(coursesDir, "COURSES")
	if err == nil {
		all = append(all, cList...)
	}

	newFilesDir := device.NewFilesDir
	if newFilesDir == "" {
		newFilesDir = filepath.Join(device.GarminDir, "NEWFILES")
	}
	nList, err := listFilesInDir(newFilesDir, "NEWFILES (Pending Sync)")
	if err == nil {
		all = append(all, nList...)
	}

	return all, nil
}

func DeleteCourse(device *GarminDeviceInfo, filename string) (bool, error) {
	if device == nil {
		return false, errors.New("no Garmin device connected")
	}

	coursesDir := device.CoursesDir
	if coursesDir == "" {
		coursesDir = filepath.Join(device.GarminDir, "COURSES")
	}
	newFilesDir := device.NewFilesDir
	if newFilesDir == "" {
		newFilesDir = filepath.Join(device.GarminDir, "NEWFILES")
	}

	cPath := filepath.Join(coursesDir, filename)
	nPath := filepath.Join(newFilesDir, filename)

	deleted := false
	if err := os.Remove(cPath); err == nil {
		deleted = true
	}
	if err := os.Remove(nPath); err == nil {
		deleted = true
	}
	
	return deleted, nil
}
