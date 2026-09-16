# Garmin Connector Roadmap & Ideas

This document tracks potential future features and expansions for `garmin-connector`, categorized by their complexity and value.

## 1. Data Extraction & Management
Currently, the tool inspects basic filesystem structure and metadata. The natural next step is handling actual Garmin data (`.FIT` files).

*   **Activity Sync/Export (`sync` or `export` command):** Copy completed activities (FIT files from `/GARMIN/Activity/`) to the local machine. Could eventually include options to convert them to `.gpx` or `.csv`.
*   **Storage & Battery Inspection:** Parse additional internal files or XML tags to report on remaining storage space on the watch, installed map files, and current battery level.
*   **Workout/Course Upload (`upload` command):** Allow users to push `.FIT` files (like downloaded courses or structured workouts) directly to the `/GARMIN/NewFiles/` directory, which the watch will automatically import upon disconnection.

## 2. Automation & Integration (Power Users)
Leveraging the existing `--json` flag to build automated pipelines.

*   **Watch Mode / Daemon (`watch` command):** Instead of a one-off run, the CLI could run in the background, listening for `udev` or `gvfs` mount events. When a watch is plugged in, it automatically triggers a backup or sync.
*   **Third-Party Webhook Triggers:** When a new activity is detected upon connection, automatically trigger a script or webhook to upload the `.FIT` file to a service like Strava, Runalyze, or a local database.

## 3. Device Configuration & Debugging
*   **Log Extraction (`diagnostics` command):** Garmin devices generate `ERR_LOG.TXT` and other diagnostic files. This command could package these up if the watch is crashing or having software issues.
*   **Multi-Device Support:** Currently the output spec expects a single device (`"device": {}`). Upgrading the CLI and `device-discovery` spec to handle multiple connected Garmin devices simultaneously (e.g., managing a family's devices).
