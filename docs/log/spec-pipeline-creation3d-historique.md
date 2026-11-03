# Local 3D pipeline history

**2026-11-03 · Intermediate close-detail and tropical trials**

- Initial PN refinement excluded the whole lower 18% of the plant, missing part of the FPS trunk.
- Its spreading/compact/windshaped L0 counts were 51,999 / 51,874 / 51,887.
- The current cook includes lower-trunk and root-side curvature with fixed support heights and a tighter root bound.
- First bark bands used value noise and 2.5/0.55/0.12 mm heights; current bands use shared gradient noise and 8/1.2/0.2 mm.
- F4 material/transport views separated almost unit cavity from a dark orbital biome colour and strong cloud attenuation.
- Porous skylight alone did not restore readable litter; the current material and observer rules replace that experiment.
- The first radial kapok had plausible depth but hollow pipe-like limbs; its assembled preview failed art review.
- The organic Trellis retry failed the retained-component area gate; the cleaned retry still had persistent branch loops.
- Six CPU views of the cleaned wood confirmed the visible loops; this was not just a conservative topology warning.
- Pixal3D on the same four pinned images also failed the branch-cycle gate.
- Its first submission lacked the running server's MoGe model path and returned only the crop preview; this was a configuration failure.
- The runner now checks visible loader choices, requests required outputs only, and rejects partial output success.
- E: retains references, native canvases, mesh exports, topology reports, rejected previews and configuration evidence.
- These trials add no production-approved species.
- A later text-only sparse-wood trial still exported torn woody surfaces and failed the cycle gate.
- Early radial-scaffold trials lost the acquired trunk because geometric UV seams were not welded before capping.
- A solidify detour introduced acute-corner spikes; it is discarded.
- The retained profile welds seams, measures the collar centre, tapers its upper trunk and rebuilds the crown explicitly.
- The retired planar native kapok had 35,547 / 27,224 / 22,984 / 17,154 / 13,974 / 5,050 / 2,366 triangles.

**2026-11-03 · Preserve root volume across the production chain**

- **Report:** torn, stretched roots in the foreground oak at -11.040080 / 49.783495.
- **Cause:** discontinuous offline root conformation plus independent runtime XZ compression, already visible at detailed L0.
- **Master:** one support field with gradient at most 0.495; preserve core thickness, fade vertically over 0.16–0.24 source height, and sink the supported base by 0.004 normalized units.
- **Footprint:** bake uniform XYZ root scaling to 0.085 * crownWidth / 0.45, fading to identity over 0.16–0.32 height; preserve the logical ground pivot.
- **Frames:** deform normals, tangents and attachment pivots consistently; check core edge strain against the analytic bound.
- **LOD:** protect wood below 0.18 height at L1/L2; direct QEM, aggressiveness 3, at L3/L4; no independent second underside warp.
- **Limits:** root-surface p95 0.0008 / 0.003 / 0.006 / 0.012 normalized height, maximum three times p95 limit; retain trunk-section and whole-plant triangle gates.
- **Runtime:** remove the 2.4 m reach cap and root-only horizontal squeeze; rooted trunks skip legacy extrusion.
- **Contact:** four samples fit all lower wood with a smooth fade; burial min(0.25, 0.025 + 0.025 * radius) metres; contact fades out before the static impostor.
- **Dependency:** offline fast-simplification 0.2.0 on E:, matching Blender's CPython ABI; runtime has no new dependency.
- **Materials:** retain L2 source UVs and 512 maps; L3/L4 rebake base colour through emission and dilate from covered texels to avoid dark bark transitions.
- **Catalogue:** recook three oak variants and the kapok root witness; reject beech's lost L2 trunk envelope and retain a labelled baseline fallback.
- **Checks:** Release x64, 7,000 contact planes through 24 m radius, continuous seams, thickness, positive Jacobian and normal/tangent transport pass.
- **Material checks:** all four recooked forms retain 100% of sampled close-root position/UV pairs and exact source-map downsampling at L2.
- **Review:** hidden exact-pose captures and tools/tests/2026-11-03-root-integrity.txt; shared-GPU renders establish appearance and format only.
- **Native result:** 29 hidden captures pass queue bounds, all five forced levels, reported model/seed identity, stationary feet and visible wind motion; E:/ExoluneAssets/root-integrity/native-review-final/root-review.json.
- **Limits:** current native art, complete quality and performance acceptance remain open; rejected planar masters stay diagnostic witnesses.
- **Status:** uncommitted; no tag or publication requested; replaced settings and intermediate measurements moved to log/spec-pipeline-creation3d-historique.md.

