// The one march toward the sun at each visible vertex (Shadows.hlsli), into the vertices the terrain pass has just
// written: the terrain's horizon, and its column's shadow height. The pixels interpolate the horizon and take the
// sun's share above it: interpolated as an angle, the shadow's edge falls between the vertices, as sharp as the sun's
// disc and the pixel allow (docs/recherche-ombres-relief.md). The atmosphere reads the shadow height between the
// vertices: the air below it scatters only the sky's light (docs/recherche-rayons.md).
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Relief.hlsli" // for Terrain.hlsli, not called
#include "Terrain.hlsli"
#include "Mesh.hlsli"
#include "Materials.hlsli"
#define SHADOW_MESH RWStructuredBuffer<FaceVertex>
#include "Shadows.hlsli"

RWStructuredBuffer<FaceVertex> verts : register(u0); // the terrain pass's output: the march reads its elevations

[numthreads(64, 1, 1)]
void CSMain(uint3 threadId : SV_DispatchThreadID)
{
    const uint id = threadId.x;
    const uint n = (uint)faceParams.w;
    if (id >= (n + 1) * (n + 1) + (uint)ringParams.x * 4 * n)
        return;
    const FaceVertex v = verts[id];
    if ((asuint(v.pos.x) & 0x7fffffffu) > 0x7f800000u) // culled (NaN)
        return;
    // The vertices kept only for their shadow need no horizon: the terrain pass's, written again where it kept a vertex
    // from the last frame. The others hold every column of air the camera sees below the highest summit: MaybeVisible
    // keeps a column from the sea to MAX_TERRAIN_HEIGHT.
    const float R = faceParams.y, camAltitude = faceParams.z;
    const float2 xy = v.dir.xy * (R / v.dir.z);
    float cellSize;
    MeshNeighbours(id, cellSize);
    float3 d;
    float r2, L;
    PlanePoint(xy, R, d, r2, L);
    if (!MaybeVisible(RelativePosition(d, r2, L, R, camAltitude, 0.0),
                      RelativePosition(d, r2, L, R, camAltitude, MAX_TERRAIN_HEIGHT), 0.0, 6.0 * cellSize))
    {
        verts[id].horizon = -1.5707964; // as TerrainCompute.hlsl leaves it
        verts[id].shadow = 0.0;
        return;
    }
    float shadow;
    verts[id].horizon = SunHorizon(verts, xy, v.pos, v.dir, max(v.elevation, 0.0), shadow);
    verts[id].shadow = shadow;
}
