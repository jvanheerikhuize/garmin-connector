# garmin-connector

A standalone Linux CLI tool and local Web GUI to connect modern Garmin watches to exchange files, inspect storage and diagnostics, explore internal filesystems, and upload routes over USB.

## Overview

Modern Garmin watches (such as the Venu, Forerunner, and Fenix series) use the Media Transfer Protocol (MTP) rather than USB Mass Storage when connected to a computer. On Linux, MTP devices are dynamically mounted by Desktop Environments (such as GVFS under `/run/user/<uid>/gvfs`).

`garmin-connector` provides:
- **Automatic Device Discovery**: Detects connected Garmin watches across Linux mount points (`/run/user/*/gvfs/*`, `/media/*/*`, `/mnt/*`) and parses `GarminDevice.xml`.
- **Status & Diagnostics**: Reports device connection, firmware versions, hardware subsystems (GPS, BLE/ANT wireless, sensor hub), and installed Connect IQ apps.
- **Filesystem Inspection**: Flat directory listing (`ls`) and recursive visual hierarchy (`tree`) with depth limiting, human-friendly units, and structured JSON output.
- **Course & Workout Upload**: Transfers route and course files (`.fit`, `.gpx`) directly to the watch's incoming directory (`GARMIN/NewFiles/`), with automatic GVFS D-Bus fallback.
- **Embedded Web GUI**: An on-demand local web server (`garmin-connector web`) serving a modern responsive dashboard, macOS Finder-style Miller columns file browser with file downloading, course route vector map and elevation profile preview, and drag-and-drop course upload. Zero external frontend dependencies or CDNs required.

## Installation & Build

Requires Go 1.22+. Uses only the Go standard library with zero third-party dependencies.

```bash
# Build standalone binary
go build -o garmin-connector ./cmd/garmin-connector

# Install to $GOPATH/bin
go install ./cmd/garmin-connector
```

## CLI Usage

```
garmin-connector [command] [flags]
```

### Commands

#### `status`
Check device connection status and basic metadata:
```bash
garmin-connector status
garmin-connector status --json
```

#### `info`
Display detailed device diagnostics, filesystem storage capacity metrics, hardware subsystem firmware, and installed Connect IQ apps:
```bash
garmin-connector info
garmin-connector info --json
```

#### `ls`
List files and directories on the watch (relative to the internal storage root):
```bash
garmin-connector ls
garmin-connector ls GARMIN/Activity
garmin-connector ls -a --json
```

#### `tree`
Display directory structure recursively as a visual tree with depth limits:
```bash
garmin-connector tree
garmin-connector tree GARMIN --depth 2
garmin-connector tree --json
```

#### `upload`
Upload a route or workout file (`.fit` or `.gpx`) to the watch's `GARMIN/NewFiles` directory:
```bash
garmin-connector upload /path/to/route.gpx
```

#### `web`
Launch the local web GUI dashboard and file browser:
```bash
garmin-connector web
garmin-connector web --host 127.0.0.1 --port 8080 --no-browser
```

## Web GUI Features

- **Dashboard**: Real-time connection indicator, storage capacity bar, subsystem firmware versions, and Connect IQ inventory with automatic 5-second polling.
- **Miller Columns File Browser**: macOS Finder-style multi-column lazy directory navigation, file inspector, syntax preview for XML/logs, and one-click file download.
- **Route & Elevation Preview**: Offline 2D vector route map projection and interactive elevation profile chart with hover scrubber for `.gpx` courses.
- **Course Upload**: Drag-and-drop and file-picker interface to stage and upload courses directly to the watch.

## Specifications

The development and behavior of this project are strictly driven by specifications maintained in the [`specs/`](specs/) directory:
- [Constitution](specs/constitution.md)
- [Current Tech Stack](specs/tech-stack.md)
- [Device Discovery Spec](specs/core/device-discovery.md)
- [CLI Entrypoint & Status Spec](specs/cli/cli-entrypoint.md)
- [Device Info Spec](specs/cli/device-info.md)
- [File Browser Spec](specs/cli/file-browser.md)
- [Course Upload Spec](specs/cli/course-upload.md)
- [Web GUI Dashboard Spec](specs/gui/dashboard.md)
- [Web GUI File Browser Spec](specs/gui/file-browser.md)
- [Web GUI Course Upload Spec](specs/gui/course-upload.md)
- [Web GUI Course Preview Spec](specs/gui/course-preview.md)

## License

MIT License. See [LICENSE](LICENSE) for details.
