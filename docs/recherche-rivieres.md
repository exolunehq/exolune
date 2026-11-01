# Search: rivers, rivers and mountain lakes

Status: search for 2026-10-24. It measures what complexplanet is already doing and proposes a plan. **Step 1 made the 2026-10-25,** tag `piste/carte-planete`: the map of the planet, its bowls and its network, measured (`journal-planete.md`, the map of the planet; `tools/banc_carte.py`). The rest is not decided. **The spikes of 26 and 27 October are set aside:** Dendry model, basins built with their rivers, global network on complexplanet; tag `piste/rivieres-spikes`, doc in `log/recherche-rivieres-historique.md`. Research continues on the branch `erosion-niveaux`. The sea, and the lakes seen from the water, are in `recherche-mer.md`; the coasts, in `recherche-cotes.md`.

## 1. Conclusion and plan

**In brief:**
- **complexplanet has rivers, without water.** His river positions group carves wide valleys from 15 to 45 km and deep from 50 to 230 m.
- **These are level curves of noise.** Closed loops, without source or mouth, whose bottom goes up and down. To show them in water, the author of libnoise raised the sea level from 650 to 1 111 m according to the image.
- **Filling them does not give rivers.** The water would climb the slopes: 6 to 7 hollow by 100 km deep. Funds cover one third of the land; rivers and streams cover 0,6 % of the land on Earth.
- **The relief is not drained.** At the continental scale, 41% of land is in closed basin, with a median depth of 260 m. On Earth, dead end basins make up one fifth of the land, mostly arid.
- **No point calculation gives the level of a lake or the path to the sea.** A non-local pass is required.
- **The smallest that is enough: a hydrological map of complexplanet,** on a fixed grid of the planet, calculated at startup. This is the one that `recherche-mer.md` proposes for the lakes: a pass for both.
- **It does not affect complexplanet.** It gives lakes, network and flows of the relief as it is. Its network borrows the valleys of complexplanet up to twice as much as random.
- **The coast rule extends.** The coast is where the altitude crosses the water level: 0 for the sea, the level of its lake or river elsewhere. Same `SpreadStep`, same rule at any distance.
- **Riverbeds are a topcoat.** Under 13,5 m wide, detail addition. Beyond, and for the grooves, replacement, on experiment.
- **Mountain lakes come last.** Our mountains have bowls, but too many and random: 11 % of the surface at 30 m. The real circus lakes are grouped near the former glacier boundary, at the foot of a wall.

**The plan:**

| Stage | Contents | Nature | Measure of success |
|---|---|---|---|
| 0 | The benchmark off engine: complexplanet ported on CPU, filling the cuvettes, network. Made for this research | tool, the motor does not change | it reproduces the figures from section 2 |
| 1 | The hydrological map: complexplanet on 6 × 1 024² cells at startup, filling by priority, network, water balance. Three diagnostic views: valleys, cuvettes, network | rendered alone; nothing displayed in flight | same cuvettes as the benchmark 0 on its windows; constant share to the benchmark of descent; share of lakes after water balance, to decide inland seas |
| 2 | Lakes: a flat water at the level of its lake, the model of sea water | surface water, out of the three families, like the sea | share of land in lakes and sizes against HydroLAKES; no leakage at lake edge; quality benchmark unchanged on land |
| 3 | Rivers from afar: a water strip from the pixel on the smooth and meandering network; green corridors | left alone | river surface 0,3 to 0,6 % of land; wavelength of meanders near 12 latitudes; reflection seen from aircraft |
| 4 | Fine hydrology near the camera: tiles of 600 m then 75 m on the planet grid, bounded by the coarse map. Streams and small lakes | rendered alone and water surface | drainage density from 2 to 5 km/km²; no jump at the passage from one level to another, to jitter benchmark |
| 5 | Beds: channel dug under the water level, banks, gorges | topcoat: detail added below 13,5 m wide, replacement beyond. Spec, industry, tag `piste/rivieres-lits`, adjustment `RIVER_BED` = 0 | depth of excavation, p99; share of network in gorge; quality benchmarks and jitter |
| 6 | Water flowing: direction and speed, foam, rapids, cascades, color, wet banks, ice | left alone | photos by bed type; constant foam share in descent |
| 7 | Circums and moraine lakes | overlay: replacement, on experiment | Circus sizes vs Barr 2019; Lakes elevation band |

**The step 1 is small and measurable.**
- **What it touches:** a pass of calculation at start, like the tiles generated; a fill on CPU of 6,3 million cells; three views `MYPLANETENGINE_VIEW`.
- **What it measures:** the same numbers as the benchmark 0, on the same windows.
- **What it cuts:** how many lakes and inland seas this relief carries, before drawing one only.

