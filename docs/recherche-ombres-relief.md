# Research: the cast shadows of the relief

Status: research and first step made, the 2026-10-24, experiment `piste/ombres-relief`. The sun hidden by the relief, from the valley to the chain; the sky hidden by the slopes remains to be done. Since `piste/ombre-unique`, the same step also gives the shadow height of the air (`recherche-rayons.md`).

## 1. Conclusion

**The horizon of the field towards the sun, calculated at each vertex of the mesh, interpolated as an angle, filtered to pixel.**
- **Our terrain is a field of heights,** already recalculated at each frame on the face and its rings. The horizon is read without drawing anything a second time: a walk along the great circle towards the sun, with steps increasing with the distance.
- **One rule at any distance.** The mesh already has grid cells proportional to distance: walking inherits its accuracy, from the meter near the camera to kilometers away.
- **Interpolated as an angle, not as a shadow.** Between two peaks, the horizon varies gently; the edge of the shadow falls where it crosses the sun, between the peaks, as sharp as the solar disc and the pixel allow.
- **Pixel shows average light.** The part of the solar disk above the horizon, enlarged from the spread of the horizon in the pixel: `SpreadStep`, the rule of the boundaries between materials. In the distance, shadows become soft parts, never crenellated edges.
- **The relief is finer than the mesh:** its shadow is a part, Smith shading for the dispersion of slopes that the grid cell hides, `SlopeSpread`. Without adjustment new.

**Dismissed:**
- **The shadow cards in cascade or virtual:** it would be necessary to redrawing the mesh from the sun, and a mesh that slides makes shake their edges. For 300 km of shadow at sunset, levels by dozens.
- **The walk per pixel:** four to five times more points than vertices, for edges that the real penumbra already blurs at the scale of the grid cell.
- **Pre-calculated horizon maps:** our terrain is never stored; it changes with the camera.

## 2. What we had

- **The sun filtered by the air,** hidden only by the sphere, at the edge of its disc (`SunTransmittance`).
- **The sky of a horizontal floor,** weighted by the normal and cavity of textures.
- **Micro-shades of cavity,** under the meter.
- **No shadows, no sky hidden by the slopes** (`recherche-profondeur-atmospherique.md`, 3.6).

## 3. State of the art

### Shadow cards in cascade and virtual

- **The principle:** a depth image seen from the sun, cut into slices of distance. Four slices of 1 024² in the demo of NVIDIA (Dimitrov 2007).
- **Stability:** each slice is stuck on the grid of its texels, fixed size, otherwise the edges sparkle (Microsoft, according to Engel 2006). The slices that follow the depth of the image, SDSM, can no longer be stuck; their parade: more resolution and a good filter (Lauritzen 2010).
- **Unreal Engine 5, virtual shadows:** 16 384² virtual shadows in pages of 128², levels of 64 cm to about 40 km, each twice as wide. The pages keep from one frame to another, but a moving sun invalidates them all. Penumbra by 8 rays in the map, according to the size of the sun.
- **The distant in Unreal:** a cascade “distant” for the landscape alone, then shadows by distance fields: 2,8 ms against 4,9 ms for six cascades, to 1080p on a R7870.
- **Frostbite:** nothing field specific in Andersson's 2007 presentation; stable, generic cascades.
- **For us:** redrawing the mesh from the sun, at each frame, by slices. A mesh that slides changes the shape that projects the shadow: the edges would shake despite the timing of the texels. And a setting sun requires hundreds of kilometers.

### Maps of the Horizon

