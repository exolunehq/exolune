# Inland water

**Status: first implementation, 2026-11-01, erosion branch.**
- Requested addition of rivers and lakes to the existing erosion network.
- Flight review: `tools/tests/2026-11-01-rivieres-lacs.txt`.
- Extended review: `tools/tests/2026-11-01-rivieres-montagne.txt`, eighteen views; F1–F6 add three river sites at 4,678–4,915 m, each with an overview and a close approach.
- All eighteen views have buttons in the windowed Tests palette; F1–F12 select the first twelve. The original twelve composition witnesses are retained.
- Launch erosion review with `-SansNuages`; N can restore the clouds during flight. This changes visibility, not terrain generation.
- No new simulation during flight.
- **Since 2026-11-03, with erosion steps A and B on,** rivers come from step B's corridors (`spec-erosion.md`, step B); terminal lakes keep this spec's stage slices. The same water outputs feed the pixel refinement, vegetation, contact and audio.
- **Current sizing:** explicit rivers above 300 m³/s, fading to full width by 450; dry notches from 200. Smaller rivers are omitted, so old river views may now contain only terrain, sea or lakes.
- **Composed water:** river depth remains bounded by the blended compact cut. Physical bank incision is now clipped before filtering; wet fraction and mean depth travel separately through mesh, fine and screen samples. An unresolved river no longer lowers its whole footprint to its stage. Terminal lakes retain their stage.
- **Current review:** `tools/tests/2026-11-04-embouchures.txt`, covering orbit-to-ground continuity, confluences, banks and first-water contacts; prior upstream morphology is retained.
- **Approach reconstruction:** water coverage, stage/depth moments and premultiplied flow now use the same positive B-spline as terrain. Resolution changes and pixel contour refinement mix those moments before reconstructing conditional water values.
- **Physical refinement:** tributaries open locally at their junction; low-coast marine courses split into three procedural distributaries sharing the parent discharge. Bank-height octaves and bank proximity use the same terrain queries as contact and grounded objects (`spec-erosion.md`). Detailed coastal connectivity and sediment evolution remain unresolved.
- **First-water termination:** cached shoreline contacts stop the visible reach and its downstream discharge contribution. Independent local sources survive. Resolved water shading reads the actual stage/bed gap; a tributary no longer contributes a pale closing bank inside the receiving course. The additional cache occupies 24 MiB; no performance benchmark was requested.

