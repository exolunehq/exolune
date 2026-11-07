// First standing-water contacts, prepared once after stage conditioning and stored with the drainage cache.
// Each half of a main course is independent: a drowned incoming river must not erase a separate dry catchment.
#include "Relief.hlsli"

RWStructuredBuffer<float4> outContacts : register(u0);

float ErosionContactHeight(ErosionCourse k, float t, RlPoint ref, float3 pf)
{
    const float3 tangent = ErosionCourseTangent(k, t);
    float3 q;
    float2 valley;
    float4 m = ErosionMeander(k, t, ref, pf, normalize(tangent), q, valley);
    m *= k.taper ? 1.0 - smoothstep(0.6, 1.0, t) : 1.0;
    const float3 up = normalize(pf + q), left = cross(normalize(tangent - dot(tangent, up) * up), up);
    double3 at = (double3)pf + (double3)(q + (m.x + m.z) / (1000.0 * PLANET_RADIUS_KM) * left);
    const double squared = at.x * at.x + at.y * at.y + at.z * at.z;
    double inverse = (double)rsqrt((float)squared);
    inverse *= 1.5 - 0.5 * squared * inverse * inverse;
    at *= inverse;
    uint face;
    float2 x;
    const uint n = ErosionSize();
    ErosionLocate((float3)at, n, face, x);
    const float level = ErosionLakeLevel(face, x, n, 2000.0 * PLANET_RADIUS_KM / n);
    // The actual shoreline includes ravines, coastal erosion and barriers, but not the river currently seeking it.
    return ReliefElevation(at, true, false) - level;
}

float ErosionFirstWater(ErosionCourse k, float begin, float end, RlPoint ref, float3 pf)
{
    const float span = (length(k.b - k.a) + length(k.c - k.b)) * (end - begin) * 1000.0 * PLANET_RADIUS_KM;
    const uint count = max((uint)ceil(span / RIVER_CONTACT.x), 1u);
    float previous = begin, t = begin, lo = begin, hi = end;
    uint sample = 0u, refine = 0u;
    bool bracket = false;
    // One terrain call site serves the march and its bisection. This keeps the startup shader compact.
    [loop] for (uint iteration = 0u; iteration <= count + 8u; ++iteration)
    {
        const bool wet = ErosionContactHeight(k, t, ref, pf) < 0.0;
        if (bracket)
        {
            if (wet) hi = t; else lo = t;
            if (++refine >= 7u) return saturate((hi - begin) / (end - begin));
            t = 0.5 * (lo + hi);
        }
        else if (wet)
        {
            if (sample == 0u) return 0.0;
            lo = previous, hi = t, bracket = true, t = 0.5 * (lo + hi);
        }
        else
        {
            if (sample == count) return 1.0;
            previous = t;
            t = lerp(begin, end, (float)(++sample) / count);
        }
    }
    return 1.0;
}

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 threadId : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64);
    gMaxFrequency = PLANET_RADIUS_KM / (MESH_BAND_LIMIT * 0.001 * RIVER_CONTACT.y);
    gCreaseMaxFrequency = gMaxFrequency;
    gExactLattice = false;
    const uint n = ErosionSize(), c = group.y * n * n + threadId.x;
    const float3 node = ErosionNode(c, n);
    const RlPoint ref = RlMakePoint((double3)node);
    const uint bits = ErosionRead(c, n).bits;
    float4 contacts = 1.0;
    ErosionNodeCourses v;
    const bool main = ErosionMainCourse(c, n, node, 0.0, v);
    ErosionCourse connector = v.main;
    bool hasConnector = false;
    if (bits & EROSION_HAS_RECEIVER)
    {
        const uint r = ErosionNeighbour(c, bits & 7u, n);
        ErosionNodeCourses w;
        if (ErosionMainCourse(r, n, node, 0.0, w))
        {
            uint match = 8u;
            [unroll] for (uint k = 0u; k < 8u; ++k)
                if (((w.connectors >> k) & 1u) && ErosionNeighbour(r, k, n) == c) match = k;
            if (match < 8u)
                connector = ErosionConnector(w, ErosionRiverNodeAt(c, n, node), ref, node, 0.0), hasConnector = true;
        }
    }
    [loop] for (uint part = 0u; part < 4u; ++part)
    {
        if (part == 2u ? !hasConnector : (!main || (part == 3u && !v.outlet))) continue;
        ErosionCourse course = v.main;
        if (part == 2u) course = connector;
        else if (part == 3u) course = ErosionOutletCourse(v);
        contacts[part] = ErosionFirstWater(course, part == 1u ? 0.5 : 0.0, part == 0u ? 0.5 : 1.0, ref, node);
    }
    outContacts[c] = contacts;
}
