# Optimized flight rendering

**The goal:** 60 frames per second minimum in 1920×1080, 120 targeted, with perceived quality retained. Starts the 2026-10-28 on the `optimisation` branch, originated from `main` and the optimized execution profile (`execution-optimisee.md`).

## The benchmark

**`tools/banc_perf.py` is authentic for the time.**
- **The flight configuration:** the game, the exe without variable: planetary clouds, sea FFT, vegetation detailed with HiZ, without TAA or halo, cut by default (`lancement.md`).
- **Eight views,** from the forest floor at 2 m to the globe at 10 000 km: `foret_sol`, `lisiere`, `montagne`, `mer`, `survol`, `cumulus`, `orbite`, `globe`.
- **1920×1080, VSync off, no window.** Each view gives the GPU time of each pass, averaged on 120 images (`<capture>.perf`, `D3DApp::ReadGpuTimes`).
- **Quality guard:** `--before <perf.json>` compares each frame to the previous one: average difference in levels 8 bits, share of pixels moving more than 8 levels.
- **The benchmark is deterministic:** two passes give identical images to the bit. The time ranges from 5 %, up to 10 %; a gain is judged beyond.
- **Build first:** `tools/lance.ps1 -Build -NoLaunch`. One benchmark at a time: the GPU is what we measure.
- **The quality of the ground** remains judged by `tools/banc_qualite.py`; what is seen in movement, in flight (`tools/lance.ps1`).
- **The `nuages_trace` column** isolates the cloud track in the atmosphere passage.
- **The column `terrain_dessin`** adds the depth of the field and its color, drawn after the foliage (round 2).
- **The columns `objets_place` and `plantes_place` overlap:** no barrier between objects and plant tiles sorting; their sum is judged.
- **`--views a,b`:** a subset of views, to iterate quickly. Images in a subset are compared only to an identical subset: the 4×4 tile of each view depends on the images rendered before it.
- **`cumulus_sol`** (round 7): 150 m above a forest, cumulus clouds in the sky; fast flight between the ground and clouds.
- **The options:** `--full` keeps the single pass of clouds in full resolution; `--weather <s>` fixes the weather time.
- **The actual cadence** (round 5): after the passes of the GPU, the image of the CPU, in ms. `cpu_prep` the preparation, `cpu_liste` the recording, `cpu_present` the submission and the presentation, `cpu_attente` the waiting of the GPU; `cadence` the time from one presentation to the next, what the eye receives; `gpu_inactif` the GPU unoccupied between two images, by its timestamps. The `réel` column of the table is the frame rate in fps; `fps` remains the time GPU.
- **Motion benchmark:** `--motion "<cap °> <latitude °> <météo s>"`, per frame. The camera joins each view at capture by turning and flying north; the weather runs to its time. Compared to a benchmark stationary, it shows what a time pass loses in movement.

## The reference

**RTX 4070 Ti, commit `242d0f7`, ms GPU per frame.** The CPU waits for the GPU at each frame: the time GPU makes the cadence.

| View | Atmosphere and clouds | Land, drawing | Foliage, drawing | Plants, placement | Land, calculation | Total | fps |
|---|---|---|---|---|---|---|---|
| default_s | 13,1 | 12,6 | 9,9 | 7,1 | 4,2 | 48,8 | 21 |
| slurry | 19,0 | 11,2 | 9,4 | 7,2 | 4,2 | 53,0 | 19 |
| mountain | 14,3 | 16,3 | 3,7 | 8,3 | 3,2 | 47,6 | 21 |
| mer | 41,2 | 1,1 | 0,1 | 0,8 | 2,1 | 46,0 | 22 |
| overflow | 9,7 | 11,6 | 1,8 | 4,9 | 1,4 | 30,0 | 33 |
| cumulus | 26,7 | 1,2 | 0,1 | 0 | 0,6 | 29,0 | 34 |
| orbite | 51,2 | 5,0 | 0,1 | 0 | 0,5 | 57,3 | 17 |
| globe | 45,5 | 2,1 | 0,1 | 0 | 1,2 | 49,4 | 20 |

**The budgets:** 16,7 ms for 60 fps, 8,3 ms for 120.

**The initial analysis of the cloud pass,** cost per share: `log/optimisation-historique.md`.

## The rounds

**One round per post, from the heaviest to the lightest, one after the other.** Each: measure, change, benchmark before and after, quality guard; what is seen in movement passes in flight.

1. **Clouds and atmosphere, made:** a trace by tile 4×4 in full resolution, reprojected in the world; the distant quadrature spread out in time; the shadow on the ground amortized likewise, without shadow map (The results).
2. **The drawing of the terrain, does:** its depth first, its color once per pixel shown; the shader does not calculate anymore what does not change anything (The results).
3. **Vegetation, makes:** the exact floor of the tiles kept from one frame to another; the impostors in conservative depth; the meshes close in depth first (The results).
4. **The calculation of the terrain, done:** kept as long as its inputs are those of the previous image; in flight, it remains redone in full (The results).
5. **Multiple frames in flight, measured and stopped:** GPU waits for CPU only 0,6 to 1,2 ms per frame; below threshold, no rendering (Resultates).
6. **Moving clouds, set aside:** each fresh track checked the reprojected history; drags, noise and dive corrected, but 4 to 6 ms more in slow altitude flight. To the tag `piste/optimisation-r6-nuages-mouvement` (`016d9c7`), for reference; its benchmarks `x64/r6_avant_*` and `x64/r6_full_*` serve the round 7.
7. **The clouds in fast flight, made:** under 14 km, the pixels whose history has slipped are rebuilt by a pixel drawn by square 2×2; above, nothing changes (The results).
8. **The ground in fast flight, makes:** the sky holes in the sheets filled by the history instead of being traced by the resolution of clouds; in flight, the terrain grid in float pairs; forest of 49 to 60 fps real, edge of 43 to 55, mountain of 48 to 54 (The results).

## The results of the survey

### Round 1: clouds and atmosphere (2026-10-28)

**The pass falls from 10 to 51 ms to 1,2 to 4,6 ms; the still image remains that of the reference.** benchmark `x64/banc_perf_round1`, ms GPU.

| View | Atmosphere, before | Atmosphere, after | trace | Total, before | Total after | fps |
|---|---|---|---|---|---|---|
| default_s | 13,1 | 1,6 | 1,1 | 48,8 | 37,0 | 27 |
| slurry | 19,0 | 3,1 | 2,6 | 53,0 | 36,5 | 27 |
| mountain | 14,3 | 2,0 | 1,4 | 47,6 | 35,5 | 28 |
| mer | 41,2 | 4,6 | 4,0 | 46,0 | 9,3 | 108 |
| overflow | 9,7 | 1,2 | 0,7 | 30,0 | 21,4 | 47 |
| cumulus | 26,7 | 3,0 | 2,5 | 29,0 | 5,2 | 192 |
| orbite | 51,2 | 2,6 | 2,0 | 57,3 | 8,5 | 118 |
| globe | 45,5 | 1,4 | 1,0 | 49,4 | 4,8 | 208 |

**Quality guard:** average deviation from 0 to 0,65 level; no pixels beyond 8 levels, except 0,8 % to the globe, in the grain of clouds at the edge of the disk. The other passes do not move.

