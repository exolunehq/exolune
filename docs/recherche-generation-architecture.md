**Local architectural generation: production decision**

**Decision, 2026-11-08**

- No tested local authoring route has yet produced an accepted faithful game house. The downstream technical chain works on the tested assets; artistic production remains unvalidated.
- The user rejects the continuous-shell pair's fidelity to the original design. Its clean junctions and low triangle count do not resolve that failure.
- Keep neural generation as design exploration or a geometric guide. PartCrafter's editable parts do not establish it as the best final-asset method.
- Controlled three-dimensional surfaces now produce a neutral house study and the explicitly requested exploratory series. This establishes editable geometry and bounded variation, not automatic design fidelity or finished game assets.
- Review each source against the original board before detailing, reduction and production promotion. Keep the dominant reference view canonical where the concept panels disagree.
- `reference_house_master.py` authors the single house study. `produce_series.py` extends it to four houses and creates two civic buildings and two greenhouses; see the [series command](../tools/city/README.md#neutral-architecture-series). Artistic acceptance remains separate from topology.
- Retain source traceability, shared cooking, bounded contacts, material export and native review. Stop extending the rejected house recipe.
- Use a hybrid pipeline with explicit responsibility for each stage.
- A complete single-image neural house remains a shape and material candidate until street-distance review passes.
- Preserve useful generated shell shapes; reconstruct defective apertures and interfaces as connected, editable surfaces.
- Use parametric source geometry for repeated floors, access, support interfaces, transport mechanics and structural variants.
- Surface detail belongs in shared UV, normal and roughness maps when it does not change the silhouette or function.
- Both routes enter the same source, LOD, material, placement and native-review gates in [the city specification](spec-ville-procedurale.md).
- This is a production-method decision, not acceptance of the current house or an AAA-quality claim.
- ComfyUI is the workflow runner; changing nodes without changing the underlying model, conditioning or reduction does not by itself improve architectural modelling.

**Hosted first draft, 2026-11-10**

- The user rejects directed and procedural Blender authoring as the source of form. It does not capture the boards' subtleties.
- The first draft must come from a generative model that outputs 3D directly. Optimization, polygon reduction and cleaning follow.
- The user accepts a hosted generator for that draft. Cooking, LODs and native review stay local.
- Tripo is the first candidate. Its H3.1 generator comes with retopology, UV, segmentation and texturing services that also accept an imported mesh.
- Seed3D 2.0 remains a geometry comparison candidate. Its only verified API is Volcano Engine Ark in mainland China; account access from France is unverified.
- No hosted model has been tested on the boards. Architecture quality stays unproven until the house pilot passes the same source gate.
- A procedural shell prototype, fused superellipsoid masses with cut openings, was shown on 2026-11-10 and rejected by the user. It is not a production route.

| Candidate | Verified capability | Access and tooling | Cost |
|---|---|---|---|
| Tripo H3.1, `v3.1-20260211` | Text, one image or four views; up to 1.5 M triangles, 2 M with detailed geometry; PBR up to 8K; optional parts | API v3 at `openapi.tripo3d.ai/v3`; official `tripo-cli` 0.9 with a bundled agent skill and an MCP mode; Python, JS, Go and Rust SDKs | 20–50 credits per model; detailed geometry +20; one credit is $0.01 |
| Tripo mesh services | Retopology v3.0 with quads, smart UV and bake; segmentation v2.0 beta; part completion; texturing | Same key; accept an uploaded GLB, FBX or OBJ up to 150 MB | 35–40, 40, 30–50 and 10–30 credits |
| Seed3D 2.0, `doubao-seed3d-2-0-260328` | One image; PBR mesh at 100 k, 500 k or 1 M faces; GLB, OBJ, USD; stated gains on sharp edges and thin walls | Volcano Engine Ark only; absent from the BytePlus ModelArk list; no CLI, MCP or retopology service found | 2.40 CNY per generation |

- Tripo result URLs expire after five minutes. Download at once and retain the task IDs with the source hashes.
- Tripo's terms give paid users the rights to their outputs and exclude them from training. A private-by-default statement and EU-specific terms were not found.
- Tripo announced the end of its v2 endpoints for 2026-11-01. Use v3 only.
- `generate_parts` excludes texture, quads and smart low-poly in the same request. Segment or retopologize in a later call.
- The H series targets dense detail; the P series targets controlled polygon counts and native quads. Compare both on the pilot before fixing the reduction route.
- Variation rule, decided 2026-11-11: one generated image per family supplies new form; procedural passes vary instances without changing form. See [generated first-draft buildings](spec-ville-procedurale.md#generated-first-draft-buildings).
- Tripo's inexpensive variation tools act on images only. The `variants` image template costs 5 to 10 credits per call; its output count is undocumented. `edit-multiview` costs 5 credits per edited view.
- Re-texturing costs 10 credits but changes only the atlas, which the city reads as material classes. A new 3D draw costs the full generation price.

**House pilot, 2026-11-10**

- Five Tripo tasks ran on the house board for 195 credits. Task IDs, hashes and review images are in `E:/ExoluneAssets/tripo-pilot-2026-11-10`.
- H3.1 with detailed geometry reproduces the board's canonical view closely: shells, elliptical eyes, porch, terrace and a coherent invented rear.
- Each draft is one fused surface of about 1.95 M triangles with 2048-pixel colour, normal and ORM maps.
- The raw board view also yields plants, furniture and an open interior, all fused into that surface. Component removal cannot separate them.
- Clean the image first. A Tripo image edit removed plants and furniture and closed the glazing while keeping proportions; the earlier FLUX clean-up had narrowed the house.
- The draft from that edited view has closed panes, mullions, sun blades, a door and steps. Use this input form.
- `auto_size` returned 7 m, 5 m and 3.5 m heights for the three drafts. Set the metric scale locally.
- A plain local collapse to 60,000 triangles dents panes and shells. It is not a production reduction.
- Tripo retopology v3.0 returns 17,498 triangles with rebaked colour and a baked normal map. Surfaces stay clean; rims soften. It caps at 20,000 triangles.
- P2 at a 50,000-triangle limit returned 45,306 triangles as a hollow shell with open glazing and an open rear. H3.1 with retopology is the retained route.
- The retopologized house runs in game through the common cooker; see the [city specification](spec-ville-procedurale.md#generated-first-draft-buildings). It matches the board at street distance.
- At walking distance its one baked atlas is blurred and smeared along the rims. Higher texture tiers do not solve this: the engine stores 1,024-pixel layers.
- The smears are the draft's own painting: soft highlights and shadows in recessed zones. They are not a retopology bake error.
- Tested and rejected: repainting the reduced atlas from the dense draft by nearest facing surface. It changed the class of 2.6 % of texels, mostly at borders.
- The draft's texture is a clean material map: about 90 % of its texels sit near five flat colours. The city now reads it as classes and renders shared materials; see [generated shell surfaces](spec-ville-procedurale.md#generated-shell-surfaces).
- The board holds a sixth material the first reading missed: opaque cladding in the glazing colour, on reveals and soffits.
- The user judged a web-studio draft of the same raw board view more precise. Its three settings, Ultra mesh, AI completion and 8K texture, map to `geometry_quality=detailed`, `enable_image_autofix=true` and `texture_quality=extreme`.
- A rerun with those settings, task `3fb50153`, cost 70 credits. It kept the density and returned an 8,192-pixel colour map, but its geometry was not more precise: the living room closed, the rear came back plain and one shell rim broke. The remaining gap is the draw, not a setting.
- The studio's Smart Mesh is P2. From the raw board view it gave 4,718 clean quads, but the furnished interior stays visible behind the glazing, props float as separate pieces and the rear is simplified. The user judged the H3.1 and retopology chain better. Through the API, P2 costs 110 credits per draft against 85 for that chain.
- Interior test, 2026-11-11: a depth map taken along the facade normal finds the openings, and a six-plane crop isolates the room behind one.
- The raw-view draft holds a coherent furnished living room of about 7 × 6 × 2.7 m: sofa, dining set, shelves, a rear window and a lit ceiling cove.
- That room alone takes 313,000 triangles, 17 % of the draft, at about 210 texels per metre. Kept as geometry it would consume the 20,000-triangle reduction; baked behind the glazing it costs none.
- Its furniture is soft at close range, and its rear window opens onto nothing. Review images are in `E:/ExoluneAssets/tripo-pilot-2026-11-10/review/interior`.
- The pilot and its extensions cost 375 credits in total. The surface work spent none.
- Still open: scanned or generated detail tiles of higher quality, and reflections of the scene in glazing.
- The user has not yet judged the drafts in game. Art acceptance stays false.

**What the current evidence establishes**

- The retained original house control originated in local FLUX image preparation and TRELLIS.2 reconstruction.
- Its original reduction requested 28,000 faces and passed through the older solid-resampling stage.
- Native close views show useful asymmetric shell composition, but irregular ceramic surfaces, texture stretching and furniture/plants fused into the source.
- Metric entrance fittings make the opening readable but do not repair those source defects.
- The neural civic and train experiments also failed their own surface/interface reviews; see [history](log/ville-procedurale-historique.md).
- These examples reject unconditional whole-building promotion, not neural generation as a category.
- The completed single-view Pixal controls fail reduction review; exact geometry and material results are in [city history](log/ville-procedurale-historique.md).
- Pixal multiview, PartCrafter and LATO.2 now have completed local house experiments; see [method study](log/generation-architecture-historique.md).
- The most useful new candidate is the cleaned-reference PartCrafter assembly followed by part-budgeted QEM: six named parts and 27,992 triangles.
- That candidate retains the broad composition but has dented shells, incomplete openings and two parts with remaining boundary defects. It is not a finished game asset.
- The whole-house LATO result loses facade continuity. Upper-envelope trials are more coherent; a lower conditioning view allows consistent winding after orientation repair, but dents and irregular edges still fail art review.
- The two Pixal multiview controls preserve massing but add surface defects and remain dense. Their calibrated views come from previous reconstructions, not independent evidence of hidden architecture.
- None of those direct neural/reduction candidates passes the source gate. Their experiment results remain separate from subsequent finishing work.
- The house-finishing branch rebuilds the reviewed design as continuous controlled surfaces and produces a structural variant through the common city chain.
- This is directed reconstruction, with zero reused neural vertices; PartCrafter supplies design evidence and decomposition, not the finished low-poly topology.
- Structural shells preserve continuous junctions before fittings are separated. The common cooker also protects declared roof/PV contacts at every LOD.
- The continuous-domain reconstruction replaces the reference's interleaved shells with a largely extruded facade. Overhang depth, thin shell edges, recessed glazing and the sheltered entry are insufficiently preserved. This is a source-modelling failure before lighting and texture quality.
- The cleaned FLUX input also changes some details and proportions. It remains conditioning evidence; the original user board is the art target.
- See [shell-house finishing](spec-ville-procedurale.md#directed-shell-house-finishing) for the source recipe, functional gates and native review procedure.
- The cleaned input is an intermediate local FLUX image edit. Its removal of plants and furniture materially improves PartCrafter's decomposition; it is not a rendered 3D result.

**Candidate assessment**

| Candidate | Useful capability | Decision for Exolune |
|---|---|---|
| TRELLIS.2 | General image-to-mesh and PBR generation; open and thin surfaces | Retain as a shell and material source. Avoid vegetation-style solid resampling on thin architectural envelopes. |
| Pixal3D | Image-aligned reconstruction; native ComfyUI integration | Tested locally at 1,024 and 512 on the pinned house. Dense shell quality is useful; neither direct reduction reaches an accepted architectural asset. |
| Pixal3D multiview | Joint conditioning on four calibrated views | Two local 512 controls completed with separate multiview weights. Useful silhouette consistency, but surface damage and millions of triangles remain. These controls do not establish performance on independently authored consistent views. |
| PartCrafter | Generates separate parts from one image | Useful editable six-part design guide in this trial. Neither its direct reduction nor the subsequent directed reconstruction has passed artistic acceptance. Segmentation alone is not architectural construction. |
| LATO.2 / ComfyUI-LATO2 | Generates vertex positions and connectivity from a source shape, with 200–5,000 vertices by default | Whole-house and two isolated-envelope tests completed. A lower conditioning view yields a closed, consistently oriented component after repair, but manufactured surface quality still fails. Keep raw and wrapper-rebuilt topology separately. No UV or PBR transfer is supplied. |
| BPT | Generates an artist mesh conditioned on a dense shape or point cloud | Available low-poly research control, not tested here. The published configuration needs about 12 GiB VRAM and does not establish accurate architectural interfaces. |
| MeshAnything V2 | Shape-conditioned low-poly generation | The official 1,600-face scope is too restricted for a complete detailed house. Consider small components only; no local architecture acceptance here. |
| SATO | Artist mesh representation with UV-chart boundaries and triangle/quad support | The inspected release contains the tokenizer; inference remains on its release list. Not a runnable generator in this production chain. |
| Hunyuan3D-Part | Segments an existing mesh and reconstructs selected parts | Potential cleanup stage, not a new whole-building generator. Verify the specific model's licence before adoption. |
| Hunyuan3D-Omni | Image plus box, point, voxel or skeleton control | Shape-control research candidate. No validated native architecture workflow here. |
| Hunyuan3D-2.1 | Shape and PBR generation | Not selected for this local comparison. Its published community licence excludes the EU, UK and South Korea from its territory. |
| AssetGen, 2026 | Research pipeline includes simplification, hidden-face removal and baked normals | Relevant engineering reference. No runnable local checkpoint was verified in the reviewed primary material. |
| Nova3D | Generates editable construction programs and named assemblies | Method reference for parametric authoring, not a replacement neural mesh checkpoint. |
| Sparse2Solid | Experimental architectural reconstruction from sparse photographs and reviewed semantic components | Useful assembly-review method. It expects evidence of architectural repetition and hidden sides; it is not a direct neural generator of solarpunk shells. |
| 3Ts architectural-design research | Experimental three-view/triplane notebooks | No packaged local production workflow or game-ready asset validation was found in the reviewed repository. |

**Reproducible comparison protocol**

- Pin the exact isolated input image, scale and orientation.
- Retain the original TRELLIS witness before any cleanup.
- `neural.py --backend pixal3d --prepared-reference <image>` produces a separately fingerprinted candidate.
- Use the same proposed 28,000-face budget and inspect the actual output count.
- Preserve thin source surfaces; report the changed reduction method alongside the changed backend.
- The original solid-resampled TRELLIS witness and preserved Pixal output are a workflow comparison, not an isolated model-ranking experiment.
- Retain native graphs, model hashes, execution history, dense source, reduced mesh and PBR maps on E:.
- Inspect front, back, roof underside, entry and street views before any runtime replacement.
- Compare aperture thickness, facade continuity, planar recesses, hidden-side coherence, material separation and reduction damage.
- A better front view alone does not pass this gate.
- The comparison directories are `E:/ExoluneAssets/city-2026-11-07-detail/comparison-pixal` and `comparison-pixal512` beside it.
- The multiview/parts/topology study is `E:/ExoluneAssets/architecture-2026-11-08`.
- `tools/city/README.md` documents the native Comfy graphs and isolated local inference runners.
- Keep the original and cleaned references separately fingerprinted. Changing the reference is a conditioning experiment, not an isolated backend ranking.
- Save camera calibration with synthetic views. Re-rendering an existing mesh tests reconstruction consistency; it cannot validate unseen design details.
- Reserve a bounded triangle budget for small functional parts before distributing the remaining budget by source density.
- Inspect final counts and topology. A minimum allocation and a closed-surface rebuild are requests, not acceptance guarantees.

**Division of work**

| Production need | Preferred route | Required evidence |
|---|---|---|
| Organic landmark silhouette | Neural candidate, then directed cleanup or reconstruction | All sides and underside; local surface error after reduction |
| Dense collective variants | Connected parametric floors, shells and reveals | Distinct silhouette, readable access and unchanged structural interfaces |
| Doors and engineering | Metric parts with explicit mating surfaces and opening systems | Close native view, source topology and interface fit |
| Grain, seams, vents, fastener sockets | Shared PBR sheets or high-to-low bake | UV continuity, correct tangent basis, filtered distant response |
| Hero material finish | Neural texture candidate on a controlled shape, where supported | Relighting test; no painted-in sun shadow; exact source provenance |
| City placement | The existing terrain-aware braided-archipelago planner | Four-seed access, support, water and spacing checks |

- Neural retexturing of an arbitrary controlled mesh is a future branch, not implemented by the current city command.
- The installed native texture-stage node expects the generator's shape latent; a mesh import alone is insufficient.
- `refine_neural.py` only adds fitted entry parts; it is not an automatic shell retopology or defective-facade reconstruction tool.
- A production reconstruction must preserve the approved silhouette while rebuilding apertures, thickness and junctions. Adding a door over a malformed facade is insufficient.
- PartCrafter is the current editability candidate, not a verified replacement for controlled reconstruction. Its part count is not a triangle budget or a guarantee of valid joints.
- The revised pair exercised neural form exploration, directed reconstruction, procedural variants and common LOD/native gates. The user rejects its design fidelity; retain it as technical evidence only.
- The separate-loft attempt was rejected for modelling-clay forms and disconnected junctions. The replacement reconstructs the house as one structural domain before adding functional parts; segmentation is not the design objective.
- Prefer the reviewed part-budgeted QEM control over LATO.2 for this house until a new result passes the same source gate. This is a decision on the tested asset and settings, not a general model ranking.
- Retain LATO.2 as a component research route. Inspect both sides and winding, preserve intentional apertures and re-bake maps onto accepted geometry. A closed result alone is not a success criterion.
- Remote Meshy/HY partner nodes inside ComfyUI are not local inference. The local-only requirement held until 2026-11-10; the user now accepts a hosted first draft, see above.
- Global city streaming, HLOD, building interiors and transport simulation remain separate runtime work.

**Next proof and stop condition**

- Establish the faithful master before imposing the final reduction ratio. Preserve long compound curves, shell thickness, glazing recesses and actual structural junctions in depth.
- Retopology can follow accepted surfaces; projection onto a defective neural surface would reproduce its defects. Reconstruct a defective patch locally and review its boundary curvature.
- Only after shape acceptance, derive the game mesh, transfer appropriate high-resolution detail, build LODs and inspect native materials and shadows.
- Generate production variants from an accepted master and its construction constraints. Explicitly requested neutral series may explore bounded changes earlier; a repeatable wrong design is not a production success.
- If the single-master shape comparison still fails, reject the authoring attempt before another city-wide cook. Consider specialist asset modelling; no autonomous AAA capability has been demonstrated here.
- Blender's [retopology tools](https://docs.blender.org/manual/en/latest/modeling/meshes/retopology.html), [surface projection](https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/shrinkwrap.html) and [high-to-low baking](https://docs.blender.org/manual/en/latest/render/cycles/baking.html) support these operations. Their availability does not validate the resulting design.

**Primary sources checked**

- [Microsoft TRELLIS.2](https://microsoft.github.io/TRELLIS.2/): representation, topology and PBR scope.
- [TencentARC Pixal3D](https://github.com/TencentARC/Pixal3D): image alignment, separate multiview weights and camera-file input.
- [ComfyUI Pixal3D guide](https://docs.comfy.org/tutorials/3d/pixal3d): native workflows and required checkpoints.
- [PartCrafter](https://github.com/wgsxm/PartCrafter): part-structured generation and scene-model scope.
- [LATO.2](https://github.com/LoHhhha/LATO.2): vertex/topology flow, count control, released weights and connectivity limitations.
- [ComfyUI-LATO2](https://github.com/sakalond/ComfyUI-LATO2): Windows integration, separate runtime, closed-surface reconstruction and thin-part limitations.
- [BPT](https://github.com/Tencent-Hunyuan/bpt): available dense-shape inference and stated memory requirement.
- [MeshAnything V2 paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Chen_MeshAnything_V2_Artist-Created_Mesh_Generation_with_Adjacent_Mesh_Tokenization_ICCV_2025_paper.pdf): training scope and topology generation.
- [SATO](https://github.com/Xrvitd/SATO): current tokenizer release and inference status.
- [ComfyUI HY partner nodes](https://blog.comfy.org/p/hunyuan-3d-advanced-features-now): remote decomposition, UV and topology services, not a local model download.
- [Meshy official ComfyUI guide](https://www.meshy.ai/tutorials/meshy-comfyui): service-backed partner integration.
- [Hunyuan3D-Part](https://github.com/Tencent-Hunyuan/Hunyuan3D-Part): P3-SAM and X-Part roles.
- [Hunyuan3D-Omni](https://github.com/Tencent-Hunyuan/Hunyuan3D-Omni): supported geometric controls.
- [Hunyuan3D-2.1 licence](https://raw.githubusercontent.com/Tencent-Hunyuan/Hunyuan3D-2.1/main/LICENSE): territorial scope.
- [AssetGen paper](https://arxiv.org/abs/2605.26137): runtime-oriented geometry and baking stages.
- [Nova3D project](https://github.com/RareSense/Nova3D): programmable construction approach.
- [Sparse2Solid](https://github.com/mattlmccoy/Sparse2Solid): architectural component reconstruction and explicit limits.
- [3Ts architectural research](https://github.com/11-685-Team-52/3Ts-Model-for-Architectural-design-process): available experimental notebooks.
- [Tripo H3.1](https://developers.tripo3d.ai/en/models/v3-1) and [image-to-model](https://developers.tripo3d.ai/en/docs/generation-image-to-model/standard): model identifiers, parameters and limits.
- [Tripo CLI](https://developers.tripo3d.ai/en/docs/cli) and [authentication](https://developers.tripo3d.ai/en/docs/authentication): installation, login, bundled agent skill and MCP mode.
- [Tripo pricing](https://developers.tripo3d.ai/en/pricing) and [terms](https://developers.tripo3d.ai/en/terms): credits, output rights and training exclusion.
- [Seed3D 2.0 release](https://seed.bytedance.com/en/blog/seed3d-2-0-released-higher-precision-and-greater-usability): inputs, outputs and stated gains.
- [Volcano Ark 3D generation](https://docs.volcengine.com/docs/ark/3d-generation?lang=zh): model identifier, endpoint and parameters.
- [BytePlus ModelArk model list](https://docs.byteplus.com/en/docs/ModelArk/model-list): no Seed3D entry found on 2026-11-10.
