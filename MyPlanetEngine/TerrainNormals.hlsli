#ifndef TERRAIN_NORMALS_HLSLI
#define TERRAIN_NORMALS_HLSLI
StructuredBuffer<FaceVertex> splineVertices : register(t4); // the mesh's vertices, the vertex shader's

// Weights of the four coefficients at offsets -1 to 2 from a cell's first vertex, at the fraction t of the
// cell; and their derivatives along the cell.
float4 SplineWeights(float t)
{
    const float s = 1.0 - t;
    return float4(s * s * s, (3.0 * t - 6.0) * t * t + 4.0, ((-3.0 * t + 3.0) * t + 3.0) * t + 1.0, t * t * t) / 6.0;
}

float4 SplineSlopes(float t)
{
    const float s = 1.0 - t;
    return float4(-s * s, (3.0 * t - 4.0) * t, (-3.0 * t + 2.0) * t + 1.0, t * t) * 0.5;
}

// The spline surface's normal at the pixel's chart coordinates, its elevation for the materials, and their
// weight against the vertex values: 0 within 3 cells of a chart's edge or of a ring's corner, 1 beyond 5,
// and 0 on the triangles between the face and the first ring, which mix both charts.
float3 SplineNormal(float3 chart, float corner, float3 up, out float3 surface, out float elevation, out float weight)
{
    const uint n = (uint)faceParams.w, ringCount = (uint)ringParams.x;
    const bool rings = chart.z > 0.999;
    weight = 0.0;
    elevation = 0.0;
    surface = 0.0;
    if (SPLINE_NORMALS <= 0.0 || (chart.z > 0.001 && !rings))
        return up;
    const float edge = rings ? min(corner, min(chart.y - 1.0, ringCount - chart.y))
                             : min(min(chart.x, chart.y), min(n - chart.x, n - chart.y));
    weight = SPLINE_NORMALS * saturate((edge - 3.0) * 0.5);
    if (weight <= 0.0)
        return up;

    const float2 cell = floor(chart.xy), t = chart.xy - cell;
    const float4 wu = SplineWeights(t.x), wv = SplineWeights(t.y), su = SplineSlopes(t.x), sv = SplineSlopes(t.y);
    float3 du = 0.0, dv = 0.0; // derivatives along the chart's two axes
    [unroll]
    for (int y = 0; y < 4; ++y)
    {
        float3 row = 0.0, rowSlope = 0.0;
        float rowElevation = 0.0;
        const int v = (int)cell.y + y - 1;
        [unroll]
        for (int x = 0; x < 4; ++x)
        {
            const int u = (int)cell.x + x - 1;
            const uint id = rings ? (n + 1) * (n + 1) + (uint)(clamp(v, 1, (int)ringCount) - 1) * 4 * n + (uint)(u + 4 * n) % (4 * n)
                                  : (uint)clamp(v, 0, (int)n) * (n + 1) + (uint)clamp(u, 0, (int)n);
            const FaceVertex c = splineVertices[id];
            row += wu[x] * c.pos;
            rowSlope += su[x] * c.pos;
            rowElevation += wu[x] * c.elevation;
        }
        du += wv[y] * rowSlope;
        dv += sv[y] * row;
        surface += wv[y] * row;
        elevation += wv[y] * rowElevation;
    }
    float3 normal = cross(du, dv);
    const float length2 = dot(normal, normal);
    if ((asuint(length2) & 0x7fffffffu) >= 0x7f800000u || !(length2 > 0.0)) // a culled vertex (NaN) was read
    {
        weight = 0.0;
        return up;
    }
    normal *= rsqrt(length2);
    return dot(normal, up) < 0.0 ? -normal : normal;
}

StructuredBuffer<FineSample> fineNormals : register(t7); // the fine grid's normals and water (FineNormals.hlsl)

