# Principles: correct by rules, not on a case-by-case basis

Status: reference, since 2026-10-22. Any fix and any new function complies with it; the specs detail, this file is authoritative.

## The principle

**We generate a whole planet, on a real scale, with an infinity of places and shapes. A correction that only applies to the view is almost useless, and often breaks something else.**

- **Before correcting,** ask yourself which family of problems the reported case is an example of, and which rule it violates.
- **Correct the rule, where all cases pass,** not the case.
- **Write the rule here,** with the link to the spec that details it.
- **Check on multiple locations and families,** not only on the reported view, with the benchmarks below.
- **If a specific correction is unavoidable,** a material-specific data or a calibrated setting, document it as such, with its reason and limit.

## Public Git history

**The public repository must never receive commits from the old-license history.**

- **The only remote is `origin`:** `https://github.com/exolunehq/exolune.git`.
- **Publishing a ref also publishes its ancestry.** The restriction applies to branches, tags and commits brought in by merges, even when the tip uses the current license.
- **Base new changes on the public history.** Transfer new changes without importing the old ancestry.
- **Before any requested push,** recheck the remote URLs, the selected refs and every commit that would become reachable publicly.
- **Publish only explicitly selected, verified refs.** Do not use `--all`, `--tags` or `--mirror` while legacy refs are present.

## The established rules

**Evaluate only contributions that can survive their physical filter** (`spec-erosion.md`).
- Validate flight performance with an identical moving-camera path and per-frame GPU/cadence distributions. A stationary cache hit cannot establish flight performance; isolate the costly pass and retain failed runs as failures (`diagnostic-orbite.md`).
- Read an octave's bandwidth weight before splitting its lattice or hashing its corners. A zero-weight, zero-mean octave returns zero without evaluating noise.
- A dry or interrupted tributary keeps its valley and drainage trace. Do not prepare a confluence's wet banks when its wet section is exactly absent.
- Bound spatial searches by the projection of the physical footprint, including its course halo. A tighter bound must retain every contributing course and preserve face-edge support.
- Build activity indices from the conditioned network's exact eligibility predicate. Preserve the original chart's candidate multiset, including repeated remapped cells; an index is not a new drainage network.
- Reject a node only with a conservative bound on every existing curve and connector gate. Retain floating-point reconstruction margins and a complete path when the index is unavailable.
- Reject a whole chart tile only when its enclosing sphere fails the original node gate. Include cube-face remapping, texel rounding and node jitter in that sphere; preserve the original candidate order within accepted tiles.
- Clip a chart search by the projected spherical cap of its existing node gate, including remapping and jitter margins. A cap crossing the chart horizon retains the original rectangle; never deduplicate remapped candidates.
- Optimize section integration by preserving its physical transition partition and quadrature. Coincident transitions enclose no area; an inverted capped wall still requires the original ordered intervals.
- Bound transient GPU work independently of terrain complexity. Capacity overflow must execute the complete physical query; it must never drop a river. Derive reservation limits from the actual layout to prevent integer overflow.
- Preserve composition order when scheduling ground, river and finish in separate GPU passes. Cooperative lanes must share one physical query, visit every candidate exactly once and reduce wet moments before normalization.
- When a screen stencil is missing at the planet's limb, use the existing filtered mesh/fine fallback. Do not restart the expensive pixel contour query merely because the stencil's weight is zero.
- Reuse a terrain sample only when all camera, position, bandwidth, layout and world-mode inputs are identical; retain distinct parallax evaluations. Moving the camera always invalidates a changed query.
- A ray's first evaluation only places its second. Alone on screen, it can leave out the rivers; crossfaded with another grid, it keeps them, so that both grids place the same valley floor.
- A grid no pixel reads is not computed. Under a full screen relief the fine grid serves only the limb's pixels; bound that band by the reading kernels, screen texels and fine cells, never by a viewing distance.
- A footprint wider than a startup map's cells reads the map, never a course list: the map carries the same filtered effect. A sample read only by wider pixels is filtered at their footprint, never at its own finer cell.
- Preserve the physical fields and quantify native floating-point differences separately from mathematical equivalence. Keep failed strict comparisons visible. Distance-dependent feature removal is not a performance fix.

**Hydrological consistency is checked on the composed terrain** (`spec-eaux-interieures.md`, revision requirements).
- A cut-only operation can still manufacture a false side trench; bound residual bank detail against its draining bed and verify the composed section.
- Preserve existing hollows without raising them to an independently chosen river stage.
- A monotone coarse graph and a sea-labelled cell do not prove a connected outlet through the final terrain.
- Wet extent comes from the bed, banks and water stage together; width variation or a decorative path cannot repair missing drainage.
- Filter physical wet coverage after the water/terrain intersection; averaging an unbounded profile before clipping is not equivalent.
- These requirements expose current failures; they are not a claim that the first water implementation satisfies them.
- Terrain construction and erosion must share compatible spatial support and history. A young edifice cannot inherit an old substrate's cut automatically; a closed bowl needs a resolved spillway before it can drain outward.

**Valley detail cannot manufacture a second, deeper drainage system** (`spec-erosion.md`).
- Carry positive spurs on the cut envelope; existing hollows already belong to the terrain being intersected.
- Keep the composed terrain between the original ground and its valley envelope, without an independent winning-link stage clamp.
- The liquid channel belongs within the valley floor; preserve that floor through its terminal segment.
- A shoulder join must not leave a barrier above the draining floor; let its rounding vanish on the physical floor.
- Bound the water pass's excavation by the compact channel depth; a missing outlet cannot justify an unlimited second cut.
- A coarse incision amount is not a valid local cap until its reference terrain and the rendered terrain agree.

**Inland water and its bed share continuous drainage envelopes** (`spec-eaux-interieures.md`).
- A positive altitude is not proof of inland water. Classify water from wet presence and depth, independently of ocean coverage.
- Interpolate water stage and depth premultiplied by wet presence; dry terrain must not contaminate either quantity.
- Carry flow with the same wet weight, reconstruction kernel and resolution transitions as stage and depth.
- Average the composed valley incision, including retained spurs, after its physical clipping; do not point-sample a narrow corridor on a sliding coarse grid.
- Keep confluence openings and bank detail in physical world coordinates. Their extent must enter every geometry and water search bound.
- Match a confluence to the receiving section. Preserve the upstream land tongue; open the downstream-facing bank within the wider channel's envelope instead of adding the same width to both banks. Bed, banks, wet support and filtering share this geometry.
- Use the receiving flow's local direction, including its meanders. A nearly parallel join must lose its asymmetric opening continuously before that opening changes sides.
- Joining channels share their deepest wet section; a tributary bank must not become a closing sill inside the receiving water.
- A wet section always carries its water level. Distance to a junction alone cannot extinguish an inflow before another wet section covers it.
- Resolved water shading reads the actual stage/bed gap. Wet pixel coverage must not trigger another excavation of the physical terrain.
- A river ends at its first terrain-defined standing-water contact. Cache the contact and stop its downstream discharge, rather than hiding only the submerged pixels.
- Re-accumulate from the original local runoff. Quantized cumulative discharges cannot recover that source reliably.
- An interrupted edge keeps its incoming discharge until its first water contact. The receiving node's remaining local runoff cannot taper that upstream reach prematurely.
- Keep the world-space trace fixed when effective discharge changes; otherwise cached terrain contacts refer to another path.
- Drowned terrain cannot be filled into dry river-bank dikes. Sea and lake mouths obey the same contact rule.
- Open the mouth before its physical contact, and join the receiving water level there. Pre-erosion bank elevation is not distance to the rendered shore.
- The wet-bank slope has a depth scale, independent of total river width. Integrate that physical section and derive current from its actual cross-sectional area.
- Overlapping wet intervals require a true union, including containment. Ordering channel centres does not order their banks; a cut water bed must not be classified as dry.
- Coastal and river erosion meet as independent envelopes on the same substrate. Reapplying the coastal height remap to an excavated river floor cannot manufacture a new marine basin.
- First-water probes read the coast actually rendered, with the probing river disabled; the old unmodified shoreline is not its outlet.
- A dry fluvial head loses excavation depth with its width; narrowing a full-depth cut recreates a slot canyon.
- A broad valley grows continuously from its upstream dry drainage. Keep this physical onset independent of viewing distance; distant heads use the same terrain and its filter.
- A mouth connection, an estuary and a sediment delta have distinct extents. Calibrate channel width separately from bays and tidal flats; a larger terminal flare alone cannot reproduce all three.
- Coastal branching divides the parent discharge. It requires distinct shared bed/water branches; a widened water mask alone is not a delta.
- Water and terrain shading use the same reconstruction resolution. A coarse dry vertex cannot veto water resolved by the fine grid.
- A dry grid sample is not proof that a channel is absent between samples; retain a physical candidate bound for contour refinement.
- Every pixel in a derivative quad must evaluate the same field before its derivatives are used for coverage.
- Exactly zero water depth remains dry; symmetric threshold smoothing must not turn a drainage-stage plane into reflective water.
- Refining a wet contour does not change the sampling bandwidth of land materials, normals or the mesh silhouette.
- Use the same links, discharge and stage as erosion; no independent decorative river paths.
- Pair the lower envelopes of the section with and without its channel cut; their difference bounds additional bed excavation.
- Never apply one winning link's stage to another link's bed.
- Terminal basins share a constant stored stage; reconstruct distinct stages continuously where coarse catchments meet.
- Keep level basin interiors and document the connecting bands as an approximation until spillways are resolved.
- Positive water depth controls rendering, vegetation and terrestrial habitat; a dry plane at its drainage stage is land.
- Keep the pre-erosion form independent of visible water.

