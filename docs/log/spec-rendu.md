# Specification: rendering, materials and atmosphere

Status: validated, procedural, in proposed order. Steps A, B and C done, step C bis stopped, temporal smoothing kept. Step D specified the 2026-10-21. Following on from `spec-stabilite.md`.

## The objectives

1. **More detailed materials than the mesh.** From a distance, details are visible before the geometry is refined: no mutation effect.
2. **Surface detail textures.**
3. **Details on the surface,** in shaders or procedural objects driven by the noise functions.

**Everywhere, a texture goes hand in hand with its normals.** The colour alone remains flat: it is the normal which makes the relief read in the light.
4. **An atmosphere, the sky and the sun.**
5. **The aerial perspective**, to improve the distant rendering.

## The common principle

**Everything new is calculated pixel by pixel, in fixed coordinates of the planet.** This is the fine grain method, which has proven itself in the benchmark of jitter.

- **Nothing depends on the position of the vertex:** no jitter, and no change when the mesh is refined.
- **Anchoring:** the network of 64 m close to the camera, already in place. The indices of the noise functions remain accurate on a global scale.
- **Filtering:** each octave is deleted under 2 pixels, and therefore does not flicker.
- **Procedural, no image loaded,** in the spirit of the concept. It is a choice to validate, see the end.
- **Measurements at each step:** cost GPU on the ten reference views, benchmark from jitter, before and after images.
- **Budget:** about 3 ms for all rendering, in 1280 × 720. The calculation of the terrain remains under 2 ms.

## Step A: High Dynamic Range Image

**Prerequisites of the sky and the sun:** their dynamics does not fit in a 8 bits image.

- **Rendered in floating-point image,** 16 bits per channel, in linear light.
- **Then switch to the screen:** compression of the high lights, then sRGB output by the hardware.
- **Khronos neutral compression:** identity under 0,76, then a fade to white that keeps the shades.
- **The current colors are taken as they are,** so that the step only changes the image string.

**Result:** image identical to ±1 level close on four views. Rendu +0,01 ms.

## Stage B: atmosphere, sky and sun

