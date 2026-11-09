// Index the original cube-chart search, including remapped cells beyond face edges.
// The temporary slices 24..29 hold exact physical node eligibility during this pass.
#include "Erosion.hlsli"
RWStructuredBuffer<uint2> outActivity : register(u0);
[numthreads(64, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint3 tid : SV_DispatchThreadID)
{
    const uint n = ErosionSize(), face = group.y, c = face * n * n + tid.x;
    const uint2 tile = uint2(tid.x % n, tid.x / n);
    uint2 mask = 0u;
    if (all(tile < 7u * n / 8u)) {
        const int2 origin = int2(tile * 8u) - int(3u * n);
        [loop] for (uint bit = 0u; bit < 64u; ++bit) {
            const uint node = ErosionCell(face, origin + int2(bit % 8u, bit / 8u), n);
            const uint active = erosionMap.Load(int4(node % n, node / n % n, 24u + node / (n * n), 0)).x;
            if (active != 0u) {
                if (bit < 32u) mask.x |= 1u << bit;
                else mask.y |= 1u << (bit - 32u);
            }
        }
    }
    outActivity[c] = mask;
}
