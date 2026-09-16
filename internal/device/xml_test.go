package device

import (
	"testing"
)

func TestParseGarminDeviceXML(t *testing.T) {
	tests := []struct {
		name         string
		xmlData      string
		expectedInfo *Info
	}{
		{
			name: "Standard GarminDevice.xml with default namespace",
			xmlData: `<?xml version="1.0" encoding="UTF-8"?>
<Device xmlns="http://www.garmin.com/xmlschemas/GarminDevice/v2">
    <Model>
        <PartNumber>010-02430-01</PartNumber>
        <SoftwareVersion>14.20</SoftwareVersion>
        <Description>Garmin Venu X1</Description>
    </Model>
    <Id>3123456789</Id>
</Device>`,
			expectedInfo: &Info{
				Model:           "Garmin Venu X1",
				ID:              "3123456789",
				SoftwareVersion: "14.20",
				PartNumber:      "010-02430-01",
			},
		},
		{
			name: "XML with prefixed namespaces",
			xmlData: `<?xml version="1.0" encoding="UTF-8"?>
<ns:Device xmlns:ns="http://www.garmin.com/xmlschemas/GarminDevice/v2">
    <ns:Model>
        <ns:PartNumber>010-99999-00</ns:PartNumber>
        <ns:SoftwareVersion>3.50</ns:SoftwareVersion>
        <ns:Description>Forerunner 265</ns:Description>
    </ns:Model>
    <ns:Id>9876543210</ns:Id>
</ns:Device>`,
			expectedInfo: &Info{
				Model:           "Forerunner 265",
				ID:              "9876543210",
				SoftwareVersion: "3.50",
				PartNumber:      "010-99999-00",
			},
		},
		{
			name: "Case variations in tags",
			xmlData: `
<device>
    <model>
        <partnumber>PART-123</partnumber>
        <softwareversion>1.0</softwareversion>
        <description>Fenix 7</description>
    </model>
    <id>11223344</id>
</device>`,
			expectedInfo: &Info{
				Model:           "Fenix 7",
				ID:              "11223344",
				SoftwareVersion: "1.0",
				PartNumber:      "PART-123",
			},
		},
		{
			name:    "Empty XML data falls back gracefully",
			xmlData: `   `,
			expectedInfo: &Info{
				Model: "Generic Garmin",
			},
		},
		{
			name:    "Malformed XML falls back gracefully",
			xmlData: `<Device><Model><Description>Incomplete`,
			expectedInfo: &Info{
				Model: "Generic Garmin",
			},
		},
		{
			name: "Missing Description falls back to Generic Garmin",
			xmlData: `<Device>
    <Model>
        <PartNumber>010-00000-00</PartNumber>
        <SoftwareVersion>2.0</SoftwareVersion>
    </Model>
    <Id>55555</Id>
</Device>`,
			expectedInfo: &Info{
				Model:           "Generic Garmin",
				ID:              "55555",
				SoftwareVersion: "2.0",
				PartNumber:      "010-00000-00",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			info, err := parseGarminDeviceXML([]byte(tt.xmlData))
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if info.Model != tt.expectedInfo.Model {
				t.Errorf("Model = %q, want %q", info.Model, tt.expectedInfo.Model)
			}
			if info.ID != tt.expectedInfo.ID {
				t.Errorf("ID = %q, want %q", info.ID, tt.expectedInfo.ID)
			}
			if info.SoftwareVersion != tt.expectedInfo.SoftwareVersion {
				t.Errorf("SoftwareVersion = %q, want %q", info.SoftwareVersion, tt.expectedInfo.SoftwareVersion)
			}
			if info.PartNumber != tt.expectedInfo.PartNumber {
				t.Errorf("PartNumber = %q, want %q", info.PartNumber, tt.expectedInfo.PartNumber)
			}
		})
	}
}