**To be decided before step 2: inland seas.**
- **Measured on the map, the 2026-10-25:** each filled bowl, 43 % of land is under water, 231 m of bottom median. The interiors of the continents make three bowls of 58, 28 and 10 million km²; 95 % of the land flows into them. Without a water balance, no lake to draw.
- **The large complexplanet bowls are deep.** Reopen those of less than 20 m almost no empty: 12 to 21 % of the land remains under water, at 4,8 km of grid cell.
- **Water balance dries them in dry climates:** salt marshes, such as the Great American Basin.
- **In humid climates, they remain full:** large lakes, such as the Great Lakes or the Caspian Sea.
- **Three choices:** keep them; empty them by a breach dug, a replacement; show them in swamp. The view of the step 1 allows to judge.

**Do not touch `RIVER_DEPTH`.** The valleys of complexplanet remain the source of truth. They will host a part of the network and the rosaries of lakes. Removing them would be a replacement, with its experiment.

## 2. The audit: complexplanet rivers

![The valleys of complexplanet and what water would do there](images/rivieres-complexplanet.jpg)

*a: the rivers' digging on land. b: the continental scale closed basins. c: a plain of 600 km, its valleys in dark, the network calculated at 4,8 km in cyan, a valley in green. d: the profile along the bottom of this valley. e: the same plain, each basin filled. f: 12 km of mountain at 30 m, each basin filled.*

### What the Code Says

`RiverPositions` and the end of `ComplexPlanetElevation`, in `ComplexPlanet.hlsli`:
- **Two valley families:** two RidgedMulti of one octave, at frequencies 18,75 and 43,25 on the unit sphere. Their grid cells are 340 km and 147 km.
- **A RidgedMulti of one octave is (1 − |n|)² × 1,25 − 1.** It culminates where the noise n passes through 0. The curve turns it over: its peaks become bottoms.
- **Turbulence twists them:** frequency 9,25, amplitude 1/57,75 of the radius, or 110 km, six octaves. The finest is 21 km wavelength. Nothing winds shorter.
- **The depth:** `RIVER_DEPTH` is 0,0234 unit, or 192 m. The bottom of the large valleys descends from 192 m on its edges to 227 m in the center; that of the small ones, from 48 to 66 m.
- **Where they dig:** a `Select` on the altitude. Full force at 1 024 m; half at sea level and at 2 048 m; nothing below −1 024 m or above 3 072 m.
- **So:** they also dig the continental shelf, and not the high mountains.
- **The rest of the land** drops by ten meters at most.

**What libnoise showed:** The example page shows river valleys. To see them in water, each close-up view rises to sea level: 850 m, 650 m, 1 111 m, “to flood the river valleys”.

**SpaceEngine did the same in 2013:** "pseudo-rivers" that do not flow from the heights to the sea, form loops "like blood vessels", and have water only at sea level. They are beautiful only near the coasts.

### Measures

**The method:** complexplanet ported to numpy from the HLSL, constants included, to filter octaves of a grid cell of the cell size. Three windows from 600 km to 1,2 km: a plain, a coast, a mountain. The whole planet at 0,5°. Two mountain windows of 12 km to 30 m, one plain window of 30 km to 100 m.

| Size | Great Valleys | Small valleys |
|---|---|---|
| Width of the bottom | 37 to 46 km | 14 to 17 km |
| Width to top of sidewalls | 54 to 69 km |  |
| Median depth of bottom, flat | 169 to 182 m | 45 to 47 m |
| Slope of the sides, p99 | 2 % | 2 % |
| Length per 1 000 km² of land | 2,8 to 4,4 km | 8 to 12 km |
| Average deviation along a line | 360 to 570 km | 130 to 190 km |
| Share of land in valley bottom | 19 % | 14 % |
| In mountains, median at 4 km | absent | absent |

- **42 % of land** is lowered by more than 10 m.

### What it means

- **Valleys, not rivers.** 15 to 45 km deep, this is the scale of an alluvial plain or the Rhine ditch, not a channel.
- **Almost invisible on the ground.** From the flanks to 2 %: 180 m of descent on 9 km.
- **Loops.** Where a noise is equal to 0 on a sphere, the curve is always closed. On land, a valley stops only at the coast.
- **No confluence.** The two families cross in X. Neither flows into the other in Y.
- **No flow direction.** The bottom is the relief less a depth: it follows the bumps of the relief. Along the bottoms of large valleys, smoothed on 5 km:
  - 6 to 7 hollow by 100 km;
  - the total climb is 0,6 to 1,2 times the descent;
  - 20 to 61 % of length is in a closed bowl;
  - the valley of the figure d rises from 210 to 460 m on 300 km.
- **The sea by chance.** Where a loop crosses a coast, the excavation passes under 0 and the sea enters, in ria. In the coastal window, 2,4 % of the land becomes sea as well.
- **Mountain valleys have the same shape.** `MountainBaseDef` and `HillyTerrain` dig their own by a RidgedMulti of one octave at 367: a labyrinth of loops of 17 km of grid cell, closed too.

