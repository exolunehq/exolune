# Clouds of the game: history

**What was `../spec-nuages.md` before the 2026-10-30,** under the name `spike-nuages-planete.md`: the spike of the shadows and the first globe, then its integration to `main`. Nothing here describes the present state.

- **Code and launchers of then:** tag `piste/nuages-planete-spike` (`5b53b81`) for spike; `jalon/26-nuages-main` for integration; `jalon/29-avant-ouverture` for last state before storage.
- **Removed the 2026-10-30,** commit `3663177`: the launcher `tools/nuages-planete.ps1` and its variants, the generator `tools/gen_frostbite_planet_assets.py`, the folders `assets/frostbite-*`, the frozen witness. The shader of the game was called `CloudFrostbiteOrbit.hlsli`, its time pass `CloudFrostbiteTemporal.hlsli`.

## The light and the far pixel, up to the 2026-10-31

**Replaced the 2026-10-31 by the experiment `piste/orbite-rendu`** (`../spec-rendu-orbite.md`): from orbit, they gave gray and translucent clouds, and a sandy grain.

- **The density of low clouds** kept the cover factor: `remap(forme, 1 − R, 1) × R × profil`, then erosion. A field at 10 % had ten times less water than a front.
- **Phase:** two Henyey-Greenstein lobes, g = 0,5 and −0,5, the second at 20 %.
- **Towards the sun:** four steps of 125, 250, 500 and 1 000 m, 1,875 km in all.
- **A second order approximate,** additive and isotropic: extinction ×0,2, depth to the sun ×0,2, source ×0,35. The reflectance of an infinite cloud was peak towards 0,25.
- **The pitch** was not limited in optical thickness; the pitch stopped at a transmission of 0,003.
- **The quadrature far away:** far away, a pixel averaged fine rays, at the mip 0, 2 × 2 in Eco quality and 3 × 3 in Reference, in light premultiplied and transmittance. Its weight grew with the pixel footprint at the layer entrance, from 0,25 to 0,8 km, the camera above 14 to 22 km and the rather plunging view (`CLOUD_FAR_*`). The time pass traced a thin radius per visit and averaged eight at most, two moving (`CLOUD_TEMPORAL_FAR_RAYS`, the jitter of `cloudTemporal.w`).
- **The weather map** was bilinear.
- **The air** counted all the diffusion of aerosols in its table of isotropic multiple scattering, and a gray ground at 0,3 below it, including the ocean.

## The artistic weather map, up to the 2026-10-31

**`assets/clouds/weather-planet1024.rgba8mips` and `tools/gen_cloud_weather.py`, removed the 2026-10-31** (commit `051e3f0`, tag `piste/nuages-climat`): the map is now calculated on the climate (`../spec-nuages.md`, the weather map).
- **What it was:** Perlin fields 3D on the unit sphere, from 2 600 to 90 km, seeds and shifts distinct by octave; fronts in level lines, benchmarks, fragmented convective regions; tropical convergence and mid-latitude tracks in low slopes.
- **Its figures:** average coverage 0,094; above 0,03 on 56 % of the sphere, of 0,2 on 15,5 %, of 0,4 on 3,3 %; cirrus above 0,03 on 1,6 %.
- **Its defect:** no link with geography; a distribution without meteorological coherence, considered unnatural in flight.

## The first map drawn from the climate, the 2026-10-31

**Replaced the same day** by the weather view of orbit (`../spec-nuages.md`, the weather map; log of the 2026-10-31). Commit `051e3f0`, tag `piste/nuages-climat`.
- **Its defect, seen from orbit:** three to four times too little clouds, 17 % of the sphere covered against two thirds on Earth, and isolated spots without organization. Under the law `remap(forme, 1 − R, 1) × R`, only the contour R ≈ 0,2 drew a visible cloud, and the ceiling of 0,6 bounded everything.
- **Its components:**

| Cloud | Where | Cover, family |
|---|---|---|
| Convection, the ZCIT and monsoons | heavy and hot rain, from 800 to 2 500 mm and from 14 to 26 °C, in clusters stretched along the thermal equator | 0,58 in clusters, 0,04 between them; cumulus |
| Cumulus of good weather | wetlands | 0,2; cumulus |
| Cumulus of trade winds | warm seas, cleared by subsidence, low rainfall | 0,1; cumulus |
| Stratocumulus sheets | above cold water rises, smoothed on 500 km and reached 700 km leeward | 0,5; layer |
| cloud banks windward of relief | where the wind climbs the slope of the smoothed large shapes on 120 km, from 0,02 to 0,12 m/s | 0,42; mixed |
| Cold seas stratum | beyond 45 to 62° | 0,3; layer |
| Depressions of the rails | 18 at a time, towards 50°, where the west winds blow over the sea, at 2 600 km from each other | the head in comma 0,6, its dry slit; the cold front 0,52; the hot front 0,45; its shield 0,42 under cirrus of 0,24; thick |
| Cells behind the fronts | cold air on the sea | 0,3; cumulus |
| Stratus of rails | between depressions | 0,16; layer |

