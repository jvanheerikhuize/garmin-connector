---
id: content-insight
title: Folder Purpose & File Content Inspection
namespace: core
status: implemented
owners: [jerry]
depends_on: [device-discovery]
implements_requirements: [FR-13]
relies_on_facts: [FCT-2, FCT-3, FCT-8, FCT-10, FCT-11, FCT-12, FCT-14, FCT-24, FCT-25, FCT-26]
relies_on_assumptions: [ASM-4, ASM-5]
last_updated: 2026-11-08
---

# Folder Purpose & File Content Inspection

`internal/device/insight.go`
`internal/device/fit.go`
`internal/device/xml.go`

Depends on: [Device Discovery](device-discovery.md)

## Constitution Alignment

- **Implements Requirements:** `FR-13` (Web GUI Folder & File Insight — the backend half; the GUI half is in [gui/file-browser.md](../gui/file-browser.md))
- **Relies on Facts:** `FCT-2` (`GarminDevice.xml`), `FCT-3` (storage root / `GARMIN` nesting), `FCT-8` (casing varies), `FCT-11` (MTP metadata limits), `FCT-12` (`NewFiles` import), `FCT-14` (GPX 1.1 schema), `FCT-24` (watch names imported courses from the name inside the GPX; `<wpt>` become Saved Locations), `FCT-25` (data-type declarations in `GarminDevice.xml`), `FCT-26` (FIT file format)
- **Relies on Assumptions:** `ASM-4` (graceful degradation on missing metadata), `ASM-5` (basic metadata is sufficient)

## Purpose

A Garmin watch's storage is a maze of terse folder names (`Adjstmts`, `SCORCRDS`, `MltSport`) and opaque binary files. This module answers two questions for the file browser: *what is this folder for?* and *what is in this file?* — honestly. Every folder purpose says how it is known (documented, observed on a real watch, inferred from the name, or only declared by the watch), and file summaries are decoded from the file itself, never guessed from its name. Nothing here writes to the watch.

## Scope

**In scope:**
- Reading the data-type declarations from `GarminDevice.xml` (`FCT-25`) and grouping them by folder.
- A curated folder catalog (the table below) and the rule that combines it with the declarations.
- Inspecting one file: FIT summary (`FCT-26`), GPX summary (`FCT-14`, `FCT-24`), text excerpt, image/audio classification, and a byte peek for other binaries.

**Out of scope:**
- HTTP endpoints and rendering (see [gui/file-browser.md](../gui/file-browser.md)).
- Full FIT decoding (record streams, laps, developer field values, charts) — only the fields listed below are decoded.
- A CLI surface for inspection.

## Requirements

