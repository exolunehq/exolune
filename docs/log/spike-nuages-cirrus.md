# Cumulus, cloud cover and local cirrus

**Log from the 2026-10-30:** spike closed. The local families, cumulus, nappe and cirrus, are taken over by the clouds of the game, `../spec-nuages.md`. Launcher and assets of the test: tag `piste/nuages-orbite-spike`.

**State, 27 October 2026:** common variant compiled and ready for flight, after returning to the cirrus contours. Four hidden catches inspected. The rendering and stability at the approach of the cumulus and the reference sheet remain validated by the user; the correction of cirrus awaits his judgment.

**Request:** see the three families in the same scene; refine and lengthen the cirrus, let their fibers extend beyond the main envelope.

**Launcher:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-familles.ps1
```

- Palette of twelve views: group, cumulus, blanket, cirrus and distance.
- B: rendered éclairé/opacité; C: qualité48/24 m.
- Space: pause/reprise weather; V: weather velocity ×1/×5.
- The weather starts frozen; the wheel adjusts the speed of the camera.
- `-Temoin` opens the validated cumulus and blanket, with their data and palette frozen.
- `-Vue Opacite` and `-Vue Densite`: separate diagnostics; density shows a fixed field cut.
- `-Build -NoLaunch -Vue Rendu`, `Opacite` or `Densite` recompiles the selected variant.

**Preservation of validated families:**

- Form128³: channelR and each of its mips copied exactly from the reference; channelG reserved for cirrus fibers.
- Detail32³ and profile table64³ copied in full.
- Local weather: canauxR/G and their mips kept exactly; channelB reserved for the coverage of cirrus.
- Low density preserves the recipe of the cumulus and the blanket, their positions and profiles.
- Shells2–8 km and9–13 km traveled by segments sorted along the radius; the gap between them is skipped.
- The attenuation of the layers accumulates in their order of visibility; the inherited atmospheric approximation remains the same.
- Frozen witness: `x64/NuageFrostbiteReferenceTemoin/`, fingerprints in `witness.json`.

**Correction of cirrus:**

- In the first test, a compact weather envelope and a cover threshold0,03 could cut the still visible fibers.
- The common variant retains the low cirrus cover and draws tails of low density.
- Fibers have a separate 3D field, fixed to the world; domain Est64/Nord16/vertical8 km.
- Correlations Est8/6 km, North0,28/0,14 km, vertical0,20/0,12 km; continuous North shear of maximum amplitude0,5 km, fixed to the world.
- Their shaping precedes the density mips; the shader then reads their filtered density.
- The upper profile remains centered at 11 km, with varying thickness and height; no visible boundary should come from the shell9–13 km.
- The choices of fibers and feathers are artistic and local; the scene is not a planetary weather.
- Data source: `tools/gen_frostbite_cloud_families.py`; parameters and footprints: `assets/frostbite-families/families-manifest.json`.
- Single-stage exits: `x64/NuageFrostbiteFamiliesRendu/`, `NuageFrostbiteFamiliesOpacite/`, `NuageFrostbiteFamiliesDensite/`.

**Verification:**

- Three DXC variants compiled; pre-existing binary shift warning in `Materials.hlsli`.
- Four captures: all three families, cumulus, nappe and cirrus seen from below; `x64/FamiliesPreview/`, reported in `report.json`.
- Identical base data on all mips; identical low density function body after normalization of bound names.
- Vacuum proof MipsB checked conservative; complete sample and reference sources intact.
- The fibers remain strongly oriented; their naturalness, crossing and animation remain to be judged in flight by the user.
- No extended benchmark, planetary validation, commit, tag or push.

**Memory for the following:** Cumulonimbus retained on October 27, 2026 for a later stage, with towers and anvils. This site comes after the current local families.

**Regional Extension:** The [extended weather map](spike-nuages-region.md) keeps this scene as a frozen witness in `x64/NuageFrostbiteFamiliesTemoin/`.

**References:** [local families guided by Frostbite](spike-nuages-reference.md); [first cirrus tests](spike-nuages-cirrus-historique.md); [cirrus, International Cloud Atlas](https://cloudatlas.wmo.int/fr/clouds-genera-cirrus.html).
