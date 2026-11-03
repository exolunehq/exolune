# Vegetation generation: tool selection

**Status and decision**

- Survey checked on 2026-11-02 against vendor documentation, public repositories and research papers.
- The user prefers a new artistic foundation over extending the existing model libraries.
- The current 31-model catalogue is a technical prototype, not an accepted artistic baseline.
- Latest user direction: reject FoliMesh after the native POC looks worse than the previous vegetation; continue the work in the other active conversation.
- Premium paid packs remain alternatives after native import and quality are established.
- Local ComfyUI generation remains experimental; the linked Tripo oak was rejected for its cartoon style.
- Current workflow assessment and first completed Pixal3D trial: `recherche-comfyui-vegetation.md`.
- FoliMesh is excluded from further trials; its POC and superseded recommendations are archived in `log/recherche-generation-vegetale-historique.md`.
- Compare actual exported neural assets with the biome boards before choosing a production tool.
- The default game catalogue was not replaced by the external FoliMesh POC.
- A broad survey cannot establish that every available service has been found.

**What the generator must deliver**

- Mature expressive trunks and asymmetric, substantial crowns.
- Roots and buttresses that can be fitted to Exolune's existing terrain.
- Reproducible generation inputs and stable seeds; editable species recipes where the tool supports them.
- Structural variants that retain a coherent species and art direction after selection.
- Separate woody and leafy materials, with usable opacity and textures.
- A low-cost representation of foliage, not merely a reduced solid canopy.
- Exported meshes usable by the native Direct3D renderer.
- Dimensions, material slots and variation parameters that remain reproducible offline.
- Artist review of close views, slopes, several sun directions and aerial approach.
- Existing placement, wind and impostor cooking remain useful downstream stages.
- No inference or external API call is needed during gameplay.

**Priority candidates**

