# POC: stable and animated cloud

**Log since the 2026-10-30:** POC closed. The clouds in the game are described by `../spec-nuages.md`. Sources and test launcher: tag `piste/nuages-orbite-spike`, which contains the `codex/nuage-poc` branch.

**Goal:** a consistent training when approaching, which evolves with time. The fixed reference was validated in flight by the user on 26 October 2026. This iteration adds shared weather movement and lighter fringes. Branch `codex/nuage-poc`; end to end checks entrusted to the user on request.

**Lancer:** `powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuage-poc.ps1`. Add `-Build` after modification, `-Build -NoLaunch` to compile only. Animated binary: `x64/NuagePoc/MyPlanetEngineAnime.exe`. The previous binary can remain open: it is distinct. The executable and validated shaders are also retained in `x64/NuagePocReference/`; settings and measurements in `poc-nuage-stable-historique.md`.

**Controls:**
- **Space:** Pause or resume the weather, keeping the camera free.
- **V:** normal weather speed or ×5. The title bar gives the time, pause and speed.
- **B:** opacity in white on black, or lighted, to separate the outline of the lighting.
- **F1–F8:** far, approach, edge, entry, inside, other face, top and bottom. These views follow the cloud's movement without resetting the clock. Launch begins on approach, about 3,3 km from the center.
- Arrows to move, Page haut/bas to monter/descendre, right click and mouse to look, wheel for flight speed.

**Compare to fixed time:** `tools/nuage-poc.ps1 -Static`, or Space in the app. `-Time 60` starts at 60 seconds; F2 refocuses the view on the current cloud. The clock does not depend on the number of frames, camera movement, or view changes. The benchmarks without window keep the time set.

**Movement is a common field:**
- Wind to the east: shared rotation around the axis of the planet, 12 m/s at the equator, local velocity proportional to the cosine of latitude. The center and density coordinates use the same reverse displacement.
- Deformation: three wide space waves, periods 120, 150 and 200 s, evaluated in the coordinates of the planet driven by the wind. No phase shift related to the identity of a cloud. Displacements of 80, 40 and 60 m at most on the axis of the planet.
- Detail: common lift of about 1,71 m/s in the tile 3D. Periods and scroll loop continuously at 2 400 s; phases remain precise in floats.
- Cost: same tile, always two 3D readings per density evaluation; three analytical waves in more. No animated volumes to recalculate or additional weather cache.

**Less solid appearance:** maximum extinction from 24 to 16 /km, fringes broadened from 0,18 to 0,26 in the profile then softened to square, base more progressive and diffuse lighting from 0,18 to 0,22. The core remains opaque; the goal is a more vaporous envelope, not to make the whole cumulus transparent.

**What remains of the reference:** four lobes centered at 4 000 m, relative position subtracted in double precision precision; ray marching in full resolution, at most 384 not 12 m, six points towards the sun. Without cascade, checkerboard, jitter, time history or halo. The T key keeps smoothing off. Air is inserted at the opacity centroid, without feedback on the shape. No shadow of this cloud on the ground.

**Flight criteria:** in pause, same approach stability as the validated version. As it moves, the cloud drifts and its contours slowly evolve even with a still camera. Moving the camera should not accelerate or trigger this evolution. The break resumes without jump; F1–F8 do not rejuvenate the formation.

**Scope:** a single formation in the POC; the law of motion is shared and reusable, but the cloud cover of the planet is not integrated here. The lobes, densities and speeds are model settings. The normal rendering remains accessible without `MYPLANETENGINE_CLOUD_POC`.

**Files:** `CloudMotion.hlsli` for common field, `CloudPoc.hlsli` for density and lighting, `D3DApp.cpp` for clock and wind. All under `MyPlanetEngine/`. The full screen passage is compiled by DXC for fast iterations.

**Windowless controls:** `python tools/banc_nuage_poc.py <exe> <sortie> [--reference <exe-v1>]`. The benchmark compares a fixed camera at multiple times, follows the wind to isolate the deformation, returns at the same time after other views and controls the phase coupling to 2 400 s. Batch format: `sortie.bmp vue hauteur latitude longitude inclinaison cap [faceFactor [weatherTime]]`. `MYPLANETENGINE_WEATHER_TIME` sets the default time; `MYPLANETENGINE_VIEW=clouds` makes opacity actually integrated. The planetary quality benchmark remains outside the perimeter of this local POC.

**Validation of this iteration:** complete compilation and five benchmark checks successful. Returning to the same view and at the same time returns the same opacity to the pixel. Visible deformation after wind compensation and continuous connection to 2 400 s. Close-up view: 36 739 partially transparent pixels against 24 907 in reference. Median rendering measured at 2,75 ms versus 1,93 ms for the previous full version, on the same view of this station. Detail and limits in `../journal-planete.md`; local outputs in `x64/NuagePocAnimationCheck/`. Flight judgment expected from the user.
