# Les photos de sol du moteur (Scans.cpp, kScans) : Poly Haven, CC0, hors du dépôt, dans ..\scans\<nom>\<nom>_*.
# Les télécharge quand elles manquent, ou toutes avec -Force. Usage : powershell -File tools\telecharger_scans.ps1
param(
    [string]$Scans = $(if ($env:MYPLANETENGINE_SCANS) { $env:MYPLANETENGINE_SCANS } else { Join-Path (Split-Path (Split-Path $PSScriptRoot)) 'scans' }),
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$names = 'sandy_gravel_02', 'marble_cliff_04', 'marble_cliff_05'
$files = @{ 'diff_2k.jpg' = 'jpg'; 'disp_2k.png' = 'png' }
foreach ($name in $names) {
    $dir = Join-Path $Scans $name
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    foreach ($suffix in $files.Keys) {
        $file = Join-Path $dir "${name}_$suffix"
        if ((Test-Path -LiteralPath $file) -and -not $Force) { continue }
        $url = "https://dl.polyhaven.org/file/ph-assets/Textures/$($files[$suffix])/2k/$name/${name}_$suffix"
        Write-Host "$url"
        Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing
    }
}
Get-ChildItem -LiteralPath $Scans -Recurse -File | ForEach-Object { '{0,8:N1} Mo  {1}' -f ($_.Length / 1MB), $_.FullName.Substring($Scans.Length + 1) }
