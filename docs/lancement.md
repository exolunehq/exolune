# Launch the app

**The executable alone runs the game:** `x64\Release\MyPlanetEngine.exe`, without any environment variables. For an in-flight review, `tools/lance.ps1` builds it if needed, then opens it with the “Tests” palette.

**Assisted flight review** uses the [ten-stop pilot route](../tools/tests/2026-11-20-vol-assiste.txt). F1 and F2 start at 180 m/s in air and vacuum. F3 starts at rest above the sea for the wheel. F4 permits a high-speed reversal. F5 starts outside the atmosphere and crosses it. F6 begins in fast level flight. F8 tests the moon and F9 climbs out.

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\2026-11-20-vol-assiste.txt -DepartTest 1 -Resolution fenetre
~~~

**Thrust and windscreen review** uses the [eleven-stop cockpit route](../tools/tests/2026-11-20-propulsion-verriere.txt). F1 and F2 compare a hot entry and a cold approach. At F3 or F4, hold Up for full thrust and add Shift for boost. Release Up to return to the wheel setting. At F5 and F6, hold the right mouse button to inspect the same dry pane with the sun on opposite sides. R recentres the pilot's head.

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\2026-11-20-propulsion-verriere.txt -DepartTest 1 -Resolution fenetre
~~~

**Flight and immersion review** uses `tools/tests/2026-11-20-vol-immersion.txt`. Start at F1 for an unpowered orbit. F2 and F3 share an entry attitude at two different speeds. F4 starts above the sea. F8 and F11 visit the suit on land and on an airless moon. Select the same row to restart.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\2026-11-20-vol-immersion.txt -DepartTest 1
```

- The launcher accepts `-ModeleVaisseau classique`, `chasseur`, `navigateur` or `navette` for the same route.
- In a route's pose field, optional `v=<m/s>` after the heading sets the initial forward speed in ship view. Ordinary rows start from rest.
- In vacuum, cut the throttle to coast. Hold X until the title shows `stationnaire`. Use the wheel or a thrust or translation command to resume flight. Enter calls the radio in the cockpit or suit.

**Shuttle and fighter review** uses the [six-stop flight route](../tools/tests/2026-11-20-aerofreins.txt). Turn over the coast at F1, stop over open sea at F2 and check the external surfaces with Tab at F4 and F5. F6 starts near the Moon.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Parcours tools/tests/2026-11-20-aerofreins.txt -ModeleVaisseau navette -Camera cockpit -DepartTest 1 -Resolution fenetre
```

## Transport shuttle

- Run `tools/jouer_navette.cmd` to start parked on the coastal plain. P opens the in-game flight controls and pauses piloting. P or Escape resumes.
- In atmosphere the wheel holds its setting. The main plumes stay lit at cruise speed and reach full output at notch 25 of 30. Tap Up to leave the lever at full power.
- In wing-borne flight the outer wing panels roll and pitch the shuttle. The split rudder yaws it. Space and Ctrl pitch up and down. The lateral keys steer into the turn. P shows which controls carry the load. F1 starts a coastal flight and F5 a valley flight.
- Roll the wheel down to zero or tap Down or X to brake to a powered hover. The retro jets slow the shuttle, then the main grilles turn down and the ventral jets stabilize it. Space and Ctrl change height. Release to hold position. Advance the wheel to fly on.
- In vacuum, zero allows an inertial coast. Up gives full thrust while held. Hold X or Down to stop. With the gear down below 120 m, Space and Ctrl also control manual landing on the Moon.
- L initiates automatic landing below 5 km and 1,200 km/h ground speed. The shuttle levels, brakes, deploys the gear and descends. It searches nearby when the surface is wet or too steep. L returns control in flight.
- After touchdown the hull locks to the surface. Mouse movement controls the camera. J disembarks once the rear stair is fully open. J boards again.
- L from park closes the stair before liftoff and establishes a hover 8 m above the pads. L during closure cancels departure. F4 and F7 start parked. F10 and F11 start airborne over the plain and Moon 1.
- At F7 press L to see the two side grilles discharge straight down during takeoff. At F8 hold Up for aft exhaust, Space for downward exhaust, or both for diagonal exhaust. X brakes in orbit. F9 shows the attitude outlets during lunar roll and lateral translation. Use Tab for the exterior view.
- Automatic wings open at 150 km/h indicated and retract at 90 km/h indicated. Between these speeds they keep their previous state. Vacuum, 1,340 km/h indicated or 48% entry heat engages protection. In supporting air it releases below 1,140 km/h and 22% heat. The automatic landing and departure sequences also stow the wings.
- Hold X to brake. The dorsal panels follow the braking demand in the atmosphere.
- In manual flight, 2 overrides wings, 3 gear and 4 the airbrake. When parked, 5 operates the stair. Pressing 6 or starting an automatic manoeuvre restores automatic equipment control. The number pad also works with Num Lock.
- Tab cycles the cockpit, chase view and unobstructed view. Hold the right mouse button to look around.
- The right display shows actual travel, automatic or manual control, throttle and engine demand. The left display shows attitude, speed and altitude. The middle display shows heading and coordinates.

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Parcours tools/tests/2026-11-25.txt -ModeleVaisseau navette -Camera cockpit -DepartTest 4 -Resolution fenetre
~~~

