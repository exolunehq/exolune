# Search: the sea and lakes, from orbit to water level

Status: search for the 2026-10-24, update the 2026-10-26. The nearest core is the sea FFT, in place since the `jalon/23-mer-fft-main`: `spec-mer-fft-spike.md`. Coast and lakes remain to be done.

## 1. Conclusion and plan

**In brief:**
- **The state of the art holds in three layers,** the hierarchy of Bruneton (2010): the waves larger than the grid cell in geometry, those larger than the pixel in normals, the rest in roughness of reflection. Serious productions all make a variation: FFT in cascades close, statistics from far.
- **This is our rule:** a pixel shows the average of what it covers. The slope of the waves that the pixel does not show becomes the roughness of the reflection. The whitecapss it does not show become a part of the pixel.
- **One single variable controls everything: wind at 10 m, U.** Measured laws derive the wave height, their average slope (Cox-Munk), the share of whitecaps (Monahan), the dominant wavelength. A wind map on our noise functions gives the calm sea, rough or stormy, consistent at any distance.
- **The first step does not require any waves.** From orbit and up to a few kilometers, the sea is seen by the reflection of the sun, the reflection of the sky and the whitecaps, all statistics. It is small, inexpensive and measurable against satellite data.
- **Lakes require more than just rendering.** The flat level of a lake depends on the entire basin, not the point: it takes a non-local hydrology pass, to be decided separately.

**The plan:**
1. **The statistical sea.** Wind map; reflection of the sun by Cox-Munk; Fresnel and reflected sky; whitecaps in pixel part. **First core measured in `log/recherche-mer-historique.md`; spike connection to be rechecked.**
   - **Measurements:** Reflection profile at 5 % of Cox-Munk formula; share of whitecaps flat down and equal to the law; quality benchmark unchanged on land.
2. **The color of the water.** Color of the deep sea bottoms by type of water, visible bottom in shallow water (Maritorena 1994), exact average on pixel depths. **Retained in spike; comparison to observations to be made.**
   - **Measure:** Orbit colors against Blue Marble or Sentinel-2, Lagoon, Plateau, Wide.
3. **The waves.** Spectre JONSWAP, FFT in cascades, geometry, normals and common slope moments, persistent foam triggered by the Jacobian. **Prototype in `spec-mer-fft-spike.md`; appearance to be judged, close coverage and statistical connection to be calibrated.**
   - **Measurements:** Beaufort force photos, luminance spectrum, reflection and whitecaps flats in descent, cost.
4. **The coast.** Waves dampened and refracted by depth, overflow when H > 0,78 d, edge foam in part of the pixel.
5. **Lakes.** Spec apart and decision: water level map by filling the bowls and water balance.

**What exceeds the rendering, reported:**
- **Lakes:** a non-local pass, see section 5.
- **The fetch,** distance over which the wind blows: not local, approached locally in section 2.
- **The water surface displaced:** of the geometry, but not that of complexplanet. To be entered in `geometrie.md` as water surface, out of the three families.
- **The bottom seen through the water, close up:** the grid cell cuts to 0 m (`Terrain.hlsli`), the bottom is not drawn. It is shown by parallax in pixels, not by geometry.
- **Time:** first animated parameter of the engine. The benchmarks must be able to fix it.

**Coordination:** clouds reflect in the sea and carry their shadow; the atmosphere already veils the reflection without adding anything. To be connected with the work on clouds and aerial perspective.

## 2. The sea state map, linked to our climate

**The principle:** a wind field, speed and direction, on the grid of the planet. Everything else follows from measured laws, without adjustment by place.

**Four layers of noise:**
1. **General circulation, by latitude:** trade winds, pot au noir, calm subtropical, west winds, polar east winds. Gaussian latitudes, like `ClimateHumidity` already poses one at 24° for deserts.
2. **Weather:** a vector of ±4 m/s drawn from a `Fbm3` of 3 000 to 300 km, new seed. It draws depressions and anticyclones, fixed at first; a slow drift will come with time.
3. **Gushes and calm winds:** a factor of ±30 % on speed, `Fbm3` from 100 to 5 km. Orbit reflection images show them: calm and bright spots, windy and dark spots (NASA, Arabian Sea).
4. **Swell, apart from:** a height and direction from storm belts, decreasing towards the equator, a regional noise on top.
   - Period of 10 to 16 s, or 150 to 400 m wavelength.
   - It dominates 75 % of time on the globe, more than 85 % outside the wind belts (Semedo 2011). It is mainly generated at high latitudes (Young 2013) and accumulates east of tropical basins (Chen 2002).
   - It weighs little in the slope, therefore in the orbit reflection. She counts closely, in long waves.

