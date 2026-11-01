# Search: clouds, from orbit to ground

Status: search for the 2026-10-24: state of the art, time map, types and rendering, from orbit to ground. What she gave the 24 and 25 October, the layer 2D then the old volume in cascades, tag `piste/nuages`, is in the log: `log/recherche-nuages-historique.md`. The clouds in the game, in place, are described by `spec-nuages.md`: they come from Frostbite and Wicked spikes, not from this plan. Covers clouds, fog and strata that touch the ground, and their connections with the atmosphere and terrain. Fog and aerial perspective are another research: we talk about them here only where they touch the clouds.

## 1. Conclusion and plan

**The conclusion.**
- **One time map, two more noise functions.** Two calls to `Fbm3`, placed on the climate that already exists, decide the cover, type, base and thickness. All engines do this: Horizon, Frostbite and Unity read three numbers per air column in a 2D texture.
- **One field, two ways to integrate it.** From afar, a 2D layer shows the exact mean of the field on the pixel. Close up, a volume in rays shows its shape. Both have the same optical thickness per column: the passage does not change the cloud portion.
- **The universal rule applies as it stands.** The cover is a threshold on a noise. `SpreadStep` and `FbmLostShare` give the pixel share under a cloud, the same at any distance.
- **The base comes from the climate.** Lawrence (2005): base ≈ (20 + T/5) × (100 − HR) m. When the air is saturated, it falls to the ground: it is fog.
- **The cost holds.** 2D layer and shadows: 0,3 to 0,9 ms in 1440p, estimated. Close volume: 1 to 2 ms targeted, in quarter resolution with time accumulation, like Unreal and Horizon.
- **Not published deals with the passage from orbit to ground under the rule of average.** Unreal and Star Citizen are shooting their rays from space. The SpaceEngine team judged in 2017 that no method held ground space. The layer 2D as average volume is our proposal.

**The plan.**

| Stage | Contents | Measure of success | Cost |
|---|---|---|---|
| 1 | The weather map, and a diagnostic view `clouds` : the cloud share per pixel, without rendering | fraction per band of 10° of latitude to 10 points of MODIS at most; constant share at 2 points near 1 500 to 60 km to benchmark of descent | less than 0,1 ms |
| 2 | The layer 2D illuminated, in the atmosphere pass; its shadows on the ground; the light diffuses under a ceiling | aspect against photos of the ISS, at equal height and sun | 0,3 to 0,9 ms |
| 3 | The volume near the camera, on the same board; the fade to the layer 2D | Transition benchmark: same area in 2D and volume, average to 2 % close | 1 to 2 ms |
| 4 | All types: Cumulonimbus and anvils, high clouds, valley fog, relief clouds; a land-sea map cooked at startup | height distribution vs. CALIPSO; types vs. ISCCP; ground photos by gender | to be measured |
| 5 | Fine light: shadows of clouds in the air, ground that illuminates their base, shadow map near the ground | photos of sunsets and rays | to be measured |

**The step 1 is small and measurable.**
- **What it touched:** a `Clouds.hlsli` file, one more diagnostic view in `PixelShader.hlsl` and `D3DApp.cpp`, a benchmark `tools/banc_nuages.py`. Make the 2026-10-24, remove the 2026-10-30 with the old volume, tag `piste/nuages`.
- **Nothing is displayed in flight:** we put the map on the data before drawing a cloud.

**What we leave for later:** wind and evolution in time, rain, lightning, halos. Clouds fixed on the planet reproject themselves exactly from one frame to another, like the terrain.

## 2. The map of time

### What the engines do

| Engine | The map | What she decides |
|---|---|---|
| Horizon Zero Dawn, Schneider 2015 | texture 2D: red cover, green precipitation, blue type; output from a weather simulation, or painted for cinematics | three profiles in height, stratus, stratocumulus, cumulus, mixed by type; precipitation leads to cumulonimbus towards 70 % cover |
| Frostbite, Högfeldt 2016, §5.3.1 | weather texture 2D painted: red the projected cover, green the type; repeatable as needed | separate table type × height: density and erosion; noise3D for shapes and detail |
| Unity HDRP | map: red cover, green rain, blue type; table type × height: profile, erosion sensitivity, occlusion | four presets: scattered, cloudy, cloudy, thunderstorm |
| takram three-clouds | up to four layers, one per channel of a weather texture; profile a·e^(bη) + cη + d | base and thickness per layer |
| Unreal, Hillaire 2020 | a free solid material, in a given base layer and thickness | all, at the price of one graph per project |
| Red Dead Redemption 2, Bauer 2019 | clouds and fog in one single ray | not detailed outside slides |
| Flight Simulator | Meteoblue forecasts | Data Clouding Not Published |

