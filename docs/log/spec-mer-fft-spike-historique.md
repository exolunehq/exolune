# Spike FFT: measurements of the 2026-10-26

**experiment measured:** base 47c404b, tag `piste/mer-fft-spike`, before commit of `jalon/22-mer-fft`.
**Current status:** [spec-mer-fft-spike.md](../spec-mer-fft-spike.md).
**Local exits:** x64/MerFFT/validation and x64/MerFFT/qualite.

**Protocol**
- benchmarks hidden, no competing engine rendering.
- 1280 × 720; Debug x64, shaders optimized.
- Simulated time: 1/60 s per frame, speed 1; speed 0 for frozen sea.
- Wind controlled, direction 70° in the transported plane.
- Measurements made before the commit of the milestone; old prototype kept in the `piste/mer-animee` tag.

**Appearance and cost**
- Captures at 1 and 3 m, in freshwater at 20 m, in storm at 20 m and on user view at 142,4 m.
- Storm: wind 24 m/s, swell Hs 3,5 m; capture after 600 images, or 10 s simulated.
- User view: 142.4 -44.75718 177.39448 22.5 -151.6; sun 15 165.
- The continuous white nets and broad translucent stripes of the sample are absent from this catch.
- The first captures showed too many very fine folds; choppiness now dampened under 40 cm wavelength.
- Cost of full simulation: 0,13 ms GPU in cool sea and storm.
- Rendering: 1,27 ms, minimum 1,25 ms, in cool sea; 1,12 ms, minimum 1,10 ms, in storm.
- These times are from the last interval displayed after 600 images, not from a percentile over a long session.
- Reported slope: 3,50 ms of rendering, minimum 3,35 ms, including terrain, in the previous capture with identical graphical instrumentation.
- Aspect to be validated in flight; these measurements do not prove the realism of the foam.

**Quality of the ground**
- tools/banc_qualite.py --sites 30 --reuse-sites uses the target locations, caps, and materials of the MerAnimee/bench-qualite-volume/qualite.json. cookie
- All colors, masks and variants of grid cell are recalculated.
- Comparison required by --before tools/banc_qualite_reference.json; reference retained.
- The same 3 891 crops are retained; none added or removed.
- 3 888 identical crops; in each of the other three, a pixel changes one level on 255.
- No hole, repetition or mutation p95 regresses by more than 10 % compared to the control.
- The following six exceedances of the reference are strictly identical to those of the control.

| Material | Height | Measure | Exceeding the benchmark |
|---|---|---|---|
| Rock | 12 m | Repetition p95 | +14,9 % |
| Rock | 3 000 m | Hole p95 | +314,3 %; only three crops |
| Sand | 50 m | Repetition p95 | +50,8 % |
| scree | 12 m | Hole p95 | +66,6 % |
| Snow | 3 000 m | Hole p95 | +21,7 % |
| Snow | 3 000 m | Repetition p95 | +39,1 % |

**Stability**
- tools/banc_tremblement_mer.py: fixed camera, mesh sliding like in flight; maximum channel gap between images, averaged on pixels.
- Values are in 8 bit image levels; animated deviation includes the desired movement of the waves.
- Fresh wind: 12 / 70 / 1,8; coast: same wind; micro: 4 / 70 / 0,4.

| View | Case | Sol out of sea | More | Contrast of sea detail |
|---|---|---|---|---|
| Fresh, 20 m | Freezing, smoothing | — | 0,90 | 10,94 |
| Fresh, 20 m | Frozen, without smoothing | — | 0,93 | 10,94 |
| Fresh, 20 m | Animated, smoothing | — | 2,17 | 11,41 |
| Fresh, 20 m | Animated, without smoothing | — | 2,19 | 11,41 |
| Coast, 120 m | Freezing, smoothing | 0,02 | 0,43 | 6,36 |
| Coast, 120 m | Frozen, without smoothing | 0,08 | 0,51 | 6,36 |
| Coast, 120 m | Animated, smoothing | 0,02 | 0,59 | 6,34 |
| Coast, 120 m | Animated, without smoothing | 0,08 | 0,65 | 6,36 |
| Micro, 1 m | Frozen, smoothing or without | — | 1,06 | 14,33 |
| Micro, 1 m | Animated, smoothing or without | — | 12,75 | 18,56 |

