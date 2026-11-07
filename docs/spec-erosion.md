# Spec: global erosion

**Status:** living spec, since 2026-10-31. Current worktree: `Exolune-erosion`, branch `claude/erosion-montagnes`; steps A and B remain uncommitted. Current route: `tools/tests/2026-11-04-altitude-rivieres.txt`. The terrain starts from the tectonic stack (`spec-relief-tectonique.md`).

## The objective

**Rivers and glaciers form one system, from the planet to 100 m detail.** Mountain ranges show branching transverse valleys, arêtes, buttresses and a continuous divide; folds remain in the foreland; all rivers reach the sea or a lake.

## The architecture

**Current defaults:** level 0 supplies drainage; step A builds ravines on the pre-erosion form; step B adds sized river corridors and inland water. Their implementation and review status are in the step A and B sections below.

**Legacy network path, with `EROSION_RAVINES = false`:** three levels, one network. Level 0 decides where water flows and at what height; levels 1 and 2 draw its valleys and gullies. The following table and level-1/level-2 sections describe that retained path.

| Level | Scales | Where, when | What it does |
|---|---|---|---|
| 0, the network | nodes at 20 km; shapes above 40 km | CPU, at startup, on the tectonic map grid; cache per seed | drainage to the sea, lakes by water balance, stream-power water level, discharge, ice, fans and deltas |
| 1, network valleys | from 40 km to bed width | shader, per point (`Erosion.hlsli`) | each link carves its valley into coarse ground: floor at water level, slopes at the threshold gradient, U-shaped under ice; deltas and fans |
| 2, gullies | from 11 km to 100 m | shader, within detail octaves (`Relief.hlsli`) | octaves reoriented along the slope of terrain above them: each gully descends toward its supporting valley |

**Why this division:**
- **Level 0 is global:** a river depends on the sea and its entire upstream basin. It is computed once, at startup, like the tectonic map.
- **Fine levels are local and deterministic:** simulated erosion by tiles is chaotic and joins poorly (research, spike B). A valley reads only nearby level 0 links; a gully, the slope of larger octaves.
- **Nothing is computed along the way:** levels 1 and 2 are point functions, like noise; level 0 is in memory from the start.
- **An explicit tree with several levels, like Dendry, is rejected:** each fine node must know nearby coarser links, and so on; per vertex, cost grows as 9 to the power of the number of levels.

## Level 0, `Erosion.cpp`

**The grid:** that of the tectonic map, 6 × 512², around 20 km. Uplift and erodibility are read without interpolation.

**Inputs:**
- **the pre-erosion form,** `ReliefElevation(p, false)` filtered to two grid cells, computed at startup on the GPU at each cell center (`ErosionForm.hlsl`);
- **uplift U and erodibility K,** slices 3 and 4 of the tectonic map, kept in memory until then;
- **precipitation P and temperature T,** through `ErosionClimate`, continuous bilinear `Climate::At` read on the CPU map kept since `CreateClimateMap`.

**The calculation:**
1. **Drainage:** Priority-Flood from the sea gives the filled surface and water ordering (Barnes, Lehman and Mulla 2014). A body without a sea drains to its lowest point.
2. **Lakes by water balance:** a depression retains a terminal lake if incoming water is less than what its entire surface would evaporate, minus rainfall on it; its level is where the lowest cells evaporate the inflow. Other depressions overflow and fill: plains.
3. **Routing:** each cell toward its lowest neighbor on the filled surface, flats by flood order; slope toward each neighbor weighted by ±15 %, drawn per cell and neighbor, based on rho8 (Fairfield and Leymarie 1991) but equally: paths waver between the two directions bracketing the slope, instead of straight lines at 45°. Runoff from the Schreiber curve, accumulated downstream.
4. **Water level:** from the sea and lakes upstream, stream-power equilibrium slope, S = ks A^−θ, θ = 0.45 (Kirby and Whipple 2012); A is drainage area at reference runoff, a dry basin is steeper. ks = √(30² + 150² U) / √K, U in mm/year: 30 on plains, 150 at 1 mm/year, 330 at 5, the Himalayas; the square root reflects slope exponent n = 2 measured on terrestrial ranges. Level never exceeds the filled surface: where equilibrium would be higher, the river flows on its plain.
5. **Knickpoint retreat:** incision travels upstream at finite speed, K A^0.5, along the law's characteristics (Tzathas et al. 2024). Beyond 1 000 km traveled by a river draining 10⁵ km², slower for a smaller river, the ground retains its shape: plateaus are incised only at their edges.
6. **Ice:** the equilibrium line of the last glacial maximum, 900 m below today's; today's line where summer temperature matches Ohmura, Kasser and Funk (1992) for the precipitation, with a fixed summer correction of +8 °C to the annual mean. Balance, 0.6 m/year per 100 m, capped at 2 m/year and precipitation; accumulated along the same network, upstream ice plus cell balance where ice is present. A glacier where flux remains positive.
7. **Deposits:** a fan where a river leaves a valley deeper than 200 m for ground it incises by less than a quarter as much; a delta at an ice-free mouth with discharge above 300 m³/s.

**Outputs, one `R32G32_UINT` texture per face, `t23` (`Erosion.h`):**
- water level at the node and filled surface, to a quarter meter;
- receiver among eight neighbors, tributaries among eight; flags: lake, sea, fan, mouth;
- discharge and ice flux, logarithmic.
- **Each cell's node** is a point drawn within the cell by its hash, at most 0.3 cell away: nothing to store.

**Integration with climate and volcanoes:** `t18` carries tectonics, `t19` its views, `t20` climate, `t21` volcanoes, `t22` their index, `t23` erosion. The table contains six descriptors. Level 0 reads the full pre-erosion form, including volcanic edifices and finishing. Valleys and deposits precede abrasion; barriers follow the smoothed shore, then reef finishing. Climate is computed before level 0, which reads its CPU map; `ErosionClimate` and `ErosionWaveWind` read the same fields in shader and port.

**The cache per seed:** `x64/Release/erosion-<graine>.bin`, keyed by the form read, size and all CPU climate fields, seed and executable date. The old key did not explicitly cover climate; every field change now invalidates the cache, even with identical executable and terrain. The CPU port reads it too.

**Shared terrain and water data:** valley floors, river surfaces and terminal lakes read the same drainage map. The six additional terminal-stage slices and channel construction are documented in [inland water](spec-eaux-interieures.md).

**The stack contract**
- The tectonic and volcanic support, its folds and octaves above 20 km do not depend on the network that will incise them.
- The network provides one valley envelope, with its drainage parameters.
- The difference between this envelope and the support decides incision and guides finer detail.
- Slope detail enters the cutting envelope; this envelope cuts the full terrain without raising it.
- The floor suppresses this detail only once; mesas and plateaus no longer receive a second preliminary mask.
- Deposits remain a separate operation, followed by coastal abrasion and shoreline finishing.
- The coarse prefix and detail are computed in the same loop; no second support evaluation is added for valleys.
- The global network remains computed at startup and cached; no erosion simulation runs during flight.

## Level 1: network valleys, `ErosionValleys`

**Paths and joins**
- Each link follows a quadratic curve between the midpoints of neighboring links.
- Four chords initialize the closest-point search; four Newton steps then measure the curve itself.
- Sources and outlets with repeated control points are segments: distance and parameter are computed directly, without division by a zero tangent.
- Distances are measured in the tangent plane to the unit direction; a chord's radial sag is not a riverbank.
- Height and reference ground follow the same quadratic; their slope is continuous at the shared midpoint.
- Geometric discharge and arithmetic ice flux also follow the quadratic between their shared values; their derivative does not become singular at sources.
- Warping retains wavelengths of 40 and 20 km, with amplitude 2 km.
- At 7 km, its Jacobian changed sign on nearly 13 % of tested points: a valley could fold or duplicate.
- The reduction to 2 km is checked on 100 000 directions per seed; this numerical check is not a global proof of injectivity.

