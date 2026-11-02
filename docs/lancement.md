# Launch the app

**The executable alone runs the game:** `x64\Release\MyPlanetEngine.exe`, without any environment variables. For an in-flight review, `tools/lance.ps1` builds it if needed, then opens it with the “Tests” palette.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Build -NoLaunch
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\<date>.txt
```

## Before the first launch in a worktree

**Plant binaries are not versioned:** `assets/foliage/.gitignore` excludes them. Without them, the app flies without plants and its title says “végétation absente” (vegetation missing).

- **Flight catalog:** `assets/foliage/climate_shrubs_v2`, two trees and twelve shrubs.
- **Build it once** from the root: `tools\plantes.ps1` downloads the source models (`assets/foliage/README.md`), imports them and bakes the catalog. Python 3 is required; about 3 minutes and 750 MB. It is placed alongside the repositories, in `plantes/climate_shrubs_v2`, where every worktree finds it.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\plantes.ps1
```

- **Missing scans** are downloaded by `tools\lance.ps1` on first launch.

- **Impostors from 2026-10-29:** colors averaged in linear space (`vegetation-planetaire.md`, impostor lighting). A catalog built before `7f462fc` retains the older, darker impostors. Rebake only those, without changing meshes or volumes:

```powershell
python tools/foliage/bake.py --impostor-only --out assets/foliage/climate_shrubs_v2 game_broadleaf game_fir shrub_boreal_0 shrub_boreal_1 shrub_desert_0 shrub_desert_1 shrub_montane_0 shrub_montane_1 shrub_steppe_0 shrub_steppe_1 shrub_temperate_0 shrub_temperate_1 shrub_tropical_0 shrub_tropical_1
```

- **Scans:** `..\scans` alongside the repository by default, or `-Scans <dossier>`, or `MYPLANETENGINE_SCANS`. Sand and layered rock come from them; `tools\telecharger_scans.ps1` downloads them again.
- **Cloud data:** `assets/clouds`, found above the executable like the ship; provenance in its `manifest.json`.
- **Build:** `-Build` compiles the solution in Release x64, placing the executable and shaders in `x64\Release`. A worktree without `x64/` rebuilds everything, about 8 minutes. For Debug, MSBuild with `/p:Configuration=Debug` produces `x64\Debug\MyPlanetEngine.exe`.

## Launcher options

- **`-Build`,** **`-NoLaunch`:** build, then do not open.
- **`-Parcours <fichier>`:** the “Tests” palette, one button per line and F1 to F12; defaults to `tools\tests\vues.txt`. Line format: `libellé | alt lat lon tangage cap [vue] | lat lon du soleil`, with an optional view name from `MYPLANETENGINE_VIEW`; without it, the game render. The fields are label, altitude, latitude, longitude, pitch, heading, optional view, and sun latitude and longitude.
- **`-Position '<alt> <lat> <lon> <tangage> <cap>'`:** starting view, the globe by default.
- **`-Soleil '<lat> <lon>'`:** sun position, `10 -5` by default.
- **`-Resolution '1920 1080'`** by default, full screen; `fenetre` for a 1280x720 window, where the palette is visible.
- **`-ModeleVaisseau chasseur|classique`:** the approved fighter by default; `classique` loads the preserved triangular ship. Direct executable launches use `MYPLANETENGINE_MODELE_VAISSEAU`; without it, the fighter.
- **`-PassePleine`:** clouds in a single pass, without their temporal pass (`optimisation.md`); for comparison.
- **`-Scans <dossier>`:** ground photos.

**The launcher clears the session's `MYPLANETENGINE_*` variables during launch, then restores them.** It sets only `MYPLANETENGINE_TESTS`, `_SUN`, `_RESOLUTION` and `_FULLSCREEN`, `_SCANS`, `_MODELE_VAISSEAU`, and `_CLOUD_FULL` with `-PassePleine`.

## Default game and benchmark variables

- **Clouds:** always present, using their temporal pass. Weather starts paused at time 0.
- **Temporal antialiasing:** disabled at startup; T enables it.
- **Lens halo:** disabled.
- **Override variables** for benchmarks and comparisons:

| Variable | Effect |
|---|---|
| `MYPLANETENGINE_NO_CLOUDS` | No clouds, like the N key |
| `MYPLANETENGINE_CLOUD_FULL=1` | Clouds in a single pass |
| `MYPLANETENGINE_WEATHER_TIME` | Weather time, in seconds |
| `MYPLANETENGINE_TAA` | Temporal antialiasing from startup |
| `MYPLANETENGINE_GLARE` | Lens halo |
| `MYPLANETENGINE_VIEW` | Diagnostic view; terrain views are raw, without clouds or air, except `ground`, the cloud silhouette |
| `MYPLANETENGINE_SEED` | Another seed for tectonic map and climate, to compare planets; detail noise retains its seed |

