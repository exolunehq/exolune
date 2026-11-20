// The ship's glass, over the finished image: drawn into the overlay that the tone map applies after the temporal
// smoothing (ToneMap.hlsl), screen = smoothed * alpha + rgb. Things stuck on the glass move with the ship, the world behind
// does not: kept apart, the smoothing's history never smears the drops.
// The canopy: Fresnel's reflection of the sky or of the cockpit, the sun's glint, then the weather (ShipWeather.hlsl):
// the water, simulated drops and the trails they leave, which refract the world (ShipWater.hlsli), frost grown from the sills. The combiner: a
// collimated head-up display, its symbols at infinity.
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "SceneExposure.hlsli"
#include "Ship.hlsli"
#include "OpticalSurface.hlsli"
#include "ShipEntry.hlsli"
#include "CanopyWaterActivity.hlsli"

Texture2D<float4> sceneComposite : register(t47); // the world under its atmosphere, before the smoothing

float Fbm(float2 p)
{
    float sum = 0.0, weight = 0.5;
    [unroll] for (int k = 0; k < 4; ++k) { sum += weight * GlassNoise(p); p = p * 2.03 + 11.7; weight *= 0.5; }
    return sum / 0.9375;
}

// The simulated drops' water (ShipWater.hlsli), its height (m) at a point of the ship's plan, bilinear over the map.
float WaterHeight(float2 p)
{
    const float2 f = (p - WATER_ORIGIN) / WATER_TEXEL - 0.5, t = frac(f);
    const int2 i = int2(floor(f)), top = int2(WATER_SIZE) - 1;
    const float h00 = shipWaterMap.Load(int3(clamp(i, 0, top), 0)) >> 16;
    const float h10 = shipWaterMap.Load(int3(clamp(i + int2(1, 0), 0, top), 0)) >> 16;
    const float h01 = shipWaterMap.Load(int3(clamp(i + int2(0, 1), 0, top), 0)) >> 16;
    const float h11 = shipWaterMap.Load(int3(clamp(i + 1, 0, top), 0)) >> 16;
    return lerp(lerp(h00, h10, t.x), lerp(h01, h11, t.x), t.y) * 1e-6;
}

float3 WaterLens(float2 q)
{
    const float e = WATER_TEXEL;
    const float height = WaterHeight(q);
    float3 drop = 0.0;
    if (height > 0.0) {
        drop.xy = clamp(-float2(WaterHeight(q + float2(e, 0)) - WaterHeight(q - float2(e, 0)),
                                WaterHeight(q + float2(0, e)) - WaterHeight(q - float2(0, e))) / (2.0 * e), -1.0, 1.0);
        drop.z = saturate(height / 40.e-6);
    }
    const float2 uv = (q - WATER_ORIGIN) / (e * float2(WATER_SIZE)), pixel = 1.0 / float2(WATER_SIZE);
    const float film = shipWaterFilm.SampleLevel(linearClamp, uv, 0.0);
    if (film > CANOPY_VISIBLE_FILM_UM) {
        const float wetness = smoothstep(4.0, 22.0, film + (Fbm(q * 220.0) - 0.5) * 30.0);
        if (wetness > drop.z) {
            const float2 gradient = float2(shipWaterFilm.SampleLevel(linearClamp, uv + float2(pixel.x, 0), 0).r
                                            - shipWaterFilm.SampleLevel(linearClamp, uv - float2(pixel.x, 0), 0).r,
                                            shipWaterFilm.SampleLevel(linearClamp, uv + float2(0, pixel.y), 0).r
                                            - shipWaterFilm.SampleLevel(linearClamp, uv - float2(0, pixel.y), 0).r);
            drop = float3(clamp(-0.004 * gradient + (float2(Fbm(q * 600.0), Fbm(q * 600.0 + 3.7)) - 0.5) * 0.2, -0.5, 0.5), 0.45 * wetness);
        }
    }
    return drop;
}

