// Relief.hlsli - the planet's relief (docs/spec-relief-tectonique.md, docs/geometrie.md). Exolune's own code.
// 1. The large forms, over 50 km, from the tectonic map (Tectonics.hlsli), read at a point warped by a noise of 800 to 25
//    km: the map's elevation, then the sharp profiles of the boundaries, trench, ridge, rift, transform, on its distances;
//    then the coasts, from 60 to 3 km, the level moved near the shore, indented on the steep coasts, barred by spits and
//    lagoons on the flat ones.
// 2. The detail, under 50 km, from the noise of Noise.hlsli shaped by the map's geology: its amplitude, its youth and its
//    strata. Ridged octaves on the chains, their crests sharp on the young ones, worn on the old; gradient noise elsewhere,
//    hills and plains; each octave's slope weakens the finer ones, as erosion smooths the slopes. The chains' widest
//    ridged octave in folds along them, chaînons and the valleys between; their next two octaves warped and stretched
//    along them; terraces on the platforms, mesas; fine gullies in soft sediments, badlands.
// 3. The volcanoes' edifices (Volcanoes.hlsli), on the large forms, before the detail, which their young flanks quiet;
//    after it, the old islands' tops planed, the reefs and their lagoons.
// 4. The level 0 valleys, gullies and deposits, then wave-cut cliffs (Erosion.hlsli), before the barriers and volcanic
//    finish; with EROSION_RAVINES, step A, the ravines instead of the network: gullies down the slope of everything coarser,
//    octave by octave (ReliefDetail); with EROSION_RIVERS, step B, on them, the corridors of the level 0's rivers and their
//    water (ErosionRivers). With valleys=false, the complete pre-erosion form, including volcanoes, supplies the drainage
//    and sea witness.
// Units: metres and kilometres; a noise frequency of 1 has a wavelength of one radius. The CPU port: tools/hydro/cp.py.
#ifndef RELIEF_HLSLI
#define RELIEF_HLSLI

#include "PlanetSettings.hlsli"
#include "Noise.hlsli"
#include "Tectonics.hlsli"
#include "Volcanoes.hlsli"
#include "Erosion.hlsli"

// The erosion shown, to compare in flight (key 1, D3DApp): 2 ravines and rivers, 1 ravines only, 0 none, the form before
// erosion. From the frame's constants where a pass has them; the passes without them (flight contact, walking, the
// cinematic ground, startup) keep the full erosion.
uint ErosionMode()
{
#ifdef PLANET_HLSLI
    return erosionMode.x;
#else
    return 2u;
#endif
}

bool ErosionRavines() { return EROSION_RAVINES && ErosionMode() >= 1u; }
bool ErosionRivers() { return EROSION_RAVINES && EROSION_RIVERS && ErosionMode() >= 2u; }

// The roughness of the last point evaluated, 0 smooth plains to 1 young mountains: the slopes the mesh hides
// (Materials.hlsli).
static float gRoughness = 0.0;
// The footprint (km) of the pixels that read the sample, when wider than its own cell: its rivers are filtered at it.
// Only the fine grid's limb samples under a full screen relief set it (FineTerrain.hlsl).
static float gRiverCellKm = 0.0;
static float gWaterLevel = 0.0;
static float3 gWaterFlow = 0.0;
static float gWaterDistance = 1e9;
static float gRiverBank = 0.0;
static float gWaterClearance = -1e9;
static float gWaterDepth = 0.0; // footprint mean; separate from stage minus the filtered bed
static float gWaterCoverage = 0.0;
static float gRiverCoverage = 0.0;
static float gLakeClearance = -1e9;

// Brick k's seeds, 64 each.
uint ReliefSeed(uint k)
{
    return (uint)PLANET_SEED * 4096u + 64u * k;
}

// A noise frequency for a wavelength (km).
double ReliefFrequency(float km)
{
    return (double)(PLANET_RADIUS_KM / km);
}

// The mesh's cell (km), from the octave filter: 0 when nothing is filtered.
float ReliefCellKm()
{
    return PLANET_RADIUS_KM / (MESH_BAND_LIMIT * gMaxFrequency);
}

// |x| rounded over |x| < e, its mean over the noise kept (RlCreaseExcess); slope its derivative.
float ReliefCrease(float x, float e, out float slope)
{
    const float a = abs(x);
    [branch] if (a >= e)
    {
        slope = sign(x);
        return a - RlCreaseExcess(e);
    }
    slope = x / e;
    return 0.5 * (x * x / e + e) - RlCreaseExcess(e);
}

// Sharpen |cos| with a monotone quadratic, continued linearly beyond its amplitude: (1+b)u-bu^2, b <= 1.
// Round over the same input interval e as ReliefCrease, never a power of its nearly zero centred output. Return the
// change to that crease, centred by the exact |cos| moments, including the rounding: no mesh-dependent mean shift.
// The derivative stays finite, and is zero at x=0. At b=0 both changes are exactly zero.
float ReliefSharpenCrease(float x, float e, float b, out float slope)
{
    const float mean = 2.0 / 3.14159265;
    const float scale = 0.5 * 3.14159265 * 0.5 * (1.0 + RL_MEAN_BILLOW_BEST);
    const float u = abs(x) / scale, r = e / scale;
    const float base = u < r ? 0.5 * (u * u / r + r) : u;
    const float derivative = u < r ? x / e : sign(x);
    const float k = mean / ((1.0 + b) * mean - 0.5 * b);
    [branch] if (r >= 1.0)
    {
        const float change = k * (1.0 - b) - 1.0;
        slope = change * derivative;
        return scale * change * (base - (0.5 * r + 0.25 / r));
    }
    // E[rounded |cos|] - E[|cos|]; the series avoids cancellation in the closed form at small r.
    const float rr = r * r;
    float excess;
    [branch] if (r < 0.1)
        excess = rr / 3.14159265 * (1.0 / 3.0 + rr * (1.0 / 60.0 + rr / 280.0));
    else
    {
        const float root = sqrt(1.0 - rr), angle = asin(r);
        excess = (rr * angle - 2.0 * r * (1.0 - root) + 0.5 * (angle - r * root)) / (3.14159265 * r);
    }
    const float square = u < 1.0 ? u * u : 2.0 * u - 1.0;
    const float change = k * (1.0 + b) - 1.0;
    slope = change * derivative - k * b * 2.0 * min(u, 1.0) * sign(x);
    return scale * (change * (base - mean - excess) - k * b * (square - 0.5));
}

// The mean of ReliefCrease on a sinusoidal stripe, including its mesh rounding. SharpenCrease adds zero to this mean.
float ReliefStripeMean(float e)
{
    const float mean = 2.0 / 3.14159265, scale = 0.5 * 3.14159265 * 0.5 * (1.0 + RL_MEAN_BILLOW_BEST);
    const float r = e / scale, rr = r * r;
    float value;
    [branch] if (r >= 1.0)
        value = scale * (0.5 * r + 0.25 / r);
    else
    {
        float excess;
        [branch] if (r < 0.1)
            excess = rr / 3.14159265 * (1.0 / 3.0 + rr * (1.0 / 60.0 + rr / 280.0));
        else
        {
            const float root = sqrt(1.0 - rr), angle = asin(r);
            excess = (rr * angle - 2.0 * r * (1.0 - root) + 0.5 * (angle - r * root)) / (3.14159265 * r);
        }
        value = scale * (mean + excess);
    }
    return value - RlCreaseExcess(e);
}

// Reserve the ordinary octave before admitting a replacement. The quadratic headroom is C1 at exhaustion; rational
// saturation bounds the added slope without a clamp of the height or a phase-dependent change of the stripe's mean.
float ReliefGullyGain(float under, float normal, float stripe, float share, float critical)
{
    const float left = max(critical - under - normal, 0.0);
    const float budget = left * left / critical, own = share * (normal + stripe);
    return budget / sqrt(budget * budget + own * own + 1e-30);
}

// Rock applies to broad mountain incisions, not to the mantle's fine gullies. The equilibrium line strengthens an
// already rocky chain; its absence must not turn the whole chain into soil. No current octave phase enters this share.
float ReliefGullyRock(float wavelength, float relief, float mountains, float glacial)
{
    return mountains * smoothstep(EROSION_GULLY_ROCK_RELIEF.x, EROSION_GULLY_ROCK_RELIEF.y, relief)
         * smoothstep(EROSION_GULLY_MANTLE.x, EROSION_GULLY_MANTLE.y, wavelength) * (0.8 + 0.2 * glacial);
}

// A tectonic map's gradient, per unit of its face's coordinates (TectonicFace), per radian at the unit direction d: through
// the gnomonic projection, divided by the face normal's share m of d, that normal's share of the gradient dropped. Near the
// face edges, where faces blend, taken as the main face's. The map's own readers keep its gradient as it is.
float3 ReliefMapSlope(float3 g, float3 d)
{
    const float3 a = abs(d);
    const float3 normal = a.x >= a.y && a.x >= a.z ? float3(sign(d.x), 0.0, 0.0)
                        : a.y >= a.z ? float3(0.0, sign(d.y), 0.0) : float3(0.0, 0.0, sign(d.z));
    const float m = dot(d, normal);
    return (g - dot(g, d) / m * normal) / m;
}

