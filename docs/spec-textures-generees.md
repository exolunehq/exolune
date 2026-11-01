# Specification: textures generated at startup (path B)

Status: chosen the 2026-10-21, in place: the generator, the sand, the scree, the fine detail level and the colors of the rock. Since the 2026-10-24, the visible rock is a photo, `marble_cliff_04` (`spec-parois-minerales.md`): the rock recipe is only useful if scans are missing. The experiments of the comparison, the rock towers and its structure of 64 m, withdrawn, are in `log/spec-textures-generees-historique.md`. Track B of `log/etat-de-l-art-details.md`. It replaces the pixel-close textures of step D (`log/spec-rendu.md`), whose recipes are passed to the generator.

## The target

![Current engine, at 1 m from ground](images/actuel-desert.png)

![What it could give, approximate](images/cible-desert.jpg)

**What the target has in addition, in order of importance for the scale:**

1. **In the foreground, the wrinkles of the sand and its grains,** just under the feet.
2. **Sown pebbles and stones,** with their shadows.
3. **Readable rocky slopes:** strata, erosion ravines, scree at the foot, sand in the hollows, hard rock on the ridges.
4. **Mist with distance,** and shadows carried in the valleys.

### Second target: the coast

![Engine current, one slope at 1 m from ground](images/actuel-cote.png)

![The same coast, what it could give](images/cible-cote.jpg)

**What this target adds:**

- **A dark rock in cliffs,** fractured, with ravines. Sand settles on its replat and in its hollows, and not on the steep walls: it holds under its angle of rest, about 33°.
- **The contrast between rock and sand,** frank, when the engine shows only blurred gray spots.
- **The sea:** turquoise gradient near the shore, waves and foam at the foot of the cliffs.
- **The vegetation of the dunes:** tufts dry and shrubs, with their shadows.
- **Sown pebbles** in the foreground, as in the first target.

**Way B deals with the 1 and 3 points of the first target, and the rock, sand and their border of the second:** the appearance of surfaces and their transitions. The 2 and 4 points are related to other experiments points, listed at the end of the document.

## The principle

### Generate once, at startup

**A material generator, in compute, runs only once at startup,** like the atmosphere tables.

- **For each material, a set of seamless textures:**
  - height;
  - colour;
  - hollow, ambient occlusion;
  - normal, drawn from height.
- **Six materials:** rock, scree and gravel, sand, snow, arid soil, grassy soil.
- **Resolution:** 1024 × 1024 per card, on a tile of 2 to 8 m depending on the material. Or 2 to 8 mm by texel.
- **Two texture tables RGBA8:**
  - colour and hollowness;
  - normal in x and y, height, reserve.
  With the mipmaps, about 70 MB.
- **Seamless by construction:** all noise functions of the generator are periodic, to the size of the tile.
- **One seed per planet:** deterministic, and each planet has its own materials.
- **Target Startup Time:** Less than a second.
- **No file loaded.** The concept is intact: everything comes from the code and the seed.

### Revenue

| Material | Income |
|---|---|
| Rock | Voronoi blocks with randomly inclined flat faces, chamfered and chipped edges. strata in inclined planes, in steps, hard layers in projection. Cracks on the edges of blocks. Erosion by fBm to derivatives. Dust in the hollows |
| scree and gravel | Rounded stones of various sizes, tight, sown by cell. Sand and dust between them, by the height |
| Sand | Wrinkles from 8 to 15 cm, with a asymmetrical profile: gentle slope windward, steep leeward. Wave phase to break the regularity. Grains |
| Snow | Smooth, weak wind ripples, the sastrugi |
| Arid soil | Cracking polygons, small scattered pebbles, dust |
| Grassy soil | The tuftss of stage D, under the future strands |

**Each recipe starts from a single height field.** Color, hollow and normal derived from: the crack is hollow, dark and matte at the same time. This is the main lesson of research.

### Sampling at each frame