// Reconstruct one cubic height surface from the fine grid, and differentiate that SAME surface for its normal.
// Linear heights and independently interpolated normals exposed the sliding grid in distant mountains: the
// height's slope jumped at every cell border. Positive B-spline weights keep the source height range. Water
// uses the same positive spline for its moments, followed by the physical contour query below.
// Weight fades over the face's last eight cells; no fine grid on rings or culled samples.
// uncertainty (m): how far the bilinear and the B-spline reconstructions of the same samples disagree, what the grid
// cannot tell of the height between its samples.
float3 FineNormal(float3 chart, out float weight, out float elevation, out float4 inland, out float3 flow, out float uncertainty,
                  out uint4 near)
{
    near = (uint4)0xffffffffu; // the wet nodes its four samples around the pixel know (Erosion.hlsli, ErosionRiversNear)
    weight = 0.0;
    elevation = 0.0;
    uncertainty = 0.0;
    inland = 0.0;
    flow = 0.0;
    if (ringParams.z <= 0.0 || chart.z > 0.5)
        return 0.0;
    const float n = faceParams.w;
    const int fineCells = (int)(n * ringParams.w);
    const float2 f = chart.xy * ringParams.w;
    // Clamped both ways: at the face's border the interpolated chart dips a hair below 0, and a root
    // descriptor has no bounds check, so a read out of the buffer would bring the GPU down.
    const int2 c = clamp((int2)floor(f), 0, fineCells - 1);
    const float2 t = saturate(f - c);
    const uint i = c.y * (fineCells + 1) + c.x;
    const FineSample sa = fineNormals[i], sb = fineNormals[i + 1], sd = fineNormals[i + fineCells + 1], se = fineNormals[i + fineCells + 2];
    const float4 a = sa.terrain, b = sb.terrain, d = sd.terrain, e = se.terrain;
    if (dot(a.xyz, a.xyz) * dot(b.xyz, b.xyz) * dot(d.xyz, d.xyz) * dot(e.xyz, e.xyz) == 0.0) // a point off screen
        return 0.0;
    near = uint4(asuint(sa.flow.w), asuint(sb.flow.w), asuint(sd.flow.w), asuint(se.flow.w));
    inland = lerp(lerp(sa.inland, sb.inland, t.x), lerp(sd.inland, se.inland, t.x), t.y);
    flow = lerp(lerp(sa.flow.xyz, sb.flow.xyz, t.x), lerp(sd.flow.xyz, se.flow.xyz, t.x), t.y);
    const float4 wu = SplineWeights(t.x), wv = SplineWeights(t.y), su = SplineSlopes(t.x), sv = SplineSlopes(t.y);
    float height = 0.0;
    float2 slope = 0.0;
    float4 water = 0.0;
    float3 velocity = 0.0;
    bool valid = true;
    [unroll] for (int y = 0; y < 4; ++y)
    {
        float row = 0.0, rowSlope = 0.0;
        float4 rowWater = 0.0;
        float3 rowFlow = 0.0;
        [unroll] for (int x = 0; x < 4; ++x)
        {
            const int2 tap = clamp(c + int2(x - 1, y - 1), 0, fineCells);
            const FineSample field = fineNormals[tap.y * (fineCells + 1) + tap.x];
            const float4 sample = field.terrain;
            valid = valid && dot(sample.xyz, sample.xyz) > 0.0;
            // Derivative weights sum to zero; subtract a nearby height before accumulating them.
            row += wu[x] * (sample.w - a.w);
            rowSlope += su[x] * (sample.w - a.w);
            rowWater += wu[x] * field.inland;
            rowFlow += wu[x] * field.flow.xyz;
        }
        height += wv[y] * row;
        slope += float2(wv[y] * rowSlope, sv[y] * row);
        water += wv[y] * rowWater;
        velocity += wv[y] * rowFlow;
    }
    const float4 mixed = lerp(lerp(a, b, t.x), lerp(d, e, t.x), t.y);
    elevation = valid ? a.w + height : mixed.w;
    uncertainty = abs(elevation - mixed.w);
    weight = ringParams.z * saturate(min(min(chart.x, n - chart.x), min(chart.y, n - chart.y)) / 8.0);
    if (!valid) return normalize(mixed.xyz);
    inland = water;
    flow = velocity;
    const float fineCell = 2.0 * faceParams.x / fineCells;
    slope /= fineCell;
    const float2 xy = (f / fineCells * 2.0 - 1.0) * faceParams.x;
    const float3 radial = float3(xy, faceParams.y);
    const float radius = length(radial);
    const float3 up = radial / radius;
    const float stretch = (faceParams.y + elevation) / radius;
    const float3 du = stretch * (float3(1.0, 0.0, 0.0) - up.x * up) + slope.x * up;
    const float3 dv = stretch * (float3(0.0, 1.0, 0.0) - up.y * up) + slope.y * up;
    return normalize(cross(du, dv));
}

