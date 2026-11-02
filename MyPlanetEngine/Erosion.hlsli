// Erosion.hlsli - the erosion (docs/spec-erosion.md). The level 0's network (Erosion.h), computed once per body at startup
// on the tectonic map's cube, one slice per face; around each of its links, the valley it carves (ErosionValleys).
// Exolune's own code. The CPU port: tools/hydro/cp.py.
#ifndef EROSION_HLSLI
#define EROSION_HLSLI
#include "PlanetSettings.hlsli"
#include "Noise.hlsli"
#include "Climate.hlsli"

SamplerState erosionClimateSampler : register(s4); // linear, clamped; also bound by the terrain compute passes

Texture2DArray<uint2> erosionMap : register(t23);

static const uint EROSION_HAS_RECEIVER = 8u, EROSION_LAKE = 1u << 12, EROSION_SEA = 1u << 13, EROSION_FAN_APEX = 1u << 14,
                  EROSION_MOUTH = 1u << 15;

uint ErosionSize()
{
    uint width, height, layers;
    erosionMap.GetDimensions(width, height, layers);
    return width;
}

// The direction of face f's point (s, t), s and t past [-1, 1] beyond its edge: CubeDirection (PlanetMap.hlsli).
float3 ErosionDirection(uint f, float2 st)
{
    const float s = st.x, t = st.y;
    return f == 0 ? float3(1.0, -t, -s) : f == 1 ? float3(-1.0, -t, s) : f == 2 ? float3(s, 1.0, t)
         : f == 3 ? float3(s, -1.0, -t) : f == 4 ? float3(s, -t, 1.0) : float3(-s, -t, -1.0);
}

// The face holding the direction d, D3D's choice, and d's texel coordinates there, the centre of texel i at i.
void ErosionLocate(float3 d, uint n, out uint face, out float2 x)
{
    const float3 a = abs(d);
    float ma, sc, tc;
    if (a.x >= a.y && a.x >= a.z) face = d.x > 0.0 ? 0 : 1, ma = a.x, sc = d.x > 0.0 ? -d.z : d.z, tc = -d.y;
    else if (a.y >= a.z)          face = d.y > 0.0 ? 2 : 3, ma = a.y, sc = d.x, tc = d.y > 0.0 ? d.z : -d.z;
    else                          face = d.z > 0.0 ? 4 : 5, ma = a.z, sc = d.z > 0.0 ? d.x : -d.x, tc = -d.y;
    x = (float2(sc, tc) / ma + 1.0) * 0.5 * n - 0.5;
}

// The cell (face, i, j); past the face's edge, the cell holding that point, as Erosion.cpp's neighbours.
uint ErosionCell(uint face, int2 ij, uint n)
{
    [branch] if (all(ij >= 0) && all(ij < (int)n))
        return (face * n + (uint)ij.y) * n + (uint)ij.x;
    uint f;
    float2 x;
    ErosionLocate(ErosionDirection(face, ((float2)ij + 0.5) * 2.0 / n - 1.0), n, f, x);
    const uint2 k = (uint2)clamp(floor(x + 0.5), 0.0, n - 1.0);
    return (f * n + k.y) * n + k.x;
}

// The cell's neighbour k, row by row, dj then di from -1 to 1, the centre left out (Erosion.cpp).
uint ErosionNeighbour(uint c, uint k, uint n)
{
    const uint m = k < 4 ? k : k + 1;
    return ErosionCell(c / (n * n), int2(c % n, c / n % n) + int2((int)(m % 3) - 1, (int)(m / 3) - 1), n);
}

// The cell's node: its centre moved within it by its hash, on the unit sphere.
float3 ErosionNode(uint c, uint n)
{
    const uint h = RlMix1(c * 0x9E3779B1u + 0x632BE5ABu);
    const float2 jitter = (float2(h & 0xffffu, h >> 16) / 65535.0 - 0.5) * (2.0 * EROSION_JITTER);
    return normalize(ErosionDirection(c / (n * n), (float2(c % n, c / n % n) + 0.5 + jitter) * 2.0 / n - 1.0));
}

struct ErosionData
{
    float level;     // the water's level (m)
    float ground;    // the filled ground (m)
    float discharge; // m3/s
    float ice;       // the ice flux (m3/yr), 0 without ice
    uint bits;       // Erosion.h's second word
};

ErosionData ErosionRead(uint c, uint n)
{
    const uint2 t = erosionMap.Load(int4(c % n, c / n % n, c / (n * n), 0));
    ErosionData d;
    d.level = (float)(t.x & 0xffffu) * 0.25 - 8192.0;
    d.ground = (float)(t.x >> 16) * 0.25 - 8192.0;
    d.discharge = exp2((float)(t.y >> 16 & 255u) / 8.0 - 8.0);
    const uint ice = t.y >> 24;
    d.ice = ice ? exp2((float)(ice - 1u) / 6.0 + 10.0) : 0.0;
    d.bits = t.y;
    return d;
}

// The valleys around the point: the surface they carve, the share of their floor, the water's level there.
struct ErosionValley
{
    float surface;    // the valleys' surface (m), a minimum over the links; far above the ground away from them
    float3 gradient;  // its slope (m/m), along the ground
    float floorShare; // 1 on a valley's floor, where the detail fades
    float level;      // the water's level on the link defining surface (m); never an independent nearest-link clamp
    float glacier;    // 1 in a glacial trough, fading away from it
    float incision;   // the links' valley depth at their node (m), fading away from them: continuous
    float deposit;    // the deposits' surface (m), deltas and fans; far below the ground away from them
    float lakeLevel;  // terminal lake stage across its catchment; zero for ocean drainage
    float channelBed, channelSurface; // lower envelopes of the same section, with and without its channel cut
    float channelDistance; // distance from the physical liquid channel; independent of mesh sampling
    float3 flow;      // downstream surface velocity in the planet frame (m/s)
};

