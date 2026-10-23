#!/usr/bin/env bash
# Copyright 2026 Iu-yang1. SPDX-License-Identifier: Apache-2.0
set -euo pipefail
repo="$(cd "$(dirname "$0")/../.." && pwd)"
name="${1:?module name}"
page="${2:?native page}"
cc="${CC:-arm-none-eabi-gcc}"
objcopy="${OBJCOPY:-arm-none-eabi-objcopy}"
python="${PYTHON:-python3}"
"$cc" -mcpu=cortex-m0plus -mthumb -Os -std=gnu11 -ffreestanding -fno-builtin \
    -ffunction-sections -fdata-sections -Wall -Wextra -Werror -nostdlib -nostartfiles \
    "-DL4S_APP_PAGE=$page" "$repo/App/apps/l4s/l4s_app.c" \
    "-Wl,-T,$repo/App/apps/l4s/app.ld" -Wl,--gc-sections -Wl,--build-id=none \
    -Wl,--no-warn-rwx-segment -o "$name.elf"
"$objcopy" -O binary "$name.elf" "$name.bin"
"$python" "$repo/App/apps/pack_app.py" "$name.bin" "$name.app" \
    --name "$name" --ver 0.2-dev --api-min 4 --vma 0x20000280 \
    --require l4s --exit-main