**The passage of time** (`CloudsTemporal.hlsli`, `D3DApp::Draw`):
- **Each frame traces one pixel per tile 4×4,** in full resolution: 1/16 of rays. Each pixel has its trace in 16 images; the still image converges to the trace of each pixel.
- **The resolution, in full resolution,** takes the other pixels of the history and composes the air.
- **The history is reprojected in the reference frame where its content is fixed:** the clouds in the weather, that the wind turns; their shadow on the ground, on the ground. Clouds at their weighted distance, read in the history and then at the point found.
- **Rejection:** the end of the radius, surface or sky, must agree. Otherwise, the pixel takes the neighboring fresh tiles that see the same surface, the closest to the 5×5 as needed, like the sky between leaves: thin stripes, at the edges of the screen or around what moves. This fill leaves with three quarters of the allowed drift: in motion, the trace replaces it quickly. In front of the layer, there is nothing to trace: the near relief cuts the clouds net.
- **Cloud distance is kept from the current camera.** The history stores it from the previous camera: the point at this distance from one is at another distance from the other, especially as the camera has moved along the view. Without this correction, the distance kept dated from the track, up to 16 frames: at 2 km per frame in orbit, 10 % error, and each frame reprojected off, in trails.
- **Drifting:** a volume is not at a single distance. The trace measures the standard deviation of the distance from where its light comes; at each frame, its reprojection front and back measures what the history has slipped, and the change in distance counts also, 20 % worth the allowed drift. The drift accumulates until the next track; a visit only renews its part of the distant average.
- **Beyond 1 pixel drift, or when the direction from which a cloud is seen rotates more than 1° in an image, the resolution traces the pixel itself,** as the single pass. A filling by the fresh tiles would not go: it smooths the grain of the distant clouds in pale and flat plates, those seen in flight. In ordinary flight, nothing is traced; beyond x5 in orbit, the pass costs the single pass.
- **Resample:** Catmull-Rom, bounded by the four neighboring texels; at the edges of a surface, bilinear among the texels that see it. The standard deviation and drift are in a separate image, in semi-floating: nothing is packed, the still image remains accurate.
- **The distant quadrature spreads in time:** a fine ray per visit, at one of the four positions of the 2×2 (nine in reference); the historical average up to eight, still image, two moving, its rays taken from elsewhere. Same estimator: light premultiplied and transmittance averaged. The near rays replace the history; a traced pixel takes all four rays at once.
- **The history starts over** with every camera jump, reference change, cloud lightning, and when the sun moves more than one degree.

**In the track:**
- **One single walk call site per pixel:** the central radius if the distant weight is below 1, a thin radius if it is positive. The far ray code weighed on the registers of all pixels: 10 to 20 % everywhere.
- **The step limits the altitude travelled, not the length:** at most 240 m of altitude per step, half the footprint along the radius. The globe's rasant radii change from 4,2 to 1,0 ms; the vertical radii do not change.
- **The four samples to the sun are unrolled,** and in a cloud the shape and erosion are read with the weather: the walking waits two readings per step instead of four. Result identical to the bit close.
- **The vacuum jump takes the same density threshold:** low coverage at most 0,03 in the maximum mips, instead of 0. It's always a proof.

**In the composition:**
- **Air in simple precision,** from the camera altitude along the radius (`HeightAlong`): doubles cost 1,5 to 2,5 ms, more than the air itself.
- **24 no air towards the sky, 12 towards a surface,** as the passage of the atmosphere, spread over the air that the view passes through. The cloud only cuts the step where it is, in two: the others keep the samples of a single step, for one more step.
- **The air is thus continuous in the distance of the cloud.** Before, a cloud divided the steps into two halves: an invisible cloud would change 12 steps to 6 + 6, and the distance would move all samples. The time pass reprojects an older distance: on the continent, under barely visible clouds, the air changed by regions with clear edges, a "second skin" seen in flight at 160 km. At 160 km in fast flight, the plates change from 18 % to 3 % of the image; the single pass changes less than 0,3 level, the quality benchmark not at all.

**What is still limiting:**
- **Trace is limited by latency, not by the number of rays.** A 8×4 tile, with twice as few rays, gains only 17 % in sea and nothing in cumulus: each ray chains its texture readings.
- **The sea remains at 4,6 ms.** Its racing rays walk 150 km of low layer at the pace of 48 m, without finding anything visible. This void comes from the profile and erosion, which the mips of the weather does not limit: no jump is there provenable.
- **Moving, a pixel waits for its track up to 16 images, as long as the history holds.** The uncovered areas go through the filling; on the globe, the grain of the quadrature smooths instead of sparkling.
- **Beyond x5 in orbit, the pass costs the single pass, from 10 to 38 ms:** the direction from which we see each cloud rotates of 3° per frame, and a volume seen from the other side shows other faces; no reprojection catches up. Retracing in scattered order costs as much as any trace; a budget of 15° gains almost nothing.
- **Very fast dive keeps errors.** Dive of 1,5 % of the height per frame since 36 times the height: in orbit and on the globe, the difference is reduced by half; at 440 km towards the horizon, a band of clouds remains false. Its distance kept there is twice as false, and drift, rotation and distance, all calculated from it, do not see it; it would be necessary to check the distance against fresh traces.
- **Very quickly, the clouds soften,** as long as the history holds: in 15 images, Catmull-Rom loses the highest frequencies, hence a weaving of the grid 4×4 between fresh pixels and soft history. A history without interpolation, the closest sample and its offset kept, does not change anything: it is the direction of view that turns.
- **The shadow on the ground is reprojected on the ground:** it follows the wind with a delay of at most 16 images, a few meters windward real.

**Audits:**
- **The benchmark of movement, against the single pass in movement** (`--full`, without history): average deviation, share of pixels beyond 8 levels, and share of plates, average deviation on 9×9 pixels beyond 2 levels. The first two did not see the second skin: a flat, weak and extended shift.

| View | 0,5° and 0,02° per frame, before | After | 2° and 0,05° per frame, after |
|---|---|---|---|
| orbite | 10,35 ; 43,5 % | 3,45 ; 7,8 % | 4,47 ; 12,9 % |
| globe | 1,69 ; 6,8 % | 1,37 ; 5,0 % | 1,38 ; 5,0 % |
| cumulus | 1,01 ; 2,6 % | 0,24 ; 0 % | 0,24 ; 0 % |
| overflow | 0,21 ; 0 % | 0,21 ; 0 % | 0,15 ; 0 % |

- **The plates seen in flight,** at 160 and 440 km, speed x5 to x9: `haut160` and `haut440`, added to the benchmark, and `--motion "0.2 0 0 0 0 0.05"`, 5 % of height per frame to the north, the speed rule of the application. Against `--full` with the same move (`x64/vol_full`, `x64/vol_t`); ms of the pass:

| View | Before | After | ms, after | ms, single pass |
|---|---|---|---|---|
| high160 | 1,06 ; 1,2 % | 0,72 ; 0,6 % | 14,7 | 20,4 |
| high440 | 2,97 ; 8,9 % | 1,25 ; 3,8 % | 15,1 | 19,3 |
| orbite | 5,24 ; 16,5 % | 0,66 ; 1,1 % | 38,1 | 39,1 |
| globe | 1,39 ; 5,0 % | 0,56 ; 1,8 % | 9,5 | 12,8 |
| cumulus | 0,24 ; 0 % | 0,06 ; 0 % | 23,6 | 23,6 |
| border, sea, forest | 0 to 0,3 | 0 to 0,3 | 2,9 to 6,7 | 13,6 to 38,2 |

