package cli

import (
	"encoding/json"
	"fmt"
	"io"

	"garmin-connector/internal/device"

	"github.com/spf13/cobra"
)

// StatusResponse represents the JSON output schema of the status command.
type StatusResponse struct {
	Connected bool         `json:"connected"`
	Device    *device.Info `json:"device"`
}

// NewStatusCommand creates the status subcommand.
func NewStatusCommand() *cobra.Command {
	var jsonFlag bool

	statusCmd := &cobra.Command{
		Use:   "status",
		Short: "Inspect and report Garmin device connection status",
		RunE: func(cmd *cobra.Command, args []string) error {
			return RunStatus(cmd.OutOrStdout(), jsonFlag, device.Discover)
		},
	}

	statusCmd.Flags().BoolVar(&jsonFlag, "json", false, "Output status as JSON")

	return statusCmd
}

// RunStatus executes status logic and formats the output.
func RunStatus(out io.Writer, jsonOutput bool, discoverFn func() (*device.Info, error)) error {
	dev, err := discoverFn()
	if err != nil {
		dev = nil
	}

	if jsonOutput {
		resp := StatusResponse{
			Connected: dev != nil,
			Device:    dev,
		}
		data, err := json.MarshalIndent(resp, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintln(out, string(data))
		return nil
	}

	if dev == nil {
		fmt.Fprintln(out, "No Garmin device detected.")
		return nil
	}

	if dev.ID != "" {
		fmt.Fprintf(out, "Device found: %s (ID: %s)\n", dev.Model, dev.ID)
	} else {
		fmt.Fprintf(out, "Device found: %s\n", dev.Model)
	}

	return nil
}
