package cli

import (
	"bytes"
	"encoding/json"
	"os"
	"strings"
	"testing"

	"garmin-connector/internal/device"
)

func TestCLIHelpAndVersion(t *testing.T) {
	t.Run("Version flag outputs 1.0.0", func(t *testing.T) {
		cmd := NewRootCommand()
		buf := new(bytes.Buffer)
		cmd.SetOut(buf)
		cmd.SetErr(buf)
		cmd.SetArgs([]string{"--version"})

		if err := cmd.Execute(); err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if got := strings.TrimSpace(buf.String()); got != "1.0.0" {
			t.Errorf("got %q, want %q", got, "1.0.0")
		}
	})

	t.Run("No arguments displays help and exits 0", func(t *testing.T) {
		cmd := NewRootCommand()
		buf := new(bytes.Buffer)
		cmd.SetOut(buf)
		cmd.SetErr(buf)
		cmd.SetArgs([]string{})

		if err := cmd.Execute(); err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		output := buf.String()
		if !strings.Contains(output, "Usage:") || !strings.Contains(output, "Available Commands:") {
			t.Errorf("expected usage and available commands in help output, got: %s", output)
		}
	})

	t.Run("Help flag displays usage and available commands", func(t *testing.T) {
		cmd := NewRootCommand()
		buf := new(bytes.Buffer)
		cmd.SetOut(buf)
		cmd.SetErr(buf)
		cmd.SetArgs([]string{"--help"})

		if err := cmd.Execute(); err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		output := buf.String()
		if !strings.Contains(output, "Usage:") || !strings.Contains(output, "status") {
			t.Errorf("expected status command listed in help output, got: %s", output)
		}
	})

	t.Run("Unrecognized subcommand returns error", func(t *testing.T) {
		cmd := NewRootCommand()
		buf := new(bytes.Buffer)
		cmd.SetOut(buf)
		cmd.SetErr(buf)
		cmd.SetArgs([]string{"nonexistent-subcommand"})

		if err := cmd.Execute(); err == nil {
			t.Fatal("expected error for unrecognized subcommand, got nil")
		}
	})
}

func TestRunStatus(t *testing.T) {
	mockDevice := &device.Info{
		Model:           "Garmin Venu X1",
		ID:              "3123456789",
		SoftwareVersion: "14.20",
		PartNumber:      "010-02430-01",
		MountPath:       "/run/user/1000/gvfs/mtp:host=Garmin_Venu_X1",
	}

	t.Run("Status without json when device connected", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunStatus(buf, false, func() (*device.Info, error) {
			return mockDevice, nil
		})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		want := "Device found: Garmin Venu X1 (ID: 3123456789)\n"
		if buf.String() != want {
			t.Errorf("got %q, want %q", buf.String(), want)
		}
	})

	t.Run("Status without json when device connected without ID", func(t *testing.T) {
		buf := new(bytes.Buffer)
		genericDevice := &device.Info{
			Model:     "Generic Garmin",
			MountPath: "/mnt/garmin",
		}
		err := RunStatus(buf, false, func() (*device.Info, error) {
			return genericDevice, nil
		})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		want := "Device found: Generic Garmin\n"
		if buf.String() != want {
			t.Errorf("got %q, want %q", buf.String(), want)
		}
	})

	t.Run("Status without json when no device connected", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunStatus(buf, false, func() (*device.Info, error) {
			return nil, nil
		})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		want := "No Garmin device detected.\n"
		if buf.String() != want {
			t.Errorf("got %q, want %q", buf.String(), want)
		}
	})

	t.Run("Status with json when device connected", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunStatus(buf, true, func() (*device.Info, error) {
			return mockDevice, nil
		})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		var resp StatusResponse
		if err := json.Unmarshal(buf.Bytes(), &resp); err != nil {
			t.Fatalf("failed to unmarshal json output: %v", err)
		}
		if !resp.Connected {
			t.Errorf("Connected = false, want true")
		}
		if resp.Device == nil || resp.Device.Model != "Garmin Venu X1" {
			t.Errorf("unexpected device in json: %+v", resp.Device)
		}
		if resp.Device.ID != "3123456789" {
			t.Errorf("Device.ID = %q, want %q", resp.Device.ID, "3123456789")
		}
		if resp.Device.SoftwareVersion != "14.20" {
			t.Errorf("Device.SoftwareVersion = %q, want %q", resp.Device.SoftwareVersion, "14.20")
		}
		if resp.Device.PartNumber != "010-02430-01" {
			t.Errorf("Device.PartNumber = %q, want %q", resp.Device.PartNumber, "010-02430-01")
		}
		if resp.Device.MountPath != "/run/user/1000/gvfs/mtp:host=Garmin_Venu_X1" {
			t.Errorf("Device.MountPath = %q, want %q", resp.Device.MountPath, "/run/user/1000/gvfs/mtp:host=Garmin_Venu_X1")
		}
	})

	t.Run("Status with json when no device connected", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunStatus(buf, true, func() (*device.Info, error) {
			return nil, nil
		})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		var resp StatusResponse
		if err := json.Unmarshal(buf.Bytes(), &resp); err != nil {
			t.Fatalf("failed to unmarshal json output: %v", err)
		}
		if resp.Connected {
			t.Errorf("Connected = true, want false")
		}
		if resp.Device != nil {
			t.Errorf("expected Device = nil, got %+v", resp.Device)
		}

		// Also verify exact string representation matches spec schema
		var rawMap map[string]interface{}
		if err := json.Unmarshal(buf.Bytes(), &rawMap); err != nil {
			t.Fatalf("json parse error: %v", err)
		}
		if rawMap["connected"] != false || rawMap["device"] != nil {
			t.Errorf("unexpected json map: %+v", rawMap)
		}
	})
}