**2026-11-03 · Superseded five-level branch reduction**

- Reported branch pose: -11.039991 / 49.783625, 4 m clearance, pitch -7.67, heading -123.35.
- Large branch faces appear at automatic L1; forcing L0 preserves the original surface.
- Root and trunk checks alone missed faces spanning an empty branch loop.
- The seven-level revision retains nearby wood and adds intermediate foliage reductions.
- A first diagnostic stopped at L5 because its validator still capped the old five-level range.
- The shared renderer limit now governs forced validation levels.
- A trial backlight sun below the horizon produced a night image; the current route uses an above-horizon sun.
- ComfyUI configuration failures after restart were not botanical rejections.
- Preserve logs and restore verified affected budgets; a dedicated service loads the E: models.
- Sources, intermediate cooks and failed or superseded captures remain on E:.

- The root diagnostic bank has three recooked oak variants and one recooked kapok witness; the rejected beech uses a baseline fallback.
- The root revision passes 29 hidden native captures: five forced levels, multiple sites/headings, stationary identity and wind-foot stability; performance and final art acceptance remain open.

**Native cook and geometry levels**

- Keep the logical ground pivot, crown dimensions, material mask and instance identity across representations.
- Preserve the source's logical foot in XZ; an asymmetric crown must not recenter the trunk.
- Build one continuous support field from woody undersides, with horizontal gradient at most 0.495.
- Apply it to all lower geometry and attachments; a material tag must not split coincident trunk/root vertices.
- Keep root thickness in the supported core; fade the vertical correction between 16% and 24% source height.
- Bake a uniform XYZ root reduction to the canonical reach `0.085 * crownWidth / 0.45`; fade it to the unchanged trunk between 16% and 32% height.
- Transport normals, tangents and shoot/leaf pivots through the same deformation.
- Check core edge strain against the support field's analytic bound before publishing any representation.
- Inherit this master in every LOD, light bake and impostor; do not repeat an independent per-vertex ground warp after reduction.
- Constrain every level to the common master bounds, including buried roots and shoot ribbons.
- Put authored outer root ends below the existing terrain and use its sampled contact fit; terrain never moves.
- Preserve source vertex tint in the native vertex stream.
- Source shoot and leaf weights control wind; root vertices stay fixed.
- Keep the detailed master at close range.
- Preserve curved source leaves at L1; flatten cards at L2 before removing whole leaves.
- Bound each level below 80% of the previous triangle count; actual wood and shoot costs set the whole-leaf count, with a 78% planning target.
- At coarse levels, retain spatially distributed leaves and compensate lost area inside each source shoot's bounds.
- Lock woody vertices below 18% height at L1 and L2 with Blender's inverted collapse group.
- L3/L4 use direct QEM from pinned `fast-simplification==0.2.0`, aggressiveness 3; no voxel reconstruction erases source sections.
- A low-aggression solve may retain extra faces; whole-plant reduction and the 3,000-triangle final tree cap remain hard gates.
- Symmetric sampled root-surface p95 error limits are 0.0008 / 0.003 / 0.006 / 0.012 normalized height; maximum error is at most three times each limit.
- Check eight trunk sections from 10% to 45% height; retain at least 55% overlap wherever both source spans exceed 3.5% of height.
- Retain failed cooks for review instead of weakening the geometry checks.
- Rebuild its UVs and bake textures from the master; source chart constraints must not prevent reduction.
- Exact geometry counts belong to each candidate's `native-report.json` and `lod-report.json`; do not reuse another source's budgets as evidence.
- L0 and L1 share 2048 material maps; L2 retains source UVs with downsampled 512 maps.
- L3/L4 use new UVs and 256/128 maps; emission baking transfers base colour without diffuse-lobe metallic attenuation.
- Only fully covered bake texels seed padding; partially covered edges must not darken the opaque wood.
- Source lighting and wind fields are inherited instead of recalculated from a sparser canopy.
- `lods.bin`, version `FOLLOD02`, stores geometry, light, attachment data and optional coarse maps.
- A model without the sidecar retains its original single mesh and impostor behaviour.

**2026-11-03 · Rejected torn-root preparation**