- **The common point:** three or four numbers per air column, cover, type, base, thickness, and a vertical profile per type.
- **Horizon draws its low volume clouds, from 1 500 to 4 000 m,** and the medium and high texture clouds 2D that scroll above.
- **These cards are textures that repeat themselves.** Schneider describes them as several noise functionss that parade, sometimes retouched to the main. On an entire planet, a noise on the planet grid replaces them without repetition.

### Our map: four layers, one of which exists

| Layer | noise | Wavelengths of light | What she decides |
|---|---|---|---|
| The climate | existing: `regional` of `GroundMaterials`, `ClimateHumidity`, temperature | 3 000 to 200 km | average cloudiness, base |
| The Time, The Time `W`  | and `Fbm3`  | 4 000 to 30 km | x: fronts and depressions; y: convection strength; z: high clouds |
| Clouds, Clouds and Clouds, `M`  | and `Fbm3`  | 30 km per pixel | x: presence, threshold; y: thickness; z: detail of high clouds |
| The detail, close up only | a 3D tile generated at startup | 2 km to 20 m | erosion of the edges, bulging or fraying |

- **`Fbm3` gives three noise functions for the price of one grid:** each layer costs one call.
- **The price:** 15 to 25 octaves per pixel in all. The relief requires about 340 per vertex.

### What each magnitude follows

**The target cloud cover, `cloudiness`,** the expected average share of cloudy sky over the region.
- **The humidity of the climate already bears a part of it:** its depression towards 24° of latitude is that of the deserts, under the descending branch of the circulation. The same air drops clear the sky.
- **Two rising belts to be added,** of the same Gaussian shape of latitude: the intertropical convergence zone near the equator; the middle latitudes, especially the Southern Ocean.
- **MODIS shows them as follows:** many clouds in the intertropical zone, over the Southern Ocean and on the cloud banks stratocumulus; less of 15 to 30° latitude; little over deserts, Greenland and Antarctica (King et al. 2013).
- **Weather, `W.x`,** adds fronts and depressions: large areas covered from 500 to 2 000 km.
- **Seas more than land:** 72 % vs 55 % on Earth, 67 % on average (King et al. 2013). You need the land-sea map: step 4.

**The pixel cover, `cover`.** A threshold on `M.x`, set so that the part above is worth `cloudiness`.
- **Threshold:** t = 0,146 × Probit(1 − cloudiness), 0,146 being the standard deviation of `Fbm3`. Probit(p) ≈ ln(p / (1 − p)) / 1,7 is sufficient.
- **The share of the pixel:** `SpreadStep` around t, enlarged from what the pixel does not show from `M`, by `FbmLostShare`. The average part does not move with distance.

**The type,** from 0 to 1: 0 stratiform, 0,5 cumulus, 1 cumulonimbus. Like the blue channel of Horizon and Unity.
- **Convective when the air is hot and humid at the bottom:** sea level temperature, humidity, `W.y`.
- **Cumulonimbus where air rises:** intertropical zone, and `W.y` strong.
- **Stratiform under air descents, on sea:** the cloud banks stratocumulus of the eastern edges of subtropical oceans. Their coverage increases by about 6 % per degree of air stability (Klein and Hartmann 1993).
- **Stratiform in fronts:** `W.x` strong at medium latitudes gives nimbostratus and altostratus, with cirrus in front.
- **Stratus and fog in the wet cold,** when the base falls to the ground.

