# Le lanceur du jeu : compile au besoin, puis ouvre MyPlanetEngine.exe en plein écran avec la palette « Tests », un bouton
# par ligne du fichier de tests et F1 à F12 (D3DApp, MYPLANETENGINE_TESTS). Le jeu est le comportement par défaut de l'exe :
# le lanceur ne pose que la palette, le soleil, l'écran et les scans. Les MYPLANETENGINE_* de la session sont effacées le
# temps du lancement, puis restaurées.
#
# powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 [-Build] [-NoLaunch] [-Parcours tools\tests\<date>.txt]
#     [-Position '<alt> <lat> <lon> <tangage> <cap>'] [-Soleil '<lat> <lon>'] [-Resolution '1920 1080' | fenetre]
#     [-PassePleine] [-SansNuages] [-Exe <exécutable>] [-Scans <dossier>]
param(
    [switch]$Build,
    [switch]$NoLaunch,
    [string]$Parcours = (Join-Path $PSScriptRoot 'tests\vues.txt'),
    [string]$Position = '10000000 -0.5 -18.225 90 0',
    [string]$Soleil = '10 -5',
    # Plein écran à cette résolution, celle des bancs ; 'fenetre' pour la fenêtre 1280x720, où la palette s'affiche.
    [string]$Resolution = '1920 1080',
    # Les nuages en passe unique, sans leur passe temporelle (docs/optimisation.md) : pour comparer.
    [switch]$PassePleine,
    # Masquer les nuages pour examiner le terrain ; N les réaffiche pendant le vol.
    [switch]$SansNuages,
    # Un autre exécutable que x64\Release, par exemple une compilation à part (x64\Verif).
    [string]$Exe = '',
    [string]$Scans = $(if ($env:MYPLANETENGINE_SCANS) { $env:MYPLANETENGINE_SCANS } else { Join-Path (Split-Path (Split-Path $PSScriptRoot)) 'scans' })
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot
$exe = if ($Exe) { (Resolve-Path -LiteralPath $Exe).Path } else { Join-Path $repoRoot 'x64\Release\MyPlanetEngine.exe' }

if ($Build) {
    $msbuild = Get-ChildItem "${env:ProgramFiles}\Microsoft Visual Studio\2022\*\MSBuild\Current\Bin\MSBuild.exe" |
        Select-Object -First 1 -ExpandProperty FullName
    if (!$msbuild) { throw 'MSBuild de Visual Studio 2022 est nécessaire pour compiler.' }
    & $msbuild (Join-Path $repoRoot 'MyPlanetEngine.sln') /t:Build /p:Configuration=Release /p:Platform=x64 /m /nologo /verbosity:minimal
    if ($LASTEXITCODE -ne 0) { throw 'Échec de la compilation.' }
}
if ($NoLaunch) { return }
if (!(Test-Path -LiteralPath $exe)) { throw "Exécutable absent, lancer avec -Build : $exe" }
# Les scans, à côté du dépôt par défaut : téléchargés une fois s'ils manquent, 28 Mo.
if (!(Test-Path -LiteralPath $Scans)) { & (Join-Path $PSScriptRoot 'telecharger_scans.ps1') -Scans $Scans | Out-Null }
$tests = (Resolve-Path -LiteralPath $Parcours).Path

$previous = @{}
Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { $previous[$_.Name] = $_.Value }
try {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    $env:MYPLANETENGINE_TESTS = $tests
    $env:MYPLANETENGINE_SCANS = (Resolve-Path -LiteralPath $Scans).Path
    $env:MYPLANETENGINE_SUN = $Soleil
    if ($Resolution -ne 'fenetre') { $env:MYPLANETENGINE_RESOLUTION = $Resolution; $env:MYPLANETENGINE_FULLSCREEN = '1' }
    if ($PassePleine) { $env:MYPLANETENGINE_CLOUD_FULL = '1' }
    if ($SansNuages) { $env:MYPLANETENGINE_NO_CLOUDS = '1' }
    Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -ArgumentList $Position
} finally {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    foreach ($key in $previous.Keys) { Set-Item -LiteralPath "Env:$key" -Value $previous[$key] }
}
