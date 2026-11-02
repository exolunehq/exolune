# The clouds of the game

**The clouds of the game, from orbit to ground, across the planet.** A two-layer volume, drawn from a planetary weather map calculated at start on the climate, and two noise functions 3D fixed on the planet, which the wind carries to the east. They shade the land and the sea, and the ship's canopy glass crosses them.

**State, 2026-10-31:** the only path, active by default, without variable (commit `3663177`). The light of the air is rendered to them the 2026-10-30. Since the 2026-10-31, their weather map is drawn from the climate, tag `piste/nuages-climat`: to judge in flight, `tools/tests/2026-10-31-nuages-climat.txt`. On the same day, their light, water and pixel are redone for the orbit view, tag `piste/orbite-rendu` (`spec-rendu-orbite.md`): to be judged in flight, `tools/tests/2026-10-31-orbite-rendu.txt`. On the 2026-11-02, their multiple scattering becomes a property of each point, for contrast and against shiny contours: to be judged in flight, `tools/tests/2026-11-02-nuages-contraste.txt`.

- **The code:** `MyPlanetEngine/Clouds.hlsli`, `CloudsTemporal.hlsli`, `AtmospherePass.hlsl` and its three envelopes `CloudTrace.hlsl`, `CloudTraceHalf.hlsl`, `CloudResolve.hlsl`; `D3DApp.cpp` and `.h`; the weather map, `Climate::Weather` in `Climate.cpp`; for the canopy glass, `ShipWeather.hlsl`, `Ship.cpp`.
- **Data:** `assets/clouds`, three volumes of noise and their `manifest.json`; the weather map is calculated at startup.
- **The origin:** Wicked Engine volumetric clouds, adapted (MIT, `NOTICE`); Frostbite noise functions and profiles; the map on the sphere. The spikes that led to it are in the log (`log/README.md`, the clouds); the history of this spec, in `log/spec-nuages-historique.md`.
- **Try it:** `tools/lance.ps1 -Parcours tools/tests/2026-10-27-nuages-planete.txt`; for air light, `tools/tests/2026-10-30-lumiere.txt` (`lancement.md`).

## The model

**Two layers, in a shell of 2 to 13 km altitude.**
- **Low clouds,** from 2 to 8 km: cumulus and sheets.
- **The cirrus,** from 9 to 13 km: an envelope of 0,35 to 0,6 km of half thickness, centered towards 11 km and wavy.
- **The radius of the planet:** 6 378 km.

**The weather map covers the entire sphere,** in 1 024 × 512; U the longitude, V the latitude, north at the top. It is calculated at startup on climate (next section).
- **R:** the portion of the sky covered by low clouds, up to 0,28; above, their thickness, up to 0,9; below 0,03, no clouds.
- **G:** their family, 0 the table, 1 the cumulus; between the two, the thick clouds of the fronts.
- **B:** cirrus, 0,286 at most: anvils, jet currents, shields of hot fronts.
- **It is read at the mip 0,** about 39 km at the equator, in cubic B-spline: the part covered the sheet of a steep function, and the bilinear interpolation drew squares from 80 to 160 km. It carries its shapes up to 80 km. Its mips 2 and more keep the maximum of R and B, to prove the vacuum; its margin covers the two texels of the filter.

## The weather map, drawn from the climate

**A climatology of clouds and a moment of its weather, calculated at startup by seed** (`Climate::Weather`), after the climate map (`spec-climat.md`), on its fields and the large relief forms. Each texel is calculated alone; the same seed gives the same card, bit close.

**R is the cloudy part of the sky, seen from above.**
- **Under a fraction c of 0,92,** R comes from a table measured on the three volumes, column of 6 km, under the law of rendering: the form of 32 km and its octave of 128 km threshold, water independent of R out of thickness:

| R | 0,08 | 0,10 | 0,12 | 0,14 | 0,16 | 0,18 | 0,20 | 0,22 | 0,24 | 0,26 | 0,28 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| opacity | 0,06 | 0,13 | 0,21 | 0,32 | 0,44 | 0,55 | 0,66 | 0,75 | 0,82 | 0,88 | 0,92 |