- **The strongest wins,** and gives his family.
- **The sky clears** over the deserts, under 80 to 350 mm, and leeward of the reliefs, where the air descends from 0,015 to 0,1 m/s; the sheets keep the seas dry.
- **The cirrus:** the anvils above the clusters of the ZCIT; the jet stream trails towards 31°; the shields of the hot fronts.
- **The noise functions,** gradient on the sphere, from 1 200 to 160 km: the map is read towards 80 km, thinner would only lower its average.
- **A depression,** on its own scale of 700 to 1 200 km and its stage, from a wave to an occlusion: the head northwest of the center; the dry slit that winds up from the southwest; the cold front, a curve of 300 to 200 km wide towards the south-southwest; the warm front and its shield to the east; mirrored to the south. Its left contour of 18 % of its scale.
- **The budget,** seed 0: average coverage 0,110, against 0,094 before; above 0,2 on 16,8 % of the sphere, against 15,5; above 0,4 on 3,1 %, against 3,3; cirrus above 0,03 on 3,3 %, against 1,6. By band: 0,150 from 0 to 10°, 0,059 from 20 to 35°, 0,128 from 35 to 60°.
- **Time:** 235 to 296 ms at title, on a machine loaded by other renderings.
- **His figures,** seed 0: average coverage 0,110; above 0,2 on 16,8 % of the sphere; cirrus above 0,03 on 3,3 %.

## The state and launch of then

**State, 27 October 2026:** Previous lighting restored after rejection of diffuse compensation; integration to `main` with sea FFT and vegetation. Local families and global weather remain those of the spike.