// The head-up display's symbols, at infinity: the horizon, a pitch ladder every 10 degrees, the flight path marker.
float HudSymbols(float3 d, float pixel)
{
    const float3 up = camVertical.xyz, forward = mul(float4(0.0, -1.0, 0.0, 0.0), shipModel).xyz;
    const float3 fh = normalize(forward - up * dot(forward, up) + 1e-5), rh = cross(up, fh);
    const float elevation = asin(clamp(dot(d, up), -1.0, 1.0));
    const float3 dh = d - up * dot(d, up);
    const float azimuth = atan2(dot(dh, rh), dot(dh, fh)), stroke = 1.2 * pixel;
    const float rung = round(elevation / radians(10.0)), offset = abs(elevation - rung * radians(10.0));
    const float width = rung == 0.0 ? radians(14.0) : radians(4.5);
    const float ladder = (1.0 - smoothstep(stroke, 2.0 * stroke, offset)) * step(abs(azimuth), width) * step(radians(1.2), abs(azimuth));
    float marker = 0.0;
    if (shipVelocity.w > 1.0)
    {
        const float angle = acos(clamp(dot(d, shipVelocity.xyz), -1.0, 1.0));
        marker = 1.0 - smoothstep(stroke, 2.0 * stroke, abs(angle - radians(0.9)));
    }
    return max(ladder * step(abs(rung), 9.0), marker);
}

