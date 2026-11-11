**City production experiments, 2026-11-07**

- Local evidence remains under `E:/ExoluneAssets/city-2026-11-07`.
- The first circular frontage layout and its wide paved circulation were superseded by the user's shared, nature-led solarpunk direction.
- The current planner uses habitat courts and sparse pedestrian paths instead.
- The first native captures found instance offsets applied through `StartInstanceLocation`; vertex pulling requires the explicit SRV offset.
- Those initial captures are not current validation evidence.
- The first civic TRELLIS reconstruction retained a useful detailed silhouette.
- Its woody solid-remesh and 28,000-face reduction tore thin architectural shells.
- A direct GPU reduction of the dense civic source exhausted available VRAM during concurrent GPU use.
- A CPU clustered reduction and normal-transfer experiment still produced unacceptable surface facets.
- Neither civic neural candidate is in the active review bank.
- Their raw sources, graphs, reduced meshes and comparison renders remain outside Git.
- The active civic control is a generated parametric model.
- The neural house requires the correct Blender-to-glTF UV conversion in the native cooker.
- The uncorrected textured native captures are superseded.
- No experiment in this log establishes performance acceptance.

**Superseded pilot and expansion iterations**

- The seven-court, 512 m pilot had 14 recipes, 15 buildings/infrastructure and 77 furniture/cultivation placements.
- It used a 257 × 257 terrain export, 128 × 128 exclusion mask and one combined ground draw.
- The user selected the braided archipelago for the expanded city after reviewing three masterplan proposals.
- A naive four-way subdivision of long narrow borders generated about 398,000 ground triangles.
- Boundary segmentation and longest-edge subdivision reduced this before native review; retain the final exact count in `layout.json`.
- The first seven-floor collective candidate used 89,548 triangles; removing tiny facade-fin bevels reduced its master to 57,868.
- Invalid normals on zero-area bevel triangles initially interrupted cooking of the service cabinet.
- The cooker now removes those degenerate triangles before validating normals on surviving surfaces.
- The first vehicle reference is a FLUX image; it is not 3D acceptance evidence.
- The first 512 mesh graph attempt omitted texture-stage conditioning links and was rejected before submission; all links now use the matching first-stage conditioning.

**Expansion visual corrections and vehicle candidate**

- A fixed spatial LOD dither left visible points; city transitions now share the vegetation's temporal coverage sequence.
- The first path-edge mask interpolated zero boundary distances across thin strips and removed their interiors.
- The manufactured border now owns the edge; the aggregate surface remains continuous.
- Native LOD0 controls showed that ramp and terrace artifacts also required source corrections.
- Intersecting wings now use 75 mm floor offsets, and the station ramp has 220 mm of structural thickness.
- Station and viaduct foundations receive terrain-reaching supports under their common guideway datum.
- The direct neural vehicle reduction produced 106,750 triangles despite a 32,000-face request and visibly tore the shell.
- Closed resampling produced an intact 31,750-triangle shell, but rear panels and suspension remained deformed.
- A per-face semantic material classification created visible triangular patches and was rejected.
- Bounded normal/metallic/roughness factors improved the material response but did not repair the geometry.
- Horizontal principal-axis alignment revealed a 15.21 m length and 4.26 m width; the candidate does not fit the current lane spacing.
- The neural vehicle is not in the active bank. The generated procedural train remains the review model.
- Expansion experiments remain under `E:/ExoluneAssets/city-2026-11-07-expansion`; superseded captures are not final validation.

- Material-neutral native captures isolated remaining distant holes from the lighting model.
- The GLB's UV/normal splits left geometric face islands disconnected during decimation.
- A focused reservoir comparison confirmed that welding within each source part before reduction preserves its closed wall.
- The current cooker recovers adjacency within 1 micrometre and rejects newly opened closed parts.
- Missing custom corner normals after a valid reduction fall back to the geometric face normal.
- Full-bank captures before this correction are superseded by the subsequent exact-bank review.

- After seam repair, native captures exposed flat source normals on curved glazing. Those sources now carry analytic wall normals with independent planar cap normals.

**Superseded expansion bank**

