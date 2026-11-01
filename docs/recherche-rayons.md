# Search: sun rays, air in the shadow of the relief

Status: search and step 1 make the 2026-10-24, tag `piste/rayons-soleil`. Step 2, the 2026-10-25: a single step with cast shadows, tag `piste/ombre-unique`; the polar grid of the step 1 is in `log/recherche-rayons-historique.md`. Suite of `recherche-profondeur-atmospherique.md`, index 3.7. Sources at the end of the file.

**In the game:** air passes through the cloud composition (`spec-nuages.md`, `CloudAirPiece`), which reads the same shadow height. The rays are rendered the 2026-10-30, to judge in flight (`tools/tests/2026-10-30-lumiere.txt`); until then, this composition omitted them.

## 1. Conclusion

**A ray of sun is air that the relief deprives of sun.**
- The air in the shade reflects only the light of the sky. The air near the sun also returns that of the sun.
- The contrast between the two draws the rays. They differ from the sun by the perspective alone.
- It is sufficient that the atmosphere calculation knows which points of the air see the sun. No effect added on top.

**Retained: the shadow height, a single field, read by the existing steps of the viewing radius.**
- A column of air sees the sun above an altitude, the shadow height. Below, the relief hides the sun.
- This two-dimensional field describes the entire shadow volume of a relief in height. It also gives the shadow of the ground: a point of the ground below the shadow height is in the shade.
- Like the Red Dead Redemption 2 terrain shadow map, it walks to the sun on the heights. Here, it is the march of the cast shadows, at each vertex of the mesh: a single step, a single shadow, for the ground and for the air (`recherche-ombres-relief.md`).
- Each step of the viewing beam keeps the part of its length above the shadow height: it shows the average of its light.
- Nothing comes from the screen: the mesh keeps any visible column of air and any relief whose shadow reaches it. The sun out of the frame, in the back or on the side does not change anything.

**Dismissed:**
- **Mitchell's screen rays:** a radial blur towards the sun, on the image. Nothing out of the field or back to the sun, jumps when a relief comes out of the image. A layer over the image, not the physics.
- **the Frostbite and Unreal froxels:** a few dozen at 160 m depth, for near lights. They do not see the shadow of a mountain at 20 km, and hold only by jitter and temporal smoothing, with trails.
- **the length of the Bruneton shadow:** a single length per pixel, placed at the beginning or end of the ray. False as soon as the ray crosses several shadows, which is precisely what makes the rays.
- **epipolar sampling:** an acceleration of the walk along the rays of view, not a source of shadow. To be resumed if the cost of the atmosphere requires it.

**Cost:** almost nothing more than the cast shadows. The grid of the 1 step cost 0,8 to 1,1 ms per frame in 1280 × 720 on RTX 4070 Ti; the common walk makes it 0,7 to 1,3 ms. Stability: the jitter does not rise. Detail in part 4.

## 2. When we see rays

**The conditions (Lynch 1987, glossary of the AMS):**
- **a low sun:** shadows are long, rays pass through a lot of air;
- **a sun hidden or half hidden:** behind a ridge or cloud, the observer in the shadow or near its edge;
- **looking at the sun:** contrast is maximum at less than 15° of the sun, and less than 15° of the antisolaire point, the anti-twilight rays;
- **mist, without excess:** aerosols diffuse forward and make the air in the sun shiny. A fog too dense also illuminates the shadow, by the light of the sky, and the contrast decreases.

**What makes their strength:**
- the length of the path of the eye in the shadow counts first, before the phase of aerosols;
- and the ratio between the diffused sunlight and that of the sky. The shadow is illuminated only by the sky.

**Mountains:** in low sunlight, from a summit, each peak casts a triangular shadow in the fog (Livingston and Lynch 1979). In a backlit valley, the air in front of a shaded ridge is dark, and beams pass through the passes.

**In our area:** the fog of the boundary layer, 40 km of visibility up to 2 km of altitude, is the right medium. A mountain that exceeds the layer has no longer the appearance of darkening above: its rays are born in the valleys.

## 3. The techniques

| Technical | Entrée | Published cost | Stability | At our house |
|---|---|---|---|---|
| Screen rays, Mitchell 2007 | image of occlusion | Low, not quantified | jumps at the edges of the screen, nothing out of the field | dismissed |
| Epipolar, Engelhardt and Dachsbacher 2010 | shadow map, depth | 28 ms in 1080p on HD 4850, versus 71 ms in brute force | “stable and without flicker” according to the authors | an acceleration, for later |
| Epipolar and trees min/max, Yusov 2013 | shadow maps in cascade | not verified | refinement on diffusion rather than depth | Same |
| Froxels, Wronski 2014, Hillaire 2015, Unreal | shadow maps in cascade | 1,1 to 3 ms on PS4 | moving, jitter and temporal smoothing, dragged | too short range |
| Shadow length, Bruneton 2008 and 2017 | volumes of shadow | low | stable | one shadow per ray |
| Field shadow map, Bauer 2019 | map of heights | 1,31 ms on PS4 for the trade | temporal smoothing, time-cut | **hold** |

