# Specification: the rendering from far, from 5 km to orbit

Status: validated on 2026-10-21. Facts: step 1, step 2 on the face, downward mutation, universal limit rule. milestone `jalon/13-coherence-distance`, the 2026-10-22.

**In short, what keeps the planet consistent from orbit to ground:**
- **the fine grid:** the real relief under the grid cell, in normal and altitude;
- **a relief that keeps its average height,** at any distance;
- **the universal rule:** each boundary between materials shows its average on the pixel;
- **the descent benchmark and diagnostic views,** to measure it.

## The finding

Three defects, seen in flight at 56 km, 300 km, 450 km and 1 160 km.

1. **Rock confetti.** From 50 to 450 km, white, pink and orange rock spots sown on the green, without any connection with the relief.
2. **The blur.** At 1 000 km, the planet is no longer but large blurred spots: no relief can be read between the large shapes.
3. **Intermediate level.** As you descend, the complexplanet shapes appear suddenly, and their rendering seems strange.

## Causes

**The confetti.** The rock is decided by the slope of the grid cell, plus a local noise of 8 km to 1 m.

- From afar, a grid cell is several kilometers long: its slope is almost always gentle.
- The rock appears therefore only where the local noise force it, in spots of 1 to 5 km without relation to the mountains.
- The new rock colors, red and light limestone, make them very visible.

**The blur.** The mesh always has 192 grid cells on the width of the face, so a grid cell covers about 13 pixels at any height.

- **Near the ground,** the textures of materials fill the interior of the grid cells.
- **Above a few kilometers,** textures have merge into their average. The grain of the lighting stops at the grid cell and does not exceed 6 km. Between the pixel and the grid cell, there is nothing: at 300 km, nothing between 0,4 and 6 km.

**Intermediate level.** It is the same lack seen down: the octaves of complexplanet appear only once carried by the mesh, without announcement in the pixels.

## The experiments

### 1. Rock in fractions, not in spots

- **From far away, a grid cell contains slopes steeper than its average slope:** those of the octaves that the mesh does not carry.
- **Rock becomes the expected fraction of steep slopes** in the grid cell, based on the variance of those slopes. This is the spirit of Toksvig and LEAN for normals.
- **The local noise fades with pixel size.** The mountains become continuous rocky regions, with snow and scree, and the plains remain green.
- **Cost:** few operations per pixel. **Risk:** low.

### 2. The relief under the grid cell, in pixels

You have to fill the gap between the pixel and the grid cell. Two very different ways.

- **A. A grain finer than the grid cell,** the current `DetailSlope` extended to the pixel, its amplitude adjusted on the roughness of the field, stronger in mountain than in plain.
  - **For:** low cost, about 0,1 ms.
  - **Cons:** it is an invented relief. As you approach, the mesh brings the real complexplanet relief to the grain: the mute shape.
- **B. The normals of the real relief, thinner than the grid cell,** calculated each frame by a pass of calculation on a grid 4 to 8 times thinner than the mesh, without geometry.
  - **For:** the real relief, without mutation at the approach: this is what is missing at the intermediate level.
  - **Cons:** 16 to 64 times more complexplanet ratings than the mesh, i.e. 1,5 to 6 ms to add to the 0,1 to 2 ms of today. Except to evaluate only the thin octaves, which assumes to cut complexplanet.

### 3. The colors seen from orbit

- **Biome contrast:** darker forests, lighter deserts, brown mountains and snow, as in images of Earth seen from orbit.
- **The pink mist** of the atmosphere towards the horizon, to be checked against orbit photos.

## The measure

- **An orbit benchmark:** views at 5 km, 56 km, 300 km and 1 000 km over three regions, alongside photos of Earth orbit view.
- **The benchmark downward mutation,** for the experiment 2.

## The proposed steps

1. **Rock in fraction:** experiment 1, with orbit benchmark.
2. **The relief under the grid cell:** experiment 2, A or B, to be chosen.
3. **The colors seen from orbit:** experiment 3.

