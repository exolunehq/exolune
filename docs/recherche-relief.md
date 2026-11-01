# Research: a planetary tectonic relief for Exolune

Status: search for 2026-10-31. It founds `spec-relief-tectonique.md`, the living spec of tectonic relief, the relief of the game since the 2026-10-31. The steps 0 to 3 are made: the rule of the map that carries the geometry, the tectonic map, the large shapes, the detail. What has changed since this plan is in the spec: continental crust by location, a map of 512² in texels of 20 km, no valleys dug.

**References to the 0,** `recherche-erosion-niveaux.md`, `recherche-dendry.md`, `level0_erosion.py` and `level0_cut.py` level, refer to the `erosion-niveaux` branch, which has not yet been merged.

## 1. Conclusion

**The relief is based on a tectonic map calculated at startup, not a noise.** The noise only makes the detail, under 50 km, modulated by geology.

- **Why:** The current relief has no structure that fits with water. 41 % of the lands are in cuvettes; the level 0 must invent a rise by copying the heights of complexplanet, and its rivers cross the massifs (`recherche-erosion-niveaux.md`, 5 bis to 5 quinquies).
- **What literature and games agree to do:** the overall structure is calculated once, outside the rendering; the rendering evaluates it point by point and adds noise. No one simulates plates by frame.
- **The recommendation, in four layers:**
  1. **The tectonic precalculation,** at startup, in C++: plates, their movements, their typed borders, and smooth fields on the planet cube, 6 × 1 024².
  2. **The large shapes,** in the shader: analytical profiles applied to distances at borders. Continents, plateaus, chains, pits, arcs, rifts, ridges.
  3. **Detail,** in the shader: the bricks of `Noise.hlsli`, oriented by the direction of the folds and weighted by age and rock.
  4. **The erosion,** at startup: the level 0 finally receives a real lift, that of the converging borders; its eroded relief becomes the relief above two of its cells.
- **A step-by-step simulation, like Cortial, is not the first step.** A cinematic snapshot, of plates and their speeds at a moment, already gives the borders and their types, in a few seconds and without chaos. History, the ancient sutures, is synthesized apart.
- **The cost per vertex is likely to decrease.** Three map readings and 40 to 80 evaluations of noise, against about 340 today (`concept.md`, point 7). To be measured.
- **A rule of `principes.md` changes:** the planet map will carry geometry, above two texels. Decided and written the 2026-10-31, before any code.

## 2. The Reddit post reported

**It could not be read.** reddit.com, old.reddit.com, the URL in `.json` and api.reddit.com are refused by the web reader and by the built-in browser, for security reasons. No search engines index the thread `1xhximl` yet.

- **What is missing:** his text, comments, and the deposit or video he quotes.
- **To read it:** paste the text of the post, or the link of the deposit or video, and I complete this section.
- **Most likely, unconfirmed candidate: World Orogen,** `orogen.studio`, deposit `raguilar011095/planet_heightmap_generation`. Created in February 2026, updated the 2026-10-31, 135 stars, under **GPL-3.0**: ideas only, no code.
  - **V1:** Fibonacci sphere, plates by concurrent growth, converging, diverging and transforming boundaries, subduction according to density.
  - **The relief V1:** three fields of distance, mountain, ocean, coast, combined by a harmonic mean; profiles of asymmetric chains, continental shelf, outlying basins, graben rifts, ridges, pits, island arcs, hot spots.
  - **Then:** lefting by noise, Priority-Flood that digs the passes, implied river power to the Braun and Willett, glacial and thermal erosion.
  - **V2, “Evolution”:** a true tectonic history, supercontinent cycle, collisions, rifting, sutures, with 20 000 to 80 000 simulation cells. The rocks of history regulate erosion.
- **Other recent candidates:** DasTobi’s “Plate Tectonics Simulation” series, February video 2026; Frozen Fractal’s “Around the World”, which abandoned its plate simulation, too slow and too hard to control, for Voronoi plates and noise.

**The common lesson of these projects,** useful whatever the post: the plates give the structure, but erosion makes the realism; and a step by step simulation is poorly controlled. World Orogen V1 and Frozen Fractal are based on a snapshot, not a story.

## 3. What the current relief cannot give

- **No geological structure.** The mountains are born from a threshold on a noise, `RlTerrainType`, which grows inland. They follow no borders and have no age.
- **No drainage.** 41 % of land in closed cups, 260 m deep in median (`recherche-rivieres.md`).
- **A 0 level that works against its input.** Its rise is reversed to find the heights of complexplanet; the basins remain giant or the massifs lower; its routes pass through the mountains, 44 % of the length of rivers dug more than 50 m below ground.
- **No ocean floor.** The plateau is a ramp up to −700 m, then a smooth noise; no ridge, no pit, no arch (`recherche-cotes.md`).
- **The lesson of spike B:** at 1 km, complexplanet is a labyrinth of bowls. Any erosion that relies on it the roof or cut. The relief must be born already organized.

## 4. State of the art

For each source: what it brings, its cost, and its compatibility with our constraint, a function of the position evaluated by frame with data pre-calculated at startup.

### 4.1 The Procedural Tectonics

