# History of the concept

**The outdated sections of `../concept.md`,** released the 2026-10-30. They date back to before the milestone 01, when complexplanet was not yet ported. The branches they cite, `complex-planet`, `debug-zoom-planet` and `unity-tw-portage`, are distant branches of 2025, out of `main`.

## The layers of noise: source status

**Verdict: complexplanet layers are not in the sources.** Only the basic bricks and the first subgroup are carried.

**The original** is `complexplanet.cpp` from libnoise: 1 996 C++ lines.

- 12 groups and 26 subgroups: continents, terrain type, mountains, hills, plains, badlands, rivers, four scale groups, final planet.
- 23 generators, 52 modifiers, 18 combinators, 9 selectors and 26 caches.
- Generators: 11 RidgedMulti, 6 Perlin, 3 Billow, 1 Voronoi, 2 constants.

**In the repo branches:**

| File | Branches | Contents | Status |
|---|---|---|---|
|  `Engine/Shaders/TerrainCompute.hlsl`  |  `complex-planet`, `debug-zoom-planet`, `unity-tw-portage`  | noise of libnoise gradient with its constants, Perlin, Billow, RidgedMulti | Basic bricks made. Voronoi absent. |
|  `Engine/Shaders/ComplexPlanetHLSL.hlsl`  | Same branches | Graph complex planet | Only the subgroup "basic continents" is made, then a TODO. Turbulence written but not plugged. |
|  `Legacy/ComplexPlanet.cpp`  |  `debug-zoom-planet`, `unity-tw-portage`  | Graph described in C++ | Partial: continents, terrain type, base of mountains, beginning of hills. Turbulence neutralized. Some values deviate from the original: the hills use a Perlin at 1211 instead of a Billow at 1663 and a RidgedMulti at 367,5. |
|  `Legacy/CudaKernels/NoiseKernels.cu`  |  `unity-tw-portage`  | Perlin and Simplex 3D, fBm, ridge, billow, selectors | Another family of noise functions: port from the Unity shader of 2012, no libnoise. |

**Remains to be done:** port the full graph to HLSL from the original.

**Attention to the license.** `complexplanet.cpp` is under GPL v2, libnoise under LGPL. Porting the graph as such makes the engine a derivative work GPL if distributed.

## Proposed next step

A minimum prototype to validate the concept before investing in the noise:

1. One face of 256 × 256 centered under the camera, size k × altitude.
2. A simple noise, for example the continents already carried.
3. A free camera from orbit to the ground, with altitude displayed.

Aim: see with our eyes the sliding of the relief and the problem of the horizon, then choose the remedies.
