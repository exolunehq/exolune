// Atmosphere.hlsli - the Earth's atmosphere after Hillaire 2020 (A Scalable and Production Ready Sky and
// Atmosphere Rendering Technique): Rayleigh and Mie scattering, ozone absorption, multiple scattering.
// Three small tables, computed once at startup (AtmosphereTransmittance.hlsl, AtmosphereMultiScattering.hlsl,
// AtmosphereSkyIrradiance.hlsl); the sky and the aerial perspective are ray marched per pixel. See
// docs/log/spec-rendu.md, step B.
//
// Everything works from the altitude h above sea level (km) and cosines measured against the local
// vertical: the radius r = R + h never gets subtracted from R, which would cost float its precision. The haze alone
// rises with the regional ground under it, the planet map's (PlanetMap.hlsli).
#ifndef ATMOSPHERE_HLSLI
#define ATMOSPHERE_HLSLI
#include "PlanetSettings.hlsli"
#include "Planet.hlsli"
#include "Mesh.hlsli"
#include "PlanetMap.hlsli"
#include "Celestial.hlsli"

// The tables: (altitude, angle, the haze's ground), the third axis a slice per ground (GroundCoordinate).
Texture3D<float4> transmittanceLut   : register(t1); // transmittance to the top of the atmosphere
Texture3D<float4> multiScatteringLut : register(t2); // multiple scattering, per unit sun illuminance
Texture3D<float4> skyIrradianceLut   : register(t3); // sky light on a horizontal ground, sun included
StructuredBuffer<FaceVertex> shadowMesh : register(t9); // the mesh, with its shadow heights (Horizon.hlsl)
SamplerState linearClamp : register(s0);

static const float BOTTOM = PLANET_RADIUS_KM;
static const float TOP = PLANET_RADIUS_KM + ATMOSPHERE_HEIGHT_KM;
static const float PI = 3.14159265;
static const uint2 TRANSMITTANCE_SIZE = uint2(256, 64);
static const uint2 MULTI_SCATTERING_SIZE = uint2(32, 32);
static const uint2 SKY_IRRADIANCE_SIZE = uint2(64, 16);
static const float SKY_IRRADIANCE_MAX_HEIGHT = 10.0; // km: only the terrain needs it
// The tables hold an air that is the same everywhere, its haze on a ground of GROUND_SLICES heights, every 0.25 km from
// the sea to GROUND_MAX_KM, above the highest regional ground, 5.2 km (tools/banc_carte.py); linear in between (must
// match D3DApp.cpp).
static const uint GROUND_SLICES = 25;
static const float GROUND_MAX_KM = 6.0;

struct Medium
{
    float3 rayleigh;   // scattering
    float3 mie;        // scattering
    float3 extinction;
};

// The mean of exp(-h / H) over altitudes going linearly from h1 to h2 (km): exact; its series for a small difference.
float MeanDensity(float h1, float h2, float H)
{
    const float a = max(min(h1, h2), 0.0) / H, d = abs(h2 - h1) / H;
    return exp(-a) * (d < 1e-3 ? 1.0 - d * (0.5 - d / 6.0) : (1.0 - exp(-d)) / d);
}

// The haze's density at the height h above its ground (km), 1 in the boundary layer, falling off over HAZE_TOP_WIDTH_KM
// at its top: a logistic, whose integral is HAZE_TOP_KM - w softplus((HAZE_TOP_KM - h) / w). Its mean between two
// heights, exact. Below its ground, in a valley under the regional ground, the layer is as dense.
float HazeIntegral(float h)
{
    const float x = (HAZE_TOP_KM - h) / HAZE_TOP_WIDTH_KM;
    return HAZE_TOP_KM - HAZE_TOP_WIDTH_KM * (max(x, 0.0) + log(1.0 + exp(-abs(x))));
}

float MeanHaze(float h1, float h2)
{
    return abs(h2 - h1) < 1e-3 ? 1.0 / (1.0 + exp((0.5 * (h1 + h2) - HAZE_TOP_KM) / HAZE_TOP_WIDTH_KM))
                               : (HazeIntegral(h2) - HazeIntegral(h1)) / (h2 - h1);
}

