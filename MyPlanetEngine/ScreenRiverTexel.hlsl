// One river query per texel, its wave's texels listing their rivers' nodes together (Erosion.hlsli, EROSION_WAVE_LIST),
// then its ground finished: a kernel of its own, as the corridors cost thirty times more inlined in the ground pass.
#define EROSION_WAVE_LIST
#include "ScreenRiverTasks.hlsli"

[numthreads(8, 8, 1)]
void CSMain(uint3 tid : SV_DispatchThreadID, uint lane : SV_GroupIndex)
{
    LoadGradients(lane, 64); // before any return: every thread reaches the barrier
    const uint w = (uint)screenRelief.x, h = (uint)screenRelief.y, id = tid.y * w + tid.x;
    [branch] if (tid.x >= w || tid.y >= h) return;
    if (!screenWork[id].active) return;
    const float height = screenWork[id].ground.height;
    [branch] if (ErosionRivers() && height > -500.0)
    {
        const double3 p = ScreenRiverPoint(id);
        const float cellKm = screenWork[id].ground.cellKm;
        // A wide search, at the limb, to a wave of its own (ScreenRivers.hlsl), which finishes it: its wave's other texels
        // keep their listing.
        [branch] if (ErosionRiversWide(p, cellKm))
        {
            ScreenRiverFallbackThread(id);
            return;
        }
        ScreenBandwidth(screenWork[id].footprint);
        ScreenRiverStore(id, ErosionRivers(p, cellKm, height, screenWork[id].ground.riverParent, screenWork[id].ground.riverFine));
    }
    ScreenFinishTexel(id);
}
