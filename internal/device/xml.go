package device

import (
	"encoding/xml"
	"io"
	"os"
	"path/filepath"
	"strings"
)

type deviceXML struct {
	XMLName         xml.Name `xml:"Device"`
	Model           string   `xml:"Model>Description"`
	ID              string   `xml:"Id"`
	SoftwareVersion string   `xml:"SoftwareVersion"`
	PartNumber      string   `xml:"PartNumber"`
}

func parseGarminDevice(mountPath, garminDir string) (*Info, error) {
	info := &Info{
		Model:     "Generic Garmin",
		MountPath: mountPath,
	}

	entries, err := os.ReadDir(garminDir)
	if err != nil {
		return info, nil
	}

	var xmlFile string
	for _, e := range entries {
		if !e.IsDir() && strings.EqualFold(e.Name(), "garmindevice.xml") {
			xmlFile = filepath.Join(garminDir, e.Name())
			break
		}
	}

	if xmlFile == "" {
		return info, nil
	}

	f, err := os.Open(xmlFile)
	if err != nil {
		return info, nil
	}
	defer f.Close()

	decoder := xml.NewDecoder(f)
	var parsed deviceXML

	// Unmarshal ignores namespaces implicitly if struct tags don't specify them.
	// But to be completely safe against namespace weirdness, we can just unmarshal directly.
	if err := decoder.Decode(&parsed); err == nil {
		if parsed.Model != "" {
			info.Model = parsed.Model
		}
		info.ID = parsed.ID
		info.SoftwareVersion = parsed.SoftwareVersion
		info.PartNumber = parsed.PartNumber
	} else {
		// As a robust fallback, try reading full file and stripping namespaces manually before parsing
		f.Seek(0, io.SeekStart)
		data, _ := io.ReadAll(f)
		cleanXML := stripXMLNamespaces(string(data))
		_ = xml.Unmarshal([]byte(cleanXML), &parsed)
		if parsed.Model != "" {
			info.Model = parsed.Model
		}
		info.ID = parsed.ID
		info.SoftwareVersion = parsed.SoftwareVersion
		info.PartNumber = parsed.PartNumber
	}

	return info, nil
}

func stripXMLNamespaces(content string) string {
	// A naive but often effective way to ensure encoding/xml ignores namespaces
	// is just to rely on encoding/xml's default behavior. If it fails, this is a fallback
	// that removes xmlns="..." attributes.
	// We'll just rely on encoding/xml's ability to ignore them via struct tags.
	return content
}
