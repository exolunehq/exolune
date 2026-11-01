# Search: coasts, beaches, cliffs and rocky shores

Status: search for 2026-10-24. **Steps 1 and 2 make the 2026-10-25 on the branch `plages`, tag `piste/plages`, on the old sea. The 1 stage is carried on the sea FFT the 2026-10-31, its width capped; the 2 stage remains to be carried.** The measurements come from a port CPU from complexplanet, `tools/cotes/`. The original plan of the 1 stage is in `log/recherche-cotes-historique.md`.

## 1. Conclusion and plan

**The conclusion**

- **complexplanet has no coastal shape.** The coast is the 0 contour line of a smooth plain that sinks under the sea. 90 % of the shores are plains, with median slope 6 % on 20 m and 4 % on 200 m. Nothing marks erosion, at any scale.
- **Our range is ten times too wide.** Its band of 5 to 25 m of altitude, centered on 15 m, gives a median width of 540 m, and more than 1,9 km for one shore in ten. A real range makes 20 to 80 m.
- **The strips of a real coast are water heights:** tide, shore jet, berm. An altitude band is therefore the right tool for sand, wet sand and rock belts. Its width comes out of the slope, as in nature: width = height / slope.
- **Just put it at the right height.** From 0 to 2,5 m approximately, the beach measures 40 to 70 m wide in median on our shores.
- **A cliff requires geometry.** Its slope comes from the rock, not the terrain: it needs the distance to the shore. Estimated by the elevation on the slope of a complexplanet deprived of its octaves under 200 m, it falls to a factor 2 close for 82 to 86 % of points between 25 and 100 m from the shore.
- **No one does it just because of position.** Outerra and Flight Simulator calculate a distance field per tile; Flight Simulator supports popping. Gaea, World Machine and World Creator remap the altitude near the water. The review of Galin 2019 classifies coastal erosion among the phenomena almost never treated in image synthesis.

**The plan**

| Stage | Nature | Contents | Measure of success |
|---|---|---|---|
| 1 | Made alone, **carried on the sea FFT** | The range of 0 to 2,5 m ± 1 m, at most 120 m wide, on slopes less than 0,18 | Median width 40 to 70 m, versus 540 m; curve `beach` flat to benchmark descent |
| 2 | Made alone, **made on the branch `plages`** | Water bands: clean waterline, wet sand, sea leash, rock belts | Wet sand from 10 to 45 m; net waterline to ground |
| 3 | Rendu seul | The type of coast: sand, pebbles, rocky platform, mud; a field shared with the sea | Coastal parts: approximately 31 % sand, 14 % mud, the rest rocky |
| 4 | Overlay geometry, replacement | The erosion profile: platform and cliff, `min(h, P(d))`  | Cliff heights against Young and Carilli: average 12 m, 90 % under 30 m |
| 5 | Overlay geometry, replacement | The deposit and the plan: berm, dune, caps and bays, needles | Platform widths 80 to 500 m; arc bays |
| 6 | Overlay geometry, detail added under 13,5 m | Blocks at the foot of the cliffs, notches, beach croissant | Waiting for the geometry path of `geometrie.md`  |

**Steps 1 and 2, do the 2026-10-25 on the branch `plages`, commit `c87dcd9`, tag `piste/plages`**
- **One scale, exposure:** all bands are water heights multiplied by `CoastExposure`, average 1 and variance 0,41, taken from the local noise. It is the field to share with the sea.
- **The tapes,** in `GroundMaterials`:
  - range up to 2,5 m, softened by ±1 m, on slopes less than 0,12 to 0,22, above 0 °C;
  - wet soil up to 1 m, twice darker, and its brightness, `WaterSheen` in `PixelShader.hlsl`;
  - the sea leash, from 1,06 to 1,16 m, broken into spots by a noise from 16 m to 50 cm;
  - on rock, algae up to 0,4 m, black lichen from 0,8 to 3 m.
- **The universal rule:** each band is a part of the pixel ground, `ShoreBelow`. The waterline is the spread of heights, hidden and pixel-clean, `ShoreSpread`: clear from near, average from far.
- **Measures:**
  - width of beach on 968 shores: median 39 m, 53 m where there is a beach, against 502 m; p90 209 m against 2 196 m; 18 % of shores without beach, too steep;
  - wet ground: median 14 m, p90 51 m;
  - benchmark of descent, coast of 0,478° N 116,513° E: part of flat beach at 0,1 point near 1 500 at 260 km, at 0,2 point of 800 at 60 km, at 1,4 point of 60 at 2 km.
- **What changes to the eye:** the lands of 3 to 25 m take over the colors of the climate; a beach no longer rises on a cliff.
- **Rules, on the branch only:** The coast is a limit like any other; a noise expands a limit by what it moves it, not more. They go into `principes.md` with integration.
- **Detail:** the input of the 2026-10-25 of `journal-planete.md`.

