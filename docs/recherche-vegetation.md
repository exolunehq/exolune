# Search: vegetation, from tree to forest view from orbit

Status: search and step 1 do the 2026-10-25, tag `piste/vegetation`; v2 and v3 on the same day, tags `piste/vegetation-v2` and `piste/vegetation-v3`, sections "v2" and "v3" below. Code: `Vegetation.hlsli`, `PlantPlacement.hlsli`, the canopy in `PixelShader.hlsl`. The generated plants, `Vegetation.cpp` and `Plant*.hlsl`, are removed the 2026-10-30; their shapes and their measurements are in `log/recherche-vegetation-historique.md`. benchmarks : `tools/banc_vegetation.py`, `tools/saisons_terre.py`. Flight tests: `tools/tests/2026-10-25-vegetation.txt`, `-v2.txt`, `-v3.txt`.

**In brief:**
- **Planetary test of 2026-10-27:** play trees and shrubs, near mesh and distant impostors on the same instances; leaf bouquets, local normals and pre-calculated visibility compared off-screen. The first flights and rejected models are in the log of `vegetation-planetaire.md`.
- **Prototype compared the 2026-10-26 and 27:** free detailed models, volumetric aggregates inspired by Nanite Foliage and impostors multiviews; silhouettes enhanced by volumes, cost GPU measured, light and planetary relay to be pursued; see `log/prototype-vegetation-volumique.md`.
- **One plant population, two representations, one source:** `Vegetation.hlsli` says where grows what, how much, what size.
  - **Near:** objects on the planet grid, drawn by the game models, meshes near and impostors far (`vegetation-planetaire.md`); each whole as soon as it is drawn, from 8 to 5 pixels high.
  - **Far away:** the canopy in the matter of the ground, at the height of its trees: its share, its color, the relief of its crowns, the shadow it casts on the ground.
  - **The connection:** the canopy on the ground removes what the objects draw, like a boolean layer. A forest keeps its share of each pixel from 20 km to 50 m.
- **Where grows what, by laws published:**
  - the cold limit by growing season (Körner and Paulsen);
  - water by the aridity of Holdridge, the ceiling of Sankaran and the two states of Hirota and Staver, savannah and forest;
  - where are the woods, by two fields of noise like the pebbles: regions without trees, clearings in all forest, bushes by spots, a coat at the edges;
  - bare ridges, wooded hollows, by height on the regional soil;
  - conifers in cold, deciduous in warm, flat crowns in savannah, shrubs of dry lands.
- **The recommendation of then, made:** the impostors, as 5 pixels, `vegetation-planetaire.md`; the exact floor of the tiles kept from one frame to another, `optimisation.md`, round 3. The placement remains recalculated at each frame.

## State of the art

Search for 2026-10-25, primary sources except mentioned.

### Models of trees

