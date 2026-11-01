# Spec: volcanism

Status: spec live, since the 2026-10-31. Make the 2026-10-31 on the branch `claude/volcanisme-7c3aea`, part of `bruit-propre`; experiment `piste/volcanisme`, to judge in flight: `tools/tests/2026-10-31-volcanisme.txt`. It is the 5 stage of `spec-relief-tectonique.md`, its abyssal hills excepted.

## The objective

**Volcanoes are deduced from the tectonic map:** arcs on subductions, hot spots and their chains, volcanoes of the rifts. Before, volcanism existed only as a type of rock.

- **What we see:** Stratovolcanoes in chains, in island arcs and in mountain ranges; shields, islands that wear out and sink, barrier reefs, atolls, guyots; calderas, flows, fields of small cones; traps in marches; basalts and dark ashes.
- **The model followed:** that of the card. The list of volcanoes is calculated once at startup; the relief evaluates them point by point.

## The constraints

- **Everything at start, nothing on the way** (`principes.md`): positions and shapes of volcanoes in a list, with an index on a cube.
- **A point never depends on the grid cell:** each building is a function of the point, in the reference frame of the planet; the filtering only follows the grid cell, as for the map profiles.
- **The shape before erosion:** the buildings are part of `ReliefElevation(p, false)`; erosion will dig them.
- **From the original code,** from the articles cited.

## List of volcanoes, `Tectonics.cpp`

**At the end of `Tectonics::Build`, before smoothing the fields:** the list, its index, and what hot spots change to the map. The same body gives the same list, to the bit close.

**Each volcano,** `Tectonics::Volcano`, 52 bytes: its direction, its radius, its height above the surrounding ground, its profile, its crater, the level where its summit was leveled, its reef, its field of cones, its freshness, its seed.

**The arches, on the overlapping plate:**
- **The volcanic front** where the plunging plate reaches a hundred kilometers of depth: at 140 to 230 km of the pit, around the arc of the map, 175 km in the sea, 170 to 200 km on a continent (Stern 2002).
- **Candidates:** cells at this distance from the forehead, each one carried exactly to the desired distance along the great circle that connects it to its point of forehead. None where the plate sinks flat, in sections.
- **Cleared in order of a draw:** each kept if no other is within 35 to 80 km.
- **Stratovolcanoes:** 2 to 4 km high, a quarter more in the sea, built from the foot of the ridge of the arc; a radius of 4,5 to 7,5 times the height; a crater of 0,4 to 1,1 km; 12 % collapsed into a caldera of 4 to 10 km (Crater Lake); a third with cones on their sides.
- **Behind the arc, on a continent:** fields of cones on a low shield of flows, all 180 to 300 km, to 110 km from the front (the field of Michoacán-Guanajuato).

**Continental rifts,** within 60 km of their axis, all 70 to 150 km: stratovolcanoes up to 4,5 km (Kilimanjaro), shields, calderas (Menengai), each in a field of cones.

**Hot spots:** 8 to 16 fixed plumes in the mantle, plates moving above (Wilson 1963, Morgan 1971).
- **The chain:** a volcano all 40 to 90 km in sea, 120 to 200 km on a continent; the point formed there t Ma above the plume is now turned around the Euler pole of its plate.
- **It stops** at the plate boundary, where the crust is younger than the volcano, or at the head of the plume, 30 to 130 Ma.
- **The head of the plume:** traps on a continent (the Deccan), an oceanic shelf at sea (Ontong Java).

**At sea, shields:**
- **4 to 9 km above the bottom,** most of them weak hot spots, therefore seamounts; a radius of 7 to 10 times the height; their summit at 4,5 km above the sea at most (Mauna Loa, Mauna Kea).
- **The youngest** with its summit caldera and cones.
- **The subsidence:** the plume swell decreasing and the plate cooling, 1 000 (1 − e^(−t/15)) + 6 t m, about 1 km in 30 Ma.
- **The rasement:** an island is worn by the waves, its summit at H e^(−t/4) above the sea then, then it sinks: a guyot.
- **The reef, in the tropics, within 26°:** seven times out of ten, it settles on the worn platform of the island, half the radius of its shore at 1,5 Ma, and follows the sea level as it sinks: a barrier reef, then an atoll (Darwin 1842).

**On a continent,** a caldera every 120 to 200 km during 15 Ma (from the plain of the Snake River to Yellowstone): a low dome of 40 to 70 km, a caldera of 10 to 25 km.

