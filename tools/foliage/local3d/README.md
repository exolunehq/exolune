# Local vegetation production

**Complete native chain**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Build -NoLaunch
& C:/Python313/python.exe tools/foliage/local3d/produce.py `
  tools/foliage/local3d/examples/oak-production.json `
  --out E:/ExoluneAssets/oak-production --watch --comfy-url http://127.0.0.1:8190
```

- This command includes requested performance and quality benchmarks; use it only when the user requests those checks.
- All renders are hidden; no window or focus change is needed.
- `--watch` retries pending GPU work for 120 minutes; omit it for one checkpointed attempt.
- The command preserves a reviewed master, cooks native materials, roots, wind, seven LODs and a multiview impostor, checks native captures, then compares performance and canonical quality.
- Read `production-report.json` or `production-report.md` under the output directory.
- `--report-only` refreshes that report from completed evidence without inference or rendering, including while the watcher is running.
- Pending or failed checks prevent `production_ready`; diagnostic images are labelled separately from natural renders.
- Exit codes: 0 production-ready, 1 execution error, 2 failed acceptance, 3 pending acceptance. A completed benchmark alone cannot produce code 0.
- The reviewed source is the 39,933-triangle surface oak, SHA-256 `c11c61b00d093c57025ec4a7c7168e6431e198d7f11a329c6756762813e67458`.
- Current spreading-oak triangles: 53,423 / 33,741 / 29,097 / 19,035 / 14,391 / 6,269 / 2,866.
- Preserve source wood at L1–L4 and add bounded L0 curvature and curved individual leaves through L2.
- Native branch loops in the source remain an art rejection; the offline reference is not production approval.
- The new tropical review uses a radial hybrid candidate; it has one master and five role aliases, not five species.
- Superseded five-level budgets: docs/log/spec-pipeline-creation3d-historique.md.
- The CPU coverage sheet compares all cooked levels from 36 directions at 128 pixels; it records lost/added coverage and pixel deviations. This unlit probe supplements native review without declaring artistic acceptance.
- `source` names an existing master and hash. For a new plant replace it with `authoring_recipe`, a path relative to the production recipe, and remove `cook.adopt_catalogue`.
- `examples/oak-surface.json` preserves the selected surface settings; `examples/oak.json` demonstrates the alternative fuller crown.
- The authoring recipe accepts text alone or an optional image. A new master still requires art review.
- The existing witness cook may be adopted only when source, settings and cooker hashes match.
- Verified runtime files share an immutable content store on E:; each recipe retains its own catalogue and report.
- The current cooker tests one woody broadleaf in five broadleaf roles. Other plant families require a suitable placement/cook preset before claiming acceptance.
- Identical logical roles share GPU resources; the default game catalogue is not replaced by this comparison.
- Functional captures may share the GPU. Performance samples stop when another engine or ComfyUI inference starts; other sessions are never stopped.
- Paired performance uses A/B/B/A, seven views, 1080p, clouds and sea enabled, 32 warmup frames and 128 samples per view and round.
- `--adopt-measurements <previous folder>` reuses completed performance rounds only after checking all frozen executable, shader and catalogue hashes and the capture protocol. Quality verdicts are never adopted.
- Triangle submission counters describe one geometry pass; the engine measures both depth and material work. Payload bytes count unique vegetation resources, not total game VRAM.
- Quality uses the official six-material site selection and metrics at 30 places, 1280x720, and `--before tools/banc_qualite_reference.json`; missing metrics and p95 regressions above 10% remain failures.
- Site selection and complete baseline quality captures are shared across species only when executable, shaders, baseline, ground scans and quality protocol hashes match; each candidate keeps its own captures.
- Native art acceptance is an explicit `visual-acceptance.json` in the review directory: `accepted`, `reviewer`, `notes`, and `inputs_sha256` of that directory's `inputs.json`.
- Detailed contract: `docs/spec-pipeline-creation3d.md`. Current manual route: `tools/tests/2026-11-03-vegetation-render.txt`.

**Authoring stage**

- A working local broadleaf-tree recipe, starting with a mature oak.
- Text art brief and optional image → FLUX references → TRELLIS.2 wood → reduced textured geometry → independent leaf cutouts on supported shoots → GLB.
- Pixal3D is an alternative geometry backend using the same output contract.
- ComfyUI performs neural generation and material baking.
- Blender runs the deterministic assembly and CPU review without opening its interface.
- Generated assets, references, model weights and logs stay on E:.
- Artistic acceptance and Exolune runtime integration are separate steps.

**Requirements**

- Tested installation: ComfyUI 0.43.0, Python 3.13.1, torch 2.11.0+cu128, RTX 4070 Ti 12 GiB and Blender 5.2.1 LTS.
- Use the working ComfyUI virtual environment, including NumPy and Pillow.
- Native nodes only; no custom-node installation or cloud API is required.
- The CLI defaults to port 8188; this review uses a dedicated server on port 8190.
- Pass `--comfy-url http://127.0.0.1:8190` to authoring, library and production runners.
- Keep weights under E:/ComfyUI_Models/models and load their explicit model-path configuration.
- Verify required diffusion, text-encoder and VAE names in ComfyUI object_info before queuing inference.
- Start ComfyUI with `--disable-auto-launch --disable-all-custom-nodes --disable-api-nodes --extra-model-paths-config <absolute path to extra_model_paths.yaml>`.
- The supplied configuration includes the text encoder directory as well as the 3D models.
- `HF_HOME=E:/hf-cache`, `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` keep model loading local.
- The runner checks required files; it does not download weights or change the working environment.
- It also verifies that the running server's native loader choices include every required model.