**Cortial, Peytavie, Galin, Guérin, « Procedural Tectonic Planets », CGF 38(2), 2019.**
- **The contribution:** the crust is a cloud of points on the sphere; each point bears its thickness, its type, the age of the oceanic crust, the type and age of orogenesis, the direction of the folds. The plates rotate around their Euler pole.
- **The phenomena:** subduction lifting, function of the distance to the front, the relative speed and the altitude of the sinking plate; continental collision, which welds a terrain and raises a large area; new crust to the ridges, according to a ridge profile; rifting, which cuts a plate; continental erosion and ocean damping, linear in time.
- **The orders of magnitude of the article,** quoted from memory, the PDF of more than 10 MB could not be reread by the tool: no time of 2 Ma; ridge at −1 km, abyssal plain at −6 km, pit at −10 km, summits up to 10 km; subduction range 1 800 km; maximum speed 100 mm/an. To be verified.
- **Magnification:** the crust parameters choose the detail. Procedural primitives for the ocean, oriented by the ridge, with its transforming faults; real MNT copies for the continents, oriented by the folds and chosen by type of orogenesis.
- **The cost:** a step-by-step simulation on CPU, then an expensive amplification. Seconds to minutes depending on the resolution, to read in the article.
- **Compatibility:** simulation, yes, at startup. The copy amplification requires a base of real MNT; a version by procedural primitives is evaluable point by point.
- **What we get:** crustal parameters such as fields, and the shape of subduction, collision and ridge profiles. Not the loop in time, at least not at first.

**Andy Gainey, Experilous, « Procedural Planet Generation », 2014.**
- **The contribution:** the cinematic snapshot. Subdivided icosahedron, plates by random growth, one rotation pole per plate. At each boundary edge, the relative velocity gives a pressure, normal, and a shear, tangent. The type of boundary follows: collision, subduction, divergence, transformation.
- **The relief:** the elevation of each border, then an interpolation to the inside of the plates according to the distance to the border and the center of the plate, then the noise.
- **The cost:** a second or less on the browser, to a few tens of thousands of cells.
- **Compatibility:** Direct for precalculation. This is the model of the recommended 1 layer.
- **The limit:** the site is offline at the time of this search; the license of the code could not be verified.

**Red Blob Games, « Procedural map generation on a sphere », 2018.**
- **The contribution:** the same idea, simpler: Fibonacci points, triangulation of Delaunay, plates by filling, mountains where the plates come closer, by fields of distance to mountains, ocean and coast.
- **The cost:** a few hundred milliseconds.
- **The license:** Apache-2.0.

**PlaTec, Viitanen 2012,** and WorldEngine that uses it.
- **The contribution:** a 2D simulation of plates on a flat map, fast, for height maps.
- **The limit:** a flat card that folds, not a sphere.
- **License:** LGPL-3.0 for PlaTec; WorldEngine is MIT but embeds PlaTec. Nothing to complain about.

**World Orogen, 2026,** described in section 2.
- **The contribution:** the complete chain most successful in free access: plates, profiles by type of border, then river erosion, glacial, thermal, and rocks that regulate erodibility.
- **The license:** GPL-3.0. Ideas only.

**Michel, Emilien, Cani, « Generation of Folded Terrains from Simple Vector Maps », Eurographics short 2015.**
- **The contribution:** large-scale folds from a simplified plate model, then refined by hydraulic erosion that takes into account rivers.
- **What we get from it:** the folds as oriented field, parallel to the front.

**Other open projects, see for their licenses:** tectonics.js, CC-BY-4.0; SimpleTectonics, license free, so all rights reserved; realistic-planet-generation-and-simulation, license free. Nothing to complain about.

### 4.2 The rise and erosion

**Cordonnier, Braun, Cani, Benes, Galin, Peytavie, Guérin, « Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion », CGF 35(2), 2016.**
- **The contribution:** the terrain is born from a map of elevation and the law of river power. A drainage graph on Poisson points, an implicit solver to the Braun and Willett, lakes resolved by a graph of basins. Chains appear where the uprising is strong; the net is in tree and goes to the sea.
- **Cost:** minutes on CPU for a regional domain.
- **Compatibility:** at startup, yes. It is exactly the current 0 level; it only lacks a meaningful uprising.
- **What we take from it:** the rise comes from tectonics, not from desired heights.

**Cordonnier, Cani, Benes, Braun, Galin, « Sculpting Mountains », TVCG 2018.**
- **Input:** layers of rock that are pleated under the ground; erosion depends on the hardness of the surface rock.
- **What we get:** a rock field that regulates the erodibility K of the 0 level and the type of noise on the surface.

**Schott, Paris, Fournier, Guérin, Galin, « Large-scale Terrain Authoring Through Interactive Erosion Simulation », ACM TOG 42, 2023.**
- **The contribution:** the river power with lift, entirely on GPU, interactive according to the authors. The user paints the uprising; the channel and its network follow.
- **Compatibility:** at startup, on GPU. This is the path to pass the 0 level from 10 minutes in Python to seconds.
- **License:** MIT, deposit `H-Schott/StreamPowerErosion`. Readable, but the Exolune code remains original.

**Tzathas, Gailleton, Steer, Cordonnier, « Physically-based Analytical Erosion for fast Terrain Generation », CGF 43(2), 2024.**
- **The contribution:** an analytical solution of the river power law under rise. no more time integration: the equilibrium relief is calculated along the network, like the integral χ of Perron and Royden 2013.
- **The cost:** the order of a pass on the network, after drainage. The code of `level0_erosion.py` already has a `chi_integral`.
- **Compatibility:** at startup, direct. This is the 0 level cheapest.

**Braun and Willett, FastScape, 2013.**
- **The input:** the implicit solver in O(n) along the network, which `level0_erosion.py` already implements.
- **License:** fastscapelib, the reference library, is GPL-3.0; its Python envelope `fastscape` is BSD-3 but depends on it. The published algorithm is free; Exolune's code is his own.

