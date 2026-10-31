// Objects near the camera (docs/spec-objets-proximite.md): each frame, the lattice cells around the camera, one octave
// of sizes per lattice level and class, stones then tufts, decide their object afresh, the same every frame. An
// object's place, size and shape come from its cell of the planet's lattice alone, never from the mesh nor the camera; the camera only decides whether it
// is seen, and its fade. Its foot lies on the exact ground, the relief without any filtering, which the sliding
// mesh draws more or less closely: the gap between the two is measured here.
//
// Two passes: a light one over every cell keeps the candidates that may be seen (CullMain, compiled from
// ObjectCandidates.hlsl), a heavy one evaluates them (CSMain).
//
// The lattice: the planet frame's Cartesian grid. The ground where the vertical's largest component is along axis a
// takes its objects from the grid of the two other axes, projected along a onto the sphere: no seam, nothing that
// moves, each cell of s x s covering s^2 / |up.a| of the ground.
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Relief.hlsli"
#include "Terrain.hlsli"
#include "Mesh.hlsli"
#include "Materials.hlsli"
#include "Objects.hlsli"
#include "Vegetation.hlsli"
#include "Shadows.hlsli"

StructuredBuffer<FaceVertex> mesh : register(t0);         // the mesh as drawn
RWStructuredBuffer<ObjectInstance> instances : register(u0);
RWByteAddressBuffer counters : register(u1);              // the indirect draw's arguments, then the measures

cbuffer Placement : register(b1)
{
    uint2 camX, camY, camZ;    // the camera, planet frame (m), doubles
    uint2 footX, footY, footZ; // its foot on the sphere of radius R
    float pixelAngle;          // one pixel's angle on screen (rad)
    uint  flags;               // 1: objects pop at their size instead of growing (the pop measure's reference);
                               // 2: the census, every cell recorded, kept or not, the camera's say left out (tools/banc_objets.py)
    uint  planeCount;
    uint  sliceBase;           // the first pass: this dispatch's first slice, stones and tufts, then the plants' apart
    int4  planes[3];           // x: axis, y: its sign, zw: the camera's cell of FINEST_CELL m
};

// Counters, in uints: the stones' draw's arguments (instance count at 1), the measures (D3DApp::ObjectStat), then the
// tufts' draw's arguments from TUFT_ARGUMENTS; the plants' measures.
static const uint COUNT_PLACED = 5, COUNT_MEASURED = 6, GAP_SUM = 7, GAP_BELOW = 8, GAP_ABOVE = 9, FLOAT_RATIO = 10,
                  COUNT_FLOATING = 11, COUNT_EVALUATED = 12, SINK_RATIO = 13, GAP_PIXELS = 14, COUNT_TUFTS = 15,
                  TUFT_ARGUMENTS = 16, PLANT_FLOATING = 27, PLANT_GAP = 28;
// D3DApp::ObjectCandidates; the census writes one record per candidate, from the start.
static const uint CANDIDATES = 262144;
static const int WINDOW = 224; // cells per side of the tufts' windows, the stones' half; D3DApp::ObjectWindow must match
// The plants' windows, in tiles of the octave's smallest height: trees keep their volume down to 5 pixels.
// D3DApp::PlanetPlantWindow.
static const int PLANET_PLANT_WINDOW = 512;

static const double INV_R = 1.0L / 6378000.0L; // 1 / D3DApp::PlanetRadius, folded by the compiler

double3 Double3(uint2 x, uint2 y, uint2 z)
{
    return double3(asdouble(x.x, x.y), asdouble(y.x, y.y), asdouble(z.x, z.y));
}

double Component(double3 v, int i)
{
    return i == 0 ? v.x : i == 1 ? v.y : v.z;
}

float3 FaceLocal(float3 v)
{
    return float3(dot(v, faceX.xyz), dot(v, faceY.xyz), dot(v, faceZ.xyz));
}

// The mesh's cell at the face-plane point xy (m): the face's, or the ring's there, as wide as it is deep.
float MeshCell(float2 xy)
{
    return 2.0 * max(max(abs(xy.x), abs(xy.y)), faceParams.x) / faceParams.w;
}

