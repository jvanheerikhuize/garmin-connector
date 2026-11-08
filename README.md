# garmin-connector

Connect a modern Garmin watch to a Linux laptop and exchange files with it over USB (MTP), either from the command line or from a local web dashboard.

## Features

- **Folder & file insight.** The web file browser explains what each watch folder is for — from the watch's own `GarminDevice.xml` declarations and a curated catalog that says whether each purpose is documented, observed on a real watch, or only likely — and summarises the selected file: FIT type, creator, checksum, activity session (sport, duration, distance, heart rate), course/workout names, GPX names and waypoints (and what the watch will do with them on import), text excerpts and images.
- **Device discovery.** Finds a connected watch under GVFS MTP mounts (`/run/user/<uid>/gvfs/mtp:*`), `/media` and `/mnt` without any mount configuration. It looks for a `GARMIN` folder up to two levels deep, so `Internal Storage/GARMIN` is found too. If GVFS kept a dead mount after you unplugged and replugged the watch, it remounts it automatically (at most once every 30 s).
- **Status and diagnostics.** Model, unit ID, software version, part number, storage capacity, sub-component firmware (GPS, wireless, sensor hub) and installed Connect IQ apps, all read from `GARMIN/GarminDevice.xml`.
- **Read-only browsing.** `ls` and `tree`, with case-insensitive paths and depth-limited traversal so slow MTP mounts stay responsive.
- **Filesystem manipulation.** `mkdir`, `rm`, `touch` and `put` work anywhere on the watch. When the MTP mount rejects a direct write, they fall back to the GVFS client tool (`gio`).
- **Course upload.** `upload` copies `.fit` / `.gpx` files into `GARMIN/NewFiles/`, and the watch imports them when you unplug the cable.
- **Web GUI.** An on-demand local dashboard with:
  - a Finder-style column file browser (download, delete, new folder or file, drag-and-drop upload)
  - drag-and-drop course upload
  - an offline route map and elevation profile for `.gpx` courses

Every inspection command exits `0` and reports "no device" when no watch is connected. Every mutation exits `1` in that case, so scripts never mistake a no-op for success. The tool ships as a single binary with no runtime dependencies.

## Requirements

- Linux, with the watch mounted over MTP by your desktop (GVFS). Other volume managers mounting under `/media` or `/mnt` also work.
- To write to MTP mounts: the GLib/GIO client tool `gio` and the GVFS MTP backend (`gvfsd-mtp`). Both ship with standard GNOME-based desktops.
- To build: Go 1.22 or newer. There are no third-party dependencies.

## Build and install

> This repository is spec-driven. [`specs/`](specs/) is the source of truth, and the code under `cmd/` and `internal/` is generated from it (see [`specs/workflows/regeneration.md`](specs/workflows/regeneration.md)). Regenerate the code before building if it is not present.

```sh
go build -o garmin-connector ./cmd/garmin-connector   # build
go install ./cmd/garmin-connector                     # install for the current user
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
  mkdir    Create a directory on the watch
  rm       Remove a file or directory on the watch
  touch    Create an empty file or update timestamp
  put      Copy a local file to the watch
```

Every command accepts `-h`/`--help`. Flags may come before or after the arguments, and `--` ends flag parsing, e.g. `rm -- -notes.txt`. `garmin-connector --version` prints `1.0.0`.

### Inspecting the watch

```sh
garmin-connector status                 # human-readable connection summary
garmin-connector status --json          # {"connected": true, "device": {...}}
garmin-connector info                   # storage, firmware components, Connect IQ apps
garmin-connector info --json
garmin-connector ls                     # storage root (the folder that contains GARMIN)
garmin-connector ls garmin/activity -a  # case-insensitive; -a shows dot-files
garmin-connector tree GARMIN --depth 2  # default depth is 3
garmin-connector tree --json
```

Watch paths are relative to the storage root. A leading `/` is allowed. `..` can never climb above the root.

### Uploading courses

```sh
garmin-connector upload ~/Downloads/alpine-loop.gpx
```

The file lands in `GARMIN/NewFiles/` under its original name, replacing any file with the same name. The watch converts it into a course after you disconnect USB. For `.gpx` files, the watch names the course after the `<name>` element inside the file, not after the file name. Top-level `<wpt>` waypoints become saved locations.

### Changing files

```sh
garmin-connector mkdir -p GARMIN/Custom/Plans
garmin-connector touch GARMIN/Custom/marker.txt
garmin-connector put workout.fit GARMIN/Workouts          # into a folder, keeping the name
garmin-connector put local.fit GARMIN/Workouts/renamed.fit
garmin-connector rm GARMIN/NewFiles/old_route.gpx
garmin-connector rm -r GARMIN/Custom                       # directories need -r
garmin-connector rm -f GARMIN/maybe-missing.txt            # no error if missing
```

All four commands accept `--json`. Changes are immediate: there is no trash and no undo. Neither the storage root nor the top-level `GARMIN` folder can be removed.

### Web GUI

```sh
garmin-connector web                    # serves http://127.0.0.1:8080/ and opens your browser
garmin-connector web --port 9000 --no-browser
```

The page has three tabs:

- **Dashboard:** live status, polled every 5 seconds.
- **File Browser:** arrow keys and Enter navigate. Selecting a file shows its details, a text preview for small text or XML files, and a route preview for `.gpx`.
- **Upload Course:** drag-and-drop course upload.

Press Ctrl+C to stop the server.

The server binds to loopback by default. It only acts on requests from its own page: requests with a foreign `Host` or `Origin` are refused with `403`, and state-changing requests with an unexpected `Content-Type` are refused with `415`. This means other websites open in the same browser cannot reach the watch. `--host` can bind to another address, but the API has no authentication, and the tool prints a warning when you do this.

## Troubleshooting

- **`no Garmin device detected`:** unlock the watch and check that your file manager shows it. Discovery only needs a readable `GARMIN` folder on a mounted volume.
- **Writes fail with "Operation not supported":** GVFS MTP mounts do not accept direct file creation, so the tool falls back to `gio copy` / `gio mkdir` / `gio remove`. Sandboxed launchers (snap, flatpak) often export a broken `GIO_MODULE_DIR`. The tool detects this and points `gio` at the host module directory (for example `/usr/lib/x86_64-linux-gnu/gio/modules`). If writes still fail, check that `gio` and the GVFS MTP backend are installed.
- **Deleting large folders is slow:** MTP cannot delete a non-empty folder in one step, so every file is removed first.

## Development

```sh
go test ./...                 # unit tests
go vet ./... && gofmt -l .    # static checks; gofmt must print nothing
```

The behaviour, data contracts and requirements live in [`specs/`](specs/README.md). Change the spec first, then regenerate or update the code.

## License

Custom Non-Commercial & Evaluation License; see [LICENSE](LICENSE). Commercial use requires permission.
