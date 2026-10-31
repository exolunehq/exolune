// The lens's glare, down the pyramid (docs/recherche-halo.md). Each level halves the previous one, from the composite
// image down to a few pixels, with Jimenez's 13 taps (Call of Duty: Advanced Warfare, 2014): five overlapping 2 x 2
// boxes, round and steady as the sources move. No threshold, no damping of bright pixels: the glare is linear, and the
// sun keeps its energy. Alpha 1: GlareUp.hlsl counts the levels with it.
Texture2D<float4> source : register(t0); // the composite image, or the previous level
SamplerState linearClamp : register(s0);
cbuffer GlarePass : register(b0) { float2 targetTexel; float apply; };

// Offsets in source texels, and weights: the centre box 1/2, the four corner boxes 1/8 each.
static const float3 TAPS[13] = {
    float3(0, 0, 0.125),
    float3(-1, -1, 0.125), float3(1, -1, 0.125), float3(-1, 1, 0.125), float3(1, 1, 0.125),
    float3(-2, 0, 0.0625), float3(2, 0, 0.0625), float3(0, -2, 0.0625), float3(0, 2, 0.0625),
    float3(-2, -2, 0.03125), float3(2, -2, 0.03125), float3(-2, 2, 0.03125), float3(2, 2, 0.03125) };

float4 PSMain(float4 position : SV_POSITION) : SV_TARGET
{
    float2 size;
    source.GetDimensions(size.x, size.y);
    const float2 uv = position.xy * targetTexel;
    float3 c = 0.0;
    [unroll] for (int i = 0; i < 13; ++i)
        c += TAPS[i].z * source.SampleLevel(linearClamp, uv + TAPS[i].xy / size, 0.0).rgb;
    return float4(all(isfinite(c)) ? c : 0.0, 1.0); // one broken pixel would veil the whole screen
}
