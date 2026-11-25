// The jets marched through their boxes (ShipPlume.hlsli). The main engines' plumes give light, a hot blue-white core
// fading along their length, with shock diamonds; they live: a turbulence that streams downstream, a ragged tip, a
// flicker, a faint glow around the core; the attitude jets' puffs are a white vapour that the sun and
// the sky light, and that hides what is behind it.
#include "ShipPlume.hlsli"
#include "ShipHeat.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"

Texture2D<float4> sceneComposite : register(t47); // alpha: the scene's distance (km), 0 for the sky

// Each projection stores lip depth, open slots and their continuous envelope.
float3 OutletSample(Jet jet, float2 uv, float lod)
{
    const uint image = uint(jet.chart) - 1;
    if (jet.tileStride > 0)
        uv.y = jet.tileStart + (.125 + .75*saturate(uv.y))*jet.tileStride;
    float3 sample = shipImages[image].SampleLevel(linearClamp, uv, lod).rgb;
    if (jet.tileMix > 0) {
        uv.y += jet.tileStride;
        sample = lerp(sample, shipImages[image].SampleLevel(linearClamp, uv, lod).rgb, jet.tileMix);
    }
    return sample;
}

float3 TurbineGas(Jet jet, float3 q, float3 rayStep, float clock, float seed, float3 hot)
{
    const float2 section = q.xy / jet.radii;
    const float source = OutletSample(jet, .5 + .5*section, 0).r * jet.rake;
    const float run = saturate((q.z-source)/jet.length);
    const float mixing = shipAutomation.y > .5 ? smoothstep(.16, .84, run) : smoothstep(.055, .70, run);
    const float3 p = float3(section.x*2.1, section.y*3.0, q.z*1.6-clock*9.5+seed);
    const float eddy = PlumeNoise(p), streak = PlumeNoise(p*2.7 + float3(7,2,clock*6));
    // Streamlines join gently downstream. At the physical mouth the mapping
    // is exactly the surveyed cross-section, including its curved jambs.
    const float flare = lerp(.18,.075,saturate(shipOptions.w)) * sin(3.14159*run);
    const float2 scale = 1.0 + flare - float2(.52,.69)*smoothstep(.10,1.0,run);
    const float2 uv = (section - mixing*float2(eddy-.5,streak-.5)*.15) / scale;
    // Filter a marching interval in the fitted 192 x 96 chart. At full deflection
    // several slots can cross one ray step even with an almost horizontal view.
    const float footprint = max(abs(rayStep.x)*96.0/jet.radii.x, abs(rayStep.y)*48.0/jet.radii.y);
    const float slotLod = shipAutomation.y > .5 ? clamp(log2(max(1.0, footprint)),0.0,3.0) : 0.0;
    const float3 aperture = OutletSample(jet, .5 + .5*uv, max(slotLod,3.4*mixing));
    const float distance = q.z - (jet.tileStride > 0 ? source : aperture.r*jet.rake);
    const float age = saturate(distance / (jet.length*lerp(.49,1.0,aperture.b)));
    const float gas = lerp(aperture.g, .64*aperture.b, mixing);
    const float edge = 1.0 - smoothstep(.94,1.0,max(abs(uv.x),abs(uv.y)));
    const float entry = smoothstep(-.012,.028,distance);
    const float fade = pow(1.0-age,1.55) * (1.0-smoothstep(.62,1.0,age + (eddy-.5)*.22));
    const float density = gas*entry*edge*fade * lerp(1.0,.35+1.05*streak,mixing);
    const float3 colour = hot * lerp(float3(1.0,1.28,1.44),float3(.89,.65,.48),age);
    return colour*density;
}