**The proposed traffic,** φ in degrees, u to the east, in m/s. Orders of magnitude to be calibrated on ERA5 or QuikSCAT:
- `u = −7 exp(−((|φ| − 15)/9)²) + 11 exp(−((|φ| − 48)/10)²) − 4 exp(−((|φ| − 75)/8)²)`
- a meridian component from 2 to 3 m/s towards the equator in trade winds;
- at the equator and towards 30°, u falls near 0: the pot in black and calms. The layer 2 leaves a weak and variable wind, from 3 to 5 m/s;
- **one wind for the planet:** the sand ridges turn today according to `8.0 * regional.z`. They can follow this same field.

**The laws, all in U** (m/s, at 10 m):
- **Beaufort:** B = (U / 0,836)^(2/3).
- **Significant height:** 0,22 U²/g for a totally risen sea (Pierson-Moskowitz); 5,2·10⁻⁴ U √F limited by the fetch F in m (JONSWAP). We keep the smallest one.
- **Peak wavelength:** 0,83 U² m, i.e. 83 m to 10 m/s and 330 m to 20 m/s.
- **Pentes, Cox-Munk:** σ²_vent = 3,16·10⁻³ U ; σ²_travers = 0,003 + 1,92·10⁻³ U. Film-covered water, sheltered lakes or water table: 0,005 + 0,78·10⁻³ U and 0,003 + 0,84·10⁻³ U.
- **whitecaps:** W = 3,84·10⁻⁶ U^3,41 (Monahan 1980), 1 % to 10 m/s.
  - Published laws differ by a factor 2 to 5. Stramska and Petelski (2003) have a threshold: W = 5,0·10⁻⁵ (U − 4,47)³.
  - Satellite-viewed, the share of whitecaps varies less with latitude: Monahan overestimates it at high latitudes (Salisbury et al. 2013 and 2014).
  - The law is chosen at the benchmark, against the photos.

**What the card gives:**

| Zone | U (m/s) | Beaufort | Hs lifted | whitecaps, Monahan | σ² Cox-Munk |
|---|---|---|---|---|---|
| Pot in black, 0–5° | 3–4 | 2–3 | 0,2–0,35 m, plus swell | 0,03 % | 0,02 |
| Subtropical calm, ~30° | 5 | 3 | 0,6 m | 0,1 % | 0,03 |
| Alizés, 10–25° | 7 | 4 | 1,1 m | 0,3 % | 0,04 |
| Wind from west, 40–60° | 10–13 | 5–6 | 2,2–3,8 m | 1–2,4 % | 0,05–0,07 |
| Storm | 20–25 | 8–10 | 9–14 m | 11–22 % | 0,11–0,13 |
| Lake, fetch 5 km | 5 | 3 | 0,18 m | 0,1 % | 0,03, or less under film |

- **The Beaufort table agrees:** force 4 gives 1 to 2 m, force 6 gives 3 to 4 m, force 10 gives 9 to 12,5 m.

**The fetch, only non-local entry:**
- **Stage 1:** sea totally risen everywhere. The open ocean is just right; the coasts and lakes have too high waves.
- **Next, a local approximation:** the continent field of complexplanet is slow. The distance to the coast, upwind, is about its value divided by its slope in that direction. Limit: an island smaller than this field is not home to anything.
- **Lakes:** the fetch is the size of the lake, given by the hydrology pass.

## 3. Waves at all distances

**The hierarchy of Bruneton (2010), with us:**

