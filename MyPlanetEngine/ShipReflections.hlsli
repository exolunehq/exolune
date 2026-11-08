// Same-frame scene reflections, completed by the physical atmosphere and the planet's actual maps.
// The world is rendered without this hull; t47 is never the render target being written.
#ifndef SHIP_REFLECTIONS_HLSLI
#define SHIP_REFLECTIONS_HLSLI
#include "BiomePalette.hlsli"
Texture2D<float4> reflectionScene : register(t47);
TextureCubeArray<float4> reflectionClimate : register(t10);

bool ReflectionUV(float3 p, out float2 uv)
{
    const float z = dot(p, camForward.xyz);
    uv = float2(dot(p, camRight.xyz) / camRight.w, -dot(p, camUp.xyz) / camUp.w) / max(z, 0.001) * 0.5 + 0.5;
    return z > 0.05 && all(uv > 0.001) && all(uv < 0.999);
}

float ReflectionEdge(float2 uv)
{
    return smoothstep(0.0, 0.075, min(min(uv.x, uv.y), min(1.0 - uv.x, 1.0 - uv.y)));
}

float3 ReflectionBiome(float temperature, float rain)
{
    const float t = saturate((temperature - BIOME_T_MIN) / (BIOME_T_MAX - BIOME_T_MIN)) * (BIOME_T_BINS - 1);
    const float h = saturate(log(max(rain, 1.0) / 100.0) / log(30.0)) * (BIOME_H_BINS - 1);
    const int ti = min((int)t, BIOME_T_BINS - 2), hi = min((int)h, BIOME_H_BINS - 2);
    return lerp(lerp(BIOME_PALETTE[ti * BIOME_H_BINS + hi].rgb, BIOME_PALETTE[ti * BIOME_H_BINS + hi + 1].rgb, h - hi),
                lerp(BIOME_PALETTE[(ti + 1) * BIOME_H_BINS + hi].rgb, BIOME_PALETTE[(ti + 1) * BIOME_H_BINS + hi + 1].rgb, h - hi), t - ti);
}

float3 ReflectionPlanet(float3 pos, float3 ray)
{
    const float3 up = camVertical.xyz, sun = lightDir.xyz;
    const float h = max(0.001, shipUp.w + dot(pos - shipModel[3].xyz, up) * 0.001);
    const float mu = dot(ray, up), muS = dot(sun, up);
    gTableGround = RegionalGround(PlanetDirection(up));
    ShadowRay shadow = (ShadowRay)0;
    float3 transmission;
    bool groundHit;
    float3 color = IntegrateScattering(h, mu, muS, dot(ray, sun), 1e7, 12, true, shadow, transmission, groundHit);
    if (groundHit)
    {
        // Stable sphere intersection, retaining the ship's altitude instead of subtracting two planet radii.
        const float radius = BOTTOM + h;
        const float distance = -radius * mu - sqrt(max(radius * radius * mu * mu - h * (2.0 * BOTTOM + h), 0.0));
        const float3 hitUp = normalize(up * radius + ray * distance);
        const float3 direction = PlanetDirection(hitUp);
        const float elevation = planetMap.SampleLevel(linearClamp, direction, 0.0).x;
        const float4 climate = reflectionClimate.SampleLevel(linearClamp, float4(direction, 0.0), 0.0);
        const float temperature = climate.y - 0.0065 * elevation;
        const float3 land = ReflectionBiome(temperature, climate.x);
        // The map stores zero on the sea. This fallback has biome colour, never invented tree silhouettes.
        const float3 albedo = lerp(float3(0.006, 0.018, 0.028), land, smoothstep(0.0, 4.0, elevation));
        const float hitSun = dot(hitUp, sun), ground = elevation * 0.001;
        const float3 irradiance = SUN_ILLUMINANCE * SunTransmittance(ground, hitSun, ground) * saturate(hitSun)
                                + SkyIrradiance(ground, hitSun, ground);
        color += transmission * albedo * irradiance / PI;
    }
    return max(color, 0.0);
}