- **The plates came from the filling:** when the drift rejected the historical, whole regions passed to the fresh tiles, smoothing the grain of clouds in pale sail, with clean edges. The “before” column is measured before this processing, at 13 km per frame on all views (`x64/pl_t`, removed).
- **The dive** (`--motion "0 0 0 1.015"`, `x64/plong_t` vs `x64/plong_full`): orbit 9,51 → 4,31 levels, globe 3,74 → 2,00, high440 3,05 → 2,85, high160 0,89; move from 1,2 to 17,9 ms.

- **Before, the fault seen in flight:** in orbit, small cumulus dragged along the movement; at the cumulus, seams separated offset regions. After: shapes and edges in place; the orbit remains a little softer, the globe without its grain. Images `x64/mvt_t`, `x64/mvt_full`. At the same benchmark after the processing of the plates: orbit 3,37; 7,3 % at 3,0 ms, globe 1,36, cumulus 0,16; on the ground, at 2,2 km per frame, unrealistic near the ground, the pass traces and rises up to 35 ms.
- **Still image does not change:** 0,00 level against `x64/fixe_verif` on nine views; to the globe, at most 2 levels on 2 % of the disk (`x64/fixe_t`). The pass keeps its cost, from 1,2 to 4,5 ms.
- **Wind,** 0,5 s of weather per frame, thirty times real time at 60 frames per second: at most 0,94 level and 1 % of pixels. At 30 s per frame, the checkered 4×4 appears on the distant clouds.
- **`--full`,** the single pass, renders the same image as the reference; it remains that of the diagnostic views `weather` and `cloudshadow` (`spec-nuages.md`).
- **In flight:** `tools/tests/2026-10-28-optimisation-nuages.txt`, by `tools/lance.ps1 -Parcours`.

**Tested and withdrawn:**
- **A tile 8×4:** 17 % better at sea, nothing else, for twice as long waiting on the move.
- **Read shape and erosion with weather at every step:** 0,4 ms less at cumulus, 0,65 ms more at sea; kept only in a cloud.
- **A presence boundary on the form:** its median, 0,89, exceeds any coverage threshold; it does not prove any void.
- **A tile 2×2 in fast flight:** the triple trace everywhere, sea 3,6 → 10 ms.
- **Retracing according to a cumulative rotation budget (4 to 20°):** in orbit at medium speed, 8 to 27 ms for zero gain; the per-frame limit replaces it.
- **A history without interpolation,** the closest sample and its offset kept: sharper but crenneled, further away from the single pass (orbite 4,03 against 3,45 at medium speed).
- **Count re-sample blur in drift:** better (orbite 6,5 → 3,5), but 30 to 39 ms.

### Round 2: terrain drawing (2026-10-28)

**The drawing falls from 11 to 17 ms to 3 to 7 ms near the ground; the image remains that of the reference.** benchmark `x64/banc_perf_r2_terrain_bis`, compared to `x64/banc_perf_r1_verif`, ms GPU.

| View | Ground, front | Ground, after | Total, before | Total after | fps |
|---|---|---|---|---|---|
| default_s | 12,7 | 4,0 | 37,5 | 28,8 | 35 |
| slurry | 11,2 | 3,1 | 36,3 | 28,5 | 35 |
| mountain | 16,5 | 6,8 | 35,7 | 26,1 | 38 |
| mer | 1,2 | 1,4 | 9,7 | 9,2 | 109 |
| overflow | 12,5 | 5,3 | 23,1 | 15,0 | 67 |
| cumulus | 1,3 | 1,2 | 5,6 | 5,2 | 192 |
| orbite | 5,3 | 4,3 | 9,2 | 7,9 | 127 |
| globe | 2,2 | 1,8 | 5,1 | 4,7 | 215 |

**Quality guard:** no pixel moves more than one level across the eight views.
- **Identical to the bit near:** forest, mountain, cumulus, orbit, globe.
- **A level, on a few pixels:** 6 in edge, 4 in fly-over, 7 in sea.
- **`banc_qualite.py`,** 30 locations, seed 1, against `main` on the same locations (`x64/qualite_r2_base`, `x64/qualite_r2_final`): no p95 degrades, including mutation; 87 crops on 3 891 move, no pixels of more than 8 levels. Against `tools/banc_qualite_reference.json`, of the 2026-10-24, `main` already exceeds the 10 % on 26 measures; the round adds no more.

**Depth first** (`D3DApp::Draw`):
- **The terrain writes its depth alone,** even vertex shader, without pixel shader: 0,2 to 0,3 ms.
- **Then objects and foliage,** as before; the HiZ of foliage reads the same depth.
- **Then the color of the terrain,** in equal depth, without writing: the shader of materials turns once per pixel shown, neither under the plants, nor under the relief that hides it.
- **Gain:** 7 to 9 ms near the ground, 4,4 ms in the air. The wire keeps the old path.

**In the shader, what does not change anything is no longer calculated:**
- **The strata, where the rock shows them:** `StrataShift`, its 12 octaves, and the lenses, in the branch of the rock and walls only, once per pixel (`PixelStrataShift`). The phases of the beds stop where their sinuses are off, pixel more than 5,75 m; the lenses, where the beds are, not of the column more than 0,66 m.
- **The presence of woods stops as soon as the suite can no longer change it:** `PresenceField` sums its octaves as long as the rest, bounded, can bring the field back to the width of the threshold. Beyond this, `Presence` is equal to 0 or 1, whatever the sequence. The bound is a proof: 3,135 per unit amplitude of `Noise3`, not its standard deviation, 0,40.
- **Nothing from the woods where nothing grows or roots:** `WoodsAt` jumped where neither tree nor bush is possible, or on the rock, the scree or the beach whole.
- **The drawn plants, without their fades in the distance:** even though the highest holds under the pixel threshold, all the fades of `PlantsDrawn` are worth 0.
- **One quadrature of the slopes for rock, scree and snow** (`SlopeShares3`), instead of two.
- **`FbmLostShare` in closed form:** a geometric sum, bounded at [0, 1]; equal to the loop on octaves at 10⁻¹⁶ close to double.
- **Step by step, ms in overflying / mountain:** depth first −4,4 / −9,4; strata and wood without trees −1,6 / −0,4; limited presence −0,2 / 0; phases, lenses and quadrature common −0,3 / −0,7; the rest −0,3 / −0,3.

**What is still limiting:**
- **The surcharge for quads.** The GPU shadows by quads of 2×2 pixels; the ground triangles cover 6 pixels about, and the foliage leaves isolated ground pixels. Measured by `IsHelperLane`: 2,0 paths per pixel shown in flyby, 1,9 in forest, 1,6 in mountain and cumulus, 1,2 in orbit.
- **The experiment:** the color of the field in compute, on a visibility buffer, one way per pixel. A work: cached vertices outputs, analytic derivatives instead of quad differences, including `ddx(q)`.
- **The entire calculation of hashes.** Each octave of `Noise3` hatches its 8 coins (pcg3d); near the ground, a pixel sums about 80 octaves.
- **What weighs still,** shader variants, ms in flyover / mountain / orbit: vegetation 2,4 / 2,2 / 2,1, including presence of woods 1,8 / 1,5 / 0,8 and slab of the canopy 0,7 / 0,6 / 0; textures 0,8 / 3,6 / 2,0, including rock 0,1 / 2,0 / 0; noise functions local and detail 1,2 / 0,7 / 1,0.
- **Mountain, flyover and orbit remain above the targeted 4 ms.**
- **In motion:** the possible holes of the same depth, at the crests and under the plants, to be judged in flight: `tools/tests/2026-10-28-optimisation-terrain.txt`. Still images do not show any of them: they remain those of the reference at a level close.