| Wavelength of light | Carried by | At our house |
|---|---|---|
| more than 2 grid cells | geometry: the surface of the water displaced | face and rings, already laid at 0 m on the sea |
| more than 2 pixels | normals of pixel | as the fine grid and `DetailSlope`  |
| less than 2 pixels | the roughness of reflection | σ²_reflection = σ²_Cox-Munk(U) − σ²_shown |

- **The wavelength fade is ours:** that of `Fbm3`, between 2 and 4 pixels. The variance shown is calculated as `FbmLostShare`, octave by octave of the spectrum.
- **The total remains constant at any distance:** the reflection keeps its width of orbit at the water level. No flicker, no mutation.
- **The sea already follows “one slope per octave”:** in the tail of the spectrum, each octave carries about the same slope variance, like `OCTAVE_SLOPE` for relief.

**The spectrum:**
- **JONSWAP or TMA, with directional spread** (Horvath 2015), rather than Phillips (Tessendorf 2001). They take the wind, fetch and depth: exactly the outputs of our map.
- **Three bands, like Unity HDRP:** the swell, the sea of wind, the wrinkles.
- **Two spectra superimposed,** sea of wind and swell each with its direction, like WaveWorks 2.

**FFT or Gerstner sum:**
- **FFT (Tessendorf):** 65 000 waves per tile of 256², a cost in log N per point. cascades of 3 or 4 non-multiple sizes against repetition: Atlas has 4 (GDC 2019). Limit: one tile, one spectre, therefore one sea state.
- **Gerstner sum** (Bruneton, Proland, Outerra, Unreal): 30 to 100 waves per pixel, cost in N. Their amplitudes are calculated pixel by pixel from the local wind: the sea state varies naturally. Limit: few waves, repetition visible close up.
- **Recommendation:** the FFT for near field, calculated for wind under the camera. Its amplitude is scaled and turned to the local wind, cell by cell; statistics take over in the distance.
  - **Known limit:** a front that crosses the near field changes the height of the waves, not their shape.
  - **Evolution:** two or three interpolated FFT states, like the Beaufort levels of Assassin's Creed III.

**Place the waves on the sphere, on the grid of the planet:**
- **What doesn't work:** projection of material tiles on the planet axes (`GeneratedTexture`). It stretches the tile up to 1,7 times at the corners of the cube; the spectrum is distorted there.
- **What works:** a reference frame tangent per cell of the grid of the planet, a few kilometers. The tile is turned to the local wind, and the neighboring cells mix.
- **The mixture, constant variance:** weights divided by √Σw² (Heitz and Neyret 2018).
  - For a sea, it is correct: a sea FFT is a Gaussian field.
  - Simple mixing of the current tiles would lose slope and narrow reflection.
  - Cell rotation: Mikkelsen hexagonal paving (2022).
- **The phase of each cell:** calculated in double precision precision on the CPU, never relative to the anchor of 64 m.

**Time:**
- **Dispersion:** ω² = g k tanh(k d).
- **A time in the image constants,** set by an environment variable for benchmarks.
- **Time smoothing:** the reprojection on the surface point remains accurate; the lighting that changes is bounded by the neighbors. To watch at benchmark of jitter.

**Geometry, near:**
- **Vertical and horizontal displacement** (choppy waves) for wavelengths greater than 2 grid cells. A grid cell covers about 13 pixels at any height: the geometry carries what exceeds 26 pixels, the normals the rest.
- **Only the surface of the water moves,** never the complexplanet ground.

**Coast:**
- **Depth d is known to pixel:** the altitude under 0.
- **All deformations are local,** in d and its slope: the waves shorten and slow down (dispersion), dampen (factor TMA), turn towards the coast (refraction).
- **They are flowing when H > 0,78 d** (McCowan criterion). The overflow strip has a width of H / (0,78 × slope): wide on a flat beach, thin at the foot of a cliff. It is a limit on a field: `SpreadStep` on depth.
- **Edge waves aligned with isobaths,** later. Outerra places them by distance to the coast; in our case, the depth divided by the smoothed slope takes its place.
- **Horizon Forbidden West’s breaking reels** are animated at the main: Out of Range.

**What others do:**

