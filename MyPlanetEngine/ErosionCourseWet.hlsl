// Each eligible node's word completed once its courses are built (D3DApp::CreateErosionMap): bit 31 when one of them can
// carry a channel (ErosionCourseWet), bits 19 to 30 the reach of those channels from the node, in 32 m, 4095 for none
// within 131 km (ErosionNodeChannelBound). The water contour lists no other node, and gates the wet ones by that reach.
#include "Erosion.hlsli"

RWStructuredBuffer<uint2> outEligible : register(u0);

// The farthest a course's hull lies from its node, its controls relative to the node (ErosionActivity.hlsl's CourseBound).
float ErosionHullExtent(float3 a, float3 b, float3 c)
{
    return (max(length(a), length(c)) + 0.5 * length(b - 0.5 * (a + c))) * (1000.0 * PLANET_RADIUS_KM);
}

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 tid : SV_DispatchThreadID)
{
    const uint n = ErosionSize(), c = group.y * n * n + tid.x;
    uint2 slot = erosionMap.Load(int4(c % n, c / n % n, c / (n * n) + 30u, 0));
    [branch] if ((slot.x & 1u) != 0u)
    {
        const uint first = (slot.x >> 1) & EROSION_FIRST_MASK;
        const ErosionCourseRecord main = erosionCourses[first];
        float reach = -1.0;
        [branch] if (ErosionRecordWet(main))
        {
            reach = ErosionHullExtent(main.a, main.b, main.c) + main.channelReach;
            // An outlet's line carries the main course's last discharge (ErosionAccumulateNode's test).
            [branch] if ((main.flags & 64u) != 0u && (main.flags & 16u) == 0u && main.lq.z > log2(RIVER_Q.y) - 1e-3)
            {
                ErosionNodeCourses v = (ErosionNodeCourses)0;
                v.main = ErosionCourseFromRecord(main, 0.0);
                v.scale = main.scale;
                v.r.stops = float4(main.stops0, main.stops1, 0.0, main.stopsW);
                const ErosionCourse outlet = ErosionOutletCourse(v);
                gErosionWater = true;
                reach = max(reach, ErosionHullExtent(outlet.a, outlet.b, outlet.c) + ErosionCourseReach(outlet));
                gErosionWater = false;
            }
        }
        const uint connectors = countbits(main.flags >> 8 & 255u);
        [loop] for (uint i = 0u; i < connectors; ++i)
        {
            const ErosionCourseRecord m = erosionCourses[first + 1u + i];
            [branch] if (ErosionRecordWet(m))
                reach = max(reach, ErosionHullExtent(m.a, m.b, m.c) + m.channelReach);
        }
        [branch] if (reach >= 0.0)
        {
            // The float reconstruction's guard of the activity's bound (ErosionActivity.hlsl), rounded up.
            const float guard = 64.0 * (1000.0 * PLANET_RADIUS_KM) * 1.1920928955078125e-7;
            const uint quanta = isfinite(reach) ? (uint)min(ceil((reach + guard) / 32.0) + 1.0, 4095.0) : 4095u;
            slot.x = (slot.x & 0x7ffffu) | quanta << 19 | 0x80000000u;
        }
    }
    outEligible[c] = slot;
}