**The step 1 on the sea FFT, the 2026-10-31**
- **Scope of `c87dcd9`,** in `GroundMaterials`: `ShoreSpread`, `LandShare`, `ShoreBelow`, `CoastExposure` and the range band. Without the step 2.
- **Cap width:** the top of the band is worth `min(2,5 m, 120 m × pente)`, `BEACH.z`. Without ceiling, a band of 2,5 m made 1,25 km on the coastal plains of slope 0,002, which relief has (`RELIEF_COAST_QUIET`).
- **The slope of the ceiling, on 60 m:** a shore normal read on the surface of the mesh to `SHORE_BASELINE` on both sides (`VertexShader.hlsl`). The normal of materials, at 1 m, followed the bumps: at port, 73 % of the land of a coastal plain in beach, 3 % with a slope taken on 20 m. In the distance, the thin grid carries the shore normal as soon as its grid cells covers 60 m (`PixelShader.hlsl`).
- **Offshore exposure,** `CoastFetch`: open water at 3, 10 and 30 km down the slope, on the planet map, a continuous portion of the ground from 10 m to 0; a closed coast keeps `BEACH.w`, 40 % of its exposure.
- **Verified in rendering,** before and after: green motus fringed with sand; cordon of 20 km to 150 m, beach of 50 to 90 m seaside; coastal plain with the colors of the climate; steep coast without beach.
- **Limitations:**
  - a pond of a few hundred meters keeps a ring of sand, the map at 3 km does not see it sheltered;
  - beyond the face of the mesh, without fine grid, a narrow cord loses its range;
  - the exposure remains the local noise, not yet the swell of the sea FFT.

**To wear on the sea FFT**
- **Make on the old sea:** the branch leaves the `jalon/18-lumiere`, before the animated sea and the sea FFT. A fusion test with the animated sea, tag `piste/essai-fusion-mer-plages`, gave the wet sand the reflection of the sea instead of `WaterSheen`; it remained with the old sea (`log/recherche-mer-historique.md`).
- **What remains to be done to integrate the 2 step:**
  - the sea share, `LandShare` and `ShoreSpread`, instead of the fixed fade of `PixelShader.hlsl`, in accordance with the sea surface FFT;
  - the brightness of the wet sand by the reflection of the water of `Sea.hlsli`, which the sea FFT already foresees for the film of a wet shore;
  - `CoastExposure` shared with the wind and the swell of the sea.
- **Remained on the branch:** close, wet sand clearer than a sea without reflection, what the sea FFT can set; the part of sea from far, which varies from 6 points on 2 km; the type of coast, step 3.

**The 4 and 5 steps are replacements:** a dedicated spec, a branch, a `piste/cotes-erosion` tag, a `COAST_EROSION` setting that brings them back to 0.

## 2. Audit: complexplanet by the sea

**Method**
- **A port CPU** of `ComplexPlanet.hlsli` and `LibNoise.hlsli` in numpy, in double precision precision, with the same filtering of octaves and the same rounding of peaks.
- **Validated against engine:** four ground heights measured in `tools/tests/2026-10-24-detail-roche.txt` are found at 0,2 m near, 1,8 m on a summit of 4 354 m.
- **279 shore points,** found on 1 500 randomly drawn arcs, of 150 km each. An arc cuts the coast in proportion to its length: each kilometre of coast weighs as much.
- **Full detail,** the one the mesh wears near the ground. The scripts are in `tools/cotes/`: `cp.py` and `t0.py` to `t7.py`; `t8.py` and `t9.py`, on the `plages` branch, measure the strips and the shares of the ground.

**The noise functions that touch the coast, and their scales**

| noise | Wavelengths of light | Amplitude at shore | Role at the coast |
|---|---|---|---|
| Continents, Perlin 14 octaves | 6 378 km to 214 m | slope 1,4 % on 20 m, 0,9 % on 2 km | lays the coast, gently sloping |
| Turbulence of the continents | capped at 6 km | a few meters of coastal displacement | large-scale sinuosity |
| Plains, two octaves Billow of 8 | 5,8 km to 13,5 m | ±32 m around +64 m | **draw the thin ridge**: slope 4,7 % on 20 m |
| Rivers, RidgedMulti | 340 and 150 km | −26 m median to shore | Wide valleys, rivers of 100 km |
| Collines | 3,8 km to 81 m | up to 2 km | 9 % of shoreline |
| Mountains | 4,6 km to 22 m | up to 8 km | no coast measured |
| Badlands, cliffs and terraces | 7,6 km to 143 m | hundreds of meters | 1 % of shoreline |