// The mean of sqrt(2 (1 + cos u) + r^2) over a turn: (2 / pi) sqrt(r^2 + 4) E(4 / (r^2 + 4)), E the complete elliptic
// integral of the second kind (Abramowitz and Stegun 17.3.36, error under 2e-8).
float ReliefRavineMean(float r)
{
    const float m1 = r * r / (r * r + 4.0);
    const float a = 1.0 + m1 * (0.44325141463 + m1 * (0.06260601220 + m1 * (0.04757383546 + m1 * 0.01736506451)));
    const float b = m1 * (0.24998368310 + m1 * (0.09200180037 + m1 * (0.04069697526 + m1 * 0.00526449639)));
    return 0.63661977 * sqrt(r * r + 4.0) * (a - b * log(m1));
}

// A ravine blend's profile (re = m cos u): 2 |cos(u / 2)| m, its trough rounded over r radians of phase, less its mean;
// d its derivatives in re and in m.
float ReliefRavineProfile(float re, float m, float r, out float2 d)
{
    const float root = sqrt(max(2.0 * m * (m + re), 0.0) + r * r * m * m), mean = ReliefRavineMean(r);
    const float inverse = 1.0 / max(root, 1e-30);
    d = float2(m * inverse, (2.0 * m + re + r * r * m) * inverse - mean);
    return root - mean * m;
}

// Ravine octave k's blend (docs/spec-erosion.md, the ravines): stripes of a period across `across`, a unit tangent, from
// the 8 corners of a lattice cell of a period, each anchoring them at a pivot jittered by its hash, blended by the quintic
// weights: where their phases cancel, a gully ends or two merge. Read at the point bent by one warp octave of the lattice
// (cell, q) of 2 periods, unshifted, whose halving is the stripes'. x the blend's real part, y its strength, both boosted
// by m (2 - m); dre, dm their gradients per metre along the ground, `across` held fixed.
float2 ReliefRavineBlend(int3 cell, float3 q, float3 up, float3 across, float period, uint k, out float3 dre, out float3 dm)
{
    const uint seed = ReliefSeed(20) + k;
    const float3 shift = RlShift((int)k);
    const float4 wx = RlGradientNoiseD(cell, q + shift, seed + 32u), wy = RlGradientNoiseD(cell, q + shift, seed + 48u);
    const float4 wz = RlGradientNoiseD(cell, q + shift, seed + 64u);
    const float bend = RAVINE_SHAPE.w / RL_SIGMA;
    float3 qs = 2.0 * q + bend * float3(wx.x, wy.x, wz.x) + shift;
    const float3 fl = floor(qs);
    qs -= fl;
    uint4 h0, h1;
    RlCornerHashes(2 * cell + (int3)fl, h0, h1);
    const float3 s = RlFade(qs, true), ds = 30.0 * qs * qs * (qs - 1.0) * (qs - 1.0);
    const float turn = 6.2831853;
    float2 sum = 0.0;
    float3 dRe = 0.0, dIm = 0.0;
    [unroll] for (int i = 0; i < 8; ++i)
    {
        const float3 corner = float3(i & 1, (i >> 1) & 1, i >> 2);
        const uint r = RlMix1((i < 4 ? h0[i] : h1[i - 4]) + seed * 0x27D4EB2Fu);
        const float3 jitter = float3(r & 1023u, (r >> 10) & 1023u, (r >> 20) & 1023u) / 1023.0 - 0.5;
        float sn, cs;
        sincos(turn * dot(qs - corner - RAVINE_SHAPE.z * jitter, across), sn, cs);
        const float3 t = lerp(1.0 - s, s, corner), dt = lerp(-ds, ds, corner);
        const float w = t.x * t.y * t.z;
        sum += w * float2(cs, sn);
        const float3 dw = float3(dt.x * t.y * t.z, t.x * dt.y * t.z, t.x * t.y * dt.z);
        dRe += cs * dw - turn * w * sn * across;
        dIm += sn * dw + turn * w * cs * across;
    }
    const float m = length(sum), boost = 2.0 - m;
    const float3 dM = (sum.x * dRe + sum.y * dIm) / max(m, 1e-20);
    // Per metre along the ground: the bent lattice's Jacobian, a stripe cell per period.
    const float3 u = boost * dRe - sum.x * dM, v = (2.0 - 2.0 * m) * dM;
    dre = (u + 0.5 * bend * (u.x * wx.yzw + u.y * wy.yzw + u.z * wz.yzw)) / period;
    dm = (v + 0.5 * bend * (v.x * wx.yzw + v.y * wy.yzw + v.z * wz.yzw)) / period;
    dre -= up * dot(dre, up);
    dm -= up * dot(dm, up);
    return float2(sum.x * boost, m * boost);
}

// A profile of half-width w (km), at least two mesh cells: wider, its depth falls in proportion, so that its mean stays.
float ReliefWidth(float w, float cellKm, inout float depth)
{
    const float wide = max(w, 2.0 * cellKm);
    depth *= w / wide;
    return wide;
}

// A Gaussian rise crossing the sea: its dry part, not just its support, must span two cells, or stay submerged.
// The lagoon flank mixes in `fan` of a Gaussian three times wider. Insert a flat core of half-width b and lower
// the amplitude by the area added: A w sqrt(pi) (1 + fan) is unchanged. Resolved profiles have b = 0, exactly.
// With L = max(log(A / -ground), 0), k = w min(sqrt(L), sqrt(pi) (1 + fan) L / 2), b = max(2 cell - k, 0):
// b >= cell carries any emergence; otherwise log(1 + t) <= t bounds both flanks above sea at cell, or the crest is wet.
// Parameters are local, as for ReliefWidth; no neighbour, camera distance or change to the underlying ground.
float ReliefSeaProfile(float x, float w, float cellKm, float ground, float amplitude, float fan)
{
    const float sqrtPi = 1.7724538509;
    float core = 0.0;
    [branch] if (ground < 0.0 && amplitude > 0.0)
    {
        const float head = log(max(amplitude / max(-ground, 1e-20), 1.0));
        const float kept = w * min(sqrt(head), 0.5 * sqrtPi * (1.0 + fan) * head);
        core = max(2.0 * cellKm - kept, 0.0);
        amplitude /= 1.0 + 2.0 * core / (sqrtPi * w * (1.0 + fan));
    }
    const float u = max(abs(x) - core, 0.0) / w;
    float g = exp(-u * u);
    [flatten] if (x > 0.0)
        g += fan * (exp(-u * u / 9.0) - g);
    return amplitude * g;
}

