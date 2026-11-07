// The courses built once at startup (Erosion.hlsli, ErosionCourseRecord), after the activity index: each eligible node's
// main course, then its re-routed tributaries' connectors, by neighbour order, their controls relative to the node. No
// footprint here: a junction's meander at full detail, as a confluence stays where it is (gMaxFrequency without limit).
#include "Erosion.hlsli"

RWStructuredBuffer<ErosionCourseRecord> outCourses : register(u0);

ErosionCourseRecord Record(ErosionCourse k, uint extra)
{
    ErosionCourseRecord m = ErosionCourseToRecord(k, extra);
    m.reach = ErosionCourseReach(k);
    gErosionWater = true;
    m.channelReach = ErosionCourseReach(k);
    gErosionWater = false;
    return m;
}

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 tid : SV_DispatchThreadID, uint lane : SV_GroupIndex)
{
    LoadGradients(lane, 64); // before any return: every thread reaches the barrier
    const uint n = ErosionSize(), c = group.y * n * n + tid.x;
    const uint word = erosionMap.Load(int4(c % n, c / n % n, c / (n * n) + 30u, 0)).x;
    if ((word & 1u) == 0u)
        return;
    const float3 centre = ErosionNode(c, n);
    ErosionNodeCourses v;
    if (!ErosionMainCourse(c, n, centre, 0.0, v))
        return; // eligible nodes always have one (ErosionActivity.hlsl)
    const uint first = (word >> 1) & EROSION_FIRST_MASK;
    ErosionCourseRecord main = Record(v.main, (v.head ? 32u : 0u) | (v.outlet ? 64u : 0u) | v.connectors << 8);
    main.scale = v.scale, main.stopsW = v.r.stops.w;
    outCourses[first] = main;
    const RlPoint ref = RlMakePoint((double3)centre);
    uint slot = first + 1u;
    [loop] for (uint todo = v.connectors; todo != 0u; todo &= todo - 1u)
    {
        const ErosionRiverNode u = ErosionRiverNodeAt(ErosionNeighbour(c, firstbitlow(todo), n), n, centre);
        outCourses[slot++] = Record(ErosionConnector(v, u, ref, centre, 0.0), 0u);
    }
}
