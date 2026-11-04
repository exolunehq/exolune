# Passation : chantier de l'érosion (2026-11-04)

Pour reprendre le travail sans l'historique de la conversation. À lire d'abord : `AGENTS.md`, `docs/principes.md`, puis `docs/spec-erosion.md` (sections « step A » et « step B ») et `docs/spec-eaux-interieures.md`.

## Où on en est

**Paused at the user's request, 2026-11-04, 16:58 Paris: high-altitude performance**
- The user is rebooting because the system is overloaded. Stop here; do not resume experiments before a new request. No erosion engine, diagnostic engine or compiler remained running at the stop check.
- The performance fix is NOT validated. Timings varied substantially during the overloaded session. After reboot, establish comparable observations before attributing the remaining cost to a particular shader change.
- Worktree: `C:/Users/etien/Documents/repos/Exolune-erosion`, branch `claude/erosion-montagnes`. Preserve its extensive pre-existing changes. No benchmark, commit, tag or push was run. No interactive app was relaunched at the stop.
- Current production changes: zero-weight river noise pruning; unused dry/interrupted confluence metadata pruning; tighter interior footprint bounds with the original face-edge halo; one shared screen terrain loop; exact reuse of an identical sea-level ray hit; 8 by 8 screen dispatch; terrain cache key restricted to the wave height margin actually read; a separate screen-relief GPU timestamp in the title.
- The last production revision also skips fully filtered meander budgets, dry sections beyond their longitudinal support, and zero-result fill-only integrals. Split and unsplit corridor quadrature share one integral call site. No morphology constants or sampling resolutions changed.
- Last full Release build PASSED: `x64/erosion-filtered-sections-build.log`. Sources and `x64/Release` agree. Correctness: 9,216 composed samples match the preceding revision exactly, including footprints 9,999 / 10,000 / 10,001 m; `x64/erosion-filtered-sections-identity.log`. Approach/quadrature checks pass in `x64/erosion-filtered-sections-approach.log`.
- Earlier exact checks: 126 noise cases, 56 without lattice access, 7,200 composed samples; tighter footprint search retains 8,544 sampled interior edge searches and leaves nine tested seam halos unchanged; 2,880 composed samples unchanged. Logs: `x64/erosion-river-footprint-check.log`, `x64/erosion-river-footprint-approach.log`. Earlier retained morphology/contact/confluence suites passed before the final exact pruning.
- Native cache remains EXOEROS6, 50,331,672 bytes; payload SHA-256 after 24 bytes: `c13c3cc07c544a81f70e30b94a4c9f2bbbffc1642d4d4ed549c6031c524fb108`.
- Review route: `tools/tests/2026-11-04-altitude-rivieres.txt` (eight poses). Native captures only, no global desktop capture. Latest production evidence is `x64/erosion-reprise/distance-river-filtered-sections/`: F1 about 1,231 km, F3 about 2,998 km, F8 about 9,998 km. Last caption compute observations were 16.3 / 118.5 / 639.8 ms; these are NOT benchmark results or a verified improvement under comparable system load. The screen pass accounts for almost all the stationary cost at these heights.
- Earlier production capture phases: `distance-river-filter-cost-before/`, `distance-river-filter-cost-after/`, `distance-river-screen-loop/`, `distance-river-footprint/`, `distance-river-screen-tiles/`, `distance-river-cache-key/`. Before-this-task observations were 65.4 / 206.2 / 344.4 ms for the same three poses; do not compare them statistically with the overloaded final observations.
- IMPORTANT: `x64/erosion-reprise/diagnostic-relief/` contains an isolated copied executable, shaders and caches. It is NOT the production build. Experiments there removed corridor integration, clipped compact support, simplified unperturbed profiles, moved a discharge gate, forced a 512-cell size, regrouped active scans, or restored original course code. None of these later experiments was copied to production. The regrouped scan was slower. The last diagnostic uses the original pre-task river code with the newer screen loop/tiles; its final caption was also very slow (764.3 ms), reinforcing the need to retest after reboot.
- A CPU prototype of compact-support quadrature retained 7,168 composed samples exactly: `x64/erosion-compact-support-identity.log`. It is still only a prototype. A possible shader specialization for fully filtered river octaves was only considered, never implemented or validated.
- Source backups in `x64/erosion-reprise/`: `source-before-river-filter-cost/` (before this task), `source-river-filter-prune-only/`, `source-river-footprint/`, `source-before-filtered-sections/`. They preserve the confluence and valley work; never reset to repository HEAD to undo this task.
- Existing morphology limitations and the accepted confluence work below remain. Documentation of performance trials is provisional; complete or archive it after stable post-reboot verification. The next requested milestone tag is deferred to a requested commit.