- **Coordinates anchored on the planet:** the pixel point, relative to the anchor of 64 m, is accurate. The periods of the tiles divide 64 m, so the anchor always falls on a tile edge. Nothing slips.
- **Biplanar projection,** by Inigo Quilez, on the fixed axes of the planet: two projections instead of the three of the triplanar, without stretching on the steep slopes.
- **Hexagonal Paving,** by Mikkelsen 2022: each hexagon randomly shifts the tile. Three readings per projection, no repeated pattern visible.
- **Oriented materials, sand and snow, do not rotate randomly:** a rotation would break the alignment of the wrinkles. Their direction follows a regional wind, drawn from a slow noise.
- **Two scales per material:** the tile, and the tile divided by eight. The large one carries the structure, the small one the grain. Together, they cover from centimeter to several meters and hide repetition.
- **mipmaps and anisotropy filtering:** stable, without flicker. From a distance, the texture is reduced to its average.

### The mixture of materials

- **The weights of stage C remain the basis:** climate, slope, altitude.
- **New masks drawn from the shape of the relief:**
  - scree at the foot of steep slopes;
  - sand and dust in the hollows;
  - rock on the crests.
  The curvature comes from the spline surface, which gives its second derivatives almost free.
- **Mix by texture height:** at the border, the highest material prevails. Sand fills the gaps between the stones.
- **Two materials per pixel at most,** the two strongest, to keep the cost down.
- **Preserved Average:** the generated color is normalized to an average of 1, then multiplied by the color of step C. The hue seen from afar does not change.

### The light

- **The normal of textures is added** to the normal spline.
- **The hollows darken the light of the sky.**
- **Fine shadows, like Call of Duty WWII:** the occlusion becomes a cone that also cuts the sunlight in the hollows. Few operations per pixel.

## What changes in the code

- **`MaterialGenerator.hlsl`,** new: recipes, one pass per material and card, then the mipmaps.
- **`D3DApp.cpp`**: the two texture tables, their generation at start after the atmosphere tables, an anisotropic repeat sampler.
- **`PixelShader.hlsl`**: biplanar projection, hexagonal paving, mixture, light. The pixel-level close textures, `GrassTexture` and `RockTexture`, become generator recipes.
- **`PlanetSettings.hlsli`**: tile sizes, intensities, switch between old and new rendering to compare.

## The steps

1. **The frame, with sand alone:** generator, tables, mipmaps, projection, hexagonal paving. This is the foreground of the target. Side by side comparison with it.
2. **The rock and the scree,** with the shape masks and the mix by the height.
3. **Snow, arid soil, grassy soil.**
4. **Light:** hollows and fine shadows.
5. **Measurements.**

## The measure

- **Side by side with the target,** from a point of view close to his own: at 1 m above the ground, in the dunes, in front of a rocky slope.
- **benchmark of jitter and mutation,** on reference and ground level views.
- **Color from far:** average deviation less than 1 on 255.
- **Cost:** generator start-up time, and rendered at worst at ground level. Less than 1 ms more than today.

## Validation criteria

- **At the ground level, we read the scale without hesitation:** wrinkles, grains, blocks, scree.
- **No visible repeat,** neither close nor mid-range.
- **No flicker or mutation in addition.**
- **The color from far does not change.**

## Results of the 1 stage: the frame and the sand

- **Wind wrinkles are read at the ground level:** asymmetrical profile, ridges that waddle and divide, darker hollows, grain. Beyond a few tens of meters, they pass under the pixel and merge into the color.
- **Stochastic paving** is done on a slightly sheared rather than hexagonal triangle grid: 64 m make an integer number of squares, so the anchor that follows the camera never moves the tiles. The slight gridling in the copy mixtures is reduced by netter weights and an angle variation of ±4°.
- **One scale for sand:** a second scale eight times smaller would give wrinkles of 1,5 cm, which do not exist. The large-scale variation already comes from the noise functions of stage C.
- **Colour from far preserved:** +0,28 on 255 to 10 m, +0,17 to 50 m. The average of each texture is read in its last mipmap level.
- **jitter:** unchanged with temporal smoothing; without it, from 0,02 to 0,05 to 2 m.
- **Cost:** no measurable difference in rendering. Generation at startup: a fraction of a second.
- **Test location:** a desert near sea level, 26° N, 45° E.
- **What is still missing for the target:** the pebbles sown, the dunes at the scale of the relief, the rock and the scree, the shadows cast.

## Step 2: sand creases redone, rock and rocks scree

**Method:** the visual benchmark, `tools/banc_visuel.py`. It captures each site at 1,5 m, 10 m, 100 m and 1 km above its ground, next to the reference image, and allows for fast iteration.

