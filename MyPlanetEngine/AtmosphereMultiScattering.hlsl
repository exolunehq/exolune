// Atmosphere table 2 of 3, at startup: multiple scattering, per unit sun illuminance (Hillaire 2020, part 5.5).
// For each altitude and sun height: the light scattered twice, from every direction, with an isotropic
// phase, L2; and the share of light that scatters again, f. Infinite bounces sum to L2 / (1 - f). A slice per haze's ground.
#include "Planet.hlsli"
#define ATMOSPHERE_TABLE 1
#include "Atmosphere.hlsli"

RWTexture3D<float4> output : register(u1);

[numthreads(8, 8, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    const float2 uv = (id.xy + 0.5) / MULTI_SCATTERING_SIZE;
    const float muS0 = SunCosineFromUv(uv.x, MULTI_SCATTERING_SIZE.x);
    const float h0 = FromTexture(uv.y, MULTI_SCATTERING_SIZE.y) * ATMOSPHERE_HEIGHT_KM;
    const float ground = SliceGround(id.z);
    const float r0 = BOTTOM + h0, h0Term = h0 * (2.0 * BOTTOM + h0);
    const float3 sun = float3(sqrt(max(0.0, 1.0 - muS0 * muS0)), 0.0, muS0); // local frame, z up; muS0 may round past 1
    const float isotropic = 1.0 / (4.0 * PI);

    const uint directions = 64, steps = 20;
    float3 secondOrder = 0.0, transfer = 0.0;
    for (uint k = 0; k < directions; ++k)
    {
        // Fibonacci sphere: evenly spread directions.
        const float mu = 1.0 - 2.0 * (k + 0.5) / directions;
        const float phi = k * 2.39996323;
        const float3 dir = float3(sqrt(1.0 - mu * mu) * cos(phi), sqrt(1.0 - mu * mu) * sin(phi), mu);
        const float nu = dot(dir, sun);

        float end = DistanceToTop(h0, mu);
        const float groundDisc = r0 * r0 * mu * mu - h0Term;
        const bool hitsGround = mu < 0.0 && groundDisc >= 0.0;
        if (hitsGround)
            end = -r0 * mu - sqrt(groundDisc);

        const float dt = end / steps;
        float3 transmittance = 1.0;
        for (uint i = 0; i < steps; ++i)
        {
            const float t = (i + 0.5) * dt;
            const float r = sqrt(r0 * r0 + t * (2.0 * r0 * mu + t));
            const float h = HeightFrom(h0Term + t * (2.0 * r0 * mu + t), r);
            const float muS = clamp((r0 * muS0 + t * nu) / r, -1.0, 1.0);
            const Medium m = MediumAlong(HeightAlong(h0, mu, t - 0.5 * dt), h, HeightAlong(h0, mu, t + 0.5 * dt), ground.xxx);
            // Van de Hulst similarity: forward scattering is removed from isotropic transport.
            const float3 scattering = m.rayleigh + m.mie * (1.0 - MIE_ASYMMETRY);
            const float3 extinction = m.extinction - MIE_ASYMMETRY * m.mie;
            const float3 stepTransmittance = exp(-extinction * dt);
            const float3 integral = transmittance * (1.0 - stepTransmittance) / max(extinction, 1e-9);
            secondOrder += integral * scattering * SunTransmittance(h, muS, ground) * isotropic;
            transfer += integral * scattering;
            transmittance *= stepTransmittance;
        }
        if (hitsGround) // the ground sends back the sunlight it receives, as a Lambertian surface
        {
            const float muS = clamp((r0 * muS0 + end * nu) / BOTTOM, -1.0, 1.0);
            secondOrder += transmittance * SunTransmittance(0.0, muS, ground) * saturate(muS) * AIR_GROUND_ALBEDO / PI;
        }
    }
    // Integrals over the sphere weighted by the isotropic phase: 4 pi / N * sum * 1 / 4 pi, the mean.
    secondOrder /= directions;
    transfer /= directions;
    output[id] = float4(secondOrder / (1.0 - transfer), 1.0);
}