float3 ReflectionFiltered(float2 uv, float distance, float travel, float roughness)
{
    float2 size;
    reflectionScene.GetDimensions(size.x, size.y);
    const float radius = min(8.0, roughness * roughness * travel * size.y / max(distance * camUp.w, 0.01));
    const float2 footprint = max(radius, 0.5) / size;
    float3 color = reflectionScene.SampleLevel(linearClamp, uv, 0.0).rgb * 2.0;
    float weight = 2.0;
    [unroll] for (uint i = 0; i < 4; ++i)
    {
        const float2 offset = i == 0 ? float2(1, 0) : i == 1 ? float2(-1, 0) : i == 2 ? float2(0, 1) : float2(0, -1);
        const float4 sample = reflectionScene.SampleLevel(linearClamp, uv + offset * footprint, 0.0);
        const float w = saturate(1.0 - abs(abs(sample.a) * 1000.0 - distance) / max(0.5, distance * 0.01));
        color += sample.rgb * w;
        weight += w;
    }
    return color / weight;
}

float3 ShipReflectedEnvironment(float3 pos, float3 normal, float3 ray, float roughness)
{
    const float3 fallback = ReflectionPlanet(pos, ray);
    const float3 origin = pos + normal * 0.035;
    float last = 0.0, travel = 0.15;
    const float limit = max(5000.0, shipUp.w * 4000.0);
    [loop] for (uint step = 0; step < 64 && travel < limit; ++step)
    {
        const float3 rayPoint = origin + travel * ray;
        float2 uv;
        if (!ReflectionUV(rayPoint, uv)) break;
        const float sceneDistance = abs(reflectionScene.SampleLevel(linearClamp, uv, 0.0).a) * 1000.0;
        const float delta = length(rayPoint) - sceneDistance;
        if (sceneDistance > 0.0 && delta > 0.0)
        {
            float lo = last, hi = travel;
            [unroll] for (uint refine = 0; refine < 7; ++refine)
            {
                const float mid = (lo + hi) * 0.5;
                const float3 p = origin + ray * mid;
                float2 q;
                ReflectionUV(p, q);
                const float depth = abs(reflectionScene.SampleLevel(linearClamp, q, 0.0).a) * 1000.0;
                if (depth > 0.0 && length(p) > depth) hi = mid; else lo = mid;
            }
            const float3 hit = origin + ray * hi;
            ReflectionUV(hit, uv);
            const float depth = abs(reflectionScene.SampleLevel(linearClamp, uv, 0.0).a) * 1000.0;
            const float error = abs(length(hit) - depth), thickness = 0.2 + depth * 0.002;
            const float confidence = ReflectionEdge(uv) * (1.0 - smoothstep(thickness, thickness * 2.0, error));
            if (depth > 0.0 && confidence > 0.0)
                return lerp(fallback, ReflectionFiltered(uv, depth, hi, roughness), confidence);
            break; // A depth discontinuity is not a reflected surface.
        }
        last = travel;
        travel = travel * 1.23 + 0.08;
    }
    // Clouds and sky at infinity use their actual rendered light when that direction is available.
    float2 skyUV;
    if (ReflectionUV(ray * 1e6, skyUV) && dot(ray, lightDir.xyz) < 0.9999)
    {
        const float4 sky = reflectionScene.SampleLevel(linearClamp, skyUV, 0.0);
        if (abs(sky.a) < 1e-7)
            return lerp(fallback, sky.rgb, ReflectionEdge(skyUV));
    }
    return fallback;
}

float3 ReflectionAerial(float3 color, float3 pos)
{
    const float distance = length(pos) * 0.001;
    const float3 ray = normalize(pos), up = camVertical.xyz;
    ShadowRay shadow = (ShadowRay)0;
    float3 transmission;
    bool hit;
    const float3 air = IntegrateScattering(max(camVertical.w, 0.001), dot(ray, up), dot(up, lightDir.xyz),
        dot(ray, lightDir.xyz), distance, 4, true, shadow, transmission, hit);
    const float cloudT = exp(-shipWeather[1].z * distance);
    const float3 cloudLight = SkyIrradiance(max(shipUp.w, 0.0), dot(up, lightDir.xyz), gTableGround) / PI;
    return (color * cloudT + cloudLight * (1.0 - cloudT)) * transmission + air;
}
#endif
