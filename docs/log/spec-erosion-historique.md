# Erosion spec history

**2026-11-04 · Incomplete high-altitude evaluation optimizations.**
- Native stationary captures before this work: GPU compute 65.4 ms at 1,231 km, 206.2 ms at 2,998 km and 344.4 ms at 9,998 km. Files: `distance-river-filter-cost-before/F01`, `F03`, `F08` under `x64/erosion-reprise/`.
- Skipping zero-weight noise and unused dry confluence metadata alone was insufficient: corresponding captures were 52.1, 220.2 and 677.6 ms in `distance-river-filter-cost-after/`. These results did not establish a performance fix.
- Changing the screen pass from an unrolled pair to one shared loop reduced its compiled program from 651,308 to 329,972 bytes. Both terrain evaluations remained. Corresponding captures were 22.1, 108.2 and 651.5 ms in `distance-river-screen-loop/`; the whole-globe cost remained excessive.
- These are individual title observations at 1280 by 720, clouds hidden, one engine on the GPU. They are diagnostic evidence, not performance-benchmark statistics. The current candidate adds tighter footprint bounds and exact repeated-hit reuse; its validation belongs in `../spec-erosion.md`.
- Pruning identity checks: 126 octave/footprint/seed cases, including 56 zero-weight cases without lattice work; 7,200 composed points unchanged. The loop-only change introduced no new physical approximation.
- Source snapshots: `source-before-river-filter-cost/`, `source-river-filter-prune-only/`. No benchmark, commit, tag or push.

**2026-11-04 · Superseded head-growth verification before confluence bank matching.**
- Release x64 succeeds through `tools/lance.ps1 -Build -NoLaunch`: `x64/erosion-head-growth-build.log`. Existing material-shift and atmosphere-division warnings remain.
- `verifie_tetes.py`: CPU/GPU settings agree; growth is bounded and monotone with smooth ends. A real upstream section grows from sub-metre incision to widths 282, 1,020 and 4,626 m while remaining dry. Width and depth decrease together towards the source.
- The reported terrain retains its additional dry tip at 40, 500 and 2,000 m footprints. Twelve dry joins across the planet converge under refinement. Tighter spatial culling leaves all tested terrain/water fields bit-identical in three massifs; raw-flow bounds hold on all 512,980 receiver links.
- Native cache `EXOEROS6`, payload SHA-256 `c13c3cc07c544a81f70e30b94a4c9f2bbbffc1642d4d4ed549c6031c524fb108` after the 24-byte header. Original graph words, all drainage/basin stages and local runoff match the pre-change cache exactly. Newly evaluated dry courses also acquire first-water contacts; effective downstream discharge can change.
- Independent accumulation agrees on 1,572,864 nodes and 19,033 stopped links, with conserved runoff. No stage rises downstream; the 3 % grade bound holds. All 454 sampled wet cap points stay below the cap plus fill. Original-terrain and legacy-network identity pass.
- Continuity passes 36 edge lines, 36 joins and ten confluence lines across three regions. Maximum sampled water steps are 0.010, 0.002 and 0.009 m. The broad edge grid initially missed a 0.10 m deep dry notch; local refinement gives steps 0.02144 to 0.00536 m, ratio 0.250. The test now resolves both detected peaks before diagnosing a jump, retaining the original refinement factor and acceptance threshold.
- Approach, upstream slot, morphology, mouth, confluence/current and bank-filter checks pass. They retain the 257-sample wet coastal reach, 173–484 m mouth aperture, 120 wet and 103 dry quadratures, 452 resolved confluence samples, and the physical search bound. Logs: `x64/erosion-head-growth-{core,verifie_*,continuity-*}.log` and `erosion-head-growth-approach.log`.
- Twelve native views inspected in `x64/erosion-reprise/distance-head-growth-final/`; five original before views in `distance-head-scale-before/`. Near heads extend more gradually. Orbital view F2 still has overly regular broad corridors: the visual report is only partly resolved. F7 retains the corrected upstream canyon; F8/F9 retain the previous water connection fixes.
- Native descent: `approach-head-growth/`, 160 frames from about 1,230 km to 40 m above the head valley. Five spaced frames inspected; a separate final native capture confirms 39.5 m ground clearance. This is a sampled inspection, not proof of every temporal transition.
- Remaining morphology: orbital corridor repetition and missing fine tributary hierarchy; no long estuarine basin model; F10 has a side distributary ending on land, F11 a coarse straight lake-stage boundary. Bank finish still needs refinement. The onset change is not a complete answer to these reports.
- The separate coastal-talus test's inactive historical witnesses remain a known pre-existing limitation; earlier evidence is preserved in the erosion log. It was not rerun for this head-only change.
- No performance or image-quality benchmark, commit, tag or push. Flight review remains pending.


**2026-11-04 · Superseded symmetric confluence opening.**
- The connector added 1.15 receiving nominal half-widths to both banks over nine combined half-widths, independently of its own width deficit. This erased the upstream land tongue and let its round endpoint protrude outside the receiving channel.
- The former opening regression required a near-junction width gain above 35%, even for a section already wide enough. It rewarded the bulb rather than checking bank geometry.
- Replaced by receiving-width matching and downstream-facing opening. Source/cache: ignored `source-before-confluence-banks/` and `erosion-before-confluence-banks.bin`. Three native before views: `distance-confluence-banks-before/`.
- The first asymmetric candidate chose the side from the coarse receiving heading. Three of 584 sampled connectors needed the opposite side when the actual meander slope was included. The retained version uses local flow and smoothly removes the opening near parallel alignment; the coarse-heading candidate is not the final review version.

**2026-11-04 · Rejected 32 m³/s, sixth-order onset.**
- Candidate: `RIVER_Q.x = 32`, dry share `t^6 (7 - 6t)`. It extends resolved heads but contributes too little upstream incision to change the reported orbital silhouette sufficiently.
- Native view F2 also exposed extra calculation cost: its ordinary capture title rose from about 40 to 84 ms GPU calculation time. These single frames are not a benchmark or a statistical measurement.
- Twelve candidate native views: `distance-head-scale-after/`. Source/cache: `source-head-onset-rejected/` and `erosion-head-onset-rejected.bin`, all ignored. This candidate is not the final review build.
- The next candidate starts at 100 m³/s and grows in linear discharge. It also prunes provably inactive catchments before reading tributaries and tightens dry-course spatial bounds without changing their terrain.

**2026-11-04 · Superseded dry-head onset and diagnosis.**
- `RIVER_Q` was (200, 300, 450) m³/s; corridor depth and widths used a log-discharge smoothstep over 200–300. Many heads reached their full broad profile within one coarse graph link.
- Under that calibration, dry and wet courses occupied 8.2 % of land links, with inverse drainage density 170 km; wet courses alone occupied 6.0 %, with 232 km. These are not outlet-spacing measurements.
- The reported head already had a physical point before this follow-up. A 40 km fine/coarse comparison did not establish a large systematic excess incision from filtering; do not attribute the report to a proven lost-spur mean bias.
- Extending only synthetic dry head objects was insufficient evidence: actual heads can start below the activation threshold. The new regression follows real dry courses and composed terrain at several footprints.
- Before-change source and cache: ignored `x64/erosion-reprise/source-before-head-scale/` and `erosion-before-head-scale.bin`. Five native before views use `distance-head-scale-before/`.

**2026-11-01 · Visible water was deferred.**
- The earlier erosion spec stored river discharge and stage but rendered only the sea.
- Its remaining step 6 deferred river and lake surfaces to later work with the sea.
- Replaced by `../spec-eaux-interieures.md`: shared channel envelopes, terminal stages and water optics.
- A nearest-cell lake stage was rejected after sampled coarse divides produced water steps up to 276.5 m.
- Continuous reconstruction replaces that lookup; connecting bands remain an approximation of unresolved spillways.

**Superseded coastal models; see the [current spec](../spec-erosion.md).** Experiment `piste/erosion-globale`.

**2026-11-01 · Fold attenuation before erosion, removed.**
- `EROSION_FOLD_DEPTH = (800, 2000)` erased large folds according to network incision, before deciding local carving.
- This coupling could change a slope without the valley incising it; near the wooded canyon, the support lost around 933 m.
- The support is now independent; only the erosive profile can cut it.

**2026-10-31 · The distance profile.**
- **The model:** wall drawn from the estimated shore to the retreat distance, height extrapolated from the point.
- **Rendered defect:** the proxy ignores detail; mountains lowered to the platform, inland channels and kilometer-high walls.
- **Slope measurements alone did not validate it:** they checked neither maximum lowering nor neighboring windows.

**2026-10-31 · The contour from coastal slope.**
- **The model:** remapping h, Hc between 8 and 400 m, lowering bounded by Hc + 1 m.
- **Rendered defect:** G between 0.03 and 0.1 m/m underestimates actual slopes of 30 to 45°; walls remain invisible at 4 km.

**2026-10-31 · The contour from local detail slope.**
- **The model:** `SLOPE_KM = 0.3`, seven octaves from 50 km to 566 m; two walls above 100 m measured, visible in flight.
- **Rendered defect:** Hc changes at a smaller scale than its platform; landlocked cuts and land between the wall and sea.
- **Flooding, three 10 km windows at 50 m spacing:** 19.432 %, 1.373 %, 3.883 % of cuts deeper than 10 m inaccessible; centers in the current spec.

**2026-10-31 · The expected-slope variant, compared with the 9 km filter.**
- **RMS coefficient:** 0.0002283923092 /m; 65 536 fixed directions, twelve unit-amplitude ridged octaves, without folds or gullies; tectonic amplitude before the valley-wall term.
- **Landlocked shares:** 8.411 %, 0.555 %, 0 %; the 5 % threshold also fails in the first window.
- **The three fixed sections:** 256.328 / 111.488 / 132.693 m; platforms −1.069 / −1.770 / −2.199 m; no land in front of the foot.
- **The choice:** 9 km filter, retaining high walls and the observed low coast without an extra statistical proxy; neither choice guaranteed connectivity with the symmetric band.

**2026-10-31 · The symmetric band around the estimated shore.**
- **The model:** `abs(shoreKm / shoreMetric) < W + 1 km`, fading over 500 m; raw 8 km proxy; slope filtered at 9 km.
- **Rendered defect:** a beach and hills in front of the tropical wall, a flooded inland cut; detail moves the shore outside the band.
- **The windows:** 8.889 %, 0 %, 0 % landlocked; the 108 isolated cells in the first window remain inaccessible even without the lowering cap within the band.
- **Previous Hc distributions, median/p90/maximum:** 149.855/257.947/337.176; 82.360/121.832/177.379; 91.426/159.114/245.786; 119.426/247.176/340.331; 137.097/168.253/193.122; 124.299/224.383/329.615 m; same six centers as the current spec.
- **The correction:** seaward, opening to the proxy; inland, adding displacement `relief / coastSlope`, capped at 8 km; Hc remains unchanged.

**2026-10-31 · The fifth pass, without a sea-access check.**
- **Seed 0 render:** tropical wall and stack approved; no more land band in front or inland pit; clean cliff at 3° S.
- **Seed 1 defect:** channels and cliff rings around lakes on the plain at −65.00789/−113.42094.
- **Ablation over 10 km at 50 m spacing:** symmetric band 15.720 % lowered by more than 10 m; opening alone 16.121 %; inland extension alone 16.198 %; together 16.200 %.
- **Corresponding landlocked shares:** 31.286 %, 32.735 %, 32.579 %, 32.574 %; no original sea point at the −50 m threshold in this window.
- **The cause:** regional Hc cuts low terrain without checking wave access; no level 0 valley link incised the affected points.
- **Both extensions slightly worsen an earlier defect:** removing them alone does not fix it; the seaward opening is retained.
- **Seed 0 Hc distributions:** 134.698/251.737/337.176; 64.505/114.265/177.379; 78.409/162.371/245.786; 92.216/159.570/340.331; 131.832/163.650/193.122; 102.872/208.796/329.615 m; median/p90/maximum at the spec's six centers.
- **Selected correction:** a pre-erosion sea probe 3 km offshore; approved walls and the cold face remain identical, the glacial window is no longer lowered.

