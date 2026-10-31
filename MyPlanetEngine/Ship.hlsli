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
    float4x4 shipPose[2];   // ship frame -> ship frame: the stick, the throttle (ShipPose)
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
// image: colour, metal-roughness (g roughness, b metal), normal, occlusion, emission; -1 without.
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

static const float3 SHIP_CENTRE = float3(0.0, -2.15, 0.05); // the shadow maps' sphere, ship frame (m)
static const float SHIP_RADIUS = 6.7;
// The water map's rectangle in the ship's plan (m) and its size (texels, 1.2 mm): the canopy's two panes, nose F
// (0, -4.02), sills S (+-0.9375, -0.523), apex A (0, 0.32). Must match Ship::WaterWidth, WaterHeight.
static const float2 WATER_ORIGIN = float2(-0.95, -4.05);
static const float WATER_TEXEL = 0.0012;
static const uint2 WATER_SIZE = uint2(1584, 3660);

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

// A vertex's moving part (assets/vaisseau/pieces_mobiles.py): its pose is 0 when fixed, in (0, 1] on the stick, (1, 2] on
// the throttle, its weight the fraction past the integer: the stick's boot bends from its flange.
float4x4 ShipPose(float pose)
{
    const float4x4 still = float4x4(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1);
    [branch] if (pose <= 0.0)
        return still;
    const uint part = min((uint)ceil(pose), 2u) - 1;
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
