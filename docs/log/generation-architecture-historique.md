**Local architectural generation experiments**

**2026-11-08 · Same inhabited-shell house**

- Current decision: [architectural generation](../recherche-generation-architecture.md).
- Evidence root: `E:/ExoluneAssets/architecture-2026-11-08`.
- All weights, references, GLBs, latent dumps and CPU renders remain outside Git.
- No candidate was promoted, cooked into the city bank or accepted for native performance.
- No performance or quality benchmark was run. Shared-GPU execution times are not comparisons.
- Release x64 build passes after the tool changes.
- Proposed tag `piste/2026-11-08-architecture-multivue` awaits a requested commit; no tag points at an unchanged base.

**Inputs and controls**

- Original prepared image: `E:/ExoluneAssets/city-2026-11-07/neural-house/reference/306431de32f33568/image.png`.
- Original SHA-256: `2cad3917b45415e4d193a38ef70e19688dd7790e9cf242790a744578866fadda`.
- Local FLUX cleanup removes loose furniture and plants while retaining the two inhabited shells and arch.
- Cleaned image SHA-256: `86004de57cd2324c9de448fcf7b58e5e22d7318f343ee022bb19bd0b51906db9`.
- The cleanup image is a 2D intermediate, not an inferred 3D result.
- BiRefNet preparation produces separately fingerprinted white-background inputs for PartCrafter.
- Pixal uses the native front/left/back/right rig: 20-degree horizontal field of view, zero elevation, normalized source bounds and recorded camera transforms.
- The first rig renders the earlier dense Pixal512 source; the second renders the current TRELLIS house with fitted entrance parts.
- These are reconstruction controls. They do not provide independently verified hidden sides or establish the quality of a separately generated turnaround sheet.
- All geometry experiments use seed 42. The image cleanup uses seed 419308.

**Completed results**

| Candidate directory | Actual triangles | Finding |
|---|---:|---|
| `pixal-multiview512` | 7,808,426 | Broad form retained; creases, pinholes and fused contents remain or worsen. |
| `pixal-multiview-trellis512` | 4,030,580 | Better broad continuity; new surface speckles/holes and a weak hidden side remain. |
| `partcrafter-six` | 1,027,174 | Six decoded parts, but floating shells, missing supports and many fragments. |
| `partcrafter-clean-six` | 2,833,854 | Six more meaningful parts; clearer envelope/glazing/platform separation. Shell dents and deficient openings remain. |
| `partcrafter-clean-qem28k` | 28,082 | Broad form survives reduction; density-only allocation over-reduces the smallest parts. |
| `partcrafter-clean-qem28k-reserved` | 27,992 | A 500-triangle minimum per part improves small-element retention within the same total request. Still fails source acceptance. |
| `lato-dense-5000` | 7,672 | Whole house loses facade and roof continuity. Closed rebuilt edges do not imply a usable building. |
| `lato-upper-shell-5000` | 9,470 | Isolated upper envelope is more coherent; jagged boundaries, dents and inconsistent winding remain. |
| `lato-upper-front-5000` | 9,580 | Lower conditioning view improves the aperture evidence. Orientation repair succeeds, but manufactured surfaces remain degraded. |

**Pixal settings and review**

- Native ComfyUI multiview conditioning and the separately downloaded quantized multiview checkpoint.
- First 512 shape stage; no 1,024 upsampling, QEM or texture stage in these controls.
- Calibrated source images, graph, camera manifest, model hashes, prompt ID and execution history accompany each output.
- All three output views per candidate were inspected: front quarter, back quarter and top.
- The second run removes some prior crease amplification but does not establish a cleaner source than its input.
- Reject both outputs as finished architectural masters.

**PartCrafter settings and review**

