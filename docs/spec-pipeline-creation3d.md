# Vegetation production pipeline

**Status**

- Architecture uses the [generated city extension](spec-ville-procedurale.md), sharing source provenance and review gates with this chain while retaining its own surface, material and placement rules.
- Use this procedure for each new master and structural variant.
- The user accepts the surface-distribution oak shown in `10_crown/quarter.png`.
- Its immutable GLB has SHA-256 `c11c61b00d093c57025ec4a7c7168e6431e198d7f11a329c6756762813e67458`.
- The fuller crown-volume assembly is an alternative, not the accepted witness.
- Authoring, native cooking and a renderer with up to seven geometry levels are implemented; structural and native functional checks pass.
- Programmatic structural variants derive from one master without another neural reconstruction.
- The library plans five distinct trees and five shrubs for each of six climate families; generated candidates remain separate from accepted production assets.
- Root undersides, coarse bounds and forest light transport have changed since the earlier cost trial.
- The earlier trial and failed quality preflight are archived in `log/spec-pipeline-creation3d-historique.md`; their timings do not validate this revision.
- The extended quality survey is checkpointed and stopped; no current acceptance is inferred from partial work.
- Canonical quality, native art, combined residency and performance remain required gates.
- Tools: `tools/foliage/local3d/`; weights, sources, cooked assets and evidence stay on E:.

- The in-flight review covered three oak variants and one radial hybrid kapok. The user approved merging the pipeline and renderer. Asset production acceptance has its own gates below.
- L1–L4 wood remains exactly equal to the master; L0 adds bounded curvature; two added intermediate levels preserve foliage volume.

**Operator workflow**

Run from the repository root. Use a separate directory per candidate under `E:/ExoluneAssets/`. See the [tool setup](../tools/foliage/local3d/README.md) for the local model paths, Python environments and Blender dependencies.

- Generate the master mesh and plant materials locally. Use neural generation, seeded procedural modelling or a documented combination.
- Use downloaded plant meshes as comparison controls during migration. Replace their roles by climate as generated candidates pass review.
- Reference images can guide a recipe under their own terms. Native geometry and variants derive from the generated master.

| Stage | Entry point | Evidence to retain |
|---|---|---|
| Brief and references | Run `pipeline.py <brief> --out <authoring> --references-only --comfy-url http://127.0.0.1:8190` with the ComfyUI Python environment. | Biome, scale, source rights, prompt, seeds and `reference-review.json`. Inspect the tree, bare wood, branch cluster and leaf. |
| Master | Resume with `--prepared-references <authoring>/reference-review.json`. For a reconstructed crown, supply `--wood-source <wood.glb>` or set `wood_source` in the recipe. | `manifest.json`, editable scene, exact GLB hash, topology and volume results. Rebuild faulty wood before attaching leaves. |
| Variant | Run `variations.py --source <master.glb> --out <variant> --profile <profile> --seed <seed>`. | Parent hash, profile, seed and separate review of the derived GLB. |
| Native cook | Run `native.py --source <plant.glb> --out <catalogue> --name <id> --lods` with offline Python and a prepared 31-role base. Use a fresh directory. | `native-report.json`, supported roots, seven mesh levels and a multiview impostor. Use the reported leaf mask when assigning roles. |
| Functional review | Build Release x64. Run `review_native.py --catalogue <catalogue> --out <review>`, then open the dated route with `tools/lance.ps1 -Parcours <route> -Plantes <catalogue> -Resolution fenetre`. | Walking-height roots and bark, side and back silhouettes, wind, backlight and LOD/impostor transitions. Record the bank, binary and source hashes. |
| Production acceptance | Run paired performance and quality measurements when requested. Review the final resident catalogue as well as the isolated witness. | `production-report.json` with passing gates for the exact inputs. |