### What the water would show, depending on the level

1. **At sea level, today:** coastal valleys become rias; the rest is dry. An inland sea below 0, cut off from the ocean at 55 km from grid cell, covers 3,6 % of the land. It is drawn like the sea.
2. **A fixed-height ribbon above each bottom:** one third of the land underwater, in ribbons of 15 to 45 km, fifty times the surface of terrestrial rivers. The water rises and falls with the bottom.
3. **Each bowl filled to its threshold:** Lakes rosaries, 37 to 39 % of large valley bottoms.
   - Over the entire window: 19 to 26 % of land at 1,2 km, 15 to 22 % at 4,8 km.
   - On the planet, at 55 km: 41 %, deep basin of 263 m in median.
   - Reopening the cuvettes of less than 20 m empties almost nothing: there remains 12 to 21 %.
4. **In mountains, at 30 m:** 9 to 11 % of lake area.
   - 500 to 730 lakes of more than one hectare per 1 000 km².
   - Depth of 21 to 24 m in median.
   - Their sizes follow N(>A) ∝ A^−0,7.
5. **In plain water, at 100 m:** 12 % of pools of 3 m of median depth, between the Billow bumps.

### The drainage map calculated on complexplanet

A network calculated at 4,8 km, compared to the relief at 1,2 km of the same window:
- **He finds the valleys.** In the plains and on the coast, 42 to 63 % of the drainage network draining more than 200 km² passes through it, for 31 % of the surface.
- **It crosses many lakes:** 41 to 82 % of its length.
- **The finer relief does not disturb it much in plains.** The lowest 1,2 km cell exceeds the water level by more than 5 m on 0,04 % of the network in plains, 1 % in mountains, 4 % on the coast. On p99: 0,5 m, 1,8 m, 18 m.
- **In mountains, its level floats.** It passes 480 m above the fine valley floors, in the middle. The rough map shows the path and flow, not the water level: you have to fine-tune it near the camera.

### Limits of the measure

- **Minors:** the sea and the edge of each window serve as outlets. A bowl larger than the window empties there.
- **Orders of magnitude:** a few windows, not a statistic of the planet.
- **This planet has 58 % of land,** compared to 29 % for Earth.
- **To check in the engine:** a diagnostic view of the valleys. The share of land in the bottom of the great valley, 19 %, must remain the same as 1 500 km at the ground.
- **Scripts** are in `tools/hydro/`; the engine card is checked and measured by `tools/banc_carte.py`.

### Where to watch in flight

In the format `tools/tests`: altitude, latitude, longitude, inclination, heading.

| Location | Position |
|---|---|
| Background of large valley in plain, 347 m |  `20000 28.87168 -148.68863 60 0`  |
| Valley bowl, a lake if it was filled, 222 m |  `20000 28.75533 -144.96030 60 0`  |
| Valley that joins the sea, in ria |  `15000 21.44456 -107.64384 60 0`  |
| Mountain bowls, 3 600 m |  `6000 38.52929 169.97278 50 0`  |

## 3. Real rivers and lakes: types and sizes

### The network

- **Length is in streams, surface in rivers.** The essential length is in order 1; the essential area is in orders 5 to 9 (Downing 2012).
- **Hack's Law:** The length of the main course grows as the drained area at the power 0,5 to 0,6. L = 1,4 A^0,6, in thousands.
- **The drainage density:** 2 to 5 km of course per km² in general; 2 to 12 from semi-arid to humid.
- **Where a course is born:** beyond a critical drained area, which varies with slope, rock and climate (Schneider 2017).
- **complexplanet has 0,011 to 0,016 km/km²:** one hundred to four hundred times less, and only large courses.

### Width, depth, speed

- **Hydraulic geometry** (Leopold and Maddock 1953): width, depth and speed in powers of flow Q.
  - W ∝ Q^b, D ∝ Q^f, V ∝ Q^m, with b + f + m = 1.
  - Usual values downstream: b ≈ 0,5, f ≈ 0,4, m ≈ 0,1.
- **A world law:** W ≈ 7,2 Q^0,5, in m and m³/s (Moody and Troutman 2002, verified by Frasson 2019 on rivers of more than 90 m).
  - 50 m for 50 m³/s, 230 m for 1 000 m³/s, 1,6 km for 50 000 m³/s.
  - Typical deviation from −35 % to +81 %.
- **Area:** rivers and streams cover 0,58% of the unglacial land (Allen and Pavelsky 2018); 0,3 to 0,56% according to Downing 2012.
- **The slope drops downwards.** Beyond 70 cm/km, these are mostly courses of less than 100 m (Frasson 2019).

### The shapes of the bed

