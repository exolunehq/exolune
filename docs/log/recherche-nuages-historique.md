# Cloud history: the 2D layer and the old volume

**What gave `../recherche-nuages.md` the 24 and 25 October 2026,** out of the search the 2026-10-30: the time map and the layer 2D, commit `6a88d33`, then the volume in cascades of the ground orbit, tag `piste/nuages`, and its stability, branch `muse-nuages-stabilite`. The clouds in the game replace them: `../spec-nuages.md`.

The sections follow, as they were in the search, the most recent at the top.

## Fact: volume, from orbit to ground (2026-10-25)

**The 2D layer is removed.** Clouds are a volume thrown at the quarter of pixels everywhere they are in view, from orbit to ground, half of them per checkerboard frame, accumulated from one frame to another. The plane kept a layer 2D from far: in flight, it was flat, full, without transparency, and cut the bridges at the ribs.

**The field.**
- **The weather map is cooked at startup,** on a cube: the climate and the octaves of time of 131 km and more.
- **The columns hold in five cascades fixed on the planet,** from 62,5 m to 16 km the texel, each texel the average of the column on it. A cascade is recalculated only when the camera has traveled a quarter of its width. Beyond the last one, at the limb, the column is calculated on site.
- **Octaves of 1 km and less are converted to 3D.** A tile of volute cells replaces them, of the same standard deviation (0,389 of that of the clouds). They cut the edges and raise the summit: cumulus in cauliflower, bumped bridges. From afar, the mips of the tile makes the average: the universal rule.
- **The summit rises with the depth in the field:** clouds thin at their edge, in domes for cumulus, steep sides for bridges.
- **Cumulonimbus:** in strong convection, the peaks of the octaves of 16 and 8 km, a tenth of the air about. Tours up to the tropopause, flanks bumped by a reading shift that varies with height; anvils among cirrus.
- **The cirrus fibers,** from east to west, the tile stretched eight times.
- **no more grids of orbit points views.** The octaves of a gradient noise shared the nodes of their nested grids, where all cancel out together. Each octave is shifted by a fraction of the golden number (`CloudFbm`).

**The light.**
- **Simple diffusion:** three points towards the sun, from 50 m to 1,5 km; two Henyey-Greenstein lobes; the powder of the backlit edges.
- **multiple scattering two-flow (Bohren 1987):** R on the illuminated side, diffuse transmitted on the other, between the two according to the part of the optical thickness on the sun side, taken along the sun ray. Sides illuminated, bases and faces with dark shadow. The first version reversed the two faces: gray peaks, thin milky clouds.
- **The sky from above, the ground from below.**
- **One step per unit of optical thickness approximately,** to avoid skipping the illuminated skin; the foot of one step is worth the pixel footprint, plus one quarter of the step.

**In other passes.** The ground writes its sunlight alone into a second target; the atmosphere pass applies there the shadow of clouds and the light diffuses under them, and cuts the air at the depth of clouds.

**Stability (2026-10-25, branch `muse-nuages-stabilite`).** In flight: tingling, square seams then turned cascades, disk of close detail, mutations to approach. The field is frozen: all this movement was sampling.
- **The history is governed by the reprojection error** (`CloudResolve.hlsl`): in texels of the quarter of resolution. Below, the previous image's march, fresh or other half of the checkerboard, is a sample of the same cloud and accumulates; beyond a texel, the unmarched texel carries its reprojected past alone, and a distance shift (the opacity centroid, in wide ramp) removes the past. The distance itself accumulates. The past is clipped to the moments of neighborhood, two standard deviations.
- **cascades no longer draw their square**: distance on the plane, blend of 0,35 to 0,98 half-side, fractional fine level in descent, smoothed maximum between level constraints (`LevelMax`, rule in `../principes.md`), refocus by texels wholes of the own plane, transported axes.
- **Near detail keeps the average**: faded by octaves of footprint; vertex multiplied in lognormal, average the column; offset gate of the correlation gate × ceiling, `fine × lift`.
- **Field cutoff** reads the distance of the filtered clouds as their light; the smoothing reprojection distance is weighted by opacity.
- **The shift of the march remains renewed per frame**: fixed by pixel, it left the bias of quadrature of each texel in regular dotted on the converged frames, measured; in common golden progression, the jitter doubled. It is the historical governed that absorbs it.
- **Measurements:** `tools/banc_nuages.py --parts stabilite` (new) and `docs/journal-planete.md`, same day.

**Measurements:** `../journal-planete.md`, 2026-10-25.

**What remains:**
- **cost exceeds budget under cirrus,** 3,6 ms, see log;
- **cumulonimbus towers are too regular,** cylinders with a disk on top;
- **no wind:** cirrus and streets of frozen clouds; the wide movement of formations is the next work, the field remaining a pure function of place and time for the historical to reproject;
- **a fine arc at the crossing of range of the cascades,** softened but visible on the captures at 54 and 135 km: ceiling and sigma of a coarse texel are not the average of the fine texels it covers. The rule would want coarse cascadess averaged from fines where they overlap, instead of a `ColumnAt` by texel at each scale.

## Done: steps 1 and 2

**The weather map decides, by air column:**
- **cloud cover,** the average share of cloudy sky: humidity of the climate and a rising belt at the polar front, from 19 to 56°;
- **convection,** from 0 to 1: heat and humidity at sea level, and `W.y`;
- **the type:** stratiform without convection, cumulus with, cumulonimbus at the heart of clouds in strong convection;
- **the base,** by Lawrence formula; fog when it touches the ground, 2 to 3 % of columns;
- **the summit:** 0,3 km for stratus, 1,5 km for cumulus;
- **cirrus:** a layer of 1,5 km, 3 km below the tropopause, their cloudiness drawn from the polar front and anvils.

**This deviates from the plan.**
- **One spectrum, from thousands of kilometers to meters.** The time `W` and the clouds `M` are the octaves of a same noise gain 0,79, the spectrum in k^-5/3 of the cloud fields (Cahalan and Snider 1989). Fronts are in the threshold field, not in cloudiness. With the gains 0,5 and 0,55 of the plan, nothing between 30 and 300 km: all clouds had the same size, in leopard skin.
- **Cumulus weigh their small octaves 2,5 times more:** fields scattered over entire regions. The fronts make layers.
- **No intertropical belt:** the fit gave him 0,065. The humidity depression of the deserts already bears the profile.
- **Layers are thick shells,** from base to top, placed by octaves of time of 131 km and more.
- **A ray sees the first cell it encounters,** that of the pixel, then the average of the region behind it: a cell every 5 km along the path, measured on the field. The average over the entire journey blurred a field seen from bias.
- **Light: two fluxes, g = 0,85.** The part diffused forward remains in the beam (delta, 1 − g²): a cirrus shows what it covers. The summit of the cumulus is illuminated according to its slope, each octave tilting it as much as the detail bands of the ground.

**Measurements:** `../journal-planete.md`, 2026-10-24. benchmarks : `tools/banc_nuages.py`. Flight tests: `tools/tests/2026-10-24-nuages.txt`.

**What was flat or missing after step 2,** processed by volume except wind:
- **in the diaper, everything is flat:** no turns or sides. The camera in the cloud sees a uniform fog;
- **the cirrus are not frayed:** it would take the wind;
- **the air under the clouds is shaded by the average of the region,** not cloud by cloud;
- **the ground does not reflect its light back to the base of the clouds;**
- **cost exceeds plan budget,** see journal.
