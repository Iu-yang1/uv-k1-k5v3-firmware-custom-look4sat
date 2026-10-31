/* Copyright 2025 muzkr https://github.com/muzkr
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 *     Unless required by applicable law or agreed to in writing, software
 *     distributed under the License is distributed on an "AS IS" BASIS,
 *     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *     See the License for the specific language governing permissions and
 *     limitations under the License.
 *
 */

#include "driver/vcp.h"
#include "usb_config.h"
#include "py32f071_ll_bus.h"
#include "driver/system.h"
#include "usbd_core.h"
#include "usbd_cdc.h"
#include "functions.h"
#include "driver/gpio.h"

#ifdef ENABLE_FEAT_F4HWN_K5VIEWER
#include "driver/keyboard.h"
#endif

/* Reset cause is captured once per boot; USB restarts never clear it. */
volatile uint32_t gVcpBootResetFlags;
volatile uint32_t gVcpRecoveryCount;
volatile uint32_t gVcpConfiguredCount;
static bool gVcpResetFlagsCaptured;
static bool gVcpWasConfigured;
static uint8_t gVcpRecoveryTicks;
static uint8_t gVcpRecoveryAttempts;

uint8_t VCP_RxBuf[VCP_RX_BUF_SIZE];
volatile uint32_t VCP_RxBufPointer = 0;

void VCP_Init(void)
{
    if (!gVcpResetFlagsCaptured) {
        gVcpBootResetFlags = RCC->CSR & (RCC_CSR_OBLRSTF | RCC_CSR_PINRSTF |
            RCC_CSR_PWRRSTF | RCC_CSR_SFTRSTF | RCC_CSR_IWDGRSTF | RCC_CSR_WWDGRSTF);
        RCC->CSR |= RCC_CSR_RMVF;
        gVcpResetFlagsCaptured = true;
    }
    LL_APB1_GRP2_EnableClock(LL_APB1_GRP2_PERIPH_SYSCFG);
    LL_IOP_GRP1_EnableClock(LL_IOP_GRP1_PERIPH_GPIOA); // PA12:11
    LL_APB1_GRP1_EnableClock(LL_APB1_GRP1_PERIPH_USBD);

    cdc_acm_rx_buf_t rx_buf = {
        .buf = VCP_RxBuf,
        .size = sizeof(VCP_RxBuf),
        .write_pointer = &VCP_RxBufPointer,
    };
    cdc_acm_init(rx_buf);

    NVIC_SetPriority(USBD_IRQn, 3);
    NVIC_EnableIRQ(USBD_IRQn);
}

/* Called in the foreground only: the controller reset drops the on-chip
 * USB device state, while leaving radio state and the MCU running. */
bool VCP_RestartUsb(void)
{
    if (gCurrentFunction == FUNCTION_TRANSMIT || GPIO_IsPttPressed()) return false;
    /* Cancel the old L4S session and its PTT lease before re-enumeration. */
    usbd_cdc_acm_set_dtr(0, false);
    if (usbd_deinitialize() != 0) return false;
    SYSTEM_DelayMs(150);
    VCP_RxBufPointer = 0;
    gVcpWasConfigured = false;
    VCP_Init();
    gVcpRecoveryCount++;
    return true;
}

/* Two bounded retries after boot, never a permanent periodic reset loop.
 * A missing VBUS/CC indication is NOT proof that a host is attached. */
void VCP_RecoveryTick500ms(bool radioTransmitting)
{
    if (usb_device_is_configured()) {
        if (!gVcpWasConfigured) gVcpConfiguredCount++;
        gVcpWasConfigured = true;
        gVcpRecoveryTicks = 0;
        return;
    }
    if (gVcpWasConfigured || radioTransmitting || gVcpRecoveryAttempts >= 2) return;
    if (gVcpRecoveryTicks < 24) ++gVcpRecoveryTicks;
    if (gVcpRecoveryTicks == (gVcpRecoveryAttempts == 0 ? 8 : 24)) {
        ++gVcpRecoveryAttempts;
        if (VCP_RestartUsb()) gVcpRecoveryTicks = 0;
    }
}

#ifdef ENABLE_FEAT_F4HWN_K5VIEWER
static uint8_t      k5v_read_ptr = 0;
static ParseState_t k5v_state    = STATE_IDLE;

/* Skip what arrived while an overlay app owned the port (its serial data is
 * no K5Viewer traffic) and restart the parser from a clean state. */
void VCP_K5ViewerSync(void)
{
    k5v_read_ptr = (uint8_t)VCP_RxBufPointer;
    k5v_state    = STATE_IDLE;
}

bool VCP_K5ViewerPing(void)
{
    // State machine for parsing incoming packets:
    //   Keepalive:       0x55 0xAA 0x00 0x00    → viewer alive, no extensions
    //   Feature keepalive (ENABLE_FEAT_F4HWN_RXTX_LOG_K5VIEWER builds only):
    //                    0x55 0xAA 0x05 <flags> → viewer alive, extensions enabled
    //                    flags bit 0 = RF log stream
    //                    flags bit 1 = paged RF log history
    //                    flags bit 7 = restart RF log synchronization
    //   Short key press: 0xAA 0x55 0x03 <key>   → inject short press
    //   Long key press:  0xAA 0x55 0x04 <key>   → inject long press
    //
    // State transitions:
    //   IDLE  → 0x55 → KA_1
    //   KA_1  → 0xAA → KA_2       (else IDLE)
    //   KA_2  → 0x00 → KA_3       (else 0x05 → KA_FEATURE, else IDLE)
    //   KA_3  → 0x00 → keepalive OK, clear extensions, IDLE
    //   KA_FEATURE → <flags> → keepalive OK, set extensions, IDLE
    //
    //   IDLE   → 0xAA → KEY_1
    //   KEY_1  → 0x55 → KEY_2     (else IDLE)
    //   KEY_2  → 0x03 → KEY_3     (short press, else check long)
    //   KEY_2  → 0x04 → KEY_3L    (long press, else IDLE)
    //   KEY_3  → <b>  → KEYBOARD_InjectKey(b, false), IDLE
    //   KEY_3L → <b>  → KEYBOARD_InjectKey(b, true), IDLE

    uint8_t  read_ptr  = k5v_read_ptr;
    bool     connected = false;
    uint8_t  write_ptr = VCP_RxBufPointer;  // snapshot once — ISR may update concurrently

    // Cap bytes processed per call to VCP_RX_BUF_SIZE.
    // Prevents unbounded loop if the ISR write pointer laps read_ptr
    // (buffer overflow / corrupted state), which would freeze the firmware.
    uint32_t processed = 0;

    while (read_ptr != write_ptr && processed < VCP_RX_BUF_SIZE)
    {
        uint8_t b = VCP_RxBuf[read_ptr];

        read_ptr++;
        if (read_ptr >= VCP_RX_BUF_SIZE)
            read_ptr = 0;
        processed++;

        if(KEYBOARD_ProcessProtocolByte(&k5v_state, b))
            connected = true;
    }

    k5v_read_ptr = read_ptr;
    return connected;
}
#endif // ENABLE_FEAT_F4HWN_K5VIEWER
