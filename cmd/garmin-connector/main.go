package main

import (
	"fmt"
	"os"

	"github.com/jvanheerikhuize/garmin-connector/internal/cli"
	"github.com/spf13/cobra"
)

var versionFlag bool

var rootCmd = &cobra.Command{
	Use:   "garmin-connector",
	Short: "A tool to connect and manage Garmin watches",
	Run: func(cmd *cobra.Command, args []string) {
		if versionFlag {
			fmt.Println("1.0.0")
			return
		}
		cmd.Help()
	},
}

func init() {
	rootCmd.Flags().BoolVar(&versionFlag, "version", false, "Print version")
	rootCmd.AddCommand(cli.StatusCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
