// Noise.hlsli - the relief's noise bricks (Relief.hlsli; docs/geometrie.md): a gradient noise on the integer lattice, with
// its derivatives too, and its fractal sums, fBm, billow, ridged multifractal, a Voronoi distance, a vector turbulence.
// Exolune's own code.
//
// Precision: the point and the frequencies are doubles; only the lattice split runs in double, the noise itself in float.
// Each octave's split gives an integer cell and a float remainder, three ways: exact, in doubles (gExactLattice); float,
// for cells of 4 m and more; in pairs of floats, about 48 bits, under LATTICE_PAIRS only (TerrainComputePairs.hlsl).
// Filtering: an octave the vertex cannot carry fades out and is replaced by its mean (gMaxFrequency); the creases of the
// billow and the ridged are rounded over about a cell, their mean kept (gCreaseMaxFrequency).
// The CPU port, the same hash and gradients: tools/hydro/cp.py. A change here goes there too.
#ifndef RELIEF_NOISE_HLSLI
#define RELIEF_NOISE_HLSLI

#include "PlanetSettings.hlsli"

// The thread's state, written by the callers before ReliefElevation.
static float gMaxFrequency = NO_LIMIT;       // the highest frequency the vertex can show, cycles per unit sphere radius
static float gCreaseMaxFrequency = NO_LIMIT; // the same, for the creases' rounding
static bool gExactLattice = true;            // the lattice split in doubles
#ifdef LATTICE_PAIRS
static bool gLatticePairs = false;           // the lattice split in pairs of floats
#endif

// The noise's deviation, per quality its scale to it, and the means of the filtered signals at that deviation, measured
// on the noise itself (tools/hydro/cp.py): the billow's 2 E|n| - 1, the ridged's E[(1 - |n|)^2], the Voronoi's.
static const float RL_SIGMA = 0.4;
static const float RL_SCALE_STANDARD = 2.1935;
static const float RL_SCALE_BEST = 2.0961;
static const float RL_MEAN_BILLOW_STANDARD = -0.3503;
static const float RL_MEAN_BILLOW_BEST = -0.3448;
static const float RL_MEAN_RIDGED_STANDARD = 0.5103;
static const float RL_MEAN_RIDGED_BEST = 0.5048;
static const float RL_MEAN_VORONOI = -0.0550;

// The gradients: 256 unit vectors on a Fibonacci spiral, z = 1 - (2i + 1) / 256 at the angle i pi (3 - sqrt 5), in float.
static const float3 RL_GRADIENTS[256] = {
#define RELIEF_GRADIENT(x, y, z) float3(x, y, z),
#include "ReliefGradients.inl"
#undef RELIEF_GRADIENT
};

// Read at scattered indices: cheaper in group memory than in a constant. Loaded by every thread group that evaluates the
// relief, before any return.
#ifdef RELIEF_PIXEL
#define rlGradients reliefGradients
#else
groupshared float3 rlGradients[256];

void LoadGradients(uint threadInGroup, uint groupSize)
{
    for (uint i = threadInGroup; i < 256; i += groupSize)
        rlGradients[i] = RL_GRADIENTS[i];
    GroupMemoryBarrierWithGroupSync();
}
#endif

// ---------------------------------------------------------------------------------------------
// The lattice
// ---------------------------------------------------------------------------------------------

struct RlPoint
{
    double3 p;
#ifdef LATTICE_PAIRS
    float3 hi, lo; // the point in a pair of floats: its float, and the rest
#endif
};

RlPoint RlMakePoint(double3 p)
{
    RlPoint r;
    r.p = p;
#ifdef LATTICE_PAIRS
    r.hi = (float3)p;
    r.lo = (float3)(p - (double3)r.hi);
#endif
    return r;
}

// An octave's lattice point: its integer cell and the remainder, in [0, 1) but for rounding.
struct RlCell
{
    int3 cell;
    float3 q;
};