// `octaves` octaves of noise from the wavelength `topKm` down by RELIEF_LACUNARITY, at amplitude `relief` (m). Each
// octave's noise feeds two shapes: gradient noise, round hills; and ridged, 1 - |n| less its mean, crests and V valleys,
// each octave weakened in the valleys of the one above, its crest rounded over `crease` (noise units) or the mesh's
// rounding. `sharp` blends them. Each octave is weakened by the slope of the octaves above, 1 / (1 + k s^2), s in m/m,
// k RELIEF_EROSION for the hills, RELIEF_RIDGE_EROSION for the chains. The first `orientedOctaves` read `oriented`, the
// others `plain`. The first ridged octave takes `fold` (its value, its gradient per radian; ReliefFold) for `foldShare` of
// wide captures the wideOctaves widest octaves for the smooth barrier shore.
// its noise, `foldWeight` its filtering and amplitude. slope: the slope vector of the octaves summed; coarse: the sum of the
// octaves wider than EROSION_COARSE km, what the valleys carve (Erosion.hlsli).
// The gullies (ErosionGullies): from the octave EROSION_GULLY_FIRST on, the noise gives way, for `gullies.share` of it,
// to stripes down the slope of the ground under the octave, the large forms', or a valley's walls where it is carved, and
// the coarser octaves'; above the ice, rounded knife-edge crests. ErosionProfile alone shapes the U troughs.
// The ravines (step A, `gullies.ravines`; ReliefRavineBlend): RAVINE_OCTAVES octaves on the ground, x their height (m), yzw
// their slope, both apart from the detail's. Each runs down the slope of the large forms, of the octaves of wavelengths from
// 2 of its periods, their crests rounded at its scale, and of the coarser ravines, their troughs rounded so: once the next
// octave no longer steers it, it is drawn. Its gradient holds that steering fixed.
// fine: what step B's floodplains keep a share of (ErosionCorridor), the part of the sum a mesh of RIVER_FLOODPLAIN.y m would
// filter out, in noise units; and the ravines of periods under 2 RIVER_FLOODPLAIN.y, in metres.
float ReliefDetail(RlPoint oriented, RlPoint plain, int orientedOctaves, float topKm, int octaves, float relief, float sharp,
                   float crease, uint seed, float4 fold, float foldShare, float foldWeight, int wideOctaves, out float wide, ReliefGullies gullies,
                   out float3 slope, out float coarse, out float3 cliffSlope, out float4 ravine, out float2 fine)
{
    coarse = 0.0;
    fine = 0.0;
    const float floodplainFrequency = PLANET_RADIUS_KM / (MESH_BAND_LIMIT * 0.001 * RIVER_FLOODPLAIN.y);
    cliffSlope = 0.0;
    const float3 up = normalize((float3)plain.p);
    // The pending ravines' steering, slot i the ravine `ravineNext` + i's, in a tangent basis; the lattice of the first's
    // warp, in doubles once, the others' its doublings.
    const bool ravines = gullies.ravines > 0.0;
    const float3 t1 = normalize(cross(up, abs(up.y) < 0.9 ? float3(0.0, 1.0, 0.0) : float3(1.0, 0.0, 0.0))), t2 = cross(up, t1);
    float2 steer[RAVINE_OCTAVES];
    [unroll] for (int slot = 0; slot < RAVINE_OCTAVES; ++slot)
        steer[slot] = float2(dot(gullies.slope, t1), dot(gullies.slope, t2));
    int ravineNext = 0;
    RlCell ravineLattice = (RlCell)0;
    // The ravines this footprint can draw, wider than its band limit (RlWeight): a finer slot's steering is never read.
    int ravineDrawn = 0;
    [branch] if (ravines)
    {
        ravineLattice = RlSplit(plain, ReliefFrequency(0.002 * RAVINE_TOP));
        ravineDrawn = clamp((int)ceil(log2(RAVINE_TOP / (1000.0 * PLANET_RADIUS_KM)) + log2(min(gMaxFrequency, 1e30)) + 0.01), 0, RAVINE_OCTAVES);
    }
    ravine = 0.0;
    float round = 0.0, ridged = 0.0, chain = 1.0, amplitude = 1.0, crest = 0.0, top = 0.0;
    float3 roundSlope = 0.0, ridgedSlope = 0.0, coarseSlope = 0.0;
    wide = 0.0;
    double f = ReliefFrequency(topKm);
    const float metres = relief / (1000.0 * PLANET_RADIUS_KM); // a unit of noise per radius, in m/m at this amplitude
    // Near and above the equilibrium line, finite sharpening with the crease's own rounding and mean.
    const float bend = EROSION_GLACIAL_SHARPEN * gullies.glacial;
    const float meanAbs = 0.5 * (1.0 + RL_MEAN_BILLOW_BEST), stripeScale = 0.5 * 3.14159265 * meanAbs;
    const float mean = 2.0 / 3.14159265, sharpenSlope = mean * (1.0 + bend) / ((1.0 + bend) * mean - 0.5 * bend);
    // Phase-independent envelopes for unit gradient corners and quintic weights, in lattice units. The generous
    // Hessian envelope also covers the wide fold. No neighbouring terrain evaluation, map read or mesh-sized budget.
    const float noiseGradient = 26.0, noiseCurvature = 512.0;
    float curvature = 0.0;
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float w = RlWeight((float)f);
        [branch] if (w <= 0.0)
            break; // the finer octaves are filtered out too; both shapes' means are 0
        const float roundPrev = round, ridgedPrev = ridged;
        float ravineX = 0.0, ravineA = 0.0, ravineRounding = 0.0;
        float3 ravineGr = 0.0;
        // Decide from the complete parent, including both >20 km octaves. Suppressing or amplifying those octaves
        // before this decision made a valley invent the ground it was about to carve, including on uncut forest slopes.
        [branch] if (o == EROSION_GULLY_FIRST)
        {
            const float depth = max(gullies.ground + relief * coarse - gullies.surface, 0.0);
            gullies.carved = smoothstep(0.0, 800.0, depth);
            gullies.slope = lerp(gullies.slope, gullies.valleySlope, gullies.carved);
            gullies.share *= gullies.carved * (1.0 - 4.0 * gullies.carved * (1.0 - gullies.carved));
            amplitude *= max(1.0, EROSION_WALL_RELIEF * min(gullies.incision, depth) / max(relief, 1e-6));
        }
        RlCell l;
        [branch] if (o < orientedOctaves)
            l = RlSplit(oriented, f);
        else
            l = RlSplit(plain, f);
        const float4 n = RlGradientNoiseD(l.cell, l.q + RlShift(o), seed + (uint)o);
        const float3 roundBefore = roundSlope, ridgedBefore = ridgedSlope;
        float3 g = n.yzw * (float)f * metres;
        g -= up * dot(g, up); // along the ground
        // The ravines' steering: the octave's true slope, through the oriented point's Jacobian.
        float3 gs = g;
        [branch] if (ravines && o < orientedOctaves)
        {
            gs = mul(n.yzw, gullies.oriented) * ((float)f * metres);
            gs -= up * dot(gs, up);
        }
        float share = 0.0, limitedShare = 0.0;
        float4 stripe = 0.0;
        const float roundA = amplitude * w / (1.0 + RELIEF_EROSION * dot(roundSlope, roundSlope));
        const float folded = o == 1 || o == 2 ? 1.0 - 0.5 * foldShare * saturate(foldWeight) : 1.0;
        const float ridgeA = 1.7 * amplitude * w * chain * folded / (1.0 + RELIEF_RIDGE_EROSION * dot(ridgedSlope, ridgedSlope));
        [branch] if (o >= EROSION_GULLY_FIRST && gullies.share > 0.0 && PLANET_RADIUS_KM / (float)f > EROSION_GULLY.z)
        {
            // The ground's slope under the octave: the coarse octaves' does not count where a valley replaces them.
            const float3 under = gullies.slope + lerp(roundSlope, ridgedSlope, sharp) - gullies.carved * coarseSlope;
            const float steep = length(under);
            // None on the crests of the octave above and of the widest, the chains' and the folds', where the slope that
            // orients them turns over.
            share = gullies.share * smoothstep(EROSION_GULLY.x, EROSION_GULLY.y, steep) * (1.0 - smoothstep(0.85, 1.0, crest * sharp))
                  * (1.0 - smoothstep(0.9, 1.0, top * sharp));
            // The reserve uses full octave strength, before the mesh's weight. Besides its period, a stripe responds
            // to turns of its parent's slope across its two-period kernels: |d across| <= curvature / |under|.
            const float coefficient = lerp(roundA, ridgeA, sharp) / max(w, 1e-20);
            const float stripeCoefficient = lerp(roundA, ridgeA * sharpenSlope, sharp) / max(w, 1e-20);
            const float frequency = (float)f / (1000.0 * PLANET_RADIUS_KM);
            const float normalBound = noiseGradient * relief * frequency * coefficient;
            // The quintic kernel weights add at most 3 * (2 * 1.875) / 2 = 5.625 per period. Normalising the phasor
            // adds at most 2 / fork: the reserve includes weight changes and forks, not just the nominal wave slope.
            const float stripeBound = stripeScale * relief * stripeCoefficient * (2.0 / EROSION_GULLY_FORK)
                                    * (6.2831853 * (frequency + 4.0 * curvature / max(steep, EROSION_GULLY.x)) + 5.625 * frequency);
            // Rock may sustain a steeper wall, but its stripe still turns with the parent and still has forks.
            // Budgeting only amplitude / period on rock made kilometre waves oscillate over metres at those turns.
            // Use the same envelope for both materials; only the admissible slope changes.
            const float rock = ReliefGullyRock(PLANET_RADIUS_KM / (float)f, relief, sharp, gullies.glacial);
            const float critical = lerp(EROSION_GULLY_CRITICAL, EROSION_GULLY_ROCK, rock);
            limitedShare = share * ReliefGullyGain(steep, normalBound, stripeBound, share, critical);
            // The coastal contour keeps its existing >9 km calibration, before the soil-pattern budget.
            [branch] if (limitedShare > 0.0 || (share > 0.0 && PLANET_RADIUS_KM / (float)f > EROSION_CLIFF_SLOPE_KM))
            {
                const float3 across = cross(up, under) / steep;
                // The stripes' lattice: from the octave's own cell, halved, in floats; on the oriented octaves, the
                // plain point's, the stripes drawn in the ground's own measure.
                RlCell kernels;
                [branch] if (o < orientedOctaves)
                    kernels = RlSplit(plain, f / EROSION_GULLY_PERIODS);
                else
                    kernels.cell = l.cell >> 1, kernels.q = ((float3)(l.cell & 1) + l.q) * 0.5;
                stripe = ErosionGullies(kernels, across, seed + 32u + (uint)o);
                stripe.yzw *= (float)f * metres;
            }
        }
        [branch] if (sharp < 1.0)
        {
            round += roundA * n.x;
            roundSlope += roundA * g;
            [branch] if (limitedShare > 0.0)
            {
                round += roundA * limitedShare * (stripe.x - n.x);
                roundSlope += roundA * limitedShare * (stripe.yzw - g);
            }
        }
        [branch] if (sharp > 0.0)
        {
            float x = n.x, wr = w;
            float3 gr = g;
            ravineGr = gs;
            [branch] if (o == 0 && foldShare > 0.0)
            {
                float3 gf = fold.yzw * metres;
                gf -= up * dot(gf, up);
                x = lerp(x, fold.x, foldShare), gr = lerp(gr, gf, foldShare), wr = lerp(w, foldWeight, foldShare);
                ravineGr = lerp(gs, gf, foldShare);
            }
            float dc;
            const float rounding = max(crease, CREASE_ROUNDING * (float)f / gCreaseMaxFrequency);
            float c = ReliefCrease(x, rounding, dc);
            const float normalC = c, normalDc = dc;
            const float a = 1.7 * amplitude * wr * chain * folded / (1.0 + RELIEF_RIDGE_EROSION * dot(ridgedSlope, ridgedSlope));
            ravineX = x, ravineA = a, ravineRounding = rounding;
            [branch] if (limitedShare > 0.0)
            {
                float stripeDc;
                float stripeC = ReliefCrease(stripe.x, rounding, stripeDc);
                float derivative;
                stripeC += ReliefSharpenCrease(stripe.x, rounding, bend, derivative);
                stripeDc += derivative;
                // Both shapes are centred before blending. A smaller replacement never raises the whole octave.
                const float normalValue = meanAbs - normalC, stripeValue = ReliefStripeMean(rounding) - stripeC;
                ridged += ridgeA * limitedShare * (stripeValue - normalValue);
                ridgedSlope += ridgeA * limitedShare * (-stripeDc * stripe.yzw + normalDc * gr);
                c -= limitedShare * (stripeValue - normalValue);
            }
            const float r = 1.0 - c; // its mean, 1 - E|n|: the billow's mean says E|n| (Noise.hlsli)
            ridged += a * (1.0 - normalC - 0.5 * (1.0 - RL_MEAN_BILLOW_BEST));
            ridgedSlope += a * -normalDc * gr;
            chain = saturate(0.3 + 1.2 * r);
            crest = r;
            if (o == 0)
                top = r;
        }
        [branch] if (PLANET_RADIUS_KM / (float)f > EROSION_CLIFF_SLOPE_KM && share > 0.0)
        {
            const float mixed = lerp(n.x, stripe.x, share);
            const float3 mixedGradient = lerp(g, stripe.yzw, share);
            const float rounding = max(crease, CREASE_ROUNDING * (float)f / gCreaseMaxFrequency);
            float oldDc;
            ReliefCrease(mixed, rounding, oldDc);
            [branch] if (gullies.glacial > 0.0)
            {
                float derivative;
                ReliefSharpenCrease(mixed, rounding, bend, derivative);
                oldDc += share * derivative;
            }
            cliffSlope = lerp(roundBefore + roundA * mixedGradient, ridgedBefore + ridgeA * -oldDc * mixedGradient, sharp);
        }
        [branch] if (ravines)
        {
            // This octave in each pending ravine's steering: kept from 2 of its periods, as on a mesh of a period, its
            // crests rounded at that scale. Any visible ravine's octaves span over 4 cells: whole, as the mesh changes.
            const float lambda = 1000.0 * PLANET_RADIUS_KM / (float)f;
            const float2 roundPart = roundA * float2(dot(gs, t1), dot(gs, t2));
            const float2 ridgedPart = ravineA * float2(dot(ravineGr, t1), dot(ravineGr, t2));
            float t = MESH_BAND_LIMIT * RAVINE_TOP * exp2(-(float)ravineNext) / lambda;
            [unroll] for (int i = 0; i < RAVINE_OCTAVES; ++i, t *= 0.5)
                steer[i] += saturate(2.0 - 2.0 * t)
                          * lerp(roundPart, -clamp(ravineX / max(ravineRounding, CREASE_ROUNDING * t), -1.0, 1.0) * ridgedPart, sharp);
            // The ravines the next octave no longer steers, on the ground of the octaves that do.
            [loop] while (ravineNext < RAVINE_OCTAVES)
            {
                const float period = RAVINE_TOP * exp2(-(float)ravineNext);
                if (o + 1 < octaves && MESH_BAND_LIMIT * period * RELIEF_LACUNARITY < lambda)
                    break;
                const float kept = saturate(2.0 - 2.0 * MESH_BAND_LIMIT * period / lambda);
                const float level = gullies.ground + relief * lerp(lerp(roundPrev, round, kept), lerp(ridgedPrev, ridged, kept), sharp);
                const float steep = length(steer[0]), fp = 1000.0 * PLANET_RADIUS_KM / period;
                const float height = RAVINE_SHAPE.x * period * RAVINE_SHAPE.y * tanh(steep / RAVINE_SHAPE.y) * gullies.ravines
                                   * smoothstep(RAVINE_LAND.x, RAVINE_LAND.y, level) * RlWeight(fp);
                [branch] if (height > 0.0)
                {
                    const float3 across = (steer[0].x * t2 - steer[0].y * t1) / steep;
                    const float3 at = ravineLattice.q * exp2((float)ravineNext), whole = floor(at);
                    float3 dre, dm;
                    const float2 b = ReliefRavineBlend((ravineLattice.cell << ravineNext) + (int3)whole, at - whole, up, across,
                                                       period, (uint)ravineNext, dre, dm);
                    const float rounding = 6.2831853 * max(RAVINE_ROUNDING.x * fp / (MESH_BAND_LIMIT * gCreaseMaxFrequency), RAVINE_ROUNDING.y);
                    float2 d;
                    const float drawn = height * ReliefRavineProfile(b.x, b.y, rounding, d);
                    ravine.x += drawn;
                    fine.y += period < 2.0 * RIVER_FLOODPLAIN.y ? drawn : 0.0;
                    ravine.yzw += height * (d.x * dre + d.y * dm);
                    // The finer ravines steer down its walls, its troughs rounded at their scale.
                    const float2 re2 = RAVINE_STEER.x * height * float2(dot(dre, t1), dot(dre, t2));
                    const float2 m2 = RAVINE_STEER.x * height * float2(dot(dm, t1), dot(dm, t2));
                    [unroll] for (int j = 1; j < RAVINE_OCTAVES; ++j)
                    {
                        [branch] if (ravineNext + j < ravineDrawn)
                        {
                            ReliefRavineProfile(b.x, b.y, 6.2831853 * RAVINE_STEER.y * exp2(-(float)j), d);
                            steer[j] += d.x * re2 + d.y * m2;
                        }
                    }
                }
                [unroll] for (int j = 0; j + 1 < RAVINE_OCTAVES; ++j)
                    steer[j] = steer[j + 1];
                ++ravineNext;
            }
        }
        // Carry a phase-independent envelope of the parent's turning rate. Its crest width is intrinsic: the fixed
        // 2 m physical floor used by the exact terrain, never the current mesh's rounding or its octave weight.
        const float frequency = (float)f / (1000.0 * PLANET_RADIUS_KM);
        const float intrinsic = max(crease, CREASE_ROUNDING * MESH_BAND_LIMIT * CREASE_MIN_CELL * frequency);
        curvature += amplitude * relief * frequency * frequency
                   * (noiseCurvature + 1.7 * sharp * sharpenSlope * noiseGradient * noiseGradient / max(intrinsic, 1e-20));
        [flatten] if (o < wideOctaves)
            wide = lerp(round, ridged, sharp);
        if (f < PLANET_RADIUS_KM / EROSION_COARSE)
            coarse = lerp(round, ridged, sharp), coarseSlope = lerp(roundSlope, ridgedSlope, sharp);
        // Capture only scales broader than the maximum platform, in the existing sum with no additional noise read.
        if (f < PLANET_RADIUS_KM / EROSION_CLIFF_SLOPE_KM && share <= 0.0)
            cliffSlope = lerp(roundSlope, ridgedSlope, sharp);
        fine.x += lerp(round - roundPrev, ridged - ridgedPrev, sharp) * (1.0 - min(saturate(2.0 - 2.0 * (float)f / floodplainFrequency) / w, 1.0));
        f *= RELIEF_LACUNARITY;
        amplitude *= 0.5;
    }
    slope = lerp(roundSlope, ridgedSlope, sharp);
    return lerp(round, ridged, sharp);
}