**The base,** above sea level: z ≈ (20 + T/5) × (100 − HR) m, to 15 % close for HR from 50 to 100 % and T from 0 to 30 °C (Lawrence 2005).
- **T:** the temperature of the climate at sea level, without the altitude of the place.
- **HR:** derived from climate humidity; the correspondence is set to benchmark 3.
- **Orders of magnitude:** 750 m for 25 °C and 70 %; 0 m to 100 %; more than 2 km on deserts.
- **The base is the same over the plains and mountains of a region.** Where the relief exceeds it, the ground is in the cloud: the hill fog comes without rule more, and the summits drop a sea of clouds.

**The top,** depending on the type.
- **Stratus, stratocumulus:** a few hundred meters above the base, under the inversion (Wood 2012).
- **Cumulus:** 0,5 to 2 km thick, modulated by `M.y`; up to 6 km in congestus.
- **Cumulonimbus:** up to the tropopause, from 16 km in the tropics to 8 or 9 km at the poles. A function of latitude is sufficient.
- **High clouds:** a layer apart, drawn from `W.z` and neighboring cumulonimbus: the anvils spread out in cirrus.

### The sketch of the function

```hlsl
// Clouds.hlsli, proposal. q: planet point relative to the anchor; pixel: log2 of its size on the layer (m).
const float3 W = Fbm3(q, log2(4.0e6), log2(3.0e4), pixel, 0.5, 71u);  // weather
const float3 M = Fbm3(q, log2(3.0e4), 0.0, pixel, 0.55, 73u);        // clouds
const float cloudiness = saturate(c0 + c1 * (humidity - 0.6) + Belts(sinLat) + c2 * W.x); // to calibrate, benchmark 1
const float t = 0.146 * Probit(1.0 - cloudiness);
const float sigma = 0.146 * sqrt(FbmLostShare(log2(3.0e4), 0.0, pixel, 0.55));
const float cover = SpreadStep(t - 0.02, t + 0.02, M.x, sigma);       // fraction of the pixel under a cloud
const float base = (20.0 + seaLevelT / 5.0) * (100.0 - RelativeHumidity(humidity)); // m, Lawrence 2005
```

### The relief, the land and the sea: stage 4

- **Clouds need to know what is beneath them,** hundreds of miles from the camera: land or sea, smooth relief. You cannot evaluate complexplanet at every step of a radius.
- **Proposal: a card baked at startup,** like the materials tiles. A cubemap of 6 × 512² texels, about 20 km, with the relief filtered to its grid cell, the sea share, the rough weather map. His mipmaps keep the average.
- **What it allows:**
  - more clouds at sea than on land, and stratocumulus at sea only;
  - relief clouds: windward, the air rises, and the cloudiness increases with the slope of the smoothed relief face windward; leeward, the sky opens (Houze 2012);
  - valley fog: it fills the relief under a summit of fog drawn from the smoothed relief, to the cold humid;
  - the dominant winds by latitude, trade winds from the east then winds from the west, to orient the streets of clouds and cirrus.

### What keeps the card under our rules

- **noise gradient, `Noise3`, on the planet grid.** Clouds are fixed in the reference frame of the planet, never relative to the anchor.
- **No noise is erased:** its invisible part expands the coverage threshold.
- **A deviation to document:** the bulging form of the cumulus comes, in all, from a cellular noise of Worley. The repository has one, `VoronoiDistance`, and `Billow`. Try first a Billow on `Noise3`, and keep the cell only if the benchmark appearance justifies it.

## 3. Types of clouds

**The heights of the International Atlas of Clouds,** by floor:

| Floor | Poles | Medium latitudes | Tropics |
|---|---|---|---|
| High: cirrus, cirrocumulus, cirrostratus | 3 to 8 km | 5 to 13 km | 6 to 18 km |
| Medium: altocumulus, altostratus | 2 to 4 km | 2 to 7 km | 2 to 8 km |
| Low: stratus, stratocumulus, cumulus, base of cumulonimbus | 0 to 2 km | 0 to 2 km | 0 to 2 km |

- **Exceptions in the Atlas:** The nimbostratus overflows on the other floors; cumulus and cumulonimbus have their base at the bottom and rise up to the middle and upper floors.

**Types, their appearance and profile.** Thickness and optical thickness in orders of magnitude, to be confirmed at the benchmark ISCCP.

