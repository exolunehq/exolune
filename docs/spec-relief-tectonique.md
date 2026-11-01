# Spec: tectonic relief

Status: spec live, since the 2026-10-31. Steps 0 to 3 make the 2026-10-31 on the `bruit-propre` branch, not committed; their defects fixed the same day, second pass: ridges, rifts, chains, budget of the start, entries of the level 0. To be judged in flight: `tools/tests/2026-10-31-relief-tectonique.txt`. **This is the relief of the game,** without variable: `Relief.hlsli` does not keep anything of the composition inherited from complexplanet. The old relief is at commit `f00004d`. Everything comes from `recherche-relief.md`: the state of the art, licenses, sources. Outdated versions: `log/spec-relief-tectonique-historique.md`.

## The objective

**The relief is based on a tectonic map calculated at startup, not a noise.** The noise only makes the detail, under 50 km, modulated by geology.

- **Why:** The old relief had no structure that fits with water; 41 % of the land in bowls, rivers that cross the massifs (`recherche-relief.md`, section 3).
- **The model followed:** the overall structure is calculated once, outside the rendering; the rendering evaluates it point by point and adds noise. No one simulates plates by frame.

## The constraints

- **No speed limit:** you move from one point to another on the planet, or from one planet to another, in one single image. Nothing is calculated on the way or in the background.
- **The perimeter is a solar system:** the maps of all its planets and moons are calculated at startup, once per seed.
- **A map carries geometry to three conditions:** fixed data per seed, read continuously, above two of their cells (`principes.md`).
- **From the original code:** no lines from the projects listed by search, even under MIT (`recherche-relief.md`, section 5).

## Architecture, in four layers

| Layer | Scales | Where, when | Status |
|---|---|---|---|
| 1. Tectonic map | plates from 1 000 to 10 000 km; fields to 20 km | CPU, at startup, less than 1 s, 38 MB on the GPU | made, corrected on 2026-10-31 |
| 2. Large forms | 6 000 km to 50 km; coasts up to 3 km | map and analytical profiles, by vertex | Done on 2026-10-31 |
| 3. Detail | 50 km to 13,5 m | noise of `Noise.hlsli` modulated by the map, by vertex | made the 2026-10-31 |
| 4. Level 0 | above 20 to 40 km | Start-up | inputs ready; the connection to be made, branch `erosion-niveaux`  |

## The tectonic map, `Tectonics.cpp`

**One card per celestial body:** `Tectonics::Build({ seed, radiusKm })`. The same executable and body produces the same file, bit by bit. The planet takes `PLANET_SEED`.

**The calculation:**
1. **The grid:** the cube of the planet, 6 × N², N the power of two that gives texels of 20 km about. For the planet, 512².
2. **The noise functions:** gradient fBm of noise, from 3 000 to 60 km, each reduced to a standard deviation of 1.
3. **Continents, by location:** a fBm of continent size, left-handed, threshold at the drawn part, 40 to 44 % of continental crust, like the Earth with its plateaus (Cogley 1984). The spots of less than 40 cells join the crust that surrounds them.
4. **The plates:** 12 to 20 germs, each the furthest from the others among 24 drawn; a competing growth at noise cost, slowed four times on two cells on either side of the ribs, where borders stop. Plates from 0,3 to 22 % of surface; 18 on 19 bear continent and ocean, seed 0.
5. **Movements:** a drawn Euler pole; 40 to 100 mm/an to 90° of the pole on an oceanic plate, 10 to 40 on a continental plate, between the two according to its part of continent.
6. **Boundaries:** any cell adjacent to another plate; their points smoothed along them, on both edges. The relative velocity projected on the normal; it and the crust of each edge averaged along the border on 100 km approximately.
   - **transformer** if the normal component is less than 40 % of the relative speed;
   - **convergent,** by the local crust: subduction under a continent, under an ocean, collision of two continents;
   - **divergent:** rift between two continents, ridge otherwise.
7. **Polarity, by pair of plates where they converge:** the oceanic under the continental; of two oceanic, the oldest crust; of two continents, the one that advances most into the other.
8. **The active margins:** an ocean of less than 700 km between a front that its plate overlaps and a continent of this plate is consumed; the continent reaches the pit, as under the Andes. Further on, the arc remains at sea, a marginal sea behind it, like Japan.
   - **The rifts that broke their continent:** a rift opens from 1 to 3 Ma, drawn by pair of plates; its width is its divergence times this time. Beyond 50 km, the crust becomes oceanic, younger towards the axis: a narrow sea like the Red Sea, 300 km at most, a ridge in its middle, two young margins. Below, there is still a rift valley.
   - **Then the steps 6 and 7 again.**
