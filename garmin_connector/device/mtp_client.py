"""
Direct USB MTP / PTP Client for Garmin Devices.
Communicates directly with Garmin watches over USB Bulk endpoints via pyusb,
bypassing fragile Linux GVFS / FUSE limitations.
"""

from __future__ import annotations
import struct
import time
from dataclasses import dataclass
from typing import List, Optional
import usb.core
import usb.util

# PTP / MTP Standard Constants
GARMIN_VID = 0x091E
GARMIN_PID_MTP = 0x51FB

PTP_USB_EP_OUT = 0x03
PTP_USB_EP_IN = 0x81

# Container Types
PTP_CONTAINER_COMMAND = 1
PTP_CONTAINER_DATA = 2
PTP_CONTAINER_RESPONSE = 3
PTP_CONTAINER_EVENT = 4

# Opcodes
PTP_OC_GET_DEVICE_INFO = 0x1001
PTP_OC_OPEN_SESSION = 0x1002
PTP_OC_CLOSE_SESSION = 0x1003
PTP_OC_GET_STORAGE_IDS = 0x1004
PTP_OC_GET_STORAGE_INFO = 0x1005
PTP_OC_GET_OBJECT_HANDLES = 0x1007
PTP_OC_GET_OBJECT_INFO = 0x1008
PTP_OC_GET_OBJECT = 0x1009
PTP_OC_DELETE_OBJECT = 0x100B
PTP_OC_SEND_OBJECT_INFO = 0x100C
PTP_OC_SEND_OBJECT = 0x100D

# Response Codes
PTP_RC_OK = 0x2001
PTP_RC_SESSION_ALREADY_OPEN = 0x201E

# Formats
MTP_FORMAT_UNDEFINED = 0x3000
MTP_FORMAT_FOLDER = 0x3001
MTP_FORMAT_FIT = 0xB903


@dataclass
class MTPObjectInfo:
    handle: int
    filename: str
    size_bytes: int
    is_folder: bool
    format_code: int
    parent_handle: int
    storage_id: int


