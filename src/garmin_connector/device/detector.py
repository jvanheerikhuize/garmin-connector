import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import xml.etree.ElementTree as ET
import re

@dataclass
class GarminDeviceInfo:
    model_name: str
    unit_id: Optional[str]
    software_version: Optional[str]
    part_number: Optional[str]
    mount_point: Path
    garmin_dir: Path
    newfiles_dir: Optional[Path]
    courses_dir: Optional[Path]
    activities_dir: Optional[Path]

class GarminDeviceDetector:
    @staticmethod
    def _find_candidate_roots(custom_path: Optional[str | Path] = None) -> List[Path]:
        if custom_path:
            return [Path(custom_path)]
        
        candidates = []
        uid = os.getuid()
        
        # GVFS / MTP
        gvfs_dir = Path(f"/run/user/{uid}/gvfs")
        if gvfs_dir.exists() and gvfs_dir.is_dir():
            for child in gvfs_dir.iterdir():
                if "mtp:" in child.name.lower() or "garmin" in child.name.lower():
                    candidates.append(child)
                    if child.is_dir():
                        for subchild in child.iterdir():
                            candidates.append(subchild)
                            
        # USB Mass Storage
        usb_roots = [
            Path(f"/media/{os.environ.get('USER', 'root')}"),
            Path("/media"),
            Path(f"/run/media/{os.environ.get('USER', 'root')}"),
            Path("/mnt")
        ]
        
        for root in usb_roots:
            if root.exists() and root.is_dir():
                for child in root.iterdir():
                    if child.is_dir():
                        candidates.append(child)
                        
        return candidates

    @staticmethod
    def _parse_garmin_xml(garmin_dir: Path) -> tuple[str, Optional[str], Optional[str], Optional[str]]:
        xml_names = ["GarminDevice.xml", "GARMIN.XML", "garmindevice.xml", "garmin.xml"]
        xml_file = None
        for name in xml_names:
            candidate = garmin_dir / name
            if candidate.exists() and candidate.is_file():
                xml_file = candidate
                break
                
        if not xml_file:
            return "Garmin Generic", None, None, None
            
        try:
            xml_str = xml_file.read_text(encoding="utf-8")
            xml_str = re.sub(r'\sxmlns="[^"]+"', '', xml_str, count=1)
            root = ET.fromstring(xml_str)
            
            def get_text(path):
                el = root.find(path)
                return el.text if el is not None else None
                
            model_name = get_text("Model/Description") or "Garmin Device"
            unit_id = get_text("Id") or get_text("Unit/Id")
            software_version = get_text("SoftwareVersion") or get_text("App/Version/VersionRss")
            part_number = get_text("Model/PartNumber")
            
            return model_name, unit_id, software_version, part_number
        except Exception:
            return "Garmin Device", None, None, None

    @staticmethod
    def _find_dir_case_insensitive(parent: Path, name: str) -> Optional[Path]:
        if not parent.exists() or not parent.is_dir():
            return None
        lower_name = name.lower()
        for child in parent.iterdir():
            if child.is_dir() and child.name.lower() == lower_name:
                return child
        return None

    @staticmethod
    def detect_devices(custom_path: Optional[str | Path] = None) -> List[GarminDeviceInfo]:
        candidates = GarminDeviceDetector._find_candidate_roots(custom_path)
        devices = []
        
        for cand in candidates:
            try:
                if not cand.exists() or not cand.is_dir():
                    continue
            except PermissionError:
                continue

            garmin_dir = None
            if cand.name.lower() == "garmin":
                garmin_dir = cand
            else:
                garmin_dir = GarminDeviceDetector._find_dir_case_insensitive(cand, "garmin")
                
            if not garmin_dir:
                continue
                
            mount_point = cand.parent if cand.name.lower() == "garmin" else cand
            model, uid, sw_ver, part_num = GarminDeviceDetector._parse_garmin_xml(garmin_dir)
            
            newfiles = GarminDeviceDetector._find_dir_case_insensitive(garmin_dir, "newfiles")
            courses = GarminDeviceDetector._find_dir_case_insensitive(garmin_dir, "courses")
            activities = GarminDeviceDetector._find_dir_case_insensitive(garmin_dir, "activity")
            
            if not newfiles:
                newfiles = garmin_dir / "NEWFILES"
            if not courses:
                courses = garmin_dir / "COURSES"
                
            devices.append(GarminDeviceInfo(
                model_name=model,
                unit_id=uid,
                software_version=sw_ver,
                part_number=part_num,
                mount_point=mount_point,
                garmin_dir=garmin_dir,
                newfiles_dir=newfiles,
                courses_dir=courses,
                activities_dir=activities
            ))
            
        return devices

    @staticmethod
    def get_first_device(custom_path: Optional[str | Path] = None) -> Optional[GarminDeviceInfo]:
        devices = GarminDeviceDetector.detect_devices(custom_path)
        return devices[0] if devices else None