**The curve of the continents around `SEA_LEVEL`**
- **The shore falls into a single piece of cubic,** from the input 0 to 0,0625 of the curve: from −768 to +256 m. `continentDef` is equal to −0,016 in median, from −0,13 to +0,04.
- **The shoreline is not at `continentDef` = 0:** the plains add +42 m in median, the coast is therefore where the continent descends to −42 m.
- **The curve has a break, but not at the edge.** libnoise interpolates in uniform parameter on points of unequal deviation: the slope jumps from 1,5 to 24 at the 0 input. This break is at `continentDef` = −0,375, or −768 m, at the edge of the plateau.
- **A lowland plate follows the coast:** from the entrance 0,0625 to 0,125, the curve rises four times less quickly. It is a coastal plain of tens of kilometers.

**The continental shelf, `SHELF_LEVEL` = −0,375**
- **The complexplanet “plateau” is a ramp** from the shore at −700 m. It reaches −130 m to 20 km from the shore in median, and −700 m to 74 km.
- **Then the slope drops suddenly,** from −Z700 to −2 000 m in two to three kilometers: this is the walk of the selector, on a transition of 0,03125.
- **His terrace is that of the abysses,** from −0,75 to −0,375 of `continentDef`, and his pits come from a RidgedMulti of 16 octaves, up to 10 m.
- **Offshore, the slope is likely to be:** −5,7 m to 200 m and −12,4 m to 1 km in median. This is a Dean profile of coefficient A ≈ 0,12 to 0,17, in the range measured on Earth, 0,08 to 0,40.

**No coastal form from meter to hundred meters**
- **No noise depends on distance to shore,** or elevation near 0. The only selector near sea level is that of rivers, which digs half-depth to the shore, at the scale of 100 km.
- **The thin coast is a drowned Billow plain.** A Billow has V-shaped hollows and round bumps: the sea fills the hollows. Our caps are rounded lobes, our creeks are sharp notches. An eroded coast does the opposite: smoothly curved bays, angled capes.

**The slope of the land to the shore**

| Base of measurement | p10 | Median | p90 | Part beyond 0,65, the rock |
|---|---|---|---|---|
| 2 m | 0,033 | 0,076 | 0,25 | 4 % |
| 20 m | 0,030 | 0,065 | 0,22 | 3 % |
| 200 m | 0,017 | 0,041 | 0,13 | 2 % |
| 2 km | 0,006 | 0,017 | 0,06 | 0 % |

- **By type of terrain, on 20 m:** plains 0,06, 252 points; hills 0,42, 24 points; badlands 2,0, 3 points.
- **The slope of the plains comes from the Billow:** 0,047 on 20 m, against 0,014 for continents and 0,002 for rivers.
- **From 0 to 3 m of altitude, the average slope** is 0,045 in median: that of a real beach face, 0,05 to 0,11. But it continues for miles without berm, without dune, without cliff.

**The profile to the interior, along the greatest slope**

| Distance from shore | 10 m | 50 m | 100 m | 200 m | 500 m | 1 km |
|---|---|---|---|---|---|---|
| Median altitude | 0,6 m | 2,4 m | 4,0 m | 6,1 m | 9,4 m | 11,9 m |
| Altitude p90 | 2,2 m | 6,9 m | 11,5 m | 19 m | 37 m | 49 m |

- **The relief of the back-coast is almost just.** At 100 m from the shore, 45 % of our points exceed 4,4 m, average 8,1 m. On Earth: 52 % and 12 m, and beyond 4,4 m a cliff is more likely than a beach (Young and Carilli 2019).
- **What is missing is the abrupt form.** Only 6,5 % of the banks rise by 20 m in the 100 first meters; 7 % have a slope of more than 0,65 in the 200 first meters.
- **The coastal plain is vast:** 50 m of altitude to 6 km of the shore in median, 100 m to 15 km.

**The width of our beach, in practice**

| Top of the Band | p10 | p25 | Median | p75 | p90 |
|---|---|---|---|---|---|
| 15 m, the current band | 98 m | 286 m | 540 m | 1 090 m | 1 890 m |
| 4 m | 23 m | 50 m | 92 m | 188 m | 363 m |
| 3 m | 18 m | 34 m | 66 m | 124 m | 286 m |
| 2 m | 10 m | 22 m | 40 m | 74 m | 158 m |
| 1 m | 6 m | 10 m | 18 m | 28 m | 44 m |

- **The current band:** from 5 to 25 m, center 15 m, displaced by `60 * local.y`, a standard deviation of 8,8 m. 24 % of shores do not reach 15 m in the 3 first kilometers.
- **10 % of shores are steeper than any beach face,** more than 0,18 between 0 and 3 m. 10 % are flatter than 0,01, strange.

**The waterline, at the rendering**
- **The sea covers the pixel part under 0:** `1 - SpreadStep(-1, 1, elevation, elevationSpread)` in `PixelShader.hlsl`.
- **Near the ground, the spread drops to 0,** but the fading from −1 to +1 m remains. At the middle slope, it makes 30 to 45 m of blurred shoreline. The land up to 1 m takes the shade of the sea, and the bottom up to −1 m is seen on the flat sea.
- **The shallow bottom is not visible:** the geometry is capped at `max(e, 0)`, and the color of the sea depends only on `-elevation / 3000`.