**2026-10-31 · Provisional crests and climate, superseded.**
- **Activation:** the maximum of trough ice and the equilibrium-line band also sharpened soils beneath ice.
- **The profile:** `scale × k × u^0.7`, applied to the already rounded centered crest, reamplified its small values; its slope tends to infinity at zero.
- **Climate:** zonal rain and temperature, without continentality; zonal coastal wind, strength from 1 to 1.6, with an east frame opposite to the computed map's.
- **First trials:** widening rounding alone did not guarantee removal of steepening; the selected monotone profile also bounds slope amplification.
- **Cache:** terrain, seed and executable date; climate itself was not in the key.

**Measurements before computed climate, preserved as a historical baseline.**

**CPU measurements, seeds 0 and 1:** `python tools/cotes/verifie_falaises.py`.
- **The three fixed sections:** centers rendered by the user; orientation from the original ground slope; face sought within 2 km of the center, 10 m spacing.
- **Height:** from the neighboring platform to the crest joining the original ground, without replacing this measure with Hc.
- **Land in front of the foot:** cumulative width above +5 m, to the first original ground below −20 m offshore.

| Center | Wall, m | Angle | Platform, m | Land in front, m |
|---|---:|---:|---:|---:|
| 8.72580 ; −103.29430 | 252.295 | 80.95° | −1.157 | 0 |
| −23.18981 ; 157.86949 | 42.020 | 67.38° | −1.242 | 0 |
| −3.21302 ; 169.26372 | 121.945 | 83.76° | −1.939 | 0 |

**The six windows remain below 5 % landlocked cuts and 4 km reach at p99.**
- **The windows:** 10 × 10 km, 201² points including edges, 50 m sample and grid spacing.
- **Flooding:** starts from original ground below −20 m; four neighbors; passes through new ground below 0 m or lowered by more than 1 m.
- **Landlocked share:** fraction of points lowered by more than 10 m that flooding does not reach.
- **Original sea:** original ground below 0 m connected, through four neighbors within the window, to ground below −50 m.
- **Distance to sea:** exact Euclidean minimum on this grid, for points lowered by more than 10 m; p99 and maximum, without scipy.
- **A window without cuts:** no quantile to compute, shown as “—”.

| Seed; center | Landlocked | Sea distance p99 / maximum, m | Maximum lowering, m | Surface lowered by more than 10 m |
|---|---:|---:|---:|---:|
| 0 ; 8.73276 ; −103.30263 | 0 % | 604.152 / 680.074 | 296.530 | 4.846 % |
| 0 ; −23.18173 ; 157.88952 | 0 % | 400.000 / 502.494 | 109.573 | 1.317 % |
| 0 ; −3.21302 ; 169.26372 | 0 % | 549.885 / 696.419 | 227.117 | 2.728 % |
| 1 ; −65.00789 ; −113.42094 | 0 % | — | 0 | 0 % |
| 1 ; 23.78161 ; −126.35919 | 0.113 % | 1 388.320 / 1 656.050 | 365.902 | 4.384 % |
| 1 ; 40.46592 ; −84.75513 | 0 % | 559.017 / 626.498 | 189.467 | 2.267 % |

- **Seed 1 tropical coast:** nearest active sector to 23.70143/−126.32998 within a 60 km square, 496 m spacing; no cut in the initial 10 km square.
- **The glacial plain:** no lowering; its probe remains on land, from +26 to +799 m for the old cuts.
- **Diagnosis:** the defect existed with the symmetric band; the fifth pass's two extensions only worsened it slightly, [history](log/spec-erosion-historique.md).
- **The valley hypothesis:** no level 0 link incised the lowered points in this window; an overly permissive regional Hc alone can cut its hills and detail depressions.
- **The contour:** Hc, its 9 km filter and the three measured walls remain unchanged; seaward opening is retained behind the access check.
- **Global limitation:** the local access test is not ocean routing; distance is checked on actually eroded ground, and the proxy cap can still exclude a shore displaced by more than 8 km.
- **Measured bound in these windows:** `lowering − Hc ≤ 0.998 m`.
- **The flat-coast control:** zero difference at 16.71/−89.28, on the section and 441 points of a 10 km square.
- **`valleys = false`:** identical to the committed port on 288 points for each seed, at grid spacings of 10 m, 1 km and 30 km.
- **The port:** both scripts report `ok`; continuity at the profile's three joins and band edges, seaward opening, deep ground and bounded lowering checked up to 30 km grid spacing.
- **The build:** Release x64 successful, no warnings in modified files; no engine or benchmark run.

**Hc on the active coast, median/p90/maximum, in meters:** 60 km square, 201² points, 300 m sample spacing, 10 m grid spacing; original ground between 0 and Hc, lowered by more than 1 m.

| Center | Points | Median | p90 | Maximum |
|---|---:|---:|---:|---:|
| 8.54005 ; −103.23344 | 112 | 134.698 | 251.737 | 337.176 |
| −23.01696 ; 158.00809 | 105 | 64.819 | 110.074 | 126.281 |
| −3.34285 ; 169.01181 | 229 | 78.515 | 163.812 | 245.786 |
| −51.89165 ; −40.94037 | 89 | 89.894 | 132.712 | 214.339 |
| −8.11021 ; 131.04460 | 140 | 135.055 | 163.490 | 192.919 |
| 8.76166 ; −103.24998 | 173 | 110.260 | 219.854 | 329.615 |

**Cold and active coasts:** recentered on the first zero crossing of original ground, closest to the requested point on a 30 km section normal to the large shapes.
- **The search:** crossing bracketed at 10 m spacing, refined by bisection; no selection by wall height or steepness.
- **The cold coast:** shore at −51.79251/−40.80271; wall 86.900 m at 75.62°, platform at −1.576 m; band and proxy at 1, exposure 0.28, K 0.984724.
- **Limit of this cold section:** it still crosses 660 m of land above +5 m between this foot and the first original ground below −20 m.
- **The active coast:** shore at −8.10764/131.04054; no face within 2 km along its section; exposure 0.663389, K 1, proxy and band zero.
- **Cause on the active coast:** its 11.407 km proxy exceeds the retained 8 km cap; it is not sheltered from waves.
- **Hc statistics:** field value at each point remains identical; the probe filters active surfaces, so distributions change.
- **Superseded models:** [history](log/spec-erosion-historique.md); user flight review: `tools/tests/2026-10-31-erosion.txt` for seed 0, `2026-10-31-falaises-graine1.txt` on a seed 1 build.

**The network, seeds 0, 1 and 2,** measured on the engine file, `erosion-<graine>.bin`:

| Seed | Toward sea, toward lakes | Lakes | Ice | Largest basins | Largest discharge | Node incision, p90 and p99 |
|---|---|---|---|---|---|---|
| 0 | 82.2 %, 17.8 % | 0.95 % | 22.1 % | 5.6, 3.1, 2.4 Mkm² | 71 000 m³/s | 314 m, 2.3 km |
| 1 | 81.2 %, 18.8 % | 0.80 % | 18.3 % | 4.6, 3.5, 2.9 Mkm² | 93 000 m³/s | 430 m, 2.3 km |
| 2 | 86.4 %, 13.6 % | 1.87 % | 21.8 % | 7.7, 3.0, 2.8 Mkm² | 185 000 m³/s | 559 m, 2.6 km |

- **All land reaches the sea or a terminal lake,** no cycles, for all three seeds. On Earth, around 18 % of land is endorheic; the Amazon drains 7 Mkm², 200 000 m³/s.
- **Seed 0:** 787 deltas, 2 115 fans; median incision zero, plains rivers flow on their plain.
- **Seeds 1 and 2** were checked before weighted routing; seed 0, before and after, retains full drainage.

**Cost and port before this connection, not remeasured.**

## Measurements, seed 0

| Measure | Value | Proposed budget, and why |
|---|---|---|
| Startup, cold level 0 | 0.54 s, including 0.50 s for the network; form shader compiled during the tectonic map | 0.5 s per planet: half the tectonic map, the whole system in a few seconds at first launch |
| Startup, from cache | 0.03 s | 0.05 s: one 12 MB file per body |
| GPU memory | 12 MB | 13 MB: 8 bytes per cell, one third of the tectonic map |
| Terrain computation, in motion | 0.67 to 1.46 ms versus 0.28 to 0.95 ms, +0.2 to +0.65 ms; minimum of 3 passes, shared GPU at 75 % load | at most +0.5 ms: headroom of a frame at 120 fps |
| Port against the planet map, 600 grid cells | median difference 0.6 cm; p99 0.22 m; at most 0.6 m | median 10 cm |
| Port against ground under the camera, fine grid, 7 sites | median 0.18 m, at most 0.5 m, the title's precision | — |

**2026-10-31 · Before the gully slope budget.**
- **User feedback after the connection:** forest cutoff removed, lakes and unglaciated forest clean, climate then erosion at startup without errors.
- **Remaining defect:** trenches, palisades and a bank from gully bands, without valley or deposit; the cusp-free profile did not bound their slope.
- **Rejected trials:** limiting only the wave's nominal slope lets direction rotation and weight variation steepen the ground; limiting the whole octave's amplitude also weakens its underlying noise.
- **Old measurements:** network before the user's new startup; they do not describe current saturation.

## CPU measurements of the connection, seed 0

**Reference:** `fe22cfe9d6d96e9680ca44ef2fd5e47704467939`, same level 0 caches before/after, same coordinates, 1 m grid spacing.
- **Transects:** northward, from 0 to 25 m, 0.25 m spacing; maximum slope between two points, maximum rise over 0.5 m.
- **Windows:** 200 × 200 m, 201² points, 1 m spacing; centered-gradient magnitude on the 199² interior points.

| Site, latitude; longitude | Maximum northward slope, before → after | Rise over 0.5 m, before → after | Window above 60°, before → after |
|---|---:|---:|---:|
| Forest, 34.1611352 ; −73.72443 | 82.110° → 40.624° | 2.888525 → 0.424922 m | 9.504810 → 9.812884 % |
| Slope, −48.3497 ; −44.8221 | 9.541° → 34.412° | 0.029690 → 0.087256 m | 6.530138 → 4.628671 % |
| Arêtes, −46.9 ; −33.8 | 38.073° → 39.998° | descending throughout the section | 11.416378 → 28.203833 % |

- **Absolute variation over 0.5 m:** forest 3.106238 → 0.424922 m; slope 0.084017 → 0.341587 m; arêtes 0.391559 → 0.418452 m.
- **Arêtes remain active:** removing only sharpening after correction moves ground by at most 157.873 m in their window; maximum window slope 86.993°, finite.
- **Analytical check:** monotone profiles, zero derivative at the crest, rounding from 0.0001 to 10 times amplitude; derivative error against finite differences below 6.94·10⁻⁸, mean variation below 4.48·10⁻¹³ noise unit.
- **Limitation:** the forest retains steep slopes elsewhere in its window; their share does not decrease there. The reported slope had no wall on its 25 m northward section alone. These figures do not replace flight review.
- **Climate change:** forest equilibrium line 2 982 → 2 033 m, slope 1 287 → 28 m, range 1 472 → 467 m; new rain and temperature change activation, even with a fixed network.

**Hc on the six coasts, median / p90 / maximum in meters:** 60 km squares, 201² points, 300 m sample spacing, 10 m grid spacing; ground before waves between 0 and Hc, lowered by more than 1 m.

| Center, latitude; longitude | Hc before | Hc after | Wind strength before → after |
|---|---:|---:|---:|
| 8.54005 ; −103.23344 | 134.511 / 251.589 / 337.002 | 211.469 / 376.231 / 400.000 | 1.000059 → 1.000000 |
| −23.01696 ; 158.00809 | 64.505 / 109.177 / 126.281 | 64.505 / 109.177 / 126.281 | 1.020926 → 1.000000 |
| −3.34285 ; 169.01181 | 89.815 / 175.176 / 233.046 | 89.815 / 175.176 / 233.046 | 1.000004 → 1.000000 |
| −51.89165 ; −40.94037 | 54.558 / 130.787 / 214.107 | 54.558 / 133.071 / 214.107 | 1.431430 → 1.121946 |
| −8.11021 ; 131.04460 | 121.440 / 186.622 / 234.563 | 54.275 / 69.711 / 89.271 | 1.000047 → 1.000000 |
| 8.76166 ; −103.24998 | 110.260 / 219.275 / 329.433 | 177.989 / 349.712 / 400.000 | 1.000066 → 1.000000 |