**Test rejected:** [light economic](spike-nuages-lumiere.md). The lighting model retained is the `5b53b81` commit.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-planete.ps1
```

- F1–F2: two hemispheres from 10000 km.
- F3–F6: cumulus and clouds from 800, 300 and 80 km.
- F7–F9: overflows of the three families.
- F10–F11: longitude and polar region connection; F12: shadows from 30 km.
- B: opacity; C: quality; Space: pause; V: weather×1/×5; O/P: move the sun.
- `-Regional`: only the shadow changes from the accepted Orbit data; dedicated regional palette.
- `-SansOmbres`: same data, same rendering, no cloud shadows on surfaces; separate executable.
- `-Temoin`: Planet at commit `5b53b81`, before lighting rejected and before this integration; native, palette and textures frozen.
- `-Vue Meteo`, `-Vue Opacite`, `-Vue Ombres`: isolated diagnostics; white in Shadows means solar transmission1.
- `-Soleil '5 215'`: choose sun at launch, by latitude and longitude; test buttons carry their own sun.
- `-Build -NoLaunch`: compile the native Release x64 merged then the chosen shader; Visual Studio2022/MSBuild and DXC required.
- By default, the launcher enables main validated vegetation: game models, near meshes, far impostors, twelve climate bushes, HiZ and material depth.
- The expected caches are in `assets/foliage/climate_shrubs_v2/`; `-VegetationAssets` chooses another prepared folder. A missing cache stops the launch with an explicit error.
- The historical vegetation, v3, is removed from the engine the 2026-10-30: we come back to it only by its tag, `piste/vegetation-v3` (`recherche-vegetation-historique.md`).
- `-Parcours tools/tests/2026-10-27-arbustes-climatiques.txt`: replace the flight palette with the twelve vegetable views; `-Position` chooses the initial view.

## Plant composition regression, measurements of the 27 October


- The old integration kept the solar part of the terrain under the detailed trees; even without solar attenuation, the `scène − soleil` clamp reinjected this terrain into their color.
- Off-screen control: `tools/banc_composition_surfaces.py --exe <natif> --out <dossier-neuf> --dxc <dxc.exe> --scans <scans>`.
- The benchmark copies the runtime and shaders; it only forces the transmission of shadows to 1, with active clouds. The four views boreal, temperate and desert must find the image without shadows, à1/255 close. Test copies are never used for theft.
- `--sans-hiz` and `--profondeur-historique` isolate the depth and drawing variants.
- Check of October 27: four images strictly identical after correction, zero pixel different; the old code modified up to 433185 pixels more de1/255. Clouds completely disabled were already neutral; you have to keep their active pass to reproduce this defect.
- Without solar composition, the four images avant/après remain strictly identical; lighting total plant retained. Render regular with real shadows inspected on the ground and at 35 m in boreal forest, then entrusted to the flight; no new performance budget validated.

## Isolation, the witness and variants


- Accepted witness: `x64/NuageFrostbitePlaneteTemoin/`,44 files verified by footprints, including copied sources; Git reference `5b53b81`, tag `piste/nuages-planete-spike`.
- New assets in `assets/frostbite-planet/`; `tools/gen_frostbite_planet_assets.py` generator, manifest and flight points delivered with the pack.
- Deterministic artistic weather; no atmospheric simulation, no coupling with the coasts and the relief of this planet.
- The cirrus fibers retain the reference frame E/N fixed of the accepted scene; their direction does not yet follow a local tangent wind on the whole globe.
- The global map has a pitch close to 39 km at the equator, about 78 km at mip1; small regional variations in coverage are not reproduced by this map.
- The shadow path is a spike reference; its filtering through the density mips and its sample ceiling do not constitute an exact optical mean.
- The whole planet can cover more cloudy pixels than the region; the cost of the overall rendering remains to be judged, without a promise of a valid budget.
- Release requested: branch `codex/nuages-voxel-poc`, tag `piste/nuages-planete-spike`; executables, captures and cookies under `x64/` local and ignored.
- Native built-in isolated in `x64/NuageFrostbiteMainNative/`, variants in `x64/NuageFrostbitePlaneteMain*/`. Old V4 executables and witnesses are not overwritten.
- The fusion preserves the vegetation and sea fields of `main`; cloud phase and wind have a separate vector. Planetary map in `t29`, out of cloudy resources.
- Integration experiment: `piste/nuages-main-integration`. Clouds32 mode retains the terrain, map and climate0–31 diagnostics from main.
- The second solar target retains the direct contributions of earth, water, solar reflection and foam; the reflected sky remains in the ambient component.
- Old spike launchers based on V4 are rebuilt to their historical tag; the current Planet launcher and its native use the new GPU contract from main.
- Flight checks entrusted to the user; no extended benchmark.

## The short spike and integration controls


- Compilation DXC of with/without shadows and diagnostics rendering; only pre-existing warning of `Materials.hlsli`.
- Two globes rendered on opposite hemispheres, then dense region at 800 km and earth surface at 30 km.
- Sea at 80 and 300 km with/without shadows, then sun higher at 80 km; transmission diagnostic inspected.
- Earth at 30 km: identical comparison except shadows, average deviation3,23/255, maximum123/255;32,1% of pixels darkened more de2/255. This check confirms a visible effect, not its optical convergence.
- Clouds+air point:19,46 and18,76 ms for both globes,28,09 ms in the dense region,10,36 against8,98 ms on the ground with/without shadows; GPU shared.
- Captures ignored by Git in `x64/PlanetPreview/`, `x64/PlanetLandShadow/`, `x64/PlanetLandShadowSansOmbres/` and `x64/ShadowDiagnostic/`.
- No E2E check in motion; poles, coupling and approach remain to be judged in flight.
- After integration: Release x64 and 72 shaders of the project compiled, then variant Planet; captures in orbit at 800 km and 60 m over the sea FFT, without error of start. Clouds+spotted air27,65 and17,75 ms.
- Detailed vegetation verified with the local assets already prepared of main:13610 impostors hardwoods, zero overhang or floating plant; capture at 567,2 m above ground. GPU total37,97 ms, of which14,44 ms clouds+air; this view does not validate a global budget.

## Close-up: F on the column at the seen point, 2026-10-31 to 2026-11-02

**Replaced on 2026-11-02 by F per point,** on the sun's chord (`../spec-rendu-orbite.md`): the seen point jumped between lobes and drew shiny rims and dark channels. The account of then:

**The defect, in flight, after fusion in `integration`:** from 1 to 10 km, clouds of shiny plastic, a dark circle on their contours and on the folds where one lobe passes before another, a brilliant backlit border, a flat interior.

**The causes, by elimination,** on cumulus seen from 1,5 and 3 km, sun from front, side and back, against the shaders before the experiment and the same map:
- **F measured the thickness along the view:** on an edge or the silhouette of a lobe, the razor ray crosses only a thin string, F collapses, the multiple scattering extinguishes: the cerne. Cut F erases it.
- **The edges were smooth surfaces:** the physical water of the cloud, up to 80 /km, makes the boundary opaque in 12 m, and the noise functions have no detail under their texels, 250 m and 125 m: their smooth isosurface looked like plastic. The old law, density × R, softened them by transparency.
- **Neither the phase nor the card at the mip 0** were responsible for anything.

**The tests dismissed:** F along the sun, gray spots at the heart of the cumulus where the line of the sun comes out by the base; along the normal, an aspect of liquid metal, the gradient of a thin noise turning from one pixel to another; the column in medium density, rings, then gray cumulus where the covered part mixes the clear sky.

**The correction:** the thickness of F is that of the cloud where it exists, its column smoothed at the scale of diffusion (above, the multiple scattering); and the variance of the unresolved scales broadens the edges in fringes. No more circle, fold or plastic; orbit targets do not move, thick cloud at 0,685 before as after.

**What remains:** the cumulus relief close-up is softer than before the experiment; ratio of 10e and 90e percentiles of luminance, side and back, 0,68 and 0,77 against 0,46 and 0,67. Their multiple source takes an average incidence, 0,5 for a cumulus, and not that of each face. experiment: local bearing, by the density gradient smoothed at the diffusion scale, smooth at this scale.

**Cost:** +0,1 to +0,5 ms, the column of each segment.

## The night's key light, first trial, 2026-11-13

**Discarded the same day** for the chord now in `../spec-nuages.md`, toward and away from the key moon.

- **The trial** turned only the six samples toward the light to the moon and kept the three behind the point away from the set sun.
- **Both halves then looked upwards:** a top's chord held no cloud, F fell to zero and moonlit clouds turned black from orbit; at 2 000 km, p90 37 fell to 6 in sRGB.
