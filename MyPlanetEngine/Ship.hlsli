// Ship.hlsli - the player's ship (Ship.h, assets/vaisseau): the pack's vertices and materials, the ship's frame, its own
// shadow maps and the glass's weather. Ship frame: Blender's, in metres, nose towards -y, up +z, the pilot's left +x.
#ifndef SHIP_HLSLI
#define SHIP_HLSLI
#include "ShipProfiles.h"

struct ShipNozzle { float4 mouthWidth, axisHeight, widthAxis, aperture; };

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
    float4x4 shipPose[SHIP_POSE_COUNT]; // cockpit controls, elevons, sliding wings and hinged airbrakes
    float4   shipShockBounds; // half-extents of the external gas proxy, metric support-plane offset in w
    float4   shipAirframe;   // wing extension, brake extension, reverse thrust, station keeping
    float4   shipSupportExhaust; // support-jet direction in ship axes, power in w
    float4   shipRetroOutlet, shipSupportOutlet; // mouth positions and support outlet spacing
    float4 shipRadio; // receive lamp and audio meter
    ShipNozzle shipNozzles[2];
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
// mode: 0 opaque, 1 blended (the head-up display's combiner), 2 the canopy, 3 alpha-tested.
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
Texture2D<float4> shipImages[SHIP_MAX_IMAGES] : register(t64);
Texture2D<float> shipShadowMaps[2] : register(t44);
// [0] wet, rain, frost, max film (um). [1] cloud, temperature (C), extinction (1/km), clock.
// [2] collected water, relief sun, cloud sun, reset. [3,4] Dispatch XYZ as uint bits,
// then a float in w: water optics active, film retention per frame respectively.
StructuredBuffer<float4> shipWeather : register(t46);
// The water on the canopy (ShipWater.hlsli): its map over both panes, each texel the highest drop there, its height (um)
// in the high 16 bits and its number in the low ones; and the film the drops leave behind (um).
Texture2D<uint> shipWaterMap : register(t48);
Texture2D<float> shipWaterFilm : register(t49);
Texture2D<float> shipSceneDepth : register(t53); // current reversed Z, including the late chrome
StructuredBuffer<float4> shipPaneFit : register(t54);
StructuredBuffer<float4> shipLipTravel : register(t55);
SamplerComparisonState shipShadowSampler : register(s4);
SamplerState shipSampler : register(s5); // wrapping, anisotropic

float ShipOpaqueDistance(float4 pixel, float rayDistance)
{
    const float z = shipSceneDepth.Load(int3(pixel.xy, 0));
    return z > 0.0 ? rayDistance * pixel.z / z : 1.e20;
}

// The selected profile drives geometry and weather together. See ShipProfiles.h for the CPU dimensions.
bool ShipClassic() { return shipOptions.z < 0.5; }
bool ShipNavigator() { return shipOptions.z > 1.5 && shipOptions.z < 2.5; }
bool ShipShuttle() { return shipOptions.z > 2.5; }
#include "ShipClassique.hlsli"
#include "ShipChasseur.hlsli"
#define SHIP_CENTRE (ShipNavigator() || ShipShuttle() ? float3(0, 0, 0) : ShipClassic() ? CLASSIC_CENTRE : FIGHTER_SHIP_CENTRE)
static const float SHIP_RADIUS = 6.7;
#define WATER_TEXEL (shipWaterLayout.w)
#define WATER_ORIGIN (float2(-0.5 * shipWaterLayout.x * WATER_TEXEL, shipWaterLayout.z))
#define WATER_SIZE (uint2(shipWaterLayout.xy))

static const float3 SHUTTLE_PANE_CENTRE = float3(0, SHUTTLE_PANE_CENTRE_Y, SHUTTLE_PANE_CENTRE_Z);
bool HasShuttlePane() { return shipWaterLayout.x > 1.0; }