**Retained preceding work, 2026-11-04: asymmetric confluence banks**
- **Request:** two satellite confluence references, with a pointed upstream land tongue, asymmetric banks and sediment bars. Continue universal planetary corrections.
- **Change:** replace the symmetric 1.15 receiving-half-width addition by physical receiving-width matching. `RIVER_CONFLUENCE = (0.5, 9)`; open only the downstream-facing bank by the width deficit. Match wider tributaries down; equal-width joins add no bulb. Bound the approach by the connector's own length.
- **Direction:** actual receiving flow includes its meander slope. A signed smoothstep to sin(12 degrees) removes opening near parallel alignment, preventing a full bank flip as octaves filter. First coarse-heading candidate corrected after three of 584 planetary connectors selected the wrong side.
- **Shared geometry:** bed, banks, wet support, current area and floor clearance use the same shifted section. Conservative reach uses the wider receiving/tributary width. Raw controls, stages, discharges, contacts and fan controls stay unchanged on 256 planetary nodes.
- **Release:** `x64/erosion-confluence-flow-banks-build.log` succeeds. The earlier `erosion-confluence-banks-build.log` is the intermediate coarse-heading candidate.
- **Checks:** 240 physical sections; 584 real connectors, including 24 near-parallel openings. Seven other correctness suites pass. Regional continuity: 36 edges, 36 joins, ten confluences; max ground refinement ratio 0.28, max water step 0.012 m. Logs: `x64/erosion-confluence-flow-banks-*`.
- **Core:** monotone/grade bounds on 512,980 links; 454 wet cap samples and original/legacy terrain identity pass in `erosion-confluence-banks-core.log`. Independent runoff accumulation matches all 1,572,864 nodes and 19,033 stopped links.
- **Native review:** all seven final captures inspected in `distance-confluence-flow-banks-final/` (F1, F2, F3, F4, F5, F7, F9). Compared F1–F3 lose the round protrusion and retain the upstream tongue. F4 is still a thin feeder into a large channel; no sediment bars are claimed. Mouth remains connected; straight lake-stage boundary and repetitive orbital valleys remain visible. The intermediate twelve-view set is `distance-confluence-banks-coarse-heading/`, not the final build. Before captures F1–F3 are in `distance-confluence-banks-before/`.
- **Final cache:** payload remains bit-identical to the baseline, SHA-256 `c13c3cc07c544a81f70e30b94a4c9f2bbbffc1642d4d4ed549c6031c524fb108` after 24-byte header. No new contact/stage graph needed. Log `erosion-confluence-flow-banks-native-cache.log`.
- **Interactive review:** relaunched with `tools/tests/2026-11-04-confluents.txt`, `-SansNuages -Resolution fenetre -Position '3500 -7.173005 125.036219 90 0' -Soleil '20 120'`. The erosion engine alone is responding and rendering, verified at 14:54 (PID 7164). Backspace leaves the cockpit; F3 restores this exact confluence pose.
- **Route:** F1/F2 same confluence at two distances, F3 another, F4 near-parallel confluence at -32.328588383, 85.669690200; F5–F12 retain mouth, fan, lake, heads, massif, upstream canyon and approach views. User flight review remains pending.
- **Limits:** confluence sediment bars/scour are not modelled. The previous unresolved orbital repetition, long estuaries, independent fan contacts and straight lake-stage boundary remain. Sources and rules are in `docs/spec-erosion.md`.
- **Return:** ignored `source-before-confluence-banks/` and `erosion-before-confluence-banks.bin`. No benchmark, commit, tag or push.

