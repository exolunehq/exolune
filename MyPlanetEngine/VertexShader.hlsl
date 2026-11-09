#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Mesh.hlsli"
#include "Materials.hlsli"
#include "OceanSurface.hlsli"

StructuredBuffer<FaceVertex> verts : register(t0);

// Position of a neighbour, or of the vertex itself when culling dropped the neighbour (NaN position).
float3 NeighbourPosition(uint id, float3 self)
{
    const float3 p = verts[id].pos;
    return (asuint(p.x) & 0x7fffffffu) > 0x7f800000u ? self : p; // isnan, which the compiler cannot drop
}

// The mesh's surface at the face-plane point xy (m), bilinear between the four vertices around it; false beyond the
// rings or next to a culled vertex.
bool MeshSurface(float2 xy, out float3 p)
{
    uint4 ids;
    float2 t;
    p = 0.0;
    if (!MeshCell(xy, ids, t))
        return false;
    const float3 a = verts[ids.x].pos, b = verts[ids.y].pos, c = verts[ids.z].pos, d = verts[ids.w].pos;
    if ((asuint(a.x) & 0x7fffffffu) > 0x7f800000u || (asuint(b.x) & 0x7fffffffu) > 0x7f800000u
        || (asuint(c.x) & 0x7fffffffu) > 0x7f800000u || (asuint(d.x) & 0x7fffffffu) > 0x7f800000u)
        return false;
    p = lerp(lerp(a, b, t.x), lerp(c, d, t.x), t.y);
    return true;
}

PSInput VSMain(uint id : SV_VertexID)
{
    const FaceVertex v = verts[id];
    const uint n = (uint)faceParams.w;
    const uint ringCount = (uint)ringParams.x;
    const uint faceCount = (n + 1) * (n + 1);

    // The four neighbours, two along each mesh direction: along the row and the column on the face; along
    // the ring and from one ring to the next. A missing neighbour (outermost ring) is the vertex itself.
    float cellSize;
    const uint4 nb = MeshNeighbours(id, cellSize); // x, y: one direction; z, w: the other
    float3 chart; // spline normals: the vertex in its chart of the mesh
    float corner = n;
    if (id < faceCount)
        chart = float3(id % (n + 1), id / (n + 1), 0.0);
    else
    {
        const uint ring = (id - faceCount) / (4 * n) + 1, b = (id - faceCount) % (4 * n);
        chart = float3(b, ring, 1.0);
        corner = min(b % n, n - b % n);
    }

    // Normal by centred differences over two cells: the slope finer than that is what flickered when the
    // vertices slide (docs/log/spec-stabilite.md). It also matches the drawn geometry.
    const float3 normal = cross(NeighbourPosition(nb.y, v.pos) - NeighbourPosition(nb.x, v.pos),
                                NeighbourPosition(nb.w, v.pos) - NeighbourPosition(nb.z, v.pos));
    const float length2 = dot(normal, normal);
    float3 unit = length2 > 0.0 ? normal * rsqrt(length2) : v.dir;
    if (dot(unit, v.dir) < 0.0)
        unit = -unit;

    // Both fixed baselines use the vertex's coordinates on the face plane.
    const float2 xy = id < faceCount ? (float2(id % (n + 1), id / (n + 1)) / n * 2.0 - 1.0) * faceParams.x
                    : BorderPoint((id - faceCount) % (4 * n), n) * faceParams.x * pow(ringParams.y, (float)((id - faceCount) / (4 * n) + 1));

    // The materials' normal (docs/principes.md, the decisions see the relief's forms at any height): across
    // DECISION_BASELINE either way where the cells are finer, read on the mesh's surface; the vertices' own elsewhere.
    float3 decision = unit;
    if (cellSize < DECISION_BASELINE)
    {
        float3 px, mx, py, my; // the surface DECISION_BASELINE away along the face plane's x and y, each way
        if (MeshSurface(xy + float2(DECISION_BASELINE, 0.0), px) && MeshSurface(xy - float2(DECISION_BASELINE, 0.0), mx)
            && MeshSurface(xy + float2(0.0, DECISION_BASELINE), py) && MeshSurface(xy - float2(0.0, DECISION_BASELINE), my))
        {
            const float3 across = cross(px - mx, py - my);
            const float length2 = dot(across, across);
            if (length2 > 0.0)
                decision = across * rsqrt(length2) * (dot(across, v.dir) < 0.0 ? -1.0 : 1.0);
        }
    }

    // The shore's normal follows the beach's scale: across SHORE_BASELINE either way where the cells are finer,
    // read on the mesh's surface; the vertices' own elsewhere, or when a surface point is missing.
    float3 shore = unit;
    if (cellSize < SHORE_BASELINE)
    {
        float3 px, mx, py, my; // the surface SHORE_BASELINE away along the face plane's x and y, each way
        if (MeshSurface(xy + float2(SHORE_BASELINE, 0.0), px) && MeshSurface(xy - float2(SHORE_BASELINE, 0.0), mx)
            && MeshSurface(xy + float2(0.0, SHORE_BASELINE), py) && MeshSurface(xy - float2(0.0, SHORE_BASELINE), my))
        {
            const float3 across = cross(px - mx, py - my);
            const float length2 = dot(across, across);
            if (length2 > 0.0)
                shore = across * rsqrt(length2) * (dot(across, v.dir) < 0.0 ? -1.0 : 1.0);
        }
    }

    const float2 rest=float2(dot(v.pos,waveAxisX.xyz),dot(v.pos,waveAxisY.xyz));
    float3 displacement=0.0;
    if(v.elevation<0.0 && v.water.w<=0.0) displacement=OceanGeometry(rest,cellSize,v.elevation);
    float3 horizontal=waveAxisX.xyz*displacement.x+waveAxisY.xyz*displacement.z;
    horizontal-=dot(horizontal,v.dir)*v.dir;
    float3 renderPos=v.pos+v.dir*displacement.y+horizontal;
    PSInput output;
    output.position = mul(float4(renderPos, 1.0), viewProj);
    output.pos = renderPos;
    output.seaParam=rest;
    output.seaHeight=displacement.y;
    output.dir = v.dir;
    output.elevation = v.elevation;
    output.water = v.water;
    output.inland = float4(InlandSample(v.water.w, v.waterDepth, v.waterCoverage), v.waterDistance);
    output.water.xyz *= output.inland.x;
    output.normal = unit;
    output.decision = decision;
    output.shore = shore;
    output.cellSize = cellSize;
    output.chart = chart;
    output.corner = corner;
    output.slopeSpread = SlopeSpread(v.roughness, cellSize);
    // The rock's kind by region, filtered by the cell: per pixel, the families' partition of its 5 to 40 km octaves
    // drew round patches of granite, basalt and sandstone all over the planet seen from orbit (docs/spec-texturage-
    // universel.md). The strata and lenses, whose finer octaves made the beds slide, are the pixels' (PixelShader.hlsl).
    const float3 q = detailOrigin.xyz + v.pos.x * faceX.xyz + v.pos.y * faceY.xyz + v.pos.z * faceZ.xyz;
    // On fresh volcanic ground, basalt, the palette's darkest rock (Materials.hlsli, RockColor).
    output.geology = float4(Geology(q, cellSize), v.volcanic);
    output.geology.x = lerp(output.geology.x, -0.6, v.volcanic);
    output.horizon = v.horizon;
    return output;
}