StructuredBuffer<ScreenSample> screenSamples : register(t52); // the screen relief: positions, elevation, water (ScreenRelief.hlsl)

// The screen relief under the pixel (ScreenRelief.hlsl): the smoothing B-spline of its 4 x 4 nearest texels, their
// positions, elevations and inland water, the normal its derivatives' cross product. The texels follow the view: a
// bilinear reconstruction, the tent, gave a wave of 4 texels a slope varying by 9 % with where the texels fell, and the
// ground trembled as the camera moved; the B-spline, 3 %, 0.4 % at 8 texels (docs/log/pistes-glissement.md).
// weight: the relief's own, 0 where one of the 16 has no ground (the limb). position: the ground's, camera-relative;
// ground: its own fields (ScreenSample).
float3 ScreenNormal(float2 pixel, float3 up, out float weight, out float elevation, out float4 inland, out float3 position,
                    out float4 ground, out float3 flow)
{
    weight = 0.0;
    elevation = 0.0;
    inland = 0.0;
    position = 0.0;
    ground = 0.0;
    flow = 0.0;
    if (screenRelief.z <= 0.0)
        return 0.0;
    const int2 size = int2(screenRelief.xy);
    const float2 f = pixel / screenRelief.w - 0.5;
    const int2 c = clamp((int2)floor(f), 1, size - 3);
    const float2 t = saturate(f - c);
    const float4 wu = SplineWeights(t.x), wv = SplineWeights(t.y), su = SplineSlopes(t.x), sv = SplineSlopes(t.y);
    const float3 origin = screenSamples[c.y * size.x + c.x].terrain.xyz; // positions taken relative to it: no cancellation
    float3 du = 0.0, dv = 0.0, at = 0.0;
    float height = 0.0;
    float4 water = 0.0, fields = 0.0;
    float3 velocity = 0.0;
    bool valid = true;
    [unroll] for (int y = 0; y < 4; ++y)
    {
        float3 row = 0.0, rowSlope = 0.0;
        float rowHeight = 0.0;
        float4 rowWater = 0.0, rowFields = 0.0;
        float3 rowFlow = 0.0;
        [unroll] for (int x = 0; x < 4; ++x)
        {
            const ScreenSample s = screenSamples[(c.y + y - 1) * size.x + c.x + x - 1];
            valid = valid && !isnan(s.terrain.x);
            const float3 p = s.terrain.xyz - origin;
            row += wu[x] * p;
            rowSlope += su[x] * p;
            rowHeight += wu[x] * s.terrain.w;
            rowWater += wu[x] * s.inland;
            rowFields += wu[x] * s.ground;
            rowFlow += wu[x] * s.flow.xyz;
        }
        at += wv[y] * row;
        du += wv[y] * rowSlope;
        dv += sv[y] * row;
        height += wv[y] * rowHeight;
        water += wv[y] * rowWater;
        fields += wv[y] * rowFields;
        velocity += wv[y] * rowFlow;
    }
    if (!valid)
        return 0.0;
    float3 normal = normalize(cross(du, dv));
    normal *= dot(normal, up) < 0.0 ? -1.0 : 1.0;
    elevation = height;
    inland = water;
    position = origin + at;
    ground = fields;
    flow = velocity;
    weight = screenRelief.z;
    return normal;
}

#endif
