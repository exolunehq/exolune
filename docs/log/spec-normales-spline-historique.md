# History of spline normals

**The cardinal spline prefilter,** out of `../spec-normales-spline.md` the 2026-10-30, when its passes left the engine, commit `3a4508a`. They remain in the `jalon/09-normales-spline` tag. The present state is in `../spec-normales-spline.md`.

**The original plane:** a cardinal cubic B-spline, which passes through the vertices. Expected variation: 0,4 % for a wave of 8 grid cells, against 17 % for the normal of the peaks. At the benchmark of the 2026-10-21, it aggravated the jitter; the smoothing B-spline, without prefilter, was kept.

**The prefilter:**
- **A cubic B-spline will only pass through its control points if they are prefiltered.** That is what makes it cardinal.
- **The exact prefilter** is the inverse of the filter [1 4 1] / 6. Its impulse response is √3 · z^|d|, with z = √3 − 2 ≈ −0,268.
- **Truncated to 7 coefficients,** from d = −3 to 3, then normalized so that their sum is 1: constants and uniform slopes remain accurate. Truncation error of about 0,5 %.
- **Separable:** one pass along the first axis of each card, i or b, then one pass along the second axis, j or r.

**The code then:**
- `SplinePrefilter.hlsl`: the two passes of the prefilter, after the calculation of the terrain. One pass per axis, one thread per vertex.
- Two float4 buffers per vertex: the intermediate result and coefficients, read by the pixel shader.
- `SPLINE_SHARPENING`, in `PlanetSettings.hlsli`: 1, the cardinal spline; 0, the smoothing B-spline; between the two, a mixture. To 0 from the benchmark: the prefilter was no longer used, its passes remained for the test.
- Their cost, with the pixel shader: less than 0,1 ms in all; the prefilter alone, 0,02 to 0,13 ms to the profile of the round 4 (`../optimisation.md`).

## 2026-11-01 fine-grid reconstruction

- The user accepted coastal contour antialiasing and river contours after pixel refinement; river visibility is sufficient for the present stage.
- A similar but weaker mountain defect remained at `1673620.9 -7.138614 122.604860 84.18 32.74`, seed 0.
- The fine grid previously interpolated four heights bilinearly and four centred-difference normals independently. The resulting height field was continuous, but its derivative changed at each cell border.
- The replacement takes the positive cubic B-spline mean of 16 heights and analytically differentiates it on the spherical chart; no cardinal prefilter or extra terrain query is added.
- A nearby height is subtracted before derivative accumulation to avoid cancellation; clamped addresses and the existing invalid-sample fallback remain.
- Native captures under `x64/mountain-contours/` reproduce the exact reported view in colour, elevation, snow and sunlight diagnostics.
- `motion-before/` and `motion-cubic/` each contain 120 frames at 60 Hz, 1280 by 720, clouds hidden, TAA unset, after 60 warm-up frames.
- The route shifts latitude by 0.1 degrees and longitude by 0.12 degrees while approaching by 90 km; both use the same poses and terrain.
- Inspected first, middle and last frames retain the same broad forms and soften the grid-scale mountain transitions; this is not a claim of complete temporal stability.
- Additional captures: `cubic-snowy-orbit.bmp`, `cubic-snowy-range.bmp`, `cubic-mountain-river.bmp` and `cubic-river-bank.bmp`.
- The second chain retains its massif; closer valleys still show prescribed regular cuts. The water witnesses retain their channels and the accepted river has no new side pools.
- Release x64 passes. No performance or quality benchmark was run; the previous contour-query GPU cost remains open.
- The final build was relaunched on the Exolune erosion branch at the exact reported pose, free camera, speed 1.14 and clouds hidden; F1-F6 of the new route cover mountain distance and a second chain.
- Geometry, routing, material recipes and generation settings are unchanged. Natural paths, connectivity, physical profile filtering and silhouette stability remain separate work.
