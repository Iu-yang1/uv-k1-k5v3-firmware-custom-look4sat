# Look4Sat L4S v1.0.4 — MAIN TX DUAL RX hardware-validation correction

**Pre-release / hardware validation.** For Quansheng **UV-K1 / UV-K5 V3 (PY32F071)** only. Not compatible with the original UV-K5. This release supersedes v1.0.3's MAIN TX DUAL RX handling but does not claim real-radio RF certification.

## Corrected regression from v1.0.3

When MAIN TX DUAL RX was selected, pressing **F+2** to focus the opposite SUB/RX row silently changed both `TX_VFO` and the `CROSS_BAND_RX_TX` MAIN anchor. Although v1.0.3 used `gTxVfo` for TX, that variable had already moved to SUB. The actual output could follow SUB instead of MAIN.

In v1.0.4:
- **Lock MAIN at mode selection.** The `CROSS_BAND_RX_TX` setting identifies the pinned MAIN transmitter (1=A, 2=B).
- **F+2 changes the RX/editing focus only** while MAIN TX DUAL RX is active; it no longer reassigns MAIN. Switching focus back is supported.
- **PTT, CW keyer, TX frequency, mode, power, CTCSS/DCS and error state** use the pinned MAIN; the on-screen TX indicator also follows MAIN.
- **Regular Dual Watch without MAIN TX lock** retains its normal talk-back semantics. Other cross-band modes retain their existing VFO re-selection behavior.
- Retains v1.0.3's **L4S USB RX / CW TX without automatic 600 Hz BFO correction**, USB recovery, satellite profiles and API-4 overlay compatibility. No BK4829 RF-register or CAT protocol changes.
- Firmware reports `v1.0.4-l4s` in its version string.

## Reproduction / verification

To test MAIN=A (434.815 MHz) and SUB=B (439.815 MHz), select A first, enable MAIN TX DUAL RX, then press F+2 to focus B. The receive/editing marker can move to B while **PTT must transmit on the originally anchored A**. Repeat with MAIN=B and SUB=A. Use authorized test frequencies and a **dummy load with an SDR or frequency counter**.

Automated tests execute the production F+2 switch routine and transmitter VFO selection, and check the TX programming source. The publishing workflow rebuilds L4S and Fusion from the exact release commit, requires 256 bytes minimum free Flash, validates BIN/UF2 correspondence, image vectors and SHA-256, and compares all published assets with the package.

**Automation cannot certify real RF output, spur levels, CW audio response, or USB-C direct connection.** Do not consider this a stable hardware-validated release until the on-radio tests pass.

## Installation and files

Back up calibration, channels, CW macros and satellite profiles before flashing. Keep a known-good Fusion recovery slot. Install using the normal F4HWN 6.3 Multiboot / UV Studio workflow. Do not overwrite calibration data or flash onto the original UV-K5, and do not transmit on USB-only power.

Release ZIP includes UV-K1/K5 V3 L4S BIN and UF2, Fusion recovery BIN, `INSTALL.txt`, `verification.json` and `SHA256SUMS.txt`. The original v1.0.3 release remains available as an earlier test build.

See [PR #4](https://github.com/Iu-yang1/uv-k1-k5v3-firmware-custom-look4sat/pull/4).

---

## 中文发布说明

**L4S v1.0.4 MAIN TX DUAL RX 发射信道修正迭代测试版。** 仅适用于 **UV-K1／UV-K5 V3（PY32F071）**，不适用于原版 UV-K5。未完成实机射频验收，故仍以 Pre-release 发布。

### v1.0.3 遗留问题的真正原因

v1.0.3 虽然让发射过程使用 `gTxVfo`，但按 **F+2** 切换到 SUB 时，`COMMON_SwitchVFOs()` 还会修改 `TX_VFO` 并重写 `CROSS_BAND_RX_TX`，导致原本的 MAIN 发射信道被转移到 SUB。

**v1.0.4 修复后：** 选择 MAIN TX DUAL RX 时锁定 MAIN A/B；之后 F+2 可以切换接收、编辑焦点，但不能改变锁定的 MAIN。PTT 与 CW 键控、发射频率、功率、发射模式、亚音频及 TX 指示均以 MAIN 为准。普通双守候模式保留原有回话行为。

保留原有 USB RX / CW TX（不自动添加 600 Hz 频率偏移）、USB 恢复、卫星远控和 API-4 插件兼容性。固件版本号已更新为 `v1.0.4-l4s`。

### 实机验收

以截图中的上方 434.815 MHz 为 MAIN、下方 439.815 MHz 为 SUB，先选定 MAIN 并进入 MAIN TX DUAL RX，再按 F+2 切换到 SUB 监听，按下 PTT 必须在最初锁定的 MAIN 发射。随后交换 A/B 重复验证。

**请使用假负载与频率计／SDR，并确保测试频率符合许可；不要依赖发射红灯或 UI 文本判断实际 RF 频率。** CI 通过不能替代实机检查。刷机前备份校准和数据，保留 Fusion 恢复槽，不要覆盖校准区，也不要在仅 USB 供电时发射。