| Type | Base | Thickness | Optical thickness | Aspect | Profile in height |
|---|---|---|---|---|---|
| Stratus, fog | 0 to 500 m | 0,1 to 0,5 km | 5 to 20 | uniform gray; orbit, smooth layer that embraces the valleys | dense all over, cut clean at the top |
| Stratocumulus | 0,3 to 1,5 km | 0,2 to 0,5 km, under inversion | 5 to 15 | hump, gray beaches; orbit, open or closed cells | grows upward, flat top |
| Cumulus | 0,5 to 2 km, higher on dry | 0,5 to 2 km; congestus up to 6 km | 5 to 50 | flat and dark base, cauliflower top, clean edges | grows upwards, rounded tip; domed at the top, frayed at the bottom |
| Cumulonimbus | 0,5 to 2 km | to the tropopause; anvil from 50 to 200 km | 50 to more than 100 | white tower, black base, rain curtains; orbit, smooth disks | column; at the top, cover threshold lowered: the anvil spreads |
| Nimbostratus | 0,5 to 2 km | 3 to 7 km | 20 to 60 | dark gray, blurred base, rain | thick, soft, diffuse base |
| Altostratus | 2 to 7 km | 1 to 3 km | 5 to 20 | gray veil, sun as behind a frosted glass | uniform |
| Altocumulus | 2 to 7 km | 0,2 to 0,7 km | 1 to 10 | rollers in cloud banks | thin, dented |
| Cirrus and neighbours | 5 to 13 km; 6 to 18 km in the tropics | Coin | 0,1 to 3 | filaments, veils, halos | layer 2D stretched in the wind |

- **The optical thickness ranges from less than 0,1 for a thin cirrus to more than 1 000 for a large cumulonimbus** (AMS glossary).
- **Stratocumulus covers more of the Earth than any other type,** more than half of the fresh subtropical oceans on an annual average; they are thin, at the top of the boundary layer (Wood 2012).

**How engines represent them.**
- **A density profile per type,** based on the relative height η in the layer: Horizon has three, Unity a table type × height, takram a formula.
- **Density increases upward** in convective clouds: condensed water increases with height above the base. Horizon and takram do.
- **Erosion:** a noise finely trenched at the edge, stronger where density is low. Inverted at the bottom, it shreds the base: Horizon, Frostbite.
- **The high clouds in 2D:** Horizon draws them in textures that slide; their low thickness justifies it.

**Our table of types:** a small texture type × η, generated at startup. It gives the density, erosion, the bulging or flaking part, and the integral of the profile for the optical thickness of the layer 2D.

**Fog is a cloud whose base touches the ground.**
- **Same model, same extinction.** Visibility is worth 3,9 / σ (Koschmieder).
- **In a cloud of water,** σ ≈ 3 × liquid water / (2 × density of water × effective radius) (Stephens 1978): 0,02 to 0,1 m⁻¹, or 40 to 200 m of visibility.
- **The fog starts under 1 km of visibility.** Beyond, it is the fog, of the other search.

## 4. The rendering, from orbit to inside a cloud

### The state of the art: volume beam throw

- **Beer-Lambert, integrated step by step.** Hillaire analytically integrates light on each step: the result no longer depends on the length of the step. Our `IntegrateScattering` already does it for air.
- **The multiple scattering in octaves of single scattering** (Wrenninge 2013): each octave diffuses more, is less shaded, and has a more isotropic phase. Unreal recommends one octave in game, two at most.
- **The phase:** Henyey-Greenstein with two lobes, front and rear: Unreal, takram.
- **The "powder" effect of Horizon,** the dark edges facing the sun. Hillaire judges it non-physical: he prefers to lower the albedo at the edges, where density falls.
- **Sunlight.** Horizon takes 6 samples in cone towards the sun, the last away, for the shadow of neighboring clouds. Unreal also offers its Beer shadow map: less precise, in gray, but with unlimited range.
- **Sky:** an ambient light that increases with height in the cloud.
- **Bounce vacuum:** not coarse out of cloud, fine in; stop when transmittance goes below 0,01. Nubis 2023 adds signed distance fields.