**Tested and withdrawn:**
- **DXC and model 6.0 instead of FXC:** 5 % better before other changes, nothing or worse after; compilation changes from 88 s to 4 s.
- **`precise` on the position of the summits,** against supposed holes of equal depth: without effect, and the sea moved of 14 levels. There was no hole.
- **The closed form of `FbmLostShare` without bound:** a rounding under 0, under a root, gave isolated white pixels, a few in the views of the benchmark, hundreds to 50 m in `banc_qualite.py`. Bounded at 0, the image returned.
- **Shader variants,** which turn off one part at a time: diagnostic only (`log/optimisation-historique.md`).

### Round 3: vegetation (2026-10-28)

**Footprint and leaf pattern fall from 18 to 20 ms to 6 ms in forest; the image remains the reference one.** benchmark `x64/r3_final`, compared to `x64/sup_fixe2`, ms GPU.

| View | Plants, placement, front | After | Objects, placement, before | After | Foliage, drawing, front | After | Total, before | After | fps |
|---|---|---|---|---|---|---|---|---|---|
| default_s | 7,7 | 2,2 | 1,1 | 0,8 | 10,5 | 3,8 | 30,3 | 17,6 | 57 |
| slurry | 8,4 | 2,3 | 1,1 | 1,0 | 9,7 | 3,6 | 30,7 | 18,5 | 54 |
| mountain | 9,4 | 1,9 | 1,3 | 0,8 | 3,9 | 1,8 | 27,3 | 17,0 | 59 |
| mer | 0,8 | 0,2 | 0,4 | 0,3 | 0,1 | 0,1 | 9,6 | 8,7 | 115 |
| overflow | 5,1 | 1,4 | 0 | 0 | 1,9 | 1,9 | 15,8 | 12,0 | 83 |

- **The GPU varies from 5 % from one series to another:** a previous series of the same code gave 16,9 / 17,4 / 16,3 / 8,5 / 11,6 ms, its plantless views 4 to 8 % below the reference; the latter, to 2 % near the reference.
- **The sorting of foliage** (`feuillage_tri`) does not change: 0,1 to 0,3 ms.
- **Six more views,** climate families at ground and at 150 m (tropical, boreal, steppe, desert, temperate), against the binary of the `3817e79` commit: placement of 3,9-9,7 to 1,6-3,2 ms, foliage of 0,3-12,0 to 0,3-5,8 ms; tropical at 150 m from 24,8 to 12,3 ms in total.

**Quality guard:** no pixel moves more than one level, except one.
- **Identical to bit close:** sea, overflying, cumulus, orbit, globe, high160, high440.
- **One level on 3 pixels** in forest and edge, 7 in mountain: two meshes at the same depth (the color in equal depth, below). On the six more views, at most 11 pixels of a level.
- **A mountain pixel,** the reflection of a leaf, changes 76 levels from one pass to another, and a boreal one of 27: the order of plants at equal depth, drawn by atomic operations. The binary before does the same, from one pass to the next.
- **`banc_qualite.py`,** 30 places, seed 1, against `x64/qualite_r2_final` (`x64/qualite_r3`): no p95 moves; an image on 3 903 changes, by one level.

**The starting profile,** time stamps by stage, drilling_soil / slurry / mountain / overflying, ms:
- **Placing:** heavy pass 6,2 / 6,1 / 7,6 / 2,8, one tile per wire; sorting of tiles 0,2 / 0,4 / 0,3 / 1,8; scans, compaction and dispersion 0,1.
- **In the heavy pass,** by variants: the three exact floors of each tile (`ExactElevation`), the three quarters; the exact floor of nearby plants 1; the presence of woods per candidate 0,85; the materials 0,2.
- **In `ExactElevation`,** half is the double grid (`Lattice`): the GPU doubles the 64e of the float rhythm.
- **Drawing:** impostors 6,2 / 5,2 / 1,7 / 1,7; meshes close to 3,6 / 4,0 / 1,9 / 0; HiZ 0,1.

**The exact ground kept from one frame to another** (`PlantPlacement.hlsli`, `GroundCached`; `PlanetPlantPlacement.cpp`):
- **The exact ground of a tile,** at its first cell and half tile on its two axes, depends only on the tile: its cell on the grid of the planet. Similarly the exact soil of a nearby plant.
- **A hash table on the GPU keeps them:** whole key, tile, slice, plane, first cell; 2²⁰ bytes of 32 cells, four per bucket.
- **Read in the table of the previous image, written in this one:** two tables alternately; each box claimed by a single writer. No thread reads a box that another writes.
- **A key without a box is recalculated,** and retries its chance at the next frame.
- **A jump of the camera erases the tables** (`Reset`: every view of the benchmark, every button of the “Tests” palette): a view does not depend, at the last bit, on those seen before. Without this, `tropical_sol` after `tropical_150`, 300 m further, changed on 2 965 pixels, 38 of more than one level.
- **64 MB** of tables, 4 MB of claims erased at each frame; 32 MB of zeros to erase them.
- **Immobile:** heavy pass 6,2 → 1,9 ms in forest, 7,6 → 1,7 in mountain.
- **In motion,** head 0,5° and 4 % of height per frame, then 2° and 20 %: placement 6,2 to 7,3 ms without table, 2,5 to 3,8 with; overflow 4,6 → 3,2.
- **What changes in motion:** a saved value comes from a previous camera. `MakeCandidate` positions the cell from the foot of the camera, in float: the point moves less than a millimeter from one camera to another, its exact ground of the last bit. Against the calculation of each frame, at the same movement: average deviation of 0,000 to 0,006 level, at most 0,006 % of pixels beyond 8, no plate. A plant at the exact threshold of its decision is born an image sooner or later; without the table, it flashed at the will of these rounded.
- **Nothing to invalidate:** the relief does not change in flight, and the key names the cell.

**The impostors in conservative depth** (`PlanetFoliageDepth.hlsli`, `PlanetFoliageProxyVertex.hlsl`, `PlanetFoliageImpostorPixel.hlsl`):
- **The pixel of a impostor reconstructs its depth** (`SV_Depth`): the test waited for the end of the shader, four views read and illuminated, even for a hidden pixel.
- **The limit of this depth existed:** that of the HiZ (`vegetation-hiz.md`), proven on the moments of each view and each mip. It passes in `ImpostorDepthBound`, shared by the HiZ test and the drawing; the model settings carry it (`depthBounds`).
- **The quad poses at the closest possible depth;** the pixel declares its depth at the closest possible depth (`SV_DepthLessEqual`). The test rejects before the shader what the terrain, the meshes or a impostor already drawn hide.
- **Without bound,** poorly conditioned situation, the quad is close to the plane: no rejection.
- **Required by the compiler:** the pixel position at the centroid, without perspective; without multisampling, it is the pixel center, as before.
- **Gain:** 6,2 → 0,8 ms in forest, 5,2 → 0,6 in edge, 1,7 → 0,6 in mountain. Nothing in flight: seen from above, the impostors overlap little.

**The meshes close in depth first** (`PlanetFoliage.cpp`, `PlanetFoliageMeshDepthPixel.hlsl`):
- **Their depth alone,** same vertex, same alpha rejection; then their color in equal depth, once per pixel shown. The rule of the round 2, applied to the leaves.
- **At equal depth,** doubled sheets, the strict test kept the first triangle; the equal test shaded all and kept the last one. The color is drawn in the reverse order of triangles (`meshIndicesReversed`): the last ombré is the first drawn. Without this, 50 000 to 74 000 pixels would change, up to 95 levels.
- **Gain:** 3,6 → 2,7 ms in forest, 1,9 → 1,0 in mountain. The depth alone costs 1,3 to 1,5.

