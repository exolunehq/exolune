// The jets: the selected ship's main engines' plumes and the attitude jets' puffs, over the finished image, into the glass's
// overlay (Ship.cpp): screen = smoothed * alpha + rgb, kept out of the temporal smoothing. Each jet is a cone along its
// exhaust, marched through its box (ShipPlumeVertex.hlsl, ShipPlumePixel.hlsl). The march stops at the scene's own
// distance, the composite's alpha: the hull and the ground hide what lies behind them.
// Ship frame, Blender's: nose -y, up +z, the pilot's left +x (Ship.hlsli).
#ifndef SHIP_PLUME_HLSLI
#define SHIP_PLUME_HLSLI
#include "Planet.hlsli"
#include "Ship.hlsli"

#define MAIN_JETS (ShipNavigator() ? 0u : ShipShuttle() ? 2u : ShipClassic() ? 3u : 4u)
#define LEGACY_JETS (ShipNavigator() || ShipShuttle() ? MAIN_JETS : MAIN_JETS + 10u)
static const float3 JET_TO[10] = {
    float3(0, 0, 1), float3(0, 0, -1), float3(1, 0, 0),
    float3(0, 0, 1), float3(0, 0, -1), float3(-1, 0, 0),
    float3(0, 0, 1), float3(0, 0, -1), float3(1, 0, 0), float3(-1, 0, 0) };

struct Jet
{
    float3 at, to;  // its mouth and its exhaust's direction, ship frame
    float2 radii;   // half-width and half-height at the mouth (m)
    float spread;   // the cone's widening, per metre
    float length;   // (m)
    float power;    // 0 to 1
    float chart;    // linear aperture image index + 1, zero for analytic jets
    float rake;     // axial extent of the physical outlet (m)
    float bend;     // downward discharge angle after the outlet (radians)
};

Jet TransportPort(uint index)
{
    Jet jet = (Jet)0;
    const ShipExhaustPort port = shipPorts[index / 2u];
    const float3 mirror = float3((index & 1u) ? -1 : 1, 1, 1);
    jet.at = port.mouthRadius.xyz * mirror;
    jet.to = port.axis.xyz * mirror;
    jet.radii = port.mouthRadius.w;
    if (index < 2u) {
        jet.power = shipAirframe.z;
        jet.length = .55 + 2.75 * jet.power;
        jet.spread = .065;
    } else {
        // Only the outlets whose reaction serves the translation or torque fire.
        // The main grilles already carry the positive lift component.
        const float3 push = -jet.to;
        const float3 lever = normalize(cross(jet.at - SHIP_CENTRE, push));
        const float3 slide = float3(-shipThrust.w, 0, min(0.0, shipThrust.z));
        const float3 torque = -float3(shipTurn.x, shipThrust.y, shipTurn.y);
        const float demand = saturate(dot(push, slide) + dot(lever, torque));
        const float phase = frac(shipTurn.z * 4.0 + index * .38197);
        const float pulse = smoothstep(0, .13, phase) * (1 - smoothstep(.38, .83, phase));
        jet.power = smoothstep(.018, .68, demand) * (.18 + .82 * pulse);
        jet.length = .35 + 1.35 * sqrt(jet.power);
        jet.spread = .13;
    }
    return jet;
}