## Results of the stage 1

- **The dispersion of slopes in the grid cell,** `SlopeSpread`, calculated by vertex: the curvature of the mesh from one grid cell to another gives the slope of the thinnest octave carried, and log2(grid cell / 13,5 m) octaves remain below, each of comparable slope.
- **Rock, scree and snow boundaries expand** by 1,5 times this scatter. The snow temperature limit also widens, according to the spread of altitudes in the grid cell.
- **Local rock and temperature noise functions fades** for pixels from 32 to 512 m.
- **At orbit benchmark:**
  - rock confetti disappeared from the grassy plateau, at 56 and 300 km;
  - at 300 km, snow forms a single mass instead of a patchy seeding;
  - at 56 km, snow remains in plates, but softened;
  - the desert remains blurred: this is the stage 2.

## Corrections made on the way

- **Snow and rock stripes from 450 m to 1,3 km:** the tile of 64 m bears ±1 m of relief; the mixture by the height intercalated snow and rock benchmark by benchmark, thinner than the pixel. This blending now fades for pixels from 25 cm to 2 m.
- **The two patches of the relief pass of materials,** removed the 2026-10-30: `log/spec-rendu-lointain-historique.md`.

## The 2 step in B: the fine grid

Status: chosen the 2026-10-21; first version made, the face only.

- **A grid 4 times thinner than the face of the mesh,** 768 × 768 grid cells, recalculated at each frame by complexplanet, filtered to its own grid cell as the mesh is to its own.
- **Two pass calculation:** the heights of the fine grid, then its normals.
- **Its culling margin, since 2026-11-07:** 6 fine cells, what a visible pixel's B-spline and normals read, 3 cells, and as many again. It was the mesh's 6 cells, which also cover the shadows' vertices. Images identical; 97 km's fine grid 0.28 ms faster.
- **The pixel reconstructs the fine height with a positive 4 by 4 cubic B-spline and derives its normal from that surface,** instead of independently interpolating linear heights and normals. It fades on the last eight face cells; see `spec-normales-spline.md` for the 2026-11-01 correction and its limits.
- **The grain of the lighting and the dispersion of slopes** are adjusted on the grid cell fine: the invented grain starts only below it.
- **Up to 160 m from the ground for material decisions:** active from grid cells face of 3,4 m, `FineMinCell`, fully to 6,8 m, or 320 m high. Lower, the mesh carries the thinnest octave of the relief, 13,5 m, on its 4 grid cells. It stopped first at 20 m from grid cell, towards 1 km: see the correction of the 2026-10-24 below.
- **Up to 1 km for light:** it illuminates the ground only from grid cells of 20 m, `FINE_LIGHT_MIN_CELL` front. Lower, normal spline and grain, more stable, and textures fill the grid cells.
- **The face alone, first:** orbit, it covers the essential of the view. Rings will follow if the measure justifies it.
- **Out of field points** are not calculated, as for the mesh.

**The known risk:** the experiment `piste/relief-par-pixel`, abandoned, evaluated the relief at each pixel. Its cost, 8 to 33 ms, is not that of B. But its visual defect also applies to B: from afar, ridges without volume, since the normal alone does not make geometry.

**Measurement:** the orbit benchmark before and after; the cost of calculation at 1, 5, 56 and 300 km; a descent, for the mutation.

### Results of the first version

- **From orbit, the relief reads:** at 300 km, the snowy massif shows its ridges and valleys instead of a white spot; at 5 km, the desert is clearer.
- **Cost of calculation:** 0,2 → 1,8 ms to 56 km, 0,1 → 0,7 ms to 300 km. At 5 km, it remains in the noise measurement.
- **Remains to be done:** the rings, which keep the relief of the mesh alone; the downward measurement, for the mutation.

## Corrections made on the way, continue

