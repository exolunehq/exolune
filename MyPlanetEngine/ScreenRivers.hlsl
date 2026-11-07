// One wave cooperates on each physical sample; no course or filter support is removed.
#define EROSION_WAVE_COURSES
#include "ScreenRiverTasks.hlsli"

[numthreads(256, 1, 1)]
void CSMain(uint3 group : SV_GroupID, uint lane : SV_GroupIndex)
{
    LoadGradients(lane, 256);
    const uint w = (uint)screenRelief.x, h = (uint)screenRelief.y;
    const uint wave = lane / WaveGetLaneCount(), waves = 256u / WaveGetLaneCount();
    // Dispatch arguments conservatively assume 32-lane waves. Wider hardware covers the remainder here.
    [loop] for (uint local = wave; local < 8u; local += waves)
    {
        const uint query = (group.y * 1024u + group.x) * 8u + local;
        if (query >= riverCounter.Load(0)) continue;
        const uint id = riverFallback[query];
        if (!screenWork[id].active || !ErosionRivers()) continue;
        const float height = screenWork[id].ground.height;
        if (height <= -500.0) continue;
        ScreenBandwidth(screenWork[id].footprint);
        const ErosionRiver river = ErosionRivers(ScreenWorldPoint(screenWork[id].xy), screenWork[id].ground.cellKm,
            height, screenWork[id].ground.riverParent, screenWork[id].ground.riverFine);
        // Only write the fields owned by erosion; the coastal and volcanic state stays in the buffer.
        if (WaveIsFirstLane()) {
            screenWork[id].ground.height = height + (river.fill - river.carve);
            screenWork[id].ground.lakeLevel = river.lakeLevel;
            screenWork[id].ground.channelBed = river.bed;
            screenWork[id].ground.channelSurface = river.stage;
            screenWork[id].ground.channelDistance = river.distance;
            screenWork[id].ground.channelEdge = river.edge;
            screenWork[id].ground.channelCut = river.cut;
            screenWork[id].ground.channelCoverage = river.coverage;
            screenWork[id].ground.channelBank = river.bank;
            screenWork[id].ground.waterFlow = river.flow;
            ScreenFinishTexel(id);
        }
    }
}
