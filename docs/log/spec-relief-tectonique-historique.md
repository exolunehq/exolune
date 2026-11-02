# Background: tectonic relief

**The outdated sections of `../spec-relief-tectonique.md`, for memory.** Nothing here describes the present state.

## The cords before filtering their emergence, 2026-10-31

- **Third pass:** placed on the contour of the noise-filled shore, they followed its angles and rias; in a ria narrower than themselves, their two sides joined in a flat block at 3 m.
- **Fourth pass:** the smoothed shore carries the arches; the ridge rises from the relief below it, so that the thin octaves no longer cut it to the sea.
- **Total width alone was filtered:** at least two grid cells, amplitude lowered proportionally.
- **Remaining defect:** towards 20 km of altitude, the emerged ridge occupied less than a grid cell and was drawn in white dotted; continues at 8 and 3 km.
- **Replaced by filtering the emerged part,** described in `../spec-relief-tectonique.md`.
- **Previous measurements of the port,** on 600 grid cells near the center of the faces: median 6 cm, p99 1,8 m, maximum 13 m on the wall of a pit; the first version, 6 cm, 1,6 m and 3,4 m.

## Steps 1 to 3 as you do the 2026-10-31, before the second pass

Fixed the same day: the ridges, the rifts, the chains, the start budget, the entries of the level 0 (`../spec-relief-tectonique.md`). The measures and the defects of then.

**The storage of then:** four slices per face on the GPU, 49,5 MB; the slice 3 carried an indicative elevation, that of the only border nearest, and the distance to the edge of the continents up to 3 000 km. The file, `EXOTECT1`, these four slices.

**The calculation of then:** propagations on a pile, one by one along the critical path; regional fields at full resolution; two propagations of ridges before polarity; cratons on continents according to active margins.

### Measures

**Orders of magnitude,** port CPU, seed 0, 400 000 points, grid cells of 2 km:

| Measure | Tectonic relief | Target |
|---|---|---|
| Terres | 33,0 %; seeds 1 and 2: 33,8 and 30,4 % | 30 to 45 %, closer to Earth, 29 % |
| Land mode | +125 m, median 366 m | Earth: median to 400 m |
| Oceans Fashion | −4 625 m, median −4 447 m | −4 to −5 km |
| Summits of the 12 highest chains | 6,8 to 7,9 km | 6 to 8 km |
| Pits, the deepest 8 | −9,4 to −10,5 km | −8 to −10 km |
| Above 3 km | 1,9 % of area | Earth: 1,6 % |

- **Why 33 % of land:** 44 % of continental crust, of which the plateaus, slopes and low basins drown a quarter, as on Earth (41 % for 29 %).
- **Hypsometry is bimodal,** to +0,1 and −4,6 km: `tecto3_hypsometrie.png` in session captures.

**Time:**
- **The tectonic map:** 2,5 s at startup, against 1 s in the first version: nine propagations instead of four, two border rankings. Memory GPU 50 MB, against 32.
- **The GPU calculation of the terrain,** moving camera, terrain recalculated at each frame, even six views: 0,3 to 0,7 ms at low and medium altitudes, versus 0,5 to 1,3 ms; at ground level, 0,7 to 2,5 ms depending on load, versus 3,9. The locations of the reference views are now at sea, except the orbit and ground of `macro`, in the forest.
- **The map of the planet:** 18 ms on the GPU.

**The check set:** the compilation without error or new warning; the flying views of `tools/tests/2026-10-31-relief-tectonique.txt`; the board `tecto3_planche.jpg`.

### Known defects

- **The coasts are smooth between 50 and 5 km** on the coastal plains: the detail is low, the coast follows the threshold of a smooth field.
- **The rifts are numerous,** 17 % of the borders, and their grabens often drowned in narrow seas with regular walls.
- **The chains at 300 km are wavy ridges,** somewhat marbled; no network of valleys drain them.
- **The `relief` view shows the facets of the mesh** on the sharp profiles seen from orbit; the relief of the game does not show them.
- **Not yet hot spots, volcanic cones, abyssal hills oriented by age.**
- **The reference views of `base_lumiere` fall into the sea:** new control views on land are needed; the reference of quality benchmark is no longer valid.
- **The start time:** 2,5 s for a planet; for a system, the parallel calculation of the bodies remains to be done.
- **No valleys dug:** waiting for level 0, `valleys` does not change anything.

## The step 1 as made the 2026-10-31, before the correction of the continents

