# Spec: volcanism

Status: active. The tectonic volcanism layer dates to 2026-10-31. The current flank review uses [the 2026-11-20 flight route](../tools/tests/2026-11-20-volcans-flancs.txt). This layer implements stage 5 of `spec-relief-tectonique.md` apart from abyssal hills.

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
| Scoria cones | Asymmetric vents concentrated along fissures, with rounded aprons and occasional breaches | [USGS Mauna Kea field survey, figure 23](https://pubs.usgs.gov/pp/1557/report.pdf) |
| Guyot | the summit leveled at its level, flat under the sea, rounded above | — |
| Reef, atoll | laid on the contour of the building, at the level of the old shore, plus spurs and bays of a few hundred meters; a plateau at −1,5 m, from 0,25 to 0,8 km, eroded, wider windward, east of the trade winds; motus separated at +3 m, from 150 to 500 m wide, a third of the plateau windward, an eighth leeward; passes of 8 m, especially leeward; a lagoon at −12 m, 30 % more or less deep by spots | Darwin 1842 |

- **The fleece flows:** (k cos a, k sin a, r / long), a circle across, stretched along the slope, left by a wider noise so that they serpentine. Their average is the building itself: the tongues above, the ground between them below. Without it, a ring marked their departure.
- **Several volcanoes combine in smoothed maximum,** (Σ e⁴)^Z¼, like the chains of the map; the bottom of a caldera under the ground around, the lowest; the cones in addition.
- **The calm detail on the young flanks:** up to 80 % of the relief left at noise, otherwise a cordillera wrinkles the cone.
- **After the detail:** the arasement, the reef and the lagoon of the volcano that dominates the point.
- **The reef follows the building it crowns:** the same outline, read at the level of the old shore; a barrier reef, an atoll and a guyot therefore never have another shape than their volcano. Before the 2026-10-31 in the evening, a circle noise apart and a plateau of constant width, at +0,5 m: the swell discovered it, a strip of beach continuous.
- **Filter each profile at its sampling scale.** Major buildings and craters widen and lower across two cells. Unresolved flows approach their average. Flank cones use the filter below.

**Where is the call:** `ReliefElevation`, after the ribs and before the detail, then `VolcanoFinish` after the rib cords. The settings: `VOLCANO_*` in `PlanetSettings.hlsli`.

## **Flank scoria cones, 2026-11-20**

- Use the existing 2.5 km cell to propose a seeded vent. Evaluate density at the vent's fixed centre. Favour two fissure directions and keep a 32% background density beyond their corridors. Fade the field beyond 0.60 edifice radii. It ends at 1.15 radii. Wide summit calderas suppress the neighbouring vents.
- Draw equivalent radii from 0.18 to 0.86 km with a bias towards smaller vents. Use 190 to 370 m of rise per kilometre of radius, scaled by the edifice's freshness. Orient the ellipse along an individual blend of rift and downhill directions. The elongation reaches 1.54 with constant footprint area.
- Round the summit and grade the toe into the parent slope. Displace the crater off-centre and vary its radius from 16% to 38% of the cone radius. Lower a downhill angular sector on some larger openings. The opening widens into the apron and stays within the positive deposit.
- Widen the narrow axis to two sampling cells as needed and reduce the rise by the area ratio. The crater and breach blend into the filtered flank as the rim becomes unresolved. The field blends to its expected elevation over the 417 to 833 m cell interval, using a 32.5 m km² mean cone volume before the freshness scale.
- The footprint and its blend fit the existing nine-cell neighbourhood. The CPU terrain port uses the same rule. [Before-and-after flight route](../tools/tests/2026-11-20-volcans-flancs.txt)
- Mauna Kea's photographed flank shows vents of different sizes along fissures. A LiDAR study of the Chaîne des Puys documents elongated and asymmetric outlines. [USGS aerial photograph and field survey](https://pubs.usgs.gov/pp/1557/report.pdf) · [Chaîne des Puys morphometry](https://www.mdpi.com/2072-4292/13/10/1983)
- The [history](log/spec-volcanisme-historique.md) records the former round profile and material mask.

## The materials used

**The fresh volcanic soil, `gVolcanic`, from 0 to 1:** the cone of ash and slag of a stratovolcano, the top of a shield, the flows, the cones; weighted by freshness, e^(−t/3) on a chain.
- **The path:** it replaces the `relief` field unused from `FaceVertex`, which became `volcanic`, then `geology.w` up to the pixel.
- **Scoria cover follows the local deposit.** Use its normalized thickness, freshness and footprint area. Its contribution fades with the cone field towards orbit.
- **The rock:** the basalt, the darkest of the palette (`RockColor`).
- **Soil:** ash and slag, reflectance 0,07, on 85 % of soil; black beaches.

## The port CPU

**`tools/hydro/cp.py` reads `x64/Release/volcans-<graine>.bin`,** written by the engine on each startup, header `EXOVOLC1`; `EXOLUNE_VOLCANS` gives another path. `volcano_edifices` and `volcano_finish` follow the shader; `elevation(..., extra=True)` also gives `volcanoes` and `volcanic`.

- **Precision.** Subtract the cone centre in doubles. At 120 km from a shield summit a float coordinate advances in 8 mm steps, which produced stairs on its local flank.
- **Catalogue.** Seed 0 provides 1,113 volcanoes and 15 hotspots. Its 532 cone fields include 75 back-arc fields.
- **Review.** The [flank route](../tools/tests/2026-11-20-volcans-flancs.txt) covers the appearance and the relief at multiple distances. The [broader volcanism route](../tools/tests/2026-10-31-volcanisme.txt) includes atolls, guyots and flood basalts. The [history](log/spec-volcanisme-historique.md) preserves the original measurements.

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
