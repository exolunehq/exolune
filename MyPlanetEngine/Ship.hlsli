// Ship.hlsli - the player's ship (Ship.h, assets/vaisseau): the pack's vertices and materials, the ship's frame, its own
// shadow maps and the glass's weather. Ship frame: Blender's, in metres, nose towards -y, up +z, the pilot's left +x.
#ifndef SHIP_HLSLI
#define SHIP_HLSLI
#include "ShipProfiles.h"

cbuffer ShipFrame : register(b3) // b1: the clouds' frame (Clouds.hlsli)
{
    float4x4 shipModel;     // ship frame -> face-local, camera-relative (m), for mul(float4(p, 1), shipModel)
    float4x4 shipShadow[2]; // ship frame -> shadow map clip space: [0] towards the sun, [1] from overhead (the sky)
    float4   shipSun;       // the sun's direction, ship frame
    float4   shipUp;        // the vertical, ship frame; w: the ship's altitude above the sea (km)
    float4   shipAir;       // x: airspeed as at sea level, the speed scaled by the air's thinning (m/s); y: frame time (s);
                            // z: clock (s), wraps at 3600; w: forced glass state, 0 off
    float4   shipVelocity;  // xyz: direction of flight, face-local; w: speed (m/s)
    float4   shipOptions;   // HUD, cockpit, ShipModel, local air density relative to sea level
    float4   shipAirflow;   // xyz: relative airflow direction in ship axes; w: thermal load from flight dynamics
    float4   shipWaterLayout; // width, height (texels), chart origin y (m), pitch (m)
    float4   shipThrust;    // x: the main engines, 0 to 1; y: roll right, z: lift, w: slide right, -1 to 1 (ShipPlume.hlsli)
    float4   shipTurn;      // x: pitch up, y: yaw right, -1 to 1; z: clock (s), wraps at 3600
    float4   shipCourse;    // the dashboard (ShipScreens.hlsli): heading, latitude, longitude (deg); w: the ground's height (km)
    float4   shipGauges;    // throttle command, surface altitude (km), lunar flag, total engine demand
    float4x4 shipPose[6];   // ship frame -> ship frame: the stick, the throttle, the four volets (ShipPose)
    float4   shipShockBounds; // half-extents of the external gas proxy, metric support-plane offset in w
};

cbuffer ShipDraw : register(b2)
{
    uint shipMaterial;  // the draw's material
    uint shipShadowMap; // the shadow pass's map
    uint shipResetWater; // compute only, first water frame
    uint shipDropGroups; // compute only, 64 particle slots per group
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
// [0] wet, rain, frost, max film (um). [1] cloud, temperature (C), extinction (1/km), clock.
// [2] collected water, relief sun, cloud sun, reset. [3,4] Dispatch XYZ as uint bits,
// then a float in w: water optics active, film retention per frame respectively.
StructuredBuffer<float4> shipWeather : register(t46);
// The water on the canopy (ShipWater.hlsli): its map over both panes, each texel the highest drop there, its height (um)
// in the high 16 bits and its number in the low ones; and the film the drops leave behind (um).
Texture2D<uint> shipWaterMap : register(t48);
Texture2D<float> shipWaterFilm : register(t49);
SamplerComparisonState shipShadowSampler : register(s4);
SamplerState shipSampler : register(s5); // wrapping, anisotropic

// The selected profile drives geometry and weather together. See ShipProfiles.h for the CPU dimensions.
bool ShipClassic() { return shipOptions.z < 0.5; }
bool ShipNavigator() { return shipOptions.z > 1.5; }
#include "ShipClassique.hlsli"
#include "ShipChasseur.hlsli"
#define SHIP_CENTRE (ShipNavigator() ? float3(0, 0, 0) : ShipClassic() ? CLASSIC_CENTRE : FIGHTER_SHIP_CENTRE)
static const float SHIP_RADIUS = 6.7;
#define WATER_TEXEL (shipWaterLayout.w)
#define WATER_ORIGIN (float2(-0.5 * shipWaterLayout.x * WATER_TEXEL, shipWaterLayout.z))
#define WATER_SIZE (uint2(shipWaterLayout.xy))

// The Navigator's virtual field follows the actual hull behind the cabin opening.
// Its optical chart is a 1.5 m radius spherical projection. The aperture angles
// follow assets/vaisseau/navigateur/cabine_maillage.py (13 of 28 sectors, above -0.2 rad).
static const float FIELD_RADIUS = 1.5, FIELD_HALF_ANGLE = SHIP_FIELD_HALF_ANGLE;
float2 CanopyChart(float3 local)
{
    if (!ShipNavigator()) return local.xy;
    return FIELD_RADIUS * float2(atan2(local.x, -local.y), atan2(local.z, length(local.xy)));
}
float FieldSillDistance(float2 q)
{
    return min(FIELD_RADIUS * FIELD_HALF_ANGLE - abs(q.x), q.y - SHIP_FIELD_FLOOR * FIELD_RADIUS);
}
bool OnCanopy(float2 p, float margin)
{
    if (ShipNavigator()) return FieldSillDistance(p) > margin && p.y < FIELD_RADIUS * 1.57079633;
    if (ShipClassic()) return ClassicOnCanopy(p, margin);
    return FighterOnCanopy(p, margin);
}
void CanopyFrame(float2 p, out float3 normal, out float3 chartX, out float3 chartY)
{
    if (ShipNavigator()) {
        float sa, ca, se, ce;
        sincos(p.x / FIELD_RADIUS, sa, ca);
        sincos(p.y / FIELD_RADIUS, se, ce);
        normal = float3(sa * ce, -ca * ce, se);
        // Convert a tangent displacement back to the azimuth/elevation chart.
        chartX = float3(ca, sa, 0.0) / max(ce, 0.2);
        chartY = float3(-sa * se, ca * se, ce);
    } else {
        normal = ShipClassic() ? ClassicCanopyNormal(p) : FighterCanopyNormal(p);
        chartX = float3(1.0, 0.0, 0.0);
        chartY = float3(0.0, 1.0, 0.0);
    }
}
float SillDistance(float3 local, float2 q)
{
    if (ShipNavigator()) return max(FieldSillDistance(q), 0.0);
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
float ShipVacuum() { return 1.0 - smoothstep(0.0126, 0.0821, shipOptions.w); }

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
