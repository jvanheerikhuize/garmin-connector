---
id: gui-filesystem-manipulation
title: Web GUI Filesystem Manipulation
namespace: gui
status: implemented
owners: [jerry]
depends_on: [gui-file-browser, filesystem-manipulation]
implements_requirements: [FR-12]
relies_on_facts: [FCT-3, FCT-4, FCT-8, FCT-10, FCT-11, FCT-13, FCT-15, FCT-19]
relies_on_assumptions: [ASM-1, ASM-2, ASM-3, ASM-5, ASM-8, ASM-12]
last_updated: 2026-09-17
---

# Web GUI Filesystem Manipulation

`internal/web/server.go`
`internal/web/api.go`
`internal/web/static/index.html`
`internal/web/static/app.css`
`internal/web/static/app.js`

Depends on: [Web GUI Column View File Browser](file-browser.md), [Filesystem Manipulation (mkdir, rm, touch, put)](../cli/filesystem-manipulation.md)

## Constitution Alignment

- **Implements Requirements:** `FR-12` (Web GUI Filesystem Manipulation)
- **Relies on Facts:** `FCT-3` (GARMIN directory structure), `FCT-4` (GVFS paths), `FCT-8` (MTP character casing), `FCT-10` (MTP traversal latency), `FCT-11` (MTP metadata limits), `FCT-13` (GVFS direct write limits), `FCT-15` (GVFS client tooling/D-Bus transfers), `FCT-19` (GVFS FUSE mutation limitations)
- **Relies on Assumptions:** `ASM-1` (On-demand execution), `ASM-2` (Structured output), `ASM-3` (Single connected watch), `ASM-5` (Basic metadata sufficiency), `ASM-8` (Local web interface preference), `ASM-12` (Immediate mutation without recycle bin)

## Purpose

Enables users to manage and mutate files and directories on their connected Garmin watch directly within the local Web GUI Column View file browser. Users can create new folders, create empty files, upload local files to any selected watch directory, and delete files or folders with confirmation, eliminating the need to drop down to the CLI or manage Linux GVFS mount paths manually.

## Scope

**In scope:**
- Toolbar action buttons in the File Browser view:
  - **New Folder**: Prompts for a folder name and creates it in the currently active/selected directory.
  - **New File**: Prompts for a file name and creates an empty file in the currently active/selected directory.
  - **Upload File**: Opens a file-picker dialog to upload one or more local files directly into the active directory.
- Drag-and-drop file upload:
  - Dropping files onto an active directory column uploads them directly into that column's directory.
- Deletion actions:
  - A **Delete** button in the File Preview / Inspector pane for selected files.
  - A **Delete Folder** action for selected directories.
  - An interactive confirmation modal warning that deletions are permanent (`ASM-12`, `ASM-14`).
- Backend REST API endpoints:
  - `POST /api/fs/mkdir`: Creates directory at specified watch path.
  - `POST /api/fs/touch`: Creates empty file at specified watch path.
  - `POST /api/fs/upload`: Multipart file upload targeting a destination directory.
  - `POST /api/fs/delete`: Deletes a file or directory on the watch.
- Automatic column re-fetching and UI state updates after every successful mutation.
- Toast / alert feedback displaying success or error messages.
- Safeguards preventing deletion of the storage root (`/`) or `GARMIN` root directory.

**Out of scope:**
- Renaming or moving files via drag-and-drop (`mv`).
- In-place text editing or binary hex editing inside the browser.
- Trash bin / soft deletion staging.
- Folder batch downloading or zip archiving.

## Requirements

### Sub-behavior A: Directory Creation ("New Folder")
- The File Browser toolbar MUST provide a "New Folder" button.
- Clicking "New Folder" MUST prompt the user with a modal dialog containing a text input for the folder name and "Cancel" / "Create" buttons.
- Submitting the form MUST send a `POST /api/fs/mkdir` request with the resolved target path (parent path + new folder name).
- If the request succeeds:
  - The modal MUST close.
  - The parent directory column MUST automatically reload its contents via `GET /api/fs/ls`.
  - A brief success toast notification MUST be displayed (e.g. `Folder "Custom" created`).
- If the request fails:
  - The modal MUST display an inline error message describing the failure without losing the entered folder name.

### Sub-behavior B: File Creation ("New File")
- The File Browser toolbar MUST provide a "New File" button.
- Clicking "New File" MUST prompt the user with a modal dialog containing a text input for the file name and "Cancel" / "Create" buttons.
- Submitting the form MUST send a `POST /api/fs/touch` request with the resolved target path (parent path + new file name).
- If the request succeeds:
  - The modal MUST close.
  - The parent directory column MUST automatically reload its contents.
  - A brief success toast notification MUST be displayed.
- If the request fails:
  - The modal MUST display an inline error message describing the failure.

