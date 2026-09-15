import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

_GARMIN_XML_NAMES = ("GarminDevice.xml", "GARMIN.XML", "garmindevice.xml", "garmin.xml")
_DEFAULT_MODEL = "Garmin Device"
_GENERIC_MODEL = "Garmin Generic"


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


def _safe_iterdir(path: Path) -> List[Path]:
    try:
        return [p for p in path.iterdir()]
    except OSError:
        return []


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _find_child_dir(parent: Path, name: str) -> Optional[Path]:
    target = name.lower()
    for child in _safe_iterdir(parent):
        if child.name.lower() == target and _is_dir(child):
            return child
    return None


class GarminDeviceDetector:
    @staticmethod
    def _find_candidate_roots() -> List[Path]:
        candidates: List[Path] = []

        gvfs = Path(f"/run/user/{os.getuid()}/gvfs")
        for entry in _safe_iterdir(gvfs):
            lowered = entry.name.lower()
            if ("mtp:" in lowered or "garmin" in lowered) and _is_dir(entry):
                candidates.append(entry)
                candidates.extend(sub for sub in _safe_iterdir(entry) if _is_dir(sub))

        user = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
        mass_storage_roots: Iterable[Path] = (
            Path("/media") / user,
            Path("/media"),
            Path("/run/media") / user,
            Path("/mnt"),
        )
        for root in mass_storage_roots:
            if not _is_dir(root):
                continue
            candidates.extend(sub for sub in _safe_iterdir(root) if _is_dir(sub))

        return candidates

    @staticmethod
    def _resolve_garmin_dir(candidate: Path) -> Optional[Tuple[Path, Path]]:
        if not _is_dir(candidate):
            return None
        if candidate.name.lower() == "garmin":
            return candidate.parent, candidate
        garmin_dir = _find_child_dir(candidate, "GARMIN")
        if garmin_dir is None:
            return None
        return candidate, garmin_dir

    @staticmethod
    def _parse_garmin_xml(garmin_dir: Path) -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
        xml_path: Optional[Path] = None
        for name in _GARMIN_XML_NAMES:
            probe = garmin_dir / name
            try:
                if probe.is_file():
                    xml_path = probe
                    break
            except OSError:
                continue
        if xml_path is None:
            return (_GENERIC_MODEL, None, None, None)

        try:
            root = ET.fromstring(xml_path.read_bytes())
        except (OSError, ET.ParseError):
            return (_DEFAULT_MODEL, None, None, None)

        for elem in root.iter():
            if isinstance(elem.tag, str):
                elem.tag = re.sub(r"\{.*?\}", "", elem.tag)

        def text_of(*paths: str) -> Optional[str]:
            for path in paths:
                node = root.find(path)
                if node is not None and node.text and node.text.strip():
                    return node.text.strip()
            return None

        model_name = text_of("Model/Description", "Description") or _DEFAULT_MODEL
        unit_id = text_of("Id", "Unit/Id")
        software_version = text_of("SoftwareVersion", "App/Version/VersionRss")
        part_number = text_of("Model/PartNumber")
        return (model_name, unit_id, software_version, part_number)

    @classmethod
    def _build_device(cls, mount_point: Path, garmin_dir: Path) -> GarminDeviceInfo:
        model_name, unit_id, software_version, part_number = cls._parse_garmin_xml(garmin_dir)
        return GarminDeviceInfo(
            model_name=model_name,
            unit_id=unit_id,
            software_version=software_version,
            part_number=part_number,
            mount_point=mount_point,
            garmin_dir=garmin_dir,
            newfiles_dir=_find_child_dir(garmin_dir, "NEWFILES") or garmin_dir / "NEWFILES",
            courses_dir=_find_child_dir(garmin_dir, "COURSES") or garmin_dir / "COURSES",
            activities_dir=_find_child_dir(garmin_dir, "ACTIVITY"),
        )

    @classmethod
    def detect_devices(cls, custom_path: Optional[str | os.PathLike] = None) -> List[GarminDeviceInfo]:
        if custom_path is not None:
            candidates = [Path(custom_path)]
        else:
            candidates = cls._find_candidate_roots()

        devices: List[GarminDeviceInfo] = []
        for candidate in candidates:
            try:
                resolved = cls._resolve_garmin_dir(candidate)
                if resolved is None:
                    continue
                mount_point, garmin_dir = resolved
                devices.append(cls._build_device(mount_point, garmin_dir))
            except OSError:
                continue
        return devices

    @classmethod
    def get_first_device(cls, custom_path: Optional[str | os.PathLike] = None) -> Optional[GarminDeviceInfo]:
        devices = cls.detect_devices(custom_path)
        return devices[0] if devices else None