- Reported pose: seed 0, latitude -11.040080, longitude 49.783495, altitude 34.9 m, pitch 12.92, heading 54.34.
- Full instance export identifies foreground model 73, oak_spreading, seed 3923462319; the terrain-contact packet is flat.
- The defect is already visible at L0; it cannot be attributed only to a distant LOD.
- Independent vertex-wise underside subtraction and root-tag-only burial stretched root edges and split coincident root/trunk regions.
- The previous shader squeezed the authored footprint from 6.68 m to a 2.4 m cap without reducing root height.
- Removing legacy trunk burial alone did not resolve the defect.
- The first replacement cook's voxel remeshing failed the woody-section gate; it stays unpublished.
- A later direct-geometry cook exposed dark intermediate bark: L2 re-unwrapped thousands of protected base faces, and diffuse-lobe baking attenuated base colour.
- Source L2 UVs and emission-based coarse colour baking supersede these material transfers; partial bakes and native probes remain on E:.
- Initial oak-variant counts were 39,933 / 29,215 / 13,834 / 5,268 / 2,146 triangles.
- Their previous 48-view compact checks and six-climate dispatch checks did not validate close root volume.
- Original sources, failed cooks, old shaders and the exact before capture remain in E:/ExoluneAssets/root-integrity/.
- New continuous support, canonical XYZ root shaping and protected/direct LOD reduction replace these settings; see ../spec-pipeline-creation3d.md.

**2026-11-02 · Vegetation roots, forest light and structural variations**

- **Branch:** `codex/vegetation-biomes` starts at current public `main`; walking, audio and cloud integration retained; the former vegetation work is preserved in a local stash and an E: archive.
- **Roots:** remove positive woody underside gaps before native fitting, repeat after simplification, and constrain all LODs to the common bounds; root geometry alone moves.
- **Contact:** retain four samples and the existing 0.14–2.4 m reach; bury by `min(0.12, 0.025 + 0.025 * rootRadius)` metres; do not apply tree root metadata to shrubs.
- **Forest light:** shared porous transport with 0.82 effective crown opacity, 0.08 sky scatter and a minimum four-metre shade boundary; population, canopy cover and global exposure unchanged.
- **Bank:** 91 external review roles, cap 96; thirty new tree and thirty shrub roles across six climate families; two eight-bit coverage values retain exact float32 model metadata.
- **Library:** sixty distinct woody recipes, three attempts per invalid source, separate bare-wood references, cycle diagnostics and checkpointed VRAM admission; no rejected asset becomes production-ready.
- **Variants:** compact, spreading and wind-shaped profiles; deterministic branch lift, crown spread, shear, twist and lean; lower 20% fixed; UVs, materials, connectivity and wind weights retained.
- **Cook:** each selected variant derives its own five mesh LODs and multiview impostor; the offline library does not imply simultaneous GPU residency.
- **LOD rule:** actual wood/shoot cost sets the retained leaf count under a 78% target and 80% maximum of the previous level; preserve curved leaf geometry at L1.
- **Checks:** Release x64 on current main, 4,000 root planes, 6.3 million metadata cases, root-envelope and three-profile geometry checks pass; walking/audio regressions pass.
- **Assets:** first new beech passes native stream checks at 39,942 / 28,080 / 13,304 / 5,080 / 2,072 triangles; compact oak variant passes at 39,933 / 29,215 / 13,834 / 5,268 / 2,146.
- **Tropical:** first new kapok passes at 31,464 / 24,200 / 10,420 / 4,048 / 1,660 triangles, with its own impostor and three offline structural derivatives.
- **Review:** hidden native checks and dated flight route; E:/ExoluneAssets/biome-library retains source images, actual 3D previews, states, derived variants and reports.
- **Native:** 48 compact-profile captures pass geometry relay, stationary selection and wind-foot stability on current main; six generated-bank climate views pass dispatch and queue checks.
- **Trunk support:** eight resolved sections detect neural-bark failure; bounded voxel retries preserve the tropical trunk. Its corrected cook passes another 48 native LOD/wind captures; CPU coverage probes retain the measured deviations for art review.
- **Flight:** `tools/tests/2026-11-02-vegetation-variations.txt`; its external review bank uses three structurally distinct oaks from one master, not three new species.
- **Limits:** current performance, combined residency, canonical quality and native art acceptance remain open; the previous quality survey is stopped and checkpointed.
- **Ground layer:** new flowers and grasses remain planned; this queue produces woody trees and shrubs.
- **Status:** uncommitted work; no tag or publication requested; superseded vegetation checkpoints and measurements are in `log/spec-pipeline-creation3d-historique.md`.

