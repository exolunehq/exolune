# History of planetary vegetation tests

**2026-11-03 · Superseded impostor-light investigation**

**The lighting of the impostors (2026-10-29):**
- **The defect seen in flight:** at the relay, a dark tree lit up by becoming mesh. Pre-optimization: `242d0f7` and the 8 round give the same still image.
- **The cause, the normal:** the impostor mixes four cooked views and its mips. The average of the normals of different sheets, renormalized, turns to the camera. The impostor lit up like a card facing the eye: dark in backlight and under a high sun in front, clear sun in the back.
- **What is not for nothing,** tested one term at a time: specular, occlusion, normal maps, transmission, pre-calculated visibilities, covered by the canopy.
- **Light correction:** the length of the mean normal is the consistency k of the leaves. The direct, the backlight and the term sol/ciel take the hope on these leaves: E[max(0, x)] = E[x]/2 + E|x|/2; E[x] follows the normal mean, E|x| goes from 1/2, scattered leaves, to |x|, a single leaf.
- **Where:** `OutputVolume`, and `Light` for pins without pre-calculated visibilities, under `PLANET_FOLIAGE_IMPOSTOR`. The shaders of the meshes compile to the bit as before.
- **Color correction:** `tools/foliage/bake.py` averaged its four sub-sample in sRGB; it averages them linearly. luminance of impostors: hardwood +8,6 %, pine +1,9 %, shrubs +1 %.
- **Recurated** by `python tools/foliage/bake.py --impostor-only --out assets/foliage/climate_shrubs_v2 <modèles>`, the complete list in `lancement.md`: normal, alpha and bit-identical headers. The `.bin` are not versioned; the previous ones are in `x64/vegetation_eclairage/imposteurs_avant/`.
- **Measurement:** luminance of the same plants, mesh against impostor alone. On the ground, plants more 300 pixels, 4 places, 5 suns and a place under the cumulus. At the relay, at 25 m from the ground, the farthest quarter of the meshes.

| Report mesh / impostor | Before | Colour only | color and light |
|---|---|---|---|
| On the ground, whole image | 0,82 to 1,30; 13 % on average | 0,79 to 1,24; 11 % | 0,87 to 1,15; 7 % |
| On the ground, crowns | 0,89 to 1,47; 18 % | 0,80 to 1,33; 12 % | 0,88 to 1,21; 9 % |
| On the relay | 0,86 to 2,05; 21 % | 0,77 to 1,90; 16 % | 0,86 to 1,74; 13 % |

- **What remains:** the mesh remains lighter from 4 to 26 % under a high front or rasing sun, darker from 10 to 14 % sun in the back. The worst at the relay, 1,74, is the backlit edge, where a large nearby tree dominates the measure. Cause not found.
- **Cost:** few operations per pixel of impostor, not measured at benchmark.
- **In flight:** `tools/tests/2026-10-29-imposteurs-eclairage.txt`, to be judged. Images and measurements: `x64/vegetation_eclairage/`.


**2026-11-02 · Replaced catalogue limits**
- The runtime exposed one conifer and one broadleaf model across all tree climates.
- Twelve shrubs supplied two randomly interleaved architectures per climatic family.
- Fourteen models shared six queues, seven SRV per model and a 1,056-byte command/count buffer.
- Foliage was static; no tall-grass or flower catalogue complemented the ground tufts.
- The diverse catalogue replaces those limits with twenty-nine models, spatial communities and near-ground wind.
- The original catalogue remains a supported fallback; current scope and checks are in `../spec-diversite-vegetale.md`.

**2026-10-27: first variants in flight.**
- The volume hybrid is considered too expensive and unconvincing at intermediate distance by the user.
- Pure impostors remain images at any distance; their enlargement becomes visible when approaching.
- The `hybrid-impostor` variant adds the close mesh with the same relay as the volume hybrid.
- No benchmark or automatic capture is launched before these flights, at the user's request.