- **Blades of several meters on the ridges, in flight:** the random paving mixed three copies of the tile while keeping their contrast. It amplifies the gaps up to 1,7 times, or ±3,5 m on the tile of 64 m, and crossed cornices formed blades. The heights and slopes now simply blend together; only the colors retain their contrast. Not reproduced on our points: to be checked in flight.
- **Snow Walks:** only 10 % of the snow relief remains instead of 30 %, and the walls of the 64 m tile corridors are softened.
- **To reproduce a view:** the title bar gives the camera position, and the executable accepts a fifth argument, the heading.
- **benchmark of the ridges:** `tools/banc_cretes.py`, the ridges at man's height, several builds side by side.
- **Landing far from the planet, from 5 000 to 6 500 km, once in two:** at the edge of the face, the interpolated coordinate of the pixel passed a hair under 0. The index of the fine normal then became enormous, and reading, without control of bounds on a root descriptor, dropped the GPU. The index is now bounded on both sides: six of six launches successful, compared to three before. A loss of the GPU now displays its reason instead of closing the app without a word.

## Downward mutation: measures

**The benchmark:** `tools/banc_descente.py`. It films the same area vertically, from 1 500 km to 60 km, and measures what it contains on 60 km of side. The engine then runs in its diagnostic view, `MYPLANETENGINE_VIEW` = `snow`, `rock` or `elevation`. Each pixel is white with the probability of material weight, or altitude on 6 km, without light or smoothing. The white share gives the exact average.

**Snow, mountain range in northern Africa, 32,3° N, 17,9° E:**

| Height | 1 500 km | 800 km | 400 km | 200 km | 130 km | 90 km | 60 km |
|---|---|---|---|---|---|---|---|
| Snow | 6,6 % | 6,0 % | 8,9 % | 45,3 % | 29,2 % | 26,8 % | 26,3 % |

- **Without temperature expansion:** only the distance changes, 6,6 → 0 %.
- **Without the slope widening, or without the fine grid:** nothing changes.
- **Without erasing the noise local temperature:** the far rises to 23–32 %, but the peak at 200 km remains.

**The peak at 200 km comes from the relief itself.** The average altitude of the area changes with the height of view:

| Height | 1 500 km | 800 km | 400 km | 200 km | 130 km | 90 km | 60 km |
|---|---|---|---|---|---|---|---|
| North Africa | 1 690 m | 1 820 m | 1 840 m | 2 140 m | 1 990 m | 1 900 m | 1 810 m |
| Rock site, 15° S, 120° E | 4 450 m | 4 480 m | 4 630 m | 5 090 m | 4 870 m | 4 660 m | 4 270 m |

- **Mountains inflate and deflate** from 300 to 800 m depending on distance, with a maximum for grid cells of about 4 km.
- **Cause:** Octave filtering replaces each octave that is discarded with its average, but complexplanet combines its octaves non-linearly. The average of an octave does not keep the average of the relief.
- **The consequences:** a change in shape, mountains changing size, and a change in snow, since snow follows altitude.

## Downward shift: corrections

**1. The relief keeps its average height.** The cause of the swelling was the rounding of the ridges, `CreaseAbs`:
- near the cutoff, it rounded up to twice the amplitude of noise, and the absolute value rounded up there was almost 1 instead of its average of 0,32;
- its average excess is now removed, calculated exactly for a noise of normal law standard deviation 0,4. This standard deviation is derived from the mean values already measured, those of Billow and RidgedMulti. A random draw confirms the calculation to 0,1 % close;
- the crests remain rounded, therefore always stable.

| Average altitude | 400 km | 200 km | 130 km | 90 km | 60 km | 30 km | 15 km |
|---|---|---|---|---|---|---|---|
| Rock site, before | 4 700 m | 5 160 m | 4 810 m | 4 550 m | 4 120 m | 4 090 m | 4 150 m |
| Rock site, after | 4 610 m | 4 540 m | 4 460 m | 4 360 m | 4 280 m | 4 250 m | 4 220 m |
| North Africa, after | 2 000 m | 2 000 m | 1 900 m | 1 890 m | 1 900 m | 1 890 m | 1 880 m |

