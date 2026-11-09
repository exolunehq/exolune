// The face's cells in two lists for the terrain's colour (D3DApp::Draw): those where a pixel may refine its water contour,
// drawn with the whole pixel shader, the others with its permutation without the contour (PixelShaderScreen.hlsl), the
// same image there for less: the contour's code in the shader slowed every pixel, 0.5 ms a frame at 97 km and 1.1 ms at
// 2,200 m, whether it ran or not (docs/diagnostic-orbite.md).
// A cell goes to the whole shader as soon as one value its pixels blend could put them in a contour's band (PixelShader.hlsl,
// refine): the fine grid's samples under its pixels' B-splines, and where that grid does not weigh fully, its corners'
// water and the spline's 4 x 4 vertices' heights. Blends of values never leave their range: the test is conservative, the
// image the same.
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"

StructuredBuffer<FaceVertex> verts : register(t0);  // the mesh as drawn
StructuredBuffer<FineSample> fine : register(t1);   // the fine grid as the pixels read it (FineNormals.hlsl)
RWByteAddressBuffer lists : register(u0);           // the whole shader's cells' indices, then from 6 n^2 the others'
RWByteAddressBuffer args : register(u1);            // their two indexed draws' arguments, 20 bytes each

// ElevationSpread of SlopeSpread (Materials.hlsli) per roughness and metre of cell, at most: 0.37 x OCTAVE_SLOPE.
static const float SPREAD_SLOPE = 0.37 * 0.16;

// Whether one of the cell (i, j)'s pixels may refine (PixelShader.hlsl): a river's band, a mixed shore, the coast's band.
bool MayRefine(uint i, uint j, uint n)
{
    const uint sub = (uint)ringParams.w, cells = n * sub;
    const float faceCell = 2.0 * faceParams.x / n, fineCell = faceCell / sub;
    float wLo = 1e30, wHi = -1e30, xLo = 1e30, xHi = -1e30, eLo = 1e30, eHi = -1e30, rough = 0.0, step = 0.0, bend = 0.0;
    // The fine grid's samples under the pixels' B-splines (PixelShader.hlsl, FineNormal): 4 n - 1 to 4 n + 6 each way.
    bool complete = ringParams.z > 0.0;
    [branch] if (ringParams.z > 0.0)
    {
        const int x0 = (int)(sub * i) - 1, y0 = (int)(sub * j) - 1;
        float above[8], above2[8];
        [unroll] for (int k = 0; k < 8; ++k)
            above[k] = above2[k] = asfloat(0x7fc00000u);
        [loop] for (int y = 0; y < 8; ++y)
        {
            float left = asfloat(0x7fc00000u), left2 = asfloat(0x7fc00000u);
            [unroll] for (int x = 0; x < 8; ++x)
            {
                const uint2 at = (uint2)clamp(int2(x0 + x, y0 + y), 0, (int)cells);
                const uint id = at.y * (cells + 1) + at.x;
                const float4 terrain = fine[id].terrain;
                float e = asfloat(0x7fc00000u);
                [branch] if (dot(terrain.xyz, terrain.xyz) > 0.0)
                {
                    const float4 inland = fine[id].inland;
                    e = terrain.w;
                    wLo = min(wLo, inland.w), wHi = max(wHi, inland.w);
                    xLo = min(xLo, inland.x), xHi = max(xHi, inland.x);
                    eLo = min(eLo, e), eHi = max(eHi, e);
                    if (!isnan(left)) step = max(step, abs(e - left));
                    if (!isnan(above[x])) step = max(step, abs(e - above[x]));
                    if (!isnan(left) && !isnan(left2)) bend = max(bend, abs(e - 2.0 * left + left2));
                    if (!isnan(above[x]) && !isnan(above2[x])) bend = max(bend, abs(e - 2.0 * above[x] + above2[x]));
                }
                else
                    complete = false; // off screen: no B-spline, maybe no weight
                left2 = left, left = e;
                above2[x] = above[x], above[x] = e;
            }
        }
    }
    // The samples' size (PixelShader.hlsl, sampleCell): the fine grid's at its full weight, past the face's 8 cells of
    // fading and with every sample there; the mesh's otherwise, the wider, and so the wider band.
    const bool inner = i >= 8u && j >= 8u && i + 9u <= n && j + 9u <= n;
    // There, at a full weight, the pixels' water and heights are the fine grid's alone (fineWeight 1): the mesh's,
    // interpolated over cells 4 times wider, do not reach them. Its roughness still spreads the heights.
    const bool fineOnly = complete && inner && ringParams.z >= 1.0;
    // The triangles' interpolants: the corners' water.
    [unroll] for (uint c = 0; c < 4; ++c)
    {
        const FaceVertex v = verts[(j + c / 2) * (n + 1) + i + c % 2];
        rough = max(rough, v.roughness);
        [branch] if (!fineOnly)
        {
            const float x = InlandSample(v.water.w, v.waterDepth, v.waterCoverage).x;
            wLo = min(wLo, v.waterDistance), wHi = max(wHi, v.waterDistance);
            xLo = min(xLo, x), xHi = max(xHi, x);
        }
    }
    const float sampleCell = faceCell / lerp(1.0, (float)sub, complete && inner ? ringParams.z : 0.0);
    // A river's band: its edge's candidate distance within three band scales of a sample.
    const bool rivers = EROSION_RAVINES && EROSION_RIVERS && erosionMode.x >= 2u;
    // Wider samples, a narrower band in samples (CONTOUR_CHANNEL_BAND), but a wider band in metres: the widest sample bounds it.
    const float band = 3.0 * (rivers ? lerp(CONTOUR_CHANNEL_BAND.x, CONTOUR_CHANNEL_BAND.z,
                                            smoothstep(CONTOUR_CHANNEL_BAND.y, CONTOUR_CHANNEL_BAND.w, sampleCell)) : 1.0) * sampleCell;
    // The spline's heights, the 4 x 4 vertices around the cell (SplineNormal), their steps counted per fine cell.
    [branch] if (!fineOnly)
        [unroll] for (int b = -1; b <= 2; ++b)
            [unroll] for (int a = -1; a <= 2; ++a)
            {
                const uint2 at = (uint2)clamp(int2(i, j) + int2(a, b), 0, (int)n);
                const float e = verts[at.y * (n + 1) + at.x].elevation;
                const float ex = verts[at.y * (n + 1) + min(at.x + 1, n)].elevation;
                const float ey = verts[min(at.y + 1, n) * (n + 1) + at.x].elevation;
                eLo = min(eLo, e), eHi = max(eHi, e);
                step = max(step, max(abs(ex - e), abs(ey - e)) / sub);
            }
    if (!(wLo >= band) && !(wHi <= -band))
        return true;
    // A shore's mixed samples: partly wet, or wet and dry.
    if (xHi > 0.0 && xLo < 1.0)
        return true;
    // The coast's band: three height bands about the sea; a band at most the heights' spread or what the grid cannot place
    // (PixelShader.hlsl, heightBand): a sample's step per sample (twice, for the blends' weights and the diagonals) blended
    // with twice the fine grid's uncertainty, its B-spline against its bilinear, at most a third of the samples' second
    // differences (taken whole); plus 2 % of a sample and 2 m.
    const float spread = SPREAD_SLOPE * rough * faceCell;
    const float slopeBand = 2.0 * step * sampleCell / fineCell, placed = 2.0 * bend;
    const float band2 = complete && inner ? lerp(slopeBand, placed, ringParams.z) : max(slopeBand, placed);
    const float heightBand = max(spread, band2) + 0.02 * sampleCell + 2.0;
    return eLo < 3.0 * heightBand && eHi > -3.0 * heightBand;
}