**Coastal foam uses the incident waves and the immersed part of the footprint** (`spec-mer-fft-spike.md`).
- Depth damping cannot erase the wave energy that feeds breaking near shore.
- Filter height moments with displacement; unresolved crests retain a breaking probability.
- Condition the foam mean on water, excluding the dry part of a mixed coastal pixel.
- Keep the same source in near and distant shading; pore detail may disappear, its mean coverage must remain.

**Grounded movement and environmental audio read the rendered world** (`spec-marche-ambiances.md`).
- Walking contact uses shared relief and a bounded local footprint; no second terrain model.
- Separate disembarkation recovery from movement contact; refuse invalid landings visibly.
- Step sounds follow actual grounded distance, not held input or time alone.
- Contact sounds use exposed textured coating areas, including residual soil; snow and beach cover the substrate acoustically.
- Distinct materials use distinct recorded contacts; pitch and filtering only vary or damp those contacts.
- Rain does not prove standing water and must not substitute mud or splashes for a ground material.
- Habitat, surfaces and weather use existing material, vegetation, climate and cloud fields.
- Real-time audio uses bounded voices and queues, without allocation, disk access or blocking.
- Resident recordings carry redistribution rights and reproducible provenance.
- Outdoor sound fades with distance from its habitat and atmospheric density.


**The camera's near plane does not follow its height above the ground** (`spec-vaisseau.md`).
- A nearby wall can coexist with a distant nadir; use the same 5 cm near plane for every view.
- Keep reversed Z for depth precision; clipping must not substitute for collision or modify terrain.
- A radial height clamp does not establish safe wall contact; proper contact must test the travelled segment for each body.

**Flight contact checks the swept body before accepting its motion** (`spec-vaisseau.md`).
- Query shared relief at the moving body's position; a previous nadir height or another camera's height is not collision evidence.
- Bound every intermediate attitude; a centre's final displacement alone does not bound its rotational arc.
- Test the complete chord and radius against the terrain envelope; reparameterize contact fractions after clipping the query interval.
- Use the analytic sea sphere to stop a planet-crossing chord before leaving its tangent hemisphere; do not clamp an invalid projection into a plausible local path.
- Separate placement recovery from movement; an existing shallow overlap must allow escape and tangential movement.
- Bound GPU storage and read back contact results; an exhausted sampling budget must not authorize an untested remainder or create a fictitious wall.
- State the sampled field's resolution and limits; a continuous sweep over triangles is not a proof of unsampled terrain or rendered crest stability.

**The coastal metric measures the scale of wave erosion, including at ria cusps** (`spec-erosion.md`).
- A long noise wavelength does not make the derivative of its absolute value smooth.
- Filter both the coastal spectrum and its crease derivative at the existing physical erosion scale.
- Refining the rendering mesh must not sharpen this parameter field or move an entire cliff-height contour.
- Keep the full terrain as the erosion input; the broad metric controls reach, not replacement terrain.
- Verify the gradient against independent height differences, then test cusp crossings and several coastal families.

**A coastal talus joins the cliff it supports without a reverse slope** (`spec-erosion.md`).
- With fixed coastal parameters, increasing the original ground height must not lower the supported profile.
- Locate the talus contact on the cliff face at its prescribed height; extend the apron seaward from that contact.
- Preserve the original terrain as an upper bound and the abrasion profile as a lower bound.
- Verify the profile over ranges of cliff height, face width, talus height and coastal gradient, then check several regions.

**A mesh filter averages a fixed physical profile locally** (`spec-erosion.md`).
- Coarse reference depth must not rescale a valley's coordinates or its unbounded banks.
- A resolved planar flank stays in place as the sampling footprint changes.
- Keep the physical floor mask independent of the mesh; round only the sampled profile.
- Verify fixed world positions at several mesh spacings, including zero reference depth.
- Averaging a profile does not prove conservation of the incision after clipping against arbitrary terrain.
- **Clip a section by the ground before averaging it,** at the point's own ground. Averaged first, a narrow valley's floor rose above the ground once the footprint outgrew it, and the valley vanished from orbit (`spec-erosion.md`, 2026-11-02).
- Combine clipped sections by their plain minimum; a smooth minimum's rounding digs along every divide.
- Compose the physical cliff, talus and min/max intersections before averaging the incision.
- Mesh size changes a symmetric normalized sampling support, never the physical cliff width.
- Conservation of a local section with frozen parameters does not establish conservation of the complete 2D terrain.
**Selecting a manufactured asset selects its complete geometry profile** (`spec-vaisseau.md`).
- Keep each selectable model's source and delivery files in its own asset directory.
- Match the pilot eye, canopy weather surface, shadow centre, engine mouths and animation pivots to that model.
- Change the default through model selection; retain previous models and their packet compatibility.

**Manufactured parts derive their interfaces from the visible support mesh** (`spec-vaisseau.md`).
- Design the common fascia and instrument depth together; cut actual recesses for installed equipment.
- Derive panel outlines from the usable support surface, with metric edge clearance; validate the actual control hardware against each outline.
- The usable outline ends at the visible intersection with neighbouring parts, not at the hidden tub wall; check visibility from the pilot eye and its travel limits.
- Console returns share their dashboard boundary and join the console tangentially; their sections must advance monotonically.
- Keep fitted control positions and printed legends in the same coordinate mapping.
- Cut each support's complete pocket layout together so adjacent coplanar floors remain closed.
- Keep printed instrument faces below the fascia and exposed rims thin; mounting contact alone does not establish a coherent design.
- Join coaming sheets at the chassis return instead of overlapping its top face.
- Glazing retainers have flat structural faces and a separate narrow seal; their section follows the glazing tangent plane.
- Fit the whole mounting perimeter along the mounting normal; a centre point or constant-depth block cannot establish contact with a curved panel.
- Derive shelf width from module dimensions and assembly clearance.
- Close recessed display rims and attach hoses, straps and handles to explicit fittings.
- Preserve a finite orthogonal tangent frame at UV poles in both GLB and cooked packets.
- Inspect the reimported asset from several viewpoints and retain the in-flight review route.
- Solve nose visibility in the physical hull shape; keep the glazing contact, external paint layout and attitude-jet origins consistent with it.

**Out-of-real-time rendering follows the movie clock, never the time of the calculation** (`lancement.md`, the cinematic mode).
- **A common step to everything that advances:** sea, plants, glass and histories; poses and the weather moment come from the course.
- **Safety does not draw the route:** the generator keeps a free band around the flight; any engine clamp is logged.
- **An external camera does not move the ship:** their poses remain independent, with the same rendering and shadows as the game.
- **A connection of flight segments does not require a stop:** position, speed and acceleration remain continuous; only landing, pause and start of take-off require rest. The cruise follows the length of the safe route; the orbit keeps its exponential altitude.
- **The margin protects the ground:** each segment can specify it; on the sea, the height requested starts from the level 0, with a minimum of 3 m.

**Geometry comes from the Exolune relief,** `Relief.hlsli` (`geometrie.md`).
- **Rendering does not change the shape:** the appearance of materials is worked in colors, textures, pixel normals, parallax and shadows.
- **Any geometry modification is a documented overlay:** filtering, detailing under 13,5 m, or replacement.
- **A replacement is a separate subject,** on a experiment tagged, until explicit decision.

