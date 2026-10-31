# Prepare un runtime Release : double-clic sur MyPlanetEngine.exe ensuite.
param(
    [switch]$Build,
    [switch]$NoLaunch,
    [switch]$Fenetre,
    [switch]$VSync,
    [ValidatePattern('^(auto|[0-9]{3,4} [0-9]{3,4})$')][string]$Resolution = 'auto',
    [string]$Position = '1770.9 30.68685 120.10788 32.0 -64.7',
    [string]$Soleil = '20 120',
    [string]$Scans = $(if ($env:MYPLANETENGINE_SCANS) { $env:MYPLANETENGINE_SCANS } else { Join-Path $env:USERPROFILE 'Documents\repos\MyPlanetEngine\scans' })
)
$ErrorActionPreference='Stop'
if ($Resolution -ne 'auto') {
    $dimensions=$Resolution.Split(' ')
    $width=[int]$dimensions[0]; $height=[int]$dimensions[1]
    if ($width -lt 320 -or $height -lt 180 -or $width -gt 8192 -or $height -gt 8192) {
        throw 'Resolution hors limites : largeur320–8192, hauteur180–8192.'
    }
}
$repoRoot=Split-Path $PSScriptRoot
if ($Build) {
    & (Join-Path $PSScriptRoot 'lance.ps1') -Build -NoLaunch
}
$source=Join-Path $repoRoot 'x64\Release'
$sourceExe=Join-Path $source 'MyPlanetEngine.exe'
if (!(Test-Path -LiteralPath $sourceExe)) { throw 'Runtime absent : lancer tools/lance_optimise.ps1 -Build.' }
$Scans=(Resolve-Path -LiteralPath $Scans -ErrorAction Stop).Path
foreach ($relative in 'assets\clouds\shape128.rgba8mips','assets\foliage\climate_shrubs_v2\shrubs.txt') {
    if (!(Test-Path -LiteralPath (Join-Path $repoRoot $relative))) { throw "Asset absent : $relative" }
}
$out=Join-Path $repoRoot 'x64\Optimise'
$exe=Join-Path $out 'MyPlanetEngine.exe'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$running=Get-Process MyPlanetEngine -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe }
foreach ($file in @((Get-Item -LiteralPath $sourceExe)) + @(Get-ChildItem -LiteralPath $source -Filter '*.cso')) {
    $name=if ($file.Extension -eq '.exe') { 'MyPlanetEngine.exe' } else { $file.Name }
    $dest=Join-Path $out $name
    if ((Test-Path -LiteralPath $dest) -and (Get-FileHash -LiteralPath $dest).Hash -eq (Get-FileHash -LiteralPath $file.FullName).Hash) { continue }
    if ($running) { throw 'Fermer la version Optimise avant de remplacer son executable ou ses shaders.' }
    Copy-Item -LiteralPath $file.FullName -Destination $dest -Force
}
$fullscreen=if ($Fenetre) { 0 } else { 1 }
$sync=if ($VSync) { 1 } else { 0 }
$profile=@"
[Affichage]
PleinEcran=$fullscreen
VSync=$sync
Resolution=$Resolution

[Rendu]
Racine=..\..
Scans=$Scans
VegetationDetaillee=1

[Camera]
Position=$Position
Soleil=$Soleil
"@
[System.IO.File]::WriteAllText((Join-Path $out 'MyPlanetEngine.ini'),$profile,[System.Text.Encoding]::Unicode)
Write-Output "Runtime : $exe"
Write-Output "Plein ecran : $fullscreen ; resolution : $Resolution ; VSync : $sync. Alt+Entree : fenetre/plein ecran ; Echap : fenetre puis quitter."
if ($NoLaunch) { return }
$previous=@{}
Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { $previous[$_.Name]=$_.Value }
try {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    Start-Process -FilePath $exe -WorkingDirectory $out # its profile sets the screen, the scans, the palette and the view (Settings.cpp)
} finally {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    foreach ($key in $previous.Keys) { Set-Item -LiteralPath "Env:$key" -Value $previous[$key] }
}
