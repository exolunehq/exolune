// Atmosphere table 3 of 3, at startup: the light the whole sky sends onto a horizontal ground, for each
// altitude and sun height, sun illuminance included. It lights the terrain's shadows. A slice per haze's ground.
#include "Planet.hlsli"
#include "Atmosphere.hlsli"

RWTexture3D<float4> output : register(u2);

[numthreads(8, 8, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    const float2 uv = (id.xy + 0.5) / SKY_IRRADIANCE_SIZE;
    const float muS = FromTexture(uv.x, SKY_IRRADIANCE_SIZE.x) * 2.0 - 1.0;
    const float h = FromTexture(uv.y, SKY_IRRADIANCE_SIZE.y) * SKY_IRRADIANCE_MAX_HEIGHT;
    gTableGround = SliceGround(id.z);
    const float3 sun = float3(sqrt(max(0.0, 1.0 - muS * muS)), 0.0, muS); // local frame, z up; muS may round past 1

    // Cosine-weighted directions over the upper hemisphere: irradiance = pi / N * sum of the radiances.
    const uint directions = 64;
    float3 irradiance = 0.0;
    for (uint k = 0; k < directions; ++k)
    {
        const float u = (k + 0.5) / directions, phi = k * 2.39996323;
        const float3 dir = float3(sqrt(u) * cos(phi), sqrt(u) * sin(phi), sqrt(1.0 - u));
        float3 transmittance;
        bool hitsGround;
        irradiance += IntegrateScattering(h, dir.z, muS, dot(dir, sun), 1e9, 24, true, (ShadowRay)0, transmittance, hitsGround);
    }
    output[id] = float4(irradiance * PI / directions, 1.0);
}