**What a point cannot know alone is read on a map of the planet** (`PlanetMap.hlsli`, `Tectonics.hlsli`, `recherche-rivieres.md`, `spec-relief-tectonique.md`).
- **Maps on a cube fixed on the planet:** the map of the planet, drained relief, where the regional soil of the fog comes from, the level of the bowls and the way to the sea; the tectonic map, the plates and their boundaries.
- **Everything at startup, nothing on the way:** speed has no limit, we go from one place to another, from one planet to another, in one image. No data is calculated during a journey or in the background.
- **The perimeter is a solar system:** the maps of all its planets and moons are calculated at startup, once per seed, then remain in memory; a disk cache per seed can keep them. Their time and memory budget is the same as the whole system.
- **A planet the size of Earth: less than a second and 40 MB on the GPU** (`spec-relief-tectonique.md`). What only the views or the 0 level read does not rise to full resolution on the GPU; a propagation stops at the reach of what it shapes; what does not depend on each other is computed at the same time.
- **On the grid of the planet:** nothing depends on the camera; the same place gives the same value everywhere.

**A pre-calculated map can carry geometry, under three conditions** (since the 2026-10-31; it replaces "data, never geometry", `recherche-relief.md`).
- **Fix planetary data:** calculated once per seed, in the planet's reference frame.
- **Read continuously:** no seam between the faces of the cube, no walk from one texel to another. A map that bears a shape cannot be read in bilinear: the slope would jump at every texel, and the light would draw the grid.
- **Limited to the scales they resolve:** above two of their cells. The noise does the rest, and has no octaves above.
- **The tectonic map bears the large shapes since the 2026-10-31,** read in cubic B-spline, the faces of its cube mixed near their edges; the map of the planet remains of the data (`spec-relief-tectonique.md`).
- **The rivers' map bears their filtered effect since the 2026-11-05,** for footprints from one of its cells, alone from √2 cells, where its texels' box and its B-spline filter as widely as the evaluation it replaces (`spec-erosion.md`).

**Geology decides, the noise details** (`spec-relief-tectonique.md`, since the 2026-10-31).
- **Any form of more than 50 km comes from the tectonic map:** no noise of the detail has an octave above.
- **Every analytical profile has a width of at least two grid cells:** wider, its depth decreases by the same amount, and the relief keeps its average.
- **A profile that crosses the sea filters its emergent part:** it covers at least two grid cells, or the profile remains underwater; expanding its support alone is not enough. The filter redistributes the height, without changing the area of the profile; no shape depends on the grid cell outside this filtering (`spec-relief-tectonique.md`, the cords).
- **Each profile follows a published law,** cited with its source: ocean depth by age, bending of the lithosphere, width of the plateaus.
- **A noise that moves a limit is adjusted in distance:** its amplitude is the slope of the field times the desired displacement. A coast is cut as much on a flat plain as against a mountain range; set in meters, the same noise moved it of 30 km on one, of 1 km on the other (`spec-relief-tectonique.md`, the coasts).
- **A smooth shape follows a smooth field, never the contour of a noise field:** the contour of a noise fine has its angles and its ridges. A cordon follows the shore without the fine octaves of the noise of the ribs or the detail; its crest rises from the relief below it, entire (`spec-relief-tectonique.md`, the ribs).
- **A noise never shears on a narrower area than its displacement:** shifted from 8 km to 0,6 km on either side of the transforming faults, the detail stretched in straight trenches, parallel cornices and rows of teeth. A width depends on the grid cell only to filter away.
- **A profile never stops sharply along its border:** its strength is smoothed along it and fades at its ends; two neighboring forms combine in smoothed maximum, never in sum or cut.
- **What is placed on a shape of the map is placed where the shader draws it:** its place read in the map, then brought back by the left reading of the map. Without this, the volcanoes of an arc fell down to 30 km from its ridge (`spec-volcanisme.md`, since the 2026-10-31).
- **One shape placed on another follows the contour, and its width varies with what shapes it:** a reef, the leveled top of a guyot follow the contour of their volcano; the plateau widens windward, the passes open leeward. A separate circle, of constant width, made atolls in rings (`spec-volcanisme.md`).
- **A pattern placed on a shape has a zero average:** it draws, it does not mount the shape. The flows of a volcano, laid on top of his building, drew a ring where they begin; their tongues are above him, the ground between them below (`spec-volcanisme.md`).
- **Nothing finer than level 0 blocks any of its watercourses** (`spec-erosion.md`): detail fades on valley floors.

**Water decides the shape of mountain ranges** (`spec-erosion.md`, since 2026-10-31).
- **Water routing is global, its shape is local:** level 0, computed at startup over the whole planet, carries the network, lakes and water level; valleys and gullies only draw it, as point functions attached to it.
- **A valley retains detail on its slopes:** the cutting envelope carries that detail, which fades only on the floor; a bare profile would leave smooth walls.
- **A point representing a direction stays on the sphere after warping:** distances to its links use that unit direction, with the required placement precision. A radial offset must not close a thalweg; changing its water level does not correct this false sill (`spec-erosion.md`).
- **The drained floor belongs to each link's profile:** the profile is built above it before valleys are combined. The level of an independently selected link never bounds another valley. Both signs of detail vanish on the floor actually carved (`spec-erosion.md`).
- **The supporting terrain precedes its finishing:** folds and coarse octaves are identical with or without erosion; the network neither suppresses nor amplifies them before the incision decision. Gullies and slope reinforcement act after them; a profile above the support cannot orient it (`spec-erosion.md`, since 2026-11-01).
- **A network join shares all its parameters:** position, height, slope, discharge and ice; geometry follows the curve, not the segments used to search for it (`spec-erosion.md`).
- **An erosive cut never raises a hollow:** the envelope of the floor and its slopes cuts the full terrain. Removing detail is not deposition; checks concern the final height, not only the coarse support (`spec-erosion.md`).
- **A closest point on a curve also carries a parameter:** an almost exact distance does not guarantee interpolated heights and fluxes. Check endpoints with zero tangent and use their regular limit (`spec-erosion.md`).
- **A network warp preserves its local orientation:** check its Jacobian over several seeds and whether it can be inverted. A folding deformation can duplicate valleys and reverse their drainage (`spec-erosion.md`).
- **Sharpening never creates a cusp:** its crest slope stays finite, rounded over at least the `ReliefCrease` interval, including `CREASE_ROUNDING × f / gCreaseMaxFrequency`; its mean remains that of the replaced profile. Glacial arêtes form near and above the equilibrium line; trough ice does not activate them (`spec-erosion.md`).
- **A gully follows its supporting slope:** fine octaves take the slope direction of larger shapes, at equal roughness.
- **A gully, like any pattern, never creates a slope its ground cannot sustain:** each octave reserves the slope of larger shapes and its ordinary noise before adding the pattern; continuous saturation, zero mean, physical threshold independent of grid spacing. The soil and scree threshold applies at mantle scales and outside mountains; broad incisions in mountain ranges follow rock, reinforced near the equilibrium line. The transition depends continuously on wavelength and terrain amplitude, never on grid spacing (`spec-erosion.md`).
- **Incision retreats at finite speed:** beyond knickpoint reach, the ground retains its shape; plateaus are incised only at their edges.
- **What a shape reads is continuous, even from a collection of elements:** never the value of only the nearest or lowest element, which jumps when it changes; use the maximum or blend of their influences, each fading before that change.
- **Marine abrasion follows a full-ground contour:** the shore estimate only bounds its reach, extended by the possible detail displacement; the shore platform also cuts detail, and lowering stays bounded by the coastal contour (`spec-erosion.md`, coastal cliffs).
- **A wave cut stays within reach of the sea:** its contour varies more broadly than its platform, and it requires deep sea at the retreat distance, read on the pre-erosion ground; never a valley or lake mistaken for the sea (`spec-erosion.md`).

**A slope that steers a pattern is the true gradient of the ground it follows** (`spec-erosion.md`, step A, since 2026-11-02).
- Carry it through every mapping of the point it reads: a warp's Jacobian, a lift off the sphere, a map face's projection. Without them, the detail's analytic slope was 50 to 100 % off, and the ravines ran 25 to 55° off the slope.
- Check it against finite differences of the height it claims to be the slope of, at several sites.

**A shape drawn along a curve is read on the curve, the same for every point that measures it** (`spec-erosion.md`, step B, since 2026-11-03).
- Its offsets, widths and noises are functions of the curve's parameter, read at the curve's point on the sphere; read at the sample, a meander bends the course with whoever looks, and a junction placed on it moves.
- A startup pass that measures such a shape builds it with the shader's own functions, at the same places.

**A conditioned profile holds at the resolution it is stored at** (`spec-erosion.md`, step B).
- A quadratic course between nodes stays under a cap only if all its controls do: condition the controls, not only the nodes' values.

