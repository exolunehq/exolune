# Spec: climate

Status: spec live, since the 2026-10-31, branch `claude/climat-0e9eb5`, tag `piste/climat`. **This is the climate of the game,** without variable: humidity noise, its dry band at 24° and the regional temperature noise are removed. To be judged in flight: `tools/tests/2026-10-31-climat.txt`. The code: `Climate.cpp`, `Climate.h`, `Climate.hlsli`; the port: `climate(p)` in `tools/hydro/cp.py`.

## The objective

**The climate is calculated at startup on the geography of the planet, no longer on a noise.**
- **Why:** the old humidity was a regional noise; it placed deserts at the equator and forests behind the chains. Nothing linked rain to seas, winds or terrain.
- **The model followed:** a simple general circulation, three cells per hemisphere; a balance of the vapor that the winds carry from the seas to its equilibrium state; rain by the ascension of the air and by the relief.
- **Deserts fall towards 20 to 30°** by circulation: the descending branch of the Hadley cell diverges there, the air is dry. No band is imposed.

## The constraints

- **All at start, nothing on the way,** like the tectonic map (`principes.md`): less than 0,3 s and 10 MB per planet.
- **Deterministic seed calculation:** each pass calculates each cell from the previous pass alone; the same bit-wise file, regardless of the number of threads.
- **Climate reads the form before erosion,** the large shapes of the tectonic map, never eroded relief: the level 0 reads rain without loop.
- **From the original code,** written since the published laws cited here.

## The architecture

| Stage | Where | What she does |
|---|---|---|
| 1. Inputs | 256² per face | The large shapes, slice 0 of the tectonic map, 2 × 2 texels by cell: the ground under the air, the sea surface in the sea; the land share |
| 2. Winds | 64² then 128² | The three cells by latitude; the thermal equator shifted by 7° towards summer; the thermal depressions of the warm lands and the anticyclones of the cold ones; the wind slowed down by a quarter on earth |
| 3. Marine air | Same | A plotter carried by the winds: 1 on the sea, it fades on land in 4 days and above the chains on 1 500 m of rise; continentality is its complement |
| 4. Cold currents | Same | Ekman transport to the open, 90° to the right of the north wind, left to the south: cold water rises, up to 6 °C less, under regular winds; carried to land like sea air |
| 5. Temperatures | Same | The average of the year at sea level and half the amplitude of the seasons |
| 6. water vapor and rain | Same, seasonal | The water column carried by the wind and mixed by the whirlwinds; evaporated on the sea, fallen according to the ascendancy and the relief, recycled in part on the warm lands |
| 7. The map | 256² per face | The coarse fields in bilinear; rain distributed by the fine slopes; temperatures on the fine land |

**Two grids for the equilibrium state:** 200 km first, 300 passes for air, 400 for water vapor; then 100 km, part of this solution, 100 and 150 passes. What spreads slowly, by the mere mixing in the quiet areas, is established there in four times less passes, each four times cheaper.

**Transport, in finite volumes:** flows pass through the exact edges of the cells on the sphere, the wind of the ridge the average of its two cells, upstream; the mixture acts on the water vapor relative to what the air can hold, by the smaller of the two capacities: it never climbs a slope that the wind would not climb. Local pseudo-time steps, the largest that the output allows: the balance does not depend on it.

## The laws

