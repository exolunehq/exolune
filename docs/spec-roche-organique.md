# Specification: an organic rock, varied from region to region

Status: proposed on 2026-10-22, steps 1 to 5 made and merged on 2026-10-22. Since the 2026-10-24, a single rock, its photo (`journal-planete.md`): families, tiles drawn, steps of the column and parallax removed. The relics of stage 1, the color stratigraphic column and its lenses remain alive.

## The finding

View at 150 m of a wall, position `1391.1 -11.04542 50.06777 2.6 55.3`.

- **The wall has nothing organic:** layers of 50 cm and beds from 2 to 8 m, parallel, horizontal, with a regularity of wallpaper.
- **All rock on the planet is read in the same way,** regardless of the region.
- **Nothing grows or accumulates on the replants.**

## The targets

Seven photos, in 1280 px in `docs/images/`, all in the public domain or under CC0, from Wikimedia Commons.

| File | Subject | License and source |
|---|---|---|
|  `cible-granite.jpg`  | Granite Domes, Yosemite | CC0, GeoDIL, [Half Dome 2435](https://commons.wikimedia.org/wiki/File:Half_Dome_(GeoDIL_number_-_2435).jpg) |
|  `cible-gres-zion.jpg`  | Sandstone cliffs in the fog, Zion | Public domain, NPS, [Fog Surrounds the Cliffs](https://commons.wikimedia.org/wiki/File:Fog_Surrounds_the_Cliffs_(17694606102).jpg) |
|  `cible-gres-neige.jpg`  | Cross-stratified sandstone under snow, Zion | Public domain, NPS, [Snow on cliffs](https://commons.wikimedia.org/wiki/File:Snow_on_cliffs_(23224079893).jpg) |
|  `cible-plis.jpg`  | Pleated layers, Provo Canyon | Public domain, [Folded Rock Provo Canyon](https://commons.wikimedia.org/wiki/File:Folded_Rock_Provo_Canyon.JPG) |
|  `cible-falaise-alcoves.jpg`  | Alcove Sandstone Cliffs, scree, New Mexico | Public domain, [Mountains Albuquerque 2](https://commons.wikimedia.org/wiki/File:Mountains_Albuquerque_2.jpg) |
|  `cible-basalte.jpg`  | Stacked Basalt Flows, Bruneau Canyon | Public domain, BLM, [Bruneau Wild and Scenic River](https://commons.wikimedia.org/wiki/File:Bruneau_Wild_and_Scenic_River,_Idaho_(36255524650).jpg) |
|  `cible-badlands.jpg`  | Badlands ravines, Wyoming | Public domain, BLM, [Dubois Badlands](https://commons.wikimedia.org/wiki/File:-mypubliclandsroadtrip_2016-_On_The_Way_To,_Dubois_Badlands_Wilderness_Study_Area_(27982944793).jpg) |

## What the photos show

**A rock family per region, each with its structure.**

- **Granite is solid:** rounded domes, scales parallel to the surface, some large fractures, no layers.
- **Sandstone and limestone are bonded, but not like in our country:**
  - beds from a few meters to several tens of meters, of very uneven thickness;
  - cross-stratifications, oblique inside the beds;
  - color bands from one formation to another, from red to white;
  - tops rounded by erosion, alcoves dug in the tender beds.
- **Layers bend:** they sink and bend at the scale of 100 m to a few kilometers, instead of remaining horizontal.
- **The basalt stacks in flows** of 5 to 20 m, flowing in vertical columns, separated by slopes of scree.
- **The badlands are tender:** thin and colorful strips, all over riddled with tight gutters.

**Everywhere, life and debris take the replats:** vegetation on every cornice, scree at the foot of every wall. Bare rock occupies only what is too steep to hold anything.

## The principle

### 1. Rock families, chosen by geology

The noise of geology, which already chooses the color of the rock by region, also chooses its structure, in four families.

- **Massive,** granite: no layers; curved scales of a few meters and large spaced fractures, with rounded edges.
- **Lithe,** sandstone and limestone: the current structure, but beds from 1 to 30 m of very variable thickness, cross stratifications and color bands by formation.
- **In flows,** basalt: beds from 5 to 20 m, vertical columns, a slope between two flows.
- **Tendre,** badlands: thin strips and tight gutters in the direction of the slope.

Each family has its 64 m tile, generated at startup like the others. Between two regions, two families mix.

### 2. Layers that sink and fold

- **The hanging:** the layer plane tilts by region, from 0 to 40°, instead of always following the horizontal.
- **Plains:** angle changes slowly, on the scale of 100 m to 2 km, and layers curve.
- **The means:** the rotation of the tiles, which already aligns the strata on the vertical, receives in addition this angle.

### 3. Soil and vegetation on the replants

- **Today,** the rock is decided on the slope of the mesh. A cornice of the tile of 64 m remains therefore bare rock.
- **Tomorrow,** the decision also takes the slope of texture: where a cornice is flat, the soil, grass or sand cover it; where it is steep, the rock remains bare.
- **At the foot of the walls,** the scree follows the same logic, on medium slopes.

### 4. Wear

- Rounded edges on all scales, stronger for soft rocks.
- benchmarks that break into lenses, instead of crossing the whole wall.

## The measure

- **The visual benchmark,** at 100 m, 500 m and 2 km, on mountain sites, next to the seven photos.
- **The view of the findings,** taken at its exact position, before and after.
- **The benchmarks of jitter and the ridges,** to verify that the relief carried by the mesh does not degrade.
- **The cost,** for each family tile.

## Validation criteria

- **From one region to another,** we recognize different rock families.
- **no more wallpaper:** no regular and horizontal layers everywhere.
- **The replants green or cover with debris,** the bare rock remains on the cliff.
- **Cost:** less than 0,5 ms extra.

## The steps

1. **The floor on the replats:** the widest gain for the least code.
2. **Hanging and folds.**
3. **The massive and litée families,** with the unequal beds and color bands.
4. **Families in flows and tender.**
5. **Wear.**

## Results

**The benchmark:** `tools/banc_roche.py`, the view of the observation and three mountain sites at 100 m, 500 m and 2 km. Canyon at 11° S, 50° E; dry mountains at 20° S, 125° E; snow-covered peaks at 15° S, 120° E.

### Step 1: the floor on the replants

- **The decision:** the rock yields where its own surface, mesh plus texture, is flat. scree between 0,72 and 0,82 of cosinus, ground between 0,84 and 0,92.
- **Replats:** the rounded cornices of the 64 m tile never flattened on a wall. The top of each benchmark now leans backwards, as much as it rises, on 40 % of benchmark and at most 2,5 m. A step at the foot of the next benchmark takes the height, without step.
- **Effect:** strips of grass or sand on each benchmark, snow also settles there. No more effects beyond 500 m, where the filtered tile loses its replacing.
- **Cost:** zero. **Peaks:** no peaks.
- **Rest:** the bands are as regular as the benchmarks, hence the steps 2 and 3.

### Step 2: hanging and folds

- **The method used, a shift and not a rotation:** a smooth field in meters, `StrataShift`, raises the strata of the rock tiles. Its slope is hanging. The two planes of the biplanar projection see the same offset at the same point.
- **Why not the rotation of the spec:** each projection plane sees another apparent hanging, and an oblique plane distorts it again. Result: clean rafters along the seams.
- **The slope:** octaves of 8 to 2 km, up to `STRATA_DIP` = 0,5 slope, zero where the regional noise is low.
- **Plies:** octaves from 1 km to 128 m, each 0,75 times the previous one, up to `STRATA_FOLD` = 0,4, only in the deformed regions.
- **Effect:** inclined and wavy layers from one region to another; they draw Vs in the ravines, like real strata.
- **Cost:** +0,1 ms to render, +0,1 ms to calculate near the ground. **Peaks:** no peaks.

### Step 3: massive and lithe families

- **Choice:** `MassiveRock`, on the palette of the noise of geology. Granite, and basalt waiting for the 4 stage: solid. From limestone to red sandstone: lité. About half of the mountains of each.
- **The beds no longer come from the tile:** it would repeat them all the 64 m along the wall. A stratigraphic column, `StrataColumn`, calculates them to pixel on s, the elevation less the shift of the step 2.
  - Formations of 10 to 60 m, each its shade, from white to red, its share of tender beds and the thickness of its beds.
  - beds from 4 to 24 m: a flat at the top of the hard beds, a slope at the back of the tender ones, a step at the foot of the next one.
  - The same relief as the mesh, without step: each layering plan decides its height alone, on both sides.
- **The litted tile of 64 m** only keeps what varies along the benchmarks: diaclases and corridors, oblique stratification, curtains of varnish.
- **Granite:** tiles of 8 m and 64 m, without layers. Bumps, domes, curved scales that die on the sides, two networks of fractures, water streaks. Light gray regardless of regional shade.
- **Traps encountered:**
  - Zigzags of lighting on the benchmarks: the height of the spline, smoothed, did not follow the cut relief, interpolated linearly. The column takes the linear height of the vertices.
  - Backsteps from 2 to 3 pixels, crenellated: widths of at least 4 not, not drawn from the grid cell and not from the derivatives screen.
- **Cost:** +0,2 ms to render since the start, in view of the findings. **Peaks:** no peaks.

### Step 4: families in cast and tender

- **Choice, `RockFamilies`:** on the palette of the noise geology, basalt in flows, massive granite, then sediments. Among the sediments, tender where the noise of iron is strong and the region dry. Narrow transitions: two families are calculated only along one band.
- **Castings:** the same column, casts of 3 to 20 m, all hard, each ending with a wide replat of 2 to 4 m that the scree cover, the slope. Tile of 64 m in prismatic columns of 1,3 to 2,2 m, cross joints. Basalt almost black.
- **Tender:** stripes of 2 to 15 m white, red, purple, yellow and gray, beds from 0,8 to 3 m mostly tender. Tile of 64 m in gutters of 1,3 to 2,7 m. Bare rock from 25° of slope instead of 33°.
- **The hanging and the folds** take their dosage in the noise of geology, already calculated by vertex; the regional noise proper of the step 2 disappears. Pleats reduced to 0,25.
- **Sites of benchmark:** Basalt at 15° S, 120° E; granite at 19,7° S, 124,6° E; badlands at 20,3° S, 125,4° E.
- **Limites:** the badlands of the benchmark are on gentle hills, soft rock is little seen. The columns of basalt are only read closely.
- **Cost:** total since start, +0,2 to +0,35 ms to render. Measured under a GPU loaded at 80 % by another instance, times divided by load factor. **Peaks:** no peaks.

### Step 5: wear

- **Lenses, `BedLenses`:** a slow field, noise functions of 256 and 128 m, calculated by vertex. Each layering plane has its threshold against it; below, its march fades and the two beds merge. The beds breaks in lenses, formations rarely. The hue of a bed fades with it.
- **Rounded edges:** Steps and replat 2,5 times wider for soft rock. The rest of the rounding was already there: profiles in `smoothstep`, widths of at least 4 not.
- **Effect:** discreet to the observation, some cornices that stop net.

### Balance

- **Final cost, GPU free, rendered:** +0,26 ms at the discovery, +0,32 ms at the canyon at 100 m, +0,53 ms at the dry site at 100 m. Calculation unchanged.
- **The dry site exceeds 0,03 ms:** the only family read is drawn there, but the four branches of families unfolded weigh on the registers. Tried without gain: two families chosen by index, `[branch]`, loop not unfolded.
- **Criteria:**
  - Families recognizable from one region to another: yes for litée, granite and basalt; badlands not visible due to lack of steep slopes on the site found.
  - no more wallpaper: beds uneven, colorful formations, hanging and variable folds.
  - Covered replats, bare rock on the steep: yes close; beyond 500 m the replats are erased with the filtering.
- **For the fusion:** the new limits are to be passed to the universal rule of `spec-rendu-lointain.md`. List in the session’s award note.

## Merger of 2026-10-22

- **Boundaries converted to the universal rule** of `spec-rendu-lointain.md`: families in `SpreadStep`, soft rock in `SlopeShares`, replats in `RockShares`.
- **The replats as such erased the rock from far:** decided on the slope of the mesh, almost flat at a great distance, they covered the whole rock. They are now a share, according to hidden slopes and lost texture slope: rock view 9–13 % of 800 to 8 km.
- **Projection triplanar** and normal of the relief pass on 32 grid cells, coming from the blades corrections.
- **Cost:** rendered +0,1 to +0,8 ms compared to before the merge.

## Fix of the 2026-10-22: the "felt" effect

**Symptom,** seen in flight at `3756.3 -39.55694 12.77814 -13.1 -141.1`: rectilinear strata, marked with a regular dark line, with rows of black spots.

**The rule broken,** in `principes.md`: no structure drawn with a uniform stroke. It applies to all families and all places.

**Causes, isolated by cutting each layer:**
- **The features:** each plane of the stratigraphic column had a step of 0,6 to 2 m, and each bed ran from one end to the other of the wall.
- **The spots:** in the 64 m tile, the corridors were cut benchmark by benchmark and lined up in rows of dark dash.

**Corrections, for all families:**
- **The steps of the plans follow a law to the cube:** most are barely visible, only a few make the cornices.
- **The edges of the strata wavy** approximately 80 cm, on lengths of 4 to 64 m.
- **The bedss interrupt and resume** along the wall, on 16 to 128 m, beyond the lenses per vertex.
  - The threshold of each plane expands by what the pixel does not show of this field, according to the universal rule.
  - On 4 to 64 m, the benchmarks broke into dashes.
- **The corridors follow the entire slope:** four slots per tile, one in two occupied, wide from 0,4 to 2 m, which wavy and interrupt. Their color and occlusion are softened.

**Measures:**
- **jitter,** with smoothing: 0,22 → 0,19 at the site of the observation, 0,22 → 0,18 at the cornice, 0,40 → 0,37 at the view of the beds.
- **Rock on descent:** unchanged, 10 to 13 %.
- **Cost:** not measurable while hybrid session occupies the GPU; to be resumed.

## Fix for 2026-10-24: cracks and grooves

**Symptoms,** in flight: cracks in straight segments at `4242.2 16.27025 123.15986 16.1 -166.5`, a side of badlands in velvet ribbed at `4285.0 16.27172 123.16603 4.8 -159.1`.

**The rule broken,** the same: no structure drawn with a uniform stroke.

**Correction, for all uses:**
- **Every Voronoi has wavy edges:** its grid is distorted by a periodic noise of half-grid cell and an eighth, in `Voronoi` itself. Granite, crystals and stones inherit it.
- **A crack varies along itself:** it widens, narrows and breaks over half a meter.
- **The badlands gutters run by plates** from 8 to 32 m and gather in ravines of about 16 m.

**Measurements:** quality benchmark without net regression; jitter 0,55 → 0,54 on the slope; no cost, tiles are generated at startup.