- **There remains a regular deviation** of 400 m on the rock site, from 400 to 15 km, without bump. It is probably the cascade from RidgedMulti, whose octave weights depend on the previous octaves.

**2. Snow follows the actual terrain.**
- **Its altitude is that of the fine grid,** four times more accurate than the mesh: snow falls on the real peaks under the grid cell.
- **The temperature noise** now only bears wavelengths of 2 km and less, for about 0,6 °C. It is the same at any distance.
- **What the pixel cannot show of this noise** expands the snow line around −2 °C, instead of erasing it: the average part does not move anymore.
- **The old erasure of the noise local of 8 km** for pixels from 32 to 512 m is removed from the temperature. It was he who made snow spots without any connection with the relief.

| Snow, North Africa | 800 km | 400 km | 200 km | 130 km | 90 km | 60 km |
|---|---|---|---|---|---|---|
| Before | 6,0 % | 8,9 % | 45,3 % | 29,2 % | 26,8 % | 26,3 % |
| After | 11,0 % | 8,2 % | 9,9 % | 10,9 % | 11,8 % | 12,2 % |

- **From 400 to 60 km,** the same snow sheets on the same peaks.
- **At 800 km,** the fine grid no longer distinguishes the summits, and the snow becomes a strip in the same place.
- **noise alone,** at 1,5 °C over 1 km, was seeding points from 90 to 60 km: test dismissed.

## The universal rule: a limit shows its average on the pixel

Status: in place the 2026-10-22, for all materials.

**The rule.** Any boundary between materials is a smooth transition on a field: temperature, altitude, slope. A pixel shows the average of this transition over everything it covers, at any distance.
- **The noise that makes an irregular boundary is the same at any distance.** It is never erased according to the pixel size.
- **What the pixel cannot show of a field widens the boundary:** its lost variance is added to the transition. The center does not move, so the middle part does not move either.
- **Every entry of a limit brings its lost variance.** For temperature: the noise of the snow line, the hidden altitudes in the grid cell, and the orientation of the hidden slopes.

**Tools, in `Materials.hlsli`:**
- `SpreadStep(lo, hi, x, sigma)` for a one-dimensional field: the expanded transition at equal variance. Variance less than 3 % with random draw.
- `SlopeShares(slope, sigma, limits)` for slope, two-dimensional field: a polar laminated quadrature, six radii and five angles. Variance of less than 2 % with a random draw, compared to 15 % for a Gauss-Hermite 3 × 3.
- `FbmLostShare`: the portion of variance of a noise that the pixel does not show.
- `SlopeSpread` and `ElevationSpread`: the slopes and altitudes that the grid cell hides, according to the roughness of the terrain type.

**The roughness, only data specific to the field.** The complexplanet mountain octaves, in RidgedMulti, each carry about the same slope. The hidden slopes are therefore worth this slope per octave, multiplied by the root of the number of octaves lost.
- **It comes from the terrain type,** calculated with relief and transmitted by vertex (`FaceVertex.roughness`): 1 for mountains, 0,6 for badlands, 0,4 for hills, 0,1 for plains.
- **The slope per octave,** `OCTAVE_SLOPE` = 0,16, is calibrated on the rock at the benchmark of descent.
- **Why not a measurement on the mesh:** a grid cell of several kilometers sees only the curvature of the continents. The measured dispersion fell from 0,014 to 400 km.

**Balance material by material,** at the benchmark of descent:

