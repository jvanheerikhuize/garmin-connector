import unittest
from unittest.mock import MagicMock, patch
from garmin_connector.device.mtp_client import GarminMTPClient, MTPObjectInfo

class TestGarminMTPClient(unittest.TestCase):
    def test_mtp_object_info_dataclass(self):
        obj = MTPObjectInfo(
            handle=16777270,
            filename="NewFiles",
            size_bytes=0,
            is_folder=True,
            format_code=0x3001,
            parent_handle=16777216,
            storage_id=0x00020001,
        )
        self.assertEqual(obj.filename, "NewFiles")
        self.assertTrue(obj.is_folder)
        self.assertEqual(obj.handle, 16777270)

    @patch("usb.core.find")
    def test_connect_device_not_found(self, mock_find):
        mock_find.return_value = None
        client = GarminMTPClient()
        with self.assertRaises(ConnectionError):
            client.connect()

if __name__ == "__main__":
    unittest.main()
