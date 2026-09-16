package device

import (
	"math"
	"syscall"
)

// StorageInfo represents filesystem storage metrics on the watch.
type StorageInfo struct {
	TotalBytes     uint64  `json:"total_bytes"`
	UsedBytes      uint64  `json:"used_bytes"`
	FreeBytes      uint64  `json:"free_bytes"`
	UsedPercentage float64 `json:"used_percentage"`
}

// getStorageInfo queries filesystem capacity metrics for the given mount path.
func getStorageInfo(mountPath string) StorageInfo {
	var stat syscall.Statfs_t
	err := syscall.Statfs(mountPath, &stat)
	if err != nil || stat.Blocks == 0 {
		return StorageInfo{}
	}

	total := stat.Blocks * uint64(stat.Bsize)
	free := stat.Bavail * uint64(stat.Bsize)
	if free > total {
		free = total
	}
	used := total - free

	percentage := (float64(used) / float64(total)) * 100.0
	// Round to 1 decimal place
	roundedPercentage := math.Round(percentage*10) / 10

	return StorageInfo{
		TotalBytes:     total,
		UsedBytes:      used,
		FreeBytes:      free,
		UsedPercentage: roundedPercentage,
	}
}