**Water stands in a channel cut into the ground it crosses, never above it** (`spec-erosion.md`, step B).
- Cut the channel below the lower of its stage and the composed ground; a stage held above a neighbour's carve leaves perched water and a wall at its edge.
- A curve's attributes continue past its ends along their slope: held at the end, two curves meeting there differ by a step.
- Where two channels' water overlaps, their stages blend, each weighted by how far inside its edge the point is: the highest alone stood a step above the other's water at its edge.
- Bound final river depth by its compact channel cut after combining beds; a neighbouring dry bank cannot enlarge the water column. The depth vanishes at a wet edge; terminal lakes keep their separate stage.
- **Filter incision and wet area separately:** intersect the physical bank with its supporting ground before averaging its cut. A wider sampling footprint must not move the physical banks outward or lower the whole sample to a subpixel river's stage.
- Carry mean water depth and wet fraction through mesh, fine-grid and screen samples. A positive mean cut is not full water coverage; recover depth conditional on water only for shading.
- The conservation guarantee of a local section holds with its terrain and course parameters fixed; combining several channels and varying terrain is a separate approximation.

**A drainage axis does not prescribe two parallel mountain flanks** (river-corridor review, 2026-11-03).
- Valley form must retain asymmetric mountain masses, spurs, side valleys, constrictions and basins across terrain scales.
- Perturbing only a centreline or adding one width noise cannot establish this structure.
- Preserve existing two-dimensional mountain residuals through a corridor's slope and floor transition. Their positive part can reduce incision within the original terrain bound; their negative part must not dig a second trench.
- Mountain masses must also affect the valley outline. Evaluate confinement on each terrain point so the two flanks can advance independently, while retaining the physical wet-bank clearance and the search bound.
- A confined floor contains the displaced channel and both banks in the valley's distance metric. A minimum width around the original axis can cut a meander through its own flank and leave artificial fins.
- The wet bank stays clear. Relief recovery depends on physical channel and valley widths, never on camera distance.
- Retained mountain height also needs horizontal room beyond the dry bank. Bound that added height by its bank distance; a width-only recovery can restore hundreds of metres in a narrow strip and manufacture a continuous slot canyon.
- Apply this bound to recovered spurs, not the base valley walls. Preserve small lifts with ample room and make recovery monotone in both available distance and mountain height.
- Centre physical width fluctuations so unresolved octaves return the nominal width; include their maximum width in every search bound.
- Density, valley form, water width and distance filtering require separate flight judgments; fixing one does not validate the others.
- Compare references at matching ground footprints and feature sizes. Separate wet channel, exposed bed, valley floor and mountain flanks; camera altitude alone does not fix their apparent scale.

**A reach kept in metres breaks a search kept in cells** (`spec-erosion.md`, step B).
- What a fixed set of the level 0's cells must hold scales with those cells: on the cube's edges and corners they are half as wide as at the faces' centres.

**A shape drawn for each element of a network is sized by that element, by a published law** (`spec-erosion.md`, step B, since 2026-11-03).
- A river's valley follows its discharge, its rock and its relief: one profile for every size repeats as a stamp, a valley on every link of the 20 km graph.
- Compare network density with observations using the same size cutoff and metric; inverse drainage density is not mountain-front outlet spacing.
- Separate published exponents from engine calibration, including discharge cutoffs and conversion from drainage area to discharge.
- Smaller elements fade over a size range; omitting their explicit water remains a documented limitation.
- A bound applies only where what it protects is drawn: the stage is capped where water runs, not along a dry notch.

**A directional terrain pattern must budget the spatial variation of its direction.**
- Amplitude divided by wavelength is insufficient when the orientation changes across a ridge or a valley junction.
- Rock strength changes the admissible slope; it never exempts a pattern from turning and fork bounds.
- If this envelope suppresses useful detail, fix the direction field at the pattern's scale before increasing the amplitude (`spec-erosion.md`).

**The climate comes from geography, the noise details it** (`spec-climat.md`, from the 2026-10-31).
- **Rain and temperature are calculated at startup,** on the large forms: the winds of the three cells, the water vapor carried from the seas, the rain windward of the reliefs. Never an imposed band of latitude: deserts fall where traffic and relief leave them.
- **The climate map bears what exceeds two of its cells, 100 km;** a gradient noise does the rest, and what the pixel does not show expands the limits drawn on humidity.
- **Climate only reads the form before erosion:** erosion reads rain, never the other way around.
- **Clouds also come from climate:** their weather map is calculated at startup on its fields and the relief, convection, subsidence, cold currents, depression tracks, slopes windward (`spec-nuages.md`). No cloud field taken from a noise without link with geography.

**From far as close, the same planet** (`spec-rendu-lointain.md`).
- **A field that decides appearance is filtered at the footprint of the sample that reads it, and evaluated where it is seen, never interpolated on a sliding mesh.** A triangle slides under the view; a feature narrower than it changes shape as it slides, and the ground crawls (`spec-rendu-lointain.md`, the screen relief).
  - Relief, roughness, fresh volcanic ground and geology are read at the screen texel or the pixel from orbit; the relief is filtered to 4 texels.
  - Cloud noises are read 4 pixels to a texel; at one pixel to a texel, the coverage threshold made each pixel cloud or sky.
  - A shape kept by a map keeps its area once widened to two cells; its edge is never sharper than the samples.
  - What a grid cannot place between its samples widens the limits drawn on heights, like the pixel's own spread: the gap between its bilinear and B-spline reconstructions.
- Reconstruct fine-grid altitude and slope from one differentiable height surface. Independently interpolated normals cannot repair derivative jumps in bilinear heights (`spec-normales-spline.md`).
- A shading reconstruction smooths sampling-scale transitions; it does not certify mesh silhouettes or hydrological shape. State its support, fallback and limits.
  - The coast is the terrain's own contour at the pixel where the samples' cells are wider than the pixel; their interpolated heights drew polygonal coasts that slid with them.
  - Cloud noises are read 4 pixels to a texel; at one pixel to a texel, the coverage threshold made each pixel cloud or sky.
  - A shape kept by a map keeps its area once widened to two cells; its edge is never sharper than the samples.
  - What a grid cannot place between its samples widens the limits drawn on heights, like the pixel's own spread: the gap between its bilinear and B-spline reconstructions.
