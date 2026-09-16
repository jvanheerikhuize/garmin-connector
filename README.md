# garmin-connector

A small Linux command-line tool that finds a Garmin watch connected over USB (MTP) and lets you inspect it: connection status, device metadata, storage usage, installed Connect IQ apps, component firmware versions, and the watch's filesystem. Everything is read-only.

```
$ garmin-connector status
Device found: Venu X1 (ID: 3617019779)
  Software version: 1829
  Part number:      006-B4603-00
  Mount path:       /run/user/1000/gvfs/mtp:host=091e_51fb_0000d7975783
```

## Why

Modern Garmin watches (e.g. the Venu X1) only speak MTP over USB — no USB mass storage. On Linux the desktop mounts them through GVFS under `/run/user/<uid>/gvfs/mtp:host=...`, hiding the familiar `GARMIN` folder behind an `Internal Storage/` volume. `garmin-connector` does the path-hunting for you and exposes the result as plain text or JSON so scripts can consume it.

## Install

Requires Go 1.22 or newer to build; the resulting binary is static and has no runtime dependencies.

```sh
go install github.com/jvanheerikhuize/garmin-connector/cmd/garmin-connector@latest
# or, from a checkout:
go build -o garmin-connector ./cmd/garmin-connector
```

## Usage

```
garmin-connector <command> [flags]
garmin-connector --help
garmin-connector --version        # prints 1.0.0
```

Every command accepts `--json` for machine-readable output and exits `0` when no watch is connected — "not connected" is a normal state, not an error.

| Command | What it does |
|---|---|
| `status` | Is a watch connected? Model, ID, software version, part number, mount path. |
| `info` | Everything `status` shows plus storage usage, Connect IQ apps and GPS/wireless/sensor-hub firmware versions. |
| `ls [path]` | List one directory of the watch (defaults to the storage root). |
| `tree [path]` | Recursive listing, 3 levels deep by default. |
| `upload <file>` | Upload a course file (`.fit` or `.gpx`) to `GARMIN/NewFiles/`. |

### `status`

```
$ garmin-connector status --json
{
  "connected": true,
  "device": {
    "model": "Venu X1",
    "id": "3617019779",
    "software_version": "1829",
    "part_number": "006-B4603-00",
    "mount_path": "/run/user/1000/gvfs/mtp:host=091e_51fb_0000d7975783"
  }
}
```

With no watch attached: `No Garmin device detected.` or `{"connected": false, "device": null}`.

### `info`

```
$ garmin-connector info
Device found: Venu X1 (ID: 3617019779)
  Software version: 1829
  Part number:      006-B4603-00
  Mount path:       /run/user/1000/gvfs/mtp:host=091e_51fb_0000d7975783

Storage
  Total: 28.9 GB
  Used:  13.7 GB (47.3%)
  Free:  15.2 GB

Components
  GPS:        11.02
  Wireless:   29.27
  Sensor hub: 1.02

Connect IQ (VM 6.0.3, 5/32 apps, 64.0 MB app space)
  NAME              TYPE                        VERSION  FILE          APP ID
  Spotify           audio-content-provider-app  72       G8TI4826.PRG  6eb48a8f-9bd8-4fe0-99e7-28d787c8a711
  ...
```

`info --json` nests `storage`, `connect_iq` and `components` inside `device`, next to the identity fields:

```json
{
  "connected": true,
  "device": {
    "model": "Venu X1",
    "id": "3617019779",
    "software_version": "1829",
    "part_number": "006-B4603-00",
    "mount_path": "/run/user/1000/gvfs/mtp:host=091e_51fb_0000d7975783",
    "storage": {
      "total_bytes": 31058427904,
      "used_bytes": 14691237888,
      "free_bytes": 16367190016,
      "used_percentage": 47.3
    },
    "connect_iq": {
      "vm_version": "6.0.3",
      "max_apps": 32,
      "app_space_bytes": 67108864,
      "apps": [
        {
          "name": "Spotify",
          "type": "audio-content-provider-app",
          "version": "72",
          "app_id": "6eb48a8f-9bd8-4fe0-99e7-28d787c8a711",
          "file_name": "G8TI4826.PRG"
        }
      ]
    },
    "components": {
      "gps": "11.02",
      "wireless": "29.27",
      "sensor_hub": "1.02"
    }
  }
}
```