**The tricks of resolution.**
- **Horizon:** one pixel on 16 recalculated per frame, the rest reprojected. From 20 ms to about 2 ms on PS4.
- **Unreal, 0 mode:** trace in quarter resolution, rebuilt in half, then full. Recommended from ground to space.
- **Toft et al. 2016:** 8 not instead of 128, with random start and time accumulation.
- **The price:** trails and ghosts on what moves fast. Nubis 2022 devotes a part to it, and targets 1080p without temporal reconstruction.

### Engines on a planet scale

- **Unreal:** the same throw of space rays to the ground, 0 mode recommended. Hillaire shows small planets with the soft shadows of their clouds.
- **Star Citizen:** demonstration of 2023, planetary volumetric clouds and space to ground passage. Technique not published.
- **Michelic et al. 2019, poster of I3D:** volumetric clouds and pre-calculated atmosphere, continuous transitions from ground to space, more of 120 images/s. Details not published.
- **Pixar, 2022:** a 2D image of clouds embedded in a thick spherical shell, for views of space.
- **takram three-clouds:** layers on the ellipsoid, only space views provided.
- **Elite Dangerous Odyssey:** light atmospheres, no weather system. **No Man's Sky, Outerra:** nothing published; Outerra had only one layer.
- **SpaceEngine, 2017:** no method considered good enough from space to ground.

### Our proposal: one field, two integrators

**From far: the layer 2D, exact average of the field.** One spherical shell per layer. At its intersection with the radius:
- **The pixel portion covered, `cover`,** by the universal ruler. The size of the pixel on the shell is worth the distance times the angle of the pixel, divided by the cosine of the bearing.
- **The optical thickness in the cloud,** τ = σ × thickness × integral profile.
- **The average transmittance of the pixel:** 1 − cover + cover × e^(−τ/μ). This is the average of transmittances, not the transmittance of the average: e^(−τ) is not linear.
- **The reflected light,** two-stream, non-absorbing cloud: R ≈ (1 − g) τ / (2 + (1 − g) τ), with g ≈ 0,85 (Bohren 1987). τ = 10 women R ≈ 0,43; τ = 50, 0,79. The rest, 1 − R, passes through diffused. The postman is stuck on the photos.
- **The lighting comes from our tables:** the transmittance of the sun to the top, the irradiance of the sky.
- **The relief of the summits:** the height of the summit varies with the thickness; its slope gives a normal, as for a terrain. From orbit, the cumulus fields are read in bumps.

**Close up: the volume.**
- **Density:** cover × profile(type, η) × erosion by tile 3D.
- **Erosion is a threshold on a noise: same rule.** The mipmaps of the tile give the average under the footprint; its invisible part broadens the threshold.
- **The volume column has the optical thickness of the layer 2D:** the types table bears the integral of the profile, and the transition bed checks the equality.
- **Quarter resolution and temporal accumulation,** in a cloud-specific history, reprojected by their average depth.
- **In volume, `Fbm3` would cost too much at each step.** The coarse map is read in the cubemap of the 4 step, the fine in a 2D tile generated, like the materials tiles.

**The passage.**
- **The criterion:** the thickness of the cloud on the screen, in pixels. Under a pixel, the volume adds nothing that the 2D layer does not already have.
- **At 1440p, one pixel covers 0,73 mrad.** A cloud of 1 km thickness makes 14 pixels to 100 km, 5 pixels to 300 km.
- **The budget limits the volume:** up to 100 at 200 km, takram stops at 200 km; then a fade to the 2D on a 2 factor of distance. It will be seen from the side, towards the horizon: the transition benchmark measures it.
- **From orbit,** any cloud is more than 200 km: layer 2D alone.
- **High clouds remain in 2D** at all distances, as in Horizon.

**In the cloud.** The ray comes from the camera, the density is that of the volume, the fog the same. Visibility comes from σ alone.

**The limit of the layer 2D:** towards the horizon, the cloud sides fill the holes between them; a shell without thickness leaves them open. This is one more reason for the volume near the ground.

### The budget

**What is published.**