- **Cloud views:** `clouds`, opacity; `weather`, the planet's weather map; `cloudshadow`, cloud shadow on any sun-facing surface. The latter two use a single pass.
- **Tectonic map views,** from orbit to 500 km: `plates`, `boundaries`, `boundarydist`, `crustage`, `rocktype`, `uplift`; and `relief`, shaded and colored terrain including the seabed (`spec-relief-tectonique.md`).
- **Climate views from orbit:** `precipitation`, annual rainfall; `wind`, prevailing wind and arrows; `temperature`, ground temperature in grayscale (`spec-climat.md`).
- **Execution profile:** `tools/lance_optimise.ps1` and `MyPlanetEngine.ini` (`execution-optimisee.md`) launch the same game, with the `tools\tests\vues.txt` palette.
- **Benchmarks** set their own overrides; run them only on request (`AGENTS.md`).

## Cinematic mode

**A precomputed route, one frame rendered per fixed time step, without audio or flight controls.** The window stays hidden, as for automated captures; computation time does not change film time.

| Variable | Effect |
|---|---|
| `MYPLANETENGINE_CINE` | Route path; mutually exclusive with `BATCH`, `CAPTURE` and `TREMBLE` |
| `MYPLANETENGINE_CINE_OUT` | Existing directory for frames and `cine.log` |
| `MYPLANETENGINE_CINE_RANGE="0 600 120"` | First frame, frame count, warm-up frame count |
| `MYPLANETENGINE_RESOLUTION="640 360"` | Render dimensions; same limits as other captures |

- **Without a range:** the whole route, with 120 warm-up frames.
- **Warm-up replays previous frames without writing them.** Before index 0, it repeats that frame's pose; clocks and temporal phases advance to the first frame.
- **The time step is `1/fps`:** sea, plants, glass state and histories; weather takes each line's exact time, like `MYPLANETENGINE_WEATHER_TIME`.
- **History is preserved** except when switching between exterior and cockpit; the cockpit uses the game's resting eye and head pose, without head inertia.
- **The GPU clamp reads current terrain below both poses.** Every intervention writes the index and `pince camera` or `pince vaisseau` to `cine.log`; hull clearance at least 2.5 m, camera at least 1 m.
- **Frames are named `frame_00000.bmp`,** then `frame_00001.bmp`; indices remain global within a range; the application closes after the last frame.
- **An error returns a nonzero code** and writes `<parcours>.error.txt`.

**Route file: UTF-8, whitespace separators, decimal point.** Comments start with `#`, the first meaningful line is `fps 60`, followed by exactly:

```text
index vue navLat navLon navAlt navCap navTangage navRoulis camLat camLon camAlt camCap camTangage camRoulis fov meteo
```

