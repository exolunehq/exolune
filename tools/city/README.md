**Local generated city production**

- Contract: [generated architecture and settlements](../../docs/spec-ville-procedurale.md).
- Run from the worktree root.
- Use CPython 3.13 with NumPy and Pillow, Blender 5.2, and Shapely 2.1.2.
- This workstation stores optional Python packages in `E:/ExoluneTools/city-python`.
- All generated files belong outside Git.
- The existing ComfyUI and model paths are documented in [local3d](../foliage/local3d/README.md).

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

**Probe the planet**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Build -NoLaunch
'-11.04 49.784 513 2' | Set-Content E:/ExoluneAssets/city-site.request -Encoding ASCII
$env:MYPLANETENGINE_CITY_PROBE='E:/ExoluneAssets/city-site.request'
& ./x64/Release/MyPlanetEngine.exe
Remove-Item Env:MYPLANETENGINE_CITY_PROBE
```

- This is a hidden terrain export, not a rendered performance measurement.
- Use a clean launcher environment and record the selected planet seed.
- The result is `city-site.request.bin`.
- A terrain change requires another probe and layout.

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
- `CITYSCN1` version 3: planet seed, anchor, 256 × 256 occupancy bits, 24-byte placements and manufactured ground triangles.
- `CITYGRD1`: planet seed, anchor, grid spacing and floating-point ground samples.
- Native readers bound dimensions and reject truncated payloads.
- Legacy library v1/v2 and scene v1/v2 remain readable; missing ambient visibility becomes 1, and old mask cells expand losslessly.
- The city loader is opt-in through `-Ville`; an ordinary game launch retains its existing behavior.
