# History of Climate Shrubs

**2026-10-27: first collection, not selected.**
- Twelve shapes generated with the same families, mainly by varying the port and density parameters.
- The CPU plates show silhouettes still too related in vase and a foot too bare.
- The gray-green of the dry forms is not enough to differentiate their architecture.
- This first experiment remains in `assets/foliage/climate_shrubs/`, without being the candidate's default.

**2026-10-27: second collection.**
- Boreal: tuft low irregular; desert: lateral forks; steppe: tuft of soil and some erect stems.
- Mountain: almost horizontal branches; temperate: three leafy centers; tropical: separate stems and large alternate curved leaves.
- Two orientations and a board with motor allometry are examined before the final bakes.
- The color, normals, and wood mask are explicitly extracted from the 0 source tile; the leaves use the 1 tile.
- The twelve architectures reuse photographs of leaves of Searsia Lucida under CC0; they do not describe twelve distinct actual species.

**The selection:**
- A first weight sum with a temperate floor of 0,08 leaves too many families unsuited in the free climates.
- It is replaced before the comparisons by a continuous hierarchical partition, without forced floor.
- The six extreme climate cases are controlled on CPU; the weights remain positive and sum 1.

**The GPU protocol:**
- Families share the six existing regions of 192 MiB; counts precede the calculation of subrange and then their filling.
- The prefix should not only become `StartInstanceLocation`: `SV_InstanceID` starts at zero according to the [Direct3D specification, §8.18](https://microsoft.github.io/DirectX-Specs/d3d/archive/D3D11_3_FunctionalSpec.htm#Instancing).
- Indirect commands therefore also carry the address of the SRV root adjusted to the subrange.
- The isolated compilation succeeds; the new pipeline without catalog retrieves the reference population totals on the first fourteen views, without overrunning.

**Current status:** `../arbustes-climatiques.md`.

**Engine comparisons:**
- Fourteen views with and without catalog, on the same executable: identical seeds and positions after sorting, same totals by species, no overruns.
- Four neighbors complete frames where there were only three or five shrubs.
- Observed families: dry desert and steppe, humid temperate and frank tropical; mixtures boréal/montagne and montagne/tempéré near the limits.
- A first time series signals a high cost; calls are grouped by representation and empty orders are ignored via the indirect counter GPU.
- The fourteen BMP remain identical byte by byte after this reorganization; two to thirteen commands are active depending on the view on twenty-eight possible.
- The memory cost of the representations increases by 466 967 464 bytes; the six rows remain at 192 MiB.

**The quality benchmark:**
- All twenty-four sites end without blocking GPU, but the strict criterion fails against the previous candidate on two p95: gap sable/50 m +10,15 %, gap sol/12 m +20,83 %.
- The three previous gaps are not erased; five thresholds extend beyond the front of the bouquet pass. Metrics remain unchanged.
- The condensed canonic of thirty sites gives fourteen overruns; it does not represent the same places as these twenty-four sites.
- The catalogue remains a candidate for judgment, without being declared validated by the benchmark.

**Times, limits of interpretation:**
- The first series without readback gives 39,39 ms of median drawing for V2; a repeat of the same binary gives 7,61 ms. The load on the machine therefore varies greatly.
- The optimization produces identical images; its medians are 4,81 and 4,48 ms on the same six locations, but the gross factor cannot be attributed to it alone.
- On the same optimized binary, medians by location ancien/V2 are close, with some increases: boreal 4,14/4,76 ms; desert 0,75/0,60; scrub 3,10/3,07; mountain 3,67/3,51; edge 6,98/7,44; tropical 8,97/9,08.
- No overall gain of FPS is established. The `synthese_perf_finale.json` and `optimisation_perf.json` files preserve the sequences and context.

**The flight of judgment, up to the 2026-10-30:**
- `tools/lance_planet_foliage.ps1` chooses catalog V2 and `x64/FoliageShrubs/MyPlanetEngine.exe`.
- `-Assets assets/foliage/volume_look_normals` finds the previous single bush; the recent executable can read both data sets.
- Removed the 2026-10-30 with foliage modes: the catalog is required, and without it the engine does not draw any plant. Tag `jalon/24-vegetation-detaillee-main`.