### Declared data types (FCT-25)
- MUST read the `<MassStorageMode>` → `<DataType>` entries of `GarminDevice.xml`, matching elements by local name regardless of XML namespace (same rule as [device-discovery.md](device-discovery.md)). Each `<DataType>` has a `<Name>` and one or more `<File>` children with `<Location><Path>`, `<Location><FileExtension>` and `<TransferDirection>`.
- MUST group declarations by folder. The folder key is the `<Path>` split on `/` and `\`, empty segments dropped, joined with `/`, and lower-cased (`Garmin/Activity`, `GARMIN/ACTIVITY/` and `garmin/activity` are the same folder; `Music/` is `music`).
- Within one folder, all `<File>` entries with the same `<Name>` MUST merge into one **declared type**: extensions are lower-cased, de-duplicated, kept in document order; the direction is `both` if any entry is `InputOutput` or if both `OutputFromUnit` and `InputToUnit` occur, `to_watch` if only `InputToUnit` occurs, otherwise `from_watch`. Declared types keep the document order of their first occurrence.
- A name of the form `FIT_TYPE_<n>` MUST record `fit_file_type = n`.
- **Label rule** (the human name of a declared type):
  - `FIT_TYPE_<n>` with `n` in the public file-type table below → `<public name> (FIT)`, e.g. `Activity (FIT)`; any other `n` → `Garmin data (FIT type <n>)`.
  - `MEDIA_TRACK` → `Music track`, `MEDIA_PODCAST` → `Podcast episode`, `MEDIA_AUDIOBOOK` → `Audiobook`, `MEDIA_PLAYLIST` → `Playlist`, `FITBinary` → `FIT file`.
  - Otherwise: underscores become spaces, and a space is inserted before an upper-case letter that follows a lower-case letter, or that starts a new capitalised word after a run of capitals (`IQWatchFaces` → `IQ Watch Faces`, `WiFiConfiguration` → `Wi Fi Configuration`, `CycleRoadCourse` → `Cycle Road Course`).
- The parsed declarations SHOULD be cached and re-read only when `GarminDevice.xml`'s path, size or modification time changes, because every folder listing consults them and MTP reads are slow (`FCT-10`).
- A missing or unparsable `GarminDevice.xml` MUST yield no declarations, never an error (`ASM-4`).

### Folder purpose
- A folder's purpose is looked up by its storage-root-relative path, lower-cased and normalised as above (the storage root itself has path `""`).
- If the path is in the **folder catalog**, the purpose's `title`, `description` and `basis` are the catalog's. Otherwise, if the folder has declared types, `title` is the first declared type's label, `description` is `Declared by the watch as holding <labels>.` where `<labels>` is the first four labels joined with `, ` (followed by `, …` when there are more), and `basis` is `device`. Otherwise the folder has **no purpose** (null), and the UI says nothing rather than guessing.
- The purpose always carries the folder's declared types (an empty list when there are none).
- **Basis values:** `documented` — stated by public Garmin or FIT documentation; `observed` — verified from the contents of a real watch; `inferred` — derived from the folder name only, and its description MUST start with "Likely"; `device` — known only from the watch's own declaration.

### Folder catalog

Keys are lower-cased storage-root-relative paths. Implementations MUST reproduce this table exactly; extending it is a spec change, and a new entry may only be marked `documented` or `observed` with evidence recorded in the PR.

| Folder (case-insensitive) | Title | Basis | Description |
|---|---|---|---|
| `audiobooks` | Audiobooks | documented | Audiobooks for offline playback. |
| `garmin` | Garmin system folder | observed | Root of the watch's own data: the device description (GarminDevice.xml), the device FIT file, installed map images (.img) and one folder per kind of data. |
| `garmin/activity` | Recorded activities | documented | One FIT activity file per recorded activity (runs, rides, walks, …), named after its start time. These are what Garmin Connect syncs. |
| `garmin/apps` | Connect IQ apps | documented | Installed Connect IQ apps, widgets, data fields and watch faces (.PRG) and their configuration. |
| `garmin/apps/data` | App data | documented | Data stored by installed Connect IQ apps. |
| `garmin/apps/logs` | App error logs | documented | Error reports written when a Connect IQ app crashes (.YML). |
| `garmin/apps/mail` | App mailboxes | documented | Messages queued for Connect IQ apps (.MBX). |
| `garmin/apps/settings` | App settings | documented | Settings of installed Connect IQ apps (.SET). |
| `garmin/apps/temp` | App temporary files | inferred | Likely temporary files of Connect IQ apps. |
| `garmin/audio/tones` | Tones | inferred | Likely alert tones. |
| `garmin/audio/voicenotes` | Voice notes | inferred | Likely recorded voice notes. |
| `garmin/backup/backups` | Backups from the watch | documented | Backup files written by the watch (.BAK). |
| `garmin/backup/restore` | Backups to restore | documented | Backup files placed here are restored onto the watch (.BAK). |
| `garmin/calendar` | Calendar | inferred | Likely the training calendar. |
| `garmin/clubs` | Golf clubs | inferred | Likely the golf clubs set up on the watch. |
| `garmin/coach` | Training plan | observed | The current adaptive training plan: its workouts and workout steps. Archive holds earlier versions of the plan. |
| `garmin/coach/archive` | Training plan history | observed | Earlier versions of the training plan, named by the time they were replaced. |
| `garmin/courses` | Courses | observed | Navigable courses as FIT course files. A GPX or FIT course copied into NewFiles is converted into this folder, named after the name stored inside the file. |
| `garmin/custommaps` | Custom maps | documented | Custom map overlays (.KMZ). |
| `garmin/debug` | Diagnostics | observed | Logs and diagnostic data for troubleshooting. Not needed for normal use. |
| `garmin/debug/metricsbackup` | Metrics backups | observed | Copies of physiological-metrics files, kept for diagnostics. |
| `garmin/debug/settingsbackup` | Settings backups | observed | Copies of the settings file, kept for diagnostics. |
| `garmin/debug/uploads/error` | Error reports | documented | Reports written after an unexpected shutdown. |
| `garmin/fbtbackup` | Analytics backup | inferred | Likely a backup of physiological-analytics state. |
| `garmin/fbtptdbackup` | Analytics backup | inferred | Likely a backup of physiological-analytics state. |
| `garmin/gear` | Gear | inferred | Likely tracked gear such as shoes and bikes. |
| `garmin/goals` | Goals | documented | Fitness goals (FIT goals file). |
| `garmin/golf` | Golf | inferred | Likely golf course data. |
| `garmin/hrvstatus` | HRV status | inferred | Likely heart-rate-variability status history. |
| `garmin/inreach` | inReach | inferred | Likely satellite-messaging data. |
| `garmin/location` | Saved locations | observed | Locations saved on the watch (Lctns.fit). Waypoints (<wpt>) in an imported GPX file are added here. |
| `garmin/metrics` | Physiological metrics | inferred | Likely physiological metrics such as VO2 max and training status. |
| `garmin/mltsport` | Multisport profiles | observed | Multisport activity profiles such as triathlon and swimrun. |
| `garmin/monitor` | All-day monitoring | documented | Steps, heart rate and intensity logged throughout the day (FIT monitoring files). |
| `garmin/newfiles` | Import inbox | documented | Files placed here (GPX/FIT courses, workouts, schedules, …) are imported by the watch when it is disconnected from USB, and then removed from this folder. |
| `garmin/pacebands` | Pace plans | inferred | Likely pace plans (pace bands) for running. |
| `garmin/powerguide` | Power plans | inferred | Likely cycling power plans. |
| `garmin/records` | Personal records | inferred | Likely the personal records (fastest times, longest distances) the watch keeps. |
| `garmin/remotesw` | Software updates | documented | Software update files downloaded for installation on the watch. |
| `garmin/schedule` | Training schedule | documented | Scheduled workouts (FIT schedules file). |
| `garmin/scorcrds` | Golf scorecards | inferred | Likely golf scorecards. |
| `garmin/seg_list` | Segment list | documented | The index of segments on the watch (FIT segment list file). |
| `garmin/segments` | Segments | documented | Segments to race against (FIT segment files). |
| `garmin/settings` | Device settings | documented | The watch's settings as a FIT settings file. |
| `garmin/skintemp` | Skin temperature | inferred | Likely skin temperature measurements. |
| `garmin/sleep` | Sleep | inferred | Likely recorded sleep data. |
| `garmin/sports` | Activity profiles | observed | One FIT sport file per activity profile (Run, Bike, Hike, …) with its data screens and settings. |
| `garmin/summary` | Activity summaries | observed | Compact per-activity summaries (sport, duration, distance, time in zones). |
| `garmin/totals` | Lifetime totals | documented | Accumulated distance, time and calories per sport (FIT totals file). |
| `garmin/wallet` | Wallet | inferred | Likely contactless-payment wallet data. |
| `garmin/weather` | Weather cache | observed | Cached weather forecasts and radar images. |
| `garmin/wifi` | Wi-Fi configuration | documented | Wi-Fi network configuration exchanged with the watch. |
| `garmin/workouts` | Workouts | observed | Structured workouts (FIT workout files) available on the watch. |
| `music` | Music | documented | Music tracks (MP3, M4A, WAV, AAC, …) and playlists (.M3U) for offline playback. |
| `podcasts` | Podcasts | documented | Podcast episodes for offline playback. |

### File inspection
- Input: an existing regular file inside the storage root (resolution and containment are the caller's job, see [gui/file-browser.md](../gui/file-browser.md)). The result always carries `name` (on-device name), `path` (canonical storage-root-relative path), `size_bytes`, `modified_time` (RFC 3339), and `format`.
- `folder`: the purpose of the parent folder as `{path, title, basis}`, or null when it has none.
- `declared_type`: the first declared type of the parent folder whose extensions include the file's extension (case-insensitive); for a FIT file whose `file_id` type is known, a declared type of the parent folder with that `fit_file_type` takes precedence. Null when nothing matches.
- **Format** is chosen by extension (case-insensitive), in this order: `.fit` → `fit`; `.gpx` → `gpx`; `.png .jpg .jpeg .gif .bmp .webp` → `image`; `.mp3 .m4a .m4b .wav .aac .adts` → `audio`; anything else → read up to 64 KiB + 1 byte and classify as `text` if it is non-empty, contains no NUL byte, and is valid UTF-8 (a multi-byte character cut off by the read limit — up to 3 trailing bytes — is allowed), else `binary`.
- `text` → `text: {content, truncated}`: `content` is at most the first 64 KiB, shortened further to end on a whole UTF-8 character; `truncated` is true when the file is longer than 64 KiB.
- `binary` → `hex_head`: the first 64 bytes (or fewer) as lower-case hex without separators; empty for an empty file.
- `image` and `audio` carry no extra data; the GUI renders images from the download endpoint.
- A FIT or GPX file that cannot be decoded MUST still produce a result with its `format`, a null summary, and `error` set to `cannot read FIT data: <reason>` / `cannot read GPX data: <reason>`. Inspection only fails outright when the file cannot be opened or stat'ed.
- Inspection MUST NOT write to, rename, or lock the file.

### FIT summary (FCT-26)
- Read at most 16 MiB. Data that does not start with a 12- or 14-byte header carrying the `.FIT` signature at bytes 8–11 is `not a FIT file`.
- `protocol_version` is `<high nibble>.<low nibble>` of byte 1. `profile_version` is the 16-bit little-endian value at bytes 2–3 formatted as `<v div 100>.<v mod 100, two digits>` (e.g. 2132 → `21.32`). `data_size_bytes` is the 32-bit little-endian value at bytes 4–7.
- `crc_valid`: when the file holds header + data + 2 CRC bytes, true iff the FIT CRC-16 computed over header, data and the 2 CRC bytes is zero; null when the file is too short to contain the CRC.
- Walk records from the end of the header to the end of the declared data (or end of file, if shorter):
  - Header bit 7 set: compressed-timestamp data message for local type `(h >> 5) & 3`.
  - Else bit 6 set: definition message for local type `h & 0x0F`: a reserved byte, architecture byte (1 = big-endian, otherwise little-endian), 16-bit global message number in that byte order, field count, then 3 bytes per field (number, size, base type). If header bit 5 is set, a developer-field count follows with 3 bytes per developer field (number, size, index); their sizes count toward the message length.
  - Else: data message for local type `h & 0x0F`.
  - A data message for an undefined local type, or any record that would run past the end, stops the walk and sets `complete = false`. Reading more than 16 MiB also sets `complete = false`.
- `messages`: one `{global, name, count}` per global message number seen in data messages, sorted by count descending, then global number ascending. Names: 0 file_id, 1 capabilities, 2 device_settings, 3 user_profile, 4 hrm_profile, 7 zones_target, 12 sport, 15 goal, 18 session, 19 lap, 20 record, 21 event, 23 device_info, 26 workout, 27 workout_step, 28 schedule, 31 course, 32 course_point, 33 totals, 34 activity, 35 software, 49 file_creator, 55 monitoring, 78 hrv, 101 length, 103 monitoring_info, 142 segment_lap, 148 segment_id, 149 segment_leaderboard_entry, 150 segment_point, 151 segment_file, 206 field_description, 207 developer_data_id, 216 time_in_zone; any other number → `message <n>`.
- Field values are unsigned integers of the field's size (1, 2 or 4 bytes) in the definition's byte order; a value with all bits set is invalid and treated as absent. Other sizes are not decoded as numbers.
- From the **first** `file_id` (global 0): field 0 → `file_type` and `file_type_name` (public table below, else `Garmin-specific type <n>`); field 1 → `manufacturer` (1 `Garmin`, 13 `Dynastream OEM`, 15 `Dynastream`, 255 `Development`, else `Manufacturer <n>`); field 2 → `product`; field 3 → `serial_number` (0 is also invalid); field 4 → `time_created` (FIT epoch seconds); field 8 → `product_name` (string).
- From the **first** `session` (global 18): field 5 → `sport` (0 Generic, 1 Running, 2 Cycling, 3 Transition, 4 Fitness equipment, 5 Swimming, 6 Basketball, 7 Soccer, 8 Tennis, 9 American football, 10 Training, 11 Walking, 12 Cross-country skiing, 13 Alpine skiing, 14 Snowboarding, 15 Rowing, 16 Mountaineering, 17 Hiking, 18 Multisport, 19 Paddling, 20 Flying, 21 E-biking, else `Sport <n>`); field 2 → `start_time`; field 7 → `elapsed_seconds` (value / 1000); field 9 → `distance_meters` (value / 100); field 11 → `calories`; field 16 → `avg_heart_rate_bpm`; field 17 → `max_heart_rate_bpm`. Absent fields are null.
- `name`: from the first `workout` (26) field 8, else the first `course` (31) field 5 — a NUL-terminated string, invalid UTF-8 dropped, surrounding whitespace trimmed.
- Public file-type names: 1 Device, 2 Settings, 3 Sport profile, 4 Activity, 5 Workout, 6 Course, 7 Schedules, 9 Weight, 10 Totals, 11 Goals, 14 Blood pressure, 15 Monitoring (A), 20 Activity summary, 28 Daily monitoring, 32 Monitoring (B), 34 Segment, 35 Segment list, 40 Extended display configuration.

### GPX summary (FCT-14, FCT-24)
- Parse at most 32 MiB as XML, matching elements by local name. A document whose root element is not `gpx` is `not a GPX document`.
- Report: `creator` (root attribute); `metadata_name` (`gpx/metadata/name`); `track_names` (every `gpx/trk/name`); `route_names` (every `gpx/rte/name`); counts of `trk`, `trkpt`, `rte`, `rtept`; `waypoints` = count of top-level `gpx/wpt`; `waypoint_names` = the first 50 non-empty `gpx/wpt/name` values. Names are whitespace-trimmed; empty names are skipped. `name` elements at other depths (e.g. inside `trkpt`) are ignored.
- These are exactly the inputs that decide what the watch does on import: the course is named after the name inside the file, not the file name, and top-level waypoints become Saved Locations (`FCT-24`). The summary reports both candidate names; it MUST NOT claim which one the watch picks when both are present, because `FCT-24` does not establish a precedence.

## Data Shapes / Interfaces

```yaml
DeclaredType:
  name: string             # raw <Name>, e.g. "FIT_TYPE_4"
  label: string            # per the label rule, e.g. "Activity (FIT)"
  extensions: [string]     # lower-case, no dot, e.g. ["fit"]
  direction: string        # "from_watch" | "to_watch" | "both"
  fit_file_type: integer   # n of FIT_TYPE_<n>, else null

