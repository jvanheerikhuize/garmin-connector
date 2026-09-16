package cli

import (
	"encoding/json"
	"fmt"
	"io"

	"garmin-connector/internal/device"

	"github.com/spf13/cobra"
)

// NewTreeCommand creates the tree subcommand.
func NewTreeCommand() *cobra.Command {
	var jsonFlag bool
	var allFlag bool
	var depth int

	treeCmd := &cobra.Command{
		Use:   "tree [path]",
		Short: "List contents of a directory on the Garmin watch in a tree-like format",
		Args:  cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			path := ""
			if len(args) > 0 {
				path = args[0]
			}
			return RunTree(cmd.OutOrStdout(), path, depth, jsonFlag, allFlag, device.Discover)
		},
	}

	treeCmd.Flags().BoolVar(&jsonFlag, "json", false, "Output tree as JSON")
	treeCmd.Flags().BoolVarP(&allFlag, "all", "a", false, "Do not ignore entries starting with .")
	treeCmd.Flags().IntVarP(&depth, "depth", "d", 3, "Maximum recursion depth")

	return treeCmd
}

func RunTree(out io.Writer, relPath string, maxDepth int, jsonOutput bool, showHidden bool, discoverFn func() (*device.Info, error)) error {
	dev, err := discoverFn()
	if err != nil || dev == nil {
		if jsonOutput {
			fmt.Fprintln(out, "null")
		} else {
			fmt.Fprintln(out, "No Garmin device detected.")
		}
		return nil
	}

	node, err := device.Tree(dev, relPath, maxDepth, showHidden)
	if err != nil {
		return fmt.Errorf("failed to build tree: %w", err)
	}

	if jsonOutput {
		data, err := json.MarshalIndent(node, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintln(out, string(data))
		return nil
	}

	if node != nil {
		fmt.Fprintln(out, node.Name)
		printTree(out, node, "")
	}

	return nil
}

func printTree(out io.Writer, node *device.FileNode, prefix string) {
	for i, child := range node.Children {
		isLast := i == len(node.Children)-1
		
		marker := "├── "
		if isLast {
			marker = "└── "
		}
		
		fmt.Fprintf(out, "%s%s%s\n", prefix, marker, child.Name)
		
		if child.IsDir {
			nextPrefix := prefix + "│   "
			if isLast {
				nextPrefix = prefix + "    "
			}
			printTree(out, child, nextPrefix)
		}
	}
}