func setupMockDevice(t *testing.T) (*device.Info, string) {
	tempDir := t.TempDir()
	watchRoot := tempDir
	garminDir := tempDir + "/GARMIN"
	os.MkdirAll(garminDir, 0755)
	os.WriteFile(garminDir+"/test.txt", []byte("123"), 0644)
	return &device.Info{MountPath: tempDir}, watchRoot
}

func TestRunLs(t *testing.T) {
	t.Run("RunLs without device", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunLs(buf, "", false, false, func() (*device.Info, error) { return nil, nil })
		if err != nil {
			t.Fatal(err)
		}
		if buf.String() != "No Garmin device detected.\n" {
			t.Errorf("Unexpected output: %s", buf.String())
		}
	})

	t.Run("RunLs with device json", func(t *testing.T) {
		info, _ := setupMockDevice(t)
		buf := new(bytes.Buffer)
		err := RunLs(buf, "", true, false, func() (*device.Info, error) { return info, nil })
		if err != nil {
			t.Fatal(err)
		}
		var nodes []device.FileNode
		if err := json.Unmarshal(buf.Bytes(), &nodes); err != nil {
			t.Fatal(err)
		}
		if len(nodes) != 1 || nodes[0].Name != "GARMIN" {
			t.Errorf("Expected 1 GARMIN node, got %+v", nodes)
		}
	})
}

func TestRunTree(t *testing.T) {
	t.Run("RunTree without device json", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunTree(buf, "", 3, true, false, func() (*device.Info, error) { return nil, nil })
		if err != nil {
			t.Fatal(err)
		}
		if strings.TrimSpace(buf.String()) != "null" {
			t.Errorf("Unexpected output: %s", buf.String())
		}
	})

	t.Run("RunTree with device", func(t *testing.T) {
		info, watchRoot := setupMockDevice(t)
		buf := new(bytes.Buffer)
		err := RunTree(buf, "", 3, false, false, func() (*device.Info, error) { return info, nil })
		if err != nil {
			t.Fatal(err)
		}
		out := buf.String()
		if !strings.Contains(out, "GARMIN") {
			t.Errorf("Expected GARMIN in tree output, got: %s", out)
		}
		
		parts := strings.Split(watchRoot, "/")
		rootName := parts[len(parts)-1]
		if !strings.Contains(out, rootName) {
			t.Errorf("Expected root name %s in tree output, got: %s", rootName, out)
		}
	})
}
