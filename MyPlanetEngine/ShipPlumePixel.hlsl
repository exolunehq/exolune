// The jets marched through their boxes (ShipPlume.hlsli). The main engines' plumes give light, a hot blue-white core
// fading along their length, with faint shock diamonds; the attitude jets' puffs are a white vapour that the sun and
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
    const uint steps = 24;
    const float ds = (end - start) / steps;
    float3 rgb = 0.0;
    float through = 1.0;
    [loop] for (uint k = 0; k < steps; ++k)
    {
        const float3 q = o + d * (start + (k + 0.5) * ds);
        if (q.z < 0.0)
            continue;
        const float along = saturate(q.z / jet.length);
        // The flame swells a little out of the nozzle, then narrows to a point at its tip; the vapour widens.
        const float width = engine ? jet.radius * (1.0 + 0.5 * along) * pow(1.0 - along, 0.6) + 1e-3
                                   : jet.radius + jet.spread * q.z;
        const float across = dot(q.xy, q.xy) / (width * width);
        if (engine)
        {
            // Some 4 x the sunlit white's radiance at full push, along a core that cools from blue-white to violet and
            // dies out at the tip.
            const float core = exp(-3.0 * across), fade = pow(1.0 - along, 1.5);
            const float diamonds = 0.8 + 0.2 * cos(6.2832 * q.z / (0.35 + 0.3 * jet.power));
            const float3 tint = lerp(lerp(float3(0.5, 0.7, 1.0), float3(0.95, 0.97, 1.0), core * core),
                                     float3(0.45, 0.4, 1.0), q.z / jet.length);
            rgb += tint * jet.power * core * fade * diamonds * ds * 4.0 * dot(white, 1.0 / 3.0) / PI / jet.radius;
        }
        else
        {
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