**Schott, Galin, Guérin, Paris, Peytavie, « Terrain Amplification using Multi-scale Erosion », ACM TOG 43(4), 2024.**
- **The input:** an amplification by river erosion, thermal and deposit, alternated with oversampling ×2.
- **Compatibility:** on a whole grid, yes; by tiles, no: spike B showed that a simulated erosion diverges according to its edges. Useable once on the planet map, not around the camera.
- **License:** MIT, `H-Schott/MultiScaleErosion`.

### 4.3 Hydrology first

**Génevaux, Galin, Guérin, Peytavie, Benes, « Terrain Generation Using Procedural Models Based on Hydrology », ACM TOG 32(4), 2013.**
- **Input:** the network of rivers first, from the mouths on a coast; order of Strahler; a type of bed by slope, according to Rosgen. The terrain is a primitive construction tree, valleys, hills, lakes, mixed by operators.
- **Compatibility:** the terrain is a continuous function of position, evaluable everywhere, from a pre-calculated network. Its cost per point is the number of primitives that cover it, accelerated by a spatial structure.
- **What we get from it:** valley primitives laid on rivers of the level 0, profile set by their flow and slope.

**Derzapf, Ganster, Guthe, Klein, « River Networks for Instant Procedural Planets », CGF 30(7), 2011.**
- **The input:** a hierarchical planetary network, refined on the fly.
- **The limit:** the relief follows the network; it does not serve a relief already given.

**Gaillard et al., “Dendry”, I3D 2019.**
- **The input:** a locally calculable dendritic tree, level by level. About 10 s for a grid of 512² on a four-core CPU.
- **Compatibility:** by tiles around the camera, not by vertex at each frame (`recherche-dendry.md`, section 6).
- **License:** the authors code, `mgaillard/Noise`, is **GPL-3.0**. Nothing to take back; the Exolune model is its own code.

### 4.4 Amplification and Analysis

**Guérin, Digne, Galin, Peytavie, « The spatial and temporal distribution of the spatial data in the spatial modeling of the spatial data », CGF 35(2), 2016.**
- **The input:** the relief as a hollow combination of atoms learned on real MNT; the amplification replaces each coarse atom with its fine twin.
- **Compatibility:** evaluable by point, but it takes a dictionary learned on real data.
- **The license:** MIT, in Matlab, `eric-guerin/terrain-amplification`.

**Galin et al., « A Review of Digital Terrain Modeling », CGF 38(2), STAR Eurographics 2019.**
- **The contribution:** the reference review: procedural, simulation, examples. It places each method above.

**Grenier, Guérin, Galin, Sauvage, « Real-time Terrain Enhancement with Controlled Procedural Patterns », CGF 43(1), 2024.**
- **The input:** phase patterns, independent of the resolution, whose direction is controlled at each point.
- **Compatibility:** Direct, by point. It is the tool for orienting the crests along the folds without shearing the noise.

**Argudo et al., « Terrain descriptors for landscape synthesis, analysis and simulation », Eurographics STAR 2025.**
- **The contribution:** measurable descriptors: hypsometry, slopes, prominence, networks. To judge a relief against the Earth.
- **License:** MIT, `oargudo/terrain-descriptors`. Useful for benchmarks, off the engine.

**Models learned:** Borg et al., “Authoring Terrestrial Planets with Diffusion Models”, CGF 45(2), 2026, conditioned by a global river network; “Terrain Diffusion”, arXiv 2025.
- **Compatibility:** not per frame. A network broadcast at start on the planet map would be possible, but it brings a learned weight and training data: contrary to a completely original code.

### 4.5 The noise functions "eroded"

**Quilez, the noise with analytic derivatives.**
- **Input:** each octave of the fBm is attenuated by the accumulated slope of the coarser octaves, in 1 / (1 + |∇|²). The slopes remain smooth, the hollows and the replat are covered with detail: an eroded appearance, without erosion.
- **Cost:** an evaluation of noise with its derivatives, about 1,5 to 2 once a single evaluation.
- **Compatibility:** Direct, by point.
- **The license:** Quilez's site puts under MIT the code that implements an algorithm, and keeps his works under copyright; his artistic shaders, like "Elevated", prohibit any reuse since 2021. The idea is free; we write it ourselves.

**The runevision erosion filter, Rune Skovbo Johansen, 2026.**
- **The contribution:** waves ravines aligned on the slope, placed on random pivot cells and mixed between neighbors; octave after octave, they fork. Each point is evaluated separately.
- **Its limitations, said by the author:** no global network; lines that stop at half-slope; a fade according to altitude that is not robust.
- **License:** the ticket publishes the code as MPL-2.0. An author's gist specifies that the core function derives from shaders by Fewes and clayjohn under CC BY-NC-SA 3.0. Idea only.
- **In the project:** a experiment already exists, `piste/erosion-filtre` (`geometrie.md`).

### 4.6 The games

**No Man's Sky,** GDC 2017, Innes McKendrick and Sean Murray.
- **What we know about it:** a "uber noise" per point, on voxels: left domain, attenuation by derivatives, peaks, plateaus, regions. No tectonics; a variety of aspect, not a geology.

**Elite: Dangerous, Stellar Forge.**
- **What we know about it:** a top-down simulation, from galaxy to planet. The properties of each planet, materials, volcanism, tectonics, temperatures, are sent to the GPU in a buffer; graphs of noise in compute shaders evaluate them, function of the position and the identifier of the planet. Double precision or pairs of floats, like us.
- **What we get:** the confirmation of the model: pre-calculated geological parameters, a relief evaluated by point.