**The sorting of tiles without its sixteen plans** (`CullPlantTile`):
- **Each cell of a tile checked its plane:** its point on the sphere, in double precision, sixteen times. It was almost all sort: 1,8 ms in flying, 0,7 in sea, where nothing grows.
- **When the axis of the plane dominates the vertical in the middle of the tile** more than the tile can rotate it, all its cells are there. The boundary: no candidates more than d√2 of the middle on the plane, √3 times more on the sphere; twice that, and the rounding of the float.
- **Gain:** over 1,8 → 0,4 ms, more 0,7 → 0,1.

**What is still limiting:**
- **The presence of woods per candidate,** 0,85 ms in forest: two fields of noise per candidate plant.
- **The pixels of the nearby meshes,** 2,7 ms in forest: leaves in triangles of less than one pixel. The experiment: a level of detail of the meshes, with equal silhouette; it changes the image.
- **The impostors seen from above,** 1,8 ms in flight: little overlap, and the transparent part of the quads of the four views.
- **Fast moving,** the placement goes back to 3 to 4 ms: the new tiles.
- **Rest of the forest:** terrain calculation 4,1 ms, terrain drawing 3 to 4 ms, clouds and air 2,7 to 5,5 ms; in mountains, terrain drawing, 6,5 ms.
- **In flight:** `tools/tests/2026-10-28-optimisation-vegetation.txt`.

**Tested and withdrawn:**
- **The grid in pairs of floats,** `Lattice` without doubles: heavy pass −1 ms, but the image moves everywhere near the ground, 1,2 % of pixels beyond 8 levels. A shift at the last bit of the ground moves the camera and the leaves by a fraction of a pixel; the alpha edges tilt. The calculation of the terrain gained nothing.
- **Keep also the presence of woods per candidate:** slower in forest, 1,9 → 2,7 ms; keys overflow the table.
- **Skip rejected candidates before their doubles** (`MakeCandidate`): 0,1 ms maximum.

### Round 4: terrain calculation (2026-10-28)

**The calculation of the terrain is no longer redone when its inputs are those of the previous image: from 4,2 ms to 0 on the ground still, from 4,3 to 1,7 ms turning on the spot. In flight, it remains at 2 to 4,6 ms: the mesh slides with the camera, nothing is kept there.** Image identical to the bit, still as in motion. benchmark `x64/r4_final`, compared to `x64/r3_verif`, ms GPU.

| View | Land, calculation, before | After | Total, before | After | fps |
|---|---|---|---|---|---|
| default_s | 4,23 | 0 | 17,3 | 13,2 | 76 |
| slurry | 4,22 | 0 | 17,8 | 13,8 | 73 |
| mountain | 3,28 | 0 | 16,6 | 13,7 | 73 |
| mer | 2,12 | 0 | 8,7 | 6,7 | 150 |
| overflow | 1,44 | 0 | 11,8 | 10,4 | 96 |
| cumulus | 0,58 | 0 | 5,5 | 5,0 | 199 |
| orbite | 0,47 | 0 | 8,3 | 8,0 | 124 |
| globe | 1,05 | 0,14 | 4,9 | 4,1 | 243 |
| high160 | 0,41 | 0 | 4,0 | 3,5 | 283 |
| high440 | 0,42 | 0 | 3,7 | 3,4 | 291 |

- **The views of the benchmark are immobile:** this table is the most favorable case. The two following benchmarks movements give what is worth in flight.
- **Turning on the spot,** 0,5° per frame, against the whole calculation at each frame at the same movement:

| View | Field, calculation, integer | kept | Total, whole | kept | fps |
|---|---|---|---|---|---|
| default_s | 4,29 | 1,70 | 20,1 | 17,3 | 50 → 58 |
| slurry | 4,85 | 1,88 | 22,0 | 19,1 | 45 → 52 |
| mountain | 3,29 | 1,08 | 19,3 | 17,1 | 52 → 59 |
| mer | 2,20 | 1,10 | 9,0 | 8,0 | 111 → 125 |
| overflow | 1,46 | 0,47 | 12,4 | 11,5 | 81 → 87 |

- **In flight,** `--motion "0.2 0 0 0 0 0.05"`, 5 % of height per frame: nothing changes, terrain 4,3 / 4,6 to 5,0 / 3,4 to 3,7 / 2,2 / 1,4 ms in forest, edge, mountain, sea, flying over; total 19 to 24 ms on the ground, 41 to 52 fps.
- **The GPU varies from 5 to 10 % from one series to another:** in flight, where nothing is kept, two series of the same work give 24,2 and 22,6 ms in margin.

**Quality guard:** no pixel moves.
- **Immobile:** the ten identical views bit close to `x64/r3_verif`.
- **In motion,** against the whole calculation at each frame, at the same movement: identical to the bit near when rotating (0,5° per frame), in flight (5 % of height per frame), in slow flight (0,2 %), and at stop after a movement (ten still frames before capture).
- **`banc_qualite.py`,** the 30 places of `x64/qualite_r2_final` (`x64/qualite_r4`): no p95 moves. A crop on 3 891 changes by one pixel, from 3 levels, to 12 m: the same crop changes from one pass to another since the round 2, the order of plants at equal depth.

**The starting profile,** time stamps by stage, ms, foret_sol / slurry / mountain / sea / overfly:
- **The summits of the mesh** (`TerrainCompute.hlsl`): 2,96 / 2,89 / 2,52 / 1,27 / 0,47. 1 114 rings on the ground, 890 000 vertex, sorting in keeps the visible part.
- **The fine grid** (`FineTerrain.hlsl`, `FineNormals.hlsl`), far from the ground only: fly-over 0,85 and 0,01.
- **The relief of materials** (`MaterialRelief.hlsl`), extinct, one copy: 0,07 to 0,19. Removed the 2026-10-30: the march to the sun written in the tops of the field.
- **The walk to the sun** (`Horizon.hlsl`): 1,24 / 1,29 / 0,75 / 0,61 / 0,06.
- **The prefilter of normals** (`SplinePrefilter.hlsl`): 0,02 to 0,13. Removed the 2026-10-30: the spline reads the vertex itself (`spec-normales-spline.md`).
- **In the summits,** by variants: those of grid cells less than 4 m, the grid in double precision (`EXACT_LATTICE_MAX_CELL`), cost 2,4 ms of the 3 in forest. The float grid everywhere would remove 1,7 / 1,2 / 0,8 ms in forest, mountain, sea: the doubles weigh more than all the noise in floats.
- **What is repeated at equal inputs:** everything, at each frame. Still, nothing has changed; while turning, the height of the summits has not changed, only the sorting.

