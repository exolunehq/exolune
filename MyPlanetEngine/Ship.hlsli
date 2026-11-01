// Ship.hlsli - the player's ship (Ship.h, assets/vaisseau): the pack's vertices and materials, the ship's frame, its own
// shadow maps and the glass's weather. Ship frame: Blender's, in metres, nose towards -y, up +z, the pilot's left +x.
#ifndef SHIP_HLSLI
#define SHIP_HLSLI

cbuffer ShipFrame : register(b3) // b1: the clouds' frame (Clouds.hlsli)
{
    float4x4 shipModel;     // ship frame -> face-local, camera-relative (m), for mul(float4(p, 1), shipModel)
    float4x4 shipShadow[2]; // ship frame -> shadow map clip space: [0] towards the sun, [1] from overhead (the sky)
    float4   shipSun;       // the sun's direction, ship frame
    float4   shipUp;        // the vertical, ship frame; w: the ship's altitude above the sea (km)
    float4   shipAir;       // x: airspeed as at sea level, the speed scaled by the air's thinning (m/s); y: frame time (s);
                            // z: clock (s), wraps at 3600; w: forced glass state, 0 off
    float4   shipVelocity;  // xyz: direction of flight, face-local; w: speed (m/s)
    float4   shipOptions;   // x: 1 with the head-up display (U); y: 1 in the cockpit; z: ShipModel, 0 classic / 1 fighter
    float4   shipThrust;    // x: the main engines, 0 to 1; y: roll right, z: lift, w: slide right, -1 to 1 (ShipPlume.hlsli)
    float4   shipTurn;      // x: pitch up, y: yaw right, -1 to 1; z: clock (s), wraps at 3600
    float4   shipCourse;    // the dashboard (ShipScreens.hlsli): heading, latitude, longitude (deg); w: the ground's height (km)
    float4   shipGauges;    // x: the gas, 0 to 1
    float4x4 shipPose[6];   // ship frame -> ship frame: the stick, the throttle, the four volets (ShipPose)
};

cbuffer ShipDraw : register(b2)
{
    uint shipMaterial;  // the draw's material
    uint shipShadowMap; // the shadow pass's map
    uint2 shipDrawPad;
};

struct ShipVertex
{
    float3 pos;
    float3 normal;
    float4 tangent; // w: the bitangent's sign, glTF's convention
    float2 uv0;
    float2 uv1;     // the hull's second UV: rivets' normals and occlusion
    float  pose;    // the moving parts (ShipPose): 0 fixed
};

// Match chasseur/paquet_moteur.py (VSX3); Ship::Load expands classic VSX2 materials to this layout.
// mode: 0 opaque, 1 blended (the head-up display's combiner), 2 the canopy.
// image: colour, metal-roughness (g roughness, b metal), normal, occlusion, emission; -1 without. role: what the engine
// animates, the pack's ROLES: the dashboard's screens and dials (ShipScreens.hlsli), then these.
static const uint SHIP_ROLE_HOT = 7, SHIP_ROLE_STROBE = 8, SHIP_ROLE_BEACON = 9;
struct ShipMaterial
{
    float4 color;
    float3 emission;
    float  metallic;
    float  roughness;
    float  normalScale;
    float  occlusion;
    uint   mode;
    uint   doubleSided;
    int    image[5];
    uint   uv[5];
    uint   role;
};

StructuredBuffer<ShipVertex> shipVertices : register(t30);
StructuredBuffer<ShipMaterial> shipMaterials : register(t31);
Texture2D<float4> shipImages[12] : register(t32);
Texture2D<float> shipShadowMaps[2] : register(t44);
StructuredBuffer<float4> shipWeather : register(t46); // [0]: wet, rain, frost; [1]: in cloud, temperature (C), cloud
                                                      // extinction (1/km), clock (s); [2]: x the cloud's water caught