### Sand: wrinkles calculated to the pixel

- **Constat, en vol et au benchmark:** where two copies of tile mix, their wrinkles cross out of phase. A periodic pattern does not survive stochastic paving.
- **The wrinkles are therefore calculated by pixel,** without tile, like a wave plane in space that crosses the surface of the planet.
- **Phase is accurate everywhere.** The wind, tangent to the ground, is rounded to an integer vector of length 8 approximately, close to 4°. With an integer number of wrinkles per 64 m along this vector, the 64 m of the anchor always add whole wrinkles.
- **No projection tilts:** a first test in plane projection showed a clear connection where the plane passed from one axis of the planet to the other.
- **Three anchored noise functions, of 16 m, 4 m and 2 m,** vary the spacing, curve the ridges and cause them to split where they tighten. Two others, of 16 m and 2 m, weaken wrinkles in places.
- **Accuracy Antialiasing:** Wrinkles fade according to their own step on the screen, measured in their direction.
- **The sand-generated tile** only keeps the grain, marbles and bumps, on 8 m.

### The rock and the scree

- **Generated at startup:**
  - rock in blocks with sloping faces, divided into facets, cracks on one third of the edges, strata with soft layers retreating;
  - scree in stones of 40 and 15 cm in a lighter dust.
- **The strata follow the local vertical on the walls,** thanks to a projection chosen according to the normal of the surface.
- **Mixture by height:** soil, scree at the foot of slopes, rock on steep slopes.
- **Since the 2026-10-24,** the wall photo replaces the generated rock; the recipe is only useful if scans are missing.
- **Fine shadows in the sun,** like Uncharted 4: the hollows close a cone that also cuts the direct light, relative to their average, so that the distant ground keeps its light.

## The measure of realism

**`tools/realisme.py` compares the engine floor to a real scan, at the same scale.** It takes the measurement of the POC IA of the branch `poc-ia-textures`.

- **The view:** the engine is captured vertically, at the height where a pixel covers a texel of the scan.
- **The structure alone:** the luminance, minus its local average, divided by its local variance, so that light and color count less than the shapes.
- **Two notes, lower is better:**
  - **patterns:** Wasserstein distance cut between patterns of 7 × 7, on three scales, as a multiple of the distance between two areas of the scan itself;
  - **spectre:** mean variation of spectra from 3 cm to 1 m, in dB.
- **Scans remain outside the repository,** for example those of Poly Haven licensed CC0.

**First measure, against the beach scan Aerial Beach 01:**

| Sand | Reasons | Spectre |
|---|---|---|
| Smooth, without texture | ×48 | 3,5 dB |
| Paved wrinkles, stage 1 | ×13 | 8,1 dB |
| Wrinkles to pixel, step 2 | ×20 | 8,8 dB |
| Scan against itself | ×1 | 0,8 dB |

- **The measurement discriminates well** smooth floor from textured floor.
- **She compares to a precise scan:** this beach sand has wrinkles of 50 to 80 cm, short and in tongues, when ours are wind wrinkles of 12,5 cm. The paved grooves approach it by their disorder, despite their connections.
- **A scan of the targeted material is therefore required:** desert wind wrinkles, rock wall, scree. The measure can then be used to settle revenues on the real.

**Scans, uploaded on 2026-10-21:** six Poly Haven scans licensed CC0, stored out of the repository in `../scans/`; their actual widths are in `log/spec-hybride-scans.md`. `tools/telecharger_scans.ps1` reloads those of the engine. Poly Haven has no desert wind wrinkles.

**Second measurement, version with real relief, vertical view:**

| Scan | Engine floor | Reasons | Spectre |
|---|---|---|---|
| aerial_sand, coastal sand trampled, 15 m | desert, 4,6 m high | ×7,8 | 8,2 dB |
| sandy_gravel_02, desert soil, 2,5 m | desert, 1,5 m | ×17 | 10,3 dB |
| cliff_side, block sandstone, 1,8 m | rock, 1,5 m | ×5,3 | 2,1 dB |
| dark_rock_02, layered rock, 2 m | rock, 1,5 m | ×8,8 | 2,7 dB |