- The expansion witness had 37 recipes, 122 building/infrastructure, 212 furniture/cultivation and 22 transport placements.
- Thirty-six recipes were placed; the agricultural canopy remained in the library.
- It stored 1,441,755 triangles across five LOD slots and 81.27 MiB of vertex/index data.
- Manufactured ground had 92,904 triangles; the largest collective had 57,868 LOD0 triangles and the train 9,136.
- Release x64, four seeded CPU cases, twelve native views and three startup controls passed for that exact witness.
- Ordinary and out-of-range control images matched exactly; an absent city emitted no colour or shadow draws.
- Those results are archived expansion evidence, not validation of a later bank.

**Detail iterations**

- Initial virtual interiors and emissive trim used values incompatible with Exolune's normalized solar units and burned out to white.
- The corrected shader separates indirect virtual-room radiance from sunlight and uses bounded normalized emission.
- Close review exposed a ground-floor guardrail crossing an entrance. A capped source Boolean now opens the public approach before reduction.
- The first porch used separate rectangular returns and a flat canopy. It was replaced by a connected U-shaped manufactured profile.
- The first bench had protruding slat bars, unsupported backrest pieces and a floating light strip. A connected seat cradle, curved boards and mounting straps replace that arrangement.
- The first train had oversized floating window hoops and a generic suspension pipe. The hoops now fit the ovoid; a forged yoke and conformal roof saddle express the support interface.
- A topology gate caught four reversed saddle wall boundaries; corrected face winding passes the same check without loosening it.
- Closed tube endcaps retain independent normals to remove curled-looking highlights.
- A neural-house camera initially intersected the outer arch. Moving the review camera outside exposed the actual remaining source defects.
- The neural close view rejects the current source as a finished FPS building: uneven ceramic, fused foliage/furniture and stretched surface detail remain.
- Source and screenshot iterations are retained under `E:/ExoluneAssets/city-2026-11-07-detail`; artistic and performance gates remain open.

- The first complete close route exposed a civic planter in front of a door and greenhouse ribs crossing the central access. Planter spacing and a connected vestibule replace those arrangements.
- A nine-ray approach check then caught a hangar shell and a rotated courtyard reveal missed by the old centre-only facade ray. Attachment now samples doorway width and standing height.
- The station close camera was below its elevated source footing. Captures now use the source entry datum and pinned terrain height.
- Near trees hid the hangar and helical variant in intermediate views; corrected camera positions expose those targets without removing vegetation.
- Intermediate normalized trim emission of 0.9 still emphasized distant outlines. Daylight trim is now 0.055, with 0.30 reserved for night; silhouette antialiasing remains a separate open review item.
- The 24 intermediate captures are retained in `native-before-access-review` under the detail output directory.

**Pixal3D architecture comparison: rejected 1,024-resolution reductions**

- The exact isolated house image is reused from `city-2026-11-07/neural-house/reference/306431de32f33568/image.png` on E:.
- Its SHA-256 is `2cad3917b45415e4d193a38ef70e19688dd7790e9cf242790a744578866fadda`.
- The native graph uses the installed quantized Pixal3D checkpoint, preserved surfaces and a 28,000-face request.
- Graph, model fingerprints and history belong to `city-2026-11-07-detail/comparison-pixal/wood_mesh/7cb39ab297e43b92`.
- The dense source contains 12,941,310 triangles; SHA-256 `4bf56af6237d71f2f0f2352f45a26f6c6a86115056e83567118016d5e0c45361`.
- GPU simplification progressed too slowly under shared memory pressure; the owned job was interrupted and its saved dense source retained. The PBR stage is incomplete.
- CPU QEM with a 1 micrometre source-unit adjacency weld still exported 4,119,341 triangles and severe triangular tears.
- CPU voxel reconstruction at 384 followed by QEM reached 25,257 triangles but removed much of the thin shell. Reject this result despite its budget compliance.
- The original dense quarter view is cleaner than both reductions. These failures do not establish that the model itself generated all the reduction damage.
- CPU neutral-material front/back/street views separate geometry defects from texturing. They are diagnostic images, not in-game acceptance.
- Raw output, reduction reports and rendered views are retained outside Git. No failed candidate replaces the active house.
- Both the generation backend and reduction differ from the original solid-resampled TRELLIS witness; this is a workflow comparison, not an isolated model ranking.