| Who | Waves | In the distance | Écume | Published cost |
|---|---|---|---|---|
| Tessendorf 2001 | FFT, Phillips spectrum, horizontal displacement |    | Jacobin |    |
| Bruneton 2010, Proland | sum of trochoids | normal and then BRDF Cox-Munk, filtered sky | Dupuy and Bruneton 2012, Jacobian prefiltered | real time |
| Assassin's Creed III and IV | FFT pre-calculated loop, two sets | grid cell projected, opaque at sea | Beaufort force keys 0–12; pre-calculated coast foam | 200 i/s water only |
| Sea of Thieves | FFT from Tessendorf |    | mask of ridges taken from the displacement |    |
| Atlas, GDC 2019 | FFT in 4 strips, against repetition and lack of detail |    |    |    |
| Unity HDRP | FFT, 3 bands: swell, agitation, wrinkles | grid cell adaptive | simulated according to wind | 4 ms total, PS5 and Xbox Series |
| Unreal Water | Gerstner sums from a spectrum, by octaves |    |    | cheap, depends only on the weather |
| NVIDIA WaveWorks 2 | FFT, two JONSWAP, adjustment by Beaufort scale |    |    | ~1 ms on GTX 680, not verified |
| Crest | cascades camera-centered, 256² | clipmaps |    |    |
| Outerra | Gerstner sum in tile, wind-weighted amplitudes; edge waves by distance to coast |    |    |    |
| Uncharted 3 and 4 | wave particles: local waves, rivers |    |    |    |

- **Star Citizen, Elite Dangerous, Flight Simulator:** no public technical sources found on their oceans.

## 4. The rendering: reflection, sun, color, foam

**The sum:** L = F·L_sky + L_sun + (1 − F)·L_water, the foam replacing its W part of the pixel.
- **Today,** the sea is a diffuse soil: `albedo / PI * (sunLight + skyLight)`. Neither Fresnel, nor reflection.
- **The reflection is calculated with the normal of the water:** the vertical plus the waves, never that of the coast. It is weighted by the pixel's sea share, `sea`.

**Fresnel:**
- **Index water 1,333:** F0 = 0,02.
- **Averaged on slope distribution,** by Bruneton adjustment (2010).
- **At the level of the water, almost everything is reflected:** this is what is most missing in low views.

**The reflection of the sun:**
- **Cox-Munk is an anisotropic Beckmann distribution:** α² = 2σ², aligned with the wind.
- **The formula:** L = E_sun · T_sun · F · p(slope) / (4 μ_view μ_h⁴), with p the Cox-Munk Gaussian and μ_h the cosinus of the facet.
- **Smith masking at sharp angles:** without it, the reflection is too strong towards the horizon. Near the horizon, Cox-Munk and a real surface FFT differ by a few tens of percent (Mobley).
- **Order of magnitude:** a reflectance of 0,13 at the center of the reflection, sun at zenith and 7 m/s. Bréon and Henriot (2006) measure 0,2 as a typical value.
- **Nothing to add for the atmosphere:** the sun already passes through `SunTransmittance` and blushes at sunset; the path to the eye passes through the atmosphere pass.
- **Anti-clinching comes from the variance:** shown more lost, it remains constant. For the normals shown, add their variance in the pixel (LEAN mapping; Tokuyoshi and Kaplanyan 2019 and 2021).

**Reflection of the sky:**
- **The atmosphere is spherical in symmetry:** the sky seen from sea level depends only on three angles. It is the same everywhere on the planet.
- **Step 1, without adding anything:** `IntegrateScattering` since h = 0, along the reflected direction, in 6 to 8 not, on the only pixels of sea. The atmosphere pass already makes it 12 on every pixel.
- **If it is too expensive:** a table with three dimensions, angles of view, from the sun and between them, at sea level, calculated at startup as the three existing tables. Bruneton (2017) adds altitude in fourth dimension, useful for mountain lakes.
- **Turbulent sea:** the sky is smooth; the average direction and the average Fresnel are sufficient first. Bruneton filters a map of the sky by the slope ellipse.
- **The reflected relief,** a mountain in a calm lake: reflections in screen space, retreat to the sky. With the lakes.

