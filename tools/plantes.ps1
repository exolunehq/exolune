# Le catalogue des plantes du jeu, assets/foliage/climate_shrubs_v2 : télécharge les modèles sources (assets/foliage/README.md),
# les importe et cuit maillages, volumes et imposteurs. Une fois, depuis la racine du dépôt :
# powershell -NoProfile -ExecutionPolicy Bypass -File tools\plantes.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot)
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (!$python) { throw 'Python 3 est nécessaire pour construire le catalogue des plantes.' }
$etapes = @(
    @('-m', 'pip', 'install', '--quiet', 'numpy', 'pillow', 'numba', 'UnityPy'),
    @('tools/foliage/telecharge_jeu.py'),
    @('tools/foliage/importe_jeu.py'),
    @('tools/foliage/bake.py', 'game_fir', 'game_broadleaf', '--volume-res', '64'),
    @('tools/foliage/importe_arbuste.py'),
    @('tools/foliage/bake.py', 'game_shrub', '--volume-res', '64'),
    @('tools/foliage/volume_assets.py'),
    @('tools/foliage/volume_assets.py', '--normals'),
    @('tools/foliage/arbustes_climatiques_v2.py', '--preview'),
    @('tools/foliage/arbustes_climatiques_v2.py', '--final'),
    @('tools/foliage/prepare_vegetation_jeu.py', '--base', 'assets/foliage/climate_shrubs_v2')
)
foreach ($etape in $etapes) {
    Write-Host "python $($etape -join ' ')"
    & $python @etape
    if ($LASTEXITCODE -ne 0) { throw "Échec : python $($etape -join ' ')" }
}
# --preview redessine les planches de contrôle suivies par git : on garde celles du dépôt.
git checkout -- assets/foliage/climate_shrubs_v2/*.png 2>$null
# Publié à côté des dépôts, comme les scans : tous les worktrees du dépôt le trouvent en remontant depuis leur exe (D3DApp,
# « plantes »). À côté du dépôt principal, celui de git ; à côté de celui-ci hors de git.
$depot = Split-Path $PSScriptRoot
$commun = git -C $depot rev-parse --path-format=absolute --git-common-dir 2>$null
$racine = if ($LASTEXITCODE -eq 0 -and $commun) { Split-Path (Split-Path $commun) } else { Split-Path $depot }
$partage = Join-Path $racine 'plantes\climate_shrubs_v2'
New-Item -ItemType Directory -Force -Path $partage | Out-Null
Copy-Item -Recurse -Force (Join-Path $depot 'assets\foliage\climate_shrubs_v2\*') $partage
Write-Host "Catalogue prêt : assets/foliage/climate_shrubs_v2, publié dans $partage"
