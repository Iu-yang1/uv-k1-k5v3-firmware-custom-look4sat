/* Copyright 2026 Iu_yang1. SPDX-License-Identifier: Apache-2.0 */
APP_VMA = 0x20000280;
ENTRY(app_main)
MEMORY { APP (rwx) : ORIGIN = APP_VMA, LENGTH = 0x1000 }
SECTIONS {
    .app APP_VMA : {
        KEEP(*(.text.entry))
        *(.text .text.* .rodata .rodata.* .data .data.*)
        . = ALIGN(4);
        *(.bss .bss.* COMMON)
        . = ALIGN(4);
    } > APP
    ASSERT(SIZEOF(.app) <= 0x1000, "L4S overlay exceeds 4 KiB")
    /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.eh_frame*) *(.comment) *(.note.*) }
}
