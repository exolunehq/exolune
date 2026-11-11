// CityGrade.hlsli - earthworks under the city (tools/city/grading.py, grading.bin): flat pads graded into the relief.
// Around a pad the ground departs from its height by at most its talus slope per metre, reached over the edge
// rounding; crest and toe are rounded over the knee; beyond, the natural ground is untouched. Active where the Frame
// constants are visible (Planet.hlsli included first), so the terrain mesh, its pixels, the screen relief, vegetation
// and horizons share the graded ground. Passes that must read the natural relief define CITY_NATURAL_RELIEF before
// their includes. CityBank tells the materials where a bank stands, so it keeps the ground it was cut from. A pass
// without the Frame constants (the flight contact) declares the same fields and CITY_GRADE_FIELDS, with its radius.
#ifndef CITY_GRADE_HLSLI
#define CITY_GRADE_HLSLI

#if (defined(PLANET_HLSLI) || defined(CITY_GRADE_FIELDS)) && !defined(CITY_NATURAL_RELIEF)
#ifndef CITY_GRADE_RADIUS
#define CITY_GRADE_RADIUS faceParams.y // the body's radius (m)
#endif
float CitySoftClamp(float v, float limit)
{
    const float w = min(cityEast.w, limit), a = abs(v);
    if (a <= limit - w) return v;
    if (a >= limit + w) return sign(v) * limit;
    const float t = a - (limit - w);
    return sign(v) * ((limit - w) + t - t * t / (4.0 * max(w, 1e-6)));
}

// Largest departure from a pad's level at `dist` metres from its edge: level at the edge, the pad's own bank slope
// beyond the rounding distance. A pad on steep ground keeps a steeper bank, so its earthworks stay local.
float CityEnvelope(float dist, float talus)
{
    const float r = (float)cityUp.w, beyond = max(dist, 0.0);
    return talus * (beyond < r ? beyond * beyond / (2.0 * r) : beyond - 0.5 * r);
}

// The city frame's metres for a direction from the planet's centre, and the pads of its index cell; 0 pads when
// there are no earthworks here.
uint CityGradeCell(float3 d, out float2 p, out uint first)
{
    p = 0.0; first = 0;
    if (cityNorth.w < 0.5 || dot(d, d) > 1e-6) return 0; // beyond about 6 km of the city
    p = CITY_GRADE_RADIUS * float2(dot(d, cityEast.xyz), dot(d, cityNorth.xyz));
    const int2 cell = (int2)floor((p - cityGradeGrid.xy) / cityGradeGrid.z);
    if (any(cell < 0) || any(cell >= 32)) return 0;
    const uint index = uint(cell.y * 32 + cell.x), packed = cityGradeCells[index >> 2][index & 3];
    first = packed & 0xffffu;
    return packed >> 16;
}

// Signed distance to the i-th indexed pad's flat (negative inside), its level and its bank slope. A pad is
// (centre xy, yaw, talus) and (half extents, corner radius, level): CITYPAD2.
float CityPadDistance(float2 p, uint i, out float level, out float talus)
{
    const uint pad = (cityGradeIndex[i >> 3][(i >> 1) & 3] >> (16 * (i & 1))) & 0xffffu;
    const float4 a = cityPads[pad * 2], b = cityPads[pad * 2 + 1];
    float s, c;
    sincos(a.z, s, c);
    const float2 q0 = p - a.xy;
    const float2 q = float2(dot(q0, float2(c, s)), dot(q0, float2(-s, c)));
    const float2 e = abs(q) - b.xy + b.z;
    level = b.w;
    talus = a.w;
    return length(max(e, 0.0)) + min(max(e.x, e.y), 0.0) - b.z;
}

float CityGrade(double3 position, float h)
{
    float2 p;
    uint first;
    const uint count = CityGradeCell((float3)(position - cityUp.xyz), p, first);
    for (uint k = 0; k < count; ++k)
    {
        float level, talus;
        const float dist = CityPadDistance(p, first + k, level, talus);
        h = level + CitySoftClamp(h - level, CityEnvelope(dist, talus));
    }
    return h;
}

// 1 on a pad, and on its bank where the graded ground is held at the bank's slope (within its knee of the
// envelope, less 0.4 m for the pixel's interpolated elevation); 0 on untouched ground.
float CityBank(float3 direction, float elevation)
{
    float2 p;
    uint first;
    const uint count = CityGradeCell(direction - (float3)cityUp.xyz, p, first);
    float bank = 0.0;
    for (uint k = 0; k < count; ++k)
    {
        float level, talus;
        const float dist = CityPadDistance(p, first + k, level, talus);
        const float limit = CityEnvelope(dist, talus), w = min(cityEast.w, limit);
        bank = max(bank, dist <= 0.0 ? 1.0 : smoothstep(limit - w - 0.4, limit - w + 0.1, abs(elevation - level)));
    }
    return bank;
}
#else
float CityGrade(double3 position, float h) { return h; }
float CityBank(float3 direction, float elevation) { return 0.0; }
#endif

#endif
