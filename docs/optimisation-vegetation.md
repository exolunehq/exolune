# Optimisation of vegetation performance

**Status: first optimizations integrated to main the 2026-10-27; phase to continue.**
- Base validated in the state: `jalon/24-vegetation-detaillee-main`.
- Starting point of the phase: `piste/vegetation-optimisation-base`.
- Integration: `jalon/25-vegetation-performance-main`.
- The HiZ and material depth are detailed in `vegetation-hiz.md`.

**Culling already in place:**

| Stage | Work Avoided | Source |
|---|---|---|
| Terrain | Peaks outside the visible volume, with margins for normals, waves and shadows |  `TerrainCompute.hlsl`, `Terrain.hlsli::MaybeVisible`  |
| Relief noise | Octaves invisible to the grid cell and field branches with weight zero; average retained |  `Noise.hlsli`, `Relief.hlsli`  |
| Placement | Tiles out of field, out of reach or without ground support; reject before exact ground and heavy noise functions |  `PlantPlacement.hlsli::CullPlantTile`  |
| Individual plants | Projected size, medium fineness and presence; choice mesh or proxy |  `PlantPlacement.hlsli`, `PlanetFoliageClassify.hlsl`  |
| Drawing | Empty indirect commands ignored on GPU and depth test |  `PlanetFoliage.cpp`  |

- The next pass `vegetation-hiz.md` adds a depth pyramid running to avoid the work of impostors completely hidden by the ground or nearby meshes.
- impostorss rebuild their depth in the pixel shader; so depth testing does not necessarily save all of their pixel work.
- The foliage is double-sided; no general rejection of the back faces is enabled.

**First pass:**
- The angles, view indices and sinus/cosinus already calculated by the proxy vertex are passed without interpolation.
- The pixel shader reuses these bases for all four views; it no longer recalculates their trigonometric functions.
- The placement, scans, mesh close, alpha cut, depth and thresholds remain those of the validated base.
- The atmosphere compaction and displacement tests are in `log/optimisation-vegetation-historique.md`.
- A dedicated measure separates plant placement from plant classification; the old `placement` field on the sidecar still denotes classification.
- These two additional timestamps are reserved for batch captures; the flight retains the twelve timestamps of the base.

**Protocol:**
- Reference and candidate have the same instrumentation GPU; sources and binaries are frozen under `x64/VegetationPerf/`.
- `tools/banc_arbustes_climat.py`: fourteen views, six climate families; series on GPU free with 32 heating images and 128 measures per view.
- Sea time is frozen at `0 0` for comparisons; flight applications are closed during measurements.
- Images, model accounts and overruns are compared on the same poses, suns and assets.
- The general benchmark takes six fixed places, one per material and five heights, with the canonical reference unchanged and a paired comparison between the two binary.
- Identity exports are separate from time measurement, to avoid readback traffic.

**The comparison flight:** its launcher, which opened the frozen binaries of the selected version and its reference, is removed the 2026-10-30; it is described in `log/optimisation-vegetation-historique.md`.

**Result of this pass:**
- Fourteen identical images pixel by pixel; same accounts per model and family, without overrun; identical assets.
- On the dense forests measured, the pattern changes from 6,28 to 5,97 ms in boreal, from 11,05 to 10,78 ms in temperate and from 8,93 to 8,38 ms in tropical.
- Small populations do not show a stable gain; the total time remains variable, especially with other active renders. No number of FPS is guaranteed.
- The general benchmark ends the six places: 744 PNG on 745 are identical; a single pixel differs by one level on 255.
- No matched p95 regresses by more than 10 %; canonical reference and inherited limits remain unchanged.
- Summary retained: `../tools/foliage/results/2026-10-27/optimisation.json`.
- Placement remains the next project; experimental scans have not been delivered.
- **Following the 2026-10-28:** `optimisation.md`, round 3. The exact floor of the tiles kept from one frame to another, the impostors in conservative depth, the meshes in depth first.

**What should be kept:**
- The accepted appearance of trees and twelve climatic shrubs.
- Density, display distance, seeds and positions.
- Climatic mixtures and stability with a still camera.
- The relay between mesh, impostor and canopy.

**The measures to be established first:**
- Profile GPU of the placement, classification and drawing, separated from the land and the sea.
- Cost CPU, GPU resident memory, loading and preparing mipmaps.
- Paired comparisons on the same poses, suns and populations, without concurrent GPU load.
- Ground, edge and aerial approach courses on the six climatic families.
- Median time and p95 per pass; target budget to be decided after this isolated reference.

**The areas to be examined:**
- Reduce processed transparent pixels and overlays of foliage cards.
- Add or simplify the detail levels of nearby meshess, with equivalent cover and silhouette.
- Adjust the intermediate representations and the mipmaps of the impostors, without reducing their scope.
- Mutualize textures and data common to variants; cache offline preparation.
- Reduce reservations and transfers from limited queues, without unstable selection or instance loss.
- Measure drawing calls and their grouping before any further modification.

**Known cost reference:**
- Six instance regions: 192 MiB.
- Rendering buffers: 729 760 876 bytes, out of queue and temporary memory.
- The twelve bushes add about 445 MiB to the previous catalog.
- Previous timing experiences concurrent loads; they do not guarantee a budget of FPS.

**The verification of the phase:**
- One change at a time, with avant/après across multiple locations and instance counting.
- The benchmark `tools/banc_qualite.py --before tools/banc_qualite_reference.json` remains the general reference.
- The base was visually accepted despite the deviations documented in `vegetation-planetaire.md` and `arbustes-climatiques.md`.
- These deviations remain quality limits; they are neither erased nor reclassified as performance issues.
- No change in baseline or metric should mask a regression.
