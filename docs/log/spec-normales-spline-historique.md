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