#ifdef LATTICE_PAIRS
// p f in a pair of floats: the high parts' exact product by Dekker's method, Veltkamp's split by 2^12 + 1; the cross terms
// added to its error, then a fast two-sum. The cell is the high part's floor.
RlCell RlSplitPairs(RlPoint pt, double f)
{
    precise float fh = (float)f;
    precise float fl = (float)(f - (double)fh);
    precise float cf = 4097.0 * fh;
    precise float fhh = cf - (cf - fh);
    precise float fhl = fh - fhh;
    precise float3 cp = 4097.0 * pt.hi;
    precise float3 phh = cp - (cp - pt.hi);
    precise float3 phl = pt.hi - phh;
    precise float3 prod = pt.hi * fh;
    precise float3 err = (((phh * fhh - prod) + phh * fhl + phl * fhh) + phl * fhl) + (pt.hi * fl + pt.lo * fh);
    precise float3 s = prod + err;
    precise float3 e = err - (s - prod);
    precise float3 c = floor(s);
    RlCell l;
    l.cell = (int3)c;
    l.q = (s - c) + e;
    return l;
}
#endif

RlCell RlSplit(RlPoint pt, double f)
{
#ifdef LATTICE_PAIRS
    [branch] if (gLatticePairs && gExactLattice)
        return RlSplitPairs(pt, f);
#endif
    RlCell l;
    [branch] if (gExactLattice)
    {
        const double3 x = pt.p * f;
        const float3 c = floor((float3)x);
        l.cell = (int3)c;
        l.q = (float3)(x - (double3)c);
    }
    else
    {
        const float3 x = (float3)pt.p * (float)f;
        const float3 c = floor(x);
        l.cell = (int3)c;
        l.q = x - c;
    }
    return l;
}

// Each octave's lattice shifted by a fraction of a cell: no two octaves share their nodes (docs/principes.md).
float3 RlShift(int octave)
{
    return frac((float)octave * float3(0.7548776662, 0.5698402910, 0.4142135624));
}

// ---------------------------------------------------------------------------------------------
// The hash: xxHash32's rounds nested axis by axis, the cell's corners sharing them, then the seed and the avalanche.
// ---------------------------------------------------------------------------------------------

uint RlRound1(uint h, uint v)
{
    h += v * 0x85EBCA77u;
    h = (h << 13) | (h >> 19);
    return h * 0x9E3779B1u;
}

uint4 RlRound4(uint4 h, uint4 v)
{
    h += v * 0x85EBCA77u;
    h = (h << 13) | (h >> 19);
    return h * 0x9E3779B1u;
}

uint4 RlMix4(uint4 h)
{
    h ^= h >> 15;
    h *= 0x85EBCA77u;
    h ^= h >> 13;
    h *= 0xC2B2AE3Du;
    return h ^ (h >> 16);
}

uint RlMix1(uint h)
{
    h ^= h >> 15;
    h *= 0x85EBCA77u;
    h ^= h >> 13;
    h *= 0xC2B2AE3Du;
    return h ^ (h >> 16);
}

// The cell's eight corners, before the seed: h0 at z, h1 at z + 1; in each, x, x + 1, then y + 1.
void RlCornerHashes(int3 c, out uint4 h0, out uint4 h1)
{
    const uint x = asuint(c.x), y = asuint(c.y), z = asuint(c.z);
    const uint4 a = RlRound4(0x165667B1u.xxxx, uint4(x, x + 1u, x, x + 1u));
    const uint4 b = RlRound4(a, uint4(y, y, y + 1u, y + 1u));
    h0 = RlRound4(b, z.xxxx);
    h1 = RlRound4(b, (z + 1u).xxxx);
}

// A value in [-1, 1) per cell hash and seed.
float RlValue(uint h, uint seed)
{
    return (float)(RlMix1(h + seed * 0x27D4EB2Fu) >> 8) * (2.0 / 16777216.0) - 1.0;
}

// ---------------------------------------------------------------------------------------------
// The gradient noise
// ---------------------------------------------------------------------------------------------

// The blend weights: standard, 3t^2 - 2t^3, C1; best, 6t^5 - 15t^4 + 10t^3, C2.
float3 RlFade(float3 t, bool best)
{
    return best ? t * t * t * (t * (t * 6.0 - 15.0) + 10.0) : t * t * (3.0 - 2.0 * t);
}

