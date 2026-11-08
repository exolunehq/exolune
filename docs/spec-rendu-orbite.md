# The planet seen from orbit

**Distant-surface continuity, 2026-11-08**
- The distant representation and detailed terrain blend colour only; HDR alpha remains a physical surface distance, independent of the blend weight.
- The proxy samples filtered relief from the existing terrain map, with ocean at sea level.
- Its expanded transition envelope supplies raster coverage only; it neither clips clouds nor overwrites the detailed depth buffer.
- Cloud layers, atmosphere and their sampling settings remain unchanged.
- Review: `tools/tests/2026-11-08-transition-nuages.txt`; eight fixed-light approach views from 40,000 km to 500 km.
- Release x64 and five background views at 20,000, 10,000, 7,000, 4,000 and 2,000 km pass visual continuity review; continuous flight remains for the user.
- The replaced depth blend and enlarged occluder are recorded in [history](log/spec-rendu-orbite-historique.md).

**The goal:** that the planet seen from orbit supports the comparison with the Earth of Apollo 17, "Blue Marble": a dark blue ocean, ochre deserts, white and opaque clouds with smooth hearts, a thin blue limb. Without degrading anything at 10 km, at 1 km or on the ground.

**State, 2026-10-31:** made on the experiment `piste/orbite-rendu`, branch `claude/orbite-rendu-0e3f4e`; to be judged in flight, `tools/tests/2026-10-31-orbite-rendu.txt`. **2026-11-02:** the clouds' multiple scattering per point, for contrast and against shiny contours; to be judged in flight, `tools/tests/2026-11-02-nuages-contraste.txt`.