// The elevation the mesh draws at the face-plane point xy: the triangle over it, as the index buffer splits the cells
// (D3DApp.cpp), interpolated; max(e, 0) as its vertices are placed. False off the mesh, or by a culled vertex.
bool MeshElevationAt(float2 xy, out float elevation, out float horizon, out float3 normal)
{
    elevation = 0.0;
    horizon = 0.0;
    normal = float3(0.0, 0.0, 1.0);
    const uint n = (uint)faceParams.w;
    const float halfWidth = faceParams.x, side = max(abs(xy.x), abs(xy.y));
    uint3 ids;
    float3 bary;
    if (side <= halfWidth)
    {
        const float2 g = (xy / halfWidth * 0.5 + 0.5) * n;
        const uint2 c = min((uint2)max(floor(g), 0.0), n - 1);
        const float2 t = g - c;
        const uint v0 = c.y * (n + 1) + c.x;
        if (t.x + t.y <= 1.0) // v0, v2, v1
        {
            ids = uint3(v0, v0 + 1, v0 + n + 1);
            bary = float3(1.0 - t.x - t.y, t.x, t.y);
        }
        else // v2, v3, v1
        {
            ids = uint3(v0 + n + 2, v0 + n + 1, v0 + 1);
            bary = float3(t.x + t.y - 1.0, 1.0 - t.x, 1.0 - t.y);
        }
    }
    else
    {
        // Between rings `ring` and `ring` + 1, the face's border being ring 0; along the border as BorderPoint goes.
        const uint ring = (uint)floor(log(side / halfWidth) / log(ringParams.y));
        if (ring + 1 > (uint)ringParams.x)
            return false;
        const float2 u = xy / side;
        const float b = abs(u.y) >= abs(u.x) ? (u.y < 0.0 ? 0.5 * (u.x + 1.0) : 2.0 + 0.5 * (1.0 - u.x))
                                             : (u.x > 0.0 ? 1.0 + 0.5 * (u.y + 1.0) : 3.0 + 0.5 * (1.0 - u.y));
        const uint b0 = min((uint)floor(b * n), 4 * n - 1), b1 = (b0 + 1) % (4 * n);
        const float inner = halfWidth * pow(ringParams.y, (float)ring), outer = halfWidth * pow(ringParams.y, (float)(ring + 1));
        const float2 i0 = BorderPoint(b0, n) * inner, i1 = BorderPoint(b1, n) * inner;
        const float2 o0 = BorderPoint(b0, n) * outer, o1 = BorderPoint(b1, n) * outer;
        // Triangles (inner0, outer0, outer1) and (inner0, outer1, inner1), as D3DApp.cpp joins the rings.
        float2 a = i0, e1 = o0 - i0, e2 = o1 - i0;
        ids = uint3(RingVertex(ring, b0, n), RingVertex(ring + 1, b0, n), RingVertex(ring + 1, b1, n));
        float det = e1.x * e2.y - e1.y * e2.x;
        float2 p = xy - a;
        bary.yz = float2(p.x * e2.y - p.y * e2.x, e1.x * p.y - e1.y * p.x) / det;
        if (bary.y < -1e-4 || bary.z < -1e-4 || bary.y + bary.z > 1.0 + 1e-4)
        {
            e1 = o1 - i0;
            e2 = i1 - i0;
            ids = uint3(RingVertex(ring, b0, n), RingVertex(ring + 1, b1, n), RingVertex(ring, b1, n));
            det = e1.x * e2.y - e1.y * e2.x;
            bary.yz = float2(p.x * e2.y - p.y * e2.x, e1.x * p.y - e1.y * p.x) / det;
        }
        bary.x = 1.0 - bary.y - bary.z;
    }
    float3 corners[3];
    [unroll]
    for (int k = 0; k < 3; ++k)
    {
        const FaceVertex v = mesh[ids[k]];
        if ((asuint(v.pos.x) & 0x7fffffffu) > 0x7f800000u) // culled: NaN
            return false;
        elevation += bary[k] * max(v.elevation, 0.0);
        horizon += bary[k] * v.horizon;
        corners[k] = v.pos;
    }
    normal = normalize(cross(corners[1] - corners[0], corners[2] - corners[0]));
    normal *= normal.z < 0.0 ? -1.0 : 1.0; // up, roughly: the face's z
    return true;
}