// The mean of the medium along a step whose altitudes are hA, hM and hB at its start, middle and end: a step shows
// the mean of the air it crosses (docs/principes.md, the pixel's rule along the ray). Taken at its middle, a step of
// 8 km from orbit read the haze at 4 km for the mean of 0 to 8 km, 4.6 times too little, which a denser haze would turn
// into a change on the way down. Two halves, for a step that holds the ray's lowest point. ground: the haze's ground under
// the step's start, middle and end (km); the haze takes the heights above it, the rest of the air those above the sea.
Medium MediumAlong(float hA, float hM, float hB, float3 ground)
{
    const float rayleigh = 0.5 * (MeanDensity(hA, hM, RAYLEIGH_SCALE_HEIGHT) + MeanDensity(hM, hB, RAYLEIGH_SCALE_HEIGHT));
    const float mie = 0.5 * (MeanHaze(hA - ground.x, hM - ground.y) + MeanHaze(hM - ground.y, hB - ground.z));
    const float ozone = max(0.0, 1.0 - abs(max(hM, 0.0) - OZONE_CENTRE_KM) / OZONE_HALF_WIDTH_KM); // 30 km wide
    Medium m;
    m.rayleigh = RAYLEIGH_SCATTERING * rayleigh;
    m.mie = MIE_SCATTERING * mie;
    m.extinction = m.rayleigh + MIE_EXTINCTION * mie + OZONE_ABSORPTION * ozone;
    return m;
}


float RayleighPhase(float nu)
{
    return 3.0 / (16.0 * PI) * (1.0 + nu * nu);
}

float MiePhase(float nu) // Cornette-Shanks
{
    const float g = MIE_ASYMMETRY;
    return 3.0 / (8.0 * PI) * (1.0 - g * g) * (1.0 + nu * nu) / ((2.0 + g * g) * pow(abs(1.0 + g * g - 2.0 * g * nu), 1.5));
}

// h (r - R) of the radius r, without subtracting two large numbers: r^2 - R^2 = rSquaredMinusR2.
float HeightFrom(float rSquaredMinusR2, float r)
{
    return rSquaredMinusR2 / (r + BOTTOM);
}

// The altitude (km) at distance t along a ray from altitude h0, of cosine mu with the vertical there.
float HeightAlong(float h0, float mu, float t)
{
    const float r0 = BOTTOM + h0, h0Term = h0 * (2.0 * BOTTOM + h0);
    const float r = sqrt(max(0.0, r0 * r0 + t * (2.0 * r0 * mu + t)));
    return HeightFrom(h0Term + t * (2.0 * r0 * mu + t), r);
}

// Distance to the top of the atmosphere from altitude h, along a direction of cosine mu.
float DistanceToTop(float h, float mu)
{
    const float r = BOTTOM + h;
    return max(0.0, -r * mu + sqrt(max(0.0, r * r * (mu * mu - 1.0) + TOP * TOP)));
}

// Cosine of the horizon seen from altitude h: below it, rays hit the ground.
float HorizonCosine(float h)
{
    return -sqrt(max(0.0, h * (2.0 * BOTTOM + h))) / (BOTTOM + h);
}

// Texel centres at the ends of [0, 1].
float ToTexture(float x, uint size) { return 0.5 / size + x * (1.0 - 1.0 / size); }
float FromTexture(float u, uint size) { return (u - 0.5 / size) / (1.0 - 1.0 / size); }

// The tables' third coordinate, from the haze's ground (km); and the ground of a slice.
float GroundCoordinate(float ground) { return ToTexture(saturate(ground / GROUND_MAX_KM), GROUND_SLICES); }
float SliceGround(uint slice) { return slice * GROUND_MAX_KM / (GROUND_SLICES - 1); }

// Transmittance table, Bruneton 2017 mapping: x from the distance to the top, y from the altitude.
float2 TransmittanceUv(float h, float mu)
{
    const float H = sqrt(TOP * TOP - BOTTOM * BOTTOM);
    const float rho = sqrt(max(0.0, h * (2.0 * BOTTOM + h)));
    const float dMin = TOP - (BOTTOM + h), dMax = rho + H;
    return float2(ToTexture((DistanceToTop(h, mu) - dMin) / (dMax - dMin), TRANSMITTANCE_SIZE.x),
                  ToTexture(rho / H, TRANSMITTANCE_SIZE.y));
}