- **Meanders:**
  - wavelength of 12,7 widths in median, 9 in mode (Frasson 2019); 11 at Leopold and Wolman 1960;
  - The ratio decreases with width: 21 below 100 m, 8,4 beyond 300 m;
  - radius of curvature from 2 to 3 widths;
  - mean sinuosity of 1,25 to 1,5, very asymmetrical.
- **Braids:** steep slope for flow, abundant coarse sediments, variable flow. Glacial streams, ejection cones.
  - Leopold and Wolman threshold 1957: S = 0,06 Q^−0,44, Q in pieds³/s, or about 0,012 Q^−0,44 in m³/s. Above, braids.
- **Slope-dependent bed** (Montgomery and Buffington 1997): cascades above about 6,5 %; steps and basins from about 3 %; flat bed, then lower thresholds and wetlands; sand dunes at the lower slopes.
- **cascades:** where the profile breaks. Hard rock, valley suspended from an ancient glacier, fault.
  - Falling falls are also born alone, in series, on a uniform bed (Scheingross 2019).

### Lakes

- **How many:**
  - 117 million more than 0,2 ha, 5 million km², 3,7 % of non-iceland land (Verpoorter 2014);
  - 1,4 million more than 10 ha, 2,67 million km², about 1,8 % (HydroLAKES).
- **Sizes:** large and medium lakes make up the bulk of the surface (Verpoorter 2014).
- **Where:** mainly on the lands once covered by glaciers, Canadian and Scandinavian shields.
- **No-exit basins:** one fifth of the land, in arid and semi-arid climate (Wang 2018). Their lakes are salty or dry.
- **Types:** glacial, in a circle, behind a moraine, in a trough; tectonic, in a rift; river, dead arm; volcanic; barred by a landslide; karstic.

### Mountain Lakes

- **The circus lake:** a circus is a chair-like hollow with a steep wall and a hollowed-out bottom (Barr and Spagnolo 2015). The bottom often keeps a lake.
  - **Sizes:** on 2 208 circuses of Great Britain and Ireland, length 774 ± 426 m, width 786 ± 365 m, depth 283 ± 108 m, in log-normal law (Barr 2019).
  - **The lake** occupies a part of the bottom: from a few hectares to a few dozen.
  - **Altitude:** Circus bottoms are grouped near the balance line of past glaciers. They are used to rebuild it.
- **Moraine lake:** held by the moraine arc at the front of a glacier. Often turquoise.
- **The rosary:** lakes in stairs along a glacier, between rocky locks.
- **Glacial lakes are growing:** +53 % in number and +51 % in surface from 1990 to 2018 (Shugar 2020).
- **What our mountains have:** noise, 11 % of the surface, everywhere, at any altitude, without a chair wall above. True circus lakes are rare, in a band of altitude, at the foot of a wall.

### The colors

- **31 % of lakes are blue, 69 % green to brown,** on 85 360 lakes (Yang 2022). Blue is deep and cold, in humid climate, frozen in winter.
- **Turquoise milky:** glacial flour, very fine rock grains, remains suspended (NASA Earth Observatory). It makes up two thirds of the light attenuation in glacier lakes (Rose 2014).
- **Dark blue, almost black:** a deep and clear mountain lake, without flour.
- **Brown:** dissolved organic matter, peatlands and boreal forests; plain sediments.
- **A scale of measurement:** Forel-Ule, 21 shades from blue to brown. A global dataset exists for lakes, from 2000 to 2018.
- **Rivers:** beige and muddy in the plain, milky under glaciers, transparent in rock torrent.

## 4. Building them in our engine: options compared

### The key question

**Altitude is a noise evaluated point by point, without global pass.**
- **What a point cannot know:** The level of a lake depends on the lowest threshold of its entire basin, sometimes hundreds of kilometers away. The direction of a river depends on the whole downstream to the sea.
- **So:** no purely local method gives, on the complexplanet relief, rivers that descend and flat lakes.
- **The local methods that get there make the relief around the water.** They replace complexplanet.

### The options

| Option | Always get down | Flat lakes | Our rules and regulations | Family, `geometrie.md`  | Verdict |
|---|---|---|---|---|---|
| A. Fill the valleys of complexplanet at a level drawn from the point | no: 6 to 7 hollow by 100 km | no | universal and on the grid; water rises | surface of water | for rivers |
| B. Level drawn from neighbouring minima, without pass | no | no: the threshold is far | expensive; flat per cell only, steps at edges | surface of water | Dismissed |
| C. Coarse hydrological map of complexplanet, at startup | yes, by construction | yes, one level per lake | fixed grid, independent of the camera: same result at any distance, no jumps | Lakes: water surface; beds: detail addition or replacement | retention, the base |
| D. Thin hydrological tiles near the camera, bounded by C | yes | yes | deterministic per tile; the transition from one level to another under the pixel | Same | Retention, step 4 |
| E. Network first, relief around: Derzapf 2011, Génevaux 2013, Dendry 2019, Fischer 2022, Davis 2026 | yes | yes | local for Dendry; the relief follows the water | heavy replacement | experiment distant |
| F. Erosion of the whole planet: stream power, hydraulic erosion on GPU | yes, drained relief | few cuvettes | heavy overall pass; new relief | Total replacement | Geometry |
| Mr. Erosion Filter, `piste/erosion-filtre`  | no: its lines are interrupted | no | local and universal | replacement, already closed | ravines only |