// Auxiliary detail calls keep the same full-resolution slope without requesting the coastal slope.
float ReliefDetail(RlPoint oriented, RlPoint plain, int orientedOctaves, float topKm, int octaves, float relief, float sharp,
                   float crease, uint seed, float4 fold, float foldShare, float foldWeight, ReliefGullies gullies,
                   out float3 slope, out float coarse)
{
    float3 unused;
    float wide;
    float4 ravine;
    float2 fine;
    return ReliefDetail(oriented, plain, orientedOctaves, topKm, octaves, relief, sharp, crease, seed, fold, foldShare,
                        foldWeight, 0, wide, gullies, slope, coarse, unused, ravine, fine);
}

// One octave of noise of wavelength `km` at p, in deviations, and its gradient per radian; 0 where the mesh cannot carry it.
float4 ReliefNoiseD(RlPoint p, float km, uint seed)
{
    const double f = ReliefFrequency(km);
    const float w = RlWeight((float)f);
    [branch] if (w <= 0.0)
        return 0.0;
    const RlCell l = RlSplit(p, f);
    return w * RlGradientNoiseD(l.cell, l.q, seed) * float4(1.0, (float3)f.xxx) / RL_SIGMA;
}

// A phase in doubles brought into its turn, for a float's sine: a phase of hundreds of km lost its centimetres in a float.
float ReliefTurn(double phase)
{
    const double turns = phase * 0.15915494309189535;
    return (float)((turns - (double)floor((float)turns)) * 6.283185307179586);
}