- **Every pixel of a derivative quad evaluates the same field before its derivatives set a coverage.** Refining a contour changes neither the sampling of land materials and normals nor the mesh's silhouette.
- Reconstruct fine-grid altitude and slope from one differentiable height surface. Independently interpolated normals cannot repair derivative jumps in bilinear heights (`spec-normales-spline.md`).
- A shading reconstruction smooths sampling-scale transitions; it does not certify mesh silhouettes. State its support, fallback and limits.
- **A pixel shows the average of what it covers.** Any boundary between materials widens from what the pixel cannot show from its inputs: `SpreadStep`, `SlopeShares`, `RockShares`.
- **A noise never fades depending on the pixel size.** It remains the same at all distances; only its invisible part expands the limits.
- **The relief keeps its average height at any distance,** regardless of the octave filtering.
- **Decisions see the relief forms at any height.** The fine grid carries their normal as long as the mesh does not carry the finest octave, 13,5 m, on its 4 grid cells. Extinct from grid cells of 20 m, it let the forms of 13,5 to 100 m of snow and rock come and go from 2 km to 160 m (`journal-planete.md`, 2026-10-24).
- **A width is decided on the slope taken at its own scale.** The range, a water level, is capped at 120 m once the slope is taken on 60 m, `SHORE_BASELINE`. On the normal of materials, taken at 1 m, the bumps of the relief left kilometers of coastal plain in sand. In the distance, the fine grid carries this slope as soon as its grid cells covers 60 m; thinner, they bring back the bumps (`recherche-cotes.md`).
- **A noise color filters to pixel, never to grid cell.** A grid cell covers about 13 pixels: calculated by vertex, its octaves appear in sight when approaching, and what it draws slides (`spec-parois-minerales.md`).
- **Every pattern is calculated on the planet grid, never relative to the anchor.** The anchor jumps by 64 m when the camera moves; a stretch or rotation taken from it re-cuts the pattern. The ravines of `WallRelief` were infringing it; it is removed the 2026-10-30.
- **A quantity passed from one pass to another retains the accuracy of the scale it serves,** not that of its size. The distance of the ground serves the atmosphere to the meter close and exceeds 30 000 km: half-floating, its steps of 16 km drew circles on the oceans. The HDR image is in floating 32 bits. Likewise, the smoothed distance at the border, hundreds of km, moves the noise of the chains to the meter close: floating, its steps of a few cm made walls on the ground; it is read in double precision (`journal-planete.md`, 2026-10-31). The small cones of a volcano, up to 120 km from its summit, are placed in double precision (`spec-volcanisme.md`).
- **Reference photos set exposure at each scale.** On the ground, those of the landscapes, +1 EV; orbit, those of the Earth, 0 EV; between the two, the part of the air under the camera. Always an incident exposure meter, never the image reading (`spec-rendu-orbite.md`, `recherche-tons-exposition.md`).
- **A shadow follows the limit rule** (`recherche-ombres-relief.md`). The horizon of the relief is interpolated between the summits like an angle; the part of the sun is taken by pixel, enlarged by the spread of the horizon it covers. The relief thinner than the grid cell keeps its share of shadow, on average: the Smith shading, `FinerReliefLit`.
- **What acts on the screen is calculated even off the screen.** A vertex whose shadow can fall on the screen is calculated (`ShadowSweep`); otherwise shadows appear when the camera rotates.
- **A noise never shows its grid: noise gradient, never value.** A noise value is flat around each point of its grid, and its octaves, on nested grids, align their plates. From afar, the pixel only keeps two or three: they pave the floor like a low-resolution image. One noise, `Noise3`, for all fields, including climate and geology (`journal-planete.md`, 2026-10-24).
- **The octaves of a noise never share the nodes of their grids.** A gradient noise cancels itself at its nodes; on nested grids, all octaves cancel together, and a threshold on their sum draws rows of orbital points. Each octave is shifted by a fraction of grid cell (`CloudFbm` of the old volume, `log/recherche-nuages-historique.md`).
- **A close-up volume is calculated in 3D, not in extruded 2D field.** The thin octaves of a 2D field, raised in height, make cliffs and needles. They pass into a noise 3D of the same standard deviation, of which the mips make the average far (`ResolvedColumn` of the old volume, `log/recherche-nuages-historique.md`).
- **The formation of a cloud remains anchored in the world.** At time freeze, its density is not dependent on the camera, the mesh or the sliding anchor. A reference without history or cascades is used to check the approach before optimizing (`log/poc-nuage-stable.md`).
- **Clouds share a time and a weather field.** Wind and deformations are read in the world with this clock; views, the number of images and the identity of formations do not change it. A weather break leaves the camera free (`D3DApp.cpp`, `kWeatherWindSpeed`; `spec-nuages.md`, weather).
- **A pre-calculated density volume keeps the reference frame and the time of its source.** The camera does not choose its origin or phase. If the final density depends on time, publish the full volume of that same time before reading it (`log/poc-nuage-voxel.md`).
- **Combined directions must belong to the same reference frame.** A sun expressed in the field face must be transformed before a calculation with planetary positions; explicitly provide camera and sun world to the relevant passes (`log/spike-nuages-voxel-planete.md`).
- **Passes share an explicit GPU contract.** Reserve a range of resources per system; keep constant structure identical in C++ and HLSL. Weather has its fields, separate from the vegetation and sea indicators (`spec-nuages.md`).
- **The validated rendering is that of the executable without variable.** A code present but disabled does not count; a variable is only used for benchmarks and comparisons. A missing resource stops the boot with a message, without silent return to an old rendering (`spec-nuages.md`, `lancement.md`).
- **Optimization distinguishes quality, resolution and presentation rate.** Compare with identical resolution and settings before assigning a gain; a capture remains invisible even if the flight profile requests full screen (`execution-optimisee.md`).
- **An exact optimization is proven in one executable:** the former path kept behind a switch, both rendered without clouds, the images identical to the bit. Two executables differ in their last bits wherever the compiler contracts differently, even for a switch alone, and plant placement turns those bits into other plants. A compiler error in one shader leaves the others stale: check the build before measuring (`diagnostic-orbite.md`, 2026-11-07).
- **A feature costs what its own branch pays with it on, against it off, in the same executable.** Another branch differs by more than the feature: `main`'s clouds cost 0.5 to 1 ms more than the erosion branch's.
- **Another executable is compared in the same window, runs alternated.** Other processes on the GPU move a run by 5 to 20 %: a `main` measured in the morning made the erosion look 7 % cheaper than it was (`diagnostic-orbite.md`, 2026-11-07 evening).
- **A branch no pixel can take for a whole frame goes to a permutation,** and the permutation is measured, not assumed: the terrain's colour under a full screen relief without its contour, 1.1 ms less in orbit; the same permutation without the contour's dead code, 0.6 ms more (`PixelShaderScreen.hlsl`).
- **A heavy query runs in a kernel of its own when its inputs are already stored.** Inlined in a large kernel, the rivers' corridors cost thirty times more. Where storing its inputs is the new cost, it can lose: the fine grid's rivers did (`diagnostic-orbite.md`, 2026-11-07).
- **A dispatch's waves cover tiles, not rows:** neighbouring threads share their data only if they are neighbours on both axes.
- **A grid computes what its readers read:** its margin is their stencil's, not another grid's. The fine grid kept the mesh's, which also covers shadows: four times too wide (`spec-rendu-lointain.md`, the fine grid).
- **A rare heavy step goes to a pass of its own, its items listed:** a lone lane through it holds its whole wave. The plants' missing exact grounds, one or two per wave, cost 0.5 ms more at 2,200 m inline than in their own pass (`optimisation.md`, the kept ground).
- **Sun shade reduces the sunlight received by the surface.** Keep sky and air separate; plot the same volume, at the same time, from the receiver to the sun, including above the sea (`spec-nuages.md`).
- **Color, depth and solar share describe the same visible surface.** Any opaque pass, including impostors and meshes after HiZ, replaces both colors with the same alpha discards. A solar transmission of 1 leaves the color exactly intact; a shadow never reintroduces the object hidden behind (`spec-nuages.md`).
- **A distance on a map is not a distance on the planet.** A global weather jump is limited by the spherical boundaries of the cells, with the filter margin; the connection and poles are part of the contract (`spec-nuages.md`).
- **An acceleration envelope does not draw the shape of the volume.** Its density extinguishes before the faces of this envelope; its visible boundaries come from continuous local profiles, not from the course shell (`log/spike-nuages-reference.md`).
- **Multiple layers are composed in the order of radius.** Sorting their segments before accumulating light and transmittance; skipping the vacuum between layers keeps this order (`log/spike-nuages-cirrus.md`).
- **A soft extinction is verified on the final density, and its continuity does not validate the silhouette.** The threshold and erosion can intersect a gradient; even continuous, a nearly uniform substrate can give opaque flat faces. Judge together the 3D fields, local heights and optical thickness. Geometric parameters remain global and independent of the camera (`log/spike-nuages-reference.md`).
- **Proof of vacuum requires a presence bound.** The levels used for a jump keep a conservative maximum and filter margin; neither a mean nor a null sample proves the void of the interval (`log/spike-nuages-reference.md`).
- **A skipped calculation is proved to have no effect.** A decision on a threshold stops when a rigorous limit of the other can no longer change it, never on a standard deviation; what is only useful in a branch is calculated in the branch (`optimisation.md`, round 2).
- **A closed form keeps the domain of what it replaces.** A rounding can get it out of [0, 1] where the loop could not: bounded, otherwise a root gives a NaN, isolated white pixels (`optimisation.md`, round 2).
- **A costly pixel is calculated once, on the viewed surface.** The ground writes its depth first, its color after the foliage, in equal depth (`optimisation.md`, round 2). The meshes plants are the same; at equal depth, the color keeps the first drawn, as the strict test: it is drawn in the reverse order (round 3).
- **A pixel that writes its depth declares it bounded as soon as a bounded is proven.** Its primitive is placed at the bound, the pixel promises it (`SV_DepthLessEqual`): the test rejects before the shader. The impostors take the end of their HiZ test (`optimisation.md`, round 3).
- **What depends only on one grid cell is calculated once and saved.** The exact soil of a plant tile is read from one frame to another, the key being the cell; a kept value differs from the fresh only by the camera roundings. A jump of the camera erases it, so that a place does not depend on those seen before. An overflowing cache costs more than it makes: measure it at full load (`optimisation.md`, round 3).
- **A calculation whose inputs have not changed does not redo; its key is exactly what it reads.** The constants that its shaders read, found in their compiled code, compared to the bit close: not wider, nor approached. A value that depends only on a part of the entries is saved when that part is equal: the height of a vertex does not depend on the view, only the sorting depends on it. What sort discards becomes what it would be in the whole calculation. Checks in motion against the whole calculation, bit close (`optimisation.md`, round 4).
- **An approximate calculation for movement is compiled separately, and what places the camera remains accurate.** The exact same code, compiled with more code next to it, changes its last bits: the binary of the exact calculation remains the same as before. The ground under the camera places it; at the last bit, it moves the entire image by a fraction of a pixel and the edges of the leaves tilt. At the stop, everything becomes correct again (`optimisation.md`, round 8).
- **Cross-filtering does not replace integration along the radius.** A pixel-appropriate mip can still leave an optically thick interface between two steps; refine the density integration before masking its bands with noise or a history (`log/spike-nuages-reference.md`).
- **An isotropic multiple scattering reduces a medium that diffuses forward by similarity.** Its diffusion becomes `σs (1 − g)` (van de Hulst): taken whole, the fog returned to the orbit three to five times too much light (`spec-rendu-orbite.md`).
- **The cover says the part of the sky covered, not the water in the cloud; the water follows the regime, which the map carries.** The cloud density is divided by the cover, then follows the thickness of the map, from 20 /km for scattered cumulus and blankets to 80 /km for front hearts: everywhere at 80 /km, a blanket saturated and lost all texture (`spec-nuages.md`).
- **A cloud field has octaves at all scales that we see.** Between the tile of the noise, 32 km, and two texels of the map, 80 km, there was an octave missing: with partial coverage, the cumulus were uniformly sown. The same volume reread at 128 km gives (`spec-nuages.md`).
- **The light that a cloud sends back depends on its overall thickness and on what it receives.** His multiple scattering is set on Monte-Carlo references, seen from above and below; the sun and the sky enter together, and his samples to the sun cross the whole layer (`spec-rendu-orbite.md`, `tools/calage_orbite.py`).
- **What builds up or drains the light a point of a cloud scatters is read in the cloud around that point, never in the pixel: its seen point, its column, the view ray.** A pixel's quantity in a point's light draws its own isosurfaces on the cloud: the build-up F taken at the pixel's seen point drew shiny rims and dark channels wherever that point jumped between lobes; the side leak taken against the view's column drew bright veins (`spec-rendu-orbite.md`, 2026-11-02).
  - **The thickness that builds up the multiple scattering is the cloud's chord along the sun through the point,** both sides, in its density where it exists. Along the view, a flat edge was extinguished in a circle; toward the sun only, a lit face darkened; averaged with the clear sky of a coarse interval, a cumulus turned grey; along the normal of a thin noise, everything turned to metal.
