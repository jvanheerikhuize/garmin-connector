# garmin-connector

A tool to connect a modern Garmin watch to a Linux laptop and exchange files over USB (MTP) — from the command line or a local web dashboard.

## Features

- **Device discovery** — automatically finds a connected Garmin watch across `/run/user/<uid>/gvfs`, `/media`, and `/mnt`, without manual mount configuration.
- **Status & diagnostics** — connection status, storage capacity, installed Connect IQ apps, and sub-component firmware versions.
- **Read-only filesystem browser** — `ls` and `tree` for exploring the watch's internal storage from the CLI.
- **Course upload** — transfer `.fit`/`.gpx` route files to the watch's `GARMIN/NewFiles/` directory.
- **Web GUI** — an on-demand local dashboard with a Finder-style column-view file browser, drag-and-drop course upload, and an offline vector route/elevation preview.

Everything runs on-demand, exits cleanly when no watch is connected, and ships as a single dependency-free binary.

## Install

Requires Go 1.22+.

```sh
go build -o garmin-connector ./cmd/garmin-connector
# or
go install ./cmd/garmin-connector
```

## Usage

```
garmin-connector <command> [flags]

Commands:
  status   Show connection status of a Garmin watch
  info     Show detailed device diagnostics
  ls       List files on the watch
  tree     Recursively list files on the watch
  upload   Upload a course file to the watch
  web      Launch the web GUI dashboard
```

### Examples

```sh
garmin-connector status                 # human-readable connection status
garmin-connector status --json          # machine-readable status
garmin-connector info --json            # storage, Connect IQ apps, firmware versions
garmin-connector ls GARMIN/Activity      # list a directory
garmin-connector tree --depth 2          # recursive listing
garmin-connector upload route.gpx        # copy a course to GARMIN/NewFiles/
garmin-connector web                     # launch the dashboard at http://127.0.0.1:8080/
```

Every command exits `0` when no watch is connected (a disconnected watch is a valid state, not an error) and supports `--help`.

## Web GUI

`garmin-connector web` starts a local HTTP server (default `127.0.0.1:8080`) and opens it in your default browser. It provides:

- A **Dashboard** with live connection status, storage gauge, firmware versions, and Connect IQ inventory (auto-refreshing).
- A **File Browser** with macOS Finder-style Miller columns, keyboard navigation, and file download.
- An **Upload Course** view with drag-and-drop, extension validation, and an offline route/elevation preview before transfer.

All frontend assets are embedded in the binary; nothing is fetched from the network.

## Development

```sh
go build ./...     # build
go test ./...       # run tests
go vet ./...        # static checks
gofmt -l .           # formatting check (should print nothing)
```

## Design

This repository is developed spec-first: behavior lives under [`specs/`](specs/) and the code in `cmd/`/`internal/` is a generated, derived artifact of those specs. See [`specs/README.md`](specs/README.md) for the working agreement and [`specs/constitution.md`](specs/constitution.md) for the system's purpose, grounding facts/assumptions, and requirements.

## Assumptions Needing Verification (Help Promote Them to Facts!)

In this spec-driven project, system behavior is grounded in **External Facts** (empirically verified hardware, OS, and protocol truths) and **Assumptions** (design choices or observations awaiting broader verification).

We welcome testing across different **Garmin models** (Fenix, Forerunner, Edge, Instinct, Epix, Venu) and **Linux distributions** (Ubuntu, Fedora, Arch, Debian, openSUSE, minimal WMs) to verify these assumptions and promote them into permanent facts in the [Constitution](specs/constitution.md).

### 1. `ASM-13`: GVFS Tooling & Backend Availability Across Linux Distributions
- **Current Assumption:** Linux desktop systems mounting Garmin watches over MTP have GLib/GIO CLI tooling (`gio`) and the `gvfsd-mtp` D-Bus daemon installed out-of-the-box.
- **Open Question:** Does file transfer succeed out-of-the-box on minimal window managers (i3, sway), pure KDE Plasma, or minimal Arch installations, or does it require installing packages like `gvfs-backends`?
- **Route to Verify:**
  ```sh
  # Check if GIO tooling and GVFS backend module exist on your distro:
  which gio
  find /usr/lib* -name "libgvfsdbus.so" 2>/dev/null

  # Test transferring a course to the watch:
  garmin-connector upload /path/to/test.gpx
  ```