**2026-10-27: flashing with a still camera.**
- The first placement retained first-come first-served per atomic append up to 65 536 plants per list.
- The renderer still imposed a limit of 65 536 per species and representation, after gathering the lists.
- In the title of the application during the flight, the placement announces 87 395 distant plants, beyond its capacity.
- The render also announces 1 134 overruns in the queue of hardwoods impostors.
- These truncations can change the plants retained according to the order of the waves GPU, even without camera movement.
- The opacity mask already uses the pixel and the stable seed of the plant; no frame number is involved.
- The correction replaces saturating selections with deterministic compaction and sizes downstream queues for source list union.
- The values are from the existing title of the application; they do not constitute a performance benchmark.

**2026-10-27: photo models, rectangles and material filtering.**
- The first fitting uses the young spruce and Poly Haven jacaranda, even in adult forests.
- The user finds the connection and range satisfactory, but the models are too photorealistic and detailed.
- A first optimization keeps these models to isolate the projected rectangles and textures filtered by the hardware.
- The direction chosen then is semi-realistic stylized: natural forms, foliage in masses and simplified details.
- Photo models remain selectable by `-Models photo`; they are no longer the default of the launcher.

**2026-10-27: full bundles test, rejected.**
- `tools/foliage/stylise.py` builds a hardwood of 9 720 triangles and a conifer of 8 174 triangles.
- The foliage uses lobed opaque volumes, soft colors and smoothed normals, without individual leaves.
- The user sees balls and judges this simplification excessive.
- The target is specified: realistic AAA game trees, credible leaves and twigs; the masses consist of detailed foliage.
- `-Models stylized` retains this try; it is no longer the launcher's default.
- The decrease in the number of triangles is not a visual validation or a measure of gain of FPS.

**Current condition:** `../vegetation-planetaire.md`.

**2026-10-27: pointillism on the ground and full bushes.**
- The user's screenshot shows a deciduous tree with trunk and contours disintegrating in spots, in front of the old bushes in masses.
- View: `364.2 10.37168 -119.46971 1.1 89.2`; the title of the capture announces 56 FPS, without constituting a benchmark.
- The impostors 128² participated up to 512 pixels of theoretical height, with opacity and stochastic relays.
- The nearby meshes read atlases to the buffer, without mipmaps; bushes remained in the old renderer.
- The fix adds an earlier relay per plant, a stable alpha test, the mipmaps and a real bush model.
- No automatic measurement or capture preceded this new flight, at the request of the user.