**Flight review: structural revision in progress**
- The user accepted coastal contour antialiasing and river bank contours after pixel refinement; earlier river visibility is sufficient for this stage. The mountain blur and crawl reported from orbit at `1673620.9 -7.138614 122.604860 84.18 32.74` are corrected by the screen relief, validated in flight on 2026-11-02 (`spec-rendu-lointain.md`).
- Coherent fine-grid height/normal reconstruction now addresses the mountain sampling transitions; `spec-normales-spline.md` and `tools/tests/2026-11-01-montagnes-distance.txt` describe the separate flight review. Prescribed incision shapes remain open.
- The user validated disappearance of the artificial side trenches at F7/F8 of `2026-11-01-rivieres-montagne.txt`; this is a local acceptance result, not global erosion acceptance.
- Every release review must name the corrected defect, the expected observation and the unresolved defects; diagnostic witnesses are not advertised as completed fixes.
- The reported defects include late water visibility, uniform ribbon widths, geometric junctions, closed outlets, perched channels and coastal serrations.
- These are separate failure modes; improving water visibility cannot validate drainage geometry.
- The signed residual formerly excavated false side trenches beside a perched channel, even with coastal erosion disabled; the reproduction is archived in the erosion log.
- The current channel width depends on discharge; its prescribed section dominates the detailed bank contour.
- The network samples the coarse pre-erosion terrain at cell centres; rendered nodes are jittered and the query is warped afterwards.
- Monotone stages on this graph do not prove a descending, connected route through the finished terrain.
- A coarse sea flag does not certify an outlet through the detailed coast.
- The former fine shading grid omitted water and was capped by coarse wetness; its replacement is described below.
- Targeted observations and exact reproduction poses are in [the erosion log](log/spec-erosion-historique.md#2026-11-01-hydrology-composition-audit).

**All reported defects remain in scope**

| Report | Acceptance condition | Current status |
|---|---|---|
| Artificial side pools and perched channels | The original ground is not cut into deeper parallel trenches; wet centre remains | Reported F7/F8 accepted by the user; broader terrain checks pass |
| Huge orbital coast blocks and flicker | Continuous coast classification across mesh triangles and approaches | Coastal contour correction accepted by the user; similar mountain artifacts remain open |
| Late river/erosion appearance, moving scars | Coherent physical surface and wet extent through continuous approach/retreat | River contours and earlier visibility accepted for this stage; further visibility improvement deferred. Upstream profile filtering, silhouette and full LOD acceptance remain open |
| Uniform ribbons and geometric confluences | Banks, discharge and local terrain determine the section and path | Discharge sizing and composed-water bound awaiting flight review; physical confluence widening remains open |
| Closed outlets and deltas | A descending wet route reaches the detailed sea/lake; branches conserve discharge | Connectivity revision open |
| Repeated mountain scratches and summit cuts | Relief-dependent incision preserves different histories and material responses | Incision/routing revision open |
| Crater cuts and rivers leading nowhere | Closed basins retain water or have a resolved spillway; construction history is respected | Volcanic integration open |
| Coastal sawteeth, crest flicker and disappearing cliffs | Stable visible surface through approach and across steep slopes | Earlier projection/coastal metric corrections are limited; rendering investigation open |
| Camera crossing a cliff | Swept contact protects camera and hull along the movement, with no ground teleport | Swept contact integrated; CPU fixtures, Release x64 and interactive startup pass; the user found the two cliff-contact views of `2026-11-02-vallees-orbite.txt` okay, 2026-11-02 |
| Lake shores and stage connections | Level basin interiors, coherent shorelines and explicit outlet transitions | Initial lake implementation; connection refinement open |
| Lake level fixed per erosion cell; lake district fragmenting on approach | A continuous lake level first; then a statistical wet coverage keeps the district whole at every distance | Open; a statistical coverage on the per-cell level made square blocks and was rejected (`log/spec-rendu-lointain-historique.md`) |
| Rivers perched on a mound | The channel follows the lowest route of the composed terrain; network and relief agree where the river is drawn | Open; part of the network placement revision |
| Valleys appearing suddenly from orbit, 1,400 to 1,800 km | Valleys fade in continuously with distance, their mean kept, like any other relief | Corrected and validated in flight, 2026-11-02: each section clipped by the ground before averaging (`spec-erosion.md`); `tools/tests/2026-11-02-vallees-orbite.txt` |
| Cost of the transition zone near 300 km | The pixel water contour query fits the frame budget where the screen relief fades in | Open; 16 ms at 250 km after the channel rung, 2026-11-06 |
| Root cause: a network computed on coarse relief, then pressed onto it | Paths, widths and junctions follow the rendered terrain; nothing reads as hand-drawn | Open; addressed by the network placement and connectivity revisions below |

**First composition correction, 2026-11-01**
- The cut envelope carries only positive terrain spurs; original hollows remain in the terrain being intersected.
- A compact C1 positive part reuses the 60 m join scale; its rounding raises the cut envelope by at most 15 m, never the original terrain.
- Fine residual detail can no longer excavate below the valley envelope.
- The fluvial floor includes the channel width, within the existing influence limit, and continues through terminal segments.
- The 60 m shoulder join fades to zero on the physical floor, which reaches its drainage profile even for shallow cuts. Existing lower hollows remain.
- Water cutting is bounded by the difference between the paired channel envelopes; it cannot excavate an additional V valley.
- All ten water-presence witnesses pass after coupling the floor and the join. This does not certify complete downstream connectivity.
- An absolute cap from the existing coarse incision map was rejected: mismatched terrain samples made valid river witnesses dry. The prototype and measurements are archived in the erosion log.
- No new terrain setting, map, simulation or extra terrain query is introduced.
- The width law, coarse paths, volcanic drainage and late visibility still require the remaining revision below.

**Proposed correction order**
1. Validate the first composition correction in flight, including mountains and volcanic bowls. Preserve pre-existing hollows; never raise them with an independent water-level clamp. Check slope continuity and tributary competition as well as height bounds.
2. Couple channel geometry and wet extent. Use discharge as a capacity constraint; derive the water contour from the resulting terrain section. Banks, bed and water must describe one surface construction. Avoid independent width noise or decorative meanders.
3. Reconcile network placement with terrain. Sample the terrain at the positions used by the network. Where coarse connections fail, test one bounded startup refinement of existing links, shared junctions and outlets. Cache the result; do not add recursive per-pixel routing or simulation during flight.
4. Verify downstream connectivity on the finished bed. Deposits and coastal finishing must preserve a route to a connected sea or lake. An estuary may widen where its section allows it; branching deltas require shared physical branches with a divided parent discharge. The current procedural distributaries supply those sections but do not resolve their downstream routing through the detailed coast. Retain level lake interiors; stage interpolation alone is not a spillway.
5. Filter the same physical bed and wet coverage for all rendering resolutions. Carry water information through the existing fine grid. Evaluate the physical wet extent before averaging; a coarse dry vertex must not erase a resolved fine channel.
- Start with composition and section shape before deciding whether additional network data are necessary.
- This proposal retains the existing climate, discharge and basin graph as the starting point; the finer routing method is not yet selected or costed.
- Any startup refinement must fit the existing planetary memory and startup budgets; no budget increase is assumed.
- Coastal silhouette, mesh and normal defects remain a separate rendering investigation; hydrological consistency alone does not fix them.
- Young volcanic construction must not inherit an old substrate's incision automatically. The existing freshness field affects detail and materials, but does not directly constrain the drainage solve. This integration remains open.
- Acceptance requires several rivers, confluences, lakes and coast types, followed through continuous approaches and retreats. Coordinates identify regressions, never generation exceptions.

**One drainage network**
- Rivers use the same warped quadratic links, discharge and stage as the valleys.
- The level-0 solve and its original six texture slices are unchanged.
- Six additional `R32G32_UINT` slices store terminal lake stage and basin ID across each catchment.
- Receiver-first propagation keeps one stage for every terminal basin.
- Basin ID zero denotes ocean drainage.
- Cache version `EXOEROS6` includes conditioned course fields and first-water contacts; startup rebuilds obsolete caches.
- The current erosion texture has 24 RG32 slices and occupies 48 MiB at 512 cells per face. Contact limits, surviving discharge and local runoff account for the latest 24 MiB increase.
- Rendered step-B courses stop at the first lake or sea contact on the actual ravine/coastal substrate, before river incision. Interrupted upstream flow is removed from downstream accumulation; local sources and other tributaries remain.
- Coastal and river erosion intersect independently; coastal remapping must not excavate a second sea basin into an already lowered river floor. Fan coverage is an exact union including contained branches.
- A surviving midpoint on an interrupted edge keeps its source discharge on both sides; receiving-node runoff cannot attenuate it before the contact.
- Mouth opening uses physical distance to that contact and joins the receiving water level. Lake and sea use the same rule; a delta's sediment evolution remains outside this implementation.
- Contact lookup is cached. Per-frame terrain queries are not added to search for a shoreline.
- The probe's finite resolution and the existing network threshold limit small-pond and minor-stream routing. Terminal lakes do not gain an invented outflow.

**Legacy channel geometry (`EROSION_RAVINES = false`)**
- Half-width is `max(1, 2.4 sqrt(Q))` metres, with discharge Q in m³/s.
- Depth is `clamp(0.35 Q^0.3, 0.15, 20)` metres, fading in from Q=0.05 to 0.5.
- These coefficients are engine calibration, not a calibrated hydrodynamic model.
- A compact quartic cut meets the bank with zero depth and zero derivative.
- An exact local box mean uses the existing `max(cellMetres, 2 m)` radius.
- The channel cuts after terrain finishing, including deposits and coastal barriers.
- Two continuous lower envelopes carry the section with and without its channel cut.
- The upper envelope intersects the finished terrain to give the candidate water surface.
- The bed is lowered by at most the difference between the envelopes; the resulting positive depth determines water presence.
- Taking their minima preserves continuity where links compete.
- A winning link's independent stage must never flood an unrelated hollow or form a water wall.
- `EROSION_WATER = 0` removes channel cutting and terminal lake filling.

**Lakes and rendering**
- Terminal lakes fill detailed terrain up to their catchment's constant stage.
- A continuous four-tap reconstruction joins distinct terminal stages over a 2 km half-width around coarse divides.
- Basin interiors stay level; the connecting bands are approximations, not resolved lake spillways.
- The terrain mesh carries both raw ground and the visible water surface.
- Lakes follow a sphere at constant sea-level altitude; they do not receive ocean FFT displacement.
- Rivers share the atmosphere reflection and depth attenuation used by the sea.
- Small planet-anchored ripples move downstream and fade below the pixel footprint.
- Two 64-second advection phases blend continuously; this is surface animation, not fluid transport.
- Dry floodplains at the drainage stage stay dry.
- The mesh and fine grid carry wet presence, premultiplied stage and premultiplied depth from the same terrain evaluation.
- Step B carries physical wet fraction and mean depth, including dry area; stage is premultiplied by that fraction. An unresolved river can lie below mean terrain without lowering the whole sample to its stage. Pixel refinement uses this same fraction and a separate lake contour.
- Dry samples contribute no water stage; conditional stage/depth are decoded after interpolation.
- Fine water replaces coarse water with the same border weight as fine elevation; a dry coarse vertex no longer suppresses resolved fine water.
- Ocean coverage remains the ground/sea intersection; inland coverage overlays it continuously, without a Boolean switch on interpolated altitude.
- The two existing fine buffers use a 32-byte sample: terrain/normal, premultiplied inland water and a contour-candidate distance.
- The mesh carries the same candidate distance; neither a coarse nor a fine dry sample excludes a river passing between samples.
- Near unresolved coast, channel or mixed lake boundaries, the pixel shader refines the water at half the pixel footprint, with the existing 2 m physical floor.
- **Candidate bands, since 2026-11-07:** a channel's band where the grid's edge distance is within 0.6 to 0.9 samples, formerly 2 to 3 (2026-11-06). Partly wet samples are candidates at a lake's shore only: along a river they spread its filtered wetness over the band already kept. Images within 8/255 of the 0.4 bands; at 0.2, spots of 24/255 in a meander's bend.
- **Past the band and any lake, no channel water from the grid** (`PixelShader.hlsl`): the B-spline spread a narrow channel's filtered wetness over three samples, a halo the photographs show no trace of.
- **The inland reflection's sky in three steps,** the sea's in six (`Sea.hlsli`, `gReflectionSteps`): the same image within 1/255.
- **The channel rung lists only wet nodes, since 2026-11-07,** gated by their channels' reach, not their valleys', or only those the fine grid's four samples recorded near it (`spec-erosion.md`, the contour's nodes). 97 km's contour from 2.5 to 1.3 ms with the shared listing's changes.
- **Two rungs, since 2026-11-06.** A shore is the terrain's own level line: within two height bands of the sea's or a lake's level, the whole shared terrain at the pixel. A channel is narrower than the grid's samples, its valley is not: elsewhere, the grid's ground and the channels alone at the pixel (`gErosionWater`, `spec-erosion.md`).
- The channel rung gives the full query's wet fraction, stage, cut and current. Its depth omits the terrain's clamps; its images match the whole relief's within 7/255.
- Coast candidates in the band's fade keep the channel rung: the grid's height lies past any shore there. A valley's steep walls, unresolved by the grid, widened that band along every river.
- Candidate bands use sample size; the final wet/dry transition uses pixel derivatives. All four derivative lanes evaluate together, using fine derivative reductions. A GPU wave runs one rung, never both in turn.
- The refined water sample also supplies its stage, depth and flow. Exactly zero clearance remains dry.
- Land material heights, normals, depth and silhouettes retain their existing sampling; this contour query does not refine geometry.
- Storage is 72 bytes per mesh vertex and 32 bytes per fine sample, including step B's independent mean depth and coverage; no new resource binding or simulation.
- A shared immutable 4 KiB noise table is appended to the frame constants; CPU and compute use the same gradient literals.
- The terrain VS and PS both use DXC, with identical varying packing. Existing unrelated shaders keep their compiler settings.
- Cost varies with boundary coverage and terrain complexity. Step B integrates one local channel section; the full two-dimensional union at confluences, variable terrain and lake-district wet area remain approximate or open.
- Near objects, cached plant feet and distant vegetation reject submerged ground.
- Flight clearance follows the visible surface; terrestrial habitat audio excludes submerged ground.