// The chains' folds (RELIEF_FOLD): crests along the level lines of the distance to the boundary, `along` (km), and its
// gradient per radian; a short set and a long one, mixed by a noise, shifted across by another; sines as the ridged
// octave reads a noise, of the same mean |n|, their mix kept at the same deviation. x the value, yzw its gradient per
// radian; weight: its filtering by the mesh times its amplitude, 1 in the mean.
float4 ReliefFold(RlPoint p, double along, float3 alongGradient, out float weight)
{
    const float pi = 3.14159265;
    // Their shift across, km, the same for both sets.
    const float4 shift = (ReliefNoiseD(p, RELIEF_FOLD.z, ReliefSeed(8)) + 0.5 * ReliefNoiseD(p, RELIEF_FOLD.z / 3.0, ReliefSeed(8) + 2u))
                       * (RELIEF_FOLD.y * RELIEF_FOLD.x / 1.118);
    // The set, 0 the short folds to 1 the long ones, pure over most of the chains.
    const float4 z = ReliefNoiseD(p, RELIEF_FOLD_SETS.y, ReliefSeed(8) + 3u);
    const float u = saturate(0.5 + 0.6 * z.x), set = u * u * (3.0 - 2.0 * u);
    const float3 setGradient = (u > 0.0 && u < 1.0 ? 3.6 * u * (1.0 - u) : 0.0) * z.yzw;
    const float k1 = pi / RELIEF_FOLD.x, k2 = k1 / RELIEF_FOLD_SETS.x;
    const double x = along + (double)shift.x;
    const float3 dx = alongGradient + shift.yzw;
    const float t1 = ReliefTurn((double)k1 * x), t2 = ReliefTurn((double)k2 * x);
    const float s1 = sin(t1), c1 = cos(t1), s2 = sin(t2), c2 = cos(t2);
    const float n = (1.0 - set) * s1 + set * s2, m = sqrt((1.0 - set) * (1.0 - set) + set * set);
    const float3 dn = ((1.0 - set) * c1 * k1 + set * c2 * k2) * dx + (s2 - s1) * setGradient;
    const float3 dm = (2.0 * set - 1.0) / m * setGradient;
    // Their amplitude: 1 + s tanh(1.5 z), z the segments' noise in deviations: near 0 or near twice the mean, by segments.
    const float zs = ReliefNoiseD(p, RELIEF_FOLD_SADDLES.y, ReliefSeed(8) + 1u).x;
    weight = lerp(RlWeight((float)ReliefFrequency(RELIEF_FOLD.x)), RlWeight((float)ReliefFrequency(RELIEF_FOLD.x * RELIEF_FOLD_SETS.x)), set)
           * (1.0 + RELIEF_FOLD_SADDLES.x * tanh(1.5 * zs));
    const float a = 0.5 * (1.0 + RL_MEAN_BILLOW_BEST) * 0.5 * pi; // E|a sin| = E|n|
    return float4(a * n / m, a * (dn / m - n * dm / (m * m)));
}

// The coasts' noise at p, unit deviation: RELIEF_COAST_NOISE.y octaves from RELIEF_COAST_NOISE.x km, lacunarity 2.2,
// each `gain` of the one above, the finer ones `rias` in drowned valleys, |n| less its mean, narrow troughs along the
// noise's zeros; an octave the mesh cannot carry filtered out, its mean 0. wide: its RELIEF_BARRIER_FORM.w widest octaves
// alone, their rias rounded over half a deviation, the barriers' smooth shore.
float ReliefCoastNoise(RlPoint p, float gain, float rias, uint seed, out float wide)
{
    const float meanAbs = 0.5 * (1.0 + RL_MEAN_BILLOW_BEST), deviationAbs = sqrt(RL_SIGMA * RL_SIGMA - meanAbs * meanAbs);
    double f = ReliefFrequency(RELIEF_COAST_NOISE.x);
    float sum = 0.0, amplitude = 1.0;
    wide = 0.0;
    [loop] for (int o = 0; o < (int)RELIEF_COAST_NOISE.y; ++o)
    {
        const float w = RlWeight((float)f);
        [branch] if (w <= 0.0)
            break;
        const RlCell l = RlSplit(p, f);
        const float n = RlGradientNoise(l.cell, l.q + RlShift(o), seed + (uint)o, true);
        float dc;
        const float valley = (ReliefCrease(n, CREASE_ROUNDING * (float)f / gCreaseMaxFrequency, dc) - meanAbs) * (RL_SIGMA / deviationAbs);
        sum += amplitude * w * lerp(n, valley, o > 0 ? rias : 0.0);
        [branch] if (o < (int)RELIEF_BARRIER_FORM.w)
        {
            const float rounded = (ReliefCrease(n, 0.5 * RL_SIGMA, dc) - meanAbs) * (RL_SIGMA / deviationAbs);
            wide += amplitude * w * lerp(n, rounded, o > 0 ? rias : 0.0);
        }
        f *= 2.2;
        amplitude *= gain;
    }
    // The octaves' deviations summed, filtered or not: a filtered octave lowers the deviation, as it should.
    const float deviations = rsqrt((1.0 - pow(gain * gain, RELIEF_COAST_NOISE.y)) / (1.0 - gain * gain));
    wide = wide / RL_SIGMA * deviations;
    return sum / RL_SIGMA * deviations;
}

// The coast's gradient at the physical erosion scale, per radian. A ria's |noise| cusp can span metres even in a
// kilometre-wide octave. Both its spectrum and its crease derivative must be filtered before setting a cliff's height.
// The full coast noise still places the shore; this derivative only measures the reach of wave erosion.
float3 ReliefCoastGradient(RlPoint p, float gain, float rias, uint seed)
{
    const float meanAbs = 0.5 * (1.0 + RL_MEAN_BILLOW_BEST), deviationAbs = sqrt(RL_SIGMA * RL_SIGMA - meanAbs * meanAbs);
    const float physicalFrequency = PLANET_RADIUS_KM / EROSION_CLIFF_SLOPE_KM;
    const float maxFrequency = min(gMaxFrequency, physicalFrequency);
    const float creaseFrequency = min(gCreaseMaxFrequency, physicalFrequency);
    double f = ReliefFrequency(RELIEF_COAST_NOISE.x);
    float3 sum = 0.0;
    float amplitude = 1.0;
    [loop] for (int o = 0; o < (int)RELIEF_COAST_NOISE.y; ++o)
    {
        const float w = saturate(2.0 - 2.0 * (float)f / maxFrequency);
        if (w <= 0.0) break;
        const RlCell l = RlSplit(p, f);
        const float4 n = RlGradientNoiseD(l.cell, l.q + RlShift(o), seed + (uint)o);
        float dc;
        ReliefCrease(n.x, CREASE_ROUNDING * (float)f / creaseFrequency, dc);
        sum += amplitude * w * (float)f * n.yzw * lerp(1.0, dc * RL_SIGMA / deviationAbs, o > 0 ? rias : 0.0);
        f *= 2.2;
        amplitude *= gain;
    }
    return sum / RL_SIGMA * rsqrt((1.0 - pow(gain * gain, RELIEF_COAST_NOISE.y)) / (1.0 - gain * gain));
}

// Flat-lying strata: the elevation in steps of `step` (m), each riser a share of the step, never narrower than two mesh
// cells across a ground of this slope; the steps' mean is the elevation's.
float ReliefTerraces(float h, float step, float slope, float cellKm)
{
    const float x = h / step, k = floor(x);
    // Each step its own riser, hard beds in cliffs, soft ones in slopes: RELIEF_RISER.x to .y of the step, drawn by step.
    const float drawn = (float)(RlMix1(asuint((int)k) + (uint)PLANET_SEED * 0x9E3779B1u) >> 8) / 16777216.0;
    const float mesh = 2000.0 * cellKm * slope / step, riser = saturate(max(lerp(RELIEF_RISER.x, RELIEF_RISER.y, drawn), mesh));
    const float shift = saturate(max(0.5 * (RELIEF_RISER.x + RELIEF_RISER.y), mesh)); // the steps' mean riser
    return (k + smoothstep(1.0 - riser, 1.0, x - k) + 0.5 * (1.0 - shift)) * step;
}

// Ground before wave erosion and barriers, with the point's own coastal inputs and roughness. The same evaluator
// supplies an uneroded marine witness; it never invokes wave erosion itself.
struct ReliefGround
{
    float height, coastHeight, shoreKm, coastSlope, rocky, near, offsetKm, erodibility, cellKm, relief, shoreMetric, roughness;
    float3 formsGradient, cliffSlope;
    float smoothKm, volcanicShare;
    float channelBed, channelSurface, channelDistance, lakeLevel;
    float channelEdge, channelCut, channelCoverage, channelBank; // step B: support, mean depth, wet fraction and dry-bank proximity
    float3 waterFlow;
    VolcanicFinish volcanic;
    float riverParent, riverFine; // inputs retained when the river evaluation runs in a separate GPU pass
};