**2026-11-02 · Rejected tropical intermediate LODs**

- The first tropical source has 31,464 triangles; retaining twelve curved leaves per shoot at L1 failed the 20% reduction gate.
- Source-aware whole-leaf budgeting retains ten at L1, reaching 24,200 triangles without flattening the nearby leaf geometry.
- A diagnostic then found 0.638 minimum L2 coverage and a five-pixel p95 contour deviation at a 128-pixel probe.
- The missing volume was woody trunk geometry, not the crown: fine voxel grids preserved neural surface holes and erased sections of the stem.
- Eight cross-section checks reject the 0.003 and 0.006 normalized voxel attempts; the bounded 0.012 reconstruction retains at least 95.3% section overlap.
- Corrected levels are 31,464 / 24,200 / 10,420 / 4,048 / 1,660 triangles.
- Corrected L2 coverage spans 0.810–0.986 with a two-pixel p95 contour deviation; native art acceptance remains required.
- Failed native cooks and old review banks stay on E:; they are not the catalogue selected for the final flight route.
- A temporary JSON-report name collision was corrected before the successful budgeted cook; partial artifacts remain unpublished.

**2026-11-02 · Selected master and superseded cost trials**

- The earlier authoring assessment favoured a 39,938-triangle crown-volume assembly and described the 39,933-triangle surface assembly as narrow plumes.
- The user subsequently preferred and accepted the actual surface render `10_crown/quarter.png`.
- Its source SHA-256 is `c11c61b00d093c57025ec4a7c7168e6431e198d7f11a329c6756762813e67458`.
- It contains 10,521 wood triangles and 29,412 shoot/leaf triangles, 387 shoots and 4,644 individual curved leaves.
- The initial isolated A/B/B/A test drew that full mesh everywhere near; ground GPU median rose from 15.56 to 29.17 ms at 1080p.
- The distant impostor control did not show that cost; all five broadleaf roles shared the witness with unchanged population.
- Evidence: `E:/ExoluneAssets/local3d-performance-2026-11-02/measurements/performance.json`.
- That experiment's quality phase was interrupted by another engine; it has no complete quality acceptance.
- Early native cooks v1–v5 and measurements-v1/v2 remain on E: as intermediate evidence.
- Neural wood junctions prevented sufficient QEM reduction; coarse voxel reconstruction, new UVs and CPU material baking resolved the reduction limit.
- A flat-leaf L1 at 26,123 triangles was superseded by curved leaves at 29,219 triangles to preserve nearby volume.
- The current five-level chain and validation contract are in `../spec-pipeline-creation3d.md`.

**2026-11-02 · Five-level witness validation**

- Native source and cooked streams pass structural checks; all five levels, the far impostor, stationary selection and wind are exercised in hidden captures.
- Background inspection retains the source bark, roots and leaf appearance; deep forest lighting remains dark in the baseline too.
- A/B/B/A covers seven views at 1920x1080, with clouds and sea enabled, 32 warmup frames and 128 samples per view per round.
- All 28 retained blocks are clean under the other-engine/ComfyUI monitor; the CPU audit verifies frozen runtime files and identical logical populations in every round.
- GPU frame medians, baseline to candidate: temperate ground 15.89 to 16.10 ms; second heading 16.16 to 16.66; canopy 13.73 to 13.96; 120 m 18.24 to 17.89; tropical ground 19.05 to 18.76; tropical 120 m 19.47 to 18.83; distant 15.48 to 15.22.
- Paired GPU p95 changes range from -4.79% to +5.41%; no paired regression exceeds 10%.
- The 60 fps frame/cadence budget fails in five candidate views; their baseline controls also miss that budget.
- Unique vegetation payload is 1437.1 MiB for baseline and 1307.4 MiB for this repeated witness, excluding queues and other game resources.
- Five distinct future masters cannot assume the memory saving from sharing this single witness.
- CPU 36-direction probes at 128 pixels retain 99.1–99.9% coverage at L1, 97.7–100.0% at L2, 94.0–101.5% at L3 and 81.3–90.4% at L4.
- The largest p95 nearest-coverage deviation is 1.42 pixels; these nearest-sampled unlit probes do not include native mip filtering, wind or lighting and are not an acceptance threshold.
- Evidence: `E:/ExoluneAssets/oak-production/validation/69fe03645a56a6f7af43/measurements/` and `E:/ExoluneAssets/oak-production/lod-coverage/`.
- Full canonical quality results and the live acceptance state remain in `E:/ExoluneAssets/oak-production/production-report.json`.
- The six-site preflight finishes with eight missing canonical material/height pairs and six paired p95 regressions in grass regions.
- At 12 m, grass gap p95 changes from 2.664 to 3.760; at 800 m, repeat p95 changes from 0.0832 to 0.1012.
- These failures are retained; incomplete material coverage is not presented as a successful quality gate.
- The candidate repeats one witness across five broadleaf roles; this comparison does not establish the quality of a future diverse catalogue.
- Production quality switches to the official 30-site protocol; verified identical raw performance rounds are adopted without rerendering and without reusing a quality verdict.