**Camera review** uses `tools/tests/2026-11-10.txt` with `-Camera orbite -DepartTest 1`. At F1, hold forward to descend towards the coast in Horizon. Press Home, select F1 again and repeat in Fixed altitude. F5 points straight down at Moon 2.

**Three-moon review:** `tools/tests/2026-11-08-trois-lunes.txt`. Launch with `-DepartTest 1 -Resolution fenetre -Camera libre` to begin at moon 2. F1–F8 cover orbit, approach, contact and walking on the new surfaces; F9–F12 cover moon 1, distant moon 2, Exolune and polar terrain. `J` disembarks. `lune` / `lune1`, `lune2` and `lune3` select a body; lunar altitude means clearance above its own terrain. `marche` explicitly selects walking for a route row. Cook all atlases with `tools/prepare_airless.ps1` in a fresh worktree. See `spec-lune-terrain.md` for limits.

**Cloud continuity review:** `tools/tests/2026-11-08-transition-nuages.txt` holds geography and sunlight fixed from 40,000 km to 500 km. The distant terrain blend must preserve the same cloud layers.

For the **above-cloud flight review**, run `tools/lance.ps1 -Parcours tools/tests/2026-11-19.txt -DepartTest 1 -Camera altitude-fixe`. Use F1–F4 for the continental altitude sweep and F5–F12 for ocean, polar, orbital and layer checks. Compare cloud detail and cadence during straight flight, turning and stopping.

For the **cirrus passage review**, use `tools/tests/2026-11-19-cirrus.txt` with `-DepartTest 1 -Camera altitude-fixe`. F1 starts at 12 km over the continent. F2 and F3 bracket the layer. F4–F7 cover the Atlantic, tropics, antimeridian and polar region.

For the **fast Atlantic flight review**, use `tools/tests/2026-11-19-atlantique.txt` with `-DepartTest 1 -Camera altitude-fixe`. F1 starts over the Atlantic. F2–F5 cover the other 12 km views. F6–F8 cross the layers.

**Combined handoff:** `tools/tests/2026-11-08-lunes-et-nuages.txt`, with `-Camera libre -DepartTest 1 -Resolution fenetre`; F1–F6 visit the three moons and F7–F12 cross the cloud transition.

**Direct exposure review:** `tools/tests/2026-11-07-exposition-sans-lissage.txt`. F1 returns just before the reported orbital sunrise; F2 reveals the Sun. The remaining views cover orbit, atmospheric day/night and a lunar approach. The temporal filter was reverted; the previous orbital luminosity corrections remain active.

**Orbital exposure review:** `tools/tests/2026-11-07-exposition-orbite.txt` starts at the two reported overexposed views, then covers neighbouring phases, planetary shadow, atmosphere and celestial controls.

