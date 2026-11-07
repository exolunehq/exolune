// The terrain mesh, recomputed every frame: a cube face that faces the camera, surrounded by square
// rings that grow geometrically up to the horizon. Everything lies on the face plane z = R and is
// normalised onto the sphere. See docs/log/spec-champ-de-vision.md.
//
// Vertex layout, matching the index buffer built in D3DApp.cpp:
// - the face: (n + 1) x (n + 1) vertices, row by row;
// - then each ring: 4n vertices around a square, in the same order as the face's border.
#define EROSION_WAVE_LIST // neighbouring samples list their rivers' nodes together (Erosion.hlsli)
#include "Planet.hlsli"
#include "Relief.hlsli"
#include "Terrain.hlsli"
#include "Mesh.hlsli"

RWStructuredBuffer<FaceVertex> outVerts : register(u0);

[numthreads(64, 1, 1)]
void CSMain(uint3 groupId : SV_GroupID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64); // before any return: every thread must reach the barrier
    const uint n = (uint)faceParams.w;
    const uint faceVertexCount = (n + 1) * (n + 1);
    // By 8 x 8 tiles (D3DApp::Draw): the face's grid by squares, its rings by 8 vertices along 8 of them. A wave's
    // vertices are then neighbours on both axes and list their rivers' nodes together (Erosion.hlsli).
    uint id;
    const uint across = (n + 8u) / 8u, faceTiles = across * across, group = groupId.x;
    if (group < faceTiles)
    {
        const uint2 ij = uint2(group % across, group / across) * 8u + uint2(threadInGroup % 8u, threadInGroup / 8u);
        id = any(ij > n) ? 0xffffffffu : ij.y * (n + 1) + ij.x;
    }
    else
    {
        const uint g = group - faceTiles, alongTiles = n / 2u; // 4 n vertices a ring, by 8
        const uint ring = (g / alongTiles) * 8u + threadInGroup / 8u, along = (g % alongTiles) * 8u + threadInGroup % 8u;
        id = ring >= (uint)ringParams.x ? 0xffffffffu : faceVertexCount + ring * 4u * n + along;
    }
    if (id >= faceVertexCount + (uint)ringParams.x * 4 * n) return;

    const float halfWidth = faceParams.x;
    const float R = faceParams.y;
    const float camAltitude = faceParams.z;

    // Position on the face plane, and the mesh cell size there.
    float2 xy;
    float cellSize;
    if (id < faceVertexCount)
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

    // Normalised onto the sphere.
    float3 d;
    float r2, L;
    PlanePoint(xy, R, d, r2, L);

    // Culling: a vertex that cannot be on screen gets no terrain, and a NaN position so that the
    // rasteriser drops its triangles. The vertex under the camera is always computed: it gives the
    // ground height. The margin also keeps the neighbours that visible vertices take their normal from, and
    // those of the spline normals (docs/spec-normales-spline.md). So are the vertices whose
    // shadow can fall on screen (docs/recherche-ombres-relief.md).
    const uint nadirVertex = (n / 2) * (n + 1) + n / 2;
    if (id != nadirVertex
        && !MaybeVisible(RelativePosition(d, r2, L, R, camAltitude, 0.0),
                         RelativePosition(d, r2, L, R, camAltitude, MAX_TERRAIN_HEIGHT), ShadowSweep(d), 6.0 * cellSize + waveAxisX.w * (1.0-smoothstep(32.0,64.0,cellSize))))
    {
        FaceVertex hidden = (FaceVertex)0;
        hidden.pos = asfloat(0x7fc00000u).xxx;
        outVerts[id] = hidden;
        return;
    }
#ifdef LATTICE_PAIRS
    // The vertex under the camera, whose ground places it, is left without terrain to the exact shader, dispatched next
    // with the mesh kept (D3DApp::Draw).
    if (id == nadirVertex)
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
    v.horizon = -1.5707964; // the horizon pass's (Horizon.hlsl)
    v.shadow = 0.0;
    outVerts[id] = v;
}
