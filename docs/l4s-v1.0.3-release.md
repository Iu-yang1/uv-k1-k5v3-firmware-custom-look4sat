# Look4Sat L4S v1.0.3 — CW reception and MAIN TX DUAL RX correction

**Hardware-validation iteration.** Intended exclusively for **Quansheng UV-K1 / UV-K5 V3 using PY32F071**, **not** the original UV-K5. Builds on F4HWN 6.3.0 and retains the v1.0.2 USB CDC recovery changes. This version has **not** completed on-radio RF/USB hardware validation.

## Changes since v1.0.2

- **L4S satellite CW: RX USB / TX CW.** When the phone requests CW reception with CW transmit, the firmware applies the existing USB receive path and retains CW transmission. The effective RX/TX modes are reported back to the phone. Older CW satellite profiles are normalized **in RAM** without rewriting stored Flash profiles.
- **No automatic 600 Hz offset.** USB receive does not apply the CW-only BFO tuning shift. A CW carrier close to the displayed RX frequency may be near zero beat; adjust **RX frequency manually** to obtain the desired audible pitch. The TX frequency is not shifted.
- **MAIN TX DUAL RX.** PTT now uses the selected MAIN VFO for TX frequency, modulation, power and subaudio tone, even when dual-watch reception is currently on DUAL. The UI's TX-channel indicator is consistent with the active TX VFO. Ordinary dual-watch talk-back behavior is retained.
- **Retains v1.0.2 USB recovery.** The established F + long 7 USB reset and F + long 6 safe MCU reset diagnostics remain available under their existing safety conditions.
- Existing API-4 Look4Sat / CWPractice overlays remain compatible. The firmware's CAT wire protocol, profile schema and satellite TX Doppler handling are unchanged.

## Verification

- GitHub Actions: **39/39 targeted host regressions passed**, including actual C VFO selection function and displayed TX channel selection extracted from source.
- Docker firmware/toolchain build for Fusion, Transfer, FieldOps, Labs and L4S passed on the PR baseline. The L4S image measured **120,556 / 120,832 bytes**, leaving **276 bytes** (minimum packaging reserve: 256 bytes).
- The publishing workflow **rebuilds** both L4S and the Fusion rescue image from its exact source commit. It rejects insufficient Flash reserve, checks firmware vectors, verifies UF2 block layout and byte-for-byte BIN payload equivalence, creates a manifest and SHA-256 checksums.
- Source-change aislop review was run; the scan includes pre-existing warnings/errors in large touched files. It is not a substitute for RF validation.

**The final ZIP's `verification.json` contains the authoritative image size and source commit for this release.**

## Install and hardware safety

1. Back up calibration, channels, macros, satellite profiles and current firmware. Keep a known-good Fusion recovery slot.
2. Use F4HWN 6.3 Multiboot / UV Studio to load the **L4S BIN or UF2 for PY32F071 UV-K1 / UV-K5 V3 only**. Do not overwrite calibration or restore an old full flash dump.
3. To verify MAIN TX DUAL RX, configure MAIN and DUAL with distinct, authorized frequencies, receive on DUAL, then use a **dummy load** and an SDR/frequency counter to confirm PTT remains on MAIN. Verify both MAIN=A and MAIN=B.
4. Compare USB RX/CW TX with the older CW receive mode using a calibrated test signal; no automatic BFO correction is performed.
5. Do not transmit from USB-only power. Direct C-to-C enumeration and physical charging/USB power-path behavior remain unverified.

### Included release assets

- `look4sat-l4s-v1.0.3-f4hwn630-k1-k5v3.bin`
- `look4sat-l4s-v1.0.3-f4hwn630-k1-k5v3.uf2`
- `recovery-Fusion-v6.3.0.bin`
- `Look4Sat-L4S-l4s-v1.0.3-k1-k5v3.zip`
- `verification.json`, `INSTALL.txt`, `SHA256SUMS.txt`

See [PR #2](https://github.com/Iu-yang1/uv-k1-k5v3-firmware-custom-look4sat/pull/2) and [PR #3](https://github.com/Iu-yang1/uv-k1-k5v3-firmware-custom-look4sat/pull/3) for the exact source changes.

---

## 中文发布说明

**L4S v1.0.3 收发模式与双守候修复迭代版。** 只适用于 **PY32F071 的 UV-K1 / UV-K5 V3**，**不适用于原版 UV-K5**。保留 v1.0.2 的 USB CDC 恢复功能，属于**尚未完成实机射频验收的硬件验证版本**。

### 本次变化

- **Look4Sat CW 使用 USB 接收、CW 发射**：手机请求 CW/CW 时自动采用现有 USB 接收通道，但发射继续使用 CW。协议状态回报实际生效的接收模式。旧 CW 卫星档案只在内存中转换，不改写原有 Flash 记录。
- **不添加 600 Hz 自动频偏**：USB 接收不再执行 CW 专用的 BFO 偏移。若 CW 载波与 RX 调谐频率重合，可能接近零拍，需自行微调 RX；**不会调整 TX 频率**。
- **修复 MAIN TX DUAL RX**：无论双守候当前停留在 MAIN 还是 DUAL，PTT 始终使用选定 MAIN 的发射频率、模式、功率及 CTCSS/DCS，修正了界面 TX 指示。普通 Dual Watch 的回话行为不变。
- 保留 **F + 长按 7** 的 USB 重枚举、**F + 长按 6** 的安全 MCU 复位诊断；不改变 CAT 协议、卫星上下行控制和已有 API-4 模块兼容性。

### 自动验证与限制

PR 基线的 **39 项主机回归测试全部通过**，此前 L4S 完整构建为 **120,556 / 120,832 字节**，剩余 **276 字节**（最低预留 256 字节）。发布流水线会重新构建并验证固件，最终准确数值以 ZIP 中的 `verification.json` 为准。**未完成实机射频、USB-C 直连及 CW 听感验收。**

刷机前备份校准数据、频道、卫星档案和固件，并保留 Fusion 恢复槽；不要覆盖校准区。请使用假负载和频率计/SDR 检查 MAIN=A/B 时的发射信道，避免在未授权频率上发射。**禁止仅靠 USB 供电进行发射测试。**
