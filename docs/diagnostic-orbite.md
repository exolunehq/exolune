# High-orbit performance correction

**Status, 2026-11-07: against `main` itself, the erosion costs under 15 % of its frame rate at every view, 14 % at worst. Against erosion off, seven views of eight; 97 km loses 15.6 %.**

## Against main, 2026-11-07

**Goal: the erosion costs `main` at most 15 % of its frame rate.** Its cost is measured in its own executable, erosion on against erosion off (`principes.md`): `main` has heavier clouds, 0.5 to 1 ms, that the branch lacks. Moving camera, same protocol, eight views, two runs each; `E:/Exolune-diagnostics/goal-20261106/`: `main` (dc24e0b) in `main2/`, the erosion before this work in `erosion/`, after batch 1 in `it14/`, batch 2 in `it21/`, now in `fin1/` and `fin2/`, erosion off in `fin1-off/` and `fin2-off/`.

| View | FPS, `main` | Erosion's cost before, ms | Batch 1 | Batch 2 | Now | Allowed | FPS lost, now | Against `main` itself |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Approach, 250 km | 76.7 | 36.0 | 4.5 | 2.5 | 2.0 | 2.3 | 13.4 % | −9.1 % |
| Valley heads, 97 km | 88.3 | 8.7 | 4.2 | 2.4 | 2.1 | 2.0 | 15.6 % | −13.9 % |
| Upstream valley, 3,840 m | 20.2 | 4.4 | 3.6 | 2.7 | 2.6 | 8.7 | 5 % | +5 % |
| Confluence, 2,200 m | 57.1 | 7.5 | 4.2 | 3.9 | 3.0 | 3.1 | 14.7 % | −13.9 % |
| Massif, 1,231 km | 95.3 | 6.1 | 3.6 | 2.1 | 1.8 | 1.9 | 14.9 % | −13.6 % |
| Hemisphere, 3,000 km | 106.3 | 1.8 | 1.6 | 1.5 | 1.2 | 1.7 | 12 % | −9 % |
| Globe, 10,000 km | 164.6 | 1.2 | 0.5 | 0.4 | 0.4 | 1.1 | 6 % | −4 % |
| Far, 40,000 km | 322.8 | 0.7 | 0.3 | 0.1 | 0.1 | 0.5 | 4 % | −3 % |

- **Allowed:** `main`'s frame time × (1 / 0.85 − 1). Runs vary by 0.1 ms.
- **Against `main` itself,** every view within 15 %. Against erosion off, 97 km stays 0.09 ms over.
- **At 2,200 m the two scenes differ:** erosion on, the ground under the camera lies at 1.5 km in a forested valley, 5,153 trees; off, at 4.9 km on a bare plateau, none.

**Batch 1, settings and evaluation:**
- **Screen relief crossfade from 150 to 200 km,** formerly 400 km (`ScreenReliefHigh`). A setting; images within 3/255 on average.
- **Courses built once at startup** (`ErosionCourseBuild.hlsl`, `spec-erosion.md`). A junction's meander at full detail: a model change, sub-footprint.
- **Shared node listings** by wave and by tile; **direct screen relief** when the map answers every footprint; **mesh rivers from the map** at mid orbit, within 5/255; **contour bands** halved, within 6/255.

**Batch 2, all exact (images identical to the bit in one executable):**
- **Screen rivers per texel in a kernel of their own** (`ScreenRiverTexel.hlsl`), wide searches to a wave each; the former queue of node tasks, its results and reduction deleted, 270 MB of scratch with them. 250 km: rivers from 2.7 to 0.9 ms.
- **Fine grid and mesh by 8 × 8 tiles of samples:** 97 km's fine grid from 1.9 to 1.4 ms, 3,840 m's mesh from 1.9 to 1.2 ms.
- **The contour lists wet nodes only** (`ErosionCourseWet.hlsl`), **gated by their channels' reach,** or the fine grid's near nodes alone (`ErosionRiversNear`): 97 km's contour from 2.1 to 1.3 ms.
- **The wave's listing without margin** for helper lanes, and **handing over each node's word and bound:** 0.1 to 0.2 ms each.

