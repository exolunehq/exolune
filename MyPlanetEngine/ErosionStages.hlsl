// The erosion and planet-map passes read the natural relief, never the city earthworks.
#define CITY_NATURAL_RELIEF
// Step B's second startup pass (docs/spec-erosion.md, the corridors), when the level 0 is computed: the relief each
// cell's courses cross where they are drawn (Erosion.hlsli, the same courses as ErosionRivers), for Erosion::Condition.
// Along its main course, and along its re-routed course when it is a minor inflow of its receiver: RIVER_CAP_SAMPLES
// points of the channel, displaced by its meanders, the relief before erosion filtered at RIVER_CAP_CELL. Their cap is
// the lowest of that relief where the course carries water, from RIVER_Q.y, clipped at the sea, less the bank: a dry
// notch needs none. The junctions follow the level 0's stages: the map's conditioned stages are still those.
#include "Relief.hlsli"

struct ErosionStage
{
    float main, connector; // the caps along the main course and the re-routed one (m), 1e30 without or dry
    float relief;          // the relief's mean along the main course (m)
    uint flags;            // 1: a main course; 2: the receiver's largest inflow; 4: re-routed to the receiver's main course
    float length;          // to the receiver's node (m)
};

RWStructuredBuffer<ErosionStage> outStages : register(u0); // face by face, row by row

// The cap and the relief's mean along a course, from the reference point pf, its node.
float2 ErosionCapAlong(ErosionCourse k, RlPoint ref, float3 pf)
{
    float lowest = 1e30, sum = 0.0;
    [loop] for (int i = 0; i < RIVER_CAP_SAMPLES; ++i)
    {
        const float t = i / (RIVER_CAP_SAMPLES - 1.0);
        const float3 tangent = ErosionCourseTangent(k, t);
        float3 q;
        float2 valley;
        const float4 m = ErosionMeander(k, t, ref, pf, normalize(tangent), q, valley) * (k.taper ? 1.0 - smoothstep(0.6, 1.0, t) : 1.0);
        const float3 up = normalize(pf + q), left = cross(normalize(tangent - dot(tangent, up) * up), up);
        double3 at = (double3)pf + (double3)(q + (m.x + m.z) / (1000.0 * PLANET_RADIUS_KM) * left);
        const double squared = at.x * at.x + at.y * at.y + at.z * at.z;
        double inverse = (double)rsqrt((float)squared);
        inverse *= 1.5 - 0.5 * squared * inverse * inverse;
        const float h = ReliefElevation(at * inverse, false), discharge = exp2(ErosionBezier(k.lq, t));
        if (discharge > RIVER_Q.y) lowest = min(lowest, max(h, 0.0) - RIVER_BANK * ErosionRiverSize(discharge).y);
        sum += h;
    }
    return float2(lowest, sum / RIVER_CAP_SAMPLES);
}

[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 threadId : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64);
    const uint n = ErosionSize(), c = group.y * n * n + threadId.x;
    gMaxFrequency = PLANET_RADIUS_KM / (MESH_BAND_LIMIT * 0.001 * RIVER_CAP_CELL);
    gCreaseMaxFrequency = gMaxFrequency;
    gExactLattice = false;
    ErosionStage o;
    o.main = 1e30, o.connector = 1e30, o.relief = 0.0, o.flags = 0u, o.length = 0.0;
    const float3 node = ErosionNode(c, n);
    const RlPoint ref = RlMakePoint((double3)node);
    const uint bits = ErosionRead(c, n).bits;
    ErosionNodeCourses v;
    [branch] if (ErosionMainCourse(c, n, node, 0.0, v))
    {
        const float2 cap = ErosionCapAlong(v.main, ref, node);
        o.main = cap.x, o.relief = cap.y, o.flags = 1u;
    }
    [branch] if (bits & EROSION_HAS_RECEIVER)
    {
        const uint r = ErosionNeighbour(c, bits & 7u, n);
        o.length = length(ErosionNode(r, n) - node) * 1000.0 * PLANET_RADIUS_KM;
        ErosionNodeCourses w;
        [branch] if (ErosionMainCourse(r, n, node, 0.0, w))
        {
            uint k = 8u;
            [unroll] for (uint j = 0; j < 8u; ++j)
                if (ErosionNeighbour(r, j, n) == c) k = j;
            if (k == w.mainInflow)
                o.flags |= 2u;
            else if (k < 8u && (w.connectors >> k & 1u))
            {
                o.flags |= 4u;
                o.connector = ErosionCapAlong(ErosionConnector(w, ErosionRiverNodeAt(c, n, node), ref, node, 0.0), ref, node).x;
            }
        }
    }
    outStages[c] = o;
}
