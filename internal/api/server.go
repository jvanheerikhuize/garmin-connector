package api

import (
	"context"
	"encoding/json"
	"fmt"
	"io/fs"
	"log"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"runtime"
	"syscall"
	"time"

	garminconnector "garmin-connector"
	"garmin-connector/internal/device"
	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true }, // Open CORS
}

func Serve(host string, port int, openBrowser bool) error {
	mux := http.NewServeMux()

	// Static assets
	sub, err := fs.Sub(garminconnector.UIAssets, "ui/dist")
	if err != nil {
		log.Printf("Warning: failed to serve embedded assets: %v", err)
	} else {
		fileServer := http.FileServer(http.FS(sub))
		mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
			if _, err := sub.Open(r.URL.Path[1:]); os.IsNotExist(err) && r.URL.Path != "/" {
				// Fallback to index.html for unknown paths (client-side routing)
				r.URL.Path = "/"
			}
			// Disable caching for index.html to avoid stale embed.FS responses
			if r.URL.Path == "/" || r.URL.Path == "/index.html" {
				w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
			}
			fileServer.ServeHTTP(w, r)
		})
	}

	// GET /api/device
	mux.HandleFunc("/api/device", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		dev, _ := device.GetFirstDevice("")
		if dev != nil {
			json.NewEncoder(w).Encode(map[string]interface{}{
				"connected":        true,
				"model_name":       dev.ModelName,
				"unit_id":          dev.UnitID,
				"software_version": dev.SoftwareVersion,
				"part_number":      dev.PartNumber,
				"mount_point":      dev.MountPoint,
			})
		} else {
			json.NewEncoder(w).Encode(map[string]interface{}{
				"connected":  false,
				"model_name": nil,
			})
		}
	})

	mux.HandleFunc("/api/courses", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "GET" {
			handleGetCourses(w, r)
		}
	})
	mux.HandleFunc("/api/courses/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "DELETE" {
			handleDeleteCourse(w, r)
		}
	})
	mux.HandleFunc("/api/sideload", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" {
			handleSideload(w, r)
		}
	})
	mux.HandleFunc("/api/fetch-course/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "GET" {
			handleFetchCourse(w, r)
		}
	})

	// WS /api/ws
	mux.HandleFunc("/api/ws", wsHandler)

	addr := fmt.Sprintf("%s:%d", host, port)
	server := &http.Server{
		Addr:    addr,
		Handler: mux,
	}

	// Graceful shutdown
	done := make(chan struct{})
	go func() {
		sigint := make(chan os.Signal, 1)
		signal.Notify(sigint, os.Interrupt, syscall.SIGTERM)
		<-sigint
		log.Println("Shutting down server...")
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := server.Shutdown(ctx); err != nil {
			log.Printf("HTTP Server Shutdown Error: %v", err)
		}
		close(done)
	}()

	log.Printf("Server listening on http://%s", addr)
	
	if openBrowser {
		go func() {
			time.Sleep(500 * time.Millisecond) // Give server time to start
			openURL(fmt.Sprintf("http://%s", addr))
		}()
	}

	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		return err
	}
	<-done
	return nil
}

func wsHandler(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}
	defer conn.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	updates := device.WatchDevices(ctx)
	for {
		select {
		case event := <-updates:
			payload := map[string]interface{}{
				"connected": event.Connected,
			}
			if event.Device != nil {
				payload["model_name"] = event.Device.ModelName
				payload["mount_point"] = event.Device.MountPoint
			} else {
				payload["model_name"] = nil
				payload["mount_point"] = nil
			}

			msg := map[string]interface{}{
				"type":    "device_status",
				"payload": payload,
			}

			if err := conn.WriteJSON(msg); err != nil {
				log.Printf("WebSocket write error: %v", err)
				return // Client disconnected
			}
		case <-ctx.Done():
			return
		}
	}
}

func openURL(url string) {
	var err error
	switch runtime.GOOS {
	case "linux":
		err = exec.Command("xdg-open", url).Start()
	case "windows":
		err = exec.Command("rundll32", "url.dll,FileProtocolHandler", url).Start()
	case "darwin":
		err = exec.Command("open", url).Start()
	}
	if err != nil {
		log.Printf("Could not open browser: %v", err)
	}
}