The plates were entire, all continental or all oceanic; each coast was a plate boundary. Fixed the same day: continental crust by location, passive and active margins (`../spec-relief-tectonique.md`, tectonic map).

### The tectonic map, first version

**In place, the relief does not read it.** It is calculated at startup and is shown in six diagnostic views.

#### The calculation, `Tectonics.cpp`

**One card per celestial body:** `Tectonics::Build({ seed, radiusKm })`. The same body gives the same card, to the bit close; the planet takes the seed of the relief, `CUR_SEED`.

1. **The grid:** the cube of the planet map, 6 × N², N the power of two that gives texels of 20 km about. For the planet, 512².
2. **Costs:** gradient fBm of noise, from 2 000 to 60 km, in exp(3 fBm): half to twice the median at one standard deviation.
3. **The plates:** 12 to 20 germs, each the furthest from the others among 24 drawn. Competitive growth at noise cost, speeds of 0,4 to 2,5: plates of 0,3 to 17 % of the surface, irregular contours, never arcs of large circle.
4. **Continental or Oceanic:** plates in a drawn order, continental as long as their share remains under a target of 30 to 40 %.
5. **Motions:** an Euler pole drawn on the sphere; 40 to 100 mm/an to 90° of the pole for an oceanic plate, 10 to 40 for a continental plate.
6. **Boundaries:** any cell adjacent to another plate. The normal between the cells of the two plates on 4 pas; the relative velocity (ω_a − ω_b) × p, projected on the normal, averaged along the border on about 100 km, on both sides.
   - **transformer** if the normal component is less than 40 % of the relative speed;
   - **convergent:** subduction ocean subcontinent, ocean under ocean, collision of two continents;
   - **divergent:** ridge if one side is oceanic, rift between two continents.
7. **Polarity, a choice per pair of plates:** the oceanic under the continental; of two oceanic, the oldest crust; of two continents, the one that advances most into the other.
8. **Ocean floor age:** the distance to the nearest plate ridge, at half-average plate expansion speed; 200 Ma at most, and on a plate without a ridge.
9. **The ancient sutures:** each continent cut into 1 to 8 cratons by the same growth, one by 2 % of the surface; a suture between two cratons, of an age drawn from 100 to 1 000 Ma.
10. **Distances:** a propagation of the nearest germ, that of the 0 level, from the boundary point between two cells; smoothed on two texels.
11. **The indicative elevation,** in mm/an, according to type, polarity, convergence and distance:
    - subduction: pit on the plunging plate; mountain range of 150 to 400 km, or island arc, on the other;
    - collision: chain on both plates, foreland basin in front;
    - rift: grave between two shoulders; elsewhere, 0.
12. **Rock, by class:** oceanic crust; volcanic, on arcs; young pleated, where the rise passes 1 mm/an; sediments, forelands, rifts and platforms; old pleated, less than 150 km from a suture; basement, in spots drawn by a noise.

**Three parallel propagations,** each on its own thread: the cratons and their sutures, the dorsals, the borders. The rest, cell by cell on all wires.

#### Storage, `Tectonics.hlsli`

**An array of two cubes RGBA16F, half-maps, `t18`:**
- **cube 0:** distance to the nearest plate boundary (km), positive on a continental plate, negative on an oceanic one, which passes through 0 only at the margins; convergence through it (mm/an), negative when the plates diverge; elevation (mm/an); age of the ocean floor (Ma).
- **cube 1:** distance to the nearest suture (km); its age (Ma); two classes, read without filter by `Gather` to mip 0: the rock, plus 8 on a continent; the plate, plus 32 times the type of the nearest boundary, plus 256 if the plate sinks under it.

**The sign by the crust, not by polarity:** a distance signed by polarity would jump from −d to +d between two boundaries, and any filter would invent a false zero there. Signed by the crust, it is continuous everywhere; the polarity passes through the classes.

**The resolution, 512² for the planet:** 25 km at the center of a face, 11 km at the corners, 20 km on average.
- **What she wears:** shapes of more than two texels, 40 km; large shapes make it more of 50.
- **The sharp edges come from analytical profiles of the 2 step,** laid on smooth distances, which interpolate to a fraction of texel close.
- **1 024² would not work:** four times the memory and time, for scales that the noise does better. It would no longer hold the budget of an entire system.

#### Diagnostic views

**By `MYPLANETENGINE_VIEW`, by name in batch mode, or at the end of a test line.** Without light, air, or clouds; they are read from orbit at 500 km.