- **A sample standing for an interval carries the interval's mean, its height profile included.** The noise read at the interval's mip was smoothed, but the profile at its middle was not: as that middle crossed a cumulus' flat base, a whole 2 km interval of the sun's chord lit or went out, and planes at fixed heights crossed the clouds, still while they drifted. A conditional quantity counts by its probability: the density in the cloud does not vanish with its cover, and its floor at 1e-4 drew the same planes (`spec-rendu-orbite.md`, 2026-11-02).
- **A law fitted on an infinite slab is checked on a finite cloud.** A finite cloud loses through its sides the light it scatters: fitted on the slab alone, the multiple scattering flattened the cumulus, three times less contrasted than the Monte Carlo of a sphere. The side leak is zero in a slab, so the orbit keeps its calibration (`spec-rendu-orbite.md`, `tools/calage_orbite.py relief`).
- **What a noise does not carry under its texels remains a variance.** Its thinner octaves, extrapolated from the thinnest one it bears, broaden its edges in fringes at any distance: without them, its smooth isosurface is seen as a surface (`spec-nuages.md`).
- **A threshold on several noise functions is averaged on their attached law.** Under the pixel footprint, the covered part and density are calculated on the law of each noise, its standard deviation read by mip; taken at its average, the erosion erased any thin cloud in the distance. In the footprint, clouds are superimposed to the maximum; beyond, randomly (`spec-nuages.md`, the pixel statistic).
- **The generator paving does not draw the formations.** A field of form aiming at a distribution without preferred axes does not begin with a dominant octave reduced to a single periodic gradient; check its directions and its mips at the source (`log/spike-nuages-reference.md`).
- **The LOD of a volume averages its optical contribution.** A threshold applied to an averaged noise does not preserve coverage; the exponential of an average density does not preserve average transmittance. Statistical approximations describe their population, parameters and limits (`log/spike-nuages-reference.md`).
- **A detail level lights up as the average of what it replaces, not as a surface.** Its colors average linearly. An average normal keeps its length, the consistency of what it summarizes: renormalized, it claims to a single orientation, and the impostor lit up like a map facing the eye. Light is hopeful on this dispersion; the relay to the detail must change only the detail (`vegetation-planetaire.md`, the lighting of the impostors).
- **Average spatial quadrature of integrated rays.** Evaluate each distant sample on the same fine density field, then average premultiplied light and transmittance; specify the cost, filter support and its limits. A mix with the close rendering retains these same magnitudes (`log/spike-nuages-orbite.md`).
- **A history is tested on what it holds.** The clouds' history is valid where the rays cross the same clouds, not where they end on the same surface: a surface beyond the clouds is the sky for them. Tested on the surface, toward the horizon, where its distance changes by 4 % a row, it was refused above and below and drew a line fixed on the screen in a fast flight (`spec-nuages.md`, 2026-11-02).
- **A history is reprojected in the reference frame where its content is fixed.** Clouds in the weather, that the wind turns; their shadow on the ground. A distance that it keeps is related to the current camera, otherwise each frame reprojects crooked. What it carries is re-sampled at each frame: a count or a drift averages, a minimum would erode it and a maximum would extend it in a few frames (`CloudsTemporal.hlsli`, `optimisation.md`).
- **What a history provides to another calculation, that calculation must be continuous there.** A saved value always differs a little from the fresh value; if the calculation that reads it jumps or moves its samples with it, the difference becomes plates with sharp edges, where what it describes is invisible: the distance of an almost transparent cloud cut the air of the composition in two halves (`optimisation.md`, round 1). An image guard also measures flat offsets, averaged over a few pixels.
- **A lightened trace is only valid where the image has no detail at the scale it loses.** Under the door of the distant quadrature, the clouds are larger than the pixel: a pixel between two traces is the interpolation, to one level close. Above, their grain is pixel; interpolated, it softens in plates. The regime is read on the estimator, not on the image: decided pixel by pixel, a shortcut costs the whole wave (`optimisation.md`, round 7).
- **A long calculation reserved for a few scattered pixels costs the entire pass.** Each one holds his wave, the pass waits the last one: a few dozen holes in the sky traced in the resolution of the clouds cost 3 ms. The rare case takes the value of neighbors who see the same surface; failing that, a neutral value for an image, which the parallel calculation replaces (`optimisation.md`, round 8).
- **Each correction acts on its scale and field.** A front organization is worked in the weather map; a deformation of the coordinates of the noise acts on individual clouds. Compare distribution, density recipe and filtering separately, at identical times and positions. Disabling a LOD is not a witness if the fine density has also changed (`log/spike-nuages-reference.md`).
- **A published reference distinguishes between reproduction and local selection.** Preserve the source, revisions, licenses, and parameters of noise functions; name parts not provided by the publication. Check density, transmittance and light separately before modifying a combination or generalizing it (`log/spike-nuages-reference.md`).
- **Two level constraints combine without a bend, and a recentering grid does not rotate.** A dry `max` between the level of the footprint and that of the range keeps the continuous value but breaks its slope: the place of their equality, a circle around the camera, is drawn. Similarly, a cascade recentered on new axes recuts the average of each texel at each step of the flight. The level is combined in smoothed maximum (`LevelMax`); the cascade is recentered by texels wholes of its own plane, its axes transported (the old volume, tag `piste/nuages`, `log/recherche-nuages-historique.md`).

**The shadow of the relief has a single source, for air as for the ground** (`recherche-rayons.md`, `recherche-ombres-relief.md`).
- **One single step:** towards the sun, at each vertex of the mesh, on the heights of the image. It gives the horizon, for the ground, and the shadow height, the altitude below which the column does not see the sun, for the air.
- **Nothing comes from the screen:** the mesh keeps every visible column of air, from the sea to the highest summit, and every relief whose shadow can reach it (`ShadowSweep`). An out-of-field relief casts its shadow in the field, and turning the camera does not change anything.
- **A step of the radius of view shows the illuminated part of its length,** as it shows the average of the air it passes through.

**Materials do not depend on what the mesh** (`log/spec-relief-reel.md`) is wearing.
- **Decisions are made on the ground alone** and on the entire slope of textures. Only light removes the part carried by the mesh.
- **A texture effect on a boundary is only faded with pixel size if it keeps the average,** and does not exist where materials are filtered to one cell, for object placement: `gHeightBlend`. The height, centered, moves the limit in both directions and keeps the average. The slope passes through the standard of a vector: added near the ground, it changed the snow share by several points, less on gentle slopes, more on steep ones. It no longer decides on snow.