**Previous follow-up, 2026-11-04: dry heads and real mouth scales**
- **Request:** pointed heads nearby still look like round brush strokes from orbit; verify mouth widening against the user's Google Earth references. Keep universal planetary rules.
- **Change:** `RIVER_Q` is now (100, 300, 450) m³/s. Dry depth and widths share `smoothstep(100, 300, Q)` in linear discharge. Mature profile share and water thresholds stay unchanged. Raw-flow bounds reject inactive catchments early; dry-course reach includes its actual maximum growth share.
- **Status:** Release succeeds, `x64/erosion-head-growth-build.log`. The rejected 32 m³/s sixth-order candidate and its excessive evaluation work are archived in `docs/log/spec-erosion-historique.md`. Its `distance-head-scale-after/` captures are NOT the final build.
- **Correctness:** all 1,572,864 nodes pass independent runoff accumulation with 19,033 stopped links. Original graph, drainage/basin stages and local runoff are unchanged. Cache payload SHA-256 `c13c3cc07c544a81f70e30b94a4c9f2bbbffc1642d4d4ed549c6031c524fb108`. Logs `x64/erosion-head-growth-*`.
- **Continuity:** 36 edge lines, 36 joins and ten confluence lines pass in three regions. A 0.10 m dry notch initially escaped the broad test grid; local refinement proves continuity (0.02144 to 0.00536 m steps). `verifie_couloirs.py` now reports witnesses and resolves suspect peaks without relaxing its threshold. It supports `--continuity-site` for separate region runs.
- **Other checks:** new `verifie_tetes.py`, approach, upstream, morphology, mouth, junction/current, bank quadrature and pre-terrain/legacy identity pass. Native cache has been regenerated; do not use the earlier candidate cache to claim final results.
- **Visual evidence:** all twelve views in `distance-head-growth-final/` inspected. Five original before views in `distance-head-scale-before/`. Heads extend more gradually near the reported source; F2 still has overly regular large corridors. This is an incremental improvement, not a complete orbital-shape fix.
- **Descent:** 160 native frames in `approach-head-growth/`, five spaced frames inspected. Final separate capture `head-ground-end.png` confirms 39.5 m above ground; the dark close view is within dense tree crowns. No global desktop capture.
- **References:** inspected Gironde and Somme in a separate Earth tab, preserving the user's original tab. Somme entrance measured approximately 5.2 km; primary sources give Gironde over 75 km long and up to 12 km wide. Large bay/tidal-flat envelopes are not liquid-channel widths. Sources, calibration and current model limits are in `docs/spec-erosion.md`.
- **Mouth scope:** current aperture remains 173 to 484 m on the witness, over roughly 700 m. No enlarged universal funnel or long estuary implementation was added. Next work must carry receiving-water influence upstream, distinguish channels from shallow basins/flats, and use confinement/coastal regime.
- **Remaining:** orbital corridor repetition, finer tributary hierarchy, estuarine basins, independent branch contacts (F10), continuous lake-stage boundaries (F11), bank finish. The earlier inactive coastal-talus test remains documented; not rerun for this head-only change.
- **Interactive review:** launched at 14:10 with `tools/tests/2026-11-04-tetes-estuaires.txt`, `-SansNuages -Resolution fenetre -Position '96901 -6.185543 125.892589 71.08 20.55' -Soleil '20 120'`. F1/F2 latest near/orbital poses, F3/F4 head approach, F5/F6 other massifs, F7–F12 retained river/water witnesses. Backspace leaves the cockpit, then F1 restores the exact pose.
- **Return:** ignored `source-before-head-scale/`, `erosion-before-head-scale.bin`. No benchmark, commit, tag or push.

