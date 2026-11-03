# Vegetation diversity and near-ground wind

**Status**
- Technical prototype implemented on 2026-11-02; artistic replacement under investigation.
- The user's boards and selected generative or premium authored sources take priority over retaining the old library.
- Current direction and tool selection: `direction-artistique-vegetation.md`, `recherche-generation-vegetale.md`.
- Extend the detailed vegetation renderer, not the planet's terrain or climate model.
- The former fourteen-model catalogue remains a compatible fallback.
- Build and functional validation use background processes and hidden renders.
- The user requests end-to-end validation; previous witness measurements do not validate the current root/light revision or a diverse library.
- Uncommitted work has no milestone tag; tags must identify committed states.

**Catalogue**
- Thirty-one prototype models: three conifer forms, five broadleaf forms, fifteen shrubs and eight ground plants.
- `game_biomes_v1` replaces photographic fir companions with variations of the original game pine.
- The twelve baseline shrubs and four additional Rakshi broadleaf prefabs remain temporary source material.
- Add Poly Haven upright edge shrubs and another Searsia architecture.
- Add two sorrel forms, two tall-grass forms, two flowering plants and two fern forms.
- Prototype conifers: 6,411–7,107 triangles; broadleaves: 3,600–7,794 triangles, including roots.
- Grass and flowers: 290–758 triangles; ferns: 2,248–2,384 triangles.
- Preserve textures, opacity, normals and roughness; bake each model's own impostors and light data.
- Sources are CC0 or CC BY; credits and pinned hashes remain with the reproducible asset pipeline.
- Models are architectural game forms, not a simulated census of terrestrial botanical species.
- An external `FOLBIO03 91` review bank adds thirty tree and thirty shrub roles across the six climate families.
- Sixty distinct text-guided recipes target five woody architectures per kind and family; queued or rejected work is never counted as finished.
- Each cooked master also derives three offline structural variations; their own LODs, impostors and acceptance remain required before use.
- The active cap is 96 roles; all offline species and variations cannot be assumed simultaneously resident.
- Detailed authoring and validation contract: `spec-pipeline-creation3d.md`.

**Coherent communities**
- Existing season, aridity, temperature, exposure and conifer share admit compatible model pools.
- A shared spatial field spans 2,048 to 512 m; two components serve trees and undergrowth.
- Compute the community field once per placement tile.
- Eighty-eight percent of choices follow two continuously blended local dominants.
- Twelve percent supplies compatible minority forms.
- Dry and cold shrubs keep their sparse or low architectures.
- Upright leafy companions occur in temperate/tropical communities; leafy Searsia needs warm, sufficiently moist ground.
- Selection depends on the world's field and stable seed, never time, camera distance or GPU completion order.
- Mesh and impostor carry the same model identity.
- Tree family selection reads climate temperature and dryness, not the packed crown-spread field.
- The population grid, cover laws and rooted terrain remain shared with the existing system.

**Ground layer**
- Add a bounded herb footprint to the placement's shrub channel; do not create a separate long instance queue.
- Potential cover ceiling: 32%; reduce it under trees and modulate it with existing thicket patches.
- Require a suitable growing season and humidity; allow forest litter as well as grassy material.
- Exclude snow, bare rock, scree, beach and submerged roots.
- Source height distribution centres on 0.65 m; individual flowers use a 0.7 height multiplier.
- Open places favour tall grass; warmer moist undergrowth favours fern masses with sorrel companions.
- Dryness warms green ground foliage toward straw while preserving flower colours.
- Flowers occupy at most 12% of suitable open-ground herb choices, within spatial patches.
- The light pass bounds meadow and woody maxima separately; a densely wooded bound cannot discard clearing herbs.
- Existing whole-plant appearance and mesh/impostor transitions also apply to the ground layer.
- Ground plants add local detail; the distant woody canopy does not count them as shrubs.
- Foliage bounds, scaling and HiZ read the same instance height metadata.

**Wind**
- Read the existing local climate wind; transform it into the terrain face frame.
- Use the common weather clock, including deterministic hidden captures and films.
- Bend with squared local height; the rooted base remains fixed.
- Add a small leaf flutter using the model's leaf-material mask.
- Smooth triangle waves avoid per-plant CPU animation or a bone system.
- Base flexibility: 0.012 for trees, 0.048 for undergrowth; force scales with wind/6 m/s and caps at 2.
- Leaf flutter caps at 1.8 cm before wind scaling.
- Motion fades from zero at 160 projected pixels to full strength at 320 pixels.
- Wind reaches zero before the model relay; distant impostors remain static and retain their validated depth bound.
- Depth and colour passes use the same vertex deformation and frame constants.
- Inter-tree collisions, exact branch mechanics and player interaction remain outside this animation model.