**The saved calculation** (`D3DApp::Draw`, `TerrainInputs`; `TerrainCompute.hlsl`, `FineTerrain.hlsl`):
- **The key is exact:** the constants that the field passes read, recorded in their compiled code (`cbufferLoadLegacy` of DXIL), compared to the bit close. Nothing else enters: the field stamps are written only by these passes, their textures are fixed.
- **The mesh first:** the face axes, its half width, the nadir in double precision, the rings and the fine grid, the camera on the face. Equal, each vertex is at the same point of the planet, with the same octaves: its height is the same.
- **Then the view and the sun:** the camera axes, the sun, the margin of the waves. They only decide the necessary summits and the horizon.
- **All the same:** none of these passes are carried out. Transitions remain; buffers keep what they wrote.
- **mesh only equal,** the camera turns on the spot: a vertices calculated at the previous image, `NaN` otherwise, keeps its height; only those that enter the view are calculated. A vertices out of view becomes `NaN` again, as in the whole calculation: normals and the walk to the sun see the same mesh. These passes are redone.
- **The walk to the sun is redone by turning:** it reads the heights of the neighboring vertices, zero for those that the sorting removes; changing the sorting, its result can change.
- **No camera jumps are to be processed:** an equal key gives a result equal to the bit closest, regardless of the above.

**What is still limiting:**
- **In flight, everything is redone.** The mesh slides continuously with the camera: no vertex remains at the same point from one frame to another. A mesh placed by step on the planet grid would keep each vertex, but it is removed: its refinement would be seen in fast movement (`principes.md`).
- **The grid in double precision,** 1,7 ms in forest: per axis and per octave, a multiplication and an addition in double precision, at the 64e of the rhythm of floats. Approached, it changes the last bit of the ground under the camera, thus the entire image (round 3).
- **The walk to the sun,** 0,6 to 1,3 ms on the ground: his steps start from the grid cell and grow by 2 %, about 500 near the camera; half the time is reading the heights.
- **The wave margin also applies on land:** 16 to 128 m around the view, for sea summits that the waves move. Without it, 0,3 ms less in forest and 0,6 in sea, unchanged image on five views; but to prove that a summit is not of the sea requires its height.
- **Rest on the ground in flight:** terrain drawing 3 to 7 ms, foliage 2 to 4 ms, clouds and air 3 to 7 ms; forest and edge remain under 60 fps in fast flight.
- **In flight:** `tools/tests/2026-10-28-optimisation-terrain.txt`.

**Tested and withdrawn:**
- **The grid in integers:** the cutting of `Lattice`, floor and remains in float, redone by whole operations on the bits of the double, the product only in double precision. Exact to the bit on 1,1 million values, rounded and equals included, and on all views; but not faster, 3,07 ms against 2,96 in forest. A double addition is worth thirty whole operations, the cutting required as much.
- **Unroll the octave loops,** so that the frequencies in double precision become constants: slower, 3,26 ms, and the sea changed 20 levels on average.
- **128 threads per group instead of 64:** without effect.
- **Keep the heights of the last grid cell in the march to the sun:** correct, no effect; the readings were already cached.
- **A lower height limit to stop the walk:** 2 000 m instead of 10 000, not exact, only gains 0,25 ms in forest. An exact boundary, the maximum of the heights of the mesh, would gain less where mountains are in sight.

### Round 5: flight images (2026-10-28)

**Stop at measurement: the GPU waits for the CPU only 0,7 to 0,9 ms per frame on the ground, still as in flight.** Two images in flight would make at most this time: from 71 to 75 fps on the ground still, from 50 to 52 in flight. It is below the threshold of 1 ms set initially, in the noise of the GPU, for a redesign that affects all readings from the GPU to the CPU.

**The measure,** `tools/banc_perf.py`, new columns (The benchmark). Immobile `x64/r5_mesure`, in flight `--motion "0.2 0 0 0 0 0.05"` `x64/r5_mesure_vol`; ms per frame.

| View | List and Submission, CPU | GPU inactive | Total GPU | Cadence | fps GPU | Actual fps |
|---|---|---|---|---|---|---|
| default_s | 0,83 | 0,77 | 13,3 | 14,1 | 75 | 71 |
| slurry | 0,93 | 0,89 | 14,7 | 15,6 | 68 | 64 |
| mountain | 0,85 | 0,84 | 14,2 | 15,1 | 70 | 66 |
| mer | 0,73 | 0,73 | 6,8 | 7,5 | 147 | 133 |
| overflow | 0,86 | 0,82 | 10,8 | 11,6 | 92 | 86 |
| cumulus | 0,62 | 0,62 | 5,2 | 5,9 | 191 | 171 |
| orbite | 0,82 | 0,83 | 8,3 | 9,1 | 120 | 109 |
| globe | 0,76 | 0,77 | 4,1 | 4,9 | 244 | 205 |
| foret_sol, in flight | 0,84 | 0,81 | 19,1 | 19,9 | 52 | 50 |
| slurry, in bulk | 0,82 | 0,80 | 22,1 | 22,9 | 45 | 44 |
| mountain, in flight | 0,87 | 0,81 | 19,1 | 19,9 | 52 | 50 |
| over, in flight | 0,76 | 0,71 | 12,5 | 13,2 | 80 | 76 |
| orbit, in flight | 0,90 | 1,16 | 43,9 | 45,1 | 23 | 22 |

- **Imaging preparation costs 0,01 to 0,04 ms;** list registration costs 0,35 to 0,53 ms; submission and presentation costs 0,27 to 0,40 ms.
- **The CPU waits for the GPU almost everything else:** `cpu_attente` is worth the total GPU to 0,1 ms close.
- **The inactive GPU is worth what the CPU does between two images:** it waits for the next one to be recorded and submitted. The cadence is the total GPU plus this time, to 0,05 ms close.
- **The fps of the rounds 1 to 4 are those of the time GPU:** the actual cadence is 4 to 16 % lower, the most in high altitude where the image is short.
- **The image does not change:** the ten still views identical to the bit close to `x64/r4_verif`; the measurement only adds time stamps of the CPU.

**What two images in flight would ask for,** noted in the code and not done:
- **Double by frame in flight** the buffers that the CPU writes: constants of the frame, clouds, sea, cascades.
- **Read each record in the image that wrote it:** timestamps, object and plant counters, sea level, capture.
- **The ground under the camera** (`mReadbackBuffer`) would arrive one frame later: the height of the camera would change in flight, so the image. The benchmark mode should keep an image in flight.
- **What the GPU keeps from one frame to another would remain accurate without doing anything:** the terrain of the 4 round, the table of the soil of plants, the histories ones. The queue executes the images in order; the key compares to the previous image, which wrote the buffers just before on the GPU.

**What limits the pace:**
- **The time GPU,** 94 to 96 % of the ground cadence: 19 to 22 ms in forest and edge flight, where the terrain calculation is redone at each frame, 4,4 ms (round 4).
- **In flight beyond x5 in altitude,** cloud passage, 15 to 38 ms (round 1).
- **The share of CPU,** 0,8 ms, counts only above 120 fps: 10 % of the cadence at sea, 16 % at the globe.

**To be resumed if** the time GPU falls below 8 ms at the ground: the gain would become 10 % of the cadence.


### Round 7: clouds in fast flight (2026-10-29)

**Below 14 km, the fast flight no longer traces every pixel that has slipped: one pixel per square 2×2 is traced, the other three are interpolated.** Cumulus to 10 km in fast flight: the change from 24,2 to 8,1 ms, from 36 to 90 fps real; 150 m under the cumulus in dive: from 18,1 to 9,5 ms, from 34 to 52 fps. Above 14 km, nothing changes: 160 and 440 km remain at 15 ms, the orbit at 38 ms. Still image identical to the bit. benchmarks `x64/r7_final_*` against full pass at the same movement, `x64/r6_full_*`; front, `x64/r6_avant_*`.