- **Above,** the masses: R = 0,28 + 0,62 e, e the thickness, that the rendering reads for the cloud water, `0,25 + 0,75 e`. A layer with e = 0 keeps 8 % of holes.
- **Thickness by class:** 0 to 0,2 sheets in 120 km cells; polar strata 0,1 to 0,25; cloud banks windward 0,3 to 0,5; shields 0,35 to 0,6; spiral arms 0,45 to 0,7; depression heads 0,8 to 1; fronts 0,75 to 1 on the axis, 0,5 at the end, 0,35 on the sides; convective cores 0,85 to 1.
- **Its structure:** left-handed variations of 80 and 250 km; e falls at 0 on the 40 to 80 km of the edge of a mass, left-handed, so that the edges fray.
- **Under 0,03,** R = 0: the sky is empty.

**Sky is clear by default,** as in Earth photo, bimodal: on blocks of 150 km, 43 % clear, 34 % mixed, 23 % cloudy, 37 % white overall. The map only puts clouds where a shape does.

**Two classes of clouds:**
- **The organized masses,** drawn by the map, opaque, with clear edges: arms and heads of depressions, cold fronts, hot shields, clusters of ZCIT and wet convection, stratocumulus sheets, polar strata, cloud banks windward.
  - The layers are made in surface, not in transparency: opaque where a texture n < c, n of 500 to 800 km made uniform on the area by its distribution function.
- **The fields of small clouds,** left at the grain of about 30 km of the shader: a partial fraction, 0,5 at most, without seiling, in four regimes only, each extinguished at 0 on its edges. The open cells behind the fronts, the broken edges of the sheets, the cumulus of alizé downstream of the sheets, the cumulus of the wet and warm lands.

| Cloud | Where | Fraction, family |
|---|---|---|
| The ZCIT | the maximum rainfall line between ±25°, smoothed on 2 000 km; half width 4°, left-handed | clusters of 0,46 to 0,68, threshold; thick, cumulus |
| Wet convection | above 1 500 to 2 400 mm and 20 to 25 °C, mainly earth | up to 0,7, threshold; cumulus |
| The layers of stratocumulus | above smoothed cold rises on 500 km, carried on 1 600 km leeward, stronger on a cool sea | 0,9 at heart, threshold in tears; defeats leeward in fields of 0,3 to 0,5; layer |
| The cumulus of alizé | downstream of the sheets, under trade winds, extinct on 1 250 km | 0,1 to 0,25; cumulus |
| Polar strata | under −8 to −18 °C on sea, −6 to −18 °C on land | 0,3, threshold; layer |
| The cloud banks windward | where the wind climbs the slope of the smoothed large shapes on 120 km, from 0,02 to 0,12 m/s | 0,82, threshold; mixed |
| The cumulus of the land | above 1 000 to 1 600 mm and 15 to 22 °C | 0,2 to 0,3; cumulus |
| Depressions | 8 to 10 in a ring between 45 and 62° S; 6 to 8 between 38 and 62° N, on the sea, at least 2 500 km | see below; opaque, mixed |

**A depression,** at its scale of 1 500 to 2 200 km and at its stage, from a wave to an occlusion, mirrored to the south:
- **spiral:** 2 or 3 logarithmic arms from 1 to 1,75 turn, wide from 0,2 to 0,3 times the scale; full head when it occluses;
- **dry slit:** the interval between the arms, narrower than them, clear;
- **the cold front:** a polyline on the sphere, from 2 500 to 5 000 km, which starts south-east of the center, sweeps south-south-west then west and reaches 25 to 31°; wide of 600 km near the center, 220 km at the end, 30 % more south;
- **cold side of the front,** a clear lane from 130 to 280 km; **hot side,** the hot area, cleared;
- **the hot shield,** about 1 350 × 1 000 km east and towards the pole, cirrus on its front edge;
- **the cold area,** on the sea, open cells of 0,35 to 0,5 behind the front, extinct before the ridge, halfway to the previous depression.

