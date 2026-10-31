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
    float level;      // the water's level on the nearest link (m)
    float glacier;    // 1 in a glacial trough, fading away from it
    float incision;   // the links' valley depth at their node (m), fading away from them: continuous
    float deposit;    // the deposits' surface (m), deltas and fans; far below the ground away from them
};

// The gullies' inputs to the detail (ReliefDetail).
struct ReliefGullies
{
    float3 slope;  // the slope (m/m) of the ground under the detail: the large forms', or a valley's walls where it is carved
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

// A quadratic Bezier from a to c, control b, all relative to the point, in radii: its nearest sample to the origin among
// five, refined on the polyline; the distance (radii) and the curve's parameter there; nearest: that point.
float2 ErosionCurveDistance(float3 a, float3 b, float3 c, out float3 nearest)
{
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
    return float2(sqrt(best), at);
}

// One link's valley at distance d (m) from its axis: the water's level z, the discharge q (m3/s), the ice flux, the slope
// of the level along the link, the walls' slope; widened to `wide` (m), two mesh cells, its depth less in proportion.
// Returns the surface and the floor's share; rise: the surface's slope away from the axis.
float2 ErosionProfile(float d, float z, float q, float ice, float slope, float walls, float depth, float wide, float widest,
                      out float glacier, out float rise)
{
    // The fluvial floor, wider on a gentle river; never wider than `widest`, so that it ends before the links read change.
    const float floorWidth = min(EROSION_FLOOR.x * sqrt(q) * clamp(EROSION_FLOOR.y / max(slope, 1e-6), 1.0, EROSION_FLOOR.z), widest);
    // The glacial trough: its half-width with the ice flux, deepened by a share of it.
    glacier = saturate(log2(max(ice, 1.0)) - EROSION_GLACIER.w);
    const float trough = clamp(EROSION_GLACIER.x * pow(max(ice, 1.0) / 1e8, EROSION_GLACIER.y), 150.0, 1500.0);
    const float over = EROSION_GLACIER.z * trough * glacier;
    // Two mesh cells at least across the top: wider, shallower.
    const float top = lerp(floorWidth, trough, glacier) + max(depth, 0.0) / walls;
    const float stretch = max(1.0, wide / max(top, 1.0));
    const float x = d / stretch, lift = (depth + over) * (1.0 - 1.0 / stretch);
    const float fluvial = walls * max(x - floorWidth, 0.0);
    const float u = min(x / trough, 1.0);
    const float glacial = -over + over * u * u + EROSION_GLACIER_WALLS * max(x - trough, 0.0);
    const float surface = z + lift + lerp(fluvial, glacial, glacier);
    rise = lerp(x > floorWidth ? walls : 0.0, 2.0 * over * u / trough + (x > trough ? EROSION_GLACIER_WALLS : 0.0), glacier) / stretch;
    // The floor, where the detail fades: the river's; the trough's middle, where the gullies of its two walls would meet.
    const float flat = lerp(1.0 - smoothstep(floorWidth, floorWidth + max(floorWidth, 200.0), x),
                            1.0 - smoothstep(0.25 * trough, 0.7 * trough, x), glacier);
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
    float nearest = 1e30;
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
        float zDown = dr.level, qDown = dr.discharge, iceDown = dr.ice;
        [branch] if (dr.bits & EROSION_HAS_RECEIVER)
        {
            const uint rr = ErosionNeighbour(r, dr.bits & 7u, n);
            const ErosionData drr = ErosionRead(rr, n);
            c = 0.5 * ((pr - pf) + (ErosionNode(rr, n) - pf)) - rest;
            zDown = 0.5 * (dr.level + drr.level);
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
            float zUp = dr.level, qUp = dr.discharge, iceUp = dr.ice;
            [branch] if (inflows != 0u)
            {
                const uint kq = firstbitlow(inflows);
                inflows &= inflows - 1u;
                const uint q = ErosionNeighbour(r, kq, n);
                const ErosionData dq = ErosionRead(q, n);
                a = 0.5 * ((ErosionNode(q, n) - pf) + (pr - pf)) - rest;
                zUp = 0.5 * (dq.level + dr.level), qUp = dq.discharge, iceUp = dq.ice;
            }
            float3 nearestPoint;
            const float2 dt = ErosionCurveDistance(a, b, outlet ? b : c, nearestPoint);
            const float d = dt.x * radius;
            [branch] if (d < EROSION_REACH * cellM)
            {
                const float z = lerp(zUp, outlet ? dr.level : zDown, dt.y);
                const float q = exp2(lerp(log2(qUp), log2(qDown), dt.y)), ice = lerp(iceUp, iceDown, dt.y);
                const float span = max(distance(a, outlet ? b : c), 1e-9) * radius;
                const float depth = max(dr.ground - dr.level, 0.0);
                float glacier, rise;
                const float2 s = ErosionProfile(d, z, q, ice, abs(zUp - zDown) / span, walls, depth, wide, 0.15 * cellM, glacier, rise);
                // Past three quarters of the reach the valley rises out of every ground: the links read change there.
                const float beyond = smoothstep(0.35, 0.5, d / cellM);
                [branch] if (s.x + 1e4 * beyond < v.surface)
                {
                    v.surface = s.x + 1e4 * beyond;
                    v.gradient = -rise * nearestPoint / max(length(nearestPoint), 1e-12);
                }
                // What the detail reads, continuous where the lowest or the nearest link changes: each link's, fading
                // from its axis to before the links read change, the largest.
                const float near = 1.0 - smoothstep(0.1, 0.35, d / cellM);
                v.incision = max(v.incision, depth * near);
                v.glacier = max(v.glacier, glacier * near);
                v.floorShare = max(v.floorShare, outlet ? 0.0 : s.y * (1.0 - beyond));
                if (d < nearest) nearest = d, v.level = z;
            }
            if (head) break;
        }
    }
    return v;
}

