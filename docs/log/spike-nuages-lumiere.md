# Clouds: economic light

**State, 27 October 2026:** test discarded after flight comparison. The user prefers the previous rendering; the coefficients and define of this test are removed from the active sources. The comparable GPU time does not validate its appearance.

**Return:** "It was better before." The lighting of the `5b53b81` commit is restored before the integration of `main`.

**Local archives:** modified source, launcher and palette of this test in `x64/RejectedLighting20261027/`; captures and binaries ignored by Git. The commands below describe the removed test, not the current launch.

**Old launch,** by a launcher never versioned; the test base is at the tag `piste/nuages-planete-spike`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-lumiere.ps1
```

- Departure over the cumulus, weather frozen, Eco quality.
- F1: illuminated peaks; F2: snowy mountain, exposure control; F3: layer.
- F4–F5: below layers; F6–F7: low sun and twilight; F8: cirrus.
- F9: dense region from 800 km; F10–F11: two globes; F12: shadows on the earth.
- B: opacity; C: quality; Space: weather break; V: speed×1/×5; O/P: move the sun.
- `-Temoin`: Planet before this change, with the same comparison palette, the same poses and suns.
- `-Build -NoLaunch`: compile the new isolated variant; the native V4 binary is still required.
- Legacy variants: `-Regional`, `-SansOmbres`, `-SansFiltrage`, `-Vue Meteo|Opacite|Ombres`; their first preparation requires `-Build`.

**Approximation:**

- Same density and same weather; same view transmittance integration and same shadows on the ground.
- Reuse four solar samples per illuminated point; no direction, no step, no subpixel added.
- Preserve the existing direct phase and group the following bounce in a diffuse source with little directionality.
- Solar source: `soleil × [phase × exp(−τ) + (0,65/π) × exp(−0,35τ)]`, where `τ = 80 × profondeurSolaire` is already calculated.
- Sky source: `(0,25/π) × irradianceCiel`, from the existing LUT, which already includes multiple atmospheric diffusion.
- Integrate this source with the same Beer factor of view `1 − exp(−extinction × pas)`; transmittance and depth weights are not dependent on this source.
- Sun already filtered by the atmosphere: the shades of the sunset and the disappearance of direct night are preserved.
- Image adjusted coefficients; no complete physical transport or overall energy conservation claimed.
- Local rebound of snow, ground or sea to clouds is absent from this test.

**Cost:**

- A reading of LUT and an exponential less per illuminated point than the old second order term.
- Same number of rays of view, solar densities and shadow trails; same steps and orbital filtering.
- The already high cost of four sub-radius planetary rendering remains; this fix of lighting does not resolve it.
- Point comparisons GPU on identical frames; they do not constitute a global budget or a benchmark statistic.

**Witness and sources:**

- `x64/NuageFrostbitePlaneteTemoin/`:44 files, resources and sources verified by fingerprints; base `5b53b81`, tag `piste/nuages-planete-spike`.
- Variant enabled by `FROSTBITE_EFFICIENT_LIGHTING` in `CloudFrostbiteOrbit.hlsli`; branch without this define keeps old calculation.
- Planet assets, profiles and noise functions retained; executables, captures and local witness manifests under `x64/`.
- New iteration not committed; publish and new tag on next request.
- [Epic, Volumetric Clouds](https://dev.epicgames.com/documentation/unreal-engine/volumetric-clouds?application_version=4.27) explains the role of rebounds and energy compensations in real-time approximations; the coefficients in this test are not from this documentation.
- [NASA, Shades of White](https://science.nasa.gov/earth/earth-observatory/shades-of-white-87125/) provides a real comparison neige/nuages; [With Office](https://weather.metoffice.gov.uk/learn-about/weather/types-of-weather/clouds/why-are-clouds-white) explains their variations of white and gray.

**Audits:**

- Rendering and opacity variants compiled by DXC; pre-existing warning from `Materials.hlsli`.
- Short snapshots of summits, bases and orbit; same sun and same weather for pairs ancien/nouveau.
- Opacity at 800 km: one pixel differs than 1/255 on 1280×720; the others are identical, under floating rearrangement of the optimizer.
- Snowy terrain control: difference maximale1/255; this view contains few clouds and is used for exposure control.
- Clouds+air pointed, old and new:10,90/10,74 ms in flight;27,68/27,02 ms at 800 km. New below the cumulus:8,45 ms. No additional costs observed on these points; overall gain not established.
- Full shader compiled:275→261 filtered play call sites,207→193 exponential sites; these static counts include compiler duplications and do not directly give a GPU time.
- Local captures and reports: `x64/LightPreview/`, `x64/LightPreviewTemoin/`, `x64/LightOpacityNouveau/`, `x64/LightOpacityTemoin/`, `x64/lighting-checks.json`.
- Low sun, cirrus and movement to be judged in flight by the user; no prolonged benchmark.
