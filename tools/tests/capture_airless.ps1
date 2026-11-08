# Functional flight-route stills. No performance/quality benchmark or score comparison.
param([string]$Views='1,2,3,4,5,6,8,9,11',[int]$Frames=240,[string]$OutputName='lune-2026-11-08',[string]$Resolution='1280 720',[string]$Route='2026-11-08-lune.txt',[ValidateSet('sans','libre','cockpit','poursuite')][string]$Camera='sans',[string]$Exe='')
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
if(Get-Process | Where-Object ProcessName -like 'MyPlanetEngine*'){throw 'Another engine is using the GPU.'}
if(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -match '\b(banc_\w+|abn|site_views|exact|review_native)\.py\b' }) {
    throw 'A benchmark or native capture runner is active, including its intervals between engine processes.'
}
$previous=@{}
Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object {$previous[$_.Name]=$_.Value}
try {
    Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object {Remove-Item -LiteralPath "Env:$($_.Name)"}
    foreach($view in $Views.Split(',')) {
        if(Get-Process | Where-Object ProcessName -like 'MyPlanetEngine*'){throw 'Another engine is using the GPU.'}
        if(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -match '\b(banc_\w+|abn|site_views|exact|review_native)\.py\b' }) {
            throw 'A benchmark or native capture runner became active; no further engine will be launched.'
        }
        $out=Join-Path $repo ("artifacts\$OutputName\view-{0:00}.bmp" -f [int]$view)
        New-Item -ItemType Directory -Path (Split-Path $out) -Force | Out-Null
        $env:MYPLANETENGINE_TESTS=Join-Path $PSScriptRoot $Route
        $env:MYPLANETENGINE_FIRST_TEST=$view
        $env:MYPLANETENGINE_CAPTURE=$out
        $env:MYPLANETENGINE_CAPTURE_FRAME="$Frames"
        $env:MYPLANETENGINE_RESOLUTION=$Resolution
        $env:MYPLANETENGINE_VSYNC='0'
        $env:MYPLANETENGINE_SCANS=Join-Path (Split-Path $repo) 'scans'
        $env:MYPLANETENGINE_VAISSEAU=$Camera
        $info=New-Object System.Diagnostics.ProcessStartInfo
        $info.FileName=if($Exe){(Resolve-Path -LiteralPath $Exe).Path}else{Join-Path $repo 'x64\Release\MyPlanetEngine.exe'}
        $info.WorkingDirectory=Split-Path $info.FileName
        $info.UseShellExecute=$false;$info.CreateNoWindow=$true;$info.WindowStyle='Hidden';$info.RedirectStandardError=$true
        [IO.File]::WriteAllLines(($out+'.launch.txt'),@('exe='+$info.FileName,'capture='+$info.EnvironmentVariables['MYPLANETENGINE_CAPTURE'],
            'cine='+$info.EnvironmentVariables['MYPLANETENGINE_CINE'],'batch='+$info.EnvironmentVariables['MYPLANETENGINE_BATCH']))
        $process=New-Object System.Diagnostics.Process
        $process.StartInfo=$info
        [void]$process.Start()
        $errors=$process.StandardError.ReadToEnd()
        $process.WaitForExit()
        if($errors){[IO.File]::WriteAllText(($out+'.error.txt'),$errors)}
        if($process.ExitCode -ne 0){throw "View $view failed: $($process.ExitCode) $errors"}
        Get-Item -LiteralPath $out | Select-Object FullName,Length
    }
} finally {
    Get-ChildItem Env: | Where-Object Name -like 'MYPLANETENGINE_*' | ForEach-Object {Remove-Item -LiteralPath "Env:$($_.Name)"}
    foreach($key in $previous.Keys){Set-Item -LiteralPath "Env:$key" -Value $previous[$key]}
}
