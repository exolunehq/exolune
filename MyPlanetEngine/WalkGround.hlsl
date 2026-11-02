// A 4 m local height field, read with the already existing frame fence. No physics terrain or new geometry.
#include "Relief.hlsli"
#include "SurfaceProbe.hlsli"
cbuffer WalkPoints : register(b0) { double4 centre; double4 axisX; double4 axisY; }
RWStructuredBuffer<float> heights : register(u0);
[numthreads(64,1,1)]
void CSMain(uint3 id : SV_DispatchThreadID, uint lane : SV_GroupIndex) {
    LoadGradients(lane, 64);
    if (id.x >= 81) return;
    const double2 xy = double2(int(id.x % 9) - 4, int(id.x / 9) - 4) * 0.5l;
    const double3 p = centre.xyz + axisX.xyz * xy.x + axisY.xyz * xy.y;
    const double3 d = SurfaceProbeDirection(p);
    gExactLattice = true;
    gMaxFrequency = NO_LIMIT;
    gCreaseMaxFrequency = PLANET_RADIUS_KM * 1000.0 / (MESH_BAND_LIMIT * CREASE_MIN_CELL);
    heights[id.x] = ReliefElevation(d);
}
