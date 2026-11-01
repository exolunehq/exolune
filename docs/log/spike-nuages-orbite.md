# Clouds: first orbital integration

**Log from the 2026-10-30:** spike closed. His distant quadrature is that of the clouds of the game, `../spec-nuages.md`. Launcher and assets of the test: tag `piste/nuages-orbite-spike`.

**State, 27 October 2026:** test ready for flight; rendering, opacity and map compiled. Four views and two comparison captures inspected. The large masses are less granular from orbit, with an overhead measured on capture at 800 km.

**User feedback:** the other regional clouds are considered correct; cirrus are too many and too regularly spaced. Next priority: very high altitude and orbit.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-orbite.ps1
```

- F1-F6: same region at 30, 80,150, 300,800 and 1500 km.
- F7: rasant view; F8–F9: cumulus and close-up cloud cover; F10–F11: cirrus from below and above; F12: low sun from 800 km.
- B: opacity; C: quality; Space: pause/reprise; V: weather×1/×5.
- `-Temoin` opens the regional version frozen, with its old cirrus and palette.
- `-SansFiltrage` keeps the new cirrus data and disables orbital filtering only; separate output for comparison to identical data.
- `-Vue Meteo` and `-Vue Opacite` open the diagnostics; `-Build -NoLaunch` recompiles the chosen variant.

**Cirrus :**

- WeatherB distributed in irregular clusters, with large empty areas; average reduced to 26,8% of the regional version and peaks retained to 0,286.
- New field3D of rare and oriented fibers in several directions; shaping before the density mips.
- After shaping,7,42% of the texels of the fiber mip0 exceed0,05; the peaks reach1,0. These are field statistics, not a measure of sky coverage.
- MétéoR/G/A and forme3DR/B/A copied exactly at each mip; detail32³ and profile table64³ copied entirely.
- The low distribution, its profiles and the recipe of the cumulus/nappes remain those validated by the user.
- Data and fingerprints: `assets/frostbite-orbit/orbit-manifest.json`; source: `tools/gen_frostbite_orbit_assets.py`.

**Remote filtering:**

- The center radius retains the inherited path and detail levels.
- The distance weight increases continuously for a pixel footprint of 0,25 to 0,8 km at the first cloudy segment.
- Safety ramps reserve this first test for cameras above the layers and sufficiently deep views; incidence measured at the cloud point.
- Economic mode: four sub-pixel rays quadrature2×2; thinner mode: nine rays 3×3.
- Each distant ray samples the fine density and then integrates its own light and transmittance before the average.
- Mixing with the center radius concerns light premultiplied, transmittance and depth weights; no density mean before exponential.
- The atmospheric composition remains calculated once per pixel after the average of cloudy rays.
- The legacy center is also plotted for blending: up to five or ten cloud paths per pixel, without time history or renewed jitter.
- Data, world phase and shared clock remain independent of the number of frames and camera.

**Isolation:**

- Regional witness frozen: `x64/NuageFrostbiteRegionalTemoin/`, forty files and sources verified by fingerprints.
- Sources and previous binaries retained; new executable identical to V4 binary, only isolated data and shaders change.
- Git release: sources, assets and tools included; `x64/` ignored. Frozen executables, captures, and witness manifests remain local. Launchers require these native outputs; `-Build` recompiles the shaders and reuses the frozen V4 binary.
- Region1200×800 km and envelope650 km preserved; no extension to the whole planet.

**Limits:**

- Four or nine rays remain a finished quadrature; this first try does not guarantee the disappearance of any grain or flicker.
- Periodic textures can remain recognizable at resolved scales.
- The rasant views gradually return to the central path; not all of them benefit from orbital filtering.
- The depth of field of the central pixel is also used for the neighboring rays; approximation of this spike especially maritime.
- The cost of filtering remains to be judged on distant views; the finer mode is not a converged reference.
- In-flight checks belong to the user; no extended benchmark.

**Short controls:**

- Compiled rendering, opacity, map and unfiltered rendering; only pre-existing warning of `Materials.hlsli`.
- Views at 800 and 1500 km, cirrus seen from below and near point at 4 km; comparison without filtering at 800 km and at the same near point.
- The very dark close-up view is identical pixel by pixel with and without filtering; this control point is in the volume. The flyover buttons allow a more legible departure for the flight.
- At the same point at 800 km, clouds + air point2,88 ms without filtering and11,37 ms with four distant rays;5,96 ms at 1500 km on another capture. GPU shared, no global budget validated.
- The other captures give11,87 ms under the cirrus and3,32 ms at the near point; window titles sometimes delayed in batch mode, only the summaries GPU of the capture are taken here.
- Low channels, copies détail/profils, mips of cirrus presence and witness prints verified intact.
- Captures and reports: `x64/OrbitPreview/` and `x64/OrbitPreviewSansFiltrage/`; motion stability and transitions to be judged by the user.

**Memory:** Cumulonimbus retained for the rest, outside of this test.

**References:** [regional distribution](spike-nuages-region.md), [local families](spike-nuages-cirrus.md), [provenance Frostbite](spike-nuages-reference.md).
