# History of hierarchical occlusion of vegetation

**`../vegetation-hiz.md` sections released the 2026-10-30,** when its witnesses left the engine, commit `3a4508a`. They remain at the `jalon/25-vegetation-performance-main` tag. The present state is in `../vegetation-hiz.md`.

**Witnesses withdrawn:**
- `MYPLANETENGINE_FOLIAGE_HIZ=0` cut the HiZ.
- `MYPLANETENGINE_FOLIAGE_MESH_HARDWARE`, missing by default, kept the historical depth of meshes: the original shader recalculated `SV_DEPTH`. The choice was made by PSO.
- `MYPLANETENGINE_FOLIAGE_HIZ_INTERLEAVE` and `MYPLANETENGINE_FOLIAGE_MESH_INTERLEAVE` alternated these states in batch.
- The volumes and the impostors with stochastic alpha, representations removed the same day, kept their integral drawing lack of depth boundary.
- Their tools: `tools/lance_vegetation_hiz.ps1`, and the options `--hiz off|interleave`, `--mesh-depth legacy` and `--matrix` of `tools/banc_arbustes_climat.py`.

**The measure, 2026-10-27:**
- `tools/banc_arbustes_climat.py --hiz off` and `--hiz on` use the same executable, models, poses, suns and frozen sea time.

**Interlaced comparison:**
- A batch mode alternates the four states: historical or hardware depth, HiZ disabled or enabled.
- Camera, models and data reside in the same process; each cycle gives a close comparison, less sensitive to other renderings.
- Six views, 32 heating images, 256 measures per view, or 64 complete cycles.
- Interlaced mode is reserved for batch; it is not used in flight.
- In the inner temperate forest, the vegetation rendering changes from 10,30 to 4,64 ms and the GPU image from 27,61 to 21,84 ms.
- In the rainforest, it changes from 8,21 to 3,46 ms and the GPU image from 28,64 to 24,06 ms.
- In boreal forest, it changes from 5,95 to 4,27 ms and the GPU image from 23,69 to 21,54 ms.
- The desert pays an extra cost: drawing from 0,38 to 0,54 ms, image GPU from 14,41 to 14,47 ms.
- These GPU times are not a guarantee of FPS; the terrain, placement and cost CPU remain present.

**The flight:**
- `tools/lance_vegetation_hiz.ps1` opens the retained version; `-Reference` disables HiZ and returns to historical depth.
- `-LegacyDepth` isolates the HiZ by keeping the historical depth of the meshes.
- Same executable, same `2026-10-27-vegetation-hiz.txt` palette, same models, density and range; one flight at a time.