9. **The profile families, by sign of movement, not by type:** overlapping, plunging, collision, rift, ridge. An oblique border still raises its chain. The movement of each family is smoothed along the border on 200 km, the other families counting 0: it falls to 0 at the ends, where chains and pits taper.
10. **Ocean floor age:** distance to the plate ridge, on half plate expansion speed; without ridge, nearest elsewhere, on average speed; 200 Ma at most.
11. **The ancient sutures:** the continents before the plates cut into cratons, one by 2 % of the surface, their germs pulled apart; a suture between two cratons, from 100 to 1 000 Ma.
12. **Distances:** a propagation of the nearest germ by source; to all borders, to each family in its plate, to the edge of continents, to sutures. Each stops at the reach of what it shapes: 1 500 km for borders and families, 2 000 km for the edge of continents, 1 000 km for sutures.

**The fields per cell,** then smoothed on two texels: the large shapes, the amplitude and character of detail, the vivid profiles, the classes (the next section); the elevation and erodibility, for the level 0.

**Budget, less than 1 s per planet:**
- **Propaganda on buckets of one quarter of texel,** Dijkstra order to one quarter of texel close, without heap; already closer neighbors excluded from comparison.
- **What does not depend on each other at the same time:** regional variations and cratons on a thread as plates grow; the edge of continents during second ranking; the last propagations together, one per thread.
- **The turns along the borders on eight wires** held together from one turn to another; the smoothing of all fields in the same passes.
- **What exceeds 300 km on a half-resolution cube,** read in continuous bilinear between the faces: the lefting of the continents, the first octaves of their potential and the cost of the fronts, the regional variations.
- **The age for polarity,** at the only borders, by a search among the ridges; its whole field with the last propagations.

**Storage, `Tectonics.hlsli`:** a texture array RGBA16F, `t18`, three slices per face, 520² texels; a second to a quarter of the resolution, `t19`, one slice per face, 130² texels, for views. 38 MB on the GPU.
- **0 section:** the altitude of the large forms (m); the relief of the detail (m); its youth, 1 on a young chain; the strata, > 0 in horizontal layers on a platform, < 0 in soft sediments.
- **1:** the distance to the plate boundary (km); the depth of a pit, the axial relief of a ridge or rift, the hollow of a transform (m).
- **2 section:** the distance signed by the order of the plates, at 300 km at most, exact across the boundary for its profiles; the distance to the smoothed boundary on 40 km, along which the chains stretch; the rock and the plate, in classes.
- **3, for the views, at a quarter of the resolution:** the age of the bottom (Ma), the distance to the edge of the continents (km), 2 000 at most, the elevation (mm/an), the distance to the sutures (km).
- **4 slice, in the file only, for the 0 level:** erodibility of the rock; the file also keeps the 3 slice at full resolution.

**The reading, continues between the faces:**
- **Each face has a border of 4 texels,** the field beyond its edge, interpolated on the neighboring face. A cubic B-spline, 4 × 4 readings, reads one face only.
- **Near an edge, the faces mix** on 1,5 texel, by weights that depend only on the point. Measured on the port, no jumps or bends at edges and corners.
- **The position in the texel in double precision:** 1/m in float, refined by a Newton step in double precision; the point is read to the millimeter.
- **No hardware filtered reading:** its weights have only 8 bits, the card would run in steps of 80 m.

**Diagnostic views,** by `MYPLANETENGINE_VIEW` or at the end of a test line, without light or air:

| Name | What it shows |
|---|---|
|  `plates`  | each plate its colour, darkened on the oceanic crust; borders in black, continents' edge in white |
|  `boundaries`  | the type of the nearest border on 250 km; twice darker on the sinking plate; sutures in brown |
|  `boundarydist`  | distance to the edge of continents up to 2 000 km, orange on continental crust, blue on oceanic |
|  `crustage`  | the age of the bottom, red to the dorsals to purple to 200 Ma; the old chains in brown |
|  `rocktype`  | oceanic crust, volcanic, young pleated, sediments, old pleated, base |
|  `uplift`  | the level lift 0, orange up to +6 mm/an, blue up to −6 |
|  `relief`  | the relief in hypsometric shades and in the sun, the seabed including, the water removed, exaggerated with the pixel size |