**Batch 3:**
- **Each screen texel's finish in its river kernel** (`ScreenFinishTexel`): exact; 250 km and 1,231 km 0.4 to 0.5 ms faster.
- **The fine grid's culling margin, 6 fine cells instead of 6 mesh cells** (`spec-rendu-lointain.md`): exact; 97 km 0.28 ms faster.
- **The plants' missing exact grounds in a pass of their own** (`PlanetPlantGround.hlsl`, `optimisation.md`): within 1/255 on 8 pixels; 2,200 m 0.5 to 0.65 ms faster.
- **The contour's band at 0.6–0.9 samples instead of 0.8–1.2,** no grid water past it outside lakes; the inland reflection's sky in 3 steps: within 8/255; 97 km 0.15 ms faster.

**Measured, not retained:**
- **Signed channel distance** for a narrower band: no gain, images changed by the blend's band.
- **The fine grid's rivers in their own kernel:** exact, but its 100 MB intermediate buffer cost more, +0.6 ms at 2,200 m and 10,000 km.
- **The node's position handed over:** −0.2 ms, but its last bits differ from each lane's own; computed `precise` to share it, +0.3 to +0.9 ms.
- **The contour's band at 0.4–0.6 samples:** 0.34 ms at 97 km, but spots of 24/255 in a meander's bend; at 0.5–0.75, no more than at 0.6–0.9.
- **No gain:** the ravines' steering bounded by those drawn; the water gate before the corridor's setup, and a curve-distance gate; the fine grid's near reach at 2.5 cells; the contour without its fallback; shore bands of 1.5 and 1 height bands; plants' exact ground at a 4 m footprint; fewer ravine slots; float lattice splits.

**Where the rest goes, ms over erosion off:**
- **97 km:** the pixel 1.27: its channel contour 1.0, shores 0.3, water shading 0.1. The fine grid 0.58, its rivers 0.45. Clouds and air 0.34, over deeper valleys.
- **The pixel's channel contour at 97 km:** setup and node positions 0.35, each course's gates 0.53, meanders and sections 0.25.
- **The fine grid's rivers:** listing 20 %, records and chord gates 15 %, closest points 12 %, the corridors that reach a sample 55 %. Its ravines cost little.
- **1,231 km:** screen rivers 1.22, screen ground 0.25, the pixel 0.32.
- **2,200 m:** the fine grid 1.2, the pixel 1.1, plants 0.5; clouds and air 0.6 less.
- **The cost split's method:** a switch returning at a stage, its value kept alive through every field a caller reads, by a factor zero at run time.

**Quality bench** (`tools/banc_qualite.py`, 30 places, seed 1): the branch in `goal-20261106/qualite-fin/`, `main` on the same places in `qualite-main/`.
- **Against `main` on the same places, 12 p95 of 50 worse by over 10 %:** the octave gap of soil and grass from 50 to 800 m, of rock at 12 and 800 m; repetition of rock at 12 and 50 m, of grass at 12 m. Snow improves by 15 to 42 %.
- **On the 13 worst places** (`qualite-subset.json`): erosion off in the branch keeps 4 of them, grass at 200 m and soil at 12 and 800 m among them: not the erosion's. Without rivers, all 9 remain: not the rivers'.
- **The erosion's own:** rock at 12 and 50 m, from one cliff the valleys bare, its rock texture's horizontal strata repeated down the face; the soil's gap at 50 m, two places.
- **Ravines twice as bent (`RAVINE_SHAPE.w` 0.5), not retained:** still 9, moved from soil to rock and snow.
- **Not resolved:** the strata's regularity on bare faces is the rock texture's, the next quality task.