**Verification**
- Release x64 build through `tools/lance.ps1 -Build -NoLaunch`.
- `tools/hydro/verifie_mise_en_eau.py`: independent section quadrature, overlapping tributaries, all level-0 receiver links, terminal basin stages and ten terrain windows at 2 m and 16 m mesh cells.
- A 512-border convergence check distinguishes continuous stage transitions from grid steps.
- The original drainage words match the pre-water cache byte for byte.
- No performance or image-quality benchmark is part of this change.
- Native captures confirm visible river water, near/far plant exclusion, lake shores and continuous sampled basin connections.
- The corrected reported river loses its two artificial side pools and crosses the former shoulder-join barrier; its regular ribbon shape remains.
- The mountain comparison retains the overall massif but still shows systematic network incisions; composition bounds do not validate naturalness.
- The wide outlet view also exposes a premature termination on detailed dry terrain; it remains in the flight route.
- `tools/hydro/verifie_composition.py` checks cut-only composition, the valley-envelope bound, shallow-floor drainage, compact channel depth, tributary competition and six terrain windows.
- The full `verifie_mise_en_eau.py` passes, including wet presence in ten terrain windows; sampled profile continuity is not proof of a complete river.
- `tools/tests/2026-11-01-eau-orbite.txt` separates orbital coast checks, water approach checks and previous geometry regressions.
- Its F7/F8 retain the accepted side-trench views; F9/F10 show mountain water and F11/F12 show lake shores. Six additional palette buttons exercise the new interactive contact solver.
- `tools/hydro/verifie_contours.py` checks derivative-quad participation, sliding-grid candidate detection, explicit bed/water intersection and dry-floor coverage. `water_rung` checks the channel rung against the full query on the CPU port.
- `tools/tests/2026-11-06-contour.txt` reviews both rungs in flight: rivers from 250 km to 2,200 m, mouths, a delta and lake shores.
- Native 120-frame sequences reproduce the latest orbital pose and the reported river approach from 18,045.3 m to 14,271 m; clouds are hidden and TAA is not enabled.
- The inspected sequence frames show a finer orbital coast and strongly reduced bank steps; water remains visible through the sampled river approach. A real channel interruption and regular paths remain.
- The lake and high-mountain captures retain water; the mountain banks improve but the prescribed straight route remains apparent.
- Interactive F7/F8 still have no artificial side trenches. F1 starts at the latest reported orbital pose, with free camera and speed 5.77.
- Moving camera, 2026-11-06: the contour costs 16.4 ms at 250 km, 5.3 ms at 97 km and 0.9 ms at 2,200 m; before its rungs 21.6, 11.1 and 2.4 ms (`diagnostic-orbite.md`).
- Broader continuous flight remains required; these short reproductions do not establish global temporal stability. Exact observations and superseded captures are in [the erosion log](log/spec-erosion-historique.md#2026-11-01-pixel-water-contour-refinement).

**Limits**
- This adds visible water to the current coarse drainage network; it does not solve shallow-water dynamics.
- Existing fine hollows below both channel envelopes are preserved and can interrupt a river outside a terminal lake.
- Coarse marine outlets can still end on detailed dry terrain; reaching a level-0 sea cell does not prove a visible ocean connection.
- Long uniform reaches and angular coarse-network bends remain visible; water makes their regularity more apparent.
- Only terminal water-balance lakes are filled; small perched lakes and fine tributaries are not invented.
- Catchment boundaries still come from level 0; their connecting water bands can slope and need further in-flight review.
- No waterfalls, river ice, swimming, underwater view, bank sediment textures or water interaction are included.
- Full wet-area conservation below a pixel is not implemented; very narrow distant channels can still fade or disappear.

**Volcanic context**
- Volcanic deposits erode from their formation; age, material resistance and climate affect the result ([NPS](https://www.nps.gov/subjects/volcanoes/erosional-volcanic-landforms.htm)).
- A volcanic basin need not have a surface outlet: Crater Lake balances precipitation with evaporation and seepage ([NPS](https://www.nps.gov/places/crater-lake.htm)).
- These examples motivate coherent construction history and basin connectivity, not a blanket volcanic erosion exclusion.