## The large forms, step 2

**The map gives the shapes of more than 50 km; the shader there puts the sharp profiles on its distances.** Everything is read at a left point by a noise of 800 to 25 km, 30 km of difference, so that no shape appears drawn. The chains, bows and shoulders rises combine in smooth maximum, (Σ u⁴)^¼: never their sum.

| Forme | Where | Profile | Source |
|---|---|---|---|
| Oceanic crust | everywhere at sea | GDH1: −(2 600 + 365 √t) before 20 Ma, −(5 651 − 2 473 e^(−0,0278 t)) after; less sediment load, 800 (1 − e^(−t/60)); ±400 m of large-scale swell | Stein and Stein 1992 |
| Margin liability | borders of continents | slope of −3 300 m at the foot to −140 m in 70 km; plateau of 50 to 250 km to the coast; coastal plain inland, 280 ± 220 m | Kennett, *Marine Geology* ; Cogley 1984 |
| Active margin | under a subduction | slope of 35 km, plateau of 12 km, break at −250 m | Same |
| Marge jeune | on the edge of a narrow sea | that of an active margin, its foot at −1 800 m; shoulders of 1,1 km to 40 km of the coast | Red Sea |
| Fosse | subduction front | 2,1 to 4,3 km below the plain, half width 22 km, rounded bottom on 6 km; segments of 120 km, ±25 % | Stern 2002 |
| External burr | plunging plate | +380 m to 150 km from front | Turcotte and Schubert, *Geodynamics*, 3.17 |
| Cordillera | continental shelf | 1,4 to 3,2 km average, ±20 %, from 90 to 400 km of pit, 150 to 400 km wide; volcanic arc on its ridge | Stern 2002 |
| Island arc | Oceanic straddling | +3,3 to 4,2 km to 175 km of the front, islands by detail | Stern 2002 |
| Collision chain | two continents | 1,7 to 3 km average on 170 to 210 km on both sides | — |
| Plateau of the hinterland | overlapping, convergence > 15 mm/an | up to 4,6 km, on 150 to 800 km (Tibet) | — |
| Basin of the Outback | collision | −450 m to 240 km from front, soft sediments | Turcotte and Schubert |
| Rift | slow divergence between continents | a thermal dome of 1,2 km over 400 km; shoulders of 1,1 km to 55 km; half-width graben of 25 km, 0,5 to 0,8 km, walls of 5 km: an emerged bottom | East African Rift |
| Narrow Sea | rift opened more than 50 km | young crust lifted from 1 km, hot and filled: 2 to 3 km of depth; a slow ridge in its middle, its axial valley half; two young margins | Red Sea |
| Dorsale | divergence at sea | the young crust; axial valley of 1,6 km on a slow ridge, dome of 350 m on a fast, 10 km half width, by segments | Macdonald 1982 |
| Faille transformante | dominant shear | lows of 1,2 km at sea, 600 m on a continent | — |
| Old chain | sutures | 2 600 e^(−âge/250 Ma): 750 m of average to 300 Ma | Appalachian Mountains, Ural Mountains |
| Craton | far from borders | 280 ± 220 m, ±150 m of hills on the base | — |

**Every profile has a width of at least two grid cells:** wider, its depth decreases by so much, its average remains.

## The coasts

