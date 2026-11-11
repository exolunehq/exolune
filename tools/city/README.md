**Local generated city production**

- Contract: [generated architecture and settlements](../../docs/spec-ville-procedurale.md).
- Run from the worktree root.
- Use CPython 3.13 with NumPy and Pillow, Blender 5.2, and Shapely 2.1.2.
- This workstation stores optional Python packages in `E:/ExoluneTools/city-python`.
- All generated files belong outside Git.
- The existing ComfyUI and model paths are documented in [local3d](../foliage/local3d/README.md).

<a id="generated-first-draft-building"></a>

**Generated first-draft building**

- Contract and limits: [generated first-draft buildings](../../docs/spec-ville-procedurale.md#generated-first-draft-buildings).
- The form comes from a hosted generator. Install `tripo-cli` and sign in with `tripo login --region ov`; `tripo balance` shows the credits.
- One asset costs 50 credits: H3.1 with detailed geometry. The user makes the input images with ChatGPT; spend no Tripo credits on images.
- The draft is reduced locally, not by Tripo retopology: that service stops at 20,000 triangles and bakes normal and metal-roughness at 1,024 pixels.
- Result URLs expire after five minutes; the CLI downloads at once. Keep every run folder and task ID on E:.

```powershell
tripo make '<clean-view.png>' --model H3.1 -p geometry_quality=detailed -p enable_image_autofix=true -p pbr=true `
  --name '<name>' -o '<run>/draft' --json --yes
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python-exit-code 1 `
  --python tools/city/generated_source.py -- --asset shell_house `
  --model '<run>/draft/tripo-out/<folder>/model.glb' --out '<delivery>/models'
& C:/Python313/python.exe tools/city/integrate_generated.py `
  --base E:/ExoluneAssets/city-series-2026-11-08/candidate-02 --out '<delivery>' --assets shell_house `
  --terrain '<current-terrain>.request.bin'
& C:/Python313/python.exe tools/city/review_native.py --houses --bank '<delivery>/bank' --out '<delivery>/native-houses' `
  --plants E:/ExoluneAssets/understory-2026-11-04/review-bank-generated-ground
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 `
  -Parcours tools/tests/2026-11-10-maison-generee.txt -Ville '<delivery>/bank' `
  -Plantes E:/ExoluneAssets/understory-2026-11-04/review-bank-generated-ground -Resolution fenetre
```

- The clean view comes from ChatGPT: same architecture and camera, plants and outdoor props removed, the furnished interior visible behind the glazing, plain background.
- The user validated this route on 2026-11-11: clean view, H3.1 draft, `generated_source.py`, common cooker. The same day the user validated the local reduction in place of the retopology, for close-range detail.
- `generated_batch.py --out '<delivery>/models' <asset>...` builds several sources from `draft.model_path` in the spec. It retries an obstructed open entrance 2 m apart along the front and records the passing position.
- `generated_source.py` options for assets without a door: no `entry`; `length_m` for a beam segment; `anchor` `top` or `centre`; `align` to square a turned draft to its smallest rectangle.
- A second bank on another terrain reuses the cooked files: copy `library.*`, `materials.json`, `texture*.bin`, `atlas*.bin`, `cook-state.json` and `overrides.json` into a new bank folder, then run `produce.py` with `--bank` and the other `--terrain`. The cook is skipped.
- `bc.py` compresses displayed atlases at cook time; run it alone for its self-check.

<a id="clean-views-and-variants-with-chatgpt"></a>

**Clean views and variants with ChatGPT**

- The agent drives the user's ChatGPT through Claude in Chrome. It needs the user's go-ahead for the session and spends no Tripo credits.
- Crop each board panel at full resolution from the user's downloads. Keep the board hash and the crop hash in `assets/city/generated-buildings.json`.
- Open one new chat per image; three tabs run in parallel. Attach the panel through the hidden file input named "Joindre des photos", then send the prompt.
- Cleaning prompt:

```text
Edit this image. Keep the building exactly the same: same architecture, shapes, proportions, camera angle,
materials, colours, glazing, and the furnished, lit interiors visible behind the glass. Remove every person, tree,
plant, flower, pot, planter, outdoor furniture, pond, waterfall, rock, path, lamp, label and text, including the
plants on the balconies and terraces. Show the whole building isolated on a plain light grey background with a margin
around it, standing on flat light grey ground. Landscape format, at the highest resolution you can produce.
```

- A new variant uses the same frame: name the family's language (shells, ribbons, solar roofs, timber fins), state what changes (massing, storeys, wings, patio, cantilever), and ask for the same isolated, interior-visible view.
- The result is ready when an image whose alternative text starts with "Image générée" appears, after about a minute. ChatGPT returns about 1,700 × 900 pixels, larger than a board panel.
- Fetch the image's blob in the page and download it. Chrome keeps the file as `.crdownload` in the downloads folder, but complete: copy it to `inputs/<asset>-clean.png` and open it once to check it.
- Review each clean view against its panel before spending credits on a draft.
- Review the edited image against the board before generating. It must keep shapes, proportions and camera.
- Use `--dry-run --json` on `tripo make` to validate a request and read its credit estimate without spending.
- Pin the board, edited image, draft and retopology hashes and task IDs in `assets/city/generated-buildings.json`.
- Measure `yaw_degrees`, `height_m` and the `entry` rectangle on an orthographic front view of the mesh. Take the scale from a human-scale feature such as the door.
- `generated_source.py` refuses a blocked standing approach and an entrance rectangle that matches no door surface. An entrance without a separable leaf, such as a patio or a glazed lobby, sets `"open": true` in its `entry`: the tool fits a glazed leaf, a pull and a threshold instead.
- A draft made from a view with visible interiors sets `"surface": false`: its glazing is painted with rooms, which the class reading takes for timber or shell.
- The atlas names materials and is not displayed; see [generated shell surfaces](../../docs/spec-ville-procedurale.md#generated-shell-surfaces).
- The shared rule sits under `surface` in `assets/city/generated-buildings.json`: reference colours, allowed orientations, `mullion_m` and `storey_m`. `integrate_generated.py` copies it into the recipe.
- Review the classes before cooking. This writes the atlas beside its classes; without arguments the tool runs its self-check:

```powershell
& C:/Python313/python.exe tools/city/surface_classes.py --source '<delivery>/models/shell_house/master.glb' --preview '<review>/classes.png'
```

- Review near and far, by day and at dusk: `tools/tests/2026-11-10-maison-de-pres.txt`.
- Reject foliage-obstructed cameras. `review_native.py --poses <file>` captures other placements of the same model.
- A bank placed on another terrain export floats or sinks. Export the terrain with the current executable first; see [probe the planet](#probe-the-planet).
- Keep a furnished room as a [baked interior](../../docs/spec-ville-procedurale.md#baked-interiors), never as geometry. Bake it from a draft that shows it, then pin the image hash and the window box under `interiors`:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python-exit-code 1 `
  --python tools/city/interior_bake.py -- --draft '<draft>/model.glb' --box '<room>.box.json' `
  --out '<delivery>/interiors/<asset>-<room>.png'
```

- The box holds `origin`, `u`, `v` and `depth` in the draft's imported space; `u x v` faces outwards. A depth map along the facade normal finds the window. `-- --check` runs the tool's self-check.

<a id="integrate-a-neutral-series-into-the-city"></a>

**Integrate a neutral series into the city**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Build -NoLaunch
& C:/Python313/python.exe tools/city/integrate_series.py `
  --series E:/ExoluneAssets/architecture-series-2026-11-08/series-v3 `
  --base-bank E:/ExoluneAssets/house-finish-2026-11-08/candidate-17/bank `
  --out '<fresh-external-output>'
```

- `assets/city/series-runtime.json` maps the four houses, two civic sources and two greenhouses to city roles.
- `prepare_series_runtime.py` verifies the immutable neutral GLB and retains its exact lineage.
- Reduce only dense structural surfaces to a 54,000-triangle LOD0 target; keep fitted panes, entries and steps intact.
- Transfer the original surface normals and check closure and bidirectional sampled surface deviation before export.
- Apply the shared ceramic, timber, teal, stone and glazing palette with metric UVs and common material detail.
- Describe actual door leaves, opening controls and thresholds. Place the approach datum in front of the closed leaf and its frame; independently ray-test the standing approach.
- Preserve the other bank sources by exact override. The common cooker validates copied caches and generates five LODs, material arrays and source-derived ambient visibility.
- The common planner selects available house families, then checks footprints, terrain support and pedestrian access over four seeds.
- Integration fails if any mapped variant is absent from the review city. Art and performance acceptance stay open.
- This command is CPU-only. Wait until other GPU jobs have finished before native review or the requested visible launch.

```powershell
& C:/Python313/python.exe tools/city/review_native.py --series `
  --bank '<output>/bank' --out '<output>/native-review' `
  --plants E:/ExoluneAssets/understory-2026-11-04/review-bank-generated-ground
& C:/Python313/python.exe tools/city/verify_delivery.py --series --out '<output>'
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 `
  -Parcours tools/tests/2026-11-08-ville-serie.txt -Ville '<output>/bank' `
  -Plantes E:/ExoluneAssets/understory-2026-11-04/review-bank-generated-ground -Resolution fenetre
```

- Inspect all twelve native captures before delivering this route. Record an image-bound judgement for every view.
- The review includes every mapped model, two near entrances and two city-scale views.
- Source and shader hashes, CPU validation and native capture identity must match the launched bank.
- The city still uses its coarsest mesh at distance; no city impostor, HLOD or performance acceptance is implied.
- If a camera is inside natural foliage, review other actual placements of that model. Do not remove vegetation for a clearer screenshot.
- `review_native.py --poses <file>` accepts `library` and `scene` SHA-256 values plus explicit `views` tuples, and retains that camera file with the captures.
- `assemble_review.py --selection <file> --out <fresh-directory>` selects inspected views from the same exact bank, executable, shaders and textures. The ordered selection maps each output label to `{ "directory": "<review>", "view": "<capture-name>" }`.
- Assembly verifies the native BMP hash and PNG pixel identity, and retains each original capture protocol. It does not retouch or reframe pixels.
- Verify a curated route with `verify_delivery.py --series --review-dir native-selected --out <output>`.
- The current twelve-view route selects eleven first-pass views and the unobstructed sixth low-house placement. Original and rejected captures remain external.

**Generate a master**

```powershell
& E:/ComfyUI/.venv/Scripts/python.exe tools/city/neural.py `
  --reference '<user-board.png>' --out E:/ExoluneAssets/architecture/house `
  --name shell_house --brief '<architectural brief>' --references-only
```

- Review the isolated reference before continuing without `--references-only`.
- `--prepared-reference <image>` reuses the exact isolated image.
- `--faces` specifies a proposed neural reduction budget, not an acceptance guarantee.
- `--subject vehicle --voxel-resolution 512` uses vehicle isolation and the native first TRELLIS shape stage.
- `--surface-mode closed` resamples a closed opaque vehicle before reduction. It is unsuitable for open architectural shells.
- Reject torn surfaces even if the graph succeeds; inspect both the master and its reduced GLB.
- `normalize.py --anchor top --long-axis-x` aligns the horizontal principal axis and places the vehicle below its suspension datum.
- Verify the normalized width against lane spacing; axis-aligned bounds of a diagonal reconstruction are not its actual width.
- `finish_vehicle.py` retains the mesh and bounds the neural normal/metallic/roughness response; this does not repair malformed geometry.
- `neural.py --backend pixal3d --prepared-reference <image>` compares a second installed backend on a pinned reference.
- `--minimum-free-vram-gib` records an explicit inference admission budget; its default is 7.25 GiB. `--wait-gpu` waits without closing another session.
- The architecture comparison uses 6.5 GiB admission with ComfyUI's dynamic model offloading. This is not a performance result or a guarantee against memory exhaustion.
- Consult `docs/recherche-generation-architecture.md` before selecting a new whole-building route.
- Neural references, failed candidates and promoted masters remain separate artifacts.
- Architectural reduction bypasses the woody solid remesher.
- Large raw meshes can still exceed available VRAM; retain the failure and the raw source.
- `normalize.py --source <glb> --out <folder> --height <metres> --id <id>` runs inside background Blender.
- `review.py <glb> --out <folder>` also runs inside background Blender and renders on the CPU.
- `review.py --clay` isolates geometry from material quality; those CPU images are not native-render acceptance evidence.
- `reduce_neural.py --source <dense.glb> --out <diagnostic> --triangles 28000 --height 7.7` attempts CPU QEM after recovering coincident adjacency. Inspect `within_triangle_budget`; a requested ratio does not guarantee the target is reachable.
- Its optional `--voxel-resolution 256|384|512` is a destructive diagnostic for closed volume reconstruction. Leave the default zero for thin architectural shells; the tested 384 alternative erased envelopes despite meeting the triangle budget.
- The CPU recovery retains the dense source and records incomplete PBR processing. It does not promote a candidate to the city bank.
- `author.py --recipe assets/city/solarpunk.json --out <models>` creates the procedural sources.
- An override JSON maps an asset ID to a generated, normalized `master.glb` with its adjacent `source.json`.
- `produce.py --references <folder>` fingerprints the supplied boards without copying images into Git.

**Local architecture method study**

- Current decision and source gates: [architecture methods](../../docs/recherche-generation-architecture.md).
- Evidence: `E:/ExoluneAssets/architecture-2026-11-08`; exact revisions, package snapshots and model hashes stay with the runs.
- Pixal uses the native ComfyUI graph. PartCrafter uses its official local implementation in an isolated Python 3.11 environment.
- LATO.2 uses the isolated Python 3.12 runner installed by ComfyUI-LATO2. It does not transfer UVs or PBR maps.
- Review the cleaned 2D reference before reconstruction. Keep its original and cleaned hashes separately.
- `render_multiview.py` runs in background Blender and writes four calibrated clay views plus `rig.json`.
- Views rendered from a previous reconstruction are consistency controls, not independently authored unseen sides.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' -b `
  --python tools/city/render_multiview.py -- '<source.glb>' --out '<views>' --clay
& E:/ComfyUI/.venv/Scripts/python.exe tools/city/architecture_study.py `
  --mode pixal-multiview --rig '<views>/rig.json' --out '<new-pixal-run>' --resolution 512 --seed 42
& E:/ComfyUI/.venv/Scripts/python.exe tools/city/architecture_study.py `
  --mode clean-reference --reference '<original.png>' --out '<new-reference>' --seed 419308
& E:/ComfyUI/.venv/Scripts/python.exe tools/city/architecture_study.py `
  --mode prepare-partcrafter --reference '<reviewed-clean.png>' --out '<prepared-reference>'
& E:/ExoluneTools/PartCrafter/.venv/Scripts/python.exe tools/city/partcrafter_study.py `
  --reference '<prepared.png>' --out '<new-parts-run>' --parts 6 --seed 42 --decode-depth 9
& E:/ComfyUI/custom_nodes/ComfyUI-LATO2/envs/lato2/Scripts/python.exe tools/city/lato_study.py `
  --source '<reviewed-part.glb>' --out '<new-lato-run>' --vertices 5000 --seed 42
```

- Run GPU stages sequentially and unload the owned Comfy models before external inference. Do not stop unrelated sessions.
- The API endpoint defaults to `http://127.0.0.1:8190`. Executed native graphs and canvases are saved with Pixal/image outputs and in ComfyUI's `Exolune/local3d` workflows.
- `lato_study.py --azimuth 55 --elevation 15` changes only the conditioning camera. Inspect the saved conditioning view; a roof view can hide important apertures.
- LATO outputs retain `raw.glb`, wrapper-rebuilt `mesh.glb`, the edge-logit dump and an orientation-only `oriented.glb` control.
- Orientation finishing checks unchanged positions and undirected faces. It can still fail winding consistency; inspect the report.
- For the classical control, run `reduce_neural.py` in Blender with `--backend partcrafter --triangles 28000 --minimum-part-triangles 500`.
- The optional reservation redistributes the existing total budget. It does not increase the total request or guarantee a minimum actual output count.
- Run `inspect_geometry.py <mesh.glb> --out <report.json>` with the PartCrafter Python, which contains trimesh.
- Render reduced output with `review.py --views quarter,back,top,street`; use a metric source for its standing street camera.
- Keep source defects, reduction defects and material defects distinct. Do not cook a failed source merely because it fits the triangle budget.

<a id="original-reference-neutral-master"></a>

**Original-reference neutral master**

- This isolated command authors one house against the original user board. The large upper-left exterior is the canonical view.
- It uses directed surfaces in background Blender, not neural output vertices. It neither invokes ComfyUI nor modifies the active city bank.
- `C:/Python313/python.exe` needs NumPy and the existing Shapely environment at `E:/ExoluneTools/city-python`.
- Use a new external output directory to retain each reviewed iteration.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Build -NoLaunch
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' `
  --background --factory-startup --threads 6 --python-exit-code 1 `
  --python tools/city/reference_house_master.py -- `
  --recipe assets/city/shell-house-reference-master.json `
  --reference 'C:/Users/etien/Downloads/01 — Maison à coques habitées-1.png' `
  --out '<new-external-output>' --views hero,front,side,back,porch
```

- `--preview` renders at 1,000 × 700 and 16 samples. The full review uses 1,600 × 1,120 and 48 samples. Both use Cycles CPU.
- `master.blend` and `master.glb` contain the unreduced source without the studio. `neutral-review.blend` includes the stage, lights and hero camera.
- `source.json` records topology, subtraction volumes, lineage, exact hashes and the unaccepted artistic status. `recipe.json` and `authoring/` retain the recipe and authoring code.
- Boolean volume bounds reject a cut which silently removes the wrong region. Tangent estimation uses a physical 0.12 m arc; initial cut cleanup uses 0.01 mm.
- Triangulate before the final topology gate. Export-sliver cleanup uses 0.1 mm; a collapsed sliver edge cannot move either endpoint by more than 0.1 mm. Verify the reimported GLB with material primitives rejoined per object.
- Glazing remains vertical and planar per bay. Its head and sill follow measured intersections with the structural mesh.
- Save a judgement for every rendered view beside the source; bind it to the image hash. Neutral art review must precede reduction and texture work. The user-requested exploratory series below may compare variants while production art acceptance remains open.
- Do not interpret the source triangle count as an approved game budget. The common production chain remains a later stage after shape acceptance.

<a id="neutral-architecture-series"></a>

**Produce the neutral house and public-building series**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Build -NoLaunch
& C:/Python313/python.exe tools/city/produce_series.py `
  --recipe assets/city/neutral-series.json --out '<new-external-series-directory>'
```

- This runs entirely in background Blender processes using CPU Cycles. It does not start Exolune, use the GPU or benchmark performance.
- The recipe pins the original house control and the three user boards. Preserve these external inputs before running; `source-inputs/` retains copies for the series.
- Four houses include the retained master/control and three new variants. Two civic buildings and two greenhouses come from new connected parametric masters.
- The command runs source topology gates, exports GLB, reimports it, audits it again, and renders three views per model.
- `--only house_low` limits an iteration. `--stages author`, `--stages review` and `--stages report` separate stages.
- `--resume` continues unchanged sources. A different recipe or author hash requires a new external iteration directory.
- Each source retains its recipe, exact upstream mesh/reference/tool hashes and authoring snapshot. Reporting verifies those immutable snapshots; author-stage resume additionally requires the current tools to match.
- House deformations preserve glazing planarity and transform normals analytically. Both positive local orientation and bounded junction shear are required.
- Civic side openings are real cuts with fitted glazing. End bays meet the actual jambs, and stair/gallery guards share the access geometry. Greenhouse frames have real panel apertures; their length and bay count vary together.
- Approach stairs follow the terrace boundary. Check this in the entrance view instead of relying only on object topology.
- `series.json` records exact counts, dimensions and capture hashes. `index.html` links the actual renders, GLBs and Blender sources.
- Inspect every hero, back and entrance view. Write one concrete judgement per view in an external JSON object of the form `{ "house_source": { "hero": "...", "back": "...", "entry": "..." }, ... }`.

```powershell
& C:/Python313/python.exe tools/city/record_series_review.py `
  --out '<series-directory>' --notes '<external-visual-judgements.json>'
```

- The review recorder rejects missing notes and changed source/capture hashes. It records inspection without granting user, production-art or performance acceptance.
- Source masters may exceed the game's 60,000-triangle LOD0 limit. The series command deliberately stops before textures, reduction, LODs, placement and native promotion.
- Use the common producer only after source design review. A neutral source series is not a runtime-ready bank.

<a id="finish-the-reviewed-shell-house"></a>

**Reproduce the continuous-shell technical control**

- **Art gate:** the user rejected the separate-loft junctions and then the continuous-domain pair's fidelity to the original design. The command below reproduces that technical control. Do not use its authoring recipe as an accepted production house or keep multiplying its variants.
- Follow the revised [method decision](../../docs/recherche-generation-architecture.md) for the next master. Shared cooking, source provenance and native review remain reusable.

```powershell
& C:/Python313/python.exe tools/city/finish_house_pair.py `
  --source 'E:/ExoluneAssets/architecture-2026-11-08/partcrafter-clean-six/parts.glb' `
  --reference 'E:/ExoluneAssets/architecture-2026-11-08/clean-reference/reference/f180f07b187b7190/image.png' `
  --base-bank '<reviewed-city>/bank' --out '<new-external-output>' `
  --terrain 'E:/ExoluneAssets/city-2026-11-07-expansion/terrain.request.bin' `
  --review --plants 'E:/ExoluneAssets/understory-2026-11-04/review-bank-generated-ground'
```

- This command authors both sources, pins unchanged city sources, reuses verified caches, cooks the bank and checks four placement seeds.
- `--review` adds a Release build and twelve hidden native house captures. It does not benchmark performance.
- `record_art_review.py --routes native-houses` records one judgement per exact image.
- `verify_delivery.py --houses` verifies the bank and writes `tools/tests/2026-11-08-maison-variantes.txt`.
- Run the source stage alone while iterating on a profile:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' `
  --background --factory-startup --threads 5 --python-exit-code 1 `
  --python tools/city/continuous_house.py -- `
  --recipe assets/city/shell-house-continuous.json --out '<new-output>/models' `
  --source 'E:/ExoluneAssets/architecture-2026-11-08/partcrafter-clean-six/parts.glb' `
  --reference 'E:/ExoluneAssets/architecture-2026-11-08/clean-reference/reference/f180f07b187b7190/image.png'
```

- The recipe pins both input hashes and the 40,000-triangle per-house ceiling.
- Start with `--diagnostic --asset shell_house` to inspect the continuous structure before detailing.
- One triangulated domain contains both wings, the entrance and their supporting arch, with four true apertures.
- The front surface, rear taper and roof camber share that domain. Shared vertices preserve the junctions.
- Equal-angle bevel offsets preserve short grid intersections without folding the lip.
- Both houses use matched glazing, continuous seals and fitted opening systems.
- PV laminates clip the actual roof triangles. A separately sampled curved patch can cross its support between samples.
- `surface_contacts.py` checks declared roof/PV interfaces over projected triangle intersections after reduction. LOD0 stays unchanged; reduced overlays receive at most 0.4 pixels and 0.15 m of outward compensation, or retain the preceding accepted LOD.
- Source metadata hashes invalidate cooking when these interface contracts change.
- This is directed surface reconstruction from reviewed design evidence. No neural vertices are retained in the finished masters.
- The second recipe changes upper-wing extent, crown height, overhang, bay rhythm and sun fins. All openings and structural boundaries share the deformation.
- Export retains `source.blend`, `master.glb`, exact lineage and the independent entrance-clearance audit.
- Pin both new masters in an override file for `produce.py`. Keep the other city masters pinned to their reviewed source paths.
- The common producer checks manufactured topology, cooks PBR arrays and five bounded LODs, then regenerates terrain support and access.
- Use `review_native.py --houses --bank <bank> --out <review>` for matched front, rear, entry, underside and distant views of both placed houses.
- Add `--house-lods` in a separate capture directory for six intermediate LOD witnesses.
- After shared material changes, add `--details --only collective_entry,train_fittings` in a regression directory.
- For the current candidate, `record_art_review.py --routes native-houses,native-lods,native-regression` binds all twenty judgements before `verify_delivery.py --houses` checks delivery.
- Judge each capture before selecting a bank for user review. Counts alone do not establish art or performance acceptance.
- `finish_shell_house.py` retains the superseded separate-loft experiment and shared surface helpers. Do not use its authoring command for a new production house.

<a id="probe-the-planet"></a>

**Probe the planet**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Build -NoLaunch
'-11.04 49.7776 513 2' | Set-Content E:/ExoluneAssets/city-site.request -Encoding ASCII
$env:MYPLANETENGINE_CITY_PROBE='E:/ExoluneAssets/city-site.request'
& ./x64/Release/MyPlanetEngine.exe
Remove-Item Env:MYPLANETENGINE_CITY_PROBE
```

- This is a hidden terrain export, not a rendered performance measurement.
- Use a clean launcher environment and record the selected planet seed.
- The result is `city-site.request.bin`.
- A terrain change requires another probe and layout.
- The former anchor, 49.784, now holds a river. The anchor above lies about 700 m west.

<a id="place-the-city-on-a-hill-site"></a>

**Place the city on a hill site**

```powershell
'-10.955 63.749 1025 20' | Set-Content E:/ExoluneAssets/city-hills-2026-11-11/site-b.request -Encoding ASCII
$env:MYPLANETENGINE_CITY_PROBE='E:/ExoluneAssets/city-hills-2026-11-11/site-b.request'
& ./x64/Release/MyPlanetEngine.exe
Remove-Item Env:MYPLANETENGINE_CITY_PROBE
python tools/city/site_search.py E:/ExoluneAssets/city-hills-2026-11-11/site-b.request.bin
```

- The survey covers 20 km at 20 m. `site_search.py` ranks 1 km windows and prints each one's probe request.
- Probe the chosen window at 513 × 2 m, as above.
- Read the river bed in the export and state the water surface beside it: `<export>.bin.json` holding `{"water_level_m": 324.0}`. The engine does not export river water yet.
- Copy the generated sources into `<out>/models`, then integrate on the new terrain:

```powershell
python tools/city/integrate_generated.py `
  --base E:/ExoluneAssets/city-tripo-2026-11-11/delivery-01 `
  --out E:/ExoluneAssets/city-tripo-2026-11-11/delivery-02-collines `
  --assets patio_house,shell_tall,shell_duplex,shell_crescent,ribbon_apartments,ribbon_tall,ribbon_garden_steps,ribbon_crown `
  --terrain E:/ExoluneAssets/city-hills-2026-11-11/terrain.request.bin
```

- The ground rules are in the [city spec](../../docs/spec-ville-procedurale.md#earthworks): earthwork pads, stepped paths, water margins.
- `grading.py` grades the pads into the relief and writes `grading.bin`. Run it alone for its self-check.
- `layout.json` records each building's `pad`, every pad under `earthworks`, the step count, the cables and the ground policy.
- `foundations.py` builds steps and cables into the ground mesh. Run it alone for its self-check.
- A site without the guideway gets the cable car; the spaceport and field terraces need `landing_pad`, `space_terminal` and `growing_bed` in the kit. A new generated asset joins the recipe through `integrate_generated.py`.
- A site wider than 1 km, or whose 1 km spine is not level, lays the braid along a contour (`settlement.contour_spine`, `masterplan.braid_along`); `contourpy` finds the contour.
- A site's chosen places go in its sidecar, `<export>.bin.json`: `spine_region` `[x0, y0, x1, y1]`, `farmland` `[{"centre": [x, y], "radius": r}]`, `cliff` `{"foot": [x, y], "top": [x, y]}`, all in the export's frame. The 3 km hill site states all three.
- `regional_export` names a wider export of the same anchor, seed and frame; `Terrain.height` falls back on it beyond the site. The guideway's branches follow it to its edge. Probe it like the site, e.g. `'-10.996997 63.681051 1025 16'`.
- The extended hill city reuses a cooked kit: copy `library.*`, `materials.json`, `texture*.bin`, `atlas*.bin`, `cook-state.json` and `overrides.json` into the new bank, then:

```powershell
'-10.999018 63.684025 1025 2' | Set-Content E:/ExoluneAssets/city-hills-2km-2026-11-11/terrain.request -Encoding ASCII
$env:MYPLANETENGINE_CITY_PROBE='E:/ExoluneAssets/city-hills-2km-2026-11-11/terrain.request'
& ./x64/Release/MyPlanetEngine.exe
Remove-Item Env:MYPLANETENGINE_CITY_PROBE
python tools/city/produce.py --recipe E:/ExoluneAssets/city-tripo-2026-11-11/delivery-05/recipe.json `
  --overrides E:/ExoluneAssets/city-tripo-2026-11-11/delivery-05/overrides.json `
  --out E:/ExoluneAssets/city-tripo-2026-11-11/delivery-06 --bank E:/ExoluneAssets/city-tripo-2026-11-11/delivery-06/bank `
  --terrain E:/ExoluneAssets/city-hills-2km-2026-11-11/terrain.request.bin
```

- The 3 km site with its regional export lives on G: (E: is full). Probe the region, state it in the site's sidecar as `regional_export`, then produce from a copy of the previous delivery's `models`, `recipe.json`, `overrides.json` and cooked bank files:

```powershell
'-10.996997 63.681051 1025 16' | Set-Content G:/ExoluneAssets/city-hills-16km-2026-11-11/terrain.request -Encoding ASCII
$env:MYPLANETENGINE_CITY_PROBE='G:/ExoluneAssets/city-hills-16km-2026-11-11/terrain.request'
& ./x64/Release/MyPlanetEngine.exe
Remove-Item Env:MYPLANETENGINE_CITY_PROBE
python tools/city/produce.py --recipe G:/ExoluneAssets/city-tripo-2026-11-11/delivery-08/recipe.json `
  --overrides G:/ExoluneAssets/city-tripo-2026-11-11/delivery-08/overrides.json `
  --out G:/ExoluneAssets/city-tripo-2026-11-11/delivery-08 --bank G:/ExoluneAssets/city-tripo-2026-11-11/delivery-08/bank `
  --terrain G:/ExoluneAssets/city-hills-3km-2026-11-11/terrain.request.bin
```

- Keep the older deliveries on E:: their `overrides.json` name sources inside them.

**Produce and review**

```powershell
& C:/Python313/python.exe tools/city/produce.py `
  --recipe assets/city/solarpunk.json `
  --out E:/ExoluneAssets/city-2026-11-07-detail `
  --terrain E:/ExoluneAssets/city-2026-11-07-expansion/terrain.request.bin `
  --bank E:/ExoluneAssets/city-2026-11-07-detail/bank `
  --overrides E:/ExoluneAssets/city-2026-11-07-detail/overrides.json `
  --review --plants E:/ExoluneAssets/understory-2026-11-04/review-bank-generated-ground
```

- Omit `--overrides` for the entirely procedural control kit.
- `--assets-only` separates kit production from placement and native review.
- The cooker maintains fingerprinted per-model caches under the bank.
- `masterplan.py --out <folder>` draws three planning proposals.
- `planboard.py --layout <bank>/layout.json --out <file.png>` draws the actual supported layout.
- `review_native.py --only station,path_junction` limits an intermediate functional review.
- `review_native.py --details --bank <bank> --out <review>` captures twelve entrances, functional fittings and structural variants at close range.
- `details.py` authors opening systems, service panels and mechanical connections, with semantic source audits.
- It also probes the standing approach at three widths and three heights. Cooking cannot validate a blocked entrance.
- The layout retains its terrain-source path and hash so close capture cameras can stand above manufactured entrances.
- `refine_neural.py` adds metric entrance fittings to the pinned neural house without replacing or remeshing its shell.
- `manufacturing.py` builds connected profiles and matched interfaces; `audit_manufacturing.py` gates their imported topology before cooking.
- Small vents, sockets and control markings use shared generated PBR sheets. They do not require separate meshes.
- `verify_delivery.py --out <production directory>` checks both native routes against exact production hashes and writes the dated review palettes.
- `record_art_review.py --out <production directory> --notes <judgements.json>` binds one explicit judgement per view to its exact capture and protocol. Its output keeps artistic and performance acceptance open.
- Native room shading adds exterior parallax behind windows; it does not create visitable rooms.
- `production.json` identifies each source method and fingerprint.
- `library.json` contains exact LOD counts, sampled deviations and retained-level fallbacks.
- `layout.json` contains the approved density plan, protected habitat corridors, footprints, access paths, support ranges and rejected candidates.
- `plan.svg` is a diagnostic plan, not a beauty rendering.
- `validation.json` covers deterministic placement, collisions, access and invalid sites.
- It also enforces 60,000 LOD0 triangles per building/infrastructure model and 12,000 per furniture model.
- `native-review/functional.json` fingerprints the executable, shaders, bank and textures.
- The dated palette is copied from the final review route after checking the views.
- No tool in this command marks artistic or performance acceptance.

**Native formats**

- `CITYLIB1` version 3: model names, bounds, LOD index ranges, 48-byte material records, 40-byte vertices including ambient visibility and 32-bit indices.
- `CITYTEX1`: square RGBA8 mip chains, layer-major; colour is sRGB, normal and metal/roughness are linear.
- `CITYATL1`: displayed draft atlases, block compressed, layer-major mip chains: `atlas0` BC1 sRGB colour, `atlas1` BC5 normal (X, Y), `atlas2` BC1 linear metal-roughness.
- `CITYSCN1` version 4: planet seed, anchor, 256 × 256 occupancy bits, 24-byte placements, manufactured ground triangles and the walkable index count. Step risers and cables follow the walkable triangles.
- `CITYPAD2` (`grading.bin`): pad and index counts, default talus slope, knee, edge rounding, index origin and cell; per pad, centre, yaw, its own talus slope, half extents, corner radius and level; 32 × 32 cells (first entry, count); 16-bit pad indices. `CITYPAD1` stored the frame's cosine and sine and one slope for all; the engine still loads it. Optional: a bank without it keeps the natural relief.
- `CITYCOR1` (`corridor.bin`): segment count, half width (m), then each segment's start and end in the city frame; at most 192. The vegetation keeps clear of it beyond the land grid. Optional.
- `CITYGRD1`: planet seed, anchor, grid spacing and floating-point ground samples.
- Native readers bound dimensions and reject truncated payloads.
- Legacy library v1/v2 and scene v1/v2 remain readable; missing ambient visibility becomes 1, and old mask cells expand losslessly.
- The city loader is opt-in through `-Ville`; an ordinary game launch retains its existing behavior.
