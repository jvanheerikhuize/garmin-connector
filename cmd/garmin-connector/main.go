package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"garmin-connector/internal/api"
)

var (
	host       string
	port       int
	noBrowser  bool
)

func main() {
	var rootCmd = &cobra.Command{
		Use:   "garmin-connector",
		Short: "A lightning-fast, cross-platform CLI tool for Garmin watches.",
		Version: "1.0.0",
	}

	var guiCmd = &cobra.Command{
		Use:   "gui",
		Short: "Start the web GUI and local server",
		RunE: func(cmd *cobra.Command, args []string) error {
			return api.Serve(host, port, !noBrowser)
		},
	}
	guiCmd.Flags().StringVar(&host, "host", "127.0.0.1", "Host to listen on")
	guiCmd.Flags().IntVarP(&port, "port", "p", 8080, "Port to listen on")
	guiCmd.Flags().BoolVar(&noBrowser, "no-browser", false, "Do not auto-open the browser")

	var listCmd = &cobra.Command{
		Use:   "list",
		Short: "List courses on the connected Garmin watch",
		RunE: func(cmd *cobra.Command, args []string) error {
			// headless support (placeholder)
			fmt.Println("Listing courses (headless)")
			return nil
		},
	}

	var sideloadCmd = &cobra.Command{
		Use:   "sideload [file.gpx]",
		Short: "Convert and sideload a GPX file to the connected watch",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			// headless support (placeholder)
			fmt.Printf("Sideloading %s (headless)\n", args[0])
			return nil
		},
	}

	rootCmd.AddCommand(guiCmd, listCmd, sideloadCmd)

	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