**Pixal3D native 512 comparison: completed and rejected**

- The second graph bypasses shape upsampling and uses the matching first-stage texture conditioning on the same pinned image.
- Its key is `74410018338d297e`; all seven expected artifacts completed under `comparison-pixal512/wood_mesh`.
- The dense source has 3,174,648 triangles; SHA-256 `5a2acc71ccd7ea33c3784bf151554efabf04f69e2aa39b4455df1d20af97724c`.
- GPU QEM stops at 61,780 triangles for a request of 28,000. The final GLB exports 108,323 vertices.
- The UV report contains 25,722 charts; its packing progress counter was 51,444, not the final chart count.
- Base colour, tangent normal, roughness and metallic maps are all 2,048 square pixels.
- Final GLB SHA-256: `c0028541bd5951d316b2f77bbb0eabb83f0ee7050fe823d6b27f2cfaf26194bd`.
- Three dense neutral views retain the organic composition but expose small surface defects, fused objects and an underdeveloped rear.
- Three reduced neutral views and three PBR views show severe triangular shell tears on every side. The material maps do not repair these geometric defects.
- `geometry-result.json` and `inspection.json` retain actual counts, fingerprints and explicit rejection. The candidate was not cooked into the active city.
- The shared-GPU run is an execution and art experiment only; its duration is not a performance comparison.
- The owned ComfyUI service was closed after its queue completed. Other engine sessions were retained.

**Final detail route correction**

- The updated placement omitted the former cascade recipe, so the wide route silently contained eleven views.
- It now targets the placed garden-step variant and rejects a missing required target instead of silently skipping it.
- The final twelve wide and twelve close views pass exact bank/executable/shader verification. Explicit artistic judgements remain separate from those checks.
**Superseded detail bank · 2026-11-07**

- `E:/ExoluneAssets/city-2026-11-07-detail` retained 41 recipes, 362 placements, 127 building/infrastructure placements and 253 audited connected manufactured parts.
- Stored geometry contained 1,779,003 triangles across five LOD slots and 100.11 MiB of vertex/index data. Manufactured ground contained 94,737 triangles.
- Twelve district views and twelve close views were bound to the exact executable, shaders, textures and placement scene.
- The original neural house remained a rejected FPS-quality witness. The shell-house finishing work replaces that review role with a directed reconstruction and structural variant.
- Old palettes remain historical witnesses for that bank; they do not certify the later house bank.

**Flat ground rule · until 2026-11-11**

- The planner rejected water below 2 m, path slopes above 8 % and building support relief above 0.5 m.
- It therefore rejected the former site at −11.04, 49.784: its fixed network would cross the new river banks above the 8 % grade.
- The 2026-11-10 bank moved 700 m west, to −11.04, 49.7776, where no probe cell exceeds an 8 % slope.
- The hill-site rule replaces it: graded foundations, stepped paths up to 30 % and a stated river surface (`../spec-ville-procedurale.md#hill-sites`).

**Built supports on hill sites · 2026-11-11, replaced by earthworks the same day**

- The deck stood at the footprint's highest ground. The planet's relief was never cut; the downhill side rose on walls or posts.
- Foundation by relief: a slab up to 0.5 m; a terrace up to 4 m, its stone wall leaning 0.12 m per metre under a 0.12 m coping; stilts up to 10 m, a timber frame in the manner of a hillside temple stage.
- The frame: a 0.35 m deck; 0.28 × 0.40 m beams along every grid line; octagonal posts on a grid of at most 4.2 m, thickening with height; 0.8 m stone footings; tie beams every 2.4 m down. Stone piers and sills closed the edge where the ground met the deck.
- A 0.7 m walkway and 1 m timber railings closed every edge higher than 1 m. An entrance stair left the deck where the access line crossed its edge.
- `delivery-02-collines` placed 119 buildings: 59 terraces, 58 decks on stilts, 2 slabs, 3,753 steps. `delivery-04` placed 127: 70 terraces, 57 decks on stilts.
- The user found them too cubic and asked for earthworks in the texture of the ground (`../spec-ville-procedurale.md#earthworks`).