// The ground h lowered by the valleys: by as much as their surface lies under the coarse ground, the large forms and the
// widest octaves, by a minimum smoothed over k (m), never under the water's level. The finer detail rides on the valley's
// walls; on its floor both signs of the residual detail fade to the water level. The carving distance opens the
// correction continuously: a valley which does not lower the coarse ground cannot move its detail either.
float ErosionCarve(float h, float coarse, ErosionValley v, float k)
{
    const float e = max(k - abs(coarse - v.surface), 0.0) / k;
    const float bed = min(coarse, v.surface) - 0.25 * k * e * e;
    const float cut = max(bed, min(coarse, v.level));
    // The water clamp makes a flat floor across the submerged part of a U profile, beyond its quiet middle.
    // Include that whole floor; on the walls use the same floor share as the detail, with a k-metre height transition.
    const float wet = 1.0 - smoothstep(0.0, k, bed - v.level);
    const float floor = max(v.floorShare, wet) * smoothstep(0.0, k, coarse - cut);
    return lerp(h - coarse + cut, cut, floor);
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
// and the deeper sea floor stays unchanged. The face's lowering is bounded by Hc minus the foot, even on a coarse mesh:
// widening the height interval can never turn a mountain into a platform. No horizontal profile places this face.
float ErosionCliffProfile(float h, float hc, float delta, float depth)
{
    const float platform = EROSION_CLIFF_PLATFORM.x - depth * (1.0 - min(h / hc, 1.0));
    const float face = 1.0 - smoothstep(hc, hc + delta, h);
    const float cut = min(max(h - platform, 0.0), (hc - EROSION_CLIFF_PLATFORM.x) * face);
    return h - cut;
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
    // Keep the coastal gradient as a floor in hollows. The same broad slope controls the contour and its mesh widening.
    const float g = max(ErosionCoastSlope(formsGradient, d, detailSlope), max(coastSlope * shoreMetric * 0.001, 1e-6));
    const float hc = clamp(1000.0 * retreat * g, EROSION_CLIFF_HEIGHT.x, EROSION_CLIFF_HEIGHT.y);
    const float delta = max(EROSION_CLIFF_FACE * hc, 2000.0 * cellKm * g);
    const float depth = min(1000.0 * retreat * EROSION_CLIFF_PLATFORM.y, EROSION_CLIFF_PLATFORM.z);
    float surface = ErosionCliffProfile(h, hc, delta, depth);
    [branch] if (surface == h) return h; // Neither a talus nor a preserved remnant can lower an unchanged point.
    // Rockfall at 35 degrees on the coastal slope, expressed through height below the contour. It cannot raise the
    // original ground. Valley floors may breach this contour: they are inlets, not mountains to extrapolate upward.
    const float patch = smoothstep(-0.2, 0.6, ErosionCliffNoise(p, 0.9, seed + 1u));
    const float talus = hc * EROSION_CLIFF_SCREE.y * patch;
    const float scree = max(talus - EROSION_CLIFF_SCREE.x * abs(h - hc) / g, 0.0);
    const float platform = EROSION_CLIFF_PLATFORM.x - depth * (1.0 - min(h / hc, 1.0));
    surface = min(h, max(surface, platform + scree));
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
