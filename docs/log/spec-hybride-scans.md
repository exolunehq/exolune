# Hybrid test: photo scans for close-up matter

Status: test done the 2026-10-22, tag `piste/essai-hybride-scans`. Recommendation accepted: soft soils are scanned, rock remains procedural. Integrated by the sand photo, merged the 2026-10-23, see "Integration" at the end of the file.

## The finding

- **Procedural limits to detail closely.** Our best rock is at ×2,3 of a real scan to realism measure.
- **Test:** `etat-de-l-art-details.md` track C. Photo scans give the material close up; the procedural keeps the structure and distribution.
- **The concept's "no loaded image" rule is lifted for this test only.**

## Scans

**Source:** Poly Haven, https://polyhaven.com. **License:** CC0, public domain, no attribution required.

| Scan | Authors | Actual width | Role |
|---|---|---|---|
|  `dark_rock_02`  | Amal Kumar | 2,00 m | Charge d &apos; affaires: layered rock, `MATERIAL_ROCK`  |
|  `sandy_gravel_02`  | Dario Barresi | 2,53 m | loaded: sand, `MATERIAL_SAND`  |
|  `cliff_side`  | James Ray Cock, Dario Barresi, Jenelle van Heerden | 1,83 m | witness for rock |
|  `gray_rocks`  | Dimitrios Savva | 1,80 m | witness for rock |
|  `aerial_sand`  | Rob Tuytel | 15 m | for sand |

