package device

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDiscoverWithBases(t *testing.T) {
	sampleXML := `<?xml version="1.0" encoding="UTF-8"?>
<Device xmlns="http://www.garmin.com/xmlschemas/GarminDevice/v2">
    <Model>
        <PartNumber>010-02430-01</PartNumber>
        <SoftwareVersion>14.20</SoftwareVersion>
        <Description>Garmin Venu X1</Description>
    </Model>
    <Id>3123456789</Id>
</Device>`

	t.Run("Find device in GVFS mount nested 1 level", func(t *testing.T) {
		tempDir := t.TempDir()
		runUser := filepath.Join(tempDir, "run_user")
		media := filepath.Join(tempDir, "media")
		mnt := filepath.Join(tempDir, "mnt")

		// Create candidate path: <runUser>/1000/gvfs/mtp:host=Garmin/Internal Storage/GARMIN
		candidatePath := filepath.Join(runUser, "1000", "gvfs", "mtp:host=Garmin")
		garminDir := filepath.Join(candidatePath, "Internal Storage", "GARMIN")
		if err := os.MkdirAll(garminDir, 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(garminDir, "GarminDevice.xml"), []byte(sampleXML), 0644); err != nil {
			t.Fatal(err)
		}

		info, err := discoverWithBases(runUser, media, mnt)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if info == nil {
			t.Fatal("expected device to be discovered, got nil")
		}

		if info.Model != "Garmin Venu X1" {
			t.Errorf("Model = %q, want %q", info.Model, "Garmin Venu X1")
		}
		if info.ID != "3123456789" {
			t.Errorf("ID = %q, want %q", info.ID, "3123456789")
		}
		if info.SoftwareVersion != "14.20" {
			t.Errorf("SoftwareVersion = %q, want %q", info.SoftwareVersion, "14.20")
		}
		if info.PartNumber != "010-02430-01" {
			t.Errorf("PartNumber = %q, want %q", info.PartNumber, "010-02430-01")
		}
		if info.MountPath != candidatePath {
			t.Errorf("MountPath = %q, want %q", info.MountPath, candidatePath)
		}
	})

	t.Run("Find device nested 2 levels deep with case variation", func(t *testing.T) {
		tempDir := t.TempDir()
		runUser := filepath.Join(tempDir, "run_user")
		media := filepath.Join(tempDir, "media")
		mnt := filepath.Join(tempDir, "mnt")

		// Candidate path: /mnt/watch/Level1/Level2/garmin/garmindevice.xml
		candidatePath := filepath.Join(mnt, "watch")
		garminDir := filepath.Join(candidatePath, "Level1", "Level2", "garmin")
		if err := os.MkdirAll(garminDir, 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(garminDir, "garmindevice.xml"), []byte(sampleXML), 0644); err != nil {
			t.Fatal(err)
		}

		info, err := discoverWithBases(runUser, media, mnt)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if info == nil {
			t.Fatal("expected device to be discovered, got nil")
		}
		if info.Model != "Garmin Venu X1" {
			t.Errorf("Model = %q, want %q", info.Model, "Garmin Venu X1")
		}
		if info.MountPath != candidatePath {
			t.Errorf("MountPath = %q, want %q", info.MountPath, candidatePath)
		}
	})

	t.Run("Fallback to Generic Garmin when XML is missing", func(t *testing.T) {
		tempDir := t.TempDir()
		runUser := filepath.Join(tempDir, "run_user")
		media := filepath.Join(tempDir, "media")
		mnt := filepath.Join(tempDir, "mnt")

		candidatePath := filepath.Join(media, "user", "GarminWatch")
		garminDir := filepath.Join(candidatePath, "GARMIN")
		if err := os.MkdirAll(garminDir, 0755); err != nil {
			t.Fatal(err)
		}

		info, err := discoverWithBases(runUser, media, mnt)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if info == nil {
			t.Fatal("expected device to be discovered, got nil")
		}
		if info.Model != "Generic Garmin" {
			t.Errorf("Model = %q, want %q", info.Model, "Generic Garmin")
		}
		if info.MountPath != candidatePath {
			t.Errorf("MountPath = %q, want %q", info.MountPath, candidatePath)
		}
	})

	t.Run("Return nil when no Garmin device is connected", func(t *testing.T) {
		tempDir := t.TempDir()
		runUser := filepath.Join(tempDir, "run_user")
		media := filepath.Join(tempDir, "media")
		mnt := filepath.Join(tempDir, "mnt")

		info, err := discoverWithBases(runUser, media, mnt)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if info != nil {
			t.Fatalf("expected nil, got %+v", info)
		}
	})

	t.Run("Permission denied directories are skipped gracefully", func(t *testing.T) {
		tempDir := t.TempDir()
		runUser := filepath.Join(tempDir, "run_user")
		media := filepath.Join(tempDir, "media")
		mnt := filepath.Join(tempDir, "mnt")

		// Create an unreadable user dir
		unreadableUser := filepath.Join(runUser, "unreadable")
		if err := os.MkdirAll(unreadableUser, 0755); err != nil {
			t.Fatal(err)
		}
		_ = os.Chmod(unreadableUser, 0000)
		t.Cleanup(func() {
			_ = os.Chmod(unreadableUser, 0755)
		})

		// Discovery should still succeed without error
		info, err := discoverWithBases(runUser, media, mnt)
		if err != nil {
			t.Fatalf("expected no error despite permission denied directory, got %v", err)
		}
		if info != nil {
			t.Fatalf("expected nil, got %+v", info)
		}
	})
}