**The color under the surface:**
- **Physics:** reflectance R∞ ≈ 0,33 b_b/a, b_b the backscattering, has absorption (Gordon, Morel). Pure water absorbs red, ~0,34 m⁻¹ to 650 nm, and almost no blue, ~0,009 m⁻¹ to 450 nm (Pope and Fry 1997).
- **The current blue of the deep sea is of good order:** 0,033 in linear, against a reflectance of about 0,03 in blue for a clear ocean.
- **The gradient on 3 000 m depth is false:**
  - beyond a few tens of meters, the color no longer depends on depth;
  - continental shelf appears greener because of sediment and plankton, not because of depth.
- **Instead, two parameters:** turbidity and plankton, by a water type field. Stronger near coasts and mouths, on plateaus, and in cold rising waters, depending on temperature.
- **The visible background,** Maritorena, Morel and Gentili (1994): R = R∞ + (A − R∞) e^(−2Kd), At the albedo of the background, that of the beach sand. It is the turquoise of the lagoons.
- **The average on the pixel is accurate:** for standard deviation depths σ_d around d, the average of e^(−2Kd) is e^(−2Kd + 2K²σ_d²). Valid from orbit, the benchmarks of the Bahamas, to the edge.
- **Close up:** the texture of the bottom seen through the water, shifted by refraction. A parallax in pixels, allowed by `principes.md`.

**The foam:**
- **The whitecaps from far:** the W(U) part of the pixel.
- **The whitecaps close up:** where the Jacobian of the displacement J passes below a threshold J0 (Tessendorf). They persist by accumulation and slow disappearance, as in Atlas, HDRP and Crest.
- **The connection, Dupuy and Bruneton (2012):** the share of J < J0 in the pixel is derived from the mean and variance of J, read in the mips. It's a `SpreadStep` on J. J0 is set so that the far part equals W(U): the same coverage at any distance.
- **Albedo:** 0,22 on average (Koepke 1984), × (0,89; 1; 1) in red, green, blue (Frouin 1996). Diffuse. Fresh foam is lighter, old foam is duller: 0,22 is their average.
- **From force 7:** foam trails in the direction of the wind.
- **The edge foam:** where H > 0,78 d, in part of the pixel. The wet sand, darker, on the strip that the waves reach.

## 5. Lakes

**Today:**
- **No lake.** Any point below 0 is sea, even in the heart of a continent.
- **The cuvettes above 0 remain dry.**

**What the procedural worlds do:**
1. **Fill the bowls, then a water balance.** Priority-Flood (Barnes 2014) fill costs n log n. Rain on the basin, against evaporation on the lake, decides:
   - a lake full to its threshold;
   - a partially enclosed lake, such as the Dead Sea;
   - a dry basin, salar or playa.
2. **Generate relief from hydrology** (Genevaux 2013): the relief follows the rivers. Excluded from us: it is a replacement for complexplanet.
3. **A local groundwater:** level = smoothed relief less a depth related to moisture. Local, but false on slopes: the surface of water slopes with smooth relief.
4. **Digging a pond and laying flat water:** a geometry replacement.

**Why it is more than just rendering:** a lake has a flat surface. Its level depends on the lowest threshold of its entire basin, sometimes tens of kilometers away. No pixel can calculate it alone.

**Proposal, to be decided:**
- **A water level map, global:**
  - complexplanet sampled on a fixed cube of the planet, 2 048² per face, of grid cells of about 3 km;
  - Priority filling;
  - the water balance derived from our humidity and temperature;
  - at startup or cached. Order of magnitude: 25 million points at ~340 ratings, to be measured; the mesh makes 220 million per frame.
- **The rendering:** water where the altitude is below the level of its lake, in its basin. The same water pattern as the sea.
- **Lakes smaller than the map:** a statistical lake part from far, the lake taiga, then a local fill around the camera. Same rule as the whitecaps.
- **The cuvettes under 0, in the lands:** meanwhile, they remain water at the level 0. It is a plausible full lake in humid climate; in arid climate, a salt bottom would be more correct. To distinguish them from the sea requires knowing if they touch it: the same pass.
- **Rivers:** complexplanet is already digging valleys, up to ~190 m (`RIVER_DEPTH`). Putting water there raises the same question of level, to be studied with lakes.