- Official repository revision `3d773bf02fad51c7ab31a5615573fec93b287b30` in an isolated Python 3.11 environment.
- Six parts, 1,024 tokens per part, 50 steps, guidance 7, dense depth 8 and hierarchical depth 9.
- Local weights only; image encoder, transformer and VAE use CPU offloading.
- An upstream callback references uninitialized image embeddings. The first attempt failed after one step and is retained as `partcrafter-callback-error` evidence.
- The study runner checkpoints the final scheduler latent without changing inference or using that callback.
- Both completed attempts decode all six parts. No failed part is replaced with dummy geometry.
- The original input produces 384 manifold-adjacency components across nominal parts. The render is not an exploded assembly; the floating pieces are actual output defects.
- Cleaning the image is the largest observed improvement in editability. It also changes conditioning, so the two attempts are not a pure model comparison.
- Part colours identify generated pieces; they are not final PBR materials.
- Direct QEM preserves object separation and avoids solid/voxel reconstruction.
- The Blender importer sees 2,833,846 triangles from the cleaned GLB, eight fewer than the raw trimesh count. Both counts and the immutable source hash are retained.
- The final reservation trial has 13,975 exported vertices and 27,992 triangles at a 7.7 m height.
- Four of six reduced parts are closed. The remaining parts retain 3 and 11 boundary edges, respectively; consistent winding alone does not pass the gate.
- Quarter/back/top/street review retains the composition but rejects dented ceramic, distorted glazing, unfinished access and irregular interfaces.
- Source cleanup and controlled aperture reconstruction remain necessary before UV/PBR baking, LOD cooking or native review.

**LATO.2 settings and review**

- LATO.2 revision `fbb1f5a5755e6db8700cf6922fd506830b7cdccd`; Windows wrapper revision `b9056ca27e6dbdfe546de4700f98afe8c1e7bcf5`.
- Separate Python 3.12 runtime; model and DINO caches on E:.
- A DINO torch-hub network probe failed during setup. Pinning the official local source and downloading its checkpoint resolved inference without a live hub request.
- All three trials request 5,000 vertices, 24 vertex-flow steps, 50 topology-flow steps, guidance 3 and one topology sample.
- The first two source renders use azimuth 45/elevation 30. The saved conditioning images were inspected.
- `--no-solidify` avoids the wrapper's interior-face removal. Raw topology and wrapper-rebuilt faces are retained in `topology.npz`.
- Whole house: 9,561 raw triangles, 7,672 rebuilt triangles, 3,989 exported vertices and 190 manifold-adjacency components after rebuilding.
- Upper envelope: 9,470 rebuilt triangles, 4,727 exported vertices and one manifold-adjacency component.
- These first two rebuilt results have no boundary/nonmanifold edges in the audit but inconsistent winding.
- An orientation-only control exports smooth normals and checks unchanged positions and undirected faces. Winding remains inconsistent and visible dents/tears persist.
- Raw, rebuilt and orientation-finished outputs are separate. Smooth shading does not repair topology or manufacture a clean shell.
- The first component conditioning view is dominated by the roof. A third controlled trial uses azimuth 55/elevation 15 on the same part, seed and vertex request.
- This view exposes the aperture more clearly. The output has 4,782 exported vertices and 9,580 rebuilt triangles; the raw graph has 11,184 triangles.
- Orientation-only repair now gives one closed, consistently oriented component with zero audited boundary/nonmanifold edges, degenerate faces or duplicates.
- Three finished views still reject crushed edge profiles and dents across the roof and support. The camera change resolves one topology gate without producing an accepted manufactured surface.
- No UV/PBR transfer is supplied by these runs.

**Reproduction and limits**

- `environment.json`, environment package snapshots, recipes and manifests pin repositories, models and source hashes.
- `tools/city/render_multiview.py` records source-normalized calibrated views.
- `architecture_study.py` saves executed Comfy API graphs and native canvases.
- `partcrafter_study.py` runs the official local implementation outside ComfyUI in its isolated environment.
- `lato_study.py` calls the same isolated runner as the ComfyUI LATO node and retains both face sets.
- `inspect_geometry.py` reports bounded topology diagnostics without art acceptance.
- Components use manifold face adjacency. Counts on a nonmanifold raw result are not a reliable number of physical objects.
- CPU source renders are geometry evidence only. They do not establish game lighting, frame cost, LOD continuity or the target art quality.
**2026-11-08 · Directed finishing of the PartCrafter house**

- **User rejection:** the separate-loft reconstruction has a modelling-clay appearance and embedded volumes without real junctions. Candidates through 07 remain rejected even where their individual parts are closed and their triangle budgets pass.
- Preserve the architectural flow of the source. The revision must establish connected structural junctions in neutral rendering before material finishing or variant production.
- The cleaned six-part reconstruction supplies the design guide. All final surfaces are rebuilt from explicit profile controls; no neural vertex reuse or automatic retopology is claimed.
- The rejected neural/QEM candidates remain immutable under `E:/ExoluneAssets/architecture-2026-11-08`.
- Finishing iterations and source/native captures are retained under `E:/ExoluneAssets/house-finish-2026-11-08`.

