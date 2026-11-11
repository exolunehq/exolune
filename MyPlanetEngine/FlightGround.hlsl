// Sample and sweep a bounded terrain corridor. Only per-group first contacts reach the CPU through the frame fence.
// The probe, then the city's earthworks as the frame carries them: the contact meets the graded ground (CityGrade.hlsli).
cbuffer FlightPoints : register(b0) {
    double4 probeUp,probeAcross,probeAlong,probeGrid,probeShape;
    float4 movement;
    uint4 probeCount;
    double4 cityUp; float4 cityEast,cityNorth,cityGradeGrid;
    float4 cityPads[1800]; uint4 cityGradeCells[256]; uint4 cityGradeIndex[768];
}
#define CITY_GRADE_FIELDS
#define CITY_GRADE_RADIUS (PLANET_RADIUS_KM*1000.0)
#include "Relief.hlsli"
#include "SurfaceProbe.hlsli"
#include "FlightSweep.hlsli"
RWStructuredBuffer<float4> contacts : register(u0); // fraction, outward normal in the probe's local frame
groupshared float3 patch[33*33];
groupshared float4 candidates[64];
groupshared float recovery[64];
groupshared uint invalid;

[numthreads(64,1,1)]
void CSMain(uint lane : SV_GroupIndex,uint3 group : SV_GroupID) {
    LoadGradients(lane,64);
    if (lane==0) invalid=0;
    GroupMemoryBarrierWithGroupSync();
    const uint first=group.x*32, rows=min(32,probeCount.y-first), columns=probeCount.x;
    gExactLattice=true;
    gMaxFrequency=NO_LIMIT;
    gCreaseMaxFrequency=PLANET_RADIUS_KM*1000.0/(MESH_BAND_LIMIT*CREASE_MIN_CELL);
    for (uint i=lane;i<(rows+1)*columns;i+=64) {
        const double x=probeGrid.x+(double)(i%columns)*probeGrid.z;
        const double y=probeGrid.y+(double)(first+i/columns)*probeGrid.w;
        const double radius=probeShape.x;
        const double3 local=SurfaceProbeDirection(double3(x,y,radius));
        const double3 direction=probeAcross.xyz*local.x+probeAlong.xyz*local.y+probeUp.xyz*local.z;
        const float elevation=ReliefElevation(direction);
        const float level=max(max(elevation,gWaterLevel),0.0);
        const double r=radius+(double)level;
        patch[i]=float3((float)(local.x*r),(float)(local.y*r),(float)(local.z*r-radius-probeUp.w));
        if (!all(isfinite(patch[i]))) InterlockedOr(invalid,1);
    }
    GroupMemoryBarrierWithGroupSync();
    FlightHit best=FlightNoHit();
    float support=-1e20;
    if (group.x==0) for (uint i=lane;i<(rows+1)*columns;i+=64) {
        const float3 p=patch[i];
        // Teleport recovery alone uses this conservative local support. Ordinary movement uses the sweep below.
        if (abs(p.x)<=movement.w+(float)probeGrid.z && abs(p.y)<=movement.w+(float)probeGrid.w)
            support=max(support,p.z+movement.w);
    }
    const uint cells=rows*(columns-1);
    for (uint i=lane;i<cells;i+=64) {
        const uint a=(i/(columns-1))*columns+i%(columns-1);
        const float3 p=patch[a],q=patch[a+1],r=patch[a+columns],s=patch[a+columns+1];
        FlightHit h=FlightTriangle(p,q,s,movement.xyz,movement.w);
        if (h.fraction<best.fraction) best=h;
        h=FlightTriangle(p,s,r,movement.xyz,movement.w);
        if (h.fraction<best.fraction) best=h;
    }
    candidates[lane]=float4(best.fraction,best.normal);
    recovery[lane]=support;
    GroupMemoryBarrierWithGroupSync();
    for (uint stride=32;stride>0;stride>>=1) {
        if (lane<stride && candidates[lane+stride].x<candidates[lane].x) candidates[lane]=candidates[lane+stride];
        if (lane<stride) recovery[lane]=max(recovery[lane],recovery[lane+stride]);
        GroupMemoryBarrierWithGroupSync();
    }
    if (lane==0) contacts[group.x]=invalid!=0?float4(-1,0,0,0):candidates[0];
    if (lane==0 && group.x==0) {
        const uint zero=(uint)probeShape.w*columns+(uint)probeShape.z;
        const float startHeight=patch[zero].z+(float)probeUp.w;
        const double3 local=SurfaceProbeDirection(double3((double)movement.x,(double)movement.y,
            probeShape.x+probeUp.w+(double)movement.z));
        const float endHeight=ReliefElevation(probeAcross.xyz*local.x+probeAlong.xyz*local.y+probeUp.xyz*local.z);
        contacts[256]=float4(recovery[0],startHeight,max(max(endHeight,gWaterLevel),0.0),0);
    }
}