// xyz stores the surface normal scaled by its radial distance. w is signed distance to a pane edge.
float4 ShuttlePaneAt(float2 q)
{
    const float2 dimensions = float2(SHUTTLE_PANE_COLUMNS - 1, SHUTTLE_PANE_ROWS - 1);
    const float2 extent = float2(WATER_SIZE) * WATER_TEXEL;
    const float2 uv = (q - WATER_ORIGIN) / extent;
    const float2 p = saturate(uv) * dimensions;
    const uint2 cell = min(uint2(p), uint2(dimensions) - 1);
    const float2 f = p - cell;
    const uint i = cell.x + cell.y * SHUTTLE_PANE_COLUMNS;
    float4 sample = lerp(lerp(shipPaneFit[i], shipPaneFit[i + 1], f.x),
                         lerp(shipPaneFit[i + SHUTTLE_PANE_COLUMNS], shipPaneFit[i + SHUTTLE_PANE_COLUMNS + 1], f.x), f.y);
    sample.w -= length((uv - saturate(uv)) * extent);
    return sample;
}

// The Navigator's virtual field follows the actual hull behind the cabin opening.
// Its optical chart is a 1.5 m radius spherical projection. The aperture angles
// follow assets/vaisseau/navigateur/cabine_maillage.py (13 of 28 sectors, above -0.2 rad).
static const float FIELD_RADIUS = 1.5, FIELD_HALF_ANGLE = SHIP_FIELD_HALF_ANGLE;
float2 CanopyChart(float3 local)
{
    if (ShipShuttle()) {
        const float3 delta = local - SHUTTLE_PANE_CENTRE;
        return SHUTTLE_PANE_RADIUS * float2(atan2(delta.x, -delta.y), atan2(delta.z, length(delta.xy)));
    }
    if (!ShipNavigator()) return local.xy;
    return FIELD_RADIUS * float2(atan2(local.x, -local.y), atan2(local.z, length(local.xy)));
}
float FieldSillDistance(float2 q)
{
    return min(FIELD_RADIUS * FIELD_HALF_ANGLE - abs(q.x), q.y - SHIP_FIELD_FLOOR * FIELD_RADIUS);
}
bool OnCanopy(float2 p, float margin)
{
    if (ShipShuttle()) {
        [branch] if (!HasShuttlePane()) return false;
        return ShuttlePaneAt(p).w > margin;
    }
    if (ShipNavigator()) return FieldSillDistance(p) > margin && p.y < FIELD_RADIUS * 1.57079633;
    if (ShipClassic()) return ClassicOnCanopy(p, margin);
    return FighterOnCanopy(p, margin);
}
void CanopyFrame(float2 p, out float3 normal, out float3 chartX, out float3 chartY)
{
    if (ShipShuttle()) {
        const float3 surface = ShuttlePaneAt(p).xyz;
        const float r = max(length(surface), .15);
        normal = surface / r;
        float sa, ca, se, ce;
        sincos(p.x / SHUTTLE_PANE_RADIUS, sa, ca);
        sincos(p.y / SHUTTLE_PANE_RADIUS, se, ce);
        const float scale = SHUTTLE_PANE_RADIUS / r;
        chartX = float3(ca, sa, 0) * (scale / max(ce, .2));
        chartY = float3(-sa * se, ca * se, ce) * scale;
    } else if (ShipNavigator()) {
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
    if (ShipShuttle()) {
        [branch] if (!HasShuttlePane()) return 1000.0;
        return max(ShuttlePaneAt(q).w, 0.0);
    }
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

// Transverse skinning uses x' = x + extension * travel(position).
// Transform normals by the inverse transpose and tangents by the same map's Jacobian.
ShipVertex ShipSkinnedVertex(uint id)
{
    ShipVertex v = shipVertices[id];
    [branch] if (v.pose < 0.0) {
        const float4 travel = shipLipTravel[(uint)(-v.pose) - 1] * shipAirframe.x;
        v.pos.x += travel.x;
        v.normal -= travel.yzw * (v.normal.x / (1.0 + travel.y));
        v.normal = normalize(v.normal);
        v.tangent.x += dot(v.tangent.xyz, travel.yzw);
        v.tangent.xyz = normalize(v.tangent.xyz);
        v.pose = 0.0;
    }
    return v;
}

// The packet's numbered poses cover the cockpit controls and the fighter's elevons.
// The shuttle retains its yoke, closed gear and throttle slots. The extra four poses drive the flight surfaces.
// Fractional weights bend the stick boot from its flange.
float4x4 ShipPose(float pose)
{
    const float4x4 still = float4x4(1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1);
    [branch] if (pose <= 0.0)
        return still;
    const uint part = min((uint)ceil(pose), (uint)SHIP_POSE_COUNT) - 1;
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