**Why history is rejected in fast flight,** measured at 5 % of height per frame:
- **The turn is not the only reason.** Without it, cumulus 24,0 → 22,8 ms, high160 14,9 → 13,2; orbit 38 → 20 ms, but its deviation at full pass passes from 0,67 to 4,88 levels, 46 % of plates.
- **At 10 km, the drift throws out:** 500 m per frame, clouds at a few kilometers; the spreading in distance of a volume slides by more than one pixel.
- **The reprojection already sees the parallax of the volume:** the drift is the slip between the front and back of its light. The frame-by-frame turn limits the re-sampling softening (round 6, tag `piste/optimisation-r6-nuages-mouvement`). Keeping the history longer costs the gap everywhere.
- **It remains to trace cheaper what has slipped.**

**The pixels that moved, one per square 2×2** (`CloudsTemporal.hlsli`, `PSCloudTraceHalf`, `CloudTemporalHalfFill`):
- **A half resolution pass,** one texel per square of 2×2 pixels; the pixel tracked rounds the square in four frames, with the tile 4×4.
- **It draws a square when the history of one of its four pixels has slipped or rotated,** by the resolution decision itself (`CloudTemporalLookup`, shared).
- **The resolution takes the trace as it is at the pixel traced,** and for the other three the bilinear interpolation of the neighboring squares that see the same surface. Without a neighboring square, the pixel is plotted, as before.
- **The interpolated pixel is kept as a fill,** at 0,75 drift pixel: at the stop, the tile 4×4 replaces it in 16 images.
- **Decided by square, not by pixel:** decided at the single pixel plotted, its neighbors of the same square plotted in scattered order; cumulus 14,2 ms instead of 8,2.

**Under the door of the distant quadrature only,** camera under 14 km (`CloudTemporalHalfOn`, `CLOUD_FROSTBITE_ORBIT_CAMERA_GATE_LOW_KM`):
- **There, no pixel does not mean rays under the pixel:** clouds are larger than it. The interpolation departs by one level on 12 % of the pixels of the cumulus, by more 2 levels on less than before.
- **Above, the grain of the distant clouds is pixel:** interpolated, it softens. Everywhere, the orbit fell from 38 to 14 ms, but from 0,67 to 2,94 levels and from 1,1 to 7,5 % beyond 8; globe 0,55 → 1,13; high440 1,15 → 1,78.
- **haut160 did not suffer from it,** 15 → 7 ms at equal margin: its grain is low. No rule from the estimator distinguishes it from the orbit; the thresholds on the image failed (below).
- **At the passage of 14 km,** the difference between the two regimes is one level: nothing jumps.
- **Above, the pass does not launch** (`D3DApp::Draw`): 0,2 to 0,7 ms less than launching it empty, diving above 14 km.

**The cost, pass of atmosphere and clouds, ms, before → after; actual fps before → after:**

| View | fast flight | Actual fps | Diving | Actual fps | slow flight |
|---|---|---|---|---|---|
| cumulus | 24,2 → 8,1 | 36 → 90 | 17,3 → 16,6 | 50 → 50 | 23,4 → 8,8 |
| cumulus_sol | 7,6 → 6,0 | 59 → 70 | 18,1 → 9,5 | 34 → 52 | 5,1 → 5,3 |
| overflow | 1,5 → 1,4 | 71 → 77 | 18,6 → 15,2 | 35 → 38 | 1,5 → 1,4 |
| default_s | 3,2 → 3,0 | 48 → 52 | 5,5 → 5,2 | 43 → 49 | 2,9 → 2,8 |
| slurry | 7,1 → 6,9 | 41 → 43 | 7,5 → 7,2 | 45 → 48 | 6,7 → 6,3 |
| mountain | 2,7 → 2,6 | 48 → 50 | 2,9 → 3,0 | 45 → 45 | 2,5 → 2,6 |
| mer | 4,5 → 4,5 | 104 → 102 | 4,4 → 4,7 | 117 → 108 | 4,7 → 4,6 |
| high160 | 15,1 → 14,9 | 56 → 57 | 4,1 → 4,3 | 166 → 158 | 3,4 → 3,4 |
| high440 | 15,7 → 15,0 | 50 → 53 | 3,3 → 3,5 | 203 → 189 | 3,4 → 3,3 |
| orbite | 38,3 → 38,0 | 22 → 22 | 17,6 → 18,1 | 43 → 43 | 4,0 → 3,8 |
| globe | 9,7 → 9,4 | 74 → 77 | 2,8 → 3,0 | 189 → 182 | 10,8 → 10,5 |

- **Fast flight** `--motion "0.2 0 0 0 0 0.05"`, **diving** `"0 0 0 1.025"`, **slow flight** `"0.1 0 0 0 0 0.01"`.
- **In diving, cumulus and flying gain little:** the descent starts from 36 times the height, above 14 km for most of the 120 images measured.
- **Above 14 km, the variations are in the noise of the GPU,** 5 to 10 %. Avant/après measured on the same day in dive, high160 4,21 → 4,27 ms, orbit 17,59 → 17,73.

**Quality guard:**
- **Immobile:** the ten identical views bit close to `x64/r4_verif`, including mountain (`x64/r7_final_fixe`).
- **In motion, against the full pass at the same movement:** the eleven views give the same deviations as before, except two, to the hundredth:
  - **cumulus in fast flight:** 0,06 → 0,13 medium level; beyond 8 levels, 0,01 → 0 %; plates 0,03 → 0 %. The mean rises by one level deviation, on 12 % of pixels; those of 2 levels and above decrease.
  - **cumulus_sol in dive:** plates 4,91 → 4,95 %, the rest equal.
- **What is improving:** cumulus in dive, 1,66 → 1,55 % beyond 8 levels, plates 3,26 → 2,19 %; cumulus in slow flight, 0,21 → 0,19 level, plates 0,06 → 0,01 %.
- **`banc_qualite.py`,** the 30 places of `x64/qualite_r2_final` (`x64/qualite_r7`): no p95 moves.

**What is still limiting:**
- **Above 14 km in fast flight, the pass costs the full pass:** orbit 38 ms, 22 fps; 160 and 440 km 15 ms, 53 to 57 fps; globe 9,4 ms.
- **The experiment:** a cheaper grainless distant quadrature, its rays under the pixel sharing the walk, the jump of the void and the light towards the sun; or a computation pass that compacts the pixels to be traced.
- **The threshold of 14 km is that of the distant quadrature,** not a measure of grain: at 160 km, half resolution would go as well, without a rule proving it.
- **In flight:** `tools/tests/2026-10-28-optimisation-nuages-rapides.txt`.

**Tried and removed,** fast flight, against the full pass:
- **Without the turn:** see above; orbit at 4,88 levels.
- **A single distant ray per pixel traced:** orbit 38 → 19 ms, high160 15 → 8,9 at equal distance; but globe 0,55 → 1,34 level, high440 1,15 → 1,66, orbit 0,67 → 1,01: a grain that sparkles.
- **A single distant radius where the history is smooth,** judged on the range of its four texels: tight thresholds, no gain; loose, high160 15,6 → 14,0 ms, orbit 38,8 → 34,8, the gap rising everywhere.
- **Half resolution everywhere, history limited to neighboring squares,** like a TAA: orbit 2,31 levels instead of 2,94, still far from 0,67; cumulus 0,32.
- **Half resolution everywhere, traced where neighboring squares diverge:** orbit 43 ms, slower than before. Scattered traces cost the whole wave.
- **The grain measured in the square history:** still scattered, orbits 38 ms and 2,03 levels.
- **Where the distant weight of the pixel is zero:** haut160 does not gain anything, and the globe goes from 1,80 to 2,23 % beyond 8 levels: its limb, rasant, has not distant quadrature, but grain.