ReliefGround ReliefSampleGround(double3 position, bool valleys, bool courses, bool deferRivers)
{
    const RlPoint p = RlMakePoint(position);
    const float cellKm = ReliefCellKm();

    // 1. The large forms: the map at the warped point.
    const RlPoint warped = RlTurbulence(p, ReliefFrequency(RELIEF_WARP_TOP), RELIEF_WARP / (RL_SIGMA * PLANET_RADIUS_KM),
                                        RELIEF_WARP_OCTAVES, ReliefSeed(0));
    const TectonicSample map = TectonicFields(warped.p);
    float h = map.forms.x;
    // The boundary's distance: near its line, the signed one, exact across it; farther, the plain one.
    const float axisKm = lerp(abs(map.side.x), map.sharp.x, smoothstep(25.0, 60.0, map.sharp.x));
    const float rift = smoothstep(-2500.0, -1000.0, h);
    // Along a boundary, its profiles deepen and fade by segments, a noise of RELIEF_SEGMENTS.x km, its mean 1.
    float segment = 0.0;
    float profileRate = 0.0; // step A's steering: the profiles' slope, m per km of the boundary's distance, segments fixed
    [branch] if (map.sharp.y > 1.0 || abs(map.sharp.z) > 1.0)
    {
        const double f = ReliefFrequency(RELIEF_SEGMENTS.x);
        const float wf = RlWeight((float)f);
        [branch] if (wf > 0.0)
        {
            const RlCell l = RlSplit(p, f);
            segment = wf * RlGradientNoise(l.cell, l.q, ReliefSeed(6), true);
        }
    }
    [branch] if (map.sharp.y > 1.0) // a trench, 8 to 10 km deep at its axis, its inner and outer walls (Stern 2002)
    {
        float depth = map.sharp.y * (1.0 + RELIEF_SEGMENTS.y * segment);
        const float w = ReliefWidth(RELIEF_TRENCH.x, cellKm, depth), floorKm = RELIEF_TRENCH.y;
        h -= depth * exp((floorKm - sqrt(axisKm * axisKm + floorKm * floorKm)) / w);
        const float root = sqrt(axisKm * axisKm + floorKm * floorKm);
        profileRate += depth * exp((floorKm - root) / w) * axisKm / (root * w);
    }
    [branch] if (abs(map.sharp.z) > 1.0) // a ridge's axial valley or dome; a rift's graben, its walls steep
    {
        float valley = map.sharp.z * (1.0 + RELIEF_SEGMENTS.z * segment), graben = map.sharp.z * (1.0 + RELIEF_SEGMENTS.y * segment);
        const float w = ReliefWidth(RELIEF_RIDGE_AXIS, cellKm, valley);
        const float wall = ReliefWidth(RELIEF_GRABEN.y, cellKm, graben);
        h += lerp(valley * exp(-axisKm * axisKm / (w * w)),
                  graben * (1.0 - smoothstep(RELIEF_GRABEN.x - wall, RELIEF_GRABEN.x + wall, axisKm)), rift);
        const float u = saturate((axisKm - RELIEF_GRABEN.x + wall) / (2.0 * wall));
        profileRate += lerp(-2.0 * axisKm / (w * w) * valley * exp(-axisKm * axisKm / (w * w)), -graben * 3.0 * u * (1.0 - u) / wall, rift);
    }
    [branch] if (map.sharp.w > 1.0) // a transform's trough
    {
        float depth = map.sharp.w;
        const float w = ReliefWidth(lerp(RELIEF_TRANSFORM.x, RELIEF_TRANSFORM.y, rift), cellKm, depth);
        h -= depth * exp(-axisKm * axisKm / (w * w));
        profileRate += depth * exp(-axisKm * axisKm / (w * w)) * 2.0 * axisKm / (w * w);
    }

    // The coasts: near the shore, the level moved by a noise so that the coastline moves by RELIEF_COAST.x km at one
    // deviation on a steep coast, an active margin's or a rocky one's, by RELIEF_COAST.y on a flat one, sedimentary:
    // capes, bays, islands, rias. The shore's distance along the large forms' slope; the coast's kind by that slope.
    const float coastSlope = max(length(map.formsGradient) / PLANET_RADIUS_KM, RELIEF_COAST_SLOPE.x); // m/km
    const float rocky = smoothstep(RELIEF_COAST_SLOPE.y, RELIEF_COAST_SLOPE.z, coastSlope);
    float shoreKm = h / coastSlope; // + inland
    float smoothKm = shoreKm; // the barriers' smooth shore: without the coast's and the detail's finer octaves
    const float originalShoreKm = shoreKm;
    float shoreMetric = 1.0;
    const float near = exp(-shoreKm * shoreKm / (RELIEF_COAST.z * RELIEF_COAST.z) - h * h / (RELIEF_COAST.w * RELIEF_COAST.w));
    [branch] if (near > 1e-3)
    {
        const float gain = lerp(RELIEF_COAST_NOISE.z, RELIEF_COAST_NOISE.w, rocky), rias = lerp(RELIEF_RIAS.y, RELIEF_RIAS.x, rocky);
        const float moved = near * coastSlope * lerp(RELIEF_COAST.y, RELIEF_COAST.x, rocky);
        float wide;
        h += moved * ReliefCoastNoise(p, gain, rias, ReliefSeed(7), wide);
        smoothKm += moved * wide / coastSlope;
        shoreKm = h / coastSlope;
        [branch] if (valleys && EROSION_CLIFF_RETREAT.x != 0.0 && rocky > 0.3
                     && abs(shoreKm) < EROSION_CLIFF_REACH.z)
        {
            const float3 d = (float3)position;
            const float3 baseGradient = map.formsGradient - dot(map.formsGradient, d) * d;
            const float3 nearGradient = -2.0 * near * (originalShoreKm / (RELIEF_COAST.z * RELIEF_COAST.z * coastSlope)
                                                       + originalShoreKm * coastSlope / (RELIEF_COAST.w * RELIEF_COAST.w)) * baseGradient;
            const float3 noiseGradient = ReliefCoastGradient(p, gain, rias, ReliefSeed(7));
            const float noise = (shoreKm - originalShoreKm) / (near * lerp(RELIEF_COAST.y, RELIEF_COAST.x, rocky));
            const float3 coastGradient = baseGradient + coastSlope * lerp(RELIEF_COAST.y, RELIEF_COAST.x, rocky)
                                        * (near * noiseGradient + noise * nearGradient);
            shoreMetric = max(length(coastGradient - dot(coastGradient, d) * d) / (PLANET_RADIUS_KM * coastSlope), 0.25);
        }
    }

    // The volcanoes' edifices, on the large forms; their young flanks quiet the detail.
    float volcanicQuiet;
    VolcanicFinish volcanic;
    h += VolcanoEdifices(position, cellKm, volcanicQuiet, volcanic);

    // 2. The detail.
    const float relief = map.forms.y * (1.0 - volcanicQuiet), youth = saturate(map.forms.z), strata = map.forms.w;
    const float mountains = smoothstep(300.0, 1200.0, relief);
    // The level 0's valleys (Erosion.hlsli), their walls steeper on the chains: on their floor the detail fades, nothing
    // finer than the level 0 bars its rivers. Step A (EROSION_RAVINES) carves none; step B (EROSION_RIVERS) has its own.
    const bool network = valleys && !ErosionRavines();
    ErosionValley valley = (ErosionValley)0;
    valley.surface = 1e9, valley.deposit = -1e9;
    valley.channelBed = valley.channelSurface = 1e9;
    valley.channelDistance = 1e9;
    RlPoint wander = p;
    [branch] if (network && h > -500.0) // deeper, no valley nor deposit reaches
    {
        // Read at a point warped by a few km, so that the links' straight runs wander.
        wander = RlTurbulence(p, ReliefFrequency(EROSION_WARP.x), EROSION_WARP.y / (RL_SIGMA * PLANET_RADIUS_KM), 2,
                                            ReliefSeed(9));
        valley = ErosionValleys(wander.p, cellKm, lerp(EROSION_WALLS.x, EROSION_WALLS.y, mountains));
    }
    const float large = h;
    // The gullies (ReliefDetail): down the large forms, or down a valley's walls where it lies under them; on the land;
    // near and above the glacial maximum's equilibrium line, never from the ice covering a trough.
    // Step A's ravines instead, down the same slopes, by the rock, the climate and the relief.
    ReliefGullies gullies = (ReliefGullies)0;
    [branch] if (network)
    {
        gullies.ground = h;
        gullies.surface = valley.surface;
        gullies.valleySlope = valley.gradient;
        gullies.incision = valley.incision;
        gullies.slope = map.formsGradient / (1000.0 * PLANET_RADIUS_KM);
        gullies.share = EROSION_GULLY_SHARE * smoothstep(-20.0, 60.0, h);
        gullies.glacial = smoothstep(-0.5, 0.5, (h - ErosionEquilibriumLine((float3)position)) / EROSION_GLACIAL_BAND);
    }
    else if (valleys)
    {
        // The map's slopes on the sphere, the profiles' along the boundary's distance; the map's warp held fixed.
        const float3 d = normalize((float3)warped.p);
        gullies.ground = h;
        gullies.surface = 1e9;
        gullies.slope = (ReliefMapSlope(map.formsGradient, d) + profileRate * sign(map.side.x) * ReliefMapSlope(map.sideGradient, d))
                      / (1000.0 * PLANET_RADIUS_KM);
        gullies.ravines = sqrt(clamp(map.erodibility, RAVINE_ROCK.x, RAVINE_ROCK.y)) * lerp(RAVINE_PLAINS, 1.0, mountains)
                        * lerp(RAVINE_WET.x, RAVINE_WET.y, ClimateHumidity(1000.0 * ErosionClimate((float3)position).x));
        // No ravine wider than this footprint's band limit (RlWeight, RAVINE_TOP): none is drawn, nor its steering read.
        [flatten] if (RAVINE_TOP * min(gMaxFrequency, 1e30) <= 1000.0 * PLANET_RADIUS_KM)
            gullies.ravines = 0.0;
    }
    // The widest octaves, the chains' own forms, read a point warped by a few km, so that no crest closes on itself, and
    // stretched along the chains: raised off the sphere by a measure of the smoothed distance to the plate's boundary,
    // whose level lines follow them, levelling off past RELIEF_ORIENTATION.y km. The finer octaves read the point itself.
    const RlPoint plain = RlMakePoint(position);
    const RlPoint bent = RlTurbulence(plain, ReliefFrequency(RELIEF_DETAIL_WARP.x), RELIEF_DETAIL_WARP.y / (RL_SIGMA * PLANET_RADIUS_KM),
                                      3, ReliefSeed(4));
    const float reach = RELIEF_ORIENTATION.y;
    // The lift in doubles from `along` (TectonicSample): a quintic rather than a tanh, which has no double, of the same
    // slope at the boundary and the same height, reached at 15/8 of `reach`, smooth to its second derivative.
    const double t = min(max(map.along * (double)(8.0 / (15.0 * reach)), (double)-1.0), (double)1.0), t2 = t * t;
    const double lift = (double)(RELIEF_ORIENTATION.x * reach / PLANET_RADIUS_KM) * t * (1.875 + t2 * (-1.25 + 0.375 * t2));
    const RlPoint oriented = RlMakePoint(bent.p * (1.0 + lift));
    // Step A's steering: the oriented point's Jacobian, the warp's and the lift's, the map's warp held fixed.
    [branch] if (gullies.ravines > 0.0)
    {
        const float3 liftGradient = RELIEF_ORIENTATION.x / PLANET_RADIUS_KM * (1.0 - (float)t2) * (1.0 - (float)t2)
                                  * ReliefMapSlope(map.orientationGradient, normalize((float3)warped.p));
        const float3 b = (float3)bent.p;
        gullies.oriented = (1.0 + (float)lift) * RlTurbulenceJacobian(plain, ReliefFrequency(RELIEF_DETAIL_WARP.x),
                                                                      RELIEF_DETAIL_WARP.y / (RL_SIGMA * PLANET_RADIUS_KM), 3, ReliefSeed(4))
                         + float3x3(b.x * liftGradient, b.y * liftGradient, b.z * liftGradient);
    }
    const float crease = lerp(RELIEF_OLD_CREASE, 0.0, youth);
    // The chains' widest crests in folds, where the boundary orients them. This parent is identical with or without
    // erosion: a network incision may cut it afterwards, never suppress its folds before deciding whether it is cut.
    float4 fold = 0.0;
    float foldWeight = 0.0;
    const float foldShare = RELIEF_FOLD.w * (1.0 - smoothstep(RELIEF_FOLD_REACH.x, RELIEF_FOLD_REACH.y, map.side.y)) * mountains
                          * smoothstep(RELIEF_FOLD_REACH.z, RELIEF_FOLD_REACH.w, length(map.orientationGradient) / PLANET_RADIUS_KM);
    [branch] if (foldShare > 0.0)
        fold = ReliefFold(plain, map.along, map.orientationGradient, foldWeight);
    // Near a flat coast, quiet plains and soft sediments, where the barriers and the lagoons show.
    const float coastQuiet = lerp(1.0, RELIEF_COAST_QUIET.x, (1.0 - rocky) * exp(-shoreKm * shoreKm / (RELIEF_COAST_QUIET.y * RELIEF_COAST_QUIET.y)));
    const float quiet = coastQuiet;
    float3 slope, cliffSlope;
    float coarse, wide;
    float4 ravine;
    float2 fine;
    // On a valley's walls, the detail at least a share of the depth carved there: spurs and side gullies on the scale of
    // the wall; nothing more on a plain.
    const float detail = relief * quiet;
    h += detail * ReliefDetail(oriented, plain, RELIEF_ORIENTED_OCTAVES, RELIEF_DETAIL_TOP, RELIEF_OCTAVES, detail,
                               mountains, crease, ReliefSeed(1), fold, foldShare, foldWeight, (int)RELIEF_BARRIER_FORM.w, wide, gullies, slope, coarse, cliffSlope,
                               ravine, fine);
    coarse = large + detail * coarse;
    smoothKm += detail * wide / coastSlope;
    const float s = length(slope), land = smoothstep(-20.0, 60.0, h);

    // Mesas on the platforms' strata: their own hills of a few km, then the relief in steps, flat tables between cliffs.
    // The valley floor removes the complete detail once, in ErosionCarve, including mesas and badlands.
    const float mesas = saturate(2.0 * strata) * land, badlands = saturate(-2.0 * strata) * land * quiet;
    [branch] if (mesas > 0.0)
    {
        float3 tableSlope;
        float unused;
        h += mesas * RELIEF_MESAS.x * ReliefDetail(plain, plain, 0, RELIEF_MESAS.y, (int)RELIEF_MESAS.z, RELIEF_MESAS.x, 0.0, 0.0,
                                                   ReliefSeed(5), 0.0, 0.0, 0.0, (ReliefGullies)0, tableSlope, unused);
        h = lerp(h, ReliefTerraces(h, RELIEF_MESA_STEP, length(slope + mesas * tableSlope), cellKm), mesas);
    }
    [branch] if (badlands > 0.0)
    {
        float3 gullySlope;
        float unused;
        h += badlands * RELIEF_BADLANDS.x * ReliefDetail(plain, plain, 0, RELIEF_BADLANDS.y, (int)RELIEF_BADLANDS.z,
                                                         RELIEF_BADLANDS.x, 1.0, 0.0, ReliefSeed(2), 0.0, 0.0, 0.0, (ReliefGullies)0,
                                                         gullySlope, unused);
    }
    // The ravines, on the whole pre-erosion ground.
    [branch] if (valleys && ErosionRavines())
    {
        h += ravine.x;
        slope += ravine.yzw;
    }
    // Coastal and river erosion share this substrate. Applying the coastal remap to an already lowered
    // river floor manufactured rectangular marine pools and disconnected the water from its drainage stage.
    const float coastHeight = h;
    // Step B's corridors on that ground (ErosionRivers): floodplains, walls; their channels after the finish (ReliefElevation).
    ErosionRiver river;
    river.fill = 0.0, river.carve = 0.0, river.bed = 1e9, river.stage = -1e9, river.cut = 0.0, river.weight = 0.0, river.edge = -1e9;
    river.distance = 1e9, river.flow = 0.0, river.lakeLevel = 0.0, river.coverage = 0.0, river.bank = 0.0;
    [branch] if (!deferRivers && valleys && courses && ErosionRivers() && h > -500.0)
    {
        river = ErosionRivers(position, max(cellKm, gRiverCellKm), h, large, detail * fine.x + fine.y);
        h += river.fill - river.carve;
    }

    // 3. The valleys carved into the coarse ground, the finer detail riding on their walls.
    [branch] if (valley.surface < 1e8)
        h = ErosionCarve(h, coarse, valley, EROSION_SMOOTH);
    // The deposits fill what lies under them: deltas, fans.
    h = max(h, valley.deposit);

    ReliefGround ground;
    ground.smoothKm = smoothKm, ground.volcanic = volcanic, ground.volcanicShare = gVolcanic;
    ground.riverParent = large, ground.riverFine = detail * fine.x + fine.y;
    ground.height = h, ground.shoreKm = shoreKm, ground.coastSlope = coastSlope, ground.rocky = rocky, ground.near = near;
    ground.coastHeight = valleys && courses && ErosionRivers() ? coastHeight : h;
    ground.offsetKm = shoreKm - originalShoreKm, ground.erodibility = map.erodibility, ground.cellKm = cellKm;
    ground.relief = relief, ground.shoreMetric = shoreMetric, ground.formsGradient = map.formsGradient, ground.cliffSlope = cliffSlope;
    ground.lakeLevel = valley.lakeLevel;
    ground.channelBed = valley.channelBed, ground.channelSurface = valley.channelSurface;
    ground.channelDistance = valley.channelDistance;
    ground.waterFlow = valley.flow;
    ground.channelEdge = -1e9, ground.channelCut = 0.0, ground.channelCoverage = 0.0, ground.channelBank = 0.0;
    [flatten] if (valleys && courses && ErosionRivers())
    {
        ground.lakeLevel = river.lakeLevel;
        ground.channelBed = river.bed, ground.channelSurface = river.stage;
        ground.channelDistance = river.distance, ground.channelEdge = river.edge, ground.channelCut = river.cut;
        ground.channelCoverage = river.coverage;
        ground.channelBank = river.bank;
        ground.waterFlow = river.flow;
    }
    // Roughness: plains 0.1, hills 0.35, old chains 0.5, terraces and badlands 0.6, young chains 1.
    float rough = 0.1 + 0.25 * smoothstep(50.0, 400.0, relief) + 0.15 * smoothstep(400.0, 1500.0, relief);
    rough = lerp(rough, 1.0, youth * smoothstep(500.0, 1500.0, relief));
    ground.roughness = lerp(rough, 0.6, max(mesas, badlands));

    return ground;
}