| Material | Decided on | Treatment | Measured share, from far to close |
|---|---|---|---|
| Terrain | complex planet | universal: the rounding of the peaks keeps the average | average altitude without bump; remains a gap of 400 m on a chain |
| Snow | temperature, slope | universal rule; calibrated slope orientation, see below | 12 → 16 % and 6 → 14 %, compared to 6 → 45 → 26 % previously |
| Rock | Slope | universal rule, `SlopeShares`  | 18 → 22 %, compared to 0 → 17 % before |
| scree | Slope | universal rule, `SlopeShares`  | 33 → 45 %, stable |
| Grass, sand | humidity, temperature | stable by construction: regional humidity of more than 200 km, never filtered; temperature limits in `SpreadStep`  | 100 % at tested sites; grass 6,0 → 8,1 % at the cold dry boundary of the North African Range |
| Green wetlands, forest | humidity | stable by construction | 100 % on the tested site |
| Beach | altitude, noise local, temperature | universal rule, `SpreadStep`  | 5,1 → 6,0 %, against 4,0 → 6,1 % |
| More | altitude | universal rule: sea share in pixel, instead of a yes or no | 83 → 87 %, stable |
| Tundra, color | temperature |  `SpreadStep`  | not measured, same rule |
| Clarity, hue | noise functions local and regional | linear: their averages are accurate by construction | not applicable |
| Textures | tiles generated | mipmaps keep the average | not applicable |

**The specific, and why.**
- **Roughness by terrain type and `OCTAVE_SLOPE`** are complexplanet-specific data, not a rule. They are calibrated on the rock of the rock site.
- **The orientation of hidden slopes counts for 4 °C per unit of slope,** instead of the 8 °C of the temperature orientation term:
  - at 8 °C, snow was twice as abundant from far on the North African chain, 28 % against 14 %;
  - at 0 °C, it was twice too rare by far on both channels;
  - at 4 °C, it holds on both to a few points.
  - Probable reason: the roughness by terrain type overestimates the slopes of some mountains, softer than average.
- **The limit of any statistical method:** on a small area of 3 km, the rock share still rises as you approach, from 20 to 33 % or from 18 to 45 %. From a distance, we show the average part of the region, not a steeper part than the average.

**What remains to be measured or done:**
- a border between grass and hot desert, where sand counts;
- the 400 m deviation from the relief, probably the cascade of RidgedMulti;
- a roughness measured rather than drawn from the only type of terrain, for example by the fine grid, to no longer calibrate to the main.

**Cost:** +0,10 to +0,28 ms of rendering, at a minimum of three passes.

## Fix of the 2026-10-22: the flicker close up

**Symptom,** seen in flight after the milestone 13: large sparkles and aberrant shapes near the ground, balls and rock arches. Positions `6561.8 -18.67002 131.64981 9.8 -117.1` and `563.6 5.98065 127.83668 11.2 -58.7`.

**The benchmark:** `tools/banc_tremblement.py <dossier> <exe> "<position>" [exe ...]`. It captures an exact position of the title bar and measures the average difference between successive frames, with and without time smoothing, when the mesh slides under a fixed camera.

**The cause, found by going back the builds of the day:** the fix of the rounding of the peaks, `CreaseExcess`.
- **For a small rounded,** its exact form subtracts almost equal terms then divides by the rounded.
- **In simple precision,** the error grew as the rounding narrowed, that is, near the camera, and differed from one summit to another: the ground vibrated and creased.
- **The correction:** under a rounded of 0,4, we take its series, `p0 e²/3 − p0 e⁴/(60 σ²)`, exact to 0,0002 close. The exact form serves only above.

| jitter, with / without smoothing | View of snowy ridge | View of dune |
|---|---|---|
| Before the peak correction, `5f53ef9`  | 0,43 / 1,68 | 0,21 / 1,46 |
| milestone 13 | 1,26 / 3,07 | 2,37 / 5,11 |
| With the series | 0,37 / 1,37 | 0,16 / 1,01 |

- **Better than before the milestone 13,** on both views.
- **The average descent altitude remains flat,** 71 to 72 % of 200 to 15 km on the rock site, and the rock share does not change.
- **Test dismissed:** move the relief of materials vertically instead of normal. It gained little, and the crests were covered with saw teeth.

## Fix of 2026-10-24: the circles on the oceans, seen from far