**Timing windows:** a remote desktop stream (Parsec) takes about 18 % of the GPU. In such a window every cost reads 0.15 to 0.4 ms higher: compare builds only by alternating runs in one window. So measured, reading `ErosionCoursesBuilt` once per query instead of per node saves 0.06 ms at 97 km and 0.12 ms at 2,200 m, exact by construction; the table above predates it.

**Method limits:** a rebuilt executable's first run recompiles its pipelines for minutes, and its first view can measure slow: discard it. Two executables differ in their last bits; plants amplify them at 2,200 m.

## Water contour rungs, 2026-11-06

**The pixel contour now costs 16.4 ms at 250 km instead of 21.6, and 5.3 ms at 97 km instead of 11.1.** Moving camera, same protocol; `claude-contour-moving/` against `contour-probe0/`, before, and `contour-probe1/`, contour off, same day.

| View | FPS before | FPS after | FPS, no erosion | Contour before, ms | Contour after, ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Approach, 250 km | 17.8 | 20.5 | 65.9 | 21.6 | 16.4 |
| Valley heads, 97 km | 37.1 | 49.6 | 90.7 | 11.1 | 5.3 |
| Upstream valley, 3,840 m | 19.2 | 20.0 | 22.5 | 1.5 | 0.6 |
| Confluence, 2,200 m | 34.6 | 39.4 | 58.8 | 2.4 | 0.9 |

- **Contour:** terrain drawing minus the same pass with the contour off.
- **Diagnosis:** 14 % of the pixels were candidates at 250 km, 5.5 % at 97 km. The river query took 62 to 73 % of each, the terrain the rest.
- **Change:** away from a shore's level, the grid's ground and the channels alone at the pixel (`spec-eaux-interieures.md`, `spec-erosion.md`). Without clouds, its images match the whole relief's within 7/255, p99.9 at most 2/255, in all four views.
- **Remaining at 250 km:** shore candidates within two height bands keep the whole relief, 4.7 % of the pixels by whole waves. The screen relief's rivers cost about 12.7 ms there, the fine grid's 4.1 ms.
- **Measured, not retained:** listing the nodes takes 28 % of the channel rung at 97 km. A channel bound per node would remove 30 % of the nodes prepared.
- 1,231 km is unchanged: 16.4 ms, 59.4 FPS (`claude-contour-orbit/`).

## Low altitudes, 2026-11-06

**The largest erosion cost is below 400 km, not in mid orbit.** Moving camera, same protocol, review route views; `claude-low-moving/` and `claude-low-off/` (mode 0, same executable) in `E:/Exolune-diagnostics/orbit-20261106/`.

| View | FPS, erosion | FPS, none | Gap, ms | Terrain drawing | Screen relief | Fine grid | Mesh |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Approach, 250 km | 18.6 | 65.9 | 38.5 | 21.3 | 12.7 | 4.1 | 0.5 |
| Valley heads, 97 km | 38.4 | 90.7 | 14.9 | 11.1 | 0 | 3.3 | 0.4 |
| Upstream valley, 3,840 m | 19.7 | 22.5 | 6.3 | 1.7 | 0 | 1.9 | 1.9 |
| Confluence, 2,200 m | 37.1 | 58.8 | 10.0 | 3.3 | 0 | 4.1 | 0.9 |

- **Terrain drawing:** near a channel, an unresolved pixel evaluated the whole terrain, rivers included, to place the water's contour (`PixelShader.hlsl`, `refine`). Its rungs since: above.
- **150 to 400 km:** the fine grid, both screen-relief evaluations and the pixel contour all keep their rivers across the crossfade.
- Plant placement adds 1.8 ms at 2,200 m.
- The CPU port counts, around the massif, 7.5 node tasks per query where a river passes, for 1.75 courses that change the result; 1.35 tasks where none does (`tools/hydro/cp.py`).

## Rivers' map for wide footprints, 2026-11-05 late night

