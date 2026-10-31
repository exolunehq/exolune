// The lens's glare, up the pyramid (docs/recherche-halo.md). Each level adds to its own image the coarser one, spread
// by a 3 x 3 tent: the sum of the levels, blurs twice wider at each, all of the same weight, falls off as 1 / theta^2,
// the glare's law, the same at every scale. The last pass spreads it over the composite image, before the temporal
// smoothing and the tone curve: each level takes GLARE_OCTAVE of the light, and the image keeps the rest. The light is
// moved, never added.
#include "PlanetSettings.hlsli"

Texture2D<float4> coarse : register(t0); // the coarser level, its alpha the number of levels summed
SamplerState linearClamp : register(s0);
cbuffer GlarePass : register(b0) { float2 targetTexel; float apply; };

// The light that a straylight s, L = s E / theta^2 with theta in degrees, spreads over one octave of angle, from theta
// to 2 theta: 2 pi ln 2 (pi / 180)^2 s, whatever theta.
static const float GLARE_OCTAVE = 2.0 * 3.14159265 * 0.69314718 * (3.14159265 / 180.0) * (3.14159265 / 180.0) * GLARE_STRAYLIGHT;

float4 PSMain(float4 position : SV_POSITION) : SV_TARGET
{
    float2 size;
    coarse.GetDimensions(size.x, size.y);
    const float2 uv = position.xy * targetTexel;
    float4 c = 0.0;
    [unroll] for (int y = -1; y <= 1; ++y)
    [unroll] for (int x = -1; x <= 1; ++x)
        c += (2 - abs(x)) * (2 - abs(y)) / 16.0 * coarse.SampleLevel(linearClamp, uv + float2(x, y) / size, 0.0);
    // Blended: added to the level's own image; or, the last time, over the composite image, which keeps 1 - alpha.
    return apply > 0.5 ? GLARE_OCTAVE * c : c;
}
