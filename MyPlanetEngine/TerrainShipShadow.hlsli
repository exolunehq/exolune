#ifndef TERRAIN_SHIP_SHADOW_HLSLI
#define TERRAIN_SHIP_SHADOW_HLSLI
Texture2D<float> shipSunMap : register(t44); // the ship's own map towards the sun (Ship.h)

// The ship's shadow on the ground and the sea: its map towards the sun, read beyond its sphere along the sun. The sun's
// disc blurs it with the distance behind the ship, its penumbra 0.0093 rad wide: the mean of 16 taps over that disc.
// Some kilometre back the penumbra is as wide as the ship, and the shadow fades out.
float ShipShadowOn(float3 p)
{
    [branch] if (shipSphere.w <= 0.0)
        return 1.0;
    const float4 c = mul(float4(p, 1.0), shipSunShadow);
    const float behind = c.z * 39.9 + 0.1 - 20.0; // m behind the ship's centre (Ship.cpp, LightFrame: 0.1 to 40 m)
    const float2 uv = c.xy * float2(0.5, -0.5) + 0.5;
    if (c.z < 0.0 || behind > 3000.0 || any(abs(uv - 0.5) > 0.5 + 0.00465 * behind / 13.4))
        return 1.0;
    const float radius = max(0.7107 * behind, 1.0); // the penumbra's, in the map's 6.5 mm texels
    float lit = 0.0;
    [loop] for (uint k = 0; k < 16; ++k)
    {
        const float r = sqrt((k + 0.5) / 16.0) * radius, a = k * 2.39996; // Vogel's disc
        const int2 t = int2(uv * 2048.0 + r * float2(cos(a), sin(a)));
        const float depth = all(t >= 0) && all(t < 2048) ? shipSunMap.Load(int3(t, 0)) : 1.0;
        lit += depth < min(c.z, 0.999) - 0.002 ? 0.0 : 1.0;
    }
    return lerp(lit / 16.0, 1.0, smoothstep(1000.0, 3000.0, behind));
}

#endif
