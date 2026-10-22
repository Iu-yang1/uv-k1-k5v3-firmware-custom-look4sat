"""F4HWN 6.2 storage and overlay packaging compatibility checks."""
import re
import struct
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def define(path, name):
    text = (ROOT / path).read_text(encoding="utf-8")
    return int(re.search(r"^#define\s+" + name + r"\s+(0x[0-9a-fA-F]+|\d+)", text, re.M)[1], 0)


class PortLayoutTest(unittest.TestCase):
    def test_deliverable_image_including_ram_stub_fits_the_multiboot_slot(self):
        binary = ROOT / "build/L4S/look4sat.f4hwn620.bin"
        self.assertTrue(binary.is_file())
        self.assertGreater(binary.stat().st_size, 0)
        self.assertLessEqual(binary.stat().st_size, 118 * 1024)

    def test_local_cw_macros_do_not_write_old_channel_or_calibration_addresses(self):
        start = define("App/app/cwmacro.h", "CW_MACRO1_EEPROM_ADDR")
        self.assertGreaterEqual(start, 0xB000)
        self.assertLess(start + 4 * 48, 0x10000)
        source = (ROOT / "App/app/cwmacro.c").read_text(encoding="utf-8")
        self.assertNotIn("EEPROM_WriteBuffer(", source)
        self.assertIn("PY25Q16_WriteBuffer(MACRO_ADDRS[macroIndex], data, sizeof(data), false)", source)

    def test_cw_schema_does_not_overlap_mixed_scan_or_l4s_settings(self):
        marker = define("App/settings.h", "EEPROM_SCHEMA_ADDR")
        mixed = define("App/settings.c", "SETTINGS_SCAN_MIX_ADDR")
        profile = define("App/app/l4s_settings.h", "L4S_PROFILE_ADDR")
        self.assertGreaterEqual(marker, mixed + 8)
        self.assertLess(marker, profile)

    def test_transaction_stores_stay_between_logo_and_log(self):
        starts = [define("App/app/l4s_store.h", name) for name in ("L4S_BANK_A", "L4S_BANK_B")]
        self.assertEqual(2, len(set(starts)))
        for start in starts:
            self.assertGreaterEqual(start, 0x12000)
            self.assertLessEqual(start + 4096, 0x18000)

    def test_custom_modules_require_fork_api_without_changing_slot_geometry(self):
        self.assertEqual(48, define("App/apps/app_overlay.h", "APP_SLOT_COUNT"))
        for name in ("Look4Sat", "CWPractice"):
            data = (ROOT / "build/Apps" / (name + ".app")).read_bytes()
            header = struct.unpack("<4sHBBIIHH16s16sIIHH", data[:64])
            self.assertEqual(b"FAP1", header[0])
            self.assertEqual((1, 3), header[2:4])
            self.assertEqual(0x20000280, header[10])
            self.assertEqual(0x48, header[11])
            self.assertTrue(0 < header[4] <= 4096)
            self.assertEqual(header[4], len(data) - 64)
            self.assertEqual(header[5], zlib.crc32(data[64:]) & 0xffffffff)
            self.assertTrue(header[7] & 4)
