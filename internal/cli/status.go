package cli

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/jvanheerikhuize/garmin-connector/internal/device"
	"github.com/spf13/cobra"
)

var jsonOutput bool

var StatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Check the connection status of a Garmin watch",
	Run: func(cmd *cobra.Command, args []string) {
		dev, err := device.Discover()
		if err != nil {
			// Spec says exit 0 if no watch is found, and not panic on unexpected states.
			// If there's an actual system error (unlikely from Discover), we treat it as disconnected.
		}

		if jsonOutput {
			printJSON(dev)
		} else {
			printText(dev)
		}
	},
}

func init() {
	StatusCmd.Flags().BoolVar(&jsonOutput, "json", false, "Output status as JSON")
}

func printJSON(dev *device.Info) {
	out := map[string]interface{}{
		"connected": dev != nil,
		"device":    dev,
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	enc.Encode(out)
}

func printText(dev *device.Info) {
	if dev == nil {
		fmt.Println("No Garmin device detected.")
		return
	}

	idStr := dev.ID
	if idStr == "" {
		idStr = "unknown"
	}

	fmt.Printf("Device found: %s (ID: %s)\n", dev.Model, idStr)
	if dev.MountPath != "" {
		fmt.Printf("Mount path: %s\n", dev.MountPath)
	}
	if dev.SoftwareVersion != "" {
		fmt.Printf("Software: %s\n", dev.SoftwareVersion)
	}
}