- **The sky clears up completely,** without floor: under anticyclones, on ridges between depressions, in hot areas, on hot deserts, under 250 mm and above 5 to 10 °C, in dry slits and fronts alleys; leeward of reliefs, where air descends from 0,015 to 0,1 m/s.
- **The cirrus:** the anvils of the ZCIT, the hot shields, the trails of the jet current towards 31°.
- **The combination:** a smoothed order maximum 4, never a sum; the family comes from the strongest form, in soft mix.
- **The budget,** seeds 0 and 1:
  - average opaque fraction 0,37 and 0,35, for 37 % of white on the Apollo photo;
  - clear sky, opacity under 0,05, on 52 and 53 % of area; cloudy, above 0,9, on 32 and 30 %; mixed on 16 and 17 %;
  - by band, the opaque fraction of the Earth at ±0,1: 0,4 from 0 to 10°, 0,2 to 0,25 from 10 to 30°, 0,5 to 0,65 from 40 to 70°; except 30-40° S, at 0,21-0,24 for 0,35, and 50-60° N of the seed 1, at 0,48 for 0,6;
  - cirrus above 0,03 on 6 to 7 %.
- **Time:** 150 to 170 ms at title, machine loaded by other renderings.
- **Measure:** `python tools/meteo_couverture.py <graine>` reads `meteo-<graine>.bin`, prints these numbers and their targets, and writes an image of the opacity seen from above, `meteo-<graine>.png`.
- **The engine writes the map** next to the executable, `meteo-<graine>.bin`, its mip 0 after a `EXOMETEO` header, the seed, width and height; and its depressions, `meteo-<graine>.txt`, latitude, longitude, scale and stage, for test views.

**Low cloud density:**
- **The shape,** a Perlin-Worley noise of 128³ texels over 32 km, and **the erosion,** a Worley noise of 32³ over 4 km. Both are fixed on the planet.
- **The vertical profile,** a table of 64² per family and per height in the layer, gives the density and strength of erosion.
  - **A light interval reads its profile's mean over its height span,** not its middle's: slice z of the volume holds the mean over a window of z texels, computed at loading (`D3DApp::UploadCloudVolume`); the file does not change. The view's samples read slice 0, the profile itself.
- **The cover is a form of shame,** in the Frostbite style: `remap(forme, 1 − R, 1) × R × profil`. Erosion is then cut off at the edge.
- **Then the density is divided by R:** R says the portion of the sky covered, not the water in the cloud. The shape, support and erosion do not change.
- **Water in the cloud follows the thickness that the map bears,** convention shared with the climate: `e = saturate((R − 0,28) / 0,62)`, zero under 0,28, and density multiplied by `0,25 + 0,75 e`, from 20 to 80 /km. The scattered cumulus and clouds, about 0,1 to 0,2 g/m³ of water, have τ from 10 to 25; the fronts and convection cores, 0,5 g/m³, τ from 80 and more. With water from a front heart everywhere, a layer of 1 km had τ ≈ 60: its reflectance saturated, flat and textureless view from low orbit.
- **An octave of the form at 128 km,** the same volume read four times its scale, axes permuted so that the two pavement do not align, is added to the form, centered on its measured average, 0,889; its variance under the texel is added to the pixel law. Without it, with partial coverage, the erosion of 4 km placed the cumulus alone: a uniform seed of the same sizes, seen from low orbit. With it, they are grouped in clusters and alleys, and the edges of the layers fray.

**Statistics per pixel** (`CloudLowDensity`): a sample reads the shape and erosion at the mip of the pixel footprint, and their law under it, not their single average.
- **The standard deviation of each noise under each texel,** of each mip, is calculated when loading from the 0 mip, in channel B of both volumes (`D3DApp::UploadCloudVolume`); the file on disk does not change.
- **The margin on erosion,** `U = clamp(X − (1 − R), 0, R) p − D g`, X the shape, D the erosion, p and g the profile, is taken Gaussian: mean and variance from the two moments of the threshold and the standard deviation of D.
- **The covered part** `f = Φ(mU / sU)`; **the density in the cloud** `E[U⁺] / f / (1 − g μD) / R`, limited to [0, 1]; under 1e-4, the part is zero.
- **The scales thinner than the texels,** that the noise functions do not carry, add their variance at any distance: 0,0124 for the shape, 0,033 for erosion, the variance of the thinnest octave, that of the blocks of the mip 1, the following octaves of half. Close up, an edge becomes a fringe of partial cover, like a turbulent edge seen at pixel. Control: `tools/nuages_statistique.py`.
- **The thin cirrus clouds** keep their average density.

**Density of cirrus:** fibers, channel G of the volume form, on 64 km to the east and 16 km to the north, sheared. They are multiplied by B, by the envelope and by 0,018.
- **Their reference frame is fixed:** the same east and the same north on the whole planet (`CLOUD_CIRRUS_*`).

