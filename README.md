# Garmin Connector (`garmin-venu-x1`)

A lightweight, high-performance tool and Python library to **sideload, convert, and manage hiking and cycling routes (GPX & FIT)** directly on Garmin watches (such as Garmin Venu, Venu Sq, Venu 2/3, Forerunner, Fenix, and Edge devices).

---

## Key Features

- 🔄 **Built-in Pure Python FIT Course Encoder**: Converts any standard `.gpx` track or route into binary Garmin `.fit` course format with timestamps, elevation profiles, distance calculations, and turn-by-turn/waypoint cues. Zero heavy dependencies required.
- 🔌 **Auto-Discovery on Linux**: Automatically detects your connected Garmin watch across USB Mass Storage (`/media/*`, `/mnt/*`) and GNOME/GVFS MTP mounts (`/run/user/$UID/gvfs/mtp:*`).
- ⚡ **Direct Sideloading**: Drops converted `.fit` or `.gpx` files directly into `/GARMIN/NEWFILES/`, allowing the Garmin OS to ingest and process the course upon unplugging.
- 📋 **Course Management**: List, inspect, delete, and back up courses and activities from your watch.
- 👁️ **Folder Watcher**: Monitor an export folder (e.g., your route maker download directory) to automatically sideload routes whenever your watch is plugged in.
- 🌐 **REST API Server**: Run a lightweight local HTTP API so web-based route planners (such as [routemaker](https://github.com/jvanheerikhuize/routemaker)) can push routes directly to your watch with a single click.

---

## Architecture & How Garmin File Ingestion Works

```
┌───────────────────────────────┐
│   Route Creator / GPX / FIT   │
└──────────────┬────────────────┘
               │
               ▼
┌───────────────────────────────┐
│       garmin-connector        │
│ ┌───────────────────────────┐ │
│ │ GPX Parser & FIT Encoder  │ │ ──> Pure-Python FIT Course Encoder
│ └───────────────────────────┘ │
│ ┌───────────────────────────┐ │
│ │  MTP / USB Auto-Detector  │ │ ──> Detects /run/user/1000/gvfs/mtp:* or /media/*
│ └───────────────────────────┘ │
└──────────────┬────────────────┘
               │ Copies to
               ▼
┌───────────────────────────────┐
│         Garmin Watch          │
│   /GARMIN/NEWFILES/<name>.fit │ ──> Ingested on disconnect & converted to /GARMIN/COURSES/
└───────────────────────────────┘
```

1. When a `.fit` or `.gpx` course is placed in `/GARMIN/NEWFILES/`, the watch's firmware parses the file upon USB disconnection or reboot.
2. The watch validates the FIT course structure, creates the internal navigation track, and moves it to `/GARMIN/COURSES/`.

---

## Installation

Clone the repository and install with pip:

```bash
cd ~/Repos/garmin-venu-x1

# Basic installation (CLI + GPX & FIT converter + Watcher)
pip install -e .

# Full installation (including REST API server & test dependencies)
pip install -e ".[all]"
```

---

## Quick Start / CLI Usage

### 1. Detect Connected Watch
Scan for USB/MTP mounted Garmin watches:
```bash
garmin-connector detect
```

### 2. Sideload a Route (GPX or FIT)
Convert (if GPX) and sideload a route directly into `/GARMIN/NEWFILES`:
```bash
# Cycling route
garmin-connector push my_gravel_route.gpx --sport cycling

# Hiking route with a custom course name
garmin-connector push alpine_hike.gpx --sport hiking --name "Alpine Loop"
```

### 3. List Installed Courses
List all courses currently stored in `/GARMIN/COURSES/` or staged in `/GARMIN/NEWFILES/`:
```bash
garmin-connector list
```

### 4. Standalone GPX to FIT Conversion
Convert a GPX file into a binary Garmin FIT Course file locally without needing the watch connected:
```bash
garmin-connector convert route.gpx -o route.fit --sport cycling
```

### 5. Remove or Back Up Courses
```bash
# Delete a course by filename
garmin-connector delete alpine_loop.fit

# Back up all courses to a local directory
garmin-connector backup --dest ~/MyRouteBackups
```

### 6. Auto-Sideload Folder Watcher
Monitor a directory (such as your browser's download folder or route maker export directory) to auto-sideload newly exported routes:
```bash
garmin-connector watch ~/Downloads --sport cycling
```

### 7. Run Local REST API Service
Start the local REST API server:
```bash
garmin-connector serve --port 8080
```
Then POST GPX/FIT files directly from external apps:
```bash
curl -X POST "http://localhost:8080/api/upload" \
  -F "file=@my_route.gpx" \
  -F "sport=cycling"
```

---

## Python API Usage

You can also import `garmin_connector` into your Python scripts or route creation applications:

```python
from garmin_connector.converter import convert_gpx_to_fit, Sport
from garmin_connector.device import GarminDeviceManager

# 1. Convert GPX to FIT course
fit_path, course_data = convert_gpx_to_fit(
    gpx_path="route.gpx",
    output_fit_path="route.fit",
    course_name="Mountain Loop",
    sport=Sport.HIKING,
)
print(f"Total distance: {course_data.total_distance / 1000:.2f} km")
print(f"Elevation gain: {course_data.total_ascent:.0f} m")

# 2. Sideload directly to connected Garmin watch
manager = GarminDeviceManager()
dest = manager.sideload_route("route.gpx", sport=Sport.HIKING)
print(f"Sideloaded to: {dest}")
```

---

## Supported Garmin Models

Compatible with all Garmin devices supporting FIT courses and standard Garmin filesystem layout:
- **Venu Series**: Venu, Venu Sq / Sq 2, Venu 2 / 2 Plus, Venu 3 / 3S
- **Forerunner Series**: 55, 165, 245, 255, 265, 745, 945, 955, 965
- **Fenix / Epix Series**: Fenix 5/6/7/8, Epix Gen 2, Enduro
- **Edge Series**: Edge 130, 530, 830, 1030, 540, 840, 1040, Explore

---

## Running Tests

Run the test suite with Python's built-in test runner:
```bash
python3 -m unittest discover -s tests
```
