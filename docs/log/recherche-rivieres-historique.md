# Rivers: spikes of October 26 and 27 2026

**Status: experiment set aside, out of `main`.** Tag `piste/rivieres-spikes`, `31a1271`, the old branch `codex/rivieres-spikes`. Start: tag `jalon/avant-spikes-rivieres`, the model Dendry, `b0252c9`. Result: tag `jalon/rivieres-cp-resultat-prometteur`, on the same commit as `piste/rivieres-spikes`.

**The following:** the search for a level erosion, branch `erosion-niveaux`, which contains the Dendry model, tag `piste/dendry-maquette`.

**To find the code:** `git checkout piste/rivieres-spikes`. Most of the `tools/…` and `MyPlanetEngine/…` files mentioned here exist only in this tag. Executables, caches and captures under `x64/` remained local.

**This file gathers the spike doc, taken from the tag:**
- **The final state:** sections 8 to 15 added to `../recherche-rivieres.md`, numbers kept.
- **Replaced tests:** the branch `log/recherche-rivieres-historique.md`.
- **The spikes log:** its entries of `journal-planete.md`, the most recent at the top; the log of `main` keeps only one short entry.
- **The branch rules and overlays:** its additions to `principes.md` and `geometrie.md`, which `main` does not take over.

## The final state, at the tag

### 8. Spike Phasor: authors reference and one octave bass

**reference frames git:** tag `piste/rivieres-spikes`; starting tag `jalon/avant-spikes-rivieres`. No commit or push; tag of the new attempt waiting for a requested commit.

**Status:** official reference reproduced locally, then adaptor of the cymbal to one octave. Code GPT-6.1 Terra xhigh; method, integration and judgment by the main agent. No benchmark at user request.

**To try:** `tools/lance-phasor.ps1`, or http://127.0.0.1:8766/phasor-spike/ when the local server is active.
- View Versant, source Bassin · 1 octave and seed 13 at startup.
- Original / Phasor compares the same terrain and the same pose; observe the furrows on the slopes.
- Small ravines activates the second level; Intensity adjusts the common amplitude.
- Water collectors is enabled on our basin; uncheck shows the bed with the same banks. The authors’ case remains unchanged, without added water.
- Seed / +1 regenerate the basin by the same procedural function.
- Terrain des auteurs allows to review the reference case; Ensemble broadens the framework.
- The launcher serves only locally, with a hidden process; it reuses the server or chooses a free port.

**Reproduction:** `tools/phasor-reference/` contains the official TerrainEnhancement repository, state `e0c75976013514e713bc05215927d4ec46462075`, with its shaders, framework and input cards. The demo is linked from the page of Charline Grenier. Original code preserved; adaptations in `tools/phasor-spike/`. The work captures use a 512² output, with the same calculation and original settings. Source and rights status documented in local README; no redistribution or engine integration decided.

**Retained method:** complex Gabor convolution guided by smooth relief gradient, rounded angular profile, radial attenuation of singularities and cascade. The authors' core and shaders are loaded without modification. The second level takes the amplitude factor 0,3 from the demo code; the article says 0,2. The frequency is multiplied by three. The peak fBm remains that of the authors.

**Adaptation to the basin:**
- Input: `RiverFirst.referenceSample`, one octave, without lateral and triangular tests. Region of 20 × 20 km centered on the basin, floating textures 512²; height divided by 3 km and fixed physical scale.
- Both shader height inputs receive the same original sampled terrain. The toggle does not smooth the reference geometry; the orientation gradient uses separate 16 passes of the authors smoothing.
- The automatic paper steering uses a drain card. Here, the amplitude is calculated from the procedural distance to the collector and the smoothed slope: `(1−exp(−d²/0,8²)) × g²/(g²+0,03²)`, d in km, g in physical slope. No new network or routing is calculated.
- Initial intensity 0,04, frequency 50: wavelengths of about 400 m then 133 m on the region of 20 km; height amplification of the order of 120 m then proportional to the first level.
- The reliefs are calculated in textures when changing source, seed or parameters; turning the camera does not regenerate the terrain.
- The normals of the basin come from the final height and its physical scale 3/20. The authors’ case retains their original normal pass. The shading of our comparison follows the displayed geometry.

**Collector water supply:** perimeter chosen by the user, without local drainage calculation for Phasor ravines.
- The level comes exclusively from `referenceSample.water`; the reference bed is already incised from 3 m. The Phasor amplitude is cancelled in these channels.
- The grid triangles are cut at the distance signed zero. The terrain and the bed share the bank peaks at the exact profile level.
- With water: off-channel land and opaque profile surface, without land surface superimposed in water. Without water: same triangulation of land and channel bed.
- The layer does not take the height of the bumps; no interruption by obstacle mask or automatic rise to the field.
- The triangulation is calculated when changing the basin or seed, and then stored in memory. The camera and the water balance do not trigger this calculation.

**Preliminary visual judgement:** comparison without/with on the official field, then on the 13 seed basin fixed. The new grooves are legible on the slopes; the large shapes and the bottom of the collector are preserved. Working captures in `x64/PhasorAuteur/` and `x64/PhasorBassin/`. The water/bed overview on the collectors confirms their reading at the bottom of the valleys and the bank connection. No benchmark or multi-seeds measure; user judgment remains to be collected.

**Limits:** this spike amplifies the relief and puts in water the existing collectors. Phasor ravines remain dry; no calculated drainage has been added, based on user decision. Their water supply and hydrological connection to the ocean remain open. The test area is regional and sampled; the planetary coupling and the port in the engine remain open. Previous tests are in the “Replaced Tests” section.

### 9. noise specialized basin: common structure and descent

**Goal:** to test a procedural core whose valleys, ridges and connected courts come from the same construction.

**To try:** `tools/lance-bassin-noise.ps1`, or http://127.0.0.1:8766/basin-noise/ with the local server active.
- The set shows sources, bifurcations and sea outlet in the same frame.
- Confluence and Versant bring the camera closer together, without changing the terrain.
- Sources overlooks the heads upstream; High Sources, activated at the start, varies their range and altitude. Uncheck returns the first version of the module, without moving the camera.
- Varied structure, activated initially, changes the subdivisions and common field; unchecking returns to the previous structure with the same sources and detail settings. The actual number of sections and sources is displayed.
- Uncheck Water shows the bed with the same banks.
- Slope detail enables gradient modulation; disabled initially to read the structure.
- Seed and +1 regenerate cells; the Reference link opens the Phasor basin one octave apart from this new terrain.

**Perimeter:** a macroscopic basin, before the Complex Planet detail; two to four levels of internal subdivisions in the current variant, three in the reference, distinct by an addition of octaves of relief. The octave reference remains accessible in the Phasor viewer of the 8 section.

**Construction:**
- The seed determines the transverse subdivisions and cell lengths.
- Each cell ends at its bifurcation; the two daughters inherit its position and width.
- The coordinate `y` increases upstream; the core curves do not return backwards according to this coordinate.
- A common profile `W(y)` grows upstream and is zero at the coast. A confluence therefore shares position and level.
- The distance to the finite cores defines the bottoms and the relief between the courses; the neighborhood boundaries form the ridges.
- The lateral relief and its detail are cancelled at the banks; the bed remains under the water profile.
- The land and the water share the cut of the banks; the camera does not reconstruct the geometry.

**Settings:** range of 22 × 23,5 km, including 2,5 km of sea; reference length of basin 18 km; fixed grid 448², grid cells of approximately 49 × 53 m. The reference gives 15 finished cores and eight terminal heads; the variant remains limited to 31 cores. Half widths of 150 m to 65 m, then extinction of sources. The distance per section and direction is not an exact Euclidean distance to the curve. Lateral relief `1,3 × (hypot(max(D,0),80)−80)^0,9`, attenuated at the coast; bed up to 4,5 m underwater.

**Various branches and crests:**
- End decisions are derived from the hash of each cell: possible stop at depths 2, 3 and 4; probability of continuation of 0,74 at 2 level and of 0,52 at 3 level.
- Cross-sharing ranges from 24 to 76 %; confluences have phase-off upstream coordinates. Children always inherit the parent’s end and profile.
- The common domain becomes `u=x+650 N(seed+4099,x/9000+17,31,y/4200−7,1)` m, with `y` unchanged. The derivative bound of noise gives `du/dx>0,54`; the transformation does not fold. The axes, the ridges and the water share this transformation.
- A slow modulation `1+0,22 N(seed+239,x/5200+3,8,y/6000−2,4)` varies the stiffness of the lateral relief. It remains positive and is cancelled at the banks by multiplication of relief; no independent mass is excavated afterwards.
- The descent keeps the same profile `W(y)`. The variation is visible without the slope detail; disabling Varied Structure retains the previous comparison.
- On seed 13: 21 sections, 11 sources at levels 2 to 4. Set and Source previews compared to fixed position; the distribution of branches is more asymmetrical. Profiles remain schematic and repetition is not declared fully resolved.

**Sources of various scope:**
- Parent cells and forks remain identical to the reference. A dedicated hash of each sheet gives `h`; its end becomes `max(yDépart+800,18 000 × (0,72+0,38 h²))` m. The initial generator calls are unchanged.
- With `t=y/18 000`, the common profile becomes `W=1 250 t+2 200 max(t−0,45,0)²` m. Its derivative remains positive; the downstream parts of 8,1 km keep the previous profile. Water and ground use the same profile.
- Disabling High Sources restores the old ends between `0,84` and `0,99` times 18 km, and `W=1 250 t` m.
- The optional detail combines three gradient fields turned, to 550, 290 and 150 m, weight 0,6 / 0,3 / 0,1, then factor `1+0,2 N`. The reference retains its only field at 550 m. The detail remains null on the banks by multiplication of lateral relief.
- The reference repeated a fixed depth binary construction and common valley profiles. The viewer samples this field; it does not create these patterns. The structure variant changes the subdivisions and domain, without yet establishing a complete natural morphology.

**Module nature:** noise hierarchical cellular structured, with identical rules for all seeds. No curve provided to the main, correction by location, simulation, path search or drainage of an old relief. This kernel goes beyond a simple sum of noise functions Perlin; the connection constraints are part of its definition.

**Scope of the descent:** the built axes descend to their coastal root. This does not prove that every point on the slopes joins a course without a basin. The oriented and bounded basin does not establish a planetary hydrology or its connection to any Complex Planet seed.

**Preliminary preview:** seed 13, overviews, confluence with water and bed, then detail and slope inspected. The High Sources variant is compared to the fixed reference in Sources view; three heads are towards 2 060 to 2 284 m, the others towards 1 159 to 1 355 m depending on the module profile. The connections and common ridges are legible; the relief remains schematic and the sources are synthetic. The geometry remains fixed when changing camera. Captures of work in `x64/BasinNoise/`. No benchmark or seed sweep; no claim to complete hydrological realism.

**Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No benchmarks, commit or push at user request; visual preview before presentation. Tag of experiment waiting for a requested commit.

### 10. First rendering of the kernel in MyPlanetEngine

**Status:** Explicit regional test, with materials, lighting, atmosphere and Complex Planet engine detail. The analytical core replaces the regional structure; it does not route rivers through an independent mass. Planetary hydrology is not integrated.

**Release:** `tools/lance-bassin-planete.ps1`, after compilation Release x64. The script exports the basin and then opens directly its general view and the `tools/tests/2026-10-27-bassin-noise.txt` palette: F1 set, F2 collector, F3 confluence, F4 branches, F5 catchment. `-Seed 13` by default; `-SansPlantes` allows reading the floor. Reproduction instruction in `tools/README-bassin-planete.md`.

**Shared field:**
- `tools/export-bassin-noise.cjs` executes JS model, high sources and varied structure enabled. It exports cells and water tape, without height map or mips.
- `MyPlanetEngine/Bassin.hlsli` evaluates the same cores, hash, domain deformation and water profile on the planet. Coordinates are taken in the reference frame tangent fixed, double before converting small shifts to floats.
- `Terrain.hlsli` places the core before the Complex Planet detail of less than about 1 km; the difference fin/grossier is limited to ±10 % of lateral relief. It is therefore zero on the banks and does not determine the water level.
- River passes reuse the exported profile; their cut comes from the analytical signed field. No obstacle mask or raising the layer on the bumps of the field.
- The cache contains cell parameters; changing cameras does not choose another height map or network structure.

**Test area:** window of 64 km, reference frame centered on 34° N / 40° O, radius 6 378 km. The center of the reference frame corresponds to `y=9 km` in the pelvis. Transition of 8 km to the outer terrain, outside the judged confluences; this presentation border does not define planetary basins. The pool seed is 13; Complex Planet’s own seed remains 0.

**Enable:** `MYPLANETENGINE_BASSIN` variable to versioned analytical file; old Dendry format follows its separate path. The launcher restores its environment variables after opening. Without this explicit mode, the engine uses its usual terrain.

**Preview:** confluence and overview inspected in native rendering. Water connected to the two branches at the confluence; uniform water and steep banks. The whole reveals a coast too straight, a sea in band and courses not readable at this height; the regional composition remains to be resumed. Images `x64/BasinNoise/planete-confluence.png` and `planete-ensemble.png`. This preview does not validate the movement, all levels of mesh or a global hydrology. No benchmark or seed scanning.

**Practical limitation:** the first Release initialization required several minutes and a large memory during shader preparation. The `MYPLANETENGINE_CAPTURE_FRAMES` option only shortens the number of preview images after initialization; it does not resolve this cost. Native rendering is offered as a test, without performance validation.

### 11. Three neighbouring basins on a coast Complex Planet

**Goal:** to test the connection between basins before a planetary organization. The previous kernel exists and remains accessible; this step generalizes its domain and CP entries.

**To try:** `tools/lance-bassins-cotiers.ps1`, or http://127.0.0.1:8766/coastal-basins/. Views Together, Common Ridge and Mouthpiece; Water and Relief CP tilt without changing the pose. The 0 seed is common to the coast and the three networks; no command changes the trees alone by pretending to change CP.

**Source CP:**
- `tools/coastal-basins/prepare_cp.py` uses CP's NumPy port and repository gradients. `tools/hydro/cp.py` now finds `LibNoise.hlsli` in relation to its file.
- A deterministic search for sign changes on the sphere proposes sections; the program retains a coastal graph `y=C(x)` sampled from the sea to the land. It fails explicitly if no candidate fits; no invented coast of escape.
- The 256 coastal points are zeros of the full CP elevation, filtered to 500 m, including its original riverine noise. Linking them linearly is an approximation; on seed 0, the height difference at the middle of the segments remains less than about 2,6 m in the preparation diagnosis.
- The current set covers 75 km of coast; reference frame tangent close to 2,868° N / 78,750° E. The earth axis of the reference frame is determined by the CP gradient, without test latitude imposed on the geometry.
- Two CP controls of 192² values: `middle=clip((mountain_base(cell=2000m)+1)/2,0,1)`; `fine=clip(0,5+mountainous(cell=grille)−mountainous(cell=2000m),0,1)`. These are relief control fields, not final basin heights.

