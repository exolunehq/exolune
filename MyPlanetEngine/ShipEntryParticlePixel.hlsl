#include "Planet.hlsli"
#include "SceneExposure.hlsli"
#include "Ship.hlsli"
#include "ShipEntry.hlsli"

float4 PSMain(EntryParticlePixel input) : SV_Target
{
    const float2 at = input.uv; // in head radii, pointing downstream from the origin
    const float core = exp2(-4.9 * dot(at, at));
    const float bloom = 0.09 * exp2(-2.05 * dot(at, at));
    const float back = max(-at.x, 0.0), span = input.light.z;
    const float taper = saturate(back / max(span, 0.001));
    const float width = lerp(0.85, 0.39, taper);
    const float strand = exp2(-2.65 * at.y * at.y / (width * width) - 0.47 * back) *
                         smoothstep(0.0, 0.66, back) * smoothstep(0.0, 0.80, span - back);
    const float temperature = 1.0 - smoothstep(0.10, 0.84, input.light.y);
    const float3 grain = lerp(float3(0.96, 0.135, 0.016), float3(1.0, 0.60, 0.185), temperature);
    const float3 tail = lerp(float3(0.70, 0.047, 0.007), float3(1.0, 0.245, 0.038), temperature);
    const float3 emission = grain * core + float3(1.0, 0.29, 0.045) * bloom + 0.82 * tail * strand;
    return float4(emission * input.light.x * min(1.0, 1.3 / max(Exposure(), 1.0)), 1.0);
}
