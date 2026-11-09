// The screen relief's river passes (ScreenRiverTexel.hlsl, ScreenRivers.hlsl): the wide queries handed to a wave each.
#include "ScreenReliefWork.hlsli"
RWByteAddressBuffer riverCounter : register(u2);     // the wide queries
RWByteAddressBuffer riverDispatch : register(u3);    // their dispatch's arguments (ScreenRiverArgs.hlsl)
RWStructuredBuffer<uint> riverFallback : register(u4); // their texels

// One thread's query to the fallback's waves (ScreenRivers.hlsl).
void ScreenRiverFallbackThread(uint id)
{
    uint slot;
    riverCounter.InterlockedAdd(0, 1u, slot);
    riverFallback[slot] = id;
}

double3 ScreenRiverPoint(uint id)
{
    double3 p = ScreenWorldPoint(screenWork[id].xy);
    const double squared = p.x * p.x + p.y * p.y + p.z * p.z;
    double inverse = (double)rsqrt((float)squared);
    inverse *= 1.5 - 0.5 * squared * inverse * inverse;
    return p * inverse;
}
void ScreenRiverStore(uint id, ErosionRiver r)
{
    screenWork[id].ground.height += r.fill - r.carve;
    screenWork[id].ground.lakeLevel = r.lakeLevel;
    screenWork[id].ground.channelBed = r.bed;
    screenWork[id].ground.channelSurface = r.stage;
    screenWork[id].ground.channelDistance = r.distance;
    screenWork[id].ground.channelEdge = r.edge;
    screenWork[id].ground.channelCut = r.cut;
    screenWork[id].ground.channelCoverage = r.coverage;
    screenWork[id].ground.channelBank = r.bank;
    screenWork[id].ground.waterFlow = r.flow;
}