// The gullies' inputs to the detail (ReliefDetail).
struct ReliefGullies
{
    float3 slope;  // the slope (m/m) of the ground under the detail: the large forms', or a valley's walls where it is carved
    float3 valleySlope;
    float ground;  // large forms before the coarse octaves
    float surface; // valley envelope, independent of the detail it will receive
    float incision;
    float carved;  // 1 where a valley replaces the coarse octaves: their slope no longer counts
    float share;   // the share of the octaves' pattern turned to gullies on a steep enough ground
    float glacial; // 1 above the equilibrium line: rounded knife-edge crests, never from trough ice
};

// As Erosion.cpp's ErosionClimate: the computed year's precipitation (m/yr), sea-level temperature (C).
float2 ErosionClimate(float3 d)
{
    return ClimateAt(erosionClimateSampler, d, 0.0).xy * float2(0.001, 1.0);
}

// The glacial maximum's equilibrium line (m), as Erosion.cpp's: the summer temperature there after the precipitation
// (Ohmura, Kasser and Funk 1992), the year's 8 C colder, 6.5 K/km, 900 m below today's.
float ErosionEquilibriumLine(float3 d)
{
    const float2 c = ErosionClimate(d);
    const float summer = (-296.0 + sqrt(296.0 * 296.0 - 36.0 * (645.0 - 1000.0 * c.x))) / 18.0;
    return (c.y - (summer - 8.0)) / 6.5e-3 - 900.0;
}

// The gullies' stripes for an octave (Tricard et al. 2019, Procedural Phasor Noise): plane waves across `across`, a unit
// tangent, one period per cell of the octave, from the 8 corners of the cell `l` of a lattice of EROSION_GULLY_PERIODS
// periods, each its own phase, blended by the quintic weights; the phase of their sum, whose singularities are the forks.
// Around a fork the phase takes every value: the stripes fade there, over a sum below EROSION_GULLY_FORK, so that the
// ground does not tear. x: the stripes, E|x| about the noise's; yzw: their gradient per cell of the octave.
float4 ErosionGullies(RlCell l, float3 across, uint seed)
{
    uint4 h0, h1;
    RlCornerHashes(l.cell, h0, h1);
    const float3 s = RlFade(l.q, true);
    float2 sum = 0.0;
    [unroll] for (int k = 0; k < 8; ++k)
    {
        const float3 corner = float3(k & 1, (k >> 1) & 1, k >> 2);
        const uint h = k < 4 ? h0[k] : h1[k - 4];
        const float phase = 6.2831853 * ((float)EROSION_GULLY_PERIODS * dot(across, l.q - corner)
                                         + (float)(RlMix1(h + seed * 0x27D4EB2Fu) >> 8) * (1.0 / 16777216.0));
        const float3 t = lerp(1.0 - s, s, corner);
        float sn, cs;
        sincos(phase, sn, cs);
        sum += t.x * t.y * t.z * float2(cs, sn);
    }
    const float m = max(length(sum), EROSION_GULLY_FORK), amplitude = 0.5 * 3.14159265 * 0.5 * (1.0 + RL_MEAN_BILLOW_BEST);
    return float4(amplitude * sum.x / m, -amplitude * (sum.y / m) * 6.2831853 * across);
}

// A quadratic Bezier, relative to the query in its tangent plane, in radii. The four chords only initialise the solve:
// measuring the chords themselves makes four angular bends per link and jumps in the longitudinal profile's tangent.
float2 ErosionCurveDistance(float3 a, float3 b, float3 c, out float3 nearest)
{
    // A head or outlet repeats a control point. Its tangent vanishes at that end: Newton can retain a wrong t even
    // when its distance is almost exact, then jump the interpolated height and ice flux. Solve this straight run.
    const bool head = all(a == b), outlet = all(b == c);
    [branch] if (head || outlet)
    {
        const float3 e = c - a;
        const float u = saturate(-dot(a, e) / max(dot(e, e), 1e-30));
        nearest = a + u * e;
        return float2(length(nearest), head ? sqrt(u) : 1.0 - sqrt(1.0 - u));
    }
    float best = 1e30, at = 0.0;
    nearest = a;
    float3 prev = a;
    [unroll] for (int k = 1; k <= 4; ++k)
    {
        const float t = k * 0.25, s = 1.0 - t;
        const float3 next = s * s * a + 2.0 * s * t * b + t * t * c;
        const float3 e = next - prev;
        const float u = saturate(-dot(prev, e) / max(dot(e, e), 1e-30));
        const float3 q = prev + u * e;
        const float d = dot(q, q);
        if (d < best) best = d, at = (k - 1 + u) * 0.25, nearest = q;
        prev = next;
    }
    const float3 bend = a - 2.0 * b + c;
    [unroll] for (int step = 0; step < 4; ++step)
    {
        const float3 q = lerp(lerp(a, b, at), lerp(b, c, at), at);
        const float3 tangent = 2.0 * lerp(b - a, c - b, at);
        const float denom = dot(tangent, tangent) + 2.0 * dot(q, bend);
        at = saturate(at - clamp(dot(q, tangent) / max(denom, 1e-20), -0.25, 0.25));
    }
    nearest = lerp(lerp(a, b, at), lerp(b, c, at), at);
    best = dot(nearest, nearest);
    if (dot(a, a) < best) nearest = a, at = 0.0, best = dot(a, a);
    if (dot(c, c) < best) nearest = c, at = 1.0;
    return float2(length(nearest), at);
}