**The relief carried by the mesh never jumps from one summit to another** (`log/spec-relief-reel.md`).
- **All that decides it is continuous, and taken at the scale of its forms:** projection triplanar to continuous weights, normal on 32 grid cells, peaks never thinner than grid cells of 2 m.
- **The copies of a tile blend without amplifying the heights.**
- **The calculations remain accurate in simple precision:** no subtraction of almost equal terms; a series where it is needed.
- **Only one double-precision read per vertex:** here, doubles run 64 times slower than floats. A neighboring position is taken relative to the point in floats: the difference of two neighboring floats is exact (Sterbenz), minus the point's remainder, read once in doubles. Valleys were reading it at every link (`spec-erosion.md`).
- **The mesh and the screen relief slide continuously with the camera, never by step on the grid of the planet:** each frame refines them exactly at the view. Placed by step, or with samples kept on the planet for reuse, their refinement would be seen, especially in fast movement. A calculation gain is not purchased in this way (`optimisation.md`, round 4; `spec-rendu-lointain.md`).
- **Each footprint refines by its own rung, chosen at every frame:** a sample computes what its scale resolves, not the whole model. A rung equals the mean of the finer one on what it shows, so that a change of rung moves nothing; its cost per pixel stays bounded. The water contour: the grid carries the valley, the pixel the channel alone (`spec-eaux-interieures.md`); wide footprints read the rivers' map (`spec-erosion.md`).

**No uniform stroke structure** (`spec-roche-organique.md`).
- **strata, fractures, corridors, wrinkles:** each varies along itself, at several scales, in strength, shape and continuity. A perfectly regular pattern reads like a drawing.
- **No structure stops clearly:** it thins or fades over several times its width (`spec-texturage-universel.md`).

**Every material covers every scale** (`spec-texturage-universel.md`).
- **A material is a stack of strips, from millimeter to kilometer, without holes:** a declared data, verified by a validator.
- **Every pixel of the floor belongs to a material that has its pile:** the rest of the floors including, the bare floor, which had no and went unnoticed of benchmarks.
- **Every strip is erased by the same rule,** according to its wavelength and pixel size, regardless of its source: noise, tile or photo.
- **The bands extend the slope of the photo:** above its tile, each octave carries the slope by octave of the photo, the one that the distant rule already counts (`STONE_SLOPE_SIGMA`). Lower, they leave each wall in carpet equal to his photo.
- **A photo keeps the orientation of its shooting:** a wall photo goes on the slopes of more than 45°, a photo taken from above on the softest ones. The limit follows the universal rule and the noise limits, like that of the rock. A material that has only one photo keeps it everywhere.
- **A correction is accepted by the quality benchmark,** on randomly drawn locations, not on the only reported view.
- **A p95 that rests on one view of one place is resolved at its worst crops.** The bench is exact: the view is real, not noise. Measuring the place over several headings and positions, the build and `main` alike (`tools/banc_qualite_vues.py`), gives its spread, not its cause. Place 4's rock at 12 m ranged from 1.5 to 4.2 dB of gap by heading alone; its worst crops were the cliff photo's straight joints, bared by the erosion (`diagnostic-orbite.md`, 2026-11-09).

**An optical effect moves light, it does not create light** (`recherche-halo.md`).
- **On the linear image, before the tone curve, without threshold:** the total light of the image does not change.
- **Strength is measured:** The halo follows the spread of a real target, not a taste.
- **Nothing that the viewer's eye already adds:** in front of the screen, its own halo covers everything that the screen shows.
**Sea: one slope variation, shown or lost** (`recherche-mer.md`).
- **The slope of the sea always has the Cox and Munk variance,** of the orbit at the level of the water: what the pixel shows of waves, each its average on the pixel, plus what it loses, which broadens the reflection. The reflection keeps its width and its medium light at any height.
- **The whitecapss that the pixel does not show are their share of the pixel,** that of Monahan; close up, their pattern keeps this average.
- **The wind is a map of the climate,** and everything that comes from it: slopes, waves, whitecaps.
- **One single function for reflecting water,** sea like wet sand: `ReflectOnWater` (`Sea.hlsli`).
- **Visual validation is not equal to physical calibration:** deviations of the FFT kernel to these laws remain declared in `spec-mer-fft-spike.md`, even after its integration.

**What moves by itself** (`recherche-mer.md`).
- **Time is a parameter of the frame:** the clock in flight, 1/60 s per frame in capture, so that the benchmarks repeat; `MYPLANETENGINE_TIME` fixes it.
- **A surface that moves by itself shows its average at each frame, without temporal smoothing of its light:** its past is elsewhere; kept, it spread the movement of the waves. The physical history of the foam remains in its simulation maps.
- **An animated pattern can follow the camera, if it never jumps:** the wave plane is carried by the camera without turning, its origin keeps the path traveled in double precision precision. A point of the sea keeps its waves, to a few millimeters per kilometer traveled. It is the exception to the grid of the planet, for a pattern that moves anyway.
- **Normal and foam are derived from the actual displaced surface:** a phase mask is not sufficient. Displacement, slope and compression share their source; see `spec-mer-fft-spike.md`.

**The screen shows the light, not the framing** (`recherche-tons-exposition.md`).
- **The exposure follows the light that falls, never the image:** the one that receives, under the camera, a map facing the sun. Turning the camera does not change anything; snow remains white, a forest remains dark.
- **One curve, on the strongest channel:** the shades do not turn. Clarity is regulated by exposure, before it, never by a gamma after.
**An object has a fixed place on the planet** (`spec-objets-proximite.md`).
- **An object is the detail of the ground, laid:** a pebble, a tuft. The bedrock and its relief are geometry.
- **His recipe is that of his soil,** based on photos taken standing, counted: the published law serves as a safeguard. A debris-clean field first decides if there is any debris.
- **Everything that does comes from its cell of the planet grid:** place, size, shape, density. Never mesh slipping, never anchor.
- **It obeys gravity, soil shape and measured laws:** nothing beyond the angle of rest; blocks accumulate at the foot of the real walls, leave the ridges; by spots; the sizes of real stone fields.
- **The camera only decides if it is visible,** by its size on the screen and the thinness of the mesh under it; it comes out of the ground, without pop.
- **His foot is on the exact ground,** buried according to the ground, always more than the measured deviation to the ground that draws the mesh.