- **Small scans** cover less than a millimeter per texel. The camera does not go below 1,5 m, so the scan is reduced to its scale, 2,4 mm per pixel.
- **What the plates show, beyond the notes:**
  - **our materials are blurred close up:** their texel of 7,8 mm, a tile of 8 m in 1024, is too big, when scans show a sharp detail to the millimeter;
  - **our sand has only wrinkles,** when sand scans are made of grain, traces and small pebbles;
  - **our colors are dull:** the real rocks vary from gray to orange and almost black, by block and by layer.
- **The resulting experiments:**
  - a fine detail level, a second tile of 1 m to 1 mm by texel;
  - grain and pebbles in the sand;
  - more frank rock colors;
  - then the adjustment of the recipes on the scans, guided by the measurement.

## The level of fine detail

Status: made the 2026-10-21, first of the experiments of the realism measure.

**The finding:** closely, our materials are blurred. At 1,5 m from the ground, one pixel covers 2,4 mm; the texel of our tiles covers 7,8. Scans show a grain clean to the millimeter: sand sown with light and dark grains of 1 to 5 mm, granite spotted with crystals, capillary cracks.

**The principle: a second tile per material, from 1 m to 1024 texels, or 1 mm to texel.**

- **Same generator, at startup:** three more slices in textures, fine sand, fine rock, fine scree.
- **It only carries wavelengths less than 3 cm.** Its repetition every meter remains invisible, and the random paving breaks it in addition.
- **Same reading:** random triangle paving and biplanar projection, with the same orientation as the coarse tile. A tile of 1 m divides the anchor of 64 m.
- **The mixture, average preserved:** color and occlusion multiplied, slopes and heights added to those of the coarse tile.
- **Erase:** beyond 1 to 2 cm per pixel, the thin tile is no longer read. His mipmapss are already moving towards the average, without jumping. The additional cost is limited to the first meters.
- **The relief of the summits ignores it:** its grid cells filter beyond 4 cm.

**Fine revenues:**

- **Sand:** dense seedling of grains of 1 to 4 mm, light, dark and colored; some rounded gravel of 3 to 8 mm; micro-bumps. The grain of 7,8 mm of the coarse tile disappears.
- **Rock:** crystals of 1 to 3 mm, each in its own shade; roughness of 4 mm and 2 mm; piqûres. The capillary cracks are waiting: their network of about ten centimeters exceeds the thin tile.
- **scree:** Angular gravel from 5 mm to 2 cm on the dust.

**Measurement:** realism measurement against sandy_gravel_02, cliff_side, dark_rock_02 and gray_rocks, before and after; the visual benchmark at 1,5 m and 10 m; the cost GPU at 1,5 m.

**Criterion:** close, clear grain instead of blur, no visible repeated pattern, for less than 0,5 ms.

**Results, realism measurement at 1,5 m, motives:**

| Scan | Before | After |
|---|---|---|
| sandy_gravel_02, desert soil | ×17 | ×4,9 |
| cliff_side, greek | ×5,3 | ×2,3 |
| dark_rock_02, layered rock | ×8,8 | ×3,2 |
| gray_rocks, stones | ×7,5 | ×3,6 |

- **The blur of close has disappeared:** grains and gravel on the sand, spotting and micro-relief on the rock.
- **The sand spectrum remains at 9,9 dB:** our 12,5 cm wrinkles do not exist in this scan of stony soil. The explanatory statement is the most telling.
- **No repeat or transition line visible,** at visual benchmark.
- **jitter unchanged,** 0,06 / 0,33 on the rock at 3 m. **Cost:** +0,05 ms to 1,5 m.
- **Setting of the first round:** denser sand grains, less rock pitting. Sable ×6,0 → ×4,9.
- **Remains to be done, according to the boards:** more frank rock colors; the sand of dune could want less gravel than this stony soil.

## The colors of the rock

Status: made the 2026-10-21, second experiment of the realism measure.

**The findings:** all the rock of the planet has one color, a brown gray reflectance 0,20 / 0,17 / 0,14, to ±15 % close. The scans and reference images range from gray to ochre, orange, red and almost black.

**Two scales.**