**Joint construction:**
- The upstream coordinate is `v=y−C(x)`; the outlets are on `v=0`, the sea on `v<0`.
- The latent domain `u=x+650 N(seed+4099,x/9000+17,31,v/4200−7,1)` retains `v`; its derivative following `x` remains positive. A branch point reverses this field and returns `y=C(x)+v`.
- Three contiguous transverse partitions produce three seeded trees, lengths between 15 and 23 km; at most 93 sections. The current set contains 57 sections.
- A single minimum distance at all sections defines the valleys and ridges between the basins. Land is not calculated and then merged separately.
- The common profile `W(v)=1 250 t+2 200 max(t−0,45,0)²`, `t=max(v/18 000,0)`, guarantees the descent on the axles and the common level at the junctions. The coast gives the same zero to the three roots.
- The lateral relief is `1,3 × (hypot(max(D,0),80)−80)^0,9 × (1−exp(−(v/5000)²))`. The coastal envelope gradually rises on 5 km, instead of imposing the prototype rampart.
- Relief CP multiplies this relief by `(0,72+0,65 middle) × (0,78+0,44 fine)`, strictly positive. The relief remains zero on the banks, the bed is up to 4,5 m below the water profile.
- The mesh of the viewer follows fixed `v` lines; axis and shore points complete the background grid. The triangles terre/eau share their edge vertices; the normals come from the displayed geometry.

**Pre-view:** Set, Mouthpiece and Common Ridge inspected, then even laid without Relief CP. The three networks join the sea and the ridges are continuous between basins; CP controls enrich the relief. Profiles still schematic and traces of sampling visible on some ridges. Captures in `x64/BassinsCotiers/web-*.png`. No benchmark or seed scanning.

**port native V2:**
- `tools/lance-bassins-planete.ps1` opens the Release engine with the three basins and the `tools/tests/2026-10-27-bassins-cotiers.txt` palette: Together, three confluences and Central mouthpiece.
- `tools/export-bassins-cotiers.cjs` exports 57 cells, 256 edge points, two CP fields 192² and 35 754 ribbon vertices. The V2 header remains separate from the single pool; the old mode retains its launcher.
- The reference frame comes from the CP game; the palette and sun are derived from this reference frame and branches, without test coordinates copied from another region.
- The HLSL kernel reads CP controls in the same place as the JS model. In his heart he does not recalculate two times full CP; the outside remains CP. The normal and filtered CP calls of histories paths are factorized without changing their formulas.
- The native window of 100 km has an external transition of 8 km. Its upstream limit comes from the highest source plus 8 km; the coupling begins after the sources, which avoids extending the polynomial profile out of domain.
- The launcher restores its sun, data, and vegetation variables. The native explicitly refuses any seed other than 0, its compiled CP seed; it does not mix a new coast with an old planet.
- Compilation Release successful, Materials warnings known only. Native overview inspected: irregular coastline and large sets of legible valleys, very fine courses at 40 km. Images in `x64/BassinsCotiers/native-*.png`; no benchmark or motion validation.
- Central mouth inspected after correction of the framing from the sea: the ribbon joins the sea at the same visible level. Banks still angled and water uniform; the connection reading does not validate a delta, movement or changes of grid cell.

**Scope:** a coast represented as a graph, three basins and a prepared seed. The evidence concerns the built courses; neither all the drops of the slopes, nor all the continents, nor the spherical connections of a world cut-out are established. Lakes, deltas, flow and spring climate remain open. Searching for a zero of noise coastal does not add any drain or routing to the network.

**Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No commit or push; experiment tag waiting for a requested commit.

### 12. Global cellular organization on the CP sphere