**Precision:**
- **in double precision:** the camera, the view and the distances, from an anchor placed on a grid of 32 km.
- **In float,** only the local remainder: no absolute coordinates enter into a noise reading.

**Light, at every step in a cloud:**
- **Extinction:** 80 /km per unit density, water albedo 1; 0,5 g/m³ at 10 µm of effective radius.
- **To the sun:** six steps, from 125 m to 4 km, 7,875 km in all, the entire lower layer; Beer on the density crossed. **Away from it:** three steps, from 500 m to 2 km, 3,5 km, for the rest of the chord.
- **The simple phase:** Henyey-Greenstein, g = 0,85, that of the drops (Bohren and Huffman).
- **The sun and the sky** come from the atmosphere tables, at the altitude of the step: `SunTransmittance`, `MultiScattering`, `SkyIrradiance`.
- **The multiple scattering,** isotropic, a property of each point: `σ W (S_soleil μ + E_ciel) F e^(−λ L) / (1 + b τs) / 4π` per km, diffuse transmission of a layer towards the sun, summed along the view; W = 3,40, b = 0,040, k = 0,061, calibrated on Monte Carlo layers (`tools/calage_orbite.py nuages`); λ = 0,20 on spheres (`relief`).
  - **μ:** a layer receives the sun like a floor, `dot(haut, soleil)`; a cumulus like a ball, 0,5 on its illuminated face: `max(dot, 0,5 × famille, 0,05)`.
  - **F, the build-up:** `1 − exp(−k τ)`, τ the cloud's chord along the sun through the point, the nine samples, in density in the cloud, counted whole from 2 % covered and by their share below (`CLOUD_CHORD_COVER`). For a flat layer, τ / μ: the size of the calibration.
  - **The side leak:** `L = 80 Σ w (1 − f) f ρ Δs` on the six samples toward the sun, f their own covered part, `w = saturate(1 + mip of the step − mip of the view)`. Zero in a flat layer.
  - **Neither the pixel's seen point nor its column enters F or the leak** (`principes.md`); the samples toward the sun keep the column's overlap for what they transmit.
- **The detail and its reasons:** `spec-rendu-orbite.md`.

**The walk, in columns:** in the pixel, the clouds of a layer superimpose to the maximum; the cloudy column is the widest part encountered, fc, and only a part of 2 % wider expands it. When the ray has left the pixel footprint, the column closes and composes to the previous ones like a layer: random overlap beyond. The transmittance of the pixel is `1 − fc (1 − Tc)`.

**The march:**
- **The segments** of each layer are sorted along the radius, stopped at the ground and the ground of the planet.
- **Pitch:** half of the pixel footprint, 48 m at least, 240 m of height at most.
- **The void jumps:** in an empty map cell at mips 3 to 7, up to 80 % of the distance to its spherical edges, 50 km at most.
- **An illuminated step does not exceed an optical thickness of 1** as long as the column is transparent; opaque, it takes the geometric step.
- **The walk stops** when the pixel transmission drops below 0,003.
- **Quality Reference,** key C: not 24 m, 160 m of altitude by step.

**The distant quadrature, removed the 2026-10-31:** the pixel statistic replaces it (`log/spec-nuages-historique.md`).

**The shadow on the ground:**
- **One trace per pixel of illuminated surface,** from the point to the sun, through both layers, on the same density at the same time.
- **Pitch:** 250 m at least, 256 samples at most per segment.
- **It only attenuates the solar part:** `scène − min(part solaire, scène) × (1 − T)`. A 1 transmission leaves the exact image.
- **The solar part** is the second target of the scene (`sunPart`, t17). Land, sea, objects and vegetation write in direct sunlight, with the same alpha emissions as the color.

## The Passes

**A full screen pass follows the scene,** in the composite image (`D3DApp::Draw`, step 3). It reads the image HDR, its distance in alpha, and the solar share.

