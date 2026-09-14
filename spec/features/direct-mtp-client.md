# Feature: Direct USB MTP/PTP Client (standalone, unwired)

`src/garmin_connector/device/mtp_client.py` — `GarminMTPClient`

## Status

**Not currently invoked by any other module.** `cli.py`, `gui/server.py`, and `device/manager.py` never import or use this class — device transfer instead goes through GVFS/GIO (see [device-manager](device-manager.md)). This spec documents it as a standalone capability so its behavior is preserved and intentionally scoped if/when it's wired in, not lost or duplicated.

## Purpose

Communicate directly with a Garmin watch over raw USB bulk endpoints using the PTP/MTP protocol via `pyusb`, bypassing the OS's GVFS/FUSE MTP stack entirely (intended as a more reliable alternative on systems where GVFS mounting is flaky).

## Requirements

### Identification
- Targets USB vendor ID `0x091E` (Garmin), product ID `0x51FB` (MTP mode) by default; constructor accepts overrides.
- Bulk endpoints: OUT `0x03`, IN `0x81`.

### Connection lifecycle (`connect`/`disconnect`, context-manager support)
- `connect()`:
  - If the MTP-mode device isn't found, additionally probe for `091e:0003` (Garmin "protocol mode" / not yet switched to MTP) and raise a `ConnectionError` with an actionable message (tap 'Yes' on watch / switch USB mode setting) if that's found instead.
  - If neither is found, raise `ConnectionError` naming the VID:PID that was searched for.
  - Sets USB configuration (best-effort; exceptions swallowed) and claims interface 0.
  - Attempts to close any stale prior PTP session before opening a new one (best-effort).
  - Opens a PTP session (`OpenSession`, session ID `1`); accepts response codes `PTP_RC_OK` or `PTP_RC_SESSION_ALREADY_OPEN` as success, otherwise raises `RuntimeError` with the response code.
- `disconnect()`: closes the PTP session and releases the USB interface, both best-effort (exceptions swallowed); safe to call even if never connected.
- Usable as `with GarminMTPClient() as client: ...`.

### PTP container protocol
- Implements the standard PTP command/data/response container framing (`struct`-packed, little-endian) for: `GetDeviceInfo`, `OpenSession`, `CloseSession`, `GetStorageIDs`, `GetStorageInfo`, `GetObjectHandles`, `GetObjectInfo`, `GetObject`, `DeleteObject`, `SendObjectInfo`, `SendObject` (opcodes defined; not all are necessarily exercised by the public methods below — `GetDeviceInfo`, `GetStorageInfo`, `GetObject`, `SendObjectInfo`, `SendObject` opcodes are defined but have no corresponding public method yet).
- `_read_data_and_resp` handles both single- and multi-packet data-phase responses, reading additional 16KB chunks until the declared payload length is satisfied, then reads the trailing response container.

### Public operations
- `get_storage_ids() -> List[int]` — typically returns `[0x00020001]` for a single internal storage.
- `get_object_handles(storage_id, parent_handle) -> List[int]` — lists children of a folder by PTP object handle (root is handle `0`).
- `get_object_info(handle) -> Optional[MTPObjectInfo]` — parses filename (UTF-16LE, PTP string encoding), size, folder flag (`format == FOLDER`), parent handle, storage ID. Returns `None` on malformed/short response.
- `find_path_handle(path_str, storage_id=0x00020001) -> Optional[int]` — resolves a `/`-delimited path (e.g. `"GARMIN/NewFiles"`) to an object handle by walking one path segment at a time, case-insensitive filename match; returns `None` if any segment isn't found.
- `list_folder_contents(path_str="GARMIN/Courses") -> List[MTPObjectInfo]` — resolves the path then returns only non-folder children.
- `delete_object(handle) -> bool` — sends `DeleteObject`, returns whether the response code was `PTP_RC_OK`.
- `probe_device() -> dict` — composite health check: storage IDs, whether `GARMIN`/`GARMIN/NewFiles`/`GARMIN/Courses` resolve, counts and listings (filename/size/handle) of courses and staged newfiles.

## Data shape — `MTPObjectInfo`
```
handle: int
filename: str
size_bytes: int
is_folder: bool
format_code: int
parent_handle: int
storage_id: int
```

## Non-goals (current)
- No file upload/send implementation (`SendObjectInfo`/`SendObject` opcodes defined but no public method uses them) — this client can currently only **read and delete**, not write, despite the module docstring's broader framing.
- No `GetObject` (file download) public method either, despite the opcode being defined.
- No integration with `GarminDeviceManager` — wiring this in as an alternative/fallback transfer strategy is a distinct, future feature-spec decision (see constitution §6).