**Previous follow-up, 2026-11-04: continuous mouths and physical wet banks**
- **Status:** Release x64 succeeds (`x64/erosion-coast-composition-build.log`). Twelve native views in `x64/erosion-reprise/distance-mouth-coast-final/` confirm continuous water, an open mouth and removal of the false coastal pool/stripe in F1–F3. The first candidate is rejected and archived in `docs/log/spec-erosion-historique.md`.
- **Universal rules:** the latest user reminder is explicit in `AGENTS.md` and `docs/principes.md`. Reported coordinates are regression witnesses, never production conditions.
- **Discharge:** both halves of an interrupted edge retain the surviving source discharge at their shared midpoint. The disconnected receiver's remaining local runoff belongs to a separate catchment. Raw meander geometry remains unchanged.
- **Mouth:** open over eight nominal half-widths before the cached contact, bounded by the owning part. Stage and dry-bank height meet the receiving sea or lake continuously. This is not a sediment-evolution model.
- **Wet bank:** flat core and cubic shoulder over `min(W, max(2 m, 4 depth))`; exact section mean and matching current area. Physical width, maximum depth and old level-0 geometry stay unchanged.
- **Coast composition:** marine erosion reads the substrate before step-B corridors; its result intersects the river envelope. It no longer remaps a lowered river floor into a rectangular sea pool. Contacts read actual ravine/coastal/finished terrain with courses disabled (`ReliefElevation(at, true, false)`).
- **Wet union:** exact inclusion/exclusion of three fan intervals handles contained branches. The former centre-order assumption could mark a deeply cut trunk as dry. The combined coast/union fix removes all 1,232 false-sea CPU samples in the reported window.
- **Coastal foam:** incident FFT height moments feed a water-conditioned mean over unresolved shore pixels. The spare moment channel is reused without a new texture fetch.
- **Final cache:** native regenerated `EXOEROS6`; payload SHA-256 `7e8bd8851a671d7666f04b9f16149a4991801257ff4ea86ee6876d5c2a9a8755` after the 24-byte header. Independent accumulation agrees on 1,572,864 nodes and 11,809 stopped links, with conserved runoff and unchanged raw graph.
- **Correctness:** 385 interrupted midpoints including 26 connectors; 257 wet samples along the reported reach; aperture 173 to 484 m; 120 wet and 103 dry quadratures; 452 resolved confluence samples; 3,002 interval partitions, six nascent fans and five independent coastal substrates. Continuity passes 17 edges, 17 joins and four confluences; original-terrain and legacy-network identity pass. Logs: `x64/erosion-coast-final-{contacts,mouths,junctions,banks,continuity}.log`.
- **Other checks:** retained morphology, approach, upstream geometry and physical coastal profiles pass. Foam passes 10,000 independent quadratures. `verifie_pied_falaise.py` still fails because its four historical witnesses no longer exercise the talus; the saved pre-composition source/cache fails identically. Details and both logs are in the current spec.
- **Descent:** `x64/erosion-reprise/approach-mouth-coast/`, 224 native frames from 1,200 km to about 8 m above the bank; sampled sheet `approach-mouth-coast.png`. No earlier giant-wall regression in inspected samples. This does not certify all temporal behaviour or planetary locations.
- **Open structural work:** F8 still has a distributary ending on land; F10 retains a coarse straight lake-stage boundary; F9's bank finish remains plain. Independent distributary contacts, continuous lake-basin boundaries/spillways, minor tributary hierarchy and richer bank finish remain required. Do not describe those views as accepted natural morphology.
- **Interactive review:** relaunched at 12:24 with `tools/tests/2026-11-04-embouchures.txt`, `-SansNuages -Resolution fenetre -Position '3226 -9.027692 127.426786 70.69 -165.64' -Soleil '20 120'`. Correct worktree process verified responding and rendering, alone on the GPU. It starts in cockpit mode; Backspace then F1 restores the exact free-camera report. F1–F12 cover the current route; user flight review remains pending.
- **Evidence and return:** `second-mouth-before.png`, `source-before-mouth-banks/`, `erosion-before-mouth-banks.bin`, `source-before-coast-composition/` and diagnostic fields under ignored `x64/erosion-reprise/`. Earlier sections below are historical. Use native game captures; no global computer control. No benchmark, commit, tag or push.