- **Contiguous indices, starting at 0;** `vue` is `exterieur`, `cockpit` or `pleine` (the pilot's eye without cockpit or hull, using the `cam*` pose).
- **Angles in degrees:** north latitude positive, east longitude positive, heading from north toward east, pitch positive upward, roll positive rightward.
- **Altitudes in meters above sea level 0;** vertical `fov`, between 5 and 150°; `meteo` in seconds, nonnegative.
- **In exterior mode,** each pose is independent; hull, shadows and plume follow the ship; throttle is inferred from movement.
- **In cockpit mode,** all six `cam*` values remain required, but the eye is derived from `nav*`; interior, rain and frost use the game's rendering.

**Generate from the root:** Python 3 and NumPy, without SciPy; `cp.py` reads `x64/Release/tectonique-0.bin`, produced by running the engine, or `EXOLUNE_TECTONIQUE` (`spec-relief-tectonique.md`).

```powershell
python tools/cine/parcours.py tools/cine/essai.json x64/cine/essai.parcours
powershell -NoProfile -ExecutionPolicy Bypass -File tools/cine/rendre.ps1 -Parcours x64/cine/essai.parcours -Sortie x64/cine/essai-640 -Resolution '640 360'
```

- **JSON scenario:** `fps` (60), `graine` (0 on this branch), `depart: [lat, lon, altitude]`, `meteo` (0), `vitesse_meteo` (1), then `segments`.
- **Each segment:** `type`, `duree` in seconds, `point: [lat, lon]` or `points: [[lat, lon], ...]`, `hauteur` above the ground, and `camera`.
- **`orbite`:** exponential descent from the preceding altitude, curving toward the point, to `hauteur` (150 m by default), or an explicit absolute `altitude`.
- **`ascension`:** the same exponential law, upward, to the requested `altitude`; a nearby point sets the climb angle.
- **`approche`, `atterrissage`, `decollage`:** transition to the point's height, defaults of 100, 4 and 100 m respectively.
- **`pause`:** hold pose; `rase-mottes`: waypoints at `hauteur` above terrain (150 m by default); `mer`: height above 0 (20 m by default).
- **Segments join continuously in position, velocity and acceleration.** Only the end of landing, the whole pause and the start of takeoff require a stop; waypoints are traversed with a quintic spline; heading tangent to the path, pitch from slope, roll from curvature.
- **Speed follows the length of the safe path,** with central cruise and two smooth transitions to neighboring speeds; distances between points do not control acceleration. Orbit retains exponential altitude decay and therefore variable speed.
- **Camera:** string `cockpit`, or object `{"type":"poursuite","distance":22,"hauteur":8,"fov":60}`; `libre` also accepts `cap_relatif` (90° by default), `regard:"paysage"`, `cap` and `tangage`; `pleine` places the eye at `hauteur` (1.1 m) above the pose, looking along the ship's heading and pitch, offset by `cap_relatif` and `tangage` (−4°).
- **`fondu`:** pose-transition duration in seconds, 1 by default; only cockpit transitions cut; between two full views, it turns the head; 0 cuts.
- **Generator safety:** `bande` on either side (40 m), longitudinal and transverse `pas_sol` (10 m), CPU terrain `cellule` (1 m), terrain `marge` (12 m; overridable per segment; landing at the requested height).
- **A smooth elevation correction keeps the band clear** after spline fitting; during low flight, the requested height becomes minimum clearance over this band, with 2 m extra if correction is needed; after arc-length reparameterization, only `marge` remains required; the camera checks its band too.
- **The `mer` segment must stay over water:** crossing emerged terrain is rejected; its height is measured from sea level 0, down to 3 m, without the terrain margin; no world geometry is modified.
- **The `<sortie>.resume.json` summary** gives duration, minimum, mean and maximum speeds, minimum clearance per segment and route hash; speed extrema include the final transition.

**Render the film:** `rendre.ps1` uses ranges of 600 frames and 120 warm-up frames; `-Plage` and `-Chauffe` allow shorter trials.

- **One engine at a time:** the script refuses to start if a MyPlanetEngine is already open; it does not stop any instance.
- **Encoding:** `C:\ProgramData\chocolatey\bin\ffmpeg.exe`, H.264, CRF 14, 60 fps, `yuv420p`; `ffprobe.exe` checks frame count before any deletion.
- **Disk:** a range's BMPs are deleted once its MP4 is verified; range MP4s remain, then are concatenated into `<Sortie>/film.mp4`.
- **Resume:** rerun the same command; `rendu.json` checks route, engine, shaders and settings; only complete ranges are reused.
- **The script isolates and restores engine variables;** it enables TAA and keeps explicit scan and plant paths.
- **Targeted CPU checks:** `python tools/cine/test_parcours.py`; they launch neither an engine nor a benchmark.

## In-flight keys

- **J / Marcher button:** instant ground placement; J again returns to the saved ship. Hold Alt or toggle M to click the upper-left buttons.
- **Walking:** WASD/ZQSD or arrows; Shift runs, Ctrl crouches, Space jumps, H toggles bob. Y / Son button mutes audio.
- **Walking route:** `tools/tests/2026-11-02-marche-main.txt`; an optional `marche` pose token places a test on current terrain.
- **Audio:** default on; optional `MYPLANETENGINE_AUDIO="master footsteps ambience ship"`, gains in [0,1], or `[Audio] Volumes` in the local profile; `spec-marche-ambiances.md`.
- **I:** camera coordinates in screenshots; enabled in interactive views and disabled in automated output by default. `MYPLANETENGINE_COORDINATES=1` includes them in a capture.

- **H:** tree impostor-to-mesh fade, enabled by default; disabled, each tree switches abruptly.
- **T:** temporal antialiasing.
- **O and P,** held: rotate the sun.
- **Space, V:** resume or pause weather; speed ×1 or ×5.
- **N:** clouds on or off. **C:** cloud quality, Eco or Reference. **B:** ground view under the cloud silhouette.
- **F:** wireframe. **R:** flat shading. **G:** terrain mesh stops following the camera.
- **K and L,** or **− and +:** finer or coarser terrain mesh, for testing.
- **F1 to F12:** route tests. **Esc:** windowed mode, then close.