// The eight corners' gradients against the point, blended; unscaled.
float RlCorners(uint4 h0, uint4 h1, uint seed, float3 q, float3 s)
{
    const uint k = seed * 0x27D4EB2Fu;
    const uint4 g0 = RlMix4(h0 + k) >> 24, g1 = RlMix4(h1 + k) >> 24;
    const float3 r = q - 1.0;
    const float4 n0 = float4(dot(rlGradients[g0.x].xyz, q), dot(rlGradients[g0.z].xyz, float3(q.x, r.y, q.z)),
                             dot(rlGradients[g1.x].xyz, float3(q.x, q.y, r.z)), dot(rlGradients[g1.z].xyz, float3(q.x, r.y, r.z)));
    const float4 n1 = float4(dot(rlGradients[g0.y].xyz, float3(r.x, q.y, q.z)), dot(rlGradients[g0.w].xyz, float3(r.x, r.y, q.z)),
                             dot(rlGradients[g1.y].xyz, float3(r.x, q.y, r.z)), dot(rlGradients[g1.w].xyz, r));
    const float4 x = n0 + s.x * (n1 - n0);
    const float2 y = x.xz + s.y * (x.yw - x.xz);
    return y.x + s.z * (y.y - y.x);
}

// One octave at the cell and its remainder, deviation RL_SIGMA. The remainder may leave [0, 1): its floor moves the cell.
float RlGradientNoise(int3 cell, float3 q, uint seed, bool best)
{
    const float3 fl = floor(q);
    cell += (int3)fl;
    q -= fl;
    uint4 h0, h1;
    RlCornerHashes(cell, h0, h1);
    return RlCorners(h0, h1, seed, q, RlFade(q, best)) * (best ? RL_SCALE_BEST : RL_SCALE_STANDARD);
}

// The eight corners' gradients against the point, blended, and the blend's gradient against q; unscaled, the weights of
// either quality.
float4 RlCornersD(uint4 h0, uint4 h1, uint seed, float3 q, bool best)
{
    const uint k = seed * 0x27D4EB2Fu;
    const uint4 i0 = RlMix4(h0 + k) >> 24, i1 = RlMix4(h1 + k) >> 24;
    const float3 g000 = rlGradients[i0.x].xyz, g100 = rlGradients[i0.y].xyz, g010 = rlGradients[i0.z].xyz, g110 = rlGradients[i0.w].xyz;
    const float3 g001 = rlGradients[i1.x].xyz, g101 = rlGradients[i1.y].xyz, g011 = rlGradients[i1.z].xyz, g111 = rlGradients[i1.w].xyz;
    const float3 r = q - 1.0;
    const float n000 = dot(g000, q), n100 = dot(g100, float3(r.x, q.y, q.z)), n010 = dot(g010, float3(q.x, r.y, q.z));
    const float n110 = dot(g110, float3(r.x, r.y, q.z)), n001 = dot(g001, float3(q.x, q.y, r.z));
    const float n101 = dot(g101, float3(r.x, q.y, r.z)), n011 = dot(g011, float3(q.x, r.y, r.z)), n111 = dot(g111, r);
    const float3 s = RlFade(q, best), ds = best ? 30.0 * q * q * r * r : -6.0 * q * r;
    // The trilinear blend as a polynomial in the weights, for the values and for the corners' gradients.
    const float k1 = n100 - n000, k2 = n010 - n000, k3 = n001 - n000, k4 = n000 - n100 - n010 + n110;
    const float k5 = n000 - n010 - n001 + n011, k6 = n000 - n100 - n001 + n101;
    const float k7 = n100 + n010 + n001 + n111 - n000 - n110 - n101 - n011;
    const float3 a1 = g100 - g000, a2 = g010 - g000, a3 = g001 - g000, a4 = g000 - g100 - g010 + g110;
    const float3 a5 = g000 - g010 - g001 + g011, a6 = g000 - g100 - g001 + g101;
    const float3 a7 = g100 + g010 + g001 + g111 - g000 - g110 - g101 - g011;
    const float value = n000 + k1 * s.x + k2 * s.y + k3 * s.z + k4 * s.x * s.y + k5 * s.y * s.z + k6 * s.z * s.x
                      + k7 * s.x * s.y * s.z;
    const float3 gradient = g000 + a1 * s.x + a2 * s.y + a3 * s.z + a4 * s.x * s.y + a5 * s.y * s.z + a6 * s.z * s.x
                          + a7 * s.x * s.y * s.z
                          + ds * float3(k1 + k4 * s.y + k6 * s.z + k7 * s.y * s.z, k2 + k5 * s.z + k4 * s.x + k7 * s.z * s.x,
                                        k3 + k6 * s.x + k5 * s.y + k7 * s.x * s.y);
    return float4(value, gradient);
}