float4 PSMain(ShipPixel input) : SV_Target
{
    const ShipMaterial m = shipMaterials[shipMaterial];
    const float3 v = normalize(-input.pos), up = mul(float4(shipUp.xyz, 0.0), shipModel).xyz;
    const bool lunar = shipGauges.z > 0.5 && erosionMode.w != 0u;
    const uint body = max(erosionMode.w, 1u) - 1;
    const float3 sun = lunar ? celestialLight[body].xyz : lightDir.xyz;
    const float3 centre = mul(float4(SHIP_CENTRE, 1.0), shipModel).xyz;
    float3 outward = normalize(input.normal);
    if (dot(outward, input.pos - centre) < 0.0)
        outward = -outward;
    // The classic's two flat panes share a softened centre ridge. The fighter has a curved canopy.
    if (ShipClassic()) {
        const float3 side = shipModel[0].xyz;
        outward = normalize(outward - side * dot(outward, side) * (1.0 - smoothstep(0.0, 0.35, abs(input.local.x))));
    }
    const bool inside = dot(v, outward) < 0.0;
    if (ShipNavigator() && !inside) discard;
    const float3 n = inside ? -outward : outward; // towards the eye
    const float nv = saturate(dot(n, v)), fresnel = GlassFresnel(nv);
    const float h = max(shipUp.w, 0.0), muS = dot(up, sun), haze = RegionalGround(PlanetDirection(up));
    const float3 beam = SUN_ILLUMINANCE * shipWeather[2].y * shipWeather[2].z
                      * (lunar ? celestialLight[body].w.xxx : SunTransmittance(h, muS, haze));
    const float3 sky = lunar ? SUN_ILLUMINANCE * PlanetShine(-camVertical.xyz * (PLANET_RADIUS_KM + camVertical.w), up)
                             : SkyIrradiance(h, muS, haze);

    // What the glass mirrors: from inside, the dim cockpit; from outside, the sky, brighter towards the horizon, and the
    // ground below it; and the sun's glint, when it shines on this side of the pane.
    const float3 r = reflect(-v, n);
    const float3 ground = 0.12 * (beam * saturate(muS) + sky) / PI;
    const float3 mirrored = inside ? sky * 0.02 / PI
                                   : lerp(ground, sky / PI * (1.4 - 0.9 * saturate(dot(r, up))), smoothstep(-0.08, 0.08, dot(r, up)));
    const float3 hv = normalize(sun + v);
    const float a2 = 1.5e-5, nh = saturate(dot(n, hv)), lit = step(0.0, dot(n, sun)) * step(0.0, muS);
    const float glint = a2 / (PI * pow(nh * nh * (a2 - 1.0) + 1.0, 2.0)) / (4.0 * max(nv, 0.05)) * lit;
    // Seen from outside, the canopy is coated, as on fighters: a dark bronze mirror that lets 8 % through, so that the
    // cockpit is not seen. From inside, a lightly smoked glass.
    const float3 coat = float3(0.32, 0.27, 0.19);
    const float3 reflectance = inside || m.mode != 2 ? fresnel.xxx : coat + (1.0 - coat) * pow(1.0 - nv, 5.0);
    float3 rgb = reflectance * (mirrored + glint * beam);
    float alpha = inside || m.mode != 2 ? 0.92 * (1.0 - fresnel) : 0.08 * (1.0 - reflectance.g);
    if (ShipNavigator()) { rgb *= 0.35; alpha = 1.0 - 0.35 * fresnel; }

    float2 size;
    sceneComposite.GetDimensions(size.x, size.y);
    const float2 uv = input.position.xy / size;
    if (m.mode == 1)
    {
        // The combiner: a faint green, and its symbols' light.
        rgb += float3(0.25, 1.0, 0.45) * 1.4 * HudSymbols(-v, taa.w) * shipOptions.x * NightInstrumentGain();
        return float4(rgb, alpha * 0.96);
    }

    const float2 q = CanopyChart(input.local), dx = ddx(q), dy = ddy(q);
    const float footprint = max(length(dx), length(dy));
    const float3 nose = -shipModel[1].xyz;
    const float peripheral = inside ? 1.0 - smoothstep(cos(radians(46.0)), cos(radians(13.0)), dot(-v, nose)) : 1.0;
    const float3 scatter = (sky + beam * saturate(dot(outward, sun))) / PI;
    const float aim = inside ? smoothstep(cos(radians(28.0)), cos(radians(7.0)), dot(-v, nose)) : 0.0;
    const float2 wear = CanopyAbrasion(q, dx, dy, ddx(input.pos), ddy(input.pos), sun + v)
                      * (1.0 - 0.94 * aim);
    const float rimLight = 1.0 - abs(dot(outward, sun));
    // A groove redirects the transmitted scene. It can read silver against a
    // dark sea and darker against bright sky. Only aligned tangents catch the sun.
    alpha *= 1.0 - wear.x * (0.54 + 0.20 * (1.0 - nv));
    rgb += (wear.x * (0.12 + 0.18 * (1.0 - nv)) * sky
         + wear.y * (0.18 + 0.60 * rimLight) * beam) / PI;
    float3 drop = 0.0;
    if (shipWeather[3].w > 0.5) drop = WaterLens(q);
    drop.z *= (1.0 - ShipVacuum()) * saturate(2.5 * WATER_TEXEL / max(footprint, 1.e-6)) * lerp(0.70, 1.0, peripheral);
    if (drop.z > 0.0) {
        // Rotate the optical slope with the pane and the pilot's head. A sampled opaque
        // instrument in front of the pane cannot be refracted through its wet outer face.
        const float2 slope = float2(dot(drop.xy, dx) / max(length(dx), 1.e-6), dot(drop.xy, dy) / max(length(dy), 1.e-6));
        const float4 through = sceneComposite.SampleLevel(linearClamp, uv - 0.12 * slope * float2(size.y / size.x, 1.0), 0.0);
        const float rim = 1.0 - 0.60 * smoothstep(0.2, 1.0, dot(drop.xy, drop.xy));
        const float2 skyDir = float2(dot(up, camRight.xyz), -dot(up, camUp.xyz));
        const float spot = pow(saturate(1.0 - length(slope - 0.42 * skyDir) / 0.4), 2.0);
        const float paneKm = length(input.pos) * 0.001;
        if (through.a == 0.0 || abs(through.a) >= paneKm * 0.996) {
            rgb += drop.z * through.rgb * rim * alpha;
            alpha *= 1.0 - drop.z;
        }
        rgb += drop.z * scatter * 0.48 * spot * (1.0 - 0.5 * saturate(shipWeather[1].x * 4.0));
    }
    float frost = 0.0;
    if (shipWeather[0].z > 0.01) {
        const float fronds = Fbm(q * 90.0) * 0.6 + Fbm(q * 400.0) * 0.4;
        frost = saturate((0.32 * shipWeather[0].z - SillDistance(input.local, q)) * 18.0 + (fronds - 0.5) * 3.0)
              * lerp(0.18, 0.82, peripheral);
        rgb += frost * scatter * 0.55;
        alpha *= 1.0 - 0.85 * frost;
    }
    const float heat = EntryIntensity();
    if (heat > 0.002) {
        const EntrySection section = EntryAt(input.local);
        rgb += EntrySealReflection(section, heat) * min(1.0, 1.3 / max(Exposure(), 1.0));
    }
    // The canopy is the head-up display's combiner too: its symbols in a cone around the nose, at infinity. The pane's
    // own combiner sits below the eye, there is no room under the roof.
    if (!ShipNavigator() && inside && dot(-v, nose) > cos(radians(24.0)))
        rgb += float3(0.25, 1.0, 0.45) * 1.2 * HudSymbols(-v, taa.w) * shipOptions.x * NightInstrumentGain() * (1.0 - frost);
    return float4(rgb, alpha);
}
