# Functional CPU checks only; no GPU or performance benchmark.
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$compiler=Get-ChildItem "${env:ProgramFiles}\Microsoft Visual Studio\2022\*\VC\Tools\MSVC\*\bin\Hostx64\x64\cl.exe" | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
$vc=Split-Path (Split-Path (Split-Path (Split-Path $compiler)))
$sdk=Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\Include\*\um\windows.h" | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
$inc=Split-Path (Split-Path $sdk)
$lib=Join-Path (Split-Path (Split-Path $inc)) ('Lib\'+(Split-Path $inc -Leaf))
$out=Join-Path $repo 'artifacts\vol-libre-2026-11-08'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$oldInclude,$oldLib=$env:INCLUDE,$env:LIB
try {
    $env:INCLUDE="$vc\include;$inc\ucrt;$inc\shared;$inc\um"
    $env:LIB="$vc\lib\x64;$lib\ucrt\x64;$lib\um\x64"
    Push-Location $out
    try {
        & $compiler /nologo /std:c++14 /EHsc /O2 /W4 /Fe:flight_frame_checks.exe (Join-Path $PSScriptRoot 'flight_frame_checks.cpp')
        if($LASTEXITCODE -ne 0){throw 'Flight frame checks did not compile.'}
        & (Join-Path $out 'flight_frame_checks.exe')
        if($LASTEXITCODE -ne 0){throw 'Flight frame checks failed.'}
    } finally {Pop-Location}
} finally {$env:INCLUDE,$env:LIB=$oldInclude,$oldLib}