- Prepare the 31-role base with `tools/plantes.ps1`, or pass a prepared copy with `native.py --base <path>`. A tracked catalogue manifest alone is not a cooked asset bank.
- Set `reject_branch_cycles: true` in new woody recipes. Inspect forks and supports from several angles even after the topology check passes.
- A source re-export changes the input hash. Review and cook the new input before reusing its evidence.
- Preserve rejected sources and their diagnostics locally. Publish only code, recipes and provenance permitted by the source licenses.

**Run requested acceptance measurements**

Run this command only when performance and quality benchmarks are explicitly requested. It starts the measurement campaign after authoring, cooking and functional review. Use the individual stages above for routine asset work.

```powershell
& C:/Python313/python.exe tools/foliage/local3d/produce.py `
  tools/foliage/local3d/examples/oak-production.json `
  --out E:/ExoluneAssets/oak-production --watch --comfy-url http://127.0.0.1:8190
```

- Build Release x64 first with `tools/lance.ps1 -Build -NoLaunch`.
- Install `tools/foliage/local3d/requirements-offline.txt` with Blender's matching CPython ABI into `E:/ExoluneTools/python-deps`; `EXOLUNE_PYTHON_DEPS` can override this location.
- The production recipe either preserves a reviewed GLB or names an `authoring_recipe` JSON/text brief.
- The authoring recipe accepts an optional image; `examples/oak-surface.json` retains the approved assembly settings.
- `--watch` retries pending GPU blocks for up to 120 minutes; the same command resumes verified work later.
- The report is `E:/ExoluneAssets/oak-production/production-report.json`, with a readable Markdown companion.
- Producer exit codes distinguish production-ready (0), execution error (1), failed acceptance (2) and pending acceptance (3).
- Shared content on E: avoids copying unchanged native models for each new species.
- Source, cook, executable, shaders and validation protocol are fingerprinted; changed inputs create another validation folder.
- Completed measurements are reused only with the same frozen inputs and protocol.
- A quality-protocol extension can adopt verified identical raw performance rounds; it never adopts the previous quality verdict.
- Shared quality selection and baseline captures are keyed by executable, shaders, baseline assets, ground scans and survey protocol.

**One chain**

1. Store the art brief, biome, species, size, seed and optional image in a recipe.
2. Generate isolated references locally with FLUX.3 Image Klein.
3. Reconstruct detailed wood and roots with TRELLIS.2; retain high geometry and predicted materials.
4. Bake colour, normal and roughness detail onto a reduced woody mesh.
5. Generate leaf appearance and assemble attached, independently deformable leaf geometry.
6. Preserve the reviewed master GLB and its fingerprint.
   Derive selected structural variants, preserving their lineage and individual review state.
7. Cook native materials, ground-contact metadata, source colour and wind attributes.
8. Derive seven mesh levels from that same master.
9. Bake the existing multiview impostor and its lighting from the master.
10. Audit every stream, load the asset in Exolune, inspect native captures and measure paired performance.
11. Publish a validation report; a failed or missing check must remain visible.

**Authoring contract**

- Use the existing native ComfyUI installation and models on E:.
- A text brief alone works; an image may supplement it.
- Botanical presets supply explicit captions without loading another language model.
- Preserve API graphs, canvases, seeds, model hashes and execution histories.
- Reuse verified stages and resume incomplete work.
- Do not reconstruct a fused full crown and assume that decimation creates animatable leaves.
- The current tested recipe is a woody broadleaf with individual leaf cutouts.
- Conifers, flowers and other understory plants must use appropriate authoring recipes and the same downstream gates.
- A successful oak does not validate those other botanical recipes.
- Reject leafy wood references before reconstruction; the bare structure uses its own text-guided reference rather than inheriting the full crown image.
- Diagnose persistent woody cycles at three voxel resolutions; this heuristic does not replace visual branch inspection.
- Preserve rejected attempts, intermediate references and source hashes.
- Whole-plant and bare-wood references request radial branching, front/back boughs and an oblique view with visible depth; leaf cutouts remain flat references.
- `branch_volume.py` clips wood above 35% of woody height, excluding roots and every leaf; triangle-area moments and horizontal PCA are invariant to yaw, scale and tessellation.
- Both oriented extent and surface-spread ratios must remain at most 3:1 for these volumetric presets; exceptions require an explicit botanical/art contract.
- Assembly checks this before attaching foliage; the exported-master audit and production variants repeat the same gate.
- Reconstruct a planar master before deriving its variants; scaling or twisting that fan does not supply missing radial branches.

