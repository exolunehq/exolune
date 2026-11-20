// Surface-space optics shared by canopy glazing and the helmet visor.
#ifndef OPTICAL_SURFACE_HLSLI
#define OPTICAL_SURFACE_HLSLI

float GlassHash(float2 p)
{
    p = frac(p * float2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return frac(p.x * p.y);
}

float GlassNoise(float2 p)
{
    const float2 i = floor(p), f = frac(p), u = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(GlassHash(i), GlassHash(i + float2(1, 0)), u.x),
                lerp(GlassHash(i + float2(0, 1)), GlassHash(i + 1.0), u.x), u.y);
}

// One short polished hairline in a fraction of the 7 cm cells. Integrate its
// thickness over the pixel footprint so distant panes do not glitter or alias.
float GlassHairline(float2 metres, float footprint)
{
    const float pitch = 0.07, halfWidth = 0.000082;
    const float2 grid = metres / pitch, cell = floor(grid);
    const float choice = GlassHash(cell + 3.7);
    const float angle = 6.2831853 * GlassHash(cell + 9.3);
    const float2 axis = float2(cos(angle), sin(angle)), side = float2(-axis.y, axis.x);
    const float2 p = (frac(grid) - 0.5) * pitch;
    const float along = dot(p, axis), across = abs(dot(p, side) + 5.0 * along * along);
    const float end = lerp(0.009, 0.026, GlassHash(cell - 5.1));
    const float filter = max(halfWidth, 0.5 * footprint);
    const float coverage = (1.0 - smoothstep(0.0, halfWidth + filter, across)) * halfWidth / filter;
    return step(0.77, choice) * coverage * (1.0 - smoothstep(0.3 * end, end, abs(along)));
}

// An integer seed keeps every groove tied to the same surface cell on every GPU.
uint AbrasionHash(uint x)
{
    x = (x ^ (x >> 16)) * 0x7feb352du;
    x = (x ^ (x >> 15)) * 0x846ca68bu;
    return x ^ (x >> 16);
}

float AbrasionUnit(uint bits) { return (bits & 1023u) * (1.0 / 1023.0); }

// An abrasion has a principal groove and occasionally one or two short, broken
// neighbours. Both the fixed chart and the pixel filter are measured in metres.
float2 CanopyAbrasion(float2 q, float2 dx, float2 dy, float3 dPdx, float3 dPdy, float3 sunPlusView)
{
    const float pitch = 0.136;
    const float resolved = 1.0 - smoothstep(0.022, 0.070, max(length(dx), length(dy)));
    float2 grid = q / pitch + float2(0.17, 0.31);
    grid.x += frac(floor(grid.y) * 0.618034);
    const uint2 cell = asuint(int2(floor(grid)));
    const uint site = AbrasionHash(cell.x * 0x9e3779b9u ^ cell.y * 0x85ebca6bu ^ 0xa511e9b3u);
    [branch] if ((site & 255u) >= 134u || resolved <= 0.0) return 0.0;

    const uint marks = AbrasionHash(site + 17u);
    const float2 offset = float2(AbrasionUnit(site >> 8), AbrasionUnit(site >> 18)) - 0.5;
    const float2 p = (frac(grid) - 0.5) * pitch - 0.040 * offset;
    float sn, cs;
    sincos(3.14159265 * AbrasionUnit(marks), sn, cs);
    const float2 axis = float2(cs, sn), side = float2(-sn, cs);
    const float u = dot(p, axis), v = dot(p, side);
    [branch] if (abs(u) > 0.050 || abs(v) > 0.026) return 0.0;
    const float reach = lerp(0.018, 0.044, AbrasionUnit(marks >> 10));
    const float fan = (marks & 0x80000000u) ? 1.0 : -1.0;
    const uint count = (marks >> 20) & 255u;

    // Transport the local tangent to the actual pane, including the Navigator's
    // angular chart. Its common Jacobian factor cancels when we normalize T.
    const float3 tangentU = dPdx * dy.y - dPdy * dx.y;
    const float3 tangentV = dPdy * dx.x - dPdx * dy.x;
    float2 response = 0.0;
    [unroll] for (uint i = 0; i < 3; ++i) {
        if ((i == 1 && count > 142u) || (i == 2 && count > 37u)) break;
        const uint groove = AbrasionHash(marks + 0x9e3779b9u * (i + 1u));
        const float a = AbrasionUnit(groove), b = AbrasionUnit(groove >> 10), c = AbrasionUnit(groove >> 20);
        const float end = reach * (i == 0 ? 1.0 : lerp(0.23, 0.66, a));
        const float x = u - (i == 0 ? 0.0 : 0.022 * (b - 0.5));
        const float t = x / end;
        const float tip = (1.0 - smoothstep(0.55, 1.0, abs(t))) * lerp(0.76, 1.0, saturate(t + 0.5));
        const float lane = i == 0 ? 0.0 : fan * (i == 1 ? -1.0 : 1.0) * lerp(0.0024, 0.0085, c);
        const float slope = i == 0 ? 0.0 : fan * (i == 1 ? -1.0 : 1.0) * lerp(0.05, 0.37, b);
        // A curved cut changes tangent along its length. A shallow section or a
        // worn-away nick interrupts the reflection without per-frame random noise.
        const float bow = (c - 0.5) * 0.43;
        const float derivative = slope + 2.0 * bow * t;
        const float invLength = rsqrt(1.0 + derivative * derivative);
        const float distance = (v - lane - x * (slope + bow * t)) * invLength;
        const float2 across = (side - derivative * axis) * invLength;
        const float pixel = max(0.00008, 0.63 * (abs(dot(dx, across)) + abs(dot(dy, across))));
        const float width = (i == 0 ? lerp(0.00026, 0.00048, a) : lerp(0.00012, 0.00028, c)) * tip;
        const float nick = lerp(-0.50, 0.47, b);
        const float depth = lerp(0.07 + 0.35 * a, 1.0, smoothstep(0.025, 0.24, abs(t - nick)));
        const float covered = smoothstep(-pixel, pixel, distance + width)
                            - smoothstep(-pixel, pixel, distance - width);
        const float2 tangent = axis + derivative * side;
        const float3 T = tangent.x * tangentU + tangent.y * tangentV;
        const float alongLight = dot(T, sunPlusView) * rsqrt(max(dot(T, T), 1.e-24));
        const float lobe = rcp(1.0 + lerp(11.0, 36.0, a) * alongLight * alongLight);
        response += covered * depth * float2(1.0, lobe * lobe);
    }
    return resolved * saturate(response);
}

float GlassFresnel(float incidence)
{
    // Uncoated dielectric, effective refractive index 1.5 at the air interface.
    return 0.04 + 0.96 * pow(1.0 - saturate(incidence), 5.0);
}

#endif