// The exact ground, the mesh's own function as its cells shrink under 2 m: every octave, the creases as rounded as at
// CREASE_MIN_CELL, the lattice in double precision.
float ExactElevation(double3 u)
{
    gMaxFrequency = NO_LIMIT;
    gCreaseMaxFrequency = faceParams.y / (MESH_BAND_LIMIT * CREASE_MIN_CELL);
    gExactLattice = true;
    return max(ReliefElevation(u), 0.0);
}

// The lattice's slices: one per class and octave, stones (OBJECT_OCTAVES), tufts (TUFT_OCTAVES), then plants (PLANT_OCTAVES).
static const uint STONES = 0, TUFTS = 1, PLANTS = 2;
static const uint STONE_SLICES = (uint)(OBJECT_OCTAVES.y - OBJECT_OCTAVES.x + 1);
static const uint PLANT_SLICE = STONE_SLICES + (uint)(TUFT_OCTAVES.y - TUFT_OCTAVES.x + 1); // D3DApp::ObjectSlices must match
static const float FINEST_CELL = 4.0 * exp2((float)OBJECT_OCTAVES.x); // the stones' finest cell (m); D3DApp::ObjectFinestCell

uint SliceClass(uint slice) { return slice < STONE_SLICES ? STONES : slice < PLANT_SLICE ? TUFTS : PLANTS; }
int SliceOctave(uint slice)
{
    return slice < STONE_SLICES ? OBJECT_OCTAVES.x + (int)slice
         : slice < PLANT_SLICE ? TUFT_OCTAVES.x + (int)(slice - STONE_SLICES) : PLANT_OCTAVES.x + (int)(slice - PLANT_SLICE);
}
float CellsPerSize(uint kind) { return kind == STONES ? 4.0 : kind == TUFTS ? 2.0 : 0.25; }
int Window(uint kind) { return kind == STONES ? WINDOW / 2 : kind == TUFTS ? WINDOW : PLANET_PLANT_WINDOW; } // cells per side

// A cell's candidate: its place in the cell, its size within the octave, its draw, its looks; its point on the sphere.
struct Candidate
{
    uint kind;                // STONES or TUFTS
    int octave, axis, b, c;   // its octave; the plane's axis and the two others
    float d, cell, size;      // the octave's smallest object, its lattice cell, its own width (m)
    float accept;             // its draw, in [0, 1)
    uint3 looks;              // random bits for its turn, shape and colour
    double3 p;                // its point on the sphere of radius R, planet frame (m)
    float3 up;                // the vertical there, planet frame
    float chance;             // the probability to keep it per unit share of ground covered
    float patches, clumps;    // the patches and clumps there (OBJECT_PATCHES, OBJECT_CLUMPS), their mean over the ground 1
    float stony;              // a stone's: the stoniness field there (OBJECT_STONY)
};

// Where debris lies at all (OBJECT_STONY): the stoniness field, raised by `drive`, what strips the ground of its fines.
float Stoniness(float field, float drive)
{
    return SpreadStep(OBJECT_STONY.x, OBJECT_STONY.y, field + OBJECT_STONY.z * drive, 0.0);
}

// Golombek and Rapp's law: the share of the ground covered by rocks of width d to 2d, for the abundance k.
float GolombekShare(float k, float d)
{
    const float q = 1.79 + 0.152 / max(k, 1e-4);
    return k * (exp(-q * d) - exp(-2.0 * q * d));
}

// The pebbles of sand and bare soil (PEBBLES): the same share in each octave, fading past PEBBLES.y m.
float PebbleShare(float d)
{
    return PEBBLES.x * exp(-d / PEBBLES.y);
}

