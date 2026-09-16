package cli

import (
	"encoding/json"
	"fmt"
	"io"

	"garmin-connector/internal/device"

	"github.com/spf13/cobra"
)

// InfoResponse represents the JSON output schema of the info command.
type InfoResponse struct {
	Connected bool                 `json:"connected"`
	Device    *device.DetailedInfo `json:"device"`
}

// NewInfoCommand creates the info subcommand.
func NewInfoCommand() *cobra.Command {
	var jsonFlag bool

	infoCmd := &cobra.Command{
		Use:   "info",
		Short: "Display detailed device metadata, storage capacity, and installed apps",
		RunE: func(cmd *cobra.Command, args []string) error {
			return RunInfo(cmd.OutOrStdout(), jsonFlag, device.Discover, device.GetDetailedInfo)
		},
	}

	infoCmd.Flags().BoolVar(&jsonFlag, "json", false, "Output detailed information as JSON")

	return infoCmd
}

// RunInfo executes detailed inspection and formats the output.
func RunInfo(
	out io.Writer,
	jsonOutput bool,
	discoverFn func() (*device.Info, error),
	detailedFn func(*device.Info) (*device.DetailedInfo, error),
) error {
	dev, err := discoverFn()
	if err != nil || dev == nil {
		if jsonOutput {
			resp := InfoResponse{
				Connected: false,
				Device:    nil,
			}
			data, _ := json.MarshalIndent(resp, "", "  ")
			fmt.Fprintln(out, string(data))
		} else {
			fmt.Fprintln(out, "No Garmin device detected.")
		}
		return nil
	}

	detailed, err := detailedFn(dev)
	if err != nil || detailed == nil {
		detailed = &device.DetailedInfo{Info: *dev}
	}

	if jsonOutput {
		resp := InfoResponse{
			Connected: true,
			Device:    detailed,
		}
		data, err := json.MarshalIndent(resp, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintln(out, string(data))
		return nil
	}

	// Human-readable format
	if detailed.ID != "" {
		fmt.Fprintf(out, "Device:   %s (ID: %s)\n", detailed.Model, detailed.ID)
	} else {
		fmt.Fprintf(out, "Device:   %s\n", detailed.Model)
	}

	if detailed.SoftwareVersion != "" {
		if detailed.PartNumber != "" {
			fmt.Fprintf(out, "Software: v%s (Part: %s)\n", detailed.SoftwareVersion, detailed.PartNumber)
		} else {
			fmt.Fprintf(out, "Software: v%s\n", detailed.SoftwareVersion)
		}
	}
	if detailed.MountPath != "" {
		fmt.Fprintf(out, "Mount:    %s\n", detailed.MountPath)
	}

	// Storage section
	if detailed.Storage.TotalBytes > 0 {
		fmt.Fprintln(out, "\nStorage:")
		fmt.Fprintf(out, "  Total: %s\n", formatBytes(detailed.Storage.TotalBytes))
		fmt.Fprintf(out, "  Used:  %s (%.1f%%)\n", formatBytes(detailed.Storage.UsedBytes), detailed.Storage.UsedPercentage)
		fmt.Fprintf(out, "  Free:  %s\n", formatBytes(detailed.Storage.FreeBytes))
	}

	// Components section
	if detailed.Components.GPS != "" || detailed.Components.Wireless != "" || detailed.Components.SensorHub != "" {
		fmt.Fprintln(out, "\nComponents:")
		if detailed.Components.GPS != "" {
			fmt.Fprintf(out, "  GPS:        v%s\n", detailed.Components.GPS)
		}
		if detailed.Components.Wireless != "" {
			fmt.Fprintf(out, "  Wireless:   v%s\n", detailed.Components.Wireless)
		}
		if detailed.Components.SensorHub != "" {
			fmt.Fprintf(out, "  Sensor Hub: v%s\n", detailed.Components.SensorHub)
		}
	}

	// Connect IQ section
	if detailed.ConnectIQ.VMVersion != "" || len(detailed.ConnectIQ.Apps) > 0 {
		appCount := len(detailed.ConnectIQ.Apps)
		if detailed.ConnectIQ.MaxApps > 0 {
			fmt.Fprintf(out, "\nConnect IQ (VM: %s, %d/%d apps):\n", detailed.ConnectIQ.VMVersion, appCount, detailed.ConnectIQ.MaxApps)
		} else {
			fmt.Fprintf(out, "\nConnect IQ (VM: %s):\n", detailed.ConnectIQ.VMVersion)
		}

		for _, app := range detailed.ConnectIQ.Apps {
			if app.Version != "" {
				fmt.Fprintf(out, "  - %s (%s, v%s)\n", app.Name, app.Type, app.Version)
			} else {
				fmt.Fprintf(out, "  - %s (%s)\n", app.Name, app.Type)
			}
		}
	}

	return nil
}

func formatBytes(b uint64) string {
	const (
		unit = 1000
		kb   = unit
		mb   = kb * unit
		gb   = mb * unit
	)
	switch {
	case b >= gb:
		return fmt.Sprintf("%.2f GB", float64(b)/float64(gb))
	case b >= mb:
		return fmt.Sprintf("%.2f MB", float64(b)/float64(mb))
	case b >= kb:
		return fmt.Sprintf("%.2f KB", float64(b)/float64(kb))
	default:
		return fmt.Sprintf("%d B", b)
	}
}
