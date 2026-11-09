// The screen relief (docs/spec-rendu-lointain.md): the true relief under each screen texel, recomputed whenever its
// inputs change, filtered at the texel's own footprint. Far off, the fine grid's cells span several pixels: lit and decided on
// it alone, the ground blurred into its cells and crawled as they slid, then sharpened once the per-pixel detail took
// over, its widest octave 6 km. The texels follow the pixels at every distance; only an identical query is reused.
#define EROSION_WAVE_LIST // neighbouring texels list their rivers' nodes together (Erosion.hlsli)
#include "ScreenRiverTasks.hlsli"

// Distance along the unit ray from the camera to the sphere of radius R + h, or -1 when it misses. The camera sits
// at (camPlane.xy, R + camAltitude) from the planet's centre; the radii's difference is taken apart, without cancellation.
float RayToSphere(float3 ray, float R, float camAltitude, float h)
{
    const float3 eye = float3(camPlane.xy, R + camAltitude);
    const float b = dot(ray, eye);
    const float c = (camAltitude - h) * (2.0 * R + camAltitude + h) + dot(camPlane.xy, camPlane.xy);
    const float disc = b * b - c;
    return disc < 0.0 ? -1.0 : -b - sqrt(disc);
}

// The face-plane point under the ray's hit on the sphere of radius R + h, and its footprint (m): the texel's angle at
// that distance, stretched along the view by the incidence. False when the ray misses.
bool PlaneHit(float3 ray, float R, float camAltitude, float h, float texelAngle, out float2 xy, out float footprint)
{
    xy = 0.0;
    footprint = 0.0;
    const float t = RayToSphere(ray, R, camAltitude, h);
    if (t <= 0.0)
        return false;
    const float3 d = normalize(float3(camPlane.xy, R + camAltitude) + t * ray);
    if (d.z <= 0.05)
        return false;
    xy = R * d.xy / d.z;
    footprint = t * texelAngle / max(-dot(ray, d), 0.1);
    return true;
}

// The texel's sample from its finished ground, as ScreenFinishTexel writes it (ScreenReliefWork.hlsli).
void ScreenWriteSample(uint id, float2 xy, float surface)
{
    float3 d;
    float r2, L;
    const float R = faceParams.y;
    PlanePoint(xy, R, d, r2, L);
    ScreenSample sample;
    sample.terrain = float4(RelativePosition(d, r2, L, R, faceParams.z, max(surface, gWaterLevel)), surface);
    sample.inland = float4(InlandSample(gWaterLevel, gWaterDepth, gWaterCoverage), gWaterDistance);
    sample.flow = float4(sample.inland.x * gWaterFlow, 0.0);
    sample.ground = float4(gRoughness, gVolcanic, 0.0, 0.0);
    outScreen[id] = sample;
}

// Compact tiles keep neighbouring rays together through variable river-search loops, especially at the limb.
[numthreads(8, 8, 1)]
void CSMain(uint3 threadId : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64); // before any return: every thread must reach the barrier
    if (all(threadId.xy == 0u)) riverCounter.Store(0, 0u);
    const uint w = (uint)screenRelief.x, h = (uint)screenRelief.y, id = threadId.y * w + threadId.x;
    if (threadId.x >= w || threadId.y >= h || screenRelief.z <= 0.0)
        return;
    ScreenSample missing = (ScreenSample)0;
    missing.terrain = asfloat(0x7fc00000u).xxxx; // NaN: no ground under the texel
    const float R = faceParams.y, camAltitude = faceParams.z;
    const float2 uv = (float2(threadId.xy) + 0.5) / float2(w, h) * 2.0 - 1.0;
    const float3 ray = normalize(camForward.xyz + uv.x * camRight.w * camRight.xyz - uv.y * camUp.w * camUp.xyz);
    const float texelAngle = taa.w * screenRelief.w;
    // At full weight, the first pass places the ground without its rivers; the second reads that elevation for the
    // parallax, and only it queries the rivers, once per texel (D3DApp::Draw). A nonpositive height keeps its sea-level
    // ground, still active for that query; a texel off the sphere stays inactive. Crossfaded with the fine grid, both
    // passes keep their rivers: a valley's incision then places its floor where the fine grid draws it.
    const bool single = screenRelief.z >= 1.0;
    // screenPass bit 1: every footprint reads the rivers' map, or no river is drawn (D3DApp::Draw). Both rays here and
    // their ground finished at once, as ScreenFinishTexel does, without the river passes and their scratch: the same samples.
    [branch] if ((screenPass & 2u) != 0u)
    {
        float2 xy;
        float footprint;
        if (!PlaneHit(ray, R, camAltitude, 0.0, texelAngle, xy, footprint))
        {
            outScreen[id] = missing;
            return;
        }
        ScreenBandwidth(footprint);
        double3 ground = ScreenWorldPoint(xy);
        // The first ray's ground leaves its rivers at full weight, as the passes' does; the second keeps them.
        float surface = ReliefFinishGround(ground, ReliefSampleGround(ground, ErosionMode() > 0u, true, single), ErosionMode() > 0u, true);
        [branch] if (surface > 0.0)
        {
            if (!PlaneHit(ray, R, camAltitude, surface, texelAngle, xy, footprint))
            {
                outScreen[id] = missing;
                return;
            }
            ScreenBandwidth(footprint);
            ground = ScreenWorldPoint(xy);
        }
        surface = ReliefFinishGround(ground, ReliefSampleGround(ground, ErosionMode() > 0u, true, false), ErosionMode() > 0u, true);
        ScreenWriteSample(id, xy, surface);
        return;
    }
    // screenPass bit 2, at full weight: the first ray queries no river (D3DApp::Draw). Its ground finished here, as
    // ScreenFinishTexel would; a nonpositive one stays active for the second pass's query, from the same ground.
    [branch] if ((screenPass & 4u) != 0u)
    {
        float2 xy;
        float footprint;
        if (!PlaneHit(ray, R, camAltitude, 0.0, texelAngle, xy, footprint))
        {
            screenWork[id].active = 0u;
            outScreen[id] = missing;
            return;
        }
        ScreenBandwidth(footprint);
        const double3 ground = ScreenWorldPoint(xy);
        ScreenWork work;
        work.xy = xy, work.footprint = footprint, work.active = 1u;
        work.ground = ReliefSampleGround(ground, ErosionMode() > 0u, true, true);
        const float surface = ReliefFinishGround(ground, work.ground, ErosionMode() > 0u, true);
        // Only a nonpositive ground keeps its work: the second pass queries its rivers from it.
        [branch] if (surface > 0.0)
            screenWork[id].active = 0u;
        else
            screenWork[id] = work;
        ScreenWriteSample(id, xy, surface);
        return;
    }
    const float elevation = screenPass == 0u ? 0.0 : outScreen[id].terrain.w;
    if (screenPass != 0u && !(elevation > 0.0))
    {
        if (!single) screenWork[id].active = 0u; // the first pass's query is final
        return;
    }
    screenWork[id].active = 0u;
    float2 xy;
    float footprint;
    if (!PlaneHit(ray, R, camAltitude, max(elevation, 0.0), texelAngle, xy, footprint))
    {
        outScreen[id] = missing;
        return;
    }
    ScreenBandwidth(footprint);
    ScreenWork work;
    work.xy = xy, work.footprint = footprint, work.active = 1u;
    work.ground = ReliefSampleGround(ScreenWorldPoint(xy), ErosionMode() > 0u, true, true);
    screenWork[id] = work;
}