// Box mean of max(x,0)^2 minus its point value, and the derivative of that difference.
// This form avoids subtracting large cubic primitives when the footprint is small.
float2 ErosionBoxSquareExcess(float x, float radius)
{
    const float tail = max(radius - abs(x), 0.0);
    const float cap = tail * tail * tail / (6.0 * radius);
    return float2(x >= 0.0 ? radius * radius / 3.0 - cap : cap, tail * tail / (2.0 * radius));
}

float2 ErosionRiverSize(float q)
{
    return float2(max(1.0, EROSION_RIVER_SHAPE.x * sqrt(q)),
                  clamp(EROSION_RIVER_SHAPE.y * pow(q, EROSION_RIVER_SHAPE.z), 0.15, EROSION_RIVER_SHAPE.w)
                  * smoothstep(0.05, 0.5, q));
}

// Local mean of a compact quartic channel, depth*(1-(d/width)^2)^2. Both the bed and its bank slope vanish at
// the physical edge; averaging keeps its excavated section when the mesh cannot resolve the whole width.
float2 ErosionRiverCut(float d, float q, float radius)
{
    const float2 size = ErosionRiverSize(q);
    const float2 x = clamp(float2(d - radius, d + radius) / size.x, -1.0, 1.0);
    const float2 x2 = x * x;
    const float2 primitive = x * (1.0 + x2 * (-2.0 / 3.0 + x2 * 0.2));
    const float2 edge = (1.0 - x2) * (1.0 - x2);
    return EROSION_WATER * size.y * float2(size.x * (primitive.y - primitive.x), edge.y - edge.x) / (2.0 * radius);
}

float ErosionRiverProfile(float d, float z, float q, float walls, float radius)
{
    const float width = ErosionRiverSize(q).x;
    const float2 bank = float2(d - width, -d - width);
    const float2 tail = max(radius - abs(bank), 0.0);
    const float rise = walls * (max(d - width, 0.0) + dot(tail, tail) / (4.0 * radius));
    return z + rise - ErosionRiverCut(d, q, radius).x;
}

// One link's physical cross-section at distance d (m), averaged over a footprint of width `wide`.
// Water level z, discharge q (m3/s), ice flux and along-link slope determine the profile, independently of mesh size.
// Returns the surface and physical floor share; rise is the filtered slope away from the axis.
float2 ErosionProfile(float d, float z, float q, float ice, float slope, float walls, float wide, float widest,
                      out float glacier, out float rise)
{
    // The fluvial floor, wider on a gentle river; never wider than `widest`, so that it ends before the links read change.
    const float floodplain = EROSION_FLOOR.x * sqrt(q) * clamp(EROSION_FLOOR.y / max(slope, 1e-6), 1.0, EROSION_FLOOR.z);
    // The liquid channel belongs inside its valley. A narrower floor forced the later water pass to excavate banks.
    const float floorWidth = min(max(floodplain, ErosionRiverSize(q).x), widest);
    // A parabolic U above its drained floor (Hirano & Aniya 1988), extended by its tangent at the wall slope.
    // Subtracting an overdepth before clamping to water would flatten the whole U into a kilometre-wide ribbon.
    glacier = saturate(log2(max(ice, 1.0)) - EROSION_GLACIER.w);
    const float trough = clamp(EROSION_GLACIER.x * pow(max(ice, 1.0) / 1e8, EROSION_GLACIER.y), 150.0, 1500.0);
    const float curvature = EROSION_GLACIER.z / trough;
    const float shoulder = EROSION_GLACIER_WALLS / (2.0 * curvature);
    // Average the physical cross-section over the mesh footprint. Never scale its coordinate by network depth:
    // depth can be zero while the detailed terrain stands hundreds of metres above that coarse reference.
    // A depth-derived dilation then moved even distant planar banks when the mesh changed by a few metres.
    // The finest terrain shares the same physical rounding as the other crests.
    const float radius = max(0.5 * wide, CREASE_MIN_CELL);
    const float2 bank = float2(d - floorWidth, -d - floorWidth);
    const float2 tail = max(radius - abs(bank), 0.0);
    const float fluvial = walls * (max(d - floorWidth, 0.0) + dot(tail, tail) / (4.0 * radius));
    const float fluvialRise = walls * (saturate(0.5 + 0.5 * bank.x / radius) - saturate(0.5 + 0.5 * bank.y / radius));
    const float u = min(d, shoulder);
    const float2 right = ErosionBoxSquareExcess(d - shoulder, radius);
    const float2 left = ErosionBoxSquareExcess(-d - shoulder, radius);
    const float glacial = curvature * u * u + EROSION_GLACIER_WALLS * max(d - shoulder, 0.0)
                        + curvature * max(radius * radius / 3.0 - right.x - left.x, 0.0);
    const float glacialRise = 2.0 * curvature * u - curvature * (right.y - left.y);
    const float surface = z + lerp(fluvial, glacial, glacier);
    rise = lerp(fluvialRise, glacialRise, glacier);
    // The floor, where the detail fades: the river's; the trough's middle, where the gullies of its two walls would meet.
    const float flat = lerp(1.0 - smoothstep(floorWidth, floorWidth + max(floorWidth, 200.0), d),
                            1.0 - smoothstep(0.25 * trough, 0.7 * trough, d), glacier);
    return float2(surface, flat);
}

