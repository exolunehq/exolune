#include "ShipNavigatorFixtures.hlsli"

// Native instrument faces use the same ship-space patches as the asset generator. No UV atlas or playback clock.
// Right amber: commanded propulsion, 0--100%. Left blue: actual heading, 0--359 degrees.
void NavigatorInstrument(float3 pos, out float3 albedo, out float3 emission)
{
    const bool compass = pos.x > 0.0;
    const float side = compass ? 1.0 : -1.0;
    const float2 delta = pos.xy - NAVIGATOR_DIAL_CENTERS[compass ? 1 : 0].xy;
    // The top of each lateral dial points away from the pilot.
    const float2 p = float2(-side * delta.y, -side * delta.x) * (128.0 / NAVIGATOR_DIAL_RADIUS);
    screenPx = max(max(length(ddx(p)), length(ddy(p))), 0.001);
    const float r = length(p), angle = atan2(p.x, -p.y);
    const float heading = frac(shipCourse.x / 360.0 + 1.0) * 360.0;
    const float power = saturate(shipGauges.x);
    const float needle = compass ? radians(heading) : lerp(-0.75 * PI, 0.75 * PI, power);
    const float3 ink = compass ? float3(0.18, 0.40, 1.0) : float3(1.0, 0.32, 0.045);
    float3 marks = 0.0;
    const float arcRadius = 0.5 * (NAVIGATOR_DIAL_ARC.x + NAVIGATOR_DIAL_ARC.y) * 128.0 / NAVIGATOR_DIAL_RADIUS;
    const float arcWidth = (NAVIGATOR_DIAL_ARC.y - NAVIGATOR_DIAL_ARC.x) * 128.0 / NAVIGATOR_DIAL_RADIUS;
    const float slot = abs(frac(angle * 24.0 / (2.0 * PI) + 0.5) - 0.5) * (2.0 * PI * arcRadius / 24.0);
    const float arcMask = Stroke(r - arcRadius, arcWidth) * Fill(slot - 11.0);
    const float sweep = compass ? smoothstep(0.94, 0.99, cos(angle - needle))
                                : step(-0.75 * PI, angle) * step(angle, needle);
    Paint(marks, ink * (0.08 + 0.92 * sweep), arcMask);

    // Major and minor graduations remain readable under perspective minification.
    const float tickStep = compass ? PI / 6.0 : 1.5 * PI / 10.0;
    const float origin = compass ? 0.0 : -0.75 * PI;
    const float tick = round((angle - origin) / tickStep);
    const float t = origin + tick * tickStep;
    const float2 direction = float2(sin(t), -cos(t));
    const float valid = compass || (tick >= 0.0 && tick <= 10.0) ? 1.0 : 0.0;
    const float major = compass ? step(0.5, 1.0 - fmod(abs(tick), 3.0)) : step(0.5, 1.0 - fmod(tick, 5.0));
    Paint(marks, float3(0.36, 0.43, 0.48), valid * Stroke(Segment(p, direction * lerp(111.0, 101.0, major), direction * 123.0), lerp(1.4, 2.5, major)));
    if (compass)
    {
        static const uint letters[4] = { GLYPH_N, GLYPH_E, GLYPH_S, GLYPH_W };
        [unroll] for (uint i = 0; i < 4; ++i)
        {
            const float2 at = float2(sin(i * PI * 0.5), -cos(i * PI * 0.5)) * 87.0 - float2(4.0, 7.0);
            Paint(marks, float3(0.36, 0.43, 0.48), Stroke(Glyph(p - at, float2(8.0, 14.0), letters[i]), 1.5));
        }
    }
    const float2 nd = float2(sin(needle), -cos(needle)), crossNeedle = float2(-nd.y, nd.x);
    Paint(marks, ink, Fill(Triangle(p, nd * 106.0, nd * 15.0 + crossNeedle * 3.5, nd * 15.0 - crossNeedle * 3.5)));
    // Small inset numerical reading, with an explicit degree or percent sign.
    Paint(marks, 0.0, Fill(max(abs(p.x) - 35.0, abs(p.y - 64.0) - 13.0)));
    Paint(marks, ink * 0.8, Stroke(Number(p, float2(-27.0, 55.0), 18.0, compass ? fmod(round(heading), 360.0) : round(power * 100.0), 3, 0, true), 1.6));
    if (compass)
        Paint(marks, ink * 0.8, Stroke(length(p - float2(17.0, 55.0)) - 2.5, 1.2));
    else
    {
        Paint(marks, ink * 0.8, Stroke(Segment(p, float2(15, 73), float2(24, 55)), 1.3));
        Paint(marks, ink * 0.8, Stroke(min(abs(length(p - float2(15, 57)) - 2.0), abs(length(p - float2(24, 71)) - 2.0)), 1.2));
    }
    albedo = float3(0.004, 0.009, 0.013) + marks * 0.30;
    emission = marks * 0.32;
}

// Analytic lights anchored to the actual recessed lamp sockets in the continuous cabin mesh.
float3 NavigatorCabinLights(float3 pos, float3 n, float3 v, float3 albedo, float metallic, float roughness)
{
    static const float3 candela[3] = { float3(1100, 1700, 3000), float3(1100, 1700, 3000), float3(1300, 1900, 3000) };
    const float3 f0 = lerp(0.04, albedo, metallic);
    const float nv = max(dot(n, v), 0.001), a = roughness * roughness, a2 = a * a;
    const float k = (roughness + 1.0) * (roughness + 1.0) / 8.0;
    float3 light = 0;
    [unroll] for (uint i = 0; i < 3; ++i)
    {
        const float3 delta = NAVIGATOR_LAMP_POSITIONS[i] - pos, l = normalize(delta), h = normalize(l + v);
        const float nl = saturate(dot(n, l)), nh = saturate(dot(n, h));
        const float d = a2 / (3.14159265 * pow(nh * nh * (a2 - 1.0) + 1.0, 2.0));
        const float vis = 1.0 / (4.0 * (nl * (1.0 - k) + k) * (nv * (1.0 - k) + k));
        const float3 fresnel = f0 + (1.0 - f0) * pow(1.0 - saturate(dot(h, v)), 5.0);
        // World light uses a normalized sun (pi), rather than lux. Convert authored candela to that same scale.
        light += (albedo * (1.0 - metallic) / 3.14159265 + d * vis * fresnel) * nl * candela[i]
            * (SUN_ILLUMINANCE / 120000.0) / max(dot(delta, delta), 0.15);
    }
    return light;
}