**Symptom,** seen in flight at 24 600 km, `24622915.3 46.51198 60.64808 79.2 78.2`: oceans covered with concentric rings around many centers, like a moiré. Net from 10 000 to 30 000 km; pale from 2 000 km, on land also. Image: `images/cercles-avant-apres.jpg`.

**Diagnosis, by elimination, on the reported view:**
- the colour of the sea is fixed, instead of its depth: the circles remain;
- normal vertical everywhere: they remain;
- black ground, atmosphere alone: they remain. It's the atmosphere.

**The cause: the distance spent in the atmosphere in semi-floating.**
- **The terrain writes its distance,** in km, in the alpha of the image HDR; the atmosphere stops its integration along the radius.
- **A half-float has only 11 bits:** steps from 0,5 km to 1 000 km, 8 km to 10 000 km, 16 km beyond 16 384 km.
- **The radius stopped up to 8 km before the ground,** or at the ground when the rounded fell below. The densest layer of air, 8 km height scale, counted or not depending on the pixel.
- **These steps follow the distance:** of the circles around the nadir. Closer than the pixel, they fold into rings around a network of centers, like a Fresnel sight.

**The fix:** the HDR image goes into floating 32 bits (`HdrFormat`, `D3DApp.h`). The distance there keeps 2 m to 30 000 km, where passes any distance to the atmosphere and time smoothing.

**The rule** (`principes.md`): a quantity passed from one pass to another keeps the precision of the scale it serves, not that of its size.

**The measures:**
- **No more circles,** from 2 000 to 30 000 km, over two regions, even in contrast × 8.
- **The ocean clears up a little from far away:** every pixel finally counts the whole air column.
- **Descent, shares unchanged at the tenth:** snow 20,5 → 14,6 % in North Africa, sea 98,8 → 97,7 % from 25 000 to 1 200 km.
- **quality benchmark, 30 locations:** all p95 to 0,1 dB near reference, identical mutation, right segments per view to 0,3 near.
- **Near ground, identical image** to close 1/255; cost in the noise measurement, less than 0,1 ms.

## Fix of the 2026-10-24: the mutation approaching

**Symptom,** in flight towards a snowy mountain: a green spot in the snow, clear at 1,6 km from the ground, eaten by the white at 1,3 km, returned at 530 m; brown spots at the last moment, at 143 m. Views: `tools/tests/2026-10-24-approche.txt`.

**Causes, measured at the benchmark of descent on a square of 100 m below the spot, from 2 km to 100 m:**
- **The decision normal lost the forms of 13,5 to 100 m.** The fine grid was extinguished between grid cells of front of 40 and 20 m, from 1,9 km to 960 m high. The mesh alone carries an octave only beyond 4 grid cells: 84 m to 1 km, 13,5 m only under 160 m. The temperature follows the orientation of the slopes: the spot, slope turned to the equator, closed and then reopened.
- **The texture slope changed the snow near the ground.** Added to the normal snow for pixels less than 2 m, without its lost part counting by far: on the 600 last meters, snow lost up to 7 points on gentle slopes, the rock appearing below, and gained 8 on the steep rock.
- **Distanced at measurement:** Without `HeightBlend`, the shares do not move; without the grain `DetailSlope` in the decisions, or with the hidden slopes counted at 8 °C, they move more.

**The fix:** the fine grid remains active for decisions up to the grid cells of 3,4 m, the light keeps its threshold of 20 m; snow only takes into account the slope of the terrain. Measurements are in `journal-planete.md`.

**Rest:** the octave of 13,5 m and a part of that of 27 m are still missing from the fine grid above 500 m, and `SlopeSpread` does not count them; the rock still rises from 3 to 9 % on the spot between 2 and 1,2 km, from 4 to 17 % on hills. Counting these octaves with the roughness by type of terrain regulates the mountains but overflows elsewhere: you need the roughness measured, higher.

## The screen relief, 2026-11-02