| Size | Law | Source |
|---|---|---|
| Surface winds | trade winds 6,5 m/s to the west, west winds 8 m/s, polar east winds 3,5 m/s, sin 6φ; Hadley return of 3,5 m/s, converging within 4° of the thermal equator, diverging from 12 to 30° | Peixoto and Oort 1992, Physics of Climate, ch. 7 |
| Mousson | 6·10⁵ m/s by K/m to the warm, the season's deviation to the mean of its latitude smoothed on 1 500 km; turned from 55° outside the tropics, 5 m/s at most | Thermal wind, a fine choice |
| Capacity of the column | 65 mm to 28 °C, 6 % more per degree; it fades with the ground on 2 200 m; the low flow, blocked by the chains, rises only half of it | Clausius-Clapeyron; Smith 1979, blocking for a Froude number under 1 |
| Evapotranspiration | the sea column reaches half its capacity in 1 day, on a sea of at least −1,8 °C, less under the ice | — |
| Large scale rain | the column falls in 7 days, divided by exp(convergence / 1,5·10⁻⁶ s⁻¹), from 4,5 times less to 4,5 times faster; the rate divided by 1 + descent / 0,03 m/s leeward | the residence time of the vapor, 8 to 9 days on Earth |
| Orographic rain | 20 % of what the rise condenses, rise / 2 200 m; excess over capacity falls in 5 hours | the model of ascending slope |
| Recycling | a third of the rainfall from the warm lands evaporates again | Eltahir and Bras 1996 |
| Mixture | 6·10⁵ m²/s, from 0,4 times at the equator to 1,4 times towards 50°, the tracks of depressions; 3·10⁵ for marine air | Middle latitude vortices |
| Temperature | 28 − 52 sin²φ at sea level, the law of before; more the cold of currents; less 12 sin²φ (continentality − 0,6) on land | the old law, without its noise |
| Seasons | 1 + 5 sin²φ on the sea; on land, the adjustment on TerraClimate, 3,5 + 18 sin²φ, at the average continentality 0,6, up to 1,5 times indoors |  `tools/saisons_terre.py`  |
| Cold currents | the rise of Ekman times the wind regularity, 1 under trade winds, 0,4 beyond 42° | Ekman 1905; trade winds blow a quarter 80 % of the time |

## The Outings

**Two RGBA16F cubes of 256² per face, 9 mips, 8,0 MB on the GPU** (`Climate.hlsli`, `t20`), read in hardware filtering, continuous between faces. It is data, never geometry.

| Cube | x | y | z | w |
|---|---|---|---|---|
| 0 | annual rainfall (mm) | average annual temperature at sea level (°C) | half-season range (°C) | share of rainfall in the warm half of the year |
| 1 | moderate wind east (m/s) | average wind north (m/s) | continentality, 0 at sea to 1 where the marine air does not reach | cooling of the sea by cold currents (°C, ≤ 0) |

**On the CPU:** `Climate::Build(tectonique, rayon)` reads the card in floats; `Climate::At(carte, direction, champs)` reads it in bilinear, the texels beyond an edge is taken on the neighboring face.

**The file:** `x64/Release/climat-<graine>.bin`, 12,6 MB, the `EXOCLIM1` header, the seed, the size, 8 fields, 6 faces, then the floats, face by face, row by row. `EXOLUNE_CLIMAT` gives another path to the port.

## The interface for erosion

- **Rainfall at a point:** `cp.climate(p)["precipitation"]`, in mm per year, for directions `p` (n, 3); or `Climate::At` on the map stored in memory. `cp.humidity(P)` gives the moisture of materials.
- **The ground temperature:** `temperature − 5 × altitude (km)`; in the month `t` of the year, plus `amplitude × sin`, summer north to the middle of the year. Snow material falls below −2 °C of annual average.
- **Seasonal rainfall:** `summer`, its share in the warm half.
- **No loop:** climate reads only the large shapes of the tectonic map; the eroded relief of the 0 level does not change the rain that carved it.
- **Keep the map in memory:** `D3DApp::CreateClimateMap` throws it after sending to GPU; level 0 will keep it, like the tectonic map.

## Consumers

- **Materials,** `GroundMaterials`: temperature is that of the map at sea level, minus 5 °C/km, minus 8 °C per unit of slope towards the pole, plus the noise of the snow line; humidity is the log of precipitation, from 100 to 3 000 mm, plus their variation under the map, `LocalRain`.
- **`LocalRain`:** the map bears what exceeds two of its cells, 100 km; a noise gradient of 100 to 6 km, standard deviation 0,08 in humidity, does the rest, like the detail of the relief under the tectonic map. What the pixel does not show expands the boundaries of grass and sand (`SpreadStep`).
- **Plants,** `PlantClimate` and `VegetationAt`: same fields; half the amplitude of the seasons comes from the map, no longer from latitude alone.
- **Sea:** the color of the water follows the temperature of the map; cold currents green it.
- **The ship:** the temperature of the canopy glass, that of the map at sea level minus 6,5 °C/km; the cube of noise that it cooked at startup is removed.
- **Clouds:** their weather map is calculated on the climate map and relief, from the 2026-10-31 (`Climate::Weather`, `spec-nuages.md`, the weather map).
- **`ClimateNoise` remains,** for texture variations and regional shade.

## Diagnostic views

