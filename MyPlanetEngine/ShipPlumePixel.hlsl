// The jets marched through their boxes (ShipPlume.hlsli). The main engines' plumes give light, a hot blue-white core
// fading along their length, with shock diamonds; they live: a turbulence that streams downstream, a ragged tip, a
// flicker, a faint glow around the core; the attitude jets' puffs are a white vapour that the sun and
// the sky light, and that hides what is behind it.
#include "ShipPlume.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"

Texture2D<float4> sceneComposite : register(t47); // alpha: the scene's distance (km), 0 for the sky

float4 PSMain(PlumePixel input) : SV_Target
{
    const Jet jet = JetOf(input.jet);
    float3 u, v;
    JetFrame(jet, u, v);
    // The view ray in the ship frame, then in the jet's.
    const float3 t = shipModel[3].xyz, eye = mul((float3x3)shipModel, -t);
    const float3 dir = normalize(input.local - eye), rel = eye - jet.at;
    const float3 o = float3(dot(rel, u), dot(rel, v), dot(rel, jet.to)), d = float3(dot(dir, u), dot(dir, v), dot(dir, jet.to));
    const float half = jet.radius + jet.spread * jet.length + 0.05;
    const float3 lo = float3(-half, -half, -0.05), hi = float3(half, half, jet.length);
    const float3 inv = 1.0 / (d + (abs(d) < 1e-6) * 1e-6), a = (lo - o) * inv, b = (hi - o) * inv;
    const float3 nearest = min(a, b), farthest = max(a, b);
    const float enter = max(max(nearest.x, nearest.y), nearest.z), leave = min(min(farthest.x, farthest.y), farthest.z);
    // Each box is drawn once, by its far side, whichever way its faces turn; inside it the march starts at the eye.
    if (leave <= max(enter, 0.0) || length(input.local - eye) < 0.5 * (enter + leave))
        discard;
    const float scene = abs(sceneComposite.Load(int3(input.position.xy, 0)).a) * 1000.0;
    const float start = max(enter, 0.0), end = min(leave, scene > 0.0 ? scene : 1e9);
    if (end <= start)
        discard;

    const float3 sun = lightDir.xyz, up = camVertical.xyz;
    const float h = max(shipUp.w, 0.0), muS = dot(up, sun), haze = RegionalGround(PlanetDirection(up));
    const float3 white = SUN_ILLUMINANCE * float3(1.0, 1.0, 1.0);
    const float3 vapourLight = 0.9 * (white * SunTransmittance(h, muS, haze) * shipWeather[2].y * 0.6
                                      + SkyIrradiance(h, muS, haze)) / PI;
    const bool engine = input.jet < MAIN_JETS;
    const uint steps = engine ? 32 : 24;
    // The flame's life: a flicker some twenty times a second, each engine out of step; the turbulence streams down the
    // plume at about 20 m/s.
    const float clock = shipTurn.z, seed = float(input.jet) * 7.31;
    const float flicker = 0.85 + 0.3 * PlumeNoise(float3(clock * 23.0, seed, 0.5));
    const float ds = (end - start) / steps;
    float3 rgb = 0.0;
    float through = 1.0;
    [loop] for (uint k = 0; k < steps; ++k)
    {
        const float3 q = o + d * (start + (k + 0.5) * ds);
        if (q.z < 0.0)
            continue;
        const float along = saturate(q.z / jet.length);
        if (engine)
        {
            // The turbulence, coarse and fine, carried downstream; it sways the flame's axis and frays it towards the tip.
            const float3 s = q / jet.radius;
            const float n1 = PlumeNoise(float3(s.xy * 1.6, s.z * 0.5 - clock * 65.0 + seed));
            const float n2 = PlumeNoise(float3(s.xy * 4.0, s.z * 1.4 - clock * 110.0 - seed));
            const float2 axis = 0.24 * jet.radius * along * float2(n1 - 0.5, n2 - 0.5);
            const float tip = saturate(along * (0.9 + 0.25 * n1));
            // The flame swells a little out of the nozzle, then narrows to a ragged point at its tip.
            const float width = jet.radius * (1.0 + 0.5 * along) * pow(1.0 - tip, 0.6) * (1.0 + 0.3 * (n1 - 0.5) * along) + 1e-3;
            const float across = dot(q.xy - axis, q.xy - axis) / (width * width);
            // Some 4 x the sunlit white's radiance at full push, along a core that cools from blue-white to violet and
            // dies out at the tip; streaks in it, standing shock diamonds that waver, a faint wide glow.
            const float core = exp(-3.0 * across) * (0.7 + 0.6 * n2), fade = pow(1.0 - tip, 1.5);
            const float diamonds = 0.75 + 0.25 * cos(6.2832 * q.z / (0.35 + 0.3 * jet.power) + 0.6 * (n1 - 0.5));
            const float glow = 0.1 * exp(-0.6 * across) * (1.0 - along);
            const float3 tint = lerp(lerp(float3(0.5, 0.7, 1.0), float3(0.95, 0.97, 1.0), saturate(core * core)), float3(0.45, 0.4, 1.0), along);
            rgb += (tint * core * diamonds + float3(0.35, 0.45, 1.0) * glow) * jet.power * flicker * fade
                 * ds * 4.0 * dot(white, 1.0 / 3.0) / PI / jet.radius;
        }
        else
        {
            // The vapour widens.
            const float width = jet.radius + jet.spread * q.z;
            const float across = dot(q.xy, q.xy) / (width * width);
            // The vapour thins as it widens; dense at the mouth, it hides what is behind.
            const float density = 30.0 * jet.power * exp(-3.0 * across) * exp(-2.5 * q.z / jet.length)
                                * (jet.radius * jet.radius) / (width * width);
            const float kept = exp(-density * ds);
            rgb += through * (1.0 - kept) * vapourLight;
            through *= kept;
        }
    }
    return float4(rgb, through);
}
