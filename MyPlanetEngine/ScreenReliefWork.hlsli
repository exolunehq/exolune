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

void ScreenWriteSample(uint id, float2 xy, float footprint, float elevation, ReliefGround ground)
{
    const float roughness = gRoughness, volcanic = gVolcanic;
    float3 inland = InlandSample(gWaterLevel, gWaterDepth, gWaterCoverage);
    const float cell = 1000.0 * ground.cellKm;
    const float lakeCell = max(0.65 * cell, 0.5 * ErosionRiverMapCell());
    const float lakeShare = smoothstep(0.0, 0.25, 1.0 - lakeCell / max(cell, 1e-3));
    [branch] if (ErosionRivers() && ground.lakeLevel > 0.0 && lakeShare > 0.0)
    {
        // Retain the basin's depressions at the drainage scale, with at least 2.6 texels per wavelength.
        // Only refine the substrate. The existing channel cut and lake stage still determine the water column.
        ScreenBandwidth(footprint * lakeCell / cell);
        const ReliefGround finer = ReliefSampleGround(ScreenWorldPoint(xy), true, true, true);
        ScreenBandwidth(footprint);
        const float clearance = gLakeClearance + ground.coastHeight - finer.coastHeight;
        const float lakeCoverage = smoothstep(0.0, 0.001 * lakeCell, clearance);
        const float lakeDepth = lakeCoverage * max(clearance, 0.0);
        const float bed = ground.lakeLevel - gLakeClearance;
        const float riverStage = min(ground.channelSurface, bed + ground.channelCut);
        const float riverDepth = gRiverCoverage > 0.0
            ? lerp(ground.channelCut, max(riverStage - bed, 0.0), gRiverCoverage) : 0.0;
        const float3 refined = InlandSample(gWaterLevel, max(riverDepth, lakeDepth), max(gRiverCoverage, lakeCoverage));
        inland = lerp(inland, refined, lakeShare);
    }
    float3 d;
    float r2, L;
    const float R = faceParams.y;
    PlanePoint(xy, R, d, r2, L);
    ScreenSample sample;
    sample.terrain = float4(RelativePosition(d, r2, L, R, faceParams.z, max(elevation, gWaterLevel)), elevation);
    sample.inland = float4(inland, gWaterDistance);
    sample.flow = float4(min(sample.inland.x, gWaterCoverage) * gWaterFlow, 0.0);
    sample.ground = float4(roughness, volcanic, 0.0, 0.0);
    outScreen[id] = sample;
}

// The texel's ground finished, its rivers queried, as its sample (ScreenRiverTexel.hlsl, ScreenRivers.hlsl).
void ScreenFinishTexel(uint id)
{
    const ScreenWork work = screenWork[id];
    ScreenBandwidth(work.footprint);
    const float elevation = ReliefFinishGround(ScreenWorldPoint(work.xy), work.ground, ErosionMode() > 0u, true);
    ScreenWriteSample(id, work.xy, work.footprint, elevation, work.ground);
}