**The options in detail:**
- **A, fill the valleys:** that's what libnoise did. The measurements of the section 2 dismiss it: the water would rise, the ribbons would be giant, the loops would have no meaning.
- **B, local minima:** a point that would like to find its threshold would have to evaluate the relief over tens of kilometers. Anchored on cells, the level would be flat per cell and would make steps between them.
- **C, the rough map:** the only one that keeps complexplanet as it is.
  - complexplanet on a fixed cube of the planet, 6 × 1 024² first, about 10 km; 2 048² if the measurement requires it.
  - Priority filling (Barnes 2014), in n log n.
  - Water balance by Fill-Spill-Merge (Barnes 2021): 4 million cells in 8,7 s.
  - Direction, drained area and flow of each cell.
- **D, fine tiles:** the coarse map gives path and flow; the water level comes from the fine relief.
  - Tiles of 600 m then 75 m, calculated on demand around the camera, each bounded by the rough map: the river enters and exits by points fixed in advance.
  - The content of a tile depends only on its place on the planet.
  - This is the idea of Derzapf 2011, on a planet, and Davis 2026, per plate.
- **E, the network first:** the richest family.
  - Kelley 1988, cited by Fischer 2022, then Derzapf 2011 on a planet: the network first, by displacement of the constrained center point, the relief then. Derzapf builds entire planets in seconds and refines on GPU in flight.
  - Prusinkiewicz and Hammel 1993: mountain and river in one process.
  - Génevaux 2013: a drainage graph, then primitives of relief along the rivers.
  - Dendry, Gaillard 2019: a function evaluated point by point, the distance to a tree built on the fly. Coherent networks, but relief must follow.
  - Fischer 2022: lakes and rivers first, the relief "pushed" around.
  - Davis 2026: networks plotted by plate tectonics, cached, heights adjusted so that each segment descends.
  - Red Blob Games, TerraFirmaCraft: river trees on a map or a finite region; an endless world is cut into regions.
  - **At our house:** all this replaces the form of complexplanet on a large scale. To keep for a decision of the geometry path.
- **F, the global erosion:** Cordonnier 2016 and Schott 2023 by the stream power law, Tzathas 2024 by his analytical solutions, Mei 2007 on GPU. The relief becomes drained. It is a new relief.
- **G, the erosion filter:** its author says it: its drainage lines can stop halfway down the slope. He draws ravines, not a network.

### The rules that follow

1. **Generalized coast.** The coast is where the altitude crosses the water level. The sea has 0; a lake has its level; a river, the level of its course. The water share of the pixel follows `SpreadStep`, like the sea.
2. **One level per lake, constant.** The map bears the lake's identification. Its area, enlarged by one cell, bears a single level. The shore is where the fine relief crosses this level: islands and bays come alone.
3. **The water balance, drawn from our climate.**
   - Runoff: rain, from 100 to 3 000 mm/an by our humidity, less evaporation, drawn from temperature.
   - A basin fills up until the evaporation from the lake equals the contribution from its basin, at most up to its threshold. Full, it overflows into the next.
   - In dry climate: partial salt lakes, or dry basin.
4. **Width by flow:** W ≈ 7,2 Q^0,5, Q runoff times the drained area. No width chosen at the main.
5. **The smooth and meandering course on the grid of the planet.** The path of cells smoothed, then meanders of wavelength near 12 widths, of varying amplitude along the course.
6. **No course is born from a stroke.** A stream appears beyond the critical area and widens over some widths (`principes.md`: no structure stops clearly).
7. **A thinner layer appears only below the pixel.** A thin tile moves the course by less than a pixel where it takes over. The same rule as the octaves filtered by grid cell.

### Families, in terms of `geometrie.md`

- **The surface of a lake or river:** the geometry, but not the terrain. The mesh goes up to `max(e, niveau)`, as it goes up to `max(e, 0)` for the sea. To be registered with the sea, out of the three families, as proposed by `recherche-mer.md`.
- **A bed less than 13,5 m wide:** detail addition.
- **A wider bed, a gorge, a breach:** replacement. Spec, branch, tag `piste/…`, stop setting.
- **A circus:** replacement.

### The cost

- **The map:** 6,3 million points of complexplanet, filtered to 10 km: of the order of a few images of the mesh, once. Filling on CPU: a few seconds, to be measured. Then in cache.
- **Memory:** floating level, direction, drained area and lake identifier: in the order of 50 to 80 MB to 1 024² per face.
- **Thin tiles:** 600 m on 500 km radius, or 75 m on 50 km: a few million cells each.
- **Rendering:** a texture reading per vertex and per pixel.

