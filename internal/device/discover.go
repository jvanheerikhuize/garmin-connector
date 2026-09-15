package device

import (
	"os"
	"path/filepath"
	"strings"
)

type Info struct {
	Model           string `json:"model"`
	ID              string `json:"id"`
	SoftwareVersion string `json:"software_version"`
	PartNumber      string `json:"part_number"`
	MountPath       string `json:"mount_path"`
}

func Discover() (*Info, error) {
	var candidates []string

	userDirs, _ := filepath.Glob("/run/user/*")
	for _, ud := range userDirs {
		gvfsDirs, _ := filepath.Glob(filepath.Join(ud, "gvfs", "*"))
		candidates = append(candidates, gvfsDirs...)
	}

	mediaDirs, _ := filepath.Glob("/media/*/*")
	candidates = append(candidates, mediaDirs...)

	mntDirs, _ := filepath.Glob("/mnt/*")
	candidates = append(candidates, mntDirs...)

	for _, cand := range candidates {
		entries, err := os.ReadDir(cand)
		if err != nil {
			continue
		}

		var garminDir string
		for _, e := range entries {
			if e.IsDir() && strings.EqualFold(e.Name(), "garmin") {
				garminDir = filepath.Join(cand, e.Name())
				break
			}
		}

		if garminDir != "" {
			return parseGarminDevice(cand, garminDir)
		}
	}

	return nil, nil
}
