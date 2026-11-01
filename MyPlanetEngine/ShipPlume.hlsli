// The jets: the four main engines' plumes and the attitude jets' puffs, over the finished image, into the glass's
// overlay (Ship.cpp): screen = smoothed * alpha + rgb, kept out of the temporal smoothing. Each jet is a cone along its
// exhaust, marched through its box (ShipPlumeVertex.hlsl, ShipPlumePixel.hlsl). The march stops at the scene's own
// distance, the composite's alpha: the hull and the ground hide what lies behind them.
// Ship frame, Blender's: nose -y, up +z, the pilot's left +x (Ship.hlsli).
#ifndef SHIP_PLUME_HLSLI
#define SHIP_PLUME_HLSLI
#include "Planet.hlsli"
#include "Ship.hlsli"

static const uint MAIN_JETS = 4, JET_COUNT = 14; // Ship.cpp draws JET_COUNT boxes
// The nozzles' lips, along +y (assets/vaisseau/forme_chasseur.py, GRANDE and PETITE): the two big engines in their
// cowls, the two small ones in the wing roots; w, the lip's inner radius (m).
static const float4 NOZZLE[4] = { float4(0.93, 4.78, 0.50, 0.31), float4(-0.93, 4.78, 0.50, 0.31),
                                  float4(1.85, 3.60, 0.36, 0.20), float4(-1.85, 3.60, 0.36, 0.20) };
// The attitude jets, flush in the skin (design_chasseur.py prints them, JETS): at the wing tips, up and down; on the
// engine cowls, outward; at the nose, up, down and to each side.
static const float3 JET_AT[10] = {
    float3(3.05, 1.632, 0.297), float3(3.05, 1.632, 0.22), float3(1.378, 4.28, 0.5),
    float3(-3.05, 1.632, 0.297), float3(-3.05, 1.632, 0.22), float3(-1.378, 4.28, 0.5),
    float3(0.0, -4.12, 0.542), float3(0.0, -4.12, 0.032), float3(0.45, -4.12, 0.31), float3(-0.45, -4.12, 0.31) };
static const float3 JET_TO[10] = {
    float3(0, 0, 1), float3(0, 0, -1), float3(1, 0, 0),
    float3(0, 0, 1), float3(0, 0, -1), float3(-1, 0, 0),
    float3(0, 0, 1), float3(0, 0, -1), float3(1, 0, 0), float3(-1, 0, 0) };

struct Jet
{
    float3 at, to;  // its mouth and its exhaust's direction, ship frame
    float radius;   // at the mouth (m)
    float spread;   // the cone's widening, per metre
    float length;   // (m)
    float power;    // 0 to 1
};

Jet JetOf(uint j)
{
    Jet jet;
    if (j < MAIN_JETS)
    {
        jet.at = NOZZLE[j].xyz;
        jet.to = float3(0.0, 1.0, 0.0);
        jet.radius = NOZZLE[j].w;
        jet.spread = 0.06;
        jet.power = saturate(shipThrust.x);
        jet.length = (1.5 + 6.5 * jet.power) * jet.radius / 0.31;
        return jet;
    }
    jet.at = JET_AT[j - MAIN_JETS];
    jet.to = JET_TO[j - MAIN_JETS];
    jet.radius = 0.04;
    jet.spread = 0.3;
    jet.length = 1.2;
    // A jet pushes against its exhaust: it fires when that push serves the command, the slide (right: towards -x; up:
    // +z) or the turn, a torque about the ship's centre (roll right: -y; pitch up: -x; yaw right: -z).
    const float3 push = -jet.to, lever = cross(jet.at - SHIP_CENTRE, push);
    const float3 slide = float3(-shipThrust.w, 0.0, shipThrust.z), torque = -float3(shipTurn.x, shipThrust.y, shipTurn.y);
    const float want = dot(push, slide) + dot(lever, torque) / max(length(lever), 1e-3);
    // In soft puffs, two or three a second, each jet out of step with the others. Only when the ship does not go ahead:
    // under way the main engines and the air steer it, and the jets rest; climbing or sliding, they work. Never seen from
    // the cockpit (shipOptions.y). The nose, face-local, is -shipModel[1].
    const float phase = frac(shipTurn.z * 2.5 + float(j) * 0.37);
    const float ahead = abs(dot(shipVelocity.xyz, shipModel[1].xyz)) * shipVelocity.w;
    const float hovering = 1.0 - smoothstep(2.0, 10.0, ahead);
    jet.power = saturate(2.0 * want - 0.2) * smoothstep(0.0, 0.1, phase) * smoothstep(0.5, 0.2, phase) * hovering
              * (1.0 - shipOptions.y);
    return jet;
}

// A smooth value noise in [0, 1], for the plumes' turbulence.
float PlumeHash(float3 p)
{
    p = frac(p * 0.3183099 + 0.1) * 17.0;
    return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
}
float PlumeNoise(float3 x)
{
    const float3 i = floor(x), f = frac(x), w = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(lerp(PlumeHash(i), PlumeHash(i + float3(1, 0, 0)), w.x), lerp(PlumeHash(i + float3(0, 1, 0)), PlumeHash(i + float3(1, 1, 0)), w.x), w.y),
                lerp(lerp(PlumeHash(i + float3(0, 0, 1)), PlumeHash(i + float3(1, 0, 1)), w.x), lerp(PlumeHash(i + float3(0, 1, 1)), PlumeHash(i + float3(1, 1, 1)), w.x), w.y), w.z);
}

// The jet's own frame: across (two axes) and along its exhaust.
void JetFrame(Jet jet, out float3 u, out float3 v)
{
    u = normalize(cross(jet.to, abs(jet.to.z) < 0.9 ? float3(0, 0, 1) : float3(1, 0, 0)));
    v = cross(jet.to, u);
}

struct PlumePixel
{
    float4 position : SV_POSITION;
    float3 local    : TEXCOORD0; // ship frame (m)
    nointerpolation uint jet : TEXCOORD1;
};
#endif