- **Files:** color in JPEG 2k, height in PNG 16 bits 2k. Out of the depot, in `MyPlanetEngine\scans\`.
- **The witnesses were not used in the rendering:** the measure against them is not circular.
- **`dark_rock_02` rather than `cliff_side`:** its color varies mainly in clarity. `cliff_side` carries red veins and pale blocks that `RockColor` would recolor badly out of sandstone.

## The loading

- **On startup, by WIC,** built into Windows: no new dependencies. `LoadScans` in `D3DApp.cpp`.
- **The folder:** `MYPLANETENGINE_SCANS`, otherwise the first folder `scans` above the executable.
- **In the same tables as the generator,** `materialColor` and `materialSurface`. The generator writes all the slices, then the scans replace their own, mip by mip, by copy.
- **A missing scan** leaves the generated tile at the wrong scale. The title will then display "scans missing".
- **1024 px with the mips:** the 2k is reduced by averages of 2 × 2, then each mip averages the previous one, like the generator.
- **Vertical reversed:** the top of the picture goes towards the y of the tile, which rises along the walls.

**The scale:**

- **Rock:** 2 m tile, the exact real scale.
- **Sand:** tile of 64/24 = 2,67 m, which divides 64 m. The scan is enlarged by 5 %, including heights.
- **The generated tiles keep their size:** granite at 8 m, scree at 4 m, structures at 64 m. Hence `MASSIVE_TILE`, separated from `ROCK_TILE`.

**Colour:**

- **A factor around 1,** the average removed, as the tiles generated: linear color divided by its average.
- **Stored divided by 4,** to hold factors up to 4. The pixel already divides by the average of the tile, the mip 1 × 1.
- **No occlusion:** the photo already bears his.
- **The saturation of the scan is kept,** `kScanSaturation` = 1. Its hue variations are small: standard variation 0,06 for rock, 0,10 for sand, against 0,26 and 0,28 in clarity. `RockColor` gives the region's hue.

**Relief:**

- **Slope:** differences centered on the torus, in meters by meter, on the scaled tile.
- **The height,** in meters, on the unchanged `HEIGHT_RANGE` of the strip: ±30 cm for rock, ±3 cm for sand.
- **Poly Haven does not publish the height scale.** MaterialX gives 0,01 for all its scans: a default value. `metresPerUnit` is ours:
  - rock, 0,15 m per unit: 12 cm of relief on 2 m. Its slopes then have a standard deviation of 0,65, the one that the universal rule assumes for the rock, `STONE_SLOPE_SIGMA` = 0,6;
  - sand, 0,05 m per unit: 3 cm on 2,5 m, slope type 0,26.

**The high pass, for sand:**

- **The defect:** from 10 m, the sand showed a regular camouflage. The 1 m spots in the scan repeat from one copy of the tile to the next.
- **Fix:** Wavelengths greater than 50 cm are removed from the color and height of the scan. Three boxed blurs on the torus, close to a Gaussian.
- **The rock does not have:** its plates of 1 to 2 m make its character, and do not repeat visibly.

## What the procedural keeps

- **Where goes what material:** decisions do not change, `docs/spec-rendu-lointain.md`. Only their texture inputs change, heights and slopes of the scan.
- **The structure of 64 m,** `MATERIAL_MACRO`, the stratigraphic column, the hanging and the replants.
- **The region hue,** `RockColor`: scanning is only one factor.
- **The wrinkles of the sand,** drawn in pixel.
- **Granite and other families,** generated.

**Fine procedural grain remains on the scans:**

- **The scan is less sharp than the thin tile.** A 2k reduced to 1024 texels gives 2 to 2,6 mm by texel. The thin tile generated has 1 mm.
- **Without it,** the rock appears smooth and plastic within 2 m, and the measure sees it: `dark_rock_02` rendered only ×5,7 against itself.
- **With her,** ×1,7. The scan therefore brings the scales of 3 cm to its tile, 50 cm for the sand. The procedural bears the finest and the largest.

## The measure

**The variants, same settings, same build generation:**

- **before:** `b63d0ad`, procedural;
- **raw hybrid:** scans without high pass or fine tile, removed for sand camouflage;
- **hybrid without fine grain:** high pass sand, without fine tile;
- **hybrid retained:** high pass sand and fine tile, the state of the branch.

**Realism, `tools/realisme.py`, vertical view at 1,5 m,** patterns then spectrum. The site `litee` is added to `banc_visuel.py`: the site `roche` shows another family of rock, which the essay does not touch: its notes do not move.

| Witness | Site | Before | Without fine grain | Retained | Floor of the spectrum |
|---|---|---|---|---|---|
|  `cliff_side`  | litee | ×2,77 ; 1,6 dB | ×2,58 ; 1,3 dB | ×2,94 ; 1,3 dB | 1,3 dB |
|  `gray_rocks`  | litee | ×2,90 ; 3,0 dB | ×3,65 ; 3,0 dB | ×3,49 ; 2,4 dB | 2,1 dB |
|  `aerial_sand`  | desert, 4,6 m | ×7,63 ; 8,8 dB | ×6,04 ; 5,0 dB | ×6,55 ; 5,2 dB | 1,0 dB |
|  `dark_rock_02`, charged | litee | ×1,92 ; 2,4 dB | ×5,71 ; 1,5 dB | ×1,73 ; 1,0 dB | 1,2 dB |
|  `sandy_gravel_02`, charged | desert | ×3,83 ; 10,4 dB | ×7,54 ; 3,7 dB | ×5,79 ; 4,0 dB | 1,5 dB |

- **Spectrum gains everywhere:** scan gives the right energy distribution from 3 cm to 1 m. Sand 8,8 → 5,2 dB vs. `aerial_sand`. The rock reaches the floor of the scan against itself.
- **The patterns do not separate the rock:** ×2,77 → ×2,94 against `cliff_side`, ×2,90 → ×3,49 against `gray_rocks`. The note is played at pixel, on the grain, where the scan 2k is too blurred.
- **The sand wins against its witness,** ×7,63 → ×6,55. Against `sandy_gravel_02` himself, he loses: our wrinkles of 12,5 cm add to the stony ground, and the scan is blurred than the original.

**benchmark visual,** `tools/banc_hybride.py`: the three close views, then sand and layered rock to 2, 10 and 50 m. Boards: `docs/images/hybride-avant-apres.jpg`, `hybride-detail.jpg` and `hybride-repetition.jpg`.

- **Sand at 2 m:** gravel, scattered pebbles, a credible desert soil. The procedure showed uniform sand.
- **Rock at 2 m:** a real network of cracks and plates, instead of cracks generated. The large spots of color, the beds and the cornices remain those of the procedural.
- **At 10 m:** fine cracks; the rest is identical.
- **At 50 m and beyond,** and on the views constat, corniche and roche rouge: nothing changes. The tile is erased when a pixel covers 2 to 4 m.

**Repeat,** at 2, 10 and 50 m:

- **Rock:** no repeated pattern visible.
- **Rough sand:** a regular camouflage from 10 m, the spots of 1 m of the scan. **After the high pass:** nothing more, `hybride-repetition.jpg`.

**jitter, `tools/banc_tremblement.py`,** with and without time smoothing:

| View | Before | Without fine grain | Retained |
|---|---|---|---|
| layered rock to 3 m, `588.1 -25.21899 135.73187 30 92`  | 0,66 / 3,78 | 0,68 / 3,89 | 0,67 / 4,21 |
| Sand to 1,5 m, `122.8 26.0 45.0 8`, sun `20 110`  | 0,01 / 0,07 | 0,01 / 0,11 | 0,01 / 0,11 |

- **Unchanged with smoothing.** Without it, a little more flicker: the scan has more fine detail than the generated tile.

**Rendering cost,** same build generation, Debug, five captures per build alternately, minimum and median rendering time GPU:

| View | Before | Without fine grain | Retained |
|---|---|---|---|
| Sand to 1,5 m | 3,25 ; 3,41 ms | 3,31 ; 3,38 ms | 3,25 ; 3,56 ms |
| layered rock to 2 m | 5,11 ; 5,39 ms | 4,42 ; 4,55 ms | 5,16 ; 5,45 ms |
| Constat | 5,27 ; 5,37 ms | 5,03 ; 5,19 ms | 5,23 ; 5,35 ms |
| Corniche | 4,92 ; 5,02 ms | 4,96 ; 5,04 ms | 4,94 ; 5,18 ms |

- **Rendering costs nothing more:** Same texture reads, to ±0,05 ms close. Without the thin tile, the rock would gain 0,7 ms.
- **Startup:** +1,8 s in Debug, 7,9 s instead of 6,1 s for a full capture. Decoding WIC and calculating mips on the CPU.
- **The times displayed on the boards** are not useful: other renderings were running at the same time.

## The recommendation: mix according to scale, and according to material

- **Load soils, sand, gravel, earth: switch to hybrid,** on the band of 3 cm to 50 cm. This is where the procedural is the poorest, and the scan wins to the eye and to the measure: a credible desert soil at 2 m, spectrum 8,8 → 5,2 dB.
- **The rock: keep the procedural.** The scan only gains a fine cracking at less than 10 m, and the measurement does not separate it. The shape of a wall comes from the structure of 64 m, the stratigraphic column and the replats: all this remains procedural.
- **Always procedural:** under 3 cm, the fine grain, sharper than a 2k scan; above 50 cm, the structure, distribution and hue. The high pass cut the scan at this limit, otherwise it repeats in camouflage.
- **Price:** the “no image uploaded” rule falls, for 8 to 11 MB of 2k scans per material on disk. Graphics memory does not change. And the scale of scan heights is to be guessed: Poly Haven does not publish it.

**If the hybrid is selected for soils:**

- a scan by floor, chosen by our masks, as provided for in the C path;
- scans in 4k on slices of 2048 texels, to go down under 2 mm by texel;
- the measure of realism on a rasant view also, where the grain counts less than the form.

**Not done:** `cliff_side` as rock charged, and a shared saturation. With `dark_rock_02`, the question did not arise. `cliff_side` would need: 0,21 of hue, and factors up to 5, beyond the 4 that holds the storage.

## Integration: photo floors

Status: made the 2026-10-22, from `f385126`; merged the 2026-10-23, commit `7bf38a9`.

**What is reported from the test:**

- **Loading WIC,** `LoadScans` in `D3DApp.cpp`, unchanged.
- **The scan `sandy_gravel_02` in the sand slice,** tile of 64/24 m, 0,05 m height per unit.
- **The high pass at 50 cm,** become a rule for any scan, `kScanKeep`: a scan only carries wavelengths less than 50 cm.
- **Procedural fine grain remains** on the scan.
- **The rock remains procedural:** `dark_rock_02` is not relegated, `ROCK_TILE` remains at 8 m.

**Recoloration by the biome:**

- **Sand remains a factor around 1,** which multiplies the biome color, `BiomeColor` into `PixelShader.hlsl`.
- **Averages are taken after high pass:** the stored factor has an average of 1 on each channel. Verified on a Python copy of the load, 8 bits including cut and rounded: 1,0000; 1,0000; 1,0000, and 0,001 % of texels cut.
- **The pixel divides in addition by the mip 1 × 1 of the tile.** The average hue comes from the biome, never from the scan. The scan only keeps its local deviations, especially in clarity: deviations type 0,28, against 0,10 in hue.

**The scree, tried and rejected:**

- **The only scan in main** for another slice is `gray_rocks`, stones in piles. No earth or grass scan in `../scans/`, and no download.
- **Tested on the scree,** 2 m tile slice: more natural to 10 m, a real pile of stones.
- **Scattered:** seen from the cornice, it becomes a uniform carpet of small stones. The stones generated by 25 cm, scattered on the dust, are read better from afar. And it is not a loose floor in the sense of the recommendation.
- **To try it:** a line in `kScans`, and `SCREE_TILE` to 2 m. Plate: `docs/images/sols-photo-eboulis.jpg`.

**The measurement, `f385126` vs `sols-photo`, same builds Debug:**

- **Descent, `tools/banc_descente.py`, from 800 to 8 km,** on 8 km side:
  - sand, desert at 26° N 45° E: 100 % at all heights, in both builds;
  - grass, at 15° S 50° E: 100 % at all heights, in both builds;
  - sand in desert margin, at 30,16° N 54,68° E, where it occupies only a part of the square: 0,0; 0,0; 0,2; 0,6; 1,4; 2,6; 3,4 %, from 800 to 8 km, identical in both builds.
  - **Unchanged everywhere,** to the decimal: from 8 km and above, the scan tile is erased.
  - **The margin curve is not flat,** from 0 to 3,4 %, already in `f385126`. To be considered separately: the square is only 6 pixels at 800 km.
- **Realism vs. `aerial_sand`:** patterns ×7,66 → ×6,54; spectrum 8,8 → 5,2 dB, floor 1,0 dB.
- **jitter,** with and without smoothing:
  - sand at 1,5 m, `122.8 26.0 45.0 8`, sun `20 110`: 0,01 / 0,07 → 0,01 / 0,11;
  - corniche, `2182.0 31.16045 8.58814 1.9 -17.1`: 0,17 / 1,11 → 0,18 / 1,12.
- **Rendering cost,** five captures per build alternately, minimum and median:

| View |  `f385126`  |  `sols-photo`  |
|---|---|---|
| Sand to 1,5 m | 4,03 ; 4,24 ms | 4,02 ; 4,08 ms |
| layered rock to 2 m | 5,83 ; 6,19 ms | 5,71 ; 6,10 ms |
| Constat | 5,32 ; 5,40 ms | 5,38 ; 5,43 ms |
| Corniche | 4,62 ; 4,71 ms | 4,56 ; 4,65 ms |

- **No measurable additional cost:** the variances remain under 0,1 ms, in the noise. Startup takes 1,1 s more in Debug, 6,1 s instead of 5,0 s for a full capture.
- **Planches:** `docs/images/sols-photo-avant-apres.jpg`.