**2026-11-02 · Offline authoring prototype before native LOD work**

# Local 3D vegetation pipeline

**Status**

- Offline authoring prototype, implemented and executed on 2026-11-02.
- The witness is a mature oak derived from a text brief and an optional user-board crop.
- The goal is substantial game vegetation with preserved surface detail and independently deformable foliage.
- Artistic acceptance, a complete biome catalogue and runtime integration remain open.
- Tools: `tools/foliage/local3d/`; models and generated binaries stay on E:.

**Pipeline**

1. FLUX.3 Image Klein generates a complete isolated plant from the brief and optional reference.
2. Image edits produce matching bare wood, a leafy branch and one individual leaf.
3. Native TRELLIS.2 reconstructs the wood, roots and materials at 1024 resolution.
4. Native remeshing and decimation derive wood near 12,000 triangles.
5. UV unwrapping and baking transfer base colour, roughness, metallic and normal detail.
6. BiRefNet extracts leaf alpha; colour extends eight texels beneath transparent contours.
7. Blender attaches small shoots and distinct curved leaf cutouts to the reconstructed wood.
8. Export a bounded GLB with two materials, vertex tint and explicit wind data.
9. Audit the file and import it again for background CPU review.

**Authoring choices**

- Prefer the working native nodes over another wrapper in the tested environment.
- TRELLIS.2 is the selected woody backend after comparison with Pixal3D on one bare-oak image.
- Keep Pixal3D as an explicit backend option; this is not a universal ranking.
- Retain high geometry and predicted material maps alongside the reduced result.
- Reduce wood separately; solid remeshing must not fill intended leaf gaps.
- The current witness targets 8 m total height and at most 40,000 triangles.
- Twelve curved leaf cutouts per shoot remain distinct surfaces.
- The selected distribution samples an irregular crown envelope derived from upper wood bounds.
- Every shoot starts on a woody triangle; a maximum span limits unsupported reach.
- Spacing and the triangle budget bound assembly.
- Roots are part of the wood; no soil slab is added.
- Component cleanup must retain at least 90% of source surface area.
- Image, mesh and assembly seeds remain recorded separately.
- Explicit botanical captions supplement the brief without loading a second language model.
- The current cook targets broadleaf plants; needles, flowers and grass need other recipes.

**Export contract**

- glTF Y-up, foot at Y=0, final combined height normalized to the recipe.
- Separate woody and foliage primitives with two materials.
- Wood retains baked base colour, normal and metallic/roughness textures.
- Leaves use double-sided alpha masking and exported `COLOR_0` tint.
- `_WIND_PIVOT`, `_WIND_WEIGHT` and `_WIND_PHASE` describe shoot bending.
- `_LEAF_PIVOT` and `_LEAF_WEIGHT` describe individual leaf flutter.
- Pivot vectors share the local frame of exported positions.
- The editable Blender scene restores pivots to Z-up.
- Check finite attributes, dimensions, textures, alpha and triangle counts after export.

**Reproduction**

- Run `pipeline.py` with a UTF-8 text or JSON brief and an E: output directory; its README gives the command.
- An optional `--reference` image supplements the text; minimal briefs receive generic botanical stage captions.
- Use loopback ComfyUI, native nodes and offline loading.
- Each stage saves its API graph, native canvas, prompt ID, history and output hashes.
- Model filenames and SHA-256 fingerprints are retained with the run.
- Saved canvases appear in ComfyUI's `Exolune/local3d` workflow directory.
- Reruns reuse verified artifacts and resume submitted stages.
- Release models and the execution cache between stages to avoid system-memory paging.
- Wait for a running game before submitting another GPU stage; never close another session.
- Review quarter, back, walking, roots and a wind pose on CPU without opening Blender.
- The wind witness checks fixed attachments; it does not validate Exolune's shaders.
- `tools/tests/check_local3d.py` checks completed stages, canvas links, fingerprints and the asset contract.