## 3. Real ribs: types, sizes, what decides them

**The overlapping shares of the world’s coastline**
- **Sandy, including gravel:** 31 % of ice-free coastline, 1,11 million km measured (Luijendijk 2018). Africa 66 %, Europe 22 %.
- **Probably cliff:** about 52 % (Young and Carilli 2019). The old estimate of 80 % (Emery and Kuhn 1982) is too high. Europe 47 %, California 67 to 72 %, Malta 87 %.
- **Vaseux:** 14 % of ice-free coastline, of which 60 % between 25° N and 25° S. Mangroves cover 17 % of the world's coastline.
- **The shares overlap:** a beach at the foot of a cliff counts in both.
- **By latitude:** cliffs culminate at 45 to 50°, beaches at 25 to 30°; in the humid tropics, less than 20 % sand.

**The beaches of**
- **Emergent width, from shore to dune foot:** no global base. Narrabeen, 40 to 80 m. Aegean Islands: 59 % of beaches are less than 20 m at the widest.
- **Length:** 1,37 km average in Australia, 0,8 km for reflective beaches, 15 km for dissipative beaches. A pocket beach is less than 200 m long.
- **Face slope, tan β:** 0,01 to 0,18; regional medians 0,055 to 0,08 on 5 207 Australian beaches. The finer the grain and the stronger the swell, the flatter it is.
  - sand from 0,2 mm: 1/50 to 1/100;
  - sand from 0,5 mm: 1/20 to 1/40;
  - Gravel of 5 mm: 1/8 to 1/15; pebble berms, 0,1 to 0,25.
- **Dissipative or reflective:** Dean parameter Ω = Hs / (w T). Under 1, reflective, steep, no surf zone; above 6, dissipative, flat, surf zone up to 500 m.
- **Berm:** 2 to 3,5 m above the average level; this is the water level plus the shore jet.
- **Shore jet, R2:** approx. 1 m. Its width at the ground is R2 / tan β: 45 m on a dissipative range, 15 m intermediate, 8 m reflective. Measured: 13 to 32 m.
- **Underwater profile:** h = A x^(2/3), A from 0,08 to 0,40. For A = 0,1, 10 m of depth to 1 km. Closing depth: 13 m in global average. Global median slope so far: 0,007.

**The dunes**
- **Avant-dune:** less than 1 m to 10 or 20 m high, up to 35 m. Narrabeen: 3 to 9 m.
- **Dune fields:** from hundreds of meters to a few kilometers inland.

**The cliffs**
- **Height:** the back coast at 100 m from the shore is 12 m on average, standard deviation 15 m; 90 % of regions are below 30 m; more than 500 m in Yemen and British Columbia.
- **Examples:** Algarve, 10 to 120 m; Caux plateau in Normandy, 100 to 180 m; Twelve Apostles sea stacks, 45 m.
- **Three forms, according to Sunamura:**
  - **type A:** a platform with a gentle slope, from 1 to 7,5°, from the foot of the cliff to below the low sea;
  - **type B:** an almost horizontal platform, from 0,2 to 1,3°, ending off the coast with a small cliff; 80 to 270 m wide in New Zealand;
  - **diving:** no platform, the cliff enters the water.
- **Notch:** from a few centimeters to a few meters of hollow. Its height is worth about the marnage.
- **Backlog, global medians:** hard rock, 2,9 cm per year; medium rock, 10 cm; soft rock, chalk or soft sandstone, 23 cm. Norman chalk: 0,1 to 0,5 m per year. Holderness glacial clays: 0,8 to 2,1 m per year.

**Caps, berries, needles**
- **Arc bays:** a logarithmic spiral or parabola, from a few hundred meters to a few kilometers. The shape does not depend on the size between 0,1 and 16 km.
- **Caps:** their advance increases with their spacing and with the contrast of hardness of the rocks; it decreases with the sand contribution.
- **Needles:** more numerous where sediment is lacking.

**What decides beach, cliff or rock**
- **The altitude of the back coast:** beyond 4,4 m to 100 m from the shore, the cliff becomes probable. This is the most useful cipher rule.
- **The hardness of the rock:** it regulates the retreat, therefore the width of the platforms and the advance of the caps.
- **Sediment contribution:** abundant sand makes beaches and dunes; rare, needles and bare rock.
- **Wave energy:** storm coasts, from 40 to 60° latitude, have wide beaches and dunes; sheltered seas, weak waves.
- **Tide:** beyond a ratio of 15 between tide and wave height, the beach becomes strange.
- **The history of sea level:** rias and fjords are flooded valleys, river or glacier.
- **The tectonic framework:** collision ridges, narrow plateau and cliffs; passive margins, wide plateau and cordons.