| Iteration | House / variant LOD0 triangles | Finding and correction |
|---|---:|---|
| 01 | 45,140 / not exported | Exceeded the 40,000 budget. The left standing probe hit the lower shell. Reduce redundant profile subdivisions and move the entry interface. |
| 02 | 33,980 / 34,448 | Closed-part topology passed. The full functional gate rejected the missing threshold role. Reconstruct an explicit sill; reduce the entrance bulge and close the rear service wall. |
| 03 | 34,088 / 34,556 | Explicit sill and clear approach. Slab bevels still consumed unnecessary triangles. |
| 04 / 05 | 31,896 / 32,364 | Four-ring formed slabs replaced bevelled triangulated caps. Five LODs, source topology and four placement seeds passed. A complete command reproduced both sources and the city bank. |
| 05 native | Same geometry | Three native views exposed repeated virtual-room floors and an inappropriate room shader on the door. Correct facade UVs and room vertical coordinates; use timber leaves and a satin entry enclosure. |
| 06–07 | 31,896 / 32,364 | Room mapping, timber doors, soffit lighting and coherent ceramic joint maps were added. User review rejected the underlying disconnected rounded envelopes; these material fixes did not establish architectural continuity. |
| 08–09 | 15,540 structural triangles | One planar domain with four apertures replaced the separate shells. A differential normal field removed triangulation-fan shading. Neutral front, street and rear views exposed excessive depth and blank flanks. |
| 10–12 | About 29,000–31,000 including fittings | Added rear taper, roof camber, matched glazing, opening systems and a shared footing. Cooking rejected null corner normals. A sampled PV grid crossed its supporting roof between samples. |
| 13–14 | Source-stage diagnostics only | PV surfaces now clip the actual supporting triangles. Equal-angle bevel offsets remove folded microscopic corners. Resampled light channels and exclusion of a tiny arch-side PV fragment complete the source corrections. |
| 15 native | 30,063 / 31,148 cooked LOD0 | Structural junctions and roof contact survive native rendering. The second export loses known material roles through `.001` display names. One virtual room per narrow pane makes repeated cubicles; an independent wood stripe creates crossed grain. Canonicalize source semantics, share house-wing UV rooms and use one coherent timber PBR field. |
| 16 native and LOD audit | 30,063 / 31,148 cooked LOD0 | Stable material roles and whole-wing rooms correct the prior defects. Independent roof/PV reductions intersect by up to 81 mm and 109 mm in LOD4. Exact projected triangle intersections also expose millimetre crossings missed by sparse probes in LOD2. Add a common bounded assembly-contact gate; do not promote this bank. |

- The first two native attempts were externally terminated by another session's benchmark cleanup. They produced no image and establish no rendering result. Captures resumed after that campaign ended.
- The source and material changes are distinct from the planetary terrain. No performance benchmark was run for this finishing work.


**2026-11-08 - Continuous-domain control: technical pass, artistic rejection**

- User finding: the resulting house remains too far from the original design. No production-art acceptance.
- Diagnosis: the connected facade loses interleaved volume depth, thin overhangs, recessed glazing and the sheltered entry. Better topology does not repair this design drift.
- The following bank record describes the completed technical control before that user decision. Retain its sources and exact captures; do not promote the house recipe.

**Retained bank evidence**

- The current review candidate is `E:/ExoluneAssets/house-finish-2026-11-08/candidate-17/bank`.
- `shell_house` stores 30,063 / 18,660 / 10,132 / 5,006 / 2,854 triangles across LOD0–4.
- `patio_house` stores 31,148 / 19,326 / 10,490 / 5,174 / 2,936 triangles across LOD0–4.
- Both houses have one connected structural skin and four apertures. Their 158 manufactured parts pass source topology and entrance checks.
- `junction-verification.json` checks the serialized roof/PV surfaces at all ten LOD slots. Minimum clearance is 4.009 mm; both LOD0 payloads are unchanged by the contact correction.
- The full bank has 41 models, 363 placements and 127 buildings. Superseded and rejected iterations remain in [architecture history](log/generation-architecture-historique.md).
- `bank/production.json` records model, placement, material and all-LOD storage counts for the exact bank.
- Storage totals are not triangles rendered per frame.
- The paired house route fingerprints the executable, shaders, textures, library and placement scene.
- `native-runtime/` retains the exact executable and shaders for review reproduction.
- Twenty native captures are inspected: twelve paired exterior views, six intermediate LOD views and two shared-material regression views. `art-review.json` retains one judgement per image; `delivery-verification.json` binds them to the exact bank.
- Structural continuity is ready for user review. Coarse close shadow edges, synthetic timber grain, sparse virtual-room detail and distant bright contours still prevent AAA art acceptance.
- CPU gates cover four placement seeds, source-relative LOD error, geometry budgets and connected manufactured-part topology.
- Exact counts and completed review evidence are recorded in the external production and delivery reports.
- `verify_delivery.py --houses` verifies the paired route before generating `tools/tests/2026-11-08-maison-variantes.txt`.
- Superseded expansion counts and captures are retained in [history](log/ville-procedurale-historique.md).
- Thin bright contours remain visibly aliased at distance; the existing temporal filter does not establish moving-camera silhouette quality.
- Procedural glazing, planted furniture and several public-building facades remain simpler than the reference boards.
- The original neural house and direct reductions remain rejected comparison witnesses outside this bank.
- `art-review.json` binds a judgement to each exact capture; its accepted flags stay false. Read these findings alongside `delivery-verification.json`.
- These are open art-review items; neither the screenshots nor geometry budgets establish performance acceptance.

