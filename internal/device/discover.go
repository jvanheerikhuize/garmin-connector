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
		// Sometimes the GARMIN folder is an immediate child of the mount,
		// and sometimes it is behind a logical volume like "Internal Storage".
		// We will search up to 2 levels deep for a folder named GARMIN.
		
		var garminDir string
		filepath.WalkDir(cand, func(path string, d os.DirEntry, err error) error {
			if err != nil {
				return filepath.SkipDir // skip permission errors
			}
			
			// If we are deeper than 2 levels from candidate, don't descend further
			rel, _ := filepath.Rel(cand, path)
			depth := len(strings.Split(filepath.ToSlash(rel), "/"))
			if depth > 2 {
				return filepath.SkipDir
			}
			
			if d.IsDir() && strings.EqualFold(d.Name(), "garmin") {
				garminDir = path
				return filepath.SkipAll // found it, stop walking
			}
			return nil
		})

		if garminDir != "" {
			return parseGarminDevice(cand, garminDir)
		}
	}

	return nil, nil
}