- Coastal terrain keeps the values of the witness: 0,02 with smoothing, 0,08 without.
- The fresh frozen sea varies more than the analytical control, 0,90 vs 0,20; the new geometry remains sensitive to the displacement of the mesh.
- The benchmark does not therefore prove the absence of geometric flicker; flight judgment is necessary.
- At the North and South Poles, at 100 m: white water mask on 921 600 pixels, no visible hole.

**Reflet lointain**
- tools/banc_mer.py, reflection mode, at 400 km; locations -17.36 -26.84 and 55.95 8.07.
- Wind 12 m/s: average variation of 2,8 % on each of the two locations.
- Wind 24 m/s: average deviation of 6,2 %; the target of 5 % of the initial search is missed.
- The weak tail of the reflection is less well reproduced in strong wind; statistical connection to be taken before integration.
- Planetary wind and near Monahan coverage are not validated by this uniform wind prototype.

**Judgment in flight**
- tools/lance.ps1 with tools/tests/2026-10-26-mer-fft-spike.txt and x64/MerFFT/MyPlanetEngine.exe.
- F1 and F2: micro-relief; F5: storm; F7: reported coastal view; F11 and F12: poles.
- The foam maps return to the change of view; leave a few seconds to see the trails.

**Integration with main · 2026-10-26**
- Rebase to main 083bfb1; Earth code of the witness identical to that of vegetation v3, executable Veg3.
- Debug x64 recompile after rebase; sea resources, planet map, vegetation and objects together.
- Time: 1280 × 720, Debug x64 with optimized shaders, after 600 images; values from last title interval on this machine.
- quality benchmark on six locations of the initial drawing, one per material; same caps, five heights, all views recalculated on the two executables.
- Compare by --before to tools/banc_qualite_reference.json, then matched comparison to the main witness.
- 753 common crops, all strictly identical; none added or removed; no p95 regression compared to control.
- The fifteen overruns of the reference below are identical in the witness and in the integration; the draw of six places differs from the initial benchmark by thirty places.

| Material | Height | Measure | Exceeding the benchmark |
|---|---|---|---|
| grass | 12 m | repeat_p95 | +113,3 % |
| grass | 50 m | repeat_p95 | +11,6 % |
| grass | 200 m | repeat_p95 | +24,1 % |
| rock | 3000 m | gap_p95 | +105,9 % |
| sand | 50 m | repeat_p95 | +25,4 % |
| sand | 200 m | repeat_p95 | +37,8 % |
| scree | 12 m | gap_p95 | +78,2 % |
| scree | 12 m | repeat_p95 | +192,1 % |
| snow | 50 m | repeat_p95 | +13,6 % |
| snow | 3000 m | gap_p95 | +45,3 % |
| snow | 3000 m | repeat_p95 | +68,3 % |
| soil | 12 m | gap_p95 | +242,7 % |
| soil | 12 m | repeat_p95 | +126,5 % |
| soil | 800 m | gap_p95 | +13,7 % |
| mutation | 12 m | p95 | +510,6 % |

- Local outputs: x64/MerMain/qualite-main-6, qualite-integre-6 and qualite-comparaison-main.json.
- Storm at 20 m, wind 24 m/s and swell Hs 3,5 m, 600 images: 0,13 ms simulation, 1,22 ms rendering, minimum 1,20 ms; object placement 0,23 ms, objects absent from the water.
- benchmark of vegetation views: temperate and tropical forests at 150 m; the two images 1280 × 720 are strictly identical to the control, pixel by pixel.