## 5. The rendering of the inner water

### What is shared with the sea

`recherche-mer.md` gives the model; the lakes take it as it is.
- **The reflection:** Fresnel, reflected sky, sun by Cox-Munk. For a sheltered lake, the variations of water covered with a film: a sharper reflection.
- **Lake waves:** the fetch is the size of the lake, which gives the map. 5 m/s on 5 km make 0,18 m.
- **Colour:** by depth and type of water, the visible bottom in shallow water, the scale of Forel-Ule.
- **foam:** a part of the pixel.
- **Relief reflections:** in screen space.

### What is specific to running water

- **The direction and speed:** the tangent of the course, mixed with the slope of the water level. A speed from 0,5 to 3 m/s, which slowly increases with the flow, like Q^0,1.
- **The surface that flows:**
  - closely, two-phase flow charts (Vlachos 2010);
  - on large networks, the advection of Yu 2009, taken up in Proland;
  - from afar, the slope of the wrinkles lost by the pixel becomes roughness of the reflection, as for the sea.
- **The bed according to the slope** (section 3): smooth thresholds and wets; flat bed wrinkled; steps and sinks, foam in spots; cascades, white water.
  - **Rapids:** a part of foam that grows with the slope and flow. Uncharted 4 makes them by wave particles.
- **The cascades:** where the level drops more than the width over a short distance, or crosses a rock face.
  - Close up: a vertical layer, texture that slides, sprays on the foot.
  - From afar: a white line on the pixel.
- **The color, drawn from the climate and the place:**
  - milky and turquoise under the glaciers, near the snow line;
  - beige in large plain courtyards;
  - transparent in rock torrents;
  - brune in wet forest and bog.
- **Wet banks:** a strip above the water, wider as the flow increases. Darker albedo according to porosity, smoother surface (Lagarde 2013). benchmarks of pebbles in the braids.
- **Green corridors:** moisture measured along the network. The vegetation of the banks is seen from orbit in deserts, like the Nile. `BiomeColor` already exists.
- **Ice:** under −2 °C, the snow rule, lakes and slow streams freeze under the snow. Fast torrents remain open.
- **From far:** a course narrower than the pixel is a part of it, its width on the pixel size. It shines in line when the sun is reflected on it.

### Rendering references

- **Peytavie 2019, *Procedural Riverscapes*:** beds dug according to Rosgen classification, surface animated by a flow tree, foam and debris. The reference for the steps 5 and 6.
- **Hendrickx 2010:** river networks in Bezier curves and maps of normals that scroll.
- **Lightspeed, GDC 2023:** Water Height, Speed and Foaming Calculated, Adaptive Water mesh.

## 6. Measuring against the real

### The data

To download in `../donnees-terre`, with agreement:
- **HydroLAKES and HydroRIVERS** (HydroSHEDS): lakes over 10 ha, global network with flows.
- **GRWL** (Allen and Pavelsky 2018): river widths of more than 30 m.
- **GRIN** (Schneider 2017): global drainage density at 7,5′.
- **Frasson 2019 base:** width, slope, meanders, sinuosity, flow.
- **The game Trout-Ule of the lakes,** 2000 to 2018.

### What we compare

- **The network:**
  - drainage density by climate, against GRIN;
  - Hack exhibitor, 0,5 to 0,6, on our main courses;
  - share of land without exit, near 20 % (Wang 2018); 41 % today at 55 km.
- **Rivers:**
  - Total area, 0,3 to 0,6 % of land;
  - distribution of widths against GRWL;
  - meanders: wavelength over width of 9 to 13, sinuosity against Frasson base.
- **Lakes:**
  - share of land, 1,8 % above 10 ha, 3,7 % above 0,2 ha;
  - number per size class against HydroLAKES;
  - in mountains: density, sizes and altitude band against the lakes of the Alps and Pyrenees in HydroLAKES.
- **Colours:** Forel-Ule index; 31 % of blue lakes.

### The photos

**A game by type, in `../references`:** Circus lake, turquoise moraine lake, braided river, meanders seen from an airplane, torrent with steps and basins, cascade, orbit river reflecting the sun. Compared with the measurements of `tools/realisme.py`.

### The benchmarks of the engine

- **benchmark descent:** the constant indoor water share of 1 500 km to the ground, by a diagnostic view.
- **quality benchmark:** no regression on earth.
- **benchmark of jitter:** banks and ribbons immobile.
- **benchmark of the map, `tools/banc_carte.py`:** the elevation of the map against the port numpy, its filled surface against a Priority-Flood written apart, its flows to the sea; lakes, network, Hack law.

## 7. Sources