float4 PSMain(PlumePixel input) : SV_Target
{
    const Jet jet = JetOf(input.jet);
    float3 u, v;
    JetFrame(input.jet, jet, u, v);
    // The view ray in the ship frame, then in the jet's.
    const float3 t = shipModel[3].xyz, eye = mul((float3x3)shipModel, -t);
    const float3 dir = normalize(input.local - eye), rel = eye - jet.at;
    const float3 o = float3(dot(rel, u), dot(rel, v), dot(rel, jet.to)), d = float3(dot(dir, u), dot(dir, v), dot(dir, jet.to));
    float3 lo, hi;
    JetBounds(jet, lo, hi);
    const float3 inv = 1.0 / (d + (abs(d) < 1e-6) * 1e-6), a = (lo - o) * inv, b = (hi - o) * inv;
    const float3 nearest = min(a, b), farthest = max(a, b);
    const float enter = max(max(nearest.x, nearest.y), nearest.z), leave = min(min(farthest.x, farthest.y), farthest.z);
    // Each box is drawn once, by its far side, whichever way its faces turn; inside it the march starts at the eye.
    if (leave <= max(enter, 0.0) || length(input.local - eye) < 0.5 * (enter + leave))
        discard;
    const float scene = abs(sceneComposite.Load(int3(input.position.xy, 0)).a) * 1000.0;
    const float opaque = ShipOpaqueDistance(input.position, length(input.local - eye));
    const float start = max(enter, 0.0), end = min(leave, min(opaque, scene > 0.0 ? scene : 1e9));
    if (end <= start)
        discard;

    const float3 sun = lightDir.xyz, up = camVertical.xyz;
    const float h = max(shipUp.w, 0.0), muS = dot(up, sun), haze = RegionalGround(PlanetDirection(up));
    const float3 white = SUN_ILLUMINANCE * float3(1.0, 1.0, 1.0);
    const float3 vapourLight = 0.9 * (white * SunTransmittance(h, muS, haze) * shipWeather[2].y * 0.6
                                      + SkyIrradiance(h, muS, haze)) / PI;
    const bool transport = shipAutomation.y > .5;
    const bool retro = transport && input.jet >= 2u && input.jet < 4u;
    const bool engine = transport ? input.jet < 4u : (input.jet < MAIN_JETS || input.jet >= LEGACY_JETS);
    const bool shuttleMain = ShipShuttle() && input.jet < MAIN_JETS;
    const float radius = sqrt(jet.radii.x * jet.radii.y);
    const uint steps = transport && shuttleMain ? 48u : engine ? 32u : 24u;
    // The flame's life: a flicker some twenty times a second, each engine out of step; the turbulence streams down the
    // plume at about 20 m/s.
    const float clock = shipTurn.z, seed = float(input.jet) * 7.31;
    const float flicker = 0.85 + 0.3 * PlumeNoise(float3(clock * 23.0, seed, 0.5));
    const float ds = (end - start) / steps;
    // The same duct carries the same load as it vectors. Its projected height
    // can double in hover, but that does not lower the gas radiance.
    float ductHeight = jet.radii.y;
    if (jet.tileStride > 0) ductHeight = shipNozzles[input.jet].axisHeight.w;
    const float3 turbineLight = ExhaustRadiance(jet.power, .67) * ds * flicker
                              * dot(white, 1.0 / 3.0) / (PI * max(2.0*ductHeight, .01));
    float3 rgb = 0.0;
    float through = 1.0;
    [loop] for (uint k = 0; k < steps; ++k)
    {
        const float3 q = o + d * (start + (k + 0.5) * ds);
        if (q.z < 0.0)
            continue;
        const float along = saturate(q.z / jet.length);
        if (jet.chart > 0)
        {
            rgb += TurbineGas(jet, q, d*ds, clock, seed, turbineLight);
        }
        else if (engine)
        {
            // The turbulence, coarse and fine, carried downstream; it sways the flame's axis and frays it towards the tip.
            const float3 s = q / float3(jet.radii, radius);
            const float n1 = PlumeNoise(float3(s.xy * 1.6, s.z * 0.5 - clock * 65.0 + seed));
            const float n2 = PlumeNoise(float3(s.xy * 4.0, s.z * 1.4 - clock * 110.0 - seed));
            const float2 axis = 0.24 * jet.radii * along * float2(n1 - 0.5, n2 - 0.5);
            const float tip = saturate(along * (0.9 + 0.25 * n1));
            // The flame swells a little out of the nozzle, then narrows to a ragged point at its tip.
            const float2 width = jet.radii * (1.0 + 0.5 * along) * pow(1.0 - tip, 0.6) * (1.0 + 0.3 * (n1 - 0.5) * along) + 1e-3;
            const float2 section = (q.xy - axis) / width;
            const float across = dot(section, section);
            // Some 4 x the sunlit white's radiance at full push, along a core that cools from blue-white to violet and
            // dies out at the tip; streaks in it, standing shock diamonds that waver, a faint wide glow.
            float coreProfile = exp(-3.0 * across);
            if (shuttleMain) {
                // The source fills the slots between the physical vanes. These
                // sheets of hot gas merge downstream of the rolled lip.
                const float slots = .16 + .84 * smoothstep(-.45, .55, cos(6.2832 * (q.y + .016) / .151));
                const float2 mouth = 1.0 - smoothstep(.52, 1.04, abs(section));
                coreProfile = lerp(mouth.x * mouth.y * slots, coreProfile, smoothstep(.08, .68, along));
            }
            const float core = coreProfile * (0.7 + 0.6 * n2), fade = pow(1.0 - tip, 1.5);
            const float diamonds = 0.75 + 0.25 * cos(6.2832 * q.z / (0.35 + 0.3 * jet.power) + 0.6 * (n1 - 0.5));
            const float glow = 0.1 * exp(-0.6 * across) * (1.0 - along);
            const float3 tint = (shuttleMain || retro) ? ExhaustRadiance(jet.power, 1.0)
                : lerp(lerp(float3(0.5, 0.7, 1.0), float3(0.95, 0.97, 1.0), saturate(core * core)), float3(0.45, 0.4, 1.0), along);
            const float3 halo = (shuttleMain || retro) ? .21 * tint : float3(0.35, 0.45, 1.0);
            const float gasGain = shuttleMain ? lerp(.14, .85, smoothstep(.57, .97, jet.power)) : 1.0;
            rgb += (tint * core * diamonds + halo * glow) * gasGain * jet.power * flicker * fade
                 * ds * 4.0 * dot(white, 1.0 / 3.0) / PI / radius;
        }
        else
        {
            // The vapour widens.
            const float width = radius + jet.spread * q.z;
            const float across = dot(q.xy, q.xy) / (width * width);
            // The vapour thins as it widens; dense at the mouth, it hides what is behind.
            const float density = 30.0 * jet.power * exp(-3.0 * across) * exp(-2.5 * q.z / jet.length)
                                * (radius * radius) / (width * width);
            const float kept = exp(-density * ds);
            float3 light = vapourLight;
            if (transport) {
                const float core = exp(-2.4*across - 2.1*along);
                light += float3(.26,.54,.87) * (1.0 + 1.4*core) * dot(white,1.0/3.0) / PI;
            }
            rgb += through * (1.0 - kept) * light;
            through *= kept;
        }
    }
    return float4(rgb, through);
}
