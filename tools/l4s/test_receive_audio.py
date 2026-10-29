"""Run production RX register setup with audio hardware replaced by a register bank."""
import ctypes
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

from test_cw_start import function

ROOT = Path(__file__).resolve().parents[2]


class ReceiveAudioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='l4s-rx-')
        cls.libs = []
        radio = (ROOT/'App/radio.c').read_text(encoding='utf-8')
        control = (ROOT/'App/app/l4s_control.c').read_text(encoding='utf-8')
        rit = (ROOT/'App/app/cwrit.c').read_text(encoding='utf-8')
        settings = (ROOT/'App/app/l4s_settings.c').read_text(encoding='utf-8')
        harness = r'''
#include <stdbool.h>
#include <stdint.h>
#include "l4s_protocol.h"
#define ENABLE_CW_MODULATOR
#define MODULATION_FM 0
#define MODULATION_AM 1
#define MODULATION_USB 2
#define MODULATION_CW 3
#define BK4819_AF_FM 1
#define BK4819_AF_BASEBAND2 2
#define BK4819_REG_3D 0x3d
#define FUNCTION_MONITOR 3
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
typedef unsigned BK4819_AF_Type_t;
typedef unsigned ModulationMode_t;
typedef struct { unsigned Modulation; } VFO_Info_t;
static VFO_Info_t vfo, *gRxVfo=&vfo, *gTxVfo=&vfo;
static struct { unsigned SQUELCH_LEVEL,CW_TONE_FREQUENCY; } gEeprom;
static bool gMonitor,gCW_CrossMode,s_rit_on,s_xit_on;
static int s_offset;
static L4S_State state;
static L4S_MenuState menu;
static bool tx_busy;
static bool can_retune(void) {return !tx_busy;}
static unsigned regs[256],listen_calls,gSetting_set_audio_fm,gSetting_set_audio_am;
static const unsigned afDacGainRegSpec=0x48,afcDisableRegSpec=0x73;
static void BK4819_WriteRegister(unsigned r,unsigned v) {regs[r]=v;}
static unsigned BK4819_ReadRegister(unsigned r) {return regs[r];}
static void BK4819_SetAF(unsigned v) {regs[0x47]=v;}
static void BK4819_SetRegValue(unsigned r,unsigned v) {regs[r]=v;}
static unsigned RADIO_ResolveFilter(const VFO_Info_t *v) {(void)v;return 0;}
static void BK4819_SetFilterBandwidth(unsigned bw,bool enable) {(void)bw;(void)enable;}
static void RADIO_SetupAGC(bool am,bool disabled) {(void)am;(void)disabled;}
static void RADIO_SetupRegisters(bool foreground) {(void)foreground;}
static void APP_StartListening(unsigned f) {(void)f;listen_calls++;}
static bool LocalOffsetAllowed(void) {return false;}
'''
        profiles = ('AUDIO_ApplyFMProfile', 'AUDIO_ApplyAMProfile', 'AUDIO_ApplyUSBProfile')
        harness += '\n#ifdef ENABLE_FEAT_F4HWN_AUDIO\n'
        harness += '\n'.join(function(radio, 'static void '+name+'(') for name in profiles)
        harness += '\n#endif\n'+function(radio, 'static void AUDIO_ApplyCWProfile(')
        harness += '\n'+function(radio, 'void RADIO_SetModulation(')
        harness += '\n'+function(control, 'bool L4S_ReceiveMonitor(')
        harness += '\n'+function(control, 'static void setup_receive(void)\n')
        harness += '\n'+function(control, 'static bool apply_rx_mode(')
        harness += '\n'+function(settings, 'static uint8_t change(')
        harness += '\n'+function(settings, 'bool L4S_MenuKey(')
        harness += '\n'+function(rit, 'uint32_t CW_RIT_RxFrequency(')
        harness += r'''
void select_rx(unsigned mode,unsigned sql) {
    vfo.Modulation=mode;gEeprom.SQUELCH_LEVEL=sql;listen_calls=0;
    RADIO_SetModulation(mode);setup_receive();
}
unsigned reg(unsigned r) {return regs[r];}
unsigned monitoring(void) {return gMonitor;}
unsigned listening(void) {return listen_calls;}
unsigned sql(void) {return gEeprom.SQUELCH_LEVEL;}
void audio_profile(unsigned fm,unsigned am) {gSetting_set_audio_fm=fm;gSetting_set_audio_am=am;}
uint32_t tuned(unsigned mode,uint32_t frequency) {
    vfo.Modulation=mode;gEeprom.CW_TONE_FREQUENCY=60;gCW_CrossMode=false;
    return CW_RIT_RxFrequency(&vfo,frequency);
}
void menu_reset(unsigned mode) {
    state=(L4S_State){0};menu=(L4S_MenuState){0};tx_busy=false;
    state.settings.mode=state.saved_settings.mode=mode;state.settings.power=3;
    state.rx_mode=mode==1 ? L4S_CW_MODE : mode==2 ? L4S_USB : L4S_FM;
    state.tx_mode=mode==1 || mode==2 ? L4S_CW_MODE : L4S_FM;
    state.applied=(L4S_Pair){435100000,145900000,4,true};state.mode_ready=true;
    menu.draft=state.settings;menu.draft.power=7;menu.open=true;menu.index=L4S_MENU_RX_MODE;
}
unsigned menu_key(unsigned key) {
    if(!L4S_MenuKey(&menu,key,tx_busy)) return 0;
    return menu.index==L4S_MENU_RX_MODE && apply_rx_mode(menu.draft.mode);
}
void busy(unsigned value) {tx_busy=value;state.tx_window_open=value;}
unsigned current_mode(void) {return state.settings.mode;}
unsigned saved_mode(void) {return state.saved_settings.mode;}
unsigned draft_mode(void) {return menu.draft.mode;}
unsigned current_power(void) {return state.settings.power;}
unsigned generation(void) {return state.profile_generation;}
unsigned modified(void) {return state.user_modified;}
unsigned pair_unchanged(void) {return state.applied.rx_hz==435100000 && state.applied.tx_hz==145900000 && state.applied.revision==4;}
unsigned menu_open(void) {return menu.open;}
unsigned editing(void) {return menu.editing;}
'''
        source = Path(cls.folder.name)/'receive.c'
        source.write_text(harness, encoding='utf-8')
        compiler = os.environ.get('L4S_HOST_CC') or shutil.which('gcc') or 'H:/tools/msys64/ucrt64/bin/gcc.exe'
        environment = dict(os.environ, PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
        for enabled in (False, True):
            binary = Path(cls.folder.name)/('receive-'+str(enabled)+('.dll' if os.name=='nt' else '.so'))
            command = [compiler, '-shared', '-O2', '-std=c11', '-I',str(ROOT/'App/app'),'-I',str(ROOT/'App'),str(source), '-o', str(binary)]
            if enabled:
                command.append('-DENABLE_FEAT_F4HWN_AUDIO')
            subprocess.run(command, check=True, env=environment)
            lib = ctypes.CDLL(str(binary))
            lib.tuned.argtypes = [ctypes.c_uint, ctypes.c_uint32]
            lib.tuned.restype = ctypes.c_uint32
            cls.libs.append(lib)

    @classmethod
    def tearDownClass(cls):
        if os.name == 'nt':
            import _ctypes
            for lib in cls.libs:
                _ctypes.FreeLibrary(lib._handle)
        cls.libs.clear()
        cls.folder.cleanup()

    def test_cw_profile_survives_disabled_optional_effects_and_mode_changes(self):
        for lib in self.libs:
            for previous in (0, 1, 2):
                lib.select_rx(previous, 0)
                lib.select_rx(3, 9)
                self.assertEqual(0x0500, lib.reg(0x2b))
                self.assertEqual(0x9009, lib.reg(0x54))
                self.assertEqual(0x31a9, lib.reg(0x55))
                lib.select_rx(2, 9)
                self.assertEqual(0, lib.reg(0x2b))

    def test_cw_usb_stay_open_without_overwriting_saved_squelch(self):
        for lib in self.libs:
            for mode in range(4):
                for sql in (0, 1, 9):
                    lib.select_rx(mode, sql)
                    expected = mode in (2, 3) or sql == 0
                    self.assertEqual(expected, bool(lib.monitoring()))
                    self.assertEqual(int(expected), lib.listening())
                    self.assertEqual(sql, lib.sql())

    def test_all_fm_am_effect_presets_remain_selectable(self):
        lib = self.libs[1]
        for index, expected in enumerate((0x3200, 0x33a9, 0x3600, 0x3af0, 0x3d00)):
            lib.audio_profile(index, 0);lib.select_rx(0, 0)
            self.assertEqual(expected, lib.reg(0x55))
        for index, expected in enumerate((0x9009, 0x9009, 0x8846)):
            lib.audio_profile(0, index);lib.select_rx(1, 0)
            self.assertEqual(expected, lib.reg(0x54))

    def test_switching_cw_usb_applies_bfo_once_without_changing_the_base(self):
        for lib in self.libs:
            base = 43510000
            self.assertEqual(base-60, lib.tuned(3, base))
            self.assertEqual(base, lib.tuned(2, base))
            self.assertEqual(base-60, lib.tuned(3, base))

    def test_menu_confirmation_only_changes_live_rx_and_not_other_drafts_or_flash(self):
        for lib in self.libs:
            lib.menu_reset(1)
            self.assertFalse(lib.menu_key(10))  # MENU: edit
            lib.menu_key(11)  # UP: choose USB
            self.assertEqual(2,lib.draft_mode());self.assertEqual(1,lib.current_mode())
            self.assertTrue(lib.menu_key(10))  # MENU: apply only RX
            self.assertEqual(2,lib.current_mode());self.assertEqual(1,lib.saved_mode())
            self.assertEqual(3,lib.current_power());self.assertEqual(1,lib.generation())
            self.assertTrue(lib.modified());self.assertTrue(lib.pair_unchanged())
            lib.menu_key(13)  # EXIT closes menu, keeps the confirmed selection
            self.assertFalse(lib.menu_open());self.assertEqual(2,lib.current_mode())

    def test_menu_cancel_fm_and_transmit_cannot_change_receive_mode(self):
        for lib in self.libs:
            lib.menu_reset(1);lib.menu_key(10);lib.menu_key(11);lib.menu_key(13)
            self.assertEqual(1,lib.current_mode());self.assertEqual(0,lib.generation())
            lib.menu_reset(0);lib.menu_key(10)
            self.assertFalse(lib.editing());self.assertEqual(0,lib.current_mode())
            lib.menu_reset(1);lib.menu_key(10);lib.menu_key(11);lib.busy(1)
            self.assertFalse(lib.menu_key(10));self.assertEqual(1,lib.current_mode())
            self.assertEqual(0,lib.generation())


if __name__ == '__main__':
    unittest.main()