- **How to Report:** If `gio` is missing or fails, share your distro, desktop environment, and any package installation requirements.

### 2. `ASM-6`: MTP Traversal Latency Across Watch Models & Storage Sizes
- **Current Assumption:** Restricting recursive traversal depth (default `--depth 3`) keeps commands responsive under 1 second and prevents MTP hanging.
- **Open Question:** How does traversal time scale on watches with large storage capacities (e.g. 32GB/64GB on Fenix/Forerunner models with worldwide topographic maps)? Does `--depth 3` stay fast, or does it slow down significantly?
- **Route to Verify:**
  ```sh
  time garmin-connector tree --depth 3
  time garmin-connector tree --depth 5
  ```
- **How to Report:** Share your watch model, firmware version, total storage size, and the `time` output.

### 3. `ASM-7`: Watch Handling of Malformed Course Files
- **Current Assumption:** Restricting uploads by file extension (`.fit`, `.gpx`) is sufficient, and deep file schema validation in the client is unnecessary because Garmin watch firmware safely handles/rejects corrupted files upon USB disconnect.
- **Open Question:** What does your specific watch model do when an invalid or truncated GPX/FIT file is placed into `GARMIN/NewFiles/`? Does it silently delete it, log an error in `GARMIN/Debug/`, or does it cause a reboot?
- **Route to Verify:**
  ```sh
  # Stage an invalid file:
  echo "not a valid xml file" > /tmp/corrupt.gpx
  garmin-connector upload /tmp/corrupt.gpx

  # Disconnect watch from USB safely, wait for watch to return to watchface, then reconnect:
  garmin-connector ls GARMIN/NewFiles/
  garmin-connector ls GARMIN/Debug/ 2>/dev/null
  ```
- **How to Report:** Note whether the watch processed, discarded, or retained the invalid file, and whether any error log was written.

### 4. `ASM-3`: Multi-Device Connection Behavior
- **Current Assumption:** Users typically connect only one Garmin device at a time, and surfacing the first detected device mount is sufficient.
- **Open Question:** If you connect both a Garmin watch and a Garmin bike computer (e.g. Edge), or two watches simultaneously, which device is selected, and does it cause race conditions or mount conflicts?
- **Route to Verify:**
  ```sh
  # Connect two Garmin devices via USB:
  garmin-connector status --json
  ls -ld /run/user/$(id -u)/gvfs/mtp* /media/$USER/* 2>/dev/null
  ```
- **How to Report:** Share the JSON status output and whether both devices are recognized in your mount directory.

### 5. `ASM-14`: Non-Empty Directory Deletion Performance Over MTP
- **Current Assumption:** Because MTP lacks atomic directory removal (`FCT-21`), leaf-first recursive item deletion introduces latency but succeeds reliably without timeouts.
- **Open Question:** On large directories with many nested items (e.g. 20+ files), does sequential deletion take noticeable time or encounter MTP bus timeouts on your device?
- **Route to Verify:**
  ```sh
  # Create a test folder with multiple files on the watch:
  garmin-connector mkdir test-deletion
  garmin-connector touch test-deletion/file1.txt
  garmin-connector touch test-deletion/file2.txt
  time garmin-connector rm -r test-deletion
  ```
- **How to Report:** Share your watch model, number of deleted items, and total deletion time.

---

### How to Promote an Assumption to a Fact

When you have tested an assumption on your setup:
1. Follow the [Validate an Assumption Workflow](specs/workflows/validate-assumption.md).
2. Open an Issue or Pull Request on GitHub with:
   - **Hardware**: Watch Model, Firmware Version.
   - **Environment**: Linux Distribution, Desktop Environment / Window Manager.
   - **Evidence**: Command outputs, timing benchmarks, or log snippets.
3. In a PR, move the assumption from the **Assumptions table** to the **External Facts table** (`FCT-X`) in [`specs/constitution.md`](specs/constitution.md), documenting the *Verification Method* and observations. Once reviewed, your findings become permanent constitutional facts!


## License

This project is licensed under a **Custom Non-Commercial & Evaluation License** — see the [LICENSE](LICENSE) file for details.

- **Free for Testing & Non-Commercial Use:** You are free to test, evaluate, study, develop, and use this tool for personal and non-commercial purposes.
- **Commercial Use:** Any commercial use, distribution, or integration requires prior written permission from Jerry van Heerikhuize (<jvanheerikhuize@gmail.com>).

