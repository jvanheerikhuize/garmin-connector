package device

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseDetailedXML(t *testing.T) {
	xmlData := `<?xml version="1.0" encoding="UTF-8"?>
<Device xmlns="http://www.garmin.com/xmlschemas/GarminDevice/v2">
    <Model>
        <Description>Venu X1</Description>
    </Model>
    <Id>3617019779</Id>
    <MassStorageMode>
        <UpdateFile>
            <PartNumber>006-B4603-00</PartNumber>
            <Version><Major>11</Major><Minor>02</Minor></Version>
            <FileName>gup4603.gcd</FileName>
        </UpdateFile>
        <UpdateFile>
            <PartNumber>006-B3651-10</PartNumber>
            <Version><Major>29</Major><Minor>27</Minor></Version>
            <FileName>gup3651.gcd</FileName>
        </UpdateFile>
        <UpdateFile>
            <PartNumber>006-B4605-02</PartNumber>
            <Version><Major>1</Major><Minor>02</Minor></Version>
            <FileName>gup4605.gcd</FileName>
        </UpdateFile>
    </MassStorageMode>
    <Extensions>
        <IQAppExt>
            <VmVersion>6.0.3</VmVersion>
            <MaxApps>32</MaxApps>
            <AppSpace>67108864</AppSpace>
            <Apps>
                <App>
                    <AppName>Spotify</AppName>
                    <AppType>audio-content-provider-app</AppType>
                    <Version>72</Version>
                    <AppId>6eb48a8f-9bd8-4fe0-99e7-28d787c8a711</AppId>
                    <FileName>G8TI4826.PRG</FileName>
                </App>
                <App>
                    <AppName>Goals 8</AppName>
                    <AppType>watchface</AppType>
                    <Version>38</Version>
                    <AppId>9652ba99-8a9c-4202-b57c-37af2525ab68</AppId>
                    <FileName>G8UA0039.PRG</FileName>
                </App>
            </Apps>
        </IQAppExt>
    </Extensions>
</Device>`

	iq, comps := parseDetailedXML([]byte(xmlData))

	if iq.VMVersion != "6.0.3" {
		t.Errorf("VMVersion = %q, want %q", iq.VMVersion, "6.0.3")
	}
	if iq.MaxApps != 32 {
		t.Errorf("MaxApps = %d, want 32", iq.MaxApps)
	}
	if iq.AppSpaceBytes != 67108864 {
		t.Errorf("AppSpaceBytes = %d, want 67108864", iq.AppSpaceBytes)
	}
	if len(iq.Apps) != 2 {
		t.Fatalf("len(Apps) = %d, want 2", len(iq.Apps))
	}
	if iq.Apps[0].Name != "Spotify" || iq.Apps[0].Type != "audio-content-provider-app" || iq.Apps[0].Version != "72" {
		t.Errorf("unexpected first app: %+v", iq.Apps[0])
	}
	if iq.Apps[1].Name != "Goals 8" || iq.Apps[1].Type != "watchface" {
		t.Errorf("unexpected second app: %+v", iq.Apps[1])
	}

	if comps.GPS != "11.02" {
		t.Errorf("GPS = %q, want %q", comps.GPS, "11.02")
	}
	if comps.Wireless != "29.27" {
		t.Errorf("Wireless = %q, want %q", comps.Wireless, "29.27")
	}
	if comps.SensorHub != "1.02" {
		t.Errorf("SensorHub = %q, want %q", comps.SensorHub, "1.02")
	}
}

func TestGetDetailedInfo(t *testing.T) {
	tempDir := t.TempDir()
	garminDir := filepath.Join(tempDir, "GARMIN")
	if err := os.MkdirAll(garminDir, 0755); err != nil {
		t.Fatal(err)
	}

	xmlData := `<Device><Model><Description>Test Device</Description></Model></Device>`
	if err := os.WriteFile(filepath.Join(garminDir, "GarminDevice.xml"), []byte(xmlData), 0644); err != nil {
		t.Fatal(err)
	}

	dev := &Info{
		Model:     "Test Device",
		ID:        "123456",
		MountPath: tempDir,
	}

	detailed, err := GetDetailedInfo(dev)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if detailed == nil {
		t.Fatal("expected detailed info, got nil")
	}
	if detailed.Model != "Test Device" {
		t.Errorf("Model = %q, want %q", detailed.Model, "Test Device")
	}
	if detailed.Storage.TotalBytes == 0 {
		t.Errorf("expected non-zero storage total for temp dir, got %d", detailed.Storage.TotalBytes)
	}
}
