// The terrain mesh, recomputed every frame: a cube face that faces the camera, surrounded by square
// rings that grow geometrically up to the horizon. Everything lies on the face plane z = R and is
// normalised onto the sphere. See docs/log/spec-champ-de-vision.md.
//
// Vertex layout, matching the index buffer built in D3DApp.cpp:
// - the face: (n + 1) x (n + 1) vertices, row by row;
// - then each ring: 4n vertices around a square, in the same order as the face's border.
#define EROSION_WAVE_LIST // neighbouring samples list their rivers' nodes together (Erosion.hlsli)
#include "Planet.hlsli"
#include "SurfaceStack.hlsli"
#include "Terrain.hlsli"
#include "Mesh.hlsli"

RWStructuredBuffer<FaceVertex> outVerts : register(u0);

[numthreads(64, 1, 1)]
void CSMain(uint3 groupId : SV_GroupID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64); // before any return: every thread must reach the barrier
    const uint n = (uint)faceParams.w;
    const uint faceVertexCount = (n + 1) * (n + 1);
    const uint ringCount = (uint)ringParams.x, vertexCount = faceVertexCount + ringCount * 4u * n;
    // By 8 x 8 tiles (D3DApp::Draw): the face's grid by squares, its rings by 8 vertices along 8 of them. A wave's
    // vertices are then neighbours on both axes and list their rivers' nodes together (Erosion.hlsli).
    uint id;
    const uint across = (n + 8u) / 8u, faceTiles = across * across, group = groupId.x;
    const uint alongTiles = n / 2u;
    const bool probe = group == faceTiles + ((ringCount + 7u) / 8u) * alongTiles;
    if (probe)
    {
        if (threadInGroup != 0) return;
        id = vertexCount;
    }
    else if (group < faceTiles)
    {
        const uint2 ij = uint2(group % across, group / across) * 8u + uint2(threadInGroup % 8u, threadInGroup / 8u);
        id = any(ij > n) ? 0xffffffffu : ij.y * (n + 1) + ij.x;
    }
    else
    {
        const uint g = group - faceTiles;
        const uint ring = (g / alongTiles) * 8u + threadInGroup / 8u, along = (g % alongTiles) * 8u + threadInGroup % 8u;
        id = ring >= ringCount ? 0xffffffffu : faceVertexCount + ring * 4u * n + along;
    }
    if (!probe && id >= vertexCount) return;

    const float halfWidth = faceParams.x;
    const float R = faceParams.y;
    const float camAltitude = faceParams.z;

    // Position on the face plane, and the mesh cell size there.
    float2 xy;
    float cellSize;
    if (probe || id < faceVertexCount)
    {
        xy = (float2(id % (n + 1), id / (n + 1)) / n * 2.0 - 1.0) * halfWidth;
        cellSize = 2.0 * halfWidth / n;
    }
    else
    {
        const uint ring = (id - faceVertexCount) / (4 * n) + 1;
        const float ringHalfWidth = halfWidth * pow(ringParams.y, (float)ring);
        xy = BorderPoint((id - faceVertexCount) % (4 * n), n) * ringHalfWidth;
        cellSize = 2.0 * ringHalfWidth / n;
    }
    xy = probe ? camPlane.xy * (R / (R + camAltitude)) : MeshPlanePoint(xy);

    // Normalised onto the sphere.
    float3 d;
    float r2, L;
    PlanePoint(xy, R, d, r2, L);

    // Culling: a vertex that cannot be on screen gets no terrain, and a NaN position so that the
    // rasteriser drops its triangles. The dedicated nadir sample always gives the ground height.
    // The margin keeps the normal and spline stencils and the vertices that cast shadows on screen.
    const uint centreVertex = (n / 2) * (n + 1) + n / 2;
    if (!probe && id != centreVertex)
    {
        const float3 low = RelativePosition(d, r2, L, R, camAltitude, TERRAIN_MIN_HEIGHT);
        const float3 high = RelativePosition(d, r2, L, R, camAltitude, TERRAIN_MAX_HEIGHT);
        const float waves = waveAxisX.w * (1.0 - smoothstep(32.0, 64.0, cellSize));
        const float margin = 6.0 * cellSize + waves;
        float coverMargin = margin;
#ifndef AIRLESS_SURFACE
        // Keep the 60 m material probes and their bilinear support around the view, independent of the sun.
        coverMargin = SHORE_BASELINE + 3.0 * cellSize + waves;
#endif
        if (!MaybeVisible(low, high, ShadowSweep(d), margin)
            && (coverMargin <= margin || !MaybeVisible(low, high, 0.0, coverMargin)))
        {
            FaceVertex hidden = (FaceVertex)0;
            hidden.pos = asfloat(0x7fc00000u).xxx;
            outVerts[id] = hidden;
            return;
        }
    }
#ifdef LATTICE_PAIRS
    // These two samples are left to the exact shader dispatched next (D3DApp::Draw).
    if (probe || id == centreVertex)
    {
        FaceVertex none = (FaceVertex)0;
        none.pos = asfloat(0x7fc00000u).xxx;
        outVerts[id] = none;
        return;
    }
#endif
    // The mesh is the previous frame's (D3DApp::Draw, camPlane.z): a vertex computed then has the same terrain.
    if (camPlane.z > 0.0 && (asuint(outVerts[id].pos.x) & 0x7fffffffu) <= 0x7f800000u)
        return;

    // Octave filtering: the cell size on the unit sphere (tangential, the largest) bounds the noise frequency.
    gMaxFrequency = L / (MESH_BAND_LIMIT * cellSize);
    gCreaseMaxFrequency = L / (MESH_BAND_LIMIT * max(cellSize, CREASE_MIN_CELL));
    gExactLattice = cellSize < EXACT_LATTICE_MAX_CELL;
#ifdef LATTICE_PAIRS
    gLatticePairs = true; // in a flight (TerrainComputePairs.hlsl), the split in pairs of floats
#endif
    // Under a full screen relief the mesh gives only depth, the silhouette and the sun's horizon: its rivers come from
    // the rivers' map, the rung above its own footprint (Erosion.hlsli, ErosionRiverMapShare).
    // Cells of a quarter of the map's and wider: finer ones still cast the valleys' shadows seen from 250 km.
    [branch] if (screenRelief.z >= 1.0 && ErosionRiverMapReady() && cellSize >= 0.25 * ErosionRiverMapCell())
        gRiverCellKm = 0.0015 * ErosionRiverMapCell();

    FaceVertex v;
    v.elevation = TerrainAt(xy, R, camAltitude, v.dir, v.pos);
    v.water = float4(gWaterFlow, gWaterLevel);
    v.waterDistance = gWaterDistance;
    v.waterDepth = gWaterDepth, v.waterCoverage = gWaterCoverage;
    v.roughness = gRoughness;
    v.volcanic = gVolcanic;
#ifdef AIRLESS_SURFACE
    v.volcanic = gAirlessAlbedo; // the profile's material scalar in the shared vertex layout
#endif
    v.horizon = -1.5707964; // the horizon pass's (Horizon.hlsl)
    v.shadow = 0.0;
    outVerts[id] = v;
}
