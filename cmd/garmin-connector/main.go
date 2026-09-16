package main

import (
	"os"

	"garmin-connector/internal/cli"
)

func main() {
	rootCmd := cli.NewRootCommand()
	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