- **Weber and Penn 1995** ([article](https://courses.cs.duke.edu/fall02/cps124/resources/p119-weber.pdf)):
  - a parametric model, trunk, branches, sub-branches, leaves, 3 to 4 levels;
  - 5 000 to 100 000 facets per shaft;
  - from far, the stems become lines and the leaves of the points, removed by masses: a tree of 100 000 facets to 2 km keeps only thirty. The goal: no waves of resolution between levels of detail.
- **The colonization of space,** Runions, Lane and Prusinkiewicz 2007 ([article](https://www.algorithmicbotany.org/papers/colonization.egwnp2007.html)):
  - branches grow to attractive points sown in the crown envelope, 1 500 to 12 000;
  - radii follow the pipe pattern, rⁿ = r₁ⁿ + r₂ⁿ, n from 2 to 3;
  - seconds to minutes per tree.
- **Self-organizing models,** Palubicki et al. 2009 ([article](https://www.algorithmicbotany.org/papers/selforg.sig2009.html)): buds fight for light; shape adapts to neighbours. Cost offline.
- **The L-systems** ([The Algorithmic Beauty of Plants](http://algorithmicbotany.org/papers/abop/abop.pdf)): parallel rewriting and turtle; inexpensive, but blind to the environment without extension.
- **SpeedTree** ([documentation](https://docs.unity3d.com/speedtree-runtime-sdk/manual/level-of-detail.html)):
  - a hierarchy: mesh branches, slings along the branches, leaf maps facing the camera, then panels;
  - levels of detail are merged by interpolated positions in the vertex shader: small branches are reduced to their axis, some maps shrink while others grow;
  - wind in stages: global swing, waving of leaves, branches, leaf turning.
- **The budgets of the games,** secondary source ([polycount](https://polycount.com/discussion/comment/2625799)): 15 000 to 22 000 triangles at the closest, 4 500 to 5 000 at the third level, 36 for a panel.
- **What we learned:** Generating a library of a few dozen shapes at startup is cheap; a single tree per instance is not. The forms of Weber and Penn are sufficient for crowns; the colonization of space will be valid for branches seen closely.

### The chain of levels of detail

- **The impostors octahedrals,** Ryan Brucks ([blog](https://shaderbits.com/blog/octahedral-impostors), [ImpostorBaker](https://github.com/ictusbrucks/ImpostorBaker), [80.lv](https://80.lv/articles/impostor-baker-for-ue4/)):
  - the object rendered from a grid of directions on an octahedron or semi-octahedron, color, normal and depth in an atlas;
  - current setting, 16 × 16 views on 2048², three mixed views per pixel, depth for parallax ([three.js](https://discourse.threejs.org/t/a-forest-of-octahedral-impostors/85735), [Godot](https://github.com/SIsilicon/Godot-Octahedral-Impostors));
  - the semi-octahedron gives more resolution to the side views, those of the foliage;
  - used in Fortnite for distant trees.
- **Panel clouds,** Décoret et al. 2003 ([article](https://graphics.cs.yale.edu/publications/billboard-clouds-extreme-model-simplification)): a few chosen plans under a limited geometric error; expensive in filling.
- **Forest as soil material,** Bruneton and Neyret 2012 ([article](https://diglib.eg.org/handle/10.1111/v31i2pp373-382), [video](https://www.youtube.com/watch?v=4Ghulpp6CPw)):
  - nearby trees rendered one by one;
  - beyond, a shader of the terrain that depends on the place, the view and the light covers the trees smaller than the pixel;
  - the transition from one to the other is done without pop or crenelage. Their times could not be read.
- **The geo-optical model,** Li and Strahler 1992 ([report](https://apps.dtic.mil/sti/pdfs/ADA263570.pdf)): crowns placed at random, a Boolean model; a pixel mixes crowns with sun and shadow, ground with sun and shadow; the hot spot when the view aligns with the sun. A reflectance of forest in closed shape, density and shape of crowns.
- **Nanite foliage,** Unreal 5.7, experimental ([documentation](https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage)):
  - instanced part assemblies, up to 65 000 by mesh;
  - from afar, the voxels of 4 × 4 × 4 which keep a distribution of normals;
  - wind by bones, 100 000 os for 0,1 ms;
  - transparency maps and wind moving the summits are not recommended.
- **Fades:** Unreal's rasterized fade leaves a pop at the end of the fade; SpeedTree and Weber and Penn make it grow or shrink, without a frame.

### The great worlds

- **Horizon Zero Dawn,** van Muijden, GDC 2017 ([slides](https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf)) :
  - deterministic, locally stable; the world built around the player by computational passes;
  - a density map by type, compared to a fixed threshold pattern;
  - more 500 types, more 100 000 objects, about 250 µs of GPU on average.
- **The Vegetation of Horizon,** Sanders, GDC 2018 ([GDC Vault](https://gdcvault.com/play/1025066/Between-Tech-and-Art-The)): not read. **Forbidden West** ([McLaren](https://www.guerrilla-games.com/read/adventures-with-deferred-texturing-in-horizon-forbidden-west)): A visibility pre-pass for foliage and transparency geometry.
- **Ghost of Tsushima** ([Grass](https://gdcvault.com/play/1027214/Advanced-Graphics-Summit-Procedural-Grass), [vent](https://gdcvault.com/play/1027124/Blowing-from-the-West-Simulating)): tile-generated strands on GPU, in Voronoi cluster; a wind of noise 2D shared by the CPU and the GPU; in the distance, textures.
- **Far Cry 5** ([Carrier, 2018](https://blog.playstation.com/2018/03/22/the-procedural-world-generation-of-far-cry-5/)): offline, in Houdini, on 100 km²; species fight for space according to sunshine, humidity and water. **Far Cry 4** ([McAuley](https://gdcvault.com/play/1022235/Rendering-the-World-of-Far)): close-up modeled leaves, tesselated and moved panels from far away.
- **Microsoft Flight Simulator,** Asobo ([Fuentes](https://www.asobostudio.com/files/inline-images/Designing_Terrain_System_Fuentes_Lionel.pdf)): trees placed based on coverage data, photogrammetry in cities; tree drawing distance not found.
- **Unreal 5, PCG** ([modes](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-pcg-generation-modes-in-unreal-engine), [GPU](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-pcg-with-gpu-processing-in-unreal-engine)): nested grids, large objects on the coarse grid; one generation radius per level; nodes on GPU.
- **Outerra,** author's forum, 2009 ([file](https://forum.outerra.com/index.php?topic=15.0)): panels issued by tile according to a coverage map, altitude, slope, curvature and a noise fractal; at most 44 000 trees per km², about 200 000 per scene.
- **Star Citizen,** secondary source ([wiki](https://starcitizen.tools/Planet_Tech_v5)): Planet shader estimates distant color, including objects not yet loaded, to remove pop.

### Biomes and placement

- **Whittaker,** redesigned by Ricklefs ([digitized data](https://github.com/valentinitnelav/plotbiomes)): the tundra under −5 °C approximately; the boreal forest of −7 to +4 °C; the transition from temperate to tropical to 19 °C; forests, woods and steppes separated by precipitation, from a few tens to a few hundred cm.
- **Holdridge** ([Lugo et al. 1999](https://research.fs.usda.gov/download/treesearch/30306.pdf)): biotemperature, average temperatures between 0 and 30 °C; potential evapotranspiration, 58,93 mm per degree; humidity provinces by its relation to precipitation: humid below 1, subhumid from 1 to 2, semi-arid from 2 to 4, arid beyond.
- **The tree line** ([Körner and Paulsen 2004](https://edoc.unibas.ch/8594), [Paulsen and Körner 2014](https://edoc.unibas.ch/33369)):
  - The growing season, days more than 0,9 °C, less than 94 days and average 6,4 °C in March in San Antonio
  - 6,7 ± 0,8 °C in the soil at 46 sites from 68° N to 42° S;
  - The Earth, from 3 100 to 4 100 m in the tropics, 4 200 m to 28° N, 2 200 m in the Alps, 1 100 m to 61° N, the sea to 68 to 70° N (compilation of Körner 1998, secondary source).
- **Tree cover and water:**
  - Sankaran et al. 2005 ([article](https://researchspace.csir.co.za/bitstream/handle/10204/2072/sankaran_2005.pdf)): in 854 African savannahs, woody cover at most 0,14 MAP − 14,2 %, from 101 to 650 mm; no trees below 101 mm; beyond 650 mm, the canopy may close;
  - Hirota et al. 2011 ([article](https://gael.univ-grenoble-alpes.fr/sites/default/files/Mediatheque/Files/EC2%C2%B0C%20-%20hirota%26al_2011_science.pdf)): three states, forest to 80 %, savannah to 20 %, no trees to 5 %;
  - Staver et al. 2011 ([article](https://researchspace.csir.co.za/bitstream/handle/10204/4802/Staver_2011.pdf)): forest and savannah bistable from 1 000 to 2 500 mm, fire cut.
- **Density,** Crowther et al. 2015 ([article](https://cdanfort.w3.uvm.edu/csc-reading-group/crowther-nature-2015.pdf)): 3 040 billion trees over 10 cm, 43 % tropical, 24 % boreal, 22 % temperate. Densities per hectare and per biome are only readable on one figure: unconfirmed.
- **The forms,** based Tallo, Jucker et al. 2022 ([article](https://eprints.gla.ac.uk/272945/1/272945.pdf)), medians of 498 838 trees, crown diameter by height: humid tropical forest 0,24; temperate deciduous 0,36; temperate resinous 0,31; boreal 0,21; Mediterranean 0,53; savannah 0,34; drylands 1,07. The radius of the crown grows as H^0,7.
- **The bushes of the deserts,** Larrea: 1,7 m average, 14 % of the soil, 24 % with other bushes in Santa Rita ([FluxLetter](https://fluxnet.org/wp-content/uploads/FluxLetter_Vol2_No4.pdf)). **The scrub and the chaparral:** cover and height not confirmed.
- **Slopes:** 82 % of forests on slopes less than 15°, 4 % beyond 30° ([SND](https://snd.se/en/catalogue/dataset/snd1296-1)); tropical mountain forest at 75 % on more than 27°; avalanches start from slopes more than 30° without dense forest.

### The structure of forests

- **Trees are clustered,** almost all species from six plots of 25 to 52 ha (Condit et al. 2000, [Summary](https://pubmed.ncbi.nlm.nih.gov/10827950/)).
- **Hole-holes** (Asner et al. 2013, [article](https://pmc.ncbi.nlm.nih.gov/articles/PMC3626694/)): 5,9 million holes on 125 581 ha; their sizes in exponential power law 1,83 ± 0,09; a hole descends to 2 m from the ground.
- **Edge clearings** (Laurance 2002): many species avoid clearings less than 100 m. Depth: not confirmed.
- **Natural thinning,** Reineke's law ([summary](https://en.wikipedia.org/wiki/Stand_density_index)): log N = −1,605 log D + k.
- **Height** ([Lang et al. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10627820/), [Simard et al. 2011](https://earthobservatory.nasa.gov/IOTD/view.php?id=77637)): more than 30 m in the humid tropics, up to 65 m; less than 20 m in boreal forest; 3 m on average at 70° N.

### The color of a canopy

- **A tablecloth is darker than a sheet:** it hides its own shadows.
- **Visible and near infrared,** Cescatti et al. 2012 ([article](https://www.cen.uni-hamburg.de/en/icdc/data/land/docs-land/cescattietal-rse-2012.pdf)), albedo from 0,3 to 5 µm: persistent coniferous 0,05 to 0,11; deciduous 0,11 to 0,15; savannah 0,14 to 0,19; grassland 0,16 to 0,22.
- **In blue,** Moody et al. 2007 ([Summary](https://collaborate.umb.edu/en/publications/northern-hemisphere-five-year-average-2000-2004-spectral-albedos-/)): 0,03 for softwoods, 0,36 under snow.
- **The Amazon,** 0,03; 0,06; 0,025 in red, green and blue: the dark anchor of the climate palette (`tools/palette_biomes.py`).

### Published costs

- Horizon: 250 µs for more 100 000 objects.
- Nanite: 500 000 trees from 1 to 10 millions of polygons in The Witcher demo 4, to 60 frames per second on PS5.
- impostors: 16 × 16 views on an atlas of 2048²; 12 to 36 summits per map.
- Outer: about 200 000 panels per stage.

## The recommendation

**Three architectures fit our rules,** fixed place on the grid, no pop, one pixel shows its average:
1. **A stateless placement on the planet grid, indirect drawings:** HZD, Proland, Outerra, PCG. This is the system of nearby objects.
2. **Two analytically connected representations:** Bruneton and Neyret, Li and Strahler, Star Citizen. The material of the ground carries the cover, the color, the shadow and the relief of the crowns, and removes what the objects draw.
3. **Clusters and continuous voxels,** Nanite foliage: best match with pixel average, but mesh shaders, a level of detail per cluster and a rendering of voxels.

**Retained: 1 and 2, in this order of work.**
- **Step 1, made:** nearby objects and canopy on the ground, a single source, the Boolean connection.
- **Step 2: one plant cache per tile.** The placement is recalculated at each frame; its cost per plant limits the range of objects to 24 pixels. A tile rated once, kept as long as it remains within range, divides it by the number of frames.
- **Step 3: from impostors for the band of 6 to 24 pixels,** generated at start from our shapes, half octahedral, 16 × 16 views. Plants would emerge from the ground at 6 pixels, like pebbles, instead of 24.
- **Next:** wind, undergrowth and forest soil, shadows cast by plants, more species.

## Step 1: what is done

### Where grows what: `Vegetation.hlsli`, `VegetationAt`

**Engine climate:** the average annual temperature and humidity, the log of precipitation from 100 to 3 000 mm (`BiomePalette.hlsli`). Everything else follows from that.
- **Seasons:** a sinusoid around the annual average, of half-amplitude 3,5 + 18 sin² of latitude.
  - Fitted on the Earth's lands, TerraClimate 1991-2020 (`tools/saisons_terre.py`).
  - On the months themselves, the measured sine wave gives the same growing season for 98 % of cells; the latitude model, for 92 %.
  - With it, in closed form: the growing season, its average and length; the Holdridge biotemperature.
- **Cold limit:** the average of the growing season, from 5,7 to 7,1 °C (`TREE_LINE`), 6,4 ± 0,7 from Körner and Paulsen, enlarged by what the pixel covers of temperatures (`SpreadStep`). With our amplitudes, 94 days never limit before the 6,4 °C: checked up to 21,5 °C amplitude.
- **Water:** aridity, precipitation on evapotranspiration of Holdridge.
  - The ceiling of Sankaran, rewritten with aridity at their evapotranspiration of 1 414 mm (24 °C).
  - The Savannah state: a quarter of the forest state under the ceiling, like the two modes of Hirota, 20 and 80 %; or 20 % as 650 mm, the elbow of Sankaran. Its trees are scattered among the settlements.
  - The forest state: of the settlements to 90 % of crowns (`STAND_COVER`), on the part of the lands that gives the 80 % of Hirota with the savannah between them; it gains from 1 000 to 2 500 mm to this evapotranspiration (Staver).
- **Settlements:** a field of the noise gradient of the planet, from 4 km to 8 m, above the threshold that leaves the good part of the lands. Clearings, groves and edges emerge as clear as its finest octave; what the pixel cannot show of the field broadens the threshold, the universal rule.
- **Shrubs:** 20 % of the soil between the settlements in dry lands (Larrea), from hyper-arid with nothing to wetlands where grass replaces them.
- **Species:** conifers under 3 °C annual mean, from 0 to 6 °C (Whittaker), deciduous above; lower and three times wider crowns in savannah, above 19 °C and under an aridity of 1.
- **The height of the canopy:** 40 m in warm and humid, less with the season and water: 15 to 20 m in boreal, 8 to 12 m in savannah (Simard, Lang, Tallo). The trees spread around 0,7 from this height, on 0,6 octave.
- **The ground:** neither on the bare rock, nor on the scree, nor on the beach. On snow, yes: our snow follows the annual average, and a boreal forest grows where winter is long.

### Plants near the camera: `PlantPlacement.hlsli`

- **The system of proximity objects, one more class:** one octave of heights per grid level, from 0,5 to 64 m; one candidate per cell of the quarter of the smallest height of the octave. In windows of 424 cells, a separate dispatch.
- **A Boolean placement:** randomly placed crowns cover 1 − e^(−footprint) of the ground. The imprint of each octave is the one that gives the coverage of the place, shared by the heights.
- **The two passes:**
  - **the light** limits each candidate by the climate on the ground of the mesh, and pulls the species like the heavy: deserts, tundra and seas do not go further;
  - **the heavy** puts the foot on the exact ground, decides on the parts of materials without their textures (`gMaterialTextures`), pulls the species, keep or not.
- **The placement counts each crown** as the Tallo disc seen from above: 0,3, 0,45 and 1,1 times the height, `PLANT_CROWN`.
- **The plant only grows where the grid cells are less than one and a half times its height.** Its trunk always descends to 15 % of its entire height under its foot: the ground of the mesh never discovers it.
- **His generated forms and their growth,** removed the 2026-10-30: `log/recherche-vegetation-historique.md`.
- **Light:** the shadow of the relief at its foot, by the horizon of the mesh; under the cover of the population, the light through its holes, less and less towards its summit, as on the ground.

### The forest beyond: the canopy in the ground, `PixelShader.hlsl`

- **His share:** the cover of the place, less what the objects draw at this distance, in Boolean layer: 1 − (1 − cover)^ (1 − drawn part). The ground under a crown drawn is hidden by it; only counts the one that it lets see.
- **Side,** a canopy hides more the ground, like the Boolean model: the part seen is 1 − (1 − part)^(1/cos of the view).
- **His color, his:** that of the Amazon for hardwoods, 0,7 of this for conifers, an olive gray for shrubs. The open ground keeps the color of the climate.
- **Its relief:** the detail bands of 2 to 16 m, the size of the crowns, illuminated as the ground.
- **Shadow on the ground:** the ground under crowns, drawn or not, receives the sun through their holes, (1 − cover)^(1/μ), and the sky by (1 − cover). The pebbles and the tufts also; under a population, the ground is the litter of trees, without the tufts or the rocks of a meadow.

### Diagnostic views and benchmarks

- **`MYPLANETENGINE_VIEW`:** `forest`, the canopy with the grid floor and the plants in white; `trees`, the trees alone; `biome`, the class; `temperature`, `humidity`, `season`, `altitude`, their values as they are.
- **`MYPLANETENGINE_NO_PLANTS`:** no plants, the canopy on the ground everywhere.
- **`tools/banc_vegetation.py` :** `biomes`, `orbite`, `raccord`, `lisiere`, `climat`, `tests`, `vues`, `releve`. The benchmark `cout`, which measured the plants generated among the objects, is removed with them.
- **Fix on the way:** Diagnostic view `objects` was drawing objects in `sun` view, the hint slipping when it arrived.

## Step 1: measurements

### Coverage by biome

Orbital view, eight sides of the planet, the middle of each disk (`banc_vegetation.py biomes`). Engine Biome: Holdridge humidity provinces, Whittaker temperatures.

| Biome | Share of land | Wooden tableware | Of which trees | Published |
|---|---|---|---|---|
| Tundra and Alpine | 26,7 % | 7,9 % | 7,8 % | 0; orbit pixel blends the wooded valleys |
| Boréal | 13,0 % | 54,0 % | 51,7 % | forest, mode at 80 % (Hirota), with its wooded tundra |
| Temperature humid | 14,4 % | 58,8 % | 58,0 % | forest, mode at 80 % |
| Dry temperate | 10,5 % | 28,7 % | 15,8 % | woods and steppes, under the ceiling of Sankaran |
| Tropical humid | 6,5 % | 55,5 % | 52,6 % | Forest and Savannah bistable from 1 000 to 2 500 mm (Staver) |
| Savannah and tropical dry | 13,1 % | 31,1 % | 15,3 % | Savannah, mode at 20 % (Hirota) |
| Desert | 15,9 % | 18,2 % | 3,1 % | Treeless below 5 %; shrubs 14 to 24 % (Larrea) |

- **Trees follow the published modes,** except for the bistable part: the humid tropical of the planet has mostly 1 000 to 2 000 mm, where forest and savannah share the land.
- **A comparison to the measured cover of the Earth by biome,** MODIS VCF or Hansen, remains to be done: a download.

### The line of trees

**Depending on latitude, the formula alone, its noise functions to zero** (`banc_vegetation.py formule`):

| Latitude | 0° | 10° | 20° | 30° | 40° | 45° | 50° | 55° |
|---|---|---|---|---|---|---|---|---|
| Planet | 4 320 m | 4 010 m | 3 480 m | 2 680 m | 1 610 m | 1 020 m | 440 m | Sea |
| Earth (Körner) | 3 100 to 3 900 m |  | 4 000 m to 19° N | 4 200 m to 28° N | 3 200 to 3 600 m | 2 200 m to 47° N |  |  |

- **On Earth, further to the pole:** 1 100 m to 61° N, 650 m to 68° N, the sea to 70° N.

- **In the tropics, the planet is Earth.** At medium latitudes, its line is 1,5 to 2,5 km lower: its climate is colder there, 2 °C at sea level at 45° against 10 to 12 °C on Earth (`Temperature`, 28 − 52 sin²). Vegetation follows the climate; it is the climate that diverges from the Earth.

**On six massifs, the trees fall half** (`banc_vegetation.py lisiere`, plane view of 20 km, exact values of altitude and season):

| Location | Season when trees fall halfway | Altitude of the line here | Formula only | Terre |
|---|---|---|---|---|
| 15° S, 120° E | 5,3 °C | 3 870 m | 3 630 m | 4 100 m to 18° S |
| 32° N, 18° E | 6,2 °C | 2 410 m | 2 450 m | 4 200 m to 28° N |
| 40° N, 149° W | 6,3 °C | 290 m | 1 560 m | 3 200 to 3 600 m |
| 40° S, 119° W | 5,8 °C | 1 730 m | 1 650 m | 3 200 to 3 600 m |
| 50° N, 151° E | 5,8 °C | 670 m | 400 m | 1 100 to 2 200 m, from 47 to 61° N |
| 50° S, 91° E | 6,2 °C | 640 m | 480 m | 1 100 to 2 200 m, from 47 to 61° N |

- **Season at line: 5,3 to 6,3 °C,** in the range of Körner and Paulsen, 6,4 ± 0,7, except from 0,4 °C to 15° S.
- **Altitude varies from place to place** from more than 1 km to 40° N: the noise regional temperature, ±2,5 °C.

### No pop: the share of forest per pixel in the descent

`banc_descente.py`, view `forest`, from the ground, fixed squares. Plate: `journal/2026-10-25-vegetation-descente.jpg`.

| Place, square | Hauteurs | Forest share |
|---|---|---|
| Temperature Temperature Temperature Temperature Temperatures Temperature Temperature Temperature Temperatured forest, 30,4° N 120,5° E, 2 km | 20, 10, 5, 3, 2 km | 85,4 ; 85,2 ; 85,0 ; 85,1 ; 84,9 % |
| Same, 200 m | 2 km, 1 km, 700, 500, 400, 300, 250, 200 m | 91,5 ; 90,4 ; 89,2 ; 91,4 ; 91,6 ; 90,1 ; 90,9 ; 91,6 % |
| Same, 50 m | 200, 150, 100, 70, 50 m | 94,4 ; 94,3 ; 94,1 ; 93,1 ; 92,1 % |
| Boreal forest, 49,6° S 90,5° E, 200 m | 2 km, 1 km, 700, 500, 400, 300, 200 m | 91,8 ; 91,5 ; 91,3 ; 90,7 ; 90,6 ; 90,9 ; 93,1 % |
| Savane, 10,4° N 119,5° W, 200 m | 2 km to 200 m | 35,3 to 33,3 % |

- **At ±1,5 point near,** where the trees pass from the canopy to the objects, from 700 to 200 m.
- **Before the Boolean connection,** the canopy removed the drawn part in simple subtraction: the forest lost 7 to 9 points between 500 and 300 m.

### The connection of the light

`banc_vegetation.py raccord`: the same view, with plants and without, the canopy on the ground everywhere; the ratio of the average light, linear, in the middle of the screen. Plate: `journal/2026-10-25-vegetation-raccord.jpg`.

| Forest | From the ground, 200 m | At 45°, 200 m |
|---|---|---|
| Moderate | 1,05 | 1,05 |
| Tropical | 1,07 | 0,99 |
| Boreal, on the snow | 0,89 | 0,70 |
| Savannah | 1,04 | 1,03 |
| Maquis | 1,02 | 1,01 |

- **The setting of then,** the albedo of the leaves of the generated plants, `LEAF_ALBEDO`, is removed with them: `log/recherche-vegetation-historique.md`.
- **Rest:** the boreal forest seen from a bias, 0,70: its narrow cones show more snow in the shadow than the Boolean model.

### Light seen from orbit

`banc_vegetation.py orbite`: with vegetation, on without, by biome.

| Tundra | Boréal | Temperature humid | Dry temperate | Tropical humid | Savannah | Desert |
|---|---|---|---|---|---|---|
| 0,92 | 0,62 | 0,82 | 0,83 | 0,95 | 0,93 | 0,89 |

- **Forests darken the planet,** especially the boreal, lying on the snow of our climate.
- **The climate palette already holds the forests of the Earth:** it counts twice their shadow where the planet poses. Correct it requires the cover of the trees of the Earth, MODIS VCF, to draw the color of the open ground: step to come.

### Floating, the jitter

- **No plant floats half a pixel,** on the fourteen test views; at most 0,3 pixel. Before the trunk descended to 15 % of the entire height, some nascent plants floated from 3,4 pixels in the mountain.
- **The jitter,** `banc_tremblement.py`, before and after, with and without smoothing:

| View | Before | With vegetation |
|---|---|---|
| Temperature Temperature Temperature, 2 m | 0,01 / 0,08 | 0,00 / 0,03 |
| Temperature Temperature Temperature, 150 m | 0,01 / 0,07 | 0,00 / 0,02 |
| Boreal Forest, 150 m | 0,07 / 0,36 | 0,00 / 0,03 |
| Savannah, 2 m | 0,00 / 0,01 | 0,00 / 0,00 |
| Grassy ridge, 1,7 m | 0,02 / 0,13 | 0,00 / 0,02 |

- **Never more than before:** plants do not move, and cover the shaking ground.

### The cost, the quality benchmark and the appearance

Measured on plants generated, removed the 2026-10-30: `log/recherche-vegetation-historique.md`.

## v2: where there are no trees

The 2026-10-25, on the user's verdict after the 1 step. Flight tests: `tools/tests/2026-10-25-vegetation-v2.txt`. Before and after plates: `journal/2026-10-25-vegetation-v2-avant-apres-1.jpg` and `-2.jpg`; the sixteen views: `journal/2026-10-25-vegetation-v2-tests.jpg`.

**The verdict:** trees everywhere, whatever the soil; too few shrubs; trees on the ridges; too simple shapes; trees that come out too late.

**In brief:**
- **A two-scale distribution rule, like pebbles:** a regional field leaves entire regions without trees; a spot field opens clearings of 30 m to 1 km in any forest. Trees and shrubs share it.
- **Spotted shrubs,** more numerous, in coat on almost all edges, above the tree line.
- **Ridges lose trees:** 0 to 2 % above 300 m on regional soil, compared to 11 to 83 % in v1; hollows retain 14 to 80 %.
- **Trees come out at 14 pixels instead of 24,** 1,7 times further away, roughly drawn in the distance; eight variants per species instead of four.
- **The cost of plant placement:** 0,6 to 1,6 ms at rest, compared to 0,4 to 1,2 ms in v1, for three times more area covered.

### State of the art, v2

Search for 2026-10-25, primary sources except mentioned.

**Treeless lands and spots:**
- **Hirota et al. 2011** ([article](https://gael.univ-grenoble-alpes.fr/sites/default/files/Mediatheque/Files/EC2%C2%B0C%20-%20hirota%26al_2011_science.pdf)), MODIS on 1 km², 35° S to 15° N. The share without shafts, read on figure 1B: 0,95 to 300 mm, 0,76 to 600, 0,32 to 900, 0,12 to 1 200, 0,05 to 1 500, 0,02 to 0,035 from 1 800 to 2 400 mm. The supplement tables could not be read.
- **Scheffer et al. 2012** ([PMC3535627](https://pmc.ncbi.nlm.nih.gov/articles/PMC3535627)), boreal forest, 45 to 70° N: stable modes at 0, 20, 45 and 75 % cover; tundra in cold, steppe in dry.
- **Taubert et al. 2018** ([article](https://formind.org/wp-content/uploads/2018/08/Taubert2018_Nature.pdf)): 130 million forest fragments; their sizes in power law of exponent 1,90 to 1,98, percolation gives 2,05; percolation threshold at 59 % of forest. Saravia et al. 2018 ([PMC6288094](https://pmc.ncbi.nlm.nih.gov/articles/PMC6288094)): 1,90 to 2,01 on the globe.
- **Asner et al. 2013**: Amazonian holes, showing 1,83 ± 0,09, the same for all forest types.

**Relief:**
- **Broll, Holtmeier et al. 2007** ([Fennia](https://fennia.journal.fi/article/view/3714)): on the windswept ground, the birch forest clears up to 240 at 300 m; in the valleys and leeward, groves rise to 370 m. Snow: a few cm on the bumps, 1 m and more in the hollows.
- **Case and Buckley 2015** ([PMC4627911](https://pmc.ncbi.nlm.nih.gov/articles/PMC4627911/)): 2 189 treeline points; most 100 to 250 m below local summit; curvature is the first predictor.
- **Rita et al. 2023** ([PMC9843241](https://pmc.ncbi.nlm.nih.gov/articles/PMC9843241/)): sun exposure changes sign, +78 m in the Southern Alps limited by cold, −114 m in the Apennines limited by water.
- **Serious Sam 4,** Croteam, GDC 2019 ([PDF](https://gpuopen.com/gdc-presentations/2019/gdc-2019-agtd2-4-million-acres-serious-sam-4.pdf)): the forest placed by altitude, slope and convexity, summit or valley.

**Edges and shrubs:**
- **The Swiss and Austrian border guides** ([canton of Vaud](https://www.vd.ch/fileadmin/user_upload/themes/environnement/forets/fichiers_pdf/Biodiv_Foret/ANNEXE_4_Revitalisation_des_lisieres__final.pdf), [Naturschutzbund](https://naturschutzbund.at/files/NATUR%20VERBINDET/Waldraender-Gestaltung-Pflege_NL4_17.pdf), [WWF](https://www.wwf.ch/sites/default/files/doc-2019-02/2012-10-factsheet-gemeinden-waldraender.pdf)): grass border from 5 to 10 m, shrub cord from 5 to 10 m, coat from 10 to 20 m; all border, 25 to 40 m. Guidelines, not measures.
- **Above the tree line:** a transition zone of 300 m and more in Switzerland; one tree is 3 m, the rest is krummholz.
- **The chaparral** ([USFS](https://fs.usda.gov/psw/publications/4403/On_Estimating.pdf)): 60 to 100 % of cover, 1 to 5 m.

**Leave earlier:**
- **Epic's impostors** ([Impostor Baker](https://dev.epicgames.com/documentation/en-us/unreal-engine/impostor-baker-plugin-in-unreal-engine)): 12 × 12 half-sphere views, 8 triangles per map, three mixed views; Fortnite uses them for all its trees without Nanite.
- **Serious Sam 4:** in the distance, 2 triangles per tree, 8 directions, the two closest mixed; 16 000 trees per block of 1 km.
- **SpeedTree** ([documentation](https://docs.unity3d.com/speedtree-runtime-sdk/manual/level-of-detail.html)): small branches shrink to their axis instead of disappearing; only the last level blends into the panel.
- **Battlefield 3,** GDC 2012 ([PDF](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/gdc12-terrain-in-battlefield3.pdf)): instances hanging from nodes of a quadtree, coarse levels for scattered trees seen from afar, fine levels for density; 1 to 4 ms on PS3.
- **Horizon Zero Dawn:** footprints of 6 m for trees, 3 for bushes, 1 for grass; a tree map that distinguishes between scattered trees, edge and core forest.
- **Not found in primary sources:** Drawing distances of Horizon Forbidden West, Ghost of Tsushima, Far Cry, Red Dead Redemption 2 and Flight Simulator.

**What we keep from it:** spots in power law, which gives a field of noise fractal cut at a threshold; the bare ridges and wooded hollows by height on the regional soil; the coat of bushes on the edge; to come out earlier, a rough level of the same shape first impostor, then the canopy on the ground.

### What is done

**Where are the woods, `WoodsAt`: two fields of noise, one rule, `Presence`.**
- **The rule:** a field of the planet's gradient noise, above the threshold that leaves a state its share of the lands, raised or lowered by some deviations. What the pixel does not show of the field widens the threshold.
- **The regions,** field of 32 km to 8 m: woods, savannah or forest, on the part of the lands that Hirota leaves them; the rest without a tree, whatever the soil.
- **The spots,** field of 1 km to 8 m, in the woods only: the populations on their part of the woods, the rest in clearings. At least one tenth of all forest, 30 m to 1 km; the Hirota rainforest keeps 80 % of cover.
- **The product of the two keeps the average:** two independent fields, the share of the settlements is that of the step 1. This is the rule of pebbles, `OBJECT_STONY` then `OBJECT_PATCHES`.
- **The tree comes out only there:** the heavy pass decides each plant at its foot, the canopy on the ground at every pixel, the same function.

**Shrubs:**
- **A field of spots to them,** 1 km to 8 m, on 60 % of land (`SHRUB_LAND`): shrubs and expanses without a shrub.
- **More:** 40 % of soil in wet clearings instead of 30, 30 % in undergrowth instead of 15. Estimates, to be checked on photos.
- **The mantle of the edges:** where the stands, seen at 32 m, are neither inside nor outside, the field of shrubs is raised by two gaps (`FOREST_EDGE`).
- **The krummholz:** their cold limit 1,5 °C of season below that of trees, or 300 m higher.
- **From afar, a bush is smooth:** the relief of the crowns of the canopy on the ground is that of the trees alone, weighted by their share of the canopy. The clearings full of bushes read like forest.

**The peaks and the lows, `Exposure`:**
- **The height of the ground on the regional ground,** the map of the planet at 16 km, on 300 m: −1 in the lows, +1 on the ridges and peaks.
- **Its ramp widens with the height spread under the pixel or the cell,** `sqrt(300² + 5 spread²)` m (2026-11-02): in high ranges, it narrowed to one level line of the grid, and bare ridges and wooded hollows cut its diamonds as it slid (`spec-rendu-lointain.md`, the screen relief).
- **A peak cools the season by 0,5 °C,** a depression warms it: the tree line 100 m lower on the bumps, like Broll.
- **It lowers the two fields of woods by two gaps,** a hollow raises them: a wet forest keeps a fifth of its trees on a full ridge. An estimate: no published law gives this figure below the tree line.

**Leave earlier:**
- **The shapes, their levels of detail and their output at 14 pixels,** removed with the plants generated the 2026-10-30: `log/recherche-vegetation-historique.md`.
- **The foot far away on the drawn ground:** under 48 pixels, the plant lands on the ground of mesh, which it follows; from 48 to 64 pixels, its foot slides to the exact ground, where it stays close. The exact soil, one per plant, was the most expensive of the placement: it serves only one tenth of the plants.
- **The tile placement** of 4 × 4 cells: the light pass spreads the tile by its middle before its sixteen cells; the heavy pass decides the climate and materials once per tile, then each plant.

**The new benchmarks,** `banc_vegetation.py`: `cretes`, trees by height on regional ground; `bord`, a clearing near the middle of a view, to land there; `krummholz`, a place just above the tree line.

### Measures

**Ridges** (`banc_vegetation.py cretes`, of plane of 20 km, the height on the average at 16 km, far below the tree line, season of more than 8 °C): the part of the ground under trees, in parentheses the part of the place.

| Location | Build | Hollow, under −150 m | Between | High, 150 to 300 m | Peak, more than 300 m |
|---|---|---|---|---|---|
| 15° N 121° E | v1 | 4 % | 4 % | 4 % | 4 % |
|  | v2 | 42 % (30 %) | 26 % (19 %) | 7 % (5 %) | 0 % (3 %) |
| 30° N 89° O | v1 | 15 % | 14 % | 13 % | 11 % |
|  | v2 | 40 % (27 %) | 15 % (37 %) | 2 % (11 %) | 1 % (4 %) |
| 32° N 19° E | v1 | 75 % | 76 % | 77 % | 83 % |
|  | v2 | 80 % (2 %) | 66 % (93 %) | 19 % (5 %) | 2 % (0 %) |
| 15° N 119° O | v1 | 11 % | 10 % | 12 % | 12 % |
|  | v2 | 26 % (3 %) | 3 % (89 %) | 0 % (7 %) | 0 % (1 %) |

- **In v1, trees ignored the relief.** In v2, the guard peak 0 to 2 %, the low 14 to 80 %.

**Coverage by biome** (`banc_vegetation.py biomes`), v1 and v2:

| Biome | Share of land | Wooden tableware | Of which trees |
|---|---|---|---|
| Tundra and Alpine | 26,7 % | 7,9 then 11,1 % | 7,8 then 5,6 % |
| Boréal | 13,0 % | 54,0 then 59,1 % | 51,7 then 43,8 % |
| Temperature humid | 14,4 % | 58,8 then 62,4 % | 58,0 then 50,3 % |
| Dry temperate | 10,5 % | 28,7 then 34,4 % | 15,8 then 9,9 % |
| Tropical humid | 6,5 % | 55,5 then 58,5 % | 52,6 then 43,2 % |
| Savannah and tropical dry | 13,1 % | 31,1 then 37,2 % | 15,3 then 8,5 % |
| Desert | 15,9 % | 18,2 then 14,4 % | 3,1 then 1,2 % |

- **Less trees, more shrubs:** Clearings, bare ridges and treeless lands take 7 to 9 tree points; shrubs give more.

**No pop** (`banc_descente.py`, `forest` view, from the ground, fixed squares):

| Place, square | Hauteurs | Forest share |
|---|---|---|
| Temperature Temperature Temperature Temperature Temperatures Temperature Temperature Temperature Temperatured forest, 30,4° N 120,5° E, 2 km | 20, 10, 5, 3, 2 km | 86,8 ; 86,1 ; 86,1 ; 86,1 ; 85,9 % |
| The same, 200 m, on a clearing | 2 km, 1 km, 700, 500, 400, 300, 250, 200 m | 62,0 ; 61,3 ; 62,1 ; 62,1 ; 62,0 ; 62,0 ; 62,1 ; 62,2 % |
| Boreal forest, 49,6° S 90,5° E, 200 m | 2 km, 1 km, 700, 500, 400, 300, 200 m | 67,9 ; 67,9 ; 67,8 ; 67,5 ; 67,8 ; 67,7 ; 68,6 % |
| Savane, 10,4° N 119,5° W, 200 m | 2 km, 1 km, 500, 300, 200 m | 57,0 ; 57,7 ; 56,8 ; 55,9 ; 55,6 % |

- **At ±1 point near** where trees pass from the canopy to objects, to ±1,5 in savannah.

**The light connection** (`banc_vegetation.py raccord`, with plants on without, in the middle of the screen):

| Forest | Flat, 200 m, v1 then v2 | At 45°, 200 m, v1 then v2 |
|---|---|---|
| Moderate | 1,05 then 0,99 | 1,05 then 0,98 |
| Tropical | 1,07 then 1,14 | 0,99 then 0,98 |
| Boreal, on the snow | 0,89 then 0,93 | 0,70 then 0,48 |
| Savannah | 1,04 then 1,02 | 1,03 then 0,99 |
| Maquis | 1,02 then 0,99 | 1,01 then 0,98 |

- **The boreal forest of bias darkens:** its clearings show the snow; the canopy on the ground lets them see, the drawn cones hide them. The average of the image is due to the snow seen, twenty times clearer than the forest.

**Floating, the jitter:**
- **No plants float half a pixel** on the sixteen test views. In mountain, two floated from 0,7 pixel with exact foot everywhere; none with foot on ground drawn in the distance.
- **The jitter,** `banc_tremblement.py`, v1 and v2, with and without smoothing:

| View | v1 | v2 |
|---|---|---|
| Temperature Temperature Temperature, 2 m | 0,00 / 0,01 | 0,01 / 0,05 |
| Temperature Temperature Temperature, 150 m | 0,00 / 0,02 | 0,01 / 0,07 |
| Boreal Forest, 150 m | 0,01 / 0,03 | 0,02 / 0,10 |
| Savannah, 2 m | 0,00 / 0,00 | 0,00 / 0,00 |
| Far view, 400 m | 0,00 / 0,03 | 0,01 / 0,05 |

- **It rises without smoothing, at the level of bare ground before vegetation,** 0,07 to 0,36: distant plants follow the mesh that slides. With smoothing, 0,02 at most.

**The cost** of the plants generated, v1 vs v2, removed with them: `log/recherche-vegetation-historique.md`.

### Rest after v2

- **The two questions asked to the user, without answer:** warm the climate of the middle latitudes to Earth's values; remove the forest part of the biomes palette.
- **The boreal forest seen from a bias:** the drawn conifers hide the snow of the clearings that the canopy on the ground lets see; the light, 0,5 to 45°.
- **The shrubs:** their shares and their covers are estimates, to be caled on photos counted as the pebbles.
- **Exit even earlier:** impostors from 6 to 14 pixels, or one plant cache per tile.

## v3: trees no longer grow

The 2026-10-25, on the user's verdict after the v2. Flight tests: `tools/tests/2026-10-25-vegetation-v3.txt`. Boards before and after: `journal/2026-10-25-vegetation-v3-avant-apres-1.jpg` and `-2.jpg`; a flight from 1 km to 150 m, frame by frame: `journal/2026-10-25-vegetation-v3-vol-150m.jpg`.

**The verdict:** in views like F3, at 150 m, trees seem to grow as the camera moves forward; bushes are a little too many.

**The cause, two rules violated:**
- **A tree grew:** from 14 to 21 pixels high, its size followed its fade, from 0 to its height.
- **The forest far away was flat:** the canopy on the ground, at the height of the ground, a tree height under the crowns. By bias, a tree height makes 14 pixels at the distance of the relay: the peaks went up of 14 pixels passing from the canopy to the objects.

**In brief:**
- **A tree is whole or absent:** each appears at its height, at its own threshold of the fade. The drawings are the part of the fade, as the canopy counts them.
- **The canopy has the height of its trees:** the ray of view crosses their crowns before the ground; a edge stands in wall, hides the clearing behind it; the summits have the parallax of their height.
- **The view height of the forest no longer collapses beyond the drawn trees:** 26 to 37 m up to 3 km, against 0 to 4 m in v2 beyond 2 km.
- **Shrubs: one fifth less,** low and gray-green desert bushes, no more dark spots on deserts seen from orbit.
- **The cost:** 1 ms more for the ground, the placement unchanged.

### State of the art, v3

Search for 2026-10-25, primary sources except mentioned.

- **No source grows trees:** the relay exchanges two drawings of the same trees, same places, same average light, by a constant opacity fade.
  - **SpeedTree** ([documentation](https://docs.unity3d.com/speedtree-runtime-sdk/manual/level-of-detail.html)): the 3D tree fades while the panel appears, by alpha-to-coverage; only the small branches shrink, never the tree.
  - **Unity** ([LOD Group](https://docs.unity3d.com/Manual/class-LODGroup.html)): cross-fade or vertices slide; **Unreal**, raster fade.
- **Bruneton and Neyret 2012** ([article](https://web.archive.org/web/20140826014406/http://hal.inria.fr/docs/00/65/01/20/PDF/article.pdf)), the closest reference:
  - a flat canopy "ignores the thickness of the forest" and makes the silhouettes jump: they move to objects towards 3 pixels high, not 14;
  - the distant cover discs come from the same seeds as the near trees: the places follow one drawing after another;
  - the light of nearby trees is pushed towards the statistical mean at the relay; their figure 7 checks that the light remains constant with the distance.
- **Serious Sam 4,** Croteam, GDC 2019 ([PDF](https://gpuopen.com/gdc-presentations/2019/gdc-2019-agtd2-4-million-acres-serious-sam-4.pdf)): trees, impostors to 2 triangles, then forest in the ground, all taken from the same recording by texel.
- **Flight Simulator 2020** ([SDK](https://docs.flightsimulator.com/html/Content_Configuration/Environment/Vegetation/Species_Definitions.htm)): octahedral impostors. **Outerra** ([blog](https://outerra.blogspot.com/2008/08/lots-of-trees.html)): panels up to 1 pixel, more than 500 000 trees. **X-Plane 12** ([documentation](https://developer.x-plane.com/article/building-custom-3-d-trees/)): the 3D shaft up to 500 m, one panel beyond.
- **Horizon Zero Dawn** ([GDC 2017](https://www.guerrilla-games.com/media/News/Files/GDC2017_VanMuijden_GPUBasedProceduralPlacementInHorizonZeroDawn.pdf)) and **Unreal PCG**: Placement is cached, not recalculated at each frame.
- **Mantler and Jeschke 2006** ([article](https://www.cg.tuwien.ac.at/research/publications/2006/Mantler-06-landscape/Mantler-06-landscape-paper.pdf)): the canopy launched in rays in the pixel, 30 not; a cost per pixel.
- **Not found in primary sources:** distances from Ghost of Tsushima, Horizon Forbidden West, Far Cry, Red Dead Redemption 2, Star Citizen, Arma, DCS.
- **What we recall:** never grow; give its height to the forest far away; ideally, draw the same trees in the distance as close.

### What is done

**A whole or missing tree** (`PlantPlacement.hlsli`):
- **Each plant has its threshold of the melt,** drawn from its cell of the grid. Drawing entire as soon as the fade exceeds it, from 21 to 14 pixels high in v3, from 8 to 5 from the planetary vegetation; never halfway.
- **The canopy removes the drawn part,** the average of the fade, in a Boolean layer (`PlantsDrawn`). The temporal smoothing blends each appearance into a dozen images.

**The canopy at the height of its trees** (`PixelShader.hlsl`, `PlantsDrawn`):
- **The crowns of the plants not drawn,** each of 0,45 of its height at its top; three layers at 0,95, 0,75, and 0,55 of the height under which stand nine tenths of them, each with its share of the crowns.
- **The ray of view crosses them before the ground:** each layer takes the woods part near its own foot on the ray path. One more sample, at the foot of the middle layer, seen at its distance from the pixel; none when these feet fall into the pixel.
- **What comes out of it:** a edge stands in wall and hides the clearing behind it; the relief of the peaks is taken where the radius meets them, with their parallax; the aerial perspective, at their distance and not that of the ground.
- **Their light seen from a bias:** the drawn plants show their shaded sides; measured on them, the canopy keeps 1 − 0,2 (1 − sin e)³ of its light at the elevation e of the view (`CANOPY_SIDE_LIGHT`): 1 from a bias, 0,85 to 5 degrees.

**The forms of the v3,** the coarse form that does not shrink or swell and the dome bush, removed with the plants generated the 2026-10-30: `log/recherche-vegetation-historique.md`.

**The bushes** (`PlanetSettings.hlsli`):
- **One fifth less:** on 50 % of land instead of 60; 35 % of soil in wet clearings instead of 40, 25 % in undergrowth instead of 30.
- **The gray-green of dry lands:** `SHRUB_ALBEDO` less saturated, an estimate to be caled on photos.

**Dark spots of deserts seen from orbit:**
- **Cause:** the logistics of the forest state left 1 % of forest at 300 mm; compared to the 5 % of wood of a desert, one fifth of settlements. 14% spots of dark trees on the sand.
- **The rule:** no forest state below 1 000 mm, where forest and savannah are not yet bistable (Staver et al. 2011); the logistics brought back to 0 there (`FOREST_RAIN.z`).

**The new benchmarks,** `banc_vegetation.py`: `mouvement`, camera moves over a forest, 41 images of 25 m; `relais`, light with and without plants by distance, bias view. The `height` and `distance` views of `MYPLANETENGINE_VIEW`: the height of the surface seen on the ground, 0 to 64 m, and its distance, 0 to 4 km, as they are.

**Tried, not kept: the crowns of each tree thrown into the pixel,** as Bruneton and Mantler recommend. The same cells, prints and colors as the objects, ellipsoids encountered cell by cell along the radius. Rapid, the path of the ray in the crowns makes hundreds of cells: 10 ms more at F3, and crowns still in strips. To be taken up with a plant cover per tile.

### Measures

**Flight, benchmark `mouvement`**: the height seen from the surface, average of all images per distance band (m).

| Distance | 150 m, v2 | 150 m, v3 | 400 m, v2 | 400 m, v3 |
|---|---|---|---|---|
| 600 to 800 m | 21,5 | 22,0 | 17,7 | 19,0 |
| 800 m to 1 km | 27,3 | 28,9 | 18,5 | 22,4 |
| 1 to 1,3 km | 29,0 | 34,6 | 14,5 | 25,8 |
| 1,3 to 1,6 km | 26,0 | 35,8 | 13,7 | 29,5 |
| 1,6 to 2 km | 22,0 | 37,2 | 10,1 | 30,9 |
| 2 to 2,5 km | 3,6 | 33,3 | 1,2 | 28,2 |
| 2,5 to 3 km | 0,1 | 26,3 | 0,0 | 25,0 |

- **In v2, the forest collapsed beyond the trees drawn,** at 0 m to 2,5 km: this is the shoot seen in flight. In v3, it keeps its height.
- **By strip of 20 m of ground, from 450 m to 2,2 km:** the height view changes from 1,92 m from one image to the next against 2,58 in v2 to 150 m, from 0,97 against 1,34 to 400 m. The rest comes from the soil itself, which goes from clearings to woods.
- **The layer remains a little high at the measurement:** 33 to 37 m against 23 to 30 for the drawn trees, whose pixels also see the bottom of the crowns. On the screen, at 2 km, less than 3 pixels.

**The light relay, benchmark `relais`**: light with plants on without, by distance.

| View | 1 to 1,4 km | 1,4 to 1,8 km | 1,8 to 2,3 km | 2,3 to 3 km |
|---|---|---|---|---|
| F3, 150 m to 20°, v2 | 0,81 | 0,85 | 0,80 | 0,87 |
| F3, v3 | 0,94 | 0,95 | 0,90 | 0,88 |
| 400 m to 8°, v2 | 0,88 | 0,94 | 0,96 | 1,00 |
| 400 m to 8°, v3 | 0,90 | 0,96 | 0,97 | 0,99 |

- **The drawn trees remain 5 to 12 % darker** than the canopy bias at F3, against 13 to 20 % in v2.
- **From the top and at 45°** (benchmark `raccord`): 0,97 to 1,18, as in v2; the boreal forest seen from the side, 0,52, its cones hiding the snow of the clearings.

**The rest, unchanged or better:**
- **No pop downhill:** the forest part at ±1,5 point from 2 km to 200 m.
- **No floating plants** on all sixteen test views.
- **The jitter,** the same as in v2: 0,00 to 0,02 with smoothing.
- **Cost,** at rest under load of another instance: rendering 1 ms more, 10,1 to 10,9 ms versus 9,2 to 9,9; placement unchanged.
- **Shrubs,** woody cover less trees: −17 % in temperate humid forest, −20 % in boreal, −23 % in savannah and drylands, −17 % in desert.

### Rest after v3

- **The two questions asked to the user, without answer:** warm the climate of the middle latitudes; remove the forest part of the biomes palette.
- **The same trees far as close:** the crowns of each tree in the ground, or impostors, require a plant cache per tile.
- **The trees drawn, still a little darker bias** than the canopy: the measured curve is an average of two forests under two suns.

## What remains of the step 1

- **The impostors and the forms, facts:** the game models, `vegetation-planetaire.md`. The tile cache, in part: the exact floor kept from one frame to another, `optimisation.md`, round 3.
- **Land cover by climate,** MODIS VCF, as the color palette: the measured cover and color of open ground, plus double counting.
- **The season for grass also:** its cold limit still follows the annual average, −2 to 6 °C; the tree line follows the season. A boreal forest grows on bare soil.
- **The shadows cast by plants,** with the unification of shadows; until then, the statistical shadow of the cover.
- **The exposure under cover:** the exposure meter ignores the canopy; inside, the forest is too dark.
- **More species and forms:** palm trees, birch trees, acacias in parasol; leaves and holes close up, colonization of space for branches.
- **Wind,** litter of forest soil. The mantle of the edges and the undergrowth of shrubs: made in v2.
- **The hot spot** of the distant canopy (Li and Strahler): lighter in the sun, darker in front of it.
