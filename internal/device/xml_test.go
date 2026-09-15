package device

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseGarminDevice(t *testing.T) {
	tmpDir := t.TempDir()
	garminDir := filepath.Join(tmpDir, "GARMIN")
	os.Mkdir(garminDir, 0755)

	xmlContent := `<?xml version="1.0" encoding="UTF-8"?><Device xmlns="http://www.garmin.com/xml/schemas/Device/v2"><Model><PartNumber>010-02430-01</PartNumber><SoftwareVersion>1420</SoftwareVersion><Description>Garmin Venu X1</Description></Model><Id>3123456789</Id></Device>`
	os.WriteFile(filepath.Join(garminDir, "GarminDevice.xml"), []byte(xmlContent), 0644)

	info, err := parseGarminDevice(tmpDir, garminDir)
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	if info.Model != "Garmin Venu X1" {
		t.Errorf("Expected model 'Garmin Venu X1', got '%s'", info.Model)
	}
	if info.ID != "3123456789" {
		t.Errorf("Expected ID '3123456789', got '%s'", info.ID)
	}
}

func TestParseGarminDevice_MissingFile(t *testing.T) {
	tmpDir := t.TempDir()
	garminDir := filepath.Join(tmpDir, "GARMIN")
	os.Mkdir(garminDir, 0755)

	info, err := parseGarminDevice(tmpDir, garminDir)
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}

	if info.Model != "Generic Garmin" {
		t.Errorf("Expected generic fallback, got '%s'", info.Model)
	}
}