**Cause: wide footprints enumerated courses whose effect they cannot resolve.**
- From 10,000 km, mesh vertices, limb samples and distant texels each enumerated hundreds of courses: 2.5 to 5.6 ms per consumer.
- The fine grid's limb samples filtered their rivers at their own cell, about 11 km edge-on at 10,000 km, while only limb pixels over 100 km wide read them.

**Changes:**
- `ErosionRiverMap.hlsl`: at startup, the complete river evaluation on a padded cube map of about 25 km cells, six GPU-only slices of `t23`. 36 ms; the erosion texture grows from 72 to 84 MB.
- `ErosionRivers`, `ScreenRiverQueue`, `ScreenRiverReduce`: a sampling radius from one map cell blends into the map, from √2 cells reads it alone, in B-spline with face blending (`spec-erosion.md`).
- `FineTerrain.hlsl`, `FineLimbFootprint`: under a full screen relief, the limb samples filter their rivers at the reading texel's footprint, as the screen relief does.

**Moving camera, 1920 × 1080, clouds and vegetation, same protocol as below:**

| View | Before | Map | Map and limb footprint | No erosion |
| --- | ---: | ---: | ---: | ---: |
| Massif, 1,231 km | 56.3 | 59.9 | **59.8** | 89.8 |
| Hemisphere, 3,000 km | 65.6 | 83.0 | **89.5** | 100.7 |
| Globe, 10,000 km | 66.7 | 100.3 | **133.6** | 148.5 |
| Distant globe, 40,000 km | 69.4 | 180.4 | **243.3** | 260.6 |

- Runs in `E:/Exolune-diagnostics/orbit-20261105/`: `claude-river-map-moving`, `claude-river-map2-moving`, and `claude-river-map-off` (mode 0, same executable). Before: `claude-limb-single-river-final`.

**Image checks against the preceding build, same poses, 1280 × 720 without clouds:**
- 250 km, 97 km and 2,200 m: pixel-identical, but one pixel by one code at 97 km.
- 1,231 km: 99.9 % of pixels identical, at most 2 codes.
- 3,000 km: 98.9 % identical; 0.001 % beyond 8 codes, at most 19.
- 10,000 km: 99.5 % identical; 0.002 % beyond 8 codes, at most 45. Those are lake-shore pixels: the ground under a flat shore moves by a few metres.
- 40,000 km, against an older capture: 99.9 % identical, at most 53, at shores.
- No seam at the cube's faces, no ring where the map takes over. The limb footprint alone changes 4 pixels by one code.
- Captures: `claude-river-map-fields/`, `claude-river-map2-fields/`; rivers off for scale: `claude-river-map-ravines/`.

**The map carries the rivers.** Screen-relief elevation with rivers minus without (ravines only), land texels:

| View | Mean, courses | Mean, map | Rms, courses | Rms, map |
| --- | ---: | ---: | ---: | ---: |
| Hemisphere, 3,000 km | −1.59 m | −1.54 m | 7.6 m | 7.8 m |
| Globe, 10,000 km | −4.41 m | −4.39 m | 14.6 m | 23.1 m |

- At 10,000 km the incised area is kept; the map is sharper than the texels' own 64 km box, peaks at 545 m instead of 372 m. Invisible at that distance.
- At the 40,000 km limb, 20 texels of the older capture stood 2 to 188 km below the ground. None does with the map.

**Remaining erosion cost, ms per frame, same build, erosion minus none:**

| View | Mesh | Fine grid, limb | Screen rivers | Total gap |
| --- | ---: | ---: | ---: | ---: |
| Massif, 1,231 km | 0.86 | 0.01 | 4.12 | 5.6 |
| Hemisphere, 3,000 km | 0.02 | 0.10 | 0.91 | 1.2 |
| Globe, 10,000 km | 0.03 | 0.28 | 0.22 | 0.75 |
| Distant globe, 40,000 km | 0.03 | 0.14 | 0.02 | 0.27 |

