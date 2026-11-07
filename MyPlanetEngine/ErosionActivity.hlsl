// Exact topology eligibility, once after first-water contacts and discharge accumulation.
// The return predicate uses map fields only; no camera, bandwidth or reference-position input.
#include "Erosion.hlsli"

RWStructuredBuffer<uint2> outActivity : register(u0);

// Bound the existing projected chord-minus-bulge gate around this node.
// Projection cannot enlarge either the control offsets or the bulge.
float CourseBound(ErosionCourse k)
{
    return (max(length(k.a), length(k.c)) + 0.5 * length(k.b - 0.5 * (k.a + k.c)))
         * (1000.0 * PLANET_RADIUS_KM) + ErosionCourseReach(k);
}

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 tid : SV_DispatchThreadID)
{
    const uint n = ErosionSize(), c = group.y * n * n + tid.x;
    ErosionNodeCourses v;
    const float3 centre = ErosionNode(c, n);
    if (!ErosionMainCourse(c, n, centre, 0.0, v)) { outActivity[c] = 0u; return; }
    float bound = CourseBound(v.main);
    if (v.head) bound = max(bound, CourseBound(ErosionHeadCourse(v)));
    if (v.outlet) bound = max(bound, CourseBound(ErosionOutletCourse(v)));
    const float reach = 2.0 * ErosionCourseReach(v.main);
    [loop] for (uint todo = v.connectors; todo != 0u; todo &= todo - 1u) {
        const uint side = firstbitlow(todo);
        const float3 start = 0.5 * (ErosionNode(ErosionNeighbour(c, side, n), n) - centre);
        // The connector's existing early gate uses its start, this node and a point on the main curve.
        const float extent = max(length(start), max(length(v.main.a), max(length(v.main.b), length(v.main.c))));
        bound = max(bound, extent * (1000.0 * PLANET_RADIUS_KM) + reach);
    }
    // Cover the float reconstruction error when controls use another local reference point.
    const float guard = 64.0 * (1000.0 * PLANET_RADIUS_KM) * 1.1920928955078125e-7;
    // x: eligible, and its connectors' count for the courses built next (ErosionCourseBuild.hlsl).
    outActivity[c] = uint2(1u | countbits(v.connectors) << 1, asuint(isfinite(bound) ? bound + guard : 1e30));
}
