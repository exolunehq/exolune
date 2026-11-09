// The fine grid (docs/spec-rendu-lointain.md, step 2): the face of the mesh cut ringParams.w times finer,
// recomputed every frame like the mesh, for the pixels' normals only. It carries the true relief finer than
// the mesh's cells, so that nothing mutates as the mesh refines on the way down. No rings, no geometry.
#define EROSION_WAVE_LIST // neighbouring samples list their rivers' nodes together (Erosion.hlsli)
#include "Planet.hlsli"
#include "Relief.hlsli"
#include "Terrain.hlsli"

RWStructuredBuffer<FineSample> outFine : register(u0); // position/elevation and the same evaluation's inland water

// Under a full screen relief, a pixel reads this grid only where one of its 4 x 4 screen texels misses the sea-level
// sphere (PixelShader.hlsl, ScreenNormal): near the limb. The band holds those texels (about 5 pixels, 8 kept), the
// samples the pixel's B-spline and FineNormals' differences read (3 cells, 4 kept), and the column up to the summits.
bool FineNearLimb(float3 d, float r2, float L, float R, float camAltitude, float cellSize)
{
    const float3 centre = -float3(camPlane.xy, R + camAltitude); // the planet's centre, camera-relative
    const float D = length(centre);
    const float limb = asin(min(R / D, 1.0));
    [unroll] for (int k = 0; k < 2; ++k)
    {
        const float3 p = RelativePosition(d, r2, L, R, camAltitude, k == 0 ? 0.0 : MAX_TERRAIN_HEIGHT);
        const float distance = length(p);
        const float angle = acos(clamp(dot(p, centre) / (distance * D), -1.0, 1.0));
        if (angle >= limb - 8.0 * taa.w - 4.0 * cellSize / distance)
            return true;
    }
    return false;
}

// The footprint (m) of the screen relief's texel at the sample, as PlaneHit measures it: its angle at the sample's
// distance, stretched by the incidence. Only limb pixels read the sample then; its rivers are filtered at it.
float FineLimbFootprint(float3 d, float r2, float L, float R, float camAltitude)
{
    const float3 p = RelativePosition(d, r2, L, R, camAltitude, 0.0);
    const float t = length(p);
    const float3 up = normalize(p + float3(camPlane.xy, R + camAltitude)); // from the planet's centre
    return t * taa.w * screenRelief.w / max(-dot(p, up) / t, 0.1);
}

// By 8 x 8 tiles of samples: a wave's samples are neighbours on both axes, and list their rivers' nodes together.
[numthreads(8, 8, 1)]
void CSMain(uint3 threadId : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64); // before any return: every thread must reach the barrier
    const uint n = (uint)(faceParams.w * ringParams.w);
    const uint id = threadId.y * (n + 1) + threadId.x;
    if (threadId.x > n || threadId.y > n)
        return;
    const float halfWidth = faceParams.x, R = faceParams.y, camAltitude = faceParams.z;
    const float2 xy = (float2(id % (n + 1), id / (n + 1)) / n * 2.0 - 1.0) * halfWidth;
    const float cellSize = 2.0 * halfWidth / n;

    float3 d;
    float r2, L;
    PlanePoint(xy, R, d, r2, L);
    FineSample missing = (FineSample)0;
    missing.terrain = asfloat(0x7fc00000u).xxxx; // NaN: off screen
    // Its margin: the samples a visible pixel reads, its B-spline's 4 x 4 and FineNormals' differences, 3 cells, and as many
    // again; the mesh's 6 cells cover its shadows' vertices too (TerrainCompute.hlsl), none of which read this grid.
    if (!MaybeVisible(RelativePosition(d, r2, L, R, camAltitude, 0.0),
                      RelativePosition(d, r2, L, R, camAltitude, MAX_TERRAIN_HEIGHT), 0.0, 6.0 * cellSize))
    {
        outFine[id] = missing;
        return;
    }
    // The mesh is the previous frame's (D3DApp::Draw, camPlane.z): a point computed then has the same terrain.
    if (camPlane.z > 0.0 && (asuint(outFine[id].terrain.x) & 0x7fffffffu) <= 0x7f800000u)
        return;
    // erosionMode.y: the screen relief covers every pixel at full weight (D3DApp::Draw).
    if (erosionMode.y != 0u)
    {
        if (!FineNearLimb(d, r2, L, R, camAltitude, cellSize))
        {
            outFine[id] = missing;
            return;
        }
        // The rivers at the reading texel's footprint, as the screen relief's (ScreenBandwidth): 2 footprints.
        gRiverCellKm = 0.002 * FineLimbFootprint(d, r2, L, R, camAltitude);
    }
    gMaxFrequency = L / (MESH_BAND_LIMIT * cellSize);
    gCreaseMaxFrequency = L / (MESH_BAND_LIMIT * max(cellSize, CREASE_MIN_CELL));
    gExactLattice = cellSize < EXACT_LATTICE_MAX_CELL;
    // The wet nodes whose channels pass near the sample, for the pixel contour (Erosion.hlsli, ErosionRiversNear): within
    // its cell from the pixel, the pixel's own footprint and the meanders' octaves finer than the sample's.
    gErosionNearReach = 3.5 * cellSize + 50.0;
    gErosionNear = EROSION_NEAR_UNKNOWN;
    float3 dir, pos;
    const float elevation = TerrainAt(xy, R, camAltitude, dir, pos);
    FineSample sample;
    sample.terrain = float4(pos, elevation);
    sample.inland = float4(InlandSample(gWaterLevel, gWaterDepth, gWaterCoverage), gWaterDistance);
    // Bit 7 of the near word: no terminal lake within the pixels' reach of the sample, a fine cell and a half; it spares
    // them the lake's lookups (PixelShader.hlsl, lakeFree).
    const bool lakeFree = ErosionLakeFree(dir.x * faceX.xyz + dir.y * faceY.xyz + dir.z * faceZ.xyz, 1.5 * cellSize);
    sample.flow = float4(sample.inland.x * gWaterFlow, asfloat(gErosionNear | (lakeFree ? 0x80u : 0u)));
    outFine[id] = sample;
}
