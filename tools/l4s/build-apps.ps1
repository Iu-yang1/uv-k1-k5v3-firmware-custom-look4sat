param(
    [string]$CompilerRoot = 'H:/tools/arm-gnu-toolchain-15.2.rel1/bin',
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$output = Join-Path $repo 'build/Apps'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$compiler = Join-Path $CompilerRoot 'arm-none-eabi-gcc.exe'
$objcopy = Join-Path $CompilerRoot 'arm-none-eabi-objcopy.exe'
$source = Join-Path $repo 'App/apps/l4s/l4s_app.c'
$linker = Join-Path $repo 'App/apps/l4s/app.ld'
foreach ($module in @(@{Name='Look4Sat';Page=0}, @{Name='CWPractice';Page=1})) {
    $stem = Join-Path $output $module.Name
    & $compiler -mcpu=cortex-m0plus -mthumb -Os -std=gnu11 -ffreestanding -fno-builtin `
        -ffunction-sections -fdata-sections -Wall -Wextra -Werror -nostdlib -nostartfiles `
        "-DL4S_APP_PAGE=$($module.Page)" $source "-Wl,-T,$linker" '-Wl,--gc-sections' `
        '-Wl,--build-id=none' '-Wl,--no-warn-rwx-segment' -o "$stem.elf"
    if ($LASTEXITCODE -ne 0) { throw "Overlay compile failed: $($module.Name)" }
    & $objcopy -O binary "$stem.elf" "$stem.bin"
    if ($LASTEXITCODE -ne 0) { throw "Overlay binary conversion failed: $($module.Name)" }
    & $Python (Join-Path $repo 'App/apps/pack_app.py') "$stem.bin" "$stem.app" `
        --name $module.Name --ver '0.2-dev' --api-min 4 --vma 0x20000280 `
        --require l4s --exit-main
    if ($LASTEXITCODE -ne 0) { throw "Overlay packaging failed: $($module.Name)" }
}