- **Wind direction matters:** speed conversion remains in the old useful range; the frame is corrected to read climate. Hc can therefore change considerably, as can active points.
- **`valleys = false`:** bit-identical on 288 points per seed, seeds 0 and 1, at grid spacings of 10 m, 1 km and 30 km.
- **The flat coast:** zero difference on its section and the 441 points of its 10 km square, at 16.71; −89.28.
- **Caches:** seed 0 tectonics, volcanoes and climate present in `x64/Release`, computed with unchanged integrated sources; old level 0, not rebuilt. For coastal-check seed 1, existing tectonic, volcanic and climate maps reused from the climate worktree, identical tectonic generator and identical `Climate::Build`; old network preserved.
- **Cost:** no benchmark requested or run; old cost measurements remain in the history.
- **The build:** `tools/lance.ps1 -Build -NoLaunch`, Release x64 successful; no warnings in modified files.
- **Checks:** `cp.py`, `verifie_cretes_climat.py` and `verifie_falaises.py` report `ok`; two fixed faces present before and after, one above 100 m. The coastal check compares this integrated control, because its third historical face is already absent before the connection.
- **Sections with sea access:** at most 0.500 % landlocked in the six windows, p99 reach at most 1 373.851 m; 2 950.013 m in the additional tropical-cape window; `lowering − Hc ≤ 0.998 m`.

**The global network must be remeasured after rebuilding level 0.** The port reads the engine file; it does not compute this level. Old shares of drained, frozen and lake-covered land remain in the [history](log/spec-erosion-historique.md).

## 2026-10-31 · Measurements before floor joins and the rock bound

**Budget C, before D.**

**Before/after on the same current network, computed by the engine launched by the user.** No engine or benchmark run during this correction.
- **The reference before C:** `x64/Release/cp-avant-pentes.py`, copy of the port before modification; SHA256 `2240e47c60635f41d3877f53abdb355d7c72bec428ffe5f85b8acbeba986d7ea`.
- **The check:** `python tools/hydro/verifie_pentes_ravines.py`, or `--only analytic`, `windows`, `coasts`; `--before-file` accepts another reference copy.
- **The windows:** 100 × 100 m between edges, 101² points, 1 m spacing; centered gradient, one-sided difference at the edge.

| Site, latitude; longitude | >35°, before → after | >45°, before → after | >60°, before → after | Maximum, before → after |
|---|---:|---:|---:|---:|
| Forest, 34.1611352 ; −73.72443 | 39.320 → 0 % | 10.460 → 0 % | 3.794 → 0 % | 84.939° → 30.648° |
| Slope, −48.3497 ; −44.8221 | 13.724 → 0 % | 5.784 → 0 % | 1.245 → 0 % | 71.630° → 22.578° |
| Canyon, −38.1080 ; 166.4916 | 83.364 → 14.254 % | 74.640 → 0 % | 40.869 → 0 % | 84.484° → 44.060° |
| Flat, 44.16 ; −60.08 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 4.610° → 4.613° |
| Arêtes, −46.9 ; −33.8 | 63.082 → 31.948 % | 49.770 → 0.863 % | 31.977 → 0 % | 86.751° → 47.432° |

**Controls, without gullies / before erosion:**

| Site | >35° without gullies / `valleys=false` | >45° without gullies / `valleys=false` | >60° | Maximum without gullies / `valleys=false` |
|---|---:|---:|---:|---:|
| Forest | 0 / 0 % | 0 / 0 % | 0 % | 30.648° / 30.648° |
| Slope | 0 / 0 % | 0 / 0 % | 0 % | 22.577° / 22.577° |
| Canyon | 14.254 / 25.909 % | 0 / 1.500 % | 0 % | 44.060° / 47.268° |
| Flat | 0 / 0 % | 0 / 0 % | 0 % | 4.612° / 4.612° |
| Arêtes | 31.948 / 31.948 % | 0.863 / 0.863 % | 0 % | 47.432° / 47.432° |

- **Target met:** no point above 45° in the four mobile-soil windows, versus at most 1.500 % on the pre-erosion form.
- **The reserve is conservative:** gullies entirely removed in the forest and canyon, effect below 1 mm on the slope; underlying noise preserved bit-identically, not flattened.
- **Arêtes:** rocky crests of 47.432°, 31.948 % of the window above 35°; gully replacement almost zero there, around 1 µm in height. Old slopes of 86.751° came from the problematic pattern.
- **Grid spacing:** bit-identical results in these five windows between 0.25 and 1 m grid spacings, where octaves are resolved.
- **The mean:** centered band profiles, quadrature error below 1.03·10⁻¹³ noise unit, rounding from 0.0001 to 2 amplitudes; a 100 m window does not average phases of octaves several km wide.

**The two northward transects:** 0 to 25 m, 0.25 m sample spacing, 1 m grid spacing.

| Site | Maximum slope, before → after | Maximum rise over 0.5 m | Maximum absolute variation over 0.5 m |
|---|---:|---:|---:|
| Forest | 40.624° → 17.267° | 0.424922 → 0.155406 m | 0.424922 → 0.155406 m |
| Slope | 34.412° → 13.486° | 0.087256 → 0.119753 m | 0.341587 → 0.119753 m |

**The six cliff contours are preserved:** Hc comparison at the same 201² points in `verifie_falaises.py` windows, zero maximum difference for each field; quantiles below taken at points active before C.

| Center | Hc median / p90 / maximum at points active before, m | Hc at points active after, m |
|---|---:|---:|
| 8.54005 ; −103.23344 | 211.469 / 376.231 / 400.000 | 203.744 / 382.981 / 400.000 |
| −23.01696 ; 158.00809 | 69.649 / 109.531 / 126.281 | 67.239 / 109.075 / 126.281 |
| −3.34285 ; 169.01181 | 89.815 / 175.176 / 233.046 | 82.142 / 175.291 / 218.965 |
| −51.89165 ; −40.94037 | 46.701 / 134.083 / 214.107 | 54.649 / 137.112 / 214.107 |
| −8.11021 ; 131.04460 | 54.275 / 69.711 / 89.271 | 50.437 / 71.033 / 89.271 |
| 8.76166 ; −103.24998 | 177.989 / 349.712 / 400.000 | 171.101 / 345.552 / 400.000 |

- **The Hc field changes at no point:** the ground correction shifts active points; their median varies from −8.54 to +17.02 %, their p90 by at most 2.26 %. The same points retain exactly the same quantiles before/after.

- **`valleys=false`:** bit-identical on 288 points per seed, seeds 0 and 1, at grid spacings of 1 m, 1 km and 30 km.
- **Without gullies:** bit-identical before/after C in the five windows.
- **The flat coast:** zero difference on the 441 points of its 10 km square, at 16.71; −89.28.
- **Network files:** current caches read by both versions; no new level 0 produced during C.
- **Flight review remains pending:** `tools/tests/2026-10-31-pentes-ravines.txt`.
- **Verification:** Release x64 through `tools/lance.ps1 -Build -NoLaunch`, no errors or new warnings in modified files; `cp.py`, `verifie_pentes_ravines.py`, `verifie_falaises.py` and the crest check report `ok`.


**C's rule superseded after user feedback:**
- **No higher threshold under the glacial flag alone:** ice at the last maximum does not prove bare rock is present; gullies remain a mobile-soil pattern. Noise supporting rocky crests, valley profiles and cliffs are not capped by this setting.

## 2026-10-31 · D before spherical projection and scale separation

**D measurements.**

**Same current network before/after D, provided by the engine launched by the user.** No engine or benchmark run here; the port does not rebuild level 0.
- **The reference:** `x64/Release/cp-avant-fonds.py`, SHA256 `e8e551b5df2a62e8caaec981be4fb1289f8a07c424d9665bc800c70987a2f3e4`; C measurements and earlier references in the [history](log/spec-erosion-historique.md).
- **Commands:** `python tools/hydro/verifie_fonds_vallees.py`; `python tools/hydro/verifie_pentes_ravines.py --before-file x64/Release/cp-avant-fonds.py`.
- **Flooding:** 4 km square between edges, 161² points, 25 m spacing, eight neighbors, open edges. First square centered 2 325 m north and 1 475 m east of −25.566; −26.916; second centered on −25.486; −27.075. Port grid spacing 5 m.

| Area | Maximum closure depth of square, before → after | At the deepest point before, before → after | 10 km square more than 5 m below its water level, before → after |
|---|---:|---:|---:|
| First trough | 77.010 → 72.964 m | 77.010 → 48.373 m | 0.450936 → 0 % |
| Second trough | 734.793 → 681.453 m | 734.793 → 579.469 m | 0.666601 → 0.058818 % |

- **The first floor:** at the point of maximum depth before, ground 992.265 → 1 021.138 m, its water level. At the offset point given in the report, ground 1 049.607 → 1 036.022 m, its level; closure depth 19.668 → 33.489 m. The square's residual maximum, 72.964 m, also exists in coarse incised ground without detail.
- **The second floor:** at the point of maximum depth before, ground 1 060.705 → 1 216.029 m, its water level. Square closure is not removed: coarse incised ground alone, without any detail, already contains a 441.570 m depression. The cause of this depression in the current network remains to investigate; residual detail alone does not cause it.
- **Plateaus actually bounded by water:** 4 592 and 2 764 points; ground − water differences of [−67.036; +191.015] m and [−155.324; +164.339] m before, zero after. Thalweg traces take the deepest coarse profile in each section, without selecting by fine height: 72 and 50 points; differences [−15.521; +58.883] m and [−39.522; +88.158] m before, zero after. CSV in `x64/Release/thalweg-*-*.csv`.
- **The 10 km squares:** 101² points at 100 m, centered on the two reported coordinates. More than 5 m below level among points with `floorShare > 0`: 0.137241 → 0 % and 0.313695 → 0 %. The second window's residual deficit of 64.863 m lies outside this mask.
- **The initial 84 m depression is not reproduced with the new network:** do not confuse integration measurements before A–C with this baseline before D.
- **Outside incision:** floor correction isolated from the rock bound, 6 172 and 7 234 points of the two 10 km squares bit-identical.

**C windows:** 100 × 100 m between edges, 101² points at 1 m; centered differences, one-sided at the edge.

| Site | >35°, before → after | >45°, before → after | >60°, before → after | Maximum, before → after |
|---|---:|---:|---:|---:|
| Forest, 34.1611352 ; −73.72443 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 30.647836 → 30.647798° |
| Slope, −48.3497 ; −44.8221 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 22.577514 → 22.577126° |
| Canyon, −38.1080 ; 166.4916 | 14.253505 → 14.253505 % | 0 → 0 % | 0 → 0 % | 44.060265 → 44.060258° |
| Flat, 44.16 ; −60.08 | 0 → 0 % | 0 → 0 % | 0 → 0 % | 4.613229 → 4.613229° |
| Arêtes, −46.9 ; −33.8 | 31.947848 → 31.947848 % | 0.862661 → 0.862661 % | 0 → 0 % | 47.432335 → 47.432339° |

- **The rock threshold alone does not restore walls:** tan(70°) is applied, but C's conservative bound still limits the pattern to 0.255 mm in the arête window. Walls above 60° have not returned; slope and rotation bounds must be tightened without removing soil protection.
- **Soils remain as in C:** zero above 45° in the four controls; the canyon before erosion remains at 1.499853 %. Floor joins do not change their noise without gullies, bit-identical.
- **Northward transects, 0 to 25 m at 0.25 m:** forest, slope 17.267267 → 17.267291°, rise and absolute variation over 0.5 m 0.155405864 → 0.155406092 m; slope, 13.486420 → 13.485948°, 0.119753109 → 0.119749038 m for both variations.
- **Grid independence:** five windows bit-identical between resolved grid spacings of 0.25 and 1 m.

