package device

import (
	"encoding/xml"
	"strings"
)

type rawXMLDevice struct {
	XMLName    xml.Name `xml:"Device"`
	Extensions struct {
		IQAppExt struct {
			VmVersion string `xml:"VmVersion"`
			MaxApps   int    `xml:"MaxApps"`
			AppSpace  int64  `xml:"AppSpace"`
			Apps      struct {
				AppList []struct {
					AppName  string `xml:"AppName"`
					AppType  string `xml:"AppType"`
					Version  string `xml:"Version"`
					AppId    string `xml:"AppId"`
					FileName string `xml:"FileName"`
				} `xml:"App"`
			} `xml:"Apps"`
		} `xml:"IQAppExt"`
	} `xml:"Extensions"`
	MassStorageMode struct {
		UpdateFiles []struct {
			PartNumber string `xml:"PartNumber"`
			FileName   string `xml:"FileName"`
			Version    struct {
				Major string `xml:"Major"`
				Minor string `xml:"Minor"`
			} `xml:"Version"`
		} `xml:"UpdateFile"`
	} `xml:"MassStorageMode"`
}

// parseDetailedXML extracts Connect IQ apps and subsystem component versions from GarminDevice.xml.
func parseDetailedXML(data []byte) (ConnectIQInfo, ComponentVersions) {
	var raw rawXMLDevice
	if err := xml.Unmarshal(data, &raw); err != nil {
		return ConnectIQInfo{Apps: []AppInfo{}}, ComponentVersions{}
	}

	apps := make([]AppInfo, 0, len(raw.Extensions.IQAppExt.Apps.AppList))
	for _, a := range raw.Extensions.IQAppExt.Apps.AppList {
		apps = append(apps, AppInfo{
			Name:     a.AppName,
			Type:     a.AppType,
			Version:  a.Version,
			AppID:    a.AppId,
			FileName: a.FileName,
		})
	}

	iqInfo := ConnectIQInfo{
		VMVersion:     raw.Extensions.IQAppExt.VmVersion,
		MaxApps:       raw.Extensions.IQAppExt.MaxApps,
		AppSpaceBytes: raw.Extensions.IQAppExt.AppSpace,
		Apps:          apps,
	}

	var comps ComponentVersions
	for _, u := range raw.MassStorageMode.UpdateFiles {
		fn := strings.ToLower(u.FileName)
		ver := ""
		if u.Version.Major != "" || u.Version.Minor != "" {
			ver = u.Version.Major + "." + u.Version.Minor
		}

		if comps.GPS == "" && (strings.Contains(fn, "gup4603") || strings.Contains(fn, "gps")) {
			comps.GPS = ver
		} else if comps.Wireless == "" && (strings.Contains(fn, "gup3651") || strings.Contains(fn, "ble") || strings.Contains(fn, "ant")) {
			comps.Wireless = ver
		} else if comps.SensorHub == "" && (strings.Contains(fn, "gup4605") || strings.Contains(fn, "sensor")) {
			comps.SensorHub = ver
		}
	}

	return iqInfo, comps
}
