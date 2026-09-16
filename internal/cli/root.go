package cli

import (
	"github.com/spf13/cobra"
)

// NewRootCommand creates the base garmin-connector command.
func NewRootCommand() *cobra.Command {
	rootCmd := &cobra.Command{
		Use:     "garmin-connector",
		Short:   "CLI tool to connect Garmin watches to a laptop over USB",
		Version: "1.0.0",
		RunE: func(cmd *cobra.Command, args []string) error {
			return cmd.Help()
		},
	}

	rootCmd.SetVersionTemplate("{{.Version}}\n")

	rootCmd.AddCommand(NewStatusCommand())
	rootCmd.AddCommand(NewInfoCommand())
	rootCmd.AddCommand(NewLsCommand())
	rootCmd.AddCommand(NewTreeCommand())

	return rootCmd
}
