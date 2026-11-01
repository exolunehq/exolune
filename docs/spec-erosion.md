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

**Terrain and water come from the same data (research rule R5):** valley floors, lakes and later river water all read this texture.

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
- Width is measured at the exact intersection of the profile and its reference ground.
- A valley narrower than two grid cells widens; its depth and entire vertical section shrink in inverse proportion.
- This transformation preserves the incised cross-section area; the old formula did not contract the whole profile and could leave a U narrower than two grid cells.

**Combining valleys**
- The surface is the minimum of the profiles; each already carries its own drained level.
- The geometrically closest link's level no longer bounds another link's surface.
- The slope guiding gullies blends over 60 m between competing profiles; it no longer jumps when the link changes.
- The cutting surface receives slope detail, progressively suppressed on the floor.
- This surface then cuts the full terrain: `depth × smoothstep(0, 60, depth)`.
- Incision never raises a hollow; suppression controlled only by the coarse support could raise a rim several hundred meters high.
- An initial hollow below the profile remains; filling it belongs to deposits or lakes, not this cut.
- At overlaps, a point on the old axis may belong to the slope of a lower valley; its ground follows that profile, not an independently selected water level.

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

**Two ground types, two scales, one continuous blend (`ReliefGullyRock`, `ReliefGullyGain`):**
- **Soil and scree:** `Sc = 1.25`, Roering et al. 1999; below 300 m wavelength and outside ranges, C's conservative budget remains intact.
- **Transition to rock:** from 300 m to 1 km, physical `smoothstep`, never mesh spacing. [Grieve, Mudd and Hurst 2016](https://onlinelibrary.wiley.com/doi/10.1002/esp.3884), *How long is a hillslope?*, measure median hillslope lengths from 98 to 228 m; the 300 m–1 km range is our progressive separation between these hillslopes and mountain-scale incisions, not a universal constant from the article.
- **Rock presence:** `r = mountains × smoothstep(600, 1400, relief) × smoothstep(0.3, 1, wavelengthKm) × (0.8 + 0.2 glacial)`. `relief` is the amplitude in meters passed to detail, `mountains` the existing range share; the equilibrium line reinforces rock, it is no longer its only evidence. Never `valley.glacier`.
- **Rock strength:** `Sc = tan(70°)`, strong-rock choice within Selby 1980's framework, retained from D. Finite crest rounding and its mean do not change.
- **Shared saturation:** for supporting slope s, ordinary-octave reserve N and band reserve G, `L = max(Sc − s − N, 0)`, `B = L²/Sc`, `gain = B / sqrt(B² + [share × (N + G)]²)`; C1 join at zero reserve.
- **On the mantle:** N and G retain C's conservative bounds, noise gradient 26 and curvature 512, including band weights and bifurcations; physical 2 m rounding bounds reversals.
- **In broad rock:** reserve at octave scale: N is amplitude × frequency, G the finite sinusoid's slope, `2π × stripeScale × amplitude × frequency`, including sharpening. Keeping 2 m reversal bounds for a kilometer-scale incision canceled its bands even at `Sc = tan(70°)`.
- **Scope of this rock threshold:** characteristic slope at octave scale, not a cap on all local slopes after orientation; local walls exceed 70°, like the preserved noise and valley profiles. The mantle retains its conservative pointwise bound.
- **The blend:** `share × lerp(gainSoil, gainRock, r)` replaces only the pattern; it does not reduce ordinary noise when the reserve is exhausted. Gain and rock share do not read the current phase; noise and band remain separately centered.
- **Cost:** no neighboring terrain read or new octave for the budget; same bands, scalar saturation. Stack cost is measured below; this budget's cost alone is not isolated.

## Coastal cliffs

**Abrasion follows a full-ground contour, including detail, valleys and deposits.**
- **Where:** `ErosionCoast`, after deposits and before coastal barriers, only with `valleys = true`.
- **The estimated shore bounds reach:** it no longer places a wall in the mountains.
- **The contour:** `Hc = clamp(1000 W G, 8, 400)` m; ground above `Hc + δ` remains identical.
- **Width W:** 1.2 km × exposure × erodibility, at most 3 km; 45 % variation through 2.4 km noise (Sunamura 1992, force over resistance).
- **Slope G:** tangent magnitude of large shapes and the three detail octaves above 9 km, before gully limiting on mobile soils; coastal slope `coastSlope × shoreMetric / 1000` remains a floor.
- **Why 9 km:** three times maximum retreat; the 50, 23.7 and 11.2 km octaves retain large slopes without letting small spurs move Hc.
- **One terrain evaluation:** `cliffSlope` comes from the main `ReliefDetail` and its three octaves above 9 km; no recalculation or off-sphere read to freeze Hc. The projection parameter is removed: valleys are always read on the sphere.
- **The 400 m cap:** calibration near the 426 m Conachair cliffs listed by [NatureScot](https://www.nature.scot/landscapes-and-habitats/habitat-types/coast-and-seas/coastal-habitats/coastal-cliffs), without a universal geological maximum.
- **Capes and coves:** hard rock and shelter reduce W and the contour; soft rock and exposure increase them.

**The profile remaps height h.**
- **Below Hc:** `min(h, P)`; P is −1 m at the foot, then descends linearly with h toward the old shore.
- **The platform:** nominal 2 % slope over W, height difference capped at 4 m (Trenhaile 1987).
- **Under the sea:** continuous join to the same line; deeper ground remains intact.
- **The face:** transition over `δ = max(0.1 Hc, 2000 cellKm G)` m; if narrower than two grid cells, it widens and tilts.
- **Lowering:** at most `Hc + 1 m`, even on a coarse grid; no ground raised.
- **Scree:** 35° slope, up to 22 % of Hc, in 900 m patches; distance to the foot expressed by `abs(h − Hc) / G`.
- **Stacks:** rare intersections of 130 m bands preserving the original ground; widened over two grid cells, reduced in proportion to their area.
- **Rivers:** low floors can pierce the contour and become sea inlets.

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
| `SLOPE_KM` | `9` | threshold for slope-carrying octaves, km; formerly 0.3 |
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

**With water, later:** rivers are drawn from link discharge and water level, lakes from their level, fjords and estuaries where valleys pass below the sea.

## The CPU port

**`tools/hydro/cp.py` reads the engine's level 0,** `erosion-<graine>.bin`, and reconstructs valleys, deposits and gullies; nodes in float32, like the shader. `EXOLUNE_EROSION` gives another path.

## Verification on 2026-11-01

**Reference:** `14c99ec`, the last state of “Global erosion: rivers and glaciers”.

**Move to the public repository**
- This stage is frozen in local worktree `claude/erosion-globale-b42982`, now an archive; no push of this branch or its old ancestry.
- Work continues in `C:\Users\etien\Documents\repos\Exolune`, after the coordinating session transfers changes onto public `main`.
- `verifie_auges.py` still loads the reference port through `git show 14c99ec:tools/hydro/cp.py`; this control must be adapted to the new clone without importing the old Git history.
- Captures, caches and raw reports remain in the local archive's `x64/erosion-2026-11-01`, outside Git; this assessment, checks and flight route are versioned.

**Checks performed**

- `python tools/hydro/verifie_auges.py`: profiles, curves, four soils, two glacial windows, 200 joins and six traces on seeds 0 and 1.
- Eighteen sections check two-grid-cell width and area conservation; integration error below 0.001 %.
- Curves are compared against all roots of their distance polynomial; 500 cases, maximum error below 10⁻⁸ radius.
- Source and outlet parameters are checked at 804 positions; distance alone did not detect their width jumps.
- Ten thousand random sections check that suppressing detail raises no hollow.
- On 4 010 points across both seeds, the coarse support is bit-identical with erosion on or off.
- On the 3 908 points outside incisions in this sample, detail before cutting also remains identical.
- The 840 crossings of face boundaries or read-window boundaries give zero residual height jump; residual guiding-slope difference below 0.0005 m/m.
- The six traces cover 11 to 23 km each; no residual detail on incised floors.
- Overlaps explain differences from the selected link's water level up to 16.12 m; river water is not rendered and its future connection must follow the actual winning surface.
- Noise without erosion remains bit-identical in the four soil windows.
- The rendered level 0 network, seed 0, retains every texel bit-identically against `14c99ec`; only the executable-dependent cache key changes.
- Sections resolved at 1 m and 0.25 m are identical.

| 4 km window, seed 0 | Before | After |
|---|---:|---:|
| First trough: surface within 10 cm of water level | 31.60 % | 0.47 % |
| Second trough: same measure | 33.53 % | 0.96 % |
| First trough: largest local depression | 57.50 m | 23.88 m |
| Second trough: largest local depression | 65.79 m | 15.40 m |

- Remaining depressions in these windows lie outside the checked floor; an open-edged square does not measure full basin drainage.
- Maximum slopes of the four soils are 30.65°, 22.58°, 47.27° and 4.61°; the mantle threshold is `atan(1.25) = 51.34°`.
- Angular deformation is checked on 200 000 directions, two seeds: 12.87–12.91 % negative Jacobians at 7 km, none at 2 km; minima 0.181 and 0.231.
- Local results in `x64/erosion-2026-11-01/geometrie-finale.json`.
- Release x64 built; twelve views rendered without a window in `x64/erosion-2026-11-01/apres-native`.
- The quality benchmark completes on the twelve sites; thirteen p95 values out of 47 comparable exceed those of `14c99ec` by more than 10 %.
- The acceptance criterion remains unmet; this experiment is not integrated.

**Cost in motion**
- `tools/banc_perf.py`, three fixed views, 1920 × 1080, VSync disabled, weather frozen, average of 120 frames per view.
- Movement per frame: `1 0 0 1 0 0.003`, same trajectories for `14c99ec` and the corrected stack; one run at a time.
- Results in `perf-reference/perf.json` and `perf-apres/perf.json`, under the same validation folder.

| Flight | Terrain computation before → after | Total GPU before → after |
|---|---:|---:|
| Trough, 3 km | 1.243 → 1.416 ms | 28.119 → 29.304 ms |
| Tropical valley, 5 km | 1.177 → 1.260 ms | 19.289 → 20.928 ms |
| Forest, 50 m | 2.103 → 2.376 ms | 22.864 → 24.193 ms |

- The correction adds 0.08 to 0.27 ms to terrain computation; total GPU time increases by 4.2 to 8.5 % on these flights.
- These averages do not measure variance between runs.

**The quality baseline**
- Twelve common sites, five heights from 12 m to 3 km, 1920 × 1080; temporal smoothing and halo enabled, clouds hidden.
- Command: `tools/banc_qualite.py ... --from-sites x64/erosion-2026-11-01/sites.json --batch-suns --before tools/banc_qualite_reference.json`.
- `14c99ec` provides 3 254 crops and already exceeds 10 % on 22 p95 measurements against the historical 2026-10-24 baseline.
- This baseline predates tectonic terrain; it is preserved, with a second comparison on the same sites against `14c99ec`.
- Some material–height pairs have fewer than twenty crops; their results remain reported, without exclusion from the threshold.
- The control provides no isolated sand crop, despite the two target sites; scree has only four crops at 12 m, none at other heights.
- This coverage cannot validate every material family.
- Mutation measures the entire image under its gray mask; unlike crops, it does not explicitly exclude the sea.
- Captures give height above filtered ground; at high altitude, cameras of the two meshes may therefore differ. The control reaches a 40.3 m difference at 3 km, versus zero at 12 and 50 m views.
- These limitations are preserved in both passes; neither metric nor baseline is changed to pass the threshold.

**Benchmark result**
- Two complete passes: 60 views and 540 captures each; 3 254 crops before, 2 535 after.
- All final measurements are finite; no control material–height pair disappears.
- Scree at 50 m appears with sixteen crops; its two p95 values have no comparable control.
- Against the historical baseline, 19 exceedances out of 47 comparable p95 values, versus 22 before; this does not validate the correction.
- Against `14c99ec`, the thirteen exceedances are below; low sample counts remain included.

| Material, height | p95 measure | Before → after | Crops before → after |
|---|---|---:|---:|
| Grass, 200 m | Repetition | 0.090 → 0.112 | 235 → 157 |
| Grass, 3 km | Repetition | 0.203 → 0.234 | 171 → 183 |
| Rock, 3 km | Gap / repetition | 2.24 → 2.71 dB / 0.144 → 0.193 | 157 → 46 |
| Scree, 12 m | Repetition | 0.073 → 0.187 | 4 → 18 |
| Snow, 800 m | Gap | 2.73 → 3.01 dB | 174 → 212 |
| Snow, 3 km | Gap | 2.69 → 3.41 dB | 231 → 234 |
| Bare soil, 12 m | Repetition | 0.070 → 0.103 | 16 → 104 |
| Bare soil, 50 m | Gap / repetition | 2.20 → 5.73 dB / 0.076 → 0.216 | 46 → 96 |
| Bare soil, 200 m | Gap / repetition | 1.01 → 2.67 dB / 0.080 → 0.217 | 40 → 103 |
| Bare soil, 800 m | Repetition | 0.094 → 0.205 | 14 → 20 |

- Mutation p95 falls at all five heights: 0.200 → 0.196 at 12 m; 0.205 → 0.146 at 50 m; 0.216 → 0.168 at 200 m; 0.110 → 0.101 at 800 m; 0.060 → 0.049 at 3 km.
- The main soil gap at 50 m comes from site −25.6°, −26.94°, now bare soil and snow where the control showed a rock wall.
- An 800 m window around this site, 1 681 probes at 1 m grid spacing, is entirely outside incision; its ground is bit-identical with or without erosion.
- The measured lack of detail in this window therefore belongs to rendering of the preserved support; the cut suppresses no detail there.
- Color and terrain views of this site and the canyon are in `diagnostic-reference` and `diagnostic-apres`; differences per crop in `attribution-qualite.json`, under the same validation folder.
- Full reports: `qualite-apres/rapport.md`, `qualite-apres/comparaison-14c99ec.md` and `audit-qualite.json`.

## Known defects

- **Flight feedback from 2026-11-01 invalidates a conclusion of clean geometry:** thin blades, spikes and sawtooth joins remain in the captures below, despite CPU checks passing on their samples.
- **The quality threshold still fails:** thirteen texture p95 values regress against the current control; newly visible bare soils and snow require further material-rendering work.
- **Gullies now follow actual incision:** slopes no longer lose their coarse support before the decision. Some unincised crests lose version E's artificial bands; their shape awaits in-flight review.
- **Glacial floors are no longer broad flats:** the U stays curved, its joins are continuous in checked cases. Slope hollows remain. River and lake water is not yet rendered.
- **Level 0 valleys remain regular at large scales:** the U corrects the glacial floor; convex-concave fluvial slopes and truncated spurs remain to build.
- **Deltas are small, and one is false:** at most 5 km, the reach of nodes read; at the largest river mouth, -7.8°, 27.2°, an isolated depositional tongue offshore, cause not found, and a straight-edged coastal section unrelated to deposits. Large deltas require a deposit field read in B-spline.
- **Gullies may be barely visible from afar:** their amplitude is now bounded by the supporting ground; the two octaves above 20 km retain their crests oriented along ranges.
- **Cost increases slightly on the three checked flights:** measurements above; no additional simulation during flight.
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
- The precise cause of blades and spikes remains to isolate; these images alone do not distinguish between the height field, its gully directions and its reconstruction by the mesh.
- Priority in the new clone: recover poses, preserve a reproduction of these cases, then fix breaks before continuing large-shape variety.

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
| 4 bis | Convex-concave fluvial slopes, truncated spurs | to do |
| 5 | Large deltas, through a deposit field | to do |
| 6 | River and lake water, from the same network | to do, with the sea |