| Source | Equipment | Method | Cost |
|---|---|---|---|
| Horizon, 2015 | PS4 | 64 to 128 not, 6 light samples; 1 pixel on 16 per frame | 20 ms, then about 2 ms |
| Toft et al. 2016 | GTX 1080, 1080p | half resolution, 8 not, random start, accumulation | 7,5 ms; 2,4 ms in quarter resolution; 297,7 ms for 128 not in full resolution |
| Unity HDRP, 2021 | PS4; GPU high-end recent | Not specified | 2 ms; less than 0,5 ms |
| Frostbite, Högfeldt 2016 | Radeon HD 7870 | 960 × 540, accumulation at 5 % | curves only |
| takram, version 0.0.1 | RTX 4090, browser | 1/16 of texels by frame | 60 images/s, ceilinged |

**Our estimates, to be measured, on the RTX 4070 Ti.**
- **The 2D layer:** two `Fbm3` per pixel. `GroundMaterials` does more for 0,1 to 2 ms of rendering. Estimated 0,2 to 0,6 ms in 1440p.
- **Shadows on the ground:** one more `Fbm3` per pixel of ground, 0,1 to 0,3 ms.
- **The volume:** quarter of resolution in 1440p, 0,9 million rays, 64 not at most. The 4070 Ti calculates about four times faster than a GTX 1080, and the screen has 1,8 times more pixels: Toft would give about 1 ms. Target: 1 to 2 ms.

## 5. With the atmosphere and the terrain

**Compose with the atmosphere.**
- **Layer 2D enters the loop of `IntegrateScattering`.** At the step that crosses the shell, the light of the cloud is added, multiplied by the transmittance already accumulated; then the transmittance is multiplied by that of the cloud. The air and the ground behind are veiled as much.
- **Volume renders light, transmittance and opacity weighted average depth.** The atmosphere pass inserts the cloud at this depth.
- **takram does the same,** with flaws when two scattered clouds overlap at different distances. Unreal offers a step-by-step aerial perspective, more expensive.
- **The depth of clouds passes in floating 32 bits,** like that of the field: pass accuracy rule.

**The atmosphere illuminates the clouds.**
- **Sun:** the transmittance table gives its color to the altitude of the point. At nightfall, the clouds blush from below. Hillaire takes it every step for sunsets.
- **Sky:** the irradiance table stops at 10 km. It must be climb to 18 km for the summits of cumulonimbus and cirrus.
- **The ground illuminates the base,** more on snow or desert. Unreal offers optional: step 5.

**Clouds act on the atmosphere.**
- **Under a ceiling, the air no longer diffuses direct sunlight.** Otherwise, the air under a cloudy sky remains blue and bright: a visible fault.
- **The simple remedy:** at every step of the atmosphere under the layer, the coarse shadow, drawn from `W` alone.
- **The sun rays between the clouds** come from the same shadow, taken more finely: step 5.

**The shadow on the ground.**
- **Analytical, without shadow map.** At the ground point, the ray to the sun crosses the shell; the average transmittance at this point is the shadow. Its shift with the height of the sun comes by itself.
- **It follows the pixel rule:** the shadow share is the average of what the pixel covers.
- **A shadow map does not fit the scale of a planet:** of orbit, it should cover a hemisphere. Unreal limits it to a radius around the camera. It will only serve the volume near the ground.
- **Diffused light under clouds:** the diffused part, 1 − R, less the direct, is added to the sky light. Under a thick ceiling, the floor is illuminated without casted shadows.

**The fog, where it touches the clouds.** Points to share with other research.
- **Same height of limit layer:** the fog of the lower layers stops below the inversion, at the top of the stratocumulus, or towards the base of the cumulus. Proposal: One field for both.
- **Same humidity field:** aerosols swell with humidity; around 100 %, the cloud takes over.
- **A continuous extinction of the fog to fog,** on both sides of 1 km of visibility.

## 6. Measure

**benchmark 1, the cloudy fraction by latitude.** Step 1.
- **Reference:** MODIS, monthly cloud fraction, annual average per band of 10°. Images on NASA NEO; numbers to 1° in products MOD08_M3 and MYD08_M3, with a free Earthdata account.
- **Our measurement:** the `clouds` view rendered in equirectangular at 1°; each pixel white with the probability of its coverage, like the other diagnostic views. Alternatively, vertical captures on a grid of places.
- **The target:** the profile shape, and an average close to 67 %. Spread per band under 10 points.
- **Later:** Separate land and sea, 55 % and 72 %, with the land-sea map.

