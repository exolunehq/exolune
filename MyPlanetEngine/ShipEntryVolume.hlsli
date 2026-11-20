// One external shock geometry for the ray-integrated gas and the particles it sheds.
// Ship space, metres. The selected VSX supplies the surfaces in this cube.
#ifndef SHIP_ENTRY_VOLUME_HLSLI
#define SHIP_ENTRY_VOLUME_HLSLI
#include "Ship.hlsli"
#include "ShipEntry.hlsli"

TextureCube<float4> shipShockHull : register(t52);

float3 EntryShockCentre() { return SHIP_CENTRE; }

// The separated gas opens downstream past the shoulders. This axial deformation
// and its exact inverse let streaks and optical rays traverse the same wake.
float3 EntryShockAdvect(float3 p)
{
    return p + shipAirflow.xyz * clamp(0.28 * (dot(p, shipAirflow.xyz) - 0.25), 0.0, 1.30);
}
float3 EntryShockUnadvect(float3 p)
{
    return p - shipAirflow.xyz * clamp((0.28 / 1.28) * (dot(p, shipAirflow.xyz) - 0.25), 0.0, 1.30);
}
float3 EntryShockBounds() { return shipShockBounds.xyz + 1.30 * abs(shipAirflow.xyz); }

struct EntryShockSection {
    float radius, radialScale, gap, thickness, bow, incidence;
    float3 normal;
};

EntryShockSection EntryShockProfile(float3 outward, float heat)
{
    EntryShockSection s;
    const float4 support = shipShockHull.SampleLevel(shipSampler, outward, 0.0);
    const float roundedRadius = length(support.yzw);
    s.normal = support.yzw / max(roundedRadius, 0.001);
    s.radius = support.x;
    s.radialScale = clamp((roundedRadius - support.x) / shipShockBounds.w, 1.0, 3.5);
    const float windward = dot(outward, -shipAirflow.xyz);
    s.incidence = dot(s.normal, -shipAirflow.xyz);
    s.bow = smoothstep(0.08, 0.97, 0.63 * windward + 0.37 * s.incidence);
    // Compressed air is detached ahead of the windward nose. Along the flanks
    // the inner edge approaches the body and the shearing gas spreads in depth.
    s.gap = (0.065 + 0.64 * s.bow) * (0.75 + 0.25 * heat);
    s.thickness = (0.32 + 0.28 * s.bow + 0.15 * saturate(-s.incidence)) * (0.73 + 0.27 * heat);
    return s;
}

float3 EntryShockPoint(float3 outwardDirection, float across, float heat)
{
    const float3 outward = normalize(outwardDirection);
    const EntryShockSection s = EntryShockProfile(outward, heat);
    return EntryShockCentre() + EntryShockAdvect(outward * (s.radius + (s.gap + across * s.thickness) * s.radialScale));
}

// Persistent hot areas are fixed in the gas around the hull. Their energy pulses
// slowly enough that a particle born in a bright patch can be followed downstream.
float EntryShockFeed(float3 outward, float time)
{
    const float2 site = float2(dot(outward, float3(2.17, -1.09, 1.71)),
                               dot(outward, float3(-1.47, 1.58, 2.36)));
    const float broad = EntryNoise(site * 1.14 + float2(7.8, 3.2));
    const float pulse = EntryNoise(site * 2.8 + float2(0.29 * time, -0.21 * time));
    return smoothstep(0.21, 0.77, 0.78 * broad + 0.22 * pulse);
}

struct EntryVolumePixel {
    float4 position : SV_Position;
    float3 local : TEXCOORD0;
};
#endif
