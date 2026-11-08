// Export the existing relief to the offline city planner. No alternate terrain.
#include "Relief.hlsli"
#include "SurfaceProbe.hlsli"
cbuffer CityGroundPoints : register(b0) { double4 cityCentre; double4 cityEast; double4 cityNorth; }
RWStructuredBuffer<float> cityHeights : register(u0);
[numthreads(64,1,1)]
void CSMain(uint3 id : SV_DispatchThreadID, uint lane : SV_GroupIndex) {
    LoadGradients(lane,64);
    const uint side=(uint)cityCentre.w;
    if(id.x>=side*side)return;
    const double2 xy=double2(int(id.x%side)-int(side/2),int(id.x/side)-int(side/2))*cityEast.w;
    const double3 p=cityCentre.xyz+cityEast.xyz*xy.x+cityNorth.xyz*xy.y;
    gExactLattice=true;gMaxFrequency=NO_LIMIT;
    gCreaseMaxFrequency=PLANET_RADIUS_KM*1000.0/(MESH_BAND_LIMIT*CREASE_MIN_CELL);
    cityHeights[id.x]=ReliefElevation(SurfaceProbeDirection(p));
}