**benchmark 2, the descent.** `tools/banc_descente.py` with the view `clouds`: the cloud share of an area of 60 km, from 1 500 to 60 km high. A flat curve, at 2 points close, proves the universal rule.

**benchmark 3, heights and types.**
- **CALIPSO-GOCCP:** Cloud cover by latitude, longitude and elevation, per month. Compare our cut latitude × altitude: bases, summits, tropical towers.
- **ISCCP:** nine types by top pressure and optical thickness. Compare the share of each type by latitude band.
- **The base:** Lawrence's formula against the table of his article; the distribution of bases against GOCCP.

**benchmark 4, the orbit aspect.**
- **The photos of the ISS,** base « Gateway to Astronaut Photography of Earth »: each gives its point at the nadir, the altitude, the angle of the sun and an estimated coverage.
- **Engine captures** at the same height and in the same sun, in a place with the same climate.
- **Measurements:** Covered part, luminance histogram, power spectrum for cell and hole size, shadow shift.
- **Blue Marble 2002:** its layer of clouds, composed of two days of MODIS, for the overall appearance.

**benchmark 5, the appearance on the ground.**
- **Photos from the International Atlas of Clouds,** by type, at known or estimated sun height.
- **Measurements:** luminance ratio between base and sky, contrast of edges, spectrum, as `realisme.py`.
- **The transition benchmark,** at the 3 step: same area in 2D and volume, at the swing distance; average deviation and standard deviation of luminance.

**The cost:** the clouds pass in ms to 1, 10, 100, 400 and 2 000 km, like the rest of the log.

## 7. Sources