**Celestial review:** `tools/tests/2026-11-07-ciel.txt` covers orbital depth, moonless and moonlit nights, twilight, noon, clouds, lunar approaches and the Sun. F1--F12 select the first twelve views; the last two use the windowed palette. Optical glare is part of normal rendering. The three cooked airless atlases supply lunar surface detail without runtime downloads; `spec-ciel-celeste.md`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Build -NoLaunch
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Parcours tools\tests\<date>.txt
```

## Before the first launch in a worktree

**Plant binaries are not versioned:** `assets/foliage/.gitignore` excludes them. Without them, the app flies without plants and its title says “végétation absente” (vegetation missing).

- **Current technical prototype:** `assets/foliage/game_biomes_v1`, 31 models, local communities, ground vegetation, volumetric roots and wind; art direction remains under review (`spec-diversite-vegetale.md`).
- **Build once** from the root: `tools\plantes.ps1` downloads pinned sources, imports and cooks the baseline and prototype. Python with numpy/Pillow/numba/UnityPy is required during development.
- **Existing baseline:** `python tools/foliage/prepare_vegetation_jeu.py` builds only the rooted extension; `--base` selects a local baseline. No Blender dependency for this prototype.
- **Fallback:** the old fourteen-model catalogue remains in `assets/foliage/climate_shrubs_v2` or shared `plantes/climate_shrubs_v2` beside the repositories.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\plantes.ps1
```

- **Missing scans** are downloaded by `tools\lance.ps1` on first launch.
- **Immersion audio takes are not versioned either:** `assets/audio/immersion/*.wav`. Without them the engine synthesizes stand-in layers, and the helmet's breathing sounds like surf while walking. Copy them from a checkout that has them, after checking each against `cooked.json`.

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
- **`-ModeleVaisseau chasseur|classique|navigateur|navette`** selects the physical model. The fighter is the default. `navette` loads the V9 transport. Direct executable launches use `MYPLANETENGINE_MODELE_VAISSEAU`. [Model profiles](spec-vaisseau.md)
- **`-Camera cockpit|poursuite|sans|libre|orbite|altitude-fixe|marche`** selects the initial view. `orbite` starts in Horizon. The default is the cockpit.
- **`-PassePleine`:** clouds in a single pass, without their temporal pass (`optimisation.md`); for comparison.
- **`-SansNuages`:** start with clouds hidden for terrain review; N toggles them during flight. Use this option for the current erosion review.
- **`-Scans <dossier>`:** ground photos.
- **`-Plantes <catalogue>`:** explicitly select an external asset catalogue for an authoring POC; the default game catalogue is unchanged.
- **`-Ville <bank>`:** load a generated settlement library and placement scene; see `spec-ville-procedurale.md` and the dated city review route.

**The launcher clears the session's `MYPLANETENGINE_*` variables during launch, then restores them.** It sets only `MYPLANETENGINE_TESTS`, `_SUN`, `_RESOLUTION` and `_FULLSCREEN`, `_SCANS`, `_MODELE_VAISSEAU`, `_VAISSEAU` with `-Camera`, and `_CLOUD_FULL` with `-PassePleine`, `_NO_CLOUDS` with `-SansNuages`, and `_FOLIAGE_ASSETS` with an explicit `-Plantes`, and `_CITY_ASSETS` with an explicit `-Ville`.

## Default game and benchmark variables

- **Clouds:** always present, using their temporal pass. Weather starts paused at time 0.
- **Temporal antialiasing:** enabled at startup; T toggles it. `MYPLANETENGINE_TAA=0` disables it explicitly.
- **Lens halo:** enabled; linear energy-conserving response before tone mapping.
- **Override variables** for benchmarks and comparisons:

| Variable | Effect |
|---|---|
| `MYPLANETENGINE_NO_CLOUDS` | No clouds, like the N key |
| `MYPLANETENGINE_CLOUD_FULL=1` | Clouds in a single pass |
| `MYPLANETENGINE_WEATHER_TIME` | Weather time, in seconds |
| `MYPLANETENGINE_TAA` | Temporal antialiasing; default enabled, explicit `0` disables it |
| `MYPLANETENGINE_GLARE` | `0` disables optical glare; enabled by default |
| `MYPLANETENGINE_VIEW` | Diagnostic view; terrain views are raw, without clouds or air, except `ground`, the cloud silhouette |
| `MYPLANETENGINE_SEED` | Another seed for tectonic map and climate, to compare planets; detail noise retains its seed |

- **Cloud views:** `clouds`, opacity; `weather`, the planet's weather map; `cloudshadow`, cloud shadow on any sun-facing surface. The latter two use a single pass.
- **Tectonic map views,** from orbit to 500 km: `plates`, `boundaries`, `boundarydist`, `crustage`, `rocktype`, `uplift`; and `relief`, shaded and colored terrain including the seabed (`spec-relief-tectonique.md`).
- **Climate views from orbit:** `precipitation`, annual rainfall; `wind`, prevailing wind and arrows; `temperature`, ground temperature in grayscale (`spec-climat.md`).
- **Execution profile:** `tools/lance_optimise.ps1` and `MyPlanetEngine.ini` (`execution-optimisee.md`) launch the same game, with the `tools\tests\vues.txt` palette.
- **Benchmarks** set their own overrides; run them only on request (`AGENTS.md`).