- **From afar, the type of rock, by region:** a noise from 500 m to 40 km chooses from a palette of real rocks, in linear reflectance.
  - Grey granite, 0,26 / 0,25 / 0,24;
  - light limestone, 0,36 / 0,34 / 0,30;
  - ochre sandstone, 0,38 / 0,28 / 0,18;
  - red sandstone, 0,32 / 0,16 / 0,09;
  - Dark basalt, 0,08 / 0,075 / 0,07.
  - Two other noise functionss dose the oxidation, towards the red, and the desert varnish, towards the dark. The scree take the color of the rock from which they fall.
- **Close up, in the flush,** in the recipe of the coarse tile:
  - **layers:** each its shade, from pale to rusty, and its clarity at ±15 %;
  - **blocks:** clearness at ±20 %;
  - **iron oxide spots,** red, by plates of 30 to 60 cm;
  - **the varnish,** dark brown, in the grooves;
  - **lichens:** crusts of 2 to 4 cm, grouped in colonies of one meter, gray green or orange from one colony to another.
- **The average of the tile remains that of the rock type:** variations close do not change the color seen from afar.

**The measure:** the measure of realism only looks at the luminance, so we judge by eye. The visual benchmark, on several mountain sites, shows the variety of types; close views, variety in surface, against scans and reference images.

**Criterion:** rocks that change color from one region to another, and that have close to the variety of scans, without bariolage.

**Results:**

- **One shade per region:** dark brown on the rock site, cream in the dry hills at 26° N 130° E, ochre elsewhere, pale gray limestone on grassy plateau.
- **Close up,** the wall shows its layers, rust stains, varnish in the grooves and lichens.
- **Cost:** the regional noise, seven octaves, cost 0,3 ms per pixel. Calculated by vertex then interpolated, it costs only 0,05 to 0,08 ms. Its wavelengths of 500 m and more allow it.
- **First round settings:**
  - limestone, at 0,45 reflectance, appeared white: reduced to 0,36;
  - the lichens in round spots aligned on their grid: replaced by crusts drawn from a noise.

## Rock in beds and diaclases

Status: first round made the 2026-10-21. The recipe remains; since the 2026-10-24, it is only visible if scans are missing.

**The findings:** view of 50 m on a steep slope, the rock looks like repetitive scales. His Voronoi blocks are all the same size, 1,3 m. Each has its rounded edge and dark border.

**The principle:** the blocks follow the actual structure of a wall, as in the scans cliff_side and dark_rock_02.

- **From beds:** layers of 50 cm are grouped in beds from 0,5 to 2 m thick.
- **Diaclases:** in each benchmark, fractures about perpendicular to the layers, spaced from 0,5 to 2 m according to the benchmark, shifted from one benchmark to another, slightly wavy.
- **Few open fractures:** about four out of ten are open, dark and rounded on their edges; the others are only a light step or stroke.
- **The rest does not change:** the inclination and the hue per block, the roughness, the colors.

**The measurement:** a view at 50 m on a steep slope and a close-up view, before and after; the realism measure against cliff_side and dark_rock_02.

**First round results:**

- **Close up,** large smooth faces, some open fractures, some benchmarks: closer to a wall.
- **From further away,** a grid of beds and diaclases remains visible.
- **Setting:** a first trial, with diaclases all the 0,5 to 2 m and inclined blocks of ±0,25, made a masonry. It has passed to diaclases all the 0,8 to 4 m, inclined blocks of ±0,10 and one open fracture on four.
- **Realism, motifs:** cliff_side ×2,05 → ×2,18, dark_rock_02 ×3,3 → ×3,7. **Spectrum:** 2,2 → 2,0 dB and 2,6 → 2,2 dB. Neutral overall.

## Sand mixed with rock

- **The defect:** the rock surfaced in each groove, in strips of broken paving.
- **Cause:** Height-by-Height Mixing compares the heights of each material in its own unit. A wrinkle of 6 mm weighed as much as a rock bump of 30 cm.
- **Fix:** borders compare real heights, in meters. A texture that exceeds `BLEND_RISE` = 0,3 m above its average moves the border by an entire weight. The wrinkles remain continuous; the rock only pierces where it really sticks out.
- **Edge effect:** the tufts grass, of 5 cm, almost no longer pass between the stones of the scree.

**Note of the 2026-10-22:** the biplanar projection is replaced by a triplanar projection with continuous weights, `max(|n| − 0,45, 0)²`. See `log/spec-relief-reel.md`, Blade correction.
