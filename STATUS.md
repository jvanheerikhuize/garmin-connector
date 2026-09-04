# Feature Status & Playbook Matrix (`STATUS.md`)

This document is the **single source of truth** for feature maturity, testing status, and verification playbooks for `garmin-venu-x1`.

---

## 1. Feature Readiness Matrix

| Feature | Interface | Status | Last Verified | Notes / Blockers |
| :--- | :--- | :--- | :--- | :--- |
| **GPX Parsing & Telemetry** | CLI / Core | 🟢 **Verified** | 2026-09-04 | Tested with NodeMapp & Outdooractive GPX tracks |
| **FIT Course Binary Encoding** | CLI / Core | 🟢 **Verified** | 2026-09-04 | FIT 2.0 header, CRC-16, CoursePoint packing validated |
| **DEM Elevation Auto-Enrichment** | CLI / Core / GUI | 🟢 **Verified** | 2026-09-04 | Auto-enriches 0.0m flat GPX files via Open-Elevation DEM |
| **Interactive GPS Map** | GUI | 🟢 **Verified** | 2026-09-04 | 4 free basemaps (OSM, Topo, CyclOSM, Satellite) without API keys |
| **Vector SVG Elevation Profile** | GUI | 🟢 **Verified** | 2026-09-04 | Dynamic SVG graph with interactive crosshair hover sync |
| **Hardware USB Detection** | CLI / GUI | 🟢 **Verified** | 2026-09-04 | Identifies Garmin Vendor ID (`091e:0003` & `091e:51fb`) |
| **MTP / Storage Sideloading** | CLI / GUI | 🟡 **In Testing** | — | Focus of Playbook #1 (Testing storage unlock & byte transfer) |
| **On-Watch Course Manager (List/Delete)** | CLI / GUI | 🟡 **In Testing** | — | Focus of Playbook #2 (Scanning `/GARMIN/Courses` & `/NewFiles`) |
| **Folder Auto-Sideload Watcher** | CLI / GUI | 🟡 **In Testing** | — | Focus of Playbook #3 (Auto-detecting exports from RouteMaker) |
| **Garmin Connect Cloud Sync** | CLI / Core | ⚪ **Planned** | — | Optional wireless phone sync via Garmin API |

---

## 2. The Playbook Protocol (How We Test)

When testing or building any feature, we follow this 4-step loop:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Agent provides a targeted Test Playbook                  │
│    (Objective, Prerequisites, Step-by-Step, Expected Result)│
├─────────────────────────────────────────────────────────────┤
│ 2. User executes the playbook & shares findings             │
├─────────────────────────────────────────────────────────────┤
│ 3. Agent diagnoses any failures & fixes root cause          │
├─────────────────────────────────────────────────────────────┤
│ 4. Update STATUS.md to 🟢 Verified and pick next feature    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Active Playbooks

### Playbook #1: Watch Storage Unlock & Route Sideloading
- **Objective**: Verify that a route can be converted and successfully written to the watch's `/GARMIN/NewFiles/` directory.
- **Prerequisites**:
  - Garmin Venu X1 plugged in via USB.
  - Watch in MTP / Mass Storage mode (Screen prompt accepted).
- **Test Steps**:
  1. Open GUI at `http://127.0.0.1:8081` and check status pill (`● Venu X1 Connected`).
  2. Drop `~/Desktop/ovelo-unterwegs-im-oberen-ourtal.gpx` into the GUI.
  3. Verify map and elevation profile render.
  4. Click **"Sideload to Watch"**.
  5. Check watch: Safely unplug USB cable and wait ~5 seconds.
  6. On the watch, navigate to **Navigation / Courses** (or **Activities &rarr; Bike/Hike &rarr; Options &rarr; Courses**).
- **Pass Criteria**: The route "ovelo---unterwe" appears in the watch's course list with accurate distance and elevation.
- **Fail Criteria**: Error popup in GUI or file not appearing in watch's course list.
- **Findings**: *(To be filled by User)*

---

### Playbook #2: On-Watch Course List & Deletion
- **Objective**: Verify that courses stored on the watch can be listed, inspected, and deleted from the GUI.
- **Prerequisites**: At least one course installed on the watch.
- **Test Steps**:
  1. In the GUI, look at the **"Courses on Watch"** table.
  2. Click **"Refresh"**.
  3. Verify the uploaded `.fit` course appears with its file size.
  4. Click the red **"Delete"** button next to a course.
  5. Confirm deletion prompt.
- **Pass Criteria**: Course disappears from table and is removed from the watch storage.
- **Findings**: *(To be filled by User)*

---

### Playbook #3: Zero-Touch RouteMaker Auto-Sideload
- **Objective**: Verify that exporting a GPX from RouteMaker automatically pushes to the watch without manual file dragging.
- **Prerequisites**: Watch connected, Watcher toggle switch active in GUI.
- **Test Steps**:
  1. In GUI, enable the **"Auto-Sideload Folder Watcher"** toggle.
  2. Verify watch directory is set to `/home/jerry/Downloads`.
  3. Export any new route from RouteMaker (`~/Repos/routemaker`).
  4. Check the GUI's **Live Activity Log** console.
- **Pass Criteria**: Log displays `Auto-sideloaded: <file.gpx> -> <file.fit>` and file lands on watch.
- **Findings**: *(To be filled by User)*