class GarminMTPClient:
    """Pure-Python MTP Client for direct Garmin USB communication."""

    def __init__(self, vid: int = GARMIN_VID, pid: int = GARMIN_PID_MTP):
        self.vid = vid
        self.pid = pid
        self.dev: Optional[usb.core.Device] = None
        self.tx_id = 0
        self.is_connected = False

    def connect(self):
        """Finds and claims the Garmin USB device."""
        self.dev = usb.core.find(idVendor=self.vid, idProduct=self.pid)
        if not self.dev:
            raise ConnectionError(f"Garmin MTP device ({hex(self.vid)}:{hex(self.pid)}) not found on USB bus.")

        try:
            self.dev.set_configuration()
        except Exception:
            pass

        usb.util.claim_interface(self.dev, 0)
        
        # Open PTP Session
        try:
            self._close_session()
        except Exception:
            pass

        raw_open = struct.pack('<IHHI I', 16, PTP_CONTAINER_COMMAND, PTP_OC_OPEN_SESSION, 0, 1)
        self.dev.write(PTP_USB_EP_OUT, raw_open)
        resp = bytes(self.dev.read(PTP_USB_EP_IN, 4096, timeout=3000))
        _, _, code, _ = struct.unpack_from('<IHHI', resp, 0)
        if code not in (PTP_RC_OK, PTP_RC_SESSION_ALREADY_OPEN):
            raise RuntimeError(f"Failed to open PTP session on Garmin device: 0x{code:04x}")

        self.tx_id = 1
        self.is_connected = True

    def disconnect(self):
        """Closes session and releases interface."""
        if self.dev and self.is_connected:
            try:
                self._close_session()
            except Exception:
                pass
            try:
                usb.util.release_interface(self.dev, 0)
            except Exception:
                pass
            self.is_connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _close_session(self):
        self.tx_id += 1
        raw_close = struct.pack('<IHHI', 12, PTP_CONTAINER_COMMAND, PTP_OC_CLOSE_SESSION, self.tx_id)
        self.dev.write(PTP_USB_EP_OUT, raw_close)
        self.dev.read(PTP_USB_EP_IN, 4096, timeout=1000)

    def _send_cmd(self, code: int, params: tuple = ()):
        self.tx_id += 1
        fmt = '<IHHI' + 'I' * len(params)
        data = struct.pack(fmt, struct.calcsize(fmt), PTP_CONTAINER_COMMAND, code, self.tx_id, *params)
        self.dev.write(PTP_USB_EP_OUT, data)

    def _send_data(self, code: int, payload: bytes):
        hdr = struct.pack('<IHHI', 12 + len(payload), PTP_CONTAINER_DATA, code, self.tx_id)
        self.dev.write(PTP_USB_EP_OUT, hdr + payload)

    def _read_data_and_resp(self) -> tuple[bytes, int, tuple]:
        raw = bytes(self.dev.read(PTP_USB_EP_IN, 16384, timeout=5000))
        l, pt, code, tx = struct.unpack_from('<IHHI', raw, 0)
        if pt == PTP_CONTAINER_RESPONSE:
            params = struct.unpack_from(f'<{(l-12)//4}I', raw, 12) if l > 12 else ()
            return b'', code, params

        data = bytearray(raw[12:l])
        while len(data) + 12 < l:
            more = bytes(self.dev.read(PTP_USB_EP_IN, 16384, timeout=5000))
            data.extend(more)

        resp = bytes(self.dev.read(PTP_USB_EP_IN, 4096, timeout=5000))
        rl, rpt, rcode, rtx = struct.unpack_from('<IHHI', resp, 0)
        params = struct.unpack_from(f'<{(rl-12)//4}I', resp, 12) if rl > 12 else ()
        return bytes(data), rcode, params

    def get_storage_ids(self) -> List[int]:
        """Gets all storage IDs from the watch (typically [0x00020001])."""
        self._send_cmd(PTP_OC_GET_STORAGE_IDS)
        data, code, _ = self._read_data_and_resp()
        if code != PTP_RC_OK or len(data) < 4:
            return []
        n = struct.unpack_from('<I', data, 0)[0]
        return list(struct.unpack_from(f'<{n}I', data, 4))

    def get_object_handles(self, storage_id: int = 0x00020001, parent_handle: int = 0x00000000) -> List[int]:
        """Lists object handles inside a given parent folder."""
        self._send_cmd(PTP_OC_GET_OBJECT_HANDLES, (storage_id, 0x0000, parent_handle))
        data, code, _ = self._read_data_and_resp()
        if code != PTP_RC_OK or len(data) < 4:
            return []
        n = struct.unpack_from('<I', data, 0)[0]
        return list(struct.unpack_from(f'<{n}I', data, 4))

    def get_object_info(self, handle: int) -> Optional[MTPObjectInfo]:
        """Fetches metadata and filename for a specific MTP object."""
        self._send_cmd(PTP_OC_GET_OBJECT_INFO, (handle,))
        data, code, _ = self._read_data_and_resp()
        if code != PTP_RC_OK or len(data) < 52:
            return None

        storage_id, obj_format, prot_status, obj_comp_size = struct.unpack_from('<IHHI', data, 0)
        parent_handle = struct.unpack_from('<I', data, 38)[0]
        offset = 52
        filename = ''
        if offset < len(data):
            c_len = data[offset]
            offset += 1
            if c_len > 0:
                name_bytes = data[offset:offset + (c_len * 2)]
                filename = name_bytes.decode('utf-16le', errors='ignore').rstrip('\x00')

        is_folder = (obj_format == MTP_FORMAT_FOLDER)
        return MTPObjectInfo(
            handle=handle,
            filename=filename,
            size_bytes=obj_comp_size,
            is_folder=is_folder,
            format_code=obj_format,
            parent_handle=parent_handle,
            storage_id=storage_id,
        )

    def find_path_handle(self, path_str: str, storage_id: int = 0x00020001) -> Optional[int]:
        """Resolves a folder path like 'GARMIN/NewFiles' to its object handle."""
        parts = [p for p in path_str.strip('/').split('/') if p]
        current_parent = 0x00000000
        current_handle = None

        for part in parts:
            handles = self.get_object_handles(storage_id, current_parent)
            found = False
            for h in handles:
                info = self.get_object_info(h)
                if info and info.filename.lower() == part.lower():
                    current_parent = h
                    current_handle = h
                    found = True
                    break
            if not found:
                return None

        return current_handle

    def list_folder_contents(self, path_str: str = "GARMIN/Courses") -> List[MTPObjectInfo]:
        """Lists all files inside a watch folder path."""
        folder_handle = self.find_path_handle(path_str)
        if not folder_handle:
            return []

        handles = self.get_object_handles(0x00020001, folder_handle)
        results = []
        for h in handles:
            info = self.get_object_info(h)
            if info and not info.is_folder:
                results.append(info)
        return results

    def delete_object(self, handle: int) -> bool:
        """Deletes an object by handle."""
        self._send_cmd(PTP_OC_DELETE_OBJECT, (handle, 0))
        resp = bytes(self.dev.read(PTP_USB_EP_IN, 4096, timeout=5000))
        _, _, code, _ = struct.unpack_from('<IHHI', resp, 0)
        return code == PTP_RC_OK

    def probe_device(self) -> dict:
        """Comprehensive health and status probe of the connected watch."""
        storages = self.get_storage_ids()
        garmin_handle = self.find_path_handle("GARMIN")
        newfiles_handle = self.find_path_handle("GARMIN/NewFiles")
        courses_handle = self.find_path_handle("GARMIN/Courses")

        courses = self.list_folder_contents("GARMIN/Courses") if courses_handle else []
        newfiles = self.list_folder_contents("GARMIN/NewFiles") if newfiles_handle else []

        return {
            "connected": True,
            "transport": "USB MTP (Pure Python Direct)",
            "vendor_id": hex(self.vid),
            "product_id": hex(self.pid),
            "storages": [hex(s) for s in storages],
            "garmin_folder_found": bool(garmin_handle),
            "newfiles_folder_found": bool(newfiles_handle),
            "courses_folder_found": bool(courses_handle),
            "courses_count": len(courses),
            "staged_newfiles_count": len(newfiles),
            "courses": [{"filename": c.filename, "size": c.size_bytes, "handle": c.handle} for c in courses],
            "staged_files": [{"filename": f.filename, "size": f.size_bytes, "handle": f.handle} for f in newfiles],
        }