**Next steps, not implemented:**
- **Mid orbit, 400 to 3,000 km:** the river query per screen texel, at footprints of 5 to 13 km, recomputed every frame. At 1,231 km: node evaluation 2.6 ms, listing 1.1 ms, union 0.4 ms. Only a lighter query keeps the refinement exact at every frame; screen samples kept on the planet would refine by steps (`principes.md`).
- **150–400 km:** one river query per texel there too, the parallax placed by the fine grid's elevation, which already carries the valleys.
- The quality bench was not run: its views, 12 to 3,000 m above the ground, never reach the map's 25 km footprint.

## Limb-only fine grid and one screen river query, 2026-11-05 night

**Cause: two consumers evaluated rivers for nothing.**
- Above 400 km the screen relief has full weight. The pixel reads the fine grid only where one of its 4 × 4 screen texels misses the sphere: the limb. The whole 768 × 768 grid still ran the river evaluator, 2.3 to 6.1 ms.
- Each land texel queried its rivers twice: at the sea-level hit, only to place the parallax, then at the raised point.

**Changes:**
- `FineTerrain.hlsl`, `FineNearLimb`: with full weight on every row (`erosionMode.y`), a fine sample is computed only within 8 pixels plus 4 fine cells of the sea-level limb, for a column from sea level to the highest summit. Other samples stay off screen, as `MaybeVisible` leaves them. Exact: the pixels that read them use the screen relief alone.
- `ScreenRelief.hlsl`, `D3DApp::Draw`: at full weight, the first evaluation places the ground without its rivers; the river query runs once, at the raised point, or at the kept sea-level point. Between 150 and 400 km the screen relief is crossfaded with the fine grid: both evaluations keep their rivers there, so both grids place a valley floor at the same spot.

**Moving camera, 1920 × 1080, clouds and vegetation, same protocol as below:**

| View | Before | After | No erosion, after | No erosion, before |
| --- | ---: | ---: | ---: | ---: |
| Massif, 1,231 km | 35.7 | **56.3** | 89.1 | 77.5 |
| Hemisphere, 3,000 km | 53.9 | **65.6** | 100.2 | 89.4 |
| Globe, 10,000 km | 48.4 | **66.7** | 147.5 | 129.0 |
| Distant globe, 40,000 km | 41.5 | **69.4** | 259.3 | 224.4 |

- Two runs of the same build differ by up to 5 % (69.1 and 65.6 FPS at 3,000 km). No GPU frame above 33.3 ms.
- No-erosion mode also gains: its fine grid is skipped in orbit as well.
- Runs: `claude-limb-single-river-final` (erosion) and `claude-limb-single-river-off` (mode 0) in `E:/Exolune-diagnostics/orbit-20261105/`.

**Image checks against the preceding build, same poses:**
- 250 km (crossfade band), 97 km and 2,200 m: pixel-identical.
- 3,000 and 10,000 km: at most 4 and 1 RGB codes.
- 1,231 km: 94 % of pixels identical, 0.06 % differ by more than 8 codes, at most 27. The valley walls move by a fraction of a texel: the parallax no longer includes the river incision. Indistinguishable side by side.
- Captures: `claude-limb-single-river2-fields/`, compared with `cap-reduce-section-fields/`.

**Remaining erosion cost, ms per frame:**

| View | Mesh | Fine grid, limb | Screen rivers | Total gap |
| --- | ---: | ---: | ---: | ---: |
| Massif, 1,231 km | 0.85 | 0.02 | 4.94 | 6.5 |
| Hemisphere, 3,000 km | 1.46 | 1.06 | 2.00 | 5.2 |
| Globe, 10,000 km | 2.53 | 2.84 | 2.53 | 8.2 |
| Distant globe, 40,000 km | 3.23 | 1.61 | 5.56 | 10.5 |

- Mean GPU time with erosion minus without, same build; screen rivers sum enumeration, nodes, reduction and fallback.