## 4. Building them in our engine: options compared

**What others do**
- **Outerra:** a distance map per tile, only for tiles that have land and sea; filtered, its gradient orients the foam. For walls, a horizontal shift in the shader of vertices, which the author says that it does not yet make real cliffs.
- **Flight Simulator:** a distance field per tile, drawn from water vector polygons; it is used for water-image blending, foaming, flattening. Their GDC presentation admits popping at changes in detail level.
- **Star Citizen, No Man's Sky, Elite Dangerous:** nothing published on the coasts.
- **SpaceEngine, Terragen:** a range color per altitude band, without shape.
- **Gaea, World Machine, World Creator:** Altitude remappings near water level. World Creator has a profile with two sides, land and sea, with lengths, angles and noise. Gaea chooses beach or cliff by the stiffness of the transition. World Machine says it is “an approximation without simulation”, and its ranges remain too wide.
- **Houdini:** no rib node.
- **Research:** Galin 2019 ranks coastal erosion among the phenomena almost never addressed. Paris 2019 carves cliffs, caves and arches by implicit primitives, the action of the sea limited to ±8 m around the average level. Génevaux 2013 softens or stiffens the slopes depending on the distance to the coast. Sapoval 2004 shows that an erosion that amortizes converges towards a fractal coast of dimension 4/3.

**Our rules, to judge:** a pure function of position; the same at any distance; patterns on the grid of the planet; no mutation when the mesh is refined.

| Option | Pure function | Even at any distance | Cost | Accuracy to the meter | Family in `geometrie.md`  |
|---|---|---|---|---|---|
| **(a) Altitude band, rendered** | yes | yes, by `SpreadStep`  | zero | exact: the strips are water heights | left alone |
| **(b) Altitude remapping near 0,** `h' = F(h)`, type chosen by a noise | yes | yes, if `F` is smoothed by the hidden spread | zero | widths in `1/pente` : good for a berm, bad for a cliff | replacement |
| **(c) Estimated distance,** `d = h / s_L`, `s_L` the slope of a complexplanet without octaves under 200 m | yes | yes, `s_L` is fixed | 2 additional capped assessments on coastal peaks | factor 2 for 82 to 86 % of points from 25 to 100 m | replacement |
| **(d) Distance field grid,** per tile or window, by jump flood | no | no: depends on texel and window | one pass per tile | exact to texel | out of order |
| **(e) Deformation of the coast plane,** caps and bays by a noise hardness | yes | yes | and noise | does not give distance | replacement |
| **(f) Simulation,** Sapoval erosion, Paris primitives | no | no | heavy, pre-calculated | realistic | out of order |

**(b) Remapping alone** is not enough for cliffs. A cliff of 20 m is not dependent on the slope of the terrain; an altitude remapping makes it a ramp of 400 m on a plain at 5 %, and a wall on a hill.

**(c) The estimated distance is the key to the cliffs.** Measurements of the benchmark CPU, distance along the greatest slope:

| True distance | Slope taken without octaves under 50 m | under 200 m | under 1 km |
|---|---|---|---|
| 10 m | 88 % close to ×2 | 67 % | 25 % |
| 25 m | 89 % | 82 % | 36 % |
| 50 m | 81 % | 86 % | 46 % |
| 100 m | 73 % | 82 % | 58 % |
| 200 m | 63 % | 73 % | 66 % |
| 400 m | 57 % | 66 % | 69 % |

- **An octaveless slope under 200 m, taken in front differences at the step of 50 m,** covers the band of 20 to 200 m of beaches and cliffs. The medians fall just.
- **Remaining error comes from the fine octaves of `h`,** ±0,5 m approximately: ±12 m distance to 4 % slope. It makes the foot of the cliff wavy, which is natural.
- **The direction of the sea** is the descent of this slope: `-∇h_L / |∇h_L|`. In pixels, the normal of the field already gives it.
- **Do not take the slope of the mesh:** it depends on the grid cell, so it changes as you go down.

**Recommended profile, step 4: erosion removes, it does not add**
- **`h' = min(h, P(d))`,** with `d = h / s_L`. `P` is the eroded profile: a platform at +0,3 to +1 m up to the `r` retreat, then a slope wall 2 to 6, or 63 to 80°.
- **The shore does not move:** `h' ≤ h` and `P ≥ 0` on land.
- **The height of the cliff out of the ground:** is the altitude of the ground at the retreat `r`. Measured on our shores:

| Recul `r`  | Cliff median | Cliff p90 |
|---|---|---|
| 50 m | 2,4 m | 6,9 m |
| 100 m | 4,0 m | 11,5 m |
| 200 m | 6,1 m | 19 m |
| 500 m | 9,4 m | 37 m |

