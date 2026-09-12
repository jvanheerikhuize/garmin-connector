import tempfile
import unittest
from pathlib import Path
from garmin_connector.device.detector import GarminDeviceDetector
from garmin_connector.device.manager import GarminDeviceManager
from garmin_connector.converter.fit_encoder import Sport


class TestDeviceManager(unittest.TestCase):
    def test_device_detection_and_sideload(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            garmin_dir = tmp_root / "GARMIN"
            garmin_dir.mkdir()
            (garmin_dir / "NEWFILES").mkdir()
            (garmin_dir / "COURSES").mkdir()

            # Create mock GarminDevice.xml
            xml_content = """<?xml version="1.0" encoding="UTF-8"?>
            <Device xmlns="http://www.garmin.com/xmlschemas/GarminDevice/v2">
              <Model>
                <Description>Garmin Venu 3</Description>
                <PartNumber>006-B4280-00</PartNumber>
              </Model>
              <Id>1234567890</Id>
              <SoftwareVersion>10.15</SoftwareVersion>
            </Device>
            """
            (garmin_dir / "GarminDevice.xml").write_text(xml_content, encoding="utf-8")

            # Detect
            devices = GarminDeviceDetector.detect_devices(custom_path=tmp_root)
            self.assertEqual(len(devices), 1)
            dev = devices[0]
            self.assertEqual(dev.model_name, "Garmin Venu 3")
            self.assertEqual(dev.unit_id, "1234567890")
            self.assertEqual(dev.software_version, "10.15")

            # Manager
            manager = GarminDeviceManager(device=dev)

            # Sideload GPX
            example_gpx = Path(__file__).parent.parent / "examples" / "sample_hiking_route.gpx"
            dest = manager.sideload_route(example_gpx, sport=Sport.HIKING)

            self.assertTrue(dest.exists())
            self.assertEqual(dest.suffix, ".fit")
            self.assertEqual(dest.parent, garmin_dir / "NEWFILES")

            # Verify staged course
            v_status = manager.verify_staged_course(dest.name)
            self.assertTrue(v_status["verified"])
            self.assertEqual(v_status["filename"], dest.name)
            self.assertGreater(v_status["size_bytes"], 0)

            # List courses
            courses = manager.list_courses()
            self.assertEqual(len(courses), 1)
            self.assertEqual(courses[0].filename, dest.name)
            self.assertIn("Pending Sync", courses[0].location)

            # Test deleting
            deleted = manager.delete_course(dest.name)
            self.assertTrue(deleted)
            self.assertFalse(dest.exists())

    def test_format_mtp_uri(self):
        from garmin_connector.device.detector import format_mtp_uri
        uri = format_mtp_uri("091e_51fb_test", "Internal Storage/GARMIN/NewFiles")
        self.assertEqual(uri, "mtp://091e_51fb_test/Internal%20Storage/GARMIN/NewFiles")


if __name__ == "__main__":
    unittest.main()