**The default time pass** (`CloudsTemporal.hlsli`; `optimisation.md`, rounds 1, 7 and 8):
- **The trace, `PSCloudTrace`:** one pixel per tile 4 × 4 and per frame, in Bayer order; each pixel has its trace in 16 frames. It writes light, transmittance, distance, sound standard deviation, shadow and distant weight.
- **The half-track, `PSCloudTraceHalf`,** under 14 km altitude only: one pixel per square 2 × 2, where the history of one pixel of the square has slipped.
- **The resolution, `PSCloudResolve`,** at full resolution. It takes the fresh trace; failing, the reprojected history, the clouds in the reference frame of the weather, their shadow on the ground; failing, the squares of the half-trace; failing, it draws the pixel. She composes the air and writes the following history.
- **A pixel traces** beyond 1 pixel drift, 1° rotation of view direction per frame, or 20 % distance change.
- **Two rays share their clouds when their surfaces cut none of them:** the history and the fills compare the ray ends as the clouds see them, 0 like the sky where the ray has left the low layer through its bottom before the surface (`CloudTemporalCloudEnd`). Compared as surfaces, toward the horizon where the sea's distance changes by 4 % a row, they refused their neighbours above and below: in a fast flight, a line fixed on the screen across the clouds (2026-11-02).
- **The history starts again** at a jump of the camera, the change of quality, the lighting of clouds, and when the sun turns more than 1°.

**The single pass, `PSMain`** (`AtmospherePass.hlsl`): every pixel traced, at every frame.
- **It serves** with `MYPLANETENGINE_CLOUD_FULL=1` or `-PassePleine` of the launcher, and always for the `weather` and `cloudshadow` views.

**The composition, `CloudComposite`:**
- **Air:** 12 not towards a surface, 24 towards the sky, in simple precision from the camera's altitude.
- **The cloud fits into its weighted distance:** it cuts in half the only step where it falls. The air remains continuous when this distance changes.
- **Behind:** the surface, its shadow removed; or, in the sky, the solar disc.

**The weather GPU,** time stamps 18 to 19: "clouds+air" in the title, column `atmosphere` of `tools/banc_perf.py`. The trace alone, timestamps 18 to 20, column `nuages_trace`.

## The b1, `CloudFrame`

**304 bytes, identical in C++ (`D3DApp.h`) and in HLSL (`Clouds.hlsli`),** held together by a `static_assert`. `D3DApp::Update` fills it.

| Champ | Contents |
|---|---|
|  `cloudCameraKm`  | the camera in the planet reference frame, km, double; w: 1 with clouds, key N |
|  `cloudForward`, `cloudRightTan`, `cloudUpTan`  | the axes of view, including the rolling of the ship; w: the tangents of the field |
|  `cloudWind`  | xy: sinus and cosinus of the wind angle; z: 1 in quality Reference |
|  `cloudSun`  | the direction of the sun |
|  `cloudPrevQ[3]`, `cloudPrevGround[3]`  | the previous camera, for reprojection, in the reference frame of the weather then the ground |
|  `cloudTemporal`  | xy: the pixel plotted from the tile; z: 1 if history is true; w: reserved |

## Resources

| Register | Resource | Format, size |
|---|---|---|
| b1 |  `CloudFrame`  | 304 bytes, sending buffer |
| t17 | the solar part of the scene | RGBA16F, full screen |
| t24 | shape and fibers, `shape128` ; B: the standard deviation of the shape under the texel, calculated at loading | RGBA8, 128³, 8 mips |
| t25 | erosion, `detail32` B = its standard deviation below the texel, calculated at loading | RGBA8, 32³, 6 mips |
| t26 | profiles, `weather64`  | RGBA8, 64³, 7 mips; mip 0's slice z, the mean over z texels of height |
| t27 | weather map, calculated at startup (`Climate::Weather`) | RGBA8, 1 024 × 512, 11 mips |
| s2, s3 | the noise functions, in repetition; the map | Linear |
| t44, t45 | fresh tiles, a texel by 4 × 4 | RGBA16F ; RGBA32F |
| t46 to t48 | read history: light, data, standard deviation and drift | RGBA16F; RGBA32F; RG16F, full screen |
| t49, t50 | half-track, a texel by 2 × 2 | RGBA16F ; RGBA32F |

- **Two historicals,** one read, the other written, exchange each frame.
- **Temporary images are not created** with `MYPLANETENGINE_CLOUD_FULL=1`.

## The air around the clouds