### 3.1 Screen Rays, Mitchell, GPU Gems 3

- **Principle:** Each pixel samples on the line that joins it to the sun on the screen, with a decay. The sum is added to the image.
- **Entry:** an occlusion image, black relief, clear sky. Only visible obstacles count.
- **Limits, according to the author:** rays from the background pass before nearby objects; they twinkle when an obstacle passes the edge of the screen; facing the sun from the side, its position on the screen goes infinitely, you have to fade the effect. Sun in the back is not treated.

### 3.2 Epipolar sampling, Engelhardt and Dachsbacher 2010

- **Principle:** rays of light project on the screen on straight lines from the sun. Only along 256 to 1 024 of these lines, 8 to 32 points each, plus two points at each depth jump, are sampled.
- **Marching:** Each point walks in the shadow map along the radius of view. A bilateral interpolation fills the screen.
- **Cost:** 1,2 ms for straights, 6,0 ms for jumps, 16,7 ms for march, 4,4 ms for interpolation, on HD 4850 in 1080p: 36 frames per second against 14 in brute force.
- **Yusov, Intel 2013:** the atmosphere of a planet, shadow maps in cascade, and trees min/max at one dimension. In the straightened shadow map, each epipolar line becomes a one-dimensional relief.

### 3.3 Froxels, Frostbite and Unreal

- **Principle:** a grid aligned on the screen, 8 × 8 pixels and 64 slices in depth at Frostbite, 160 × 90 × 64 at Wronski. Each cell takes the sun shadow card.
- **Stability:** one sample per cell crenellate in motion, "shadows aggravate it" (Hillaire). Fixed by Halton jitter, reprojection and 5 % of new image. Unreal announces a strong temporal smoothing, with trails behind the fast lights.
- **Cost:** 2,95 ms on PS4 in 900p at Frostbite, including 0,5 ms for the sun; about 1,1 ms at Wronski; about 1 ms on PS4 at Unreal.
- **Scope:** 50 to 128 m in Wronski, 160 m in Red Dead Redemption 2. Beyond that, something else.

### 3.4 The length of shadow, Brunetto

- **2008:** shadow volumes give, per pixel, the total length of the look in the shadow. The spread of this length is removed.
- **2017:** the demo calculates this length for the shadow of a sphere, analytically. The sky removes it at the beginning of the ray, the diffusion to a point removes it at the end. A shadow in one piece, at one end.
- **A trick:** the rays fade when the sun approaches the horizon, `lightshaft_fadein_hack`.

### 3.5 The Shadow Map of the Field, Red Dead Redemption 2

- **Principle:** a march on the map of heights, towards the sun, in a texture of 128 × 128. It keeps the height of the intersection and the length of the radius, which softens the shadow.
- **Air:** near the camera, the froxels read this card with the cascades and the shadow of clouds. In the distance, a march in half resolution, redone on 4 images. The sky is modulated by the average visibility, “not physically correct, but plausible”.
- **Cost:** 1,31 ms for air marking on PS4.

## 4. What is done: shadow height, per vertex

**One step (`SunHorizon`, `Shadows.hlsli`, pass `Horizon.hlsl`).** That of the cast shadows (`recherche-ombres-relief.md`, part 4).
- At each visible vertex, along the great circle towards the sun, on the heights of the mesh, steps of 2 % of the distance travelled, never below the grid cell.
- Each market point gives the horizon, for the ground, and its height above the sun's radius drawn from the summit, for the air: q · (u − sin θ s) / cos² θ, for a point q seen from the summit, u the vertical, s the sun at the height θ. Exact: the marked points are in their true place, including curvature.
- The largest, added to the ground of the summit, is the shadow height of the column. Ground and air see the same relief: a summit is in shade if and only if its shadow height exceeds its ground.
- The march stops when nothing beyond, even a summit of 10 km, can exceed the horizon found and the bottom of the disc, nor pass above the ray of the sun drawn from the shadow height. A summit in the sun walks as before; a summit in the shade, at most as far.

**What the mesh covers.**
- **Any visible air column:** the mesh keeps a peak if its column, from the sea to `MAX_TERRAIN_HEIGHT`, can be seen (`MaybeVisible`). The air that the camera sees below the highest peak is therefore above calculated peaks, even when their ground is out of the picture.
- **Any relief that makes it shadow:** the mesh also keeps a summit if its column, swept opposite the sun, can fall into the image (`ShadowSweep`). The sweep covers the entire column, not only the ground: the shadow of an out-of-field relief on the air of the field is walked.
- **Beyond the rings,** the horizon passed, no relief: the grid stopped at the same reach.

