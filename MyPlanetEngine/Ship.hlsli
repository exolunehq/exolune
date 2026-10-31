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
    float4   shipOptions;   // x: 1 with the head-up display (U); y: 1 in the cockpit (the attitude jets hidden)
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

// Must match assets/vaisseau/paquet_moteur.py. mode: 0 opaque, 1 blended (the head-up display's combiner), 2 the canopy.
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

static const float3 SHIP_CENTRE = float3(0.0, -0.25, 0.55); // the shadow maps' sphere, ship frame (m)
static const float SHIP_RADIUS = 6.7;
// The canopy (assets/vaisseau/forme_chasseur.py, which this must match), d the distance from the nose tip, y = d - 5.32:
// in the plan, a blunt nose widening almost straight to 2 m wide at d = 4.55, then a round tail, the rear frame; over
// the deck a round section, (1 - s^2)^0.55, up to the crown. The deck's and the crown's heights, every 1/32 of its length.
static const float CANOPY_NOSE = 5.32, CANOPY_D0 = 2.58, CANOPY_DW = 4.55, CANOPY_D1 = 5.5;
static const float CANOPY_Y0 = CANOPY_D0 - CANOPY_NOSE, CANOPY_Y1 = CANOPY_D1 - CANOPY_NOSE, CANOPY_W = 1.0;
static const float CANOPY_DECK[33] = { 0.7484, 0.7511, 0.7533, 0.7554, 0.7580, 0.7616, 0.7662, 0.7717, 0.7777, 0.7837, 0.7895, 0.7950, 0.8003, 0.8055, 0.8106, 0.8159, 0.8212, 0.8268, 0.8326, 0.8388, 0.8454, 0.8526, 0.8605, 0.8689, 0.8776, 0.8865, 0.8954, 0.9046, 0.9159, 0.9279, 0.9389, 0.9469, 0.9500 };
static const float CANOPY_CROWN[33] = { 0.8100, 0.8562, 0.9025, 0.9478, 0.9914, 1.0336, 1.0705, 1.1036, 1.1342, 1.1624, 1.1880, 1.2115, 1.2334, 1.2539, 1.2730, 1.2907, 1.3072, 1.3236, 1.3394, 1.3538, 1.3658, 1.3747, 1.3811, 1.3867, 1.3914, 1.3953, 1.3986, 1.4012, 1.4033, 1.4051, 1.4067, 1.4083, 1.4100 };
// The water map's rectangle in the ship's plan (m), around the bubble, and its size (texels, 1.2 mm). Must match
// Ship::WaterWidth, WaterHeight.
static const float2 WATER_ORIGIN = float2(-1.01, CANOPY_Y0 - 0.01);
static const float WATER_TEXEL = 0.0012;
static const uint2 WATER_SIZE = uint2(1684, 2450);

float CanopyDeck(float d)
{
    const float f = saturate((d - CANOPY_D0) / (CANOPY_D1 - CANOPY_D0)) * 32.0; const uint i = min((uint)f, 31u);
    return lerp(CANOPY_DECK[i], CANOPY_DECK[i + 1], f - i);
}
float CanopyCrown(float d)
{
    const float f = saturate((d - CANOPY_D0) / (CANOPY_D1 - CANOPY_D0)) * 32.0; const uint i = min((uint)f, 31u);
    return lerp(CANOPY_CROWN[i], CANOPY_CROWN[i + 1], f - i);
}
// The bubble's half-width at the deck, before its tail (forme_chasseur.bulle_l).
float CanopyBase(float d)
{
    if (d <= CANOPY_D0) return 0.0;
    if (d >= CANOPY_DW) return 1.0;
    return (1.0 - 0.6 * pow(max(0.0, (4.7 - d) / 2.0), 1.6)) * pow(saturate(1.0 - pow(max(0.0, (CANOPY_D0 + 0.2 - d) / 0.2), 2.5)), 0.4);
}
// The glass's outline: the bubble's sides, then its round tail (x_cadre).
float CanopyHalfWidth(float y)
{
    const float d = y + CANOPY_NOSE;
    if (d <= CANOPY_DW) return CanopyBase(d);
    return pow(saturate(1.0 - pow(saturate((d - CANOPY_DW) / (CANOPY_D1 - CANOPY_DW)), 2.3)), 1.0 / 2.3);
}
// Inside the outline, with a margin (m): the half-width's excess over its slope, a distance near the outline.
float CanopyInside(float2 p)
{
    const float e = 0.005, g = (CanopyHalfWidth(p.y + e) - CanopyHalfWidth(p.y - e)) / (2.0 * e);
    return (CanopyHalfWidth(p.y) - abs(p.x)) / sqrt(1.0 + g * g);
}
bool OnCanopy(float2 p, float margin) { return CanopyInside(p) > margin; }
// The bubble's height over a point of the plan.
float CanopyZ(float2 p)
{
    const float d = p.y + CANOPY_NOSE, deck = CanopyDeck(d), s = saturate(abs(p.x) / max(CanopyBase(d), 1e-4));
    return deck + (CanopyCrown(d) - deck) * pow(saturate(1.0 - s * s), 0.55);
}
// The bubble's outward normal, ship frame, by its slopes over 5 mm; its flanks stand near the vertical by the rim.
float3 CanopyNormal(float2 p)
{
    const float e = 0.005;
    const float dx = CanopyZ(p + float2(e, 0.0)) - CanopyZ(p - float2(e, 0.0)), dy = CanopyZ(p + float2(0.0, e)) - CanopyZ(p - float2(0.0, e));
    return normalize(float3(-dx, -dy, 2.0 * e));
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