**Since the 2026-10-30, the air of the composition is again that of the atmosphere pass before the clouds** (`CloudAirPiece`, `IntegrateScattering`, `Atmosphere.hlsli`). In place, to be judged in flight:
- **Sun rays:** the shadow of the relief in the air, by the shadow height of each vertex (`recherche-rayons.md`).
- **The fog on the regional ground,** along the view: the boundary layer follows the ground of the planet map (`recherche-profondeur-atmospherique.md`, 3.5).
- **The solar disc,** behind the clouds and air, when the view does not meet the planet. It shows the portion of the pixel it covers.
- **Before this day,** the composition of the clouds omitted them: its air was that of a ground at sea level, without relief.

**The lens halo and temporal smoothing no longer depend on clouds** (`lancement.md`):
- **halo** is off by default; `MYPLANETENGINE_GLARE` activates it (`recherche-halo.md`);
- **the TAA** is cut off at startup; the T key restores it, `MYPLANETENGINE_TAA` at startup.

## Weather and canopy glass

- **One clock:** weather turns eastward around the axis of the planet, 12 m/s at the equator (`kWeatherWindSpeed`). The shapes do not deform. At the moment 0, the map is laid on the geography.
- **It starts in pause, at the moment 0.** Space the free camera replay; V goes from ×1 to ×5.
- **The test palette follows the wind:** each test finds its clouds when the weather has turned.
- **canopy glass reads the same clouds,** at the same time, instead of the ship: `ShipWeather.hlsl` includes `Clouds.hlsli`. It gets wet in a cloud, takes rain under its base.
- **The temperature** comes from the climate map, at sea level minus 6,5 °C/km (`spec-climat.md`). See `spec-vaisseau.md`.

## Diagnostic views

**By `MYPLANETENGINE_VIEW`,** at direct launch of the exe: the launcher deletes the variables.

| View | What it shows | Passe |
|---|---|---|
|  `clouds`  | opacity of clouds, 1 − transmittance | both |
|  `weather`  | the flat weather map: blue to orange the coverage by family, magenta the cirrus | single |
|  `cloudshadow`  | transmission to the sun on any surface facing it; white, no shadow | single |
|  `ground`  | the view of the ground, under the clouds silhouette; key B | both |

- **Other views of the terrain are measurements:** no clouds or air above.

## Variables and keys

| Variable | Effect |
|---|---|
|  `MYPLANETENGINE_NO_CLOUDS`  | cloudless, like N |
|  `MYPLANETENGINE_CLOUD_FULL=1`  | single pass |
|  `MYPLANETENGINE_WEATHER_TIME`  | the time of the weather, in seconds |

| Touche | Effect |
|---|---|
| N | clouds, yes or no |
| C | quality, Eco or Reference |
| B | the view of the ground under their silhouette |
| Space | the weather resumes or stops, in free camera |
| V | weather ×1 or ×5 |
| O, P | the sun is turning |

- **The title** says the quality, the state of the clouds, the time and speed of the weather, and the time "clouds + air".
- **benchmarkss pose their variables themselves,** and run only on demand: `tools/banc_perf.py` (`--full`, `--weather`, `--motion`); `tools/banc_composition_surfaces.py`, which checks that a transmission from 1 leaves the surfaces intact.

## Data and its origin

**Three textures frozen in `assets/clouds`,** 10,9 MB: RGBA8 without header, mips in the following, x the fastest. The exe finds them above it, like the ship; if it misses one, it stops with a message. The weather map is no longer an asset: it is calculated at startup.

| File | Role | Done by |
|---|---|---|
|  `shape128`  | R: the shape; G: the cirrus fibers | R : TileableVolumeNoise de Hillaire (MIT), commit `1f879a26` ; G : generated fibers |
|  `detail32`  | R: erosion | TileableVolumeNoise |
|  `weather64`  | RG: profiles by family and height | profiles written at the main |

- **`manifest.json` is authoritative:** SHA-256 footprints, role and source of each texture.
- **The old map,** of the fields of noise without link with geography, and its generator are removed the 2026-10-31: `log/spec-nuages-historique.md`.
- **The three volumes no longer regenerate in this repository.** Their chain, generators and sources, from `third_party/FrostbiteNoise` to `assets/frostbite-orbit`, is `jalon/26-nuages-main`.
- **Licenses:** `NOTICE`, parts 1 and 2; `LICENSES/MIT-TileableVolumeNoise.txt`; `third_party/WickedEngine/LICENSE.txt`.

## Known defects

