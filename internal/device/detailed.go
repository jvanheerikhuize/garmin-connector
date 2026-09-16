package device

import (
	"os"
	"path/filepath"
	"strings"
)

type AppInfo struct {
	Name     string `json:"name"`
	Type     string `json:"type"`
	Version  string `json:"version"`
	AppID    string `json:"app_id"`
	FileName string `json:"file_name"`
}

type ConnectIQInfo struct {
	VMVersion     string    `json:"vm_version"`
	MaxApps       int       `json:"max_apps"`
	AppSpaceBytes int64     `json:"app_space_bytes"`
	Apps          []AppInfo `json:"apps"`
}

type ComponentVersions struct {
	GPS       string `json:"gps,omitempty"`
	Wireless  string `json:"wireless,omitempty"`
	SensorHub string `json:"sensor_hub,omitempty"`
}

type DetailedInfo struct {
	Info
	Storage    StorageInfo       `json:"storage"`
	ConnectIQ  ConnectIQInfo     `json:"connect_iq"`
	Components ComponentVersions `json:"components"`
}

// GetDetailedInfo gathers comprehensive device, storage, and app metrics.
func GetDetailedInfo(dev *Info) (*DetailedInfo, error) {
	if dev == nil {
		return nil, nil
	}

	detailed := &DetailedInfo{
		Info:       *dev,
		Storage:    getStorageInfo(dev.MountPath),
		ConnectIQ:  ConnectIQInfo{Apps: []AppInfo{}},
		Components: ComponentVersions{},
	}

	garminDir := findGarminDirectory(dev.MountPath)
	if garminDir == "" {
		return detailed, nil
	}

	entries, err := os.ReadDir(garminDir)
	if err != nil {
		return detailed, nil
	}

	var xmlFilePath string
	for _, entry := range entries {
		if strings.EqualFold(entry.Name(), "garmindevice.xml") {
			xmlFilePath = filepath.Join(garminDir, entry.Name())
			break
		}
	}

	if xmlFilePath != "" {
		data, err := os.ReadFile(xmlFilePath)
		if err == nil {
			iqInfo, comps := parseDetailedXML(data)
			detailed.ConnectIQ = iqInfo
			detailed.Components = comps
		}
	}

	return detailed, nil
}