// The valleys of the level 0's links around the point p (unit, planet frame), for mesh cells of cellKm; walls: their slope.
// The links whose curve's control is one of the 4 x 4 nodes around p; each valley reaches EROSION_REACH cells at most.
ErosionValley ErosionValleys(double3 p, float cellKm, float walls)
{
    // Turbulence warps a direction in 3D. Its radial displacement is not distance from the river: put it back on the
    // sphere before measuring against the links. One double Newton step keeps metre placement at planetary scale.
    const double squared = p.x * p.x + p.y * p.y + p.z * p.z;
    double inverse = (double)rsqrt((float)squared);
    inverse *= 1.5 - 0.5 * squared * inverse * inverse;
    p *= inverse;
    const uint n = ErosionSize();
    const float radius = 1000.0 * PLANET_RADIUS_KM, cellM = 2.0 * radius / n;
    uint face;
    float2 x;
    ErosionLocate((float3)p, n, face, x);
    const int2 origin = (int2)floor(x) - 1;
    ErosionValley v;
    v.surface = 1e9, v.gradient = 0.0, v.floorShare = 0.0, v.level = 0.0, v.glacier = 0.0, v.incision = 0.0, v.deposit = -1e9;
    // A nearest-cell terminal stage creates vertical water walls wherever fine relief crosses a coarse divide.
    // Reconstruct it continuously in a fixed physical band. Equal-stage interiors stay exactly level;
    // connections between different basins are a stage transition, not a resolved hydraulic spillway.
    v.lakeLevel = 0.0;
    const float band = min(EROSION_LAKE_TRANSITION / cellM, 0.5);
    const float2 blend = smoothstep(0.5 - band, 0.5 + band, frac(x));
    [unroll] for (int lakeTap = 0; lakeTap < 4; ++lakeTap)
    {
        const int2 offset = int2(lakeTap & 1, lakeTap >> 1);
        const uint c = ErosionCell(face, (int2)floor(x) + offset, n);
        const uint2 basin = erosionMap.Load(int4(c % n, c / n % n, c / (n * n) + 6u, 0));
        const float2 weight = lerp(1.0 - blend, blend, (float2)offset);
        if (EROSION_WATER > 0.0 && basin.y != 0u)
            v.lakeLevel += weight.x * weight.y * max(0.0, (float)(basin.x & 0xffffu) * 0.25 - 8192.0);
    }
    v.flow = 0.0;
    v.channelBed = 1e9, v.channelSurface = 1e9;
    v.channelDistance = 1e9;
    float guideSurface = 1e9;
    const float wide = 2000.0 * cellKm;
    // Positions relative to the point, in floats: a node less the point's float, exact between neighbours (Sterbenz), less
    // the point's rest, the one reading in doubles. Doubles run 64 times slower than floats here.
    const float3 pf = (float3)p, rest = (float3)(p - (double3)pf);
    [loop] for (int k = 0; k < 16; ++k)
    {
        const uint r = ErosionCell(face, origin + int2(k & 3, k >> 2), n);
        const float3 pr = ErosionNode(r, n), b = (pr - pf) - rest;
        // A node's links stay within 1.15 cells of it, its deposits within less: farther, nothing reaches the point.
        [branch] if (length(b) * radius > (EROSION_REACH + 1.15) * cellM)
            continue;
        const ErosionData dr = ErosionRead(r, n);
        const bool outlet = (dr.bits & (EROSION_SEA | EROSION_LAKE)) != 0;
        // Downstream: the midpoint to the receiver, or the node itself at an outlet.
        float3 c = b;
        float zDown = dr.level, qDown = dr.discharge, iceDown = dr.ice, groundDown = dr.ground;
        [branch] if (dr.bits & EROSION_HAS_RECEIVER)
        {
            const uint rr = ErosionNeighbour(r, dr.bits & 7u, n);
            const ErosionData drr = ErosionRead(rr, n);
            c = 0.5 * ((pr - pf) + (ErosionNode(rr, n) - pf)) - rest;
            zDown = 0.5 * (dr.level + drr.level);
            qDown = sqrt(dr.discharge * drr.discharge);
            iceDown = 0.5 * (dr.ice + drr.ice);
            groundDown = 0.5 * (dr.ground + drr.ground);
        }
        // The deposits: a delta at a mouth without ice, its lobe seaward, a plain a few metres above the sea, its front
        // sloping down to the shelf; a fan at the mountain front, a cone from the river's level down its valley. Both
        // within 0.3 cell of their apex, a cell of their node: the nodes read always hold them.
        [branch] if ((dr.bits & (EROSION_MOUTH | EROSION_FAN_APEX)) && dr.ice <= 0.0)
        {
            const bool delta = (dr.bits & EROSION_MOUTH) != 0;
            const float3 apex = delta ? c : b, ahead = normalize(c - b);
            const float along = -dot(apex, ahead) * radius, across = length(-apex - dot(-apex, ahead) * ahead) * radius;
            const float size = min((delta ? EROSION_DELTA.x : EROSION_FAN.x) * sqrt(dr.discharge), 0.25 * cellM);
            const float back = delta ? EROSION_DELTA.y : EROSION_FAN.y;
            const float e = length(float2(along / (along > 0.0 ? size : back * size), across / (EROSION_DELTA.z * size)));
            const float fade = 1.0 - smoothstep(0.2, 0.3, length(apex) * radius / cellM); // within the nodes read, always
            const float surface = delta ? EROSION_DELTA.w * (1.0 - e) - (e > 1.0 ? EROSION_DELTA_FRONT * (e - 1.0) * size : 0.0)
                                        : dr.level - EROSION_FAN.z * e * size - (e > 1.0 ? (e - 1.0) * size : 0.0); // its toe, at 45 degrees
            [branch] if (size > 10.0 && (delta ? dr.discharge > EROSION_DELTA_DISCHARGE : true))
                v.deposit = max(v.deposit, lerp(-1e4, surface, fade));
        }
        uint inflows = dr.bits >> 4 & 255u;
        // A head: from its node down; an outlet without inflow carves nothing.
        const bool head = inflows == 0u && !outlet;
        [loop] while (inflows != 0u || head)
        {
            float3 a = b;
            float zUp = dr.level, qUp = dr.discharge, iceUp = dr.ice, groundUp = dr.ground;
            [branch] if (inflows != 0u)
            {
                const uint kq = firstbitlow(inflows);
                inflows &= inflows - 1u;
                const uint q = ErosionNeighbour(r, kq, n);
                const ErosionData dq = ErosionRead(q, n);
                a = 0.5 * ((ErosionNode(q, n) - pf) + (pr - pf)) - rest;
                zUp = 0.5 * (dq.level + dr.level), qUp = sqrt(dq.discharge * dr.discharge);
                iceUp = 0.5 * (dq.ice + dr.ice), groundUp = 0.5 * (dq.ground + dr.ground);
            }
            float3 nearestPoint;
            // A chord lies below the sphere even when its direction is on the river. Its radial sag is not a bank.
            const float3 end = outlet ? b : c;
            const float2 dt = ErosionCurveDistance(a - dot(a, pf) * pf, b - dot(b, pf) * pf,
                                                   end - dot(end, pf) * pf, nearestPoint);
            const float d = dt.x * radius;
            [branch] if (d < EROSION_REACH * cellM)
            {
                // Height and flux use the same shared midpoints as the curve. Its quadratic height has the same
                // tangent on both sides of a join; a per-link linear slope made the floodplain width jump there.
                const float t = dt.y, s0 = 1.0 - t, zEnd = outlet ? dr.level : zDown;
                const float z = s0 * s0 * zUp + 2.0 * s0 * t * dr.level + t * t * zEnd;
                const float q = exp2(s0 * s0 * log2(qUp) + 2.0 * s0 * t * log2(dr.discharge)
                                    + t * t * log2(outlet ? dr.discharge : qDown));
                const float ice = s0 * s0 * iceUp + 2.0 * s0 * t * dr.ice + t * t * (outlet ? dr.ice : iceDown);
                const float3 tangent = 2.0 * lerp(b - a, (outlet ? b : c) - b, t);
                const float span = max(length(tangent), 1e-9) * radius;
                // At a repeated control, both derivatives vanish together: use their finite straight-run limit.
                const float waterSlope = head ? abs(zEnd - dr.level) / max(length(end - b) * radius, 1e-6)
                                       : outlet ? abs(dr.level - zUp) / max(length(b - a) * radius, 1e-6)
                                       : abs(2.0 * lerp(dr.level - zUp, zEnd - dr.level, t)) / span;
                const float ground = s0 * s0 * groundUp + 2.0 * s0 * t * dr.ground
                                   + t * t * (outlet ? dr.ground : groundDown);
                const float depth = max(ground - z, 0.0);
                float glacier, rise;
                const float2 s = ErosionProfile(d, z, q, ice, waterSlope, walls, wide, 0.15 * cellM, glacier, rise);
                // Past three quarters of the reach the valley rises out of every ground: the links read change there.
                const float beyond = smoothstep(0.35, 0.5, d / cellM);
                const float candidate = s.x + 1e4 * beyond;
                // The carved envelope is the union of the profiles, each already above its own drainage level.
                // Only the slope guiding the gullies blends over 60 m at divides; it must not jump between links.
                const float guide = saturate(0.5 + 0.5 * (guideSurface - candidate) / EROSION_SMOOTH);
                v.gradient = lerp(v.gradient, -rise * nearestPoint / max(length(nearestPoint), 1e-12), guide);
                guideSurface = lerp(guideSurface, candidate, guide) - EROSION_SMOOTH * guide * (1.0 - guide);
                [branch] if (candidate < v.surface)
                {
                    v.surface = candidate;
                    v.level = z;
                }
                const float channel = ErosionRiverProfile(d, z, q, walls, max(0.5 * wide, CREASE_MIN_CELL)) + 1e4 * beyond;
                [branch] if (EROSION_WATER > 0.0 && q > 0.05 && z > 0.0)
                    v.channelDistance = min(v.channelDistance, d - ErosionRiverSize(q).x + 1e4 * beyond);
                [branch] if (EROSION_WATER > 0.0 && q > 0.05)
                    v.channelSurface = min(v.channelSurface, channel + ErosionRiverCut(d, q, max(0.5 * wide, CREASE_MIN_CELL)).x);
                [branch] if (EROSION_WATER > 0.0 && q > 0.05 && channel < v.channelBed)
                {
                    v.channelBed = channel;
                    const float2 channelSize = ErosionRiverSize(q);
                    const float speed = min(q / max((16.0 / 15.0) * channelSize.x * channelSize.y, 1e-3), 4.0);
                    v.flow = tangent / max(length(tangent), 1e-12) * speed;
                }
                // What the detail reads, continuous where the lowest or the nearest link changes: each link's, fading
                // from its axis to before the links read change, the largest.
                const float near = 1.0 - smoothstep(0.1, 0.35, d / cellM);
                v.incision = max(v.incision, depth * near);
                v.glacier = max(v.glacier, glacier * near);
                // Keep the floor through the terminal segment. Dropping it at an outlet reintroduced the residual
                // terrain across the water and created a dam just before the coarse sea/lake node.
                v.floorShare = max(v.floorShare, s.y * (1.0 - beyond));
            }
            if (head) break;
        }
    }
    return v;
}

