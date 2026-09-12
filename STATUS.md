# Garmin Connector MVP Status (`STATUS.md`)

## MVP Features

| Feature | Status | Notes |
| :--- | :--- | :--- |
| **Watch Connection Status (GUI)** | 🟢 Verified | Detects MTP & Mass Storage via detector.py. |
| **GPX Upload & Sideload** | 🟢 Verified | Converts to FIT and pushes to `/GARMIN/NEWFILES`. |
| **Course Manager (List/Delete)** | 🟢 Verified | Reads directly from watch storage. |
| **Map Preview from Watch** | 🟢 Verified | Parses GPX from watch storage directly into Leaflet map. |

## Stripped Features (Removed for Lean MVP)
- Elevation auto-enrichment (`elevation.py`)
- Directory Watcher / Auto-sideload (`watcher.py`)
- CLI command lab / terminal UI
- Cloud Sync (`garminconnect`)
- Advanced diagnostics / self-test
