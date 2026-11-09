# Functional stills using the normal game rendering; one GPU engine at a time.
param([string]$Vue = 'foret', [string]$Sortie = 'artifacts\navigateur-jeu-2026-11-03')
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if (Get-Process MyPlanetEngine -ErrorAction SilentlyContinue) { throw 'Close the running game before the capture.' }
$out = Join-Path $repo (Join-Path $Sortie $Vue)
$views = Get-Content (Join-Path $repo 'artifacts\navigateur-jeu-2026-11-03\views.json') -Raw | ConvertFrom-Json
$sun = ($views | Where-Object name -eq $Vue).sun
if (!$sun) { throw 'Unknown inspection view.' }
$previous = @{}
Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object { $previous[$_.Name]=$_.Value }
try {
    Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    $env:MYPLANETENGINE_CINE = Join-Path $out 'pose.txt'
    $env:MYPLANETENGINE_CINE_OUT = $out
    $env:MYPLANETENGINE_CINE_RANGE = '0 1 40'
    $env:MYPLANETENGINE_RESOLUTION = '1280 720'
    $env:MYPLANETENGINE_MODELE_VAISSEAU = 'navigateur'
    $env:MYPLANETENGINE_SUN = $sun
    $env:MYPLANETENGINE_SCANS = (Resolve-Path (Join-Path $repo '..\scans')).Path
    $env:MYPLANETENGINE_TAA = '1'
    $exe = Join-Path $repo 'x64\Release\MyPlanetEngine.exe'
    $process = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -PassThru
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "Capture failed: $($process.ExitCode)" }
    Get-Item (Join-Path $out 'frame_00000.bmp') | Select-Object FullName,Length
} finally {
    Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    foreach ($key in $previous.Keys) { Set-Item -LiteralPath "Env:$key" -Value $previous[$key] }
}
