// The canopy's weather, one thread per frame: what the air around the ship leaves on its glass. In a cloud it wets and
// mists; under a shower's cloud base it takes rain; below freezing, frost grows from its water; the airflow dries it.
// The state persists from frame to frame (Ship::mWeather), read by ShipGlass.hlsl.
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "Materials.hlsli"
// The climate map (Climate.hlsli), its first cube: y, the year's mean temperature at sea level.
TextureCubeArray<float4> shipClimate : register(t10);
#include "Relief.hlsli" // for Terrain.hlsli, not called
#include "Terrain.hlsli"
#include "Mesh.hlsli"
#include "Shadows.hlsli"
#include "Ship.hlsli"
#include "Clouds.hlsli"
#include "WorldWeather.hlsli"

RWStructuredBuffer<float4> weatherState : register(u0);
StructuredBuffer<FaceVertex> shipTerrain : register(t50); // the mesh, after its horizon pass

// The share of the sun the relief leaves the ship: the terrain's one march toward the sun (Shadows.hlsli), from the
// ship's origin, for the whole ship; its 10 m are much less than a shadow's penumbra.
float ShipReliefSun()
{
    const float R = faceParams.y;
    const float3 p = shipModel[3].xyz;                                   // camera-relative, face-local
    const float3 c = p + float3(camPlane.xy, R + faceParams.z);          // from the planet's centre
    const float3 up = normalize(c);
    float shadow;
    const float horizon = SunHorizon(shipTerrain, up.xy * (R / up.z), p, up, length(c) - R, shadow);
    return SunAboveHorizon(dot(up, lightDir.xyz), horizon, 0.0);
}

[numthreads(1, 1, 1)]
void CSMain()
{
    const float dt = shipAir.y, air = shipAir.x;
    // D3DApp supplies a weather frame centred on the ship, even for a distant exterior camera.
    const float altitudeKm = shipUp.w;
    const float3 dir = normalize((float3)cloudCameraKm.xyz);
    const float temperature = shipClimate.SampleLevel(linearClamp, float4(dir, 0.0), 0.0).y - 6.5 * altitudeKm;
    const float3 weather = WorldWeather(cloudCameraKm.xyz);
    const float rain=weather.x, inCloud=weather.y, extinction=weather.z;
    float4 s = weatherState[0]; // wet, rain, frost
    const float4 t = weatherState[1];
    const float cold = saturate(-temperature / 10.0);
    // A cloud's droplets are caught the faster the ship goes through them (ShipWater.hlsli gathers them into drops). The
    // glass's wetness, which shows the fine beads (ShipGlass.hlsl), comes at once, within a quarter of a second of entering the
    // cloud; out of the water it goes in a quarter of a minute or so, a little faster in fast air.
    float catching = saturate(inCloud * 4.0) * (0.5 + saturate(air / 40.0));
    s.x = saturate(s.x + dt * (6.0 * catching + 1.5 * rain) - dt * (0.04 + 0.0002 * min(air, 400.0) + 2.0 * ShipVacuum()) * (1.0 - max(inCloud, rain)));
    s.y = lerp(s.y, rain, saturate(dt * 2.0));
    // Frost needs water: in dry air, however cold, the glass stays clear.
    s.z = saturate(s.z + dt * 0.08 * cold * (inCloud + 0.3 * s.x) - dt * 0.05 * saturate(temperature / 5.0));
    s.w = 0.0;
    // A forced state, for the captures (MYPLANETENGINE_VERRIERE): 1 rain, 2 in a cloud, 3 frost.
    float cloud = inCloud;
    if (shipAir.w > 2.5)      s = float4(0.35, 0.0, 0.9, 0.0);
    else if (shipAir.w > 1.5) { s = float4(0.9, 0.1, 0.0, 0.0); cloud = 1.0; catching = 1.0; }
    else if (shipAir.w > 0.5) s = float4(0.95, 1.0, 0.0, 0.0);
    weatherState[0] = s;
    weatherState[1] = float4(cloud, temperature, extinction, fmod(t.w + dt, 3600.0));
    weatherState[2] = float4(catching, ShipReliefSun(), 0.0, 0.0);
}
