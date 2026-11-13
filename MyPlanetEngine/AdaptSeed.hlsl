// The local adaptation's first level (Adaptation.h; docs/recherche-tons-exposition.md). Each pixel, at a quarter of the
// screen's resolution, averages its 4 x 4 pixels of the composite image: their light in stops from the grey card under
// the global exposure, weighted. Surfaces count whole; the sky only where it is bright, never the black of space, which
// would darken the edge of a lit planet. The Sun counts as six stops over the grey card, no more: its region darkens,
// its glare does the rest. The tone map divides the stops by the weight (ToneMap.hlsl).
#include "Planet.hlsli"
#include "Atmosphere.hlsli" // the atmosphere tables, t1 to t3, and the sampler
#include "Coordinates.hlsli"
#include "SceneExposure.hlsli"

Texture2D<float4> composite : register(t0); // alpha: distance (km), 0 for the sky, negative on the waves
Texture2D<float4> glareLight : register(t8); // the lens's glare summed over its levels (Glare.h)

static const float3 SEED_LUMINANCE = float3(0.2126, 0.7152, 0.0722); // Rec. 709

float4 PSMain(float4 position : SV_POSITION) : SV_TARGET
{
    float2 size;
    composite.GetDimensions(size.x, size.y);
    const float exposure = Exposure();
    // The eye adapts to what it sees, the Sun's veil with it: near the Sun, a region holds its adaptation.
    const float veil = LOCAL_ADAPTATION_GLARE * GLARE_OCTAVE
        * dot(glareLight.SampleLevel(linearClamp, (position.xy * 4.0) / size, 0.0).rgb, SEED_LUMINANCE);
    float2 sum = 0.0;
    [unroll] for (int y = 0; y < 4; ++y)
    [unroll] for (int x = 0; x < 4; ++x)
    {
        const float4 c = composite.Load(int3(min(int2(position.xy) * 4 + int2(x, y), int2(size) - 1), 0));
        const float luminance = dot(c.rgb, SEED_LUMINANCE) + veil;
        if (!(luminance >= 0.0 && luminance < 1.0e30)) // a broken pixel would shift its whole region
            continue;
        const float stops = clamp(log2(max(luminance * exposure / 0.18, 1.0e-12)), -40.0, 6.0);
        const float weight = abs(c.a) > 0.0 ? 1.0 : smoothstep(-8.0, -4.0, stops);
        sum += weight * float2(stops, 1.0);
    }
    return float4(sum / 16.0, 0.0, 1.0);
}
