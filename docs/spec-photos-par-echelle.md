# Specification: real photos, recomposed by our noise functions, at all scales

Status: steps 1 and 2 done; step 3, the patterns seen from plane, becomes a source of bands from 10 m to 1 km of `spec-texturage-universel.md`. Complete `log/etat-de-l-art-details.md` (track C) and `log/spec-hybride-scans.md`: the scans test, then the photo sand.

## The idea

**Keep the procedural for the “what and where”, take the real “what it looks like”.** Our noise functions of climate, geology and relief decide what is in each place; real photos give the appearance of every thing, recomposed on the fly by these same noise functions.

- **We never copy a photo as it is on a large scale:** it would copy the Earth, with coasts and reliefs that do not coincide with our terrain.
- **We get what transposes:** statistics, average color and variance, or textures without position, which pave and recolor.
- **The universal rule applies** (`principes.md`): an appearance taken from a photo is an average per place, and a pixel shows the average of what it covers.

## What the state of the art says

- **Blend copies of a photo without losing contrast:** random paving with blending that preserves the histogram. [Heitz and Neyret 2018](https://eheitzresearch.wordpress.com/722-2/), [Burley 2019](https://jcgt.org/published/0008/04/02/), [hex-tiling 2022](https://jcgt.org/published/0011/03/05/). We already have a nearby paving, in triangles.
- **Recolor a photo on the fly according to target statistics,** the core of the idea: [Lutz and Gilet 2026](https://www.lirmm.fr/nicolas-lutz/publications/lg26/preprint.pdf), about 1 ms. In our case, the targets come from climate and geology.
- **Mix multiple photos according to a noise:** [Laplacian blending, Wronski 2025](https://arxiv.org/abs/2502.13945), about 0,1 ms.
- **Seed elements cut out in the photos,** rocks or cracks: [texture bombing](https://developer.nvidia.com/gpugems/gpugems/part-iii-materials/chapter-20-texture-bombing).
- **Synthesize relief from real elevation models:** [Zhou et al. 2007](https://faculty.cc.gatech.edu/~turk/my_papers/terrain_synth_tvcg.pdf). Requests a precalculation and a memory of the field.
- **To discard for us:** the synthesis of full texture and neuronal, too slow or state, while everything is recalculated at each frame.
- **What others do:** [Star Citizen](https://starcitizen.tools/Planet_Tech_v5) distributes its materials by temperature, humidity and geology, like us, without publishing its method.

## The experiments, by scale

| Scale | What we take in the photos | Source | Feasibility |
|---|---|---|---|
| Orbite at 10 km | color palette and variance by biome | satellite mosaic, [Blue Marble by NASA](https://visibleearth.nasa.gov/collection/1484/blue-marble), public domain | easy: a small table, no image in the engine |
| 10 km to 100 m | Plane viewed motifs: fields, forests, dunes, scree, dry beds | Royalty Free Aerial Photos, Rare | medium: same tools as close up, but you need the photos |
| 100 m to ground | material close up: rock, sand, soil | scans CC0, Poly Haven and ambientCG | sand photo done; the rock remains procedural, `log/spec-hybride-scans.md`  |
| Terrain | pieces of real reliefs | models of elevation | possible, but against the concept of "recalculated at each frame"; experiment distant |

## Step 1: the biome palette from Blue Marble

**The principle.** Today, the color of the ground comes from a few shades chosen at the main: desert, steppe, meadow, forest, tundra. They become the true colors of the Earth, sorted by climate.

1. **Once off the engine:** `tools/palette_biomes.py` reads the Blue Marble mosaic and two Earth climate maps, average temperature and annual rainfall. The data remains outside the repository, in `../donnees-terre/`, with their licenses.
2. **It places each pixel of earth** in a temperature box × humidity, and measures the average color and its dispersion of each box, in linear light. Permanent ice is excluded, snow has its own treatment.
3. **The humidity of our noise functions** is related to precipitation by a logarithmic scale: 100 mm per year for 0, 3 000 mm for 1. To be calibrated so that our thresholds of desert, steppe and forest fall on the same precipitation as on Earth.
4. **The array enters the engine as a generated code file,** `BiomePalette.hlsli`, a few KB. No images are loaded.
5. **The pixel reads its color** in the table, by interpolation, at its temperature and humidity. The scattering of the box regulates the amplitude of the local clarity variation.

**The measurement:** the benchmark of orbit and views at 5, 56 and 300 km, next to views of the Earth at the same latitudes; the benchmark of descent, to check that the color does not change.

**Criterion:** colors seen from orbit recognizable as terrestrial, without changing the distribution of materials.

### Results of the stage 1

- **Data:**
  - Blue Marble of January and July 2004, NASA, public domain; each hemisphere is taken in its summer, its least snowy month, since snow is drawn separately;
  - TerraClimate normals 1991-2020 to 1°, CC0. The service NASA NEO, planned first, closed in September 2026.
- **Blue Marble is not a reflectance measure:** its colors are enhanced. They are reduced to the channel albedo, `albédo = a · valeur^g`, calibrated on two reference frames measured by satellite: the Libyan Sahara, (0,45; 0,35; 0,22), and the Amazon, (0,03; 0,06; 0,025).
- **The table:** 23 temperatures from −20 to 35 °C and 11 humidities. 202 boxes on 253 are filled by Earth; the others, of climates that Earth does not have, take the average of their neighbors.
- **reference frames, red, green, blue albedo:**
  - Sahara 0,42 ; 0,34 ; 0,22 ;
  - steppe 0,20 ; 0,18 ; 0,12 ;
  - Europe 0,08; 0,10; 0,06;
  - Amazon 0,04; 0,07; 0,03.
- **In the engine:** `BiomeColor`, three readings on the spread of temperature in the pixel, according to the universal rule. The local variation in brightness bears half of the measured dispersion.
- **What changes on the screen:**
  - deserts almost keep their color, already close;
  - the temperate wetlands become less green, more olive and brown. At 20 °C and 550 mm, Earth is a dry savannah, not a green meadow; our planet was greener than its climate.
- **Cost:** none measurable.
- **Calibrations to be reviewed in flight:** the scale between humidity and precipitation, 100 to 3 000 mm, and the dispersion part given to the local noise.

## Step 2: photo floors, close up

Launched the 2026-10-22, after the `log/spec-hybride-scans.md` test: the loose soils go to hybrid, the rock remains procedural.

- **Sand and Gravel scan replaces the tile generated from sand,** on the strip from 3 cm to 50 cm. A high pass cut it over to avoid repeated camouflage.
- **There is still one average factor 1:** the shade comes from the biome palette, the 1 stage. This is statistical recoloring, at its first degree.
- **Merged the 2026-10-23,** commit `7bf38a9`.

## Step 3: patterns seen from plane, from 100 m to 4 km

**The observation:** between the pixel and the grid cell, at 1 to 50 km altitude, the ground has only the color of its biome and the grain of the lighting. Nothing draws the dunes, the fields, the spotted forests, the lakes of the taiga, the networks of wades.

**The principle:**
- **One tile per landscape,** approximately 4 km in 1024 px, or 4 m per pixel, cut out of a royalty-free satellite image of a typical Earth location: erg, reg, savannah, bushland and crops, temperate forest, lake taiga, tundra, steppe, rainforest, wading network.
- **Made connectable out of the engine,** then paved randomly like the other tiles, without visible repetition.
- **A 1 average factor on the biome color:** the tile gives the pattern, the palette gives the shade. The landscapes mix by their weights, drawn from the climate and the relief, with the limits expanded according to the universal rule.
- **It erases itself from far away,** by its mipmaps, when a pixel covers the entire tile.
- **The large tiles do not divide the anchor of 64 m:** their coordinates are taken on the whole planet, in simple precision. The error, half a meter, remains under the pixel of the tile.

**Loading:** the same as photo floors, by WIC, at startup, now on the main branch.

**Measurement:** the orbit benchmark and views at 2, 10 and 50 km, next to the same real landscapes; the luminous descent benchmark, to check that the average color does not move.

## Next steps to be decided

2. **Statistical recoloring close up,** after hybrid test: each scan takes the mean and variance of its region.
3. **Mixing multiple scans** according to a noise.
4. **The motifs seen from airplane,** if we find free aerial photos.
