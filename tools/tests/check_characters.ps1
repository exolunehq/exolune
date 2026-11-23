# Standalone CPU verification of the cooked CHR1/CHRPLC1 bank and ozz-animation evaluation. No GPU required.
param(
    [string]$Bank = 'E:\ExoluneAssets\characters-m1-2026-11-21\bank'
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$compiler = Get-ChildItem "${env:ProgramFiles}\Microsoft Visual Studio\2022\*\VC\Tools\MSVC\*\bin\Hostx64\x64\cl.exe" |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
if (!$compiler) { throw 'Visual Studio 2022 C++ is required.' }
$vc = Split-Path (Split-Path (Split-Path (Split-Path $compiler)))
$sdk = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\Include\*\um\windows.h" |
    Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
$sdkInclude = Split-Path (Split-Path $sdk)
$sdkVersion = Split-Path $sdkInclude -Leaf
$sdkLib = Join-Path (Split-Path (Split-Path $sdkInclude)) "Lib\$sdkVersion"
$out = Join-Path $repo 'x64\CharacterChecks'
New-Item -ItemType Directory -Path $out -Force | Out-Null

$ozzRoot = Join-Path $repo 'third_party\ozz-animation'
$ozzSources = @(
    'src\base\containers\string_archive.cc',
    'src\base\encode\group_varint.cc',
    'src\base\io\archive.cc',
    'src\base\io\stream.cc',
    'src\base\log.cc',
    'src\base\memory\allocator.cc',
    'src\base\platform.cc',
    'src\base\maths\box.cc',
    'src\base\maths\math_archive.cc',
    'src\base\maths\simd_math.cc',
    'src\base\maths\simd_math_archive.cc',
    'src\base\maths\soa_math_archive.cc',
    'src\animation\runtime\animation.cc',
    'src\animation\runtime\blending_job.cc',
    'src\animation\runtime\local_to_model_job.cc',
    'src\animation\runtime\sampling_job.cc',
    'src\animation\runtime\skeleton.cc'
) | ForEach-Object { Join-Path $ozzRoot $_ }

$oldInclude = $env:INCLUDE
$oldLib = $env:LIB
try {
    $env:INCLUDE = "$ozzRoot\include;$ozzRoot\src;$vc\include;$sdkInclude\ucrt;$sdkInclude\shared;$sdkInclude\um;$sdkInclude\winrt"
    $env:LIB = "$vc\lib\x64;$sdkLib\ucrt\x64;$sdkLib\um\x64"
    Push-Location $out
    try {
        & $compiler /nologo /std:c++17 /EHsc /O2 /W3 /D_CRT_SECURE_NO_WARNINGS /Fe:character_checks.exe (Join-Path $PSScriptRoot 'character_checks.cpp') @ozzSources /link kernel32.lib
        if ($LASTEXITCODE -ne 0) { throw 'Character checks did not compile.' }
        & (Join-Path $out 'character_checks.exe') $Bank
        if ($LASTEXITCODE -ne 0) { throw 'Character checks failed.' }
    } finally { Pop-Location }
} finally { $env:INCLUDE = $oldInclude; $env:LIB = $oldLib }