**Reading (`Atmosphere.hlsli`, `IntegrateScattering`).**
- The shadow height, bilinear between the four vertices around the point, like the height of the mesh (`MeshCell`, `Mesh.hlsli`).
- The beam of view keeps its 12 steps towards the ground; towards the sky, 24 in the game, where the cloud cuts in half the step where it falls (`spec-nuages.md`). Each step reads the shadow height at its two ends and in its middle.
- The illuminated part of each half is exact for a linear margin between its ends: the edge of a ray slides into the pitch, it does not jump from one pitch to another.
- Only the sunlight that has been diffused once is cut off. The multiple scattering, the light of the sky, remains: the shadow is illuminated only by the sky.
- The boot tables do not have relief: `(ShadowRay)0`.

**What we see,** board of `tools/banc_tests.py` on `tools/tests/2026-10-24-rayons.txt`, `images/rayons-avant-apres.jpg`:
- **backlight, sun behind the peak:** the glow that bathed the air in front of the peak disappears, the camera is in its shadow;
- **sun just above the ridges:** clear beams between the shadows of the ridges, and the corner of shadow of each needle on the fog;
- **sun from the side or back, desert, orbit:** little or no change.

**Measurements of step 2, against the polar grid** (`journal-planete.md`, 2026-10-25; `images/ombre-unique-avant-apres.jpg`):
- **Nearly identical images:** average deviation of 0,00 to 0,88 level on 255 on the eleven ray views, from 0,03 to 0,74 on the eight cast shadows.
- **Darker air on the ridges,** a few levels on a few pixels. A polar grid of 1 024 × 1 024 deviates twice less from the new shadow than from the old one: the grid of 512 lowered the ridges.
- **jitter never above before,** on three rays views and two cast shadows.
- **Cost,** RTX 4070 Ti shared, successive capture pairs: calculation loses 0,7 to 1,3 ms on the four views measured at calm, rendering does not move at 0,1 ms near. The sun in the back, worst case of walking, was measured only with four other instances of the engine on the GPU: −0,4 to −1,2 ms in median, to be confirmed in calm.
- **The step counts:** at 5 %, the ground kept its shadows, but the air shook more than before at the peak at 14°, 0,10 / 0,66 → 0,12 / 0,69. At 2 %, 0,10 / 0,66.

## 5. Next steps

- **The darkness:** the sun is 0,53°. A shadow at 10 km from its relief has 93 m of penumbra. Here, the edge is softened only by the grid cell and the linear margin.
- **The steps of the sky:** 24 steps on the whole radius, more than 30 km each on the horizon. The shadow near the camera is rough. Closer steps close to the camera if a view shows it.
- **The shadow of clouds in the air,** absent: only their shadow on the ground is made (`spec-nuages.md`). It is also a shadow height, below.

## Sources

- K. Mitchell, « Volumetric Light Scattering as a Post-Process », GPU Gems 3, ch. 13, 2007. https://developer.nvidia.com/gpugems/gpugems3/part-ii-light-and-shadows/chapter-13-volumetric-light-scattering-post-process
- T. Engelhardt, C. Dachsbacher, « Epipolar Sampling for Shadows and Crepuscular Rays in Participating Media with Single Scattering », I3D 2010. https://faculty.digipen.edu/~gherron/references/References/LightEffects/VolumetricLighting/espmss10.pdf
- E. Yusov, "Practical Implementation of Light Scattering Effects Using Epipolar Sampling and 1D Min/Max Binary Trees", GDC 2013 ; GPU Pro 5. https://github.com/GameTechDev/OutdoorLightScattering
- S. Hillaire, « Physically Based and Unified Volumetric Rendering in Frostbite », SIGGRAPH 2015. https://advances.realtimerendering.com/s2015/Frostbite%20PB%20and%20unified%20volumetrics.pptx
- B. Wronski, Volumetric Fog, SIGGRAPH 2014. https://bartwronski.com/wp-content/uploads/2014/08/bwronski_volumetric_fog_siggraph2014.pdf
- Epic Games, Volumetric Fog in Unreal Engine. https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-fog-in-unreal-engine
- E. Bruneton, F. Neyret, "Precomputed Atmospheric Scattering", EGSR 2008. https://inria.hal.science/inria-00288758
- E. Bruneton, « Precomputed Atmospheric Scattering: a New Implementation », 2017. https://ebruneton.github.io/precomputed_atmospheric_scattering/
- F. Bauer, « Creating the Atmospheric World of Red Dead Redemption 2 », SIGGRAPH 2019. https://advances.realtimerendering.com/s2019/slides_public_release.pptx
- D. K. Lynch, &quot; Optics of sunbeams &quot;, JOSA A 4, 609, 1987. https://thulescientific.com/Lynch_Sunbeams.PDF
- W. Livingston, D. Lynch, « Mountain shadow phenomena », Applied Optics 18, 265, 1979. https://authors.library.caltech.edu/records/nk414-7an79
- American Meteorological Society, glossary: “Crepuscular rays”, “Anticrepuscular rays”. https://glossary.ametsoc.org/wiki/Crepuscular_rays
