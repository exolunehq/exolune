// The lens's glare, up the pyramid (docs/recherche-halo.md). Each level adds to its own image the coarser one, spread
// by a 3 x 3 tent: the sum of the levels, blurs twice wider at each, all of the same weight, falls off as 1 / theta^2,
// the glare's law, the same at every scale. The tone map spreads the finest level over the image (ToneMap.hlsl): each
// level takes GLARE_OCTAVE (PlanetSettings.hlsli) of the light, and the image keeps the rest. The light is moved, never
// added; it is shown at the observer's exposure, outside the local adaptation of the night hemisphere.
#include "PlanetSettings.hlsli"

Texture2D<float4> coarse : register(t0); // the coarser level, its alpha the number of levels summed
SamplerState linearClamp : register(s0);
cbuffer GlarePass : register(b0) { float2 targetTexel; float apply; };

float4 PSMain(float4 position : SV_POSITION) : SV_TARGET
{
    float2 size;
    coarse.GetDimensions(size.x, size.y);
    const float2 uv = position.xy * targetTexel;
    float4 c = 0.0;
    [unroll] for (int y = -1; y <= 1; ++y)
    [unroll] for (int x = -1; x <= 1; ++x)
        c += (2 - abs(x)) * (2 - abs(y)) / 16.0 * coarse.SampleLevel(linearClamp, uv + float2(x, y) / size, 0.0);
    // Blended: added to the level's own image.
    return c;
}