**complexplanet and engines:**
- libnoise, the complexplanet example, sea levels risen "to flood the river valleys": https://libnoise.sourceforge.net/examples/complexplanet/index.html
- SpaceEngine, pseudo-rivers, 2013: https://spaceengine.org/news/blog131222/
- Outerra, rivers by vector data: https://forum.outerra.com/index.php?topic=99.0; update, width and bed modulated: https://www.avsim.com/forums/topic/540892-outerra-major-update-17109830-82118/
- Microsoft Flight Simulator, water masks from OpenStreetMap, community report: https://forums.flightsimulator.com/t/how-does-the-sim-determine-quantity-of-water-in-rivers/701889
- Star Citizen, Genesis or Planet Tech v5, rivers drawn from geology and erosion, no technical detail published: https://www.gamestar.de/videos/jeder-planet-ein-spektakel-star-citizen-macht-mit-genesis-einen-weiteren-schritt-richtung-fotorealismus,138406.html
- No Man's Sky, Worlds Part II, lakes and oceans, no rivers documented: https://www.gematsu.com/2025/01/no-mans-sky-worlds-part-ii-update-now-available
- Proland, the rivers plug: https://proland.inrialpes.fr/doc/proland-4.0/river/html/index.html

**Actual hydrology:**
- Allen and Pavelsky 2018, *Global extent of rivers and streams*, Science: https://www.sciencenews.org/article/earth-rivers-cover-44-percent-more-land-we-thought; GRWL: https://gee-community-catalog.org/projects/grwl/
- Downing et al. 2012, *Global abundance and size distribution of streams and rivers*, Inland Waters : https://utrecht-main-test.atmire.com/items/da859c45-f6a9-4acd-a82f-49fac6463ff8
- Frasson et al. 2019, *Global relationships between river width, slope, catchment area, meander wavelength, sinuosity, and discharge*, GRL : https://research-information.bris.ac.uk/en/publications/global-relationships-between-river-width-slope-catchment-area-mea/ ; base : https://zenodo.org/record/2579160
- Moody and Troutman 2002, *Characterization of the spatial variability of channel morphology*, ESPL: https://doi.org/10.1002/esp.403
- Leopold and Maddock 1953, *The hydraulic geometry of stream channels*, USGS PP 252: https://pubs.usgs.gov/publication/pp252
- Leopold and Wolman 1957, *River channel patterns: braided, meandering, and straight*, USGS PP 282-B: https://pubs.usgs.gov/publication/pp282B
- Leopold and Wolman 1960, *River meanders*, GSA Bulletin: https://pubs.usgs.gov/publication/70185557
- Hack 1957, USGS PP 294-B: https://pubs.usgs.gov/pp/0294b/report.pdf; the law of Hack: https://en.wikipedia.org/wiki/Hack%27s_law
- Montgomery and Buffington 1997, *Channel-reach morphology in mountain drainage basins*, GSA Bulletin: https://fs.usda.gov/rm/boise/publications/watershed/rmrs_1997_montomeryr001.pdf
- Drainage density, usual values: https://www.netmaptools.org/Pages/NetMapHelp/drainage_density.htm
- Schneider et al. 2017, global network and drainage density, GRL: https://hal.sorbonne-universite.fr/hal-01496152; GRIN: https://www.metis.upmc.fr/en/node/375
- Scheingross, Lamb et Fuller 2019, *Self-formed bedrock waterfalls*, Nature: https://resolver.caltech.edu/CaltechAUTHORS:20181121-090230516
- Verpoorter et al. 2014, World Lakes Inventory, GRL: https://hal.archives-ouvertes.fr/hal-01066344
- Messager et al. 2016, HydroLAKES, Nature Communications: https://www.hydrosheds.org/hydrolakes
- Wang et al. 2018, endoreic basins, Nature Geoscience: https://www.sciencedaily.com/releases/2018/11/181130153841.htm
- Barr et Spagnolo 2015, *Glacial cirques as palaeoenvironmental indicators*, Earth-Science Reviews: https://e-space.mmu.ac.uk/619051/
- Barr et al. 2019, *The dynamics of mountain erosion: cirque growth slows as landscapes age*, ESPL: https://eprints.whiterose.ac.uk/147552/
- Shugar et al. 2020, *Rapid worldwide growth of glacial lakes since 1990*, Nature Climate Change : https://eprints.whiterose.ac.uk/168562
- Yang et al. 2022, *The Color of Earth's Lakes*, GRL : https://news.agu.org/press-release/climate-change-is-making-lakes-less-blue/
- Rose et al. 2014, glacial flour and light attenuation, JGR: https://researchcommons.waikato.ac.nz/bitstream/10289/8942/1/2014%20rose%20hamilton%20williamson%20mcbride%20fischer%20olson%20saros%20allan%20cabrol%20Journal%20of%20Geophysical%20Research.pdf
- NASA Earth Observatory, *How glaciers turn lakes turquoise* : https://www.earthobservatory.nasa.gov/images/145055/how-glaciers-turn-lakes-turquoise
- Forel-Ule Index of Inland Waters, 2000 to 2018: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7835379/; Pitarch et al. 2019 : https://ore.exeter.ac.uk/repository/handle/10871/38277