Sections whose source is missing degrade gracefully: no Connect IQ block means `"apps": []`, an absent firmware record means an empty version string.

### `ls` and `tree`

Paths are relative to the watch's storage root (the folder that contains `GARMIN`) and are matched case-insensitively, so `garmin/activity` works even though the watch reports `GARMIN/Activity`. Entries starting with `.` are hidden unless you pass `-a`/`--all`.

```
$ garmin-connector ls garmin/activity
    9.4 KB  2026-08-29 21:00  2026-08-29-20-58-40.fit
   31.4 KB  2026-08-30 15:40  2026-08-30-15-29-09.fit
   49.4 KB  2026-08-31 12:49  2026-08-31-12-28-08.fit
   76.4 KB  2026-09-11 20:49  2026-09-11-20-12-40.fit
  377.3 KB  2026-09-12 13:24  2026-09-12-10-10-03.fit
       0 B  2023-01-01 00:00  PendingHD/

$ garmin-connector tree garmin/courses --depth 2
GARMIN/Courses
└── Deurnsche_Peel_.fit

0 directories, 1 file
```

| Flag | `ls` | `tree` | Meaning |
|---|---|---|---|
| `-a`, `--all` | ✓ | ✓ | Show hidden entries |
| `--json` | ✓ | ✓ | JSON output (`ls`: array of entries; `tree`: nested object) |
| `--depth N` | | ✓ | Descend at most `N` levels (default `3`, like `tree -L`) |

Each entry carries `name`, `is_dir`, `size_bytes` and `modified_time` (RFC 3339). In `tree --json`, directories that were traversed carry a `children` array (empty if the directory is empty); files and directories beyond `--depth` have no `children` key.

```
$ garmin-connector ls --json garmin/courses
[
  {
    "name": "Deurnsche_Peel_.fit",
    "is_dir": false,
    "size_bytes": 5752,
    "modified_time": "2026-09-13T11:06:56+02:00"
  }
]
```

A path that doesn't exist on the watch prints an error to stderr and exits `1`.

### `upload`

Uploads a `.fit` or `.gpx` course file directly into the watch's incoming `GARMIN/NewFiles/` folder. When the watch is disconnected from USB, it will automatically process the course.

```sh
$ garmin-connector upload my_course.gpx
Course my_course.gpx uploaded successfully.
```

If no watch is connected, the file extension is not `.fit`/`.gpx`, or the local file is unreadable, `garmin-connector upload` prints an error to stderr and exits with a non-zero code.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success, including "no device connected" |
| `1` | A device is connected but the request failed (e.g. unknown path for `ls`/`tree`) |
| `2` | Usage error: unknown command, unknown flag, bad flag value |

## How discovery works

1. Candidate mounts are globbed in order: `/run/user/*/gvfs/*`, `/media/*/*`, `/mnt/*`.
2. A candidate qualifies if it contains a `GARMIN` directory (case-insensitive) either directly or up to two folders down (MTP typically exposes `Internal Storage/GARMIN`).
3. The first match wins — one watch at a time is the supported setup. Unreadable paths (other users' `/run/user/<uid>`, permission errors) are skipped silently.
4. `GARMIN/GarminDevice.xml` is parsed for the model, ID, software version and part number. If the file is missing or malformed the watch is still reported, as `Generic Garmin` with empty metadata.

## Scope

Linux only, read-only, one watch at a time. There is no GUI, no activity/course syncing and no firmware flashing. See [ROADMAP.md](ROADMAP.md) for ideas beyond that.

## Development

This repository is spec-driven: the behaviour above is defined in [`specs/`](specs/README.md), and the Go sources are regenerated from it (see [`specs/workflows/regeneration.md`](specs/workflows/regeneration.md)). Change the spec first, then the code.

```sh
go test ./...                       # unit tests
go vet ./... && gofmt -l .          # static checks
go build ./cmd/garmin-connector     # build
```

## License

[MIT](LICENSE)