**Rooted prototype**
- Strengthen lower stems and leaf bouquets offline; keep the actual trunk base at the placement origin.
- Prototype trees have a flared collar and seven curved roots; generated sources retain their own authored root structure.
- `form.bin` stores independent crown width so root bounds cannot shrink the crown.
- Root reach follows `max(0.085 * size * spread * ownWidth, 0.14)` metres; canonical source proportions are baked before LODs and proxies.
- Four terrain contacts use the existing exact-ground cache's third float; height remains in the first.
- Generated root undersides use one continuous supported master; near LODs protect the base and coarse LODs inherit it with explicit error bounds.
- Rooted trunks skip legacy burial extrusion; runtime fitting never squeezes root XZ independently of height.
- Smoothly fit all lower wood to terrain, then fade contact out with wind before the static impostor.
- Contact burial is `min(0.25, 0.025 + 0.025 * rootRadius)` metres.
- Root-specific deformation applies only to tree species; shrubs reuse those instance fields for other metadata.
- Close trees sample the same terrain function east, west, north and south; a smooth quadratic fits the root mesh.
- Blend the tile-plane fallback toward exact contacts over 192–384 projected pixels.
- Root vertices stay fixed under wind; outer material blends toward the local ground colour.
- Four samples approximate smooth local terrain; they do not guarantee a watertight fit over arbitrary cliffs or stones.
- The sampled fit remains an approximation over abrupt relief; native art acceptance remains open.

**Forest illumination**
- Crown envelope coverage is not an opaque roof.
- `CanopyLighting.hlsli` shares porous sun transmission and sky scattering between ground and all plant paths.
- Effective gap is `1 - 0.82 * coverAbove`; direct transmission follows the existing solar slant, bounded below by a 0.15 cosine.
- Diffuse sky transport includes bounded leaf scattering and inter-layer returns; see `spec-rendu-vegetation.md`.
- Reuse existing woodland fields and widen their shade boundary over at least four metres; population and canopy coverage remain unchanged.
- Intercepted sunlight supplies bounded canopy bounce; cloud shadows retain its solar attribution.
- Two-sided leaf lighting, volume normals, GGX and local contact occlusion follow `spec-rendu-vegetation.md`.
- This is an ambient transport approximation; per-tree shadow mapping remains absent.
- Forest litter has its own ground reflectance; the orbital canopy palette remains aerial.
- A bounded world-derived observer response improves under-crown readability; open/orbital exposure remains unchanged.

**Runtime bounds**
- Preserve six renderer queues and their 192 MiB total allocation.
- Partition those queues by up to 96 models and eight representations: seven mesh levels plus the impostor.
- Seven-level generated assets preserve source wood at L1–L4 and add bounded L0 curvature; legacy five-level assets remain readable.
- Share the indirect-command layout between C++ and HLSL in `FoliageCatalog.hlsli`.
- Shared layout determines command/count/cursor storage; distinct meshes and textures have a separate resident cost.
- The mesh transition order buffer is 12 MiB; existing instance queues remain 192 MiB.
- Per-model CPU/HLSL settings are 128 bytes, including root and LOD form data.
- Use existing GPU placement, deterministic compaction, indirect draws, impostors and HiZ.
- No new per-frame CPU/GPU wait, streaming thread, middleware or runtime decoder.
- The new catalogue is selected automatically when its readiness manifest exists above the executable.
- The fourteen-model fallback disables the new herb layer; former 29/31-model prototypes remain readable.
- External generated banks are selected explicitly with `-Plantes`; they do not replace the default catalogue.

**Preparation and checks**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Build -NoLaunch
python tools/foliage/prepare_vegetation_jeu.py
powershell -NoProfile -ExecutionPolicy Bypass -File tools\tests\check_roots.ps1
python tools/tests/check_biomes.py
```
- Preparation checks pinned source hashes and cooks in the background.
- Functional checks validate mesh structure, normals, budgets, unique models and light data.
- Hidden native views cover forest, temperate ground, boreal roots, slopes, several suns, desert and approach heights.
- The earlier 38-view branch/contact review is archived; current code needs its own retained effective settings and native controls.
- The refinement revision retains 64 native stills across environment controls, roots, seven forced levels and the radial tropical candidate.
- That tropical replacement is one hybrid master, not a five-species biome collection; native art and performance remain pending.
- Check active catalogue, bounded queues, repeated identities and fixed feet under changing wind time.
- Still-capture jobs restart the temporal dither sequence, so wind comparisons do not measure unrelated relay grain.
- Root arithmetic checks cover 7,000 planes through a 24 m radius, endpoint quantization, a curved witness, fixed origin and finite storage.
- Continuous conformation checks cover thickness, coincident seams, positive Jacobian and transported normals/tangents.
- Current refinement images and controls: E:/ExoluneAssets/vegetation-refinement-2026-11-03/.
- User review route: `tools/tests/2026-11-03-vegetation-refinement.txt`; verification uses hidden captures and no Computer Use.
- Existing foliage lighting approximations, missing object collisions and known baseline quality deviations remain documented in `vegetation-planetaire.md`.
- Superseded fir assets, density and source choices are archived in `log/spec-diversite-vegetale-historique.md`.

**Research and decisions**
- [Guerrilla: GPU-based procedural placement](https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn): hierarchical ecological placement and local rules around the player.
- [Epic: PCG Biome Core](https://dev.epicgames.com/documentation/en-us/unreal-engine/procedural-content-generation-pcg-biome-core-and-sample-plugins-in-unreal-engine): data-defined biome choices and runtime hierarchical generation remain current practice.
- [Crytek: vegetation animation in Crysis](https://developer.nvidia.com/gpugems/gpugems3/part-iii-rendering/chapter-16-vegetation-procedural-animation-and-shading-crysis): separate main bending and leaf motion, smooth triangle waves and rooted deformation.
- [Poly Haven licensing](https://polyhaven.com/license): CC0 artist sources, adapted and credited in the asset catalogue.
- Retain the existing renderer's seamless representation system; add climate-compatible local variety and bounded near-ground detail.