**Procedural hydrology and algorithms:**
- Prusinkiewicz and Hammel 1993, *A fractal model of mountains with rivers*: https://algorithmicbotany.org/papers/mountains.gi93.html
- Derzapf, Ganster, Guthe and Klein 2011, *River networks for instant procedural planets*, CGF: https://diglib.eg.org/handle/10.1111/v30i7pp2031-2040; authors' page: https://www.mathematik.uni-marburg.de/~derzapf/public/2011/index.html
- Génevaux et al. 2013, *Terrain generation using procedural models based on hydrology*, SIGGRAPH : https://doi.org/10.1145/2461912.2461996
- Cordonnier et al. 2016, *Large scale terrain generation from tectonic uplift and fluvial erosion*, CGF : https://hal.archives-ouvertes.fr/hal-01262376
- Schott et al. 2023, *Large-scale terrain authoring through interactive erosion simulation*, ACM TOG: https://history.siggraph.org/learning/large-scale-terrain-authoring-through-interactive-erosion-simulation-by-schott-paris-fournier-guerin-and-galin; code: https://github.com/H-Schott/StreamPowerErosion
- Tzathas et al. 2024, *Physically-based analytical erosion for fast terrain generation*, CGF : https://diglib.eg.org/handle/10.1111/cgf15033
- Mei, Decaudin and Hu 2007, *Fast hydraulic erosion simulation and visualization on GPU*: https://hgpu.org/?p=2256; Jákó and Tóth 2011: https://diglib.eg.org/handle/10.2312/EG2011.short.057-060
- Galin et al. 2019, *A review of digital terrain modeling*, CGF : https://cs.purdue.edu/cgvlab/www/publications/Galin19CGF
- Gaillard et al. 2019, *Dendry: a procedural model for dendritic patterns*, I3D : https://cs.purdue.edu/cgvlab/www/publications/Gaillard19I3D
- Peytavie et al. 2019, *Procedural riverscapes*, CGF : https://diglib.eg.org/handle/10.1111/cgf13814
- Fischer, Boeckers et Zachmann 2022, *Procedural generation of landscapes with water bodies using artificial drainage basins*, CGI: https://cgvr.cs.uni-bremen.de/papers/cgi22/CGI22.pdf
- Davis 2026, *Plate-local river generation*, arXiv : https://arxiv.org/abs/2610.00301
- Red Blob Games, *Procedural river drainage basins*: https://www.redblobgames.com/x/1723-procedural-river-growing/
- O'Leary, *Generating fantasy maps* : https://mewo2.com/notes/terrain
- TerraFirmaCraft, *Why are rivers so complicated?* : https://gist.github.com/alcatrazEscapee/8bd54572c8d3fe070d1ed92704dd6aed
- Johansen 2026, *Fast and gorgeous erosion filter* : https://blog.runevision.com/2026/03/fast-and-gorgeous-erosion-filter.html
- Barnes, Lehman and Mulla 2014, *Priority-Flood*: https://arxiv.org/pdf/1511.04463
- Planchon and Darboux 2001, filling of depressions: https://horizon.documentation.ird.fr/exl-doc/pleins_textes/divers20-05/010031925.pdf
- Lindsay 2016, selective breach: https://doi.org/10.1002/hyp.10648
- Barnes, Callaghan and Wickert 2021, *Fill-Spill-Merge*, ESurf: https://esurf.copernicus.org/articles/9/105/2021/

**Render:**
- Vlachos 2010, *Water flow in Portal 2* : https://www.advances.realtimerendering.com/s2010/Vlachos-Waterflow(SIGGRAPH%202010%20Advanced%20RealTime%20Rendering%20Course).pdf
- Yu, Neyret, Bruneton and Holzschuch 2009, *Scalable real-time animation of rivers*: https://artis.inrialpes.fr/Publications/2009/YNBH09/
- Hendrickx, Smelik and Bidarra 2010, Real-time rendering of river networks: https://publications.tno.nl/publication/17006495/cJodKI/hendrickx-2010-realtime.pdf
- Uncharted 4, rapids by wave particles, quoted by: https://github.com/acskyline/wave-particles-with-interactive-vortices
- Lightspeed Studios, GDC 2023, water open world: https://gdcvault.com/play/1028915/Advanced-Graphics-Summit-Open-World
- Lagarde 2013, *Water drop 3a: physically based wet surfaces* : https://seblagarde.wordpress.com/2013/03/19/water-drop-3a-physically-based-wet-surfaces/
