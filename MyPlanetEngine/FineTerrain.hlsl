// The fine grid (docs/spec-rendu-lointain.md, step 2): the face of the mesh cut ringParams.w times finer,
// recomputed every frame like the mesh, for the pixels' normals only. It carries the true relief finer than
// the mesh's cells, so that nothing mutates as the mesh refines on the way down. No rings, no geometry.
#include "Planet.hlsli"
#include "Relief.hlsli"
#include "Terrain.hlsli"

RWStructuredBuffer<FineSample> outFine : register(u0); // position/elevation and the same evaluation's inland water

[numthreads(64, 1, 1)]
void CSMain(uint3 threadId : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64); // before any return: every thread must reach the barrier
    const uint id = threadId.x;
    const uint n = (uint)(faceParams.w * ringParams.w);
    if (id >= (n + 1) * (n + 1))
        return;
    const float halfWidth = faceParams.x, R = faceParams.y, camAltitude = faceParams.z;
    const float2 xy = (float2(id % (n + 1), id / (n + 1)) / n * 2.0 - 1.0) * halfWidth;
    const float cellSize = 2.0 * halfWidth / n;

    float3 d;
    float r2, L;
    PlanePoint(xy, R, d, r2, L);
    if (!MaybeVisible(RelativePosition(d, r2, L, R, camAltitude, 0.0),
                      RelativePosition(d, r2, L, R, camAltitude, MAX_TERRAIN_HEIGHT), 0.0, 6.0 * cellSize * ringParams.w))
    {
        FineSample missing = (FineSample)0;
        missing.terrain = asfloat(0x7fc00000u).xxxx; // NaN: off screen
        outFine[id] = missing;
        return;
    }
    // The mesh is the previous frame's (D3DApp::Draw, camPlane.z): a point computed then has the same terrain.
    if (camPlane.z > 0.0 && (asuint(outFine[id].terrain.x) & 0x7fffffffu) <= 0x7f800000u)
        return;
    gMaxFrequency = L / (MESH_BAND_LIMIT * cellSize);
    gCreaseMaxFrequency = L / (MESH_BAND_LIMIT * max(cellSize, CREASE_MIN_CELL));
    gExactLattice = cellSize < EXACT_LATTICE_MAX_CELL;
    float3 dir, pos;
    const float elevation = TerrainAt(xy, R, camAltitude, dir, pos);
    FineSample sample;
    sample.terrain = float4(pos, elevation);
    sample.inland = float4(InlandSample(gWaterLevel, gWaterDepth, gWaterCoverage), gWaterDistance);
    sample.flow = float4(sample.inland.x * gWaterFlow, 0.0);
    outFine[id] = sample;
}