// The candidate of cell `index` of the plane planes[plane] in `slice`. False outside the plane's own ground, where the
// vertical's largest component is along its axis, or when nothing can be kept there, whatever the ground.
bool MakeCandidate(uint slice, uint plane, int2 index, out Candidate k)
{
    const int4 pl = planes[plane];
    k.kind = SliceClass(slice);
    k.octave = SliceOctave(slice);
    k.axis = pl.x;
    k.b = (pl.x + 1) % 3;
    k.c = (pl.x + 2) % 3;
    k.d = exp2((float)k.octave);
    k.cell = CellsPerSize(k.kind) * k.d;
    const uint seed = (slice + 16u) * 8u + (uint)pl.x * 2u + (pl.y > 0 ? 1u : 0u);
    const uint3 h = Hash(uint3((uint)index.x, (uint)index.y, seed * 0x9E3779B9u));
    k.looks = Hash(h ^ 0x5BD1E995u);
    const float2 jitter = float2(h.xy >> 8) / 16777216.0;
    k.accept = float(h.z >> 8) / 16777216.0;
    k.size = k.d * exp2(float(k.looks.x >> 8) / 16777216.0);

    // From the camera's foot: the in-plane steps, then the step along the axis, solved without subtracting large
    // numbers. Doubles only for sums and products: no double division on the GPU.
    const double3 foot = Double3(footX, footY, footZ);
    const float dB = (float)(((double)index.x + (double)jitter.x) * (double)k.cell - Component(foot, k.b));
    const float dC = (float)(((double)index.y + (double)jitter.y) * (double)k.cell - Component(foot, k.c));
    const float footB = (float)Component(foot, k.b), footC = (float)Component(foot, k.c), footA = (float)Component(foot, k.axis);
    const float lift = -(2.0 * footB + dB) * dB - (2.0 * footC + dC) * dC; // X^2 - X0^2
    float dA = lift / (2.0 * footA);
    dA = lift / (2.0 * footA + dA);
    k.p = foot + (double3)(Axis(k.axis) * dA + Axis(k.b) * dB + Axis(k.c) * dC); // one term per component: exact
    k.up = (float3)(k.p * INV_R);
    const float upA = dot(k.up, Axis(k.axis));
    // Kept with the probability that gives the share it covers: a cell covers (cell / d)^2 d^2 / |up.a| of the ground, an
    // object 1.47 d^2 on average (its width log-uniform over the octave, its footprint 0.68 of the square of its width).
    k.chance = (k.cell / k.d) * (k.cell / k.d) / (1.47 * abs(upA));
    // Its patch and clump: one field at its point on the sphere of radius R, the same for every camera, the stones' and
    // the tufts' apart. Rocks lie in patches with gaps between; pebbles and tufts clump, softer.
    k.patches = 1.0;
    k.clumps = 1.0;
    k.stony = 0.0;
    const bool census = (flags & 2u) != 0;
    if (abs(upA) < abs(dot(k.up, Axis(k.b))) || abs(upA) < abs(dot(k.up, Axis(k.c))) || upA * pl.y <= 0.0)
        return false;
    if (k.kind == PLANTS) // the plants: their light pass bounds them by the climate, CullMain
        return true;
    const float3 q = (float3)(k.p - (double3)detailAnchor.xyz * (double)detailOrigin.w);
    const float field = Fbm3(q, log2(64.0), log2(8.0), -16.0, 0.6, k.kind == STONES ? 71u : 73u).x;
    k.patches = smoothstep(OBJECT_PATCHES.x, OBJECT_PATCHES.y, field) / OBJECT_PATCHES.z;
    k.clumps = OBJECT_CLUMPS.z + (2.0 - 2.0 * OBJECT_CLUMPS.z) * smoothstep(OBJECT_CLUMPS.x, OBJECT_CLUMPS.y, field);
    // The most any ground gives this octave.
    const float most = k.kind == STONES ? k.patches * (GolombekShare(DEBRIS_ABUNDANCE.x, k.d) + GolombekShare(DEBRIS_ABUNDANCE.y, k.d)
                                                       + GolombekShare(GRASS_ROCKS, k.d)) + k.clumps * PebbleShare(k.d)
                                        : k.clumps * max(TUFT_COVER.x, TUFT_COVER.y);
    if (!census && k.accept >= most * k.chance)
        return false;
    if (k.kind == TUFTS)
        return true;
    // A stone, then, only where its region is stony, at the most its ground's drivers give (4: scree on a slope near
    // repose). Regions of 0.5 to 32 km, the same for every camera.
    k.stony = Fbm3(q, log2(32000.0), log2(500.0), -16.0, 0.5, 83u).x;
    return census || k.accept < most * k.chance * Stoniness(k.stony, 4.0);
}