- **A retreat of 200 to 500 m approaches the heights of the Earth:** average 12 m, 90 % under 30 m. It also gives platforms of the width of the real ones, 80 to 500 m.
- **The backlash comes from the hardness:** a noise on the grid of the planet, to take in `Geology`, so that rock color and coast shape agree. Soft rock, long retreat; hard rock, short retreat and plunging coast.
- **From far, a grid cell wider than the cliff** takes the average of `min(h, P)` on its hidden heights, as `SpreadStep` does for the limits. Without this, the plateau and cliff would mutate as they approached.
- **The rock comes alone:** the wall exceeds 0,65 of slope, the rule of materials there puts the rock and its wall photos; the platform, soft, takes the photo taken from above.
- **Cost:** two ratings capped at 200 m, for only summits between 0 and 100 m of altitude. To be measured on a coastal view.

**The 5 step: the deposit and the plan**
- **Berm and dune:** `h' = max(h', B(d))` where the type is sandy. A slope face 0,05 to 0,11 up to a berm of 2 to 3,5 m, a flat beach top, a front dune of 2 to 10 m.
- **Capes and bays:** a noise of hardness moves the shore, `h + a · dureté` near 0. Advance on hard rock, bay on soft rock. The shore moves: replacement on the scale of 100 m to a few kilometers.
- **Needles:** in the eroded platform, a cellular noise keeps pillars at the original altitude, where sediment is missing.

## 5. The rendering of the shore, without geometry

**The water strips, all at altitude, so accurate and pure**
- **The waterline, sharp close up:** the fade from −1 to +1 m becomes the spread of the pixel alone, its slope times its size. The transition is marked by the following bands.
- **Wet sand:** from 0 to shore jet, 0,5 to 1,5 m depending on exposure. Albedo divided by 2 approximately: 0,18 dry versus 0,09 wet. On our slopes, 0 to 1 m makes 18 m in median, 44 m at p90; the actual shore jet makes 8 to 45 m.
- **The shine of wet:** it takes a specular lobe, absent from the soil today, which is only diffuse. Lagarde: diffus multiplied by `lerp(1, 0.2, porosité)`, brilliance towards 1. To share with the sea.
- **The sea leash:** a dark and broken line at the highest point of the shore jet, of a few decimeters to 1 or 2 m. It follows the universal rule from far.
- **The belts of rocks,** on the rock at the shore:
  - **wetted** under the jet of shore, darker;
  - **algae and balanes** on the marnage, from −½ to +½ marnage, brown-green;
  - **black lichen,** *Verrucaria maura*, just below the high sea and above, wider on exposed coasts; waves add 2 to 4,4 m;
  - **dry rock** above.
- **The bottom under shallow water:** sand or rock, attenuated by the depth `-h`, which is accurate. It is the sea side that absorbs it.

**The materials**
- **Beach sand:** the Aerial Beach scan 01 has wrinkles from 50 to 80 cm, in tongues; our wind wrinkles are 12,5 cm (`spec-textures-generees.md`). On the beach face, wind wrinkles have no place to be.
- **Pebbles:** a matter of its own, on the slopes of 0,1 to 0,25, where the type of hill says it.
- **The cliffs:** the photos of wall in place, `marble_cliff`, and the column of strata. Chalk, granite, sandstone: shades of `Geology` and `StrataColumn`.
- **Poly Haven candidates, to check:** shoreline textures, sand and rock mixed, and the mesh `coastal_cliff_04` of 87 m already spotted in `spec-parois-minerales.md`.

**What the coast expects from the sea**
- **The height and period of the waves,** to fix the shore jet, therefore the height of the wet sand and the leash.
- **A shared exposure field:** exposed coasts have cliffs and wide belts, sheltered ones have beaches and mud. Coast and waves must read the same noise.
- **The marnage, if there is one:** it regulates the strain bands. Micro below 2 m, meso from 2 to 4 m, macro beyond.
- **The foam of the flood and the jet of shore,** oriented by the direction of the sea: the descent of the slope.
- **The transparency of shallow water,** to see the bottom of the coast.

## 6. Measuring against the real

**The benchmark CPU, `tools/cotes/`**
- **The port CPU of complexplanet** is validated at 0,2 m against the engine. It measures in minutes, without GPU, on hundreds of randomly drawn shore points.
- **What it outputs:** Band width, six-scale shoreline slopes, inland and offshore profiles, accuracy of estimated distance, cliff heights of a candidate profile.
- **The scripts:** `t2.py` finds the banks; on the branch `plages`, `t8.py` measures the width of the bands, `t9.py` gives the true shares of a square of ground, for the benchmark of descent.

**Quantified targets**