| Directory under `E:/ComfyUI_Models/models` | Required file |
|---|---|
| diffusion_models | flux3-image-klein-int8-convrot.safetensors |
| text_encoders | qwen3vl_4b_int8_convrot.safetensors |
| vae | flux2-vae.safetensors |
| diffusion_models | trellis_2_int8_convrot.safetensors |
| vae | trellis_2_shape_vae_bf16.safetensors |
| vae | trellis_2_texture_vae_bf16.safetensors |
| clip_vision | dino_v3_L_naf_fp32.safetensors |
| background_removal | birefnet.safetensors |
| diffusion_models, Pixal3D only | pixal3d_int8_convrot.safetensors |
| geometry_estimation, Pixal3D only | moge_2_vitl_normal_fp16.safetensors |

**Run from the repository root**

```powershell
& E:/ComfyUI/.venv/Scripts/python.exe tools/foliage/local3d/pipeline.py `
  tools/foliage/local3d/examples/oak.json --out E:/ExoluneAssets/oak-witness-v1 --comfy-url http://127.0.0.1:8190
```

- Copy the example recipe before changing species or art direction.
- A UTF-8 `.txt` brief also works; add `--reference E:/path/example.png` when needed.
- A minimal JSON brief needs only `description`; optional fields override the tested defaults.
- Minimal briefs use general botanical captions inferred from the generated reference; the oak recipe retains its more specific captions.
- `description` is the text brief included in the reference-generation prompt.
- `reference` is optional; use `null` for text alone or a path relative to the recipe.
- `captions` specify the full-tree, bare-wood, leafy-branch and individual-leaf images.
- These explicit captions avoid loading a second large language model just to expand the prompt.
- When overriding captions, adapt them together; the assembly assumes a broadleaf plant with a bottom-facing leaf petiole.
- Fixed seeds control image generation and procedural assembly independently.
- Use --references-only to retain four pinned images before geometry inference.
- Use --prepared-references <reference-review.json> to compare Trellis/Pixal geometry on those exact images.
- All four hashes are verified; missing or changed images stop the job before inference.
- wood_reference_source selects an image to edit independently into a leafless structural reference.
- wood_source selects a curated woody PBR GLB; --wood-source overrides it without bypassing topology or volume checks.
- radial_scaffold.py is an experimental Blender CPU stage: retain a neural lower trunk and build a seeded radial tropical crown.
- It requires a fresh output folder and records the retained source, script hash and seed.
- Its eight-metre profile has five primary and ten secondary boughs; other botanical families still need directed profiles.
- The resulting wood.glb enters the common leaf, native LOD and impostor chain.
- Mesh-stage seeds remain explicit in the saved native graph.
- `wood_triangles`, `max_triangles`, `height_m`, leaf size and cluster spacing control the cook.
- `foliage_distribution: crown_volume` distributes shoots in an irregular crown envelope derived from the upper wood bounds.
- Each shoot connects to a woody triangle; `max_connector_m` limits its reach and `cluster_spacing_m` avoids crowded clumps.
- `foliage_distribution: surface` retains the earlier surface-only assembly for comparisons.
- In surface mode, `shoot_length_m`, `branch_alignment` and `shoot_upward_bias` control growth.
- The hard triangle budget bounds assembly; it does not prove forest performance.

**Outputs and restart**

- `manifest.json` points to the final asset, review scene, preview and structural audit.
- Every neural stage records its API graph, native canvas, prompt ID, execution history and artifact hashes.
- Required output targets exclude unrelated previews; a partially accepted graph never counts as a successful geometry stage.
- Model weights are fingerprinted once per output folder, then verified against size and modification time.
- Stage keys include executed graph inputs and model fingerprints.
- Rerun the same command to reuse verified outputs and resume a submitted job.
- A lost server history triggers resubmission of that stage.
- A changed brief, source, seed or setting creates another stage directory.
- The runner releases ComfyUI models and its execution cache between stages to avoid system-memory paging.
- It waits before a GPU stage while `MyPlanetEngine.exe` is running; it never closes the game.
- Saved canvases appear under `E:/ComfyUI/user/default/workflows/Exolune/local3d/`.
- The low mesh retains wood base colour, normal, roughness and metallic textures.
- Disconnected woody fragments are removed only when the main connected component retains at least 90% of source area.
- Leaf colour is extended eight texels under transparent contours.
- Leaves use alpha masking, double-sided shading and exported vertex tint.

**Authoring evidence**

- Complete alternative crown-volume run: `E:/ExoluneAssets/oak-witness-v1/manifest.json`.
- That alternative has 39,938 triangles, 48,932 exported vertices, two materials and 4,656 leaf cutouts.
- Quarter, back, walking, roots and wind views: `E:/ExoluneAssets/oak-witness-v1/export-review-final/`.
- The French text-only image stage also completed; a full second mesh run without a reference was not repeated.
- The source and job ledger is `trials/2026-11-02-oak.json`.
- Torn fine woody ends remain visible; the witness is not artistically accepted.

**Check the actual exported file**

```powershell
& E:/ComfyUI/.venv/Scripts/python.exe tools/foliage/local3d/audit.py E:/path/plant.glb
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' `
  --background --factory-startup --threads 4 --python tools/foliage/local3d/review.py `
  -- E:/path/plant.glb --out E:/path/export-review
```