// First pass, light: every cell of every slice's window, on each plane. The candidates that may be seen go to a list,
// for the second pass, where each thread gets one: the few that are seen, scattered among the many cells, would
// otherwise leave most of their waves' threads idle through the exact ground, ten times slower.
RWByteAddressBuffer candidateList : register(u2); // uint4 per candidate: slice and plane, its cell, the mesh's elevation
RWByteAddressBuffer dispatch : register(u3);      // the second pass's group count, 1, 1, then the candidates' count
#ifdef PLANET_STABLE_PLANTS
// The plants' variant (PlanetPlantCandidates.hlsl, PlanetPlantPlacement.hlsl): their tiles and plants, each in its own
// slot, compacted in order afterwards (PlanetPlantPlacement).
RWStructuredBuffer<uint4> stableTileRecords : register(u4);
RWStructuredBuffer<uint2> stableValues : register(u5);
RWStructuredBuffer<ObjectInstance> stablePlantScratch : register(u6);
RWStructuredBuffer<uint2> stableMasks : register(u7);
RWStructuredBuffer<uint4> groundRead : register(u8);   // the tiles' exact ground: last frame's, this frame's
RWStructuredBuffer<uint4> groundWrite : register(u9);
RWByteAddressBuffer groundClaims : register(u10);
#include "PlantPlacement.hlsli"
#endif

[numthreads(8, 8, 1)]
void CullMain(uint3 id : SV_DispatchThreadID)
{
    const uint plane = id.z % planeCount, slice = sliceBase + id.z / planeCount;
#ifdef PLANET_STABLE_PLANTS
    // All threads in this variant are plant tiles; larger octaves precede smaller ones.
    const uint tileIndex = (((6u - id.z / planeCount) * planeCount + plane) * 512u + id.y) * 512u + id.x;
    stableValues[tileIndex] = uint2(0, 0);
    CullPlantTile(id, slice, plane);
    return;
#endif
    const int window = Window(SliceClass(slice));
    const int shift = (int)round(log2(CellsPerSize(SliceClass(slice)) * exp2((float)SliceOctave(slice)) / FINEST_CELL));
    const int2 index = (planes[plane].zw >> shift) + (int2)id.xy - window / 2;
    Candidate k;
    if (id.x >= (uint)window || id.y >= (uint)window || !MakeCandidate(slice, plane, index, k))
        return;

    // Seen at all? Against the view and the farthest distance at which it spans OBJECT_PIXELS.x pixels: the ground the
    // mesh draws there, give or take far more than it ever strays from the exact ground (measured: centimetres), so
    // that the mesh never decides; off the mesh, any height from sea level to the highest summit.
    const float R = faceParams.y;
    const float3 sea = FaceLocal((float3)(k.p - Double3(camX, camY, camZ))), upFace = FaceLocal(k.up);
    const float3 centred = sea + float3(camPlane.xy, R + faceParams.z);
    const float2 xy = R * centred.xy / centred.z;
    const bool census = (flags & 2u) != 0;
    if (MeshCell(xy) > OBJECT_CELLS.y * k.size && !census) // the mesh cannot carry its foot (OBJECT_CELLS)
        return;
    float low = 0.0, high = MAX_TERRAIN_HEIGHT, meshElevation, horizon;
    float3 meshNormal;
    const bool onMesh = MeshElevationAt(xy, meshElevation, horizon, meshNormal);
    if (onMesh)
    {
        const float margin = 1.0 + 0.05 * length(sea + upFace * meshElevation);
        low = max(meshElevation - margin, 0.0);
        high = meshElevation + margin;
    }
    const float reach = min(k.size / (OBJECT_PIXELS.x * pixelAngle), (window / 2 - 1) * k.cell);
    const float along = clamp(-dot(sea, upFace), low, high);
    if ((length(sea + along * upFace) > reach || !MaybeVisible(sea + low * upFace, sea + (high + 2.0 * k.d) * upFace, 0.0, 2.0 * k.d))
        && !census)
        return;
    uint slot;
    dispatch.InterlockedAdd(12, 1u, slot);
    if (slot >= CANDIDATES)
        return;
    if (slot % 64 == 0)
        dispatch.InterlockedAdd(0, 1u);
    candidateList.Store4(16 * slot, uint4(slice * 4 + plane | f32tof16(horizon) << 16, (uint)index.x, (uint)index.y,
                                          asuint(onMesh ? meshElevation : -1.0)));
}