| Size | Actual | Today | Source |
|---|---|---|---|
| Width of range | 20 to 80 m; Aegean, 59 % under 20 m | median 540 m; 39 m on the branch `plages`  | Narrabeen, Aegean Islands |
| Slope of the beach face | medians 0,055 to 0,08, 0,01 to 0,18 | 0,045 from 0 to 3 | Your 2022 |
| Underwater slope up to 13 m | median 0,007 | about 0,012 | Athanasiou 2019 |
| Back coast to 100 m | average 12 m; 52 % beyond 4,4 m | average 8,1 m; 45 % | Young and Carilli 2019 |
| Coast to cliff | approximately 52 % | 7 % have a slope of more than 0,65 | Young and Carilli 2019 |
| Sandy coast | 31 % | all temperate coast | Luijendijk 2018 |
| Coastal mud | 14 % | 0 % | Sandy coasts, 2023 |
| Width of platform | 80 to 500 m | None | Sunamura, Trenhaile |

**Open Data Sets**
- **Beach slopes:** Australia, 132 000 transects; Pacific, 3 000 beaches; California.
- **Near coast slopes, world:** Athanasiou 2019, one point per kilometer.
- **Lidar profiles of US beaches:** USGS, dune foot, crest, width, all 10 m.
- **Profiles of Narrabeen from 1976.**
- **Cliff retreat rate:** GlobR2C2, more than 1 680 values.
- **OpenStreetMap :** `natural=coastline`, `beach`, `cliff`, `bare_rock`, `shingle`. The taginfo counts give an order of magnitude, including the inner cliffs.
- **Downloads:** to be authorized on a case-by-case basis.

**In the engine**
- **`banc_descente.py`,** views `beach` and `sea`: the 1 500 km range part on the ground must remain flat.
- **`banc_qualite.py`:** no p95 degraded by more than 10 %.
- **`banc_visuel.py`:** coastal locations at different heights, facing target photos. Étretat for the chalk, the Algarve for the sandstone, the Côte de Granit rose, the Twelve Apostles for the needles, an Australian beach for the sand. Public domain images, such as the `cible-*.jpg`.
- **The fractal dimension of the coastline:** by counting boxes on the shore points of the benchmark CPU, from 10 m to 10 km. West coast of Great Britain: 1,25 according to Mandelbrot.

## 7. Sources

**Geomorphology**
- Young and Carilli 2019, coastal cliffs of the world: https://escholarship.org/uc/item/579326kr
- Luijendijk et al. 2018, the state of the beaches of the world: https://www.vliz.be/imisdocs/publications/ocrd/312913.pdf
- Sandy coasts of the world, 2023: https://pmc.ncbi.nlm.nih.gov/articles/PMC10716179/
- Vos et al. 2022, beach slopes in Australia: https://essd.copernicus.org/articles/14/1345/2022/
- Athanasiou et al. 2019, near coast slopes, world: https://essd.copernicus.org/articles/11/1515/2019/
- Short 2006, Australian beaches: https://ozcoasts.org.au/wp-content/uploads/2018/05/ShortJCR06.pdf
- Masselink and Short 1993, relative marking: https://journals.flvc.org/jcr/article/view/79047
- Reflective and dissipative beaches, Coastal Wiki: https://coastalwiki.org/wiki/Reflective_beach, https://www.coastalwiki.org/wiki/Dissipative_beach
- Shore jet, Stockdon 2006, Coastal Wiki: https://www.coastalwiki.org/wiki/Wave_run-up
- Grain-dependent slope, CEDD Hong Kong: https://www.cedd.gov.hk/filemanager/eng/content_102/p5_table.pdf
- Dean, Bosboom and Stive's balance profile: https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/07%3A_Cross-shore_transport_and_profile_development/7.02%3A_Equilibrium_shorface_profile/7.2.2%3A_(Semi-)_empirical_derivations
- Tectonic classification, Bosboom and Stive: https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/02%3A_Large-scale_geographical_variation_of_coasts/2.03%3A_Tectonic_control_of_coasts/2.3.4%3A_Summary_of_the_tectonic_classification
- Davies Surf Environments: https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/04%3A_Global_wave_and_tidal_environments/4.03%3A_Large-scale_variation_in_wave_environments/4.3.2%3A_Wave_environments
- Barrier Island Berms, USGS: https://www.usgs.gov/publications/predictions-barrier-island-berm-evolution-time-varying-storm-climatology
- Narrated : https://pmc.ncbi.nlm.nih.gov/articles/PMC4828941/
- Beaches of the Aegean: https://nhess.copernicus.org/articles/17/449/2017/
- Hesp 2011, coastal dunes: https://ref.coastalrestorationtrust.org.nz/site/assets/files/6990/568c626208ae153299b66729.pdf
- Type A and B platforms: https://www.erudit.org/en/journals/gpq/2006-v60-n1-gpq1758/016362ar/, https://pmc.ncbi.nlm.nih.gov/articles/PMC4754505
- Platforms from New Zealand: https://researchspace.auckland.ac.nz/handle/2292/19986
- Notches: https://www.redalyc.org/pdf/505/50544801002.pdf
- Prémaillon et al. 2018, GlobR2C2, retreat of the cliffs: https://esurf.copernicus.org/articles/6/651/2018/
- Sussex Chalk Retreat: https://research.edgehill.ac.uk/en/publications/temporal-and-spatial-variations-of-chalk-cliff-retreat-in-east-su/
- Arc bays: https://nora.nerc.ac.uk/id/eprint/512322/
- Limber and Murray 2014, caps: https://scholars.duke.edu/publication/1033824
- Twelve Apostles: https://www.doi.org/10.2112/SI75-119.1
- Bird et al. 2013, rocky shore areas: https://pmc.ncbi.nlm.nih.gov/articles/PMC3792175/
- Belt of *Verrucaria maura*, MarLIN: https://www.marlin.ac.uk/habitats/detail/120/verrucaria_maura_on_littoral_fringe_rock
- Darker wet sand: https://www.wgtn.ac.nz/scps/staff/pdf/darkerwhenwet.pdf, https://pmc.ncbi.nlm.nih.gov/articles/PMC4226492/
- Morphology of beaches of the United States, USGS: https://www.usgs.gov/data/lidar-derived-beach-morphology-dune-crest-dune-toe-and-shoreline-us-sandy-coastlines
- Profiles of Narrabeen: https://datadryad.org/dataset/doi:10.5061/dryad.28g01
- Pacific Beach Slopes: https://zenodo.org/records/18368941
- OpenStreetMap, values of `natural`: https://taginfo.openstreetmap.org/keys/natural#values
- Mandelbrot 1967 : https://gis.humboldt.edu/olm/courses/gsp_510/Articles/Mandelbrot1967.pdf

