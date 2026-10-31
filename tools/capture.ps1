# Runs MyPlanetEngine with MYPLANETENGINE_CAPTURE set: it renders without showing its window, saves its own frame
# and quits. Nothing is read from the screen, and the user's focus is never taken. Prints the window's last title
# (heights, rings, GPU times), which the engine writes next to the capture; older builds, which show their window,
# are read from it.
param([string]$Out, [string]$AppArgs = "", [string]$Exe = "C:\Users\etien\Documents\repos\MyPlanetEngine\MyPlanetEngine\x64\Debug\MyPlanetEngine.exe")
Add-Type -AssemblyName System.Drawing
$bmp = [System.IO.Path]::ChangeExtension($Out, ".bmp")
$titleFile = "$bmp.txt"
Remove-Item $bmp, $Out, $titleFile -ErrorAction SilentlyContinue
$env:MYPLANETENGINE_CAPTURE = $bmp
if ($AppArgs) { $p = Start-Process $Exe -ArgumentList $AppArgs -WindowStyle Minimized -PassThru }
else { $p = Start-Process $Exe -WindowStyle Minimized -PassThru }
Remove-Item Env:\MYPLANETENGINE_CAPTURE
$title = ""
$deadline = (Get-Date).AddSeconds(60)
while (-not $p.HasExited -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 200
    $p.Refresh()
    if ($p.MainWindowTitle -like "*fps*") { $title = $p.MainWindowTitle }
}
if (-not $p.HasExited) { $p | Stop-Process -Force; "TIMEOUT" }
if (Test-Path $titleFile) {
    $title = [System.IO.File]::ReadAllText($titleFile, [System.Text.Encoding]::UTF8)
    Remove-Item $titleFile
}
if (Test-Path $bmp) {
    $img = [System.Drawing.Image]::FromFile($bmp)
    $img.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
    $img.Dispose()
    Remove-Item $bmp
}
else { "NO CAPTURE" }
$title -replace '^MyPlanetEngine \| ', ''