- **The code:** `Atmosphere.hlsli`, `AtmosphereMultiScattering.hlsl`, `Clouds.hlsli`, `CloudsTemporal.hlsli`, `ToneMap.hlsl`, `PlanetSettings.hlsli`, `D3DApp.cpp` (the standard deviations of noise functions and the profiles' means over a height span, at loading), `ShipWeather.hlsl`.
- **References and timing:** `tools/calage_orbite.py`, Monte Carlo of the air seen of orbit and cloud layers; `tools/nuages_statistique.py`, the control of pixel laws.
- **The detail of clouds:** `spec-nuages.md`, light, walk and statistics to pixel.

## The finding

**Measured at 10 000 km, sun in the back, against Blue Marble** (sRGB medians; clear ocean, opaque clouds, rim ring):

|  | Before | After | Apollo 17 |
|---|---|---|---|
| Ocean | 102, 129, 177 | 56, 75, 111 | 45, 67, 100 |
| Thick clouds | 189, 186, 195 | 208, 202, 204 | 220 to 233, neutral |
| Language | 149, 165, 209 | 109, 123, 162 | 99, 133, 171 |

- **Three deviations reported:** clouds dull, gray pink and translucent; a grain of sand on the distant clouds; a lavender veil over the whole planet, the lower limb that roses.

**The equivalent reflectance,** `π L / E_soleil` before the curve, orbit, single pass; the median of the clear ocean and opaque clouds, in the center of the disk:

|  | Ocean | Thick cloud | Contrast |
|---|---|---|---|
| Before, sun in the back | 0,090 | 0,237 | 2,6 |
| After, sun in the back | 0,061 | 0,645 | 10,5 |
| Before, sun at 60° | 0,069 | 0,125 | 1,8 |
| After, sun at 60° | 0,046 | 0,302 | 6,6 |
| Earth, CERES | 0,08 to 0,1 | 0,5 to 0,8 | 6 to 8 |

- **The thick cloud is in the target.**
- **The ocean is darker than the average of CERES:** under a sun almost at the zenith, without reflection, the Monte-Carlo of our air gives the same 0,06; CERES averages all the angles of the sun and reflection. Hence a contrast of 10 at the zenith, of 6,6 at the oblique sun.

## Causes, established by elimination

**The lavender veil comes from the air, not from the clouds.** Cloudless, the ocean remained lavender. Variants of composition, in the same place: airless, aerosol-free, multiple scattering-free, ozone-free, exposure to 0 EV.
- **The multiple scattering of the air equaled the simple:** 0,7 to 1,0 times, against 0,15 to 0,37 in Monte-Carlo of the same atmosphere (`calage_orbite.py air`).
- **For a Rayleigh air alone, the engine followed the Monte-Carlo:** 0,31 against 0,26 in blue. The excess came from aerosols: Hillaire's table 2020 assumes an isotropic phase, while they diffuse forward, g = 0,7. Seen from orbit, they reflected three to five times too much light upwards.
- **A gray 0,3 ground under the air,** including the ocean, made a quarter of the excess.
- **A fault:** in the table, a Boolean `ground` masked the floor of the slice; the fog of the descending rays was set at 1 km.
- **The exposure** of +1 EV, set on landscapes, added one EV too much for a photo of the Earth.

**Dull clouds.**
- **Their reflectance was capped towards 0,25,** even infinitely thick: single scattering and a second order approached, against 0,86 to 0,99 in Monte-Carlo.
- **Their phase was too backward:** 20 % of a lobe g = −0,5. A cloud of optical thickness 1 came out at 0,15 instead of 0,02: thin clouds and edges also made a milky veil.
- **Their water followed the cover of the sky:** density was multiplied by the cover, and a cumulus field at 10 % was ten times more transparent than a front.

**The grain.**
- **Optically thick steps:** orbit, steps of 240 m in a cloud of 24 /km, six optical thicknesses. The light of a thick cloud varied from 0,18 to 0,64 depending on where its summit fell into the step.
- **The distant quadrature:** 4 to 8 point rays, at the mip 0, for a pixel of 10 km on cumulus of 1 to 4 km. The standard deviation was the mean.

## Corrections

### The air

- **Van de Hulst similarity:** the multiple scattering of an anisotropic medium is treated as isotropic with reduced diffusion, `σs (1 − g)`. Aerosols enter for `Mie × (1 − 0,7)`, in the table and in the multiple source of `IntegrateScattering`. The single scattering does not change. The orbit ocean joins the Monte-Carlo: 0,071, 0,125, 0,283 exposed, against 0,067, 0,123, 0,279.
- **Soil under air,** in table only: `AIR_GROUND_ALBEDO` = 0,12, clear sky average albedo, 70 % of ocean to 0,06 and land to 0,25. `GROUND_ALBEDO` guards 0,3 for objects and plants.
- **The Boolean** is called `hitsGround` and no longer masks the floor of the slice.

### The light of the clouds

- **Drop phase:** Henyey-Greenstein, g = 0,85 (Bohren and Huffman).
- **Water in the cloud no longer depends on cover:** the final density is divided by the cover R. The shape, support and erosion remain. R no longer says the part of the sky covered; water follows the thickness of the map, from 20 to 80 /km (lower, seen from low orbit).
- **The multiple scattering, capped on Monte-Carlo:** an isotropic source per km at each point, `σ W (S_soleil μ + E_ciel) F e^(−λ L) / (1 + b τs) / 4π`, summed along the view.
  - W = 3,40, b = 0,040, k = 0,061, adjusted on layers of g = 0,85, thicknesses 2 to 100, sun at zenith and at 60°, top and bottom views; error 0,30 in log.
  - **The decay towards the sun is that of diffuse transmission of a layer,** `1 / (1 + b τs)` (two streams): steep near a lighted face, slow at the bottom. An exponential adjusted on the same layers, error 0,31, left the shadow face of a tower at 57 % of its illuminated face, instead of 38 %.
  - **μ, the incidence of the sun on the cloud:** a sheet receives it as a ground, `dot(haut, soleil)`; a cumulus as a ball, 0,5 on average on its illuminated face: `max(dot, 0,5 × famille, 0,05)`.
  - **F = 1 − exp(−k τ), the build-up:** τ the cloud's chord along the sun through the point, six samples toward the sun and three away from it, in density in the cloud without the covered part. For a flat layer, τ / μ: the size of the calibration. Since 2026-11-02; before, on the column at the pixel's seen point (below).
  - **The side leak, `L`:** a finite cloud loses through its sides the light it scatters, `80 Σ w (1 − f) f ρ Δs` on the samples toward the sun, λ = 0,20 on Monte Carlo spheres; zero in a slab (below).
  - **The sky enters it with the sun:** a cloud diffuses everything it receives. Without him, the clouds would come out creamy.
- **Six samples towards the sun,** from 0,125 to 4 km, or 7,875 km: all the lower layer. With four, the base of a thick cloud received the light of a thin cloud.
- **An illuminated step does not exceed an optical thickness of 1** as long as the column is transparent.

### The pixel: statistics instead of fine rays

- **The joined law of shape and erosion:** X the shape, D the erosion, under the pixel footprint, Gaussian mean read at the mip of the pixel and standard deviation calculated at loading (channel B of the two volumes). The margin `U = clamp(X − (1 − c), 0, c) p − D g` gives the covered part `f = Φ(mU / sU)` and the density in the cloud `E[U⁺] / f / (1 − g μD) / c`.
  - **Measured on textures:** at c = 0,2, f = 0,724 and an average density of 0,178, for true 0,727 and 0,183.
  - **Scales thinner than texels** add their variance at any distance: 0,0124 for shape, 0,033 for erosion. An edge becomes a partial fringe, like a turbulent edge seen at the pixel.
  - **Taken at its average, erosion erased any thin cloud in the distance:** of orbit, the share of partial pixels fell from 16 % to 2 %.
- **Maximum overlap on a footprint, random beyond:** In the pixel, clouds of a layer overlap, the cloudy column is the widest encountered; when the ray has left the footprint, a new column is composed to the previous one as a layer.
- **The distant quadrature is removed,** and the average of the distant radii of the time pass with it.
- **The weather map is read at the mip 0, 39 km, in cubic B-spline:** threshold by a steep function, its bilinear interpolation drew squares and diamonds from 80 to 160 km; at the mip 0, the climate map draws its shapes up to 80 km.

### The exhibition

- **Orbital terminator, 2026-11-07:** direct sunlight is metered at the observer above the air, using its altitude-dependent planetary horizon. A dark ground reference cannot trigger night exposure while the observer remains in sunlight (`recherche-tons-exposition.md`).
- **0 EV in orbit, +1 EV on the ground:** landscape photos are exposed for the ground, those of the Earth for its clouds. Measured on "Blue Marble", its sea and clouds match ours at 0 EV.
- **Between the two, the air under the camera,** `1 − exp(−h / 8 km)`: +0,88 EV to 1 km, +0,29 to 10 km. The exposure remains an incident exposure meter, without reading the image.

## The cost of GPU

**Measured at the same place, before and after, in 1920 × 1080, the launcher's only exe** (columns `nuages_trace` and `atmosphere`, ms; other engines were running on the GPU):

| View | Front track | Trace after | Clouds and air front | Clouds and air after |
|---|---|---|---|---|
| Orbite, sun in the back | 0,92 | 1,44 | 1,58 | 2,09 |
| Orbite, terminateur | 1,34 | 1,80 | 1,98 | 2,44 |
| 10 km, cumulus on the chain | 6,17 | 7,90 | 7,78 | 9,48 |
| 10 km, layer on the sea | 4,88 | 7,73 | 6,41 | 9,21 |
| 1 km, forest under the clouds | 4,55 | 5,33 | 6,02 | 6,80 |
| 1 km, under the layer | 1,81 | 1,83 | 3,22 | 3,24 |
| Ground, equatorial plain | 1,49 | 1,14 | 2,93 | 2,58 |
| At the sea level | 2,73 | 1,75 | 4,14 | 3,15 |

- **At 10 km, +1,7 to +2,8 ms:** the entire image changes from 15,2 to 16,9 ms above the cumulus, below the 60 images per second. Six samples towards the sun instead of four and an optical step of 2 instead of 1 weigh only 0,1 to 0,2 ms: the rest is the statistic, calculated at each sample, and denser clouds, therefore more illuminated steps.
- **From orbit, +0,5 ms; at ground and sea level, 0,2 to 1 ms less:** one single ray per pixel instead of the distant quadrature.

## Above and below layers

**The criterion:** whiten clouds without burning the contrast above or below a layer. Six views, at noon and low sun, at 12°, before and after, in single pass (board).
- **Above, at noon:** white, uncut tops, 0,96 exposed to 90e percentile, 226 in sRGB; their internal shadows, ratio of 10e and 90e percentiles of luminance, 0,65 against 0,76 before: more marked.
- **Above, in low sunlight:** 0,68 vs 0,57 before: less marked. A cumulus receives the sun on average, μ = 0,5, and not according to the incidence of each face.
- **Below:** lighter bases than before, gray at low sun, cream at noon.
- **No local exposure:** correct reflectances and curve are sufficient; to be considered only if relief is still missing above a layer.
- **Nothing in the history keeps track of a bleaching that burned the contrast:** the journal measures the contrast of 2,5; the old volume had first gray peaks, two reversed flows (`log/recherche-nuages-historique.md`).

**The close-up correction of 2026-10-31,** F on the column at the seen point: replaced on 2026-11-02 (below), its account in `log/spec-nuages-historique.md`.

## Low orbit view, 750 km: flat sheets and regular seeding, corrected on the same day

**The defect, in flight:** uniform white sheets, without texture, with clear edges; between them, a regular seeding of small cumulus of the same size, everywhere.

**The causes, by elimination,** at 750 km, on two places and three suns:
- **The layers had water from a front heart,** 80 /km: τ ≈ 60 for 1 km, where reflectance saturates. With a quarter of this water, they take on a cellular texture.
- **An octave was missing between 10 and 150 km:** the erosion of 4 km placed only the scattered cumulus. The form reread at 128 km groups them in clusters and alleys and shreds the edges of the layers.
- **Not the card with the mip 0 nor the fine variance.** The same family as plastic seen close up: clouds become physically dense show the shortcomings of the noise. The too high coverage of the map, it is taken up by the climate session.

**Corrections:** water in the cloud follows the thickness that the map bears, `0,25 + 0,75 e`, from 20 to 80 /km, convention shared with climate; the octave of the form at 128 km (`spec-nuages.md`).

**The result:** textured sheets with frayed edges, cumulus in clusters and alleys, thick fronts still white; orbit, thick cloud at 0,674, contrast 8,1 to the oblique sun; close up, more translucent and softer cumulus, closer to before the experiment.

**Cost, measured by pairs:** +0,3 to +0,9 ms to 10 km, +0,4 to +0,5 to 1 km, +1,7 ms to ground under convection: less dense cumulus requires more steps before being opaque.

## Contrast and shiny contours, corrected on 2026-11-02

**The defect, in flight:** since the whitening, flat clouds, without relief; strange bright outlines on their lobes, like specular highlights.

**The causes, by elimination,** from 1,5 km to orbit, sun at 60° and at 10°, against the build before the experiment (`e738b9d`, in another `x64` folder):
- **F, the build-up, was a quantity of the pixel:** taken once per segment, at its seen point, on the vertical column. Where the seen point jumped between two lobes, F jumped: bright rims along the lobes, dark winding channels in a layer. With F = 1, both disappear.
- **Under them, the multiple scattering was nearly uniform:** F = 1 left a flat white sheet. Its source, fitted on slabs, falls slowly toward the sun and loses nothing through a finite cloud's sides: on a Monte Carlo sphere, 1,4 to 2,0 between lit and shaded halves, against 2,5 to 9,7.
- **The side leak, taken against the view's column,** `f / f_colonne`, drew bright veins inside the cumulus at low sun: the column's covered part is also a pixel's quantity.

**The correction, one rule:** what builds up or drains the light a point scatters is read in the cloud around it, never in the pixel (`principes.md`).
- **F per point,** on the cloud's chord along the sun through it: the six samples toward the sun and three away from it, 500 m to 2 km, in density in the cloud, whole from 2 % covered. For a slab, τ / μ: the calibration does not move. Over 1,75 km away from the sun, thick clouds greyed from orbit, 179 against 199 in sRGB; in mean density, a cumulus turned grey.
- **The side leak,** `CLOUD_MULTI_LEAK` = 0,20, on each sample's own covered part; zero in a slab. Refitted with F per point: λ = 0,20 stays the best relief, error 0,38; sphere 1,9, 3,2 and 8,5 against 2,5, 5,0 and 9,7 (`tools/calage_orbite.py relief`).
- **Removed:** the seen point, the twelve slices of its column, the mean μ of the segment.

**The result, 1280 × 720, game passes:** in opaque clouds, ratio of the 10th and 90th percentiles of luminance; lower is more relief.

| View | Before | After |
|---|---|---|
| 10 km over the range, sun at 10° | 0,70 | 0,60 |
| 3 km, cumulus, sun at 60° | 0,78 | 0,61 |
| 3 km, sun at 10° in front | 0,78 | 0,61 |
| 3 km, sun at 10° on the side | 0,74 | 0,51 |
| 3 km, sun at 10° behind | 0,86 | 0,70 |
| 2 km, sun at 10° on the side | 0,63 | 0,50 |

- **The white is kept where it was calibrated:** median of opaque clouds, 196 against 199 in sRGB from orbit and at 750 km under a high sun; 90th percentile unchanged.
- **Near cumulus are greyer:** median 157 against 190 at 3 km under a high sun. A thin chord builds up less light, as the slabs say; the old F was nearly 1 everywhere but on its lines.
- **No rim, vein, channel or plane** in the 18 views and the two poses of the planes.

**Planes at fixed heights, seen in flight and corrected the same day:** at 3,7 km, a nearly level view, a grey horizontal band across the clouds, still while they drifted.
- **The cause, by elimination:** F per point, not the leak. The chord's long intervals read the profile at their middle: as it crossed the cumulus' flat base, 2 km of chord lit or went out, a plane at a fixed height. The same plane came from the density in the cloud, finite up to its 1e-4 floor of cover.
- **The correction:** each light interval reads its profile's mean over its height span, the slices of the profile volume computed at loading (`spec-nuages.md`); the chord counts an interval whole from 2 % covered, by its share below, `CLOUD_CHORD_COVER` (a calibrated setting; at 10 %, cumulus greyed, 136 instead of 145).
- **Measured on the row means of the vertical gradient,** the step of the line: 0,53 before, 0,32 with the mean profile alone, 0,15 with both, the level of the cloud's own detail.

**Cost, game passes, 1920 × 1080, two measures each, against main:** still, 2,0 → 2,1 ms from orbit, 4,3 → 5,0 at 40 km, 10,2 → 10,9 at 10 km, 9,8 → 11,0 at 8 km, 4,9 → 5,3 at 3,7 km, 7,8 → 8,2 at 2 km; in fast flight, everything traced again, 22,7 → 24,4 at 40 km, 26,9 → 30,5 at 8 km, 14,8 → 15,6 at 3,7 km, 17,6 → 18,8 at 2 km. From +5 to +15 %: three samples more per lit step, the column removed; no optimization removed.
- **Cheaper variants tried, without gain:** skipping the three samples where a bound proves them invisible, the image identical to the level, is slower, its branch breaks the overlap of the nine fetches; two samples instead of three save 0,1 to 0,2 ms, under the noise of the measure.
- **The lever left:** transmittances to the sun precomputed in a volume (`spec-nuages.md`, next steps).

**What remains:** the lit face of a finite cloud is still darker than the Monte Carlo, 0,37 against 0,50: its source takes a mean incidence, 0,5 for a cumulus, not that of each face. Experiment: the local incidence, by the gradient of the density smoothed at the diffusion scale.

## The limits

- **One octave missing between 32 and 160 km:** between the tile of the noise shape and two texels of the weather map. From orbit, the partial fields are fair on average but blurred, in spots; the grain of front gave the illusion of a detail. To be seen with the weather map (`spec-climat.md`).
- **The bottom of a layer is lighter than before:** 0,45 in reflectance factor, which transmits a layer thickness 10 to 20, against 0,11 to 0,24. It remains a little warm, R/B = 1,18: sunlight at 2 km, without white balance.
- **The limb** keeps a band a little more red than Apollo, R/B 0,67 against 0,58; a mist twice as clear does not change it.
- **The multiple scattering of the clouds is an adjustment,** of error 0,3 in log: thin clouds at low sun come out a little too clear.
- **The lit face of a finite cloud is darker than the Monte Carlo,** 0,37 against 0,50: its multiple source takes a mean incidence. Experiment: the local incidence, by the density gradient, for the lit face and the shaded face.
- **A NaN,** on 163 pixels of two million on the ground in single pass, which instrumentation makes disappear: the light of clouds is limited to 0 before the historical, which spread it in black blocks.
- **Maximum cover** assumes straight clouds in the footprint; a cumulus inclined by the wind is a little too covering.

## The references

- **Hillaire 2020,** *A Scalable and Production Ready Sky and Atmosphere Rendering Technique*: the table of isotropic multiple scattering.
- **Van de Hulst 1980,** *Multiple Light Scattering*: the similarity relationships, `σs (1 − g)`.
- **Bohren and Huffman 1983:** the phase and extinction of the drops, g ≈ 0,85.
- **Sigg and Hadwiger 2005,** GPU Gems 2, chapter 20: the B-spline in bilinear readings.
- **Maximum cloud cover,** from radiation patterns of climate models (Geleyn and Hollingsworth 1979).
- **Apollo 17, AS17-148-22727, "Blue Marble",** NASA, 1972.
