package device

import (
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sort"
	

	"github.com/ganeshrvel/go-mtpx"
	"github.com/ganeshrvel/go-mtpfs/mtp"
)

func connectMTP() (*mtp.Device, *mtpx.StorageData, error) {
	exec.Command("killall", "gvfsd-mtp").Run()

	dev, err := mtpx.Initialize(mtpx.Init{DebugMode: false})
	if err != nil {
		return nil, nil, err
	}
	
	storages, err := mtpx.FetchStorages(dev)
	if err != nil || len(storages) == 0 {
		mtpx.Dispose(dev)
		return nil, nil, fmt.Errorf("no storages found on MTP device")
	}
	
	return dev, &storages[0], nil
}

func mtpSideload(finalBytes []byte, courseName, ext string) (string, error) {
	dev, storage, err := connectMTP()
	if err != nil {
		return "", err
	}
	defer mtpx.Dispose(dev)

	tmpPath := filepath.Join(os.TempDir(), courseName+ext)
	if err := ioutil.WriteFile(tmpPath, finalBytes, 0644); err != nil {
		return "", err
	}
	defer os.Remove(tmpPath)

	mtpx.MakeDirectory(dev, storage.Sid, "/GARMIN/NewFiles")

	_, _, _, err = mtpx.UploadFiles(dev, storage.Sid, []string{tmpPath}, "/GARMIN/NewFiles", false, nil, nil)
	if err != nil {
		return "", err
	}
	return "/GARMIN/NewFiles/" + courseName + ext, nil
}

func mtpListCourses() ([]CourseFileSummary, error) {
	dev, storage, err := connectMTP()
	if err != nil {
		return nil, err
	}
	defer mtpx.Dispose(dev)

	var list []CourseFileSummary

	fetchDir := func(dirPath, locationLabel string) {
		mtpx.Walk(dev, storage.Sid, dirPath, false, false, false, func(objectId uint32, fi *mtpx.FileInfo, err error) error {
			if err != nil || fi.IsDir {
				return nil
			}
			ext := strings.ToLower(filepath.Ext(fi.Name))
			if ext == ".fit" || ext == ".gpx" {
				list = append(list, CourseFileSummary{
					Filename:   fi.Name,
					FullPath:   fi.FullPath,
					SizeBytes:  fi.Size,
					ModifiedAt: fi.ModTime.UTC(),
					Location:   locationLabel,
				})
			}
			return nil
		})
	}

	fetchDir("/GARMIN/Courses", "COURSES")
	fetchDir("/GARMIN/NewFiles", "NEWFILES (Pending Sync)")
	
	sort.Slice(list, func(i, j int) bool {
		return list[i].Filename < list[j].Filename
	})
	return list, nil
}

func mtpDeleteCourse(filename string) (bool, error) {
	dev, storage, err := connectMTP()
	if err != nil {
		return false, err
	}
	defer mtpx.Dispose(dev)

	deleted := false
	paths := []string{"/GARMIN/Courses/" + filename, "/GARMIN/NewFiles/" + filename}
	
	for _, p := range paths {
		err := mtpx.DeleteFile(dev, storage.Sid, []mtpx.FileProp{{FullPath: p}})
		if err == nil {
			deleted = true
		}
	}
	
	return deleted, nil
}

func mtpFetchCourse(filename string) ([]byte, error) {
	dev, storage, err := connectMTP()
	if err != nil {
		return nil, err
	}
	defer mtpx.Dispose(dev)

	paths := []string{"/GARMIN/Courses/" + filename, "/GARMIN/NewFiles/" + filename}
	var foundPath string
	for _, p := range paths {
		_, err := mtpx.GetObjectFromPath(dev, storage.Sid, p)
		if err == nil {
			foundPath = p
			break
		}
	}

	if foundPath == "" {
		return nil, fmt.Errorf("file not found")
	}

	tmpDir := os.TempDir()
	_, _, err = mtpx.DownloadFiles(dev, storage.Sid, []string{foundPath}, tmpDir, false, nil, nil)
	if err != nil {
		return nil, err
	}
	
	tmpFile := filepath.Join(tmpDir, filename)
	defer os.Remove(tmpFile)
	
	return ioutil.ReadFile(tmpFile)
}
