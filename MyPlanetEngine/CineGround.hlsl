// The cinematic safety clamp reads the exact relief at the current camera and ship.
#include "Relief.hlsli"
cbuffer Points : register(b0) { double4 points[2]; }
RWStructuredBuffer<float> ground : register(u0);
[numthreads(64,1,1)]
void CSMain(uint3 id : SV_DispatchThreadID, uint lane : SV_GroupIndex) {
    LoadGradients(lane, 64);
    if (id.x >= 2) return;
    gExactLattice = true;
    gMaxFrequency = NO_LIMIT;
    gCreaseMaxFrequency = (PLANET_RADIUS_KM * 1000.0) / (MESH_BAND_LIMIT * CREASE_MIN_CELL);
    ground[id.x] = ReliefElevation(points[id.x].xyz);
}