**Method: Hillaire 2020** (Eurographics, Unreal's one). Rayleigh and Mie diffusion, ozone absorption, multiple scattering approximated. It is worth from the ground to space.

### Three small tables, calculated at startup

They depend only on the settings of the atmosphere, not the camera or the sun: recalculating them at each frame would be useless.

- **Transmittance,** 256 × 64: what the atmosphere lets through, depending on altitude and direction.
- **multiple scattering,** 32 × 32: the light that bounced back several times, depending on the altitude and height of the sun.
- **illuminance of the sky,** 64 × 16: the light that the whole sky sends on a horizontal ground. It illuminates the shadows.

### The rest is calculated pixel by pixel

**Simpler than the two camera-related tables of the original method,** and more fair. To measure: if it is too expensive, these tables come back.

- **Sky:** one ray per pixel crosses the atmosphere, in 32 not. The sun's disc is added to it.
- **Field:**
  - it receives the sun filtered by the atmosphere, hence the red sunsets, plus the illuminance of the sky;
  - the aerial perspective then veils its color according to the distance, by the same radius, from the camera to the ground.
- **Orbit view:** The ray enters the atmosphere from above. The blue limb appears by itself.
- **lighting linear:** the colors of the field become reflections, illuminated in linear light.

### Adjustments and tests

- **Earth settings** in `PlanetSettings.hlsli`, atmosphere of 100 km thick.
- **Keys O and P:** the sun rotates around the axis of the planet, to see the sunsets.
- **`MYPLANETENGINE_SUN=latitude longitude`** sets the sun at start, for captures.
- **Target cost:** less than 0,5 ms.

### Results

**Atmosphere costs 0,15 ms at worst of ten reference views:** rendering from 0,11 to 0,26 ms.

- **Aerial perspective is applied in the final pass, once per pixel.** The ground transmits its distance to it through the alpha channel.
  - Calculated in the terrain shader, it cost 0,65 ms in mountains: every fragment hidden by a nearer relief paid it too.
  - The picture is the same at ±2 levels close.
- **Sky, sun, sunsets and limbe** visible on the diary screenshots.
- **jitter:** slightly lower, from 0,22 to 0,14 on the plain at 50 m. The veil of air softens the contrasts.
- **Fault fixed:** sun at zenith, the illuminance table of the sky contained NaN, hence a black ocean seen from orbit.
- **Limits:**
  - fixed exposure, the scene is dark at nightfall;
  - no reflection of the sun on the ocean;
  - from very high, the blue veil dominates on the dark lands. It is physical, but the materials of Stage C, clearer and more varied, will rebalance it.

## Step C: Materials per pixel

**The problem: the color comes from the altitude and slope interpolated between the summits.**

- **From afar,** the color borders follow the coarse mesh. When it becomes thinner, they change shape: this is mutation.
- **In mountains,** the color rock or snow shakes, measured at benchmark.

**The principle: each pixel weights its materials,** sea, sand, grass, rock, snow and arid soil. Each material brings its color and normal.

- **The altitude and slope of the summits give only wide transitions.**
- **The fine borders are drawn from a noise per pixel,** fixed on the planet, at all visible scales.
- **An additional stable input:** the complexplanet terrain type, plains, hills, mountains or badlands, exported by the compute shader. His octaves are already limited to ~100 km, he does not shake.
- **A simple climate, made of a few noise functions:** today the color follows the altitude, uniformly, with clear borders. That is not realistic.
  - **Temperature:** latitude and altitude, plus a regional noise of a few hundred kilometers.
  - **Humidity:** a regional noise, plus a wider noise of the order of 1 000 km.
  - **Together, they choose the biome:** desert, steppe, prairie, forest, tundra, snow. Always by wide fades, never by net thresholds.
  - **Macro and micro variations:** noise functions of shade at all scales, from continent to meter, so that two neighboring meadows are never identical.
- **No border is a line, at no scale.** Today, snow stops clearly on a mountain range.
  - **The snow line is fading away:** isolated snowfalls below, rock piercing above, snow tongues in the corridors. Its altitude varies with a noise on several scales, from the valley to the meter.
  - **The relief modulates it:** snow holds in the hollows and on the slopes in the shade, slides steep slopes where the rock surfaces.
  - **Same principle for other borders:** beach, meadow and rock, forest and alpine pasture.
  - **The fine line is calculated in pixels:** it remains sharp and stable from close as far, independent of the mesh.
- **The slope used is that of the pixel,** normal of the vertices plus fine grain.

- **The material normals extend the relief beyond the mesh:** strata and scree for rock, smooth surface for snow, wrinkles for sand. They replace the generic fine grain, which did not know how to make mountain ridges.

**Expected result:** a distant mountain already shows its snow, its ridges and its scree, in color as in light, before its geometry refines.

**Limit:** The actual relief appears when the mesh is sharpened. The borders move then a little, but only in their broad transitions.

### Design

**Everything fits in the pixel shader of the terrain.** The noise functions use the 64 m anchor of fine grain: exact indices on the whole planet, stable, filtered under 2 pixels.

- **Two families of noise functions, three channels each for the price of one:**
  - **regional,** from 3 000 to 200 km: temperature difference, humidity, humidity wide;
  - **local,** from 8 km to pixel: snow spots, rock outcrops, variation of hue.
- **Temperature in °C:**
  - 27 °C at the equator, −25 °C at the poles;
  - −6,5 °C per km of altitude;
  - ±6 °C of noise regional;
  - ±5 °C of noise local, which cuts the snow line into nevets and tongues;
  - −3 °C on the slopes facing the pole.
- **Humidity from 0 to 1:** noise functions regional, plus a dry band to 25° latitude, that of the great deserts.
- **Vegetation:** desert, steppe, meadow, forest depending on humidity; tundra when cold. Wide bottoms.
- **Rock:** on steep slopes, with a slope threshold disturbed by the local noise.
- **Snow:** under 0 °C, driven from too steep slopes.
- **Beach:** near the sea level, with a variable width.
- **Hue:** ±15 % of brightness and a slight color drift, at all scales.
- **Normal by material:** Fine grain is reinforced on rock and softened on snow and sand.
- **Not yet:** the type of terrain exported by the compute shader. The climate and the slope are enough for a first try; it will come if the mountains lack character.

**Validation:** before and after images on reference views, benchmark from jitter, rendering cost. Colors are a choice of taste: it is you who decides on the images.

### Results, first trial

- **In mountains:** snow on the summits, cut out border in neves and tongues, rock that surfaces on the slopes, green valleys.
- **Region:** steppes and deserts around 25° latitude, meadows and forests elsewhere, hue that varies at all scales.
- **jitter:** no rise, and divided by two in mountain at 50 m, from 0,44 to 0,21 over the whole image.
- **Cost:** rendering from 0,26 to 0,78 ms at worst. Materials are calculated for each fragment, including those that are hidden by a nearer relief. A pre-depth pass would eliminate this waste, if the budget requires it.
- **Settings:** palette and climate in `GroundAt`, `PixelShader.hlsl`. The colors are linear reflectances: forest 8 %, meadow 15 %, desert 35 %, snow 85 %.
- **Corrected on the way:**
  - colors first written as screen values, twice too dark;
  - noise temperature too strong, which put snow in the tropics.
- **This was not a bug:** a black view was just night. Captures now place the sun in the afternoon of each view.

## Step C bis: the real relief in the pixels

**The goal: that the rendering shows the real relief of complexplanet before the geometry is refined.** Color and normals come from the same source of truth as elevations, at screen resolution. The generic grain and climate alone are only a dressing.

**The concept remains intact:** everything is recalculated at each frame, no memory or catch-up, for a fixed cost.

### The principle: share the graph between vertices and pixels

- **Vertices evaluate the slow parts of the graph:** continents, terrain type, turbulence, scale factors. They vary little from one vertex to another, their interpolated value is just.
- **Pixels re-evaluate the fractals that carry the fine relief,** with the same functions, the same seeds and the same frequencies. Their octaves are filtered to 2 pixels instead of 2 grid cells.
- **The pixel deduces an elevation difference:** its own value less the interpolated value of the vertices. This is exactly what geometry does not show yet.
- **The normal comes from the corrected surface,** the pixel position raised from this deviation. The edges of the geometry disappear under the real relief.
- **The color uses the corrected elevation and slope.**

### The prototype: mountains

**This is where the difference is most visible:** mountain ridges have wavelengths of 0,6 to 4 km, thinner than the grid cells seen from 10 km altitude.

- **Revalued per pixel:** the five ridged fractals of the mountains, base, high ridges and low mountains, about 27 evaluations of noise at most.
- **Interpolated from the summits:** the two deformations of the mountains, the scale factor, the part of the mountains in the terrain.
- **Only where there are mountains,** and only where the grid cells exceed 8 m. Closer, the summits already show all the relief, up to its finest octave of 22 m.
- **The generic grain fades in the mountains.**
- **Compilation:** the shaders of the field switch to the shader model 6, like the compute shader, to share the code of the noise.

### Expected limits

- **The distortions remain interpolated:** their octaves thinner than the grid cell are missing in the pixels. There is a residual mutation, weak.
- **Normal comes from derivatives between neighboring pixels,** calculated by blocks of 2 × 2 pixels.

### Validation

- Before and after pictures in the mountains at 10 km and 50 m.
- Mutation: comparison of pixels with fine geometry, by bringing the camera closer.
- benchmark of jitter, and cost of rendering.

### Results of the prototype

**The real relief appears well:** views of 10 km, the mountains show their ridges, snow settles on the replats, the rock remains bare on the ridges.

- **Normal:** the difference between two pixel ratings, one filtered to 2 pixels, the other to 8 grid cells, bends the smooth normal of the vertexes. A first version, which drifted the corrected surface between neighboring pixels, showed the edges of triangles.
- **Mutation,** measured by comparing the image to that of a mesh 8 times thinner, after a blur of 8 pixels: from 1,91 to 1,36 to 10 km, from 2,76 to 1,95 to 3 km. At pixel level, it increases: fine detail never falls on exactly the same pixels.
- **Cost:** rendering from 0,73 to 0,96 ms in mountain at 10 km, 1,49 ms at worst at 50 m.

**But the jitter increases strongly in mountain view from above:**

| jitter, full image | Stage C | Prototype |
|---|---|---|
| Mountain, 50 m | 0,21 | 0,25 |
| Mountain, 10 km, horizon | 3,39 | 7,99 |
| Mountain, 10 km, down | 4,30 | 7,71 |

**The cause, established by elimination, colors replaced by a gray:**

- from 1,5 without relief to 4,7 with;
- unchanged with deformations calculated in the pixel, a fixed cut, a stable pixel size, derivatives projected on the smooth surface;
- 3,3 limiting the relief to octaves more than 2 grid cells.

**This is parallax.** The pixel evaluates the relief at the point where its radius touches the coarse mesh, not the real relief. This mesh slides: the rated point slides with it along the radius. In the raised view, a few tens of meters of height difference become hundreds of meters along the ground. The more contrasted the relief, the more this slip is visible. The generic grain of stage C, ten times less contrasted, hid it.

### experiments

1. **Correct parallax:** move the evaluated point along the radius of the height difference, then re-evaluate, once or twice. Relief cost multiplied by 2 to 3. Reduces error, without canceling it at the sharpest angles.
2. **Smooth in time (TAA):** the standard method of engines against this flicker. The terrain is fixed on the planet: the reprojection from one frame to another is accurate. Slight blur, low cost.
3. **Keep the prototype for color only,** without bending the normal: less visual gain.

### experiment 1: parallax correction

- **The pixel estimates the height difference** between the real relief and the mesh, where its radius touches the mesh: its own value of mountains minus that of peaks.
- **It advances along its radius** to the height of the real relief, assuming the relief locally flat. The advance is limited to the racing angles.
- **It evaluates the relief, climate and grain at this new point,** instead of the point of the mesh.
- **One iteration first,** then two if the measure warrants it. Each iteration costs one more mountain evaluation.

**Result: rejected.** The jitter worsens, from 8,0 to 9,7 in mountains at 10 km, and the rendering goes to 2,3 ms. The height difference used to move along the radius itself depends on the interpolated vertices, which slide: the correction slides with them.

### experiment 2: the temporal smoothing (TAA)

- **Each pixel mixes its color with the one it had in the previous image,** at 10 % for the new one.
- **Exact projection:** the terrain is fixed on the planet. The position of the pixel, its distance and direction, is brought back to the camera from the previous image, in double precision precision on the processor. The sky, in infinity, follows only the rotation.
- **Anti-Trace:** the passed color is bounded by the colors of the current image around the pixel, on 3 × 3 pixels.
- **Two passes:** atmosphere writes the composed image, then the final pass smooths it and compresses the high lights.
- **No subpixel offset** for now: the goal is stability, not anti-crennel.
- **T key** to disable it, and compare.

**Result: the jitter falls below that of step C.**

| jitter, full image | Stage C | Prototype only | Prototype and smoothing |
|---|---|---|---|
| Mountain, 50 m | 0,21 | 0,25 | 0,07 |
| Mountain, 10 km, horizon | 3,39 | 7,99 | 0,95 |
| Mountain, 10 km, down | 4,30 | 7,71 | 1,18 |

- **Identical still image** to ±1 near level: without movement, smoothing converges to the same image.
- **Cost of smoothing:** in the measurement noise. Rendering peaks at 1,6 ms in mountains at 50 m, because of the relief per pixel.
- **To check in flight:** the trails behind the fast moving reliefs. The benchmark does not move the camera.

### Flight test correction: false peaks

**Constat:** when approaching a mountain, ridges drawn by the normal disappeared: they did not exist in the real relief.

- **Cause:** the octaves between 2 and 8 grid cells were counted twice, in the smooth normal of the vertexes and in the pixel relief. The slope was exaggerated from far.
- **Correction:** summits also calculate a normal without the mountains part. The pixel adds all the slope of the mountains, which it evaluates itself up to 2 pixels. No more double counting, and only one evaluation per pixel instead of two.
- **Mutation,** after a blur of 8 pixels: from 2,11 to 1,36 to 10 km, from 2,70 to 1,95 to 3 km, from 1,80 to 1,47 to 2 km.
- **jitter with smoothing:** 0,18 to 50 m, 0,99 to 10 km. Rendering from 0,8 to 1,5 ms.

### Following corrections, close

- **noise salt and pepper at a few hundred meters:** the pixel direction was accurate only to 0,6 m, and the slope divided this error by pixels of one meter. The point is now a shift from the nadir, in double precision precision, as in the compute shader.
- **Test excluded: the double precision reserved for fine octaves.** It broke the geometry at ground level: a floating point is accurate only to 20 cm on the planet, and the grid cells there make 1,6 cm. Accuracy is judged by the grid cell, not by the wavelength. Double precision in pixel under 4 m of pixel, as the vertices under 4 m of grid cell.
- **Faces on the distant mountains:** turbulence, interpolated between summits, changed slope at each triangle. They are recalculated in the pixel, filtered as at the vertex. Render up to 2,8 ms in mountains to 50 m.
- **Pixel size to ground** derived from distance and angle of view, and fine derivatives: no more jumping from triangle to triangle, no more blocks of 2 × 2.

### Conclusion: step C bis concluded

**The flying observation that decides:** from close, the geometry shows a rich relief, in volume; from far, there are only the ridged ridges, isolated and strange.

- **Cause:** The pixel was re-evaluating only the mountain branch. The hills, the low mountains, the fine octaves of turbulence existed only in geometry.
- **To be faithful, it would take the whole graph per pixel:** 8 to 33 ms. And precision requires double precision in the pixel, measured at 11 ms of rendering when extended to 16 m pixels.
- **Lesson:** the cost is in the evaluation of the noise, not in the number of vertexes. A texture sample costs as much as a top. Displaying a texture thinner than the mesh is therefore only useful if the number of vertices blocks, which is not the case here. Densifying the mesh gives the same detail, and in addition real silhouettes.
- **What we keep:** the temporal smoothing, independent of the relief per pixel.
- **Return to rendering of step C,** climate and generic grain. The prototype code is not versioned; the approach and measures are here.

### Limitation observed in flight: silhouettes

**Viewed from a distance, the pixel relief is more detailed than the contours of the mesh.** The very marked crests inside make out silhouettes remained polygonal. This is the known limit of any relief drawn by the normal.
- **The benchmark measures a deviation from one frame to another:** smoothing reduces it by construction. The flight judgment remains necessary.

## Test: the density of the mesh

**Finesse has only one source of truth:** `FaceCells`, the number of grid cells per side of the central plane. The growth of the rings follows, 1 + 2/FaceCells: a grid cell always covers about 2/FaceCells of its distance at the nadir, so the same size on the screen, regardless of the size of the plan. The plane size factor, K and L keys, only regulates the extent of the central plane.

| grid cells per side | grid cell on the screen | Calculation, worst case | Calculation, mountain 50 m | jitter, mountain 10 km, with smoothing |
|---|---|---|---|---|
| 128 | ~11 px | 1,8 ms | 1,0 ms | 0,62 |
| 160 | ~9 px | 2,8 ms | 1,2 ms | 0,53 |
| 192 | ~7 px | 3,9 ms | 1,8 ms | 0,46 |

- **Cost follows the number of vertices,** as expected: ×1,6 and ×2,2.
- **The visual gain is real but modest** on the captures: the normal of the smooth summits on 2 grid cells, the relief remains soft.
- **Time smoothing alone** changes the jitter of Stage C from 3,39 to 0,62 in mountain at 10 km, to 128 grid cells.
- **Retained: 192 grid cells,** judged significantly better in flight.

## Step D: Detail, Color, and Normal Textures

### The finding

**Close up, the floor is smooth: we lose the scale.**

- **The relief stops at 13,5 m:** this is the thinnest octave of complexplanet on earth. The mesh has nothing more fine to show.
- **The fine grain of the lighting fades towards 7 m,** at half of this octave.
- **The color varies up to the meter,** by the local noise of the stage C, but without normal: it remains flat.
- **Below, nothing:** neither tuft, nor pebble, nor wrinkle. At 2 m from the ground, nothing says whether we see 1 m or 100 m.

### The purpose

**Each material has its close texture, color and normal together,** from 8 m to the pixel, or the millimeter at ground level.

- **It takes over the fine grain without break:** the generic grain keeps the wavelengths above 8 m, the material textures those below.
- **It does not duplicate anything:** complexplanet has no wavelength under 13,5 m, the mesh neither.
- **It is calculated pixel by pixel,** anchored on the planet and filtered under 2 pixels, like fine grain: stable by construction, recalculated at each frame, without memory.

### The materials used

| Material | Colour | Normal and relief |
|---|---|---|
| Grass, steppe, meadow | Plates of green and dry hues from 1 to 3 m; tufts darker at their base | tufts from 20 to 40 cm, fine dent of a few centimeters |
| Rock | Veins and spots of lichen; dark cracks | strata following a slowly varying direction; network cracks from 20 cm to 2 m; roughness to pixel |
| Beach and desert sand | Light and dark variations of wrinkles; grains | Ridges from 10 to 20 cm in a wind direction that changes slowly |
| Snow | Almost uniform, slightly bluish in the hollows | Wind ripples, the sastrugi, from 0,5 to 2 m, weak; smooth surface below |
| Arid soil, tundra | Light and dark gravel; tundra mosses | Network cracks of 10 to 30 cm; pebbles of 2 to 10 cm |

- **The sea remains smooth.** The waves are from another site.
- **Forests remain a color** at this stage: their trees will come with the objects from stage E.

### The principle

#### One function per material

**Each material gives, at the point of the pixel planet, three values:**

- **a color factor,** of average 1;
- **a slope,** in the ground plane, which inclines the normal;
- **a height,** without unit, which is used for mixing.

#### The average is preserved

**From a distance, each texture fades to its average:** the color factor tends to 1, the slope to 0.

- **The colour of the distance does not change:** that of the stage C remains valid at any distance.
- **No mutation at approach:** texture appears by fine octaves, without shifting the overall tone.
- **The darkened hollows** by height, to read the relief on the centimeter scale, are compensated to keep the same average.

#### Mixing by height

**At the borders, the highest material prevails,** on a narrow transition band.

- **Snow accumulates in the hollows,** rock surfaces on the bumps, grass grows between the pebbles.
- **The weights from step C remain the basis:** the height of each texture only moves the border at a small scale.

#### Shared noise functions

**The cost comes from the number of octaves,** up to eleven between 8 m and the millimeter at ground level.

- **One set of octaves per pixel,** shaped differently by each material: crest for rock, absolute value for cracks, sinus deformed for wrinkles.
- **A noise cellular,** distance to the nearest point of a random network, for pebbles, cracks and tufts. It is new, and it is the most expensive: reserved for close octaves.
- **Only the materials present are evaluated:** a weight below 1 % skips them.
- **Only octaves above 2 pixels are evaluated:** from far, the texture costs almost nothing.

#### The lighting

- **The texture slope inclines the normal,** as the fine grain, after the normal spline.
- **The material also plays a role:** the choice between snow, rock and grass is made with the final normal, texture included. An isolated stone can therefore pierce the snow.

### What changes in the code

- **`PixelShader.hlsl`:** a detail function by material, the cellular noise, the mix by height, in `GroundAt`.
- **`PlanetSettings.hlsli`:** `TEXTURE_DETAIL`, the intensity of textures, 0 disables them; the wavelengths of passage with fine grain.
- **Nothing on the processor side nor mesh.**

### The steps

1. **The frame:** the function of detail, the preservation of the average, the mixture by height, the filtering. Validated with grass, the most common material near the start.
2. **Rock,** then **sand,** then **snow,** then **arid soil and tundra.** Each judged on images and in flight before the next.
3. **Measurements,** to each material.

### The measure

- **Ground-level views,** at 2 m, 10 m and 50 m, on grass, rock, sand and snow. The views of beach and low snow are to be found.
- **The benchmark of jitter and the benchmark of mutation,** on reference views and news.
- **The color from far:** captures at 10 km before and after, average difference less than 1 on 255.
- **The cost GPU,** at worst at ground level, the entire screen covered with near ground.

### Validation criteria

- **The scale is read at 2 m from the ground:** tufts, stones, wrinkles, cracks.
- **No flicker or mutation in addition,** to benchmark and in flight.
- **The color from far does not change.**
- **Cost:** less than 0,5 ms more at worst.

### Results of the 1 stage: the frame and the grass

- **The scale reads at ground level:** dense grass, irregular tufts from 15 to 35 cm to darker feet, grain of strands, tint plates from 2 m.
- **First test rejected:** tufts in cellular noise looked like paving stones, because of the sharp edge where the nearest point changes. Replaced by soft overlapping bumps of random size and height.
- **Far color preserved:** mean deviation zero at 2 km, −0,08 on 255 at 50 m. At the ground level, −1,6: the relief of the tufts darkens the whole a little.
- **jitter:** unchanged with time smoothing. Without it, from 0,04 to 0,07 to 3 m, from 0,02 to 0,03 to 10 m.
- **Rendering cost:** +0,4 ms to 3 m, +0,25 ms to 10 m, +0,1 ms to 50 m, nothing to 2 km.
- **Not yet done:** the benchmark mutation on new views, and flight judgment.

### Results of the stage 2: la roche

- **The rock is read closely:** strata wavy of about 0,8 m, each of its shade, fine cracks of 2 m and 50 cm, gray-green lichens of about 25 cm, roughness to the pixel. Its bumps of 1 m percent thin snow in small spots.
- **First attempt rejected:** strata drawn from a noise of 16 m drew concentric circles, like fingerprints, around the vertices of the noise. Drawn from a noise of 256 m, they are almost parallel to the scale of a wall, wavy by a noise of 4 m.
- **Corrected at first glance:** too yellow and too large lichens, too dark cracks that serpent.
- **Judged in flight: does not perform well.** Close up, the cracks, lines where a noise passes through zero, made soft loops like pipes. Re-established in a network of fractures, on the edges of Voronoi cells, interrupted in places. The rock remains unconvincing, like a smooth plaster: state-of-the-art research launched, see `etat-de-l-art-details.md`.
- **Colour from far preserved:** −0,1 on 255 to 50 m, −1,4 at ground level.
- **jitter:** unchanged with time smoothing; without it, from 0,18 to 0,21.
- **Cost:** almost zero more, +0,07 ms to 4 m, because grass is no longer calculated where rock covers everything.

### What remains for step E

- **The depth:** pebbles and cracks in parallax, from the same heights.
- **Objects:** grass, pebbles, rocks and trees, generated at each frame on a grid fixed on the planet. Grass blade: `spec-herbe.md`.

## Step E: Surface details

**Two way, I recommend shaders first.**

- **In shaders:** a parallax relief gives depth to the ground seen close, pebbles and cracks, from the same textures and normal. Inexpensive, no limit on number.
- **In procedural objects:** rocks, trees and grass placed by the noise functions on a fixed grid on the planet, generated at each frame in compute, then drawn by instances. More realistic close up, but it is a big project: levels of detail of objects, appearance without jump.

## Proposed order

1. **A then B, atmosphere first.** It changes all the light: adjusting the materials before would be redo.
2. **C,** materials per pixel.
3. **D,** detail textures.
4. **E,** the details on the surface: shaders first, objects then.

## Choice to validate

- **The order above.**
- **Surface details: shaders first, objects then.**
- **Procedural textures or images:**
  - the procedural keeps the spirit of the concept and has no limit of scale;
  - free images, of type CC0, placed without seams, would give a quick realism, but close they repeat themselves.
