# Spec: global erosion

Status: living spec, since 2026-10-31, branch `erosion-globale`, experiment `piste/erosion-globale`. It starts from the tectonic stack (`spec-relief-tectonique.md`); research on branch `erosion-niveaux` is only a source (section “What the research taught us”). Current route: `tools/tests/2026-11-01-auges.txt`; previous stages remain in `tools/tests/2026-10-31-erosion.txt`.

## The objective

**Rivers and glaciers form one system, from the planet to 100 m detail.** Mountain ranges show branching transverse valleys, arêtes, buttresses and a continuous divide; folds remain in the foreland; all rivers reach the sea or a lake.

## The architecture

**Three levels, one network.** Level 0 decides where water flows and at what height; valleys and gullies only draw it, in increasing detail, attached to it.

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

## The `valleys` flag

**`ReliefElevation(p, true)` renders eroded terrain; `(p, false)` the pre-erosion form,** without any level, the one level 0 reads. Level 0 never reads its own outputs.

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