// A bounded cut: water belongs to each link before their union, never to an independently chosen nearest link.
float ErosionCut(float coarse, float surface, float k)
{
    const float depth = max(coarse - surface, 0.0);
    // At k=0 the cut reaches its profile, including when depth is zero. Avoid a degenerate smoothstep.
    const float t = depth / max(max(k, depth), 1e-20);
    return coarse - depth * t * t * (3.0 - 2.0 * t);
}

float ErosionCarve(float h, float coarse, ErosionValley v, float k)
{
    // Existing hollows already belong to h. Adding their negative residual to the cut a second time dug side trenches
    // below the draining floor while leaving a perched river in the middle. Only positive spurs decorate the envelope;
    // this C1 positive part uses the existing join scale, and h remains the upper bound, including in a deep hollow.
    const float detail = h - coarse, tail = max(k - abs(detail), 0.0);
    const float spurs = max(detail, 0.0) + tail * tail / (4.0 * k);
    const float surface = v.surface + spurs * (1.0 - v.floorShare);
    // The profile remains the lower bound of any new excavation. Existing hollows survive through h; no separate
    // winning-link stage is imposed after the union, which would introduce steps where tributaries compete.
    // Soften the shoulders, not the draining floor. A 60 m join on a shallow floor left a barrier above its stage;
    // the compact liquid channel then could not reach it without an unbounded second excavation.
    return ErosionCut(h, surface, k * (1.0 - v.floorShare));
}