// Ordinary callers keep the composed evaluation. Screen relief can schedule the river independently;
// in river mode the legacy valley/deposit stage is inactive, so this split preserves the composition order.
ReliefGround ReliefSampleGround(double3 position, bool valleys, bool courses)
{
    return ReliefSampleGround(position, valleys, courses, false);
}

// Barriers and summit limiting are identical for the primary ground and the marine witness.
float ReliefFinish(double3 position, float h, float near, float rocky, float smoothKm, float cellKm, VolcanicFinish volcanic)
{
    const RlPoint p = RlMakePoint(position);
    // The flat coasts' barriers, along the smooth shore, not the shore's contour, which the finer octaves fold into angles
    // and rias: arcs offshore between inlets, recurved toward them, a smooth beach, low dunes and washover fans behind.
    // Raised from the relief beneath them, their crests whole: from the smooth level, fine coast noise cut them to the sea.
    // Faded over the first half metre of dry land.
    [branch] if (near > 1e-3 && rocky < 1.0 && h < 0.5 && abs(smoothKm + RELIEF_BARRIER.x) < 10.0 * max(RELIEF_BARRIER.y, 2.0 * cellKm))
    {
        const double fp = ReliefFrequency(RELIEF_BARRIER_GAPS.x), fi = ReliefFrequency(RELIEF_BARRIER_GAPS.y);
        const double fd = ReliefFrequency(RELIEF_BARRIER_FORM.z);
        const RlCell lp = RlSplit(p, fp), li = RlSplit(p, fi), ld = RlSplit(p, fd);
        const float patch = RlWeight((float)fp) * RlGradientNoise(lp.cell, lp.q, ReliefSeed(7) + 16u, true) / RL_SIGMA;
        const float a = abs(RlWeight((float)fi) * RlGradientNoise(li.cell, li.q, ReliefSeed(7) + 17u, true) / RL_SIGMA);
        const float dunes = clamp(RlWeight((float)fd) * RlGradientNoise(ld.cell, ld.q, ReliefSeed(7) + 18u, true) / RL_SIGMA, -1.0, 1.0);
        // the islands: the inlets at the noise's zeros, the barrier farthest out halfway between them, an arch
        const float t = saturate(a / 0.8), arch = t * (2.0 - t);
        // its share of the flat coasts: the patch noise over the normal quantile of 1 - RELIEF_BARRIER.w, near 0.5
        const float over = 2.5 * (0.5 - RELIEF_BARRIER.w);
        const float presence = (1.0 - rocky) * smoothstep(over - 0.1, over + 0.1, patch)
                             * smoothstep(RELIEF_BARRIER_FORM.y, 2.0 * RELIEF_BARRIER_FORM.y, a) * (1.0 - smoothstep(0.0, 0.5, h));
        // A narrow rise, narrower and lower toward the inlets; filter both its support and its emerged width.
        float lift = max(RELIEF_BARRIER.z * (0.75 + 0.25 * arch) * (1.0 + 0.4 * dunes) - h, 0.0);
        const float w = ReliefWidth(RELIEF_BARRIER.y * (0.6 + 0.4 * arch), cellKm, lift);
        const float x = smoothKm + RELIEF_BARRIER.x * (1.0 - RELIEF_BARRIER_FORM.x * (1.0 - arch));
        // behind, where the dunes are low, washover fans: lobes of a third of the crest, three times as wide
        h += ReliefSeaProfile(x, w, cellKm, h, presence * lift, saturate(-dunes) / 3.0);
    }

    // The old islands' planed tops, the reefs and their lagoons, on the detail.
    h = VolcanoFinish(h, volcanic);

    // The highest summits level off under MAX_TERRAIN_HEIGHT.
    [branch] if (h > RELIEF_HIGHEST.x)
        h = RELIEF_HIGHEST.x + RELIEF_HIGHEST.y * tanh((h - RELIEF_HIGHEST.x) / RELIEF_HIGHEST.y);
    return h;
}