| Name | What it shows |
|---|---|
|  `plates`  | each plate its colour, darkened on the oceans; their borders in black |
|  `boundaries`  | the type of the nearest boundary on 250 km: red, subduction under a continent; orange, under an ocean; magenta, collision; cyan, ridge; yellow, rift; green, transforming. Twice darker on the sinking plate; brown sutures |
|  `boundarydist`  | distance signed up to 3 000 km, orange on continents, blue on oceans; a line every 250 km |
|  `crustage`  | the age of the bottom, red to dorsals to purple at 200 Ma; on continents, sutures, light at 100 Ma, dark at 1 000 Ma |
|  `rocktype`  | oceanic crust night blue, volcanic red, young brown pleated, sediments sand, old olive pleated, pink base |
|  `uplift`  | the rise, orange up to +6 mm/an, blue up to −6 |

**To be judged in flight:** `tools/tests/2026-10-31-tectonique.txt`, each view of the orbit then to 500 km on a marked line.

#### Measures

- **Time:** 0,93 to 0,99 s at startup, at the title “tectonic … ms”; 0,89 to 1,0 s off engine. Measured with other sessions on the machine.
- **Memory:** 32 MB on the GPU, plus 32 MB of send buffer, rendered at startup. A peak of 190 MB on the CPU during calculation, rendered after.
- **Determinism:** two calculations, the same file bit by bit.
- **Game rendering:** bit-to-bit identical across all six control views, from orbit to ground.
- **The plates, on three seeds:** 15, 15 and 19 plates, from 0,3 to 17 % of surface; 31, 35 and 38 % of continental crust.
  - **Against Bird 2003:** the largest earth plate, the Pacific, is about 20 %; ours are capped at 17 %.
  - **The microplates are missing:** Bird counts tens under 1 %, the snapshot has only 2 or 3.
- **Boundaries, seed 0, in part of border cells:** subduction under a continent 41 %, under an ocean 4 %, collision 1 %, ridges 23 %, rifts 1 %, transforming 29 %.

#### The budget of a solar system

**Time and memory follow the surface:** the grid keeps the texels of 20 km, its size follows the radius.

| Corps | Grid | Memory GPU | Time |
|---|---|---|---|
| Size of Earth or Venus | 512² | 32 MB | 1 s |
| Mars, Mercury, Ganymede, Titan | 256² | 8 MB | 0,23 s |
| Moon size, Io, Europe | 128² | 2 MB | 0,07 s |

- **Target budget:** 150 MB and 2 s for the whole system. A system like ours, without the giants: two large planets, five medium bodies, five small; 114 MB, 3,5 s of calculation in the following, less 1,5 s estimated by calculating the bodies in parallel.
- **Beyond:** disk cache per seed, 32 MB per planet of the size of the Earth.
- **Not yet done:** the list of bodies in the system; step 1 calculates only one.

#### What remains uncertain

- **The plates are whole:** all continental or oceanic. No passive margin; each coast is a plate boundary. The research poses continents independent of plates, `recherche-relief.md`, 6.2, step 1: to be decided before step 2.
- **Their shapes:** irregular but often round; small spots, never elongated.
- **Some isolated transforming traits** still cut subductions, on one or two cells.
- **The classes are at texel:** seen closely, at 500 km, their limits run by 20 km. The fields, however, are smooth.
- **Age is flat, at 200 Ma,** on an oceanic plate without a ridge.
- **Time** was measured on a loaded machine; to be repeated at rest.

## 2026-10-31: the connection plan superseded by global erosion

The previous plan is preserved here; the actual connection is described in `../spec-erosion.md`.

**The connection, planned on `erosion-niveaux`:**
1. **At startup, after the tectonic map:** `Tectonics::Map` keeps its five slices in memory until level 0; it reads U and K there without rereading the file.
2. **On the level 0 grid,** 20 to 40 km: the pre-erosion form filtered to two of its grid cells, U and K in B-spline; analytical equilibrium (Tzathas 2024), Priority-Flood, drainage area, χ integral along the network, two or three times.
3. **Eroded terrain replaces the large landforms,** above two of its grid cells, read in B-spline; detail fades on valley floors. `ReliefElevation(p, true)` renders it, `(p, false)` never does: level 0 never reads its own outputs.
4. **The budget:** level 0 adds to the map's second; a cache per seed if it exceeds it.
5. **The research scripts,** `tools/hydro/level0_*.py`, take `cp.uplift` and `cp.erodibility` instead of uplift derived from complexplanet.