**The time pass, in motion:** three defects seen in flight the 2026-10-28, set aside to finish the performance rounds.
- **The 6 round corrects them to benchmark:** every fresh trace checks the history. But it costs 4 to 6 ms more in slow flight, at altitude and near cumulus. It is the tag `piste/optimisation-r6-nuages-mouvement`, to take over by a variant cheaper.
- **The noise at high speed:** in altitude, in fast flight, a grain on the clouds. Suppose cause: three grains mixed, that of fresh pixels at a far radius, pixels traced at four, and softened history. The distant quadrature removed the 2026-10-31 removes the first two: to be reviewed in flight.
- **Ghosting in orbit dive:** by approaching very quickly a formation, trails of its size or more, which disappear in 2 to 3 s at rest. Suppose cause: the distant mean keeps its radii while the footprint shrinks. The distance kept is wrong, and the drift, calculated from it, does not see it (`optimisation.md`, round 1).
- **A line at the horizon behind the clouds, in a fast flight:** corrected on 2026-11-02, the clouds' end (above, the passes). Measured against the single pass, flying fast toward a cumulus wall at 3,7 km: the row step at the horizon 0,54 → 0,08 in sRGB levels.
- **Trails approaching a cumulus:** near the ground, moving towards a cumulus then retreating, checkered trails 4 × 4 around its silhouette, for a few images. Suppose cause: the edge moves forward in the sky without measurable drift; the history is kept while the fresh trace contradicts it.

**The cost:**
- **Since 2026-11-02, the light per point and the temporal pass tested on the clouds,** against `bfa6113`, 1920 × 1080, clouds and air: still, 2,0 → 2,1 ms from orbit, 4,3 → 5,0 at 40 km, 9,8 → 11,0 at 8 km, 4,9 → 5,3 at 3,7 km, 7,8 → 8,2 at 2 km; in a fast flight, 22 → 25 to 28 ms at 40 km, 27 → 32 at 8 km, 14,8 → 17 at 3,7 km, 17,9 → 20,2 at 2 km. Accepted by the user to be resumed in an optimization phase: no optimization was removed, the cost is the three samples per lit step and the pixels traced again rather than wrongly filled (`spec-rendu-orbite.md`).
- **Beyond ×5 in orbit,** the pass costs the single pass, 10 to 38 ms: each cloud is seen at an angle that rotates too fast.
- **Above the sea,** the racing rays walk the low layer without proving anything of emptiness: 4,6 ms to round 1.

**Limitations of the model:**
- **The map** has a texel of about 39 km at the equator: no finer regional variation.
- **Geography is just right now 0:** the clock turns the map one block east, 43 km per hour to ×1; over the hours, deserts and swamps shift from their coasts.
- **Depressions are templates,** of a common form at their scale and stage near; they do not be born or die.
- **Cirrus** keep a fixed reference frame, not a local wind.
- **Forms do not live:** weather turns a block, without formation or dissipation.
- **No cumulonimbus, no visible rain, no fog on the ground.**
- **No cloud shadow in the air,** only on the ground.

## Next steps

- **The three defects in motion,** by a history check less expensive than the round 6.
- **Precalculated transmittances to the sun,** for shadow and light: the lever for the cost of the light per point, the nine samples of each lit step read once in a volume.
- **A weather that lives:** the ZCIT and the blankets fixed on the planet, the depressions that follow the rails; the direction of cirrus, cumulonimbus.

## The references

- **[Frostbite 2016](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016-pbs-frostbite-sky-clouds-new.pdf),** Hillaire, §5.3.1: weather map for cover and type; density and erosion profiles separated from the noise functions 3D. §5.9: cloud shadows in transmittance texture, on a flat planet; here, traced on the globe.
- **[Epic, Volumetric Clouds](https://dev.epicgames.com/documentation/unreal-engine/volumetric-clouds?application_version=4.27):** secondary paths for ground-to-space transition; faster shadow maps for surfaces.
- **[NASA, Earth's Clouds on the Move](https://science.nasa.gov/earth/earth-observatory/earths-clouds-on-the-move-154443/):** tropical convergence and mid-latitude systems; here, soft trends, not rings.
- **Wicked Engine,** `volumetricCloudsHF.hlsli` and `volumetricCloud_renderCS.hlsl`, commit `5433f0a6`: the shader base.
- **The state of the art and the original plan:** `recherche-nuages.md`.