**Structural variations**

- Species identity and same-species variation are separate recipe fields.
- `variations.py` derives `compact`, `spreading` and `windshaped` profiles with deterministic seeds.
- Change crown spread, branch lift, shear, twist and lean; the lower fifth stays exactly fixed.
- Bounded monotone vertical warping and invertible horizontal slices avoid folding the deformation field.
- Connectivity and fork count stay unchanged; these profiles cannot repair a fused or invalid master.
- Preserve UVs, indices, embedded textures, materials, vertex tint, wind weights and phases byte for byte.
- Transform shoot and leaf pivots together with geometry; transform normals and tangents with the local Jacobian.
- Keep the same triangle count; this authoring stage adds no per-frame work.
- Each chosen variant must recook its own seven LODs, light data and multiview impostor.
- Never swap a structural variant on camera approach or reuse the undeformed master's impostor.
- A master's artistic approval is not inherited by its variants.
- Variant approval uses its own `variation.art_approved` and exact `variation.approved_sha256`; a changed GLB invalidates it without changing generation parameters.
- `check_structural_variations.py` checks root immobility, branch-direction change, triangle integrity, attachment transport, reproducibility and source preservation.
- The initial oak probe retains 39,933 triangles per variant; root displacement is zero and wood-edge direction p95 changes by 6.8–9.9 degrees.
- Branch-protected seven-level cooks supersede the initial profile budgets and captures; historical counts remain in the pipeline log.
- `library.py` derives three offline variants after each successful master cook and writes production recipes for the master and its variants; this does not add all variants to the resident pool.
- The library queue does not start performance benchmarks; select a production recipe for the requested complete acceptance campaign.

```powershell
python tools/foliage/local3d/variations.py --source E:/path/plant.glb --out E:/path/compact/plant.glb --profile compact --seed 12345
python tools/foliage/local3d/library.py variants --out E:/ExoluneAssets/biome-library --plant temperate_tree_beech
```

- A production JSON accepts `"variation": {"profile": "compact", "seed": 12345}` beside its master `source` or `authoring_recipe`.
- Run that JSON through `produce.py` for the common downstream chain; source, deformation code and parameters enter its cache lineage.

**Shrub authoring**

