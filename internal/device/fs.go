package device

import (
	"os"
	"path/filepath"
	"strings"
	"time"
)

type FileNode struct {
	Name         string      `json:"name"`
	IsDir        bool        `json:"is_dir"`
	Size         int64       `json:"size_bytes"`
	ModifiedTime string      `json:"modified_time"`
	Children     []*FileNode `json:"children,omitempty"` // Populated only for 'tree'
}

// resolvePath returns the absolute path on the host given a relative path from the watch root.
// It also handles case-insensitive path resolution.
func resolvePath(info *Info, relPath string) (string, error) {
	garminDir := findGarminDirectory(info.MountPath)
	var watchRoot string
	if garminDir != "" {
		watchRoot = filepath.Dir(garminDir)
	} else {
		watchRoot = info.MountPath
	}

	if relPath == "" || relPath == "." || relPath == "/" {
		return watchRoot, nil
	}

	// Split relPath and resolve case-insensitively step by step
	parts := strings.Split(filepath.ToSlash(relPath), "/")
	current := watchRoot

	for _, part := range parts {
		if part == "" || part == "." {
			continue
		}
		if part == ".." {
			current = filepath.Dir(current)
			continue
		}

		entries, err := os.ReadDir(current)
		if err != nil {
			return "", err
		}

		found := false
		for _, entry := range entries {
			if strings.EqualFold(entry.Name(), part) {
				current = filepath.Join(current, entry.Name())
				found = true
				break
			}
		}

		if !found {
			return "", os.ErrNotExist
		}
	}

	return current, nil
}

// ListDir returns a flat slice of files/directories within the specified path relative to the watch root.
func ListDir(info *Info, relPath string, showHidden bool) ([]FileNode, error) {
	absPath, err := resolvePath(info, relPath)
	if err != nil {
		return nil, err
	}

	entries, err := os.ReadDir(absPath)
	if err != nil {
		return nil, err
	}

	var nodes []FileNode
	for _, entry := range entries {
		if !showHidden && strings.HasPrefix(entry.Name(), ".") {
			continue
		}

		info, err := entry.Info()
		if err != nil {
			continue
		}

		nodes = append(nodes, FileNode{
			Name:         entry.Name(),
			IsDir:        entry.IsDir(),
			Size:         info.Size(),
			ModifiedTime: info.ModTime().Format(time.RFC3339),
		})
	}

	return nodes, nil
}

// Tree returns a hierarchical representation of the filesystem starting at the specified path.
func Tree(info *Info, relPath string, maxDepth int, showHidden bool) (*FileNode, error) {
	absPath, err := resolvePath(info, relPath)
	if err != nil {
		return nil, err
	}

	fileInfo, err := os.Stat(absPath)
	if err != nil {
		return nil, err
	}

	return buildTree(absPath, fileInfo, 0, maxDepth, showHidden)
}

func buildTree(absPath string, info os.FileInfo, currentDepth, maxDepth int, showHidden bool) (*FileNode, error) {
	node := &FileNode{
		Name:         info.Name(),
		IsDir:        info.IsDir(),
		Size:         info.Size(),
		ModifiedTime: info.ModTime().Format(time.RFC3339),
	}

	if !info.IsDir() || currentDepth >= maxDepth {
		return node, nil
	}

	entries, err := os.ReadDir(absPath)
	if err != nil {
		return node, nil // Best effort, ignore read errors for subdirs
	}

	for _, entry := range entries {
		if !showHidden && strings.HasPrefix(entry.Name(), ".") {
			continue
		}

		subInfo, err := entry.Info()
		if err != nil {
			continue
		}

		childNode, err := buildTree(filepath.Join(absPath, entry.Name()), subInfo, currentDepth+1, maxDepth, showHidden)
		if err == nil && childNode != nil {
			node.Children = append(node.Children, childNode)
		}
	}

	return node, nil
}