**Star Citizen, Planet Tech v4 and v5.**
- **What we know about it:** global maps created by artists, then tiles of height of 4 km, in 2k, distributed by ecosystem. The v5, called Genesis, adds climate, soil, geology and erosion maps that determine the detail.
- **The difference:** of the author, not of the pure generation.

**SpaceEngine.**
- **What we know about it:** quaternary tree tiles generated on GPU and kept; noise functions with ridges, craters, volcanoes; pseudo-rivers in loops since 2013 (`recherche-rivieres.md`).

**Outland.**
- **What we know about it, from its public presentations:** the real MNT of the Earth, refined by fractal on GPU. No planet generation.

**The finding:** none of these games simulate the plates in flight. Geology, when it exists, is a precalculation or a data; the rendering evaluates a function of position, like Exolune.

## 5. Licenses

| Code | License | Verdict |
|---|---|---|
| libnoise, not including complexplanet | LGPL | prohibited, already dismissed |
| PlaTec, plate tectonics | LGPL-3.0 | prohibited |
| WorldEngine | MIT, PlaTec shipment | prohibited as such |
| fastscapelib | GPL-3.0 | prohibited; the algorithm remains free |
| fastscape, the envelope | BSD-3, depends on fastscapelib | to be dismissed |
| World Orogen | GPL-3.0 | prohibited |
| Dendry, `mgaillard/Noise`  | GPL-3.0 | prohibited |
| tectonics.js | CC-BY-4.0 | Discard, non-software license |
| SimpleTectonics | none, all rights reserved | prohibited |
| realistic-planet-generation-and-simulation | None | prohibited |
| Experilous, planet generator | not verified, site offline | to be dismissed |
| Red Blob Games, 1843-planet-generation | Apache-2.0 | permission, with notice; unnecessary |
| StreamPowerErosion, Schott 2023 | MIT | license; we read it, we do not copy anything |
| MultiScaleErosion, Schott 2024 | MIT | Same |
| terrain-amplification, Guérin 2016 | MIT | Same |
| terrain-descriptors, Argudo 2025 | MIT | for benchmarks |
| Runevision Erosion Filter | MPL-2.0, a function of original CC BY-NC-SA | prohibited |
| Shaders by Quilez | MIT for algorithms, copyright for works | to be dismissed; the idea is free |

**The rule followed:** no line is taken, even under MIT. Relief is written in clean room since this research and articles, as `Relief.hlsli` has been since complexplanet.

## 6. Recommended architecture

### 6.1 Overview

| Layer | Scales | Where, when | What it gives |
|---|---|---|---|
| 1. Tectonic precalculation | plates from 1 000 to 10 000 km; fields to 10 km | CPU, at startup, approximately 1 to 3 s | plates, typed boundaries, distances, speeds, ages, rock, elevation |
| 2. Large forms | 6 000 km to 50 km | shader, by vertex, from map | crust, plateau, chains, pits, arcs, rifts, ridges, hot spots |
| 3. Detail | 50 km to 13,5 m | shader, per vertex, noise | oriented ridges, ravines, plains, terraces, volcanoes |
| 4. Level 0 | above 20 to 40 km | on startup, CPU then GPU | eroded relief, drainage, lakes, flow |

**Final relief, by vertex:**
- above two cells of the 0 level: the eroded relief of the 0 level, read in cubic B-spline;
- on the sea, and wherever water does not act: the large shapes of the layer 2;
- below: detail of layer 3, weighted by geology and extinct in the valleys of level 0.

### 6.2 The precalculation at startup

**The grid:** the cube of the planet of `PlanetMap`, 6 × 1 024², 9,8 km in the center of a face, 4,6 km at the corners. Its neighbors across the edges already exist, `ForNeighbours`.

**The steps, all deterministic, on a single wire or without variable order:**
1. **Cratons and continents.** Continental cores laid by drawing from the farthest point, then grown by a noise cost filling up to the desired part. About 65 % continental crust for 60 % land, the rest in sunken plateaus. Independent of plates: where a continent overlaps a boundary collisions and rifts arise.
2. **The plates.** 12 to 20 plates, sizes in power law as on Earth (Bird 2003). Germs by the most distant point, competing growth at noise cost: irregular borders, never arcs of great circle.
3. **The movements.** One Euler pole and one angular velocity per plate, from 1 to 10 cm/an; continental plates slower than oceanic plates.
4. **Borders.** In each boundary cell, the relative velocity (ω_a − ω_b) × p, projected on the normal and the tangent. The type is:
   - convergent, with its polarity: the oceanic plunges under the continental, the oldest under the youngest; two continents collide;
   - divergent: ridge in the sea, rift on a continent;
   - transformation, if shear is dominant.
   Dorsal segments shifted by transforming faults, all 100 to 500 km.
5. **Distance fields.** A propagation of the nearest germ on the grid, like the existing Priority-Flood: signed distance to the convergent front, distance to the divergent axis, signed distance to the continental margin, distance to the transforming fault. Accuracy to the kilometer; smoothed on two texels.
6. **Ages.**
   - Oceanic crust: the distance to its ridge at half the expansion speed.
   - Active channels: from 0 to 50 Ma according to the assumed duration of the convergence.
   - Ancient sutures, inside the continents, between cratons: from 100 to 1 000 Ma, drawn by seed. This is the synthesised history, without simulation: the Appalachian and Ural of Exolune.
