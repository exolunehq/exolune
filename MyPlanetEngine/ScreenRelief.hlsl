// The screen relief (docs/spec-rendu-lointain.md): the true relief under each texel of the screen, recomputed every
// frame, filtered at the texel's own footprint. Far off, the fine grid's cells span several pixels: lit and decided on
// it alone, the ground blurred into its cells and crawled as they slid, then sharpened once the per-pixel detail took
// over, its widest octave 6 km. The texels follow the pixels instead, at every distance; nothing is kept.
#include "Planet.hlsli"
#include "Relief.hlsli"
#include "Terrain.hlsli"

static const float SCREEN_BAND_LIMIT = 4.0;

RWStructuredBuffer<ScreenSample> outScreen : register(u0); // position/elevation, roughness, fresh volcanic ground

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

[numthreads(64, 1, 1)]
void CSMain(uint3 threadId : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64); // before any return: every thread must reach the barrier
    const uint w = (uint)screenRelief.x, h = (uint)screenRelief.y, id = threadId.x;
    if (id >= w * h || screenRelief.z <= 0.0)
        return;
    ScreenSample missing = (ScreenSample)0;
    missing.terrain = asfloat(0x7fc00000u).xxxx; // NaN: no ground under the texel
    const float R = faceParams.y, camAltitude = faceParams.z;
    const float2 uv = (float2(id % w, id / w) + 0.5) / float2(w, h) * 2.0 - 1.0;
    const float3 ray = normalize(camForward.xyz + uv.x * camRight.w * camRight.xyz - uv.y * camUp.w * camUp.xyz);
    const float texelAngle = taa.w * screenRelief.w;
    // Sea level first, then the sphere through the relief found there: the parallax of a summit seen aslant.
    float2 xy;
    float footprint;
    float3 d, pos;
    float elevation = 0.0;
    [unroll] for (int pass = 0; pass < 2; ++pass)
    {
        if (!PlaneHit(ray, R, camAltitude, max(elevation, 0.0), texelAngle, xy, footprint))
        {
            outScreen[id] = missing;
            return;
        }
        // The relief kept down to SCREEN_BAND_LIMIT texels. The texels follow the view: what lies between them is
        // resampled at every frame the camera moves, where the mesh's cells stay on the ground.
        gMaxFrequency = R / (SCREEN_BAND_LIMIT * footprint);
        gCreaseMaxFrequency = R / (SCREEN_BAND_LIMIT * max(footprint, CREASE_MIN_CELL));
        gExactLattice = footprint < EXACT_LATTICE_MAX_CELL;
        elevation = TerrainAt(xy, R, camAltitude, d, pos);
    }
    ScreenSample sample;
    sample.terrain = float4(pos, elevation);
    sample.ground = float2(gRoughness, gVolcanic);
    outScreen[id] = sample;
}
