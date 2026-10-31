# Film par plages, sans fenêtre, sans conserver les BMP déjà encodés.
param(
    [Parameter(Mandatory=$true)][string]$Parcours,
    [Parameter(Mandatory=$true)][string]$Sortie,
    [string]$Resolution = '1920 1080',
    [int]$Plage = 600,
    [int]$Chauffe = 120,
    [string]$FFmpeg = 'C:\ProgramData\chocolatey\bin\ffmpeg.exe',
    # L'exe à rendre, x64\Release par défaut ; le soleil, « lat lon » de son point subsolaire.
    [string]$Exe = '',
    [string]$Soleil = ''
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$exe = if ($Exe) { (Resolve-Path -LiteralPath $Exe).Path } else { Join-Path $root 'x64\Release\MyPlanetEngine.exe' }
$path = (Resolve-Path -LiteralPath $Parcours).Path
if (!(Test-Path -LiteralPath $exe)) { throw 'Compiler avec tools\lance.ps1 -Build -NoLaunch.' }
if (!(Test-Path -LiteralPath $FFmpeg)) { throw "ffmpeg absent : $FFmpeg" }
$probe = Join-Path (Split-Path $FFmpeg) 'ffprobe.exe'
if (!(Test-Path -LiteralPath $probe)) { throw 'ffprobe requis à côté de ffmpeg.' }
if ($Plage -lt 1 -or $Chauffe -lt 0) { throw 'Plage positive et chauffe non négative.' }
if ($Resolution -notmatch '^(\d+) (\d+)$' -or [int]$Matches[1] % 2 -or [int]$Matches[2] % 2) { throw 'Résolution paire : largeur hauteur.' }
$renderWidth = [int]$Matches[1]; $renderHeight = [int]$Matches[2]
if ($renderWidth -lt 320 -or $renderHeight -lt 180 -or $renderWidth -gt 8192 -or $renderHeight -gt 8192) { throw 'Résolution entre 320x180 et 8192x8192.' }
$lines = @(Get-Content -LiteralPath $path | ForEach-Object { ($_ -split '#',2)[0].Trim() } | Where-Object { $_ })
if ($lines.Count -lt 2 -or $lines[0] -notmatch '^fps\s+60$') { throw 'Cette chaîne encode les parcours à 60 images/s.' }
$count = $lines.Count - 1
for ($i=0; $i -lt $count; ++$i) {
    if (($lines[$i+1] -split '\s+')[0] -cne [string]$i) { throw "Index non contigu : $i" }
}
$null = New-Item -ItemType Directory -Force -Path $Sortie
$out = (Resolve-Path -LiteralPath $Sortie).Path
$frames = Join-Path $out 'images'
$null = New-Item -ItemType Directory -Force -Path $frames
# Résoudre le dossier une fois ; tout effacement reste dans ce sous-dossier.
$frames = (Resolve-Path -LiteralPath $frames).Path
if (!(($frames + '\').StartsWith($out + '\', [StringComparison]::OrdinalIgnoreCase))) { throw 'Dossier images hors sortie.' }
$signature = [ordered]@{
    parcours=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    moteur=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
    shaders=@(Get-ChildItem -LiteralPath (Split-Path $exe) -Filter '*.cso' | Sort-Object Name | ForEach-Object { (Get-FileHash -LiteralPath $_.FullName).Hash })
    resolution=$Resolution; plage=$Plage; chauffe=$Chauffe; images=$count; crf=14
}
$manifest = Join-Path $out 'rendu.json'
$json = $signature | ConvertTo-Json -Depth 4
if (Test-Path -LiteralPath $manifest) {
    if ((Get-Content -LiteralPath $manifest -Raw).Trim() -cne $json.Trim()) { throw 'Parcours, moteur ou réglages modifiés : choisir un autre dossier de sortie.' }
} else { [IO.File]::WriteAllText($manifest, $json, [Text.UTF8Encoding]::new($false)) }

function Assert-Video([string]$File, [int]$Expected) {
    $video = & $probe -v error -select_streams v:0 -count_frames -show_entries stream=codec_name,pix_fmt,nb_read_frames,width,height,r_frame_rate -of json $File | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $video.streams.Count -ne 1 -or [int]$video.streams[0].nb_read_frames -ne $Expected -or $video.streams[0].r_frame_rate -ne '60/1' -or
        $video.streams[0].codec_name -ne 'h264' -or $video.streams[0].pix_fmt -ne 'yuv420p' -or
        [int]$video.streams[0].width -ne $renderWidth -or [int]$video.streams[0].height -ne $renderHeight) {
        throw "Vidéo incomplète : $File (attendu $Expected images à 60 Hz)."
    }
}
function Clear-Frames([int]$First, [int]$Number) {
    for ($j=$First; $j -lt $First+$Number; ++$j) {
        $bmp = Join-Path $frames ('frame_{0:d5}.bmp' -f $j)
        if (Test-Path -LiteralPath $bmp) { Remove-Item -LiteralPath $bmp }
    }
}
function Test-Frame([int]$Index) {
    $bmp = Join-Path $frames ('frame_{0:d5}.bmp' -f $Index)
    return (Test-Path -LiteralPath $bmp) -and (Get-Item -LiteralPath $bmp).Length -eq (54L+4L*$renderWidth*$renderHeight)
}
$previous = @{}
Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { $previous[$_.Name]=$_.Value }
try {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    $env:MYPLANETENGINE_CINE = $path
    $env:MYPLANETENGINE_CINE_OUT = $frames
    $env:MYPLANETENGINE_RESOLUTION = $Resolution
    $env:MYPLANETENGINE_FULLSCREEN = '0'
    $env:MYPLANETENGINE_VSYNC = '0'
    $env:MYPLANETENGINE_TAA = '1'
    if ($Soleil) { $env:MYPLANETENGINE_SUN = $Soleil }
    # Garder les chemins de ressources explicitement choisis par l'utilisateur.
    foreach ($resource in @('MYPLANETENGINE_SCANS','MYPLANETENGINE_FOLIAGE_ASSETS')) {
        if ($previous.ContainsKey($resource)) { Set-Item -LiteralPath "Env:$resource" -Value $previous[$resource] }
    }
    $parts = @()
    for ($first=0; $first -lt $count; $first += $Plage) {
        $number = [Math]::Min($Plage, $count-$first)
        $name = 'plage_{0:d5}.mp4' -f $first
        $part = Join-Path $out $name
        $parts += "file '$name'"
        if (Test-Path -LiteralPath $part) {
            Assert-Video $part $number
            Clear-Frames $first $number
            Write-Output "Reprise : $name déjà encodée."
            continue
        }
        $complete = $true
        for ($j=$first; $j -lt $first+$number; ++$j) {
            if (!(Test-Frame $j)) { $complete=$false; break }
        }
        if (!$complete) {
            # Seul un moteur du même dossier partage les caches ; un autre ne fait que partager le GPU.
            if (Get-Process MyPlanetEngine -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exe }) { throw 'Ce MyPlanetEngine est déjà ouvert ; le fermer avant de rendre. Aucun processus arrêté.' }
            Clear-Frames $first $number
            $env:MYPLANETENGINE_CINE_RANGE = "$first $number $Chauffe"
            Write-Output "Rendu : $first..$($first+$number-1), chauffe $Chauffe."
            $process = Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -PassThru -Wait `
                -RedirectStandardOutput (Join-Path $out "moteur_$first.stdout.txt") -RedirectStandardError (Join-Path $out "moteur_$first.stderr.txt")
            if ($null -eq $process.ExitCode -or $process.ExitCode -ne 0) { throw "Échec du moteur ($($process.ExitCode)) ; voir $path.error.txt et images/cine.log." }
        } else { Write-Output 'Reprise : images complètes, encodage.' }
        for ($j=$first; $j -lt $first+$number; ++$j) {
            if (!(Test-Frame $j)) { throw "Image absente ou incomplète : $j" }
        }
        $temporary = Join-Path $out ('plage_{0:d5}.part.mp4' -f $first)
        & $FFmpeg -hide_banner -loglevel warning -y -framerate 60 -start_number $first -i (Join-Path $frames 'frame_%05d.bmp') `
            -frames:v $number -an -c:v libx264 -preset slow -crf 14 -pix_fmt yuv420p -r 60 -movflags +faststart $temporary
        if ($LASTEXITCODE -ne 0) { throw 'Échec encodage ; BMP conservés.' }
        Assert-Video $temporary $number
        Move-Item -LiteralPath $temporary -Destination $part
        Clear-Frames $first $number
    }
    $list = Join-Path $out 'concat.txt'
    [IO.File]::WriteAllLines($list, $parts, [Text.UTF8Encoding]::new($false))
    $film = Join-Path $out 'film.part.mp4'
    & $FFmpeg -hide_banner -loglevel warning -y -f concat -safe 0 -i $list -c copy -movflags +faststart $film
    if ($LASTEXITCODE -ne 0) { throw 'Échec concaténation ; plages conservées.' }
    Assert-Video $film $count
    $final = Join-Path $out 'film.mp4'
    Move-Item -LiteralPath $film -Destination $final -Force
    Write-Output "Film : $final"
} finally {
    Get-ChildItem Env: | Where-Object { $_.Name -like 'MYPLANETENGINE_*' } | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    foreach ($key in $previous.Keys) { Set-Item -LiteralPath "Env:$key" -Value $previous[$key] }
}