7. **The rock.** A continuous clue: crystalline base of cratons, sedimentary basins, volcanic rocks of arcs and hot spots, pleated rocks of chains. It regulates the noise and erodibility.
8. **The uprising.** Positive on converging fronts, according to the speed of convergence and a cross profile; negative in the forelands and rifts; zero on cratons.

**Storage:** two RGBA16F cubes of 1 024², mipmapped as `planetMap`, about 100 MB in total with the mips.
- **The first:** signed distance to the converging front; distance to the diverging axis; signed distance to the continental margin; speed of convergence to the nearest front.
- **The second:** age, of the crust or of the orogenesis; type of collision, in continuous weight of ocean to continent; rock index; elevation.
- **The direction of the folds is not stored:** it is perpendicular to the gradient of the distance to the front, read by two neighboring readings.
- **The semifloat is sufficient:** distances per kilometer on 20 000 km hold in 11 bits of mantisse to 10 km close; the fine distance is reconstructed by the profile.

**The resolution:** 1 024² for fields, the grid of the current map. The shapes they carry make more than 50 km, at least five texels. 512² would be enough for the test; 2 048² would not bring anything that the noise does not better.

**Time, estimated:** the steps 1 to 8 are fills and spreads on 6,3 millions of cells, like the Priority-Flood that already runs at every start. From the order of a second to a few seconds in C++. To be measured.

### 6.3 The large forms

**The principle:** the map gives smooth distances; the shader makes clear shapes by analytical profiles. Sharp edges, the axis of a pit, the edge of a graben, come from the profile, never from the texels.

**The starting values,** derived from published geophysics, to be set for 60 % of land, summits from 5 to 8 km and pits at −8 km:

| Forme | Where | Profile |
|---|---|---|
| Craton | far from any borders, on the continental crust | +200 to +600 m, ripples from 500 to 2 000 km from ±300 m: intracratonic basins and domes |
| Continental shelf | Coast to slope break | up to −130 m; 80 to 300 km wide on passive margin, 10 to 40 km on active margin |
| Talus and glacis | after break-up | up to −3 000 m on 50 to 100 km, then the abyssal plain |
| Oceanic crust | everywhere at sea | −(2 500 + 350 √age) m, age in Ma, capped at −6 000 m (Parsons and Sclater 1977; Stein and Stein 1992) |
| Dorsal lens | Oceanic divergent axis | Axial valley of 1 to 2 km deep, 20 to 30 km wide; transforming faults and perpendicular fracture zones |
| Rapid back | idem, rapid expansion | an axial dome of a few hundred meters |
| Fosse | Front converging, side plunging | −8 000 m at axis, 50 to 100 km wide; external burr by bending, w₀ e^(−x/α) cos(x/α), α ≈ 70 km, +300 to +500 m |
| Island arc | ocean against ocean, at 150 to 300 km from the front | rosary of cones, some islands above the sea, and a back-arc basin |
| Cordillera | ocean versus continent | a chain of 150 to 400 km wide, up to 6 to 7 km depending on convergence, a volcanic arc on its ridge, a high plateau behind if convergence is strong |
| Collision chain | continent against continent | 200 to 400 km wide, 6 to 8 km; a plateau of 4,5 to 5 km up to hundreds of km behind if collision is strong |
| Basin of the Outback | in front of the chain, on the diving plate | a bend of −200 to −500 m before filling, α ≈ 100 to 150 km; level 0 the plain ceiling |
| Continental rift | axis on a continent | a graben of 40 to 60 km, bottom 1 to 2 km under shoulders of +0,5 to +1,5 km; a narrow sea if it opens |
| Faille transformante | on a continent | a linear valley, ±200 m, diamond-shaped pools |
| Hot spot | seed-drawn, with their drag along the movement of the plate | a bulge of +1 km on 500 km; volcanic shields that age and sink along the trail |
| Old chain | intracontinental suture | amplitude decreases with age, A₀ e^(−âge/τ), τ from 100 to 200 Ma, one adjustment; 1 to 2 km to 300 Ma |

**The hypsometry that comes out is bimodal,** as on Earth: from continents to +500 m, from oceans to −4 to −5 km. complexplanet has only one spread mode.

**Left-handedness:** a slight left-handedness of the reading coordinates, from 5 to 50 km, filtered by the grid cell, breaks what the profiles would have too regular. It is applied before any card reading, so that all layers remain agreed.

### 6.4 Medium and fine scales

**The bricks:** `Noise.hlsli` remains as it is: fBm, billow, ridged, Voronoi, turbulence, and their filtering. Two bricks are added, written here:
- **a noise with its analytical derivatives,** for attenuation by the slope at the Quilez and to orient the ravines;
- **a noise oriented,** ridge aligned on a field of directions. Not a stretching of coordinates, shearing where the direction turns: fixed orientation cells mixed between neighbors, the idea of Grenier's phase patterns 2024 and runevision pivots.

**What geology modules:**
- **The young chains:** a ridged of 8 to 12 octaves, aligned on the folds, of amplitude given by the profile of the chain; ravines on the slopes. The strongest roughness.
- **The old strings:** the same noise, thin octaves attenuated by age, rounded peaks. roughness average.
- **Sedimentary plateaus and basins:** terraces where the rock is lit and the dry climate, today's badlands at their geological place.
- **The cratons:** soft billow, base hills.
- **Arcs and hot spots:** cones laid by hacked cell along the arc or trail, crater at the top, slope of 5 to 30° depending on type.
- **The ocean floor:** abyssal hills elongated parallel to the ridge, buried under sediments as the crust is old.