// Elevation in the planet's fixed frame, with the primary point's roughness. Without valleys this is the unchanged
// pre-erosion form read by the level 0. Only a potential cut reads a second terrain point. Its witness has no valleys,
// deposits or wave erosion, so its query cannot recurse or add another read of the erosion network.
float ReliefFinishGround(double3 position, ReliefGround ground, bool valleys, bool courses)
{
    float h = ground.height;
    [branch] if (valleys)
    {
        const float candidate = ErosionCoast(RlMakePoint(position), ground.coastHeight, ground.shoreKm, ground.coastSlope, ground.rocky,
                                            ground.near, ground.offsetKm, ground.formsGradient, ground.erodibility,
                                            ground.cellKm, ground.cliffSlope, ground.relief, ground.shoreMetric);
        [branch] if (candidate < ground.coastHeight)
        {
            const double3 witness = ErosionSeaPoint(position, ground.formsGradient);
            const ReliefGround sea = ReliefSampleGround(witness, false, false);
            const float level = ReliefFinish(witness, sea.height, sea.near, sea.rocky, sea.smoothKm, sea.cellKm, sea.volcanic);
            h = min(h, lerp(ground.coastHeight, candidate, ErosionSeaAccess(level, sea.coastSlope)));
        }
    }
    gRoughness = ground.roughness;
    gVolcanic = ground.volcanicShare;
    h = ReliefFinish(position, h, ground.near, ground.rocky, ground.smoothKm, ground.cellKm, ground.volcanic);
    gRiverBank = ground.channelBank;
    // Step B: the channels cut into the finished ground, the water at their stage where they are wet (the prototype's).
    // A wet channel is cut into the ground it crosses, its stage never above it: where a lower corridor's carve or a fill
    // fading with its river left the ground under its stage, the prototype's water stood perched, in a wall at its edge.
    // The terminal lakes as the network's. The clearance is how far inside a wet channel, continuous across its edge.
    [branch] if (valleys && courses && ErosionRivers())
    {
        float stage = min(ground.channelSurface, h);
        // A neighbour can already have lowered the supporting ground below this course's bank. Its compact cut
        // must still enter that composed ground. Only the mean depth is removed here, never the gap to the stage.
        h = min(h - ground.channelCut, ground.channelBed);
        // A neighbour's dry bank can win the bed's lower envelope below this channel's stage. Water still fills only
        // its compact cut, which vanishes at the wet edge; otherwise that edge introduces a finite wall of water.
        stage = min(stage, h + ground.channelCut);
        gWaterLevel = max(0.0, max(stage, ground.lakeLevel));
        // A subpixel channel can lie below the mean ground. Do not lower that entire footprint to its stage.
        // Keep its water area and depth moment independently, through every mesh/fine/screen reconstruction.
        gRiverCoverage = stage > 0.0 ? ground.channelCoverage : 0.0;
        gLakeClearance = ground.lakeLevel > 0.0 ? ground.lakeLevel - h : -1e9;
        gWaterCoverage = max(gRiverCoverage, gLakeClearance > 0.0 ? 1.0 : 0.0);
        // A resolved pixel shades the actual water column. An unresolved cut retains its independent depth moment;
        // neither case adds a coverage-dependent excavation to the physical terrain.
        const float column = max(stage - h, 0.0);
        const float riverDepth = lerp(ground.channelCut, column, ground.channelCoverage);
        gWaterDepth = max(stage > 0.0 ? riverDepth : 0.0, max(gLakeClearance, 0.0));
        // The channel current loses momentum continuously in the receiving lake's water column.
        // A binary river/lake choice produced a reflection seam along the submerged channel edge.
        gWaterFlow = gWaterLevel > 0.0 ? ground.waterFlow * saturate(ground.channelCut / max(gWaterDepth, 1e-3)) : 0.0;
        const float river = ground.channelEdge > 0.0 ? (stage > 0.0 ? min(stage - h, ground.channelEdge) : -1e9) : ground.channelEdge;
        gWaterClearance = max(river, ground.lakeLevel > 0.0 ? ground.lakeLevel - h : -1e9);
        gWaterDistance = min(ground.channelDistance, ground.lakeLevel > 0.0 ? abs(ground.lakeLevel - h) : 1e9);
        return h;
    }
    // Intersect two continuous envelopes with the finished terrain: the channel with its cut, and the same section
    // without it. Their difference is the water depth. A nearest-link stage would jump at drainage divides and
    // flood unrelated hollows. Existing hollows below both envelopes stay dry unless their terminal lake fills them.
    const float riverSurface = min(h, ground.channelSurface);
    // The filtered compact cut extends by its sampling radius. Keep its wet support, while giving the exactly
    // zero-depth dry plane a strictly dry sign outside that support (no 50% water on the floodplain).
    const float riverClearance = min(ground.channelSurface - ground.channelBed - abs(h - ground.channelSurface),
                                      max(1000.0 * ground.cellKm, CREASE_MIN_CELL) - ground.channelDistance);
    h -= ErosionChannelCut(h, ground.channelBed, ground.channelSurface);
    const bool lake = ground.lakeLevel > max(h, riverSurface);
    gWaterLevel = max(0.0, max(riverSurface, ground.lakeLevel));
    gWaterDepth = max(gWaterLevel - h, 0.0);
    gWaterCoverage = gWaterLevel > 0.0 && gWaterDepth > 0.0 ? 1.0 : 0.0;
    gRiverCoverage = 0.0;
    gLakeClearance = ground.lakeLevel > 0.0 ? ground.lakeLevel - h : -1e9;
    gWaterFlow = lake || gWaterLevel <= 0.0 ? 0.0 : ground.waterFlow;
    gWaterClearance = max(riverSurface > 0.0 ? riverClearance : -1e9,
                          ground.lakeLevel > 0.0 ? ground.lakeLevel - h : -1e9);
    // Candidate support, not wetness: a river between all four dry grid samples must still be refined.
    gWaterDistance = min(ground.channelDistance, ground.lakeLevel > 0.0 ? abs(ground.lakeLevel - h) : 1e9);
    return h;
}

float ReliefElevation(double3 position, bool valleys, bool courses)
{
    return ReliefFinishGround(position, ReliefSampleGround(position, valleys, courses), valleys, courses);
}

float ReliefElevation(double3 position, bool valleys)
{
    return ReliefElevation(position, valleys, true);
}

float ReliefElevation(double3 position)
{
    return ReliefElevation(position, ErosionMode() > 0u);
}

#endif
