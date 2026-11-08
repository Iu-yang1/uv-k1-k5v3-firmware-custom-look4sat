"""Regression: MAIN TX / DUAL RX must never transmit on the background VFO."""
import ctypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_cw_start import function

ROOT = Path(__file__).resolve().parents[2]


class DualWatchTxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="l4s-dual-tx-")
        source = (ROOT / "App/radio.c").read_text(encoding="utf-8")
        ui = (ROOT / "App/ui/main.c").read_text(encoding="utf-8")
        common = (ROOT / "App/app/common.c").read_text(encoding="utf-8")
        select = function(source, "static void RADIO_SelectCurrentVfo(")
        switch = function(common, "void COMMON_SwitchVFOs(")
        match = re.search(r"unsigned int activeTxVFO\s*=.*?;", ui, re.S)
        if not match:
            raise AssertionError("Unable to find the production TX indicator expression")
        harness = """
#include <stdbool.h>
#include <stdint.h>
enum { CROSS_BAND_OFF = 0, CROSS_BAND_CHAN_A, CROSS_BAND_CHAN_B };
enum { DUAL_WATCH_OFF = 0, DUAL_WATCH_CHAN_A, DUAL_WATCH_CHAN_B, DUAL_WATCH_FULL };
typedef struct { uint32_t tx_frequency; } VFO_Info_t;
static struct {
    int CROSS_BAND_RX_TX, DUAL_WATCH, TX_VFO, RX_VFO;
    VFO_Info_t VfoInfo[2];
} gEeprom;
static VFO_Info_t *gTxVfo, *gRxVfo, *gCurrentVfo;
static bool gRxVfoIsActive, gHasVfoBackup, gFlagReconfigureVfos;
static bool gScheduleDualWatch, gRequestSaveSettings;
static int gInputBoxIndex, gRequestDisplayScreen;
#define DISPLAY_MAIN 0
""" + select + "\n" + switch + """
int select_tx(int main, int rx, int crossband, int dual_watch, int active) {
    gEeprom.TX_VFO = main;
    gEeprom.RX_VFO = rx;
    gEeprom.CROSS_BAND_RX_TX = crossband;
    gEeprom.DUAL_WATCH = dual_watch;
    gEeprom.VfoInfo[0].tx_frequency = 14590000u;
    gEeprom.VfoInfo[1].tx_frequency = 43510000u;
    gTxVfo = &gEeprom.VfoInfo[main];
    gRxVfo = &gEeprom.VfoInfo[rx];
    gRxVfoIsActive = active;
    RADIO_SelectCurrentVfo();
    return gCurrentVfo - &gEeprom.VfoInfo[0];
}
uint32_t selected_tx_frequency(void) { return gCurrentVfo->tx_frequency; }
int listening_vfo(void) { return gRxVfo - &gEeprom.VfoInfo[0]; }
int focused_vfo(void) { return gEeprom.TX_VFO; }
int pinned_vfo(void) { return gEeprom.CROSS_BAND_RX_TX; }
int dual_watch_anchor(void) { return gEeprom.DUAL_WATCH; }
int switch_focus_and_select(void) {
    COMMON_SwitchVFOs();
    gEeprom.RX_VFO = gEeprom.TX_VFO;
    gTxVfo = &gEeprom.VfoInfo[gEeprom.TX_VFO];
    gRxVfo = &gEeprom.VfoInfo[gEeprom.RX_VFO];
    RADIO_SelectCurrentVfo();
    return gCurrentVfo - &gEeprom.VfoInfo[0];
}
int display_tx_vfo(void) {
""" + match.group(0) + """
    return activeTxVFO;
}
"""
        p = Path(cls.temp.name) / "tx_select.c"
        p.write_text(harness, encoding="utf-8")
        compiler = os.environ.get("L4S_HOST_CC") or shutil.which("gcc")
        if not compiler and os.name == "nt":
            compiler = "H:/tools/msys64/ucrt64/bin/gcc.exe"
        binary = Path(cls.temp.name) / ("tx_select.dll" if os.name == "nt" else "tx_select.so")
        subprocess.run([compiler or "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-O2", "-shared", "-fPIC", str(p), "-o", str(binary)],
                       check=True)
        cls.lib = ctypes.CDLL(str(binary))
        cls.lib.selected_tx_frequency.restype = ctypes.c_uint32

    @classmethod
    def tearDownClass(cls):
        if os.name == "nt":
            import _ctypes
            _ctypes.FreeLibrary(cls.lib._handle)
        del cls.lib
        cls.temp.cleanup()

    def test_main_tx_dual_rx_always_uses_selected_main_for_tx(self):
        for main in (0, 1):
            dual = 1 - main
            for crossband in (main + 1,):
                for dual_watch in (1, 2, 3):
                    for active in (0, 1):
                        with self.subTest(main=main, crossband=crossband,
                                          watch=dual_watch, active=active):
                            self.assertEqual(main, self.lib.select_tx(
                                main, dual, crossband, dual_watch, active))
                            self.assertEqual(dual, self.lib.listening_vfo())
                            self.assertEqual(main, self.lib.display_tx_vfo())
                            self.assertEqual((14590000, 43510000)[main],
                                             self.lib.selected_tx_frequency())

    def test_focus_switch_does_not_steal_main_transmitter(self):
        for main in (0, 1):
            dual = 1-main
            for watch in (1, 2, 3):
                with self.subTest(main=main, watch=watch):
                    self.assertEqual(main, self.lib.select_tx(main, main, main+1, watch, 1))
                    self.assertEqual(main+1, self.lib.pinned_vfo())
                    self.assertEqual(main, self.lib.display_tx_vfo())
                    self.assertEqual(main, self.lib.switch_focus_and_select())
                    self.assertEqual(dual, self.lib.focused_vfo())
                    self.assertEqual(dual, self.lib.listening_vfo())
                    self.assertEqual(main+1, self.lib.pinned_vfo())
                    self.assertEqual(watch, self.lib.dual_watch_anchor())
                    self.assertEqual(main, self.lib.display_tx_vfo())
                    self.assertEqual((14590000, 43510000)[main], self.lib.selected_tx_frequency())
                    self.assertEqual(main, self.lib.switch_focus_and_select())
                    self.assertEqual(main, self.lib.focused_vfo())
                    self.assertEqual(main+1, self.lib.pinned_vfo())

    def test_nonlocked_vfo_switch_still_changes_main(self):
        for main in (0, 1):
            dual = 1-main
            self.lib.select_tx(main, main, 0, 1, 1)
            self.assertEqual(dual, self.lib.switch_focus_and_select())
            self.assertEqual(dual, self.lib.focused_vfo())
            self.assertEqual(dual, self.lib.display_tx_vfo())
            self.lib.select_tx(main, main, main+1, 0, 1)
            self.assertEqual(dual, self.lib.switch_focus_and_select())
            self.assertEqual(dual+1, self.lib.pinned_vfo())

    def test_tx_register_path_uses_pinned_current_vfo(self):
        source = (ROOT / "App/radio.c").read_text(encoding="utf-8")
        tx = function(source, "static void RADIO_SetTxParametersEx(bool fm)")
        for fragment in (
            "RADIO_ResolveFilter(gCurrentVfo)",
            "gCurrentVfo->pTX->Frequency",
            "CW_RIT_TxFrequency(gCurrentVfo, tx_frequency)",
            "gCurrentVfo->TXP_CalculatedSetting",
            "gCurrentVfo->pTX->CodeType",
            "gCurrentVfo->Modulation",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, tx)
        self.assertNotIn("gTxVfo->Modulation", tx)
        self.assertIn("BK4819_SetFrequency(tx_frequency)", tx)

    def test_crossband_without_dual_watch_retains_main_tx(self):
        for main in (0, 1):
            self.assertEqual(main, self.lib.select_tx(main, 1-main, main+1, 0, 1))
            self.assertEqual(main, self.lib.display_tx_vfo())

    def test_regular_dual_watch_preserves_talkback(self):
        for main in (0, 1):
            dual = 1-main
            self.assertEqual(dual, self.lib.select_tx(main, dual, 0, 1, 1))
            self.assertEqual(dual, self.lib.display_tx_vfo())
            self.assertEqual((14590000, 43510000)[dual],
                             self.lib.selected_tx_frequency())
            self.assertEqual(main, self.lib.select_tx(main, main, 0, 1, 0))
            self.assertEqual(main, self.lib.display_tx_vfo())

    def test_single_vfo_transmits_on_main(self):
        for main in (0, 1):
            self.assertEqual(main, self.lib.select_tx(main, main, 0, 0, 0))
            self.assertEqual(main, self.lib.display_tx_vfo())


if __name__ == "__main__":
    unittest.main()