- **Max 1988:** the horizon of each texel in a few azimuths, interpolated between them; the shadow where the sun passes under the horizon. For the relief of textures.
- **Sloan and Cohen 2000:** eight directions in two textures, interpolated.
- **Stewart 1998:** the horizon of each point of a digital terrain model, faster than previous methods beyond 100 000 points.
- **Timonen and Westerholm 2010:** the exact horizon in each azimuth, in linear time, by scanning; sharp shadows and full sky. 23 images/s on 1 024², 64 directions, on a GTX 280.
- **CosmoScout VR, DLR, HPG 2025:** horizons on 360 azimuths, compressed in 16 Fourier coefficients, for planets. 0,1 to 0,55 ms to 1080p on a RTX 4090. The solar disc taken as a constant height is sufficient.
- **The hidden sky:** for a uniform sky seen from a horizontal ground, the visible part above a horizon of elevation h is cos² h per azimuth (GTAO, Jimenez 2016, eq. 17). HBAO, Bavoil 2008, take a uniform solid angle.
- **For us:** the right tool, with one difference. Our terrain is never stored: the horizon is recalculated with each frame, where we look.

### Walk in the field of heights

- **Jung et al. 2020, curved lunar terrain:** one radius to the center of the sun per pixel, accelerated by maximum mipmaps; solar disc in circle segment. 5,4 ms against 18,2 ms in regular steps, to 1080p on a GTX 970M. Longer steps in oblique made sparkle.
- **Chajdas et al. 2015:** near shadows drawn in the field cache, far shadows pre-calculated for a day-night cycle, 3 bits per point.
- **Red Dead Redemption 2:** a shadow map of the terrain plotted in the heights, according to our previous research; not reverified in public slides.
- **For us:** this is what we do, but by vertex, on the mesh, rather than by pixel.

### Engines of planets

- **Star Citizen:** "cascades of Planetary Terrain Heights" for soft shadows on a large scale, instead of shadow maps (August report 2018), then several cascades blended (end 2019). The algorithm is not published.
- **Outerra:** shadow maps in 2014, the self-shading of the terrain not yet in point; the following is not published.
- **Flight Simulator, Proland, Elite Dangerous:** nothing published found on the shadows of the field.
- **CosmoScout VR:** the above horizon maps, the only published and ciphered planetary method.

### The penumbra of the solar disc

- **The sun is 0,53°:** a radius of 0,00465 rad (NASA).
- **The visible part of the disc** above a horizon offset by d from its centre: 1 − A(d)/πr², A the area of the circle segment. A soft threshold of −r at +r approach; CosmoScout VR even finds a sufficient constant height.
- **On the ground,** behind an obstacle of height H, sun at e: a penumbra of H [cot(e − r) − cot(e + r)] ≈ 2rH / sin² e, or 4r / sin 2e of the length of the shadow. At sunset, at 5°, 5 % of shade: 1,1 km of penumbra behind a summit of 1 km. Livingston and Lynch 1979 measure this profile on mountain shadows.

### Published costs

| Method | Cost | Equipment |
|---|---|---|
| Virtual shadows, Unreal 5 | not published; sun without a cache in Fortnite to hold 60 i/s | consoles |
| 6 cascades against distance fields, Unreal | 4,9 ms vs 2,8 ms, 1080p | R7870 |
| Walk per pixel with maximum mipmaps, Jung 2020 | 5,4 ms, 1080p | GTX 970M |
| Fourier Horizons, CosmoScout VR | 0,1 to 0,55 ms, 1080p | RTX 4090 |
| Horizon by vertex, here | see the measures | RTX 4070 Ti |

## 4. What is done

**The walk, `SunHorizon` in `Shadows.hlsli`,** in a separate pass, `Horizon.hlsl`, just after the calculation of the terrain, in its vertexes.
- **For each visible vertex,** of mesh as the field just calculated it.
- **Along the great circle towards the sun:** a line on the plane of the face, the one that joins the summit to the point of the sun.
- **Steps of 2 % of distance traveled,** never thinner than the grid cell below them, `HORIZON_STEP`. The horizon counts as an angle: a height missed between two steps weighs its height on its distance. The shadow height of the air counts it whole: at 5 %, the shadows of the ground were the same, but the rays shook more (`journal-planete.md`, 2026-10-25).
- **The height between the vertices,** bilinear, on the face or on the map of the rings.
- **The true positions,** including curvature: the sphere hides the sun from itself.
- **It stops** when nothing beyond, even a summit of 10 km, can go beyond the found horizon and the bottom of the solar disc, nor pass above the sun ray drawn from the shadow height. At high sun, a few steps; at sunset, hundreds of kilometers.