[numthreads(64, 1, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    const uint n = (uint)faceParams.w;
    const bool active = id.x < n * n;
    const uint i = id.x % n, j = id.x / n;
    // Under any screen relief, every cell: the screen's texels hold the contour, the cells do not decide it.
    bool whole = false;
    [branch] if (active)
    {
        whole = true;
        [branch] if (screenRelief.z <= 0.0)
            whole = MayRefine(i, j, n);
    }
    const bool other = active && !whole;
    // One reservation per wave and list.
    const uint wholeCount = WaveActiveCountBits(whole), otherCount = WaveActiveCountBits(other);
    const uint wholeRank = WavePrefixCountBits(whole), otherRank = WavePrefixCountBits(other);
    uint wholeBase = 0u, otherBase = 0u;
    if (WaveIsFirstLane())
    {
        if (wholeCount > 0u) args.InterlockedAdd(0, 6u * wholeCount, wholeBase);
        if (otherCount > 0u) args.InterlockedAdd(20, 6u * otherCount, otherBase);
    }
    wholeBase = WaveReadLaneFirst(wholeBase), otherBase = WaveReadLaneFirst(otherBase);
    if (!active)
        return;
    // The cell's two triangles, as the mesh's index buffer has them (D3DApp: v0, v2, v1, v2, v3, v1).
    const uint v0 = j * (n + 1) + i, v1 = v0 + 1, v2 = v0 + n + 1, v3 = v2 + 1;
    const uint at = whole ? wholeBase + 6u * wholeRank : 6u * n * n + otherBase + 6u * otherRank;
    lists.Store3(4u * at, uint3(v0, v2, v1));
    lists.Store3(4u * (at + 3u), uint3(v2, v3, v1));
}