**The roughness `gRoughness`:** calculated from the same fields, continues: 0,1 on the plains, 0,3 on the cratons, 0,5 on the old chains, 0,6 on the terraces, 1 on the young chains.

**Filtering:** Each band reads `gMaxFrequency`, as today. Each analytical profile has a width of at least two grid cells, as the rounding of the ridges: a pit seen of 400 km is not a pixel slot.

### 6.5 The link with erosion

**What the 0 level expects in input, and what it finally receives:**

| Level entry 0 | Today | Tomorrow |
|---|---|---|
| U-Uprising | proportional to complexplanet, plus a minimum, reversed to its heights | that of converging fronts, zero on cratons, negative in the forelands and rifts |
| Initial relief | complexplanet without its valleys | the large forms, `ReliefElevation(p, false)`  |
| Erosion K | uniform | Rock-based: strong on sediments, weak on the base (Cordonnier 2018) |
| Basic level | sea and terminal lakes | idem, the coast from the continental margin |
| Rain | decreasing inward | idem, then the shadow of chains, which tectonics finally places |

**Why it is easier for him:**
- **Chains are where the uprising holds them.** At equilibrium, the height of a string comes from U/K and the drained area; the level 0 no longer has to copy them. The inversion of the A3 spike can remain, towards the heights of the profiles, but it starts from an already coherent rise.
- **The cuvettes have a cause.** The outlying basins, rifts and arid interiors are actual cuvettes; the rest drains to the sea by construction.
- **Basins are land size.** Coastal chains, rifts and sutures cut the continents into several basins; the giant basin of spike A2 came from an interior without organized relief.
- **Rivers bypass the mountains.** The massifs are those that erosion has left standing; they no longer come from a noise that the trace ignores.

**The solver, from cheapest to most expensive:**
1. **Analytical balance** (Tzathas 2024): Priority-Flood, drained area, then the integral χ along the network, two or three times, because the network depends on the relief. A few seconds estimated.
2. **FastScape transient on GPU** (Schott 2023), if balance lacks variety. A few seconds estimated for a thousand steps.
3. **One disk cache per seed,** waiting for the GPU, like the current bake `x64\Erosion`.

**What it does, and how relief uses it:**
- **The eroded relief** replaces the large shapes above two of its cells, on the lands; read in B-spline, by mips.
- **The drained area and the water level** give the mask of the valleys: the noise of the middle layers extinguishes on the bottom, which follows the profile of the river. The bottom has the width of the bed, then of the plain, according to the flow (`recherche-dendry.md`).
- **The slope of the 0 level** orients the ravines: they descend towards its rivers.
- **The average remains correct:** the map is calculated with the octaves filtered to two texels and replaced by their average. The level 0 sees the average height of the relief that it erodes.

**What remains open:** the valleys between 20 km and 1 km. The noise oriented therein carves longitudinal valleys, parallel to the folds, which can close. Two answers, in order:
1. **The mask and the slope to the nearest river,** in the function itself: cheap, to measure.
2. **The fine levels of Dendry,** by tiles around the camera, hanging on the rivers of the level 0 (`recherche-dendry.md`, section 6).

### 6.6 What remains of the project

- **The interface:** `ReliefElevation(double3 p)` and `ReliefElevation(double3 p, bool valleys)`.
  - With `valleys`, the complete relief, level 0 including.
  - Without, the form before erosion, the one that reads the level 0. She never reads her own outputs.
- **`gRoughness`:** written at each call, from 0 to 1, calculated from geological fields.
- **Double precision:** only for cutting octaves on the grid, as today. Map readings are made in float: 0,4 m of error of direction against 10 km of texel.
- **Filtering by the grid cell:** `gMaxFrequency`, `gCreaseMaxFrequency`, `MapLevel` for the mips cards.
- **Stability when the grid cell slides:** everything is anchored on the planet; no calculation depends on the anchor or the camera.
- **The orders of magnitude:** about 60 % of land, summits from 5 to 8 km, pits at −8 km, in `MAX_ELEV` = 8 192 m. The land share is set at the step 1 of the precalculation, the height of the peaks by profiles and elevation.
- **The port CPU of the benchmarks:** as `tools/hydro/cp.py` for the current relief, a port numpy of the precalculation and profiles, for `banc_carte.py` and the planks.

### 6.7 Cost per vertex, estimated

| Poste | Today | Tomorrow, estimated |
|---|---|---|
| Map readings | 0 | 2 cubes in B-spline, about 8 bilinear readings; plus the level 0 |
| Analytical profiles | 0 | a few dozen operations |
| Turbulences | 12, at 3 noise functions each | a left shift of 2 octaves, 6 noise functions |
| Octaves | about 114 in generators, and recalculated subgraphs | 30 to 70 depending on the terrain, in real branches |
| Total | about 340 ratings of noise | 40 to 80, to be measured |

### 6.8 The new rules, for `principes.md`

- **Geology decides, the noise details.** Any form of more than 50 km comes from the tectonic map; no noise has an octave above.
- **A pre-calculated map can carry geometry,** under three conditions: anchored on the planet, read in cubic B-spline and by mips, above two of its texels only. It replaces the rule “data, never geometry”, which the 0 level already violates on `erosion-niveaux`.
- **A map that bears a shape is never read in bilinear:** the slope jumps at every texel, and the light draws the grid.
- **Any analytical profile has a width of at least two grid cells.**
- **Nothing thinner than the level 0 blocks one of its waterways.**
- **Each profile follows a published law,** cited with its source: ocean depth by age, bending of the lithosphere, width of the plateaus.