// Adding water may dig the compact channel, never a second unbounded V valley through the finished terrain.
// The paired envelopes bound its depth even where different tributaries win them. An unresolved or misrouted
// channel may remain dry; opening it requires coherent drainage, not an unlimited final geometry clamp.
float ErosionChannelCut(float h, float bed, float surface)
{
    return min(max(h - bed, 0.0), max(surface - bed, 0.0));
}

// The only wind reading for wave erosion: the climate's mean surface wind, in its own east/north basis.
// xyz is the direction of travel, scaled by the relative wave force, not the direction from which the wind comes.
// Keep the former 1..1.6 calibration: 5 m/s gives 1, 8 m/s gives 1.6. Calms fade below 1 m/s continuously.
float3 ErosionWaveWind(float3 d)
{
    const float2 wind = ClimateAt(erosionClimateSampler, d, 0.0, 1).xy;
    const float speed = length(wind);
    const float strength = smoothstep(0.0, 1.0, speed)
                         * lerp(1.0, EROSION_CLIFF_WAVES.y, saturate((speed - 5.0) / 3.0));
    const float3 east = float3(-d.z, 0.0, d.x) / max(length(d.xz), 1e-6), north = cross(east, d);
    return (wind.x * east + wind.y * north) * (strength / max(speed, 1e-6));
}

// Remap the full ground through its coastal contour. The platform is linear in the original height (Trenhaile 1987),
// and the deeper sea floor stays unchanged. Delta is the physical face width in height coordinates, never a mesh width.
// The final incision is averaged separately, after its intersection with the original ground and the talus.
float ErosionCliffProfile(float h, float hc, float delta, float depth)
{
    const float platform = EROSION_CLIFF_PLATFORM.x - depth * (1.0 - min(h / hc, 1.0));
    const float face = 1.0 - smoothstep(hc, hc + delta, h);
    const float cut = min(max(h - platform, 0.0), (hc - EROSION_CLIFF_PLATFORM.x) * face);
    return h - cut;
}

// Attach a talus to the face at its prescribed height above the platform. A symmetric mound centred on hc fell
// again on the landward side, excavating a moat behind its crest. The supported profile must rise towards the wall.
float ErosionCliffContact(float hc, float delta, float talus)
{
    const float height = hc - EROSION_CLIFF_PLATFORM.x;
    // On the face, height above the foot is delta*t + height*smoothstep(t). Solve for the talus contact.
    // The quadratic gives an upper bound below t=0.5; four Newton steps converge on this monotone convex interval.
    float t = 2.0 * talus / (delta + sqrt(delta * delta + 4.0 * height * talus));
    [unroll] for (int i = 0; i < 4; ++i)
        t -= (delta * t + height * t * t * (3.0 - 2.0 * t) - talus) / (delta + 6.0 * height * t * (1.0 - t));
    return t;
}

float ErosionCliffScree(float h, float hc, float delta, float talus, float gradient)
{
    const float contact = hc + delta * ErosionCliffContact(hc, delta, talus);
    // The excess over the existing platform rises seaward-to-landward. Past contact, the cliff takes over.
    return max(talus - EROSION_CLIFF_SCREE.x * max(contact - h, 0.0) / gradient, 0.0);
}

// Mean contributions on u in [-1,1], h(u)=h+radius*u. Local intervals avoid subtracting large primitives at small radii.
float ErosionCliffLinearMean(float2 interval, float centre, float change)
{
    interval = clamp(interval, -1.0, 1.0);
    [branch] if (interval.y <= interval.x) return 0.0;
    const float2 values = centre + change * interval, positive = max(values, 0.0);
    // Clip the line against zero before integrating it; a sign crossing leaves a triangle, not a trapezoid.
    const float share = min(values.x, values.y) < 0.0
                      ? max(positive.x, positive.y) / max(abs(values.y - values.x), 1e-20) : 1.0;
    return 0.25 * (interval.y - interval.x) * (positive.x + positive.y) * saturate(share);
}