**In the fields of the map,** before smoothing them:
- **The plume swell** around the young chain: 0,6 to 1,3 km on 380 km on both sides, decreasing in 10 Ma; 60 % under a continent.
- **Traps:** 300 to 700 km radius, 0,8 to 1,6 km high, worn in 200 Ma; their edge in steep; their strata in steps, the mesas of the platforms (`Relief.hlsli`).
- **The ocean shelf:** a dome of 1,5 to 2,5 km, 300 to 600 km radius.
- **The volcanic rock** around each volcano and on the traps: the class and erodibility, 0,6.

**Where each volcano falls:** where the map bears its shape, brought back by the left-handed reading of the map (`RlTurbulence`, ported in C++). It falls on the shape as the shader draws it; without it, up to 30 km of deviation with the arc ridge or graben (`principes.md`).

**The index:** a cube of 64² cells per face; each cell lists volcanoes at range, 1,65 times their radius and 80 km at least. A single table: the position of the list of each cell, then the numbers.

## Buildings, `Volcanoes.hlsli`

**The shader reads the dot cell, evaluates its volcanoes.** Two structures, `t21` and `t22`, in the tectonic map table.

| Forme | Profile | Source |
|---|---|---|
| Stratovolcano | Concave sides, e^(−3x), a apron up to 1,3 radius | Karátson et al. 2010 |
| Shield | almost straight from the bottom to its wide flat top, 1 − x^1,3; its foot melted on the 40 % outside | Mauna Loa |
| Contour | elongated in a drawn direction, up to 10 % of the radius for a stratovolcano, 35 % for a shield; lobed and angular, two octaves of a noise on the circle, 12 % to a standard deviation; 30 % at most: rift zones, flows, collapses. The crater, the terrain and the reef follow it | Hawaii |
| Crater | the building drawn to a bottom, H profile (crater) − depth; a bowl, (1 − u²)² | — |
| Caldeira | a flat bottom between steep walls, 1 − u⁸, beyond 0,8 to 2,5 km radius | Crater Lake |
| Coulées | tongues of 1,5 km wide at half radius, twice as much on a shield, stretched along the slope; 40 m thick on a stratovolcano, 15 on a shield, young; they start from the third of the radius, cover half the flank, then some long reach the foot | — |
| Cones | scories, a grid cell of 2,5 km, 0,25 to 0,75 km radius, quarter highs, a crater of 0,4 radius | Wood 1980 |
| Guyot | the summit leveled at its level, flat under the sea, rounded above | — |
| Reef, atoll | laid on the contour of the building, at the level of the old shore, plus spurs and bays of a few hundred meters; a plateau at −1,5 m, from 0,25 to 0,8 km, eroded, wider windward, east of the trade winds; motus separated at +3 m, from 150 to 500 m wide, a third of the plateau windward, an eighth leeward; passes of 8 m, especially leeward; a lagoon at −12 m, 30 % more or less deep by spots | Darwin 1842 |

- **The fleece flows:** (k cos a, k sin a, r / long), a circle across, stretched along the slope, left by a wider noise so that they serpentine. Their average is the building itself: the tongues above, the ground between them below. Without it, a ring marked their departure.
- **Several volcanoes combine in smoothed maximum,** (Σ e⁴)^Z¼, like the chains of the map; the bottom of a caldera under the ground around, the lowest; the cones in addition.
- **The calm detail on the young flanks:** up to 80 % of the relief left at noise, otherwise a cordillera wrinkles the cone.
- **After the detail:** the arasement, the reef and the lagoon of the volcano that dominates the point.
- **The reef follows the building it crowns:** the same outline, read at the level of the old shore; a barrier reef, an atoll and a guyot therefore never have another shape than their volcano. Before the 2026-10-31 in the evening, a circle noise apart and a plateau of constant width, at +0,5 m: the swell discovered it, a strip of beach continuous.
- **Any profile on two grid cells at least:** the building, the crater and the cones wider and lower so, their volume kept; the flows and cones replaced by their average where the grid cell does not bear them.

**Where is the call:** `ReliefElevation`, after the ribs and before the detail, then `VolcanoFinish` after the rib cords. The settings: `VOLCANO_*` in `PlanetSettings.hlsli`.

## The materials used

**The fresh volcanic soil, `gVolcanic`, from 0 to 1:** the cone of ash and slag of a stratovolcano, the top of a shield, the flows, the cones; weighted by freshness, e^(−t/3) on a chain.
- **The path:** it replaces the `relief` field unused from `FaceVertex`, which became `volcanic`, then `geology.w` up to the pixel.
- **The rock:** the basalt, the darkest of the palette (`RockColor`).
- **Soil:** ash and slag, reflectance 0,07, on 85 % of soil; black beaches.