**Engines and conferences.**
- Schneider, *The Real-time Volumetric Cloudscapes of Horizon Zero Dawn*, SIGGRAPH 2015 : [slides](https://www.advances.realtimerendering.com/s2015/The%20Real-time%20Volumetric%20Cloudscapes%20of%20Horizon%20-%20Zero%20Dawn%20-%20ARTR.pdf)
- Schneider, *Nubis: Authoring Real-Time Volumetric Cloudscapes with the Decima Engine*, SIGGRAPH 2017 : [page](https://www.guerrilla-games.com/read/nubis-authoring-real-time-volumetric-cloudscapes-with-the-decima-engine)
- Schneider, *Nubis, Evolved*, SIGGRAPH 2022 : [page](https://www.guerrilla-games.com/read/nubis-evolved), [PDF](https://advances.realtimerendering.com/s2022/SIGGRAPH2022-Advances-NubisEvolved-NoVideos.pdf)
- Schneider, *Nubis³*, SIGGRAPH 2023 : [page](https://www.guerrilla-games.com/read/nubis-cubed), [PDF](https://advances.realtimerendering.com/s2023/Nubis%20Cubed%20(Advances%202023).pdf)
- Hillaire, *Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite*, SIGGRAPH 2016 : [notes](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016_pbs_frostbite_sky_clouds.pdf)
- Högfeldt, *Convincing Cloud Rendering*, dissertation, Chalmers 2016: [PDF](https://publications.lib.chalmers.se/records/fulltext/241770/241770.pdf)
- Hillaire, *Physically Based and Scalable Atmospheres in Unreal Engine*, SIGGRAPH 2020 : [slides](https://blog.selfshadow.com/publications/s2020-shading-course/hillaire/s2020_pbs_hillaire_slides.pdf)
- Hillaire, *A Scalable and Production Ready Sky and Atmosphere Rendering Technique*, EGSR 2020 : [article](https://diglib7.eg.org/bitstream/handle/10.1111/cgf14050/v39i4pp013-022.pdf)
- Unreal Engine, volumetric clouds: [component](https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-cloud-component-in-unreal-engine), [properties](https://dev.epicgames.com/documentation/en-us/unreal-engine/volumetric-cloud-component-properties-in-unreal-engine)
- Bauer, *Creating the Atmospheric World of Red Dead Redemption 2*, SIGGRAPH 2019 : [course](https://advances.realtimerendering.com/s2019/index.htm)
- Unity HDRP, volume clouds: [manual](https://docs.unity3d.com/Packages/com.unity.render-pipelines.high-definition@14.0/manual/Override-Volumetric-Clouds.html); costs announced in the [blog Unity](https://blog.unity.com/technology/experience-true-volumetric-clouds-with-hdrp-unity-20212), read in a search snippet, page no longer responding
- Toft, Bowles, Zimmermann, Optimisations for Real-Time Volumetric Cloudscapes, 2016 : [arXiv](https://arxiv.org/abs/1609.05344)
- takram, *three-clouds* : [deposit](https://github.com/takram-design-engineering/three-geospatial/tree/main/packages/clouds)
- Flight Simulator 2024, summary of a developers' show: [msfsaddons](https://msfsaddons.com/2024/09/25/msfs-team-answers-questions-about-msfs-2024-in-latest-developer-livestream)
- Star Citizen, CitizenCon demo 2953: [DSOGaming](https://www.dsogaming.com/?p=175272)
- Michelic et al., *Real-time Rendering of Procedural Planets at Arbitrary Altitudes*, poster I3D 2019 : [page](https://www.cg.tuwien.ac.at/research/publications/2019/kerbl_2019_planet_poster/)
- Pixar, planets and clouds seen from space, SIGGRAPH 2022: [article](https://graphics.pixar.com/library/PlanetAndClouds/paper.pdf)
- Elite Dangerous Odyssey, planets show: [Massively OP](https://massivelyop.com/?p=324331)
- SpaceEngine, forum, 31 July 2017: [file](https://forum.spaceengine.org/viewtopic.php%3Fp=10919.html)
- Wrenninge, Kulla, Lundqvist, *Oz: The Great and Volumetric*, SIGGRAPH 2013 : [archive](https://history.siggraph.org/learning/oz-the-great-and-volumetric-by-wrenninge-kulla-and-lundqvist)
- Webanck et al., *Procedural Cloudscapes*, Eurographics 2018 : [PDF](https://perso.liris.cnrs.fr/eric.galin/Articles/2018-cloudscapes.pdf)

**Climate and cloud physics.**
- King et al., *Spatial and Temporal Distribution of Clouds Observed by MODIS*, IEEE TGRS 2013 : [PDF](https://atmosphere-imager.gsfc.nasa.gov/sites/default/files/ModAtmo/King_et_al.2013.pdf)
- Klein et Hartmann, *The Seasonal Cycle of Low Stratiform Clouds*, J. Climate 1993
- Wood, *Stratocumulus Clouds*, Monthly Weather Review 2012 : [publications](https://atmos.uw.edu/~robwood/publications.html)
- Lawrence, The Relationship between Relative Humidity and the Dewpoint Temperature in Moist Air, BAMS 2005, doi 10.1175/BAMS-86-2-225
- Houze, *Orographic Effects on Precipitating Clouds*, Reviews of Geophysics 2012
- Stephens, J., Radiation Profiles in Extended Water Clouds. Atmos. Sci. 1978
- Bohr, M. Multiple Scattering of Light and Some of Its Observable Consequences. J. Phys. 1987
- OMM, International Cloud Atlas: [floors](https://cloudatlas.wmo.int/en/useful-concepts.html), [welcome and photos](https://cloudatlas.wmo.int/en/home.html)
- AMS, glossary, optical thickness of clouds: [page](https://glossary.ametsoc.org/wiki/cloud-optical-depth/)

**Data for the benchmarks.**
- MODIS, monthly cloudiness: [NASA SVS](https://svs.gsfc.nasa.gov/30397/), [NASA NEO](https://science.nasa.gov/earth/nasa-earth-observations-neo/)
- CALIPSO-GOCCP, cloudy fraction 3D: [CFMIP-OBS](https://climserv.ipsl.polytechnique.fr/cfmip-obs/Calipso_goccp.html)
- ISCCP, cloud types: [project](https://isccp.giss.nasa.gov/projects/fieldvars.html), [ISCCP-H by type, ERDDAP](https://www.ncei.noaa.gov/erddap/griddap/iscpp_hgg_by_cloud_type.html)
- Photos of the ISS: [Gateway to Astronaut Photography of Earth](https://eol.jsc.nasa.gov/)
- Blue Marble 2002 : [Earth Observatory](https://earthobservatory.nasa.gov/Features/BlueMarble/BlueMarble_2002.php)
