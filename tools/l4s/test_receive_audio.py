"""Run production RX register setup with audio hardware replaced by a register bank."""
import ctypes
import os
from pathlib import Path
import subprocess
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
        harness = r'''
#include <stdbool.h>
#include <stdint.h>
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
'''
        source = Path(cls.folder.name)/'receive.c'
        source.write_text(harness, encoding='utf-8')
        compiler = os.environ.get('L4S_HOST_CC', 'H:/tools/msys64/ucrt64/bin/gcc.exe')
        for enabled in (False, True):
            binary = Path(cls.folder.name)/f'receive-{enabled}.dll'
            command = [compiler, '-shared', '-O2', '-std=c11', str(source), '-o', str(binary)]
            if enabled:
                command.append('-DENABLE_FEAT_F4HWN_AUDIO')
            subprocess.run(command, check=True)
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


if __name__ == '__main__':
    unittest.main()