## The port CPU

**`tools/hydro/cp.py` reads `x64/Release/volcans-<graine>.bin`,** written by the engine on each startup, header `EXOVOLC1`; `EXOLUNE_VOLCANS` gives another path. `volcano_edifices` and `volcano_finish` follow the shader; `elevation(..., extra=True)` also gives `volcanoes` and `volcanic`.

**The gap to the engine:**
- **Against the map of the planet,** 200 texels on volcanoes, grid cells of 12 km: 0,4 cm in median, 6 cm at most.
- **On the ground under the camera,** 33 points on volcanoes, grid cells fine: 7,9 cm in median, 0,9 m at most, since the correction of `bruit-propre` (`d304da0`) and cones in double precision. The gap follows the slope, the engine giving its position to the decimeter; before them, 11 cm, 6 on soft ground and 13 on the sides, against 4 and 43 cm for the relief only away from the volcanoes.
- **The cones are placed in double precision:** at 120 km from the top of a shield, a float position advances by steps of 8 mm, and the side of a cone in stairs (`principes.md`, the precision of the scale where a quantity serves).

## Measures

**Seed 0:** 1 113 volcanoes, 15 hot spots; 697 stratovolcanoes, 352 shields, 163 calderas, 532 cone fields, 75 back arc fields; 26 atolls, 3 barrier reefs, 113 guyots. Seeds 1 and 2: 1 060 and 1 041 volcanoes, 10 hot spots.

| Measure | With | Sans |  |
|---|---|---|---|
| Startup, volcanism | 60 to 77 ms | — | on 1,0 to 1,3 s of card, machine loaded by other sessions |
| Memory GPU | +0,18 MB | 38 MB | the list and the index |
| Calculation of moving terrain, volcanic sites | 0,20 to 0,65 ms | 0,19 to 0,54 ms | +0,02 to +0,12 ms; GPU shared, to noise near elsewhere |
| Soils, seeds 0, 1, 2 | 32,8, 34,3, 30,7 % | 32,6 %; 34,0 and 30,5 % | port, 400 000 points, grid cells of 2 km |
| Median land, seed 0 | 388 m | 380 m |  |
| Modes, seed 0 | +375 m, −4 525 m | +375 m, −4 525 m | bimodal |
| Median of oceans, seed 0 | −4 430 m | −4 450 m | the swell and the plateaus |
| Above 3 km, seed 0 | 2,03 % | 1,99 % |  |
| Under a building of more than 10 m | 0,5 to 0,6 % of area | — |  |

- **The calculation without buildings:** `VolcanoEdifices` cut at its source, time and rest equal; the lands without volcanism, the map of `bruit-propre`.
- **The seeds 1 and 2:** their maps calculated by `Tectonics.cpp` out of the engine, a small session program; the same file as the engine for the seed 0, bit close.
- **The memory peak of the calculation** does not change: a few megabytes more.

**The check set:** the compilation without error or warning new; `tools/tests/2026-10-31-volcanisme.txt`; the `volcanisme_planche.jpg` board in the session notes; the shaded relief of the port around an arc volcano, its flows and its cones.

## Known defects

- **The cones and the flows are hard to see in front light:** a few tens of meters on a wooded flank. They are judged in racing light, or by the shaded relief of the port.
- **The high islands of the tropics appear pale from orbit:** the climate of the ground, not volcanism.
- **The island arcs:** near a third of their volcanoes remain under the sea, the ridge of the arc towards −1,5 km; of the underwater arc mountains, as to the Izu-Bonin.
- **Motus remain in bare sand near the water:** the beach is a band of altitude, from 5 to 25 m (`Materials.hlsli`); only a few palm trees, where the vegetation admits them. A beach by the distance to the shore, a rule of materials, would cover them with vegetation.
- **The small pebbles laid** keep the color of the regional rock, not that of the basalt (`ObjectPlacement.hlsl`).
- **The fresh flows still carry the vegetation of the climate:** the plant map does not read `gVolcanic`.
- **No clean caldera lakes:** water comes from the planet map, which fills the bowls at its grid cell.
- **No age-oriented abyssal hills yet,** nor seamounts out of the chains.

## The suites

- **The erosion,** on `erosion-niveaux`: digging the buildings, radiating ravines and barrancos; the ancient islands in amphitheatres.
- **The plants on the fresh streams:** `gVolcanic` in the placement and the canopy, together, so that a place remains the same from far and near.
- **The isolated seamounts and abyssal hills,** the rest of the 5 stage.