Status: implemented; validated in flight by the user on the reported massif. Flight route: `tools/tests/2026-11-02-montagnes-exposition.txt`.

**Symptom,** from orbit over a mountain range, `1673620.9 -7.138614 122.604860 84.18 32.74`:
- the ground blurred into squares, then sharpened suddenly near 1,400 km;
- moving sideways, the relief, the rock and snow limits and the forest crawled.

**Cause: the fine grid's cells span several pixels from orbit.**
- Lit and decided on the fine grid alone, the ground blurred into its cells.
- Its cells slide with the camera: what lies between its samples changed as they slid.
- The per-pixel detail took over later, its widest octave 6 km: the ground sharpened at once.
- Fields interpolated on the mesh's sliding triangles crawled the same way: roughness, fresh volcanic ground, geology.

**The change: screen relief, refreshed when its inputs change.**
- Since 2026-11-05, ground preparation, sparse river enumeration, node evaluation, reduction, complete overflow fallback and finish schedule the same physical queries in separate passes. The conditioned network supplies exact activity masks and conservative projected bounds (`spec-erosion.md`).
- The original distance gate also bounds enumeration by a spherical cap, including cube-face seams. Four adjacent lanes share each result reduction; the existing native tolerances bound wet-sum rounding differences. Filter width and resolution remain unchanged.
- Identical camera/frame/FOV, double nadir, sampling layout and erosion mode retain the exact previous result. There is no history reprojection or approximate motion reuse.
- Both ray evaluations remain; a nonpositive first height reuses the identical sea-level query. At full weight, above 400 km, the first only places the ground, without its rivers; the river query runs once, at the second point or at the kept sea-level one. Crossfaded with the fine grid, both keep their rivers, so that both grids place a valley floor at the same spot. Correctness, moving-camera performance and remaining cost: `diagnostic-orbite.md`.
- Footprints wider than a level-0 cell, about 25 km, read the rivers on a startup map instead of their courses: mesh vertices, distant texels and the limb (`spec-erosion.md`).
- **One texel per 2 × 2 pixels** (`ScreenReliefScale`), at most 1920 × 1080 texels.
- **Each texel finds its ground:** the view ray meets the sphere at sea level, then again at the elevation found there, for the parallax of summits seen aslant.
- **The relief is filtered to 4 texels** (four-texel bandwidth), as the mesh is filtered to 2 cells (`MESH_BAND_LIMIT`).
- **Each texel stores 64 bytes** (`ScreenSample`): camera-relative position and elevation, premultiplied inland water and flow, roughness and fresh volcanic ground.
- **Step-B water, since 2026-11-03:** wet fraction, fraction times stage and mean depth come from the physical channel section. The wider support of an averaged cut is not full water presence. The mesh, fine grid, screen grid and pixel contour query share this representation (`spec-erosion.md`).
- **Its weight rises with camera altitude,** smoothstep from 150 to 200 km since 2026-11-07, formerly 400 km (`ScreenReliefLow`, `ScreenReliefHigh`). Below, the fine grid and the per-pixel detail carry the relief to the pixel. Crossfaded, the screen relief, the fine grid and the pixel contour all ran their rivers.
- **Direct path:** when every texel's river footprint reads the rivers' map, or no river is drawn, both rays and their finish run in the ground pass, without the river passes or their scratch (`ScreenRelief.hlsl`, screen pass bit 1). At full weight otherwise, the first ray, which queries no river, is finished in its own pass (bit 2).
- **Rivers, one query per texel in a kernel of their own** (`ScreenRiverTexel.hlsl`, since 2026-11-07): a wave's texels list their nodes together (`spec-erosion.md`, shared listings). Inlined in the ground pass, the corridors cost thirty times more; the former queue of node tasks, their results and their reduction cost three times more at 250 km.
- **A wide search goes to a wave of its own** (`ScreenRivers.hlsl`): a window of more than 8 × 8 nodes, at the limb. Its wave's other texels keep their shared listing.
- **Each texel's finish follows its query in the same kernel** (`ScreenFinishTexel`, `ScreenReliefWork.hlsli`): no finish pass, no dispatch of its own.
- **The fine grid and the mesh by 8 × 8 tiles of samples** (`FineTerrain.hlsl`, `TerrainCompute.hlsl`): a wave's samples are neighbours on both axes. A row of 32 fine samples spanned 16 km at 97 km and shared no course.
- **Every changed query is refreshed:** the texels follow the view; only identical inputs retain their exact previous result.

