// The same two ray evaluations, scheduled as ground / rivers / finish to bound live shader state.
#include "Planet.hlsli"
#include "Relief.hlsli"
#include "Terrain.hlsli"

struct ScreenWork
{
    float2 xy;
    float footprint;
    uint active;
    ReliefGround ground;
}; // 4 + 39 scalar words; D3DApp::ScreenWorkBytes

RWStructuredBuffer<ScreenSample> outScreen : register(u0);
RWStructuredBuffer<ScreenWork> screenWork : register(u1);
cbuffer ScreenPass : register(b1) { uint screenPass; };

void ScreenBandwidth(float footprint)
{
    const float R = faceParams.y, band = 4.0;
    gMaxFrequency = R / (band * footprint);
    gCreaseMaxFrequency = R / (band * max(footprint, CREASE_MIN_CELL));
    gExactLattice = footprint < EXACT_LATTICE_MAX_CELL;
}

double3 ScreenWorldPoint(float2 xy)
{
    float3 d;
    float r2, L;
    const float R = faceParams.y;
    PlanePoint(xy, R, d, r2, L);
    const float3 offset = d.x * faceX.xyz + d.y * faceY.xyz - (r2 / (L * (R + L))) * faceZ.xyz;
    return nadir.xyz + (double3)offset;
}

// The texel's ground finished, its rivers queried, as its sample (ScreenRiverTexel.hlsl, ScreenRivers.hlsl).
void ScreenFinishTexel(uint id)
{
    const ScreenWork work = screenWork[id];
    ScreenBandwidth(work.footprint);
    const float elevation = ReliefFinishGround(ScreenWorldPoint(work.xy), work.ground, ErosionMode() > 0u, true);
    float3 d;
    float r2, L;
    const float R = faceParams.y;
    PlanePoint(work.xy, R, d, r2, L);
    ScreenSample sample;
    sample.terrain = float4(RelativePosition(d, r2, L, R, faceParams.z, max(elevation, gWaterLevel)), elevation);
    sample.inland = float4(InlandSample(gWaterLevel, gWaterDepth, gWaterCoverage), gWaterDistance);
    sample.flow = float4(sample.inland.x * gWaterFlow, 0.0);
    sample.ground = float4(gRoughness, gVolcanic, 0.0, 0.0);
    outScreen[id] = sample;
}