Jet JetOf(uint j)
{
    Jet jet = (Jet)0;
    if (shipAutomation.y > .5 && j >= 2u) return TransportPort(j - 2u);
    if (j >= LEGACY_JETS)
    {
        const uint port = j - LEGACY_JETS;
        const float side = (port & 1u) ? -1.0 : 1.0;
        const bool retro = port < 2u;
        jet.at = retro ? shipRetroOutlet.xyz : shipSupportOutlet.xyz;
        jet.at.x *= side;
        if (!retro)
            jet.at.y += (port < 4u ? -1.0 : 1.0) * shipSupportOutlet.w;
        jet.to = retro ? normalize(float3(.28 * side, -1, -.07)) : normalize(shipSupportExhaust.xyz + float3(.12 * side, 0, 0));
        jet.power = (retro ? shipAirframe.z : shipSupportExhaust.w) * (1.0 - shipOptions.y);
        jet.radii = retro ? .081 : .063;
        jet.spread = retro ? .12 : .16;
        jet.length = retro ? .9 + 1.6 * jet.power : .72 + 1.0 * jet.power;
        return jet;
    }
    if (ShipShuttle()) {
        const ShipNozzle nozzle = shipNozzles[j];
        jet.to = nozzle.axisHeight.xyz;
        jet.chart = nozzle.aperture.x;
        if (jet.chart > 0) {
            jet.rake = nozzle.aperture.y;
            jet.at = nozzle.mouthWidth.xyz;
            jet.radii = float2(nozzle.mouthWidth.w, nozzle.axisHeight.w);
            jet.power = smoothstep(.035, 1.0, shipThrust.x);
            jet.bend = shipAutomation.z;
            jet.length = jet.radii.x * lerp(1.25, shipAutomation.y > .5 ? 6.4 : 4.9, jet.power);
            jet.spread = .12;
            return jet;
        }
        jet.at = nozzle.mouthWidth.xyz - .034 * jet.to;
        jet.radii = .93 * float2(nozzle.mouthWidth.w, nozzle.axisHeight.w);
        jet.power = smoothstep(.07, 1.0, shipThrust.x);
        jet.length = jet.radii.x * lerp(1.5, 7.2, jet.power);
        jet.spread = .035;
        return jet;
    }
    if (j < MAIN_JETS)
    {
        jet.at = ShipClassic() ? float3(1.25 * (float(j) - 1.0), 2.774, 0.022) : FIGHTER_NOZZLE[j].xyz;
        jet.to = ShipClassic() ? CLASSIC_NOZZLE_AXIS : float3(0.0, 1.0, 0.0);
        jet.radii = ShipClassic() ? 0.3 : FIGHTER_NOZZLE[j].w;
        jet.spread = 0.06;
        jet.power = saturate(shipThrust.x);
        jet.length = (1.5 + 6.5 * jet.power) * (ShipClassic() ? 1.0 : jet.radii.x / 0.31);
        return jet;
    }
    jet.at = ShipClassic() ? CLASSIC_JET_AT[j - MAIN_JETS] : FIGHTER_JET_AT[j - MAIN_JETS];
    jet.to = JET_TO[j - MAIN_JETS];
    jet.radii = 0.04;
    jet.spread = 0.3;
    jet.length = 1.2;
    // A jet pushes against its exhaust: it fires when that push serves the command, the slide (right: towards -x; up:
    // +z) or the turn, a torque about the ship's centre (roll right: -y; pitch up: -x; yaw right: -z).
    const float3 push = -jet.to, lever = cross(jet.at - SHIP_CENTRE, push);
    const float support = 1.0 - smoothstep(.07, .21, shipSupportExhaust.w);
    const float3 slide = support * float3(-shipThrust.w, 0.0, shipThrust.z), torque = -float3(shipTurn.x, shipThrust.y, shipTurn.y);
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
void JetFrame(uint index, Jet jet, out float3 u, out float3 v)
{
    if (ShipShuttle() && index < MAIN_JETS)
        u = shipNozzles[index].widthAxis.xyz;
    else
        u = normalize(cross(jet.to, abs(jet.to.z) < 0.9 ? float3(0, 0, 1) : float3(1, 0, 0)));
    v = cross(jet.to, u);
    if (jet.chart > 0 && v.z < 0) v = -v; // both aperture images have increasing ship height in +v
}

// The inner sheet must clear the turn centre even where the mouth flares.
float BendRadius(Jet jet) { return jet.radii.y * 1.45 + .09; }

void JetBounds(Jet jet, out float3 low, out float3 high)
{
    const float2 across = jet.radii + jet.spread * jet.length + .05;
    low = float3(-across, -.05);
    high = float3(across, jet.rake + jet.length);
    if (jet.bend > .001) {
        const float radius = BendRadius(jet);
        low.y -= radius * (1 - cos(jet.bend)) + jet.length * sin(jet.bend);
        high.z = jet.rake + (radius + across.y) * sin(jet.bend) + jet.length * cos(jet.bend) + .06;
    }
}

struct PlumePixel
{
    float4 position : SV_POSITION;
    float3 local    : TEXCOORD0; // ship frame (m)
    nointerpolation uint jet : TEXCOORD1;
};
#endif
