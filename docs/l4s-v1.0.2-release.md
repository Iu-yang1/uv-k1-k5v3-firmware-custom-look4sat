## Look4Sat L4S v1.0.2 — USB CDC recovery iteration

**Hardware validation release (pre-release).** Dedicated firmware for **UV-K1 / UV-K5 V3 (PY32F071)** only. **Not compatible with the original UV-K5.** Firmware source includes merged [PR #1](https://github.com/Iu-yang1/uv-k1-k5v3-firmware-custom-look4sat/pull/1); pair it with the Android app changes in [Look4Sat-FT4 PR #17](https://github.com/Iu-yang1/Look4Sat-FT4/pull/17).

### Changes

- Implement USB device-controller deinitialization/reinitialization in the PY32F071 CherryUSB port. Mask interrupt before clearing CDC interfaces; reset USB peripheral and endpoint state.
- Clear stale DTR and abort the remote L4S session after USB bus reset. Resume using the existing CDC DTR and L4S HELLO/OPEN handshake.
- Record boot reset cause (`gVcpBootResetFlags`), USB successful configuration and recovery counters for diagnostics.
- Allow only two startup re-enumeration attempts. Never automatically reboot the whole radio.
- Idle handset diagnostics: **F + long 7** restarts USB peripheral; **F + long 6** performs software MCU reset when no transmission, save or L4S session is in progress.
- Build outputs are gated on at least **256 bytes of free application flash**, then verified for UF2 block identity, flash base and BIN payload.

### Build capacity and verification

The size-optimized L4S image is **120,568 / 120,832 bytes** (only **264 bytes free**). This narrow reserve is acceptable for the specific USB hardware-validation pre-release only; keep a reliable recovery slot and do not treat it as a production-stable update. Full firmware build and multiboot RAM stub checks pass in CI.

### Install and safety

Back up radio calibration, channels, macros and satellite profiles, and keep a known-good Fusion recovery slot. Install via the normal F4HWN Multiboot/UV Studio procedure. Do not overwrite calibration, use on an original UV-K5 or test RF transmit from USB-only power.

**Real USB-C C-to-C enumeration and charging/power-path behavior are not certified by CI.** If the phone cannot detect `36B7:FFFF` directly, a firmware change cannot compensate for missing CC pin termination, insufficient VBUS or a broken D+/D− electrical path. Compare direct C-C and Hub connections and collect ADB USB host diagnostics.

The API-4 `Look4Sat.app` / `CWPractice.app` launchers from v1.0.0 remain compatible; this iteration does not modify their API. The ZIP also contains a Fusion 6.3 reference/recovery BIN, installation notes, checksums and a verification report.

---

## 中文说明

**L4S v1.0.2 USB 连接恢复迭代测试版。** 仅适用于 PY32F071 的 UV-K1 / UV-K5 V3，不适用于原版 UV-K5。本次包含固件 PR #1 与配套 Android 应用 PR #17 的 USB 恢复改动。

- 修复 CherryUSB 在 PY32 上无法真正反初始化 USB 外设的问题，清理中断、控制器与 USB 配置状态。
- USB RESET 后撤销 DTR 和旧 L4S 会话，避免重连后沿用陈旧的远程发射状态。
- 记录 MCU 上电复位原因；开机后最多执行两次 USB 重新枚举尝试，不无限循环重启。
- 主屏幕 **F + 长按 7**：仅重启 USB 外设；**F + 长按 6**：安全条件满足时执行 MCU 软件复位诊断。
- 发布构建要求应用 Flash 至少剩余 256 字节，并验证 UF2 与 BIN 内容一致。

刷机前备份校准、频道、宏及卫星档案，保留 Fusion 恢复槽。通过既有 F4HWN Multiboot / UV Studio 刷入，不要覆盖校准区。

**注意：本次尚未通过 UV-K1 + 手机 C-C 直连实机验证。** USB-C CC、电源与充电路径仍可能是枚举失败原因。请先在安全接收状态下测试，切勿在仅 USB 供电的情况下发射。
