package cli

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"

	"garmin-connector/internal/device"
)

func TestRunInfo(t *testing.T) {
	mockDev := &device.Info{
		Model:           "Garmin Venu X1",
		ID:              "3617019779",
		SoftwareVersion: "1829",
		PartNumber:      "006-B4603-00",
		MountPath:       "/mnt/garmin",
	}

	mockDetailed := &device.DetailedInfo{
		Info: *mockDev,
		Storage: device.StorageInfo{
			TotalBytes:     31000000000,
			UsedBytes:      14000000000,
			FreeBytes:      17000000000,
			UsedPercentage: 45.2,
		},
		ConnectIQ: device.ConnectIQInfo{
			VMVersion:     "6.0.3",
			MaxApps:       32,
			AppSpaceBytes: 67108864,
			Apps: []device.AppInfo{
				{
					Name:    "Spotify",
					Type:    "audio-content-provider-app",
					Version: "72",
				},
			},
		},
		Components: device.ComponentVersions{
			GPS:       "11.02",
			Wireless:  "29.27",
			SensorHub: "1.02",
		},
	}

	t.Run("RunInfo without json when device connected", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunInfo(buf, false, func() (*device.Info, error) {
			return mockDev, nil
		}, func(dev *device.Info) (*device.DetailedInfo, error) {
			return mockDetailed, nil
		})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		out := buf.String()
		if !strings.Contains(out, "Garmin Venu X1") || !strings.Contains(out, "3617019779") {
			t.Errorf("missing device ID or model in output: %s", out)
		}
		if !strings.Contains(out, "Storage:") || !strings.Contains(out, "GB") {
			t.Errorf("missing storage in output: %s", out)
		}
		if !strings.Contains(out, "Connect IQ") || !strings.Contains(out, "Spotify") {
			t.Errorf("missing connect iq in output: %s", out)
		}
		if !strings.Contains(out, "Components:") || !strings.Contains(out, "GPS:") {
			t.Errorf("missing components in output: %s", out)
		}
	})

	t.Run("RunInfo with json when device connected", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunInfo(buf, true, func() (*device.Info, error) {
			return mockDev, nil
		}, func(dev *device.Info) (*device.DetailedInfo, error) {
			return mockDetailed, nil
		})
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		var resp InfoResponse
		if err := json.Unmarshal(buf.Bytes(), &resp); err != nil {
			t.Fatalf("failed to unmarshal json: %v", err)
		}
		if !resp.Connected {
			t.Errorf("Connected = false, want true")
		}
		if resp.Device == nil || resp.Device.Model != "Garmin Venu X1" {
			t.Errorf("unexpected device: %+v", resp.Device)
		}
		if resp.Device.Storage.TotalBytes != 31000000000 {
			t.Errorf("Storage.TotalBytes = %d, want 31000000000", resp.Device.Storage.TotalBytes)
		}
		if len(resp.Device.ConnectIQ.Apps) != 1 || resp.Device.ConnectIQ.Apps[0].Name != "Spotify" {
			t.Errorf("unexpected apps: %+v", resp.Device.ConnectIQ.Apps)
		}
		if resp.Device.Components.GPS != "11.02" {
			t.Errorf("Components.GPS = %q, want %q", resp.Device.Components.GPS, "11.02")
		}
	})

	t.Run("RunInfo without json when no device connected", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunInfo(buf, false, func() (*device.Info, error) {
			return nil, nil
		}, nil)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if buf.String() != "No Garmin device detected.\n" {
			t.Errorf("got %q, want %q", buf.String(), "No Garmin device detected.\n")
		}
	})

	t.Run("RunInfo with json when no device connected", func(t *testing.T) {
		buf := new(bytes.Buffer)
		err := RunInfo(buf, true, func() (*device.Info, error) {
			return nil, nil
		}, nil)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		var resp InfoResponse
		if err := json.Unmarshal(buf.Bytes(), &resp); err != nil {
			t.Fatalf("failed to unmarshal json: %v", err)
		}
		if resp.Connected != false || resp.Device != nil {
			t.Errorf("unexpected json response: %+v", resp)
		}
	})
}
