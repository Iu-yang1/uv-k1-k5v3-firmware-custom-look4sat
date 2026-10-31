# UV-K1 USB-C / L4S CDC recovery (2026-10-31)

## Observed problem

- Android (RMX5062) did not enumerate the UV-K1 on a direct C-to-C cable.
- Through a USB hub Android saw **36B7:FFFF** (PUYA CDC DEMO).
- Removing the UV-K1 battery briefly caused the USB device identity to appear.

These observations do **not** prove USB charging overload or MCU reset is the cause. CC pin termination, VBUS integrity, USB PHY reset timing and firmware enumeration remain competing hypotheses.

## Implemented

- `usb_dc_deinit()` gates USB interrupts, resets the USBD peripheral and disables its clock; `VCP_Init()` re-enables it.
- CherryUSB removes its configured status when deinitialized. CDC bus RESET invalidates DTR and the L4S session.
- `gVcpBootResetFlags`: RCC reset cause bits (capture once at startup).
- `gVcpRecoveryCount`: firmware USB re-enumeration count.
- `gVcpConfiguredCount`: successful USB configuration observations.
- Two bounded auto-recovery attempts are permitted if no host configuration was observed after startup. Auto retry stops after the first successful host configuration; it never loops forever.
- In the main screen: **F + long 7** manually reinitialize USB (RF/PTT idle only).
- In the main screen: **F + long 6** manually restart the MCU (diagnostic only, no transmit, flash-save request, or L4S session in progress).

## Device validation procedure

1. Save your known-good firmware and settings before flashing. First verify the build artifacts with GitHub Actions.
2. Fully charge the battery; use the same verified C-to-C data cable, phone, and USB hub for A/B tests.
3. With battery installed, connect directly and wait a few seconds; inspect the Android USB descriptor viewer for **36B7:FFFF**.
4. While idle, use **F + long 7** to rearm just the USB controller. Note whether device discovery becomes stable.
5. If still missing, use **F + long 6** to reset the entire MCU (the firmware only allows it when safe).
6. Repeat using the hub as a control. Do not transmit while testing without a stable power supply.

If no operation makes Android enumerate 36B7:FFFF when directly connected, the Android app cannot solve that absence of a USB device. Check CC1/CC2 termination, VBUS waveform and D+/D- signal integrity.

## Remaining hardware questions

This patch does not prove that resetting the USBD peripheral physically disconnects and reconnects the internal D+ pull-up in this board revision. Confirm a host sees detach -> attach on an oscilloscope/USB analyzer or Linux `dmesg`. Do not force PA11/PA12 high/low, bypass charge management, or flash blindly without a recovery path.
