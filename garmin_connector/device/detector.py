"""
Garmin Device Detection for Linux / POSIX systems.
Detects USB Mass Storage and MTP (GVFS) mounts and parses device XML descriptors.
"""

from __future__ import annotations
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class GarminDeviceInfo:
    model_name: str
    unit_id: Optional[str] = None
    software_version: Optional[str] = None
    part_number: Optional[str] = None
    mount_point: Path = Path(".")
    garmin_dir: Path = Path(".")
    newfiles_dir: Optional[Path] = None
    courses_dir: Optional[Path] = None
    activities_dir: Optional[Path] = None
    is_mtp: bool = False


class GarminDeviceDetector:
    """Discovers connected Garmin devices across standard Linux mount points."""

    @staticmethod
    def _find_candidate_roots() -> List[Path]:
        """Gathers potential mount roots where Garmin devices could appear."""
        candidates: List[Path] = []
        uid = os.getuid()
        user = os.environ.get("USER", "")

        # 1. GVFS MTP Mounts (Ubuntu/GNOME default for MTP watches)
        gvfs_root = Path(f"/run/user/{uid}/gvfs")
        if gvfs_root.exists():
            for child in gvfs_root.iterdir():
                if "mtp:" in child.name.lower() or "garmin" in child.name.lower():
                    # Check direct or subdirectories (e.g. /run/user/1000/gvfs/mtp:host=.../Primary/GARMIN)
                    candidates.append(child)
                    for sub in child.iterdir():
                        if sub.is_dir():
                            candidates.append(sub)

        # 2. Linux USB Mass Storage / Media Mounts
        media_roots = [
            Path(f"/media/{user}") if user else None,
            Path("/media"),
            Path(f"/run/media/{user}") if user else None,
            Path("/mnt"),
        ]

        for m_root in media_roots:
            if m_root and m_root.exists():
                for child in m_root.iterdir():
                    if child.is_dir():
                        candidates.append(child)

        return candidates

    @classmethod
    def _parse_garmin_xml(cls, xml_path: Path) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
        """Parses GarminDevice.xml or GARMIN.XML."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for elem in root.iter():
                if "}" in elem.tag:
                    elem.tag = elem.tag.split("}", 1)[1]

            model_elem = root.find(".//Model/Description")
            if model_elem is None:
                model_elem = root.find(".//Description")
            model_name = model_elem.text.strip() if (model_elem is not None and model_elem.text) else "Garmin Device"

            unit_id_elem = root.find(".//Id")
            if unit_id_elem is None:
                unit_id_elem = root.find(".//Unit/Id")
            unit_id = unit_id_elem.text.strip() if (unit_id_elem is not None and unit_id_elem.text) else None

            sw_elem = root.find(".//SoftwareVersion")
            if sw_elem is None:
                sw_elem = root.find(".//App/Version/VersionRss")
            software_version = sw_elem.text.strip() if (sw_elem is not None and sw_elem.text) else None

            part_elem = root.find(".//Model/PartNumber")
            part_number = part_elem.text.strip() if (part_elem is not None and part_elem.text) else None

            return model_name, unit_id, software_version, part_number
        except Exception:
            return "Garmin Device", None, None, None

    @classmethod
    def detect_devices(cls, custom_path: Optional[str | Path] = None) -> List[GarminDeviceInfo]:
        """Scans for connected Garmin devices and returns info objects."""
        devices: List[GarminDeviceInfo] = []
        candidates = [Path(custom_path)] if custom_path else cls._find_candidate_roots()

        for cand in candidates:
            if not cand.exists() or not cand.is_dir():
                continue

            # Look for GARMIN directory (case-insensitive)
            garmin_dir = None
            if cand.name.upper() == "GARMIN":
                garmin_dir = cand
            else:
                for sub in cand.iterdir():
                    if sub.is_dir() and sub.name.upper() == "GARMIN":
                        garmin_dir = sub
                        break

            if not garmin_dir:
                continue

            # Find GarminDevice.xml or GARMIN.XML
            xml_path = None
            for fname in ["GarminDevice.xml", "GARMIN.XML", "garmindevice.xml", "garmin.xml"]:
                potential = garmin_dir / fname
                if potential.exists():
                    xml_path = potential
                    break

            if xml_path:
                model, unit_id, sw_ver, part_num = cls._parse_garmin_xml(xml_path)
            else:
                model, unit_id, sw_ver, part_num = "Garmin Generic", None, None, None

            # Check subdirectories
            newfiles_dir = None
            courses_dir = None
            activities_dir = None

            for sub in garmin_dir.iterdir():
                if not sub.is_dir():
                    continue
                s_name = sub.name.upper()
                if s_name == "NEWFILES":
                    newfiles_dir = sub
                elif s_name == "COURSES":
                    courses_dir = sub
                elif s_name == "ACTIVITY":
                    activities_dir = sub

            # If NEWFILES doesn't exist, target path would be garmin_dir / "NEWFILES"
            if not newfiles_dir:
                newfiles_dir = garmin_dir / "NEWFILES"

            if not courses_dir:
                courses_dir = garmin_dir / "COURSES"

            is_mtp = "mtp" in str(cand).lower() or "gvfs" in str(cand).lower()

            devices.append(
                GarminDeviceInfo(
                    model_name=model,
                    unit_id=unit_id,
                    software_version=sw_ver,
                    part_number=part_num,
                    mount_point=cand if garmin_dir != cand else cand.parent,
                    garmin_dir=garmin_dir,
                    newfiles_dir=newfiles_dir,
                    courses_dir=courses_dir,
                    activities_dir=activities_dir,
                    is_mtp=is_mtp,
                )
            )

        return devices

    @classmethod
    def get_first_device(cls, custom_path: Optional[str | Path] = None) -> Optional[GarminDeviceInfo]:
        """Returns the primary connected Garmin device, if found."""
        devices = cls.detect_devices(custom_path)
        return devices[0] if devices else None

    @classmethod
    def check_raw_usb(cls) -> dict:
        """Checks sysfs for physically attached Garmin USB devices even if not mounted as a filesystem."""
        try:
            sysfs_usb = Path("/sys/bus/usb/devices")
            if sysfs_usb.exists():
                for p in sysfs_usb.glob("*"):
                    vendor_f = p / "idVendor"
                    product_f = p / "idProduct"
                    if vendor_f.exists() and product_f.exists():
                        vid = vendor_f.read_text().strip().lower()
                        pid = product_f.read_text().strip().lower()
                        if vid == "091e":
                            is_protocol_mode = (pid == "0003")
                            return {
                                "detected": True,
                                "vid": vid,
                                "pid": pid,
                                "is_protocol_mode": is_protocol_mode,
                                "sysfs_path": str(p),
                            }
        except Exception:
            pass
        return {"detected": False}
