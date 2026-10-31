// Atmosphere table 1 of 3, at startup: transmittance from (altitude, direction) to the top of the atmosphere, a slice
// per haze's ground.
#include "Planet.hlsli"
#include "Atmosphere.hlsli"

RWTexture3D<float4> output : register(u0);

[numthreads(8, 8, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    float h, mu;
    TransmittanceFromUv((id.xy + 0.5) / TRANSMITTANCE_SIZE, h, mu);
    const float ground = SliceGround(id.z);
    const float r0 = BOTTOM + h, h0Term = h * (2.0 * BOTTOM + h);
    const uint steps = 40;
    const float dt = DistanceToTop(h, mu) / steps;
    float3 opticalDepth = 0.0;
    for (uint i = 0; i < steps; ++i)
    {
        const float t = (i + 0.5) * dt;
        const float r = sqrt(r0 * r0 + t * (2.0 * r0 * mu + t));
        opticalDepth += MediumAlong(HeightAlong(h, mu, t - 0.5 * dt), HeightFrom(h0Term + t * (2.0 * r0 * mu + t), r),
                                    HeightAlong(h, mu, t + 0.5 * dt), ground.xxx).extinction * dt;
    }
    output[id] = float4(exp(-opticalDepth), 1.0);
}
