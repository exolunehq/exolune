// The erosion and planet-map passes read the natural relief, never the city earthworks.
#define CITY_NATURAL_RELIEF
// The planet map (PlanetMap.hlsli), once at startup: the relief's elevation at the centre of every texel of the cube
// (m), its octaves filtered to two texels, as the mesh's to two cells (TerrainCompute.hlsl). PlanetMap.cpp drains it.
#include "Relief.hlsli"
#include "PlanetMap.hlsli"

RWStructuredBuffer<float> outElevation : register(u0); // face by face, row by row

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 threadId : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64);
    const uint face = group.y, texel = threadId.x, n = PLANET_MAP_SIZE;
    const float3 d = normalize(CubeDirection(face, (float2(texel % n, texel / n) + 0.5) / n * 2.0 - 1.0));
    // The cell on the unit sphere, tangential, the largest: the face plane's 2 / n over its distance, 1 / max |d|.
    const float cell = 2.0 / n * max(abs(d.x), max(abs(d.y), abs(d.z)));
    gMaxFrequency = 1.0 / (MESH_BAND_LIMIT * cell);
    gCreaseMaxFrequency = gMaxFrequency;
    gExactLattice = false;
    outElevation[face * n * n + texel] = ReliefElevation((double3)d);
}
