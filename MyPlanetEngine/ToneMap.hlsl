// Final pass: temporal smoothing, then the scene's light to the screen: the exposure, the film curve. The render target
// view is sRGB: the hardware encodes the output. See docs/recherche-tons-exposition.md and docs/log/spec-rendu.md.
#include "Planet.hlsli"
#include "Atmosphere.hlsli" // the atmosphere tables, t1 to t3, and the sampler
#include "Coordinates.hlsli"
#include "CanopyLighting.hlsli"
#include "ObserverExposure.hlsli"

Texture2D<float4> composite : register(t0); // the scene under its atmosphere; alpha: distance (km), 0 for the sky,
                                            // negative on the waves the sea shows, which move by themselves
Texture2D<float4> history : register(t4);   // the previous frame's result, before the exposure
Texture2D<float4> glass : register(t5);     // the ship's glass (ShipGlass.hlsl): screen = smoothed * alpha + rgb

static const float3 LUMINANCE = float3(0.2126, 0.7152, 0.0722); // Rec. 709

// The exposure, as an incident light meter turned towards the sun, at sea level under the camera: the sun's beam through
// the air, plus the sky, counted as a flat ground receives it. A grey card facing the sun then shows its own reflectance,
// whatever the sun's height: sunlit faces keep their light at dusk, flat ground and shade darken, as in a photograph
// exposed for its highlights. It never reads the image: turning the camera, or what the frame holds, cannot move it; no
// pumping, no flicker. Past sunset the meter keeps the sunset's light: the twilight darkens.
// ponytail: the card's own sky, the low sky and aureole in front of it, would take 0.1 to 0.5 stop more at low sun (tried).
float Exposure()
{
    const float muS = max(dot(camVertical.xyz, lightDir.xyz), 0.0);
    const float3 sunMeter=SUN_ILLUMINANCE*SunTransmittance(0.0,muS,0.0),skyMeter=SkyIrradiance(0.0,muS,0.0);
    const float3 daylight = sunMeter+skyMeter;
    // camVertical.w: the camera's altitude above the sea, km (D3DApp::Draw).
    const float airBelow = 1.0 - exp(-max(camVertical.w, 0.0) / RAYLEIGH_SCALE_HEIGHT);
    const float compensation = lerp(EXPOSURE_COMPENSATION, EXPOSURE_COMPENSATION_ORBIT, airBelow);
    float observer=1.0;
    if(camPlane.w>0.0) {
        const CanopyTransport transport=CanopyLight(camPlane.w,0.0,muS);
        const float3 sheltered=sunMeter*transport.direct+skyMeter*transport.sky
            +sunMeter*transport.sunScatter*float3(0.45,0.65,0.32);
        observer=ObserverExposure(dot(daylight,LUMINANCE),dot(sheltered,LUMINANCE),dot(camVertical.xyz,lightDir.xyz));
    }
    return observer*exp2(compensation) * PI / dot(daylight, LUMINANCE);
}

// The film curve: the photoreceptors' response, x^a / (x^a + k^a) (Naka-Rushton; Lottes 2016 and ACES 2 build on it),
// through the grey card, 0.18 to 0.18. Its toe deepens the shadows, its shoulder rolls the highlights off towards white.
// Applied to the brightest channel, the colour's ratios kept: hues never turn. What it takes off the brightest channel
// bleaches the colour towards white, as overexposed film does (Khronos PBR Neutral's desaturation, 0.15).
float3 FilmCurve(float3 color)
{
    const float peak = max(color.r, max(color.g, color.b));
    if (peak <= 0.0)
        return 0.0;
    const float z = pow(peak, FILM_CONTRAST), newPeak = z / (z + pow(0.18, FILM_CONTRAST) * (1.0 / 0.18 - 1.0));
    color *= newPeak / peak;
    const float g = 1.0 - 1.0 / (0.15 * max(peak - newPeak, 0.0) + 1.0);
    return lerp(color, newPeak.xxx, g);
}

struct Output
{
    float4 screen  : SV_Target0;
    float4 history : SV_Target1;
};

// Temporal smoothing: each pixel blends its colour with the one it had in the previous frame. The terrain
// is fixed on the planet, so the reprojection is exact: the pixel's point, from its direction and its
// distance, goes into the previous frame's camera. The sky, at infinity, only follows the rotation. The
// past colour is clamped to the current colours around the pixel, against trails. The waves the sea shows move by
// themselves, their past is somewhere else: none of it is kept. Each frame shows their mean over the pixel already
// (Sea.hlsli); kept, the past smeared their motion, 30 % of their contrast at 20 m (tools/banc_tremblement_mer.py).
Output PSMain(float4 position : SV_POSITION)
{
    float2 size;
    composite.GetDimensions(size.x, size.y);
    const int2 pixel = int2(position.xy);
    const float4 current = composite.Load(int3(pixel, 0));
    float3 low = current.rgb, high = current.rgb;
    [unroll] for (int dy = -1; dy <= 1; ++dy)
    [unroll] for (int dx = -1; dx <= 1; ++dx)
    {
        const float3 c = composite.Load(int3(clamp(pixel + int2(dx, dy), int2(0, 0), int2(size) - 1), 0)).rgb;
        low = min(low, c);
        high = max(high, c);
    }

    float3 color = current.rgb;
    if (taa.x < 1.0 && current.a >= 0.0)
    {
        const float2 ndc = float2(2.0 * position.x / size.x - 1.0, 1.0 - 2.0 * position.y / size.y);
        const float3 view = normalize(camForward.xyz + ndc.x * camRight.w * camRight.xyz + ndc.y * camUp.w * camUp.xyz);
        const float4 seen = current.a > 0.0 ? float4(view * current.a * 1000.0, 1.0) : float4(view, 0.0);
        // The ship's pixels move with it: inside its sphere, their own path to the previous frame (Ship.h).
        const bool onShip = shipSphere.w > 0.0 && current.a > 0.0 && length(seen.xyz - shipSphere.xyz) < shipSphere.w;
        const float4 previous = mul(seen, onShip ? reprojectShip : reproject);
        const float2 uv = previous.xy / previous.w * float2(0.5, -0.5) + 0.5;
        if (previous.w > 0.0 && all(uv >= 0.0) && all(uv <= 1.0))
            color = lerp(clamp(history.SampleLevel(linearClamp, uv, 0.0).rgb, low, high), current.rgb, taa.x);
    }

    Output output;
    output.history = float4(color, current.a);
    // The scene's light, linear: a glare or bloom term, in the same units, is added to `color` here. The diagnostic
    // views are measures, not light (tools/banc_qualite.py): their white stays 1, whatever the sun.
    // The glass after the smoothing, kept out of the history: what sticks to it moves with the ship, not the world.
    const float4 g = glass.Load(int3(pixel, 0));
    const float3 shown = color * g.a + g.rgb;
    output.screen = float4(taa.y > 0.5 ? shown : FilmCurve(shown * Exposure()), 1.0);
    output.screen.rgb = CoordinateOverlay(output.screen.rgb, pixel, int2(size));
    output.screen.rgb = ActionOverlay(output.screen.rgb, pixel, int2(size));
    return output;
}