**Previous follow-up, 2026-11-04: junctions, heads and first standing water**
- New reports: angular junction banks, an internal pale water sill, straight fine banks, blunt valley heads, and rivers crossing lakes/bays then reappearing on the far shore.
- Implemented: arrival range 12–55 degrees; opening 1.15 receiving half-width over nine combined widths; world-fixed bank-edge displacement and physical shoulder; deepest compact wet-section union; continuous lake-current attenuation; dry heads lose width and incision together.
- Drowned support no longer receives bank fill. Both lake and sea inlets open into the receiving water.
- `ErosionContacts.hlsl` prepares four first-water limits at startup. `Erosion::StopAtWater` re-accumulates original local runoff with interrupted links removed. The original graph words and meander traces are retained.
- Cache `EXOEROS6`: 24 RG32 slices, 48 MiB. The native first-contact cache passes independent accumulation on all 1,572,864 nodes, with 11,766 interrupted links and conserved local runoff. Initial F8/F9 captures in `distance-contacts/` remove the reported coastal crossings.
- Latest Release x64 build succeeds: `x64/erosion-wet-support-build.log`. Twelve final native views are inspected in `x64/erosion-reprise/distance-contacts-final/`; the reported F8/F9 continuations and F6 confluence fragments are gone.
- Current correctness: approach, amont, morphology, bank filter, junction/fan sections and contact/runoff checks pass. The pre-erosion terrain and old network path remain bit-identical. Complete continuity passes 17 edge lines, 17 joins and four confluences, maximum sampled water step 0.003 m: `x64/erosion-wet-support-check.log`.
- The post-contact suite found a 1.207 m water jump: longitudinal handoff removed the tributary's stage before the main river covered it. That handoff is now removed; stages and currents blend on actual wet support. Resolved depth reads the stage/bed gap without a coverage-dependent terrain cut. Earlier absolute-bed and coverage-cut attempts are archived.
- Route: `tools/tests/2026-11-04-approche-berges.txt`; F8/F9 reproduce the reported coastal crossing, F10 exposes the remaining distributary issue, F12 targets a surviving lake inlet at 33.0246 N, 54.8939 E. Use native hidden engine captures only.
- Native descent: `approach-contacts-final/`, 224 frames, exit 0; sampled overview `approach-contacts-final.png`. The native regenerated cache payload equals the CPU-tested payload (SHA-256 in `docs/spec-erosion.md`).
- Next structural work: independent first-water contacts for each distributary (F10 has a side branch ending on land); continuous lake-basin boundaries/spillways (F12 shows a straight water-surface boundary); more convincing bank finish (F11 remains visually plain despite grounded objects). Do not advertise those views as completed natural morphology. User flight review remains pending.
- Previous cache: ignored `x64/erosion-reprise/erosion-before-stops.bin`; source snapshots: `source-before-junctions/`. No benchmark, commit, tag or push.

**Retained approach base, 2026-11-03; superseded review evidence**
- Preserve the accepted asymmetric valley base and the corrected upstream slots. The new user request adds stable approach, local confluence widening, broader deltas, real bank relief and optional grounded objects.
- `ErosionCorridorMean` integrates the composed physical profile; avoid a vector lerp of the uncapped spur expression, which caused catastrophic float cancellation in the rejected native candidate. The stable minimum is covered by `verifie_approche.py`.
- Fine and screen samples now include premultiplied flow (48/64 bytes); their water fields use the height B-spline, including pixel-refinement moment blending. Native CPU/GPU strides are paired.
- Node enumeration extends the physical 4 × 4 search over the sampling footprint. The geometry-only reach remains bounded; filtered samples can read more nodes.
- New shared geometry: connector flare, bank octaves and a calibrated three-distributary fan restricted to large, low-gradient marine outlets on low coasts. `ObjectPlacement` uses the resulting dry-bank band for existing gravel/tufts. No new independent decoration path.
- Settings and limits: `docs/spec-erosion.md`, `docs/journal-planete.md`. No sediment evolution, resolved detailed coastal routing or new minor tributary hierarchy is claimed.
- The six suites passed before the November 4 changes. Those results and captures are historical; current verification is above and in `docs/spec-erosion.md`.
- Review route: `tools/tests/2026-11-03-approche-berges.txt`. Native descent: ignored `x64/erosion-reprise/approach-ground.cine`, 224 frames, 1,200 km to 8 m above the bank; its first 144 frames match `approach-before/`.
- Baseline source copies: `x64/erosion-reprise/source-before-refinements/`. Logs: `x64/erosion-refinements-*`. No benchmark, commit, tag or push.
- Continue with the current route above; use engine captures only, no system-wide UI control.