### Round 8: ground in fast flight (2026-10-29)

**In fast ground flight, from 49 to 60 real fps in forest, from 43 to 55 in edge, from 48 to 54 in mountain.** Two changes: the sky holes in the leaves are no longer traced by cloud resolution; in flight, the terrain grid is cut into pairs of floats. Still image identical to bit close to `x64/r4_verif`. benchmarks `x64/r8_final_*`, against the forward binary measured in the same session, `x64/r8_avant_seance_*`; the first "forward", `x64/r8_avant_*`, is from a session where the GPU was 10 % faster.

**The idle of the GPU in the mountains was not the engine:** 5,5 ms in `x64/r7_verif_rapide`, but all the times of the CPU were multiplied by four, the sea too. Repeat, 0,55 ms, as everywhere.

**The fast flight,** `--motion "0.2 0 0 0 0 0.05"`, ms GPU before → after:

| View | Land, calculation | Cloud resolution | Total | Cadence | Actual fps |
|---|---|---|---|---|---|
| default_s | 4,6 → 3,0 | 1,8 → 0,8 | 19,7 → 16,1 | 20,6 → 16,8 | 49 → 60 |
| slurry | 4,8 → 3,3 | 3,6 → 0,9 | 22,5 → 17,5 | 23,5 → 18,2 | 43 → 55 |
| mountain | 3,6 → 2,5 | 1,2 → 1,0 | 19,7 → 17,6 | 20,6 → 18,4 | 48 → 54 |
| mer | 2,3 → 1,7 | 0,7 | 9,2 → 8,3 | 10,0 → 9,0 | 100 → 111 |
| overflow | 1,4 | 0,5 | 12,7 → 12,0 | 13,5 → 12,7 | 74 → 79 |
| cumulus_sol | 1,7 → 1,4 | 1,3 | 14,4 → 13,2 | 15,4 → 13,8 | 65 → 73 |

- **Resolution:** the passage of the atmosphere less the clouds trace.
- **In slow flight,** `"0.1 0 0 0 0 0.01"`: forest 51 → 57 real fps, edge 46 → 54, mountain 53 → 56. **In diving,** `"0 0 0 1.025"`: forest 48 → 56, edge 47 → 55, mountain 47 → 48.
- **Above the ground, nothing changes,** at 5 % close, the noise of the GPU: cumulus, orbit, globe, 160 and 440 km.
- **The forest reaches the actual 60 fps, just right:** 16,8 ms of cadence. Lisière and mountain remain above the 16,6 ms.
- **Another engine on the GPU fakes the benchmark:** a session on another worktree raised cumulus_sol immobile from 11 to 15,7 ms; signature, more than 2 ms of GPU inactive and waiting of the CPU over time GPU. The figures above are redone without it.

**The sky holes held the resolution of the clouds** (`CloudsTemporal.hlsli`):
- **Still, the resolution costs 0,6 ms; in flight, 1,8 ms in forest, 3,6 in edge.**
- **The cause:** 28 pixels per frame in forest, 45 in edge, traced by the resolution itself: new sky holes in the leaves, which neither the history nor the fresh tiles of the 5×5 see.
- **Everyone holds his wave:** a ray of almost horizontal sky walks hundreds of kilometers, and the pass waits for the last wave. Without these traces, edge 6,1 → 3,2 ms, forest 2,8 → 1,6.
- **Now, under the door of the 14 km** (`CloudTemporalHistoryFill`): the texel closest to the historical, around the reprojected pixel, which sees the same surface; in the 5×5, otherwise on a grid of 9×9 all the 6 texels.
- **A hole that nothing sees remains clear for this image,** then the squares 2×2 retrace it. A surface that nothing sees is traced as before: its clouds in front of it differ from those of its neighbors.
- **Above 14 km,** nothing changes.

**The grid of the field in pairs of floats, in flight** (`Noise.hlsli`, `TerrainComputePairs.hlsl`, `D3DApp::Draw`):
- **The double grid cost 2,4 ms of the 3 of the forest vertices calculation** (round 4): the GPU doubles the 64ᵉ of the float rhythm.
- **In pairs:** the point and frequency, each in two floats, about 48 bits; the exact product by Dekker method. Per octave, two double-precision operations instead of seven.
- **The point is the same at 2·10⁻⁸ m;** only the last bit of a height can change (`geometrie.md`).
- **Only in flight:** the mesh has slipped to this image and the previous one, and its grid cells is less than 4 m, where the grid goes into doubles. After a jump, the first image is accurate; at the stop, the entire mesh is recalculated into doubles, once.
- **A shader apart:** the exact same code, compiled into a single shader with the pairs path next to it, changed its last bits, and the still image with: 1,11 level edge, 1,77 % beyond 8. The exact shader remains the binary from before, bit close.
- **The vertex under the camera remains accurate:** the pairs lane leaves it without ground; the exact shader, re-launched with the mesh kept (`camPlane.z`), calculates only it. Calculated in pairs, it moved the camera by a fraction of a millimeter: 1,56 level edge, 2,7 % beyond 8, in the edges of the leaves.

**Quality guard:**
- **Immobile:** the ten views identical to the bit close to `x64/r4_verif`, including mountain; cumulus_sol identical to `x64/r8_avant_fixe` (`x64/r8_final_fixe`).
- **In motion, against the forward binary at the same motion:** on the ground, 0,05 to 0,09 medium level, 0,02 % of pixels beyond 8. Isolated pixels at the edges of leaves and trunks, which the last bit of ground moves by a fraction of a pixel. In mountains, 0,15 % of plates at the foot of the trunks, at 4 km altitude where the last bit is 0,5 mm. Above the ground, identical.
- **Against the full pass at the same move** (`x64/r6_full_*`): the same gaps as before at 0,1 level close. Forest 0,10 → 0,15, edge 0,11 → 0,16, mountain 0,05 → 0,13 in fast flight; other views unchanged, in fast flight, slow flight and diving.
- **`banc_qualite.py`,** the 30 places of `x64/qualite_r2_final` (`x64/qualite_r8`): no p95 moves, including mutation.

**What is still limiting:**
- **Lisière and mountain remain below 60 fps in fast flight,** 55 and 54. The edge: clouds and air 3,8 ms, including the trace 2,6. The mountain: the terrain drawing, 7 ms, twice the forest.
- **The calculation of the terrain in flight remains at 2,6 to 3,4 ms:** the walk to the sun, 0,6 to 1,3 ms, and the rest of the summits.
- **The experiment of the walk to the sun:** jump the steps of which the highest of the grid cells of the ring can not change neither the horizon nor the height of shadow. Exactly, but one more pass.
- **The placement of plants in flight,** 2,1 to 2,6 ms: its exact floors are also in double precision; in pairs, their last bit would enter the table kept.
- **In flight:** `tools/tests/2026-10-29-optimisation-sol-vol-rapide.txt`.

**Tested and withdrawn:**
- **Expand search in fresh tiles,** 9×9 then 17×17: edge 6,1 → 4,1 ms; its loop becomes the new trail.
- **Dense history search,** up to 25×25: likewise, 4,3 ms.
- **Let clear any surface that nothing sees:** isolated points on the distant relief of the mountain, 0,25 % of plates.
- **Fill also the pixels slided that the squares 2×2 do not see:** no measured case.
- **Pairs in the same shader as the exact calculation:** the still image changed (above).