- **Up to 3,000 km,** the gap is the one river query per screen texel, recomputed every frame: the texels follow the view.
- **From 10,000 km,** it is the large footprints: mesh vertices, limb samples and distant texels each enumerate hundreds of courses, whose filtered effect is invisible there. Erosion on/off captures at 10,000 and 40,000 km differ only by the terminal lakes, which come from the lake slices, not from the courses.

- The large footprints were then given the rivers' map, above.

## Earlier work, 2026-11-05 evening

**Status then: further reduction validated; erosion performance target remains unmet.**

- Worktree: `Exolune-erosion`, existing dirty `claude/erosion-montagnes` at `67637ef` plus local work.
- Comparison: clean `Exolune-main` at `b7bd60e`.
- Preserve all preceding river and valley morphology work. No erosion mode, physical parameter, filter bandwidth or sampling resolution is reduced.
- This was functional isolation, not a Git bisect: the failing river evaluator belongs to uncommitted work and is absent from committed HEAD.
- Earlier measurements and rejected schedules are in `log/spec-erosion-historique.md`.

**Causes and correction**

- Most physical nodes have no eligible course. Build exact activity masks from the conditioned network and index the original cube chart, including repeated remapped candidates at face edges.
- Conservative node bounds reject work that every existing projected curve/connector gate would reject. Shared mesh, fine-grid and screen evaluation use them.
- Compact section integration skips exactly zero contributions. The physical section and its filtering remain unchanged.
- Screen queries reserve bounded, contiguous node ranges. Independent nodes run in parallel; reduction retains the physical max/min unions and normalizes wet moments afterward.
- Large sparse searches assign different tiles to cooperating lanes, preserving original tile/bit order. Small searches retain their existing scheduling.
- A conservative sphere encloses every remapped, jittered node of each chart tile. Reject a tile only when the original node-distance gate rejects that entire sphere. This removes the oversized searches at the distant limb without narrowing physical support.
- A spherical cap from the existing node-distance gate clips candidate rectangles, including face-edge remapping and jitter margins. It preserves the original candidate multiset.
- Four adjacent lanes reduce screen results, retaining max/min unions and normalizing wet moments after reduction.
- Four sorted wall/bank boundary lists are merged directly. Every positive interval and its four-point quadrature remain unchanged, including inverted capped walls.
- Capacity overflow keeps the complete evaluator. Only actual fallback queries enter its indirect dispatch; empty fallback work does not scan the screen.
- Reservation limits follow the screen texel count to prevent 32-bit overflow. The former fixed 1,024-node limit unnecessarily serialized a few expensive limb queries.
- DRED localized the hemisphere timeout to terrain drawing, not the queue dispatch. A missing screen stencil at the limb restarted the full pixel contour evaluator. It now uses the existing filtered mesh/fine water fallback while screen relief is active.
- Exact stationary reuse remains; it never substitutes for a changed moving query. Both parallax evaluations are preserved.

**Moving-camera protocol**

- RTX 4070 Ti; 1920 × 1080; VSync off; clouds and vegetation enabled.
- Native hidden batch rendering, one engine on the GPU at a time.
- Same seed, camera path, sun and sampling counts in each comparison.
- Motion per frame: 0.08 degrees heading, 0.003 degrees north and 1/60 second weather; no descent or final pause.
- Each view settles for 12 frames, warms for 30 and measures 180 moving frames.
- FPS is 1000 divided by mean presentation cadence. GPU percentiles use native timestamps.
- `tools/banc_orbite.py` saves configuration, executable/shader hashes, images, pass timings and per-frame traces.
- Repeated original/main runs on November 5 are faster than November 4. Use the same-day baseline for improvement claims.

**Current moving-camera comparison, November 5 evening**

- Previous full erosion is the measured version the user found too costly, not the original failing shader.
- Current full/no-erosion modes use identical executable and all shader hashes. Mode 0 is diagnostic, deliberately different terrain; production stays at mode 2.
- Same motion, seed, sun, clouds, vegetation, resolution and 180 samples per view. Small changes of a few percent are not evidence of a substantial gain.