// One octave and its gradient against the lattice coordinates, best quality: x the value, deviation RL_SIGMA; yzw its
// derivatives, exact, continuous from cell to cell with the quintic blend. The relief's slopes and erosion (Relief.hlsli).
float4 RlGradientNoiseD(int3 cell, float3 q, uint seed)
{
    const float3 fl = floor(q);
    cell += (int3)fl;
    q -= fl;
    uint4 h0, h1;
    RlCornerHashes(cell, h0, h1);
    return RlCornersD(h0, h1, seed, q, true) * RL_SCALE_BEST;
}

// ---------------------------------------------------------------------------------------------
// Filtering
// ---------------------------------------------------------------------------------------------

// An octave's weight: whole while its wavelength exceeds 2 MESH_BAND_LIMIT cells, gone at MESH_BAND_LIMIT.
float RlWeight(float f)
{
    return saturate(2.0 - 2.0 * f / gMaxFrequency);
}

// erf for x >= 0, Abramowitz and Stegun 7.1.26: error under 1.5e-7.
float RlErf(float x)
{
    const float t = 1.0 / (1.0 + 0.3275911 * x);
    return 1.0 - t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))) * exp(-x * x);
}

// The rounded |x|'s mean excess over |x| for a normal noise of deviation RL_SIGMA. Under e = sigma, its series to e^8,
// within 1e-6: the closed form subtracts nearly equal terms there and divides by e.
float RlCreaseExcess(float e)
{
    const float s = RL_SIGMA, s2 = RL_SIGMA * RL_SIGMA, phi0 = 0.39894228;
    [branch] if (e < s)
    {
        const float e2 = e * e, r = e2 / s2;
        return phi0 / s * e2 * (1.0 / 3.0 + r * (-1.0 / 60.0 + r * (1.0 / 840.0 - r / 12096.0)));
    }
    const float u = e / s, er = RlErf(u * 0.70710678), ph = phi0 * exp(-0.5 * u * u);
    return s2 / (2.0 * e) * (er - 2.0 * u * ph) + 0.5 * e * er - 2.0 * s * (phi0 - ph);
}

// |x| rounded by a parabola over |x| < e, e = CREASE_ROUNDING f / gCreaseMaxFrequency, less its mean excess.
float RlCrease(float x, float f)
{
    const float e = CREASE_ROUNDING * f / gCreaseMaxFrequency, a = abs(x);
    [branch] if (e <= 0.0)
        return a;
    return (a >= e ? a : 0.5 * (x * x / e + e)) - RlCreaseExcess(e);
}

// ---------------------------------------------------------------------------------------------
// The fractal sums. Persistence 0.5; octave o has frequency f L^o and seed seed + o.
// ---------------------------------------------------------------------------------------------

float RlFbm(RlPoint pt, double f, double lacunarity, int octaves, uint seed, bool best)
{
    float sum = 0.0, amplitude = 1.0;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float w = RlWeight((float)f);
        [branch] if (w <= 0.0)
            break; // the finer octaves are filtered out too, and their mean is 0
        const RlCell l = RlSplit(pt, f);
        sum += amplitude * w * RlGradientNoise(l.cell, l.q + RlShift(o), seed + (uint)o, best);
        f *= lacunarity;
        amplitude *= 0.5;
    }
    return sum;
}

float RlBillow(RlPoint pt, double f, double lacunarity, int octaves, uint seed, bool best)
{
    const float mean = best ? RL_MEAN_BILLOW_BEST : RL_MEAN_BILLOW_STANDARD;
    float sum = 0.5, amplitude = 1.0;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float fo = (float)f, w = RlWeight(fo);
        float b = mean;
        [branch] if (w > 0.0)
        {
            const RlCell l = RlSplit(pt, f);
            b = mean + w * (2.0 * RlCrease(RlGradientNoise(l.cell, l.q + RlShift(o), seed + (uint)o, best), fo) - 1.0 - mean);
        }
        sum += amplitude * b;
        f *= lacunarity;
        amplitude *= 0.5;
    }
    return sum;
}