**2026-11-08 · Original-board neutral master**

- The user requests one faithful master and a neutral render before texture work, LODs or variants.
- The original board is `01 — Maison à coques habitées-1.png`, SHA256 `656a48197ee9accebd1dfc1613d848cb25cb7f0d3ea54e8493540412fbd2ce88`.
- The large exterior panel is canonical. Secondary panels provide depth cues, not consistent surveyed dimensions.
- Evidence root: `E:/ExoluneAssets/house-master-2026-11-08`. Sources, images and authoring snapshots stay outside Git.

| Iteration | Finding and correction |
|---|---|
| 01–02 | Independent 3D boundaries recover the asymmetry and sheltered entry. Slanted glazing, coplanar steps and an overly blank side remain. Fit vertical panes to the actual vault and derive the stair sweep from the terrace. |
| 03 | Transverse cuts open the side. The Exact solver removes the wrong region in one cut; the Manifold result preserves the volume. A global post-cut bevel pinches existing lips and fails topology. Remove it and retain modelled lip curvature. |
| 04 | Side passage and source shape improve. A nearly collinear glazing sample still produces invalid welded topology. Remove only deviations below 0.02 mm before pane triangulation. |
| 05 | An added narrow recess makes the two levels read as an artificial slit. Reject that design change; it is absent from the canonical exterior. |
| 06–09 | Advance the living canopy and fit the rear glazing vertically. Physical-arc tangents and denser ribbon sampling improve stability but do not remove rear shading ripples. Angle-based sharp edges and sampling density alone do not fix the underlying surface. |
| 10 | Give the rear ribbon one analytic curved support surface. The manufactured lip becomes smooth. Retain a 0.01 mm cleanup bound for Boolean slivers and reject any remaining topology failure. |
| 11 | The first high-resolution render exposes similar front-ribbon ripples. Use a common analytic front depth field with a smooth living/upper-wing transition. Put the studio ground at the authored walking datum so the first tread touches it. |
| Export correction | The polygon audit misses tiny triangles introduced by export triangulation. Audit triangulated geometry; clean export slivers with a 0.1 mm bound and verify the reimported object. Material primitives must be rejoined per original object for a meaningful closure check. |
| Normal preservation | Preserve structural corner normals across export triangulation. Triangle fans otherwise stripe smooth cut reveals. Flat manufactured fittings retain their geometric face normals. |
| Review source | `maitre-neutre` retains the final source and successful GLB reimport. `presentation` contains four 1,000 × 700 diagnostic views and a 1,600 × 1,120 hero view. A separate pinned render script enlarges only the studio backdrop to keep it outside the orthographic camera footprint. |

- This source uses directed surfaces with zero neural vertices. The neutral renders are actual Blender geometry, not generated concept images.
- The delivered `maitre-neutre` source contains one house, 115,640 unreduced triangles and 181 manufactured objects. The exported GLB passes reimported closure, component, winding and degenerate-triangle checks after material seams are recovered.
- `maitre-neutre/art-review.json` binds five inspected views to the exact source and image hashes. The broad roof connection, simplified service core and inferred lateral/rear design remain open artistic judgements; no fidelity acceptance is claimed.
- One connected structural shell owns the shared wing and support junctions. Separate panes and fitted parts remain physically distinct manufactured elements.
- Source topology passing does not establish faithful art or a game budget. The rear and side remain inferred where the board is ambiguous.
- Texture, UV-detail, LOD, variant and native-bank production are deliberately not started in this stage.
- Proposed `piste/2026-11-08-maison-maitre-neutre` awaits a requested commit. The current method and command live in `../spec-ville-procedurale.md` and `../../tools/city/README.md`.

