"""F4HWN 6.2 storage and overlay packaging compatibility checks."""
import re
import struct
import unittest
import zlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def define(path, name):
    text = (ROOT / path).read_text(encoding="utf-8")
    return int(re.search(r"^#define\s+" + name + r"\s+(0x[0-9a-fA-F]+|\d+)", text, re.M)[1], 0)


class PortLayoutTest(unittest.TestCase):
    def test_serial_and_l4s_capabilities_are_separate(self):
        self.assertEqual(0x40, define('App/apps/app_overlay.h', 'APP_CAP_SERIAL'))
        self.assertEqual(0x80, define('App/apps/app_overlay.h', 'APP_CAP_L4S'))
        api=(ROOT/'App/apps/app_api.h').read_text(encoding='utf-8')
        self.assertIn('offsetof(app_api_t, l4s_request_page) == 396u',api)
        self.assertIn('sizeof(app_api_t) == 400u',api)
        loader=(ROOT/'App/apps/app_overlay.c').read_text(encoding='utf-8')
        self.assertIn('h->api_min == 3u && (h->required_caps & APP_CAP_SERIAL)',loader)
        self.assertIn('memcmp(h->name, "Look4Sat", 9)',loader)
        self.assertIn('memcmp(h->name, "CWPractice", 11)',loader)

    def test_optional_services_cannot_admit_incompatible_api3_modules(self):
        presets=json.loads((ROOT/'CMakePresets.json').read_text(encoding='utf-8'))
        options=next(p['cacheVariables'] for p in presets['configurePresets'] if p['name']=='L4S')
        self.assertFalse(options['ENABLE_OVERLAY_RX_AUDIO'])
        self.assertFalse(options['ENABLE_OVERLAY_HANDOFF'])
        self.assertFalse(options['ENABLE_FEAT_F4HWN_OVERLAY_INFO'])
        loader=(ROOT/'App/apps/app_overlay.c').read_text(encoding='utf-8')
        self.assertIn('if (h->api_min >= 3u && !(h->required_caps & APP_CAP_L4S)) return APP_ERR_CAP;',loader)
        cmake=(ROOT/'CMakeLists.txt').read_text(encoding='utf-8')
        self.assertIn('option(ENABLE_OVERLAY_RX_AUDIO "Resident overlay RX audio capture" ON)',cmake)
        self.assertIn('option(ENABLE_OVERLAY_HANDOFF "Resident overlay application hand-off" ON)',cmake)

    def test_cdc_upstream_services_keep_l4s_buffer_ownership(self):
        usb=(ROOT/'App/usb/usbd_cdc_if.c').read_text(encoding='utf-8')
        for symbol in ('cdc_acm_rx_total += nbytes','cdc_acm_config_count++',
                       'usbd_ep_cancel_write(CDC_IN_EP)', '__set_PRIMASK(primask)',
                       'L4S_ReplyComplete(&l4s_reply)', 'L4S_UsbLost()', 'L4S_SendReply('):
            self.assertIn(symbol,usb)
        driver=(ROOT/'Middlewares/CherryUSB/port/usb_dc_py32.c').read_text(encoding='utf-8')
        self.assertIn('g_pyusb_udc.in_ep[ep_idx].actual_xfer_len = 0',driver)

    def test_l4s_preset_restores_nr7y_cw_menu_categories_and_layout(self):
        presets=json.loads((ROOT/'CMakePresets.json').read_text(encoding='utf-8'))
        options=next(p['cacheVariables'] for p in presets['configurePresets'] if p['name']=='L4S')
        self.assertTrue(options['ENABLE_FEAT_F4HWN_MENU_CAT'])
        self.assertTrue(options['ENABLE_CUSTOM_MENU_LAYOUT'])
        self.assertTrue(options['ENABLE_FEAT_NR7Y_CW'])
        source=(ROOT/'App/ui/menu.c').read_text(encoding='utf-8')
        category=source.split('static const uint8_t CatCw[] = {',1)[1].split('};',1)[0]
        for name in ('FREQ','SIDETONE_LEVEL','KEYER_MODE','KEY_WPM','KEY_INPUT','BKIN','HANG','MSG1','MSG2','MSG3','MSG4','MSG_REPEAT','ROGER_DITS'):
            self.assertIn('MENU_CW_'+name,category)

    def test_shared_profile_and_macro_banks_do_not_follow_config_bank_offsets(self):
        boundary=define('App/driver/py25q16.h','PY25Q16_BANK_SHARED_FROM')
        for path,names in [('App/app/l4s_store.h',('L4S_BANK_A','L4S_BANK_B')),
                           ('App/app/l4s_macros.h',('L4S_MACRO_A','L4S_MACRO_B'))]:
            for name in names:self.assertGreaterEqual(define(path,name),boundary)
        self.assertEqual(4,define('App/app/l4s_macros.h','L4S_MACRO_SLOTS'))
    def test_deliverable_image_including_ram_stub_fits_the_multiboot_slot(self):
        presets=json.loads((ROOT/'CMakePresets.json').read_text(encoding='utf-8'))
        target=next(p['cacheVariables']['TARGET'] for p in presets['configurePresets'] if p['name']=='L4S')
        binary = ROOT / 'build/L4S' / (target + '.bin')
        elf = binary.with_suffix('.elf')
        self.assertTrue(elf.is_file(), 'successful current link is required')
        self.assertGreaterEqual(binary.stat().st_mtime_ns, elf.stat().st_mtime_ns)
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
            self.assertEqual((1, 4), header[2:4])
            self.assertEqual(0x20000280, header[10])
            self.assertEqual(0x80, header[11])
            self.assertTrue(0 < header[4] <= 4096)
            self.assertEqual(header[4], len(data) - 64)
            self.assertEqual(header[5], zlib.crc32(data[64:]) & 0xffffffff)
            self.assertTrue(header[7] & 4)
