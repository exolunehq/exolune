// The erosion's level 0 input (Erosion.h), once at startup: the form before erosion at the centre of every cell of the
// tectonic map's cube (m), its octaves filtered to two cells, as the planet map's (PlanetMap.hlsl).
#include "Relief.hlsli"
#include "PlanetMap.hlsli"

RWStructuredBuffer<float> outElevation : register(u0); // face by face, row by row

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 threadId : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64);
    const uint face = group.y, texel = threadId.x, n = TectonicSize();
    const float3 d = normalize(CubeDirection(face, (float2(texel % n, texel / n) + 0.5) / n * 2.0 - 1.0));
    const float cell = 2.0 / n * max(abs(d.x), max(abs(d.y), abs(d.z)));
    gMaxFrequency = 1.0 / (MESH_BAND_LIMIT * cell);
    gCreaseMaxFrequency = gMaxFrequency;
    gExactLattice = false;
    outElevation[face * n * n + texel] = ReliefElevation((double3)d, false);
}