## 7. The plan in stages

Each stage is judged in flight, with a `tools/tests/<date>.txt` and `tools/lance.ps1` file, on several seeds and several locations. Each is on the experiment `piste/relief-tectonique`, with a setting that returns to the current relief; the current relief remains the unchanged rendering until the decision.

| Stage | Contents | What is judged in flight | Measure |
|---|---|---|---|
| 0 | Decide on the rule of the card that carries the geometry; write the spec | none | decision |
| 1 | The tectonic precalculation and its diagnostic views, `MYPLANETENGINE_VIEW` : plates, boundary type, age, rock. The relief does not change | from orbit, plates and their boundaries on the current planet: shapes, sizes, irregularity | start-up time added; plate sizes against Bird 2003 |
| 2 | The large forms alone, on the current bricks for the detail | from orbit and at 50 km: continents, plateaus, chains along fronts, pits, ridges, rifts | 60 % of land; bimodal hypsometry; summits from 5 to 8 km; pits at −8 km |
| 3 | Modulated detail: noise oriented by folds, age, rock, `gRoughness`  | from 10 km to 100 m: ridges parallel to the chains, rounded old chains, terraces of dry pools | quality benchmark: no gradient p95 of more than 10 %; flat descent benchmark |
| 4 | The level 0 on the tectonic elevation, at analytical equilibrium; its eroded relief above two cells; the mask of the valleys | at the sources of rivers, where they crossed the mountains: they circumvent them; ponds and lakes |  `level0_cut.py` : share of rivers dug more than 50 m below ground, vs. 44 %; basin sizes vs. Earth; correlation of masses with 2 layer |
| 5 | Arcs, hot spots, transforming faults, abyssal hills | the island rosaries, the volcanoes, the ocean floor seen at low altitude | number and spacing of arc volcanoes |
| 6 | Coasts by type of margin: broad plateaus and beaches on passive margins, steep coasts and cliffs on active ones | along several ribs of each type | parts of coast of `recherche-cotes.md`, step 3 |
| 7 | The fine valleys: Dendry by tiles, hung at level 0 | mountains at 2 km: tree tributaries, without basin | Lakes less than 1 % of land at 300 m; benchmark of jitter |
| 8, if necessary | A simulated story in Cortial style, if the snapshot seems too regular | continents assembled of terranes, multiple sutures | — |

**The 2 step is the first true judgment.** It shows on its own whether the planet has a legible orbit geology. The steps 1 and 2 do not affect the 0 level or materials.

## 8. Risks and issues

- **The decision of the card rule,** step 0, taken the 2026-10-31 (`principes.md`). Without it, the 0 level could not carry the relief above 20 km, and the architecture lost its 4 layer.
- **Startup time is longer:** a few seconds for plates, a few seconds for 0 level on GPU, maybe a minute on CPU. A cache per seed limits the worst case.
- **B-spline readings at the edges of the cube:** offset readings cross the faces; to be checked at the corners, where three faces meet.
- **The noise oriented:** where the direction of the folds turns fast, at the elbows of the chains, the mixture of cells can blur the ridges.
- **The cinematic snapshot lacks history:** young chains, continents without terranes. The synthesized sutures of the 1 step are the parade; the step-by-step simulation, the 8 step, the recourse.
- **The level 0 to 20 km:** it does not see the valleys between 20 and 1 km. The open question of the section 6.5.
- **Reddit posts:** not read. He can change a recommendation if he brings a method missing here.

## 9. Sources

**The post and recent projects**
- The post reported: https://www.reddit.com/r/proceduralgeneration/comments/1xhximl/procedural_plate_tectonics_simulation_for_a/ (unread, access denied).
- World Orogen : https://github.com/raguilar011095/planet_heightmap_generation; https://orogen.studio/
- Frozen Fractal, "Around The World, Part 29: One year in", 2026: https://frozenfractal.com/blog/2026/2/14/around-the-world-29-one-year-in/
- DasTobi, « Plate Tectonics Simulation, Oceans and Mountains », 2026 : https://www.youtube.com/watch?v=cP-5czRuTII

**Procedural tectonics**
- Cortial, Peytavie, Galin, Guérin, *Procedural Tectonic Planets*, CGF 38(2), 2019 : https://perso.liris.cnrs.fr/eric.galin/Articles/2019-planets.pdf ; https://onlinelibrary.wiley.com/doi/abs/10.1111/cgf.13614
- Gainey, *Procedural Planet Generation*, Experilous, 2014: https://www.experilous.com/1/blog/post/procedural-planet-generation (offline the 2026-10-31).
- Red Blob Games, *1843-planet-generation* : https://github.com/redblobgames/1843-planet-generation
- PlaTec : https://github.com/Mindwerks/plate-tectonics; WorldEngine : https://github.com/Mindwerks/worldengine
- tectonics.js : https://github.com/davidson16807/tectonics.js ; SimpleTectonics : https://github.com/weigert/SimpleTectonics ; https://github.com/FreezeDriedMangos/realistic-planet-generation-and-simulation
- Michel, Emilien, Cani, *Generation of Folded Terrains from Simple Vector Maps*, Eurographics short 2015 : https://diglib7.eg.org/bitstream/handle/10.2312/egsh.20151019.077-080/077-080.pdf

