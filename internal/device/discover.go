package device

import (
	"os"
	"path/filepath"
	"strings"
)

// Info represents the metadata extracted from a connected Garmin device.
type Info struct {
	Model           string `json:"model"`
	ID              string `json:"id"`
	SoftwareVersion string `json:"software_version"`
	PartNumber      string `json:"part_number"`
	MountPath       string `json:"mount_path"`
}

// Discover returns the first Garmin device found across Linux mount points, or nil if none are connected.
func Discover() (*Info, error) {
	return discoverWithBases("/run/user", "/media", "/mnt")
}

// discoverWithBases scans for connected Garmin devices under specified base directories.
func discoverWithBases(runUserBase, mediaBase, mntBase string) (*Info, error) {
	candidatePaths := collectCandidatePaths(runUserBase, mediaBase, mntBase)

	for _, candidate := range candidatePaths {
		garminDir := findGarminDirectory(candidate)
		if garminDir == "" {
			continue
		}

		info := extractDeviceInfo(candidate, garminDir)
		if info != nil {
			return info, nil
		}
	}

	return nil, nil
}

// collectCandidatePaths gathers candidate mount paths from:
// 1. <runUserBase>/*/gvfs/*
// 2. <mediaBase>/*/* (and direct <mediaBase>/*)
// 3. <mntBase>/*
func collectCandidatePaths(runUserBase, mediaBase, mntBase string) []string {
	var candidates []string

	// 1. /run/user/*/gvfs/*
	if userEntries, err := os.ReadDir(runUserBase); err == nil {
		for _, userEntry := range userEntries {
			if !userEntry.IsDir() {
				continue
			}
			gvfsDir := filepath.Join(runUserBase, userEntry.Name(), "gvfs")
			if gvfsEntries, err := os.ReadDir(gvfsDir); err == nil {
				for _, gvfsEntry := range gvfsEntries {
					candidates = append(candidates, filepath.Join(gvfsDir, gvfsEntry.Name()))
				}
			}
		}
	}

	// 2. /media/*/* and /media/*
	if mediaEntries, err := os.ReadDir(mediaBase); err == nil {
		for _, mediaEntry := range mediaEntries {
			if !mediaEntry.IsDir() {
				continue
			}
			userMediaDir := filepath.Join(mediaBase, mediaEntry.Name())
			subEntries, err := os.ReadDir(userMediaDir)
			if err == nil {
				for _, subEntry := range subEntries {
					if subEntry.IsDir() {
						candidates = append(candidates, filepath.Join(userMediaDir, subEntry.Name()))
					}
				}
			}
			// In case mounts are located directly under /media/<mount>
			candidates = append(candidates, userMediaDir)
		}
	}

	// 3. /mnt/*
	if mntEntries, err := os.ReadDir(mntBase); err == nil {
		for _, mntEntry := range mntEntries {
			if mntEntry.IsDir() {
				candidates = append(candidates, filepath.Join(mntBase, mntEntry.Name()))
			}
		}
	}

	return candidates
}

// findGarminDirectory searches candidatePath for a "GARMIN" directory (case-insensitive)
// up to 2 directory levels deep (FCT-3).
func findGarminDirectory(candidatePath string) string {
	// Check if candidatePath itself is named GARMIN
	if strings.EqualFold(filepath.Base(candidatePath), "garmin") {
		fi, err := os.Stat(candidatePath)
		if err == nil && fi.IsDir() {
			return candidatePath
		}
	}

	entries, err := os.ReadDir(candidatePath)
	if err != nil {
		// Gracefully skip paths with permission errors or missing directories
		return ""
	}

	// Level 0: Direct child of candidatePath
	var level1Dirs []string
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		if strings.EqualFold(entry.Name(), "garmin") {
			return filepath.Join(candidatePath, entry.Name())
		}
		level1Dirs = append(level1Dirs, filepath.Join(candidatePath, entry.Name()))
	}

	// Level 1: One subdirectory deep (e.g., candidatePath/Internal Storage/GARMIN)
	var level2Dirs []string
	for _, dir1 := range level1Dirs {
		subEntries, err := os.ReadDir(dir1)
		if err != nil {
			continue
		}
		for _, subEntry := range subEntries {
			if !subEntry.IsDir() {
				continue
			}
			if strings.EqualFold(subEntry.Name(), "garmin") {
				return filepath.Join(dir1, subEntry.Name())
			}
			level2Dirs = append(level2Dirs, filepath.Join(dir1, subEntry.Name()))
		}
	}

	// Level 2: Two subdirectories deep
	for _, dir2 := range level2Dirs {
		subEntries, err := os.ReadDir(dir2)
		if err != nil {
			continue
		}
		for _, subEntry := range subEntries {
			if !subEntry.IsDir() {
				continue
			}
			if strings.EqualFold(subEntry.Name(), "garmin") {
				return filepath.Join(dir2, subEntry.Name())
			}
		}
	}

	return ""
}

// extractDeviceInfo reads GarminDevice.xml within garminDir and parses it.
// If the file is missing, unreadable, or invalid, it returns a fallback Info struct.
func extractDeviceInfo(candidatePath, garminDir string) *Info {
	entries, err := os.ReadDir(garminDir)
	if err != nil {
		return &Info{
			Model:     "Generic Garmin",
			MountPath: candidatePath,
		}
	}

	var xmlFilePath string
	for _, entry := range entries {
		if strings.EqualFold(entry.Name(), "garmindevice.xml") {
			xmlFilePath = filepath.Join(garminDir, entry.Name())
			break
		}
	}

	if xmlFilePath == "" {
		return &Info{
			Model:     "Generic Garmin",
			MountPath: candidatePath,
		}
	}

	data, err := os.ReadFile(xmlFilePath)
	if err != nil {
		return &Info{
			Model:     "Generic Garmin",
			MountPath: candidatePath,
		}
	}

	info, _ := parseGarminDeviceXML(data)
	info.MountPath = candidatePath
	return info
}