**Those who cast shadow are calculated, even off the screen.** The mesh calculates only the vertices that can be seen. A summit is now kept also if its shadow can fall on the screen: its column, from sea level at 10 km, swept opposite the sun as far as its shadow can carry (`ShadowSweep`, `MaybeVisible`).

**In the pixel, `PixelShader.hlsl`:**
- **the portion of the disk above the interpolated horizon,** enlarged from the horizon spread in pixel, drawn from the derivatives on the screen (`SunAboveHorizon`);
- **times the part of the relief thinner than the grid cell that its own relief leaves to the sun:** the Smith shading, for the dispersion of slopes that the grid cell hides (`FinerReliefLit`);
- **only direct light changes.** The sky remains that of a clear ground.

**The `sun`** (`MYPLANETENGINE_VIEW`) diagnostic view: each white pixel with the probability of direct light it receives, N.L times the part of the sun that the relief leaves. The white part gives the average.

**For the sun rays, the same step:** each market point also keeps its height above the sun ray drawn from the top. The larger one gives the shadow height of the column, which the atmosphere reads between the tops (`recherche-rayons.md`, part 4).

## 5. Measures

The 2026-10-24, on a RTX 4070 Ti shared with three to six other engine instances: times are minimums on eight alternate launches. Image: `images/ombres-avant-apres.jpg`.

**The flicker does not mount** (`banc_tremblement.py`, with / without smoothing):

| View | Before | After |
|---|---|---|
| Snowy ridge, sun at 10° from side | 0,08 / 0,47 | 0,08 / 0,42 |
| Massif at 8 km, sun at 15° | 0,18 / 0,98 | 0,16 / 0,92 |
| Summit at 600 m, sun at 10° in the back | 0,11 / 0,54 | 0,10 / 0,48 |
| Valley background, sun at 10° | 0,07 / 0,42 | 0,06 / 0,36 |

- The shadow darkens the image, which also lowers absolute deviations.
- The map of the flicker shows the edge of the shadow in a pyramid, in a thin line: it barely moves when the mesh slides.

**No jump at descent** (`banc_ombres.py`, sun at 10°): the average direct light on the ground of the next view, its deviation from one height to another.

| Massif, 15° S 120° E | 50 → 20 km | 20 → 8 km | 8 → 3 km | 3 → 1,2 km |
|---|---|---|---|---|
| Without shadows, the lighting of the past | +7 % | +7 % | +13 % | −10 % |
| Shadows, without Smith | −7 % | −3 % | −8 % | not measured |
| Shadows with Smith, restrained | +5 % | +4 % | +2 % | −6 % |
| Correlation of light maps | 0,68 | 0,80 | 0,69 | 0,83 |

| Flat valley background, edge of a shadow | 8 → 3 km | 3 → 1,2 km | 1,2 km → 500 m | 500 → 200 m |
|---|---|---|---|---|
| Without shadows | +8 % | +5 % | −2 % | +1 % |
| Shadows | +9 % | +9 % | −2 % | 0 % |
| Correlation | 0,70 | 0,80 | 0,82 | 0,60 |

- **The shadows do not jump more than the lighting before,** and the edge of the shadow stays in the same place from 8 km to 200 m.
- **Smith retained on measurement:** Without it, the far is 3 to 8 % too light; with it, 2 to 5 % too dark. It has no adjustment.
- **Shadow share alone is not the right measure.** At fixed view, from 50 km, it goes from 42 to 61 % when the grid cells go from 1 km to 130 m: the relief drawn casts more shadow. The average light, it, is preserved, that of the average surface (Smith): it is it that the benchmark compares.
- **Above a steep relief, below 1 km,** the comparison is no longer valid: the relief is as high as the camera, and the same area is not found from one view to another.