**The rendering of a lake, with the same model:**
- **Fetch short:** weak waves. 5 m/s on 5 km give 0,18 m.
- **Frequent film:** Cox-Munk variances of covered water, a sharper reflection.
- **Colour:** on 85 000 lakes, 31 % are blue and 69 % green to brown (Yang 2022). Blue is deep and cold; green and brown are shallow and warm. So a color drawn from depth and temperature, calibrated on the Forel-Ule scale, 21 shades.
- **The sharp reflections of the relief:** reflections in screen space.

## 6. Costs

| Brique | Cost | Source |
|---|---|---|
| Sea statistics, step 1 | less than 0,1 to 0,3 ms in 1440p | estimate: a dozen operations and 6 to 8 no sky per pixel of sea |
| Table of the sky at sea level | at startup, then one read per pixel | as existing tables |
| FFT, 3 cascades of 256², heights | 0,38 ms on RTX 2070 Super | Algis et al. 2025 |
| FFT, 3 cascades of 256, not optimized | 1,65 ms on RTX 4070 | 80.lv |
| WaveWorks 2 | ~1 ms on GTX 680 | forum citing the doc, not verified |
| All water HDRP, simulation and rendering | 4 ms on PS5 and Xbox Series, 7 ms the previous generation | Unity |
| Normals of waves to pixel | 0,3 to 0,6 ms in 1440p, sea full screen | estimation: 4 cascades × 3 copies = 12 readings |
| Reflections in screen space | 0,5 to 1,5 ms in 1440p | ordinary order of magnitude, to be measured |
| Map of Lakes | once, a few seconds | Estimated |

- **Realistic for a first step:** the step 1, less than 0,3 ms.
- **Full waves,** step 3: 0,5 to 1,5 ms in total, depending on the part of sea on the screen.
- **Rendering costs more than simulation:** Unity says for HDRP, the G-buffer pass dominates.

## 7. Measuring against the real

**1. The benchmark of the reflection,** became `tools/banc_mer.py`, mode `reflet`:
- an orbit view where the sun is reflected;
- a diagnostic view `glint`, reflectance πL/(E μ_sun) without atmosphere;
- **criterion:** the profile at 5 % of the Cox-Munk calculation, done in Python for the wind of the place;
- the order of magnitude against POLDER (Bréon and Henriot 2006), the velocity against the MODIS images of NASA Earth Observatory.

**2. The benchmark of descent, new views:**
- **`foam`,** the share of whitecaps: a flat curve from 1 500 km to 10 m, equal to W(U) of the place;
- **the reflection:** its width does not change in descent, the total variance is constant.

**3. The benchmark visual, sea sites by state:**
- a calm place, a moderate, a storm, from 10 m to 10 km;
- next to the photos of each Beaufort force: the booklet NOAA of the ship observers, public domain;
- **measurements:** the threshold part of whitecaps on the photo and on the rendering; the spectrum of luminance of `realisme.py`, at the same scale.

**4. The colors of orbit:**
- deep ocean, a plateau, a lagoon, against Blue Marble or Sentinel-2: Bahamas, Red Sea, open Pacific;
- at the same angle of sun.

**5. Laws, without GPU:**
- a small script checks Hs(U), W(U), σ²(U), λ_pic(U) against the Beaufort table and the laws cited;
- on tile FFT: measured Hs equal to law, slope variance equal to Cox-Munk.

**6. Existing benchmarks:**
- **quality:** unchanged earth, no p95 degraded more than 10 %;
- **cost:** time GPU at usual heights;
- **jitter:** the reflection does not sparkle in flight.

## 8. Current status: spike FFT (2026-10-26)

**Near core replaced by the sea FFT,** validated in flight to `jalon/22-mer-fft`, integrated to `jalon/23-mer-fft-main`. Displacements, derivatives, normals, moments and persistent foam come from the same cascades FFT.

**Current specification:** [spec-mer-fft-spike.md](spec-mer-fft-spike.md).

**Old kernel:** retained in [the history](log/recherche-mer-historique.md), and in the `piste/mer-animee` tag.

## 9. Sources