float ErosionCliffFaceMean(float2 interval, float t, float radius, float height)
{
    interval = clamp(interval, -1.0, 1.0);
    [branch] if (interval.y <= interval.x) return 0.0;
    const float middle = 0.5 * (interval.x + interval.y), halfWidth = 0.5 * (interval.y - interval.x);
    const float2 samples = saturate(t + radius * (middle + halfWidth * float2(-0.57735026919, 0.57735026919)));
    const float2 cut = 1.0 - samples * samples * (3.0 - 2.0 * samples);
    // Two Gauss nodes integrate the cubic exactly on this physical piece, even when it is narrower than a cell.
    return 0.5 * halfWidth * height * (cut.x + cut.y);
}

float ErosionCliffMean(float h, float hc, float delta, float depth, float talus, float gradient, float radius)
{
    const float foot = EROSION_CLIFF_PLATFORM.x, height = hc - foot, platformSlope = 1.0 - depth / hc;
    const float bottom = (foot - depth) / platformSlope;
    [branch] if (h + radius <= bottom || h - radius >= hc + delta) return h;
    [branch] if (radius <= 0.0)
    {
        const float platform = foot - depth * (1.0 - min(h / hc, 1.0));
        return min(h, max(ErosionCliffProfile(h, hc, delta, depth),
                          platform + ErosionCliffScree(h, hc, delta, talus, gradient)));
    }
    const float contactT = ErosionCliffContact(hc, delta, talus), contact = hc + delta * contactT;
    const float slope = EROSION_CLIFF_SCREE.x / gradient, toe = contact - talus / slope;
    // Below the foot, the platform cut is linear. Where the apron takes over it is another positive-part line.
    float cut = ErosionCliffLinearMean((float2(bottom, min(toe, hc)) - h) / radius,
                                      platformSlope * (h - bottom), platformSlope * radius);
    cut += ErosionCliffLinearMean((float2(max(bottom, toe), hc) - h) / radius,
                                  height - talus + slope * delta * contactT + (platformSlope - slope) * (h - hc),
                                  (platformSlope - slope) * radius);
    const float t = (h - hc) / delta, r = radius / delta;
    float start = contactT;
    [branch] if (slope < 1.0 + 6.0 * height * contactT * (1.0 - contactT) / delta)
    {
        // The known contact root factors out of face-minus-apron. Its other root is quadratic on [0,contactT].
        const float q = delta * (1.0 - slope) + height * contactT * (3.0 - 2.0 * contactT);
        const float b = height * (3.0 - 2.0 * contactT);
        start = q >= 0.0 ? 0.0 : clamp(-2.0 * q / (b + sqrt(max(b * b + 8.0 * height * q, 0.0))), 0.0, contactT);
    }
    cut += ErosionCliffFaceMean((float2(0.0, start) - t) / r, t, r, height);
    cut += ErosionCliffLinearMean((float2(start, contactT) - t) / r,
                                  height + delta * contactT - talus + (1.0 - slope) * (h - contact), (1.0 - slope) * radius);
    cut += ErosionCliffFaceMean((float2(contactT, 1.0) - t) / r, t, r, height);
    return h - clamp(cut, 0.0, height);
}

// A gradient noise on the precise planet lattice. No float position multiplied by the planet's radius places a cliff.
float ErosionCliffNoise(RlPoint p, float km, uint seed)
{
    const RlCell l = RlSplit(p, (double)PLANET_RADIUS_KM / (double)km);
    return RlGradientNoise(l.cell, l.q, seed, true) / RL_SIGMA;
}

// The slope only includes detail broader than three maximum retreats. The full ground still supplies the contour:
// a spur below the platform's scale must not open a separate cut behind the cliff.
float ErosionCoastSlope(float3 formsGradient, float3 d, float3 detailSlope)
{
    const float3 ground = formsGradient / (1000.0 * PLANET_RADIUS_KM) + detailSlope;
    return length(ground - dot(ground, d) * d);
}

// The contour places the cliff; this bound only excludes low ground far inland. Detail can shift the shore by its
// amplitude divided by the coast's slope (km). Seaward land remains accessible within the outer proxy reach.
float ErosionCliffBand(float shoreKm, float retreat, float relief, float coastSlope)
{
    const float bound = min(retreat + EROSION_CLIFF_REACH.x + relief / coastSlope, EROSION_CLIFF_REACH.z);
    return 1.0 - smoothstep(bound - EROSION_CLIFF_REACH.y, bound, shoreKm);
}

// A marine witness within the largest retreat, in the same seaward direction as wave exposure. Read the uneroded
// ground there: river or glacial excavation cannot open this access. The small-angle rotation stays in doubles;
// a float planet position would move its noise by decimetres. No additional erosion-map query is needed.
double3 ErosionSeaPoint(double3 position, float3 formsGradient)
{
    const float3 d = (float3)position;
    const float3 slope = formsGradient - dot(formsGradient, d) * d;
    const float3 seaward = -slope / max(length(slope), 1e-6);
    const double a = (double)EROSION_CLIFF_RETREAT.z / (double)PLANET_RADIUS_KM, a2 = a * a;
    const double sn = a * (1.0 - a2 / 6.0 + a2 * a2 / 120.0), cs = 1.0 - a2 / 2.0 + a2 * a2 / 24.0;
    return position * cs + (double3)seaward * sn;
}