**Near the shore, the level moves by one noise, filtered by the grid cell, so that the coast moves by a given distance.** Its amplitude is the slope of the large shapes once this displacement (`principes.md`): a coast is cut as much on a flat plain as against a mountain range.
- **Where:** within 40 km from the shore along the slope, and 300 m from sea level; the slope read on the B-spline of the map.
- **The type of hill, by this slope:** flat below 2 m/km, a passive margin; steep above 8 m/km, an active or young margin.
- **The noise:** five octaves from 60 to 3 km, lacunarity 2,2; each 0,62 of the previous on a flat hill, 0,7 on a steep, more cut. The fine octaves partly in drowned valleys, |n| less its average, narrow furrow along the zeros of the noise: rias and estuaries, 60 % on a steep coast, 35 % on a plateau.
- **Displacement:** 12 km at a standard deviation on a steep hill, 8 on a flat. Capes, bays, islands near the steep coasts.
- **The flat ribs, cords:** on half of them, by spots of 400 km.
  - **Along the smooth shore,** not the contour of the shore: the large forms, the three wider octaves of the noise of the ribs, their rias rounded on a half-gap, and the three of the detail. Fine octaves cut the coast behind the lagoon.
  - **Arc-shaped islands between passes,** zeros of a noise of 15 km: at 2,5 km off the coast in the middle, at 1 km near the passes, where their tips curve and taper.
  - **Their profile:** 3 m above sea level, ±40 % according to dunes of 4 km, lower at the tips; 0,6 km of half width in the middle, 0,36 at the tips; a smooth beach on the sea side; behind the low dunes, cones of overflow in the lagoon, at the third of the ridge and three times wider.
  - **Relieve from the relief below them, their entire crest.** Never on land surface, erased on its first half meter.
  - **The emerged part is about two grid cells at least, or remains drowned.** `ReliefSeaProfile` redistributes the vertex in a flat core with Gaussian connection, without changing the area of the profile, including overflows; sufficiently resolved, the profile remains identical.
  - **The same rule applies to their curved tips and overflows.** No other distinct profile of volcanic arrow, plateau or motu exists in the relief of this branch; the island arcs are large map shapes.

**The filter of the profiles that cross the sea, from the 2026-10-31:** above a local `h < 0` bottom, the rise `A`, including presence, has for half width `w` after `ReliefWidth` and for overflow part `f` between 0 and 1/3.
- **Its area is `I = A w √π (1 + f)`.** Sea side, a Gaussian; lagoon side, its mixture with a Gaussian three times wider.
- **The flat heart has half width `b = max(2 c − k, 0)`,** where `c` is the grid cell, `L = max(log(A / (−h)), 0)` and `k = w min(√L, √π (1 + f) L / 2)`.
- **There is a `max(|x| − b, 0) / w` on its sides.** The amplitude becomes `A / (1 + 2 b / (w √π (1 + f)))`; the area remains exactly `I`, at fixed local parameters.
- **If `b ≥ c`, any emergence covers two grid cells.** Otherwise, `log(1 + t) ≤ t` and the choice of `k` limit the two sides by a Gaussian still emerging at `c`, or by a completely drowned vertices.
- **The filter works point by point, without map or neighbor.** Distances that move the relief over hundreds of kilometers retain their double precision.
- **Outdated versions of the cords:** `log/spec-relief-tectonique-historique.md`.

**Checking of 2026-10-31:** three ribs of seed 0 at 20, 8 and 3 km, plus 60 m, in `x64/Codex/rendus/avant/` and `apres/`; no dotted observed after filtering.
- **At 3 km:** maximum deviation of 1/255 per channel; at 60 m, same boundary except for a pixel of foliage, without visible change of silhouette.
- **At grid cell zero, the profile is identical.** On 200 000 profiles, the emerging width or submersion is respected; digital integration preserves the area to 3,5 × 10⁻¹² close relatively.
- **To be judged in flight:** `tools/tests/2026-10-31-cordons-emergence.txt`.
- **The flat coastal plains, calm:** less than 12 km from the shore, the relief left at noise and the badlands fall to 10 % of theirs: laid before, they screened the coast of ponds below the sea level.

## The link with erosion: the level 0

**The map shows what the 0 level expects,** on the `erosion-niveaux` branch (`recherche-relief.md`, 6.5).

| Entrée | Where | What it is |
|---|---|---|
| U-Uprising | tranche 3, z; `cp.uplift(p)`  | mm/an, the same shape as the rise of each form, a part of its convergence: 4 % under a mountain range, 3 % under an arc, 12 % in a collision, 3 % under a plateau; shoulders and a dome on rifts; negative in the forelands, −2 % of convergence, and grabens, −10 % of divergence; 0 on cratons and old chains |
| Erosion K | band 4, x; `cp.erodibility(p)`  | relative, by rock: basement 0,25, old chain 0,45, volcanic 0,6, young chain 1, sediments 1,6, up to double in soft sediments; several orders of magnitude on Earth (Stock and Montgomery 1999), a factor ten here, the level 0 caling its constant |
| Form before erosion |  `ReliefElevation(p, false)` ; `cp.elevation(ctx, p, valleys=False)`  | large shapes and detail, without valley; filtered to the grid cell of the level 0 by `Ctx(maille)`  |
| Basic level | the sea, `elevation < 0`  | terminal lakes of level 0 in addition |

