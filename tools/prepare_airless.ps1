$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$compiler=Get-ChildItem "${env:ProgramFiles}\Microsoft Visual Studio\2022\*\VC\Tools\MSVC\*\bin\Hostx64\x64\cl.exe" | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
$vc=Split-Path (Split-Path (Split-Path (Split-Path $compiler)))
$sdk=Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\Include\*\um\windows.h" | Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
$inc=Split-Path (Split-Path $sdk)
$lib=Join-Path (Split-Path (Split-Path $inc)) ('Lib\'+(Split-Path $inc -Leaf))
$out=Join-Path $repo 'artifacts\lune-2026-11-08'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$oldInclude,$oldLib=$env:INCLUDE,$env:LIB
try {
    $env:INCLUDE="$vc\include;$inc\ucrt;$inc\shared;$inc\um"
    $env:LIB="$vc\lib\x64;$lib\ucrt\x64;$lib\um\x64"
    Push-Location $out
    try {
        & $compiler /nologo /std:c++17 /EHsc /O2 /W4 /Fe:prepare_airless.exe (Join-Path $PSScriptRoot 'prepare_airless.cpp') (Join-Path $repo 'MyPlanetEngine\AirlessTerrain.cpp')
        if($LASTEXITCODE -ne 0){throw 'Airless cook did not compile.'}
        & (Join-Path $out 'prepare_airless.exe') (Join-Path $repo 'assets\celestial')
        if($LASTEXITCODE -ne 0){throw 'Airless cook failed.'}
        $sources=@('MyPlanetEngine\CelestialManifest.h','MyPlanetEngine\AirlessField.hlsli','MyPlanetEngine\AirlessTerrain.cpp','tools\prepare_airless.cpp')
        $provenance=[ordered]@{ sources=@($sources | ForEach-Object { @{path=$_;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo $_)).Hash} });
            atlases=@(Get-ChildItem -LiteralPath (Join-Path $repo 'assets\celestial') -Filter 'airless*.rgba8mips' | ForEach-Object { @{file=$_.Name;bytes=$_.Length;sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash} }) }
        $provenance | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $repo 'assets\celestial\airless-provenance.json')
    } finally {Pop-Location}
} finally {$env:INCLUDE,$env:LIB=$oldInclude,$oldLib}
