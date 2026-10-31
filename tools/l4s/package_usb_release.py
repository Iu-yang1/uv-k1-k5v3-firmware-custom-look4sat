#!/usr/bin/env python3
"""Fail-closed packaging for L4S USB recovery test releases.

Build artifacts are produced by the repository's pinned Docker build.
Never publish a firmware image that exhausts the 512-byte flash reserve.
"""
import argparse
import hashlib
import json
import shutil
import struct
import sys
import zipfile
from pathlib import Path

FLASH_LIMIT = 118 * 1024
MIN_FREE_BYTES = 512
UF2_START = (0x0A324655, 0x9E5D5157)
UF2_END = 0x0AB16F30
UF2_BASE = 0x08002800


def verify_uf2(image: bytes, raw: bytes) -> None:
    if not image or len(image) % 512:
        raise ValueError("UF2 blocks must be exactly 512 bytes")
    block_count = len(image) // 512
    payload = bytearray()
    for index in range(block_count):
        block = image[index * 512:(index + 1) * 512]
        words = struct.unpack_from("<8I", block)
        if words[:2] != UF2_START or struct.unpack_from("<I", block, 508)[0] != UF2_END:
            raise ValueError(f"UF2 magic mismatch in block {index}")
        flags, address, length, number, total, family = words[2:]
        if (flags & 1) or (flags & 0x2000) or address != UF2_BASE + index * 256:
            raise ValueError(f"Unexpected UF2 flashing parameters in block {index}")
        if length != 256 or number != index or total != block_count:
            raise ValueError(f"UF2 block indices mismatch at {index}")
        payload.extend(block[32:32 + length])
    if payload[:len(raw)] != raw or any(payload[len(raw):]):
        raise ValueError("UF2 does not round-trip to the source BIN")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--out", default="dist")
    args = p.parse_args()

    out = Path(args.out)
    out.mkdir(exist_ok=True, parents=True)
    src_bin = Path("build/L4S/look4sat.f4hwn630.bin")
    src_uf2 = Path("build/L4S/look4sat.f4hwn630.uf2")
    src_recovery = Path("build/Fusion/f4hwn.fusion.bin")
    for source in (src_bin, src_uf2, src_recovery):
        if not source.is_file():
            raise FileNotFoundError(f"Missing required firmware image {source}")

    raw = src_bin.read_bytes()
    free = FLASH_LIMIT - len(raw)
    print(f"L4S image: {len(raw)} B; physical budget: {FLASH_LIMIT} B; free: {free} B")
    if free < MIN_FREE_BYTES:
        raise ValueError(f"Refusing release: L4S flash free {free} B < {MIN_FREE_BYTES} B")

    if len(raw) < 8:
        raise ValueError("L4S image too small to contain vectors")
    sp, reset = struct.unpack_from("<2I", raw)
    if not (0x20000000 <= sp < 0x20008000) or not (reset & 1):
        raise ValueError("Invalid firmware stack/reset vectors")

    verify_uf2(src_uf2.read_bytes(), raw)

    prefix = f"look4sat-{args.tag}-f4hwn630-k1-k5v3"
    assets = {
        f"{prefix}.bin": src_bin,
        f"{prefix}.uf2": src_uf2,
        "recovery-Fusion-v6.3.0.bin": src_recovery,
    }
    for target, source in assets.items():
        shutil.copy2(source, out / target)

    info = {
        "tag": args.tag,
        "source_commit": args.sha,
        "hardware": "UV-K1 / UV-K5 V3 PY32F071 only",
        "flash_limit_bytes": FLASH_LIMIT,
        "flash_used_bytes": len(raw),
        "flash_free_bytes": free,
        "minimum_flash_reserve_bytes": MIN_FREE_BYTES,
        "uf2_base_address": hex(UF2_BASE),
        "uf2_matches_bin": True,
        "release_type": "hardware-validation prerelease",
        "usb_c_direct_connection": "not verified on physical radio",
    }
    (out / "verification.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")

    install = (
        "L4S v1.0.2 USB recovery test build for UV-K1 / UV-K5 V3 PY32F071.\n"
        "NOT compatible with original UV-K5. Hardware USB-C direct enumeration unverified.\n"
        "Back up calibration, channels, satellite profiles and firmware first.\n"
        "Use UV Studio / multiboot with a working Fusion recovery slot.\n"
        "Never overwrite calibration or restore an old full flash dump.\n"
        "While NOT transmitting: F + long 7 = USB re-enumeration.\n"
        "While NOT transmitting or saving: F + long 6 = MCU reset diagnostic.\n"
        "If direct C-C still fails, inspect CC1/CC2, VBUS and USB D+/D-.\n"
    )
    (out / "INSTALL.txt").write_text(install, encoding="utf-8")
    name = f"Look4Sat-L4S-{args.tag}-k1-k5v3.zip"
    with zipfile.ZipFile(out / name, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for f in sorted(out.iterdir()):
            if f.is_file() and f.suffix in (".bin", ".uf2", ".json", ".txt"):
                archive.write(f, f.name)

    with (out / "SHA256SUMS.txt").open("w", encoding="utf-8") as checksums:
        for f in sorted(out.iterdir()):
            if f.name == "SHA256SUMS.txt" or not f.is_file():
                continue
            checksums.write(f"{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.name}\n")

    print(f"Release ready: {len(list(out.iterdir()))} assets, UF2 verified, flash reserve {free} B")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(f"Packaging failed: {exc}")
