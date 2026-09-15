package device

import (
	"context"
	"time"
)

type DeviceEvent struct {
	Connected bool
	Device    *GarminDeviceInfo
}

func WatchDevices(ctx context.Context) <-chan DeviceEvent {
	updates := make(chan DeviceEvent)

	go func() {
		defer close(updates)
		ticker := time.NewTicker(2 * time.Second)
		defer ticker.Stop()

		var lastConnected bool
		var lastMountPoint string

		// Initial check
		if dev, _ := GetFirstDevice(""); dev != nil {
			lastConnected = true
			lastMountPoint = dev.MountPoint
			updates <- DeviceEvent{Connected: true, Device: dev}
		} else {
			lastConnected = false
			updates <- DeviceEvent{Connected: false, Device: nil}
		}

		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				dev, _ := GetFirstDevice("")
				connected := (dev != nil)
				
				changed := false
				if connected != lastConnected {
					changed = true
				} else if connected && dev.MountPoint != lastMountPoint {
					changed = true
				}

				if changed {
					lastConnected = connected
					if connected {
						lastMountPoint = dev.MountPoint
					} else {
						lastMountPoint = ""
					}
					updates <- DeviceEvent{Connected: connected, Device: dev}
				}
			}
		}
	}()

	return updates
}