// The water on the canopy (ShipWater.hlsli): its map over both panes, each texel the highest drop there, its height (um)
// in the high 16 bits and its number in the low ones; and the film the drops leave behind (um).
Texture2D<uint> shipWaterMap : register(t48);
Texture2D<float> shipWaterFilm : register(t49);
SamplerComparisonState shipShadowSampler : register(s4);
SamplerState shipSampler : register(s5); // wrapping, anisotropic

// The selected profile drives geometry and weather together. See ShipProfiles.h for the CPU dimensions.
bool ShipClassic() { return shipOptions.z < 0.5; }
#include "ShipClassique.hlsli"
#include "ShipChasseur.hlsli"
#define SHIP_CENTRE (ShipClassic() ? CLASSIC_CENTRE : FIGHTER_SHIP_CENTRE)
static const float SHIP_RADIUS = 6.7;
#define WATER_ORIGIN (ShipClassic() ? CLASSIC_WATER_ORIGIN : FIGHTER_WATER_ORIGIN)
#define WATER_SIZE (ShipClassic() ? CLASSIC_WATER_SIZE : FIGHTER_WATER_SIZE)
static const float WATER_TEXEL = 0.0012;
#define CANOPY_W (ShipClassic() ? 0.94 : FIGHTER_CANOPY_W)
#define CANOPY_Y0 (ShipClassic() ? -4.0 : FIGHTER_CANOPY_Y0)
#define CANOPY_Y1 (ShipClassic() ? 0.3 : FIGHTER_CANOPY_Y1)
bool OnCanopy(float2 p, float margin)
{
    if (ShipClassic()) return ClassicOnCanopy(p, margin);
    return FighterOnCanopy(p, margin);
}
float3 CanopyNormal(float2 p)
{
    if (ShipClassic()) return ClassicCanopyNormal(p);
    return FighterCanopyNormal(p);
}
float SillDistance(float3 local)
{
    if (ShipClassic()) return ClassicSillDistance(local);
    return max(FighterCanopyInside(local.xy), 0.0);
}

struct ShipPixel
{
    float4 position : SV_POSITION;
    float3 pos      : POSITION;  // face-local, camera-relative (m)
    float3 local    : TEXCOORD0; // ship frame (m)
    float3 normal   : NORMAL;    // face-local
    float4 tangent  : TANGENT;   // face-local; w: the bitangent's sign
    float4 uv       : TEXCOORD1; // xy: uv0, zw: uv1
};

// The air too thin to hold water on the glass: from 20 to 35 km up it boils off, as on Earth above the Armstrong limit.
float ShipVacuum() { return smoothstep(20.0, 35.0, shipUp.w); }

// A vertex's moving part (assets/vaisseau/pieces_mobiles.py, design_chasseur.py): its pose is 0 when fixed, in (0, 1] on
// the stick, (1, 2] on the throttle, 3 to 6 on the elevons, its weight the fraction past the integer: the stick's boot bends
// from its flange.
float4x4 ShipPose(float pose)
{
    const float4x4 still = float4x4(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1);
    [branch] if (pose <= 0.0)
        return still;
    const uint part = min((uint)ceil(pose), 6u) - 1;
    return lerp(still, shipPose[part], pose - part);
}

float4 ShipImage(int image, uint set, float4 uv, float4 fallback)
{
    [branch] if (image < 0)
        return fallback;
    return shipImages[image].Sample(shipSampler, set != 0 ? uv.zw : uv.xy);
}

// The share of a ship map's light that reaches a point of the ship: 3 x 3 comparisons, spread wider for the sky.
float ShipLight(uint map, float3 local, float bias, float spread)
{
    const float4 c = mul(float4(local, 1.0), shipShadow[map]);
    const float2 uv = c.xy * float2(0.5, -0.5) + 0.5;
    if (any(uv < 0.0) || any(uv > 1.0))
        return 1.0;
    float lit = 0.0;
    [unroll] for (int y = -1; y <= 1; ++y)
    [unroll] for (int x = -1; x <= 1; ++x)
        lit += shipShadowMaps[map].SampleCmpLevelZero(shipShadowSampler, uv + float2(x, y) * spread / 2048.0, c.z - bias);
    return lit / 9.0;
}
#endif