| Name | What it shows |
|---|---|
|  `precipitation`  | annual rainfall, in log: brown below 100 mm, sand, pale green at 500 mm, green, brownish at 2 000 mm, blue beyond 4 000; sea paler |
|  `wind`  | the average wind: its direction in hue, is red, north yellow-green, west cyan, south purple, brighter with speed; an arrow per cell of about 600 km |
|  `temperature`  | the existing view, the ground temperature of materials, from −30 to 40 °C, in gray |

**A seed apart to compare:** `MYPLANETENGINE_SEED` changes the tectonic map and climate; the noise of detail keeps `PLANET_SEED`.

## Measures

**Time and memory,** for the engine, on a machine loaded by other renderings, the tectonic map there taking 0,94 to 1,04 s against 0,85 at rest:
- **Time:** 0,22 to 0,24 s, against 0,33 s with a single grid of 400 passes.
- **Memory GPU:** 8,0 MB; file, 12,6 MB.
- **Bit-by-bit** from one calculation to the next.

**Convergence,** against 1 500, 2 000, 800 and 1 200 passes: humidity p99 0,019, at most 0,067; temperature p99 0,07 °C.

**Land precipitation by latitude band,** mm, port, three seeds:

| Band | Seed 0 | Seed 1 | Seed 2 | Earth, approx. |
|---|---|---|---|---|
| 0 to 10° | 2 167 | 1 946 | 2 293 | 2 000 |
| 10 to 20° | 1 222 | 1 059 | 1 170 | 1 100 |
| 20 to 30° | 596 | 530 | 520 | 600 |
| 30 to 40° | 615 | 714 | 605 | 600 |
| 40 to 50° | 542 | 584 | 743 | 600 |
| 50 to 60° | 417 | 367 | 504 | 500 |
| 60 to 75° | 161 | 193 | 203 | 300 |

- **Deserts, under 250 mm:** 28,5, 27,8 and 27,6 % of land; 33, 45 and 46 % of the band from 20 to 30°, 2, 3 and 1 % of the band from 0 to 10°. The average of the land: 879, 888 and 940 mm.
- **Extrems, seed 0:** more 4 000 mm on 2,0 % of lands, more 6 000 on 0,5 %, at most 15,6 m windward of equatorial chains.
- **The places typed, seed 0:** inner desert 20 mm to 25,3° 56,3°; coastal desert on cold current 77 mm to 18,3° 37,8°, the sea 4,6 °C colder; monsoon savanna 754 mm, 99 % in summer, at 19,8° 99,8°; equatorial plain 7 730 mm to −7,8° −37,3°; continental steppe 213 mm, seasons of ±15,6 °C, at 41,8° −22,3°; winter rainfall, 737 mm, 3 % in summer, at 28,3° −42,3°.
- **The rain shadow:** a chain of 2,5 km under the trade winds, near the start of the game, 2 937 mm windward to −12,4° 112,1°, 61 mm leeward to −11,8° 110,9°.

**The verification set:** the control views of the relief spec and the climate views rendered without window, before and after; the `climat_planche.jpg` board in the session notes; the global maps of the port, three seeds.

## Known defects

- **The sea wind remains uniform:** the chart carries the wind, the sea does not read it yet (`principes.md`, the sea).
- **The extremes windward of the equatorial chains** exceed those of the Earth: 15,6 m at most, against 8 to 12 to 50 km.
- **Highlands are dry:** 136 mm median above 2 km, compared to 200 to 500 on Earth.
- **The zonal law of temperature is the same as before,** cold: snow at sea level from 50°. Unchanged, since out of the subject.
- **The variation under the map is a noise,** not the fine slope of the relief windward.
- **The locations of two control views have changed climate:** the tropical flat coast, 16,7° −89,3°, is a coast leeward, 250 mm; the mesas, 15,6° 95,6°, a monsoon savannah, 919 mm.

## The plan in stages

| Stage | Contents | Status |
|---|---|---|
| 1 | The climate map, its laws, its views, its port; the materials, the plants, the sea and the ship connected | made the 2026-10-31, to be judged in flight |
| 2 | Clouds on climate: the weather map calculated at startup on its fields | made the 2026-10-31, to be judged in flight; tag `piste/nuages-climat`  |
| 3 | The wind of the sea from the map | To be done |
| 4 | Rain under the map by the fine slope windward, instead of a part of the noise | if the flight requires it |
| 5 | Level 0 reads rainfall and temperature: rivers and glaciers | session erosion |