**2026-10-27: volume of deciduous trees and shrubs.**
- The following application allows off-screen iterations compared to forest photos, without aiming at their photographic reproduction.
- The boreal serves as a witness; the lack of leaves and wire patterns are mainly found in deciduous trees and shrubs.
- Two structure and light references were examined: [Parkhill, Jim Champion](https://commons.wikimedia.org/wiki/File:Broadleafed_woodland_in_summer,_Parkhill,_New_Forest_-_geograph.org.uk_-_210761.jpg) and [A woodland edge, Evelyn Simak](https://commons.wikimedia.org/wiki/File:A_woodland_edge_-_geograph.org.uk_-_1348876.jpg), under [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0/). The local originals and their footprints are under `x64/ForetVolumeComparaisons/references/`.
- Criteria used: hierarchical bouquets, foliage oriented in several planes, shaded hearts, illuminated ends, irregular piercings; small details alone do not give volume.
- The pre-calculated occlusion approach is based on [Unity, Book of Dead](https://unity.com/blog/industry/book-of-the-dead-quixel-wind-scene-building-and-content-optimization-tricks); the local orientation of normals on [SpeedTree, Card generator](https://docs9.speedtree.com/modeler/doku.php?id=card_generator). This project does not use Unity or SpeedTree.
- series 1: source models and original lighting, then more bundles supplied to identical lighting (`volume_0`). The crowns fill up, but the plans remain legible.
- series 2: same geometry with self-shading forces 0,65 and 1. Maximum strength darkens the hearts further; 0,65 keeps more readability.
- series 3: foliar normals with local anchorage, 0,65 strength. Geometry and visibility identical to series 2; modeling progresses without additional triangles.
- These series cover eight views on four biomes and two suns; all six accounts are identical and zero overruns in each view.
- The first measurements GPU share the map with another application: they do not allow to conclude a gain or a regression of FPS.
- The black undergrowth also reveals a pre-existing error: the luminous cover adds trees and shrubs, sometimes beyond 1. Transmission composition corrects this rule for the ground and its objects.
- The benchmark quality then triggers a GPU block on its first site. The compiled shader reads the visibility buffer even without sidecar; its neutral buffer of 24 bytes does not cover the vertexes. A full buffer corrects access; the target view is captured again.
- Intermediate steps, their executables and assets are frozen and hashed in `x64/ForetVolumeComparaisons/`.
- The 60 orthographic views of the bake gain on average 24,7 % of coverage for the deciduous and 33,0 % for the shrub, at the same radius and at the 0,5 alpha threshold. It measures the silhouettes of the models, not the planetary cover or performance.
- The final version composes the soil cover by union; the undergrowth soil becomes readable again in the comparative views.
- Optimisation retained: normal color and alpha rejection readings, depth and visibility. Eight identical captures bit-by-bit avant/après; median of the vegetation pattern 9,34 → 7,43 ms and p95 30,26 → 26,73 ms on this series of 192 images, without independent repetitions. Overall times remain variable; no FPS gain guaranteed.
- Rejected variant: ignore views of exactly zero weight. All eight images remain identical, but six views out of eight slow down slightly; overall benefit not established. The retained shader only keeps the early transparent rejection.
- The repaired quality reference ends the 24 sites without blocking GPU. It already exceeds fourteen p95 thresholds of the canon condensed at 30 sites; these deviations cannot be attributed to the final variant. The matched comparison uses these same 24 sites.
- The candidate V1 also completes the 24 sites without loss GPU, but fails at three thresholds: éboulis/50 m, gap +53,48 % and repeat +14,67 % on four crops; sol/200 m, gap +19,68 % on 125 crops. Report: `x64/ForetVolumeComparaisons/qualite_finale/comparaison_p95.json`.
- The coordinates of the crops are matched exactly. Images labeled scree contain a canopy; those on the ground at 200 m contain tiny plant silhouettes. The CPU analysis shows that foliage dominates the differences, without proving a zero contribution of shadows.
- Diagnostic views reject planetary vegetation, while color draws it; the crop label does not mean that all of its visible pixels are from the ground. The benchmark and its threshold remain unchanged; the candidate is not declared validated.
- Targeted assignment: source models, force 0, ground and objects with corrected union. The four scree crops maintain the p95 gap at 1,49814, against 1,49811 in reference and 2,29934 with the candidate. On the 60 soil crops of the only 23–24 sites: 2,11036, against 2,10876 and 2,75590. The union alone explains very little of these differences; the new models and their lighting remain associated in this diagnosis. Report: `x64/ForetVolumeComparaisons/attribution_union/rapport.json`.

**2026-10-27: comparisons of the milestone 24, released from the spec 2026-10-30.**
- `tools/banc_foret_volume.py` and `tools/foliage/foret_volume_vues.json` fixed eight views of four biomes and two suns. Removed the 2026-10-30: they targeted the single bush `game_shrub` and adjustable self-shading force.
- Hidden captures, same cameras, shaders and hashed assets; 8 heat images then 24 measures GPU per view.
- The photos serve as references of structure and light; they are not scenes set for a pixel-by-pixel metric.
- Reports, captures, and logs are kept in `x64/ForetVolumeComparaisons/`.
- The first series share the GPU with another application; their times show no gain from FPS.
- On the matched series after repair, optimization alone gives a median vegetation pattern of 9,34 to 7,43 ms, with eight identical images bit by bit; the overall times remain variable.
- Compared to the source models, the final cost increases especially in the middle of temperate and tropical forests; this work does not constitute a validation at 60 FPS.
- Rendering buffers are changed from 229,49 to 250,62 MiB on this comparison; instance queues and temporary memory excluded.
- The benchmark quality accepts `--batch-suns --from-sites <rapport détaillé>` to reproduce the sites and their sun in a single hidden process.
- The condensed report `tools/banc_qualite_reference.json` is used for `--before`, not `--from-sites`.
- The two paired passes end the same 24 sites without GPU loss; the binaries and assets remain identical to their starting footprints.
- The quality criterion fails on 3 p95 on 59: scale hole of scree at 50 m (+53,48 %, 4 crops), repetition of the same crops (+14,67 %) and scale hole of the ground at 200 m (+19,68 %, 125 crops).
- These crops contain vegetation in the color view, while diagnostic views reject it; therefore, their material name does not isolate the actual visible soil. Measurements are retained, without changing the metric.
- The canonical at 30 sites has fourteen overruns in the reference to 24 sites as in the candidate; the different locations do not allow attributing the cause to this iteration.
- The version is accepted as is by user decision, with these known deviations; the automatic threshold remains unmet. Details: `x64/ForetVolumeComparaisons/qualite_finale/comparaison_p95.json`.

**2026-10-30: the modes, models and launcher removed from the engine.**
- **Removed by commit `3a4508a`;** they remain in the `piste/vegetation-relais-fondu` tag. The game foliage remains alone, active by default.
- **Removed representations:** `hybrid`, volume 64³ at a distance and mesh at a close; `volume`, volumes alone, to isolate their behavior; `impostor`, impostors alone, to compare cost. The volumes used the projection of the eight corners of their box. Both hybrid variants shared the same per plant choice.
- **Retired models:** `-Models photo` kept the imported young fir and jacaranda for comparison; `-Models stylized`, the full crown test. Their trees kept the historical complementary mask at 384–512 pixels, and their impostors stochastic alpha. The bush used the same renderer in all three model sets.
- **Without a catalog,** the Searsia Lucida remained the unique shrub; `-Assets assets/foliage/volume_look_normals` found it. The catalog is now required.
- **The meshes** bilinear folding read raw atlases, loaded on GPU for itself; the active path was already filtering through the hardware.
- **The self-shading force** was set by `MYPLANETENGINE_FOLIAGE_VOLUME`, from 0 to 1; 0 returned the historical lighting for the same geometry.
- **The withdrawn launch:**

```powershell
./tools/lance_planet_foliage.ps1 -Mode hybrid-impostor -Models game
```

- Current executable: `x64/FoliageShrubs/MyPlanetEngine.exe`; previous one remains under `x64/FoliagePlanet/`.
- The launcher uses `tools/lance.ps1` and starts near the reported view, at 1,6 m from the ground; the truncated capture course is assumed to be −115°.
- `-Position` accepts five values: absolute altitude, latitude, longitude, inclination and heading, to resume a flight.
- `-Sun` accepts the latitude and longitude of the sun; default is `20 120`.
- `MYPLANETENGINE_PLANET_FOLIAGE` activates the connection; without this variable, the usual vegetation remains used.
- Isolated prototype and planetary mode cannot be activated together.
- `-Mode hybrid-impostor` is the default launcher; `-Mode hybrid` keeps the relay to volumes.
- `-Mode volume` and `-Mode impostor` remain pure representations, including close-up.
- `-Models game` is the launcher's default; `-Models photo` retrieves the shafts from the previous prototype.
- `-Assets` explicitly chooses the folder of the three species; the engine does not look for a variant in its subfolders.
- `-Volume` chooses the auto-shading strength; it is also shown in the title and statistics.
- `MYPLANETENGINE_PLANET_FOLIAGE_MODELS=game` chooses new models; absent, this variable keeps photo models.
- The pallets `2026-10-27-vegetation-volume.txt` and `2026-10-27-vegetation-planetaire.txt` remain available by `-Tests`.
- The title indicates the set of models, the FPS, the GPU times and the meshes accounts and proxies.
- **The tools removed with them:** `tools/foliage/telecharge.ps1` and `sources.json`, which downloaded the photo models; `tools/foliage/stylise.py`, which built the stylized; the import of the photo models of `tools/foliage/importe.py`.