// Offset 1, gain 2, spectral exponent 1: each octave's signal weighted by the previous one's.
float RlRidged(RlPoint pt, double f, double lacunarity, int octaves, uint seed, bool best)
{
    const float mean = best ? RL_MEAN_RIDGED_BEST : RL_MEAN_RIDGED_STANDARD, spectralStep = 1.0 / (float)lacunarity;
    float sum = 0.0, chain = 1.0, spectral = 1.0;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float fo = (float)f, w = RlWeight(fo);
        float r = mean;
        [branch] if (w > 0.0)
        {
            const RlCell l = RlSplit(pt, f);
            const float a = 1.0 - RlCrease(RlGradientNoise(l.cell, l.q + RlShift(o), seed + (uint)o, best), fo);
            r = mean + w * (a * a - mean);
        }
        r *= chain;
        chain = saturate(2.0 * r);
        sum += r * spectral;
        f *= lacunarity;
        spectral *= spectralStep;
    }
    return 1.25 * sum - 1.0;
}

// The distance to the nearest seed point, sqrt(3) d - 1, in lattice units: one seed per cell, its corner moved by three
// values in [-1, 1], seeds seed to seed + 2; the cells at +-2 around the point's.
float RlVoronoi(RlPoint pt, double f, uint seed)
{
    const float w = RlWeight((float)f);
    [branch] if (w <= 0.0)
        return RL_MEAN_VORONOI;
    const RlCell l = RlSplit(pt, f);
    const float3 fl = floor(l.q), q = l.q - fl;
    const int3 c = l.cell + (int3)fl;
    float nearest = 1e30;
    [loop] for (int dz = -2; dz <= 2; ++dz)
    {
        [loop] for (int dy = -2; dy <= 2; ++dy)
        {
            [loop] for (int dx = -2; dx <= 2; ++dx)
            {
                const int3 k = c + int3(dx, dy, dz);
                const uint h = RlRound1(RlRound1(RlRound1(0x165667B1u, asuint(k.x)), asuint(k.y)), asuint(k.z));
                const float3 v = float3(dx, dy, dz) + float3(RlValue(h, seed), RlValue(h, seed + 1u), RlValue(h, seed + 2u)) - q;
                nearest = min(nearest, dot(v, v));
            }
        }
    }
    return RL_MEAN_VORONOI + w * (1.7320508 * sqrt(nearest) - 1.0 - RL_MEAN_VORONOI);
}

// The point displaced by power times three fBm of lacunarity 2, standard quality, one per axis, seeds seed, seed + 16,
// seed + 32: the three share the lattice split, the corners' hashes and the blend weights. No displacement at all when
// the first octave is filtered out.
RlPoint RlTurbulence(RlPoint pt, double f, float power, int octaves, uint seed)
{
    [branch] if (RlWeight((float)f) <= 0.0)
        return pt;
    float3 d = 0.0;
    float amplitude = RL_SCALE_STANDARD;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float w = RlWeight((float)f);
        [branch] if (w <= 0.0)
            break;
        const RlCell l = RlSplit(pt, f);
        float3 q = l.q + RlShift(o);
        const float3 fl = floor(q);
        q -= fl;
        uint4 h0, h1;
        RlCornerHashes(l.cell + (int3)fl, h0, h1);
        const float3 s = RlFade(q, false);
        const uint so = seed + (uint)o;
        d += amplitude * w * float3(RlCorners(h0, h1, so, q, s), RlCorners(h0, h1, so + 16u, q, s),
                                    RlCorners(h0, h1, so + 32u, q, s));
        f *= 2.0;
        amplitude *= 0.5;
    }
    return RlMakePoint(pt.p + (double3)(power * d));
}

// RlTurbulence's Jacobian: the displaced point's derivatives, row i its axis i, along the point's axes.
float3x3 RlTurbulenceJacobian(RlPoint pt, double f, float power, int octaves, uint seed)
{
    float3x3 j = float3x3(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0);
    [branch] if (RlWeight((float)f) <= 0.0)
        return j;
    float amplitude = RL_SCALE_STANDARD;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float w = RlWeight((float)f);
        [branch] if (w <= 0.0)
            break;
        const RlCell l = RlSplit(pt, f);
        float3 q = l.q + RlShift(o);
        const float3 fl = floor(q);
        q -= fl;
        uint4 h0, h1;
        RlCornerHashes(l.cell + (int3)fl, h0, h1);
        const uint so = seed + (uint)o;
        const float k = power * amplitude * w * (float)f;
        j[0] += k * RlCornersD(h0, h1, so, q, false).yzw;
        j[1] += k * RlCornersD(h0, h1, so + 16u, q, false).yzw;
        j[2] += k * RlCornersD(h0, h1, so + 32u, q, false).yzw;
        f *= 2.0;
        amplitude *= 0.5;
    }
    return j;
}

#endif
