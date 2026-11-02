# Inland water

**Status: first implementation, 2026-11-01, erosion branch.**
- Requested addition of rivers and lakes to the existing erosion network.
- Flight review: `tools/tests/2026-11-01-rivieres-lacs.txt`.
- Extended review: `tools/tests/2026-11-01-rivieres-montagne.txt`, eighteen views; F1–F6 add three river sites at 4,678–4,915 m, each with an overview and a close approach.
- All eighteen views have buttons in the windowed Tests palette; F1–F12 select the first twelve. The original twelve composition witnesses are retained.
- Launch erosion review with `-SansNuages`; N can restore the clouds during flight. This changes visibility, not terrain generation.
- No new simulation during flight.

**Flight review: structural revision in progress**
- The user accepted coastal contour antialiasing and river bank contours after pixel refinement; earlier river visibility is sufficient for this stage. Similar mountain artifacts remain reported at `1673620.9 -7.138614 122.604860 84.18 32.74`.
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
| Uniform ribbons and geometric confluences | Banks, discharge and local terrain determine the section and path | Structural channel/network revision open |
| Closed outlets and deltas | A descending wet route reaches the detailed sea/lake; branches conserve discharge | Connectivity revision open |
| Repeated mountain scratches and summit cuts | Relief-dependent incision preserves different histories and material responses | Incision/routing revision open |
| Crater cuts and rivers leading nowhere | Closed basins retain water or have a resolved spillway; construction history is respected | Volcanic integration open |
| Coastal sawteeth, crest flicker and disappearing cliffs | Stable visible surface through approach and across steep slopes | Earlier projection/coastal metric corrections are limited; rendering investigation open |
| Camera crossing a cliff | Swept contact protects camera and hull along the movement, with no ground teleport | Swept contact integrated; CPU fixtures, Release x64 and interactive startup pass; flight contact review open |
| Lake shores and stage connections | Level basin interiors, coherent shorelines and explicit outlet transitions | Initial lake implementation; connection refinement open |

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
4. Verify downstream connectivity on the finished bed. Deposits and coastal finishing must preserve a route to a connected sea or lake. An estuary may widen where its section allows it; branching deltas require explicit discharge-conserving links, not a generic widening mask. Retain level lake interiors; stage interpolation alone is not a spillway.
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
- Cache version `EXOEROS3` replaces `EXOEROS2`; startup rebuilds an obsolete cache.
- The erosion texture grows from 12 to 24 MiB at 512 cells per cube face.

**Channel geometry**
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
- Dry samples contribute no water stage; conditional stage/depth are decoded after interpolation.
- Fine water replaces coarse water with the same border weight as fine elevation; a dry coarse vertex no longer suppresses resolved fine water.
- Ocean coverage remains the ground/sea intersection; inland coverage overlays it continuously, without a Boolean switch on interpolated altitude.
- The two existing fine buffers use a 32-byte sample: terrain/normal, premultiplied inland water and a contour-candidate distance.
- The mesh carries the same candidate distance; neither a coarse nor a fine dry sample excludes a river passing between samples.
- Near unresolved coast, channel or mixed lake boundaries, the pixel shader evaluates the shared terrain at half the pixel footprint, with the existing 2 m physical floor.
- Candidate bands use sample size; the final wet/dry transition uses pixel derivatives. All four derivative lanes evaluate together, using fine derivative reductions without wave-operation requirements.
- The refined water sample also supplies its stage, depth and flow. Exactly zero clearance remains dry.
- Land material heights, normals, depth and silhouettes retain their existing sampling; this contour query does not refine geometry.
- Storage grows by 4 bytes per mesh vertex and 4 bytes per fine sample relative to the previous water reconstruction; no new resource binding or simulation.
- A shared immutable 4 KiB noise table is appended to the frame constants; CPU and compute use the same gradient literals.
- The terrain VS and PS both use DXC, with identical varying packing. Existing unrelated shaders keep their compiler settings.
- Cost varies with boundary coverage and terrain complexity; full wet-area integration below a pixel and upstream profile/intersection filtering remain open.
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
- `tools/hydro/verifie_contours.py` checks derivative-quad participation, sliding-grid candidate detection, explicit bed/water intersection and dry-floor coverage.
- Native 120-frame sequences reproduce the latest orbital pose and the reported river approach from 18,045.3 m to 14,271 m; clouds are hidden and TAA is not enabled.
- The inspected sequence frames show a finer orbital coast and strongly reduced bank steps; water remains visible through the sampled river approach. A real channel interruption and regular paths remain.
- The lake and high-mountain captures retain water; the mountain banks improve but the prescribed straight route remains apparent.
- Interactive F7/F8 still have no artificial side trenches. F1 starts at the latest reported orbital pose, with free camera and speed 5.77.
- The pixel query noticeably increases orbital GPU cost; it needs optimization. No controlled performance comparison was run.
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
