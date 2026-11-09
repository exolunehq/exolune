// Step B's first startup pass (docs/spec-erosion.md, the corridors), when the level 0 is computed: at each cell's node,
// its meanders' sinuosity, falling on the steep 25 km forms, its valley floor's factor, wider in erodible rock and narrower
// in mountains, and the forms' relief amplitude and the rock's erodibility, which set its corridor's walls
// (Erosion::Condition). The map's own gradient, as the prototype tools/hydro/couloirs.py reads it.
#include "Relief.hlsli"

// Face by face, row by row: x bits 0-3 the sinuosity, 4-7 the floor's factor (Erosion.h), 8-15 the erodibility x 64; y the
// amplitude (m).
RWStructuredBuffer<uint2> outNodes : register(u0);

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 threadId : SV_DispatchThreadID)
{
    const uint n = TectonicSize(), c = group.y * n * n + threadId.x;
    const TectonicSample map = TectonicFields((double3)ErosionNode(c, n));
    const float slope = length(map.formsGradient) / (1000.0 * PLANET_RADIUS_KM);
    const float sinuous = 1.0 - (1.0 - RIVER_SINUOUS.z) * smoothstep(RIVER_SINUOUS.x, RIVER_SINUOUS.y, slope);
    const float rock = clamp(map.erodibility, 0.25, 3.98);
    const float mountains = smoothstep(300.0, 1200.0, map.forms.y);
    const float floorLog = RIVER_FLOOR_ROCK * log2(rock) + log2(lerp(1.0, RIVER_FLOOR.w, mountains));
    const uint s = (uint)round(15.0 * (sinuous - RIVER_SINUOUS.z) / (1.0 - RIVER_SINUOUS.z));
    const uint f = (uint)round(15.0 * saturate((floorLog - RIVER_FLOOR_LOG2.x) / (RIVER_FLOOR_LOG2.y - RIVER_FLOOR_LOG2.x)));
    outNodes[c] = uint2(s | f << 4 | (uint)round(64.0 * rock) << 8, asuint(map.forms.y));
}
