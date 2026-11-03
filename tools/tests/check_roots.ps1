# Portable contact checks only. No GPU, interactive window or benchmark.
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
$out = Join-Path $repo 'x64\VegetationDiversity\RootChecks'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$oldInclude = $env:INCLUDE; $oldLib = $env:LIB
try {
    $env:INCLUDE = "$vc\include;$sdkInclude\ucrt;$sdkInclude\shared;$sdkInclude\um"
    $env:LIB = "$vc\lib\x64;$sdkLib\ucrt\x64;$sdkLib\um\x64"
    Push-Location $out
    try {
        & $compiler /nologo /std:c++17 /EHsc /O2 /W3 /Fe:root_contact_checks.exe (Join-Path $PSScriptRoot 'root_contact_checks.cpp') /link kernel32.lib
        if ($LASTEXITCODE -ne 0) { throw 'Root checks did not compile.' }
        & (Join-Path $out 'root_contact_checks.exe')
        if ($LASTEXITCODE -ne 0) { throw 'Root contact checks failed.' }
    } finally { Pop-Location }
} finally { $env:INCLUDE = $oldInclude; $env:LIB = $oldLib }