| View | Previous full FPS | Current full FPS | Current no erosion FPS | Current full GPU p95 |
| --- | ---: | ---: | ---: | ---: |
| Massif, 1,231 km | 35.6 | 35.7 | 77.5 | 29.68 ms |
| Hemisphere, 3,000 km | 53.7 | 53.9 | 89.4 | 19.98 ms |
| Globe, 10,000 km | 46.2 | 48.4 | 129.0 | 21.92 ms |
| Distant globe, 40,000 km | 31.6 | 41.5 | 224.4 | 26.80 ms |

- At 40,000 km: 31.07 to 23.51 ms mean GPU time, 31.2% more FPS. No erosion remains 4.07 ms.
- All 720 current samples complete without GPU failure. GPU frames above 33.3/50 ms: 0/0; maximum 31.66 ms.
- The large erosion overhead is still unresolved. This is an incremental reduction, not near-baseline performance.
- Ravines-only isolation gives near no-erosion performance. Remaining cost is concentrated in step-B courses.

**Remaining GPU work, current full erosion**

| View | Mesh | Fine grid | Horizon | Screen enumeration | Screen nodes | Screen reduction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Massif, 1,231 km | 0.96 ms | 4.37 ms | 0.00 ms | 2.36 ms | 5.87 ms | 1.95 ms |
| Hemisphere, 3,000 km | 1.53 ms | 2.71 ms | 0.00 ms | 1.66 ms | 1.41 ms | 0.92 ms |
| Globe, 10,000 km | 2.73 ms | 5.75 ms | 0.01 ms | 2.27 ms | 2.20 ms | 0.92 ms |
| Distant globe, 40,000 km | 3.33 ms | 6.75 ms | 0.02 ms | 6.41 ms | 2.36 ms | 1.11 ms |

- These are measured passes, not inferred costs. Fine normals cost roughly 0.16 ms; other screen preparation/finish and fallback remain in total GPU time.
- Further work needs less repeated course evaluation across terrain consumers and cheaper large-footprint enumeration. Removing valleys, shrinking their filter or silently dropping limb fallback is not an accepted shortcut.

**Correctness evidence and limits**