**The pixel reads it in B-spline,** `ScreenNormal` (`PixelShader.hlsl`).
- A smoothing cubic B-spline over the 4 × 4 nearest texels; positions taken relative to the first, without cancellation.
- Inland coverage, stage/depth moments and flow use the same positive weights on both the screen and fine grids. Flow is divided by coverage only after reconstruction; dry samples cannot rotate or slow the wet current during the crossfade.
- The normal is the cross product of the surface's derivatives.
- Slope variation as the texels slide: 9 % with a bilinear tent at 4 texels, 3 % with the B-spline, 0.4 % at 8 texels (`log/pistes-glissement.md`).
- Any texel without ground, at the limb, sets the weight to 0: the mesh and the fine grid take over.
- At full weight on every row, the fine grid computes only what those limb pixels read: its samples within 8 pixels and 4 fine cells of the sea-level limb (`FineNearLimb`, `FineTerrain.hlsl`). The others stay off screen.
- Their rivers are filtered at the reading texel's footprint, as the screen relief's, never finer than their own cell (`FineLimbFootprint`).
- Pixel contour refinement follows global screen activation, not this local stencil weight. A missing limb stencil cannot restart a full planetary river search per fragment; this caused the reproduced GPU timeout.

**What the screen relief drives, where its weight is on:**
- the lighting normal, the decision normal and the shore normal;
- the elevation, the inland water and the 3D point where material noises are read;
- the ocean's edge, its contour at the texels antialiased across the pixel;
- the slopes hidden below the texel, from its own roughness (`SlopeSpread`), and the light the finer relief leaves (`FinerReliefLit`), about its own normal;
- no per-pixel water contour query and no invented `DetailSlope` grain under it.

**Fields moved from the mesh to the texel or the pixel:**
- **roughness and fresh volcanic ground:** read in the texel, with the relief;
- **geology:** evaluated at the pixel, at the mesh cell's scale, `Geology(q, cellSize)`.

**Other corrections in the same family:**
- **The grid's uncertainty widens height limits:** the gap between the fine grid's bilinear and B-spline reconstructions adds to the elevation spread of the tree line, snow and shore bands. Off under the screen relief.
- **Exposure widens with the height spread:** `sqrt(EXPOSURE_RELIEF² + 5 spread²)` (`Vegetation.hlsli`). In high ranges, bare ridges and wooded hollows cut the grid's diamonds.
- **Volcanic cones keep their area once widened,** their edge at least two cells wide (`Volcanoes.hlsli`). From orbit, cone fields stood as two-cell discs that came and went.
- **Cloud noises are read 4 pixels to a texel** (`CLOUD_BAND_LIMIT`, `Clouds.hlsli`). The stored and unresolved variances hold the rest.

**Limits:**
- **Shading only:** the mesh still gives geometry, depth and silhouettes (`geometrie.md`).
- **Cost:** not measured; no benchmark was run. Between 150 and 400 km, the pixel water contour query still runs with the remaining weight.
- **Memory:** 64 bytes per texel, about 127 MiB for the 4K maximum; fine-grid samples are 48 bytes, about 27 MiB for 768 × 768.
- **Erosion valleys still appear suddenly** between 1,400 and 1,800 km (`spec-eaux-interieures.md`).
- **Two rejected options** are in [the history](log/spec-rendu-lointain-historique.md#2026-11-02-rejected-options-of-the-screen-relief).