**Orders of magnitude, seed 0:** the elevation exceeds 1 mm/an on 9,5 % of the land, 1,7 mm/an in median above 2,5 km, 12 mm/an at most; erodibility is 0,25 on the shields, 1,6 on half of the land.

**The connection, to do on `erosion-niveaux`:**
1. **At startup, after the tectonic map:** `Tectonics::Map` keeps its five slices in memory up to the level 0; it reads U and K there, without reread the file.
2. **On the grid of the level 0,** 20 to 40 km: the pre-erosion form filtered to two of its grid cells, U and K in B-spline; analytical equilibrium (Tzathas 2024), Priority-Flood, drained area, integral χ along the grid, two or three times.
3. **The eroded relief replaces the large forms on the lands,** above two of its grid cells, read in B-spline; the detail extinguishes at the bottom of its valleys. `ReliefElevation(p, true)` makes it, `(p, false)` never: the 0 level does not read its own outputs.
4. **The budget:** the level 0 is added to the second of the map; a cache per seed if it exceeds it.
5. **The search scripts,** `tools/hydro/level0_*.py`, take `cp.uplift` and `cp.erodibility` instead of the raise taken from complexplanet.

**Distance to the front, vivid to the axis:** near the border, the distance signed, exact across it; further, the single distance. The sign changes sign at triple junctions: possible short false axes, on 40 km.

## The detail, step 3

**Twelve octaves from 50 km to 13,5 m, lacunarity 2,11, amplitude the relief of the map.** Each octave nourishes two forms, mixed by relief and youth:
- **the chains,** above 300 to 1 200 m of relief: 1 − |n| less its average, ridges and valleys in V; each octave weakened in the valleys of the previous; sharp ridges on the young, rounded on 0,3 of noise on the old;
- **their folds,** the widest octave of the strings within 500 to 800 km of the border, a pleated belt rather than a fingerprint:
  - **the peaks along the level lines of the distance to the border,** the sinuses that the octave reads as a noise, as well as the mean |n|;
  - **two sets, of 26 and 52 km of difference,** which alternate according to a noise of 120 km: the spacing varies from single to double, along the folds and across; where one set is extinguished, the crests of the other take over, in stage. Their mixture keeps the standard deviation of one;
  - **offset across** the same noise, 0,35 times the short play gap, of 150 and 50 km: the folds curve and shift, never steeper than the distance, so that no ridge closes;
  - **their amplitude by segments,** 1 + 0,8 tanh(1,5 z) on a noise of 50 km, 1 on average: strong folds, others barely marked, their ends plunging. It weighs the weight of the octave, not its value: a weak fold is not a plateau;
  - **under them,** the peaks of the next two octaves reduced by half where the folds are full, the valleys between the chains where the next octave weakens;
  - **they fade** where the distance stops growing, halfway between two borders, and where it turns short, at the change of the closest border: under half of its slope, measured on the B-spline, nothing more;
- **the hills and the plains,** elsewhere: the gradient noise itself.

**Erosion without erosion:** each octave is weakened by the slope of the previous ones, 1 / (1 + k s²), k = 1,5 on hills, 0,5 on chains. A noise with analytic derivatives, `RlGradientNoiseD`, added to `Noise.hlsli`.

**Oriented strings:** the three widest octaves, the first out of the folds, read a left point of 5 km, so that no ridge closes on itself, and stretched along the strings.
- **Stretching:** the point is lifted out of the sphere of a measure of distance smoothed at the border; the noise varies 2,5 times faster across than along. No shear where the steering wheel turns.
- **Duplicate, from the card to noise:** the smoothed distance (`TectonicSample.along`), the lift and the phase of the folds. Floating, their hundreds of km advanced by steps of a few cm, which the rise and the folds returned to the ground: walls of 8 to 17 cm every half meter, on the chains, seen at 1 m. The rise follows a quintic rather than a tanh, which has no double: same slope at the border, same height, reached at 15/8 of 450 km.
- **It extinguishes at 450 km from the border:** further, the noise is isotropic. The sutures do not orient anything: around a point, the stretch drew rings.

