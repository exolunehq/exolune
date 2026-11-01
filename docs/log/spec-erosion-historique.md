# Erosion spec history

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