**Hc median / p90 / maximum:** same six 60 km squares, 201² points; same active points before/after D. Zero field difference everywhere.

| Center | Hc before = after, m |
|---|---:|
| 8.54005 ; −103.23344 | 203.744 / 382.981 / 400.000 |
| −23.01696 ; 158.00809 | 67.239 / 109.075 / 126.281 |
| −3.34285 ; 169.01181 | 82.142 / 175.291 / 218.965 |
| −51.89165 ; −40.94037 | 54.649 / 137.112 / 214.107 |
| −8.11021 ; 131.04460 | 50.437 / 71.033 / 89.271 |
| 8.76166 ; −103.24998 | 171.101 / 345.552 / 400.000 |

- **`valleys=false`:** 288 points × three grid spacings, seeds 0 and 1, bit-identical.
- **Flat coast:** 441 points of the 10 km square at 16.71; −89.28, bit-identical; C's flat control too.
- **Checks:** `cp.py`, cliffs, analytical budget check and floor joins report `ok`. The window check now explicitly fails on arête walls above 60°, not restored; coarse closures remain measured, without being declared fixed.
- **Build:** Release x64 through `tools/lance.ps1 -Build -NoLaunch`, zero errors, no new warnings in modified files; remaining warnings in unchanged `Materials`, `Mesh`, `OceanSurface`, `PixelShader` and `PlanetFoliageMeshPixel` files. Results in `x64/Release/verification-build-fonds-final.txt`.
- **Flight review:** `tools/tests/2026-10-31-fonds-vallees.txt`, without automatic launch.


**The superseded budget:**

