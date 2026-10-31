// Mesh.hlsli - the sliding mesh's layout (docs/log/spec-champ-de-vision.md): the face, then the rings. Shared by
// the vertex shader, the horizon pass, and the atmosphere. Needs Planet.hlsli.
#ifndef MESH_HLSLI
#define MESH_HLSLI

// Point number b of the border of the square [-1, 1]^2 cut in n cells per side, going round:
// bottom, right, top, left.
float2 BorderPoint(uint b, uint n)
{
    const uint side = b / n;
    const float t = (float)(b % n) / n * 2.0 - 1.0;
    return side == 0 ? float2(t, -1.0)
         : side == 1 ? float2(1.0, t)
         : side == 2 ? float2(-t, 1.0)
         :             float2(-1.0, -t);
}

// Vertex number b of the face's border, going round like the rings: bottom, right, top, left.
// Same as FaceBorderVertex in D3DApp.cpp.
uint FaceBorderVertex(uint b, uint n)
{
    const uint side = b / n, t = b % n;
    const uint i = side == 0 ? t : side == 1 ? n : side == 2 ? n - t : 0;
    const uint j = side == 0 ? 0 : side == 1 ? t : side == 2 ? n : n - t;
    return j * (n + 1) + i;
}

// Border number of the face vertex (i, j), which lies on the border: the inverse of FaceBorderVertex.
uint BorderNumber(uint i, uint j, uint n)
{
    return j == 0 && i < n ? i : i == n && j < n ? n + j : j == n && i > 0 ? 3 * n - i : 4 * n - j;
}

// Vertex number b of ring number ring, the face's border being ring 0.
uint RingVertex(uint ring, uint b, uint n)
{
    b %= 4 * n;
    return ring == 0 ? FaceBorderVertex(b, n) : (n + 1) * (n + 1) + (ring - 1) * 4 * n + b;
}

// The four vertices around the face-plane point xy (m) and its bilinear weights between them, on the face or on the
// rings' chart (TerrainCompute.hlsl): x, y along the row; z, w the next row. False beyond the outermost ring.
bool MeshCell(float2 xy, out uint4 ids, out float2 t)
{
    const uint n = (uint)faceParams.w;
    const float halfWidth = faceParams.x, s = max(abs(xy.x), abs(xy.y));
    ids = 0;
    t = 0.0;
    if (s <= halfWidth)
    {
        const float2 f = (xy / halfWidth + 1.0) * (0.5 * n);
        const uint2 c = (uint2)clamp(floor(f), 0.0, n - 1.0);
        t = f - c;
        const uint i = c.y * (n + 1) + c.x;
        ids = uint4(i, i + 1, i + n + 1, i + n + 2);
        return true;
    }
    const float ring = log2(s / halfWidth) / log2(ringParams.y); // 0 on the face's border
    if (ring >= ringParams.x)
        return false;
    // Along the square's border, as BorderPoint goes round: bottom, right, top, left.
    const float b = 0.5 * n * (-xy.y >= abs(xy.x) ? 1.0 + xy.x / s
                             : xy.x >= abs(xy.y)  ? 3.0 + xy.y / s
                             : xy.y >= abs(xy.x)  ? 5.0 - xy.x / s
                             :                      7.0 - xy.y / s);
    const uint r = (uint)ring, k = (uint)b;
    t = float2(b - k, ring - r);
    ids = uint4(RingVertex(r, k, n), RingVertex(r, k + 1, n), RingVertex(r + 1, k, n), RingVertex(r + 1, k + 1, n));
    return true;
}

float Bilinear(float4 v, float2 t)
{
    return lerp(lerp(v.x, v.y, t.x), lerp(v.z, v.w, t.x), t.y);
}

// The four neighbours of vertex id, two along each mesh direction: along the row and the column on the face;
// along the ring and from one ring to the next. A missing neighbour (outermost ring) is the vertex itself.
// x, y: one direction; z, w: the other. cellSize: the mesh cell there (m).
uint4 MeshNeighbours(uint id, out float cellSize)
{
    const uint n = (uint)faceParams.w;
    const uint ringCount = (uint)ringParams.x;
    const uint faceCount = (n + 1) * (n + 1);
    if (id < faceCount)
    {
        const uint i = id % (n + 1), j = id / (n + 1);
        const uint outward = ringCount > 0 ? RingVertex(1, BorderNumber(i, j, n), n) : id;
        cellSize = 2.0 * faceParams.x / n;
        return uint4(i > 0 ? id - 1 : outward, i < n ? id + 1 : outward,
                     j > 0 ? id - (n + 1) : outward, j < n ? id + (n + 1) : outward);
    }
    const uint ring = (id - faceCount) / (4 * n) + 1, b = (id - faceCount) % (4 * n);
    cellSize = 2.0 * faceParams.x * exp2(ring * log2(ringParams.y)) / n;
    return uint4(RingVertex(ring, b + 4 * n - 1, n), RingVertex(ring, b + 1, n),
                 RingVertex(ring - 1, b, n), ring < ringCount ? RingVertex(ring + 1, b, n) : id);
}

#endif