**Vegetation follows the climate by published laws** (`recherche-vegetation.md`).
- **The diversity of appearance takes over the fields of the population:** cold, aridity and exposure decide the families, with continuous mixtures at the borders. The seed chooses the shape; changing the pattern does not move the plant and create a new one (`arbustes-climatiques.md`).
- **A simplified representation is judged against its own detailed model,** with the same trees, poses, sizes and light (`log/prototype-vegetation-volumique.md`). Cover and holes count as much as silhouettes; opacity thresholds common to all trees should not correlate their holes.
- **One source for what grows,** `Vegetation.hlsli`: nearby plants and the distant canopy read it both.
- **Climate admits species pools; space composes local communities.** Stable regional fields choose a few dominant forms and compatible companions, never camera distance or weather time (`spec-diversite-vegetale.md`).
- **Ground herbs need suitable ground, light and climate.** Snow, submerged roots and bare substrates cannot become a meadow; local detail stays inside bounded queues (`spec-diversite-vegetale.md`).
- **Wind moves foliage around fixed roots.** Depth and colour share deformation; motion reaches zero before a static proxy relay, and culling uses the drawn instance dimensions (`spec-diversite-vegetale.md`).
- **Close vegetation is directed as a game asset.** Mature silhouettes, coherent foliage masses and volumetric ground connection follow the biome boards; photographic detail alone does not establish quality (`direction-artistique-vegetation.md`).
- **A placed root follows the terrain; the terrain never grows a pedestal to fit the root.** Preserve crown scale independently of added contact bounds and document the sampled fit's limits (`spec-diversite-vegetale.md`).
- **Root contact preserves a continuous volume.** Bake one supported base for meshes, attachments and impostors; protect near-root geometry and bound coarse surface error. Never squeeze horizontal reach independently of height or deform only one side of a material seam (`spec-pipeline-creation3d.md`).
- **A nearby woody LOD preserves branches as well as the trunk.** Root probes and bounds cannot validate a face spanning an empty branch loop; retain the reviewed surface while reducing foliage progressively (`spec-rendu-vegetation.md`).
- **Contact lighting preserves the source of light.** Occlusion attenuates indirect light; solar contacts and canopy sunlight scatter remain in the solar attachment. Screen-depth contacts retain explicit finite support and limitations (`spec-rendu-vegetation.md`).
- **Generated vegetation retains reproducible provenance.** Preserve references, prompts, model version, seeds and editable recipes where available; select coherent structural variants artistically before cooking a bounded runtime pool (`recherche-generation-vegetale.md`).
- **A volumetric tree needs a volumetric supporting structure.** Check upper woody geometry independently of roots and leaves, in orientation-independent coordinates. A broad root footprint or extra foliage cannot validate a planar branch fan; reject the master before its variants and LODs (`spec-pipeline-creation3d.md`).
- **Structural reconstruction is an explicit authoring stage.** Record retained and reconstructed regions, recipe and seed; apply the same topology, volume and native art gates. Weld geometric seams before capping or solid reconstruction while retaining corner UVs (`spec-pipeline-creation3d.md`).
- **Reduction preserves a game asset's surface and motion contract.** Bake high detail onto low-mesh UVs; retain material masks, leaf coverage and attachment coordinates. A triangle budget alone does not establish acceptance (`spec-pipeline-creation3d.md`).
- **A woody LOD retains the resolved trunk.** Check source cross-sections and root surface error after reduction; reject a cook that loses supported volume (`spec-pipeline-creation3d.md`).
- **Vegetation uses one production validation chain.** Preserve a reviewed master, derive its LODs and impostors, then verify native appearance, transitions and paired performance. Missing or failed gates remain visible for every species and variant (`spec-pipeline-creation3d.md`).
- **A structural variant is a complete derived asset.** Keep its root zone, material and attachment contracts; derive its own LODs and impostor, retain its master and seed, and review its silhouette independently. A deformation cannot validate an invalid branch structure (`spec-pipeline-creation3d.md`).
- **Canopy coverage describes an envelope, not an opaque ceiling.** Ground and plants share bounded porous transport; shade boundaries follow world fields without changing plant presence (`spec-diversite-vegetale.md`).
- **Material reflectance does not contain a baked shadow.** Keep sun and sky transport separate through cloud compositing; ground objects store canopy cover independently of colour. An orbital biome palette containing forests does not specify exposed litter reflectance (`spec-rendu-vegetation.md`).
- **Observer adaptation meters incident world light, never the frame.** Reuse local canopy transport with bounded gain, fade above crowns and neutral night response; preserve the open and orbital exposure baseline. Apply this camera response after linear history (`spec-rendu-vegetation.md`).
- **A shared witness does not establish a diverse library's residency.** Validate the final catalogue with its distinct models and materials; account for resource sharing explicitly (`spec-pipeline-creation3d.md`).
- **Asset licences govern both source and cooked files.** Keep plant meshes, textures and derived binaries outside the public repository when their licence prohibits standalone redistribution; track acquisition references, fingerprints and import recipes instead (`recherche-generation-vegetale.md`).
- **Asset POCs run in Exolune with portable geometry and materials.** Verify access to those files before adopting a source; vendor-engine demos do not establish native integration or performance (`recherche-generation-vegetale.md`).
- **Plant behaviour follows the catalogue's material mask.** Woody burial and leaf motion must not assume that a source library uses a particular material order (`recherche-generation-vegetale.md`).
- **Changing the representation does not change the identity of the plant:** the mesh and its proxy take over the same instance; the removal of canopy uses exactly its screen presence rule (`vegetation-planetaire.md`).
- **Filtering a cut image retains its coverage:** color in linear light and alpha weighted values for mipmaps. impostors remain premultiplied until filtering; cut textures of meshes have dilated edges and mipmaps are set to their alpha threshold (`vegetation-planetaire.md`).
- **Superimposed coverings are composed by their transmission:** trees and shrubs can occupy the same ground; their union is `1 − (1 − arbres) × (1 − arbustes)`. Their addition can exceed 100 % and produce negative light.
- **The occlusion of the foliage filters incoming radiance:** sky and sun have their own visibilities; albedo and observer adaptation do not replace shadow transport (`vegetation-planetaire.md`).
- **Changing stochastic coverage needs a temporal consumer.** Depth and colour share their sequence; freeze it when temporal smoothing is disabled. Independent fades retain their joint coverage, and fractional alpha remains inside conservative depth bounds (`spec-rendu-vegetation.md`).
- **An optional GPU resource keeps a valid access range:** a branch can be flattened by the compiler. A SRV root without limits receives neutral data covering all possible clues, even when the effect is disabled.
- **A GPU limit never chooses objects in order of arrival:** the bounded selection follows a deterministic order; compaction and transition between representations must not vary the population with a still camera (`vegetation-planetaire.md`).
- **An occlusion rejection must cover the entire envelope actually drawn:** a depth of the current image, a conservative limit and a visible fold for any uncertain case. Source lists and drawing order are retained (`vegetation-hiz.md`).
- **A computation shift is validated by the GPU time, not by the number of instructions:** Work added to the vertex, transmitted data and commands can cancel pixel saving. Compare on the same poses, with the same population and without competing load (`optimisation-vegetation.md`).
- **Each limit is a measured law:** the growing season for cold, aridity, the Sankaran ceiling and Hirota modes for water; its thresholds are widened by the universal rule.
- **Where are the plants, a single rule with two scales, like the pebbles** (`Presence`): a field of noise above the threshold that leaves each state its share. The field of regions leaves entire regions without trees, whatever the soil; the field of spots opens clearings in any forest and arranges shrubs in thickets. Two independent fields: the product keeps the average.
- **The ridges lose their trees, the hollows keep them:** the height of the ground on the regional soil cools the season and lowers the fields of the woods. Never a rule specific to a mountain.
- **A distant plant stands on the drawn ground, a near one on the exact ground:** in the distance, it follows the ground that we see; its foot slides towards the exact ground while its shape refines. Never a plant floating above the mesh.
- **A plant never grows:** whole or absent, at its own threshold of the fade; its coarse form covers the screen as the fine. The forest it replaces has already its height: the distant canopy stands at the height of its trees, the ray of view crosses their crowns before the ground.
- **What replaces an object in the distance has its height, space and light,** measured on the object (benchmarks `relais`, `mouvement`).
- **A forest from far is the canopy of the ground, not millions of trees:** its share, its color, the relief of its crowns, the shadow it casts.
- **What the objects draw is removed in boolean layer:** 1 − (1 − cover)^ (1 − drawn part). Removed in simple subtraction, the forest lost 8 points where trees are born.
- **What the light sees under a cover is true for everything there:** the ground, the pebbles, the tufts, the bottom of the plants.

## The benchmarks, to check a rule

- **`tools/banc_qualite.py`:** the appearance on places drawn by material, from 12 m to 3 km: blur, scale holes, repetition, straight bands, mutation when the mesh is refined. Its reference: `tools/banc_qualite_reference.json`.
- **`tools/banc_descente.py`:** the viewed share of each material on a single square of soil, from 1 500 km to 100 m, with the diagnostic views `MYPLANETENGINE_VIEW`. A flat curve is a coherent planet.
- **`tools/banc_tremblement.py`:** the flicker at an exact position, copied from the title bar.
- **`tools/banc_halo.py`:** the halo around the sun and snow, in linear light, against the law in 1/θ².
- **`tools/banc_tons.py`:** the luminance of the ground and sky against the photos; the exposure in descent and when the camera turns.
- **`tools/banc_ombres.py`:** direct sunlight on a single ground, from 50 km to 200 m, at low sun. Its average must not move: on a rough soil, it is that of its average surface, regardless of the relief drawn. The shadow part, it, grows with him.
- **`tools/banc_carte.py`:** the map of the planet checked against the port numpy of the relief and against a separate written fill; its lakes and network measured against the Earth.
- **`tools/hydro/verifie_auges.py`:** valley profiles and joins, support conservation, bounded cuts, warping, soils and face boundaries on two seeds; complements the image benchmark without replacing it.
- **`tools/banc_mer.py`:** the reflection of the sun against Cox and Munk, pixel by pixel, windward of the pixel; downhill, the average reflection and the share of whitecaps against Monahan; the wind map. **`tools/banc_tremblement_mer.py`:** the flicker out of the sea when it moves, and the sea movement with or without smoothing.
- **`tools/banc_cretes.py`, `tools/banc_visuel.py`, `tools/realisme.py`:** peaks, views at multiple heights, distance to actual scans.
- **`tools/banc_objets.py`:** objects per ground in the counted photos, the distance between their foot and the mesh's ground along an approach, the rises along a descent, and the man-height views next to the photos.
- **`tools/banc_vegetation.py` :** biome cover, tree line, light connection between plants and the canopy, the orbit light view, the test views. With `banc_descente.py` and `forest` view: the share of forest per pixel, from 20 km to the ground.
- **The benchmarks render without window** and do not take the user's focus.