**The slope budget, `ReliefGullyGain`:**
- **The mobile-soil threshold:** `EROSION_GULLY_CRITICAL = 1.25`, around 51.3°; working value from MR1, `1.25 ± 0.10`, [Roering, Kirchner and Dietrich 1999](https://seismo.berkeley.edu/~kirchner/reprints/1999_29_Roering_nonlinear.pdf), §5.2 and table 1. Their transport grows without bound approaching this threshold; it is not the repose angle of cohesionless grains.
- **The rock threshold:** `Sc = lerp(1.25, tan(70°), gullies.glacial)`, `EROSION_GULLY_ROCK = 2.74747742`; only the equilibrium-line band, never `valley.glacier`. Selby 1980 relates rock slope to rock-mass strength; 70° is our choice for strong rock, within the reported 60–80° range, not a universal threshold from the article. [Augustinus 2002's fieldwork](https://pubs.geoscienceworld.org/gsl/sjg/article-abstract/38/1/15/114650/The-influence-of-rock-mass-strength-on-the-form) applies this strength balance on deglaciated slopes. Ordinary noise, valley profiles and cliffs retain their laws.
- **First reserve room for ordinary noise:** `s` is the slope of larger octaves, `N` a bound on the ordinary octave's slope; `L = max(Sc − s − N, 0)` and `B = L² / Sc`. The square joins the reserve to zero with zero derivative.
- **Then replacement alone:** `D = share × (N + G)`, `gain = B / sqrt(B² + D²)`; the pattern blends with noise at `share × gain`, without clipping a height. Its additional slope is at most B, B at most L; when the reserve is exhausted, ordinary noise remains intact.
- **G covers bands and their orientation:** wave period, quintic weights of the eight corners and normalization near bifurcations; direction rotation follows the curvature bound of larger octaves, divided by their slope. Limiting only the sinusoid's nominal slope was insufficient.
- **Quintic-noise bounds:** 26 for gradient, 512 for curvature in grid-cell units; conservative upper bounds from unit corners and weight derivatives, not per-site settings. Rounded-crest curvature uses the physical 2 m floor and geology; never current grid spacing or octave filtering weight.
- **The mean:** noise and band are centered separately before replacement; for band crests, exact mean of the rounded sinusoid, including sharpening. Gain depends on supporting shapes, not the current octave's phase.
- **Cost:** no neighboring terrain or map read; an exhausted budget skips pattern computation, except the coastal calibration octave. No GPU benchmark run.

## 2026-10-31 · E's duplicate coastal estimator, removed

- **Calibration is independent of incision:** only at points where waves can act, the valley read and three octaves above 9 km retain D's estimator; actual ground uses spherical projection and new gullies. Hc thus remains identical at the same points. This adds a valley query and three octaves in this coastal band alone; no neighboring ground or full terrain reevaluated for Hc.

**Coastal controls:** same six 60 km squares, 201² points, same Hc at the same points, zero field difference everywhere. Quantiles at D's active points, median / p90 / maximum in m:

| Center | Hc D = E |
|---|---:|
| 8.54005 ; −103.23344 | 203.744 / 382.981 / 400.000 |
| −23.01696 ; 158.00809 | 67.239 / 109.075 / 126.281 |
| −3.34285 ; 169.01181 | 82.142 / 175.291 / 218.965 |
| −51.89165 ; −40.94037 | 54.649 / 137.112 / 214.107 |
| −8.11021 ; 131.04460 | 50.437 / 71.033 / 89.271 |
| 8.76166 ; −103.24998 | 171.101 / 345.552 / 400.000 |

- **Active points change with the ground:** their quantiles can therefore vary without changing the Hc field.
**Removed at the user's request:** bit-identical Hc was overspecified; it justifies neither a second off-sphere valley read nor three recalculated octaves. Current measurements are in `../spec-erosion.md`.


## 2026-11-01 · Superseded profiles and measurements from version 14c99ec

Overdeepened troughs then flattened at water level, four chords per curve and 7 km warping are superseded. The following measurements concern that old state.

## Level 1: network valleys, `ErosionValleys`

**Each level 0 link is a curve:** a quadratic B-spline between link midpoints, tangent from one link to the next; a tributary joins the trunk tangentially, downstream. The point is read with a 7 km warp, at wavelengths of 40 and 20 km, making straight links meander.

**A direction warp stays on the sphere:**
- **Cause of closed troughs:** turbulence moved p in 3D without renormalizing it. Distance to the curve counted its radial offset, sometimes kilometers, as transverse distance; the profile rose along the thalweg and closed the floor.
- **Correction in `ErosionValleys`:** return to unit length before localization and distance calculations; inverse-square-root estimate in float, one Newton refinement in doubles before multiplying p. No water level changed, no forced sill or local drainage.
- **Unincised ground stays free:** the floor calms detail only if `h > max(surface, level)`; the same water-bounded surface estimates the incised share and wall-detail reinforcement. The underwater profile must not erase ground below its level that it cannot incise.

**The valley, around the nearest curve:**
- **the floor,** at water level interpolated along the curve, half-width 2 √Q m, up to 15 times wider on a slow river, at most 0.15 cell; detail fades there, except under the sea, nothing finer than level 0 blocks the course;
- **the slopes,** at the threshold gradient, 14° on soft soils to 33° on young ranges;
- **under ice,** a U-shaped trough: half-width 600 m at 10⁸ m³/year of ice, scaling with power 0.4, from 150 m to 1.5 km; overdeepened by 0.3 of its half-width, slopes at 40°; detail fades in its middle, where gullies from both sides would meet. Near a cold coast, its floor passes below the sea: a fjord;
- **the mesh:** a valley narrower than two grid cells widens, proportionally shallower.

**Incision moves coarse ground, rather than cutting it:** ground is lowered by how far the valley lies below large shapes and octaves above 20 km, through a minimum smoothed over 60 m, never below water level. Finer detail remains on slopes, reinforced up to 0.35 of the local incised depth: buttresses and gullies at slope scale, nothing extra on a plain.

**The floor joins water level in both directions (`ErosionCarve`):**
- **The fine residual is `h − coarse`:** simple coarse lowering let it dig pits and raise sills in trough centers.
- **The actually submerged plateau counts in full:** raw profile `bed` is bounded by `min(coarse, level)`; where this bound imposes water, the join removes the entire residual, positive or negative. `floorShare` alone was insufficient: the calm middle of the U ends before its entire underwater part.
- **Toward walls:** share `max(floorShare, 1 − smoothstep(0, 60, bed − level))`; same floor share, supplemented by the plateau actually bounded by water. A `smoothstep(0, 60, coarse − cut)` opens the join with incision; no incision, no change. Coarse terrain and profile remain intact.
- **Level always comes from the link read:** a level 0 lake retains its own level; no invented local water height. These floors indicate where river and lake water will be; it is not yet rendered.

**Deposits:** a delta, an offshore lobe 3 m above the sea, 60 √Q m, 1.6 times wider along the coast, its front descending toward the shelf; a fan, 120 √Q m downstream, 3 % slope, its foot at 45°. Both bounded to 0.25 cell, fading at 0.3 cell from their apex: the nodes read always contain them.

**Texture searches:** the 4 × 4 nodes around the point, each with its tributaries and receiver; a node farther than 1.75 cells is skipped; no valley reaches beyond 0.5 cell, or into sea deeper than 500 m. Positions are relative to the point, in floats: only one double-precision read per vertex.

**What detail reads from it is continuous:** valley depth and ice are the maximum of nearby link values, each fading before the links read change. Taken from only the lowest link, they jumped between links, taking detail with them.

## CPU measurements of rock gullies and open troughs, seed 0

**References on the same caches:** integration `fe22cfe`, D `1ca9743`, sources loaded directly through `git show`; no level 0 rebuild. Command: `python tools/hydro/verifie_erosion_roche.py`, or `--only windows`, `troughs`, `coasts`.

**Ranges seen from afar:** 5 × 5 km squares between edges, 201² points at 25 m, 25 m grid spacing; centered gradient, one-sided difference at the edge. Shares in percent.

| Site | Version | >35° | >45° | >60° |
|---|---|---:|---:|---:|
| −25.60 ; −26.94 | Integration | 56.867 | 40.472 | 7.039 |
| | D | 45.595 | 26.715 | 0.196 |
| | E | 51.432 | 44.746 | 6.307 |
| −46.9 ; −33.8 | Integration | 26.390 | 9.784 | 1.017 |
| | D | 5.745 | 0.183 | 0 |
| | E | 27.645 | 11.599 | 2.193 |

- **Same sampling, 5 m grid spacing for checking:** E range 51.662 / 44.454 / 6.903 %, E arêtes 29.455 / 12.178 / 2.205 %; finer crests better resolved.
- **C's protection still holds:** in the four 100 × 100 m squares at 1 m, zero above 45° and 60°, before and after E. D → E maxima: forest 30.648 → 31.358°, slope 22.577 → 20.052°, canyon 44.060 → 43.960°, flat 4.613 → 4.613°. Above 35°, only the canyon: 14.254 → 12.214 %.
- **The small arête window remains local:** over 100 m at 1 m, E reaches 14.626 % above 45°, zero above 60°, maximum 52.675°; it can fall on a single flank of a kilometer-scale band. E's rock check concerns the requested 5 km square, where walls above 60° are present. Noise without erosion remains compared through `valleys=false`; incised ground without gullies can change with the valley correction.
- **Band mean remains zero:** gain and rock share independent of current phase; same centered profiles, sharpening and rounding. Profile quadrature: error below 1.03·10⁻¹³ noise unit.

**Troughs:** 4 km squares, 161² points at 25 m; eight-neighbor flooding, open edges, 5 m grid spacing. First center at −25.545112988; −26.901313945, the reported offset of 2 325 m north and 1 475 m east; second at −25.486; −27.075.

| Area | Coarse-cut closure D → E | Water-bounded floor closure D → E | Maximum over the whole square D → E |
|---|---:|---:|---:|
| First trough | 72.964 → 0 m | 72.964 → 0 m | 72.964 → 57.498 m |
| Second trough | 441.570 → 0 m | 609.559 → 0 m | 681.453 → 65.790 m |

- **Remaining maxima lie outside incision:** ground 3 067.853 m versus water level 963.779 m for the first, 3 281.771 versus 1 225.714 m for the second; `coarse == cut`, `floorShare == 0`. They do not close trough floors.
- **True thalwegs are followed downstream:** link curve, then its receivers; inversion of angular warp, error below 3.4 nm. Routes of 5 002 and 5 046 m, without interpolating heights off the curve; CSV `x64/Release/erosion-e-thalweg-*.csv`.
- **Ground − water difference, first route:** D from 0 to +708.725 m at 5 m grid spacing, 0 to +690.982 m at 200 m; E zero at both spacings. E coarse cut − water: zero too.
- **Second route:** D from +571.903 to +3 177.031 m at 5 m grid spacing, +592.529 to +3 180.971 m at 200 m; E zero at both spacings, full and coarse ground. Water level descends along both routes.
- **Level 0 lakes:** sixteen lake outlets receiving a tributary; level read at their node within 0.000006 m of their stored level. Isolated lake cells have no level 1 curve; they are outside this check.

**Cliffs without coastal recalculation:** before/after comparison for removal of the block preserving bit-identical Hc. Same E port and current caches for both versions; reference `x64/Release/cp-avant-simplification-cotes.py`, SHA256 `b89e84542c3826aea5656bdc73315e366479693d32a10496781f5941f4c3ed01`. Measurement command: `python x64/Release/mesure-simplification-cotes.py`; output `verification-simplification-cotes.txt` in the same folder.

**Hc on the six coasts, median / p90 / maximum in m:** 60 km squares, 201² points, 10 m grid spacing; quantiles on each version's active points, like `distribution` in `verifie_falaises.py`.

| Center | Before | After |
|---|---:|---:|
| 8.54005 ; −103.23344 | 212.071 / 378.526 / 400.000 | identical |
| −23.01696 ; 158.00809 | 70.800 / 109.075 / 119.508 | identical |
| −3.34285 ; 169.01181 | 80.218 / 180.002 / 255.085 | 81.427 / 181.618 / 343.741 |
| −51.89165 ; −40.94037 | 54.558 / 133.074 / 214.107 | identical within 0.001 m |
| −8.11021 ; 131.04460 | 51.545 / 68.277 / 89.271 | 51.969 / 68.365 / 89.271 |
| 8.76166 ; −103.24998 | 170.834 / 345.453 / 400.000 | identical |

- **Main variation:** third-window maximum +88.657 m; median +1.209 m, p90 +1.616 m. The cap remains 400 m; the maximum must not be described as a small variation.
- **Ground before abrasion is bit-identical** in the six squares; only the slope supplied to Hc and the wave result change.

**The three fixed sections:** before = after at the stated precision; angle at 10 m spacing, platform adjacent to the face, land above +5 m up to the original sea.

| Section, latitude; longitude | Wall | Angle | Platform | Land in front |
|---|---:|---:|---:|---:|
| 8.72580 ; −103.29430 | 377.816 m | 84.91° | −1.412 m | 0 m |
| −23.18981 ; 157.86949 | 41.877 m | 72.47° | −1.099 m | 0 m |
| −3.21302 ; 169.26372 | 42.519 m | 75.64° | −1.540 m | 0 m |

**The three check windows, seed 0:** 10 km squares, 201² points at 50 m; before = after at the stated precision.

| Center | Landlocked share before → after | Marine reach p99 before = after |
|---|---:|---:|
| 8.73276 ; −103.30263 | 0 → 0 % | 1 138.519 m |
| −23.18173 ; 157.88952 | 0 → 0 % | 400.031 m |
| −3.21302 ; 169.26372 | 0 → 0 % | 683.482 m |

- **No cliff target fails:** three active faces, one above 100 m, before and after; no land sill in front of their foot, no landlocked cuts in these three windows, p99 below 4 km, lowering below Hc + 1 m. Full check `python tools/cotes/verifie_falaises.py` also reports `ok`.
- **Resources:** one `ErosionValleys` query, always on the sphere, and only the main `ReliefDetail` for `cliffSlope`; `sphere` / `project` parameters removed. No GPU time gain claimed without measurement.
- **Flight review:** `tools/tests/2026-10-31-cotes-sans-recalcul.txt`, without automatic launch; E's range route remains valid.

- **`valleys=false`:** bit-identical on 288 points × three grid spacings, seeds 0 and 1. Flat coast, 441 points at 16.71; −89.28: zero difference.
- **Simplification checks:** `cp.py`, before/after comparison and full cliff check report `ok`; Release x64 without errors or new warnings in modified files (`verification-build-simplification-cotes.txt`). The old Hc-identity assertion is removed; physical limits remain tested.
- **Limitations:** no engine or benchmark run; flight feedback remains necessary, `tools/tests/2026-10-31-ravines-roche-auges.txt`. Caches are not rewritten.


## 2026-11-01: rejected rock-only characteristic slope budget

Superseded by the shared turning envelope. Four CPU windows reproduce blades up to 514.73 m per one-metre step. The former specification follows.

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

## 2026-11-01: rejected depth-derived profile dilation

The following contract passed positive-depth area checks but moved unbounded banks when reference depth approached zero. It is replaced by a local profile mean.

- Width is measured at the exact intersection of the profile and its reference ground.
- A valley narrower than two grid cells widens; its depth and entire vertical section shrink in inverse proportion.
- This transformation preserves the incised cross-section area; the old formula did not contract the whole profile and could leave a U narrower than two grid cells.

## 2026-11-01: archive worktree closure

Historical checks before the current blade and approach corrections; these are not current validation results. Legacy hashes below identify archive-only references.

### Original verification

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

## 2026-11-01: rejected symmetric coastal talus

- The former support was `platform + max(talus - screeSlope*abs(h-Hc)/G, 0)`.
- Its mound fell on the landward side before meeting the cliff, making a false groove.
- The user's pose `28.7 -47.008952 -32.993928 62.67 -50.35` reproduced the defect exactly.
- Snow accumulated on both false ridges; changing the material would not repair the geometry.
- The old profile reversed slope in 288 of 384 parameter sections; the reported section dropped 7.39 m behind its crest.
- The replacement finds the contact on the cliff face and extends the apron seaward; see the current specification.
- Before the coastal metric correction, native color, snow and relief captures at the same reported pose removed the false groove and its two snow ribbons.
- A wider cold view and a tropical witness retained continuous coastlines; the southern witness still showed isolated inland pits.
- The physical coastal metric subsequently rejected the cold-location cut altogether; these screenshots describe the earlier metric, not the current terrain.

**Superseded specification:**
- **Scree:** 35° slope, up to 22 % of Hc, in 900 m patches; distance to the foot expressed by `abs(h − Hc) / G`.

## 2026-11-01: rejected mesh-scale coastal metric

- `ReliefCoastGradient` previously used all five coastal octaves and the rendering mesh's crease rounding.
- At the user's pose `254.1 34.983719 88.511430 43.46 -106.41`, a ria cusp produced a straight wall with thin needles.
- Across a 10 m cusp crossing, the metric changed from 1.31 to 5.93 and the cliff-height contour from 56.89 to 258.82 m.
- The same 128 m window sampled every metre contained a 172.67 m height step.
- The coast before wave erosion remained continuous; disabling wave erosion isolated the cause from the valley and mesh profile.
- Filtering only the source octave wavelengths would not remove an absolute-value cusp in their derivative.
- The replacement filters both the metric spectrum and its crease derivative at the existing 9 km physical scale.
- The second reported pose `78.3 34.977346 88.514165 4.61 -99.01` was in the same false excavation; its ground changes from 36.19 to 235.03 m.
- Local diagnostic captures and arrays are under `x64/erosion-walls/`; no performance or image-quality benchmark was run.

## 2026-11-01: hydrology composition audit

**Scope: diagnosis and proposed design, no generator change.**
- The user requested a structural response to ribbon-like rivers, perched channels, closed outlets, geometric junctions, coastal serrations and late visibility.
- Evaluator: current `tools/hydro/cp.py`, seed 0, existing `EXOEROS3` cache.
- The probes are functional terrain inspections, not performance or image-quality benchmarks.

**Perched river reproduction**
- Reported camera: `150.9 -12.406891 52.928246 26.44 -118.93`.
- A transverse section crosses the nearby wet channel at latitude -12.4068909864, longitude 52.9309713794.
- Section length: 5 km, 1,001 samples, 2 m terrain footprint.
- At its centre: parent before valley cutting 176.48 m, coarse support 372.46 m, valley stage 31.63 m, final bed 30.65 m.
- At -250 m across: pre-erosion ground 236.10 m, final ground -63.44 m.
- Disabling coastal erosion leaves this false side depression unchanged.
- No deposit raises the ground anywhere in the accompanying 12 km window.
- The cause is `surface = valleySurface + (height - coarse) * (1 - floorShare)`.
- Negative residual detail lowers the banks past their drainage level while the floor suppresses that same residual.
- The existing cut-only rule prevents raising the parent ground, but does not prevent manufacturing a deeper side channel.
- The 12 km window uses 81 by 81 samples and an 8 m footprint: 423 samples are cut below their channel stage despite starting above it; maximum undercut 278.25 m.
- Of those window samples, 350 move from positive parent elevation to negative elevation through valley cutting.
- These counts describe this sampled window, not planetary prevalence.

**Other observations and limits**
- The geometric-junction window at -12.486714, 52.694265 also contains newly manufactured side depressions; the closed-outlet window at -1.882499, 69.597920 does not reproduce this particular mechanism.
- The closed outlet therefore remains a separate connectivity investigation; it is not proven to be a delta-deposit defect.
- Coarse drainage stages and rendered paths use different sample positions, as shown by `ErosionForm`, `ErosionNode` and the later relief warp.
- The late-water failure is independently visible in `PixelShader`: finer terrain elevation is combined with a coarse-mesh water-depth cap.
- Local diagnostic arrays and the transverse plot are under `x64/water-approach/`; they are not checked into Git.
- No shader, geometry setting or executable was changed during this audit.
- The subsequent implementation and remaining revision are in `../spec-eaux-interieures.md`.

## 2026-11-01: bounded valley composition and floor coupling

**Superseded rules**
- Signed residual detail was added to the valley envelope, except on its floor; negative detail could dig a second, lower channel.
- The floor mask was set to zero on terminal links, restoring residual obstacles before the coarse outlet.
- The valley join used a constant 60 m depth even on the floor; an 8 m incision barely lowered the terrain and left a barrier.
- The final water pass used `min(terrain, channelBed)` with an unbounded bank profile, hiding incomplete floor construction by excavating another V valley.
- The replacement carries positive spurs, retains original hollows, couples the floor to the channel and bounds the final water cut by compact channel depth.

**Rejected absolute incision cap**
- The prototype bounded lowering by the coarse network's stored incision at every detailed sample.
- At the river witness -1.828016777, 69.643755616: parent 234.02 m, coarse support 197.51 m, stage 21 m and stored incision 31.625 m.
- This left the carved ground at 216.92 m and the bounded channel bed at 207.17 m; the formerly wet bed was 11.25 m.
- The cap cannot be used before reconciling the network's reference terrain with its rendered route.
- It is not integrated; no absolute network-incision limit is claimed.

**Focused checks**
- 20,000 random compositions preserve the original upper bound, the valley-envelope lower bound and existing hollows.
- 96,048 channel samples stay within physical channel depth; tributary switching stays continuous.
- Six terrain windows pass composition bounds; four earlier blade witnesses retain no slope above 80 degrees.
- The reported transverse bank minimum becomes 42.70 m over offsets 125–500 m; the wet centre retains 0.98 m depth.
- The two formerly dry outlet witnesses pass after the floor join fades to zero; all ten water windows pass presence and 2–16 m approach checks.
- Filter checks retain independent quadrature and derivative comparisons; the historical failure control restores both the old profile and the old signed-detail composition.
- The old blade reference reads the original six slices of the current EXOEROS3 cache through the current decoder; its geometry rules remain historical.
- Diagnostic logs and captures remain local under `x64/water-approach/` and `x64/inland-water/`.
- Release x64 passes with the floor join; the existing `Materials.hlsli:46` bit-shift warning remains.
- `composition-floor-join-perched.bmp` removes the side pools and opens the previously dry cross-ridge; its width remains visually uniform.
- `composition-floor-join-range.bmp` retains the massif's broad shape; repeated incisions and a few distant water/terrain artifacts remain visible.
- No performance or image-quality benchmark was run.

**Volcanic integration remains unresolved**
- These are diagnostic witnesses, not the unidentified crater reported by the user.
- Seed 0 volcano 15: centre 9.3391172538, -50.0430150622; freshness 0.97245; crater radius 2,492.49 m.
- All 128 nominal rim samples lose over 100 m; maximum lowering is 1,378.82 m with the first composition correction.
- Volcano 170: centre 11.6826844900, -51.4192830407; freshness 0.621637; crater radius 523.17 m; maximum rim lowering 980.69 m.
- Volcano 1002, a shield witness, has no rim lowering in the same inspection.
- Freshness currently modifies detail and materials, not drainage incision directly.
- A coarse support can miss a small closed crater; monotone graph stages cannot certify a real outlet through its rim.
- The evidence supports checking common terrain support, construction history and spillways before adding any volcanic exclusion mask.

## 2026-11-01: coarse water classification failure

- User orbital pose: `5717762.1 -13.777632 124.771150 84.18 43.01`, seed 0.
- `orbit-coast-before.bmp` reproduces the broad diamond/triangle coastal fringe at that pose.
- The old pixel shader selected inland water with `interpolatedStage > 0`, although dry land could carry its own positive height as the candidate stage.
- The type switch then replaced the finer ocean shoreline across whole mesh triangles.
- Fine elevation was shaded with `min(stage - fineElevation, meshWaterDepth)`, so dry coarse vertices could erase water resolved on the fine grid.
- Superseded rule: wet coverage required positive mesh water depth and the fine grid had no water samples.
- The replacement carries premultiplied wet quantities at both resolutions and composes independent ocean/inland coverages.
- The running erosion build was the Exolune checkout; terrain shaders dated 18:34 followed the 18:31 composition edit. Shader loading resolves paths beside the executable.
- The user subsequently accepted disappearance of the side trenches at F7/F8 of the extended mountain route; the other hydrology complaints remain in scope.
- Native captures `orbit-coast-after.bmp`, `orbit-water-river18km.bmp` and `orbit-water-river14km.bmp` confirm the removal of the orbital fringe and water presence at both approach poses. Serrated banks, regular junctions and reach interruptions remain; these still images do not validate motion stability.
- Additional witnesses: `orbit-other-coast.bmp`, `orbit-water-lake.bmp` and `orbit-water-mountain.bmp`. A second coast and a lake shoreline preserve their classifications. Mountain water is visible from the overview; its straight path and stair-stepped banks remain.

## 2026-11-01 one-sided coastal filter

- Superseded rule: `delta = max(0.1 Hc, 2 * cellMetres * G)` widened the cliff only landward.
- A 100 m cliff on a 0.2 source slope moved its crest by 78 m at 64 m cells, adding 13.54% to the excavated section.
- At 256 m cells the displacement was 462 m and the added section 80.20%.
- Replacement: compose the physical cliff, talus and min/max joins, then average its incision symmetrically.
- Independent quadrature: 1,440 cases, maximum discrepancy 3.74e-8 m; simulated float32 error 0.12 mm.
- Forty-five join checks and 384 talus sections pass; four terrain windows retain a bit-identical flat coast.
- These are local CPU proofs and witnesses, not global visual or temporal acceptance.

## 2026-11-01 pixel water contour refinement

**Report and reproduction**
- The user still saw moving orbital blocks and late, aliased river banks after the first water reconstruction.
- Latest orbital pose: `4957836.7 -13.909648 124.644062 84.18 43.05`, seed 0.
- Two native CINE reproductions use 120 frames at 60 Hz, 1280 by 720, clouds hidden, TAA unset and 60 warm-up frames.
- The orbital route approaches by 180 km while shifting latitude by 0.08 degrees and longitude by 0.13 degrees.
- The river route descends from the reported 18,045.3 m pose to 14,271 m over the same reach.
- Final artifacts: `x64/inland-water/motion-orbit-review/` and `motion-river-review/`; baseline folders end in `-before`.
- Inspected first, middle and last orbital frames retain the same coastal features without the former broad grid diamonds.
- The river's broad repetitive bank steps are strongly reduced. A narrow interruption in the actual bed remains visible at both ends of the approach.
- `contour-lake.bmp` retains a continuous shoreline; `contour-mountain.bmp` improves the narrow banks but still exposes a straight prescribed route.
- Interactive F4, F7 and F8 were checked after relaunch; F7/F8 still have no artificial side pools. The application was left on F1 in free camera at speed 5.77.
- These are targeted reproductions, not performance or quality benchmarks, nor acceptance of all locations and movements.

**Implementation checks**
- Candidate support survives dry grid samples; the pixel evaluates the shared physical terrain only near unresolved contours.
- Sixteen derivative-quad masks, 2,673 angle/grid-phase cases, 1,380 explicit intersection cases and four dry-floor scales pass in `tools/hydro/verifie_contours.py`.
- The noise table's 256 vectors are bit-identical; the shared frame is 4,800 bytes, with the table at offset 704 and a 4,864-byte constant-buffer allocation.
- Mesh vertices use 64 bytes and fine samples 32 bytes; existing resource bindings are retained.
- Release x64 passes in `x64/inland-water/build-contours-land.log`; the existing material bit-shift warning remains.
- The isolated D3D12 PSO check succeeds with no InfoQueue errors using the final paired shaders.
- A live F1 title showed about 7.64 ms GPU rendering, versus about 2.08 ms in the user's preceding screenshot. This is not a controlled comparison, but the added orbital cost is material and remains open.

**Rejected prototypes**
- FXC compilation of the expanded pixel shader stalled for several minutes; the terrain VS and PS now use DXC with HLSL 2018 syntax.
- Mixing the prior DXBC vertex shader with the DXIL pixel shader failed PSO creation because varying register packing differed; compiling both together resolves it.
- A quad wave-operation prototype was replaced with fine derivatives; no new WaveOps requirement is introduced.
- Divergent evaluations with a large negative clearance sentinel made false wet halos; common derivative-quad evaluation and bounded fallback remove that cause.
- A physical-width-only support cap clipped the averaged channel's halo; support now includes its filter radius.
- Symmetric inland coverage made exactly dry drainage-stage planes half wet; the final inland coverage remains zero at nonpositive clearance.
- Using the pixel-refined height for land materials exposed orbital snow and material hatching. The final query refines water only and retains the existing land-material bandwidth.
- Intermediate folders ending in `-after` or `-final` contain these superseded prototypes; `-review` contains the delivered contour version.

**Remaining limits**
- Pixel classification does not repair bed connectivity, coarse routing, width regularity, closed outlets or volcanic incision.
- Geometry, depth, normals and silhouettes retain their mesh/fine-grid sampling.
- The separate coastal mean composes before filtering; the upstream valley profile still needs equivalent intersection-aware filtering.
- Full wet-area integration below a pixel and the extra cost of contour terrain queries remain unresolved.

## 2026-11-02: valley profile averaged before clipping

Superseded by the clipped section mean (`../spec-erosion.md`, level 1). The former contract:
- **Mesh filtering:** exact local box mean of the physical fluvial/glacial section, with radius `max(cellMetres, CREASE_MIN_CELL)`.
- Averaging a convex section only raises its profile, by at most `maximumWallSlope × radius / 2`; far planar banks remain fixed.
- This is a local profile mean, not a claim of exact area conservation after clipping against arbitrary terrain.
- **Composition bound:** new excavation could not go below the averaged envelope; `verifie_composition.py` asserted it.

**Its defect, seen from orbit on 2026-11-02:** native captures of the massif at `-7.138614 122.604860`, from 2,400 to 900 km.
- No valley at 2,400 km; thin dendritic valleys at 2,000 km; full valleys by 1,400 km. A snowy range at `-25.6 -26.94` did the same between 1,600 and 1,200 km.
- The averaged floor stood above the ground once the box outgrew the valley's top width.

**A first correction, rejected in flight earlier on 2026-11-02:**
- It approximated the footprint mean of `min(ground, profile)` with a quadratic smooth minimum, `lerp(a, b, w) - k w (1 - w)`, for both the union of links and the ground crossing.
- Its rounding `k` came from slope differences times the footprint, with the large forms' gradient for the ground.
- It dug furrows along every divide between links, parallel to the valleys, and the ground trembled more.
- The crossing sat where the profile met the estimated ground, not the real one.
- The patch stayed outside Git, `vallees-empreinte.patch` in the scratchpad of the session that wrote it.

## 2026-11-03: step B's first corridors, before their sizing

Superseded the same day by the corridors sized by discharge (`../spec-erosion.md`, step B). The former contract:
- **Every link from 10 m³/s** drew a corridor and water, `RIVER_Q` (10, 15): 48 % of land links, 31 km apart over all land, 14 km on the wet plateau at −6.6°, 125.3°.
- **The floor** was the channel and its meanders' bound, 2W plus twice their amplitudes: ±4 % at a given discharge, 0.6 km at 10 to 30 m³/s, 4.9 km at 1 000 to 3 000 m³/s.
- **The walls** a smoothstep over the relief's height above the stage over 0.2 to 0.5, 300 m to 6 km: p10 300 m, p50 825 m, p90 3.3 km; at 6 km across the plateau.
- **Every course capped:** 71 % of river cells lowered, p50 50 m, p95 568 m, max 3.8 km.
- **The highest wet channel's stage** over overlapping water: a step at confluences, 8 cm at most then, 35 cm on larger rivers once sized.

**Its checks, 2026-11-03,** `verifie_couloirs.py` on the CPU mirror of the startup:
- **Stage:** no rise downstream over 513 000 links, no drop steeper than 3 %; 66 % of river cells lowered, p95 542 m.
- **Cap:** 99.4 % of the samples along the five sites' courses under the cap plus the fill; the rest on re-routed tributaries, whose junction the conditioning moved on 6 % of them.
- **Distance to the meandered course:** median error 0.1 % of the half-width, p95 1.6 %.
- **Continuity,** along 120 lines: the ground Lipschitz everywhere, the water at edges and joins; at confluences a water step of at most 8 cm.
- **Water against the prototype,** 20 windows: dry share and wet leaks equal or lower in each, as 0.073 / 0.073 and 0.189 / 0.189 on the snowy range at 10 km, 0.026 / 0.005 and 0.173 / 0.010 on the perched river.
- **Sheets:** `x64/etude-relief-couloirs-moteur`; route `tools/tests/2026-11-03-rivieres.txt`.
- **Cost per point:** 16 nodes read, 1 to 4 curves solved, up to 3 meanders; noise octaves added to step A's 27 to 55: 0 to 8 off the mountains, 8 to 30 in them.

**Its defect, seen from 465 km on 2026-11-03:** over the wet plateau, a valley of one width and depth on nearly every link, “drawn with a Photoshop brush of one size”; native captures in `x64/captures-taille/avant`.

## 2026-11-03: sizing handoff verification

**Superseded documentation**
- The spec header still named `erosion-globale`, tag `piste/erosion-globale`, and route `2026-11-01-auges.txt`; those refer to the earlier network-valley stage.
- The sizing draft mixed settings from several iterations: 50/100 m³/s and a 10 km corridor reach in geometry, versus 200/300/450 m³/s and 8.5 km in code.
- It reported 232 km globally, 64 km on the wet plateau and 37 km on its flank as river spacing.
- Those values were area divided by channel length, not distances between mountain-front outlets.
- The Hovius comparison and the former 30 m Earth-river density comparison did not validate the 300 m³/s cutoff.
- The live spec now distinguishes observational scaling laws, calibrated thresholds and inverse drainage density.
- First-corridor cap, continuity and cost results had also remained in the live sizing section; their original results are preserved above.

**Recovered failure**
- `python tools/hydro/verifie_couloirs.py` on the engine's `EXOEROS5` cache passed stages, widths and sampled caps, then failed confluence continuity.
- 22 corridor-edge lines and 22 joins passed; one of four confluence lines retained a 0.660 m depth jump when sampling was refined fourfold.
- Seed 0, receiver cell 1197130, inflow direction 1; water edge near latitude −6.25015352°, longitude 125.32594265°, terrain 1553.39 m.
- A neighbouring dry bank won the bed envelope below the wet channel's stage. The entering channel's compact cut was practically zero at its edge.
- Removing the tributary's blend taper did not change this failure; that option was discarded.
- Bounding water by the final bed plus the compact cut removed the isolated jump without changing bed heights.
- Before/final logs and native captures are local artifacts in `x64/erosion-reprise*`; current acceptance status is in `../spec-erosion.md`.

**Native review completion**
- The first capture pass stopped after F2 while other worktrees used the GPU; it resumed after the user's continuation request.
- Former F6/F8 camera altitudes, 362 m and 1014 m, triggered placement recovery on the revised terrain. Their current views start at 1100 m and 1800 m.
- The first F12 location no longer had a wet tributary at the new cutoff. Its replacement is a wet downstream confluence near −7.173005°, 125.036219°, at 3500 m camera altitude.
- Initial framings remain in `x64/erosion-reprise/initial-framing/`; the twelve final captures are in `x64/erosion-reprise/apres/`.

## 2026-11-03: widened banks and distance-dependent water

**Superseded construction**
- The compact water cut was averaged, but banks were moved from W/2W to W+r/W+r+max(W,r).
- Every positive averaged depth became full water presence; a 2 cm depth threshold could then erase a diluted river.
- Final composition forced every point in the filtered wet support down to the candidate stage minus the mean cut.
- A fixed row through the reported coast shows up to 4881 m of additional channel lowering with a 4 km radius, against at most 109 m with a 500 m radius. These are diagnostic samples, not a quality benchmark.
- Physical bank filtering and separate wet fraction supersede this construction. Morphology and density remain separate open issues.

**Reproductions, seed 0, sea-level camera poses**
- Wide river: `250325.2 -7.489828 125.499386 65.74 -9.13`.
- Thin/disappearing river: `172718.8 -7.189383 125.450731 65.74 -9.12`.
- Repeated coastal strokes: `863385.4 -11.180370 124.914240 65.06 30.66`.
- Native reference views: `x64/erosion-reprise/distance-avant/`.

**Superseded first distance-filter candidate**
- `x64/erosion-reprise/distance-apres/` predates the final composed-ground correction; its F12 is also an earlier mountain view rather than the current lake witness.
- Applying only the lowest channel bed omitted compact incision where a neighbouring corridor had already lowered the supporting ground.
- In a 64 by 64 confluence window near -7.173005, 125.036219, 113 of 522 resolved wet samples disagreed with their actual stage/bed gap; the maximum discrepancy was 3.178 m.
- The first native F11 showed trees over that falsely wet dry ground.
- The final composition also subtracts the compact mean cut from the composed support. The same window has no failing sample and a maximum discrepancy below 2e-13 m.
- Final native captures are in `distance-final/`; the current route uses an actual terminal lake for F12.

**Preceding sizing-review results**

**Current verification, 2026-11-03,** `python tools/hydro/verifie_couloirs.py`, using the engine's `EXOEROS5` cache:
- **Stage:** no rise downstream over 512 980 links; drops satisfy the 3 % bound within stored-stage precision. River nodes lowered on 57.7 %, median 19 m, p95 265 m.
- **Cap:** all 536 wet samples in the six inspected regions satisfy the sampled cap plus fill. Only one wet re-routed tributary is represented; this is not global connectivity validation.
- **Distance:** median error 0.1 % of nominal half-width, p95 1.5 %, maximum 19.8 % in the sampled courses.
- **Continuity:** 22 corridor-edge lines, 22 joins and four confluence lines pass the refinement check after the compact-cut bound. The former 0.660 m jump is absent; the largest adjacent water-depth change at the finer sampling is about 0.002 m in the confluence witnesses. This is sampled continuity, not global river connectivity.
- **Identity:** the pre-erosion form is bit-identical with step B on or off. The older-cache comparison is optional and was not repeated in this continuation.
- **Result:** the complete default CPU check passes; log `x64/erosion-reprise-checks-final.log`.
- **Build:** Release x64 passes through `tools/lance.ps1 -Build -NoLaunch`; log `x64/erosion-reprise-build.log`. The existing material bit-shift warning remains.
- **Saved sheets** require explicit `--sheets` and `--sheets-before`; they do not evaluate current code. Older prototype comparisons and cost counts are in [the erosion log](log/spec-erosion-historique.md#2026-11-03-step-bs-first-corridors-before-their-sizing).
- **Performance and image-quality benchmarks:** not run for this continuation. Viability and approach stability remain open.

**Review:** `tools/tests/2026-11-03-tailles.txt`; the reported plateau, its retained large river, former river sites, snowy terrain and confluence witnesses. Sizing still requires the user's flight review. The first step B version was reviewed before sizing, according to the handoff.
- **Native captures after the correction:** all twelve views rendered and inspected at 1280 × 720, in `x64/erosion-reprise/apres/`. F2/F3 retain the large river; F10/F11 show the corrected confluence; F12 shows another wet confluence downstream. F6/F8 frame the former small courses from above the current terrain.
- **Review limits:** captures verify framing and visible water, not continuous approach stability or global drainage. Ribbon-like channels, abrupt confluence shapes and small rivers omitted by the threshold remain visible limitations.
- **Interactive launch:** verified on 2026-11-03 through `tools/lance.ps1`, at the reported 465 km location, with the twelve-view route, clouds hidden and 1920 × 1080 full screen. User acceptance remains pending.

**2026-11-03 · Distance-filter baseline before morphology changes.**
- Release x64 passes through `tools/lance.ps1 -Build -NoLaunch`; existing material bit-shift warning only. Log: `x64/erosion-distance-build.log`.
- The full default `verifie_couloirs.py` passes: stages, sizing, sampled caps, curve distance, 22 edge lines, 22 joins, four confluence lines and pre-erosion identity. Log: `x64/erosion-distance-checks.log`.
- `verifie_filtre_rivieres.py` passes 103 independent section cases; normalized float32 error is at most 5.5e-6.
- A separate 64 by 64 resolved confluence window checks 522 wet samples: reported depth agrees with the actual stage/bed gap within 2e-5 m.
- All twelve final native captures are inspected in `x64/erosion-reprise/distance-final/`: the reported approach, three coastal scales, close rivers, two confluences and a terminal lake.
- The approach retains a thin course in the checked views; the second confluence no longer has the first candidate's trees over falsely wet dry ground. These captures do not validate every continuous flight transition.
- Uniform water ribbons and repeated valley walls remain visible. User acceptance remains pending.
- Interactive review was relaunched through `tools/lance.ps1`; F1 and all twelve palette entries were verified, with free camera and clouds hidden.
- The intermediate `distance-apres/` captures are superseded; their composed-ground failure is recorded in `log/spec-erosion-historique.md`.
- No performance or image-quality benchmark was run.

**2026-11-03 · Valley residual restricted below 20 km, superseded.**
- Native candidate `x64/erosion-reprise/distance-morphology-1/`: F1, F5, F6 and F9.
- Preserving only the residual below the coarse support retained small relief but left the orbital valley tubes almost unchanged.
- A local 40 km terrain probe retained at most 320 m; including the 50 km and 25 km detail octaves retained up to 1752 m at the same points.
- The second candidate therefore uses the pre-detail support, including volcanic edifices, without adding new noise or increasing the original terrain height.
- The initial 40 km meander extension also required a reach correction: wavelengths above 20 km now belong wholly to the bounded valley displacement. This was corrected before the native candidate above.
- An exponential width modulation was considered and discarded before native tests: filtering its input would change its mean width with distance. The retained modulation is linear and centred.

**2026-11-03 · Height preservation without outline confinement, superseded.**
- Twelve native captures in `x64/erosion-reprise/distance-morphology-2/`; F1, F5 and F6 inspected against the first candidate.
- Including the 50 km and 25 km mountain octaves retained real spurs but left the broad corridor outlines too regular.
- The next candidate also contracts local floor and wall widths around the positive terrain mass, independently on the two flanks.
- Source snapshot: ignored `x64/erosion-reprise/source-before-confinement/`.
- Full correctness passed before confinement: 22 edges, 22 joins, four confluence lines, stages, sampled caps, distance and pre-erosion identity. Log `x64/erosion-morphology-2-corridors.log`.
- Continuity witnesses now follow the actual displaced course; a 300 m line through the old graph could miss the river after adding larger bends.

**2026-11-03 · Confinement around the undisplaced axis, superseded.**
- Candidate captures: `x64/erosion-reprise/distance-morphology-3/`; the close confluence F9 exposed long narrow rock strips beside the water.
- The floor's minimum covered two channel widths around the valley axis, but the channel could meander outside that narrowed floor.
- The correction contains the displaced channel and both banks in the valley metric, extends its culling bound accordingly, and keeps spur recovery at the uncontracted floor scale.
- `verifie_morphologie.py` now independently constructs displaced-bank points and checks that every one stays inside the floor.

**2026-11-03 · Verification before the upstream bank-distance envelope.**
- Release x64 passes through `tools/lance.ps1 -Build -NoLaunch`; log `x64/erosion-morphology-build.log`.
- `verifie_morphologie.py` passes 4096 bounded terrain compositions, 4096 confined profiles, onset smoothness, resolved-width invariance and centred distant width; log `x64/erosion-morphology-invariants.log`.
- Across seed 0's full discharge range, the conservative corridor reach is 13 731 m; the fixed node-search contract is 14 094 m at cube corners.
- The full default `verifie_couloirs.py` passes: 512 980 stage links, 536 wet cap samples, base sizing, curve distance, 22 edge lines, 22 joins, four confluence lines and pre-erosion identity; log `x64/erosion-morphology-final-corridors.log`.
- Continuity witnesses follow the displaced river, including its larger bends. They no longer test only the undisplaced graph's neighbourhood.
- `verifie_filtre_rivieres.py` passes 103 independent section cases; normalized float32 error is at most 5.5e-6. All 347 resolved wet samples in the confluence window agree with the stage/bed gap; log `x64/erosion-morphology-water.log`.
- All twelve final native views are inspected in `x64/erosion-reprise/distance-morphology-final/`; the exact reported approach, coast, two other wet basins, confluences and a terminal lake.
- Additional 2 km windows in the southern and western basins check 518 and 716 resolved wet points against the actual stage/bed gap; log `x64/erosion-morphology-other-basins.log`.
- The native cache payload is byte-identical to the one used by the full correctness checks; the pre-detail-support and confinement changes do not change the conditioned stages.
- The reported approach retains a visible thin river in the checked frames. Original mountain masses survive in the sides, but the orbital network still reads as repeated corridors; the Alpine hierarchy is not achieved.
- Narrow exposed bank strips remain prominent at the confluence despite the displaced-bank containment correction. The raw relief witness is `x64/erosion-reprise/confluence-relief.png`; do not claim that all apparent fins or bank shapes are fixed.
- These static views do not certify continuous flight transitions. User acceptance remains pending.
- Interactive app relaunched from this worktree with the twelve-view route, clouds hidden and a 1280 × 720 window; the process is responsive and rendering. It starts in cockpit mode; no UI control was used to change it.
- Earlier candidates and their verification are archived in `log/spec-erosion-historique.md`.
- No performance or image-quality benchmark was run.

**2026-11-03 · Width-only spur recovery, superseded.**
- Recovery reached its full share at four channel half-widths or 0.6 of the valley floor, regardless of the retained mountain height.
- The user reproduced a long slot at `3840.6 -5.038412 124.886462 13.17 -102.18`. On 29 cross-sections over 18.9 km, the old recovery raised the ground by up to 667 m within 300 m of the small channel.
- A prototype enlarged the recovery interval in proportion to spur height. It reduced the slots but could recover less height when the original mountain grew; it was not shipped.
- The retained fix limits added height by available bank distance with a monotone soft cap; current formulas and verification are in the living spec.


**2026-11-03 · Upstream baseline before approach and bank refinements**

**Current verification, 2026-11-03:**
- Release x64 passes through `tools/lance.ps1 -Build -NoLaunch`; log `x64/erosion-amont-build.log`.
- `verifie_amont.py` passes monotonicity, C1 joins, unchanged small lifts with ample room, and 29 composed cross-sections over 18.9 km of the reported course. Maximum rise within 300 m of the channel falls from 666.6 to 146.4 m; water coverage is identical. Log: `x64/erosion-amont-regression.log`.
- `verifie_morphologie.py` passes the bounded terrain, confinement, physical-width and search-reach invariants; log `x64/erosion-amont-morphology.log`.
- `verifie_filtre_rivieres.py` passes 103 independent filtered-section checks and 347 resolved confluence water samples; log `x64/erosion-amont-water.log`.
- The full default `verifie_couloirs.py` passes: 512 980 stage links, 536 wet cap samples, curve distance, 22 edge lines, 22 joins, four confluence lines and pre-erosion identity. Log: `x64/erosion-amont-corridors.log`.
- All twelve native frames in `x64/erosion-reprise/distance-amont/` are inspected, plus the terminal-lake witness in `distance-amont-lake/F12.png`. The reported slot is absent at the exact camera pose; broad-valley witness F5 retains its large form.
- The native stage-cache payload is byte-identical to the cache used by the correctness suites.
- The upstream close view is partly obscured by canopy. Water remains overly regular in some views, and the orbital network still repeats broad corridors; this correction does not establish the Alpine tributary hierarchy.
- These static captures do not certify every location or continuous approach. Flight review: `tools/tests/2026-11-03-amont.txt`; no performance or image-quality benchmark was run.
- The interactive app is relaunched on that route at the reported position, windowed with clouds hidden; the worktree process is responsive and rendering. Backspace then F1 restores the exact free-camera pose from cockpit mode.
- Previous morphology verification and discarded recovery variants are archived in `log/spec-erosion-historique.md`.


**Rejected approach candidates**
- Point-sampling the composed valley profile loses or oversamples narrow valleys when coarse cells move. The retained filter integrates the signed local incision, including spur recovery.
- A vector `lerp` selected between the retained lift and an unused cap with a nearly zero divisor. Float cancellation produced tall parasitic walls in native approach frames. The stable minimum bounds the divisor before evaluation; `verifie_approche.py` exercises 26,123 float32 cases.
- Enabling the same fan on high-relief coastal outlets widened mountain valleys excessively. Fan eligibility now includes the terminal wall scale as a coarse coastal-relief proxy. This is calibrated eligibility, not a resolved sediment or coast-routing model.
# Junction and first-water follow-up, 2026-11-04

**Rejected intermediates**
- The first confluence widening used 0.7 receiving half-width over six combined half-widths. The user still observed angular banks and a pale internal sill.
- The terminal fan initially held constant spread after its sea node. Continuing its opening removed that mathematical plateau, but native F8/F9 still exposed canals crossing lakes and coastal islands.
- Those captures are local ignored evidence: `x64/erosion-reprise/distance-refinements/` and `distance-refinements-splay/`. They are not acceptance of the later contact rule.
- Taking the minimum absolute wet-bed elevation removed a color sill but introduced jumps where a lower-stage course first entered the support. The independent continuity check found a 1.287 m step.
- The next candidate retained the maximum compact cut and imposed a matching bed as coverage approached one. Its pre-contact continuity checks passed, but that coverage-dependent excavation was subsequently removed. Resolved shading now reads the actual water column without an extra terrain cut.
- The post-contact continuity suite found a separate 1.207 m water-depth jump. Longitudinal handoff zeroed the tributary's stage weight while its wet incision remained and the narrower main course did not cover it. Removing that handoff preserves the water level throughout the actual wet support; the regression remains covered by the corridor suite.

**Superseded approach verification, 2026-11-03**
- Six CPU suites passed before the later junction and contact changes. The tested tributary opened 96 to 184 m near its join and retained 92 m upstream.
- The first fan witness spanned 1,536 m versus 296 m without the fan. The continuous terminal version spanned 1,512 m versus 324 m.
- The earlier physical reach bound was 13,896 m against the 14,094 m corner contract.
- `approach-final/` contains 224 native frames, from 1,200 km to the bank. `distance-refinements/` contains twelve poses. The coastal traces were subsequently rejected by the user.
- Their stage payload remained `b537f704e1bd60f92ee018b7131ce2d08ee8aaeab0d1ee8449395031abd83308`; the later first-water cache has a new schema and must be rechecked.

**2026-11-04 · Before surviving-midpoint and wet-bank corrections**
- The later coastal counterexample revealed discharge fading before its contact. These captures and measurements describe the preceding implementation.
**Previous verification:**
- Release x64 succeeds (`x64/erosion-wet-support-build.log`). Twelve fixed native views and a 224-frame orbit-to-bank descent are captured; user flight acceptance remains pending. Superseded captures and measurements are in `log/spec-erosion-historique.md`.
- `verifie_approche.py`: 256 composed sections against dense independent quadrature, maximum normalized error 0.000272; 48 footprint/phase combinations preserve incision area within 0.2%; 26,123 float32 cap cases within 2.5e-7 relative error; 480 footprint-edge searches retain neighbouring candidates.
- `verifie_raccords.py`: the isolated tributary stays 122 m wide upstream and opens from 102 to 240 m near the join. The low-coast fixture has three separated channels over 1,512 m versus 320 m without the fan; the high-relief outlet stays excluded. A four-times finer step reduces the largest wet current change by 0.250.
- `verifie_amont.py`, `verifie_morphologie.py` and `verifie_filtre_rivieres.py` pass. The physical reach bound is 13,920 m, within the current planet's 14,094 m corner contract. Independent bank integration covers 103 sections with float32 relative error below 2.6e-6; 439 resolved confluence samples match the stage/bed gap.
- `verifie_contacts.py`: all 1,572,864 nodes match independent runoff accumulation and preserve the sink balance; 11,766 graph links stop at first water. On the coastal witness, 100 of 101 formerly wet samples lose disconnected continuations. Four termination footprints match independent quadrature.
- The corridor suite's stage, cap and distance checks pass on the contact cache: 440 wet cap samples, none above cap plus fill; normalized distance error p95 0.040. After removing longitudinal handoff, the complete continuity check passes 17 edge lines, 17 joins and four confluences; largest sampled water steps are 0.003 m and shrink with the sampling step. Pre-erosion and old-network identity checks pass. Logs: `x64/erosion-final-corridors.log` for unchanged stage/distance checks, `x64/erosion-wet-support-check.log` for the corrected continuity, `x64/erosion-final-identity.log`.
- Review route: `tools/tests/2026-11-04-approche-berges.txt`; native descent source in ignored `x64/erosion-reprise/approach-ground.cine`.
- Native descent: `x64/erosion-reprise/approach-contacts-final/`, exit code 0, from 1,200 km to about 8 m above the bank. Inspected samples at 417, 145, 50, 17, 6 and 2.2 km, then near the bank, retain the corridor and water without the earlier giant-wall regression. This sampled review does not certify all temporal behaviour over the planet.
- Native `distance-contacts-final/F08.png` removes the reported island and bay continuations. F6 also removes the former grey fragments at the tributary handoff and retains continuous water at the junction.
- The regenerated native cache payload is identical to the tested payload: SHA-256 `98b849141acfa28264b0a310564f04cbae406bc78cbde7fc8d925d1a97a36e3f` (bytes after the 24-byte header).
- F10 exposes a remaining fan limitation: one side distributary ends on land because the three branches share the centre course's contact. Independent distributary routing/contact remains required; this view is not accepted delta morphology.
- F12 exposes the pre-existing coarse basin-stage boundary near a lake inlet. First-water termination does not resolve that straight water-surface boundary; basin connectivity and spillways remain open.
- F11 has grounded gravel and tufts with no reported floating instances, but its exposed margin still looks plain. This is not acceptance of the full bank-material/geometry refinement.
- No performance or image-quality benchmark is run. The full planetary network, connected minor tributaries, sub-threshold streams and detailed coastal routing remain open.

**2026-11-04 · Rejected first mouth/bank native review**
- Release builds `erosion-mouth-banks-build.log` and `erosion-mouth-banks-final-build.log` succeeded. Twelve native views are in ignored `x64/erosion-reprise/distance-mouth-banks/`.
- F1–F3 still show a rectangular coastal pool and a coloured stripe through its river. The native cache payload matches the earlier contact payload; this is a rendering/composition defect, not an inconsistent cache.
- Wave erosion remapped a river floor that was already lowered. Centre-ordered interval accumulation also missed the trunk where a narrower nascent branch lay inside it.
- The isolated discharge and bank-section checks passed, but did not cover either composed failure. The current checks include independent coastal substrates and exact interval partitions.
- The combined CPU correction removes all 1,232 formerly false-sea samples in the reported 6 km window; native confirmation belongs to the current spec.

**Superseded mouth/wet-bank verification before the head-growth follow-up, 2026-11-04**
- Release x64 succeeds (`x64/erosion-coast-composition-build.log`). Twelve native views and a 224-frame descent are captured. The rejected false-pool/dry-stripe candidate is archived in `log/spec-erosion-historique.md`.
- `verifie_embouchures.py`: all 385 visible interrupted midpoints, including 26 connectors, agree on incoming discharge. The reported reach remains wet at 257 successive samples. The isolated mouth opens from 173 to 484 m before contact; sea and elevated-lake apertures coincide and stages meet the receiving level.
- `verifie_filtre_rivieres.py`: independent quadrature conserves 120 wet and 103 dry sections. Float32 relative error stays below 2.9e-5 and 2.6e-6 respectively. All 452 resolved confluence samples match the stage/bed gap.
- Additional mouth regressions cover 3,002 interval unions and six nascent fans without dry strips; five coastal substrates agree with the independent river-free terrain. The reported window no longer contains the spurious marine pool.
- `verifie_contacts.py`: all 1,572,864 nodes match independent accumulation, 11,809 interrupted links and conserved local runoff. Four physical termination filters pass. On the original coastal witness, 120 of 124 formerly wet samples lose disconnected continuations.
- Approach, junction/current, upstream and morphology checks pass on the new CPU rules. The physical search bound remains 13,920 m within 14,094 m; existing graph traces and pre-erosion terrain are unchanged.
- Complete continuity passes 17 edge lines, 17 joins and four confluences. Maximum sampled water steps are 0.010, 0.002 and 0.009 m and shrink with the sampling step. Both pre-erosion and legacy-network identity pass (`x64/erosion-coast-final-continuity.log`).
- These contact, mouth, junction, bank and continuity checks use the regenerated native cache. Its payload SHA-256 is `7e8bd8851a671d7666f04b9f16149a4991801257ff4ea86ee6876d5c2a9a8755`, after the 24-byte header. Logs: `x64/erosion-coast-final-{contacts,mouths,junctions,banks,continuity}.log`.
- `tools/verifie_ecume_cotiere.py`: 10,000 wave/depth cases against independent quadrature; maximum probability error below 0.00012. Mixed-coast foam decreases as the unresolved depth range grows; crest, trough and deep-water limits pass.
- The physical coastal-profile filter passes. The separate `verifie_pied_falaise.py` assertion "No current cliff exercises the talus" fails identically on the saved pre-composition source/cache and current code: its four historical witnesses no longer activate the tested talus. This fixture limitation remains open; it is not a passing regression check. Logs: `x64/erosion-coast-cliff-check.log`, `x64/erosion-reprise/cliff-before-composition.log`.
- Current route: `tools/tests/2026-11-04-embouchures.txt`. Native captures are in `x64/erosion-reprise/distance-mouth-coast-final/`. F1–F3 remove the false coastal pool and internal stripe, retain continuous water and open the mouth. F4 retains the removed bay crossings; F5–F6 retain continuous confluence water; F7 retains the corrected upstream valley; F11–F12 cover orbital distances.
- Native descent: `x64/erosion-reprise/approach-mouth-coast/`, 224 frames from 1,200 km to about 8 m above the bank; sampled sheet `approach-mouth-coast.png`. Inspected samples retain the corridor without the earlier giant-wall regression. Static samples do not certify all temporal behaviour or planetary locations.
- Remaining visible limits: F8 has a side distributary ending on land; F10 has a coarse, straight basin-stage boundary; F9 retains a plain bank finish. These are not accepted natural morphology. Independent distributary contacts, continuous basin boundaries/spillways, connected minor tributaries and physical sediment budgets remain open.
- No performance or image-quality benchmark is requested or run. User flight review remains pending.