**The platforms:** mesas, their relief of 350 m on 12 km set in steps of 120 m, each counterstep of 10 to 60 % of the step, drawn by step: cliffs and slopes. **Soft sediments:** fine ravines, 45 m from 600 to 14 m, badlands.

**`gRoughness`,** of the same fields: 0,1 the plains, 0,35 the hills, 0,5 the old chains, 0,6 the mesas and badlands, 1 the young chains.

**The valleys:** none is dug. The valleys in zeros of a noise drew looped channels; the rivers will be those of the level 0. `ReliefElevation(p, false)` gives the same relief.

**What holds:** the `ReliefElevation(p)` and `(p, valleys)` interface; the doubles for octave cutting; the filtering by `gMaxFrequency` and the rounding of peaks; no octave under two grid cells; the smoothly capped summits above 8 km.

## The port CPU and the cache

**The engine writes its card at each start, next to the executable:** `x64/Release/tectonique-<graine>.bin`, 65 MB, a `EXOTECT2` header and then the five slices at full resolution (`Tectonics::Save`).

**`tools/hydro/cp.py` reads it again:** the same reading in B-spline, the same mixture of faces, the same profiles and the same noise, in float64. `EXOLUNE_TECTONIQUE` gives another path.
- **Why this choice:** port the map calculation to numpy would double 900 lines of C++ and diverge at the smallest rounding. The cache is the engine card itself.
- **The limit:** a seed that the engine never calculated has no map; the port says it.
- **Checked the 2026-10-31 after emergence filtering:** against the engine planet map, 600 grid cells near the center of the faces: median deviation 6,48 cm, p99 2,17 m, maximum 13,39 m; same deviation before filter; `x64/Codex/rendus/apres/portage.json`.
- **The interface kept:** `Ctx`, `elevation(ctx, p, extra, valleys)`, `window`, `latlon`, `move`; in addition, for the level 0, `uplift(p)` and `erodibility(p)`. `extra` women `elev`, `norivers`, `large`, `relief`, `youth`, `strata`, `axis`, `roughness`. `CUR_SEED` becomes `PLANET_SEED`. The scripts of the erosion research that read `CUR_SEED`, and those of `tools/hydro` and `tools/cotes` that read the parts of the old relief, are to be adapted.

**The planet map is calculated after the tectonic map,** which it reads (`D3DApp::CreateTectonicMap`).

## Measures

**The orders of magnitude,** port CPU, 400 000 points, grid cells from 2 km, vertices and pits refined on 80 km to 500 m:

| Measure | Second pass | Before | Target |
|---|---|---|---|
| Land, seed 0; seeds 1 and 2 | 32,9 %; 34,0 and 30,5 % | 33,0 %; 33,8 and 30,4 % | 30 to 45 %, Earth 29 % |
| Mode and median of land | +125 m, 379 m | +125 m, 363 m | Earth: median to 400 m |
| Ocean mode and median | −4 525 m, −4 452 m | −4 525 m, −4 445 m | −4 to −5 km |
| Summits of the 12 highest chains | 6,9 to 7,6 km | 6,6 to 7,6 km | 6 to 8 km |
| Pits, the deepest 8 | −9,1 to −10,1 km | −9,0 to −10,5 km | −8 to −10 km |
| Above 3 km | 2,0 % | 1,9 % | Earth: 1,6 % |
| Rifts, in part of border cells, seeds 0, 1, 2 | 2,5, 8,6, 2,5 % | 15,7, 17,6, 10,9 % | few percent |

- **The plates and continents remain the same as before:** 0,2 % of cells change plate, 0,7 % of crust, the rifts open above all; the places of tests keep their meaning.
- **Why 33 % of land:** 43 % of continental crust, of which the plateaus, slopes and low basins drown a quarter, as on Earth (41 % for 29 %). The hypsometry remains bimodal, towards +0,1 and −4,5 km.
- **The narrow seas take fast rifts:** plates diverge here from 10 to 60 mm/an, much more than the land rifts, some mm/an.

**Time and memory of the tectonic map,** at rest:
- **Time:** 0,81 to 0,86 s under the engine, on three starts, against 2,53 s for the first version; 0,88 to 0,90 s off the engine. At the bit close from one calculation to another.
- **The memory GPU:** 37,9 MB, against 49,5: three slices at full resolution, the slices of views at quarter.
- **The peak on the CPU:** 440 to 500 MB during calculation, rendered after; to be monitored for the bodies of a system calculated in parallel.