**Rise and erosion**
- Cordonnier et al., *Large Scale Terrain Generation from Tectonic Uplift and Fluvial Erosion*, CGF 35(2), 2016 : https://hal.archives-ouvertes.fr/hal-01262376 ; https://www.cs.purdue.edu/homes/bbenes/papers/Cordonier16CGF.pdf
- Cordonnier et al., *Sculpting Mountains: Interactive Terrain Modeling Based on Subsurface Geology*, TVCG 2018 : https://www.cs.purdue.edu/homes/bbenes/papers/Cordonnier18TVCG.pdf
- Schott et al., *Large-scale Terrain Authoring Through Interactive Erosion Simulation*, ACM TOG 42, 2023 : https://hal.science/hal-04049125v1 ; https://github.com/H-Schott/StreamPowerErosion
- Schott et al., *Terrain Amplification using Multi-scale Erosion*, ACM TOG 43(4), 2024 : https://h-schott.github.io/publications/mserosion/publi_mserosion.html ; https://github.com/H-Schott/MultiScaleErosion
- Tzathas, Gailleton, Steer, Cordonnier, *Physically-based Analytical Erosion for fast Terrain Generation*, CGF 43(2), 2024 : https://diglib.eg.org/handle/10.1111/cgf15033
- fastscapelib : https://github.com/fastscape-lem/fastscapelib ; fastscape : https://github.com/fastscape-lem/fastscape
- Astrolith, *Real-time planet scale erosion* : https://gamedev.net/blogs/entry/2275217-real-time-planet-scale-erosion

**Hydrology and Amplification**
- Génevaux et al., *Terrain Generation Using Procedural Models Based on Hydrology*, ACM TOG 32(4), 2013: https://www.cs.purdue.edu/homes/bbenes/papers/Genevaux13ToG.pdf; https://hal.archives-ouvertes.fr/hal-01339224
- Derzapf et al., *River Networks for Instant Procedural Planets*, CGF 30(7), 2011 : https://diglib.eg.org/handle/10.1111/v30i7pp2031-2040
- Gaillard et al., *Dendry: A Procedural Model for Dendritic Patterns*, I3D 2019 : https://www.cs.purdue.edu/cgvlab/www/resources/papers/Gaillard-2019-Dendry_A_Procedural_Model_for_Dendritic_Patterns.pdf ; code GPL-3.0 : https://github.com/mgaillard/Noise
- Guérin, Digne, Galin, Peytavie, *Sparse Representation of Terrains for Procedural Modeling*, CGF 35(2), 2016 : https://diglib.eg.org/handle/10.1111/cgf12821 ; https://github.com/eric-guerin/terrain-amplification
- Galin et al., *A Review of Digital Terrain Modeling*, CGF 38(2), 2019 : https://www.cs.purdue.edu/homes/bbenes/papers/Galin19CGF.pdf
- Grenier, Guérin, Galin, Sauvage, *Real-time Terrain Enhancement with Controlled Procedural Patterns*, CGF 43(1), 2024 : https://diglib.eg.org/handle/10.1111/cgf14992
- Argudo et al., *Terrain descriptors for landscape synthesis, analysis and simulation*, Eurographics 2025 : https://hal.science/hal-05246144/document ; https://github.com/oargudo/terrain-descriptors
- Borg et al., *Authoring Terrestrial Planets with Diffusion Models*, CGF 45(2), 2026 : https://diglib.eg.org/handle/10.1111/cgf70390
- *Terrain Diffusion*, arXiv 2025: https://arxiv.org/abs/2512.08309

**The noise functions eroded**
- Quilez, articles on the noise and its derivatives: https://iquilezles.org/; the license change of 2021: https://github.com/huwb/volsample/issues/1
- Johansen, *Fast and Gorgeous Erosion Filter*, 2026 : https://blog.runevision.com/2026/03/ ; https://www.shadertoy.com/view/wXcfWn ; https://gist.github.com/runevision

**The games**
- McKendrick, *Continuous World Generation in No Man's Sky*, GDC 2017 : https://gdcvault.com/play/1024265/Continuous-World-Generation-in-No
- Murray, *Building Worlds Using Math(s)*, GDC 2017 : https://gdcvault.com/play/1024514/Building-Worlds-Using
- *Generating the Universe in Elite: Dangerous*, 80.lv : https://80.lv/articles/generating-the-universe-in-elite-dangerous/
- Star Citizen, Planet Tech v5: https://starcitizen.tools/Planet_Tech_v5; https://theimpound.com/pages/star-citizen-starchitect-planet-tech-v5
- SpaceEngine, *First procedural terrain*: https://spaceengine.org/news/blog100531/

**The geophysics of profiles** (published laws, without code)
- Parsons, Sclater, An analysis of the variation of ocean floor bathymetry and heat flow with age, JGR 82, 1977, doi:10.1029/JB082i005p00803.
- Stein, Stein, *A model for the global variation in oceanic depth and heat flow with lithospheric age*, Nature 359, 1992, doi:10.1038/359123a0.
- Bird, *An updated digital model of plate boundaries*, G³ 4(3), 2003, doi:10.1029/2001GC000252.
- Turcotte, Schubert, *Geodynamics*, the bending of the lithosphere: external burrelet and outlying basins.
- Perron, Royden, *An integral approach to bedrock river profile analysis*, 2013 : https://dspace.mit.edu/handle/1721.1/75359
- Braun, Willett, *A very efficient O(n), implicit and parallel method to solve the stream power equation*, Geomorphology 180, 2013.
- Barnes, Lehman, Mulla, Priority Flood, 2014.
