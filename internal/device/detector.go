package device

import (
	"encoding/xml"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"github.com/ganeshrvel/go-mtpx"
)

type GarminDeviceInfo struct {
	ModelName       string `json:"model_name"`
	UnitID          string `json:"unit_id,omitempty"`
	SoftwareVersion string `json:"software_version,omitempty"`
	PartNumber      string `json:"part_number,omitempty"`
	MountPoint      string `json:"mount_point"`
	GarminDir       string `json:"-"`
	NewFilesDir     string `json:"-"`
	CoursesDir      string `json:"-"`
}

func getCandidateRoots() []string {
	var roots []string
	switch runtime.GOOS {
	case "linux":
		// User mounts
		if uid := os.Getuid(); uid > 0 {
			gvfsPath := fmt.Sprintf("/run/user/%d/gvfs", uid)
			entries, _ := ioutil.ReadDir(gvfsPath)
			for _, e := range entries {
				name := strings.ToLower(e.Name())
				if strings.Contains(name, "mtp:") || strings.Contains(name, "garmin") {
					roots = append(roots, filepath.Join(gvfsPath, e.Name()))
				}
			}
		}
		user := os.Getenv("USER")
		if user != "" {
			roots = append(roots, fmt.Sprintf("/media/%s", user), fmt.Sprintf("/run/media/%s", user))
		}
		roots = append(roots, "/media", "/mnt")
	case "darwin":
		roots = append(roots, "/Volumes")
	case "windows":
		for c := 'A'; c <= 'Z'; c++ {
			roots = append(roots, fmt.Sprintf("%c:\\", c))
		}
	}
	return roots
}

func DetectDevices(customPath string) ([]GarminDeviceInfo, error) {
	var devices []GarminDeviceInfo

	checkMount := func(mount string) {
		// Does it have a GARMIN dir? Or is it GARMIN?
		garminPath := ""
		if strings.EqualFold(filepath.Base(mount), "garmin") {
			garminPath = mount
		} else {
			// Find child
			entries, err := ioutil.ReadDir(mount)
			if err != nil {
				return
			}
			for _, e := range entries {
				if e.IsDir() && strings.EqualFold(e.Name(), "garmin") {
					garminPath = filepath.Join(mount, e.Name())
					break
				}
			}
		}

		if garminPath == "" {
			return
		}

		// Read GarminDevice.xml
		info := GarminDeviceInfo{
			MountPoint: mount,
			GarminDir:  garminPath,
			ModelName:  "Garmin Generic", // Fallback
		}

		xmlPath := filepath.Join(garminPath, "GarminDevice.xml") // Try exact case first
		if _, err := os.Stat(xmlPath); os.IsNotExist(err) {
			// Case insensitive search
			entries, _ := ioutil.ReadDir(garminPath)
			for _, e := range entries {
				if !e.IsDir() && strings.EqualFold(e.Name(), "garmindevice.xml") {
					xmlPath = filepath.Join(garminPath, e.Name())
					break
				}
			}
		}

		if b, err := ioutil.ReadFile(xmlPath); err == nil {
			type Model struct {
				Description string `xml:"Description"`
			}
			type Device struct {
				Model           Model  `xml:"Model"`
				Id              string `xml:"Id"`
				SoftwareVersion string `xml:"SoftwareVersion"`
				PartNumber      string `xml:"PartNumber"`
			}
			type Doc struct {
				Device Device `xml:"Device"`
			}
			var doc Doc
			// Remove namespaces for simpler parsing
			cleanXML := strings.ReplaceAll(string(b), "xmlns", "ignore")
			if err := xml.Unmarshal([]byte(cleanXML), &doc); err == nil {
				if doc.Device.Model.Description != "" {
					info.ModelName = doc.Device.Model.Description
				}
				info.UnitID = doc.Device.Id
				info.SoftwareVersion = doc.Device.SoftwareVersion
				info.PartNumber = doc.Device.PartNumber
			}
		}

		// Find Subdirs case insensitive
		entries, _ := ioutil.ReadDir(garminPath)
		for _, e := range entries {
			if e.IsDir() {
				name := strings.ToLower(e.Name())
				if name == "newfiles" {
					info.NewFilesDir = filepath.Join(garminPath, e.Name())
				} else if name == "courses" {
					info.CoursesDir = filepath.Join(garminPath, e.Name())
				}
			}
		}
		if info.NewFilesDir == "" {
			info.NewFilesDir = filepath.Join(garminPath, "NEWFILES")
		}
		if info.CoursesDir == "" {
			info.CoursesDir = filepath.Join(garminPath, "COURSES")
		}

		devices = append(devices, info)
	}

	if customPath != "" {
		checkMount(customPath)
		return devices, nil
	}

	roots := getCandidateRoots()
	for _, root := range roots {
		if runtime.GOOS != "windows" {
			entries, err := ioutil.ReadDir(root)
			if err != nil {
				continue
			}
			for _, e := range entries {
				if e.IsDir() {
					checkMount(filepath.Join(root, e.Name()))
				}
			}
		} else {
			if _, err := os.Stat(root); err == nil {
				checkMount(root)
			}
		}
	}

	
	// Also check raw MTP devices via go-mtpx (in case gvfsd-mtp is dead)
	if customPath == "" {
		dev, err := mtpx.Initialize(mtpx.Init{DebugMode: false})
		if err == nil {
			info, err2 := mtpx.FetchDeviceInfo(dev)
			if err2 == nil {
				devices = append(devices, GarminDeviceInfo{
					ModelName: "Garmin " + info.Model,
					MountPoint: "MTP:" + info.SerialNumber,
				})
			}
			mtpx.Dispose(dev)
		}
	}
	return devices, nil
}

func GetFirstDevice(customPath string) (*GarminDeviceInfo, error) {
	devices, err := DetectDevices(customPath)
	if err != nil {
		return nil, err
	}
	if len(devices) > 0 {
		return &devices[0], nil
	}
	return nil, nil
}