// A positive influence requires deep water at the witness, never just a local low floor. The depth threshold defines
// this conservative marine test; its transition is a distance converted by the witness's coastal slope.
float ErosionSeaAccess(float height, float coastSlope)
{
    return 1.0 - smoothstep(-EROSION_CLIFF_SEA.x - coastSlope * EROSION_CLIFF_SEA.y, -EROSION_CLIFF_SEA.x, height);
}

// Wave erosion follows a contour of the full ground, including detail, valleys and deposits. The large forms' shore
// distance only bounds its support: a mistaken shoreline cannot excavate high ground. All inputs remain pointwise.
float ErosionCoast(RlPoint p, float h, float shoreKm, float coastSlope, float rocky, float near,
                   float coastOffsetKm, float3 formsGradient, float erodibility, float cellKm, float3 detailSlope,
                   float relief, float shoreMetric)
{
    const float proxyBand = 1.0 - smoothstep(EROSION_CLIFF_REACH.z - EROSION_CLIFF_REACH.y, EROSION_CLIFF_REACH.z, abs(shoreKm));
    shoreKm /= shoreMetric;
    [branch] if (EROSION_CLIFF_RETREAT.x == 0.0 || proxyBand == 0.0 || rocky <= 0.3 || near <= 1e-3
                 || shoreKm >= EROSION_CLIFF_REACH.z) return h;
    const float shelter = smoothstep(EROSION_CLIFF_BAY.x, EROSION_CLIFF_BAY.y, coastOffsetKm);
    const float3 d = (float3)p.p;
    const float3 slope = formsGradient - dot(formsGradient, d) * d;
    const float3 seaward = -slope / max(length(slope), 1e-6);
    const float exposure = shelter * (EROSION_CLIFF_WAVES.x + (1.0 - EROSION_CLIFF_WAVES.x)
                                      * max(dot(-seaward, ErosionWaveWind(d)), 0.0));
    const float hard = 1.0 - smoothstep(0.45, 1.6, erodibility);
    const float presence = EROSION_CLIFF_RETREAT.x * smoothstep(0.3, 0.9, rocky) * smoothstep(1e-3, 0.05, near)
                         * shelter * max(hard, smoothstep(0.1, EROSION_CLIFF_WAVES.x, exposure));
    [branch] if (presence == 0.0) return h;
    const uint seed = (uint)PLANET_SEED * 4096u + 640u;
    const float variation = ErosionCliffNoise(p, EROSION_CLIFF_NOISE, seed);
    // Sunamura 1992: accumulated recession grows with wave force over rock resistance. Its distance sets the height
    // contour through the real ground's slope, not through an extrapolation of the point's own elevation.
    const float retreat = min(EROSION_CLIFF_RETREAT.z, EROSION_CLIFF_RETREAT.y * exposure * erodibility
                              * max(0.2, 1.0 + EROSION_CLIFF_RETREAT.w * variation));
    const float band = ErosionCliffBand(shoreKm, retreat, relief, coastSlope);
    [branch] if (band == 0.0) return h;
    // Keep the coastal gradient as a floor in hollows. It sets the physical contour and converts the sampling footprint.
    const float g = max(ErosionCoastSlope(formsGradient, d, detailSlope), max(coastSlope * shoreMetric * 0.001, 1e-6));
    const float hc = clamp(1000.0 * retreat * g, EROSION_CLIFF_HEIGHT.x, EROSION_CLIFF_HEIGHT.y);
    const float delta = EROSION_CLIFF_FACE * hc, footprint = 1000.0 * cellKm * g;
    const float depth = min(1000.0 * retreat * EROSION_CLIFF_PLATFORM.y, EROSION_CLIFF_PLATFORM.z);
    const float bottom = (EROSION_CLIFF_PLATFORM.x - depth) / (1.0 - depth / hc);
    [branch] if (h + footprint <= bottom || h - footprint >= hc + delta) return h;
    // Rockfall at nominally 35 degrees on the coastal slope, attached to the face at its talus height. It cannot
    // raise the original ground. Valley floors may breach this contour and remain inlets.
    const float patch = smoothstep(-0.2, 0.6, ErosionCliffNoise(p, 0.9, seed + 1u));
    const float talus = hc * EROSION_CLIFF_SCREE.y * patch;
    const float surface = ErosionCliffMean(h, hc, delta, depth, talus, g, footprint);
    // Sparse crossing bands preserve the original rock as a remnant; they never add a pillar's height. Their mask
    // broadens over two cells while its peak decreases, retaining the narrow band's area as ReliefWidth does.
    const float radius = EROSION_CLIFF_STACK.x, wide = max(radius, 2.0 * cellKm);
    const float x = ErosionCliffNoise(p, EROSION_CLIFF_STACK.y, seed + 2u) * EROSION_CLIFF_STACK.y;
    const float y = ErosionCliffNoise(p, EROSION_CLIFF_STACK.y, seed + 3u) * EROSION_CLIFF_STACK.y;
    const float remnants = smoothstep(EROSION_CLIFF_STACK.z, EROSION_CLIFF_STACK.z + 0.4, variation);
    const float edge = max(EROSION_CLIFF_FACE * radius, 2.0 * cellKm);
    const float stack = remnants * (radius * radius / (wide * wide))
                      * (1.0 - smoothstep(max(0.0, wide - edge), wide, abs(x)))
                      * (1.0 - smoothstep(max(0.0, wide - edge), wide, abs(y)));
    return lerp(h, surface, presence * proxyBand * band * (1.0 - stack));
}

#endif