void TransmittanceFromUv(float2 uv, out float h, out float mu)
{
    const float H = sqrt(TOP * TOP - BOTTOM * BOTTOM);
    const float rho = H * FromTexture(uv.y, TRANSMITTANCE_SIZE.y);
    h = rho * rho / (sqrt(rho * rho + BOTTOM * BOTTOM) + BOTTOM);
    const float r = BOTTOM + h;
    const float dMin = TOP - r, dMax = rho + H;
    const float d = dMin + FromTexture(uv.x, TRANSMITTANCE_SIZE.x) * (dMax - dMin);
    mu = d == 0.0 ? 1.0 : clamp((H * H - rho * rho - d * d) / (2.0 * r * d), -1.0, 1.0);
}

// Sunlight reaching altitude h when the sun is at cosine muS, the haze on `ground` (km): the table, times the sun's
// visible part above the horizon (it sets over the width of its disc).
float3 SunTransmittance(float h, float muS, float ground)
{
    // Above the air, sunlight crosses it only if its ray enters it: the table from where the ray enters, else the whole
    // sun (a ship by a moon). The table's top row is not the light at any distance.
    if (h > ATMOSPHERE_HEIGHT_KM)
    {
        const float r = BOTTOM + h, enter = (1.0 - muS * muS) * r * r / (TOP * TOP); // squared sine at the top
        if (muS >= 0.0 || enter >= 1.0)
            return smoothstep(-SUN_ANGULAR_RADIUS, SUN_ANGULAR_RADIUS, muS - HorizonCosine(h));
        h = ATMOSPHERE_HEIGHT_KM;
        muS = -sqrt(1.0 - enter);
    }
    const float3 t = transmittanceLut.SampleLevel(linearClamp, float3(TransmittanceUv(h, muS), GroundCoordinate(ground)), 0.0).rgb;
    return t * smoothstep(-SUN_ANGULAR_RADIUS, SUN_ANGULAR_RADIUS, muS - HorizonCosine(h));
}

// Legacy cloud models predate the regional-ground axis; keep their sea-level atmosphere lookup.
float3 SunTransmittance(float h, float muS)
{
    return SunTransmittance(h, muS, 0.0);
}

float2 AltitudeSunUv(float h, float muS, float maxHeight, uint2 size)
{
    return float2(ToTexture(0.5 + 0.5 * sign(muS)*sqrt(abs(muS)), size.x), ToTexture(saturate(h / maxHeight), size.y));
}

float SunCosineFromUv(float u,uint size) { const float x=2.0*FromTexture(u,size)-1.0; return x*abs(x); }

float3 MultiScattering(float h, float muS, float ground)
{
    return multiScatteringLut.SampleLevel(linearClamp, float3(AltitudeSunUv(h, muS, ATMOSPHERE_HEIGHT_KM, MULTI_SCATTERING_SIZE),
                                                              GroundCoordinate(ground)), 0.0).rgb;
}

float3 MultiScattering(float h, float muS)
{
    return MultiScattering(h, muS, 0.0);
}

// The sky's light on a horizontal ground whose vertical is `vertical`, at altitude h; the moons' as Moonlight gives it.
float3 SkyIrradianceAt(float h, float muS, float ground, float3 vertical)
{
    float3 sky=skyIrradianceLut.SampleLevel(linearClamp, float3(AltitudeSunUv(h, muS, SKY_IRRADIANCE_MAX_HEIGHT, SKY_IRRADIANCE_SIZE),
                                                            GroundCoordinate(ground)), 0.0).rgb;
#ifndef ATMOSPHERE_TABLE
    sky+=NIGHT_IRRADIANCE;
    [unroll] for(uint i=0;i<3;++i) {
        const float mu=dot(MoonDirectionFrom(i,vertical*(PLANET_RADIUS_KM+h)),vertical);
        const float3 beam=SunTransmittance(h,mu,ground);
        const float3 scattered=skyIrradianceLut.SampleLevel(linearClamp,
            float3(AltitudeSunUv(h,mu,SKY_IRRADIANCE_MAX_HEIGHT,SKY_IRRADIANCE_SIZE),GroundCoordinate(ground)),0).rgb/PI;
        sky+=Moonlight(i)*(beam*saturate(mu)+scattered);
    }
#endif
    return sky;
}