**The far and the reflection:**
- Bruneton, Neyret, Holzschuch, Real-time Realistic Ocean Lighting using Seamless Transitions from Geometry to BRDF*, CGF 2010 : [HAL](https://inria.hal.science/inria-00443630), [Eurographics](https://diglib.eg.org/items/fb727c69-2be2-4edd-833e-f7a9baea9b63), [presentation](https://cgg.mff.cuni.cz/~jaroslav/teaching/2012-npgr031/prezentace/Realtime%20Realistic%20Ocean%20Lighting.pdf)
- Dupuy, Bruneton, *Real-time Animation and Rendering of Ocean Whitecaps*, SIGGRAPH Asia 2012 : [PDF](https://liris.cnrs.fr/Documents/Liris-5812.pdf)
- Bruneton, *Precomputed Atmospheric Scattering: a New Implementation*, 2017 : [site](https://ebruneton.github.io/precomputed_atmospheric_scattering/)
- Hillaire, *A Scalable and Production Ready Sky and Atmosphere Rendering Technique*, EGSR 2020 : [PDF](https://sebh.github.io/publications/egsr2020.pdf)
- Olano, Baker, *LEAN Mapping*, I3D 2010 : [page](https://www.csee.umbc.edu/~olano/papers/lean/)
- Tokuyoshi, Kaplanyan, *Stable Geometric Specular Antialiasing with Projected-Space NDF Filtering*, JCGT 2021, continue of their article of I3D 2019: [PDF](https://www.jcgt.org/published/0010/02/02/paper-lowres.pdf)
- Heitz, Neyret, *High-Performance By-Example Noise using a Histogram-Preserving Blending Operator*, HPG 2018 : [page](https://eheitzresearch.wordpress.com/722-2/)
- Mikkelsen, *Practical Real-Time Hex-Tiling*, JCGT 2022 : [PDF](https://jcgt.org/published/0011/03/05/paper.pdf)

**Waves:**
- Tessendorf, *Simulating Ocean Water*, 2001 : [PDF](https://jtessen.people.clemson.edu/reports/papers_files/simdoc.pdf)
- Horvath, *Empirical Directional Wave Spectra for Computer Graphics*, DigiPro 2015 : [DOI](https://doi.org/10.1145/2791261.2791267)
- Stewart, *Ocean-Wave Spectra*: Pierson-Moskowitz, JONSWAP and their laws in U and F: [LibreTexts](https://geo.libretexts.org/Bookshelves/Oceanography/Introduction_to_Physical_Oceanography_(Stewart)/16:_Ocean_Waves/16.4:_Ocean-Wave_Spectra)
- Jeschke, Wojtan, *Water Wave Packets*, SIGGRAPH 2017 : [page](https://visualcomputing.ist.ac.at/publications/2017/WWP)
- Algis et al., Arc Blanc: a real time ocean simulation framework, JCGT 2025 : [arXiv](https://arxiv.org/abs/2503.03326)

**Productions:**
- Mihelich, Tcheblokov, *Wakes, Explosions and Lighting: Interactive Water Simulation in Atlas*, GDC 2019 : [PDF](https://gpuopen.com/gdc-presentations/2019/gdc-2019-agtd6-interactive-water-simulation-in-atlas.pdf)
- Ang et al., *The Technical Art of Sea of Thieves*, SIGGRAPH 2018 : [PDF](https://history.siggraph.org/wp-content/uploads/2022/09/2018-Talks-Ang_The-Technical-Art-of-Sea-of-Thieves.pdf)
- Assassin's Creed III, the ocean and the Beaufort scale: [fxguide](https://www.fxguide.com/?p=38193); Black Flag: [PlayStation Blog](https://blog.playstation.com/archive/2013/09/12/why-assassins-creed-iv-black-flag-on-ps4-is-a-truly-next-gen-experience)
- Malan, *Rendering Water in Horizon Forbidden West*, SIGGRAPH 2022 : [PDF](https://advances.realtimerendering.com/s2022/SIGGRAPH2022-Advances-Water-Malan.pdf)
- Unity HDRP Water : [blog](https://unity.com/blog/engine-platform/new-hdrp-water-system-in-2022-lts-and-2023-1)
- Unreal Water, Gerstner Waves by spectrum: [API](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/Water/UGerstnerWaterWaveGeneratorSpect-)
- NVIDIA WaveWorks : [page](https://developer.nvidia.com/waveworks)
- Crest: [documentation](https://crest.readthedocs.io/en/stable/about/introduction.html), [SIGGRAPH Advances](https://advances.realtimerendering.com/)
- Outerra, *Ocean Rendering*: [blog](https://gamedev.net/blogs/entry/2249487-ocean-rendering)
- FFT in Unity, 3 cascades from 256: [80.lv](https://80.lv/articles/real-time-physically-accurate-ocean-surface-simulation-in-unity/)

**Measures of reality:**
- Cox, Munk, *Measurement of the Roughness of the Sea Surface from Photographs of the Sun's Glitter*, JOSA 1954: [PDF](https://data-ww3.ifremer.fr/BIB/Cox_Munk_JOSA1954.pdf); abstract: [Ocean Optics Web Book](https://oceanopticsbook.info/view/surfaces/cox-munk-sea-surface-slope-statistics)
- Bréon, Henriot, *Spaceborne observations of ocean glint reflectance and modeling of wave slope distributions*, JGR 2006 : [PDF](https://data-ww3.ifremer.fr/BIB/Breon_Henriot_JGR2006.pdf)
- Monahan, O'Muircheartaigh, *Optimal power-law description of oceanic whitecap coverage dependence on wind speed*, JPO 1980 : [notice](https://researchrepository.universityofgalway.ie/entities/publication/955c2fc7-e4f6-4a44-ab15-7e7073732378)
- Salisbury, Anguelova, Brooks, *On the variability of whitecap fraction using satellite-based observations*, JGR 2013 : [notice](https://eprints.whiterose.ac.uk/77830)
- whitecaps in atmospheric correction: Stramska and Petelski 2003, Koepke 1984, Frouin 1996: [Ocean Optics Web Book](https://oceanopticsbook.info/view/atmospheric-correction/level-2/whitecaps)
- Maritorena, Morel, Gentili, *Diffuse reflectance of oceanic shallow waters*, L&O 1994 : [HAL](https://hal-lirmm.ccsd.cnrs.fr/LOV_OMTAB/hal-03284969v1)
- Pure water absorption, Pope and Fry 1997: [OMLC](https://omlc.org/spectra/water/abs/index.html)
- Beaufort scale, wave speeds and heights: [Wikipedia](https://en.wikipedia.org/wiki/Beaufort_scale)
- Sea conditions photos by Beaufort force, NOAA: [booklet](https://repository.library.noaa.gov/view/noaa/56110/noaa_56110_DS1.pdf)
- Reflection of the sun seen from orbit: [NASA, The Science of Sunglint](https://earthobservatory.nasa.gov/images/84333/the-science-of-sunglint), [Sea of Arabia](https://earthobservatory.nasa.gov/images/90132/sunglint-on-the-arabian-sea)
- Surf Climate: Young 1999: [PDF](https://data-ww3.ifremer.fr/BIB/Young_IJC1999.pdf); Chen et al. 2002, swell reservoirs: [PDF](https://data-ww3.ifremer.fr/BIB/Chen_etal_JTECH2002.pdf); Semedo et al. 2011 : [PDF](https://data-ww3.ifremer.fr/BIB/Semedo_etal_JC2011.pdf)
- Surface winds, QuikSCAT climatology: [NOAA NCEI](https://www.ncei.noaa.gov/archive/accession/0177404)

**Lakes:**
- Barnes, Lehman, Mulla, *Priority-Flood*, Computers & Geosciences 2014 : [arXiv](https://arxiv.org/abs/1511.04463)
- Génevaux et al., *Terrain Generation Using Procedural Models Based on Hydrology*, SIGGRAPH 2013: [PDF](https://www.cs.purdue.edu/homes/bbenes/papers/Genevaux13ToG.pdf)
- Yang et al., *The Color of Earth's Lakes*, GRL 2022 : [notice](https://doaj.org/article/c8d49c4c3ddf4418a449a17586e25ad6)
- Wang et al., Forel-Ule Index of Inland Waters, 2000–2018: [Scientific Data](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7835379/)
