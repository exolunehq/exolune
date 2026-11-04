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

struct ErosionSection
{
    float d, z, floorWidth, curvature, glacier;
};

// The valleys around the point: the surface they carve, the share of their floor, the water's level there.
struct ErosionValley
{
    ErosionSection links[2];
    float walls, boxRadius;
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
    float ravines; // step A's ravines: their amplitude factor, the rock's, the climate's and the relief's; 0, none
    float3x3 oriented; // and the oriented point's Jacobian, row i its axis i along the point's: their octaves' true slope
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
                      out float glacier, out float rise, out float floorWidth, out float curvature)
{
    // The fluvial floor, wider on a gentle river; never wider than `widest`, so that it ends before the links read change.
    const float floodplain = EROSION_FLOOR.x * sqrt(q) * clamp(EROSION_FLOOR.y / max(slope, 1e-6), 1.0, EROSION_FLOOR.z);
    // The liquid channel belongs inside its valley. A narrower floor forced the later water pass to excavate banks.
    floorWidth = min(max(floodplain, ErosionRiverSize(q).x), widest);
    // A parabolic U above its drained floor (Hirano & Aniya 1988), extended by its tangent at the wall slope.
    // Subtracting an overdepth before clamping to water would flatten the whole U into a kilometre-wide ribbon.
    glacier = saturate(log2(max(ice, 1.0)) - EROSION_GLACIER.w);
    const float trough = clamp(EROSION_GLACIER.x * pow(max(ice, 1.0) / 1e8, EROSION_GLACIER.y), 150.0, 1500.0);
    curvature = EROSION_GLACIER.z / trough;
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

// The terminal lakes' stage at the point of texel coordinates x on `face`. A nearest-cell terminal stage creates vertical
// water walls wherever fine relief crosses a coarse divide. Reconstruct it continuously in a fixed physical band.
// Equal-stage interiors stay exactly level; connections between different basins are a stage transition, not a
// resolved hydraulic spillway. The basin's ID is the low half of its slice's second word (Erosion.h).
float ErosionLakeLevel(uint face, float2 x, uint n, float cellM)
{
    float level = 0.0;
    const float band = min(EROSION_LAKE_TRANSITION / cellM, 0.5);
    const float2 blend = smoothstep(0.5 - band, 0.5 + band, frac(x));
    [unroll] for (int lakeTap = 0; lakeTap < 4; ++lakeTap)
    {
        const int2 offset = int2(lakeTap & 1, lakeTap >> 1);
        const uint c = ErosionCell(face, (int2)floor(x) + offset, n);
        const uint2 basin = erosionMap.Load(int4(c % n, c / n % n, c / (n * n) + 6u, 0));
        const float2 weight = lerp(1.0 - blend, blend, (float2)offset);
        if (EROSION_WATER > 0.0 && (basin.y & 0xffffu) != 0u)
            level += weight.x * weight.y * max(0.0, (float)(basin.x & 0xffffu) * 0.25 - 8192.0);
    }
    return level;
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
    v.lakeLevel = ErosionLakeLevel(face, x, n, cellM);
    v.flow = 0.0;
    v.channelBed = 1e9, v.channelSurface = 1e9;
    v.channelDistance = 1e9;
    float guideSurface = 1e9;
    const float wide = 2000.0 * cellKm;
    v.walls = walls, v.boxRadius = max(0.5 * wide, CREASE_MIN_CELL);
    v.links[0] = (ErosionSection)0, v.links[1] = (ErosionSection)0;
    v.links[0].z = v.links[1].z = 1e9;
    float secondCandidate = 1e9;
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
                float glacier, rise, floorWidth, curvature;
                const float2 s = ErosionProfile(d, z, q, ice, waterSlope, walls, wide, 0.15 * cellM, glacier, rise, floorWidth, curvature);
                // Past three quarters of the reach the valley rises out of every ground: the links read change there.
                const float beyond = smoothstep(0.35, 0.5, d / cellM);
                const float candidate = s.x + 1e4 * beyond;
                // The carved envelope is the union of the profiles, each already above its own drainage level.
                // Only the slope guiding the gullies blends over 60 m at divides; it must not jump between links.
                const float guide = saturate(0.5 + 0.5 * (guideSurface - candidate) / EROSION_SMOOTH);
                v.gradient = lerp(v.gradient, -rise * nearestPoint / max(length(nearestPoint), 1e-12), guide);
                guideSurface = lerp(guideSurface, candidate, guide) - EROSION_SMOOTH * guide * (1.0 - guide);
                ErosionSection link;
                link.d = d, link.z = z + 1e4 * beyond, link.floorWidth = floorWidth;
                link.curvature = curvature, link.glacier = glacier;
                [branch] if (candidate < v.surface)
                {
                    v.links[1] = v.links[0], secondCandidate = v.surface;
                    v.links[0] = link;
                    v.surface = candidate;
                    v.level = z;
                }
                else if (candidate < secondCandidate)
                    v.links[1] = link, secondCandidate = candidate;
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

float ErosionBoxRamp(float x, float radius)
{
    const float tail = max(radius - abs(x), 0.0);
    return max(x, 0.0) + tail * tail / (4.0 * radius);
}

float ErosionBoxPositiveSquare(float x, float radius)
{
    const float positive = max(x, 0.0);
    return positive * positive + ErosionBoxSquareExcess(x, radius).x;
}

// The distance from the axis where a link's section, fluvial and glacial mixed by its glacier share, rises `depth`
// above its level. The section is quadratic between its floor's edge f and the trough's shoulder s; on that piece,
// a t^2 + b t + g = depth, solved without cancellation when a vanishes.
float ErosionSectionCrossing(float depth, float f, float s, float c, float walls, float glacier)
{
    const float lo = min(f, s), hi = max(f, s);
    const float2 edges = float2(lo, hi);
    const float2 rises = (1.0 - glacier) * walls * max(edges - f, 0.0)
                       + glacier * (c * min(edges, s) * min(edges, s) + EROSION_GLACIER_WALLS * max(edges - s, 0.0));
    const float at = depth <= rises.x ? 0.5 * lo : depth <= rises.y ? 0.5 * (lo + hi) : hi + 1.0;
    const bool floor = at < f, trough = at < s;
    const float a = trough ? glacier * c : 0.0;
    const float b = (trough ? 0.0 : glacier * EROSION_GLACIER_WALLS) + (floor ? 0.0 : (1.0 - glacier) * walls);
    const float g = (trough ? 0.0 : glacier * (c * s * s - EROSION_GLACIER_WALLS * s)) - (floor ? 0.0 : (1.0 - glacier) * walls * f);
    const float rest = max(depth - g, 0.0);
    return 2.0 * rest / max(b + sqrt(b * b + 4.0 * a * rest), 1e-20);
}

// The mean over the box of radius `radius` of a link's physical section clipped by a ground constant across it: the
// incision a sample shows, its area kept at every footprint. Averaging the section before clipping it raised a narrow
// valley's floor above the ground once the box outgrew it, and the whole valley vanished from far away. The clipped
// part is the section less its excess above the ground, each term a stable box mean of ramps and squares.
float ErosionClippedSection(ErosionSection link, float ground, float walls, float radius)
{
    const float depth = ground - link.z;
    if (depth <= 0.0 || link.curvature <= 0.0) return ground;
    const float d = link.d, f = link.floorWidth, c = link.curvature;
    const float shoulder = EROSION_GLACIER_WALLS / (2.0 * c);
    const float u = min(d, shoulder);
    const float glacial = c * u * u + EROSION_GLACIER_WALLS * max(d - shoulder, 0.0)
        + c * max(radius * radius / 3.0 - ErosionBoxSquareExcess(d - shoulder, radius).x
                  - ErosionBoxSquareExcess(-d - shoulder, radius).x, 0.0);
    const float fluvial = walls * (ErosionBoxRamp(d - f, radius) + ErosionBoxRamp(-d - f, radius));
    // One crossing for the mixed section: clipping each shape at its own crossing and mixing them is another section.
    const float x = ErosionSectionCrossing(depth, f, shoulder, c, walls, link.glacier);
    const float xF = max(f, x);
    const float excessF = walls * (ErosionBoxRamp(d - xF, radius) + ErosionBoxRamp(-d - xF, radius));
    float excessG = 0.0;
    [unroll] for (int side = 0; side < 2; ++side)
    {
        const float e = side == 0 ? d : -d;
        if (x >= shoulder)
            excessG += EROSION_GLACIER_WALLS * ErosionBoxRamp(e - x, radius);
        else
            excessG += c * (ErosionBoxPositiveSquare(e - x, radius)
                + 2.0 * x * ErosionBoxRamp(e - x, radius)
                - ErosionBoxPositiveSquare(e - shoulder, radius));
    }
    return clamp(link.z + lerp(fluvial - excessF, glacial - excessG, link.glacier), link.z, ground);
}

float ErosionCarve(float h, float coarse, ErosionValley v, float k)
{
    // Existing hollows already belong to h. Adding their negative residual to the cut a second time dug side trenches
    // below the draining floor while leaving a perched river in the middle. Only positive spurs decorate the envelope;
    // this C1 positive part uses the existing join scale, and h remains the upper bound, including in a deep hollow.
    const float detail = h - coarse, tail = max(k - abs(detail), 0.0);
    const float spurs = max(detail, 0.0) + tail * tail / (4.0 * k);
    const float lift = spurs * (1.0 - v.floorShare), ground = h - lift;
    const float surface = min(ErosionClippedSection(v.links[0], ground, v.walls, v.boxRadius),
                              ErosionClippedSection(v.links[1], ground, v.walls, v.boxRadius)) + lift;
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

// Wave erosion follows the full supporting ground. Step-B river corridors meet this independent coastal envelope;
// they do not supply a second, artificially lowered input. The large forms' shore distance only bounds support.
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

// ---------------------------------------------------------------------------------------------
// Step B: the rivers' corridors (docs/spec-erosion.md), ported from the CPU prototype tools/hydro/couloirs.py. The level
// 0's links whose discharge reaches RIVER_Q.x, drawn as courses: their curve displaced by the meanders, a floodplain at
// the bank's height, a wall up to the relief, a channel with water from RIVER_Q.y; each sized by its discharge, its rock
// and its relief. Their stages are conditioned at startup.
// ---------------------------------------------------------------------------------------------

// A cell, read for its courses: its node relative to the reference point, less its rest (the node less the reference's
// float, exact between neighbours); its conditioned stage (m), log2 of its discharge, its corridor's wall width (m), its
// meanders' sinuosity and log2 of its valley floor's factor, the high halves of the terminal-lake slice (Erosion.h).
struct ErosionRiverNode
{
    float3 at;
    float stage, lq, wall, sinuous, floorLog, lake;
    float4 stops;
    uint code, outCode, graphCode, bits;
    bool broken; // outgoing flow reaches water before its receiving node
};

ErosionRiverNode ErosionRiverNodeAt(uint c, uint n, float3 pf)
{
    const uint2 t = erosionMap.Load(int4(c % n, c / n % n, c / (n * n), 0));
    const uint2 k = erosionMap.Load(int4(c % n, c / n % n, c / (n * n) + 6u, 0));
    ErosionRiverNode v;
    v.at = ErosionNode(c, n) - pf;
    const uint2 limits = erosionMap.Load(int4(c % n, c / n % n, c / (n * n) + 12u, 0));
    const uint2 flow = erosionMap.Load(int4(c % n, c / n % n, c / (n * n) + 18u, 0));
    v.stops = float4(limits.x & 65535u, limits.x >> 16, limits.y & 65535u, limits.y >> 16) / 65535.0;
    v.bits = t.y, v.graphCode = t.y >> 16 & 255u, v.code = flow.x & 255u, v.outCode = flow.x >> 8 & 255u;
    v.broken = (flow.x & 65536u) != 0u;
    v.lq = (float)v.code / 8.0 - 8.0;
    v.stage = (float)(k.x >> 16) * 0.25 - 8192.0;
    v.lake = (float)(k.x & 65535u) * 0.25 - 8192.0;
    v.wall = (float)(k.y >> 16 & 255u) * 25.0;
    v.sinuous = RIVER_SINUOUS.z + (1.0 - RIVER_SINUOUS.z) * (float)(k.y >> 24 & 15u) / 15.0;
    v.floorLog = RIVER_FLOOR_LOG2.x + (RIVER_FLOOR_LOG2.y - RIVER_FLOOR_LOG2.x) * (float)(k.y >> 28) / 15.0;
    return v;
}

// A course: a quadratic Bezier, its controls relative to the reference point, unprojected; and its attributes' controls
// along it, x at its start, y the middle one, z at its end: the stage (m), log2 of the discharge, the wall width (m), the
// sinuosity and log2 of the floor's factor.
struct ErosionCourse
{
    float3 a, b, c;
    float3 stage, lq, traceLq, wall, sinuous, floorLog;
    float3 flare; // receiving physical/nominal half-widths and signed downstream-bank opening; zero away from confluences
    float3 fan;   // marine distributary spread, zero at the upstream join
    float2 stops, partLq; // main half limits and incoming/node discharge; a single limit on other courses
    bool split, fanFirst;
    bool mouth;  // a terminal reach may open into its actual receiving lake or sea
    bool taper; // a re-routed tributary: its meanders fade over its last 40 %, to arrive on the main channel
    bool dry;   // a head's valley, above its river: no channel
};

float3 ErosionBezier3(float3 a, float3 b, float3 c, float t)
{
    const float s = 1.0 - t;
    return s * s * a + 2.0 * s * t * b + t * t * c;
}

float ErosionBezier(float3 k, float t)
{
    const float s = 1.0 - t;
    return s * s * k.x + 2.0 * s * t * k.y + t * t * k.z;
}

// Its direction at t, unnormalised; a repeated control's straight run has its regular limit.
float3 ErosionCourseTangent(ErosionCourse k, float t)
{
    return all(k.a == k.b) || all(k.b == k.c) ? k.c - k.a : lerp(k.b - k.a, k.c - k.b, t);
}

// A meander octave of wavelength `wave` (m): x its amplitude (m), a share of its wavelength, faded in from 0.7 to 1.4 of
// the finest; y the share of it bending the valley, the rest bending the channel within its floodplain.
float2 ErosionMeanderOctave(float wave, float finest, float sinuous)
{
    const float r = wave / finest;
    const float share = RIVER_MEANDER.w + (RIVER_MEANDER.z - RIVER_MEANDER.w) * (1.0 - smoothstep(2.0, 4.0, r));
    const float valley = max(smoothstep(RIVER_SPLIT / 1.4, RIVER_SPLIT * 1.4, r),
                             smoothstep(RIVER_CHANNEL_WAVE, 2.0 * RIVER_CHANNEL_WAVE, wave));
    return float2(share * wave * smoothstep(0.7, 1.4, r) * sinuous, valley);
}

// The floodplain's meanders' bound (m), twice their amplitudes, and the valley's amplitudes summed; at a discharge's
// finest wavelength, 12 channel widths.
float2 ErosionMeanderBounds(float finest, float sinuous)
{
    float2 sum = 0.0;
    [loop] for (int o = 0; o < 10; ++o)
    {
        const float wave = RIVER_MEANDER.x * exp2(-(float)o);
        if (wave < 0.7 * finest) break;
        const float2 m = ErosionMeanderOctave(wave, finest, sinuous);
        sum += m.x * float2(2.0 * (1.0 - m.y), m.y);
    }
    return sum;
}

float ErosionFinest(float lq)
{
    return RIVER_MEANDER.y * 2.0 * ErosionRiverSize(exp2(lq)).x;
}

// A noise of wavelength `wave` (m) at the course's point q, within +-1: the valley (17) and finer water widths (18, 19).
float ErosionCourseNoise(RlPoint ref, float3 q, float wave, uint salt)
{
    const double f = (double)(1000.0 * PLANET_RADIUS_KM / wave);
    const float weight = RlWeight((float)f);
    // The filtered octave's exact mean is zero. Do not split the lattice or hash its eight corners
    // after the footprint has removed it; this is the same bandwidth rule as ReliefNoiseD.
    [branch] if (weight <= 0.0) return 0.0;
    const RlCell l = RlSplit(ref, f);
    const float n = weight * RlGradientNoise(l.cell, l.q + q * (float)f, (uint)PLANET_SEED * 4096u + 64u * 40u + salt, true);
    return clamp(n / (2.0 * RL_SIGMA), -1.0, 1.0);
}

// Coarse confinement follows the valley's opening. Finer widths share the same global field at every curve join.
// A centred linear modulation stays positive and its filtered mean stays nominal; the bound is 1+y.
float ErosionWidthFactor(RlPoint ref, float3 q, float opening)
{
    const float n = 0.5 * opening + 0.3 * ErosionCourseNoise(ref, q, RIVER_WIDTH_NOISE.x, 18u)
                  + 0.2 * ErosionCourseNoise(ref, q, 0.25 * RIVER_WIDTH_NOISE.x, 19u);
    return 1.0 + RIVER_WIDTH_NOISE.y * n;
}

// Bank relief is sampled on the terrain, so opposing banks do not repeat one height sequence.
// Each octave has a zero mean and the same bandwidth rule as the surrounding ground.
float ErosionBankFactor(RlPoint ref)
{
    const float n = 0.55 * ErosionCourseNoise(ref, 0.0, RIVER_BANK_DETAIL.x, 20u)
                  + 0.30 * ErosionCourseNoise(ref, 0.0, RIVER_BANK_DETAIL.x * 0.25, 21u)
                  + 0.15 * ErosionCourseNoise(ref, 0.0, RIVER_BANK_DETAIL.x * 0.0625, 22u);
    return 1.0 + RIVER_BANK_DETAIL.y * n;
}

// Retain the existing 2D mountain residual, not a second profile copied on both sides of the drainage axis.
// Positive spurs reduce incision, bounded by the original ground. Negative residuals never create a second trench.
// Both the positive part and its onset at the bank are C1; neither depends on the sampling radius.
float ErosionSpurRelief(float ground, float parent, float fine)
{
    const float residual = max(ground - parent - fine, 0.0), rounding = RIVER_SPURS.y;
    return residual < rounding ? 0.5 * residual * residual / rounding : residual - 0.5 * rounding;
}

float ErosionSpurLift(float ground, float parent, float fine, float bankLevel, float keep)
{
    const float spur = ErosionSpurRelief(ground, parent, fine), rounding = RIVER_SPURS.y;
    const float above = max(ground - bankLevel, 0.0);
    return keep * (above * above / (above + rounding)) * spur / max(above + spur, 1e-6);
}

// Retaining a high spur in a short bank transition must not manufacture a long slot canyon. Its added height needs
// horizontal room: a C1 envelope from the physical dry bank. Preserve small lifts exactly; approach the envelope
// monotonically as the mountain grows. The base valley profile and its broad gorges keep their own shape.
float ErosionSpurBankLift(float lift, float run)
{
    run = max(run, 0.0);
    const float allowance = RIVER_SPURS.z * run * run / (run + RIVER_SPURS.y / RIVER_SPURS.z);
    return lift <= 0.5 * allowance ? lift : allowance * (1.0 - 0.25 * allowance / max(lift, 1e-9));
}

// Mountain masses change the corridor outline, not just its interior height. Contraction stays inside the original
// search bound and cannot deepen the dry profile's incision; the two sides read different parts of the 2D terrain.
float ErosionConfinement(float ground, float parent, float fine, float bankLevel)
{
    const float above = max(ground - bankLevel, 0.0) + RIVER_SPURS.y;
    const float spur = ErosionSpurRelief(ground, parent, fine);
    return lerp(RIVER_CONFINEMENT.x, 1.0, above / (above + RIVER_CONFINEMENT.y * spur));
}

// A course's depth share at log2 of its discharge: 0 at RIVER_Q.x, 1 from RIVER_Q.y, where its water starts.
float ErosionCourseShare(float lq)
{
    // A narrow, shallow tributary grows before the broad corridor. C1 at both thresholds; mature valleys stay intact.
    // A log-discharge smoothstep over 200..300 made the entire opening occur within roughly one coarse graph cell.
    const float t = saturate((exp2(lq) - RIVER_Q.x) / (RIVER_Q.y - RIVER_Q.x));
    return t * t * (3.0 - 2.0 * t);
}

// The walls' profile at x, 0 at the floor's edge to 1 at the relief: a ramp rounded into both over a share r of its width,
// C1, its slope 1 / (1 - r) between; at log2 of the discharge lq, r from RIVER_WALL.x to y.
float ErosionWallProfile(float x, float lq)
{
    const float r = lerp(RIVER_WALL.x, RIVER_WALL.y, smoothstep(log2(RIVER_Q.y), log2(RIVER_WALL.z), lq));
    const float t = saturate(x), s = 1.0 / (1.0 - r);
    return t < r ? 0.5 * s * t * t / r : t > 1.0 - r ? 1.0 - 0.5 * s * (1.0 - t) * (1.0 - t) / r : s * (t - 0.5 * r);
}

// Freeze the local terrain and course fields, then average the composed incision, including spur recovery.
// A narrow section must retain its area when the sampling grid slides or its footprint grows.
struct ErosionCorridorSection
{
    float2 distance;
    float along, ratio, floor, outer, rounding, bank, keep;
    float height, spur, rough, cutShare, fillShare;
};

float4 ErosionCorridorProfile(float4 x, ErosionCorridorSection s)
{
    const float4 v = s.distance.x + x, c = s.distance.y + s.ratio * x;
    const float4 dv = sqrt(s.along * s.along + v * v), dc = sqrt(s.along * s.along + c * c);
    const float4 t = saturate((dv - s.floor) / (s.outer - s.floor));
    const float r = s.rounding, scale = 1.0 / (1.0 - r);
    float4 g = lerp(scale * (t - 0.5 * r), 0.5 * scale * t * t / r, 1.0 - step(r, t));
    g = lerp(g, 1.0 - 0.5 * scale * (1.0 - t) * (1.0 - t) / r, step(1.0 - r, t));
    const float4 rough = s.rough * smoothstep(2.0 * s.bank, 4.0 * s.bank, dc);
    const float4 above = max(s.height - rough, 0.0);
    float4 lift = smoothstep(2.0 * s.bank, s.keep, dc) * above * above / (above + RIVER_SPURS.y)
                  * s.spur / max(above + s.spur, 1e-6);
    const float4 run = max(dc - 2.0 * s.bank, 0.0);
    const float4 allowance = RIVER_SPURS.z * run * run / (run + RIVER_SPURS.y / RIVER_SPURS.z);
    // The unused cap can be huge and negative when lift is tiny. Never lerp it back to lift: that loses metres in float.
    lift = min(lift, allowance * (1.0 - 0.25 * allowance / max(lift, max(0.5 * allowance, 1e-9))));
    const float4 delta = (rough - s.height + lift) * (1.0 - g);
    return delta * lerp(s.cutShare, s.fillShare, step(0.0, delta));
}

float ErosionCorridorIntegral(float lo, float hi, ErosionCorridorSection s)
{
    const float4 x = lo + (hi - lo) * float4(0.0694318442, 0.3300094782, 0.6699905218, 0.9305681558);
    return (hi - lo) * dot(ErosionCorridorProfile(x, s), float4(0.1739274226, 0.3260725774, 0.3260725774, 0.1739274226));
}

float ErosionCorridorMean(ErosionCorridorSection s, float radius)
{
    if (abs(s.along) >= s.outer) return 0.0;
    // Roughness lies between zero and s.rough; recovered spurs are nonnegative. If the whole
    // section could only fill and filling is absent, every quadrature sample is exactly zero.
    if (s.fillShare <= 0.0 && s.height <= min(s.rough, 0.0)) return 0.0;
    float edges[16];
    edges[0] = -radius, edges[1] = radius;
    const float wall = s.outer - s.floor;
    const float4 boundaries = float4(s.floor, s.floor + s.rounding * wall, s.outer - s.rounding * wall, s.outer);
    [unroll] for (int i = 0; i < 4; ++i)
    {
        const float reach = sqrt(max(boundaries[i] * boundaries[i] - s.along * s.along, 0.0));
        edges[2 + 2 * i] = -s.distance.x - reach;
        edges[3 + 2 * i] = -s.distance.x + reach;
    }
    const float3 banks = float3(2.0 * s.bank, 4.0 * s.bank, s.keep);
    [unroll] for (int j = 0; j < 3; ++j)
    {
        const float reach = sqrt(max(banks[j] * banks[j] - s.along * s.along, 0.0));
        edges[10 + 2 * j] = (-s.distance.y - reach) / s.ratio;
        edges[11 + 2 * j] = (-s.distance.y + reach) / s.ratio;
    }
    bool split = false;
    [unroll] for (int b = 2; b < 16; ++b)
    {
        split = split || abs(edges[b]) < radius;
        edges[b] = clamp(edges[b], -radius, radius);
    }
    if (split)
    {
    [unroll] for (int width = 2; width <= 16; width *= 2)
        [unroll] for (int stride = width / 2; stride > 0; stride /= 2)
            [unroll] for (int k = 0; k < 16; ++k)
            {
                const int other = k ^ stride;
                if (other > k)
                {
                    const float lo = min(edges[k], edges[other]), hi = max(edges[k], edges[other]);
                    edges[k] = (k & width) == 0 ? lo : hi;
                    edges[other] = (k & width) == 0 ? hi : lo;
                }
            }
    }
    // One integral call site for both the unsplit section and the sorted intervals.
    float sum = 0.0;
    [loop] for (int part = 0; part < (split ? 15 : 1); ++part)
        if (edges[part + 1] > edges[part]) sum += ErosionCorridorIntegral(edges[part], edges[part + 1], s);
    return sum / (2.0 * radius);
}

// The valley floor's half-width (m) by the law, at discharge q and log2 of the floor's factor, before its noise.
float ErosionValleyFloor(float q, float floorLog)
{
    return 0.5 * RIVER_FLOOR.x * pow(q, RIVER_FLOOR.y) * exp2(floorLog);
}

// The meanders at a course's parameter t (Leopold and Wolman 1960): x the valley's offset to the left (m), y its slope
// along `along`, a unit tangent, z and w the channel's within the floodplain, each bounded by a tanh. A fractal of 3D
// noise read at the course's point on the sphere, the chordal curve's point taken radially: the same for every reference
// point; filtered by the mesh as any octave. q: that point, relative to the reference. valley: x the floor's half-width
// (m), the law's times its noise along the course, y that noise. The floodplain's meanders bend the channel within the
// floor as far as it allows, the valley with it beyond: in a gorge, incised meanders; the channel's course is the same.
float4 ErosionMeander(ErosionCourse k, float t, RlPoint ref, float3 pf, float3 along, out float3 q, out float2 valley)
{
    const float3 b = ErosionBezier3(k.a, k.b, k.c, t);
    const float s2 = 2.0 * dot(pf, b) + dot(b, b);
    q = b * (1.0 - 0.5 * s2) - pf * (0.5 * s2 - 0.375 * s2 * s2);
    const float lq = ErosionBezier(k.traceLq, t);
    valley.y = ErosionCourseNoise(ref, q, RIVER_VALLEY_NOISE.x, 17u);
    valley.x = min(ErosionValleyFloor(exp2(lq), ErosionBezier(k.floorLog, t)) * exp2(RIVER_VALLEY_NOISE.y * valley.y), RIVER_FLOOR.z);
    // Every finer octave also has zero weight. Its amplitude budget only acts on a zero displacement.
    [branch] if (RlWeight((1000.0 * PLANET_RADIUS_KM) / RIVER_MEANDER.x) <= 0.0) return 0.0;
    const float finest = ErosionFinest(lq), sinuous = ErosionBezier(k.sinuous, t);
    const uint seed = (uint)PLANET_SEED * 4096u + 64u * 40u;
    float4 m = 0.0;
    float fine = 0.0;
    [loop] for (int o = 0; o < 10; ++o)
    {
        const float wave = RIVER_MEANDER.x * exp2(-(float)o);
        if (wave < 0.7 * finest) break;
        const float2 octave = ErosionMeanderOctave(wave, finest, sinuous);
        fine += 2.0 * octave.x * (1.0 - octave.y);
        const double f = (double)(1000.0 * PLANET_RADIUS_KM / wave);
        const float w = RlWeight((float)f);
        [branch] if (w > 0.0)
        {
            const RlCell l = RlSplit(ref, f);
            const float4 n = RlGradientNoiseD(l.cell, l.q + RlShift(o) + q * (float)f, seed + (uint)o);
            const float2 v = float2(n.x, dot(n.yzw, along) / wave) * (w * octave.x / RL_SIGMA);
            m += float4(octave.y * v, (1.0 - octave.y) * v);
        }
    }
    const float kf = max(fine, 1e-9), tc = tanh(m.x / RIVER_OFFSET_MAX), tf = tanh(m.z / kf);
    const float free = saturate((valley.x - 2.0 * ErosionRiverSize(exp2(lq)).x) / kf), offset = kf * tf, slope = m.w * (1.0 - tf * tf);
    return float4(RIVER_OFFSET_MAX * tc + (1.0 - free) * offset, m.y * (1.0 - tc * tc) + (1.0 - free) * slope, free * offset, free * slope);
}

// The level 0's cell's side at its node, relative to the widest, at the faces' centres: the courses' extensions follow it.
float ErosionCellScale(uint c, uint n)
{
    const float2 st = (float2(c % n, c / n % n) + 0.5) * 2.0 / n - 1.0;
    const float k = 1.0 + dot(st, st);
    return min(sqrt(1.0 + st.y * st.y), sqrt(1.0 + st.x * st.x)) / k;
}

float ErosionFanStrength(float discharge, float grade, float wall)
{
    return smoothstep(RIVER_DELTA.x, RIVER_DELTA.y, discharge) * (1.0 - smoothstep(0.002, 0.01, grade))
           * (1.0 - smoothstep(600.0, 1600.0, wall));
}

// The courses of node r: its main course, from the midpoint with its largest inflow, or from itself at a head, through
// it, to the midpoint with its receiver, or to itself at an outlet; whether a head's dry valley continues it upstream, an
// outlet's line downstream; its other inflows carrying a river, to be re-routed to it. False: no river at r.
struct ErosionNodeCourses
{
    ErosionCourse main;
    ErosionRiverNode r;
    bool head, outlet;
    uint mainInflow, connectors; // the largest inflow, 8 for none; the re-routed ones, by neighbour
    float scale;
};

bool ErosionMainCourse(uint r, uint n, float3 pf, float3 rest, out ErosionNodeCourses v)
{
    v = (ErosionNodeCourses)0;
    v.r = ErosionRiverNodeAt(r, n, pf);
    const uint bits = v.r.bits;
    v.outlet = (bits & (EROSION_SEA | EROSION_LAKE)) != 0;
    // A midpoint's discharge, sqrt(q q'), reaches RIVER_Q.x from this sum of the two bytes: compared as integers.
    const float twice = 16.0 * (log2(RIVER_Q.x) + 8.0);
    ErosionRiverNode down = v.r;
    if (!v.outlet)
    {
        if (!(bits & EROSION_HAS_RECEIVER)) return false;
        down = ErosionRiverNodeAt(ErosionNeighbour(r, bits & 7u, n), n, pf);
    }
    // Raw cumulative flow bounds every surviving inflow. Skip inactive subcatchments before reading their tributaries.
    // One quantization code of slack covers separate floating-point accumulations of original and surviving runoff.
    if ((float)(2u * (max(v.r.graphCode, down.graphCode) + 1u)) < twice) return false;
    ErosionRiverNode up = v.r;
    v.mainInflow = 8u;
    [loop] for (uint m = bits >> 4 & 255u; m != 0u; m &= m - 1u)
    {
        const uint kq = firstbitlow(m);
        const ErosionRiverNode u = ErosionRiverNodeAt(ErosionNeighbour(r, kq, n), n, pf);
        const uint targetCode = u.stops.z < 1.0 ? u.outCode : v.r.code;
        if ((float)(u.outCode + targetCode) >= twice) v.connectors |= 1u << kq;
        if (v.mainInflow == 8u || u.graphCode > up.graphCode) v.mainInflow = kq, up = u;
    }
    if (v.outlet && v.mainInflow == 8u) return false; // an outlet without inflow carves nothing
    const bool inflow = v.mainInflow < 8u;
    if ((float)(v.r.code + (v.r.broken ? v.r.code : down.code)) < twice
        && (!inflow || (float)(2u * up.outCode) < twice) && v.connectors == 0u) return false;
    v.head = !inflow || (float)(up.graphCode + v.r.graphCode) < twice;
    up.lq = (float)up.outCode / 8.0 - 8.0;
    v.connectors &= inflow ? ~(1u << v.mainInflow) : 0xffu;
    ErosionCourse k;
    k.b = v.r.at - rest;
    k.a = inflow ? 0.5 * (up.at + v.r.at) - rest : k.b;
    k.c = v.outlet ? k.b : 0.5 * (v.r.at + down.at) - rest;
    float4 start = inflow ? 0.5 * float4(up.stage + v.r.stage, up.lq + v.r.lq, up.wall + v.r.wall, up.sinuous + v.r.sinuous)
                                : float4(v.r.stage, v.r.lq, v.r.wall, v.r.sinuous);
    float4 end = 0.5 * float4(v.r.stage + down.stage, v.r.lq + down.lq, v.r.wall + down.wall, v.r.sinuous + down.sinuous);
    // A cut edge carries its source discharge up to the contact. The receiver's local runoff is unrelated:
    // averaging it into the shared midpoint made the source disappear and the receiving half restart abruptly.
    if (inflow && up.broken) start.y = up.lq;
    if (v.r.broken) end.y = v.r.lq;
    k.stage = float3(start.x, v.r.stage, end.x), k.lq = float3(start.y, v.r.lq, end.y);
    // Re-accumulating surviving discharge changes width, never the world-space trace measured by the contact pass.
    k.traceLq = float3(inflow ? 0.5 * (up.graphCode + v.r.graphCode) : v.r.graphCode,
                      v.r.graphCode, 0.5 * (v.r.graphCode + down.graphCode)) / 8.0 - 8.0;
    k.wall = float3(start.z, v.r.wall, end.z), k.sinuous = float3(start.w, v.r.sinuous, end.w);
    k.floorLog = float3(inflow ? 0.5 * (up.floorLog + v.r.floorLog) : v.r.floorLog, v.r.floorLog, 0.5 * (v.r.floorLog + down.floorLog));
    k.taper = false, k.dry = false;
    k.flare = 0.0, k.fan = 0.0;
    k.stops = v.r.stops.xy, k.partLq = float2(up.lq, v.r.lq), k.split = true, k.fanFirst = false;
    k.mouth = ((v.r.bits | down.bits) & (EROSION_LAKE | EROSION_SEA)) != 0u || any(k.stops < 1.0);
    if ((v.r.bits & EROSION_SEA) != 0u)
    {
        const float grade = start.x / max(length(k.b - k.a) * (1000.0 * PLANET_RADIUS_KM), 1.0);
        const float fan = ErosionFanStrength(exp2(v.r.lq), grade, v.r.wall);
        // Spread over the whole terminal reach, including its extension. Holding the spread at the sea node
        // made three parallel canals for the rest of the outlet, rather than a continuing fan.
        const float upstream = length(k.b - k.a) * (1000.0 * PLANET_RADIUS_KM);
        const float through = upstream / max(upstream + RIVER_EXTEND.x * ErosionCellScale(r, n) * v.r.stops.w, 1.0);
        k.fan = float3(0.0, fan * through, fan * through);
    }
    // A detailed coast can precede the coarse sea node. Its real first contact, not that distant node, is the fan mouth.
    if (v.r.lake <= 0.0 && any(k.stops < 1.0))
    {
        const bool first = k.stops.x < 1.0 && (k.stops.y >= 1.0 || up.outCode > v.r.code);
        const float begin = first ? 0.0 : 0.5, end = first ? 0.5 * k.stops.x : 0.5 + 0.5 * k.stops.y;
        const float run = length(ErosionBezier3(k.a, k.b, k.c, end) - ErosionBezier3(k.a, k.b, k.c, begin)) * (1000.0 * PLANET_RADIUS_KM);
        const float discharge = exp2(first ? up.lq : v.r.lq), width = ErosionRiverSize(discharge).x;
        const float fan = ErosionFanStrength(discharge, max(ErosionBezier(k.stage, begin), 0.0) / max(run, 1.0), ErosionBezier(k.wall, end))
                        * smoothstep(4.0 * width, 12.0 * width, run);
        k.fan = (float3(0.0, 0.5, 1.0) - begin) * (fan / max(end - begin, 1e-3));
        k.fanFirst = first;
    }
    v.main = k;
    v.scale = ErosionCellScale(r, n);
    return true;
}

// Above a head, its dry valley rises at RIVER_EXTEND.z into the relief, straight on from the course's start.
ErosionCourse ErosionHeadCourse(ErosionNodeCourses v)
{
    ErosionCourse k = v.main;
    const float extent = RIVER_EXTEND.y * v.scale;
    k.c = v.main.a;
    k.a = k.c - extent / (1000.0 * PLANET_RADIUS_KM) * normalize(ErosionCourseTangent(v.main, 0.0));
    k.b = 0.5 * (k.a + k.c);
    const float z = v.main.stage.x, rise = RIVER_EXTEND.z * extent;
    k.stage = float3(z + rise, z + 0.5 * rise, z);
    k.lq = v.main.lq.x, k.wall = v.main.wall.x, k.sinuous = v.main.sinuous.x, k.floorLog = v.main.floorLog.x;
    k.traceLq = v.main.traceLq.x;
    k.dry = true;
    k.fan = 0.0;
    k.stops = 1.0, k.split = false, k.fanFirst = false;
    return k;
}

// Past an outlet, its river continues at its level along its last direction, to reach the detailed coast.
ErosionCourse ErosionOutletCourse(ErosionNodeCourses v)
{
    ErosionCourse k = v.main;
    k.a = v.main.b;
    k.c = k.a + RIVER_EXTEND.x * v.scale / (1000.0 * PLANET_RADIUS_KM) * normalize(v.main.b - v.main.a);
    k.b = 0.5 * (k.a + k.c);
    k.stage = v.main.stage.z, k.lq = v.main.lq.z, k.wall = v.main.wall.z, k.sinuous = v.main.sinuous.z, k.floorLog = v.main.floorLog.z;
    k.traceLq = v.main.traceLq.z;
    const float upstream = max(length(v.main.b - v.main.a) * (1000.0 * PLANET_RADIUS_KM), 1.0);
    const float fanEnd = v.main.fan.z * (1.0 + RIVER_EXTEND.x * v.scale / upstream);
    k.fan = float3(v.main.fan.z, 0.5 * (v.main.fan.z + fanEnd), fanEnd);
    k.stops = v.r.stops.y < 1.0 ? 0.0 : v.r.stops.w, k.split = false, k.fanFirst = false;
    return k;
}

// The first t from 0.5 where a main course's stage, non-increasing, is down to zS: the Bezier's root without cancellation.
float ErosionJunction(ErosionCourse main, float zS)
{
    const float3 z0 = main.stage - zS;
    const float t = z0.x <= 0.0 ? 0.0 : z0.x / max(z0.x - z0.y + sqrt(max(z0.y * z0.y - z0.x * z0.z, 0.0)), 1e-20);
    return clamp(t, 0.5, 1.0);
}

// The distance from the origin to the triangle a, b, c in the plane normal to `up` (radians): zero inside.
float ErosionTriangleDistance(float3 a, float3 b, float3 c, float3 up)
{
    const float3 e0 = b - a, e1 = c - b, e2 = a - c;
    const float s0 = dot(cross(e0, -a), up), s1 = dot(cross(e1, -b), up), s2 = dot(cross(e2, -c), up);
    if ((s0 >= 0.0 && s1 >= 0.0 && s2 >= 0.0) || (s0 <= 0.0 && s1 <= 0.0 && s2 <= 0.0)) return 0.0;
    const float3 p0 = a + saturate(-dot(a, e0) / max(dot(e0, e0), 1e-30)) * e0;
    const float3 p1 = b + saturate(-dot(b, e1) / max(dot(e1, e1), 1e-30)) * e1;
    const float3 p2 = c + saturate(-dot(c, e2) / max(dot(e2, e2), 1e-30)) * e2;
    return sqrt(min(dot(p0, p0), min(dot(p1, p1), dot(p2, p2))));
}

// The inflow u re-routed: from its link's midpoint, continuing its own course, to the main course's channel where the
// main stage has fallen to its own, past the main course's middle, arriving at Howard's angle, cos = the main's slope
// over its own, within RIVER_JUNCTION. Its control: where its heading meets the arrival line, if ahead of both and short
// of the node, else the chord's middle; the connector stays among the node's neighbours. Its stage leaves at its own
// course's slope, falling to the main's: past its start, the two go on alike, no step where their water overlaps.
ErosionCourse ErosionConnector(ErosionNodeCourses v, ErosionRiverNode u, RlPoint ref, float3 pf, float3 rest)
{
    const ErosionCourse main = v.main;
    const float radius = 1000.0 * PLANET_RADIUS_KM;
    const float zS = 0.5 * (u.stage + v.r.stage);
    const float tj = ErosionJunction(main, zS);
    const float3 tangent = ErosionCourseTangent(main, tj);
    float3 q;
    float2 valley;
    const float4 m = ErosionMeander(main, tj, ref, pf, normalize(tangent), q, valley);
    const float3 up = normalize(pf + q), along = normalize(tangent - dot(tangent, up) * up), left = cross(along, up);
    const float3 J = q + (m.x + m.z) / radius * left;
    const float3 a = 0.5 * (u.at + v.r.at) - rest, into = normalize(v.r.at - u.at);
    const float span = max(length(J - a), 1.0 / radius);
    const float zJ = ErosionBezier(main.stage, tj);
    const bool straight = all(main.a == main.b) || all(main.b == main.c);
    const float slopeMain = straight ? abs(main.stage.z - main.stage.x) / max(length(main.c - main.a) * radius, 1e-6)
                          : abs(lerp(main.stage.y - main.stage.x, main.stage.z - main.stage.y, tj)) / max(length(tangent) * radius, 1e-6);
    const float cosine = saturate(slopeMain / max((zS - zJ) / (span * radius), 1e-9));
    const float theta = radians(clamp(degrees(acos(cosine)), RIVER_JUNCTION.x, RIVER_JUNCTION.y));
    const float side = dot(a - J, left) > 0.0 ? 1.0 : -1.0;
    const float3 arrive = cos(theta) * along - side * sin(theta) * left;
    const float3 d = J - a;
    const float det = dot(cross(into, arrive), up);
    const float l0 = dot(cross(d, arrive), up) / det, l1 = dot(cross(into, d), up) / det;
    const bool ahead = abs(det) > 1e-6 && l0 > 0.0 && l0 < 1.5 * span && l1 > 0.0 && l1 < 1.5 * span;
    ErosionCourse k;
    k.a = a, k.c = J;
    k.b = ahead ? a + min(l0, length(v.r.at - rest - a)) * into : 0.5 * (a + J);
    const float wallS = 0.5 * (u.wall + v.r.wall), wallJ = ErosionBezier(main.wall, tj);
    const float sinS = 0.5 * (u.sinuous + v.r.sinuous), sinJ = ErosionBezier(main.sinuous, tj);
    const float floorS = 0.5 * (u.floorLog + v.r.floorLog), floorJ = ErosionBezier(main.floorLog, tj);
    const float slopeUp = (v.r.stage - u.stage) / max(length(v.r.at - u.at) * radius, 1e-6);
    k.stage = float3(zS, max(zS + slopeUp * length(k.b - k.a) * radius, zJ), zJ), k.lq = 0.5 * (u.lq + v.r.lq);
    k.wall = float3(wallS, 0.5 * (wallS + wallJ), wallJ), k.sinuous = float3(sinS, 0.5 * (sinS + sinJ), sinJ);
    k.floorLog = float3(floorS, 0.5 * (floorS + floorJ), floorJ);
    k.taper = true, k.dry = false;
    k.flare = 0.0, k.fan = 0.0;
    k.stops = u.stops.z, k.partLq = 0.0, k.split = false, k.fanFirst = false;
    const float incomingLq = (float)u.outCode / 8.0 - 8.0;
    k.lq = u.stops.z < 1.0 ? incomingLq : 0.5 * (incomingLq + v.r.lq);
    k.traceLq = 0.5 * (u.graphCode + v.r.graphCode) / 8.0 - 8.0;
    // A stopped tributary never reaches this confluence. A dry course has exactly zero wet width/shift.
    // Keep its valley and immutable trace, without preparing a wet bank that cannot contribute.
    [branch] if (u.stops.z >= 1.0 && exp2(k.lq.x) > RIVER_Q.y)
    {
        const float mainWidth = ErosionRiverSize(exp2(ErosionBezier(main.lq, tj))).x;
        // Match the receiving section; only its downstream-facing bank opens.
        const float3 receivingFlow = normalize(along + clamp(m.y + m.w, -1.0, 1.0) * left);
        const float turn = dot(receivingFlow, cross(normalize(J - k.b), up));
        // Smoothly lose the opening before a filtered, nearly parallel meander changes sides.
        const float bankTurn = sign(turn) * smoothstep(0.0, sin(radians(RIVER_JUNCTION.x)), abs(turn));
        k.flare = float3(mainWidth * ErosionWidthFactor(ref, q, valley.y), mainWidth, bankTurn);
    }
    k.mouth = main.mouth || u.stops.z < 1.0;
    if (u.stops.z < 1.0 && v.r.lake <= 0.0)
    {
        const float run = length(ErosionBezier3(k.a, k.b, k.c, u.stops.z) - k.a) * radius;
        const float discharge = exp2(incomingLq), width = ErosionRiverSize(discharge).x;
        const float fan = ErosionFanStrength(discharge, max(zS, 0.0) / max(run, 1.0), ErosionBezier(k.wall, u.stops.z))
                        * smoothstep(4.0 * width, 12.0 * width, run);
        k.fan = float3(0.0, 0.5, 1.0) * (fan / max(u.stops.z, 1e-3));
    }
    return k;
}

// A course's reach (m): its corridor or its channel, and its valley's offset.
float ErosionCourseReach(ErosionCourse k)
{
    const float lq = max(max(k.lq.x, max(k.lq.y, k.lq.z)), k.split ? max(k.partLq.x, k.partLq.y) : -1e9);
    const float2 bounds = max(ErosionMeanderBounds(ErosionFinest(max(k.traceLq.x, max(k.traceLq.y, k.traceLq.z))), 1.0),
                             ErosionMeanderBounds(ErosionFinest(min(k.traceLq.x, k.traceLq.z)), 1.0));
    const float nominal = ErosionRiverSize(exp2(lq)).x;
    const float W = max((1.0 + RIVER_WIDTH_NOISE.y) * nominal, k.flare.x) + RIVER_BANK_EDGE.x
                  + max(k.mouth ? min(RIVER_MOUTH.x * nominal, RIVER_MOUTH.z) : 0.0,
                        smoothstep(0.0, 1.0, max(k.fan.x, max(k.fan.y, k.fan.z))) * RIVER_DELTA.w);
    const float F = min(ErosionValleyFloor(exp2(lq), max(k.floorLog.x, max(k.floorLog.y, k.floorLog.z)))
                       * exp2(RIVER_VALLEY_NOISE.y), RIVER_FLOOR.z) + 2.82842712 * W;
    const float share = ErosionCourseShare(lq);
    const float D = min(share * F + max(share * max(k.wall.x, max(k.wall.y, k.wall.z)) * exp2(RIVER_VALLEY_NOISE.z), 1.0), RIVER_REACH);
    return max(D, 2.0 * W + bounds.x) + bounds.x + RIVER_OFFSET_MAX;
}

// The rivers around a point: the corridors combined, their channels and the water over them.
struct ErosionRiver
{
    float fill, carve; // the ground the corridors raise and lower (m), their maxima
    float bed;         // the channels' lower envelope (m), 1e9 away from them
    float stage;       // the stage over the wet channels (m), blended by how far inside each the point is; -1e9 elsewhere
    float cut;         // depth from their blended stage to the wet bed union (m)
    float coverage;    // fraction of the footprint covered by the physical channels, not their filtered support
    float weight;      // the blend's sum of weights, 0 outside all
    float edge;        // how far inside a channel's edge (m), the farthest; negative outside all
    float distance;    // from the nearest channel's edge (m)
    float bank;        // dry-bank proximity for grounded gravel and tufts
    float3 flow;       // downstream velocity, blended with the same wet weights as stage (m/s)
    float lakeLevel;   // the terminal lakes' stage (ErosionLakeLevel)
};

// Box mean of a flat wet bed with depth-scaled cubic shoulders. A width-scaled quartic made almost the entire
// wide river a shallow pale shelf. Integrate the same physical section at every footprint, in local coordinates.
float ErosionChannelMean(float d, float w, float depth, float r)
{
    const float2 lo = max(float2(d - r, -d - r), 0.0), hi = max(float2(d + r, -d + r), 0.0);
    const float shoulder = min(w, max(RIVER_BANK_SHOULDER.x, RIVER_BANK_SHOULDER.y * depth)), core = w - shoulder;
    float2 area = min(hi, core) - min(lo, core);
    const float2 a = saturate((lo - core) / shoulder), b = saturate((hi - core) / shoulder), span = b - a;
    const float2 mean = a * a * (3.0 - 2.0 * a) + span * (3.0 * a * (1.0 - a)
                          + span * (1.0 - 2.0 * a - 0.5 * span));
    area += shoulder * span * max(1.0 - mean, 0.0);
    return depth * (area.x + area.y) / (2.0 * r);
}

// Mean incision of the DRY bank, clipped against the supporting ground before filtering. Its physical profile is
// flat to w, a smooth shoulder by bankHeight, a terrace to 2w, then a slope RIVER_STEEP_BANK. Moving those limits by r used to
// carve kilometre-wide trenches around a subpixel river. Integrate each positive piece in local coordinates instead.
float ErosionChannelBankCut(float d, float w, float bankHeight, float above, float r)
{
    const float2 lo = max(float2(d - r, -d - r), 0.0), hi = max(float2(d + r, -d + r), 0.0);
    float2 area = above * (min(hi, w) - min(lo, w));
    // The inverse of smoothstep locates the bank/ground intersection; above >= bankHeight keeps the whole bank.
    const float fraction = saturate(above / max(bankHeight, 1e-9));
    const float end = 0.5 - sin(asin(1.0 - 2.0 * fraction) / 3.0);
    const float shoulder = min(w, max(RIVER_BANK_SHOULDER.x, RIVER_BANK_SHOULDER.y * bankHeight));
    const float2 a = clamp((lo - w) / shoulder, 0.0, end), b = clamp((hi - w) / shoulder, 0.0, end), span = b - a;
    const float2 mean = a * a * (3.0 - 2.0 * a) + span * (3.0 * a * (1.0 - a)
                          + span * (1.0 - 2.0 * a - 0.5 * span));
    area += shoulder * span * max(above - bankHeight * mean, 0.0);
    area += max(min(hi, 2.0 * w) - max(lo, w + shoulder), 0.0) * max(above - bankHeight, 0.0);
    const float rise = max(above - bankHeight, 0.0), reach = rise / RIVER_STEEP_BANK;
    const float2 c = clamp(lo - 2.0 * w, 0.0, reach), e = clamp(hi - 2.0 * w, 0.0, reach);
    area += (e - c) * max(rise - 0.5 * RIVER_STEEP_BANK * (c + e), 0.0);
    return (area.x + area.y) / (2.0 * r);
}

float ErosionChannelCoverage(float d, float w, float r)
{
    return max(min(d + r, w) - max(d - r, -w), 0.0) / (2.0 * r);
}

// Exact union of up to three clipped wet intervals. Ordering channel centres does not order their left banks:
// a narrow nascent branch may lie entirely inside the wider trunk, or miss the footprint while the trunk covers it.
float ErosionIntervalCoverage(float3 lo, float3 hi, float radius)
{
    const float3 pairs = max(min(hi.xxy, hi.yzz) - max(lo.xxy, lo.yzz), 0.0);
    const float common = max(min(hi.x, min(hi.y, hi.z)) - max(lo.x, max(lo.y, lo.z)), 0.0);
    return saturate((dot(max(hi - lo, 0.0) - pairs, float3(1.0, 1.0, 1.0)) + common) / (2.0 * radius));
}

// Box mean of the fixed 80 m submerged termination. The sampling radius never moves the physical contact.
float ErosionStopPrimitive(float x)
{
    const float f = RIVER_CONTACT.z, u = saturate(x / f);
    return min(x, 0.0) + f * (u - u * u * u + 0.5 * u * u * u * u);
}

float ErosionCourseStop(ErosionCourse k, float t, float along, float radius)
{
    const bool first = k.split && t < 0.5;
    const float stop = first ? k.stops.x : k.stops.y;
    if (stop >= 1.0) return 1.0;
    const float3 middle = ErosionBezier3(k.a, k.b, k.c, 0.5);
    const float lengthM = max(length(k.split ? (first ? middle - k.a : k.c - middle) : k.c - k.a)
                             * (1000.0 * PLANET_RADIUS_KM), 1.0);
    const float part = k.split ? (first ? 2.0 * t : 2.0 * t - 1.0) : t;
    const float beyond = (part - stop) * lengthM + along;
    return saturate((ErosionStopPrimitive(beyond + radius) - ErosionStopPrimitive(beyond - radius)) / (2.0 * radius));
}

// The mouth starts on land, a physical number of widths before its cached contact. Its owning part bounds the
// approach, so it starts at zero even when a lake lies immediately after a midpoint. No height-before-erosion gate.
float ErosionMouthShare(ErosionCourse k, float t, float along, float width)
{
    const bool first = k.split && t < 0.5;
    const float limit = first ? k.stops.x : k.stops.y;
    if (limit <= 0.0 || limit >= 1.0) return 0.0;
    const float3 middle = ErosionBezier3(k.a, k.b, k.c, 0.5);
    const float lengthM = max(length(k.split ? (first ? middle - k.a : k.c - middle) : k.c - k.a)
                             * (1000.0 * PLANET_RADIUS_KM), 1.0);
    const float part = k.split ? (first ? 2.0 * t : 2.0 * t - 1.0) : t;
    const float run = max(min(RIVER_MOUTH.y * width, limit * lengthM), 0.001);
    return 1.0 - smoothstep(0.0, run, (limit - part) * lengthM - along);
}

// One course's corridor at the point, the origin (the prototype's evaluate). Its course: the curve displaced by its
// meanders, the distance to it |l - m| / sqrt(1 + m'^2), l the lateral distance, m' clamped to 1. Its base profile g goes
// from the floor's half-width F to the corridor's F + wall; the existing 2D residual retains asymmetric spurs through
// ErosionSpurLift. The floor follows the law, never narrower than the channel; the floodplain keeps RIVER_FLOODPLAIN.x
// of the fine relief past the banks; raised ground only where a river runs, `sea` 0 under standing water. Below RIVER_Q.y, a dry
// notch: its depth, floor and walls a share of the full corridor's. Its channel cut, its banks at RIVER_STEEP_BANK past
// its edge. hr: the relief; parent: its support before ReliefDetail; fine: its part finer than the floodplain keeps;
// radius: the sampling footprint (m).
void ErosionCorridor(ErosionCourse k, RlPoint ref, float3 pf, float hr, float parent, float fine, float radius, float sea, inout ErosionRiver river)
{
    const float R = 1000.0 * PLANET_RADIUS_KM;
    [branch] if (ErosionCourseShare(max(max(k.lq.x, max(k.lq.y, k.lq.z)), k.split ? max(k.partLq.x, k.partLq.y) : -1e9)) <= 0.0)
        return;
    // In the point's tangent plane, as the valleys: a chord's radial sag is not a bank.
    const float3 a = k.a - dot(k.a, pf) * pf, b = k.b - dot(k.b, pf) * pf, c = k.c - dot(k.c, pf) * pf;
    // The curve stays within half its control's offset from its chord: farther than its reach, nothing.
    const float3 e = c - a;
    const float u = saturate(-dot(a, e) / max(dot(e, e), 1e-30));
    [branch] if ((length(a + u * e) - 0.5 * length(b - 0.5 * (a + c))) * R > ErosionCourseReach(k) + radius)
        return;
    float3 nearest;
    const float t = ErosionCurveDistance(a, b, c, nearest).y;
    ErosionCourse projected = k;
    projected.a = a, projected.b = b, projected.c = c;
    const float3 T = normalize(ErosionCourseTangent(projected, t)), N = cross(T, pf);
    const float lat = -dot(nearest, N) * R, along = -dot(nearest, T) * R;
    // Past its ends, its stage goes on along its slope, its neighbour's to first order: held at an end, its banks, bed
    // and water stood a step above or below the next course's. `along` is zero elsewhere.
    const bool straight = all(a == b) || all(b == c);
    const float slopeZ = straight ? (k.stage.z - k.stage.x) / max(length(c - a) * R, 1e-6)
                       : lerp(k.stage.y - k.stage.x, k.stage.z - k.stage.y, t) / max(length(lerp(b - a, c - b, t)) * R, 1e-6);
    float lq = ErosionBezier(k.lq, t);
    if (k.split && any(k.stops < 1.0))
        lq = t < 0.5 ? (k.stops.x < 1.0 ? k.partLq.x : lerp(k.lq.x, k.partLq.y, smoothstep(0.0, 0.5, t)))
                     : (k.stops.y < 1.0 ? k.partLq.y : lerp(k.partLq.y, k.lq.z, smoothstep(0.5, 1.0, t)));
    const float q = exp2(lq);
    float z = ErosionBezier(k.stage, t) + slopeZ * along;
    const float2 size = ErosionRiverSize(q);
    const float approach = k.mouth ? ErosionMouthShare(k, t, along, size.x) : 0.0;
    z -= max(z - river.lakeLevel, 0.0) * approach;
    const float stop = ErosionCourseStop(k, t, along, radius);
    const float live = k.dry ? 0.0 : smoothstep(RIVER_Q.y, RIVER_Q.z, q) * stop;
    // A dry head loses both width and excavation towards its origin. Narrowing a full-depth cut made slot canyons.
    const float share = ErosionCourseShare(lq) * (k.dry ? smoothstep(0.0, 1.0, t) : stop);
    if (share <= 0.0 && live <= 0.0) return;
    const float2 bounds = ErosionMeanderBounds(ErosionFinest(ErosionBezier(k.traceLq, t)), ErosionBezier(k.sinuous, t));
    // The corridor's half-width bound, the valley's noise at its largest.
    const float wall = share * ErosionBezier(k.wall, t);
    const float widthBound = max((1.0 + RIVER_WIDTH_NOISE.y) * size.x, k.flare.x) + RIVER_BANK_EDGE.x
                           + max(k.mouth ? min(RIVER_MOUTH.x * size.x, RIVER_MOUTH.z) : 0.0,
                                 smoothstep(0.0, 1.0, max(k.fan.x, max(k.fan.y, k.fan.z))) * RIVER_DELTA.w);
    const float D = min(share * (min(ErosionValleyFloor(q, ErosionBezier(k.floorLog, t)) * exp2(RIVER_VALLEY_NOISE.y), RIVER_FLOOR.z) + 2.82842712 * widthBound)
                        + max(wall * exp2(RIVER_VALLEY_NOISE.z), 1.0), RIVER_REACH);
    // The section filter is transverse: it cannot bring an absent dry section past its longitudinal end.
    [branch] if (live <= 0.0 && abs(along) >= D) return;
    // A corridor or a channel too far to reach the point is skipped: their distances' bounds, the meanders' bounded.
    const float coarse = RIVER_OFFSET_MAX * tanh(2.5 * bounds.y / RIVER_OFFSET_MAX);
    const float dvLow = max(abs(along), (abs(lat) - coarse - bounds.x) * 0.70710678), dcLow = dvLow;
    const float edgeMax = widthBound * live + radius, bankMax = edgeMax - radius;
    const float channelLow = dcLow > edgeMax + bankMax
                           ? z + (1.0 - RIVER_BANK_DETAIL.y) * RIVER_BANK * size.y * live
                               + RIVER_STEEP_BANK * (dcLow - edgeMax - bankMax) : -1e9;
    [branch] if (dvLow >= D + radius && (live <= 0.0 || channelLow >= hr))
        return;
    float3 onCourse;
    float2 valley;
    float4 m = ErosionMeander(k, t, ref, pf, T, onCourse, valley);
    valley.x = min(ErosionValleyFloor(q, ErosionBezier(k.floorLog, t)) * exp2(RIVER_VALLEY_NOISE.y * valley.y), RIVER_FLOOR.z);
    m *= k.taper ? 1.0 - smoothstep(0.6, 1.0, t) : 1.0;
    const float slopeValley = clamp(m.y, -1.0, 1.0), slope = clamp(m.y + m.w, -1.0, 1.0);
    const float dv = length(float2(along, (lat - m.x) * rsqrt(1.0 + slopeValley * slopeValley)));
    const float dc = length(float2(along, (lat - m.x - m.z) * rsqrt(1.0 + slope * slope)));
    const float remaining = length(c - nearest) * R;
    const float joinRun = max(min(RIVER_CONFLUENCE.y * (k.flare.y + size.x), length(c - a) * R), 0.001);
    const float join = k.flare.x > 0.0 ? 1.0 - smoothstep(0.0, joinRun, remaining) : 0.0;
    const float bankFactor = ErosionBankFactor(ref);
    // Two banks read different terrain points. Confined, steeper reaches retain more small protrusions;
    // gentle reaches remain smoother. The zero-mean octaves disappear with the terrain's bandwidth.
    const float edgeNoise = (bankFactor - 1.0) / RIVER_BANK_DETAIL.y;
    const float receiving = k.mouth
                          ? 1.0 - smoothstep(0.0, 2.0 * size.y, max(z - river.lakeLevel, 0.0)) : 0.0;
    const float fanControl = k.fanFirst && t >= 0.5 ? 0.0 : saturate(ErosionBezier(k.fan, t));
    const float fan = smoothstep(0.0, 1.0, fanControl);
    const float spread = fan * min(RIVER_DELTA.z * size.x, RIVER_DELTA.w);
    // The widening and the distributary spread share one aperture budget, not two superposed excavations.
    const float aperture = max(approach, receiving * (1.0 - smoothstep(0.0, RIVER_MOUTH.y * size.y, hr - river.lakeLevel)));
    const float mouth = max(min(RIVER_MOUTH.x * size.x, RIVER_MOUTH.z) * aperture - spread, 0.0);
    const float ownWidth = size.x * ErosionWidthFactor(ref, onCourse, valley.y) + mouth;
    const float matched = lerp(ownWidth, min(ownWidth, k.flare.x), join);
    const float opening = RIVER_CONFLUENCE.x * max(k.flare.x - matched, 0.0) * join;
    const float baseWidth = matched + abs(k.flare.z) * opening, bankShift = k.flare.z * opening * live;
    const float edgeOffset = min(min(RIVER_BANK_EDGE.x, RIVER_BANK_EDGE.y * size.x), 0.25 * baseWidth)
                           * lerp(0.3, 1.0, smoothstep(0.002, 0.02, abs(slopeZ))) * edgeNoise;
    const float W = (baseWidth + edgeOffset) * live;
    float asymmetry = 0.0;
    [branch] if (fan > 0.0) asymmetry = ErosionCourseNoise(ref, onCourse, 2400.0, 24u);
    const float fanSlope = 6.0 * fanControl * (1.0 - fanControl) * lerp(k.fan.y - k.fan.x, k.fan.z - k.fan.y, t)
                         * min(RIVER_DELTA.z * size.x, RIVER_DELTA.w) / max(length(lerp(b - a, c - b, t)) * R, 1.0);
    const float depth = size.y * live, bankHeight = RIVER_BANK * depth * bankFactor * (1.0 - approach), zb = z + bankHeight;
    const float confinement = ErosionConfinement(hr, parent, fine, zb);
    // The floor must contain the displaced channel and both banks, measured in the valley's distance metric.
    // A width about the undisplaced axis alone can pinch a meander against a mountain and leave long artificial fins.
    const float valleyMetric = rsqrt(1.0 + slopeValley * slopeValley);
    const float bankMetric = max(1.0, sqrt(1.0 + slope * slope) * valleyMetric);
    // The bank shift is in channel-normal metres; the valley measures the same point in its own metric.
    const float belt = abs(m.z + bankShift * sqrt(1.0 + slope * slope)) * valleyMetric
                     + 2.0 * (spread + max(size.x, W)) * bankMetric;
    const float F = share * max(belt, valley.x * confinement);
    const float outer = min(F + max(wall * exp2(RIVER_VALLEY_NOISE.z * valley.y) * confinement, 1.0), RIVER_REACH);
    const float bank = max(spread + W, CREASE_MIN_CELL);
    ErosionCorridorSection section;
    section.distance = float2((lat - m.x) * valleyMetric, (lat - m.x - m.z) * rsqrt(1.0 + slope * slope) - bankShift);
    section.along = along, section.ratio = rsqrt(1.0 + slope * slope) / valleyMetric;
    section.floor = F, section.outer = outer;
    section.rounding = lerp(RIVER_WALL.x, RIVER_WALL.y, smoothstep(log2(RIVER_Q.y), log2(RIVER_WALL.z), lq));
    section.bank = bank, section.keep = max(4.0 * bank, RIVER_SPURS.x * max(F, share * valley.x));
    section.height = hr - zb, section.spur = ErosionSpurRelief(hr, parent, fine);
    section.rough = max(RIVER_FLOODPLAIN.x * fine, -0.8 * bankHeight);
    section.cutShare = share, section.fillShare = live * sea;
    const float S = hr + ErosionCorridorMean(section, radius);
    river.fill = max(river.fill, S - hr), river.carve = max(river.carve, hr - S);
    [branch] if (live > 0.0)
    {
        // A low coastal fan divides its discharge between one central and two diverging channels.
        // The lateral channels grow from zero at the same apex; their sum never duplicates the parent discharge.
        const float lateral = (lat - m.x - m.z) * rsqrt(1.0 + slope * slope) - bankShift;
        float3 intervalsLo = 0.0, intervalsHi = 0.0;
        [loop] for (int branch = (fan > 0.0 ? -1 : 0); branch <= (fan > 0.0 ? 1 : 0); ++branch)
        {
            const float fraction = branch == 0 ? 1.0 - 0.5 * fan : 0.25 * fan * (1.0 + branch * 0.6 * asymmetry);
            const float width = max(W * sqrt(fraction), 1e-3), cutDepth = depth * pow(fraction, EROSION_RIVER_SHAPE.z);
            const float spreadFactor = 0.85 + branch * 0.15 * asymmetry;
            const float offset = lateral - branch * spread * spreadFactor, distance = length(float2(along, offset));
            const float edge = width + radius;
            const float inside = distance < edge ? ErosionChannelMean(distance, width, cutDepth, radius) : 0.0;
            const float channel = S - ErosionChannelBankCut(distance, width, bankHeight, max(S - z, 0.0), radius) - inside;
            river.bed = min(river.bed, channel);
            // Keep a water level wherever this course has a wet section. Fading it by distance to the junction
            // can erase a still-wet tributary before the narrower receiving channel actually covers it.
            const float w = distance < edge ? smoothstep(0.0, max(width, CREASE_MIN_CELL), edge - distance) : 0.0;
            river.stage += w * z, river.weight += w;
            // Beds form a union. Averaging a shallow tributary edge into a deep receiving channel created
            // a pale closing sill inside uninterrupted water. Identical overlapping reaches remain idempotent.
            river.cut = max(river.cut, inside);
            const float wetShoulder = min(width, max(RIVER_BANK_SHOULDER.x, RIVER_BANK_SHOULDER.y * cutDepth));
            river.flow += w * normalize(T + (slope + branch * fanSlope * spreadFactor) * N)
                          * min(q * fraction / max((2.0 * width - wetShoulder) * cutDepth, 1e-3), 4.0);
            // Integrate the union, not the sum, of overlapping wet intervals at the fan apex.
            const float signedDistance = offset < 0.0 ? -distance : distance;
            intervalsLo[branch + 1] = clamp(-signedDistance - width, -radius, radius);
            intervalsHi[branch + 1] = clamp(-signedDistance + width, -radius, radius);
            river.edge = max(river.edge, edge - distance);
            river.distance = min(river.distance, distance - width);
            river.bank = max(river.bank, 1.0 - smoothstep(0.0, 40.0, max(distance - width, 0.0)));
        }
        river.coverage = max(river.coverage, ErosionIntervalCoverage(intervalsLo, intervalsHi, radius));
    }
}

// Union of physical 4 x 4 searches over a spherical footprint. For chart coordinate s = p_i / p_n,
// |delta s| <= |delta p| sqrt(1+s*s) / (p_n-|delta p|); the spherical chord is at most radius/R.
// Retain the original corner bound when its halo touches a face edge, where ErosionCell remaps the nodes.
float2 ErosionFootprintReach(float3 p, float2 x, uint n, float radius)
{
    const float R = 1000.0 * PLANET_RADIUS_KM, cellM = 2.0 * R / n;
    const float corner = 3.0 * radius / (cellM * max(1.0 - 2.0 * radius / R, 0.5));
    const float2 st = (x + 0.5) * 2.0 / n - 1.0;
    const float normal = max(abs(p.x), max(abs(p.y), abs(p.z)));
    const float2 local = radius / cellM * sqrt(1.0 + st * st) / max(normal - radius / R, 1e-6) + 1e-4;
    return all(x - corner >= 1.0) && all(x + corner <= (float)n - 3.0) ? min(corner, local) : corner.xx;
}

// The rivers around the point p (unit, planet frame), for mesh cells of cellKm (step B): the 4 x 4 physical search,
// extended over the filter footprint, each corridor combined by maximum fill/carve and minimum bed. hr: the relief
// they are drawn on; parent: its support before ReliefDetail; fine: its part finer than the floodplain keeps. The 4 x 4 nodes hold
// courses within 1.2 cells, about 14 km in the cube's corners; check the reach when changing widths or meanders.
ErosionRiver ErosionRivers(double3 p, float cellKm, float hr, float parent, float fine)
{
    const double squared = p.x * p.x + p.y * p.y + p.z * p.z;
    double inverse = (double)rsqrt((float)squared);
    inverse *= 1.5 - 0.5 * squared * inverse * inverse;
    p *= inverse;
    const uint n = ErosionSize();
    const float R = 1000.0 * PLANET_RADIUS_KM, cellM = 2.0 * R / n;
    uint face;
    float2 x;
    ErosionLocate((float3)p, n, face, x);
    const float radius = max(1000.0 * cellKm, CREASE_MIN_CELL);
    const float2 reachCells = ErosionFootprintReach((float3)p, x, n, radius);
    const int2 origin = (int2)floor(x - reachCells) - 1;
    const int2 count = (int2)floor(x + reachCells) + 3 - origin;
    ErosionRiver river;
    river.fill = 0.0, river.carve = 0.0, river.bed = 1e9, river.stage = 0.0, river.cut = 0.0, river.weight = 0.0, river.edge = -1e9;
    river.distance = 1e9, river.flow = 0.0, river.coverage = 0.0, river.bank = 0.0;
    river.lakeLevel = ErosionLakeLevel(face, x, n, cellM);
    // A drowned valley never rebuilds its banks across a standing lake or the sea. Only dry support is filled.
    const float sea = smoothstep(0.0, 50.0, hr - river.lakeLevel);
    const RlPoint ref = RlMakePoint(p);
    const float3 pf = (float3)p, rest = (float3)(p - (double3)pf);
    [loop] for (int k = 0; k < count.x * count.y; ++k)
    {
        const uint r = ErosionCell(face, origin + int2(k % count.x, k / count.x), n);
        // A node's courses stay within 1.15 cells of it, their outlet's line within its extension.
        [branch] if (length((ErosionNode(r, n) - pf) - rest) * R > 1.15 * cellM + RIVER_EXTEND.x + 16000.0 + radius)
            continue;
        ErosionNodeCourses v;
        [branch] if (!ErosionMainCourse(r, n, pf, rest, v))
            continue;
        // A connector stays within its triangle, its start, its node, its junction on the main curve, widened by the
        // junction's offset and its corridor: a main course's reach each.
        const float reach = (2.0 * ErosionCourseReach(v.main) + radius) / R;
        uint todo = 1u | (v.head ? 2u : 0u) | (v.outlet ? 4u : 0u) | v.connectors << 3;
        [loop] while (todo != 0u)
        {
            const uint j = firstbitlow(todo);
            todo &= todo - 1u;
            ErosionCourse course = v.main;
            [branch] if (j == 1u)
                course = ErosionHeadCourse(v);
            else if (j == 2u)
                course = ErosionOutletCourse(v);
            else if (j >= 3u)
            {
                const ErosionRiverNode u = ErosionRiverNodeAt(ErosionNeighbour(r, j - 3u, n), n, pf);
                const float3 start = 0.5 * (u.at + v.r.at) - rest;
                const float3 junction = ErosionBezier3(v.main.a, v.main.b, v.main.c, ErosionJunction(v.main, 0.5 * (u.stage + v.r.stage)));
                [branch] if (ErosionTriangleDistance(start - dot(start, pf) * pf, v.main.b - dot(v.main.b, pf) * pf,
                                                     junction - dot(junction, pf) * pf, pf) > reach)
                    continue;
                course = ErosionConnector(v, u, ref, pf, rest);
            }
            ErosionCorridor(course, ref, pf, hr, parent, fine, radius, sea, river);
        }
    }
    river.stage = river.weight > 0.0 ? river.stage / river.weight : -1e9;
    river.flow = river.weight > 0.0 ? river.flow / river.weight : 0.0;
    return river;
}

#endif
