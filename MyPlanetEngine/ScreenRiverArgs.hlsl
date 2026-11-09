#include "ScreenRiverTasks.hlsli"
[numthreads(1, 1, 1)]
void CSMain()
{
    const uint groups = (riverCounter.Load(0) + 7u) / 8u; // eight 32-lane queries per group
    riverDispatch.Store3(0, uint3(min(groups, 1024u), (groups + 1023u) / 1024u, 1u));
}
