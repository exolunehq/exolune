// The terrain mesh in a flight (docs/optimisation.md, round 8): TerrainCompute.hlsl, the lattice split in pairs of floats
// (Noise.hlsli) for every vertex but the one under the camera, left to the exact shader. A shader of its own: the
// exact one stays the same binary, its results the same to the last bit; the same code compiled with more beside it
// changed them.
#define LATTICE_PAIRS
#include "TerrainCompute.hlsl"