**Status:** rough world prototype in `tools/global-basins/`, off engine. The local one-octave basin and coastal test remain accessible. The first global version with free arcs is preserved in [history](#tests-replaced); its too straight branches could cross or cross a bay.

**To try:** `tools/lance-bassins-globaux.ps1`, or http://127.0.0.1:8766/global-basins/. Switch CP current / CP + basins keep pose, lighting inspection, grid and amplification. Structural grid displays the axes, without water surface. The Current Basin and Current Basin Mouth views are cameras from the same globe. See hidden axes explicitly displays the topology above the grid: this scheme does not validate its incision.

**CP entry:**
- Common seed 0, radius 6 378 km, 32 514 directions and 65 024 triangles; shared poles and closed seam. The equatorial grid cell is worth about 157 km.
- The full CP height filtered to 30 km provides the terre/mer sign and altitude controls. It still includes the native CP river noise; the bands are not all separated. The mountain weight CP modulates the selection of sources.
- 4 154 Coastal zeros are refined on sign-changing edges. Continental fields and filtered elevation at 10 km are exported, without yet forming a new detail band.

**noise specialized and preparation:**
- The module generates a discrete global cellular structure and then a continuous relief field. This preparation depends on the grid and the seed; it is not a simple octave Perlin evaluated isolated in a point.
- Each CP triangle is cut at coastal zero into a convex terrestrial polygon. Connections only pass through shared portions of the ridge; they cannot jump over a bay in this area.
- Coastal outlets spaced 600 km are selected in each land component. A macroscopic cellular noise assigns the centers to the coastal site closest to their component.
- Kruskal builds a seeded forest: internal connections to a macroscopic cell first, hash then; a union never unites two components already equipped with an outlet. The separated pieces of a cell can join another basin through a ground connection.
- This forest is the generated topology of the module. No slope cost or optimal path on CP altitudes, no flow, bowl filling, corrective displacement of old routes or erosion simulation.
- Source cells are selected with probability of 2 to 4 % depending on mountain weight. A high altitude cell provides selection when a tree has no cell; branches without a source are pruned. Active sheets take the CP height interpolated at their center.

**Curves and profiles:**
- Each port is shared in position and altitude by its two cells. The junctions are internal, with positive barycentric coordinates.
- Around a true junction, each arm remains in its fan triangle, distinct from those of the other arms. The curves have positive controls and monotonous radial progression; their polylines remain in these sectors.
- In two-port cells, a single cubic connects them without a center-imposed passage. Its controls remain in the convex polygon in gnomon projection; their progression by thirds of string excludes a loop. Sources and true confluences retain their centers.
- Ports aim at a common tangent; only continuity in position and altitude is guaranteed everywhere. Fan cells use four segments per arm, crossed cells use eight segments per curve.
- The minimum of descending source heights multiplies `depth/(depth+12)` for junctions; the leaves take their positive CP height. Ports keep a common level between parent and child and each outlet is worth 0.
- Profiles interpolate these levels monotonically; the spatial curvature does not add noise to the water height. The evidence is about the axes built, not about every drop of the slopes.

**Common field:**
- The small curve arcs and coastal arcs of level 0 carry compact support cores of 450 km. The weight is proportional to their length and to `(1−u)^4(1+4u)/u^4`, with `u=d/L<1`.
- `W=(0,01 H_CP+Σ wᵢhᵢ)/(0,01+Σ wᵢ)` continuously returns to CP out of supports. The exactly recognized axes and junctions return to their shared level.
- `H=W+max(H_CP−W,0) × smooth(D/120 km)` defines the relief around the same grid. This width represents a rough global structure, not that of a realistic channel.
- A fixed 3D space grid accelerates the cores of this compact function. The camera does not select another structure or height data.
- The viewer subdivide the source into 130 050 vertices and 260 096 triangles. On coastal ridges, the new summits are CP zeros; elsewhere, CP heights are interpolated. Both modes share this grid, their geometric normals and the initial visual amplification ×20.

**Limits:**
- The absence of sea passage concerns the coastal polygons of this grid. The CP coast continues thinner, the small islands and the missed sign changes remain to be rebuilt.
- The resolution and orientation of the grid cell influence the shape. The network is not a hydrological reconstruction; the main lines of division of the massifs are not yet deduced from CP.
- `W > H_CP` can lift a low ground. The new module may significantly alter the terrain near the courts; the exact preservation of the mass is not guaranteed.
- The globe grid can mask the axes and does not sample the banks. The zoom with bed and water is described in section 13; the globe has neither reconnected slope detail nor global port in the engine.
- Only one seed is prepared; changing seed requires regenerating CP and module together. No judgment of stability at all levels of mesh is established.

**Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. Targeted syntax and preview; no benchmark, multi-seed scanning, commit or push. Tag waiting for a requested commit. Detailed construction in `tools/global-basins/README-reseau.md` and `README-modele.md`.

**Current set:** 35 956 terrestrial cells, 217 outlets, 9 410 active cells, 610 effective sources and 74 412 small arcs. Preparation is independent of the camera; staffing is not a measure of hydrological quality.

**Preview:** same seed 0, globe and basin compared to fixed-position CP, mouth and island of 131 land summits inspected; no JavaScript errors on loading. Softer curves, continuous connections in the complete scheme and axes contained in the earth visible on these frames. The meanders remain sometimes systematic, with tight returns; the wide relief and the grid cell control are still visible. The features masked by the grid remain a sampling defect of the terrain, distinct from the constructed topology. Captures `x64/GlobalBasins/cell-review-*.png` and `cell-final-*.png`; no benchmark or multi-seeds validation.

### 13. Bed and supply of water of the global network

**Status:** coupled spike of bed, banks and water, in `tools/global-basins/water.html`. Views are fixed sampling windows of the same global module; no other network or local terrain is generated. The globe of the 12 section remains the structure reference. No additional native port.

**To try:** http://127.0.0.1:8766/global-basins/index.html?water=1 first opens the sphere, centered on the test site identified. The Planet → Basin → Bed and water pathway announces the change of scale; See the test basin frame its network before Approaching the water. The old entry `water.html` returns on this globe. `water.html?detail=1` explicitly opens the zoom of 32 km, with CP locator and visible returns to the planet or basin.

**In zoom:** Collector, Confluence and Embouchure frame the same basin; Berge brings the camera closer to a bank of the collector. Water masks the layer by preserving the ground and the laying. View together or R restores the framing. The wheel approaches; drag rotates, shift-drag moves. The water remains tested in these windows; its water supply on the entire sphere is not realized.

**Shared profile:**
- `model.sampleChannel` reuses the `W` level and `D` distance of the global model without changing the sources, junctions, curves or their 0 seed. The reference `sample` and the heights of the globe remain accessible.
- Half width `b=300 m`, nominal depth `p=8 m`, structure width `L=120 km`. These are uniform spike settings, without flow or hydrological calibration.
- On land: `q=max(1−(D/b)²,0)²`, then `H=W−p q+max(H_CP−W,0) × smooth(max(D−b,0)/L)`. On the bank `D=b`, the bottom joins exactly `W`; in the channel, the bottom is below.
- At sea: water level 0, `H=min(H_CP,−p q)`. The bed continues under the marine layer at the mouth. The coastal supports of level 0 keep the connection with the river profile.

**Geometry:**
- A frame rule chooses a confluence near an outlet, then the middle of its descending arm and its root. The choice does not change the module.
- CP controls are the same subdivided triangles as the globe, with shared coastal zeros. Radial barycentric interpolation provides CP control to the new points.
- Each window measures 32 km of side, fixed grid of 256 squares per side, no 125 m. Additional intersections follow the coast and banks.
- Each triangle is cut first at zero CP, then at `D−b=0` on the earth part. Edge intersections are cached and reused by neighboring triangles.
- The terrain retains all polygons, dry or wet. The layer is triangulated once in the wet union: a confluence does not overlap several independent ribbons.
- The bank peaks have exactly the same position in the ground and water. Masking the water therefore keeps the bed. The river and marine waters return to their common coastal peaks of level 0.
- Local metric positions include planetary curvature, calculated in double precision before conversion to floats. The normals come from the displayed terrain. No water displacement to hide a depth defect.
- The camera does not rebuild the network or the mesh; views are cached. The ×1 or ×3 amplification acts identical on land and water; the graphic depth is logarithmic for close inspection.
- In Collector and Bank, a cut intersects the actually displayed triangles, land and water, on ±800 m across the course. Its meters axes have distinct scales; it retains the heights ×1 and does not replace the 3D geometry.

**Scope:** the test is about the translation into geometry of the already built network. The width remains constant, the mesh represents approximately the profile of 8 m, the coast remains that of the rough controls and the materials are sober. Sources, deltas, flow, fine CP detail, mesh level changes and engine performance are not validated. Sources are not validated.

**Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. Targeted syntax and previews, no benchmark or seed scanning. No commit or push; tag waiting for a requested commit. Notes `tools/global-basins/README-eau.md` and `README-eau-geometrie.md`.

**Overview:** seed 0, basin 55, confluence of cell 12 342 at about 5,66 m, near 6,24 km from its outlet. Confluence and connection to the sea inspected; the sheet remains continuous in these frames. The collector ground keeps its bed when water is masked; the mesh cross section shows a bottom near −5,2 m under water to 2,8 m. Approach of 180 to 100 m and small rotation inspected, same object of mesh retained and no JavaScript error. Made still very sober and roughly not perceptible in wide view with 600 m width; no validation of all places or levels of detail of the engine. Captures in `x64/GlobalWater/review-*.png`.

### 14. CP reference and native comparison

**Reference:** CP complete provides the terrain and the roughness, with all its bands; no approximation of the gross globe replaces the mountains.

- B swing original CP / CP + rivers with the same pose, the same lighting and the same finesse.
- The CP height at the nadir sets the grid cell and the near plane in both states; the collision follows the active field.
- The regional map remains original CP; no historical drainage feeds the fluvial module.
- It masks the water and keeps the bed.
- The first assembly with independent profiles could raise the floor; its code and views remain in `x64/GlobalBasinsAvantMorpho` for comparison, its report in [history](#tests-replaced).

### 15. Profiles bounded by CP, meanders and variable widths

**Goal:** to remove river mounds, preserve CP reliefs and make the courses less straight and uniform.

**Module structure:**
- The seeded cellular network retains its terrestrial topology and shared junctions.
- Two gradient noise functions, at the steps of 12 km and 3,5 km, deform the arms in their eligible sectors.
- The displacement is bounded by 70 % of the sector margin and 2 200 m; the second noise weighs 0,45.
- A C1 fade of 1,2 km at each end preserves the fittings without removing the curvature on the first kilometers.
- Phases are seeded by arm to avoid aligning the starts of the noise functions. The subdivision refines the curve according to a deviation at the middle of the string of `max(10 m, 25 % de la demi-largeur)`, with target step of 125 m to 1 km; a polygonal approximation remains.

**Profile and coast:**
- `CPNoiseSampler.hlsl` directly calls `ComplexPlanetElevation`, at the same axis and bank positions, to two fixed grid cells of 32 m and 256 m.
- This evaluation is part of the module generation; no flow per frame, slope routing or cuvette filling is added.
- Each terrestrial source maintains its built path until the first marine contact of the sampled CP; the path is cut there, without continuation at sea and then on land.
- The nodal envelope takes the minimum of the two CP references and banks, with margin of 8 m; its inherited minimums constrain the profiles downstream.
- The analytical factor `d / (d + 20 000 m)`, with d the distance to the new outlet, gives a common slope under this envelope and joins 0 to the sea.
- Contacts are interpolated between probes; this does not prove zero or drop at any point of the continuous CP.

**Bed and width:**
- The ground is `min(CP, lerp(CP, W - profondeur, masque))`: this module never raises the CP geometry.
- The connection mask decreases to zero on 3 km from the shore; out of influence, the terrain is CP exact.
- The half-width starts at 4 m at the source and grows with the number of sources gathered; its base is `24 sqrt(nombre de sources)`.
- A consistent variation of coefficient 0,3 and step 9 km changes the width along the arms, with the same fading at the junctions.
- The evapotranspiration reaches a factor of 2,2 on the 25 last kilometers before the outlet; depth depends on width.
- It is a broadened mouth; no distribution arm fan or delta depot is yet built.

**Format and cost:**
- V4: 32 floats per segment, high+low precision positions, levels and widths at both ends.
- The 3D hash sparsely of grid cell 20 km queries a media of 12 km, against 450 km previously.
- Sections are aligned on 64 floats; their large addresses are reconstructed in uint, relative IDs and offsets remain exactly representable.
- Seed 0: 1 456 417 river segments retained, 196 new marine contacts, data of about 268 MB.
- On 610 initial sources, 18 are at sea in the finest CP and are excluded by the land mask.

**To judge:**
- `tools/lance-global-basins-planete.ps1` opens `x64/GlobalBasinsMorpho/bin/MyPlanetEngine.exe` and the `tools/tests/2026-10-27-global-morpho.txt` path.
- F10 confluence in general view, F4 in the same place close up, F3 source, F5 collector, F8 relief CP, F9 refined mouth; F1 and F2 keep the planetary context.
- The inspection fineness is 0,25; the avant/après comparisons keep this same value and the same absolute poses.
- `x64/GlobalBasinsMorpho/comparaison.html` compares old and new module; B in engine compares original CP and new module.

**Limits:**
- The stress on the axis and banks is sampled, not demonstrated between probes.
- At coastal contacts, probes have a CP negative ground under zero water; the sea and channel are cut off by the native CP sign.
- The water banks still follow the interpolants of the mesh; the thin channels require a grid cell thinner than their width.
- The validity on other seeds, the movement and all changes of grid cell remain open. The cost of GPU remains sensible in some views.

**Verification:** Isolated release compiled; three pairs of native source, confluence and mouth inspected, same absolute pose, sun and fineness 0,25. The elevated head of the source disappears and marine contact is restored; the widths change between source, collectors and coast. The large organization of branches remains geometric despite the added curves, and the river retains a uniform appearance in some close-up frames. The details of the bed and the stability in motion remain to be judged. Final captures `x64/GlobalBasinsMorpho/{source,confluence,embouchure}-{avant,apres}.png`, local page `comparaison.html`. Automated opening of local files is blocked by the built-in browser; native images were inspected directly. No benchmark or seed scanning.

**milestone:** `jalon/rivieres-cp-resultat-prometteur`, backup of sources and tools requested on 27 October 2026 on the branch of the tag `piste/rivieres-spikes`. Executables, caches, and captures in `x64/` remain local; playback commands are in `tools/README-global-basins-planete.md`.

**Work:** code GPT-6.1 Terra xhigh; architecture, orchestration and judgement by the main agent. Promising result with the above limits; no additional benchmark for this backup.

## Tests replaced

### 2026-10-26 · Dendry profile raw · spread

**Try:** transmit the profile of the tree to the bake, dig under it and put the tops of the channel at its level.

- **Result:** walls of water above the valley on captures at 600 m and 30 m.
- **Cause:** the terrain takes the lowest of the superimposed valleys. The profile of another branch can therefore pass over the obtained ground.
- **Measurement before correction:** water-ground difference at course, p90 84,8 m, p99 347 m, maximum 1 171 m. 8,5 % of samples exceed the ground by more than 100 m.
- **Other defect:** the tributaries end on the axis of the parent before its meanders. They can miss the visible course by several hundred meters.
- **Next:** Boundary profile by the land, spread the lowerings downstream, connect the tributaries to the meandering course and spread the banks of the incision.

**The original rendering:** the bake kept only the point of the course, the width and the distance. The pixel colored the relief without changing the height of the water. No channel was dug under an independent profile.

### 2026-10-26 · Profile incised on interpolated fields · spaced

- **Settings:** Profile margin of 2 m; minimum slope of 1 m/km; bank connection at least two half widths, or 1,5 times the incision.
- **Profile:** 194 156 knots, no rise; median lowering 2 m, p95 11,3 m, maximum 573 m.
- **Faults:** 293 m grid cuts courses into rounded pieces; residual indoor water-ground overflow up to 4,5 m. The fine relief and the mips do not yet share the profile reference.
- **Captures:** seven views; 13,8 s with Dendry2 vs 8,2 s with first build fixed, different caches possible. This time is not an isolated measure of river cost.
- **benchmark quality:** 30 places, seed 1, reference of the 24 October: 22 of the 57 comparable p95 exceed +10 %. Twelve control captures at three locations at 12 m and 3 000 m are identical to Dendry2 from October 25.
- **Pallet replaced:** `tools/tests/2026-10-26-dendry-profil.txt`.

### 2026-10-26 · Minimum of vector edges · spaced

- The minimum of all incisions can dig the ground under a high river in the vicinity of a much lower bed.
- On 3 025 off-channel probes in the active zone: maximum overrun of 529,31 m; 13 points above 0,1 m.
- Worst case found: latitude 34.241986, longitude −40.289026; course levels 4 248 m and 3 680 m, distant about 135 m.
- The first Shepard partition with a discrete selection of channels removes the overflow, but creates a jump of 3,60 m at their edge.
- The suite continuously extends the off-channel constraint; no `distance <= half` selection changes the terrain per jump.

### 2026-10-26 · Replaced · Edge and Profile Iterations

- **Partition without coupling:** 3 025 banks off active channels, maximum overhang 6,23 cm. The view of the worst old pass reveals however a very steep artificial gorge; the level control is not sufficient for visual judgment.
- **Coupled profile with repeated bed and margin:** spread out; take the bottom of the neighbor as water ceiling and remove again 3 m at each pass forces a diffuse drop. This result does not demonstrate a divergence of coupling limited to banks.
- **Limited to bank coupling:** only other branches, out of their channel; no additional margin withdrawal. The 12 and 36 passes significantly improve the extreme case. The variant of 36 passes remains explicitly non-converged.
- **Vertical simplification to 24 cm:** the new profile reveals a deviation of 17,26 cm on one shore. The bound is reduced to 4 cm; the full benchmark of the current spike then passes with a maximum of 5,10 cm.
- **Fix the benchmark coupling:** cells of more than 128 probes were requesting packet offset in local reduction; fixed, then 36 passes replayed from initial profile. Unfinished data now causes an explicit failure.

### 2026-10-26 · Vector model and coupling · dismissed after flight test

**User observation:** Geometry and flicker significant mutations when approaching rivers. Profile checks and fixed captures did not validate this stability. The slippage of the mesh is a hypothesis, not a proven cause.

#### Old condition · Model Dendry: water profile, springs, delta

**Current spike: continuity and incised bed, 2026-10-26.**
- The network of 150 km maintains an independent water profile, strictly descending downstream and shared at the confluences.
- The profile is capped 3 m below the Catmull-Rom ground of the bake, on the axis and both banks, with probes spaced 2,29 m at most. Any lowering spreads downstream.
- The vector sections replace the five river fields interpolated at 293 m. A grid of 512² cells gives the candidate segments, without deciding the connections.
- A triangled ribbon carries water independently of the ground mesh. The pixel cuts its edge according to the union of the channels; the ground is actually incised under the profile.
- The coordinates remain in double precision precision until the subtraction of the segment point. The steps due to planetary quantification must not enter the local relief.
- The radius of bank varies by monotonous Hermite, shared to the connections. In its corridor, the terrain uses the same Catmull-Rom mip 0 as the profile; detail and filtering return to 100 m.
- Before rendering, 36 passes lower profiles that the banks of other courses make incompatible. These drops spread downstream; 1,65 % of points drop by more than 1 m.
- The adjacent banks are then combined by a continuous partition; an extended channel constraint protects the depth without suddenly changing branches.
- The simplification keeps the water level to 4 cm close, and the plot to 5 % of its half width close.
- The ribbon appears at 8 km from the edge and reaches its full coverage at 10 km. This border is a model fitting, not a mouthpiece.
- Tests excluded and intermediate measurements are in [the history](#tests-replaced).

**To test:** `powershell -NoProfile -File tools/lance-rivieres.ps1`.
- The `tools/tests/2026-10-26-dendry-continu.txt` palette offers twelve views, accessible by buttons and F1 to F12. Absolute altitudes are synchronized from the GPU tracks.
- Adding `-SansPlantes` to the launcher allows the banks to be read, including the F11 view hidden by a tree.
- The executable is `x64/Release/MyPlanetEngine.exe` and the bake is `tools/hydro/proto/dendry-2026-10-26-continu.bin`.
- Without `MYPLANETENGINE_DENDRY`, this overlay is disabled.

**Reproduction of the bake:** after the field and network cache `*-river-input.npz` produced by `dendry.py`:
```powershell
python tools/hydro/river_profile.py tools/hydro/proto/dendry-2026-10-26-river-input.npz tools/hydro/proto/dendry-profile-catmull.bin
python tools/hydro/river_segments.py tools/hydro/proto/dendry-2026-10-26-river-input.npz tools/hydro/proto/dendry-2026-10-26-river-segments.npz --profile-cache tools/hydro/proto/dendry-profile-catmull-profile.npz --water-tolerance-m 0.24
python tools/hydro/river_profile_coupled.py --passes 36 --output tools/hydro/proto/dendry-profile-coupled-checked-36.npz
python tools/hydro/river_segments.py tools/hydro/proto/dendry-2026-10-26-river-input.npz tools/hydro/proto/dendry-coupled-precis-segments-36.npz --profile-cache tools/hydro/proto/dendry-profile-coupled-checked-36.npz --water-tolerance-m 0.04
python tools/hydro/build_river_spike.py tools/hydro/proto/dendry-2026-10-26-river-input.npz tools/hydro/proto/dendry-coupled-precis-segments-36.npz tools/hydro/proto/dendry-2026-10-26-continu.bin
python tools/hydro/river_spike_checks.py
```

**Current format:** header16 and 512² field, then payload version 2: prefix16, CSR index, 12 floating segments and 4 floating ribbon vertexes. The coordinates of the sections are in local kilometers; heights, widths and radii are in meters. Offsets count floats. The loader adds the mips and encodes the payload's signed offset into `header[15]`. The historical five-field format remains readable.

**Limits:**
- The edge of the network remains its outlet; neither glacial springs nor the connection to the ocean or deltas are implemented in this spike.
- The land remains a bake at 293 m. The rare incisions reach about 602 m. The preset clearly softens the throat of F10, but it remains stiff; very small courses can be partially masked by the mesh seen from above. This case remains visually unaccepted.
- The preset in 36 passes is not a converged solver: its auxiliary bound on the neighboring banks keeps a maximum residue of 0,617 m on 186 points. The weighted final digging passes its separate control to 0,1 m. This coupling remains an experimental experiment.
- The water color is temporary. The judgement is on continuity, level and banks; animation and water materials remain to be worked on.
- The independence of the tape does not give the mesh of ground an infinite resolution: the very small channels seen in the distance remain a case to watch.

**Parallel work of this spike, three sub-agents GPT-6 Luna xhigh:**
- Continuity: bounded simplification, sections, index CSR and water ribbon.
- Profile and bed: Catmull-Rom profile, continuous bank radii and fittings.
- Validation: independent sampler, profiles, banks, index, accuracy and superimposed digging.
- The main agent integrates format and shaders, compiles and checks captures without window.

**Proposed architecture:**
- **`RiverGraph`:** Global hydrological map, linked to `PlanetMap`, with runoff and melting sources, nodes, receivers, flow and outlets mer/lac. Dendry adds tributaries between graph anchors; he does not choose the mouth.
- **`RiverProfile`:** topological pass that gives a water level per node and imposes a drop downstream. Lakes are flat areas that connect two levels of the graph.
- **`RiverBed`:** width and depth from the flow; the ground is incised below the water level, and the water surface is rendered separately at the profile level.
- **`RiverReach` and water ribbon:** continuous polyline, anchored on the planet, with water altitude, flow, width and depth at its points. An independent water geometry follows this polyline. The sections are indexed by tile for digging; the rough field of the nearest point no longer decides the visible connections.
- **`RiverDelta`:** at an oceanic estuary of sufficient flow, the course splits into distributors in a range deposited on the coast. Delta is not a type of source or a rule applied to lakes.

**Joint contract for future parallel tasks:**
- **The graph is read-only** after its construction. Each cell has a stable key, a receiver or outlet, a drained area, a flow and a source contribution (rain, melt, or both).
- **Lakes are explicit nodes.** The inner graph is cycle-free; an inner node has only one receiver. Each outlet provides its type and water level.
- **The profiles consume the oriented edges** and render a water level per node. Beds consume this profile and flow; they do not recalculate drainage.
- **A section retains its ends and its direction.** His contract contains his polyline, his abscisse along the course, his water levels, flows, widths and depths, with declared units.
- **The deltas consume the marine estuaries** and make their distributors and deposits as local geometry. They do not change the inner graph or the profile of the upstream river.
- **The integration is the sole owner of the bake format and shaders.** It fixes the test views and checks the connections between deliverables.

**Future lots, after judgment of continuity and bed:**

| Lot | Deliverable off engine | Limit |
|---|---|---|
| Sources and drainage | oriented graph, rain and melting flow, path from a mountain source to the ocean | does not modify any shader |
| Profile and bed | continuous vector sections, downstream levels, channel and banks on a provided graph | does not choose sources or outlets |
| Delta | fragment to distributors, flow sharing and deposit for a coastal outlet provided | fixed the entrance of the river |

- **Before parallel work:** fix the contract and two small data sets, mountain-ocean and coastal estuary. The profile and delta batches start on these datasets.
- **The main agent integrates** deliverables, water tape, and section index into the engine. It holds the captures and the benchmarks. Each batch delivers a short pallet for flight judgment.

**Order of spikes:**
1. **Profile and bed on the model of 150 km:** remove the height following the bumps, incision channel; no change at the source of relief.
2. **Mountain springs to the ocean:** Inject runoff and melting, connect small streams to the global network, check profile and confluences.
3. **A coastal delta:** choose a single large outlet, create its distributors and the depot, then test the approach from the plane and the ground.

**Measurement contract:**
- no segment of the profile rises downstream;
- the channel bottom remains under water to a depth determined by flow;
- the mountain scene's springs join the same network to the ocean;
- Delta arms remain connected to the river and reach the coast without crossing land upstream.

**Verification of the vector spike:**
- Build Release x64 successful; twelve views captured without window, at ground and aircraft altitudes, plus twelve captures without plants.
- benchmark CPU complete: 4 817 634 probes, including 2 348 399 in the active domain; no rise or edge break. On 3 132 probes out of channels after combination of incisions: maximum exceed 0,0510 m, below the threshold of 0,1 m. The extreme case of F10 remains visually unacceptable.
- benchmark current quality: 1 350 views on the same thirty places and caps of the first benchmark. The comparable 59 p95s are identical to the first spike; no new overruns. Faced with the official reference of the 24 October, 22 of the 57 p95 exceed still +10 %, so the global acceptance remains unearned.
- Local results: `x64/Release/river-spike-checks-precis-final.txt`, `x64/Release/rivieres-pret-a-tester/`, `x64/Release/rivieres-pret-a-tester-sans-plantes/`, `x64/Release/qualite-continu-2026-10-26/`.
- The official reference has not been replaced. Previous tests are in the history.
- To redo the captures: `python tools/banc_rivieres.py x64/Release/MyPlanetEngine.exe --dendry tools/hydro/proto/dendry-2026-10-26-continu.bin --tests tools/tests/2026-10-26-dendry-continu.txt --out x64/Release/rivieres-rejeu`. Add `--sans-plantes` to read the floor.
- Work without commit or push. The experiment tag is waiting for the requested commit after fly judgment.

### 2026-10-26 · Two-course analytical viewer · replaced

### Old section 8 · New spike: a relief built with its rivers

**Status: Standalone viewer implemented, first benchmark executed.** The vector Dendry test is dismissed after the regression observed in flight. Its state, measurements and limits are in [history](#tests-replaced).

**Question to be answered:** Does a unique geometry, built around known waterways, remain stable during an approach and when the mesh slips?

**User restriction: mathematical composition of noise functions.** The target retains the modular architecture of complexplanet: deterministic procedural fields, octaves, domain deformations, curves and generic operators. Location-based exceptions, pass-profile retouching, and corrective solvers are not part of this experiment. A separately calculated drainage graph would be another approach, to be explicitly distinguished.

**Note:** The current viewer uses two predefined curves and an imposed linear profile. Its function is pure and independent of the camera, but it is not yet a generic river noise. It verifies a valley cut and its sampling; it does not demonstrate a procedural network generation. The next problem is to build a river module that provides its connections and descent by construction; a stacking of octaves alone does not guarantee them.

**Perimeter:** a basin on a sphere, a river, a tributary, a high spring and a coast. Sea level is zero. The rendering is sober, with a solid water color.

**One construction:**
- The course and its descending profile constitute the backbone of the relief.
- A smooth cross-section gives the bottom, banks and slopes.
- The relief of the massifs and its details grow from the banks; their amplitude is zero there.
- The same function makes bed height, water level and distance to the course, in fixed coordinates on the planet.
- The two branches share their level at the confluence.

**Order of first test:**
1. mesh fixed and simple geometry; check the bed, confluence and arrival at the coast.
2. Approaches at several heights on these three sites; measure the ground deviation at the same coordinates.
3. mesh sliding, camera still, same geometry; measure the flicker and compare to the fixed mesh.

**Stop criterion:** if fixed version fails, review the relief function. If only the sliding version fails, process the sampling of the mesh before complexifying the rivers.

**Cost included:** a small analytical model and a single viewer. The global hydrological graph, climatic sources, deltas, vegetation and detailed textures remain outside this first attempt. The complexplanet relief will be reintroduced to large scales after this verification.

**To test:** Open `tools/river-first/index.html` in a browser, or launch `tools/lance-rivieres-simples.ps1`. No download, server or compilation required.
- Choose Confluence, Riverbank, High Source or Coast; the entire basin is a comprehensive view.
- The descent button approaches the bank up to 3 m, with the same grid cell throughout the approach.
- Compare Fixed and Simulated slide with still camera. The slide shifts the grid of a grid cell; the camera and the relief field remain independent.
- Deselect Water to see the bottom. Slide to look, wheel for height, ZQSD or arrows for moving, R/F to go up and down.

**Model:** two analytical curves, a common profile of 20 m/km, a bed of 3 m, channels of 130 to 240 m, slopes on 1,4 km. A bounded noise modulates the amplitude of the slopes; it does not change the water level. The projection on the sphere is calculated without subtraction of two large floats.

**Code:** `tools/river-first/model.js` carries the field CPU and its translation GLSL; the benchmark checks their concordance. `viewer.js` does not filter or regenerate this field with distance. A grid of 512² cells remains at constant resolution; changing grid cell is an explicit action.

**benchmark:** `node tools/banc_rivieres_simples.cjs x64/RiverFirst`; `--cpu-only` is sufficient for invariants and geometric errors. Captures require Playwright and pngjs, available in the work runtime; the viewer does not depend on them.
- 39 000 course probes: no cut or rise; center depth of 3 m.
- Concordance CPU/GPU: maximum measured deviation of 1,26 mm on 256 points.
- grid cell 16 m, displayed area: maximum geometric error of 8,29 cm on the probes and phases of the benchmark; at 8 m, 4,09 cm. The bottom alone is more sensitive: maximum 23,93 cm to 16 m, 6,42 cm to 8 m.
- Source, confluence and hill: automatic descent up to 3 m, without moving the anchor of the mesh.
- Nine still views at 3, 120 and 1 200 m: zero image deviation in fixed mesh. Eight slip phases: maximum mean deviation 0,125/255, at the edge of the ridge at 3 m; up to 1,11 % of pixels exceed 3/255 in the measured central area. The flicker is therefore not declared null.
- Report and captures: `x64/RiverFirst/rapport.json` and `x64/RiverFirst/*.png`. Rendered without window or focus.

**Limits:** finished analytical basin, without hydrological simulation or material realism. The fixed mesh is not a replacement for the planetary motor mesh. The coarse grid cells of 64 and 128 m are used to observe sampling; their approach to the ground is not validated. The benchmark quality of MyPlanetEngine is not applicable to this separate rendering; previous engine measurements are not replaced.

**git status:** no commit or push; tag of experiment to put on a requested commit. The mutations reported in Dendry are not declared corrected by this viewer.


### 2026-10-26 · Independent CP relief, before integrated basins

**Previous viewer state:**

**reference frames git:** tag `piste/rivieres-spikes`; start tag `jalon/avant-spikes-rivieres` on `b0252c9`, Dendry state of 25 October before these spikes. Experimental changes remain uncommitted.

**Status: variant with relief inspired by complexplanet to be judged by the user. No benchmark launched, at his request. Code entrusted to GPT-6.1 Terra xhigh; architecture and judgment retained by the main agent.**

**To try:** `tools/lance-rivieres-simples.ps1`, or `tools/river-first/index.html` in the browser. Reload the tab to replace the old two-curve model.
- Seed then Apply, or +1: same parameters and same generator for all seeds, 32 bits signed integer.
- Octaves from 1 to 4: depth of fractal branches.
- CP relief / Simple relief: comparison to the same coordinates, angle and height above the ground. CP mode is active by default; no cropping on mode change.
- Places generated from the seed: branches, bank of a trunk, source, coast, whole network.
- Water allows to see the bed; Fixe/Glissement and the descent remain available.

**Construction:** a module of dyadic branches produces a field of distance to courses. The daughter cells converge continuously to their parent cell downwards. The seed hash places the axes at each scale; a four-octave gradient noise distorts their positions. No paths are stored or adjusted for a particular seed.

**Relief:** the common profile decreases towards the coast; the slopes start from the river field. The single mode keeps the previous gradient 2D noise. The CP mode adapts the mountains group hautes/basses and hills of `ComplexPlanet.hlsli`: RidgedMulti, Billow, Turbulence, blend and exponentiation, then soft selection of massifs.
- The frequencies of the sphere are divided by 6 378 and the turbulence powers multiplied by 6 378 to work in kilometers.
- Source gaps: 2,142578125 for mountains, 2,162109375 for hills.
- Fixed spike points: low mountains 8 → 3 octaves, hills 6 → 3, turbulence → 2. They do not vary with the camera or the grid cell.
- The positive relief in km is assembled by `0,25 + 1,5 × collines + 2,5 × montagnes × sélection de massif`, then multiplied by the transverse envelope which is zero at the banks. The water profile, incision and river network remain those of the seeded variant.
- The adaptation reuses the noise of the local 2D gradient; it is not a port 3D bit by bit of complexplanet. No trace, patch by seed, solver or correction pass is added.

**Display:** the relief graph is evaluated at the vertex. The interpolated normals are from the central height and two neighbors on the sphere, three evaluations per vertex. The fragment only re-evaluates the river distance and uses the interpolated height for color. This compromise keeps the relief to judge without making each triangle flat.

**Voluntary limit:** this first construction remains oriented according to a common downstream direction, with repeated basins. It explores a generic fractal module; it does not yet demonstrate a drainage adapted to arbitrary continents of complexplanet. The seed is not yet connected to the C++ engine.

**Control:** start and preview simple/CP on the seed 13, 4 octaves; ridges and valleys clearly visible on the same area. The judgment in motion remains that of the user. No benchmark or multi-seeds measurement; old analytical results do not validate this variant. No commit or push.


### 2026-10-26 · First framework of integrated pools

- **Test:** seed 14, four octaves; first preview too smooth and parallel, fine relief crushed by the quadratic factor of the gap between channels.
- **Replaced setting:** `smoothstep(0, largeurBassin × 0,35, écart)`; replaced by `écart/(écart+1,5 km)` with amplified CP modulation.
- **Framing:** view enlarged to a grid cell of 64 m and moved to the last fork; altitude 8 km and inclination 60°.
- **Second preview:** ridges and valleys readable; layout still very parallel. No benchmark launched.


### 2026-10-26 · Integrated multi-level basin, replaced by the fixed basin

**Variant basins-integres-2, previous state:**

**reference frames git:** tag `piste/rivieres-spikes`; starting tag `jalon/avant-spikes-rivieres` on `b0252c9`. No commit or push of experiments.

**Status:** spike `bassins-integres-2`, to be judged by the user. Code entrusted to GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No benchmark launched, at the user’s request.

**To try:** reload `tools/river-first/index.html`, or launch `tools/lance-rivieres-simples.ps1`.
- Integrated Basins is the default mode; Slope/Torrents frames the high branches and their connections.
- Independent CP and Simple Relief remain accessible at the same coordinates and at the same height above ground.
- Seed / +1 change the entire deterministic field; Octaves adjust its depth from 1 to 4.
- Source, Branches, Trunk bank, Coast and Whole network give other frames.
- Water shows or masks the surface; Fixed / Slide and descending to the bank remain available.

**Composition:** potential rough → basins, profiles and ridges → details of slopes.
- A gradient potential at 50 km, separated into x/y, influences the placement of nodes towards the low potentials and their altitude increments. Here it represents the gross input; it is not yet the field of the continents and chains of the engine.
- The dyadic branches remain implicit, distorted by the common noise; no routed graph or plot stored.
- The altitude of a node adds up the positive increments of its ancestors: `0,16 + 0,34 × potentiel` km at the first level, then `0,12 + 0,43 × potentiel` km per level. The children share the elevation of their parent at the confluence.
- The water interpolates the altitudes parent/enfant; the last branch gains `0,12 + 0,25 × potentiel` km to its source. The common inclined plane belongs to the old modes.
- The initial half width of 120 to 160 m is multiplied by 0,47 at each level; it shrinks to zero on the last kilometer before the source. At four levels, the terminal torrents are about 12 to 16 m wide before this taper.
- Between two channels, their profiles interpolate gently. A peak depends on their physical difference and the gross potential: `4u(1−u) × écart/(écart+1,5 km) × (0,6+1,2 × potentiel)` km; it cancels when two branches coincide.
- RidgedMulti and Billow of complexplanet’s 2D adaptation modulate this peak by a bounded residue: three octaves, 2,142578125 and 2,162109375 lacunarities, `0,25 + 2,5 × détail²` factor. Independent complete mountains remain in comparison mode.
- The lateral structure cancels into the bed, then rises on an envelope of 80 m; central incision of 3 m. The rise after the sources interpolates the two neighbors to remain continuous.

**Display:** same CPU / GLSL field, whole hash and common seed parameters. Three terrain evaluations per vertex for interpolated normals; the fragment calculates only channels. Five local candidates, without calculation of ancestral elevations in the fragment. The grid cell remains fixed during approach. The color depends on the height above the interpolated water profile, like the shapes of the valleys.

**Boundaries:** Local spherical region, common coast and drainage oriented towards it decreasing; dyadic basin still recognizable. The gross potential is simplified and separable. This spike explores the middle module; it does not demonstrate the draining of arbitrary continents, nor the integration with the C++ seed of complexplanet. Software rendering starts slowly; no measurement of the GPU hardware.

**Control:** WebGL syntax and start on seed 14 / 4 octaves, preview of default framing. Ridges and valleys readable, organization still very parallel; judgment in motion entrusted to the user. No benchmark, no multi-seeds measure. The previous variants and their settings are in the section “Replaced tests”.


### 2026-10-27 · First connections of lateral tributaries

- **First launch:** too heavy compilation; specialized program by mode and node values stored on the GPU, without changing the functions of the field.
- **First local view:** visible and connected tributary, with ridges of abrupt appearance. Hard selection of the nearest candidate also presents a risk of rupture; it is replaced by a continuous composition of neighboring valleys, each half-slope connecting to its collector.
- **Final comparison with fixed position:** steep ridges are also present without tributaries. The new valley strongly remodels the slope; its incision remains to be judged by the user.
- **Control:** working previews, no benchmark.


### 2026-10-27 · Side tributaries slopes-1, removed after user test

**User judgment:** courses too straight, cutting mountains, appearance of leaf ribs; result less good than the basin to one octave.

**Cause of construction:** oblique curves in cells and then recomposition of a slope strip; the large ridges do not arise from these branches. Continuity of the mixture does not resolve this inconsistency of structure.

**Status of test before rejection:**

**reference frames git:** tag `piste/rivieres-spikes`; starting tag `jalon/avant-spikes-rivieres` on `b0252c9`. No commit or push of experiments; tag of this experiment waiting for a requested commit.

**Status:** spike `versants-1`, to be judged by the user. Code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No benchmark launched, at the user’s request.

**To try:** reload `tools/river-first/index.html`, or launch `tools/lance-rivieres-simples.ps1`.
- The basin remains at one level; the old multi-octave links are reduced to one level.
- Whole network is the initial view, seed 14 in the absence of seed in the link.
- Streams/torrents activates tributaries without moving the camera; deactivating retrieves the built-in reference terrain to one octave.
- Slope/torrent and Source frame a real tributary of the seed, with a central grid cell of 16 m.
- CP independent, simple relief, water and descent remain available.

**Basin preserved:** collector axes, coast and profiles of the basin integrated to an octave. Coarse gradient potential at 50 km; RidgedMulti / Billow details adapted in 2D. Additional levels no longer lengthen the basin. The old multi-level construction and its settings are in the “Replaced Tests” section.

**Tributs:** implicit lateral curves, constructed in the half-intervals between collectors.
- Longitudinal cells of 3,2 km, junctions offset by seed; longitudinal length of 2,2 to 3,3 km.
- Branch crosses up to 84 % of half-slope, with slight bending; no crossing of central partition line.
- The cells belong to the band between the first main branch and its head; they do not extend the pelvis.
- The profile is `H_collecteur(y) + A × smoothstep(0,1,v)`, with `A = (0,4+0,3 × potentiel) × écart/(écart+1,5 km)` km, constant per tributary. The climb is positive; at the confluence, `v=0` finds the collector.
- Total width of 40 m downstream, decreasing and then tapered to zero near the head; central depth of 3 m.
- The relief of the slope is composed around the same profile: valley envelope of 250 m, positive lateral relief on 120 m, CP detail bounded. This replacement may lower or raise the previous microrelief; it is not a strict incision in an arbitrary immutable terrain.
- The valley weight is worth exactly one in the channel. Bed and water surface use the same profile; no interpolation of the old relief noise in the water.
- On the bank of the collector, a split profile gradually connects the branch; the main bed is retained.
- Each half-versant belongs to its collector; the envelopes of valleys are cancelled at the dividing line. The three neighboring cells are composed by continuous weights: `poidsRéférence=Π(1−qᵢ)`, `poidsValléeᵢ=qᵢ × Πⱼ≠ᵢ(1−qⱼ)`, then normalization. A weight channel one retains exactly its profile.
- No graph stored, routing, rejection based on bumps encountered, correction pass or exception by seed.

**Viewer:** 65,536 km side range for all resolutions, 512² cells grid.
- For an index `i` between −256 and 256, `t=i/256`: `x=i × mailleCentre + signe(t) × (32,768−256 × mailleCentre) × |t|³`, in km; same law for y.
- The grid cell from 8 to 128 m adjusts the central resolution; the periphery remains coarser. The domain no longer shrinks when the grid cell is refined.
- No adaptation to the camera; geometry and mesh remain stable during zoom. The simulated slip remains an explicit control.
- The orbit uses the reference terrain target; the stream swing does not move the pose.
- The CPU and GLSL fields share the same formulas. The fragment evaluates the channels; the heights and normals remain at the vertex.
- The graphic program is specialized and memorized by mode; the basin is fixed at one level. A GPU cache of 64 nodes stores the positions and altitudes of the procedural function on the region, without routing or pre-calculated hydrological graph.

**Limits:** Collectors still parallel, simplified gross potential and oriented regional drainage; a single scale of tributaries, without a complete branched subnet. The fine relief is remodelled around the branches and the valleys can be very incised; this aspect remains to be judged. The periphery and the overview do not resolve small beds with the same precision as the center of local views. No integration with the C++ engine or draining of arbitrary continents from complexplanet.

**Control:** JavaScript syntax, WebGL compilation, overview and local comparison with/without fixed camera tributaries on seed 14. The tributary appears in the slope; the steep ridges are also present in the reference. No benchmark or multi-seeds measure. The judgment in motion remains that of the user.


### 2026-10-27 · Return to reference before common module

**State before basins-communs-1:**

**reference frames git:** tag `piste/rivieres-spikes`; starting tag `jalon/avant-spikes-rivieres` on `b0252c9`. No commit or push of experiments.

**Status:** return to the reference basin by one octave. The `versants-1` side tributaries are discarded after user judgment; their code remains available by a default unchecked box. Parameters and details of the test in the section “Replaced tests”.

**To try:** reload `tools/river-first/index.html`, or launch `tools/lance-rivieres-simples.ps1`. Script cache: `reference-bassin-1`.
- Whole network is the initial view; one-level pool, seed 14 if no seed in the link.
- Trial of tributaries is unchecked. Activating it allows you to review the rejected test without changing the pose.
- Independent/single CP, Water and local views modes remain available.

**Base retained:** integrated octave basin collectors, coast and profiles. Coarse gradient potential at 50 km and RidgedMulti/Billow details adapted in 2D. The main courses remain oriented and parallel; this visual base does not yet validate the drainage of an entire planet.

**Viewer retained:** fixed range of 65,536 km side; grid of 512² cells with adjustable central resolution from 8 to 128 m. The cubic projection concentrates the vertices in the center without shrinking the region. The orbit uses the reference target; zoom does not regenerate the terrain or the mesh. Specialized programs by mode and cache GPU of the values of 64 nodes, without routing or pre-calculated hydrological graph.

**Architectural decision:** the intermediate module must build the valleys and the partition lines of a same basin organization, then accommodate the CP detail on the slopes. In the rejected test, the oblique lines were defined separately from the large ridges and the relief was reworked only in their vicinity. This construction does not meet the architecture targeted.

**Check:** Startup errors fixed, JavaScript syntax checked; no benchmark or new rendering for this return to reference, according to the requested iteration rate. No new drainage trials are presented as validated.


### 2026-10-27 · First subdivision of the common module

- **First construction:** sharing points on the top edge, 40 triangles per root. Preview too fanned and sources aligned near the upstream limit.
- **Replacement:** inner split vertex and linear peak triangle, 47 triangles; second strain band common to 3,7 km.
- **Display:** Framing taken from 48 km / 88° to 30 km / 65°; palette replaced by continuous altitude, the nearest course profile producing discontinuous color ranges out of water.
- **Final work judgement:** common structure visible before CP, but still geometrical appearance. No benchmark; previews only.


### 2026-10-27 · Triangular basins, visually inconclusive

**Decision:** the rendering remains a geometric scheme not readable; the common property of the generator is not enough to produce a natural landscape. Test set aside; the one-octave cymbal is kept for Phasor.

**State of basins-common-1 before set-aside:**

**reference frames git:** tag `piste/rivieres-spikes`; starting tag `jalon/avant-spikes-rivieres` on `b0252c9`. No commit or push; tag of the new attempt waiting for a requested commit.

**Status:** spike `bassins-communs-1`, to be judged. Code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No benchmark at the user’s request.

**To try:** reload `tools/river-first/index.html`, or launch `tools/lance-rivieres-simples.ps1`.
- Common pools is the initial mode, seed 14 in the absence of seed in the link.
- CP detail disabled shows the complete structure of the new module: valleys, tributaries, slopes and ridges.
- Reference · 1 octave retains the exact comparison ground, without the side test dismissed. Changing mode or detail does not crop.
- Whole network frames the basin; Slope/Torrents, Branches and Source use sections from the new module.
- The fixed range of 65,536 km, the adjustable central grid cell, Water and explicit slip remain available.

**Module:** hierarchical subdivision of triangular pelvic cells, deterministic from seed. It is a structured module, distinct from a simple sum of noise functions fBm. It does not run course in a already formed terrain and does not simulate erosion.
- One cell carries a low outlet O and two high bounds L/R. The subdivision produces a J junction, the course O–J and its two sides.
- An internal splitting vertex M creates the two subbasins J/L/M and J/M/R, as well as the ridge triangle M/L/R.. The shape of the valleys and their separation are derived from the same cut.
- Junctions rise from 25 to 40 % of the difference between the outlet and the lowest boundary; bound sources rise from 65 to 80 %. The section profiles interpolate the same altitudes.
- The flanks use the basin barycentric coordinates: `H=W+c^1,4 × (hC−W)`, with W the bottom profile. Terminal caps use a rise of the same exponent. The inner crest triangles linearly interpolate their three heights to connect the high edges of the subbasins.
- Three fixed levels give 47 structure triangles and 15 sections per root cell. Lateral caps complete its rectangle; the borders between root cells share the same height.
- High bounds are worth `1,8+1,2 × potentiel` km. Vertex M is placed inside J/L/R, at 18–40 % of the path from the upper edge to J; its rise is 90–115 % of that of the corresponding edge.
- A common deformation at 12 km and 3,7 km curves the entire field; displacement limited at 600 m, zero at the coast. Valleys and ridges undergo the same transformation.
- Initial width of 200 m, divided by two per level up to 25 m at the leaves; terminal taper and depth of 3 m. The weight of the bed is worth one in the channel; the water profile does not borrow the detail noise.

**CP detail after structure:** RidgedMulti / Billow adapted in 2D, three octaves, modulation limited to 10 % of the available height above the local profile. The barycentric bubble cancels on the edges; courses and shares remain those of the structural module. This mode does not add the full group of independent mountains of complexplanet.

**Rendering:** cell values stored in a texture RGBA32F, 62 lines per root, without external hydrological calculation. CPU and GLSL use the same controls and formulas. Specialized programs by mode; earth color based on altitude continues, without extending the height of the nearest course across the entire slope. The orbit uses a common reference to both terrains.

**Boundaries:** still geometrical shapes and relief of little detail; repetition of root basins and flat extension beyond their upper limit. The construction remains regional, without arbitrary continents or connection to the C++ engine. A preview does not demonstrate stability at any distance or all seeds. Visual improvement is not declared as acquired.

**Control:** WebGL syntax, start and compilation; overviews and local structure on seed 14, then resuming the inner vertex and framing. No benchmark, no multi-seeds measure. The user remains the controller of the rendering.


### 2026-10-27 · First global free arc organization · replaced

**Status:** rough world prototype in `tools/global-basins/`, off engine. It replaces the coastal window with a sphere-wide construction; the regional native rendering of the 11 section remains a separate reference. It is not yet a global hydrology or a production module.

**To try:** `tools/lance-bassins-globaux.ps1`, or http://127.0.0.1:8766/global-basins/. Switch CP Current / CP + Basins keeps the camera, light, mesh and amplification. The network is a structural diagnosis, not a surface of water. The local one-octave basin and coastal test remain accessible separately.

**CP entry:**
- `prepare_cp.py` evaluates ComplexPlanet's NumPy port on 32 514 directions and 65 024 triangles; shared poles and closed longitude seam. Radius 6 378 km, common seed 0.
- The full elevation filtered to 30 km provides the control heights and the terre/mer sign; the mountain weight CP modulates the source selection. The grid cell equatorial geometry is about 157 km, distinct from the filter width.
- 4 154 Coastal zeros come from sign-changing edges, refined by bisects of the same CP field. Small islands or sign changes that are missing from the grid remain absent.
- Continental fields and elevation filtered at 10 km are exported for the following steps; they do not yet become a new detail strip of the model. The control height includes the native noise fluvial CP: the CP bands are not yet all separated.

**Structured construction:**
- The connection of the earth-to-earth ridges defines the terrestrial components, without flowing over altitudes. Each component retains at least one outlet; a common hash order selects coastal sites spaced at least 600 km.
- Each terrestrial point belongs to the site closest to its component, according to the spherical distance. This partition does not connect a small island to another continent.
- Seeded sources occupy 4 to 6 % of the summits according to mountain weight CP; a cell without source retains its highest point. Each source keeps exactly the direction and altitude of its CP control.
- Binary subdivisions in tangent coordinates construct the junctions. Children inherit the parent's position and height; linear profiles descend to their 0 level root.
- The current set contains 208 sites, 781 sources and 1 354 sections. These are global parameters generated independent of the camera; no local window is grafted to the planet.

**Common field:**
- All river profiles and coastal arcs of height 0 contribute to the `W` field by Shepard interpolation, weight `1/d⁴`. No neighborhood threshold chooses different branches depending on the camera.
- With `D` the distance to the network, `H = W + max(H_CP−W,0) × smooth(D/120 km)`. Lateral relief is cancelled on isolated axes; CP controls reliefs between the backgrounds. The width is that of this rough world structure, not that of a realistic channel.
- The viewer subdivide each triangle into four with shared edge vertices: 130 050 vertices, 260 096 triangles. New CP heights are interpolated; the same module evaluates new basin heights.
- On each coastal ridge, the new summit is the refined CP zero rather than the middle; the estuaries and the visible coast thus share the level point 0. Both modes use the same control geometry.
- Normals come from the surface displayed. The visual amplification, initially ×20, applies identical to both modes and does not change the model altitudes.

**Limits to be addressed:**
- The cells are geometric; they do not yet follow the division lines of the large massifs. An arc can cross a concave bay or cross a branch of another level. Legacy junctions guarantee their own connection, not the compatibility of all spatial crossings.
- `W > H_CP` can raise a low ground; the exact preservation of the masses is not guaranteed. The large chains must remain recognizable in the comparison, without presenting this as a global evidence.
- The grid cell can mask the axes and does not sample their edges. There is no bed, no water surface, no detail of reconnected slope in this viewer.
- The profiles constructed descend; no evidence is available for all drops of the slopes, all continents or all seeds. The common source is seed 0; changing the seed requires regenerating CP and pools together.
- No land drainage, bowl filling, path search or erosion simulation. The cost of evaluating all cores and the port GPU remains open.

**Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. Syntax and targeted preview before presentation; no benchmark, multi-seed scanning, commit or push. Tag of experiment waiting for a requested commit.

**Preview:** globe and main basin compared at identical pose, network disabled and displayed; no JavaScript errors on loading. The large chains remain recognisable and the new valleys are visible; the branches remain very direct and some are masked by the grid cell. The inspection lighting follows the camera in both modes. Captures of work `x64/GlobalBasins/*-lit.png`. This finding does not validate crossings or a channel in water.

### 2026-10-27 · port global native on rough controls · rejected

**User report:** CP relief erased, geometry degraded and courses too straight. The connections of the sheets did not validate the morphology.

**Goal:** to judge the global network with the native terrain, its materials, atmosphere and flight controls, from orbit to shore. This mode takes the cellular module from the 12 section and the channel from the 13 section; the old regional native modes remain distinct.

**Data:**
- `tools/export-global-basins.cjs` runs the same grid generator and exports all river and coastal segments of the sphere, CP controls and a fixed spatial index.
- Seed 0 only: 74 412 river segments, 4 154 coastal segments, 130 050 CP control summits; buffer of approximately 46 MB. No final raster of river relief or replacement window.
- The V3 format, `−271028` marker, is described in `tools/global-basins/README-format-natif.md`. The engine validates dimensions, sections and indices before loading.
- The directions are separated into main float and residual float. Planetary differences are taken in double precision precision before converting small shifts to floats; the field is not dependent on the camera.

**Land:**
- `GlobalBasin.hlsli` retrieves the CP control triangles and evaluates the same arcs, profiles, compact supports and channel operators on the sphere. `Terrain.hlsli` calls it before the old regional roads.
- The CP control is that of the coarse globe. The new mode is not the original full CP elevation unchanged: its intermediate structure is that of the shared module.
- A first strip of `MountainousHigh` CP under 1 km enriches the relief. Its difference fin/grossier is mountain weighted, limited to 10 % of lateral relief and zero in the channel and coast.
- The Planetary Map and the Ground Passes use the same global relief; the other modes keep their previous path.
- In this mode, the regional map retains the soil for fog and materials, with canals of lakes and drained area at zero. The historical drainage of the map is not executed; it does not provide the network or water levels of the new module.

**Water:**
- The terrain calculation keeps the raw bottom and adds to each vertex the water level, the distance signed to the channel and the CP control height.
- The water passage takes the same clues and directions of the native mesh. One instance carries the sea level 0; the other carries the river profile. Interpolated masks separate sea, channel and land.
- The water position comes from the already calculated level, without raising to bypass the ground. It masks the water passage and preserves the bottom and the camera.
- The contours are approximated by the interpolants of the native mesh. This first port does not cut every triangle at the banks like the local viewer; the quality of contact and approach remains to be judged.
- Objects and plants are excluded from the overall water mask; objects reuse their soil assessment, plants question only river arcs for the mask.

**Path:** `tools/lance-global-basins-planete.ps1`, executable isolated in `x64/GlobalBasinsNative/bin/`, palette `tools/tests/2026-10-27-global-basins.txt`. F1 orbit, F2 full basin, F3 high source, F4 confluence, F5 collector, F6 mouth, F7 bank, F8 relief of the basin. The basin is chosen by its branches and altitude; the high spring is towards 3 652 m. Sun, caps and positions are derived from the grid. The bank is viewed at 100 m above ground, with an angle to the collector; the last view shows high control at about 100 km from the nearest course. `-SansPlantes` and `-SansEau` are available; the environment is restored by the launcher.

**Scope:** global function for prepared seed, with an inspection path in a full basin. This is not a valid hydrology for all seeds. CP geography remains rough, channel maintains uniform width of 600 m and nominal depth of 8 m; flow, deltas, full slope detail and transition quality of mesh remain open.

**Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. Compilation and native preview required before presentation; no benchmark or seed scanning. No commit or push; tag waiting for a requested commit.

**Native preview:** Successful isolated Release compilation; captures cover orbit, source, high relief, confluence, mouth, bank and waterless confluence. The confluence and mouth views show the connection of the water table; masking the water preserves the excavated terrain. The source keeps a wide heading and the relief remains too smooth; the materials and the atmosphere of the engine are not enough to validate the morphology. Captures indicate a GPU sensitive cost and variable cadences; no dedicated measurement or motion stability is validated. The first boot took several minutes in some launches. Images `x64/GlobalBasinsNative/native-*.png`; user flight controller.

### 2026-10-27 · Complete CP integration with rough profile · replaced by V4

**Status:** recapture of the port after rejection of the smooth relief. The first version and its insufficient control are in [history](#tests-replaced).

**Membership:**
- `Terrain.hlsli` evaluates `ComplexPlanetElevation` complete at current frequency and retains its roughness.
- The worldwide network of the section 12 provides the W profile, channel distance and its nominal depth of 8 m.
- The field becomes `lerp(CP, W - profondeur, integration * masque)`.
- The mask is 1 in the channel and decreases continuously to 0 on 3 km from the shore, against 120 km before.
- Beyond this range, each height is exactly that of the full CP graph; no intermediate mountain band is removed.
- The coarse CP controls are still used for the network structure and W profile, never to replace the off-valley soil.
- The regional map still evaluates original CP; it remains stable during comparison and does not start historical drain in this mode.

**Avant/après :**
- B basculates original CP / CP + valleys; same pose, same sun, same image size and same settings.
- The GPU is synchronized before the weight change in the buffer; the time history is invalidated.
- The ground lock remains suspended after B until the next move to avoid changing the framing.
- `-Reference` and `MYPLANETENGINE_GLOBAL_REFERENCE=1` start as CP reference.
- In it he masks the water without changing the bed; the rivers are masked as reference, the sea remains present.
- Fine normals, terrain and placements use the same state; the sea reference comes from the full CP.

**Data and flight:**
- V3 format, seed 0, global network and index unchanged; 74 412 river arcs, 4 154 coastal, approx. 46 MB.
- The 29 field carries the transition of 3 km; the 45 field carries the integration weight, 0 or 1 for comparison.
- `tools/lance-global-basins-planete.ps1`, isolated executable `x64/GlobalBasinsNative/bin/`, palette `tools/tests/2026-10-27-global-basins.txt`.
- F1 orbit, F2 complete basin, F3 source, F4 confluence, F5 collector, F6 mouth, F7 valley inspection, F8 relief.
- Close-up frames are raised to compare full CP; altitudes are absolute and identical between modes.
- The launcher reuses the export if it is up to date; it restores its environment variables.

**Limits:**
- The profile of the coarse network can exceed CP: the composition can then raise the soil in its influence.
- This spike does not yet resolve the artificial branch drawing, uniform width of 600 m, flows or deltas.
- The exact CP coast may differ from the one used to build the network; the water-to-sea connection must be inspected.
- Water contours remain interpolated on the native grid cell; movement and transitions of grid cell remain open.
- This local composition preserves CP but does not yet demonstrate a common construction of the ridges and the network adapted to all seeds.

**Verification:** Isolated Release compilation successful; native source, confluence and relief pairs at the same frame and lighting inspected in `x64/GlobalBasinsNative/cp2-*-avant.png` and `cp2-*-apres.png`. The relief view preserves the CP mountains. The confluence remains a too uniform and straight line; at the source, the W level raises the CP ground. Visual control confirms the conservation of the terrain outside influence, but still rejects the morphology of the network as complete integration. B key was activated in the engine; no benchmark or seed scan, no full validation in motion. The cost of global queries remains high.

**Work:** code GPT-6.1 Terra xhigh; architecture, orchestration and judgement by the main agent. No commit or push; tag waiting for a requested commit.

## The journal of spikes

### 2026-10-27 · CP profiles and morphology V4

- **Rule:** an incision never raises CP; common profile bounded by the axis and bank probes in CP32/256, margin 8 m, descending envelope and upstream factor `d/(d+20 km)`.
- **Coast:** first interpolated marine contact from each source; removal of marine sections and sources that CP ends at sea, no alternative routing.
- **Curve:** Step gradient noise functions 12 and 3,5 km, weight 1 and 0,45; displacement limited by areas and 2 200 m; fade of 1,2 km at junctions.
- **Width:** half width 4 m at the source then base 24√(sources), consistent fluctuation of step 9 km and coefficient 0,3; flare ×2,2 on the last 25 km. No delta arm added.
- **Data:** V4, 1 456 417 river segments, 196 new contacts, 268 MB; seeded phases and adaptive subdivision according to max(10 m, 25 % of half width), target not 125 m to 1 km; hash 20 km and support 12 km, sections aligned on 64 floats.
- **Reference:** old executable and data retained in `x64/GlobalBasinsAvantMorpho`; new mode in `x64/GlobalBasinsMorpho`, same pose and fineness 0,25 in the captures compared.
- **Verification:** Release successful; source, confluence and mouthpiece compared to the same frame, sun and fineness. Cape source removed and marine contact restored; variable widths, branches organization still geometric. No branched delta or general validation of movement; sensible cost. Captures `x64/GlobalBasinsMorpho/*-{avant,apres}.png`. No benchmark or seed scanning.
- **milestone:** `jalon/rivieres-cp-resultat-prometteur`, backup requested by the user on 27 October 2026 on the branch of the tag `piste/rivieres-spikes`. This reference frame retains the sources and tools of the spikes; executables, caches and captures under `x64/` remain local.
- **Work:** code GPT-6.1 Terra xhigh, architecture and judgment by the main agent. Promising result, without general validation of hydrology or performance.

### 2026-10-27 · Complete CP and comparison

- **Previous rejection:** erased relief and artificial courses; the only connections of layers were not sufficient to accept the port.
- **Terrain:** return to the full CP graph and its roughness; channel influence limited to 3 km from the shore, CP exact beyond.
- **Compare:** B switches original CP / CP + valleys without moving the camera or the sun; time history reset. It keeps the bed masking the water.
- **Map:** CP reference stable in both states, no historical drain added to mode.
- **Assumed limit:** W remains from the rough network and can locally survey the ground; traces, hill and detail of the network remain to be inspected.
- **Flight:** same palette F1 to F8, close frames raised; option `-Reference` and export reused when it is up to date.
- **Verification:** Isolated release successful; three pairs of native views in the same frame inspected. CP relief preserved, but source locally surveyed and confluence too straight; river morphology not validated. Captures `x64/GlobalBasinsNative/cp2-*-avant.png` and `cp2-*-apres.png`. B driven in the engine; no benchmark or seed sweep. Overall cost still high.
- **Work:** code GPT-6.1 Terra xhigh, architecture and judgement by main agent; no commit or push. Tag waiting for a requested commit.

### 2026-10-27 · port native to the global network

- **Mode:** `MYPLANETENGINE_GLOBAL_BASINS`, separate V3 format; all river and coastal cores, CP controls and sphere spatial index, seed 0, approximately 46 MB. No window replacement on the ground.
- **Function:** same profiles and channel 600 m / nominal depth 8 m as the prototype; analytical queries in HLSL, first band `MountainousHigh` CP under 1 km, bounded and zero at the banks.
- **Rendering:** raw terrain and water metadata in the same summits; sea and river passes from the same native indices. It masks the water without moving the bottom. The contours remain interpolated by the native grid cell.
- **Map:** Global mode does not run historical drainage; soil map for fog and materials, network and water provided by the global field.
- **Flight:** `tools/lance-global-basins-planete.ps1`, pallet F1 to F8; basin 34, 16 sources, 15 confluences, source to 3 652 m. Orbite, basin, source, confluence, collector, mouth, bank and distant relief of the course.
- **Verification:** Isolated release successful; native captures with and without water, source, relief, coastal connection and globe inspected. Source still wide, relief too smooth and cost GPU sensitive; first initializations sometimes long. Movement, LOD and overall quality remain to be judged in flight. Captures `x64/GlobalBasinsNative/native-*.png`.
- **Work:** code GPT-6.1 Terra xhigh, architecture and judgement by main agent; no benchmark, seed scan, commit or push. Tag waiting for a requested commit.

### 2026-10-27 · Back to the globe to locate the water test

- **User comment:** The local view of the waterfall breaks the context of the sphere and the flat coastal terrain makes the excavation not readable.
- **Entry:** globe centered on the site chosen by the model, reference frame and 32 km; Planet → Basin → Bed and water. The old water address redirects to this entry.
- **Detail:** explicit access, Ariane wire, planète/bassin returns and locator built from CP data. Local scope of the test is announced; no global launch claimed.
- **Preview:** old address redirected to the globe; reference frame visible, click to the basin then to the detail checked on the same basin 55. No JavaScript error. Captures `x64/GlobalWater/context-*.png`.
- **Perimeter:** guidance and framing, without modification of network, land, water level or seed. Code GPT-6.1 Terra xhigh, targeted preview, no benchmark or commit.

### 2026-10-27 · Bed and water supply of the global network

- **Goal:** translate the same global network into bed, banks and water table; no change of seed, curve or junction.
- **Profile:** `sampleChannel` takes over `W` and `D`, uniform width 600 m and nominal depth 8 m; zero lateral relief at the shore, extended bed under the sea. The reference of the globe remains accessible.
- **mesh:** windows of 32 km / not 125 m, CP controls interpolated as in the globe; common coastal and channel cut, shared bank summits and a single wet union at the confluence.
- **Reading:** `tools/global-basins/water.html`, Collector / Confluence / Mouth; Bank brings a bank closer, Water masks the layer by keeping the bed and the pose. Local metric accuracy, logarithmic graph depth and identical amplification terrain/eau.
- **Limits:** constant width, depth represented approximately by the grid cell, rough coastline and CP relief; no flows, deltas, new slope details or native port.
- **Overview:** Confluence and basin mouth 55 inspected; bed preserved without water, cut of collector triangles with approximately 8 m gap fond/eau. Approach from 180 to 100 m and rotation, even mesh preserved, no loading error. Sober rendering and depth not readable at large scale; captures `x64/GlobalWater/review-*.png`.
- **Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No benchmark, seed scan, commit or push; tag waiting for a requested commit. Details: section 13.

### 2026-10-27 · Global network in terrestrial cells

- **Replaces:** free arcs to the outlets, which could cross and cross bays. The previous method goes into the “Replaced Tests” section.
- **Structure:** convex terrestrial polygons cut at zero CP, shared ridge ports, component outlets and seeded forest; macroscopic Voronoi before the hash order. No route selection by slope or optimal distance in CP.
- **Curve:** arms in disjointed fans at confluences; a single cubic from port to port in the passage cells, without the center elbow. Controls contained in the domain and monotonous progression; ports and altitudes inherited.
- **Profiles:** outlets at 0, sources at their height CP positive, intermediate levels increasing upstream. Curvature changes the geometry, not the junction levels.
- **Field:** compact cores of 450 km, continuous retreat to CP, structure width 120 km; fixed spatial index. The field and diagnostics read the same profiles and curves.
- **Current set:** seed 0, 35 956 cells, 217 outlets, 610 sources, 74 412 small arcs. Dependence on mesh and conservation of large masses remain to be worked on.
- **Scope:** non-crossing and confinement concern the coarse coastal domain; no validation of the fine CP field or all droplets of the slopes. Viewer without water surface, always off engine.
- **Overview:** globe, basin, mouthpiece and island of 131 inspected summits; smoother curves and visible fittings, tight returns still schematic. Option Show hidden axes to read the topology without confusing it with the grid incision. Captures `x64/GlobalBasins/cell-review-*.png`; no loading error.
- **Work:** code GPT-6.1 Terra xhigh, architecture and judgement by main agent; syntax and targeted previews, no benchmark, multi-seed scanning, commit and push. Tag waiting for a requested commit.

### 2026-10-27 · Basins on the whole CP sphere · first prototype

- **Goal:** judge the global organization before a new native port; keep CP controls and remove grafted coast window.
- **Source:** common seed 0, sphere of 32 514 directions; full CP height filtered to 30 km, mountain weight and 4 154 coastal zeros. Details under the grid are not reconstructed.
- **Organization:** Geometric terrestrial components, coastal sites spaced 600 km in each component, spherical cells and seeded trees; 208 sites, 781 sources, 1 354 sections. No routing on slopes.
- **Relief:** descending profiles inherited, common interpolation `1/d⁴` with coastal supports of level 0, lateral relief guided by CP on 120 km. The axes remain schematic; a crossed bay or branches that cross are not yet resolved.
- **Comparison:** `tools/lance-bassins-globaux.ps1`, current CP / CP + identical installation basin, light, amplifier and grid. Global subdivision into four, 130 050 vertices; coastal zeros inserted as shared vertices.
- **Scope:** global structure visualizer, without water surface, without global engine integration or hydrological validation. Only one seed prepared; neither all slopes nor crosses are demonstrated.
- **Work:** code GPT-6.1 Terra xhigh; architecture and preview targeted by the main agent. No benchmark, seed scan, commit or push; tag waiting for a requested commit. Details: section 12.

### 2026-10-27 · Three adjacent basins on a coast CP

- **Goal:** move from an isolated basin to three neighbouring systems, with their common ridges and coastal outlets from CP.
- **Coast:** zero of the full CP elevation filtered at 500 m; deterministic search of a coastal graph on the sphere, without drainage. 256 points on 75 km, common seed 0; reference frame near 2,868° N / 78,750° E. Without valid section, explicit failure, no invented hill.
- **Common field:** `v=y−C(x)`, injection latent domain conserving `v`, minimum of distances of the three shafts, shared profile `W(v)`. 57 sections in the current set; subdivisions and seeded lengths, inherited fittings.
- **Coast and slopes:** envelope `1−exp(−(v/5000)²)` for a progressive rise; bed of 4,5 m. Two CP 192² controls from MountainBase and the difference from Mountainous at two filters; modulation positive of the lateral relief, zero at the banks.
- **To judge:** `tools/lance-bassins-cotiers.ps1`, views Set / Common Ridge / Mouth, water and relief CP activated. The preparation and the model share the same seed; old spikes remain accessible.
- **Preview:** same pose with/without Relief CP, seed 0; three networks join the sea, continuous ridges between basins. Richer relief, still schematic, traces of sampling visible. Only one rib and seed inspected.
- **Native V2:** Separate format with coast, cells and CP controls; window of 100 km and upstream limit derived from the highest source plus 8 km, all courses in core unmixed. `tools/lance-bassins-planete.ps1`, palette calculated from the coastal reference frame and branches; seed 0 only, other seeds explicitly rejected.
- **Compilation:** a normal CP calculation and a filtered CP calculation factored into the histories paths, after too long compilation; no change of their formulas. Release successful with known Materials warnings. Native set inspected: legible irregular coast and relief, fine courses at 40 km; no benchmark or judgment in motion.
- **Native mouth:** position from the wide calculated from the same outlet; connection rivière/mer visible at the same level, banks still angled and uniform water. Captures `x64/BassinsCotiers/native-ensemble.png` and `native-embouchure.png`.
- **Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No benchmark, multi-seed scan, commit or push; tag waiting for a requested commit.

### 2026-10-27 · First native rendering of the basin core

- **Mode:** `MYPLANETENGINE_BASSIN` loads a separate analytical format before the old Dendry; HLSL cores at fixed coordinates of the planet, without height map or mips of the basin.
- **Structure:** Same JS model, 13 seed, varied structure and high sources; 21 cells and 12 060 ribbon tops. Complex Planet own seed kept at 0.
- **CP detail:** difference fin/grossier under about 1 km, limited to ±10 % of lateral relief and zero at the banks. Water level independent of the detail bumps.
- **Rendering:** materials, lighting and engine atmosphere; water cut by the field signed. First confluence inspected, continues to this view; water still uniform and steep banks.
- **Together:** too straight coast, sea in strip and network not readable at 20 km altitude; regional fusion still unsatisfactory. Captures kept under `x64/BasinNoise/planete-*.png`, without claim to validation of the global rendering.
- **Startup:** Release initialization first time is long and heavily memory consuming when preparing shaders; no performance benchmark. Number of preview images configurable by `MYPLANETENGINE_CAPTURE_FRAMES`, default retained at 200.
- **Region:** window of 64 km centred on 34° N / 40° W; centre corresponding to `y=9 km` of the basin, radius 6 378 km. Transition border of 8 km to CP outside judged area; local test, not a planetary basin organization.
- **To judge:** `tools/lance-bassin-planete.ps1`, opening on the general view; palette `tools/tests/2026-10-27-bassin-noise.txt`, F1 to F5. Analytical export to temporary directory; launch parameters restored.
- **Control:** Release x64 compilation successful; snapshots without window, no benchmark, multi-seed scanning or motion validation. Code GPT-6.1 Terra xhigh, judged by the main agent; no commit or push, tag waiting for a requested commit.

### 2026-10-27 · Branches and peaks less repetitive

- **Request:** Varie the basin structure, keep the high sources, the descent and the connections; then continue the rendering in the Complex Planet engine.
- **Subdivisions:** end by hash at levels 2 to 4, at most 31 cores; continue 0,74 at level 2 then 0,52 at level 3; shares of 24 to 76 %, phased out confluences.
- **Common field:** `u=x+650 N(seed+4099,x/9000+17,31,y/4200−7,1)` m; `du/dx>0,54`, `y` retained. Valleys, ridges and banks undergo the same transformation.
- **Lateral relief:** positive modulation `1+0,22 N(seed+239,x/5200+3,8,y/6000−2,4)`; zero at the banks by multiplication. No independent relief superimposed on the courses.
- **Comparison:** Varied structure enabled at start; deactivation returns the previous tree, without cropping. The actual number of sections and sources is displayed.
- **Preview:** Set and Fixed-Position Sources, detail disabled, seed 13: 21 strands and 11 sources. More asymmetrical distribution; profiles still schematic, natural complete not acquired.
- **Work:** code GPT-6.1 Terra xhigh; judgement by the principal agent. No benchmark, multi-seed scan, commit or push; tag waiting for a requested commit.

### 2026-10-27 · Sources of varying heights in the same basin

- **User feedback:** Encouraging structure, repetitive patterns; make some streams rise higher in the mountains. Repetition also comes from the binary core and single-frequency detail, not just from the viewer.
- **Scope:** modify only the eight terminal cells, by dedicated hash; end `max(yDépart+800,18 000 × (0,72+0,38 h²))` m. Parent cells and bifurcations remain identical.
- **Profile:** `W=1 250 t+2 200 max(t−0,45,0)²` m, `t=y/18 000`; positive derivation, common water and land, downstream to 8,1 km identical. This variant also changes the upstream relief; it does not raise water on an old land.
- **Comparison:** High Sources checkbox initially enabled; disabled, old module exact. The pose is kept at the swing. Added Sources view to see heads above nearby ridges.
- **Optional detail:** 550 / 290 / 150 m, gradient fields turned, weight 0,6 / 0,3 / 0,1; reference to 550 m retained. Detail disabled at the start.
- **Overview:** set and fixed seed-mounted sources 13; three heads to 2 060 to 2 284 m, five to 1 159 to 1 355 m in profile. Downhill and connections preserved by construction; synthetic sources and repetitions of the core still present.
- **Work:** code GPT-6.1 Terra xhigh, visual control by the main agent. No benchmark, multi-seed scan, commit or push; tag waiting for a requested commit.

### 2026-10-27 · Coherent and downstream basin core · local spike

- **Goal:** create valleys, ridges and courses connected from the same module, before the Complex Planet detail.
- **Module:** seeded cells divided over three generations, 15 finite nuclei; each parent transmits position and width to two children at its bifurcation. No routing or drainage of a previous relief.
- **Descent:** upstream coordinate `y` preserved by curves; linear profile `W=1 250 y / 18 000` m, sea at zero. The evidence is about the axes and their connections, not about all the slopes or the planet.
- **Relief:** common distance per section and heading; non-saturating lateral climb `1,3 × (hypot(max(D,0),80)−80)^0,9`. Shared banks, bed of 4,5 m; gradient detail at 550 m optional, disabled initially.
- **Visualizer:** `tools/basin-noise/`, km range 22 × 23,5, fixed grid 448², water activated. A macro basin; the three internal generations are not three octaves of the reference basin. Phasor remains accessible separately.
- **Preliminary judgement:** set, confluence water/bed, detail and slope inspected on seed 13. Connections and common peaks readable; rendering still schematic, synthetic sources, no delta treated.
- **Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No benchmark, multi-seed scan, commit or push; tag waiting for a requested commit.

### 2026-10-27 · Phasor basin collectors in water

- **User decision:** keep only the water collectors for now; no local drainage calculated for the ravines.
- **Profile:** `referenceSample.water`, independent of detail Phasor; incised reference bed of 3 m.
- **Rives:** cut triangles at distance signed zero; common vertices eau/terre in profile. The same triangulation serves with and without water.
- **Rendering:** blue opaque sheet, normal profile; with water, the channel terrain is not drawn over. Without water, the bed becomes visible again. Authors' source unchanged.
- **Calculation:** Cached bank geometry when changing bassin/graine; camera and water box do not retrigger drainage or reconstruction.
- **Control:** syntax and preview water/bed on seed 13, same pose; no benchmark or multi-seeds measure. Code GPT-6.1 Terra xhigh, no commit or push; tag of experiment waiting for a requested commit.

### 2026-10-27 · Phasor reproduced and then connected to the basin · spike to be judged

- **Reference:** official TerrainEnhancement repository, state `e0c75976013514e713bc05215927d4ec46462075`; maps and shaders kept in `tools/phasor-reference/`.
- **Adapter:** `tools/phasor-spike/`; one octave reference basin, 20 km region, 512² textures and grid, fixed scale of 3 km.
- **Settings:** frequency 50, amplitude 0,04, second level ×3 and ×0,3 as the demo; smoothing orientation of 16 passes for the basin. Amplitude driven by distance to collector and physical slope, without external hydrological map.
- **Comparison:** original height identical avant/après, normals calculated on the final height at physical scale; pose retained at the balance. View Versant and seed 13 by default.
- **Preliminary judgement:** new furrow visible on the slopes, large shapes preserved. Authors reference and then basin inspected; no benchmark or multi-seeds measure.
- **Limites:** geometry of ravines, without water supply or global network guarantee; regional domain, off engine. The previous triangular cells are visually inconclusive and set aside.
- **Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No commit or push; experiment tag waiting for a requested commit.

### 2026-10-27 · Common pools before retail CP · visually inconclusive

- **Architecture:** a basin subdivision simultaneously creates river section, flanks and internal partition; CP details come later. The reference integrated to an octave is retained for comparison.
- **Structure:** depth 3, 47 triangles and 15 courses by root; transverse exponents 1,4; bounds from 1,8 to 3 km; junctions at 25–40 % of available climb, sources at 65–80 %.
- **Inner summits:** M to 18–40 % of upper edge to J, rise to 90–115 % of edge; linear crest triangle to connect subbasins.
- **Common field:** deformations at 12 km and 3,7 km, displacement limited to 600 m; initial width 200 m divided by two up to 25 m, bed of 3 m.
- **Detail:** RidgedMulti / Billow limited to 10 % of relief above the bottom, zeros on the edges; CP Detail box to see the structure alone. Cache RGBA32F of module values, without routing into an existing relief.
- **Visualizer:** comparison without cropping; continuous altitude palette; overview at 30 km, inclination 65°, grid cell central 64 m.
- **Initial judgment:** common module visible without CP, shapes still very geometric; visual improvement not acquired. No benchmark, previews only on seed 14.
- **Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No commit or push; cache `bassins-communs-1`, tag of experiment waiting for a requested commit.

### 2026-10-27 · Side tributaries removed, return to basin only

- **User judgment:** hyper rectilinear courses cutting mountains, appearance of leaf ribs; less good result.
- **Decision:** keep the one octave basin and the viewer corrections; disable the tributaries at start. Their test remains accessible by a unchecked box.
- **Cause:** oblique traces then recomposition of a band, without common structure of the large ridges and the network.
- **Setting:** `tributaries=false` in model and start; Test of tributaries checkbox unchecked; cache `reference-bassin-1`.
- **Control:** syntax only, no benchmark or rendering; code GPT-6.1 Terra xhigh. No commit or push.

### 2026-10-27 · Fixed basin and tributary rivers · test distance

- **User feedback:** the one octave cymbal is consistent; four levels produce parallel bands and the viewer changes the range too much. The main sources remain at the foot of the mountains.
- **Conservation:** one-level basin, axis, shoreline and main profiles; streams shift to exact reference.
- **Tributarios:** cells of 3,2 km, lengths of 2,2 to 3,3 km, heads at 84 % of half-slope; upstream `A × smoothstep(v)`, with `A=(0,4+0,3 × potentiel) × écart/(écart+1,5 km)` km; width of 40 m tapered to zero, bed of 3 m.
- **Relief:** valley envelope of 250 m, lateral relief on 120 m; slopes recomposed around the shared profile, without strict preservation of the old micro-relief. Weight equal to one in the channel; connection to the collector by the same water and bed profile. Continuous mixing of neighboring cells, off at the split line.
- **Visualizer:** fixed cubic grid of 65,536 km side, grid cell central of 8 to 128 m; orbit linked to reference target; Whole grid by default, local views on a real tributary. Specialized programs by mode and cache GPU of the 64 node values, calculated by the functions CPU unchanged.
- **Control:** syntax and preview, no benchmark at user request. A scale of tributaries and collectors still parallel; no global hydrological validation.
- **Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No commit or push; cache `versants-1`, tag of experiment waiting for a requested commit.

### 2026-10-26 · Basins integrated into the relief · spike to judge

- **Architecture:** rough potential at 50 km, common structure of profiles, valleys and ridges, then details of slopes. The simplified potential temporarily replaces the rough entry of complexplanet.
- **Profile:** positive increments inherited from ancestors, parent/enfants connections at the same altitude, terminal rise to the sources; the inclined water body remains in the old mode.
- **Settings:** width multiplied by 0,47 per level; terminal taper on 1 km; side envelope of 80 m; incision of 3 m; RidgedMulti / Billow bounded to three octaves. After the first frame too smooth: peak `écart/(écart+1,5 km) × (0,6+1,2 × potentiel)` and modulation `0,25+2,5 × détail²`; widening frame at the confluence, cache `bassins-integres-2`.
- **Test:** Integrated Basins / Independent CP / Simple Relief; new view Slope / torrents; seed 14 and four octaves for the first judgement.
- **Control:** syntax, start and visual framing, resumed after setting peaks; no benchmark at user request. Drainage still oriented and local region, without integration to the engine.
- **Work:** code GPT-6.1 Terra xhigh; architecture and judgment by the main agent. No commit or push; experiment tag waiting for a requested commit.

### 2026-10-26 · CP relief adapted in the seeded viewer · spike to judge

- **Composition:** hautes/basses mountain groups and complexplanet hills, adapted to the 2D gradient; RidgedMulti, Billow and Turbulence, then positive mixture constrained by the valley.
- **Settings:** source frequencies divided by R = 6 378 km, powers multiplied by R; source gaps; low mountains and hills limited to three octaves, turbulence to two. No seed or distance to camera adjustment.
- **Lateral elevation:** `0,25 + 1,5 × collines + 2,5 × montagnes × masque de massif`, in km, cancelled at the bank by the valley envelope. The network and water profile are preserved.
- **Rendering:** three evaluations per vertex for height and interpolated normal; the fragment retains only the river field and interpolated height. A/B Relief CP / single without cropping.
- **Initial judgment:** relief significantly enriched on seed 13 / 4 octaves; simple preview, no benchmark according to user request.
- **Work:** code GPT-6.1 Terra xhigh; architecture, choice and judgment by the main agent. No commit or push; experiment tag waiting for a requested commit.

### 2026-10-26 · Fractal river module with seed · spike to judge

- **Replaces:** the two analytical courses predefined in the standalone viewer; history in the section “Replaced trials”.
- **Module:** dyadic cell subdivisions, from 1 to 4 octaves; basin width from 20 to 28 km; positions determined by seed hashing; continuous mother-daughter interpolation.
- **noise functions:** course distortion by noise of four octave 1D gradient, 2 gap and 0,5 gain; slope modulation by noise of three octave 2D gradient, 2,14 gap, 0,5 gain and 30 amplitude %.
- **Profile:** slope from 14 to 24 m/km following the seed, depth at −3 m; course width multiplied by 0,78 at each branch. Parameters are not retouched by seed.
- **Limit:** common downstream direction; no coupling to arbitrary continents of complexplanet yet.
- **Delivery:** Seed, +1 and Octaves in the same viewer. No benchmark for this iteration, on user instruction; no commits or pushes. The tag awaits a requested commit.

### 2026-10-26 · Relief built by rivers · stand-alone viewer

- **Model:** a unique function around a river and a tributary; profile of 20 m/km, bottom at −Z3 m, channels of 130 to 240 m; smooth slopes on 1,4 km and bounded modulation of 25 % of their amplitude.
- **Geometry:** projection on a sphere of radius 6 378 km; mesh of 512² cells, grid cell constant during descent; sinusoidal offset of the grid to isolate the slip.
- **Judgment settings:** grid cells 8 and 16 m; source, confluence and shore views; approaches to 3 m. The grid cells 64 and 128 m are not ground validated.
- **Measurements:** 39 000 probes without cut-off or rise; CPU/GPU to 1,26 near mm; maximum surface error of 8,29 cm to grid cell 16 m on the benchmark probes. Still images are identical; the slide keeps a maximum average deviation of 0,125/255 at the near coast edge.
- **Delivery:** `tools/lance-rivieres-simples.ps1`, without compilation or network. Report in `x64/RiverFirst/rapport.json`.
- **Status:** analytic spike off engine, no commit or push. The tag is waiting for the requested commit; no validation of the integration to complexplanet.

### 2026-10-26 · Dendry model, continuous sections and incised bed · removed after flight test

**User observation:** Mutations and flicker important approaching. The benchmarks profile and fixed captures were insufficient. The following part of a unique relief built around the rivers; proposal in section 8.

- **Replaces:** the profile on interpolated fields, offset; [tests and measurements](#tests-replaced).
- **Profile:** Minimum slope 1 m/km; margin 3 m under Catmull-Rom mip 0 on axis and both banks; probes at most all 2,29 m. The 194 156 nodes descend downstream.
- **Pre-coupling:** 36 passes; ceilings by the banks of other branches, out of their channels, tolerance of 5 cm; accurate downstream propagation on the shared graph. Drop of more than 1 m on 1,65 % of points, p95 zero and maximum 565,77 m. Relaxation remains non-converged: maximum auxiliary residue 0,617 m.
- **Banks:** monotonous Hermite rays, connected to the confluences; return of detail and mips on 100 m. The continuous partitioning of the incisions prevents a neighboring valley from removing the bank of another stream.
- **Combination:** shore weight `masque / (max(distance − demi-largeur, 0)² + 0,25²)`; channel guard extended by `4 × distance extérieure²`; minimum smoothed on 0,05 m. No embankment above the reference.
- **Precision:** projection and subtraction of the course in double precision precision; removal of the steps from 0,3 to 0,8 m due to the old planetary float calculation.
- **Rendering:** 129 126 sections, 774 756 water summits; CSR index of 512² cells; 22,22 payload MB; level error due to simplification limited to 4 cm. Independent ribbon, progressive coverage between 8 and 10 km from the edge of the model.
- **River control:** 4 817 634 probes; 3 132 active off-channel banks after incision, maximum overflow 5,1 cm; active underwater centers of at least 18,5 cm. F10 keeps a steep gorge and streams masked from far.
- **benchmark quality:** thirty places replayed, 1 350 views; the 59 p95 of the first spike are unchanged. The official reference remains out of threshold on 22 of the comparable 57 p95.
- **Palette:** location changes keep the camera in the requested position for twelve frames, so that the ground of the previous view does not bring it up; build Release checked.
- **To judge:** `tools/lance-rivieres.ps1`, twelve buttons and F1 to F12. Glacial springs and delta remain the next steps.
- **Git status:** no commit or push. The experiment tag is waiting for the requested commit after fly judgment.

## The rules and overlays of the branch

**The rules added to `principes.md`,** not included in `main`.

**In “The Principle”:**
- **A geometry can also be validated in motion.** Fixed views do not prove its stability at approach or its absence of flicker; distinguish the change of relief from the change of its sampling.
- **A avant/après comparison retains the reference pose, scale and height.** Normals correspond to the displayed geometry; a shading change does not replace a relief change.

**Water follows the drainage, not the bumps of the mesh** (`../recherche-rivieres.md`).
- **Sources and estuaries belong to the hydrological graph:** runoff and melting join a receiver to the sea or lake.
- **Water level drops downstream,** except on the flat surface of a lake.
- **Any lowering of the profile spreads downstream.** The water surface and banks connect without walking.
- **A course retains its connections at any distance.** A filtered field does not decide its topology.
- **The bed is dug under an independent water profile.** A delta forms at the coastal estuary according to the flow.
- **A geometry built around the courses shares a single function for the bottom, banks and water.** Its lateral relief is cancelled at the banks; the detail does not move the profile.
- **The bank belongs to the land and the water.** Their cut shares the same summits; masking the water preserves the geometry of the banks.
- **The profile and the bed share the same reference ground.** The axis, banks and neighboring excavations are checked after their combination; filtering does not move the bank underwater.
- **Accuracy follows the channel scale.** Planetary coordinates are subtracted before converting them to local floats; bank connections do not change branches per jump.
- **Inspection zoom refines sampling of the same global field.** His window and camera do not define another basin or a local relief function; masking the water does not reconstruct the terrain.
- **A local test keeps its planetary context visible.** Its grip is marked on the sphere and the zoom switch announces its scale and range; a test window does not demonstrate a function available on the whole planet.

**The experiment “rivers by noise functions” retains a generic mathematical composition** (`../recherche-rivieres.md`).
- **Deterministic modules and their parameters:** octaves, domain deformations, curves and operators; a shape fixed on the planet.
- **No exceptions per location or corrective retouching by passes.** An external drainage or erosion algorithm is another approach and must be announced as such.
- **A pure function with predefined curves does not yet constitute a generic river noise.** The connection and the descent of the courses remain to be demonstrated by construction.
- **The continuity of the noise does not guarantee the descent.** A specialized core may impose a monotonous upstream coordinate, a water profile increasing according to this coordinate and inherited junctions; the proof then concerns its built courses, not all slopes of the terrain or an entire planet.
- **The rough relief guides the common structure of the basins, valleys and ridges before the details of the slopes.** The river module intersperses between the large chains and individual mountains; the details preserve the water profiles and their connections.
- **A reworked relief strip around separate paths does not build ridges and drainage together.** The division lines and branches must be derived from the same intermediate structure, before the CP detail.
- **Refine drainage conserves the basin and its collectors.** Finer branches enrich the slopes at shorter scales; their number does not lengthen the basin upstream.
- **The source range belongs to the basin module.** Its cell variation preserves the inherited junctions and the common descending profile; raising a spring does not consist of laying water on the bumps of an independent relief.
- **Varying the shape retains the common construction.** A deformation of the domain also acts on the courses, ridges and banks; it remains injection and retains the upstream coordinate used for the descent.
- **Two neighbouring basins share their separation relief.** A common field and compatible profiles define their peaks; juxtaposing separately calculated terrains is not sufficient to guarantee their connection.
- **A planetary generalization is judged on the global CP source and a common seed.** Repeating a coastal window does not demonstrate the organization of continents; inherited junctions do not demonstrate the compatibility of two branches that intersect elsewhere.
- **The topology avoids crossings before drawing the curves.** Connections through shared ground cells and arms in disjointed sectors define the permissible domain; a simple curvature of free paths does not guarantee either this domain or the connections.
- **The detail of the slopes is composed around the river profiles.** An arbitrary old microrelief does not decide to hide or interrupt courses; its local replacement is part of the shared module, without correction by passes or exception by seed.

**The overlays added to `geometrie.md`,** in its table:

| Surcouche | Family | Scale | Amplitude | Where | Arrêt | Status |
|---|---|---|---|---|---|---|
| Maquette Dendry | Replacement: the relief of the river tree, complexplanet gives only the massifs and the roughness; bed incised under an independent water profile, vector sections and separate ribbon | valleys from 1 to 10 km, bottoms from 150 m to 2 km, channel dug according to its flow; Catmull banks mip 0, detail connected on 100 m | complexplanet's, its drained bowls | area of 150 km only, calculated off engine by `tools/hydro/dendry.py`, bordered by 8 km of connection | without `MYPLANETENGINE_DENDRY`  | discarded after regression approach; history in the section "Replaced trials"; new proposal in section 8 |
| Relief built by rivers, autonomous | Experimental replacement | root basin from 20 to 28 km, subdivision into three levels; common deformation at 12 and 3,7 km | bounds of 1,8 to 3 km, bed of 3 m; courses and crests of the same cell module; CP detail limited to 10 % of lateral relief | Seeded procedural field of the viewer `tools/river-first/`, fixed range of 65,536 km; off engine | Reference · 1 octave, or close the viewer | basins-communs-1 visually inconclusive, set aside; reference retained, tests in the "Replaced Tests" section; section 8 |
| Phasor on the reference basin | Experimental replacement | Area of 20 km; ravines of approximately 400 m and 133 m | intensity 0,04 of the height scale 3 km; second level ×0,3, amplitude limited by distance to collector and slope | viewer `tools/phasor-spike/`, off engine | Relief Original | official method reproduced and adapted; water collectors and shared banks, without drainage of ravines; section 8 |
| noise specialized basin | Experimental replacement | a macroscopic basin; two to four internal levels before detail | water profile increasing upstream; common cell field and lateral deformation of 650 m; modulated lateral relief, zero at banks | viewer `tools/basin-noise/`, engine off; no simulation or drainage map | Varied structure disabled for previous reference; close viewer | local test of connection and descent by construction; does not prove Complex Planet hydrology; section 9 |
| Basin core in MyPlanetEngine | Regional experimental replacement | window of 64 km; same analytical core as the viewer; detail CP under about 1 km | water at common profile, bed of 4,5 m; CP detail limited to ±10 % of lateral relief, zero on banks | explicit mode `MYPLANETENGINE_BASSIN` ; cell parameters exported, no heights map; 8 km surface transition out of judged zone | Restart without mode; launcher variables are restored | first confluence inspected in native rendering; no global integration or motion stability demonstrated; section 10 |
| Three coastal basins CP | Regional experimental replacement | 75 km of coastline, basins from 15 to 23 km; two mountain controls CP | profile common in distance upstream to the coast, lateral relief modulated by CP and zero at the banks; bed of 4,5 m |  `tools/coastal-basins/` and native mode V2, common seed 0; coast and CP controls, no final basin height map; native window of 100 km, external connection after sources | Close viewer or restart engine without pool data; previous references retained | three networks and common ridges inspected on a section, native set inspected; open planetary generalization; section 11 |
| Global Basins on CP | Experimental off-engine replacement | whole sphere; CP grid land cells, coastal sites spaced 600 km; structure relief on 120 km | seeded cell forest, curves contained in cells, descendant inherited profiles; common field guided by CP |  `tools/global-basins/`, common seed 0; discrete overall construction without routing on slopes; compact support of 450 km, mesh fixed | Current CP in the viewer; engine unchanged by this prototype | free arcs replaced to avoid crossings and bays of the discretized domain; grid dependence and mass conservation remain open; section 12 |
| Bed and water of the global network | Experimental off-engine replacement | uniform width channel 600 m; three fixed windows of mesh of 32 km, no 125 m | nominal bed up to 8 m under overall profile, banks and bed triangulated together; same curves and CP controls |  `tools/global-basins/water.html`, seed 0; global channel function, local zooms for inspection, no window of function replacement | Close zoom; Water only masks the layer, the bed remains present | prototype of confluence and mouth; details CP fine, flow, deltas and levels of mesh open; section 13 |
| Native global basins V4 | Incision replacement around the global network | CP complete; variable channels and connection of 3 km from the banks | soil strictly less than or equal to CP; profiles limited to probes CP32/256, source width then collectors and coastal evaporation | mode `MYPLANETENGINE_GLOBAL_BASINS`, seed 0; meanders common to the axes and valleys, hash of 20 km | B for original CP in the same frame; Y for masking water | profiles and morphology retained; branched delta and guarantees between probes remain open; sections 14–15 |