## Cinematic mode

### Live cockpit recording

- Start the shuttle and choose a single departure with the normal review settings. The six [flight positions](../tools/tests/2026-11-21-prise-de-vol.txt) cover orbit, incoming heat, mountains and the inlet.
- Use [the live take driver](../tools/cine/prise_jeu.py) for gameplay films. Its `record(executable, directory, pilot, environment)` callback receives the ship instruments. Return raw mouse counts, wheel detents and buttons in `CONTROLS` order. The last button ends the take after the preceding frame has been presented.
- Optional `translation(state)` returns signed strafe and lift from −1 to 1. Optional `radio_meter(state)` supplies a separate receiver level from 0 to 1 during transmission and −1 when idle.
- Flight dynamics, collisions, weather, sound state and seat response use the normal elapsed game time. The controller window runs in the background. Cinematic pose tracks remain available for authored camera studies.
- The capture directory holds lossless RGB frames, the telemetry and the presentation clock. Mux the clock before editing: `mkvmerge -o realtime.mkv --timestamps 0:frames.timecodes frames.mkv`. The stored frame indices alone have a nominal clock of 60 Hz.

### Authored camera tracks

**A precomputed route, one frame rendered per fixed time step, without audio or flight controls.** The window stays hidden, as for automated captures; computation time does not change film time.

| Variable | Effect |
|---|---|
| `MYPLANETENGINE_CINE` | Route path; mutually exclusive with `BATCH`, `CAPTURE` and `TREMBLE` |
| `MYPLANETENGINE_CINE_OUT` | Existing directory for frames and `cine.log` |
| `MYPLANETENGINE_CINE_RANGE="0 600 120"` | First frame, frame count, warm-up frame count |
| `MYPLANETENGINE_CINE_VIDEO=out.mp4` | Frames piped to ffmpeg (HEVC NVENC, cq 12, a keyframe a second, fragmented MP4) instead of BMP files; needs `ffmpeg` on the `PATH` and an NVIDIA GPU; a file cut short by a crash stays readable up to its last whole second; `cine.log` ends with the mean ms per frame and its GPU share |
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
index vue navLat navLon navAlt navCap navTangage navRoulis camLat camLon camAlt camCap camTangage camRoulis fov meteo [control]
```

- **Contiguous indices start at 0.** The views are `exterieur`, `cockpit`, `pilote`, `pleine` (ship hidden) and `cabine` (explicit cabin inspection pose).
- **Angles in degrees:** north latitude positive, east longitude positive, heading from north toward east, pitch positive upward, roll positive rightward.
- **Altitudes in meters above sea level 0;** vertical `fov`, between 5 and 150°; `meteo` in seconds, nonnegative.
- **In exterior mode**, the hull, shadows and plume follow the ship. Append `coast` to a pose to stop the drive during a glide or entry. Earlier routes retain their moving-ship plume.
- **Cockpit views** use the selected ship's seat for the eye position. `cockpit` uses the resting head direction. `pilote` uses the authored camera heading, pitch and roll with respect to the local frame at `camLat camLon`. Set those coordinates to the ship's for a seat-mounted look. Supply all six camera values for either view. Both use the game's interior, rain and frost.
- **Pilot thrust** accepts an optional control from 0 to 1 in `pilote`. The console and the exhaust follow that setting. All views accept `coast` for zero thrust.

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

- **Backspace** detaches the camera or returns to the cockpit.
- **Home (Début)** cycles the detached camera through Free, Horizon and Fixed altitude.
- **Horizon** keeps the horizon level. Right-drag to look down and hold W/Z or Up to descend along the view. Look up and advance to climb.
- **Fixed altitude** carries the arrows or WASD/ZQSD around the body at constant radius. Page Up/Down changes altitude in both horizon-aligned modes.
- **Free flight** uses the same movement keys along the camera's own axes. Shift + Left/Right rolls.
- **The wheel** selects the detached camera's speed at any altitude. All three modes start from the same 100 m/s setting. The title shows the selected speed. [Flight review](../tools/tests/2026-11-22-vitesse-camera.txt)
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
