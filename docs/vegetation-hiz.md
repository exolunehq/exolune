# Hierarchical occlusion of vegetation

**Status: version integrated to main on request the 2026-10-27.**
- Sequel to `optimisation-vegetation.md`.
- Git base: `piste/vegetation-hiz-base`; integration: `jalon/25-vegetation-performance-main`.
- Objective: clear a margin above the some 30 FPS signaled in forest, without changing the rendering, the population or the scope.
- **Always active since the 2026-10-30:** hardware depth everywhere, HiZ out of diagnostic views. Their witnesses, the cut HiZ, the historical depth and the interlaced modes, are removed: `log/vegetation-hiz-historique.md`.

**Current depth:**
- The terrain, objects and all nearby meshes are drawn in their usual order.
- The depth D32 is read as R32 from a typeless resource; its drawing format does not change.
- A R32 pyramid reduces by minimum, since the engine uses the reversed Z.
- The sky and off-screen fill are zero; they cannot hide a plant.
- The pyramid uses the current image, without time reuse.
- At 1280 × 720: texture of 2048 × 1024, twelve levels, about 10,67 MiB of texels and 26 descriptors.

**The test of a plant:**
- The four view squares border the raster envelope of the impostor, with margins and folding at the view boundaries.
- The depth is limited to the HALF moments actually uploaded, in all views and all mipmaps.
- The reconstruction takes into account the small alpha views, separate filters and imperfectly orthogonal trigonometric bases.
- Badly conditioned divisions, unfinished, close-up plane passages and screen exits remain visible.
- The minimum of texels HiZ covering the entire rectangle must be strictly in front of the plant depth mark.
- The physical box of the model alone is not sufficient for the impostors; it is not used as proof of rejection.
- Digital guards are conservative and verified by image comparisons; they do not constitute formal proof of any hardware implementation.
- A impostor keeps its integral drawing when this bound is not eligible.

**The mask GPU:**
- Sources, classification, drawing arguments and their prefixes remain intact.
- A visibility mask of 128 KiB is rebuilt at each frame; any visible or uncertain plant writes its bit by an OR operation.
- A hash collision keeps a plant hidden; it cannot remove a visible plant.
- The proxy vertex shader rejects the absent ones before calculating the rectangle and working the pixels.
- All meshes and all proxies keep the initial drawing order, including cases of equal depth.
- `hiz_rejected_candidates` counts occlusion decisions; `hiz_rejected` counts mask collisions.
- histories and model accounts always describe the population source.

**The measure:**
- The 2026-10-27, HiZ cut against active, in the same executable: the protocol is in `log/vegetation-hiz-historique.md`.
- The `draw` time field includes meshes, HiZ construction, test and drawing of the remaining proxies.
- `hiz_gpu_samples_ms` separates construction and culling; detailed timestamps remain reserved for the batch.
- The sustainable synthesis is in `../tools/foliage/results/2026-10-27/hiz.json`; raw captures and reports in `x64/VegetationHiZ/`.
- Tests excluded and disturbed series are recorded in `log/optimisation-vegetation-historique.md`.

**The depth of the nearby meshes:**
- A variant retains the color and all alpha cutouts of the original shader, with depth interpolated by the hardware.
- It removes the recalculated `SV_DEPTH` output, allowing the GPU to reject hidden fragments earlier.
- No `earlydepthstencil` attribute is forced; alpha holes should not write depth.
- It is the only one since the 2026-10-30: the original shader, with recalculated depth, is removed.
- Since the 3 round (`optimisation.md`), this variant writes its depth alone, then its color in equal depth; the test bound also serves as conservative depth for impostors.
- Two FXC warnings of potential initialization appear in the function called by the wrapper; the branches concerned return an initialized result or reject the pixel. They remain visible in the compilation log and request image comparisons.
- On fourteen views, the material depth changes only 25 pixels in total, at depth equality; the HiZ alone keeps the fourteen images strictly identical.

**The gain measured:**
- Vegetation yield of 10,30 to 4,64 ms in temperate forest, 8,21 to 3,46 ms in tropical, 5,95 to 4,27 ms in boreal; in desert, an additional cost of 0,38 to 0,54 ms.
- Measured by interlaced comparison of the four states, removed with controls: `log/vegetation-hiz-historique.md`.
- These GPU times are not a guarantee of FPS; the terrain, placement and cost CPU remain present.

**The preservation of the rendering:**
- Fourteen views of six climate families, same accounts per model, same representations and no overruns.
- HiZ alone: fourteen strictly identical images, with historical depth as with material depth.
- Final variant against historical witness: 25 pixels modified in total on fourteen images of 1280 × 720, with equal depth.
- benchmark general on six locations and five heights, with `--before tools/banc_qualite_reference.json`: 736 identical crops on 745; ten pixels modified in total.
- The 59 p95 compared between the current control and the final variant show no further degradation of more than 10 %.
- The deviations prior to the canonical reference, accepted in the milestone 24, remain present; neither reference nor metrics are changed.

**Limits to keep visible:**
- The placement and its noise functions are still recalculated; the HiZ is drawn.
- The occlusion within the group of impostors does not feed this pyramid; the nearby meshes and the field are its occlusors.
- The mask keeps visible false; this reduces the gain, without lightening the cover.
- Other renders must be suspended to judge the total time and the FPS.
