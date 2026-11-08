# Functional stills from the flight review route. No benchmark, score or timing collection.
param([string]$Views='1,2,3,7,8,10,12', [switch]$CloudFull, [switch]$Cockpit,
    [ValidateRange(5,150)][int]$Fov=60, [string]$Resolution='1280 720',
    [string]$ReviewPath='2026-11-07-ciel.txt', [string]$OutputName='ciel-2026-11-07')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if(Get-Process MyPlanetEngine -ErrorAction SilentlyContinue) { throw 'Close the running game before capturing.' }
$route=Get-Content (Join-Path $PSScriptRoot $ReviewPath) | Where-Object { $_ -match '^[^#].*\|' }
$previous=@{}
Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object { $previous[$_.Name]=$_.Value }
try {
    Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    foreach($number in $Views.Split(',')) {
        $index=[int]$number
        if($index -lt 1 -or $index -gt $route.Count) { throw 'Invalid review view.' }
        $parts=$route[$index-1].Split('|')
        $pose=$parts[1].Trim() -split '\s+'
        $alt,$lat,$lon,$pitch,$heading=$pose
        $upward=(-[double]::Parse($pitch,[cultureinfo]::InvariantCulture)).ToString([cultureinfo]::InvariantCulture)
        $suffix=$(if($CloudFull){'-full'}else{''})+$(if($Cockpit){'-cockpit'}else{''})+$(if($Fov -ne 60){"-fov$Fov"}else{''})
        $folder=Join-Path (Join-Path $repo "artifacts\$OutputName") ('{0:00}{1}' -f $index,$suffix)
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        $view=$(if($Cockpit){'cockpit'}else{'pleine'})
        $line="0 $view $lat $lon $alt $heading $upward 0 $lat $lon $alt $heading $upward 0 $Fov 0"
        [IO.File]::WriteAllText((Join-Path $folder 'pose.txt'),"fps 60`n$line`n")
        $env:MYPLANETENGINE_CINE=Join-Path $folder 'pose.txt'
        $env:MYPLANETENGINE_CINE_OUT=$folder
        $env:MYPLANETENGINE_CINE_RANGE='0 1 40'
        $env:MYPLANETENGINE_RESOLUTION=$Resolution
        $env:MYPLANETENGINE_SUN=$parts[2].Trim()
        $env:MYPLANETENGINE_SCANS=Join-Path (Split-Path $repo) 'scans'
        if($CloudFull) { $env:MYPLANETENGINE_CLOUD_FULL='1' }
        $exe=Join-Path $repo 'x64\Release\MyPlanetEngine.exe'
        $process=Start-Process -FilePath $exe -WorkingDirectory (Split-Path $exe) -WindowStyle Hidden -PassThru
        $process.WaitForExit()
        if($process.ExitCode -ne 0) { throw "Capture $index failed: $($process.ExitCode)" }
        Get-Item (Join-Path $folder 'frame_00000.bmp') | Select-Object FullName,Length
    }
} finally {
    Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object { Remove-Item -LiteralPath "Env:$($_.Name)" }
    foreach($key in $previous.Keys) { Set-Item -LiteralPath "Env:$key" -Value $previous[$key] }
}