// Second pass, heavy: one candidate per thread, its exact ground, the materials there, its fade; kept or not.
ByteAddressBuffer candidates : register(t1);
ByteAddressBuffer candidateCount : register(t2);

[numthreads(64, 1, 1)]
void CSMain(uint3 id : SV_DispatchThreadID, uint threadInGroup : SV_GroupIndex)
{
    LoadGradients(threadInGroup, 64); // before any return: every thread must reach the barrier
    if (id.x >= min(candidateCount.Load(12), CANDIDATES))
        return;
    const uint4 record = candidates.Load4(16 * id.x);
#ifdef PLANET_STABLE_PLANTS
    PlacePlantTile(record, id.x);
    return;
#endif
    Candidate k;
    MakeCandidate((record.x & 0xFFFFu) / 4, record.x % 4, int2(record.yz), k);
    const float meshElevation = asfloat(record.w);
    const float R = faceParams.y;
    const double3 cam = Double3(camX, camY, camZ);
    const bool census = (flags & 2u) != 0, stone = k.kind == STONES;

    // The exact ground and its slope, over 1 m.
    counters.InterlockedAdd(COUNT_EVALUATED * 4, 1u);
    const float3 up = k.up, t1 = normalize(Axis(k.b) - up * dot(up, Axis(k.b))), t2 = cross(up, t1);
    const double3 u = k.p * INV_R;
    const float e0 = ExactElevation(u), e1 = ExactElevation(u + (double3)t1 * INV_R), e2 = ExactElevation(u + (double3)t2 * INV_R);
    ObjectInstance r = (ObjectInstance)0; // the census's record: see tools/banc_objets.py
    r.pos.z = k.chance * 1.47 * k.d * k.d; // the cell's ground (m^2)
    r.size = k.size;
    r.burial = (float)((record.x & 0xFFFFu) / 4); // the slice
    r.elevation = e0;
    r.axisY = up;
    if (e0 <= 0.0) // the sea
    {
        if (census)
            instances[id.x] = r;
        return;
    }
    const float3 normal = normalize(cross(t1 * (1.0 + e1 / R) + up * (e1 - e0), t2 * (1.0 + e2 / R) + up * (e2 - e0)));
    const float2 gradient = float2(e1 - e0, e2 - e0); // m per m
    const float steepness = length(gradient);
    // A stone reads the ground's form over OBJECT_LANDFORM m: the mean slope uphill, steeper than repose, sends its debris
    // down here; the curvature, a crest or a cliff top, which loose debris leaves.
    float uphill = 0.0, curvature = 0.0;
    if (stone)
    {
        const float3 towards = steepness > 1e-4 ? (gradient.x * t1 + gradient.y * t2) / steepness : t1, across = cross(up, towards);
        const double reach = OBJECT_LANDFORM * INV_R;
        const float above = ExactElevation(u + (double3)towards * reach), below = ExactElevation(u - (double3)towards * reach);
        const float left = ExactElevation(u + (double3)across * reach), right = ExactElevation(u - (double3)across * reach);
        uphill = (above - e0) / OBJECT_LANDFORM;
        curvature = (above + below + left + right - 4.0 * e0) / (OBJECT_LANDFORM * OBJECT_LANDFORM);
    }
    r.pos.xy = float2(steepness, uphill);

    // Its foot, and the camera's say: how far, how large on screen, whether the mesh carries it, whether in view.
    const double3 footPoint = k.p + (double3)(up * e0);
    const float3 pos = FaceLocal((float3)(footPoint - cam));
    const float span = k.size / (length(pos) * pixelAngle);
    const float3 centred = pos + float3(camPlane.xy, R + faceParams.z);
    const float cells = MeshCell(R * centred.xy / centred.z) / k.size;
    const float fade = census ? 1.0
                     : flags & 1u ? step(lerp(OBJECT_PIXELS.x, OBJECT_PIXELS.y, 0.5), span) * step(cells, lerp(OBJECT_CELLS.x, OBJECT_CELLS.y, 0.5))
                                  : smoothstep(OBJECT_PIXELS.x, OBJECT_PIXELS.y, span) * smoothstep(OBJECT_CELLS.y, OBJECT_CELLS.x, cells);
    if ((fade <= 0.0 || !MaybeVisible(pos, pos, 0.0, k.size)) && !census)
        return;

    // The ground's materials at its place, filtered to its cell: the ground cover each ground holds, never on bare rock,
    // which is the geometry's, nor under snow.
    const float3 upLocal = FaceLocal(up), normalLocal = FaceLocal(normal);
    const float3 q = (float3)(footPoint - (double3)detailAnchor.xyz * (double)detailOrigin.w);
    const float3 north = float3(faceX.y, faceY.y, faceZ.y);
    const float sinLat = dot(upLocal, north);
    const float3 tangentNorth = north - sinLat * upLocal;
    const float3 poleward = (sinLat < 0.0 ? -1.0 : 1.0) * tangentNorth * rsqrt(max(dot(tangentNorth, tangentNorth), 1e-12));
    gHeightBlend = 0.0;
    gBedLens = BedLenses(q, k.cell);
    gCellSize = k.cell;
    // No normal across SHORE_BASELINE is available here; the tile's normal is taken at roughly the mesh cell's scale.
    const Materials m = GroundMaterials(q, e0, upLocal, normalLocal, normalLocal, sinLat, poleward, log2(k.cell),
                                        t1 * k.cell, t2 * k.cell, 0.0, 0.0, StrataShift(q, k.cell));
    // The ground's shares as the pixels layer them (PixelShader.hlsl, GroundAt): soils, scree, rock, the beach's sand, snow.
    const float loose = (1.0 - m.snow) * (1.0 - m.beach) * (1.0 - m.rock), soils = loose * (1.0 - m.screeWeight);
    // Under the trees' crowns, the floor is their litter, not a meadow's tufts and rocks (docs/recherche-vegetation.md).
    Vegetation v = VegetationAt(m.temperature, m.humidity, m.coldSigma, m.amplitude, Exposure(up, e0));
    if (soils > 0.0)
        WoodsAt(q, log2(k.cell), v);
    v.able = PlantGround(m);
    const float scree = loose * m.screeWeight, grass = soils * m.grassAmount * (1.0 - TreesHere(v));
    const float sand = soils * m.sandAmount + (1.0 - m.snow) * m.beach, soil = soils * m.soilAmount, bare = sand + soil;
    float share, presence = 1.0;
    if (stone)
    {
        // Only in stony regions, which scree, debris itself, then dry bare ground and the slope make likelier. Pebbles on sand and bare soil;
        // rocks half-buried in grass; scree's stones and the rockfall at the foot of steep ground, where it eases, which
        // crests and cliff tops lose; all in patches, none past repose.
        const float2 easing = tan(radians(OBJECT_GATHER));
        const float foot = loose * (1.0 - smoothstep(easing.x, easing.y, steepness)) * smoothstep(0.7, 1.0, uphill);
        const float crest = smoothstep(OBJECT_CREST.x, OBJECT_CREST.y, -curvature);
        const float repose = radians(OBJECT_REPOSE.x - OBJECT_REPOSE.y * (k.octave - OBJECT_OCTAVES.x));
        const float rest = 1.0 - smoothstep(tan(repose - radians(OBJECT_REPOSE.z)), tan(repose), steepness);
        presence = Stoniness(k.stony, 3.0 * scree + bare * (1.0 - saturate(m.humidity)) + steepness);
        share = presence * rest * (k.patches * (lerp(1.0, OBJECT_CREST.z, crest) * (GolombekShare(DEBRIS_ABUNDANCE.x * scree, k.d)
                                                                         + GolombekShare(DEBRIS_ABUNDANCE.y * foot, k.d))
                                     + GolombekShare(GRASS_ROCKS * grass, k.d))
                        + k.clumps * PebbleShare(k.d) * bare);
    }
    else // tufts, in grass and a few dry ones on sand and bare soil, clumped
        share = k.clumps * (TUFT_COVER.x * grass + TUFT_COVER.y * bare);
    const float chance = share * k.chance;
    if (census)
    {
        r.axisX = float3(scree, sand, soil);
        r.albedo = float3(grass, k.accept < chance ? chance : -chance, curvature); // kept: its chance, else less it
        r.seed = f32tof16(stone ? k.patches : k.clumps) | f32tof16(presence) << 16;
        instances[id.x] = r;
        return;
    }
    if (k.accept >= chance)
        return;

    // Its frame: up between the vertical and the ground's normal, turned at random around it; a tuft stands straighter.
    const float3 axisY = normalize(lerp(upLocal, normalLocal, stone ? 0.85 : 0.4));
    const float turn = 6.2831853 * float(k.looks.y >> 8) / 16777216.0;
    const float3 side = normalize(cross(axisY, abs(axisY.z) < 0.9 ? float3(0.0, 0.0, 1.0) : float3(1.0, 0.0, 0.0)));
    const float3 axisX = cos(turn) * side + sin(turn) * cross(axisY, side);
    float3 albedo;
    float burial;
    if (stone)
    {
        // Partly buried in soft ground, barely seated on rock (OBJECT_BURIAL); the colour of the ground's scree there.
        burial = max(lerp(OBJECT_BURIAL.x, OBJECT_BURIAL.y, 1.0 - m.rock), OBJECT_BURIAL.z / (0.6 * k.size));
        const float3 rockColor = RockColor(Geology(q, k.cell), m.humidity) * (1.0 + 0.7 * m.local.z);
        albedo = 1.15 * rockColor * m.scree.color * (1.0 + 0.15 * LatticeRandom(k.looks).z);
    }
    else
    {
        // Its foot in the ground; the ground's grass colour there, a little different from tuft to tuft.
        burial = OBJECT_BURIAL.z / (0.8 * k.size);
        albedo = ClimateColor(m) * m.grass.color * (1.0 + 0.2 * LatticeRandom(k.looks).z);
    }

    // Under the plants' crowns, the ground's light through their gaps, as the pixels give it (PixelShader.hlsl): the sun
    // and the sky in their shares of a clear day's light at a high sun, 85 and 15 %, on its colour.
    {
        const float open = 1.0 - PlantCover(TreesHere(v), ShrubsHere(v)), muS = dot(upLocal, lightDir.xyz);
        albedo *= 0.85 * pow(open, 1.0 / max(muS, 0.1)) + 0.15 * open;
    }

    // The gap between a stone's foot and the ground the mesh draws, along the vertical (docs/spec-objets-proximite.md).
    if (meshElevation >= 0.0 && stone)
    {
        const float gap = meshElevation - e0; // > 0: the drawn ground above its foot, it sinks; < 0: it rises
        const float depth = burial * 0.6 * k.size; // its height, about 0.6 of its width
        counters.InterlockedAdd(COUNT_MEASURED * 4, 1u);
        counters.InterlockedAdd(GAP_SUM * 4, (uint)(abs(gap) * 1e5)); // 0.01 mm
        counters.InterlockedMax(GAP_BELOW * 4, (uint)(max(-gap, 0.0) * 1e5));
        counters.InterlockedMax(GAP_ABOVE * 4, (uint)(max(gap, 0.0) * 1e5));
        counters.InterlockedMax(FLOAT_RATIO * 4, (uint)(max(-gap, 0.0) / depth * 1000.0));
        if (-gap > depth)
            counters.InterlockedAdd(COUNT_FLOATING * 4, 1u);
        counters.InterlockedMax(SINK_RATIO * 4, (uint)(max(gap, 0.0) / ((1.0 - burial) * 0.6 * k.size) * 1000.0)); // of its visible height
        counters.InterlockedMax(GAP_PIXELS * 4, (uint)(abs(gap) / (length(pos) * pixelAngle) * 100.0)); // on screen, 0.01 px
    }

    // Stones from the start of the instances, tufts from CLASS_CAPACITY; each its own draw's instance count.
    uint slot;
    counters.InterlockedAdd((stone ? COUNT_PLACED : COUNT_TUFTS) * 4, 1u, slot);
    if (slot >= CLASS_CAPACITY)
        return;
    counters.InterlockedAdd((stone ? 1 : TUFT_ARGUMENTS + 1) * 4, 1u); // the draw's instance count
    ObjectInstance o;
    o.pos = pos;
    o.size = k.size * fade;
    o.axisX = axisX;
    o.burial = burial;
    o.axisY = axisY;
    o.elevation = e0;
    o.albedo = saturate(albedo);
    o.seed = k.looks.z;
    instances[(stone ? 0 : CLASS_CAPACITY) + slot] = o;
}