### Sub-behavior C: File Upload to Active Directory
- The File Browser toolbar MUST provide an "Upload File" button.
- Clicking "Upload File" MUST trigger a hidden file-input picker allowing the user to select local files.
- The interface MUST also support dragging and dropping local files directly onto any visible directory column.
- When files are selected or dropped:
  - An upload overlay or progress indicator MUST appear over the target column.
  - The browser MUST upload each file via `POST /api/fs/upload` with form data containing `dir` (destination watch directory) and `file`.
  - Existing files of the same name MUST be overwritten.
  - Upon completion, the target directory column MUST automatically reload to show the newly uploaded files.
  - A success toast notification MUST be displayed.

### Sub-behavior D: Deletion & Confirmation Modal
- The File Preview / Inspector pane MUST include a red, destructive **Delete** button when a file is selected.
- Each directory column or breadcrumb action bar MAY provide a "Delete Folder" option for the selected directory.
- Clicking any delete action MUST NOT immediately delete the item. It MUST display an interactive modal confirmation:
  - Title: `Delete <Item Name>?`
  - Body: `Are you sure you want to delete "<canonical_path>"? This action cannot be undone.`
  - Action buttons: "Cancel" (default) and "Delete" (destructive style).
- Confirming deletion MUST send a `POST /api/fs/delete` request with the target path and `recursive: true` if deleting a directory.
- The UI MUST NOT permit deleting the storage root (`/`) or `GARMIN` root folder; for these paths the Delete button MUST be disabled or omitted.
- Upon successful deletion:
  - The modal MUST close.
  - The parent directory column MUST reload its contents.
  - If the deleted item was currently selected, any subsequent columns (including the preview pane) MUST be dismissed.
  - A success toast notification MUST be displayed.

### Sub-behavior E: Backend REST API Endpoints

#### `POST /api/fs/mkdir`
- **Request Body (JSON):**
  - `path` (string, required): Watch-relative path of directory to create.
  - `parents` (boolean, optional, default `false`): If true, creates intermediate parent directories.
- **Behavior:**
    - If no device is connected, returns `503 Service Unavailable` with `{"error": "no device connected"}`.
  - Creates directory at target path with intermediate parent creation if requested (`FR-11`).
  - On success, returns `200 OK` with JSON envelope adhering to `FsMutationResponse`.
  - On conflict or error, returns `400 Bad Request` or `409 Conflict` with `{"error": "<reason>"}`.

#### `POST /api/fs/touch`
- **Request Body (JSON):**
  - `path` (string, required): Watch-relative path of file to create or touch.
- **Behavior:**
  - If no device is connected, returns `503 Service Unavailable` with `{"error": "no device connected"}`.
  - Creates empty file or touches timestamp at target path (`FR-11`).
  - On success, returns `200 OK` with `FsMutationResponse`.
  - On error (e.g. parent does not exist), returns `400 Bad Request` with `{"error": "<reason>"}`.

#### `POST /api/fs/upload`
- **Request Format:** `multipart/form-data`
  - `dir` (string, optional, default `""`): Destination directory relative to storage root.
  - `file` (file part, required): Binary stream of the file to upload.
- **Behavior:**
  - If no device is connected, returns `503 Service Unavailable`.
  - Reads uploaded file content and writes to destination via file write operation with GVFS/MTP fallback (`FCT-13`, `FCT-20`).
  - Overwrites existing files with identical names.
  - On success, returns `200 OK` with `FsMutationResponse` including `bytes_transferred`.
  - On error, returns `400 Bad Request` or `500 Internal Server Error` with `{"error": "<reason>"}`.

#### `POST /api/fs/delete`
- **Request Body (JSON):**
  - `path` (string, required): Watch-relative path of item to remove.
  - `recursive` (boolean, optional, default `false`): Must be true if removing a directory.
- **Behavior:**
  - If no device is connected, returns `503 Service Unavailable`.
  - Prevents removal of storage root or `GARMIN` root directory (`400 Bad Request`).
  - Executes removal operation with bottom-up deletion for MTP directories (`FCT-21`, `ASM-14`).
  - On success, returns `200 OK` with `FsMutationResponse`.
  - On error (e.g. item is a directory without `recursive: true`), returns `400 Bad Request` with `{"error": "<reason>"}`.

## Data Shapes / Interfaces

### Request / Response Payloads

```yaml
FsMkdirRequest:
  path: string             # Watch-relative path
  parents: boolean         # Optional, default false

FsTouchRequest:
  path: string             # Watch-relative path

FsDeleteRequest:
  path: string             # Watch-relative path
  recursive: boolean       # Optional, default false

FsMutationResponse:
  success: boolean         # True if operation completed successfully
  operation: string        # "mkdir" | "rm" | "touch" | "put"
  target_path: string      # Canonical relative path on watch
  bytes_transferred: integer # Optional, present on uploads
  message: string          # Human-readable summary message
```

## Non-Goals

- In-place text editing or modifying existing files inside the browser.
- Multi-file drag selection or bulk deletion.
- Trash bin or undo mechanisms (`ASM-12`).
- Renaming existing files or directories.