// Under the camera: the moons' elevations are those of the camera's vertical.
float3 SkyIrradiance(float h, float muS, float ground)
{
#ifndef ATMOSPHERE_TABLE
    return SkyIrradianceAt(h, muS, ground, camVertical.xyz);
#else
    return SkyIrradianceAt(h, muS, ground, float3(0.0, 1.0, 0.0));
#endif
}

float3 SkyIrradiance(float h, float muS)
{
    return SkyIrradiance(h, muS, 0.0);
}

// The haze's ground under the unit direction d, in the planet's frame (km): the planet map's ground, the sea's surface
// over the sea, smoothed over HAZE_GROUND_SCALE_KM. The mip whose texels span twice that, read linearly: a box and a tent
// of that width, a deviation of HAZE_GROUND_SCALE_KM.
float RegionalGround(float3 d)
{
    return planetMap.SampleLevel(linearClamp, d, MapLevel(d, 2000.0 * HAZE_GROUND_SCALE_KM)).x / 1000.0;
}

// A direction of the face's frame, in the planet's: where the planet map is read.
float3 PlanetDirection(float3 p)
{
    return normalize(p.x * faceX.xyz + p.y * faceY.xyz + p.z * faceZ.xyz);
}

// A ray over the relief, through its shadow (the mesh's shadow heights, Horizon.hlsl) and over the haze's ground
// (PlanetMap.hlsli): its origin, from the planet's centre, and its direction, in the face's frame (km). The tables,
// without relief, leave it off.
struct ShadowRay
{
    float3 origin;
    float3 direction;
    bool on;
};

// How far the point at distance t along the ray, at altitude h, stands above the shadow height (km): negative in shadow.
// The shadow height is the one the march toward the sun gave each vertex with its horizon (Shadows.hlsli), bilinear
// between the four around the point, like the mesh's height: the relief's shadow in the air is that of the image.
// Beyond the mesh, no relief.
float ShadowMargin(ShadowRay ray, float t, float h)
{
    if (!ray.on || erosionMode.w!=0u)
        return 1.0;
    if (h > MAX_TERRAIN_HEIGHT / 1000.0)
        return h; // no relief that high
    const float3 p = ray.origin + t * ray.direction;
    uint4 ids;
    float2 f;
    if (!MeshCell(p.xy * (1000.0 * BOTTOM / p.z), ids, f))
        return h + 1.0;
    return h - Bilinear(float4(shadowMesh[ids.x].shadow, shadowMesh[ids.y].shadow, shadowMesh[ids.z].shadow,
                               shadowMesh[ids.w].shadow), f) / 1000.0;
}

// The tables' air is the same everywhere: the haze's ground of the slice being computed (km).
static float gTableGround = 0.0;

// The haze's ground under the point at distance t along the ray (km): the planet map's; the tables', without relief.
float GroundAlong(ShadowRay ray, float t)
{
    if (!ray.on)
        return gTableGround;
    const float3 p = ray.origin + t * ray.direction;
    return RegionalGround(PlanetDirection(p));
}

// The lit part of a segment whose margins above the shadow are a and b at its ends, linear between: a step shows
// the mean of its light, and a shaft's edge glides across it as the camera moves.
float LitPart(float a, float b)
{
    return saturate(max(a, b) / max(abs(a - b), 1e-9));
}