**Latest user review: upstream slot canyons, 2026-11-03**
- The user judges the morphology substantially better and wants to preserve that base. Broad gorges returning to ordinary beds work; long, deep, narrowing upstream slots do not. River widths still need work.
- Exact reported pose: `3840.6 -5.038412 124.886462 13.17 -102.18`; native reproduction `x64/erosion-reprise/amont-before.png`.
- Cause reproduced in the CPU mirror: the retained mountain residual climbs hundreds of metres over the short width-based bank transition. This creates an inner gorge in an already formed valley.
- Current correction: `ErosionSpurBankLift` bounds only recovered spur height by physical bank distance, monotonically and with C1 joins. Small lifts with ample room and the base valley profile are preserved; water sizing is unchanged.
- `RIVER_SPURS` is now (0.6, 60 m, 0.6). Source backup: `x64/erosion-reprise/source-before-amont/`.
- Release build and all four correctness suites pass. `verifie_amont.py` checks 29 cross-sections over 18.9 km; maximum rise within 300 m of the channel falls from 666.6 to 146.4 m, with identical water coverage.
- Twelve native route captures plus the terminal lake are inspected in `x64/erosion-reprise/distance-amont/` and `distance-amont-lake/`. The exact reported slot is gone; broad-valley F5 retains its large form. Native stage-cache payload is unchanged.
- Flight route: `tools/tests/2026-11-03-amont.txt`. User review remains pending. Water-width regularity, orbital repetition and connected tributary hierarchy remain open. Full status and logs: `docs/spec-erosion.md`.
- Interactive app relaunched with that route, `-SansNuages -Resolution fenetre -Position '3840.6 -5.038412 124.886462 13.17 -102.18' -Soleil '20 120'`. The correct worktree process is responsive and rendering, alone on the GPU. It starts in cockpit mode; Backspace then F1 restores the exact free-camera pose. No UI control was used.

**Retained base: valley morphology, 2026-11-03**
- Active user request: continue from the Alpine references; improve repetitive valleys, parallel flanks and homogeneous river widths.
- Retained base: preserve bounded positive terrain residuals from the 50 km detail octaves down inside river corridors; recover spurs outside the wet banks; contract floor and wall widths independently at each terrain point (factor 0.25 to 1); extend valley bends to 40 km; vary water widths at 12 km, 3 km and 750 m.
- Large bends are reserved for the bounded valley offset. The current planet's conservative reach is 13 731 m, within the fixed search's 14 094 m corner bound.
- Settings, formulas and current verification are in `docs/spec-erosion.md`; route `tools/tests/2026-11-03-vallees.txt`.
- The level-0 graph is unchanged. Connected secondary valleys, density, exposed sediment and junction widening remain limitations, not validated achievements.
- Step A still steers its ravines on pre-incision terrain. The next structural issue is connecting smaller valley branches to the new main-corridor flanks; do not treat stronger width noise alone as that hierarchy.
- The current minimum floor contains the actual displaced dry banks, and spur recovery retains the uncontracted floor scale. Narrow exposed bank strips remain visible at F9/F10; their complete removal is not established. A raw relief witness is `x64/erosion-reprise/confluence-relief.png`.
- Release build and all three correctness suites pass. All twelve final native views are inspected in `x64/erosion-reprise/distance-morphology-final/`; the user reports a substantial improvement, with upstream slots still to correct. Full corridor checks now centre their witnesses on the displaced river. F3/F7 centre on actual wet courses in separate mountain basins.
- Before-morphology source snapshots: ignored `x64/erosion-reprise/source-before-morphology/`; retain the earlier distance-filter fixes. The previous native baseline is `x64/erosion-reprise/distance-final/F01.png` through `F12.png`.
- Google Earth references: ten tab captures and camera URLs in `x64/erosion-reprise/reference-earth/`; original user references are `reference-alpes.png` and `reference-alpes-detail.png` beside it. Observations and limits are in the spec.
- User preference: engine-native game captures and tab-targeted Google Earth captures; avoid system-wide computer views. The user stopped UI control with Escape; do not resume it without a new request.
- The user granted erosion priority over the other GPU sessions. Do not stop unrelated jobs or message other chats without explicit instructions.
- The user hid Google Earth's ski overlays themselves. No further layer changes are needed.
- Previous interactive launch: `tools/lance.ps1 -Parcours tools/tests/2026-11-03-vallees.txt -SansNuages -Resolution fenetre -Position '250325.2 -7.489828 125.499386 65.74 -9.13' -Soleil '20 120'`. That was the preceding review launch; use the current upstream route above.
- No benchmark, commit or push is authorized by this continuation.

- **Worktree :** `C:\Users\etien\Documents\repos\Exolune-erosion`, branche locale `claude/erosion-montagnes`.
- **Remote :** seulement `origin` (`exolunehq/exolune`). Rien n'est poussé.
- **Règle d'historique public :** le commit `79cbf25` ne doit jamais devenir un ancêtre (`docs/principes.md`, « Public Git history »).

