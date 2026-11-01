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
//    finish. With valleys=false, the complete pre-erosion form, including volcanoes, supplies the drainage and sea witness.
// Units: metres and kilometres; a noise frequency of 1 has a wavelength of one radius. The CPU port: tools/hydro/cp.py.
#ifndef RELIEF_HLSLI
#define RELIEF_HLSLI

#include "PlanetSettings.hlsli"
#include "Noise.hlsli"
#include "Tectonics.hlsli"
#include "Volcanoes.hlsli"
#include "Erosion.hlsli"

// The roughness of the last point evaluated, 0 smooth plains to 1 young mountains: the slopes the mesh hides
// (Materials.hlsli).
static float gRoughness = 0.0;

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
// the coarser octaves'; under the glaciers, U troughs and knife-edge crests.
float ReliefDetail(RlPoint oriented, RlPoint plain, int orientedOctaves, float topKm, int octaves, float relief, float sharp,
                   float crease, uint seed, float4 fold, float foldShare, float foldWeight, int wideOctaves, out float wide, ReliefGullies gullies,
                   out float3 slope, out float coarse, out float3 cliffSlope)
{
    coarse = 0.0;
    cliffSlope = 0.0;
    const float3 up = normalize((float3)plain.p);
    float round = 0.0, ridged = 0.0, chain = 1.0, amplitude = 1.0, crest = 0.0, top = 0.0;
    float3 roundSlope = 0.0, ridgedSlope = 0.0, coarseSlope = 0.0;
    wide = 0.0;
    double f = ReliefFrequency(topKm);
    const float metres = relief / (1000.0 * PLANET_RADIUS_KM); // a unit of noise per radius, in m/m at this amplitude
    // Under the glaciers the crests sharpen: |x|^power, its mean kept, E|cos|^power on the stripes.
    const float power = lerp(1.0, EROSION_GLACIAL_POWER, gullies.glacial);
    const float powerMean = lerp(2.0 / 3.14159265, EROSION_GLACIAL_POWER_MEAN, gullies.glacial);
    [loop] for (int o = 0; o < octaves; ++o)
    {
        const float w = RlWeight((float)f);
        [branch] if (w <= 0.0)
            break; // the finer octaves are filtered out too; both shapes' means are 0
        RlCell l;
        [branch] if (o < orientedOctaves)
            l = RlSplit(oriented, f);
        else
            l = RlSplit(plain, f);
        const float4 n = RlGradientNoiseD(l.cell, l.q + RlShift(o), seed + (uint)o);
        float3 g = n.yzw * (float)f * metres;
        g -= up * dot(g, up); // along the ground
        float value = n.x, share = 0.0;
        [branch] if (o >= EROSION_GULLY_FIRST && gullies.share > 0.0 && PLANET_RADIUS_KM / (float)f > EROSION_GULLY.z)
        {
            // The ground's slope under the octave: the coarse octaves' does not count where a valley replaces them.
            const float3 under = gullies.slope + lerp(roundSlope, ridgedSlope, sharp) - gullies.carved * coarseSlope;
            const float steep = length(under);
            // None on the crests of the octave above and of the widest, the chains' and the folds', where the slope that
            // orients them turns over.
            share = gullies.share * smoothstep(EROSION_GULLY.x, EROSION_GULLY.y, steep) * (1.0 - smoothstep(0.85, 1.0, crest * sharp))
                  * (1.0 - smoothstep(0.9, 1.0, top * sharp));
            [branch] if (share > 0.0)
            {
                const float3 across = cross(up, under) / steep;
                // The stripes' lattice: from the octave's own cell, halved, in floats; on the oriented octaves, the
                // plain point's, the stripes drawn in the ground's own measure.
                RlCell kernels;
                [branch] if (o < orientedOctaves)
                    kernels = RlSplit(plain, f / EROSION_GULLY_PERIODS);
                else
                    kernels.cell = l.cell >> 1, kernels.q = ((float3)(l.cell & 1) + l.q) * 0.5;
                const float4 stripe = ErosionGullies(kernels, across, seed + 32u + (uint)o);
                value = lerp(value, stripe.x, share);
                g = lerp(g, stripe.yzw * (float)f * metres, share);
            }
        }
        [branch] if (sharp < 1.0)
        {
            const float a = amplitude * w / (1.0 + RELIEF_EROSION * dot(roundSlope, roundSlope));
            round += a * value;
            roundSlope += a * g;
        }
        [branch] if (sharp > 0.0)
        {
            float x = value, wr = w;
            float3 gr = g;
            [branch] if (o == 0 && foldShare > 0.0)
            {
                float3 gf = fold.yzw * metres;
                gf -= up * dot(gf, up);
                x = lerp(x, fold.x, foldShare), gr = lerp(gr, gf, foldShare), wr = lerp(w, foldWeight, foldShare);
            }
            float dc;
            float c = ReliefCrease(x, max(crease, CREASE_ROUNDING * (float)f / gCreaseMaxFrequency), dc);
            [branch] if (share > 0.0 && gullies.glacial > 0.0)
            {
                const float meanAbs = 0.5 * (1.0 + RL_MEAN_BILLOW_BEST), scale = 0.5 * 3.14159265 * meanAbs; // the stripes' amplitude
                const float u = max(c, 1e-4) / scale, k = (2.0 / 3.14159265) / powerMean;
                const float sharpened = scale * k * pow(u, power);
                dc *= lerp(1.0, k * power * pow(u, power - 1.0), share);
                c = lerp(c, sharpened, share);
            }
            const float r = 1.0 - c; // its mean, 1 - E|n|: the billow's mean says E|n| (Noise.hlsli)
            const float folded = o == 1 || o == 2 ? 1.0 - 0.5 * foldShare * saturate(foldWeight) : 1.0; // the folds' crests over the noise's
            const float a = 1.7 * amplitude * wr * chain * folded / (1.0 + RELIEF_RIDGE_EROSION * dot(ridgedSlope, ridgedSlope));
            ridged += a * (r - 0.5 * (1.0 - RL_MEAN_BILLOW_BEST));
            ridgedSlope += a * -dc * gr;
            chain = saturate(0.3 + 1.2 * r);
            crest = r;
            if (o == 0)
                top = r;
        }
        [flatten] if (o < wideOctaves)
            wide = lerp(round, ridged, sharp);
        if (f < PLANET_RADIUS_KM / EROSION_COARSE)
            coarse = lerp(round, ridged, sharp), coarseSlope = lerp(roundSlope, ridgedSlope, sharp);
        // Capture only scales broader than the maximum platform, in the existing sum with no additional noise read.
        if (f < PLANET_RADIUS_KM / EROSION_CLIFF_SLOPE_KM)
            cliffSlope = lerp(roundSlope, ridgedSlope, sharp);
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
    return ReliefDetail(oriented, plain, orientedOctaves, topKm, octaves, relief, sharp, crease, seed, fold, foldShare,
                        foldWeight, 0, wide, gullies, slope, coarse, unused);
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

// The same coast noise's gradient per radian. Only wave erosion needs it: shoreKm is a distance proxy whose gradient
// changes in a bay. Its magnitude sets the height contour reached by a physical wave-cut width, including inside a ria.
float3 ReliefCoastGradient(RlPoint p, float gain, float rias, uint seed)
{
    const float meanAbs = 0.5 * (1.0 + RL_MEAN_BILLOW_BEST), deviationAbs = sqrt(RL_SIGMA * RL_SIGMA - meanAbs * meanAbs);
    double f = ReliefFrequency(RELIEF_COAST_NOISE.x);
    float3 sum = 0.0;
    float amplitude = 1.0;
    [loop] for (int o = 0; o < (int)RELIEF_COAST_NOISE.y; ++o)
    {
        const float w = RlWeight((float)f);
        if (w <= 0.0) break;
        const RlCell l = RlSplit(p, f);
        const float4 n = RlGradientNoiseD(l.cell, l.q + RlShift(o), seed + (uint)o);
        float dc;
        ReliefCrease(n.x, CREASE_ROUNDING * (float)f / gCreaseMaxFrequency, dc);
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
    float height, shoreKm, coastSlope, rocky, near, offsetKm, erodibility, cellKm, relief, shoreMetric, roughness;
    float3 formsGradient, cliffSlope;
    float smoothKm, volcanicShare;
    VolcanicFinish volcanic;
};

ReliefGround ReliefSampleGround(double3 position, bool valleys)
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
    }
    [branch] if (abs(map.sharp.z) > 1.0) // a ridge's axial valley or dome; a rift's graben, its walls steep
    {
        float valley = map.sharp.z * (1.0 + RELIEF_SEGMENTS.z * segment), graben = map.sharp.z * (1.0 + RELIEF_SEGMENTS.y * segment);
        const float w = ReliefWidth(RELIEF_RIDGE_AXIS, cellKm, valley);
        const float wall = ReliefWidth(RELIEF_GRABEN.y, cellKm, graben);
        h += lerp(valley * exp(-axisKm * axisKm / (w * w)),
                  graben * (1.0 - smoothstep(RELIEF_GRABEN.x - wall, RELIEF_GRABEN.x + wall, axisKm)), rift);
    }
    [branch] if (map.sharp.w > 1.0) // a transform's trough
    {
        float depth = map.sharp.w;
        const float w = ReliefWidth(lerp(RELIEF_TRANSFORM.x, RELIEF_TRANSFORM.y, rift), cellKm, depth);
        h -= depth * exp(-axisKm * axisKm / (w * w));
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
    // finer than the level 0 bars its rivers.
    ErosionValley valley = (ErosionValley)0;
    valley.surface = 1e9, valley.deposit = -1e9;
    [branch] if (valleys && h > -500.0) // deeper, no valley nor deposit reaches
    {
        // Read at a point warped by a few km, so that the links' straight runs wander.
        const RlPoint wander = RlTurbulence(p, ReliefFrequency(EROSION_WARP.x), EROSION_WARP.y / (RL_SIGMA * PLANET_RADIUS_KM), 2,
                                            ReliefSeed(9));
        valley = ErosionValleys(wander.p, cellKm, lerp(EROSION_WALLS.x, EROSION_WALLS.y, mountains));
    }
    const float large = h;
    const float open = 1.0 - valley.floorShare * smoothstep(-20.0, 20.0, h); // a floor ends at the sea: its last link reaches offshore
    // The gullies (ReliefDetail): down the large forms, or down a valley's walls where it lies under them; on the land;
    // under the glaciers within EROSION_GLACIAL_BAND of the glacial maximum's equilibrium line, and in the troughs.
    ReliefGullies gullies = (ReliefGullies)0;
    [branch] if (valleys)
    {
        gullies.carved = smoothstep(-500.0, 800.0, h - valley.surface);
        gullies.slope = lerp(map.formsGradient / (1000.0 * PLANET_RADIUS_KM), valley.gradient, gullies.carved);
        gullies.share = EROSION_GULLY_SHARE * smoothstep(-20.0, 60.0, h) * (1.0 - 4.0 * gullies.carved * (1.0 - gullies.carved)); // none on a valley's rim, a crest
        gullies.glacial = max(valley.glacier, smoothstep(-0.5, 0.5, (h - ErosionEquilibriumLine((float3)position)) / EROSION_GLACIAL_BAND));
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
    const float crease = lerp(RELIEF_OLD_CREASE, 0.0, youth);
    // The chains' widest crests in folds, where the boundary orients them.
    float4 fold = 0.0;
    float foldWeight = 0.0;
    const float foldShare = RELIEF_FOLD.w * (1.0 - smoothstep(RELIEF_FOLD_REACH.x, RELIEF_FOLD_REACH.y, map.side.y)) * mountains
                          * smoothstep(RELIEF_FOLD_REACH.z, RELIEF_FOLD_REACH.w, length(map.orientationGradient) / PLANET_RADIUS_KM)
                          * (1.0 - smoothstep(EROSION_FOLD_DEPTH.x, EROSION_FOLD_DEPTH.y, valley.incision)); // the core is cut by valleys
    [branch] if (foldShare > 0.0)
        fold = ReliefFold(plain, map.along, map.orientationGradient, foldWeight);
    // Near a flat coast, quiet plains and soft sediments, where the barriers and the lagoons show.
    const float quiet = lerp(1.0, RELIEF_COAST_QUIET.x, (1.0 - rocky) * exp(-shoreKm * shoreKm / (RELIEF_COAST_QUIET.y * RELIEF_COAST_QUIET.y)))
                      * open;
    float3 slope, cliffSlope;
    float coarse, wide;
    // On a valley's walls, the detail at least a share of the depth carved there: spurs and side gullies on the scale of
    // the wall; nothing more on a plain.
    const float detail = max(relief, EROSION_WALL_RELIEF * min(valley.incision, max(large - valley.surface, 0.0))) * quiet;
    h += detail * ReliefDetail(oriented, plain, RELIEF_ORIENTED_OCTAVES, RELIEF_DETAIL_TOP, RELIEF_OCTAVES, detail,
                               mountains, crease, ReliefSeed(1), fold, foldShare, foldWeight, (int)RELIEF_BARRIER_FORM.w, wide, gullies, slope, coarse, cliffSlope);
    coarse = large + detail * coarse;
    smoothKm += detail * wide / coastSlope;
    const float s = length(slope), land = smoothstep(-20.0, 60.0, h);

    // Mesas on the platforms' strata: their own hills of a few km, then the relief in steps, flat tables between cliffs.
    const float mesas = saturate(2.0 * strata) * land * open, badlands = saturate(-2.0 * strata) * land * quiet;
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

    // 3. The valleys carved into the coarse ground, the finer detail riding on their walls.
    [branch] if (valley.surface < 1e8)
        h = ErosionCarve(h, coarse, valley, EROSION_SMOOTH);
    // The deposits fill what lies under them: deltas, fans.
    h = max(h, valley.deposit);

    ReliefGround ground;
    ground.smoothKm = smoothKm, ground.volcanic = volcanic, ground.volcanicShare = gVolcanic;
    ground.height = h, ground.shoreKm = shoreKm, ground.coastSlope = coastSlope, ground.rocky = rocky, ground.near = near;
    ground.offsetKm = shoreKm - originalShoreKm, ground.erodibility = map.erodibility, ground.cellKm = cellKm;
    ground.relief = relief, ground.shoreMetric = shoreMetric, ground.formsGradient = map.formsGradient, ground.cliffSlope = cliffSlope;
    // Roughness: plains 0.1, hills 0.35, old chains 0.5, terraces and badlands 0.6, young chains 1.
    float rough = 0.1 + 0.25 * smoothstep(50.0, 400.0, relief) + 0.15 * smoothstep(400.0, 1500.0, relief);
    rough = lerp(rough, 1.0, youth * smoothstep(500.0, 1500.0, relief));
    ground.roughness = lerp(rough, 0.6, max(mesas, badlands));

    return ground;
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
float ReliefElevation(double3 position, bool valleys)
{
    const ReliefGround ground = ReliefSampleGround(position, valleys);
    float h = ground.height;
    [branch] if (valleys)
    {
        const float candidate = ErosionCoast(RlMakePoint(position), h, ground.shoreKm, ground.coastSlope, ground.rocky,
                                            ground.near, ground.offsetKm, ground.formsGradient, ground.erodibility,
                                            ground.cellKm, ground.cliffSlope, ground.relief, ground.shoreMetric);
        [branch] if (candidate < h)
        {
            const double3 witness = ErosionSeaPoint(position, ground.formsGradient);
            const ReliefGround sea = ReliefSampleGround(witness, false);
            const float level = ReliefFinish(witness, sea.height, sea.near, sea.rocky, sea.smoothKm, sea.cellKm, sea.volcanic);
            h = lerp(h, candidate, ErosionSeaAccess(level, sea.coastSlope));
        }
    }
    gRoughness = ground.roughness;
    gVolcanic = ground.volcanicShare;
    return ReliefFinish(position, h, ground.near, ground.rocky, ground.smoothKm, ground.cellKm, ground.volcanic);
}

float ReliefElevation(double3 position)
{
    return ReliefElevation(position, true);
}

#endif