**The verification set:** the compilation without error or new warning; the eight control views, `rend_tecto.ps1`, and their reference `base_tecto` in the session captures; the flying views of `tools/tests/2026-10-31-relief-tectonique.txt`; the `tecto4_planche.jpg`, and `tecto4_portage.jpg`, the shaded reliefs of the port at the same places.

**The eight control views,** on the seed map 0, height above ground:

| View | Height | Location, pitch, heading | Soleil |
|---|---|---|---|
| Orbite, the great continent | 10 000 km | −0,5, −18,225, 90°, 0° | 10, −5 |
| Above the cumulus, a plain | 10 km | 38,1445, 103,5352, 35°, 90° | 38,1445, 128,5352 |
| Scattered cumulus clouds and their shadows, on hills | 30 km | −27,875, −0,375, 45°, 270° | −25, 30 |
| A flat coast, tropical, sea view | 60 m | 16,70628, −89,28981, 6°, 9° | 30, −70 |
| A wooded slope at 590 m, 30 m above the summits: at 30 m from the ground, the camera is in the crowns | 60 m | −8,44835, 118,48865, 8°, 163° | −20, 130 |
| The collision chain, at 4 700 m | 1 km | −7,37725, 116,87998, 10°, 108° | −20, 100 |
| Mesas of a platform | 1,5 km | 15,625, 95,625, 12°, 90° | 15, 70 |
| Pebbles and tufts at the foot of a mesa | 1,2 m | 15,62455, 95,6292, 25°, 90° | 15, 70 |

**The start of the game:** 300 km above −12°, 116,875°, the collision chain on the horizon to the north; the sun at −5°, 125° (`main.cpp`, `Settings.h`). The globe of the launcher: −0,5°, −18,225°, the sun at 10°, −5°.

## Known defects

- **The valleys between 20 km and 1 km:** none is dug; the chains have their folds and their cols, no network that drains them. The 0 level and its fine valleys, stages 4 and 7.
- **The estuaries at the river mouths:** the coastal rias are drowned valleys drawn by the noise; the real estuaries await the rivers of the 0 level.
- **Plains follow the distance to the nearest border:** the sharpest rafters, near triple junctions, fade away; around a very curved border, its contour lines still draw concentric arcs, and a strong fold may serpentine there.
- **The very low coastal plains,** below 0,5 m/km, still have basin below sea level inside; the 0 level will drain them.
- **The `relief` view shows the facets of the mesh** on the sharp profiles seen from orbit; the relief of the game does not show them.
- **Not yet abyssal hills oriented by age:** volcanoes are made, `spec-volcanisme.md`.
- **The reference of the quality benchmark is no longer valid:** its places are those of the old relief; it is re-registered on request.
- **The memory peak of the calculation,** 0,5 GB: for a system calculated in parallel, to reduce or spread.
- **No valleys dug:** waiting for level 0, `valleys` does not change anything.

## The plan in stages

| Stage | Contents | Status |
|---|---|---|
| 0 | The ruler of the card that carries the geometry; this spec | Done on 2026-10-31 |
| 1 | The tectonic map and its diagnostic views; continents by location, margins | made the 2026-10-31, to be judged in flight |
| 2 | The large forms: oceans, margins, pits, chains, plateaus, rifts, transforming, old chains | made the 2026-10-31, to be judged in flight |
| 3 | Modulated detail: oriented chains, slope erosion, mesas, badlands, `gRoughness`  | made the 2026-10-31, to be judged in flight; quality benchmark to be redone on new views |
| 4 | The 0 level on the tectonic elevation, at analytical equilibrium; its eroded relief above two cells | ready entries on 2026-10-31; to be done on `erosion-niveaux`  |
| 5 | Hot spots, volcanic cones, abyssal hills | volcanoes made the 2026-10-31, `spec-volcanisme.md`, experiment `piste/volcanisme` ; abyssal hills to do |
| 6 | Costs by type of margin | made the 2026-10-31 by the slope of the margin; the estuaries with the rivers of the level 0 |
| 7 | The fine valleys: Dendry by tiles, hung at level 0 | To be done |
| 8 | A simulated story in Cortial style, if the snapshot seems too regular | if necessary |

The detail of each step: `recherche-relief.md`, section 7. The new rules are in `principes.md`.