// Light scattered towards the eye along a ray, and the transmittance along it. The ray starts at altitude
// h0 (km), its direction has cosine mu with the vertical there; muS0 is the sun's cosine with that
// vertical, nu the cosine between the ray and the sun. It stops at maxDistance, the ground or the top of
// the atmosphere; from space, it starts where it enters the atmosphere. hitsGround tells whether it
// stopped on the ground before maxDistance. The sun's light scattered once is cut where the relief hides the sun
// (shadow); the sky's, scattered more, stays.
float3 IntegrateScattering(float h0, float mu, float muS0, float nu, float maxDistance, uint steps,
                           bool withMultiScattering, ShadowRay shadow, out float3 transmittance, out bool hitsGround)
{
    transmittance = 1.0;
    hitsGround = false;
    const float r0 = BOTTOM + h0;
    const float h0Term = h0 * (2.0 * BOTTOM + h0); // r0^2 - R^2
    const float topDisc = r0 * r0 * (mu * mu - 1.0) + TOP * TOP;
    if (topDisc < 0.0)
        return 0.0; // passes beside the atmosphere
    const float start = h0 > ATMOSPHERE_HEIGHT_KM ? max(0.0, -r0 * mu - sqrt(topDisc)) : 0.0;
    float end = min(maxDistance, -r0 * mu + sqrt(topDisc));
    const float groundDisc = r0 * r0 * mu * mu - h0Term;
    if (mu < 0.0 && groundDisc >= 0.0)
    {
        const float ground = -r0 * mu - sqrt(groundDisc);
        hitsGround = ground < end;
        end = min(end, ground);
    }
    if (end <= start)
        return 0.0;

    const float phaseR = RayleighPhase(nu), phaseM = MiePhase(nu);
    const float dt = (end - start) / steps;
    float3 light = 0.0;
    float hA = HeightAlong(h0, mu, start), marginA = ShadowMargin(shadow, start, hA), groundA = GroundAlong(shadow, start);
    [loop]
    for (uint i = 0; i < steps; ++i)
    {
        const float t = start + (i + 0.5) * dt;
        const float r = sqrt(max(0.0, r0 * r0 + t * (2.0 * r0 * mu + t)));
        const float h = HeightFrom(h0Term + t * (2.0 * r0 * mu + t), r);
        const float muS = clamp((r0 * muS0 + t * nu) / r, -1.0, 1.0);
        const float hB = HeightAlong(h0, mu, t + 0.5 * dt);
        const float groundM = GroundAlong(shadow, t), groundB = GroundAlong(shadow, t + 0.5 * dt);
        const Medium m = MediumAlong(hA, h, hB, float3(groundA, groundM, groundB));
        const float marginM = ShadowMargin(shadow, t, h), marginB = ShadowMargin(shadow, t + 0.5 * dt, hB);
        const float lit = 0.5 * (LitPart(marginA, marginM) + LitPart(marginM, marginB));
        hA = hB;
        marginA = marginB;
        groundA = groundB;
        float3 source = SunTransmittance(h, muS, groundM) * lit * (m.rayleigh * phaseR + m.mie * phaseM);
        if (withMultiScattering)
            // Van de Hulst similarity for the isotropic multiple-scattering source.
            source += MultiScattering(h, muS, groundM) * (m.rayleigh + m.mie * (1.0 - MIE_ASYMMETRY));
        source *= SUN_ILLUMINANCE;
#ifndef ATMOSPHERE_TABLE
        // Secondary sources scatter through this same air. The finite bodies supply their phase and eclipse flux.
        if (shadow.on) {
            const float3 view=normalize(shadow.direction);
            const float3 up=normalize(shadow.origin+view*t);
            [unroll] for(uint moon=0;moon<3;++moon) {
                const float3 dir=MoonDirectionFrom(moon,shadow.origin+view*t);
                const float moonMu=dot(up,dir), moonNu=dot(view,dir);
                source+=Moonlight(moon)*SunTransmittance(h,moonMu,groundM)
                    *(m.rayleigh*RayleighPhase(moonNu)+m.mie*MiePhase(moonNu));
            }
        }
#endif
        // Finite emission layer at 86--98 km; analytic step average prevents a skipped orbital limb.
        if (withMultiScattering) {
            const float previousHeight=HeightAlong(h0,mu,t-.5*dt);
            const float lo=min(previousHeight,hB), hi=max(previousHeight,hB);
            const float fraction=hi-lo>1e-4?saturate((min(hi,98.0)-max(lo,86.0))/(hi-lo))
                :(h>86.0 && h<98.0?1.0:0.0);
            source+=float3(.65,1.0,.75)*(3.8e-9/12.0)*fraction;
        }
        const float3 stepTransmittance = exp(-m.extinction * dt);
        light += transmittance * (source - source * stepTransmittance) / max(m.extinction, 1e-9);
        transmittance *= stepTransmittance;
    }
    return light;
}

#endif
