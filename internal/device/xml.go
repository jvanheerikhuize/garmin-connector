package device

import (
	"bytes"
	"encoding/xml"
	"io"
	"strings"
)

// parseGarminDeviceXML parses the raw XML content of GarminDevice.xml and extracts
// identifying metadata fields. It strips/ignores XML namespaces and handles case variations.
// If the XML is empty, malformed, or fails to parse, it returns a partial Info struct with
// Model="Generic Garmin" instead of returning an error.
func parseGarminDeviceXML(data []byte) (*Info, error) {
	info := &Info{
		Model: "Generic Garmin",
	}

	if len(bytes.TrimSpace(data)) == 0 {
		return info, nil
	}

	decoder := xml.NewDecoder(bytes.NewReader(data))
	var elementStack []string

	for {
		token, err := decoder.Token()
		if err != nil {
			if err == io.EOF {
				break
			}
			// Malformed XML: fallback gracefully per ASM-4
			return &Info{
				Model: "Generic Garmin",
			}, nil
		}

		switch elem := token.(type) {
		case xml.StartElement:
			elementStack = append(elementStack, strings.ToLower(elem.Name.Local))
		case xml.EndElement:
			if len(elementStack) > 0 {
				elementStack = elementStack[:len(elementStack)-1]
			}
		case xml.CharData:
			text := strings.TrimSpace(string(elem))
			if text == "" {
				continue
			}

			// Check current hierarchy path
			depth := len(elementStack)
			if depth >= 2 && elementStack[depth-2] == "model" {
				switch elementStack[depth-1] {
				case "description":
					if info.Model == "Generic Garmin" {
						info.Model = text
					} else {
						info.Model += " " + text
					}
				case "softwareversion":
					info.SoftwareVersion += text
				case "partnumber":
					info.PartNumber += text
				}
			} else if depth >= 1 && elementStack[depth-1] == "id" {
				info.ID += text
			}
		}
	}

	info.Model = strings.TrimSpace(info.Model)
	if info.Model == "" {
		info.Model = "Generic Garmin"
	}
	info.ID = strings.TrimSpace(info.ID)
	info.SoftwareVersion = strings.TrimSpace(info.SoftwareVersion)
	info.PartNumber = strings.TrimSpace(info.PartNumber)

	return info, nil
}
