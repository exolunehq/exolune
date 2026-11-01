# Local reference guided by Frostbite

**Log from the 2026-10-30:** spike closed. Its recipe, the Frostbite noise functions, the profiles and extinction of 80/km, is taken over by the game's clouds, `../spec-nuages.md`. Launcher, shaders and assets of the test: tag `piste/nuages-orbite-spike`. The commands below describe the test, not the current launch, `../lancement.md`.

**State, 27 October 2026:** local rendering and approach stability validated in flight by the user for cumulus and blanket. This version remains the witness of the trials of new families. No planetary results validated.

**Start rendering:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/nuages-frostbite-reference.ps1
```

- Default freeze weather; F1–F6: cumulus; F7–F11: cloud cover; F12: two areas seen from above.
- B: opacity without lighting; C: not economical48 m / reference24 m; Space: weather break.
- `-Vue Opacite` directly opens the diagnostic3D: opaque white, transparent black.
- `-Vue Densite` opens a fixed 2D cut of the real field, independent of the camera.
- Cut: west to left, east to right, from−64 to+64 km; altitude0 at the bottom,10 km at the top; white for density≥0,25.
- Diagnostics bypass exposure and tone curve; illuminated rendering preserves them.
- `-Build -NoLaunch -Vue Rendu`, `Densite` or `Opacite` recompile only the selected variant.
- `-Temoin` opens Courants C with its four real assets frozen; its weather differs, it is not a comparison to identical data.

**What comes from the sources:**

- Report: [Hillaire, Physically Based Sky, Atmosphere and Cloud Rendering in Frostbite, chapter5](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/s2016-pbs-frostbite-sky-clouds-new.pdf), in particular pages33–39.
- Generator: [sebh/TileableVolumeNoise, revision1f879a26b89aaa4b5a7f112f14ec149d08057661](https://github.com/sebh/TileableVolumeNoise/tree/1f879a26b89aaa4b5a7f112f14ec149d08057661).
- The original C++ code and its parameters are unchanged; MSVC19.44.35209, execution4,68 s for the TGA.
- `noiseShapePacked.tga` provides shape128³; `noiseErosionPacked.tga` provides erosion32³.
- Documented conversion of TGA axes, RGB channels equal and alpha255; mips by mean3D, without dynamic range modification.
- Sources and licenses: `third_party/FrostbiteNoise/`, `third_party/FrostbiteNoise/README-provenance.md`; order and footprints: `assets/frostbite-reference/noise-manifest.json`.

**What is chosen for this test:**

- The report does not provide the full density shader or artistic adjustments of its images; this prototype is not a full port of Frostbite.
- Two weather zones drawn: cumulus around 0,5°/161,5°, cloud cover around 0,5°/162,05°.
- Local map256×128 km, projected on a fixed origin0,5°/161,775°; no climatic or NASA distribution in this scene.
- Cover traits are explicit and deterministic; it is not a global natural distribution to judge.
- Density and erosion profiles according to type/hauteur: `profiles-authored.json`, generated from the constants of `tools/gen_frostbite_reference_scene.py`.
- The 2D profile table is stored in the existing 3D64³ container, identical on Z, to avoid native modification; read to mip0.
- Form at period32 km, detail at4 km; global phases in double precision and remains local float, without deformation or additional band.
- Fixed combination: threshold of noise by cover, multiplication by density profile, then erosion weighted by the second channel of the profile.
- Extinction neutre80/km and albedo1; four solar progressive intervals0,125/0,25/0,5/1 km, sampled in the middle.
- Segment analytic integration retained; phase and second-order approximation inherited from spike, separate from full Frostbite engine.

**Support and insulation:**

- Layer2–8 km; null profiles at both ends.
- The weather support enters a sphere80 km around the fixed origin; it limits the course without drawing the silhouettes.
- R weather mip1 average, mips2+ maximum conservative; vacuum jumps measured in the local plane with filter margin.
- Same frozen V4 executable and same b1/t24–27 resources; only local shaders and their data change.
- Independent outputs: `x64/NuageFrostbiteRefRendu/`, `NuageFrostbiteRefOpacite/`, `NuageFrostbiteRefDensite/`.
- Frozen validated witness: `x64/NuageFrostbiteReferenceTemoin/`, executable, shaders, four assets and palette copied; footprints in `witness.json`.
- In diagnostics, only an isolated copy of ToneMap bypasses the exposure; old binary and shaders remain intact.

**Short control:**

- Three successful DXC builds, pre-existing shift warning in Materials.hlsli.
- Five captures: two illuminated families, two opacity silhouettes and a density cut; source and poses in `x64/FrostbiteReferencePreview/`.
- The cut confirms distinct profiles; opacity allows to judge the contours without the lighting.
- Cumulus: visible budging peaks; table: profile significantly thinner and still very smooth.
- noise functions non-constants, mips weather conservatives, identical profile slices and zero density at the checked limits.
- Clouds+air point times:6,52 ms cumulus and 5,29 ms nappe in captures; GPU shared, no statistical comparison or extrapolation to the planet.
- No complete benchmark or time history; validation of rendering and approach stability comes from user in-flight checks.

**Follow-up:**

- First complete the local families with the [cirrus](spike-nuages-cirrus.md), in an isolated exit.
- Keep the recipe of the cumulus and the valid layer.
- Next study the distribution of larger formations, distant filtering and planetary extension.
- Cumulonimbus: experiment interesting retained for later; towers and anvils to be treated after the current local families.
- No commit, tag or push requested.

**History:** [search, variants Wicked and Courants C](spike-nuages-reference-historique.md).