**2026-11-08 · Exploratory house and public-building series**

- The user explicitly requests house variations and public buildings after the original-reference study. Exploration now includes variants; source acceptance and native promotion remain separate.
- Evidence root: `E:/ExoluneAssets/architecture-series-2026-11-08`. The delivered neutral set is `series-v3`; earlier captures remain alongside it.

| Iteration | Observed finding and correction |
|---|---|
| Initial civic domain | A spline undershoots the thin ground ribbon and crosses the exterior. Extend the buried structural base, preserving the inhabited floor and original above-ground silhouette. |
| Public pilot renders | Civic rings read as overly heavy and the side walls are blank. Thin the apertures and cut actual transverse windows. The gallery remains part of the public-building construction, not a scaled house attachment. |
| Greenhouse entry | A straight stair intersects the curved foundation and leaves a black coplanar strip. Sweep the risers from the actual chamfered terrace contour. The corrected entry has a continuous landing. |
| Strong house offset | The low-house pilot remains closed but its large upper-wing offset produces a sharp shelf. Bound junction shear at 1.25; retain strong changes in footprint and upper height, with only small wing translations. Larger relocations require a reconstructed junction. |
| Import cleanup | Dissolving slivers before restoring glTF seam vertices opens parts. Weld geometric seams at 0.001 mm before cleanup. Use a near-coplanar diagonal rotation where collapsing the sliver would exceed the endpoint-motion bound. |
| Roof classification pilot | Selecting neutral roof colours by post-cut triangle centroid creates jagged zone boundaries. Remove that classifier from the neutral stage. Future PV zones must have authored continuous boundaries. |
| `series-v1` close review | Nearest-vertex normal restoration chooses the wrong duplicate at a material/cut seam and stripes the side aperture. Match material and original face direction across coincident corner candidates. The `series-v2` reimported house removes those stripes. |
| `series-v2` public review | The fitted facade heads still leave open wedges at their ends. Complete end bays by horizontal intersection with the actual jamb, then add continuous seals. Add rear-gallery and stair-side balustrades. The `series-v3` view closes those visible gaps. |
| Tall-house rear framing | The first fixed-distance rear view clips the foreground terrace. Fit the complete source bounds to the camera margin and render the tall model again; the retained entry view remains intentionally close. |

- These are actual GLB renders from CPU Blender, with no image-generation substitution and no neural vertices in the new sources.
- New public-building backs are design interpretations, not recovered reference evidence. Civic massing and the house's broad roof connection remain less elaborate than the original boards.
- The neutral set is not added to the existing city bank. No runtime performance measurement or artistic production acceptance is inferred from source counts.
- The delivered set retains the already reviewed house geometry snapshots and reauthors the public families. Source records identify the exact author version per model; no tool-hash equality across unrelated geometry revisions is implied.
- The reproducible recipe, authoring command and present contract live in `../spec-ville-procedurale.md` and `../../tools/city/README.md#neutral-architecture-series`.

**2026-11-08 · Runtime series integration preparation**

- The first runtime preparation retained the neutral entrance datum on the closed leaf plane. The standing-approach probe therefore intersected a civic centre stile protruding 30 mm in front of that plane.
- Derive the actual standing datum from the fitted door geometry, with 100 mm clearance in front of the leaf/frame, as in the existing door contract. Do not remove the centre stile or disable the obstruction test.
- All eight sources pass the independent standing-approach check in `city-series-2026-11-08/candidate-02`.
- The neutral sources remain immutable; reduced game derivatives retain their parent GLB and metadata hashes. The prior `candidate-01` preparation is incomplete and is not a launch bank.
- The first native low-house camera falls inside a crown. Moving all views to the front axis does not solve that particular placement: a leaning trunk still crosses the facade, and a civic camera gains another foreground tree.
- Inspect all six existing low-house placements with pinned camera tuples. Placements three and six are clear; select six for its visible collective-housing and transport context.
- Keep the other eleven original usable views. `assemble_review.py` verifies identical bank, engine and material inputs and copies native pixels unchanged into `native-selected`, retaining each origin protocol.
- Thirty intermediate captures and their judgements stay external. The selected twelve-view route is a functional user test, not an artistic or performance acceptance.
