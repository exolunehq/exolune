// The ship's glass, over the finished image: drawn into the overlay that the tone map applies after the temporal
// smoothing (ToneMap.hlsl), screen = smoothed * alpha + rgb. Things stuck on the glass move with the ship, the world behind
// does not: kept apart, the smoothing's history never smears the drops.
// The canopy: Fresnel's reflection of the sky or of the cockpit, the sun's glint, then the weather (ShipWeather.hlsl):
// the water, simulated drops and the trails they leave, which refract the world (ShipWater.hlsli), frost grown from the sills. The combiner: a
// collimated head-up display, its symbols at infinity.
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "Ship.hlsli"

Texture2D<float4> sceneComposite : register(t47); // the world under its atmosphere, before the smoothing

float Hash(float2 p)
{
    p = frac(p * float2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return frac(p.x * p.y);
}
float2 Hash2(float2 p) { const float n = Hash(p); return float2(n, Hash(p + n + 17.17)); }
float Noise(float2 p)
{
    const float2 i = floor(p), f = frac(p), u = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), u.x), lerp(Hash(i + float2(0, 1)), Hash(i + 1.0), u.x), u.y);
}
float Fbm(float2 p)
{
    float sum = 0.0, weight = 0.5;
    [unroll] for (int k = 0; k < 4; ++k) { sum += weight * Noise(p); p = p * 2.03 + 11.7; weight *= 0.5; }
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

// Distance (m) from a point of the canopy to its sill, the teardrop's outline, in the ship's plan.
float SillDistance(float3 local) { return max(CanopyInside(local.xy), 0.0); }

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
    const float3 v = normalize(-input.pos), sun = lightDir.xyz, up = camVertical.xyz;
    const float3 centre = mul(float4(SHIP_CENTRE, 1.0), shipModel).xyz;
    float3 outward = normalize(input.normal);
    if (dot(outward, input.pos - centre) < 0.0)
        outward = -outward;
    const bool inside = dot(v, outward) < 0.0;
    const float3 n = inside ? -outward : outward; // towards the eye
    const float nv = saturate(dot(n, v)), fresnel = 0.04 + 0.96 * pow(1.0 - nv, 5.0);
    const float h = max(shipUp.w, 0.0), muS = dot(up, sun), haze = RegionalGround(PlanetDirection(up));
    const float3 beam = SUN_ILLUMINANCE * SunTransmittance(h, muS, haze) * shipWeather[2].y, sky = SkyIrradiance(h, muS, haze);

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

    float2 size;
    sceneComposite.GetDimensions(size.x, size.y);
    const float2 uv = input.position.xy / size;
    if (m.mode == 1)
    {
        // The combiner: a faint green, and its symbols' light.
        rgb += float3(0.25, 1.0, 0.45) * 1.4 * HudSymbols(-v, taa.w) * shipOptions.x;
        return float4(rgb, alpha * 0.96);
    }

    // The water on the canopy (ShipWater.hlsli): the drops, and the trails they leave, which dry. Each is a lens: xy
    // its surface's slope, outwards from the drop's middle (1 at a cap's rim); z its cover.
    const float4 w = shipWeather[0];
    const float2 q = input.local.xy;
    const float e = WATER_TEXEL;
    const float height = WaterHeight(q);
    float3 drop = float3(-float2(WaterHeight(q + float2(e, 0.0)) - WaterHeight(q - float2(e, 0.0)),
                                 WaterHeight(q + float2(0.0, e)) - WaterHeight(q - float2(0.0, e))) / (2.0 * e),
                         saturate(height / 40e-6));
    drop.xy = clamp(drop.xy, -1.0, 1.0);
    // A trail: a thin smear with soft, wavering edges, a little wavy on top; as it dries it thins and breaks into
    // patches, then is gone.
    const float2 mapUv = (q - WATER_ORIGIN) / (WATER_TEXEL * float2(WATER_SIZE)), texel = 1.0 / float2(WATER_SIZE);
    const float film = shipWaterFilm.SampleLevel(linearClamp, mapUv, 0.0);
    const float patchy = Fbm(q * 220.0);
    const float wetness = smoothstep(4.0, 22.0, film + (patchy - 0.5) * 30.0);
    if (wetness > drop.z)
    {
        const float2 slope = float2(shipWaterFilm.SampleLevel(linearClamp, mapUv + float2(texel.x, 0.0), 0.0)
                                        - shipWaterFilm.SampleLevel(linearClamp, mapUv - float2(texel.x, 0.0), 0.0),
                                    shipWaterFilm.SampleLevel(linearClamp, mapUv + float2(0.0, texel.y), 0.0)
                                        - shipWaterFilm.SampleLevel(linearClamp, mapUv - float2(0.0, texel.y), 0.0));
        drop = float3(clamp(-slope * 0.004 + (float2(Fbm(q * 600.0), Fbm(q * 600.0 + 3.7)) - 0.5) * 0.2, -0.5, 0.5),
                      0.45 * wetness);
    }
    // A drop is a wide-angle lens: the world through it, turned over and drawn in from well around it. Its steep edge
    // turns the light away, a dark ring; where its surface faces the sky, it mirrors it, a bright spot, softened by a
    // cloud's light, which comes from everywhere.
    const float3 through = sceneComposite.SampleLevel(linearClamp, uv - drop.xy * 0.25, 0.0).rgb;
    const float edge = saturate(dot(drop.xy, drop.xy)), rim = 1.0 - 0.75 * smoothstep(0.2, 1.0, edge);
    const float spot = pow(saturate(1.0 - length(drop.xy - float2(0.12, 0.42)) / 0.4), 2.0);
    // Frost grows from the sills inwards, its crystals in fronds.
    const float fronds = Fbm(q * 90.0) * 0.6 + Fbm(q * 400.0) * 0.4;
    const float frost = saturate((0.32 * w.z - SillDistance(input.local)) * 18.0 + (fronds - 0.5) * 3.0) * step(0.01, w.z);
    const float3 scatter = (sky + beam * saturate(dot(outward, sun))) / PI;
    rgb += drop.z * (through * rim * alpha + scatter * 0.6 * spot * (1.0 - 0.5 * saturate(shipWeather[1].x * 4.0))) + frost * scatter * 0.55;
    // The canopy is the head-up display's combiner too: its symbols in a cone around the nose, at infinity. The pane's
    // own combiner sits below the eye, there is no room under the roof.
    const float3 nose = mul(float4(0.0, -1.0, 0.0, 0.0), shipModel).xyz;
    if (inside && dot(-v, nose) > cos(radians(24.0)))
        rgb += float3(0.25, 1.0, 0.45) * 1.2 * HudSymbols(-v, taa.w) * shipOptions.x * (1.0 - frost);
    alpha *= (1.0 - drop.z) * (1.0 - 0.85 * frost);
    return float4(rgb, alpha);
}