- Release x64 builds through `tools/lance.ps1 -Build -NoLaunch`.
- The physical erosion cache payload is unchanged: SHA-256 `c13c3cc07c544a81f70e30b94a4c9f2bbbffc1642d4d4ed549c6031c524fb108`, excluding its 24-byte header.
- `verifie_index_rivieres.py` checks 1,572,864 exact eligibility predicates, all 77,070,336 halo bits and 1,800 candidate searches including 700 face-seam cases. Repeated chart candidates are retained.
- `verifie_bornes_rivieres.py` retains 1,069,632 original projected gates on 1,200 planetary nodes at four footprints, including independently checked native bounds.
- `verifie_bornes_tuiles.py` encloses all 77,070,336 remapped chart nodes at resolution 512, plus complete resolution-8 and resolution-64 halos. The tightest node uses 87.7% of its conservative bound; the triangle inequality preserves the original node gate for any query and footprint.
- Before/after tile-pruning captures at 40,000 km and 1920 × 1080 are pixel-identical; all 16 native fields match exactly on 13,256 terrain rays.
- Five more images from 2,200 m to 10,000 km are pixel-identical after tile pruning. Their three screen-enabled views retain all fields exactly. A final 1282 × 722 run with a 64-node capacity passes the original scheduling tolerances.
- The latest compact fallback change preserves five native images exactly. Native fields pass at 1282 × 722 with capacities zero and 64; maximum wet-stage moment difference is 1.43e-6, with identical positions, terrain, coverage, depth and candidate distance.
- The new cap proof checks 111,963,012 original chart candidates: 53,294,646 discarded candidates already fail the old node gate; no contributing node is lost.
- The new partition proof retains every positive interval on 100,000 sections, including 8,872 inverted capped walls.
- This evening's six before/after images from 2,200 m to 40,000 km are pixel-identical. The hemisphere also matches the intermediate cap/reducer image. Native fields pass existing tolerances: maximum height/distance difference 3.05e-5 m, wet-stage moment 1.91e-6.
- New 1282x722 captures with forced capacities 64 and zero pass unchanged field tolerances and retain identical images. The physical cache payload still matches the SHA-256 above.
- The complete indexed optimization is not bit-identical to the pre-index shader. Its original strict field test fails on small numerical differences: up to 0.328 m height and 1.525 m candidate distance on the orbital massif. Do not loosen that test or label it passed.
- Corresponding native image differences are small: maximum one RGB code on the massif, two on the globe, two at 250 km and fourteen at 97 km; the tested 2,200 m confluence is pixel-identical. Geometry/filter parameters and the physical network are unchanged, but this is not proof of exact numerical equivalence everywhere.
- Material survey: 30 fixed locations, five altitudes and nine views each. Compare against both `tools/banc_qualite_reference.json` and the preceding corrected build at those exact locations.
- Current paired survey: no new +10% p95 regression across 55 metrics against the preceding corrected build; largest ratio 1.000000085.
- Both before and after fail the historical limit on 18 / 18 of 53 comparable metrics. This pre-existing gap remains; the historical gate is not passed.
- Results: `cap-reduce-section-quality-comparison.json`; raw current survey: `quality-cap-reduce-section`.

**Memory and remaining work**

- GPU-only activity/bound layers add 24 MiB to the physical 48 MiB erosion texture.
- Queued tasks/results are capped at 256 MiB. Ranges and fallback IDs add 12 bytes per screen texel.
- Existing screen work is 172 bytes per texel; final screen fields remain 64 bytes per texel. Scratch grows with the current view.
- River evaluation still costs more than main. Morphology work remains: distant head regularity, sediment-shaped confluences, long estuaries, distributary contacts and lake-stage boundaries.

**Artifacts and review**

- Artifacts: `E:/Exolune-diagnostics/orbit-20261105/`.
- Baselines: `main-moving-repeat`, `before-moving-repeat`, `quality-before`.
- Final paired sequences: `cap-reduce-section-repeat` and `cap-reduce-section-off`. The integrated first repeat is `cap-reduce-section-moving`; prior checkpoints are archived experiments.
- Final build: `x64/erosion-orbit-cap-reduce-section-build.log`. Shared source: `MyPlanetEngine/Erosion.hlsli`; queue/reduction: `ScreenRiverQueue.hlsl`, `ScreenRiverReduce.hlsl`. Per-frame CSV adds four terrain phases.
- Current native correctness: `cap-reduce-section-fields`, `cap-reduce-section-far`, `cap-reduce-section-odd`, `cap-reduce-section-zero`; comparison log: `cap-reduce-section-native-comparison.txt`.
- Review route: `tools/tests/2026-11-05-orbite-correction.txt`, F1–F8 from 2,200 m to 40,000 km.
- Interactive erosion Release was relaunched alone after all measurements and verified responsive, PID 31252. Its title confirms complete erosion, clouds, 1920 × 1080 fullscreen and VSync. Process evidence: `x64/erosion-orbit-interactive-second-correction-20261105.json`. Backspace leaves the cockpit; F1-F8 select the witnesses. Stationary caption FPS is not flight performance.
- No commit, tag or push. A milestone tag remains deferred until a reviewable commit is requested.

```powershell
python tools/banc_orbite.py --exe x64/Release/MyPlanetEngine.exe --out E:/Exolune-diagnostics/orbit-new-erosion --motion "0.08 0.003 0.016666667 1 0 0"
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Parcours tools/tests/2026-11-05-orbite-correction.txt
```