**The quality benchmark does not move** (`banc_qualite.py`, 10 places, sun towards 50°): all measurements at 0,0 dB close, including mutation, except the single rock crop at 800 m, −2,3 dB fine detail: a shadow crosses it.

**The adjustments of the walk, measured:**
- **Steps of 2 % instead of 5 %** give the same shadow shares, to 0,1 point close, on the six pairs of the descent. Retained the 2026-10-25, for the air.
- **Walk to 3° under the sun** instead of its edge: no change.

**The cost** (GPU calculation "title bar; the rendering does not change, to noise measure close):

| View | Before | After |
|---|---|---|
| Massif at 8 km, sun on left | 1,3 ms | 1,5 ms |
| Summit at 600 m, sun in the back | 0,6 ms | 2,0 ms |
| Snowy ridge, sun at 20° | 3,1 ms | 4,3 ms |

- **Worst case:** the sun in the back, when the mesh calculates the relief behind the camera for its shadow.
- **Hidden Sky, tried:** four more steps per vertex, up to 5° above the surface, cost 6 ms more on the ridge. Not cheap: not retained.

**Realism:**
- **A shadow is as long as the geometry says,** since the walk follows the real surface, including curvature: L = ΔH / tan e, plus L² / 2R. Measured on 212 shadows of a chain, view from above at 20 km, sun at 10°: median ratio 1,15 between the height lost and L tan e. The dispersion is wide, the projecting ridge being poorly identified on the grid altitude view.
- **The actual shadows:** the Teide, 3 718 m, casts more than 40 km at sunset, i.e. a sun towards 5°; a central lunar peak of 1,4 km, 22 km to 3,7°. Same rule here.
- **The penumbra:** behind a summit of 1 km, sun at 10°, about 310 m. Interpolated as an angle, the horizon keeps this width as long as it varies gently from one summit to another.
- **No comparison to photos yet:** no photo of mountain in low sun in `images/`.

## 6. Open items

- **The sky hidden by the slopes.** Shorter steps are needed: limit the relief by the highest summit of the mesh of the image, instead of 10 km; or one summit in four; or spread it over several images.
- **The same higher peak would shorten the sun’s walk and the shadows’ sweep** behind the camera, the worst case of cost.
- **From afar, the outline of the shadows follows the triangles:** it is straight on a grid cell, 13 pixels. Interpolating the horizon in B-spline, like normals, would round it.
- **The benchmark descent under 1 km** requires a flat valley bottom.
- **Mountain photos at low sunlight,** at known sun height, to judge the shadow and light of the shadow faces.

## Sources

**Shadows in cascade and virtual**
- Dimitrov 2007, *Cascaded Shadow Maps*, NVIDIA : [document](https://developer.download.nvidia.com/SDK/10/opengl/src/cascaded_shadow_maps/doc/cascaded_shadow_maps.pdf).
- Microsoft, *Common Techniques to Improve Shadow Depth Maps*, caling on the texels, after Engel, ShaderX5: [article](https://learn.microsoft.com/en-us/windows/win32/dxtecharts/common-techniques-to-improve-shadow-depth-maps).
- Lauritzen 2010, *Sample Distribution Shadow Maps*: [notes SIGGRAPH](https://www.intel.com/content/dam/develop/external/us/en/documents/sampledistributionshadowmaps-siggraph2010-notes-181237.pdf).
- Epic, *Virtual Shadow Maps*: [documentation](https://dev.epicgames.com/documentation/unreal-engine/virtual-shadow-maps-in-unreal-engine); Fortnite chapter 4: [blog](https://www.unrealengine.com/en-US/tech-blog/virtual-shadow-maps-in-fortnite-battle-royale-chapter-4); cascade distant: [API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/FShadowCascadeSettings); distance fields: [documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/distance-field-soft-shadows-in-unreal-engine).
- Andersson 2007, *Terrain Rendering in Frostbite Using Procedural Shader Splatting* : [notes](https://www.advances.realtimerendering.com/s2007/Andersson-TerrainRendering(Siggraph07)-CourseNotes.pdf).

**Horizons**
- Max 1988, *Horizon mapping: shadows for bump-mapped surfaces*, The Visual Computer 4(2); unread, described by CosmoScout VR.
- Sloan and Cohen 2000, *Interactive Horizon Mapping*; patent read instead: [US7102647B2](https://patents.google.com/patent/US7102647B2/en).
- Stewart 1998, Fast Horizon Computation at All Points of a Terrain: [page](https://www.dgp.toronto.edu/public_user/jstewart/papers/tvcg97.html).
- Timonen and Westerholm 2010, Scalable Height Field Self-Shadowing, CGF 29(2): [Summary](https://diglib.eg.org/handle/10.2312/CGF.v29i2pp723-731).
- Bavoil, Sainz and Dimitrov 2008, Image-Space Horizon-Based Ambient Occlusion: [article](https://www.cse.chalmers.se/edu/year/2018/course/TDA361/Advanced%20Computer%20Graphics/Image-Space%20Horizon-Based%20Ambient%20Occlusion.pdf).
- Jimenez et al. 2016, *Practical Real-Time Strategies for Accurate Indirect Occlusion* : [article](https://www.activision.com/cdn/research/Practical_Real_Time_Strategies_for_Accurate_Indirect_Occlusion_NEW%20VERSION_COLOR.pdf).
- CosmoScout VR, *Fast Planetary Shadows using Fourier-Compressed Horizon Maps*, HPG 2025 : [slides](https://highperformancegraphics.org/untracked/2025/presentations/Pa5_2_Fast%20Planetary%20Shadows%20using%20Fourier-Compressed%20Horizon%20Maps.pdf).

**Walk in the heights, planets engines**
- Jung et al. 2020, shadows on a curved lunar terrain: [arXiv](https://arxiv.org/abs/2005.06671).
- Chajdas et al. 2015, *High-Quality Shadows for Streaming Terrain Rendering* : [page](https://www.cs.cit.tum.de/cg/research/publications/2015/high-quality-shadows-for-streaming-terrain-rendering).
- Bauer 2019, *Creating the Atmospheric World of Red Dead Redemption 2* : [course SIGGRAPH](https://advances.realtimerendering.com/s2019/index.htm).
- Star Citizen: [August report 2018](https://robertsspaceindustries.com/en/comm-link/transmission/16743-Monthly-Studio-Report-August-2018), [Final report 2019](https://robertsspaceindustries.com/en/comm-link/transmission/17416-Star-Citizen-Monthly-Report-November-December-2019).
- Outerra, February 2014: [blog](https://outerra.blogspot.com/2014/02/).

**The sun, the real shadows**
- NASA, Sun profile, apparent diameter: [footnote](https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html).
- Circle segment: [MathWorld](https://mathworld.wolfram.com/CircularSegment.html).
- Livingston and Lynch 1979, mountain shadows, length and penumbra: [article](https://thulescientific.com/MountainShadow_Livingston&Lynch_AO_1979.pdf).
- Crater Théophile, heights drawn from the shadows: [Sky at Night](https://www.skyatnightmagazine.com/advice/skills/how-to-measure-lunar-craters-moon).
- Shade of Teide, more than 40 km: [snowy.es](https://snowy.es/wikimeteo/sombra-volcanica), secondary source.
- Walter et al. 2007, *Microfacet Models for Refraction through Rough Surfaces*, the Smith shading approximation for Beckmann: [article](https://www.cs.cornell.edu/~srm/publications/EGSR07-btdf.pdf).