| Candidate | Verified approach | Fit and unresolved evidence |
|---|---|---|
| [TRELLIS.2](https://github.com/microsoft/TRELLIS.2) | Direct image-to-3D neural generation; open surfaces, opacity and PBR; MIT model/code | Strong direct-generation trial candidate; a full editable species recipe, branch semantics and matching foliage LODs are not established by the documented output |
| [Tripo P1](https://docs.tripo3d.ai/model-generation/text-to-model-p1-20260311.html) | Direct generation with model/texture seeds, PBR and a face limit of 48–20,000 | Useful neural comparison; repeating a seed reproduces an asset, but a new seed is not a constrained morphological variation of the same species recipe |
| [Tripo H3.1](https://docs.tripo3d.ai/model-generation/image-to-model-v3-0-v3-1.html) | Higher-fidelity generation, material/alignment controls and optional mesh reduction | Deferred after the public oak's art direction was rejected; any future trial must inspect actual crown, branch gaps and roots |
| [Meshy](https://docs.meshy.ai/en/api/image-to-3d) | Image-to-3D and Smart Topology with controllable output budgets | Useful alternative neural trial; do not infer foliage hierarchy or wind-ready branch structure from a low polygon count |
| [PlantFactory](https://www.bentley.com/products/e-on-software/) | Professional procedural plant authoring and editable plant content; free perpetual versions | Strong cost and morphology reference; discontinued development, 2024 beta and background automation need evaluation; prefer production 2023 for an initial trial |
| [SpeedTree](https://unity.com/products/speedtree) | Specialized procedural modeling, editable plant graphs and game exports | Production candidate for controlled variations; Indie USD 19/month plus optional Games library USD 999/year; eligibility, subscription terms and native wind integration need review |

**Rejected FoliMesh trial**

- The user closed this route after native review on 2026-11-02.
- Acquisition notes, source provenance, technical checks and reproduction commands are archived in `log/recherche-generation-vegetale-historique.md`.

**Other specialized generators checked**

| Tool | Evidence and reason to retain or defer |
|---|---|
| [Midori](https://github.com/splatterfacegames/midori) | CLI, TOML species recipes, seeded batches, glTF, foliage materials, LOD budgets and Pivot Painter data; MIT/Apache code; engine validation and groundcover remain explicitly incomplete |
| [SeedThree](https://github.com/SkyeShark/SeedThree) | MIT, parametric trees and desert plants, generated textures, LOD/export pipeline; declared alpha; useful open authoring base, no established final artistic quality |
| [EZ-Tree](https://github.com/dgreenheck/ez-tree) | Tunable standalone library, seed, GLB export and LOD generation; inspect mature silhouettes and roots before considering it a production asset source |
| [TurboTwig](https://www.turbotwig.com/) | MIT browser L-systems, wind and glTF advertised; version 0.0.0 indicates an early candidate |
| [Druidoo](https://www.druidoo.com/) | Specialized standalone parameter-driven trees; public page lacks enough distribution, license and batch-workflow detail for selection |
| [Infinity Generation](https://www.infinitygeneration.com/) | Alpha procedural platform, space-colonization/L-system trees and static export; broader runtime platform adds integration scope beyond the immediate asset need |
| [Tree Generator](https://tree-generator.com/) | Beta procedural editor plus AI texture/mesh features; desktop export advertised at USD 19.99 once; verify stable local automation and export quality |
| [Tree It](https://www.evolved-software.com/treeit/treeit) | Free dedicated game tree generator, LODs, mesh export and wind data; limited ongoing development; evaluate fresh recipes rather than reusing the old Exolune pine |
| [The Grove](https://www.thegrove3d.com/learn/faq/) | Growth-based Blender/Houdini generator; vendor explicitly says its stock detailed twigs are unsuitable for games and that it has no game-specific LOD generator |
| [GrowFX](https://exlevel.com/) | Specialized procedural plants, merged trunk/branch surfaces, MAXScript and wind; requires a separate 3ds Max toolchain |
| [Houdini Labs Tree Tools](https://www.sidefx.com/docs/houdini/labs/) | Authorable trunk, branch, leaf and hierarchy nodes; [leaf variants/cards](https://www.sidefx.com/docs/houdini/nodes/sop/labs--tree_leaf_generator.html) and [root shaping](https://www.sidefx.com/docs/houdini/nodes/sop/labs--tree_trunk_generator-.html); substantial separate authoring toolchain |
| [Sapling Tree Gen](https://extensions.blender.org/add-ons/sapling-tree-gen/) | Blender parameter-based generator; optimization, foliage art and root design still need a deliberate authoring pass |
| [Modular Tree](https://github.com/MaximeHerpin/modular_tree/releases) | Specialized Blender generator with programmable branching; release notes identify missing material/root features; cannot assume a complete game asset pipeline |

**Additional neural and material routes**

- [Hyper3D Rodin](https://hyper3d.ai/) provides direct generation, partial editing, spatial controls and an API/MCP; vegetation-specific recipes and foliage LODs are not established by its public description.
- [Hunyuan3D](https://intl.cloud.tencent.com/document/product/1284/75540?lang=en) provides general image/text geometry and PBR; evaluate it as a general 3D candidate, not a proven vegetation specialist.
- [Autoregressive Generation of Static and Growing Trees](https://arxiv.org/html/2502.04762v1) demonstrates a genuinely tree-specific learned skeleton; its leaves are added procedurally.
- [DivineTree](https://github.com/xujiabo/DivineTree) publishes graph-based trees, diffusion weights and image/point-cloud guidance examples; a game pipeline, production reliability and redistribution terms still need audit.
- [ForestGen3D](https://arxiv.org/abs/2509.16346) targets LiDAR forest structure, not ready-to-render game vegetation.
- [3DTexel's atlas generator](https://3dtexel.com/atlas-generator/) targets transparent vegetation atlases with material maps; useful for original leaf bouquets coupled to an editable structural generator.
- Neural atlas generation can provide a visual signature without surrendering control over branching, card density and variation.
- Do not treat normals or roughness derived from an image as independently measured physical material data.

**Libraries checked as references**

- [Quaternius Stylized Nature MegaKit](https://quaternius.com/packs/stylizednaturemegakit.html) has a CC0 standard edition and a consistent game vocabulary.
- The standard archive was retrieved from the creator's [Godot store listing](https://store.godotengine.org/asset/quaternius/stylized-nature-megakit/); hash `298f6732b872e4cf7b30e6e7abf9641c7f6dc6b326df37ac089533ed7e3d58c9`.
- Its preview is substantially more stylized and saturated than the boards; do not silently adopt it as the new art direction.
- [NatureManufacture](https://naturemanufacture.artstation.com/projects/2xbJ3y) offers scanned, atlased game vegetation; a useful visual comparison, with finite authored variants and package-specific integration.
- [Globe Plants](https://globeplants.com/blogs/news/how-to-import-and-optimize-globe-plants-3d-models-in-unreal-engine-for-architectural-visualization) supports vegetation import and optimization; verify each product's game geometry rather than assuming every architectural plant is suitable.
- [Botaniq](https://polygoniq.com/3d/botaniq/) is primarily a plant library for Blender; its existence does not supply the desired editable species generator.
- [PhytoEngine](https://phytoengine.com/llms.txt) has a public query API and cached procedural GLBs; its read API responded locally, but descriptions of current features and licensing differ across its pages.
- The sampled PhytoEngine query included a fallen birch and a grass tuft in a generic forest result; resolve explicit asset metadata before judging biome suitability.
- No library sample above has been promoted into Exolune's default catalogue during this survey.

**Premium game vegetation, rechecked 2026-11-02**

- The user explicitly requests a parallel reassessment of FoliMesh and premium paid libraries.
- Prices below are displayed USD prices before taxes; confirm the selected offer at checkout.
- Counts describe advertised contents, not verified independent species or accepted structural variants.
- No premium pack was acquired or inspected as exported geometry during this reassessment.

| Candidate | Verified advertised diversity | Displayed cost | Exolune assessment |
|---|---|---|---|
| [NatureManufacture Forest](https://assetstore.unity.com/packages/3d/vegetation/forest-environment-dynamic-nature-150668) | 13 beech tree objects, 10 shrubs, 29 herb/plant objects, 16 mushrooms | USD 60 | First authored game-pack comparison; mature trees, modular roots, atlases and LODs; a complete temperate scene does not imply many tree species |
| [NatureManufacture Environment Bundle](https://assetstore.unity.com/packages/3d/vegetation/environment-bundle-dynamic-nature-199045) | 56 tree objects, 27 shrubs in 8 types, 180+ grass variants; 1,400+ prefabs include non-plant scenery and systems | USD 343; [Mountain](https://assetstore.unity.com/packages/3d/vegetation/mountain-environment-dynamic-nature-191851) alone USD 75 | Broader library to consider after one source model is validated; total prefabs are not botanical diversity |
| [BK Pure Nature 2 Swamp](https://assetstore.unity.com/packages/3d/environments/pure-nature-2-swamp-324967) and [Jungle](https://assetstore.unity.com/packages/3d/environments/pure-nature-2-jungle-296552) | Swamp 88 meshes / 84 prefabs; Jungle 102 meshes / 112 prefabs; whole environments, not tree counts | USD 50 per biome | Substantial rooted game forms, but fantasy styling may depart from the boards; Unity package, raw source formats and conversion unverified |
| [MAWI Redwood](https://www.mawiunited.com/fab/rw/mw_rw_description.html), [Broadleaf](https://www.mawiunited.com/fab/bf/mw_bf_description.html), [Conifer](https://www.mawiunited.com/fab/cf/mw_cf_description.html) | Respectively 2 species / 19 tree forms, 2 / 23 and 1 / 15; saplings included | From USD 249.99 per biome on the [official Fab shop](https://www.fab.com/sellers/MAWI%20United?lang=fr) | Premium visual comparison, deferred for native integration; Unreal delivery, Nanite/Lumen/VSM/RVT dependencies, no independent GLB/FBX delivery verified |

- SpeedTree's editable Games library provides randomisation and seasons; no verified current inventory supports an exact species count here.
- Its advertised FBX/OBJ, atlases and LOD exports suit an independent engine; proprietary wind still needs a compatible implementation.
- [Current SpeedTree terms](https://unity.com/legal/professional-artistry-additional-terms), section 2.7, restrict new distributions/platforms after termination unless the applicable offer states otherwise.
- Do not budget a single month as perpetual authoring and release rights without verifying that offer.
- [Unity's official guidance](https://support.unity.com/hc/en-us/articles/34387186019988-Can-I-use-assets-from-the-Asset-Store-with-other-engines) permits other engines subject to the EULA and separately licensed components.
- NatureManufacture lists some wind files under Unity Companion License; keep Exolune's own shaders instead of copying those files into the native engine.
- MAWI's procedural features concern biome placement; do not count them as an exportable species-variation generator.
- Keep source packages and cooked proprietary assets outside the public repository; track licence references and import manifests.

**MAWI testability before purchase**

- The user finds the rendering compelling but needs evidence of native integration and performance before buying.
- Official [Broadleaf V4](https://mawiunited.artstation.com/projects/qQlnky) and [Redwood UE5.1 V4.1.0](https://mawiunited.artstation.com/projects/yJ8qxx) announcements describe free runtime demos.
- No working direct demo download or freely exportable representative tree was verified in the current survey.
- A compiled Unreal demo can assess that scene's appearance and behaviour; Exolune needs a separate representative mesh/material import trial.
- The old Redwood announcement lists 2–5 million triangles per large sequoia; this is version-specific evidence, not a count for every current MAWI tree.
- [Current Redwood delivery](https://www.fab.com/listings/ff5dbf6c-f88c-4bd9-846b-5a739fdc3058) lists Unreal Engine and Nanite/Lumen/VSM/RVT requirements; an independent FBX/GLB delivery is not promised there.
- A useful evaluation sample includes one mature tree and one understory plant, their source geometry, textures, material layout and permission to evaluate a native-engine conversion.
- Inspect topology, foliage coverage, root volume, material reconstruction, wind and reduction before committing to a pack.
- Keep MAWI as a visual comparison until an export trial establishes that enough of its close quality survives Exolune's representations and budgets.

**Local feasibility**

- Read-only hardware inventory: NVIDIA RTX 4070 Ti, approximately 12 GiB VRAM.
- The Microsoft reference implementation's 24 GiB requirement does not establish the limit of current ComfyUI integrations.
- Native ComfyUI supports Pixal3D and TRELLIS.2 with published INT8 checkpoints.
- A native Pixal3D INT8 1024 trial completed on this workstation; its fused foliage does not meet the close-up target.
- The small source crop limits the conclusion; settings, actual renders and provenance are recorded in `recherche-comfyui-vegetation.md` and its linked trial manifest.
- This is a compatibility check, not a performance benchmark.

**Recommended trial**

- Use NatureManufacture Forest as an authored game-asset comparison before considering a larger bundle.
- Keep local Pixal3D/TRELLIS.2 as research; a complete higher-resolution reference is required before judging the neural full-tree approach.
- Compare a specialized generative recipe against a direct neural result using the user's boards.
- Require several structural variants, not only rotation, tint or non-uniform scale.
- Inspect all sides, branch junctions, crown volume, rooted base and material separation.
- Separate tree species, genuinely different branch structures, age, season, tint, LOD and placement-prefab counts.
- Inspect static geometry first, then animate through Exolune; a vendor viewer's movement does not prove portable wind data.
- Bring a small selected set into Exolune and cook its own impostors.
- Review ground and approach views without interactive automation or Computer Use.
- Count preparation/rework and service costs before deciding that a nominally cheaper generator is more efficient.
- Keep generation offline and place only a bounded cooked variant pool at runtime.
- Artist acceptance of this small set precedes expansion across all eight biomes.

**Tripo cover verification, 2026-11-02**

- The user circles the mature rooted tree in the cover of [Tripo's generator comparison](https://www.tripo3d.ai/blog/tree-model-generator).
- The article labels it as its cover image; it compares several tools and does not associate this particular tree with an inspectable model or generation settings.
- This establishes the image's editorial role, not whether it came from a 3D render, image generation or another authoring process.
- No verified provenance or exported geometry was found for the circled tree.
- A separate [public oak example](https://studio.tripo3d.ai/3d-model/create-multiple-variants-of-oak-trees-9f502ac3-67cf-42ad-bda8-159e83f26f6a) is labeled 4K, PBR and Tripo H3.1; its prompt asks for oak variants.
- That public listing is evidence of a published Tripo example, not validation of its hidden geometry, cost or suitability in Exolune.
- The official H3 API documentation recommends its high-fidelity line and supports multi-view input through a separate endpoint.
- Its Smart Low Poly option warns about failure on complex models.
- The article acknowledges possible solid foliage and additional preparation for leaf cards, LODs, pivots, collision and wind.
- An exported model trial remains necessary; no Tripo model has been generated or imported during this verification.
- The user subsequently inspected the linked oak and rejected its cartoon direction; the cover remains a target image, not proof of Tripo output.

**Interpretation**

- FoliMesh is rejected after native review; artistic quality, coherent structural variation and native-engine portability remain the selection criteria for other sources.
- Direct neural 3D is promising, especially for expressive trunks or unusual specimens, but is not automatically a complete forest-production system.
- [Tripo's own tree workflow](https://www.tripo3d.ai/blog/tree-model-generator) acknowledges possible solid foliage and additional work for LODs, leaf cards, pivots, collision and wind.
- MCP is a control interface; the generator, source materials and review process determine the resulting craft.
- A specialized Blender generator can preserve skilled procedural design; writing generic tree geometry through a script alone does not supply that design.
