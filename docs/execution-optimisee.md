# Optimized execution

**Launch:** `powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance_optimise.ps1`.

- The launcher prepares `x64/Optimise/MyPlanetEngine.exe`, its shaders and `MyPlanetEngine.ini`; double-clicking this executable then reuses the profile.
- `-Build` rebuilds the Release x64 native code and shaders through the Planet launcher; `-NoLaunch` prepares the files without opening a window.
- Assets remain in the repository and scans at their configured location; this executable is not standalone.

**Display:**

- Borderless full screen on the primary monitor, at its native resolution at startup.
- VSync disabled in this profile; the application does not limit frame rate to refresh rate, subject to the compositor and driver.
- The DXGI unrestricted-presentation flag is used only if the system supports it; VRR compatibility depends on the driver and display.
- Alt+Enter switches between full screen and windowed mode; Esc returns to a window, then closes the application on the second press.
- F1–F12 retain the twelve vegetation views; the button palette appears in windowed mode.
- Switching to a window preserves internal resolution and stretches the image; no volume, HDR target or HiZ reallocation during flight.
- `-Fenetre` starts in a window; `-VSync` enables synchronization; `-Resolution '1280 720'` keeps the cost of 720p even in full screen. Choose the same aspect ratio as the display to avoid stretching.
- The profile records these choices in `[Affichage]`; `Resolution=auto` selects the monitor resolution for full screen, 1280×720 for windowless captures.
- `MYPLANETENGINE_FULLSCREEN`, `MYPLANETENGINE_VSYNC` and `MYPLANETENGINE_RESOLUTION` override the file; benchmarks remain invisible.

**Rendering and compilation:**

- A high-performance GPU is requested from DXGI; the selected GPU name, resolution and VSync appear in the title.
- Release x64: `/O2`, function inlining, speed preference, whole-program optimization and LTCG linking; no new floating-point approximations.
- Game vegetation, climate catalog, HiZ and hardware mesh depth; Planet clouds with shadows and FFT sea.
- Density, range and LOD thresholds preserved; Eco cloud quality as in the previous flight.
- Weather starts paused for comparisons; Space resumes it and V switches between ×1/×5.

**Cost and limits:**

- 1920×1080 has 2.25 times as many pixels as 1280×720; FPS at native resolution can fall despite unrestricted presentation.
- The profile promises neither a minimum FPS nor use of every CPU core; cloud, terrain and placement passes retain their cost.
- The engine still waits for GPU completion after every frame; shared allocators, constants and CPU reads require per-frame resources before allowing multiple frames in flight.
- No global Windows or driver settings are changed.

**References:** [DXGI, presentation and VRR](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/variable-refresh-rate-displays), [high-performance GPU preference](https://learn.microsoft.com/en-us/windows/win32/api/dxgi1_6/ne-dxgi1_6-dxgi_gpu_preference).

**October 28 checks:** three 720p views compared, one differing pixel in total; two 1080p views over forest and sea, without a window or vegetation overflow. Native full screen and return to windowed mode observed; no quantified overall FPS gain.