FolderInfo:                # null when the folder has no purpose
  path: string             # canonical relative path ("" = storage root)
  title: string
  description: string
  basis: string            # "documented" | "observed" | "inferred" | "device"
  data_types: [DeclaredType]   # may be empty

FileInsight:
  name: string
  path: string
  size_bytes: integer
  modified_time: string    # RFC 3339
  format: string           # "fit" | "gpx" | "text" | "image" | "audio" | "binary"
  folder: {path: string, title: string, basis: string}   # or null
  declared_type: DeclaredType   # or null
  fit: FitSummary          # or null
  gpx: GpxSummary          # or null
  text: {content: string, truncated: boolean}   # or null
  hex_head: string         # "" unless format == "binary"
  error: string            # "" unless a FIT/GPX file could not be decoded

FitSummary:
  protocol_version: string     # "1.0"
  profile_version: string      # "21.32"
  data_size_bytes: integer
  crc_valid: boolean           # or null
  complete: boolean
  file_type: integer           # or null
  file_type_name: string       # "" when file_type is null
  manufacturer: string         # "" when absent
  product: integer             # or null
  product_name: string
  serial_number: integer       # or null
  time_created: string         # RFC 3339 UTC, or null
  name: string                 # workout/course name, "" when absent
  session:                     # or null
    sport: string              # "" when absent
    start_time: string         # or null
    elapsed_seconds: number    # or null
    distance_meters: number    # or null
    calories: integer          # or null
    avg_heart_rate_bpm: integer  # or null
    max_heart_rate_bpm: integer  # or null
  messages: [{global: integer, name: string, count: integer}]

GpxSummary:
  creator: string
  metadata_name: string
  track_names: [string]
  route_names: [string]
  tracks: integer
  track_points: integer
  routes: integer
  route_points: integer
  waypoints: integer
  waypoint_names: [string]     # at most 50
```

## Non-Goals

- Decoding FIT record streams, laps, or developer field values; rendering FIT data as charts or maps.
- Naming Garmin product IDs (the numeric `product` is shown as-is) or undocumented FIT messages.
- Previewing `.fit` courses as a route map (still `.gpx`-only, see [gui/course-preview.md](../gui/course-preview.md)).
- Audio metadata (ID3/MP4 tags).

## Open Questions

- **GPX name precedence on import.** `FCT-24` says the watch names an imported course after `<trk><name>` *or* `<metadata><name>`, but not which wins when both exist. The summary therefore shows both. A GPX with two different names, imported on a real watch, would settle it.
