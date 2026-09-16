package device

import (
	"os"
	"path/filepath"
	"testing"
)

func TestListDirAndTree(t *testing.T) {
	tempDir := t.TempDir()

	// Setup mock watch filesystem
	watchRoot := filepath.Join(tempDir, "Internal Storage")
	garminDir := filepath.Join(watchRoot, "GARMIN")
	activityDir := filepath.Join(garminDir, "Activity")
	hiddenDir := filepath.Join(watchRoot, ".xdg-volume-info")

	os.MkdirAll(activityDir, 0755)
	os.MkdirAll(hiddenDir, 0755)

	os.WriteFile(filepath.Join(activityDir, "12345.fit"), []byte("data"), 0644)
	os.WriteFile(filepath.Join(garminDir, "GarminDevice.xml"), []byte("<xml>"), 0644)
	os.WriteFile(filepath.Join(hiddenDir, "data.txt"), []byte("hidden"), 0644)
	os.WriteFile(filepath.Join(watchRoot, ".hiddenfile"), []byte("hide"), 0644)

	info := &Info{
		MountPath: tempDir, // Candidate path
	}

	t.Run("resolvePath resolves correctly", func(t *testing.T) {
		p, err := resolvePath(info, "GARMIN")
		if err != nil {
			t.Fatal(err)
		}
		if p != garminDir {
			t.Errorf("Expected %s, got %s", garminDir, p)
		}

		pCase, err := resolvePath(info, "garmin/activity")
		if err != nil {
			t.Fatal(err)
		}
		if pCase != activityDir {
			t.Errorf("Expected %s, got %s", activityDir, pCase)
		}
	})

	t.Run("ListDir at root without hidden", func(t *testing.T) {
		nodes, err := ListDir(info, "", false)
		if err != nil {
			t.Fatal(err)
		}

		if len(nodes) != 1 {
			t.Errorf("Expected 1 node, got %d", len(nodes))
		}
		if nodes[0].Name != "GARMIN" {
			t.Errorf("Expected GARMIN, got %s", nodes[0].Name)
		}
	})

	t.Run("ListDir at root with hidden", func(t *testing.T) {
		nodes, err := ListDir(info, "", true)
		if err != nil {
			t.Fatal(err)
		}

		if len(nodes) != 3 {
			t.Errorf("Expected 3 nodes, got %d", len(nodes))
		}
	})

	t.Run("Tree limits depth and filters hidden", func(t *testing.T) {
		tree, err := Tree(info, "", 1, false)
		if err != nil {
			t.Fatal(err)
		}

		// Root is Internal Storage, child is GARMIN. 
		// If max depth is 1, GARMIN shouldn't have children loaded.
		if len(tree.Children) != 1 || tree.Children[0].Name != "GARMIN" {
			t.Errorf("Expected 1 child (GARMIN), got %v", len(tree.Children))
		}
		if len(tree.Children[0].Children) != 0 {
			t.Errorf("Expected 0 grandchildren due to max depth, got %v", len(tree.Children[0].Children))
		}
	})

	t.Run("Tree goes deeper", func(t *testing.T) {
		tree, err := Tree(info, "", 3, false)
		if err != nil {
			t.Fatal(err)
		}

		garminNode := tree.Children[0]
		if len(garminNode.Children) != 2 {
			t.Errorf("Expected GARMIN to have 2 children (Activity, GarminDevice.xml), got %d", len(garminNode.Children))
		}
	})
}