**Remaining acceptance**

- Refine species-specific crown asymmetry, extent and leaf scale against the concept.
- Inspect torn tips, hidden surfaces, root volume and close materials under another light.
- Check species silhouette and leaf scale before generating variants.
- Derive LODs and impostors from the selected plant.
- Adapt materials and wind to Exolune's import format.
- Preserve cutout coverage in runtime mipmaps.
- Fit roots to existing terrain without modifying relief.
- Review the seamless aerial-to-walking approach after integration.
- No engine performance or quality benchmark has been run for this prototype.

**Sources and rights**

- Native [TRELLIS.2](https://docs.comfy.org/tutorials/3d/trellis2) and [Pixal3D](https://docs.comfy.org/tutorials/3d/pixal3d) supply the mesh and material stages.
- API templates derive from Comfy-Org revision `60d0d2c2f5c98ab50116abd837156e4010534657`, MIT; provenance and notice are retained with the tools.
- [FLUX.3 Image Klein](https://huggingface.co/black-forest-labs/flux-3-image-klein-comfy) supplies images under separate FLUX Kommunity terms.
- This run is non-production testing; retain reference rights and model terms with a production asset.
- Comparisons and rejected assemblies: `log/recherche-generation-vegetale-historique.md`.

**Superseded vegetation journal checkpoints**

**2026-11-02 · Reviewed local tree and native production chain**
- **Selection:** the user accepts `10_crown/quarter.png`, the surface assembly; its 39,933-triangle source is retained unchanged by SHA-256.
- **Cook:** native root contact, vertex colour, source wind weights, five mesh LODs and the existing 12-by-5-view impostor.
- **Levels:** 39,933 / 29,219 / 13,836 / 5,270 / 2,148 triangles; 2048 shared master maps, then 512 / 256 / 128.
- **Roots:** outer ends buried by up to 0.02 normalized units; the existing terrain fit moves plant geometry only.
- **Runtime:** deterministic screen-size selection, narrow complementary fades, unchanged logical populations and mesh/impostor threshold; 192 MiB queues plus 12 MiB LOD order indices.
- **Residency:** identical model folders share GPU resources across logical roles; distinct variants remain independent.
- **Validation controls:** batch-only forced LOD 0–4, material diagnostic `plantalbedo`, level diagnostic `plantlod`; normal launch defaults remain unchanged.
- **Reproduction:** `tools/foliage/local3d/produce.py`; checkpointed hidden captures and opportunistic paired performance/quality checks.
- **Checks:** Release x64, native streams, 48 hidden LOD/wind captures, 36-direction CPU coverage and all 28 paired performance blocks pass their structural/protocol checks.
- **Performance:** relative GPU p95 stays within the 10% limit; the absolute 60 fps budget remains unmet in several views and baseline controls.
- **Quality:** the six-site preflight fails grass-region p95 metrics and lacks canonical coverage; the checkpointed 30-site survey continues in background with a shared baseline cache.
- **Evidence:** `E:/ExoluneAssets/oak-production/`; production acceptance remains failed/pending until native art, cadence and canonical quality gates pass.
- **Scope:** the external comparison replaces five broadleaf roles with one witness; the default diverse catalogue remains active.
- **Status:** uncommitted work; no tag or publication requested. Earlier assemblies and the costly 40k-only comparison are in `log/spec-pipeline-creation3d-historique.md`.

**2026-11-02 · Local brief-to-plant authoring pipeline**
- **Scope:** offline ComfyUI and Blender; no terrain, runtime catalogue or rendering setting change.
- **Images:** FLUX.3 Image Klein INT8, 1024, 16 steps, CFG 1; seeds 314159 / 271828 / 161803 / 323606 for plant, bare wood, leafy branch and leaf.
- **Wood:** TRELLIS.2 INT8 at 1024; native solid remesh 384, 12,000-triangle target and 2048 material/normal bakes; Pixal3D comparison retained.
- **Assembly:** 8 m final height, 40,000-triangle cap, seed 424242, 0.4 m crown-cluster spacing and 2.2 m maximum connector; twelve curved leaves per shoot.
- **Witness:** 39,938 triangles, 4,656 leaf cutouts, two materials; 98.44% of woody source area retained after fragment cleanup.
- **Text-only:** a French brief also generates the image reference without an input image; the complete mesh run was tested with the optional board crop.
- **Review:** exported GLB audit and background CPU views; final art, runtime wind, LODs and seamless approach remain pending.
- **Reproduction:** `tools/foliage/local3d/`, `spec-pipeline-creation3d.md`; outputs in `E:/ExoluneAssets/oak-witness-v1/`.
- **Status:** uncommitted authoring work, no tag or publication; rejected assemblies and intermediate evidence in `log/recherche-generation-vegetale-historique.md`.

**2026-11-02 · FoliMesh POC rejected**
- **Decision:** the user finds the native result worse than the previous vegetation and closes this route.
- **Scope:** the external POC never replaced the default catalogue; no further FoliMesh tuning is planned.
- **Archive:** source, recipe, geometry, checks and limitations in `log/recherche-generation-vegetale-historique.md`; binaries remain on E:.
- **Status:** no new runtime settings, commit, tag or publication; vegetation work continues in the other active conversation.

**2026-11-02 · Generated tree density review**
- **Direction:** the user likes the local model; resolve density and deformable foliage within the ComfyUI investigation.
- **Authoring:** CPU gltfpack 1.3; original exports preserved.
- **Choices:** 0.01 and 0.2 error limits retain approximately 528,000 and 167,000 file triangles; 1.0 collapses and is rejected.
- **Derivative:** aggressive 50,000 target and duplicate-face cleanup; 40,159 triangles / 18,877 vertices.
- **Review:** eight quarter/walking renders; silhouette survives, surface detail deteriorates without UV/normal baking.
- **Scope:** no terrain, engine or runtime change; no benchmark, commit or tag; details in `log/recherche-generation-vegetale-historique.md`.

**2026-11-02 · Local Pixal3D authoring trial**
- **Trial:** native ComfyUI, existing E: models, Pixal3D INT8, 1024 resolution, batch 1; completed on the RTX 4070 Ti 12 GiB.
- **Recipe:** structure seed 56 / 12 steps, shape seed 42 / 20 steps, refinement seed 42 / 12 steps, texture seed 43 / 12 steps; no solid remeshing or reduction.
- **Result:** raw and vertex-coloured GLBs, approximately 14 million triangles; substantial woody structure, fused foliage and an unwanted soil slab.
- **Assessment:** insufficient for the FPS target; the small reference crop limits the conclusion about the model.
- **Record:** `log/recherche-generation-vegetale-historique.md`; reproducible graphs and hashes under `tools/foliage/comfyui/trials/2026-11-02-oak-pixal3d/`.
- **Scope:** authoring only; no terrain, runtime setting, catalogue or engine change; background inspection, no benchmark, commit or tag.

**2026-11-02 · Rooted prototype and generative sourcing revision**
- **Direction:** eight user-provided biome boards; mature trunks, full crowns and genuine root volume; restart model sourcing with a preference for generative authoring.
- **Prototype:** 31 temporary forms, including two ferns; scanned fir companions replaced by adapted game-pine forms.
- **Roots:** seven curved roots and flared collar per tree; reach `clamp(0.085 * size * spread * ownWidth, 0.14, 2.4)` metres; four cached terrain contacts, smooth detail introduction over 192–384 pixels.
- **Ground layer:** ceiling 0.18 to 0.32; tree attenuation 0.70 to 0.55; growing-season admission over 5–10 C and humidity 0.25–0.65; forest litter factor `0.3 + 0.7 * grassAmount`; 72% fern preference within suitable sheltered herb choices.
- **Storage:** same six 192 MiB queues; 2,280 command bytes and 112-byte per-model settings; reuse the existing ground cache.
- **Checks:** Release x64, 31-model structure/material checks, sixteen hidden native views and 4,000 root-plane cases pass.
- **Art:** these functional results do not validate the visual target; inherited silhouettes and dark undergrowth remain insufficient.
- **Research:** `recherche-generation-vegetale.md`; specialized procedural/AI authoring, direct neural 3D and reference libraries compared; no new provider selected, connected or purchased.
- **Review:** dated route retained; background verification only, no Computer Use or interactive launch.
- **Status:** uncommitted work; no milestone tag, publication or performance/quality benchmark.

**2026-11-02 · Diverse vegetation communities and wind**
- **Change:** twenty-nine resident models: eight tree forms, fifteen shrubs, six ground plants; original source libraries and redistribution credits preserved.
- **Community:** two field components from 2,048 to 512 m, once per tile; 88% local dominants, 12% compatible minority forms.
- **Ground layer:** potential cover 0.18, reduced under trees and within existing patches; height distribution centred on 0.65 m, flower multiplier 0.7; at most 12% flowering choices in suitable open patches.
- **Compatibility:** grassy, warm, moist, rooted ground only; no herbs on snow, bare rock, scree, beach or water.
- **Wind:** climate vector and common weather clock; flexibility 0.012 trees / 0.048 undergrowth, force `min(wind/6,2)`; leaf flutter capped at 1.8 cm before scaling.
- **Relay:** zero motion at 160 projected pixels, full at 320; static impostors and whole-plant placement retained.
- **Budgets:** fir models at most 48,000 triangles to retain needle coverage; new grass and flowers below 1,000; six renderer queues remain 192 MiB, command storage 2,136 bytes.
- **Terrain:** unchanged; only placed model detail and its vertex animation change.
- **Checks:** Release x64; asset structure and ten hidden native views, queue bounds, repeated identities and fixed feet under wind time; cold forest witness checked separately from the obsolete ocean location.
- **Review:** `tools/tests/2026-11-02-vegetation.txt`; captures under `x64/VegetationDiversity/checks`; no Computer Use or interactive launch.
- **Status:** uncommitted work, no milestone tag or publication; no performance/quality benchmark run or AAA quality claim.


**2026-11-03 · Superseded first rendering revision**

- Exact source wood through L4, L0 39,933 triangles for the oak.
- Closed-crown sky transport near 0.21; no metric close-bark layer.
- Interactive smoothing defaulted off while fade noise changed every frame.
- Hidden helpers set MYPLANETENGINE_TAA=0; presence-only parsing actually enabled smoothing.
- Their 38 root/level/contact captures and six cloud/ocean/orbit controls remain functional evidence for that executable.
- They do not establish parity with the unsmoothed interactive setting or acceptance of the present revision.
- The contact control changed 17.7% of one root view; ocean and orbit controls were bit-identical.
- The planar kapok remained an explicitly rejected diagnostic witness; it was not a production model.

**2026-11-03 · Near vegetation geometry and lighting**

- **Report:** stretched branch faces, coarse approach and flat vegetation lighting.
- **Geometry:** seven levels; exact source wood/UVs through L4; curved leaves and multiple shoot rows through L2.
- **Budget:** 88% planning target, 90% maximum per reduction, final tree cap 3,000 triangles.
- **Selection:** projected-size ratio 1.55 for seven-level assets; legacy spacing retained for five-level assets.
- **Normals:** 65% source curvature and 35% crown gradient on individual leaves; woody normals and source GLBs unchanged.
- **Materials:** normalized wrapped two-face diffusion, transmission 0.45 and dielectric GGX; lighting masks separate shoots from leaves.
- **Canopy:** intercepted-sun scatter 0.12 with colour weights 0.45/0.65/0.32; solar attribution retained for cloud shadows.
- **Contact:** half-resolution horizon AO, eight directions and three radial samples, support 1.2 m.
- **Sun contacts:** six steps to 1.28 m; direct and indirect light remain separate.
- **Range:** contact fade from 96 to 192 m; bilateral reconstruction and immutable HDR distance.
- **Resources:** one RG16F half-resolution image; existing queues and synchronization retained.
- **Generation:** dedicated ComfyUI on port 8190 with E: paths; configuration errors preserve modelling budgets.
- **Recovery:** restore 34 modelling budgets after verified prompt-configuration rejections; queue a clean oak first and retain previous artifacts.
- **Review:** tools/tests/2026-11-03-vegetation-render.txt; hidden screenshots and stream checks, without performance acceptance.
- **Checks:** four seven-level surface/material audits and 38 native captures pass; contact control changes 17.7% of the root view without raising its displayed peak.
- **Integration:** six cloud/ocean/orbit controls pass; ocean and orbit stay bit-identical with contacts enabled or disabled.
- **Limits:** screen-space contacts do not replace long off-screen tree shadows; source branch cycles and planar candidates still need art replacement.
- **Status:** uncommitted; no tag or publication requested; previous checkpoints moved to log/spec-pipeline-creation3d-historique.md.