- The audit checks triangle budget, embedded alpha, baked wood textures, vertex data, finite coordinates and final dimensions.
- The review imports the GLB again and renders quarter, back, walking and root views on CPU.
- A fifth view deforms leaves using the exported wind data and verifies stationary shoot attachments.
- `_WIND_PIVOT`, `_WIND_WEIGHT` and `_WIND_PHASE` describe shoot bending.
- `_LEAF_PIVOT` and `_LEAF_WEIGHT` describe individual leaf flutter.
- Custom vector attributes use the same Y-up local frame as glTF positions.
- The editable Blender scene restores these vectors to Z-up.
- The CPU witness is not an Exolune shader or animation integration test.
- `tools/tests/check_local3d.py <run directory> --review <review directory>` checks the completed run and saved canvas links.

**Limits and provenance**

- One generated image does not fully constrain hidden branches.
- Thin branch tips can remain torn even after remeshing; inspection from behind is required.
- A full crown matching the concept is not guaranteed by triangle or wind checks.
- Native material adaptation, leaf coverage mipmaps, LODs, impostors, ground fitting and shared wind are implemented in the downstream cook and renderer.
- Their acceptance is recorded per asset; one broadleaf does not validate a finished biome set.
- Native templates derive from Comfy-Org revision `60d0d2c2f5c98ab50116abd837156e4010534657` under MIT; see `templates/sources.json` and `templates/LICENSE.comfyui.txt`.
- Model licences remain separate from workflow licensing.
- [FLUX Kommunity terms](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy/blob/main/LICENSE.md) govern the image model; this experiment is non-production testing.
- Keep the complete reference rights and model terms with a selected production asset.
- Native geometry documentation: [TRELLIS.2](https://docs.comfy.org/tutorials/3d/trellis2), [Pixal3D](https://docs.comfy.org/tutorials/3d/pixal3d).
