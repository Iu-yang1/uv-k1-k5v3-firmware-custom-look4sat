# Look4Sat L4S v1.0.5 — 100 Hz default satellite tracking step

**Hardware-validation pre-release.** For Quansheng UV-K1 / UV-K5 V3 (PY32F071) only; **not** the original UV-K5. Physical RF and direct USB-C tests remain outstanding.

## Changes from v1.0.4

- Set the initial L4S satellite/Doppler tuning step to **100 Hz** in both the protocol session and handset L4S control/menu state.
- Preserve user-selected **250 Hz** legacy satellite profiles and other valid explicit increments (10–10,000 Hz, in 10 Hz units); do not silently rewrite existing profiles.
- Preserve atomic independent RX/TX PAIR with 10 Hz transport resolution; no binary framing, opcodes or CAT wire-protocol changes.
- Preserve receive **USB** / transmit **CW** without a hidden 600 Hz receive offset.
- Retain v1.0.4 MAIN TX / DUAL RX pinned transmitter and F+2 receive-focus behavior, CW/PTT frequency hold, and USB recovery.
- Add host regression cases for 100 Hz profile/menu stepping, explicit 250 Hz legacy profiles, corrections, and separate RX/TX control.

## Validation and installation

Release CI compiles the native L4S host simulator, runs protocol/receive audio/dual-watch/100 Hz profile tests, compiles L4S firmware and an independent Fusion recovery image, and validates UF2/BIN identity, stack/reset vectors, at least 256 bytes of flash reserve and SHA-256 checksums. Hardware-level RF/PTT/USB-C verification is not claimed.

Back up calibration, channels, CW macros and satellite profiles. Keep a known-good Fusion recovery slot; do not overwrite calibration. Use F4HWN 6.3 multiboot / UV Studio according to your existing UV-K1/K5 V3 procedure. Re-confirm the **MAIN TX / DUAL RX** menu choice once when upgrading from v1.0.3 if an older EEPROM value could have pinned SUB. For radio transmit tests, use a dummy load.

Compatible Android application: Look4Sat-FT4 4.4.8-ba7opf.13.18 rebuilt with 100 Hz L4S defaults.

---

## 中文发布说明

**L4S v1.0.5：卫星跟踪默认步进调整为 100 Hz。** 属于实机验收前的迭代测试版，仅适用于 **UV-K1／UV-K5 V3（PY32F071）**，不适用于原版 UV-K5。

### 相对 v1.0.4 的更新

- 固件协议会话和手台 L4S 控制／菜单的初始卫星多普勒步进由 250 Hz 改为 **100 Hz**。
- 保留用户主动设置的 **250 Hz** 旧卫星预设以及其他合法步进（10–10,000 Hz，10 Hz 为单位），不擅自改写已有预设。
- 保留独立原子 RX/TX 频率对和 10 Hz 传输分辨率；不修改 CAT 二进制帧结构、命令或操作码。
- 保留 **USB 接收／CW 发射**，不自动加入 600 Hz 接收偏移。
- 保留 v1.0.4 修复的 MAIN TX / DUAL RX 主信道锁定、F+2 接收焦点切换、CW／PTT 发射期间频率保持及 USB 恢复功能。
- 新增 100 Hz 菜单与配置写入、旧 250 Hz 预设、修正值及双频控制的主机回归测试。

### 验证与刷机

发布 CI 编译 L4S 主机模拟器，运行协议、接收音频、双守候和 100 Hz 预设测试；重新构建 L4S 固件及独立 Fusion 恢复镜像，并验证 UF2/BIN 一致性、栈和复位向量、最少 256 字节剩余 Flash 以及 SHA-256 校验。**尚未执行实机射频、PTT 或 USB-C 直连验收。**

刷机前备份校准、信道、CW 宏和卫星预设，保留可靠的 Fusion 恢复槽，不覆盖校准区。沿用 UV-K1/K5 V3 的 F4HWN 6.3 multiboot／UV Studio 刷机方法。如果从可能错误保存 SUB 发射信道的 v1.0.3 升级，需重新确认一次 **MAIN TX / DUAL RX** 菜单设置。发射测试使用假负载。

适配的 Android 程序：重新构建的 Look4Sat-FT4 4.4.8-ba7opf.13.18（L4S 默认 100 Hz）。
