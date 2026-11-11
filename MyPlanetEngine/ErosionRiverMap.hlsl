// The erosion and planet-map passes read the natural relief, never the city earthworks.
#define CITY_NATURAL_RELIEF
// The rivers' map for footprints wider than the level 0's cells (Erosion.hlsli, ErosionRiverMapRead), computed once at
// startup after the activity index. Each texel of each padded face: the complete evaluation at its direction, filtered over
// one of its cells, on the ground the rivers are drawn on, its channel beds folded into the ground's change.
#include "Relief.hlsli"

RWStructuredBuffer<uint2> outMap : register(u0);

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 tid : SV_DispatchThreadID, uint lane : SV_GroupIndex)
{
    LoadGradients(lane, 64);
    const uint n = ErosionSize(), m = n - 2u * EROSION_RIVER_MAP_PAD;
    const float cellKm = 0.001 * ErosionRiverMapCell();
    gMaxFrequency = PLANET_RADIUS_KM / (MESH_BAND_LIMIT * cellKm);
    gCreaseMaxFrequency = gMaxFrequency;
    gExactLattice = false;
    const float2 st = (float2(tid.x % n, tid.x / n) - EROSION_RIVER_MAP_PAD + 0.5) * (2.0 / m) - 1.0;
    const double3 p = (double3)normalize(ErosionDirection(group.y, st));
    const ReliefGround ground = ReliefSampleGround(p, true, true, true);
    uint2 texel = 0u;
    [branch] if (ErosionRivers() && ground.height > -500.0)
    {
        const ErosionRiver r = ErosionRiverFold(ErosionRivers(p, cellKm, ground.height, ground.riverParent, ground.riverFine),
                                                ground.height);
        const float stage = r.weight > 0.0 && r.coverage > 0.0 ? r.stage : 0.0;
        texel = uint2(f32tof16(r.fill - r.carve) | f32tof16(r.cut) << 16, f32tof16(r.coverage) | f32tof16(stage) << 16);
    }
    outMap[group.y * n * n + tid.x] = texel;
}
