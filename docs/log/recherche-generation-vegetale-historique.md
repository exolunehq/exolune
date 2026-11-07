# Vegetation generator selection history

**2026-11-02 · FoliMesh rejected after interactive review**

- The user judges the native POC worse than the previous vegetation and excludes this technical route.
- Further vegetation work continues in the other active conversation; no additional FoliMesh trials are planned.
- The external source, cooked catalogue and captures remain on E: as an archive.
- The default game catalogue was never replaced by this trial.
- Geometry classification: added plant-mesh detail with the original ground pivot and buried root ends; terrain and population positions were unchanged.
- Technical checks remain valid evidence of import compatibility, not artistic acceptance or measured performance.

**Superseded acquisition notes and POC plan**

**FoliMesh access and uncertainty**

- The [MCP documentation](https://folimesh.com/mcp) describes an authenticated HTTP endpoint.
- The published tool list documents species, parameter schema, statistics and balance reads.
- The home page also advertises generation/export orchestration; verify the live tool schema before promising automated exports.
- The vendor advertises three wind layers; the inspected GLB contains grey vertex tint and extra UV channels, whose wind semantics remain unverified.
- Exolune already animates foliage, but its mesh importer currently does not preserve these vendor weights or a branch hierarchy.
- [Pricing](https://folimesh.com/pricing) advertises USD 15/month for AI features and USD 39/month for MCP/API access.
- Manual procedural generation and commercial exports can instead use a one-time USD 5 pack of 30 downloads; AI and MCP are not needed for that option.
- Ordinary free editor exports are described as non-commercial.
- The [free sampler](https://folimesh.com/packs/free-sampler) separately claims commercial use; do not generalize its license to all free exports.
- It lists oak, spruce and birch, GLB LOD0–3, normal maps and editable parameter JSON; acquisition requires an email-linked order/account.
- The [pack catalogue](https://folimesh.com/packs) marks the 24-model temperate and 20-model conifer sets available; several other biomes and the 164-model bundle remain marked coming soon.
- The 180+ preset claim includes rocks and cave formations, rather than 180 botanical species.
- The [licence](https://folimesh.com/license) permits commercial game builds and conversion of paid assets, but prohibits standalone redistribution, including modified files in an open repository.
- The first exported GLB has been inspected, cooked and rendered locally; details below.
- Product claims and preview images do not establish parity with the user's target boards.

**FoliMesh non-commercial POC**

- The user confirms the current project is non-commercial and requests actual tests inside Exolune.
- The [free plan](https://folimesh.com/pricing) advertises three downloads after sign-up, GLB/FBX/OBJ and all LODs.
- The [free licence](https://folimesh.com/license), section 2.1, explicitly includes prototypes and evaluation.
- No paid plan, MCP subscription or commercial export entitlement is needed for that stated non-commercial evaluation.
- Start with one mature broadleaf export; retain its original file, textures, parameters and seed when available.
- A conifer and shrub can use the remaining free downloads after the first import is inspected.
- Use neutral mesh/material files and Exolune's own cooking, wind and distant proxies.
- The confirmed account supplied `old-oak_s1.glb`, 17,864,112 bytes; the original remains outside git on E:.
- Four exported LODs contain 225,904, 14,472, 3,954 and 1,154 triangles; the first is a hero mesh, the second is the website's game LOD0.
- The POC uses the 14,472-triangle level, with 972 woody triangles and 13,500 leaf triangles, two materials and embedded colour/normal maps.
- `tools/foliage/poc_folimesh.py` cooks its own impostors and lighting, preserves the source ground pivot and retains extra vertex attributes as a sidecar.
- Grey vertex tint is folded into native light factors; native transmission replaces the vendor's volume/specular material extensions.
- The current native height/leaf wind is used; vendor hierarchical wind and source-root terrain fitting remain future work.
- An isolated external catalogue replaces the five broadleaf roles with this single witness; other vegetation and the population remain the control.
- This is a source POC, not a coherent new biome or a demonstrated pool of variants.
- Native views reveal oversized close leaves and crown compression from the existing population's width/height calibration; art acceptance remains open.
- Material-driven woody burial now uses the catalogue's leaf mask rather than assuming a source material order.
- External POC: `E:/ExoluneAssets/FoliMesh/poc-2026-11-02/`; source hashes, licence snapshots and cooking report stay beside the files.
- Functional native checks: `tools/tests/check_folimesh.py`; review route: `tools/tests/2026-11-02-folimesh.txt`; no performance benchmark has been run.
- Release x64 and twelve paired native views pass; source meshes are drawn, queue capacity remains 192 MiB without overflow, and wind preserves identities and foot positions.

```powershell
python tools/foliage/poc_folimesh.py --source E:/ExoluneAssets/FoliMesh/poc-2026-11-02/exports/old-oak_s1.glb --out E:/ExoluneAssets/FoliMesh/poc-2026-11-02/catalogue
powershell -NoProfile -ExecutionPolicy Bypass -File tools/lance.ps1 -Parcours tools/tests/2026-11-02-folimesh.txt -Plantes E:/ExoluneAssets/FoliMesh/poc-2026-11-02/catalogue -Resolution fenetre
```

- Cooking requires a fresh destination, Python with NumPy/Pillow/Numba and the current baseline catalogue.
- Interactive review is left to the user; automated verification uses the real executable with its window hidden.

**2026-11-02 · FoliMesh GLB in the native engine**

- The user confirms non-commercial use and authorises the free native-engine POC.
- The user confirms the account and completes the GLB download; no paid plan or MCP is required.
- Source: `old-oak_s1.glb`, SHA-256 `ef601bf4f035fc846faafb65abd20b93ce97cda0bb02e06149304a9e0898f368`.
- Export metadata: generator `alardon-trees`, preset `old-oak`, seed 1; GLB written by Babylon.js 9.31.0.
- UI recipe: Realistic, PC and consoles, age 128, foliage density 5, leaf size 0.68 m, buttress setting 1.1 and six roots; no sculpt commands.
- The complete parameter JSON for this oak was not acquired; the immutable GLB and pinned cooking recipe reproduce the import.
- Hero level 225,904 triangles; game levels 14,472, 3,954 and 1,154; the POC selects exported LOD1, labelled LOD0 in the editor.
- Selected geometry: 18,711 vertices; bark 972 triangles, foliage 13,500; albedo maps 1024 square, normal maps 512 square.
- Root pivot is preserved instead of centring the canopy's bounding box; source root ends remain below Y=0.
- Source vertex colour is grey tint, not demonstrated RGB wind weights; original extra attributes are retained in `source_attributes.npz`.
- Normal scale, alpha cutouts, base colour factors and grey tint are retained; current native transmission/specular behaviour approximates the vendor's glTF extensions.
- The first paired native review exposed the existing material-order assumption in woody burial; the shader now reads the catalogue leaf mask for every source.
- The same review reveals very large near leaves and a compressed crown under the existing population's fixed width/height calibration.
- Instance calibration was unresolved at review; the user subsequently rejected this route after inspecting the native POC.
- The external catalogue uses one oak in all five broadleaf roles, as a source witness rather than a diversity implementation.
- Sources, licence snapshots, cooked binaries and native captures: `E:/ExoluneAssets/FoliMesh/poc-2026-11-02/`.
- Reproduction: `tools/foliage/poc_folimesh.py`; functional checks: `tools/tests/check_folimesh.py`; flight route: `tools/tests/2026-11-02-folimesh.txt`.
- Final Release x64 and twelve paired native captures pass after the material-mask correction; 3,404 accumulated source mesh draws across the views, no overflow, stable wind identities and feet.
- Final captures and machine-readable checks: `checks-final/` in the external POC folder; timings from functional captures are not a benchmark result.
- No proprietary binary enters git, no benchmark, purchase, commit, tag or publication.

**2026-11-02 · Reopened FoliMesh and premium libraries**

- Before the first local trial, the user found FoliMesh and Bentley previews insufficient and preferred direct neural generation.
- After inspecting the Pixal3D result and revisiting FoliMesh, the user finds FoliMesh more convincing and requests a parallel investigation.
- Premium paid game packs with broad model diversity and genuine structural variants are now an explicit alternative.
- This supersedes FoliMesh's previous exclusion from the priority trial; it does not accept a provider, authorise a purchase or validate its exported wind in Exolune.
- The parallel survey compares FoliMesh, NatureManufacture, SpeedTree, BK Pure Nature 2 and MAWI using official product and licence pages.
- FoliMesh is the next suggested export witness; NatureManufacture Forest is the suggested authored game-pack comparison.
- No account, purchase, subscription, premium download or renderer change was made during the survey.
- The earlier recommendation to start the next comparison with Pixal3D/TRELLIS.2 is superseded by this export-first selection; local neural authoring remains experimental.

**2026-11-02 · User review and CPU density comparison**

- The user finds the local model attractive; the earlier negative artistic assessment was too broad.
- Current concerns are density and canopy blocks rather than readily deformable leaves.
- This fork stays focused on ComfyUI generation; other sourcing work is separate.
- Original coloured GLB: 13,997,450 triangles / 6,796,117 vertices; unchanged after these trials.
- Tool: official gltfpack 1.3 Windows binary, MIT; archive SHA-256 `f6e9c09d66af23da3da71b86f0652d2413e81c734e0aecd1cd3d0e6e6e8645c0`.
- CPU only; no game process controlled or stopped, no GPU or quality benchmark.
- Attribute-aware simplification with permissive topology, vertex updates and a 0.01 error limit stops near 528,000 triangles, above the requested targets.
- A 0.2 error limit yields 166,955 triangles; 1.0 with a 20,000 target collapses the model and is rejected.
- Aggressive 50,000 target yields 43,206 triangles / 18,877 vertices before cleanup.
- Exact duplicate-face cleanup removes 3,047 triangles; final derivative: 40,159 triangles / 18,877 vertices, 770,652 bytes.
- Blender removes duplicate faces on import: 528,216 to 480,105; 166,955 to 129,838; 43,206 to 40,159.
- Geometry checks: finite positions, valid indices and no exact zero-area triangles in the three nonempty exports.
- Eight actual CPU renders compare quarter and walking views with identical camera, scale, light and sampling.
- Silhouette survives; close views reveal lost bark relief, colour detail and faceted crown masses.
- Exports contain one material, vertex RGB, no UVs or texture images, no skin or animation; decimation does not create leaf structure.
- Next material step: bake high-detail colour and normals onto a compact mesh; foliage representation still needs evaluation.
- Artifacts and commands: `E:/ComfyUI/output/Exolune/2026-11-02/reduction/`; audits and render paths are retained.
- Learned low-density candidates were researched, not run; current comparison in `../recherche-comfyui-vegetation.md`.

**2026-11-02 · First local Pixal3D trial**

- User authorization: start ComfyUI, load a workflow and keep models on E:.
- ComfyUI 0.43.0, frontend 1.57.6, PyTorch 2.11.0+cu128; native nodes only, offline loading, hidden server on `127.0.0.1:8188`.
- Existing E: model containers were complete and reused; six SHA-256 fingerprints are recorded in the manifest.
- Hardware: RTX 4070 Ti, 12,282 MiB VRAM; approximately 32 GiB system RAM.
- Source: first isolated mature oak on the user's temperate board, native crop `(2, 651, 210, 274)`; BiRefNet and mask crop to 1024 square with 1.1 padding.
- This small source has limited fine detail and slightly clipped outer foliage; it is a feasibility input, not a definitive model-quality test.
- Pixal3D INT8; structure 12 steps / seed 56, shape 20 steps / seed 42, refinement 12 steps / seed 42, texture 12 steps / seed 43.
- Shape resolution 1024, batch 1; MoGe estimates the horizontal field of view.
- Prompt `eef0c675-98c9-480c-a2b4-25806c354d25` completed successfully; recorded execution time 341.81 seconds, without a performance benchmark.
- Raw GLB: 6,796,117 vertices, 13,997,450 triangles, 249,523,768 bytes.
- Coloured GLB: 412,630,948 bytes; smooth normals and vertex RGB, without UV/PBR baking.
- Neither solid remeshing nor reduction was applied; the foliage defects are already present in the raw generated shape.
- Five actual CPU Blender renders inspect front, quarter, back, side and neutral geometry; display height is normalized to 8 m only for review.
- Trunk mass, branching and root flare are useful features; the crown is made of fused, crumpled surfaces rather than readable leaf clusters.
- The generated base retains a tilted soil slab from the reference; it has not been fitted to Exolune ground.
- Recommendation: do not integrate this sample; use a complete higher-resolution source before judging the full-tree approach, then compare woody structure and leafy branches separately if needed.
- No engine or catalogue change, cloud inference, Computer Use, interactive game launch, benchmark, commit or publication.
- Models were unloaded after inference; the ComfyUI server and saved workflow remain available.
- Local artifacts: `E:/ComfyUI/output/Exolune/2026-11-02/`; canvas in `E:/ComfyUI/user/default/workflows/Exolune/01_oak_pixal3d_1024.json`.
- Reproduction: `tools/foliage/comfyui/trials/2026-11-02-oak-pixal3d/`; manifest records model/input/output hashes, seeds, software and fixed graph settings.

**2026-11-02 · Superseded pre-trial state**

- Initial research prepared three official graphs but had not performed inference or located a responding ComfyUI server.
- It described a conservative 12 GiB run as plausible but unverified.
- The completed derivative above supersedes that hardware uncertainty for this input and graph; the unchanged upstream templates remain unexecuted.

**2026-11-02 · Superseded priorities**

- The first survey favored specialized parametric generation guided by AI.
- The user found FoliMesh and Bentley previews insufficient and preferred investigating direct neural generation.
- Tripo's article-cover tree supplied a closer artistic target, but its generation provenance was not established.
- The public Tripo oak example was subsequently rejected for its cartoon art direction.
- The current investigation prioritizes native local ComfyUI workflows; `../recherche-comfyui-vegetation.md`.

**2026-11-02 · Narrow original local-feasibility conclusion**

- The first hardware assessment compared the RTX 4070 Ti's 12 GiB with the Microsoft TRELLIS.2 reference implementation's 24 GiB requirement.
- It concluded that a standard reference run would need remote inference or a separately verified offloading implementation.
- That did not account for the current native ComfyUI implementation and published INT8 checkpoints.
- The subsequent research permitted a conservative local trial; its completed result is recorded above.

**2026-11-02 · Superseded ComfyUI trial plan and intermediate evidence**

**Status and recommendation**

- Checked on 2026-11-02 against current Comfy-Org documentation, workflow templates and implementation.
- The user rejects the linked Tripo oak's cartoon direction and requests local workflows suited to vegetation.
- Compare native Pixal3D and TRELLIS.2 on the same approved mature-tree image.
- Use Pixal3D multiview when genuinely consistent side views are available.
- Retain Hunyuan3D 2.1 as a geometry comparison.
- No well-documented, vegetation-specific ComfyUI model demonstrating the target FPS result was found in this survey.
- These are technically relevant candidates, not accepted models or proven forest assets.
- A native Pixal3D 1024 trial completed locally on the 12 GiB RTX 4070 Ti.
- The user finds the first local tree visually attractive; retain its artistic direction as promising.
- Production acceptance depends on reducing density, preserving surface detail and obtaining independently deformable foliage.
- Its source is a small crop from the temperate board; this result does not establish the model's limit with a better input.
- Existing models on E: were reused; no download, engine integration or GPU benchmark was needed.
- Reproduction and detailed observations: `log/recherche-generation-vegetale-historique.md`; `tools/foliage/comfyui/trials/2026-11-02-oak-pixal3d/`.


**Vegetation-specific approach**

- Start with a full mature tree matching the biome board, including roots and readable branching.
- A plain background and a complete silhouette give the reconstruction a clearer subject than a landscape board.
- Inspect untextured geometry before letting a convincing bark or leaf texture dominate the assessment.
- If full-tree reconstruction fuses the crown or loses fine structure, try trunk/roots and a leafy branch as separate authoring subjects.
- This decomposition is a proposed workflow, not a demonstrated result from a specialized plant model.
- A branch occupying the whole reconstruction volume can retain finer detail than that branch occupying a small fraction of a whole tree.
- Selected branch geometry can later supply foliage clusters and baked atlases; skilled assembly and review still matter.
- Character success is relevant experience, but a branching hierarchy with many open gaps presents a different reconstruction problem.
- Filling a broken trunk hole and filling an intentional crown gap require different decisions.
- Do not apply a whole-object watertight remesh to foliage without comparing the original silhouette and gaps.
- A foliage or forest LoRA for image generation is not evidence of a trained 3D botanical model.


**Current reduction evidence**

- CPU gltfpack 1.3 trials yield a cleaned derivative with 40,159 triangles and 18,877 vertices.
- Eight actual renders compare original and reduced meshes from identical quarter and walking cameras.
- The main silhouette remains recognizable; vertex-colour-only reduction visibly loses bark relief, colour and crown detail.
- This demonstrates density reduction, not a final low-poly material or animation pipeline.
- Exact duplicate triangles were removed; original GLBs remain unchanged.
- Reproduction and failed excessive reduction: `log/recherche-generation-vegetale-historique.md` and the trial manifest.

**Local feasibility**

- Verified hardware: RTX 4070 Ti, 12,282 MiB VRAM and approximately 32 GiB system RAM.
- The native workflows publish INT8 diffusion files; the Pixal3D file is about 5.58 GB and TRELLIS.2 about 5.25 GB on disk.
- Shape VAE, texture VAE, vision encoding, activations and post-processing need additional resources.
- ComfyUI 0.43.0 completed one Pixal3D INT8 run at 1024, batch 1, with shape and vertex colour export.
- This confirms feasibility for this subject and graph, not a peak-memory bound for other inputs or resolutions.
- Reduced resolution can remove fine leaves; memory feasibility and final quality remain separate questions.
- A successful run is required before recommending higher-resolution tree generation locally.
- The local server is available on `http://127.0.0.1:8188`; native nodes only, with offline model loading.
- Models remain in `E:/ComfyUI_Models/models`; workflow and generated files remain on E:.

**Template inspection and prepared files**

- Three unchanged MIT-licensed graphs are in `tools/foliage/comfyui/`.
- Upstream revision: `c067929d7e9cc0f3fd15be348fa1a1d85da15946`.
- `sources.json` records source URLs and SHA-256 fingerprints.
- Basic JSON structure and outer link endpoints were checked for the unchanged templates.
- The executed derivative bypasses solid remeshing and reduction, exports raw geometry and vertex colour, and retains fixed seeds.
- Its API graph completed successfully; its canvas is saved as `Exolune/01_oak_pixal3d_1024.json` in ComfyUI's workflow list.
- The generic full graph defaults to 1536 upsampling, solid remeshing and 700,000 decimated faces.
- Those are authoring defaults, not approved vegetation or runtime settings.
- The multiview crop rectangles target the original character sample and must be changed for tree views.
- A short guide lists relevant nodes, model locations and proposed trial settings.
- User reference pixels and generated meshes remain outside git; the trial manifest records their paths and SHA-256 fingerprints.


**2026-11-02 · Local pipeline comparisons and selected crown cook**

- Work stays within the local ComfyUI fork; external sourcing and engine trials belong to another task.
- Models already on E: supply FLUX.3 Image Klein, Pixal3D, TRELLIS.2 and BiRefNet; no further model was installed.
- New 1024 reference images retain the user's warm substantial oak direction and remove the original soil slab.
- Isolated-wood Pixal3D generates 3,382,042 high triangles and an 11,790-triangle material-baked low mesh; roots and thin tips remain uneven.
- A first native remesh submission fails because DynamicCombo selectors were encoded as objects; flat strings and dotted child fields fix the graph.
- TRELLIS.2 on the same bare-wood image gives a more convincing trunk and root body; selected for this witness only.
- Baking retains real predicted base colour, roughness and metallic textures plus high-to-low normals at 2048.
- Crossed whole-branch cards produce plume-like foliage at 28,091 triangles and are rejected.
- An individual generated leaf with alpha and procedural shoots reaches 29,065 triangles but has a sparse crown.
- Larger surface-bound shoots reach 39,933 triangles and improve density, but still trace the main limbs as narrow plumes.
- Crown-volume sampling, irregular envelope lobes and bounded woody connectors improve the overall mass at the same budget.
- Full selected run: `E:/ExoluneAssets/oak-witness-v1/`; generated high wood has 4,281,530 triangles.
- Final: 39,938 triangles / 48,932 file vertices; 10,450 woody triangles, 29,488 shoot/leaf triangles, 388 shoots and 4,656 curved leaf cutouts.
- Component cleanup retains 98.4388% of source woody surface; 1,326 disconnected faces are removed.
- Final dimensions: foot at Y=0, total height 8 m; two materials, masked double-sided leaves and exported vertex tint.
- Wind vectors are explicitly converted to glTF Y-up and restored to Z-up in the editable Blender scene.
- The exported-file CPU witness moves leaves by up to 0.188 m while fixed shoot attachments remain within 2.33e-10 m; this is not a native-engine wind test.
- Six native stages complete successfully; relaunches reuse their verified outputs without another inference.
- A French text-only brief also completes the image stage, prompt `2c7596c5-e4cf-4b25-90db-04329f17e681`; the complete no-reference mesh path was not repeated.
- Background views inspect the exported GLB from quarter, back, walking and roots; a fifth view shows the wind pose.
- Fine woody ends and several root tips remain torn or angular; the tree is not artistically accepted.
- Release x64 and `tools/tests/check_local3d.py` pass; no engine change, benchmark, commit, tag or publication.
- Immutable job identifiers, model fingerprints and artifact references: `tools/foliage/local3d/trials/2026-11-02-oak.json`.
- Current workflow: `../spec-pipeline-creation3d.md`.