**The profile**
- The fluvial floor retains its width according to discharge and longitudinal slope.
- The glacial U starts at the drained level, with `z + c x² / W`, `c = 0.3`.
- `W` depends on ice flux, from 150 to 1 500 m.
- The parabola joins its tangent when its slope reaches 0.85; height and slope are continuous.
- The parabolic profile is a morphological approximation, after [Hirano and Aniya, 1988](https://www.jstage.jst.go.jp/article/jgeography1889/97/2/97_2_107/_article/-char/en).
- The width law and its calibration remain those of the engine; they are not derived from this article.
- Underground overdeepening followed by capping at water level is removed: it turned the whole U into a flat ribbon.
- **Mesh filtering, since 2026-11-02:** the box mean of the physical fluvial/glacial section clipped by the ground, radius `max(cellMetres, CREASE_MIN_CELL)` (`ErosionClippedSection`).
- The ground is the point's own, less its positive spurs, taken constant across the box.
- **Why clip first:** averaged before clipping, the section's floor rose by up to `walls × radius / 2`. Once the box outgrew a narrow valley, that floor stood above the ground and the whole valley vanished; from orbit, valleys appeared between 2,000 and 1,400 km.
- **Clipped first, the incision keeps its area at every footprint:** from far, a valley is a wider, shallower depression that fades continuously.
- **A mixed section is clipped once,** at the crossing of the mixed fluvial/glacial profile; mixing two separately clipped shapes describes another section.
- **Stable closed forms:** the section less its excess above the ground, each term a box mean of ramps and squares, in float32.
- The 2 m minimum uses the existing physical crest rounding; there is no new setting.
- The filter ignores coarse reference depth and leaves the physical floor mask unchanged.
- The ground varies across a real box; the constant-ground mean is exact for one link on level ground only.

**Combining valleys**
- The surface is the minimum of the profiles; each already carries its own drained level.
- The geometrically closest link's level no longer bounds another link's surface.
- The slope guiding gullies blends over 60 m between competing profiles; it no longer jumps when the link changes.
- The cut surface carries positive spurs, fading on the floor; negative residual detail is not added to the cut a second time.
- Its C1 positive part uses the existing 60 m join scale; original hollows survive through intersection with the full terrain.
- **The cut reads the two lowest links,** each clipped at the ground, combined by their plain minimum. A smooth minimum, rejected, dug furrows along every divide.
- The minimum of the averaged profiles, `v.surface`, still guides the gullies.
- New excavation cannot go below the lowest clipped section mean, itself never below its link's level; this prevents artificial side trenches beside a perched channel.
- The cut is `depth × smoothstep(0, 60 × (1 - floorShare), depth)` on the shoulders; at full floor share it reaches the profile without a degenerate smoothstep.
- Incision never raises a hollow; suppression controlled only by the coarse support could raise a rim several hundred meters high.
- An initial hollow below the profile remains; filling it belongs to deposits or lakes, not this cut.
- At overlaps, a point on the old axis may belong to the slope of a lower valley; its ground follows that profile, not an independently selected water level.
- The fluvial floor includes the liquid channel width, subject to the existing reach bound, and does not drop its floor mask at terminal nodes.
- Channel cutting after terrain finishing is bounded by its compact depth; it cannot re-excavate an unbounded V profile.

**The supporting terrain stays independent of its finishing**
- The two octaves above 20 km are computed before gullies activate.
- Their height decides actual incision, together with the tectonic and volcanic form.
- The floor does not suppress these octaves before incision is computed.
- Incision no longer suppresses tectonic folds beforehand; `EROSION_FOLD_DEPTH` is removed.
- Buttress reinforcement and gullies apply only to subsequent octaves.
- Their minimum amplitude remains 0.35 of local depth, bounded by network incision.
- A valley above this support can no longer orient its gullies.

**Deposits and reach**
- Deltas and fans retain their profiles and reach limits.
- The query reads the neighboring 4 × 4 nodes; their influences fade before the set of nodes read changes.
- Depth and ice remain continuous maxima of local influences.
- Details of old profiles and measurements are in the [history](log/spec-erosion-historique.md).

## Level 2: gullies, within `ReliefDetail`

**Detail octaves from 11 km to 100 m change pattern where the ground slopes:**
- **phasor noise** (Tricard et al. 2019, *Procedural Phasor Noise*): plane waves across the slope, one period per octave grid cell, on the 8 corners of a two-period cell, each with its own phase; the phase of their sum. Its singularities are confluences;
- **the orienting slope:** that of the full support above 20 km, or of valley slopes where the valley actually incises it, plus that of larger octaves;
- **a centered replacement of the ordinary octave,** requested at 85 % on slopes above 0.15, nothing below 0.02; its share is reduced by the slope budget, without reducing the underlying noise;
- **near and above the ice,** only the ±300 m band around the glacial-maximum equilibrium line activates arêtes; ice flux shapes U-shaped troughs without sharpening detail;
- **a monotone profile with finite slope:** for `u = |x| / scale`, `(1+b)u − bu²` up to 1, then its tangent; `b = 0.2 × glacial`, zero stops it; its derivative increases by at most 15.1 % before rounding, versus a singular power before;
- **the same rounding interval:** a parabola joined in value and slope over `max(crease, CREASE_ROUNDING × f / gCreaseMaxFrequency)`; no finer width is reintroduced;
- **mean preserved:** normalization by `E|cos| = 2/π` and `E cos² = 1/2`, then subtraction of the exact rounding excess on sinusoidal bands; a series avoids subtracting nearby terms; change is exactly zero at `b = 0`;
- **they fade where the orienting slope reverses:** on crests of the octave above and of the largest one, that of ranges and folds, and at valley edges. Patterns on the two slopes do not join there: they raised comb-like blades along crests;
- **they fade around their bifurcations,** where the wave sum falls below 0.3: phase takes all values there, tearing the ground;
- **folds belong to the support:** valleys incise them according to their profile, without preliminary attenuation controlled by the network.

**One directional-pattern budget for soil and rock (`ReliefGullyRock`, `ReliefGullyGain`):**
- The rock fraction still follows mountain relief, wavelength and glacial climate.
- The admissible slope interpolates from `1.25` to `tan(70 degrees)` with that fraction.
- Both materials reserve the ordinary octave and the full directional-stripe envelope.
- The stripe envelope includes changes of direction, interpolation weights and phase forks.
- The gain is `B / sqrt(B*B + [share*(N+G)]^2)`, with `B = max(Sc-s-N, 0)^2/Sc`.
- Exhausting the reserve restores the ordinary octave; it does not remove the supporting terrain.
- The former rock exception used only amplitude divided by wavelength and produced metre-wide blades.
- This change adds no terrain lookup, octave, cache or simulation.
- The envelope is conservative: rock gullies are almost absent in the four reproduced defect windows.
- This is a geometry correction awaiting flight review, not a validated final gully model.
- Recovering stronger gullies requires a direction field coherent at their own wavelength, not relaxing the turning budget.
- The replaced budget is preserved in `log/spec-erosion-historique.md`.

**Blade regression checks, 2026-11-01:**
- `tools/hydro/verifie_lames.py` checks four 81-by-81 metre windows in two regions against public-history commit `7187c1b`.
- Maximum neighbouring one-metre height steps fall from 39.25, 39.09, 514.73 and 48.63 m to 1.55, 0.79, 1.64 and 1.32 m.
- No sampled slope exceeds 80 degrees after the change; maxima range from 40.82 to 59.44 degrees.
- The terrain before erosion is bit-identical; resolved outputs at 1 m and 0.25 m are identical.
- These are reproducible additional locations, not recovered camera coordinates from the user's screenshots.
- They do not prove global geometry validity or settle distant network repetition.
- Flight review: `tools/tests/2026-11-01-lames.txt`, close defects on F1-F4 and broader witnesses on F5-F12.
- Native captures at two close poses and two wider poses show continuous nearby slopes without the large blade family reproduced by the CPU checks.
- The distant relief diagnostic still shows serrated edges; regular large-scale drainage also remains visible. Their causes are not resolved by this correction.
- Capture artifacts are local in `x64/erosion-continuation/`; Windows window activation failed, so inspection used the engine's native image capture.

## Coastal cliffs

**Abrasion follows a full-ground contour, including detail, valleys and deposits.**
- **Where:** `ErosionCoast`, after deposits and before coastal barriers, only with `valleys = true`.
- **The estimated shore bounds reach:** it no longer places a wall in the mountains.
- **Contour:** `Hc = clamp(1000 W G, 8, 400)` m; the physical incision ends at `Hc + delta`, its sampled support at `Hc + delta + footprint`.
- **Width W:** 1.2 km × exposure × erodibility, at most 3 km; 45 % variation through 2.4 km noise (Sunamura 1992, force over resistance).
- **Slope G:** tangent magnitude of large shapes and the three detail octaves above 9 km, before gully limiting on mobile soils; coastal slope `coastSlope × shoreMetric / 1000` remains a floor.
- **Why 9 km:** three times maximum retreat; the 50, 23.7 and 11.2 km octaves retain large slopes without letting small spurs move Hc.
- **One terrain evaluation:** `cliffSlope` comes from the main `ReliefDetail` and its three octaves above 9 km; no recalculation or off-sphere read to freeze Hc. The projection parameter is removed: valleys are always read on the sphere.
- **The 400 m cap:** calibration near the 426 m Conachair cliffs listed by [NatureScot](https://www.nature.scot/landscapes-and-habitats/habitat-types/coast-and-seas/coastal-habitats/coastal-cliffs), without a universal geological maximum.
- **Capes and coves:** hard rock and shelter reduce W and the contour; soft rock and exposure increase them.

**Physical coastal metric (2026-11-01):**
- `ReliefCoastGradient` measures the coastal deformation at `EROSION_CLIFF_SLOPE_KM`, the existing 9 km erosion scale.
- Its maximum frequency is `min(meshMaxFrequency, planetRadiusKm / slopeKm)`; its crease frequency uses the same physical ceiling.
- Both octave weights and the derivative of `abs(noise)` use that ceiling; selecting long octaves alone leaves metre-wide cusps.
- The full coast noise still places the shore; the broad metric controls the contour height and the inland reach only.
- No setting, seed, map or neighbouring terrain query is added; the metric reads three contributing octaves instead of five at fine meshes.
- `python tools/cotes/verifie_metrique_cotiere.py` compares 576 derivatives with independent height differences, across three seeds.
- The derivative is identical from 0.25 m through 4,500 m sampling cells; maximum finite-difference error is below 6e-6 per radian.
- Six fixed terrain windows cover the reported cusp and its surroundings, cold, tropical, southern and flat coasts.
- The cusp's maximum 1 m height step falls from 172.67 m to 0.176 m; its 1-to-4 m mesh change is below 0.187 m.
- Source terrain is unchanged; flat coast is bit-identical; three other windows retain cuts greater than 10 m.
- The second reported canyon pose was inside the false excavation; its review camera is raised above the restored ground.
- Native captures at the original pose and the raised second pose remove the false wall and its needles.
- A wider view still shows an overly straight incision and a serrated distant bank; this correction does not establish globally clean geometry.
- The southern coastal witness no longer shows the previous isolated inland pits in its visible area.
- Flight route: `tools/tests/2026-11-01-metrique-cotiere.txt`; user review pending.
- The previous mesh-scale metric and measurements are [archived](log/spec-erosion-historique.md#2026-11-01-rejected-mesh-scale-coastal-metric).

**The profile remaps height h.**
- **Below Hc:** `min(h, P)`; P is −1 m at the foot, then descends linearly with h toward the old shore.
- **The platform:** nominal 2 % slope over W, height difference capped at 4 m (Trenhaile 1987).
- **Under the sea:** continuous join to the same line; deeper ground remains intact.
- **Face:** fixed physical width `delta = 0.1 Hc`; filter the composed incision over the symmetric height radius `footprint = 1000 cellKm G`.
- **Lowering:** at most `Hc + 1 m`, even on a coarse grid; no ground raised.
- **Talus:** nominal 35-degree apron, up to 22% of Hc, in 900 m patches; its landward end meets the cliff face at that prescribed height.
- **Stacks:** rare intersections of 130 m bands preserving the original ground; widened over two grid cells, reduced in proportion to their area.
- **Rivers:** low floors can pierce the contour and become sea inlets.

**Connected talus, `ErosionCliffScree` (2026-11-01):**
- A symmetric mound at Hc created a second downslope face before the cliff, leaving an artificial moat.
- Let `H = Hc - platformFoot`, and `T` be the existing talus-height setting times its patch mask.
- Find `t` on the cliff face from `delta*t + H*(3*t*t - 2*t*t*t) = T`; the contact is `Hc + delta*t`.
- A quadratic upper bound and four Newton steps solve this monotone interval; no terrain query or map is added.
- The apron above the platform is `max(T - screeSlope*max(contact-h, 0)/G, 0)`.
- Its excess rises towards the wall; beyond contact the cliff profile is already higher and takes over.
- The resulting section is continuous and nondecreasing in h for fixed parameters; it never rises above the original ground.
- Existing heights, patch sizes and slope settings are unchanged; the earlier symmetric profile is [archived](log/spec-erosion-historique.md#2026-11-01-rejected-symmetric-coastal-talus).

**Filtering after coastal composition, 2026-11-01:**
- `ErosionCliffMean` integrates the physical incision after the talus and min/max intersections.
- Split at the platform, talus contact and face joins; integrate linear and cubic pieces in local coordinates.
- No extra terrain query, map or generation setting is needed.
- For a planar source and frozen coastal parameters, the normalized symmetric mean preserves the incision area and its centre.
- `tools/cotes/verifie_filtre_falaises.py` checks an independent adaptive quadrature, joins, bounds, float32 precision and four terrain windows.
- Variable masks, the marine witness and later terrain composition remain outside this local conservation guarantee.
- The former one-sided widening and its measurements are [archived](log/spec-erosion-historique.md#2026-11-01-one-sided-coastal-filter).

**Talus regression checks:**
- `python tools/cotes/verifie_pied_falaise.py`: 384 parameter sections and an independent contact solver; maximum support error below 2e-10 m.
- The old profile reversed slope in 288 sections; the new profile reverses none.
- Four terrain windows cover the reported cold location, tropical and southern rocky coasts, and a flat coast; the flat coast is unchanged.
- The new physical coastal metric rejects the former cold-location cut; the independent profile check still covers its talus failure.
- The original camera comparison and its snow ribbons are [archived](log/spec-erosion-historique.md#2026-11-01-rejected-symmetric-coastal-talus); material rules are unchanged.
- Flight review: `tools/tests/2026-11-01-pieds-falaises.txt`; no performance or quality benchmark was run.
- This correction addresses the talus connection; amplification of detail filtering by the coastal remap remains a separate open issue.

**Inputs and reach are preserved.**
- **Rock:** class converted per texel before B-spline; oceanic crust 1, volcanic 0.6, young range 1, sediments 1.6, old range 0.45, shield 0.25.
- **Soft sediments:** factor `1 + saturate(-forms.w)` per texel; continuous proxy for K, absent from the GPU map.
- **The sole wind:** `ErosionWaveWind`, its CPU twin `erosion_wave_wind`, climate cube 1, east and north in m/s, travel direction.
- **Relative strength:** 1 up to 5 m/s, linear toward 1.6 at 8 m/s, capped; calms fade continuously from 0 to 1 m/s. The useful 1–1.6 interval retains the previous calibration, without retaining its zonal directions.
- **The frame:** east `(-d.z, 0, d.x)`, north `cross(east, d)`, as in `Climate.cpp`; no wind reversal or “coming from” direction.
- **Exposure:** offshore direction from the large-shape gradient; omnidirectional swell of 0.28.
- **Bays:** suppressed at −12 km coastal displacement, fully exposed at −6 km.
- **The seaward band:** no inner limit within the raw 8 km proxy; detail can raise the real coast there.
- **The inland band:** `shoreKm / shoreMetric < min(W + 1 + relief / coastSlope, 8)` km; fades over the last 500 meters.
- **Detail displacement:** its tectonic amplitude `relief`, before the valley-wall term, divided by coastal slope in m/km; a distance in km, without a new read.
- **The raw proxy:** `abs(shoreKm) < 8 km`, fading over 500 m on both sides; computation limit preserved, independent of grid spacing.
- **Sea access:** a probe at 3 km, `RETREAT.z`, in the large shapes' offshore direction already used for waves; its pre-erosion ground must be below −50 m.
- **Why before erosion:** an incised valley or trough must not open wave access by itself.
- **The probe:** same terrain, barriers and summit limiting, without valleys, erosion gullies or deposits; no extra erosion-network read.
- **The transition:** its presence moves continuously from 1 to 0 over 250 m of coastal distance, converted through the probe's slope; it is 0 from −50 m upward.
- **Nature of the test:** conservative sea probe, not a global connectivity measure; the −50 m threshold is that of the reach check, not a universal abrasion depth.
- **Probe position:** small-angle rotation in double precision; no product of a float planetary position and the radius.
- **Nothing on flat coasts or in fully sheltered bays.**
- **Cost:** early exits outside the band; intact ground skips scree and remnant noise; only a potential cut reads this second terrain point, without a new valley search.
- **The connection:** `ReliefSampleGround` separates ground from coastal processing; `ReliefFinish` keeps barriers and the cap; the probe neither recurses nor replaces the main point's roughness.

**Settings, prefix `EROSION_CLIFF_` in `PlanetSettings.hlsli`:**

| Setting | Value | Meaning |
|---|---|---|
| `RETREAT` | `(1, 1.2, 3, 0.45)` | activation, unit and maximum retreat in km, relative variation |
| `NOISE` | `2.4` | retreat wavelength, km |
| `BAY` | `(-12, -6)` | fading and full exposure, km of displacement |
| `REACH` | `(1, 0.5, 8)` | inland margin beyond retreat and detail, fading, inland cap and proxy bound, km |
| `SEA` | `(50, 0.25)` | minimum probe depth in m, transition in km; its distance is `RETREAT.z` |
| `HEIGHT` | `(8, 400)` | Hc bounds, m |
| `SLOPE_KM` | `9` | physical slope scale in km; detail octave cutoff and coastal metric's spectrum and crease filtering |
| `FACE` | `0.1` | minimum share of Hc for δ |
| `SCREE` | `(0.7002, 0.22)` | repose slope, share of Hc |
| `PLATFORM` | `(-1, 0.02, 4)` | foot in m, nominal slope, maximum height difference in m |
| `STACK` | `(0.065, 0.8, 1.4)` | half-width and noise in km, regional threshold |
| `WAVES` | `(0.28, 1.6)` | swell, maximum relative strength at 8 m/s |

**Current checks:** `python tools/cotes/verifie_falaises.py`, then `python tools/hydro/verifie_cretes_climat.py --before fe22cfe9d6d96e9680ca44ef2fd5e47704467939`.
- **The three fixed sections remain measured:** with integrated caches, the committed port already finds only two faces, one above 100 m; the third historical face is absent before the connection. The check compares before/after numbers on this same control, without changing physical limits.
- **Physical limits remain on computed wind:** lowering at most Hc + 1 m, no ground raised, mountains intact, less than 5 % landlocked cuts and p99 reach below 4 km.
- **Old tables:** [history](log/spec-erosion-historique.md).

## Step A: ravines on the pre-erosion form

**`EROSION_RAVINES`, on since 2026-11-02, replaces the network's drawing:** levels 1 and 2 drew a geometry worse than none.
- **Rendered:** the pre-erosion form and its ravines; no valleys, gullies, channels, lakes, deltas or fans; wave-cut cliffs kept.
- **Kept:** level 0, its build and its cache, for step B's corridors (`tools/hydro/couloirs.py`).
- **To return:** `EROSION_RAVINES = false`, the network as before.

**The ravines, inside `ReliefDetail`,** ported from the CPU prototype `tools/hydro/ravines.py`, its settings unchanged:
- 11 octaves of period 5 km down to 4.9 m, halving; each a phasor blend of stripes across its steering slope, a pivot jittered at each lattice corner, the point bent by one warp octave of 2 periods.
- Profile 2 |cos(u/2)| m (2 − m), its trough rounded over 2 mesh cells or 10 % of the period, less its exact mean, an elliptic integral.
- Amplitude 0.15 × period × 0.8 tanh(S / 0.8), times rock, humidity and relief, faded in over the first 50 m of the steering ground.
- Filtered by the footprint like any octave (`RlWeight`); added to the whole ground, after the mesas and badlands.

**The steering, per point and analytic, where the prototype differentiates a filtered grid:**
- Each ravine reads the large forms, the detail octaves of wavelengths from 2 of its periods, their crests rounded at its scale, and the coarser ravines at half their slope, their troughs rounded at its period.
- Each detail octave adds itself to every pending ravine; a ravine is drawn once the next octave no longer steers it.
- **The true slope:** the oriented octaves through the detail warp's and the chain lift's Jacobians (`RlTurbulenceJacobian`); the map's gradients through its face projection (`ReliefMapSlope`); the boundary profiles' slope added.
- Without them, the detail's own analytic slope is 50 to 100 % off the true gradient and the steering 25 to 55° off the prototype's; with them, 3 to 14° median. The detail's `slope` keeps its other uses unchanged.
- **Held fixed:** the map's warp, the coast noise, the volcanoes' edifices, the mesas, the segments' noise and the octaves' amplitude factors.

**Its gradient holds the steering fixed:** exact to 5e-5 against finite differences. The whole sum's differs by 23 to 37 % rms, the stripes' turning with the steering, which would need its second derivatives.

**Checks:** `python tools/hydro/verifie_ravines.py`; beside the prototype, `python tools/hydro/etude_relief.py --variants sans ravines ravines_moteur2 --samples 192 --out x64/etude-relief-moteur2`.

**Flight status:** step A's geometry was accepted by the user, as recorded in the 2026-11-03 handoff.

## Step B: river corridors from level 0

**`EROSION_RIVERS`, on step A since 2026-11-03, sized by discharge the same day:** the level 0's large rivers as corridors with their water, ported from the CPU prototype `tools/hydro/couloirs.py` (`RIVER_*`, `PlanetSettings.hlsli`).
- **Rendered:** step A's relief; on it each river's floor and walls; its channel cut after the finish; water at its stage over the wet channels; the terminal lakes from their existing stage slices.
- **To return:** `EROSION_RIVERS = false`, step A exactly. The startup passes still run when the cache is stale; nothing reads their words.

**Sized by the river, 2026-11-03.** From 465 km the first corridors drew a valley on nearly every 20 km link, one shape for all: every link from 10 m³/s, 48 % of land links, 14 km apart on the wet plateau (−6.6°, 125.3°), where one cell's runoff alone exceeds 25 m³/s; floors set by the meander belt alone, ±4 % at a given discharge; walls of 6 km wherever the relief stood 3 km above the stage.

**Which links, `RIVER_Q` (100, 300, 450) m³/s:**
- **Rivers, with water and their full corridor,** above 300 m³/s; water fades to its full nominal width by 450. The nominal channel width at 300 is 83 m before this fade and the width noise.
- **Dry notches** from 100: depth, floor and walls grow together by `smoothstep(100, 300, Q)`, in discharge rather than log discharge. The monotone curve is C1 at both thresholds. It gives a narrow, shallow continuation on existing upstream links before the broad corridor. Its share is 0.15625 at 150 m³/s and 0.5 at 200 m³/s; it is exactly one from 300.
- **Smaller links** are left to the ravines: their valleys are the relief's own, finer than the level 0's 20 km graph.
- **Observational reference:** outlet spacing in linear mountain belts is about half their flank width ([Hovius 1996](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1365-2117.1996.tb00113.x)). This does not prescribe a global discharge cutoff.
- **Calibration:** thresholds and onset polynomial are engine choices. Smaller rivers have no explicit water. This extends the existing coarse drainage hierarchy, without inventing camera-dependent head shapes or new subgrid tributaries. The former 200–300 onset and density measurements are in `log/spec-erosion-historique.md`.
- **Bounded evaluation:** raw accumulated flow bounds every surviving inflow; a one-code quantization margin permits an early inactive-catchment rejection. Dry-course culling scales floor and wall reach by their maximum physical growth share. These bounds remove evaluation work, not terrain detail.

**The floor, per point:**
- **The law:** valley floor width W_v = K_v A^c; published fits vary with lithology and region. Clubb, Weir and Mudd find c = 0.3 ± 0.06 in the Appalachian Plateau and discuss western Alpine fits of 0.3 to 0.4 ([Clubb et al. 2022](https://esurf.copernicus.org/articles/10/437/2022/)).
- **The engine's calibration:** 230 Q^0.4 m in plains, times the rock's erodibility to the power 0.5 and a mountain factor down to 0.35 over relief amplitudes of 300 to 1 200 m. The coefficient and modifiers are not universal published constants. Replacing drainage area by discharge assumes a runoff regime; A = 31.6 Q in km² only at 1 m/year, whereas the planet's runoff varies.
- **Along the course:** times 2^±1 by a noise of 12 km read on the course: gorges and basins. At most 8 km wide, never narrower than the channel.
- **The meanders bend the channel within the floor as far as it allows, the valley with it beyond:** in a gorge the valley winds with its river, incised meanders; in a basin the channel meanders across a straighter valley. The channel's course is the same either way. Every function that builds the channel, the corridor, the junctions and the startup's caps, reads the same `ErosionMeander`.
- **Stored** per node as the factor's log2 over −3 to 1, 4 bits.

**The walls:**
- **Width:** the relief's mean height above the stage plus a quarter of its amplitude, over a slope from 0.2 on plains to 0.5 in mountains, times the erodibility to the power −0.25, steeper in resistant rock (Selby 1980); within 300 m to 6 km, as before.
- **Along the course:** times 2^±0.5 by the same noise, narrower walls with a narrower floor.
- **Profile:** a ramp at constant slope, rounded into the floor and the relief over 15 % of its width for rivers of 300 m³/s, straight V sides, to 50 % from 3 000 m³/s, the broad footslopes of large valleys. The smoothstep before rounded half of every wall.
- **The corridor** stays within 8.5 km of its valley's line. The channel width and meanders also enter the search bound; `verifie_morphologie.py` checks it against the 4 × 4 node search, including cube corners.

**The channel:** nominal half-width 2.4 √Q, Leopold and Maddock's (1953) exponent 0.5; depth 0.35 Q^0.3.
- Physical width varies by `1 + 0.9 (0.5 n12 + 0.3 n3 + 0.2 n0.75)`, each bounded noise in [−1, 1].
- `n12` is the valley's existing 12 km opening field; the independent finer fields have wavelengths of 3 km and 750 m.
- The factor stays in [0.1, 1.9]. The linear centred field tends to the nominal width when unresolved.
- Each field is sampled in world space on the course, consistently at joins. Culling uses its maximum possible width.
- These coefficients are engine calibration, not a hydraulic law for exposed sediment or braided channels.

**Terrain retained inside the corridor, 2026-11-03:**
- The previous cross-section suppressed all intermediate terrain by the same symmetric ramp, including existing mountain spurs.
- Keep the positive residual between the full terrain, its support before the 50 km detail octaves, and the fine floodplain detail.
- Smooth its onset over 60 m. Bound the retained height by the terrain above the bank; negative residuals never deepen the cut.
- Contract the local floor and wall widths by `c = 0.25 + 0.75 A / (A + 3 spur)`, with `A = max(terrain - bank, 0) + 60 m`.
- Read this confinement at the terrain point, not on the drainage axis. Opposite flanks therefore follow different parts of the mountain field.
- The contraction stays between 0.25 and 1. The minimum floor contains the actual displaced channel and both dry banks, transformed into the valley's distance metric; two widths around the undisplaced axis are insufficient.
- Search bounds include the maximum displaced-bank belt. They remain inside the existing node search on seed 0.
- Contracting the profile cannot increase dry incision. Merely lifting detail inside an unchanged floor left its large outline too regular in the preceding native candidate.
- The candidate lift starts beyond twice the channel half-width, with a smooth recovery to the larger of four half-widths or 0.6 of the uncontracted floor or required bank belt.
- Bound that lift by the horizontal room from the dry bank: `x = max(channelDistance - 2 bankHalfWidth, 0)`, `B = 0.6 x² / (x + 100 m)`.
- Keep candidate lifts `L <= B/2` exactly. Otherwise retain `B (1 - B/(4L))`, a C1, monotone soft cap below both `L` and `B`.
- `RIVER_SPURS.z = 0.6` calibrates this added-height envelope. It is not a limit on the slope of the full terrain or the base valley walls.
- This prevents a recovered mountain from forming a high inner wall beside a tiny channel. Broad base gorges and small spurs with ample room retain their existing profiles.
- The final local profile is `bank + (terrain - bank) g + (1 - g) lift`, including the existing fine bank roughness.
- This preserves spatially asymmetric terrain at several scales without raising the original mountain or obstructing the wet bank.
- Large bends now start at 40 km. Wavelengths from 10 to 20 km transfer fully to the valley offset, bounded at 2.5 km; larger bends cannot enlarge the channel's fine meander belt.
- The level-0 drainage graph is unchanged. Preserving spurs does not construct a connected hierarchy of new tributary valleys; that limitation remains part of flight review.
- Step A computes its ravine steering before step B cuts the large corridors. Retention and confinement do not redirect those finer ravines into the new flanks; connected subdivision remains a structural follow-up.

**The courses, per point (`ErosionRivers`, `Erosion.hlsli`):**
- **Courses:** the links whose midpoint discharge reaches 200 m³/s, compared on the stored bytes. A course runs from the midpoint with the largest inflow, through the node, to the midpoint with the receiver: the level 0's quadratic Bezier.
- **Along it:** stage, discharge, wall width, sinuosity and the floor's factor, quadratic from the nodes' values, C1 at the joins, as the level 0's stage.
- **Heads:** a dry valley straight on from the course's start, 12 km at 15 %. **Outlets:** the course continues 15 km at its level, to the detailed coast. Both in proportion to the level 0's cells, 12 to 25 km: they stay within the 4 × 4 nodes read.
- **Confluences:** every other inflow carrying a river is re-routed from its link's midpoint to the main channel, where the main stage has fallen to its own past the course's middle. Its requested arrival follows Howard's angle, bounded to 12–55°; the bounded quadratic control may fall back to the chord. Its meanders fade over its last 40 %.
- **Its control** is where its heading meets the arrival line, clamped to its node: the connector stays among the node's neighbours, within the nodes read.
- **The course:** the curve displaced by the fractal meander offset, read at the curve's point taken radially to the sphere. Every point that measures a course sees the same course. The octaves are filtered by the mesh as any noise.
- **The corridor:** the rounded profile plus the bounded terrain residual above; fine floodplain detail, combination by maximum fill and maximum carve, channels cut with steep banks.
- **Skipped only when proved:** the meanders' slope is clamped to 1 in the distance, which bounds it; a course is skipped where neither its corridor nor its channel can reach the point.
- **Standing water:** corridor fill is zero at and below its stage, reaching full strength 50 m above it.
- **Past its ends,** a course's stage goes on along its slope, its neighbour's to first order. Held at its end value, its banks, bed and water stood a step above the next course's, 0.1 m on a 3 % river.
- **A wet channel is cut into its supporting ground:** the physical bank/ground intersection is integrated over the footprint before composing the channel beds. Its flat wet core and cubic submerged shoulders are integrated separately. Physical banks stay at W and 2W; sampling never moves them outward.
- **The final river surface respects the wet-section union:** use the deepest compact cut at the blended stage. The surface is bounded by the composed bed plus that cut. Resolved shading uses the actual water column; unresolved shading retains the independent depth moment. Coverage does not trigger another terrain excavation. Terminal lakes retain their own stage.
- **Overlapping water blends:** stages and currents use wet-interior weights; compact cuts use their maximum. The previous weighted depth created a pale closing sill at confluences.
- **A re-routed tributary retains its water level throughout its wet section.** Compact wet-interior weights blend the actual overlap; distance to the junction never erases a still-uncovered inflow. Its stage leaves at its own course's slope, then falls to the receiving stage.

**The stages, at startup, only when the cache is stale (`ErosionNodes.hlsl`, `ErosionStages.hlsl`, `Erosion::Condition`):**
- **Per node:** the sinuosity from the slope of the 25 km forms, the floor's factor, their relief amplitude and the rock's erodibility.
- **Per course,** the very courses `ErosionRivers` draws: 33 points of its channel, displaced by its meanders, the pre-erosion relief filtered at 500 m. The cap: the lowest of it where the course carries water, from 300 m³/s, clipped at the sea, less the bank; and its mean.
- **Only as deep as the corridor drawn needs:** a dry notch has no cap; its stage follows its river's by the monotone passes. The cap's filter and the 3 % drop rate are unchanged: a hollow wider than 1 km on a river's own course still sets its stage; filling it would dam the side valley.
- **On the CPU, the prototype's conditioning on the nodes.** Downstream: a node never above its course's cap plus 15 m, its re-routed inflows' caps, or its inflows' stages. Upstream: drops at most 3 %; a course's start below its cap too.
- **Why the start too:** every control of a quadratic course below its lowest cap keeps the whole course below it.
- **The wall width,** then, by the walls' law above.
- **Stored** in the high halves of the terminal-lake slice (`Erosion.h`): the stage, the wall by 25 m, the sinuosity and the floor's factor in 4 bits each. The original level-0 words remain unchanged. `EXOEROS6` adds first-water contacts and surviving discharge; all three startup shader binaries enter its key.

**Where it differs from the prototype:**
- The stage is quadratic between nodes, not per vertex: upstream of a hollow, it falls over half a link rather than at 3 %, and the corridor is deeper there.
- The junctions follow the conditioned stages per point; the startup samples the tributaries at the level 0's.
- The wall width is the node's; a head keeps its start's.
- Fine floodplain roughness keeps the detail's and the ravines' relief finer than 400 m. Existing positive terrain residuals at intermediate scales survive separately as spurs.
- The curves are solved exactly, not as 32 pieces; the cap is sampled on the channel, not on the undisplaced curve.

**Distance filtering, 2026-11-03:**
- `ErosionChannelBankCut` integrates the positive dry-bank incision in local coordinates, after clipping it against the supporting height.
- `ErosionChannelCoverage` integrates the physical wet interval, independently of the filtered cut's wider support.
- Mesh vertices carry mean depth and wet fraction; fine and screen samples carry wet fraction, fraction times stage, and mean depth.
- Water shading divides mean depth by wet fraction. Step B no longer thresholds the diluted depth to decide whether water exists.
- Pixel contour refinement uses the same river fraction; lakes retain their separate clearance and contour antialiasing.
- The analytic guarantee is for a locally straight section with frozen ground and parameters. Channel overlap uses maximum coverage and compact depth; this is not an exact two-dimensional union filter.
- After combining corridors, remove at least the compact mean cut from their supporting ground. A lower neighbouring corridor must not leave a resolved water sample over dry terrain; the check compares its depth with the actual stage/bed gap.
- The distance-filter change itself changes no discharge, width, density, map or cache-version setting.
- Independent check: `python tools/hydro/verifie_filtre_rivieres.py`; 103 sections, numerical quadrature, incision conservation, wet-area conservation and float32 precision.
- Review route: `tools/tests/2026-11-03-eau-distance.txt`; exact 250 km and 173 km approach screenshots, the reported 863 km coast, closer views and separate confluences.

**Valley morphology remains under review:**
- The user judges the current direction substantially better. Broad canyon sections returning to ordinary beds are acceptable; prolonged deep, narrowing slots upstream remain the specific defect to remove.
- The user rejects the repeated corridor shapes, nearly parallel flanks and homogeneous apparent widths, including their coastal outlet pattern.
- Required direction: retain mountain masses and asymmetric side valleys at several scales, with terrain-related constrictions and openings.
- Discharge sizing and along-course width noises alone do not establish this structure; the current candidate also retains the terrain's two-dimensional positive residual.
- **User reference:** the Alps image supplied on 2026-11-03, kept locally at `x64/erosion-reprise/reference-alpes.png`. Read a hierarchy of major valleys, secondary valleys and fine branching between asymmetric spurs. High valley density can coexist with this hierarchy; density alone is not the acceptance measure.
- At the reference image's regional scale, valley floors and snowy ridges dominate; water itself must not become the broad stroke that defines every valley.
- The distance-filter correction removes a separate source of uniform widening; it does not certify the network density, valley morphology or physical water-width variation.

**Google Earth reference traversal, 2026-11-03:**
- Inspected the user's open Alps tab from a 658 km regional camera to about 370 m above the Isere, through the Tarentaise and Bourg-Saint-Maurice basin.
- Ten original browser captures and their observed camera URLs are kept locally in `x64/erosion-reprise/reference-earth/`; `references.json` records displayed camera heights and scale bars. They are not Git assets.
- [Regional view](https://earth.google.com/web/@45.58337281,6.93291364,1998.53973021a,655705.50903775d,35y,5.18127419h,0t,0r/data=CgRCAggBOgMKATBCAggASg0I____________ARAA): major valleys organize a much finer branching relief; water does not draw each valley as a broad ribbon.
- [Bourg-Saint-Maurice at 31 km](https://earth.google.com/web/@45.60508856,6.79962949,1539.68367638a,29723.58533304d,35y,5.18016832h,0t,0r/data=CgRCAggBOgMKATBCAggASg0I____________ARAA): broad openings alternate with narrow sections; opposite slopes carry different spurs, hollows and secondary valleys.
- [Oblique comparison](https://earth.google.com/web/@45.60407231,6.77177106,907.6682615a,7504.0641206d,35y,5.18011852h,60t,0r/data=CgRCAggBKAI6AwoBMEICCABKDQj___________8BEAA): the slope asymmetry is visible in the terrain, beyond differences in shadows, forest and farmland.
- [Close river view](https://earth.google.com/web/@45.58697455,6.74873857,750.03970911a,371.82281343d,35y,328.29774422h,0t,0r/data=CgRCAggBOgMKATBCAggASg0I____________ARAA): exposed gravel bars and the wet channel vary separately within a wider valley floor. Opposite wet edges do not simply mirror one centreline.
- The second user image is preserved at `x64/erosion-reprise/reference-alpes-detail.png`.
- Compare ground footprints and feature sizes, not camera altitude alone. Camera heights in the manifest are sea-level values; the last two above-target heights are approximate.
- These are qualitative Alpine references. The developed Isere corridor is not an untouched-river width law, and the imagery does not measure bathymetry or establish a universal valley profile.
- Implementation target: organize mountain masses and connected side valleys across scales, then derive asymmetric confinement and river widths within that relief. More independent centreline or width noise alone does not meet the target.

**Photo comparison, 2026-11-07:** renders without clouds beside the captures at matching ground footprints; colours compared by their medians.
- **Channels too even:** the Isere's banks wander by tens of metres along gravel bars. Retained: width noise twice as fine, banks wandering by up to 25 m, gentle reaches keeping 60 % of it (`geometrie.md`, `journal-planete.md`).
- **Water colour, measured, not retained:** the Isere at 830 m, median (47, 80, 87); ours at 2,200 m, (50, 79, 77). A turbid grey-blue water over grey gravel moved it to (62, 74, 83), away from the photograph's.
- **The largest gap is the relief's, not the rivers':** from 30 to 100 km the photographs show dendritic ridges, snow on aretes and branching side valleys; ours shows long wavy bands. Next: the mountain masses' morphology, above.
- **At the metre scale:** whitewater, exposed gravel bars and turbid streaks along the Isere; ours is smooth and even.

**Approach reconstruction, 2026-11-03:**
- Average the composed signed corridor change, including bank roughness and bounded spur recovery, over the physical cross-section.
- Split at floor, rounded-wall, bank and spur transitions; four Gauss nodes integrate each piece. Local terrain and course fields remain frozen across the footprint.
- Culling and node enumeration include that footprint. The physical 4 × 4 search extends to the union of chart cells reached by the footprint, with the cube-corner metric bound. A coarse sample cannot omit a neighbouring narrow course merely because its centre lies outside the original four cells.
- The filter never enlarges the physical valley or channel to match a screen pixel.
- A stable float32 cap preserves tiny retained spurs beside large horizontal allowances; no subtraction of huge unused values.
- Fine and screen grids reconstruct coverage, stage/depth moments and premultiplied current with the same positive 4 × 4 B-spline as height.
- Mesh/fine/screen crossfades and pixel contour refinement blend those moments before dividing by coverage.
- Overlapping channels blend their current with the same wet weights as their stage; a change of the lowest bed no longer selects a different velocity abruptly.
- Fine samples are 48 bytes; screen samples are 64 bytes. Screen activation remains 150–400 km.
- This is a local section filter, not a full two-dimensional average over an arbitrary curved valley. Unresolved meander variance and interactions between crossing corridors remain approximations.

**Confluence openings and physical banks, 2026-11-04:**
- A connector reads the receiving channel's physical half-width at its junction, including the shared valley/width modulation. The approach spans at most nine combined nominal half-widths, bounded by the connector's own length so its upstream join stays unchanged.
- First match any wider tributary down to the receiving width. Open a narrower tributary only towards the downstream-facing bank: add half the remaining width deficit to its half-width and shift the section centre by the same amount. The opposite bank retains the upstream land tongue.
- At full approach, the half-width plus absolute shift never exceeds the receiving half-width. Equal-width arrivals add no bulb. The side comes from the actual bounded connector tangent and the receiving flow including its meander slope, also in control-point fallback cases.
- For a local turning sine `s`, the signed opening factor is `sign(s) * smoothstep(0, sin(12 degrees), abs(s))`. Width gain uses its magnitude, and centre shift its signed value. Almost-parallel courses need less opening; passing through parallel alignment cannot flip a full-width bank as the meander is filtered during approach.
- `RIVER_CONFLUENCE.x = 0.5` is a bounded geometry calibration, not a sediment-transport law. Micro-bank perturbations retain their separate physical bound.
- The requested arrival-angle range is 12–55 degrees; the existing bounded control-point fallback remains in use.
- The shift uses channel-normal metres. Bed, wet coverage, bank profile and valley-floor clearance share it; the floor converts the same displacement to its own metric. Search bounds use the larger receiving/tributary width, including the shift. The drainage spine and cached contact path stay unchanged.
- Water levels and currents blend over actual wet overlap. The former longitudinal handoff could erase a tributary before the receiving channel covered it after discharge was reduced.
- Bank height varies by `1 + 0.7 (0.55 n180 + 0.30 n45 + 0.15 n11.25)` at actual terrain points. Opposing banks read different fields.
- The dry bank rises over `min(halfWidth, max(2 m, 4 bankHeight))`, followed by its terrace to twice the half-width. The previous rise across a whole half-width made broad, nearly flat margins. The physical breaks and clipped incision are integrated before sampling.
- The wet bank uses `B = min(halfWidth, max(2 m, 4 depth))`. Depth is constant inside `W-B`, then `depth * smoothstep(0, 1, (W-|x|)/B)` to the shore. Width and maximum depth stay unchanged; the pale shallow shelf no longer spans the whole river.
- The exact box mean preserves section area `depth * (2W-B)`. Flow velocity uses this same area. The legacy level-0 quartic profile remains unchanged.
- Each octave follows the terrain bandwidth rule and tends to zero when unresolved. The existing bank height remains the mean.
- The same world field moves each wet boundary by at most 12 m, 0.16 nominal half-width and one quarter of local width. Gentle grades retain 30%; full amplitude begins at grade 0.02. This is a calibrated bank-detail proxy, not a bank-erosion simulation.
- Joining channels retain their deepest compact section. Averaging depths produced a pale closing sill inside the receiving water.
- Resolved shading reads the actual stage/bed gap without a coverage-dependent terrain correction. Current fades continuously in a lake's receiving water column.
- Within 40 m of a dry bank, existing world-lattice objects gain gravel and tuft probability. Wet rejection, slope, loose-material, snow, canopy, burial and candidate limits remain active.
- These are existing pebble and tuft meshes. No new vegetation species or independent decoration path is added.

**Confluence references and scope:**
- The user's two satellite views show different arrival angles, a pointed upstream land tongue and asymmetric banks. The second also shows exposed sediment bars. They are shape references; no scale or site identity is inferred from the cropped images.
- Angle and relative flow affect confluence separation, scour and deposition: [Best, 1987](https://doi.org/10.2110/pec.87.39.0027) and [Best, 1988](https://doi.org/10.1111/j.1365-3091.1988.tb00999.x). They do not prescribe one universal flare angle or symmetric widening.
- Field observations also link bed morphology to planform asymmetry, flow and sediment contributions: [Szupiany et al., 2009](https://doi.org/10.1029/2008WR007428).
- The current change matches physical sections. Confluence scour, sediment bars, seasonal exposure and sediment mixing remain unmodelled; adding identical decorative islands to every join would not reproduce those processes.

**Dry valley heads and receiving water, 2026-11-04:**
- A dry head multiplies both corridor width and incision by `smoothstep(0, 1, t)` from its origin to the trunk. The original mountain terrain returns as the incision vanishes.
- This treats existing fluvial extensions; an extension whose starting discharge is below the onset remains inactive. The shared discharge-growth rule above acts on actual upstream graph courses and is not restricted to these synthetic extensions.
- Neither rule replaces glacial cirques or adds new drainage links below the existing coarse graph.
- A lake or sea inlet opens by up to two nominal half-widths, capped at 600 m, over the last eight nominal half-widths before its cached contact. The approach begins at zero at the owning course part's start.
- The same approach lowers the channel stage to the receiving level and removes the closing dry-bank rise. High pre-erosion terrain cannot suppress this opening.
- Without a cached contact in the part, the previous low-bank fallback remains over eight channel depths of supporting elevation.
- Mouth widening and distributary spread share one aperture budget. They do not add two independent wide excavations.
- Corridor fill is zero below standing water and reaches full strength 50 m above it. Drowned banks cannot build dikes across a lake or bay.

**First-water contacts and surviving runoff, 2026-11-04:**
- `ErosionContacts.hlsl` samples the original course on a fixed 25 m substrate including ravines, wave erosion, barriers and volcanic finish, with river corridors explicitly disabled. A detected shoreline is refined by seven bisection steps.
- Wave erosion reads that same substrate before step-B incision. Its result meets the river envelope by a minimum; remapping an already lowered river floor created artificial marine pools and broke drainage-stage continuity.
- Probe spacing is at most 256 m on the nominal control-polygon parameterization. Sub-probe ponds and fine shoreline details remain a finite-resolution limitation.
- Four cached UNORM16 limits describe the main course's two halves, its rerouted connector and its terminal extension.
- The rendered course fades over a fixed 80 m beyond its contact. A box mean filters that physical termination; changing the footprint does not move it.
- A broken link stops its discharge contribution. Re-accumulation starts with the original local runoff, stored as a float; cumulative discharge bytes are never differenced to infer rainfall.
- The original largest-inflow geometry and meander-discharge field remain fixed. Only surviving width/depth and reach activity use the updated discharge.
- A contact in the receiving half still allows its source to reach the shared midpoint. Independent local sources and other tributaries survive.
- Both sides of that midpoint use the source's discharge. Averaging the now-disconnected receiver's local runoff into it caused premature upstream disappearance and an abrupt downstream restart. The existing interrupted-edge bit distinguishes these cases without additional cache storage.
- `EXOEROS6` stores 24 RG32 slices: 48 MiB at 512 cells per face, including 24 MiB for contact limits, discharge and local runoff.
- This follows the rendered level-0 courses. It does not reroute sub-threshold streams or generate a new outlet for a terminal lake.

**Low-coast distributary fans, 2026-11-04:**
- Marine terminal courses can open an explicit three-channel cross-section; terminal lakes never acquire this fan.
- Eligibility grows from 800 to 2,500 m³/s, fades over grade 0.002–0.01, and fades with terminal wall scale from 600 to 1,600 m.
- The fan begins with zero spread at the upstream join and continues opening through the terminal extension until its first-water contact.
- Contacts before the coarse sea node use the surviving course part's actual contact as the fan mouth. Very short runs lose eligibility over four to twelve nominal half-widths. The three branches share the centre course's stop; separate shoreline routing remains unimplemented.
- Maximum side offset is 14 nominal channel half-widths, capped at 1.8 km. A 2.4 km world field varies the two sides' offsets and discharge shares.
- Nominal discharge fractions are `1 - f/2`, `f (1 - 0.6 n)/4`, and `f (1 + 0.6 n)/4`. They sum to one; each branch has its own physical width, depth, bed and current.
- The three clipped wet intervals use exact inclusion/exclusion, including contained branches. Sorting centres did not sort their banks and could report dry coverage over the trunk's wet bed. Other overlapping courses retain the existing maximum-coverage approximation.
- The broadened low corridor shares the dry-support fill rule. No independent water triangle is painted over the terrain.
- **Calibration and limits:** three procedural branches, a coarse coastal-relief eligibility proxy and shallow fill are an initial landform model. They do not simulate sediment budgets, tides, avulsion, adaptive branching or resolved routes through the detailed shoreline.
- Reference distinction: delta shape depends on river supply, waves and tides ([NPS, Delta Landforms](https://www.nps.gov/articles/delta-landforms.htm)); branching distributes flow and sediment between channels ([USGS, Nelson et al. 2011](https://www.usgs.gov/publications/mechanics-flow-and-sediment-transport-delta-distributary-channels)). The engine coefficients above are not measured laws from those sources.

**Mouth scale references, 2026-11-04:**
- The user's Google Earth examples include large estuaries, tidal flats and distributary networks. Their outer water/sediment envelope is not the width of one liquid channel.
- **Gironde:** more than 75 km long and up to 12 km wide; low left bank and more relief on the right ([SMIDDEST](https://www.smiddest.fr/media/6742.pdf)). The Earth view confirms a long asymmetric widening, with islands upstream. The engine's local aperture cannot represent this reach.
- **Somme:** about 15 km long and 5 km wide at the bay entrance ([primary hydrology study](https://www.persee.fr/doc/jhydr_0000-0001_2009_act_31_1_5926)). A manual Google Earth ruler across the visible entrance gave 5,165.63 m, rounded to about 5.2 km; endpoint placement is approximate. The close view shows narrow channels inside broad banks and tidal flats. The regional tidal range is 9–10 m ([University of Picardie](https://www.u-picardie.fr/beauchamp/bds/bds-b.htm)).
- **Loire comparison:** one maritime section exceeds 3 km, including about 2.5 km of intertidal mudflat ([Nantes port assessment](https://www.nantes.port.fr/sites/default/files/medias/EES_PS-2021-2026_GPMNSN-VF_2.pdf)). Widening all of this into a deep river channel would misread the reference.
- **Current model:** `RIVER_MOUTH` opens only the final eight nominal half-widths, adding at most 600 m to either side; the owning course part limits its length. The regression witness opens from 173 to 484 m over roughly 700 m. This is a receiving-water connection, not a large estuary.
- **Required extension:** propagate receiving-water influence across upstream graph links in physical metres. Keep active channels distinct from shallow receiving basins and sediment flats. Condition the extent on valley confinement, receiving basin and coastal regime; do not apply a Gironde-sized funnel to every lake or mountain mouth. Tides and sediment evolution are not currently simulated.
- **Earth inspection:** separate reference tab; original user tab unchanged. Gironde camera about 116 km, scale bar 10 km; Somme cameras about 34 km and 2.6 km, with kilometre and hundred-metre scales. No scene coordinates enter production rules.

**Screen river evaluation, 2026-11-05:**
- The conditioned graph supplies exact activity predicates and conservative projected course bounds. The physical 24-slice map and its disk payload stay unchanged; twelve GPU-only slices add 24 MiB at resolution 512.
- Six mask slices index the original chart over [-3n, 4n), including repeated remapped candidates. Six node slices store eligibility and a bound covering every original main, head, outlet and connector rejection gate, with a floating-point reconstruction margin.
- Mesh, fine-grid and screen evaluation share this index. Unsupported layouts or searches outside its halo retain complete enumeration; no course is removed by viewing distance. Footprints wider than a level-0 cell read the rivers' map instead (below).
- Screen samples retain both physical parallax queries of the ground. At full screen weight, the rivers are queried once, at the point the river-free first query places; crossfaded with the fine grid, both queries keep them (`spec-rendu-lointain.md`). Ground preparation, bounded enumeration, node evaluation, reduction, complete overflow fallback and finish preserve composition order.
- Only potentially contributing nodes enter the work queue. Each accepted query owns a contiguous result range; stage and flow are normalized after reduction. Overflow queries use a packed indirect dispatch of the complete evaluator.
- Large sparse searches process chart tiles across cooperating lanes. A conservative sphere covers each tile's remapped, jittered nodes; reject it only when the original node gate rejects every enclosed point. Original tile/bit order is preserved.
- Before enumeration, intersect the original rectangle with the spherical cap implied by that same node gate. Include half-texel remapping, bounded jitter and floating-point slack. Keep the rectangle when the cap reaches the chart horizon; preserve repeated remapped nodes.
- Four adjacent lanes reduce each screen query. Empty and singleton ranges use one reader; larger ranges retain all max/min fields and normalize wet moments only after combination. Floating-point wet sums may differ from serial order.
- Scratch capacity is at most 4,194,304 nodes: 256 MiB for tasks and results, plus 12 bytes per screen texel for ranges and fallback IDs. The reservation bound follows the current texel count, preventing 32-bit overflow without a fixed node cutoff.
- Screen ground work remains 172 bytes per texel; the final sample remains 64 bytes. Buffers grow with the actual view. No lower resolution, narrower filter or approximate motion reuse is introduced.
- A missing screen stencil at the limb uses filtered mesh/fine water. It cannot restart a full contour query per fragment; that path caused the reproduced hemisphere GPU timeout.
- Exact zero-weight noise, dry confluence metadata and zero-result section pruning remain. Completely filtered spur/noise terms and integration intervals outside compact section support require no evaluation.
- Merge four sorted lists of wall/bank transitions instead of sorting and dynamically indexing sixteen edges. Keep every positive interval, its four-point quadrature and accumulation order. Sort the radii even when a wide belt exceeds the capped outer wall.
- Native index checks cover all 77,070,336 halo bits, 1,572,864 predicates and 1,800 searches including face seams. Independent projected-bound checks retain 1,069,632 original curve/connector gates.
- Tile spheres enclose all 77,070,336 remapped chart nodes at resolution 512, with complete smaller-resolution checks. The distant-globe before/after images and native fields match exactly.
- `verifie_fenetre_rivieres.py` retains every accepted node in 111,963,012 chart candidates across 120 face/interior/seam/corner/footprint cases. `verifie_partition_rivieres.py` preserves all positive intervals on 100,000 sections, including 8,872 inverted capped walls.
- Native scheduling comparisons include odd dimensions and forced zero/64-node capacities. The original pre-index strict field comparison still fails on small compiler-level differences; do not claim bit identity for the complete optimization.
- Moving-camera FPS, image differences, material quality results and review state are in `diagnostic-orbite.md`. Raw screen captures use `MYPLANETENGINE_SCREEN_DUMP=1` and `tools/hydro/verifie_relief_ecran.py`.
- Review route: `tools/tests/2026-11-05-orbite-correction.txt`. Rejected schedules and earlier precision claims are archived in `log/spec-erosion-historique.md`.

**Wide footprints read a startup map, 2026-11-05 night:**
- **Why:** from 10,000 km, mesh vertices, limb samples and distant texels each enumerated hundreds of courses, for an effect the image no longer resolves. Erosion on and off differed there only by the terminal lakes.
- **The map,** `ErosionRiverMap.hlsl`, once at startup after the activity index: six GPU-only slices of `t23`, one per face, 504² cells of about 25 km, padded by 4 texels with the field past each edge. 12 MiB.
- **Each texel:** the complete evaluation at its direction, filtered over one map cell, on the ground the rivers are drawn on. Its channel beds are folded into the ground change as `ReliefFinishGround` composes them, coast and finish aside (`ErosionRiverFold`). Stored as halves: ground change, wet cut, wet fraction, stage.
- **Reading:** cubic B-spline, faces blended near their edges, as the tectonic map. The stage is weighted by the wet fraction. Terminal lakes are still read directly.
- **Which footprints:** from a sampling radius of one map cell, blended into the map up to √2 cells; the map alone beyond. There, one cell's box and the B-spline's cell filter as widely as the direct evaluation. Below one cell, the courses as before.
- **The fine grid's limb samples** under a full screen relief filter their rivers at the reading texel's footprint, as the screen relief does (`FineLimbFootprint`, `FineTerrain.hlsl`). Only limb pixels read them; their own cell, seen edge-on, was about 11 km at 10,000 km.
- **Not carried:** current and dry-bank proximity; channels are far narrower than the map's cells. A footprint holding water is a candidate at zero distance.
- **Limits:** a footprint much wider than √2 cells sees the map sharper than its own box would. At 10,000 km the mean incision is unchanged (−4.4 m), its rms 23 m instead of 15 m. The CPU port still evaluates the courses at every footprint.
- Only frames with constants read the map (`erosionMode.z`); startup passes, their caches and the disk payload are unchanged.
- Results and image checks: `diagnostic-orbite.md`.

**Courses built at startup, 2026-11-07:**
- **Why:** each node task rebuilt its node's courses from its neighbours, its connectors' junctions by a meander each: 2 to 3 ms at 97 km and 2,200 m.
- **`ErosionCourseBuild.hlsl`,** after the activity pass: each eligible node's main course, then its connectors in neighbour order, their controls relative to the node, their corridor and channel reaches; `ErosionCourseRecord`, 176 bytes, at `t60`. About 80,000 courses, 14 MB.
- **Index:** the eligible node's word, slice 30 + face, x: `1 | first << 1`; the activity pass writes its connectors' count there first. Magic `ERI4`.
- **A junction's meander at full detail:** a confluence stays where it is, whatever the footprint; formerly filtered with the query. The CPU port still filters it.
- Startup passes before the build keep the former construction.

**Shared listings, 2026-11-07:**
- **`EROSION_WAVE_LIST`:** the screen relief, fine grid, mesh, plants and the pixel's channel rung list the union of a wave's windows once, one node per active lane by rank. Each lane then gates the nodes in its own window's order: the same sums.
- **No margin for helper lanes:** a compute wave has none; a pixel's take no derivative of the rivers' fields, only of the lake's level, read apart. The union is the active lanes' windows, the reach their spread and widest footprint.
- **The listing hands over each kept node's word and bound:** no lane reads them again. Each lane computes the node's position itself: shared, its last bits differ from the listing's own computation, and contraction disabled to share it cost more than it saved.
- The pixel's whole relief does not list by wave: its helper lanes feed the ocean's derivatives (`gErosionWaveList`).

**The contour's nodes, 2026-11-07:** the node word (slice 30 + face, x): bit 0 eligible, 1 to 18 its first course (`EROSION_FIRST_MASK`; startup refuses more than 262,143 courses), 19 to 30 its channels' reach, 31 its wetness.
- **Wet:** one of its courses can carry a channel: not dry, its discharge past `RIVER_Q.y` somewhere, its controls bounding its curve's (`ErosionCourseWet`). An outlet's line, if its main course's last discharge is.
- **Channels' reach:** the farthest its wet courses' hulls lie from the node, plus their channels' reach, in 32 m, rounded up; 4095 for none within 131 km.
- **`ErosionCourseWet.hlsl`,** once after the courses are built, completes the words. The water contour (`gErosionWater`) lists no dry node, skips dry courses before their geometry, and gates wet nodes by their channels' reach. Exact: a dry course returns before any field.
- **The fine grid's near nodes:** each sample records up to three wet nodes whose channels' edge came within 3.5 of its cells and 50 m (`gErosionNearReach`), as offsets from its cell, in `flow.w`. The pixel's channel rung evaluates its four samples' nodes alone, in the listing's order (`ErosionRiversNear`); a sample that recorded more, or none, or a face's edge, falls back to the listing. The reach covers the pixel's offset from its nearest sample, its footprint and the meanders' octaves finer than the sample's. Images identical but for 45 pixels within 1/255 at a lake, the nodes' positions computed at another site.
- **Mesh rivers from the map** under a full screen relief, for cells of a quarter map cell and wider (`TerrainCompute.hlsl`): the rung above their own footprint, for depth, silhouette and the sun's horizon.

**The pixel contour reads the channels alone, 2026-11-06:**
- **Why:** the pixel's water contour evaluated every course whose valley reached it, to place a channel narrower than the grid's samples. The grid resolves the valley.
- **`gErosionWater`:** set by the pixel shader around its channel rung (`spec-eaux-interieures.md`). `ErosionCourseReach` drops the corridor; `ErosionCorridor` skips a course whose channel cannot reach the point, before its meanders, and draws no corridor or bed.
- **Exact:** the width bound covers every branch, the fan's spread included, whatever the branch's share of the discharge. Wet fraction, stage, cut, current and positive edge equal the full query's: `verifie_contours.py`, `water_rung`, 320 points within 1.5 km of the massif's channels. Courses evaluated per point: 2.4 to 1.1.
- **Not carried:** ground change, bed, dry-bank proximity and the distance outside the channels.
- **Not done:** the node bounds keep the valley's reach. A channel bound per node would remove 30 % of the nodes prepared, 4.9 to 3.4 per point.
- The CPU port mirrors it: `cp.WATER`.

**Retained geometry verification, 2026-11-04: receiving-section confluences**
- Release x64 succeeds through `tools/lance.ps1 -Build -NoLaunch`: `x64/erosion-confluence-flow-banks-build.log`. Existing material-shift and atmosphere-division warnings remain.
- `verifie_raccords.py` checks 240 physical sections at four arrival angles and four width ratios, on both sides and through zero opening. Equal-width arrivals add no bulb; the upstream bank and short-connector start stay unchanged. Bed, wet support and the shifted section agree.
- Local-flow orientation passes on 584 planetary connectors. Twenty-four nearly parallel arrivals have attenuated openings; three require the opposite side from the coarse heading. This is a geometry regression, not a performance benchmark.
- On 256 planetary nodes, all control points, stages, discharges, contact parameters and fan controls match the pre-change source exactly. Independent runoff accumulation still agrees on 1,572,864 nodes and 19,033 stopped links.
- All 512,980 receiver links retain monotone stages and the 3% grade bound. All 454 sampled wet cap points stay below the cap plus fill. Original-terrain and legacy-network identity pass: `x64/erosion-confluence-banks-core.log`.
- Approach, upstream, morphology, mouth, head and bank-filter regressions pass: `x64/erosion-confluence-flow-banks-verifie_*.log`. Physical search reach stays within 14,093.5 m. The reported mouth retains its 173–484 m aperture and 257 successive wet samples.
- Continuity passes 36 edge lines, 36 joins and ten confluence lines across three regions. Largest sampled ground refinement ratio is 0.28; largest sampled water step is 0.012 m. The existing 0.10 m dry-notch refinement remains continuous. Logs: `x64/erosion-confluence-flow-banks-continuity-*.log`.
- Final native cache payload matches the pre-change payload byte for byte: SHA-256 `c13c3cc07c544a81f70e30b94a4c9f2bbbffc1642d4d4ed549c6031c524fb108` after the 24-byte header. The geometry change requires no new graph, stage or contact data; log `x64/erosion-confluence-flow-banks-native-cache.log`.
- Seven final native views inspected in `distance-confluence-flow-banks-final/`: F1/F2 at two distances, F3 another confluence, F4 the local-turn witness, F5 the retained mouth, F7 the lake, F9 the orbital massif. The round protrusions are removed in F1–F3 and the upstream land tongue is retained. F4 remains a very thin feeder into a much larger river; this is not a sediment-shaped confluence.
- The mouth stays connected. The pre-existing straight lake-stage boundary and repetitive orbital corridors remain visible in F7/F9. No temporal capture was repeated for this bank-only change; approach filtering is checked by the CPU section, footprint and wet-moment regressions.
- Before captures F1–F3 are in `distance-confluence-banks-before/`. Intermediate coarse-heading renders are archived in `distance-confluence-banks-coarse-heading/`; they are not the final review version.
- Remaining work: confluence sediment bars and scour; orbital corridor repetition and fine tributary hierarchy; long estuarine basins, independent distributary contacts and lake-stage boundaries. The current bank correction does not implement those processes.
- The coastal-talus test's inactive historical witnesses remain documented in the erosion log; this confluence-only change does not modify that subsystem.
- No performance or image-quality benchmark, commit, tag or push. Flight review remains pending.

**The terminal lakes** fill every hollow below their stage within their catchment, as before, connected or not.

**Review:** `tools/tests/2026-11-04-confluents.txt`; F1/F2 inspect the same confluence at two distances, F3 another confluence, F4 a nearly parallel arrival in another region, and F5–F12 retain mouth, fan, lake, mountain and approach witnesses. These refinements await flight review.
- Interactive Release engine relaunched on F3's pose with the route, clouds hidden and windowed palette. Responding and rendering verified at 14:54. Backspace leaves the initial cockpit; F3 restores the exact pose.

## The `valleys` flag

**`ReliefElevation(p, true)` renders eroded terrain; `(p, false)` the pre-erosion form,** without any level, the one level 0 reads. Level 0 never reads its own outputs.
- The third argument controls step-B courses independently. First-water contacts use `(p, true, false)`: ravines and the finished coast remain, while the probing river is absent.

## Connections

**With climate:** `ErosionClimate` returns P in m/year, annual precipitation from cube 0 divided by 1 000, and annual sea-level T in °C.
- **CPU:** `CreateTectonicMap` calls `CreateClimateMap`, which keeps `mClimateCpu`, then `CreateErosionMap` and `Erosion::Build`; no loop, climate always reads the pre-erosion form.
- **GPU:** `ClimateAt` reads t20; terrain, fine-terrain, planet-map and placement passes keep their t18–t23 table, with linear sampler s4; erosion remains t23.
- **The port:** `erosion_climate` and `erosion_wave_wind` read `cp.climate(p)`.
- **The equilibrium line:** Ohmura relation, fixed summer correction of 8 °C, lapse rate of 6.5 K/km and glacial lowering of 900 m preserved; no new formula or recalibration of the glaciated share. Computed half-amplitude is not used here.
- **Measurement limit:** the network's glaciated share is not remeasured here; the port does not rebuild level 0.

**With volcanism:** its edifices add to the pre-erosion form, `ReliefElevation(p, false)`. Level 0 sees them if they exceed 40 km; below that, gullies dissect them like any terrain. `ReliefDetail` gains two parameters, gullies and coarse sum.

**Visible water:** rivers use link discharge and stage; terminal lakes use their water-balance level. The shared channel envelopes, basin transitions, rendering and limits are in [inland water](spec-eaux-interieures.md).

## The CPU port

**`tools/hydro/cp.py` reads the engine's level 0,** `erosion-<graine>.bin`, and reconstructs valleys, deposits and gullies; nodes in float32, like the shader. `EXOLUNE_EROSION` gives another path.
- **Step B:** `erosion_rivers` mirrors `ErosionRivers`, each node's courses built once in planet coordinates; `river_startup` mirrors the startup passes and `Erosion::Condition`, for a cache written before step B or to check the engine's.

**Comparing terrain variants:** `python tools/hydro/etude_relief.py`.
- Six sites, the wet plateau added on 2026-11-03; windows of 40 km, 10 km, 2.5 km and 600 m, 256 samples, octaves filtered at the sample spacing.
- One sheet per site in `x64/etude-relief/`: rows are variants, columns are window sizes; metrics in `<site>.json`.
- Metrics: detail energy, share in closed pits deeper than 2 m, wet share, wet runs longer than 10 samples.
- A new variant is one function decorated with `@variant`; `--sites`, `--variants` and `--samples` narrow a run.

## Current verification, 2026-11-01

**Far valleys, 2026-11-02:** `python tools/hydro/verifie_vallees_lointaines.py`.
- 525 sections against an independent quadrature of the clipped mixed section: maximum error 3.2e-7 m.
- Area of the incision kept for radii from 2 m to 20 km: relative error below 4e-9.
- Continuous in distance, radius and ground height.
- At the 2 m minimum radius, the clipped mean equals the former result to 1e-13 m.
- Five terrain windows: heights change by at most 0.17 mm at 1 m and 0.25 m spacing, 0.10 m at 16 m.
- `verifie_composition.py` now bounds the cut by the lowest clipped section mean instead of the averaged envelope; it and the other existing checks pass.
- Flight route: `tools/tests/2026-11-02-vallees-orbite.txt`; validated in flight by the user on 2026-11-02. No performance or quality benchmark was run.

**Scope:** working corrections on the public-history erosion branch in `Exolune`.
- `verifie_lames.py` compares with public replay `7187c1b`.
- `verifie_auges.py` now uses public replay `7c9f475`; no legacy Git history is imported.
- Earlier closure measurements and their failed quality threshold are [archived](log/spec-erosion-historique.md#2026-11-01-archive-worktree-closure).

**Approach mutation:** the snowy pose was recovered from the running engine during the report.
- Pose: `4096.4 -46.85004 -33.85772 31.9 -63.4`; second view 31.4 m lower.
- The former filter scaled the entire valley by its intersection with coarse reference ground.
- Near zero reference depth, changing the mesh moved distant planar banks by hundreds of metres.
- The new filter averages the physical cross-section locally; it does not scale its coordinates or its floor mask.
- In a fixed 4 km window, changing mesh spacing from 1 to 4 m moves terrain by at most 1.06 m, previously 220.85 m.
- At 16 m spacing, the maximum is 9.55 m, previously 417.73 m; filtered terrain still changes with resolution.

**Targeted checks:** no performance or quality benchmark was run for these working corrections.
- `python tools/hydro/verifie_filtre_vallees.py`: 240 profile samples against independent piecewise Gaussian quadrature; maximum error below 6e-12 m.
- Checks cover zero reference depth, unchanged distant planar banks, bounded rise and an analytic derivative.
- Three fixed terrain windows cover the reported snowy approach, a snowy trough and a tropical trough.
- Mesh spacing of 1 and 0.25 m gives identical heights in these windows.
- The existing profile, curve and endpoint checks pass; the four blade regressions still pass.
- Release x64 builds through `tools/lance.ps1 -Build -NoLaunch`.
- Two native captures retain the snowy cliff's main form through the descent; this is a local visual check.
- Review route: `tools/tests/2026-11-01-mutations.txt`; F1/F2 are the snowy pair.

**Open cases:** the green disappearing scar has no recovered exact position yet.
- A nearby coastal witness is not that screenshot's position.
- At `8.48997 -103.55646`, changing mesh spacing from 1 to 16 m changes height by 45.19 m.
- The cliff remap amplifies a 3.87 m change in its input height; its width parameter is unchanged there.
- The physical coastal metric correction does not alter this witness; the nearby captures do not reproduce the reported zigzag scar.
- Useful gully amplitude, distant repetitive drainage and the previous quality failures remain unresolved.

## Known defects

- **Hydrological integration remains incomplete:** coarse paths and repeated valley profiles can dominate fine mountains and cut volcanic bowls whose outlet the coarse map does not resolve.
- The composition correction removes a demonstrated source of false side trenches; it does not validate the distribution, age or connectivity of all incisions.
- A cap from coarse network incision alone was rejected because its reference heights differ from the rendered support; stage and route reconciliation must come first.
- Volcanic freshness currently quiets detail and controls bare materials; the drainage solve does not directly use it to limit incision.
- The new flight route `tools/tests/2026-11-01-composition.txt` includes river banks, confluences, mountain ranges, two craters, an outlet, a lake and a coastal witness.

- **Flight feedback from 2026-11-01 invalidates a conclusion of clean geometry:** thin blades, spikes and sawtooth joins remain in the captures below, despite CPU checks passing on their samples.
- **Previous quality failures remain open:** the archived closure recorded thirteen texture p95 regressions; this working correction has not rerun that benchmark.
- **Gullies now follow actual incision:** slopes no longer lose their coarse support before the decision. Some unincised crests lose version E's artificial bands; their shape awaits in-flight review.
- **Glacial floors:** the U remains curved, with continuous joins in the checked cases. Hillside hollows remain. Rivers and terminal lakes now have a first visible-water implementation (`spec-eaux-interieures.md`).
- **Level 0 valleys remain regular at large scales:** the U corrects the glacial floor; convex-concave fluvial slopes and truncated spurs remain to build.
- **Deltas are small, and one is false:** at most 5 km, the reach of nodes read; at the largest river mouth, -7.8°, 27.2°, an isolated depositional tongue offshore, cause not found, and a straight-edged coastal section unrelated to deposits. Large deltas require a deposit field read in B-spline.
- **Gullies may be barely visible from afar:** their amplitude is now bounded by the supporting ground; the two octaves above 20 km retain their crests oriented along ranges.
- **Cost:** earlier flight measurements are archived; the current filter adds no terrain query or simulation, and its runtime cost has not been benchmarked.
- **Rivers on flanks remain parallel and straight over 50 to 100 km,** on regular slopes: the pre-erosion form filtered at 40 km has no terrain to divert them there.
- **Cliffs are absent where the real shore lies more than 8 km from its estimate:** the active coast at -8.11°, 131.04° has none; the cap bounds cost.
- **Cliffs are visible only within a few km:** from 30 km, the platform is only a turquoise band; the wall at 23° S remains low, 42 m.
- **The sea probe rereads pre-erosion terrain where a cut is possible:** its GPU cost was not measured by benchmark, only within the noise of renders in motion.
- **The twelve current views** await in-flight review with `tools/tests/2026-11-01-auges.txt`; previous stages retain their old route.

**Continuation captures supplied by the user**
- The five originals are preserved without retouching in `images/erosion-2026-11-01/`.
- Heights are those of the title bars; camera coordinates are unreadable in these truncated titles.
- [11:57:24, sawteeth](images/erosion-2026-11-01/115724-dents-de-scie.png): height 40.1 m, ground around 3.8 km; long rows of points on several slopes.
- [11:57:33, thin wall](images/erosion-2026-11-01/115733-paroi-mince.png): same height; high-amplitude blade rising on the slope and a comb in the distance.
- [11:57:55, blades](images/erosion-2026-11-01/115755-lames.png): height 61.7 m, ground around 1.9 km; very thin walls and spikes, including in wooded areas.
- [11:58:16, spikes](images/erosion-2026-11-01/115816-aiguilles.png): height 78.9 m, ground around 3.5 km; many peaks on a steep rim and jagged joins.
- [11:59:12, distant patterns](images/erosion-2026-11-01/115912-motifs-lointains.png): height 417.5 km; parallel valleys, overly regular spacing and curves in some regions.
- The screenshots alone do not identify the cause. Subsequent CPU probes reproduce blades in the height field and isolate the rock-gully budget exception; see the regression checks above.
- The active continuation is in the Exolune clone on the replayed erosion branch. Review the blade and valley-filter corrections in flight; recover the green scar position before declaring the approach artifacts resolved.

## What the research taught us

Branch `erosion-niveaux`, `docs/recherche-erosion-niveaux.md`:
- **a global level 0, computed once, works** (spikes A3): full drainage, lakes by water balance, basins from 1 to 9 million km². Reused here, including its water balance;
- **simulated erosion by tiles is chaotic** (spike B): 43 m mean difference between tiles and a single-block calculation, up to 2 km. Fine levels are therefore a local construction;
- **paths chosen on 25 km cells send rivers through mountains** (finding of 2026-10-27): 44 % of their length carved more than 50 m below ground. Hence: coarse ground is lowered to the valley rather than cut, the valley has slopes, detail fades on its floor;
- **what is not reused:** uplift invented from heights, stepwise erosion, 10 minutes per seed, tiles computed on approach.

## Sources

- Selby, *A rock mass strength classification for geomorphic purposes: with tests from Antarctica and New Zealand*, Zeitschrift für Geomorphologie 24(1), 31–51, 1980; Augustinus, *The influence of rock mass strength on the form and evolution of deglaciated valley slopes in the English Lake District*, Scottish Journal of Geology 38(1), 15–20, 2002.
- Grieve, Mudd, Hurst, *How long is a hillslope?*, Earth Surface Processes and Landforms 41(8), 1039–1054, 2016, DOI `10.1002/esp.3884`.
- Roering, Kirchner, Dietrich, *Evidence for nonlinear, diffusive sediment transport on hillslopes and implications for landscape morphology*, Water Resources Research 35(3), 853–870, 1999, DOI `10.1029/1998WR900090`.
- Barnes, Lehman, Mulla, *Priority-Flood: An Optimal Depression-Filling and Watershed-Labeling Algorithm*, Computers & Geosciences 62, 2014.
- Kirby, Whipple, *Expression of active tectonics in erosional landscapes*, Journal of Structural Geology 44, 2012.
- Tzathas, Gailleton, Steer, Cordonnier, *Physically-based Analytical Erosion for fast Terrain Generation*, CGF 43(2), 2024.
- Ohmura, Kasser, Funk, *Climate at the equilibrium line of glaciers*, Journal of Glaciology 38(130), 1992.
- Tricard, Efremov, Zanni, Neyret, Martínez, Lefebvre, *Procedural Phasor Noise*, ACM TOG 38(4), 2019.
- Fairfield, Leymarie, *Drainage networks from grid digital elevation models*, Water Resources Research 27(5), 1991: rho8.
- Sunamura, *Geomorphology of Rocky Coasts*, Wiley, 1992: wave force and rock resistance; cumulative distance parameterized here, without time simulation.
- Trenhaile, *The Geomorphology of Rock Coasts*, Oxford University Press, 1987: low-slope abrasion platforms.
- Gaillard, Guérin, Galin, Peytavie, Paris, *Dendry: A Procedural Model for Dendritic Patterns*, I3D 2019: read, rejected for its per-vertex cost.

## The staged plan

| Stage | Content | Status |
|---|---|---|
| 1 | Level 0 at startup, its texture, link valleys | done on 2026-10-31 |
| 2 | Gullies, knickpoint retreat, fans and deltas, port | done on 2026-10-31 |
| 3 | Cost: float positions, cache per seed | done on 2026-10-31 |
| 3 bis | Gully blades and tears, continuity of detail inputs, weighted routing, port within 0.6 cm | done on 2026-10-31 |
| 3 ter | Cusp-free arêtes, computed rainfall, temperature and wind; climate cache key | done and render approved by the user on 2026-10-31; new network delivered |
| 3 quater | Critical-slope gullies, zero mean and underlying noise preserved | soils approved by the user; arêtes revisited in E |
| 3 quinquies | Floors joined to water, rock bound at 70° | done in D; limitations revisited in E |
| 3 sexies | Gullies by rock and scale; warped directions on the sphere | code and CPU checks done; flight review pending |
| 4 | Continuous U profiles, warp without folding in checks, supporting terrain preserved | stage frozen; CPU checks passed, geometry invalidated in flight by blades and spikes; thirteen p95 failures |
| 4a | Shared gully slope budget and local valley-profile filtering | CPU checks and snowy approach captures pass; user flight review, green scar and coastal mutation remain open |
| 4b | Connected talus and physical coastal metric | Profile and six terrain checks pass; native captures remove the reported false wall; wider straight incision and approach sensitivity remain open |
| 4 bis | Convex-concave fluvial slopes, truncated spurs | to do |
| 5 | Large deltas, through a deposit field | to do |
| 6 | Water from the same river and lake network | first implementation, 2026-11-01; flight review and limitations in `spec-eaux-interieures.md` |
| A | Ravines on the pre-erosion form, the network's drawing off | geometry accepted in flight according to the 2026-11-03 handoff |
| B | River corridors from level 0, `tools/hydro/couloirs.py` | first version reviewed in flight; discharge sizing and composed-water correction awaiting flight review |
