package cli

import (
	"encoding/json"
	"fmt"
	"io"
	"strings"

	"garmin-connector/internal/device"

	"github.com/spf13/cobra"
)

// NewLsCommand creates the ls subcommand.
func NewLsCommand() *cobra.Command {
	var jsonFlag bool
	var allFlag bool

	lsCmd := &cobra.Command{
		Use:   "ls [path]",
		Short: "List contents of a directory on the Garmin watch",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			path := ""
			if len(args) > 0 {
				path = args[0]
			}
			return RunLs(cmd.OutOrStdout(), path, jsonFlag, allFlag, device.Discover)
		},
	}

	lsCmd.Flags().BoolVar(&jsonFlag, "json", false, "Output listing as JSON")
	lsCmd.Flags().BoolVarP(&allFlag, "all", "a", false, "Do not ignore entries starting with .")

	return lsCmd
}

func RunLs(out io.Writer, relPath string, jsonOutput bool, showHidden bool, discoverFn func() (*device.Info, error)) error {
	dev, err := discoverFn()
	if err != nil || dev == nil {
		if jsonOutput {
			fmt.Fprintln(out, "[]")
		} else {
			fmt.Fprintln(out, "No Garmin device detected.")
		}
		return nil
	}

	nodes, err := device.ListDir(dev, relPath, showHidden)
	if err != nil {
		return fmt.Errorf("failed to list directory: %w", err)
	}

	if jsonOutput {
		if nodes == nil {
			nodes = []device.FileNode{}
		}
		data, err := json.MarshalIndent(nodes, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintln(out, string(data))
		return nil
	}

	for _, node := range nodes {
		typeIndicator := ""
		if node.IsDir {
			typeIndicator = "/"
		}
		fmt.Fprintf(out, "%12d  %s  %s%s\n", node.Size, strings.Replace(node.ModifiedTime, "T", " ", 1)[:19], node.Name, typeIndicator)
	}

	return nil
}