**Commités, validés en vol par l'utilisateur**
- `4bac000` : la doc anglaise de l'érosion, reportée depuis la branche `erosion`.
- `1e2cbbb`, tag `piste/relief-ecran-2026-11-02` : le relief écran, une passe de calcul qui recalcule le vrai relief sous chaque texel de 2 × 2 pixels au-dessus de 150 à 400 km.
- `67637ef`, tag `piste/vallees-orbite-2026-11-02` : les vallées gardées en orbite. Chaque section est coupée par le sol avant d'être moyennée.

**Sur `main`, en local, non poussé :**
- `main` en `ced1d9a` : le rendu lointain y est fusionné, sans l'érosion.
- La branche `claude/rendu-lointain` (`82447e3`, tag `piste/rendu-lointain-2026-11-02`), faite par une autre session.

**Non commité dans le worktree : la nouvelle méthode d'érosion**
- **Étape A, `EROSION_RAVINES`** (`PlanetSettings.hlsli`) : le relief sans érosion, plus des ravines.
  - Ce sont des octaves de 5 km à 4 m, orientées par la pente des octaves plus grossières, dans `ReliefDetail` (`Relief.hlsli`).
  - L'ancien réseau de vallées est coupé.
  - **Validée en vol :** géométrie propre.
- **Étape B, `EROSION_RIVERS`** : des couloirs autour des grandes rivières du réseau de niveau 0 (graphe de 20 km).
  - The course has fractal bends and multiscale water widths; its floor and flanks preserve and contract around the existing mountain field, with clearance for the displaced banks.
  - **Au démarrage :** les passes `ErosionNodes.hlsl` et `ErosionStages.hlsl`, puis `Erosion::Condition` dans `Erosion.cpp`. Le cache courant est `EXOEROS5` (dimensionnement).
  - **Jugée en vol :** « la meilleure version de l'érosion à ce jour », mais avec les défauts listés plus bas.
- **Touche 1 en vol :** elle bascule entre érosion complète, ravines seules et sans érosion.
  - Le mode est passé par la constante `erosionMode` (`Planet.hlsli`, `D3DApp.h/.cpp`), lue par `ErosionMode()` dans `Relief.hlsli`.
  - La touche vide `mTerrainKept`, pour recalculer le maillage proche.
  - **Limite :** le contact du vaisseau et la marche gardent l'érosion complète.
- **Continuation audit, 2026-11-03:** the interrupted river-sizing work has been reviewed and retained.
  - Current settings: `RIVER_Q` (200, 300, 450) m³/s, `RIVER_REACH` 8500 m; smaller rivers have no explicit water.
  - The full default `tools/hydro/verifie_couloirs.py` now passes on the engine's `EXOEROS5` cache.
  - Release x64 builds successfully through `tools/lance.ps1 -Build -NoLaunch`; the existing material bit-shift warning remains.
  - It first exposed a 0.660 m water edge beside a confluence. `Relief.hlsli` and its CPU mirror now bound river depth by the compact cut after combining beds.
  - Documentation now distinguishes measured inverse drainage density from outlet spacing and published laws from engine calibration.
  - Current verification and flight status: `docs/spec-erosion.md`, step B; route `tools/tests/2026-11-03-tailles.txt`, twelve views, including three confluence witnesses.
  - All twelve final native captures are in `x64/erosion-reprise/apres/` and have been inspected. F6/F8 were raised above the current terrain; F12 now frames a second wet confluence downstream.
  - Launch the twelve-view route through `tools/lance.ps1 -Parcours tools/tests/2026-11-03-tailles.txt -SansNuages -Position '464941 -8.283789 124.598381 66.09 22.58' -Soleil '20 120'`. The user's in-flight acceptance of sizing remains pending.
  - That interactive launch was verified on 2026-11-03, full screen at 1920 × 1080, with only this engine running.
  - Changes remain uncommitted. No performance or quality benchmark was run.

## Le diagnostic qui a mené ici

- **L'ancienne érosion :** un réseau calculé sur un relief filtré à 40 km, dont les vallées analytiques étaient creusées dans un bruit qui ne s'y draine pas.
  - D'où des rivières perchées : 28 % du tracé était sec.
  - Des canyons lisses, sans détail.
  - Des tracés rectilignes.