**Engines and tools**
- Outerra, map of distance from shore: https://outerra.blogspot.com/2011/02/ocean-rendering.html
- Outerra, field algorithm: https://outerra.blogspot.com/2009/02/procedural-terrain-algorithm.html
- Outterra, horizontal displacement: https://outerra.blogspot.com/2009/05/horizontal-displacement.html
- Flight Simulator, Fuentes, GDC 2022 : https://www.asobostudio.com/files/inline-images/Designing_Terrain_System_Fuentes_Lionel.pdf
- SpaceEngine, create a planet: https://spaceengine.org/manual/making-addons/creating-a-planet/
- Gaea, Sea node: https://docs.quadspinner.com/Reference/Water/Sea.html
- Gaea, Coast node: https://docs.quadspinner.com/Reference/Water/Coast.html
- World Machine, coastal erosion: https://www.world-machine.com/blog/?p=73
- World Creator, Shore filter: https://docs.world-creator.com/reference/terrain/filters/effect/shore
- Houdini, HeightField Erode : https://www.sidefx.com/docs/houdini/nodes/sop/heightfield_erode.html
- Crest, shallow water: https://crest.readthedocs.io/en/stable/user/shallows-and-shorelines.html
- Sea of Thieves, SIGGRAPH 2018 : https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf
- Lagarde wet surfaces: https://seblagarde.wordpress.com/2013/04/14/water-drop-3b-physically-based-wet-surfaces/

**Search in synthesis of images**
- Galin et al. 2019, review of terrain modeling: https://people.cs.uct.ac.za/~jgain/wp-content/papercite-data/pdf/galin2019.pdf
- Génevaux et al. 2013, land by hydrology: https://www.cs.purdue.edu/homes/bbenes/papers/Genevaux13ToG.pdf
- Cordonnier et al. 2016, river lifting and erosion: https://www.cs.purdue.edu/homes/bbenes/papers/Cordonier16CGF.pdf
- Paris et al. 2019, amplification by implicit forms, cliffs and marine arches: https://people.cs.uct.ac.za/~jgain/wp-content/papercite-data/pdf/paris2019.pdf
- Paris et al. 2020, implied block rocks: https://hal.science/hal-02926218
- Doran and Parberry 2010, beach officers: https://ianparberry.com/pubs/terrain.pdf
- Sapoval et al. 2004, erosion fractal ribs: https://arxiv.org/abs/cond-mat/0311509
- Quilez, distance estimate: https://iquilezles.org/articles/distance/
- Quilez, derivatives of gradient noise: https://iquilezles.org/articles/gradientnoise/
- Rong and Tan 2006, jump flood: https://www.comp.nus.edu.sg/~tants/jfa/i3d06.pdf
- libnoise, complexplanet : https://raw.githubusercontent.com/eXpl0it3r/libnoise/master/examples/complexplanet.cpp

**Not verified or missing**
- No global statistics of beach width, cliff height or slope, fore-dune width, needle size or creek.
- The heights in meters of the black lichen belt; the world shares of micro, meso and macro tides.
- The pages of Proland and HAL could not be read directly.