- Plan the six climate families with `library.py plan --out <library>`. Four recipes carry specific stem counts, radial spread, arch, bark colour and leaf size.
- Run `library.py run --out <library> --plant temperate_shrub_hazel --limit 1 --comfy-url http://127.0.0.1:8190`. Prepare the standard 31-role base first. A library can reuse a prepared copy at `<library>/_baseline`.
- The worker builds a seeded scaffold in background Blender and saves the recipe, script and woody GLB hashes. Each stem tapers from the solid collar and forks toward free tips.
- ComfyUI generates the plant, shoot and isolated leaf references. The shrub reference bundle pins these three images. A scaffold supplies the woody structure.
- The common topology and volume gates inspect the woody GLB before curved leaf assembly. Keep the padded leaf cutout, embedded stem PBR maps, editable scene and final GLB hash.
- For a manual cook use `native.py --source <plant.glb> --base <prepared-31-role-base> --out <fresh-directory> --name <id> --lods --tile 1024 --shrub-family <0..5>`. Families follow the catalogue order from boreal to tropical.
- The seven-level shrub cook preserves the source collar and stems at L0–L4. L0–L3 share textures. L5/L6 reduce stems and rebake coarse maps under the same section and base error gates.
- The shrub collar uses existing terrain burial. Wind bends the upper mesh and flutters individual leaves before the existing multiview impostor relay.
- For a derived shrub keep `cook.shrub_family` in the production recipe and cook its own impostor. Select a bounded resident subset for the review bank.
- Botanical architecture references for the first lot include [US Forest Service hazel](https://research.fs.usda.gov/feis/species-reviews/corame), [Kew Psychotria](https://powo.science.kew.org/taxon/urn%3Alsid%3Aipni.org%3Anames%3A326020-2/general-information) and [Kew Piper](https://powo.science.kew.org/taxon/680296-1). The references guide morphology.

**Small ground flora**

- Run `python tools/foliage/prepare_ground_flora.py --out <fresh E: directory>`. Use `--group flowers` or `--group herbs` for a partial cook.
- The seeded profiles build stems, leaves, petal geometry and a small colour atlas. The common offline cooker creates lighting and a multiview impostor.
- Each colony has one sub-750-triangle mesh with wind from the existing herb shader. It switches directly to its impostor through the standard relay.
- Sorrel, tall grasses and ferns use seeded radial shoots and curved blades. Each form cooks its own lighting and multiview impostor.
- Keep the source script hash, profile, runtime file hashes and site evidence from `ground-flora-report.json`. Review in herb roles 23–30.
- Habitat, flower patch selection and moss substrate rules are described in `spec-diversite-vegetale.md`.

**Native cook and geometry levels**

- Preserve the source foot, crown dimensions, material mask and instance identity.
- Apply one continuous supported root shape before generating any representation.
- Bound its support gradient to 0.495 and check core edge strain.
- Bake canonical XYZ root scaling and transport normals, tangents and attachment pivots.
- Share that master between geometry levels, lighting and impostors.
- Preserve the complete source woody surface and UVs at L1–L4.
- Add bounded adaptive PN curvature at L0; retain original vertices, underside triangles and root support heights.
- Limit added work to 20,000 triangles and 100,000 total; reject folded new faces.
- Preserve curved leaves and multiple shoot rows through L2.
- Derive seven distinct levels with progressively reduced shoots and leaves.
- Plan each reduction below 88% of its predecessor and require less than 90%.
- Share source maps at L0/L1/L2; downsample original UV maps to 1024/512 at L3/L4.
- Use direct QEM at L5/L6, with fast-simplification 0.2.0 and aggressiveness 3.
- Validate woody sections and sampled root surface error before publishing coarse levels.
- Rebake L5/L6 UV maps at 256/128 with emission colour transfer and covered padding.
- Bound the last tree mesh to 3,000 triangles.
- FOLLOD02 supports legacy five-level assets and current seven-level assets.
- Exact budgets belong to each native-report.json.
- Rendering details and limitations: spec-rendu-vegetation.md.

**Reference and geometry comparisons**

- Run pipeline.py with --references-only to inspect the full plant, bare wood, shoot and leaf before 3D inference.
- A recipe may supply wood_reference_source for a separate pruning or art-direction edit.
- Pass --prepared-references with that reference-review.json to compare geometry backends on the same art.
- The runner verifies all four image hashes and records the bundle hash in the completed manifest.
- This bypasses image generation only; geometry, topology, upper-wood volume and native validation remain mandatory.
- A volumetric but pipe-like tree, disconnected limbs or persistent branch loops still fail acceptance.

**Hybrid radial witness**

- Direct Trellis/Pixal trials did not reliably preserve open woody branches.
- radial_scaffold.py retains a generated lower trunk and reconstructs a radial crown before leaf assembly.
- This fixed eight-metre tropical profile is experimental, not a general botanical generator.
- Weld geometric UV seams before clipping and capping; preserve their per-corner UVs.
- Join five cubic primary boughs and ten secondary boughs at the measured trunk collar.
- Taper the upper retained trunk to avoid a visible sawn rim.
- Unify collars at 18 mm voxel spacing, bound wood to 28,000 triangles, and bake colour/normal maps at 2048.
- The seed changes branch directions and curvature without another neural reconstruction.
- Keep the source, scaffold seed, script fingerprint, editable blend and reconstruction report.
- Supply the resulting PBR GLB with wood_source in the authoring recipe, or pipeline.py --wood-source.
- The common topology, upper-wood volume, leaf assembly, native LOD and impostor gates still apply.
- The current candidate has 61,355 master triangles and 5,280 individual curved leaf cutouts.
- Its woody horizontal span ratio is 1.016 and surface-spread ratio is 1.088; three coarse topology probes detect no handle.
- Its native L0 has 76,425 triangles; L6 has 2,960 and retains the multiview impostor relay.
- Five tropical roles share this one candidate; botanical diversity and production acceptance remain open.
- Evidence: E:/ExoluneAssets/vegetation-refinement-2026-11-03/kapok-scaffold-v5/ and kapok-radial-native/.

**Runtime transitions**

- Use seven screen-size mesh levels and the existing impostor relay.
- Seed-dependent thresholds remain deterministic and use projected plant dimensions.
- Complementary pixel coverage fades only adjacent mesh levels inside narrow transition bands.
- Both material passes share the same level, fade, wind time and geometry.
- The mesh/impostor fade stays complementary; wind reaches zero before that relay.
- Rooted trees skip legacy trunk extrusion and runtime horizontal root compression.
- Contact radius follows the physical canonical footprint, with a 0.14 m minimum and no 2.4 m squeeze.
- Four terrain samples fit a quadratic to the lower wood, with a smooth height fade and transformed normals.
- Contact burial is `min(0.25, 0.025 + 0.025 * rootRadius)` metres; the fit fades out with wind before the static impostor.
- Store one instance per source and reference it through LOD index lists.
- Keep the existing 192 MiB instance queues; the two-neighbour mesh order buffer adds 12 MiB.
- Logical population counts remain separate from duplicated transition draws.
- Native captures report draw counts and triangle counts for each mesh level.
- Identical models used by several logical roles share geometry, textures and impostors.
- This witness uses that sharing; resident cost for several distinct variants must be measured on their combined catalogue.
- The current loader shares whole model folders; it does not yet deduplicate partial material maps between different structural variants.
- Model identity and quantized fade/wind coverage share existing metadata; source placement data stays unchanged.

**Validation gates**

- Check source and output hashes, finite positions, normalized normals, UVs, materials, alpha and index ranges.
- Check decreasing geometry budgets and a bounded last tree LOD.
- Check buried root ends and zero root wind weights.
- Run `tools/tests/check_root_envelope.py` for supported thickness, continuous seams, a positive deformation Jacobian and normal/tangent transport.
- Run `tools/tests/check_root_materials.py <native-catalogue>` for bounded L0 curvature and exact L1–L4 source wood, root UVs and downsampled source maps.
- Inspect bases at walking height from several headings and on slopes, including the reported pose; a whole-tree silhouette test cannot validate roots.
- Batch-only `MYPLANETENGINE_PLANT_INSTANCES=1` with `MYPLANETENGINE_OBJECT_LIST=1` writes a full instance witness for identifying the actual model, seed, transform and contact packet.
- Compare cooked silhouette and coverage from 36 directions on CPU; retain per-level changes and a red/green difference sheet, without substituting that unlit probe for native appearance.
- Inspect natural, material-only and LOD-colour views; diagnostic views are not beauty renders.
- Exercise all levels, mesh/impostor boundaries, repeated stationary poses and wind.
- Review undergrowth, forest edge, canopy and aerial approach at several sites.
- Compare the same population, camera, sun, weather, resolution and executable.
- Audit every retained round, not only the final counters; verify frozen input hashes, sample counts, population equality and bounded duplicate draws.
- Time baseline/candidate/candidate/baseline on an idle GPU, without a window or desktop focus.
- Stop our measurement if another engine or inference starts; never close another session.
- Record median and p95 GPU frame/draw times, cadence, active LODs, geometry and resident payloads.
- Target at least 60 fps at 1080p; retain 120 fps as the wider engine goal.
- The production report requires GPU frame p95 and mean measured cadence within the declared frame budget, plus at most 10% paired GPU p95 regression.
- A candidate must not hide a performance regression behind reduced population or range.
- Compare the quality benchmark with `tools/banc_qualite_reference.json` using `--before`; no p95 may regress over 10%.
- Use 30 material-balanced places for production quality; a smaller preflight cannot replace missing reference metrics.
- Report inherited canonical failures separately from additional paired regressions; do not reset the reference.
- Do not mark a candidate production-ready when a required check is missing or failed.
- Record native art acceptance in the current review folder's `visual-acceptance.json`, tied to the validation input hash.
- Shared-GPU functional captures never count as performance evidence.
- Opportunistic performance checkpoints retain each uncontaminated view; quality checkpoints retain selection blocks and complete sites.

**Scaling the library**

- Each species or structural variant has its own immutable source, recipe and validation report.
- Reuse the same cook, LOD, impostor and native validation commands.
- Validate the assembled catalogue again with its actual distinct variants; a repeated witness does not establish a diverse library's memory budget.
- Adjust botanical presets and declared budgets, not the validation outcome.
- Keep offline generation separate from runtime; only cooked assets ship.
- The default technical catalogue still has 31 roles; `FOLBIO03 91` adds five tree and five shrub slots for each climate family in external review banks.
- The current renderer cap is 96 logical roles; exact float32 packing uses two eight-bit coverage values.
- Offline variants can exceed that pool; concurrent residency and a larger pool or streaming strategy remain separate work.
- The review bank contains only completed candidates plus explicitly labelled baseline fallbacks; a role count is not a generated-model count.
- Six-family captions and seed plans are in `library.py`; generated references, rejected attempts and progress stay under `E:/ExoluneAssets/biome-library/`.
- `library.py run --allow-shared-gpu` admits authoring by physical free VRAM and checkpoints busy stages; shared-GPU timings cannot establish performance.
- Service or model/workflow configuration failures pause the queue without consuming modelling retries.
- The queue accepts --comfy-url; the dedicated service uses port 8190 with explicit E:/ComfyUI_Models/models paths.
- The ground flora tool generates the eight herb roles independently of the woody queue.
- The first shrub authoring batch covers temperate and tropical woodland. Its hazel uses bowed canes with fork anchors on the curved stem.
- A new hybrid kapok candidate replaces the planar tropical source in the current review bank; this does not complete the five-tree family.
- Beech and kapok have native LOD/impostor cooks and three offline derivatives each, but their planar wood fails art/volume acceptance and is queued for revision.
- Scots pine also fails the volume check; Siberian spruce has volumetric wood but remains blocked in native LOD cooking.
- The original diagnostic oak has three native structural variants; these do not count as three species or as three newly generated masters.
- The sixty-model campaign remains incomplete; a technically loadable candidate is not a production asset.
- Multi-location user route: `tools/tests/2026-11-03-vegetation-refinement.txt`, with an explicit external review catalogue through `lance.ps1 -Plantes`.
- Root-focused hidden review: `python tools/foliage/local3d/review_roots.py --catalogue E:/path/review-bank --out E:/path/fresh-review`; 38 captures, seven forced levels, repeated feet and wind.
- Collision and gameplay interaction are separate from this rendering validation.

**Sources and history**

- Native generation: [TRELLIS.2](https://docs.comfy.org/tutorials/3d/trellis2), [Pixal3D](https://docs.comfy.org/tutorials/3d/pixal3d).
- Offline QEM: [fast-simplification](https://pyvista.github.io/fast-simplification/), pinned to 0.2.0; geometric acceptance is checked independently of its requested face target.
- Image model: [FLUX.3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy), under its separate terms.
- Workflow template revision and MIT notice are retained with the tools.
- Keep reference rights and model terms with each selected production source.
- Earlier authoring state: `log/spec-pipeline-creation3d-historique.md`.
- Trials and rejected assemblies: `log/recherche-generation-vegetale-historique.md`.