- **La règle qui en découle** (celle de la tectonique, `docs/principes.md`) : une carte précalculée ne porte de géométrie qu'au-dessus de deux de ses cellules. Le bruit fait le reste.

**Fichiers d'étude**, conservés hors Git dans `C:\Users\etien\AppData\Roaming\Claude\side-session-notes\local_55c2f770-5d1d-456b-a9b1-7d09f62e6b18\` :
- `erosion-etude\etat-de-l-art.md` : les méthodes d'érosion calculées point par point, et leur classement.
- `erosion-etude\analyse.txt` : la mesure des rivières perchées.
- `erosion-placer-abaisser\placer-abaisser.patch` : une piste mise de côté, en partie reprise par l'étape B.

**Le banc CPU de comparaison :** `tools/hydro/etude_relief.py`.
- **Les variantes :** `sans`, `actuelle`, `ravines`, `ravines_moteur2`, `couloirs`, `couloirs_moteur`, `arbre` (écartée).
- **Les planches :** `x64/etude-relief*/`.
- **Les prototypes :** `tools/hydro/ravines.py`, `couloirs.py`, `arbre.py`.
- **Les contrôles :** `tools/hydro/verifie_ravines.py`, `verifie_couloirs.py`, et les autres `verifie_*.py`.

## Retours de l'utilisateur, à traiter, dans cet ordre

1. **Les vallées toutes pareilles, « à la brosse », et trop de rivières**, vues vers 465 km.
   - La vue : `464941 -8.283789 124.598381 66.09 22.58`.
   - **Les causes :** presque tout lien de plus de 10 m³/s fait un couloir ; parois et largeur sont constantes ; le niveau d'eau est abaissé partout, de 542 m au 95e centile.
   - **Current continuation:** sizing, distance filtering and terrain confinement are implemented. Review on `2026-11-03-vallees.txt`; the broad network pattern and missing secondary-valley hierarchy remain unresolved.
2. **La cohérence à l'approche :** de loin, des taches d'eau ou d'érosion, qui disparaissent à une certaine altitude puis reviennent avec les rivières.
3. **La largeur des cours d'eau :** elle doit varier le long du cours et selon le type de rivière.
4. **Les confluences et les deltas :** trop abrupts, il faut des évasements.
5. **La performance :** nettement dégradée. Mesurer, et dire si la méthode est viable et optimisable. Un banc seulement sur demande de l'utilisateur.
6. **La variété des vallées :** « une crête à gauche, une crête à droite », répété partout. À juger avec la touche 1.
7. **À noter :** sur une chaîne enneigée, la neige apparaît avec la descente, entre 1 600 et 1 200 km.

Le reste du tableau de `docs/spec-eaux-interieures.md` (cratères, lacs, contact avec les falaises…) est à revoir avec la nouvelle méthode.

## Méthode de travail (règles de l'utilisateur)

- **Des corrections à la cause et universelles,** jamais un patch local.
- **Jugement en vol :**
  - écrire un parcours `tools/tests/<date>.txt` ;
  - compiler avec `powershell -NoProfile -ExecutionPolicy Bypass -File tools\lance.ps1 -Build -NoLaunch` ;
  - lancer avec `... tools\lance.ps1 -Parcours tools\tests\<date>.txt -SansNuages`.
- **Les touches :** F1 à F12 pour les vues, N pour les nuages, 1 pour l'érosion.
- **Vérifier le cadrage avant de lancer :** des captures cachées avec `tools\capture.ps1`. Pour les démarrages longs, `capture_long.ps1` et `captures_parcours.ps1` sont dans le dossier `erosion-etude` ci-dessus.
- **Un seul moteur sur le GPU à la fois :** `tasklist | grep -i myplanet`. D'autres copies (`Exolune`, `MyPlanetEngine-trailer`) tournent parfois.
- **Le jeu ouvert verrouille l'exe :** le fermer avant de compiler.
- **Pas de banc de `tools/` sans demande.**
- **Commit et push sur demande seulement.**
- **La doc en anglais,** selon `AGENTS.md` : spec, journal, principes, géométrie et index.
- **Salle blanche :** aucun code de runevision, Dendry, PlaTec, fastscapelib, World Orogen, libnoise ou complexplanet.
- **Rapports à l'utilisateur :** courts, en français, la conclusion d'abord.
