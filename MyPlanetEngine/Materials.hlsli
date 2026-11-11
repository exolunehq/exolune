// Materials.hlsli - the ground's materials: noises anchored on the planet, close-up textures, the generated
// materials, and their weights. Shared by the terrain's pixels and the objects' placement. Needs Planet.hlsli and
// PlanetSettings.hlsli.
#ifndef MATERIALS_HLSLI
#define MATERIALS_HLSLI
#include "BiomePalette.hlsli"
#include "Climate.hlsli"
#include "PlanetMap.hlsli"
#include "CityGrade.hlsli"

// ---------------------------------------------------------------------------------------------
// Noises drawn per pixel in the planet's fixed frame: they do not move with the mesh, so they do not
// flicker. See docs/log/spec-stabilite.md and docs/log/spec-rendu.md, step C.
// ---------------------------------------------------------------------------------------------

uint3 Hash(uint3 v) // pcg3d, Jarzynski & Olano 2020
{
    v = v * 1664525u + 1013904223u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    v ^= v >> 16u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    return v;
}

float3 LatticeRandom(uint3 cell) // in [-1, 1]
{
    return float3(Hash(cell) >> 8u) * (2.0 / 16777215.0) - 1.0;
}

// Lattice cell and fraction of the planet point anchor + q (q in m, planet frame) for the octave of
// wavelength unit * 2^-j. The anchor is a whole number of every octave's lattice period: lattice indices
// stay exact over the whole planet, in 32-bit wrapping arithmetic.
void LatticePoint(float3 q, int j, out uint3 cell, out float3 w)
{
    const float unit = detailOrigin.w;
    int3 whole;
    float3 p;
    if (j >= 0) // anchor * 2^j is whole
    {
        whole = detailAnchor.xyz << j;
        p = q * exp2((float)j) / unit;
    }
    else // anchor * 2^-s: whole part by shifting, the rest goes with q
    {
        const int s = -j;
        whole = detailAnchor.xyz >> s;
        p = (q / unit + (float3)(detailAnchor.xyz & ((1 << s) - 1))) * exp2((float)j);
    }
    const float3 c = floor(p);
    cell = uint3(whole + (int3)c);
    w = p - c;
}

// Gradient, in lattice units, and value of the gradient noise at lattice cell `cell` + fraction w.
float4 NoiseValueGradient(uint3 cell, float3 w)
{
    const float3 u = w * w * w * (w * (w * 6.0 - 15.0) + 10.0);
    const float3 du = 30.0 * w * w * (w * (w - 2.0) + 1.0);
    const float3 ga = LatticeRandom(cell), gb = LatticeRandom(cell + uint3(1, 0, 0));
    const float3 gc = LatticeRandom(cell + uint3(0, 1, 0)), gd = LatticeRandom(cell + uint3(1, 1, 0));
    const float3 ge = LatticeRandom(cell + uint3(0, 0, 1)), gf = LatticeRandom(cell + uint3(1, 0, 1));
    const float3 gg = LatticeRandom(cell + uint3(0, 1, 1)), gh = LatticeRandom(cell + uint3(1, 1, 1));
    const float va = dot(ga, w), vb = dot(gb, w - float3(1, 0, 0)), vc = dot(gc, w - float3(0, 1, 0));
    const float vd = dot(gd, w - float3(1, 1, 0)), ve = dot(ge, w - float3(0, 0, 1));
    const float vf = dot(gf, w - float3(1, 0, 1)), vg = dot(gg, w - float3(0, 1, 1)), vh = dot(gh, w - 1.0);
    const float kxy = va - vb - vc + vd, kyz = va - vc - ve + vg, kzx = va - vb - ve + vf;
    const float kxyz = -va + vb + vc - vd + ve - vf - vg + vh;
    const float3 gradient = ga + u.x * (gb - ga) + u.y * (gc - ga) + u.z * (ge - ga) + u.x * u.y * (ga - gb - gc + gd)
         + u.y * u.z * (ga - gc - ge + gg) + u.z * u.x * (ga - gb - ge + gf) + u.x * u.y * u.z * (-ga + gb + gc - gd + ge - gf - gg + gh)
         + du * (float3(vb, vc, ve) - va + u.yzx * float3(kxy, kyz, kzx) + u.zxy * float3(kzx, kxy, kyz) + u.yzx * u.zxy * kxyz);
    const float value = va + u.x * (vb - va) + u.y * (vc - va) + u.z * (ve - va) + u.x * u.y * kxy + u.y * u.z * kyz
                      + u.z * u.x * kzx + u.x * u.y * u.z * kxyz;
    return float4(gradient, value);
}

float3 NoiseGradient(uint3 cell, float3 w)
{
    return NoiseValueGradient(cell, w).xyz;
}

// Three independent gradient noises for the price of one lattice: at each lattice point, three gradients of 10-bit
// components from one hash, its bits laid as the mantissas of floats in [1, 2), without conversions. Never a value
// noise (docs/principes.md, a noise never shows its lattice): flat around each lattice point, its plateaus, aligned from
// one octave to the next, tiled the land like a low-resolution image once the pixels kept two or three octaves, from
// 50 km up. Scaled to the value noise's deviation, 0.40 per octave against 0.19, for which Fbm3's deviation and every
// threshold drawn on these noises were set: the tails match within 3 %.
float3 Noise3(uint3 cell, float3 w)
{
    const float3 u = w * w * w * (w * (w * 6.0 - 15.0) + 10.0);
    float3 sum = 0.0;
    [unroll]
    for (uint k = 0; k < 8; ++k)
    {
        const uint3 o = uint3(k & 1u, (k >> 1) & 1u, k >> 2);
        const float3 d = w - (float3)o, weights = lerp(1.0 - u, u, (float3)o);
        const uint3 h = Hash(cell + o);
        const float3 a = asfloat(((h << 11u) & 0x7FE000u) | 0x3F800000u), b = asfloat(((h << 1u) & 0x7FE000u) | 0x3F800000u);
        const float3 c = asfloat(((h >> 9u) & 0x7FE000u) | 0x3F800000u);
        sum += weights.x * weights.y * weights.z * (2.0 * float3(dot(a, d), dot(b, d), dot(c, d)) - 3.0 * (d.x + d.y + d.z)); // in [-1, 1)
    }
    return 2.09 * sum;
}

// Fractal sum of Noise3 at the planet point anchor + q, from the widest wavelength down to the finest
// (log2, in m), each octave `gain` times the previous one. Octaves fade out between 4 and 2 pixels
// (pixel: log2 of the pixel size, in m): far away, only the wide ones remain, without flickering.
// Normalised by the sum of all the amplitudes: standard deviation about 0.2.
float3 Fbm3(float3 q, float widest, float finest, float pixel, float gain, uint seed)
{
    const float unitLog = log2(detailOrigin.w);
    const int first = (int)ceil(unitLog - widest), last = (int)floor(unitLog - finest);
    float3 sum = 0.0;
    float amplitude = 1.0;
    [loop]
    for (int j = first; j <= min(last, first + 15); ++j)
    {
        const float wavelength = unitLog - j;
        if (wavelength <= pixel + 1.0)
            break;
        uint3 cell;
        float3 w;
        LatticePoint(q, j, cell, w);
        sum += amplitude * smoothstep(pixel + 1.0, pixel + 2.0, wavelength) * Noise3(cell + (uint)j * 0x9E3779B9u + seed, w);
        amplitude *= gain;
    }
    return sum * (1.0 - gain) / (1.0 - pow(gain, (float)(last - first + 1)));
}

// Slope of the fine detail at the planet point anchor + q: octaves of wavelength unit * 2^-j, only where
// the vertex normals lost the terrain's slope: between 1 and 8 cells. Only within the terrain's own fine
// octaves, and never finer than 2 pixels, below which they would flicker. Both ends fade continuously.
float3 DetailSlope(float3 q, float cellSize, float footprint)
{
    const float unit = detailOrigin.w;
    const float coarse = log2(cellSize); // all logs base 2, in m
    const float fine = max(max(coarse, log2(2.0 * footprint)), log2(DETAIL_MIN_WAVELENGTH) - 1.0);
    const float widest = log2(DETAIL_MAX_WAVELENGTH);
    const int first = (int)ceil(log2(unit) - min(coarse + 3.0, widest)), last = (int)floor(log2(unit) - fine);
    float3 slope = 0.0;
    [loop]
    for (int j = first; j <= min(last, first + 3); ++j)
    {
        const float wavelength = log2(unit) - j;
        const float weight = (1.0 - smoothstep(coarse + 1.0, coarse + 3.0, wavelength))
                           * (1.0 - smoothstep(widest - 1.0, widest, wavelength))
                           * smoothstep(fine, fine + 1.0, wavelength);
        uint3 cell;
        float3 w;
        LatticePoint(q, j, cell, w);
        slope += weight * NoiseGradient(cell + (uint)j * 0x9E3779B9u, w);
    }
    return DETAIL_SLOPE * slope; // amplitude DETAIL_SLOPE * wavelength: the same slope at every scale
}

// ---------------------------------------------------------------------------------------------
// Close-up textures (docs/log/spec-rendu.md, step D): colour and slope of each material below the terrain's
// finest octave, anchored on the planet like the fine detail. Each octave fades out between 4 and 2 pixels:
// far away a texture fades to its mean, colour factor 1, no slope, height 0.5, and step C's colour holds.
// ---------------------------------------------------------------------------------------------

struct Texture
{
    float3 color;  // factor on the material's colour, mean 1
    float3 slope;  // height gradient, planet frame, whole: the materials are decided on it
    float  cavity; // factor on the sky's light, mean 1
    float  relief; // height above the texture's mean (m), for the borders between materials (HeightBlend)
};

Texture FlatTexture()
{
    Texture t;
    t.color = 1.0;
    t.slope = 0.0;
    t.cavity = 1.0;
    t.relief = 0.0;
    return t;
}

// 1 for an octave of wavelength 2^wavelength m wider than 4 pixels, 0 under 2 pixels (pixel: log2 of the
// pixel size, in m).
float OctaveFade(float wavelength, float pixel)
{
    return smoothstep(pixel + 1.0, pixel + 2.0, wavelength);
}

// Tufts: around a random point in each lattice cell, a soft bump of random radius, 0.6 to 1.3 cells, and
// height, 0.5 to 1: a * (1 - d^2 / r^2)^2. The bumps overlap and add up to S; the field is 1 - exp(-S), with
// no crease where one bump takes over from another. Returns the field and its gradient, in lattice units.
float TuftField(uint3 cell, float3 w, uint seed, out float3 gradient)
{
    float sum = 0.0;
    float3 sumGradient = 0.0;
    [unroll]
    for (int z = -1; z <= 1; ++z)
        [unroll]
        for (int y = -1; y <= 1; ++y)
            [unroll]
            for (int x = -1; x <= 1; ++x)
            {
                const int3 o = int3(x, y, z);
                const uint3 c = cell + (uint3)o + seed;
                const float3 d = w - ((float3)o + 0.5 + 0.5 * LatticeRandom(c));
                const float2 shape = 0.5 + 0.5 * LatticeRandom(c + 0x51EDu).xy;
                const float radius = 0.6 + 0.7 * shape.x, height = 0.5 + 0.5 * shape.y;
                const float inside = max(0.0, 1.0 - dot(d, d) / (radius * radius));
                sum += height * inside * inside;
                sumGradient -= 4.0 * height * inside / (radius * radius) * d;
            }
    const float e = exp(-sum);
    gradient = e * sumGradient;
    return 1.0 - e;
}

// Mean of TuftField over the planet, measured: 47 % of the ground under tufts.
static const float TUFT_MEAN = 0.464;

// Grass, steppe and meadow: 2 m patches of greener and drier tints, tufts of 15 to 35 cm with darker feet,
// bumps from 4 m down to the pixel, and the blades' speckle from 3 cm down. Octave j of the anchor's
// lattice has a wavelength of 64 m * 2^-j.
Texture GrassTexture(float3 q, float pixel)
{
    const int unitLog = (int)log2(detailOrigin.w);
    Texture t = FlatTexture();
    uint3 cell;
    float3 w;

    float fade = OctaveFade(1.0, pixel); // patches, 2 m
    if (fade > 0.0)
    {
        LatticePoint(q, unitLog - 1, cell, w);
        const float3 n = Noise3(cell + 0x5A17u, w);
        t.color *= 1.0 + fade * (0.20 * n.x + float3(0.12, 0.04, -0.10) * n.y);
    }
    fade = OctaveFade(-3.0, pixel); // tufts, on cells of 12.5 cm
    if (fade > 0.0)
    {
        LatticePoint(q, unitLog + 3, cell, w);
        float3 gradient;
        const float tuft = TuftField(cell, w, 0x7F4Au, gradient);
        t.color *= 1.0 + fade * 0.40 * (tuft - TUFT_MEAN);
        t.relief += fade * 0.05 * (tuft - TUFT_MEAN);
        t.slope += fade * (0.05 / 0.125) * gradient; // 5 cm high, over the 12.5 cm cell
    }
    [loop]
    for (int j = unitLog - 2; j <= unitLog + 7; ++j) // bumps, 4 m to 8 mm; the blades from 3 cm
    {
        fade = OctaveFade((float)(unitLog - j), pixel);
        if (fade <= 0.0)
            break;
        LatticePoint(q, j, cell, w);
        const bool blades = j >= unitLog + 5;
        t.slope += fade * (blades ? 0.15 : 0.05) * NoiseGradient(cell + (uint)j * 0x9E3779B9u + 0x3C6Fu, w);
        if (blades)
            t.color *= 1.0 + fade * 0.22 * Noise3(cell + (uint)j * 0x9E3779B9u + 0x2B7Du, w).x;
    }
    return t;
}

// The detail bands (docs/spec-texturage-universel.md): the scales a material's other sources leave empty, from
// 2^finest to 2^widest m, one octave of the planet's gradient noise per wavelength. Each octave tilts the ground by
// the same `slope`, a self-similar relief like nature's, the same contrast in every octave, and changes its colour by
// the same `colour` factor; each fades out with the pixel like every noise (OctaveFade). One function for every
// material: only its parameters differ (PlanetSettings.hlsli). Colour factor of mean 1; slope in the planet frame.
Texture DetailBands(float3 q, float pixel, float finest, float widest, float slope, float colour, uint seed)
{
    const int unitLog = (int)round(log2(detailOrigin.w));
    Texture t = FlatTexture();
    [loop]
    for (int j = (int)round(unitLog - widest); j <= (int)round(unitLog - finest); ++j) // octave j: 2^(unitLog - j) m
    {
        const float fade = OctaveFade((float)(unitLog - j), pixel);
        if (fade <= 0.0)
            break;
        uint3 cell;
        float3 w;
        LatticePoint(q, j, cell, w);
        const float4 n = NoiseValueGradient(cell + (uint)j * 0x9E3779B9u + seed, w);
        t.slope += fade * slope * n.xyz; // a height of slope * wavelength * noise: its gradient in lattice units
        t.color *= 1.0 + fade * colour * n.w;
    }
    return t;
}

// A texture with its detail bands laid on it: colour factors multiplied, slopes added.
Texture WithBands(Texture t, Texture bands)
{
    t.color *= bands.color;
    t.slope += bands.slope;
    return t;
}

// ---------------------------------------------------------------------------------------------
// Generated materials (docs/spec-textures-generees.md): seamless tiles drawn at startup by
// MaterialGenerator.hlsl, laid on the planet with a stochastic tiling and a biplanar projection.
// ---------------------------------------------------------------------------------------------

Texture2DArray<float4> materialColor : register(t5);   // rgb: colour factor / 2; a: cavity
Texture2DArray<float4> materialSurface : register(t6); // xy: slope * 0.25 + 0.5; z: height
SamplerState materialSampler : register(s1);           // wrapping, anisotropic

// Materials and their tiles (m), as in MaterialGenerator.hlsl; a tile divides the anchor's 64 m. Each has a
// fine tile too, MATERIAL_FINE slices further: FINE_TILE, 1 mm per texel, wavelengths under 3 cm only. It is
// read while a pixel covers less than FINE_FADE.y, fading from FINE_FADE.x.
static const uint MATERIAL_SAND = 0, MATERIAL_ROCK = 1, MATERIAL_SCREE = 2, MATERIAL_FINE = 3;
// A photo has the orientation it was shot in: the rock's cliff photo, MATERIAL_ROCK, is a face; MATERIAL_ROCK_TOP is
// the same marble photographed from above, marble_cliff_05, 20 m, for the gentler rock.
static const uint MATERIAL_ROCK_TOP = 6;
static const float ROCK_TOP_TILE = 64.0 / 3.0;
// Photo scans (docs/log/spec-hybride-scans.md), loaded by Scans.cpp over their generated slices at their real scale,
// rounded to a tile that divides 64 m: the sand, and the rock, a cliff face of 12.7 m photographed head-on, for its
// fractures and flutes (docs/spec-parois-minerales.md), and the same marble from above. Their fine tiles stay, sharper
// than a 2k scan on 1024 texels. Every rock is that photo (docs/journal-planete.md, 2026-10-24, one rock).
static const float SAND_TILE = 64.0 / 24.0, ROCK_TILE = 64.0 / 5.0, SCREE_TILE = 4.0, FINE_TILE = 1.0;
static const float HEIGHT_RANGE[7] = { 0.06, 0.6, 0.3, 0.01, 0.01, 0.02, 0.6 }; // m per height unit, as in MaterialGenerator.hlsl
static const float2 FINE_FADE = float2(0.01, 0.02); // m per pixel
static const float MATERIAL_LAST_MIP = 10.0; // 1 x 1: the tile's mean

// Set by the pixels before reading the materials: the mesh cell there (m), for the strata's step; 0 elsewhere.
static float gMeshCell = 0.0;
// How much the textures' heights move the materials' borders (HeightBlend): 1 for the pixels near the camera,
// fading out as they grow; 0 where the materials are filtered to a lattice cell, for the objects' placement.
static float gHeightBlend = 1.0;
// 0: GroundMaterials decides the materials' shares without sampling their textures (the plants' placement, which needs
// the shares alone, docs/recherche-vegetation.md); the height blend must be off too, gHeightBlend = 0.
static float gMaterialTextures = 1.0;

struct MaterialTaps
{
    float3 color;  // factor, mean 1
    float  cavity; // factor, mean 1
    float  height; // mean 0.5
    float2 slope;  // along the projection's two axes, m per m, whole
};

// One projection of a material on the plane of two planet axes. q2: the point on that plane from the anchor
// (m); anchor2: the anchor on it, in 64 m units. A triangle grid of cells of half a tile, sheared so that
// 64 m are whole cells: every vertex takes the tile at its own random offset, turned by `angle` plus a
// little, and every coordinate is measured from the vertex, so that nothing depends on where the anchor
// is. The three taps' colours are blended keeping their variance, so the blend is not washed out.
MaterialTaps ProjectMaterial(float2 q2, float2 dq2dx, float2 dq2dy, int2 anchor2, uint slice, float tile, float angle,
                             float4 meanColor, float meanHeight)
{
    const float cell = 0.5 * tile;
    const int perAnchor = (int)(64.0 / cell + 0.5); // even
    const int2 anchorSkew = int2(anchor2.x * perAnchor - anchor2.y * perAnchor / 2, anchor2.y * perAnchor);
    const float2 g = q2 / cell, skew = float2(g.x - 0.5 * g.y, g.y);
    const int2 base = (int2)floor(skew);
    const float2 f = skew - base;
    int2 v[3];
    float3 bary;
    if (f.x + f.y < 1.0)
    {
        v[0] = base; v[1] = base + int2(1, 0); v[2] = base + int2(0, 1);
        bary = float3(1.0 - f.x - f.y, f.x, f.y);
    }
    else
    {
        v[0] = base + int2(1, 1); v[1] = base + int2(0, 1); v[2] = base + int2(1, 0);
        bary = float3(f.x + f.y - 1.0, 1.0 - f.x, 1.0 - f.y);
    }
    float3 w = bary * bary;
    w *= w; // sharpened: the blends between copies stay narrow
    w /= dot(w, 1.0);

    MaterialTaps r;
    r.color = 0.0; r.cavity = 0.0; r.height = 0.0; r.slope = 0.0;
    [unroll]
    for (int k = 0; k < 3; ++k)
    {
        const uint3 h = Hash(uint3((uint2)(v[k] + anchorSkew), slice * 0x632BE5ABu + 0x1F3Du));
        const float2 offset = float2(h.xy >> 8) / 16777216.0;
        const float turn = angle + 0.15 * (float(h.z >> 8) / 16777216.0 - 0.5);
        const float2 cs = float2(cos(turn), sin(turn));
        const float2 d = q2 - float2(v[k].x + 0.5 * v[k].y, v[k].y) * cell; // from the vertex, m
        const float2 uv = float2(dot(cs, d), cs.x * d.y - cs.y * d.x) / tile + offset;
        const float2 uvdx = float2(dot(cs, dq2dx), cs.x * dq2dx.y - cs.y * dq2dx.x) / tile;
        const float2 uvdy = float2(dot(cs, dq2dy), cs.x * dq2dy.y - cs.y * dq2dy.x) / tile;
        const float4 c = materialColor.SampleGrad(materialSampler, float3(uv, slice), uvdx, uvdy);
        const float4 s = materialSurface.SampleGrad(materialSampler, float3(uv, slice), uvdx, uvdy);
        const float2 slope = (s.xy - 0.5) * 4.0; // along the turned tile
        r.color += w[k] * (c.rgb / meanColor.rgb - 1.0);
        r.cavity += w[k] * (c.a / meanColor.a - 1.0);
        r.height += w[k] * (s.z - meanHeight);
        r.slope += w[k] * float2(cs.x * slope.x - cs.y * slope.y, cs.y * slope.x + cs.x * slope.y);
    }
    // Colours keep their contrast where copies blend; heights and slopes do not: amplified up to 1.7 times,
    // crossing ledges of two copies would add up into blades, metres high on the 64 m tile.
    const float keep = rsqrt(dot(w, w));
    r.color = 1.0 + keep * r.color;
    r.cavity = 1.0 + keep * r.cavity;
    r.height = 0.5 + r.height;
    return r;
}

// The unit vector of planet axis i.
float3 Axis(int i)
{
    return float3(i == 0, i == 1, i == 2);
}

// A generated material at the planet point q (from the anchor), with q's screen derivatives, its fine tile laid
// on it near the camera: the planet axes closest to the surface's normal
// (planet frame) project it, so that cliffs are not stretched. Each axis weighs max(|n| - 0.45, 0)^2: one plane
// alone within 25 degrees of its axis, two along an edge of the cube, three at its diagonal, and continuous
// everywhere. A biplanar blend (Quilez's, sharpened to the power 8) turned all its weights to nearly 0 near the
// diagonal, so that a hair of normal moved them from one plane to the other, and a tile's relief from one copy to
// another between neighbouring vertices: needles and blades. The tile turns by `angle` on each projection plane, the
// wind for sand.
// With alignUp, it turns instead so that its y axis climbs the local vertical upPlanet wherever that vertical
// crosses the plane: a cliff photo stays upright.
Texture GeneratedTexture(uint slice, float tile, uint fineSlice, float3 q, float3 dqdx, float3 dqdy, float3 normalPlanet,
                         float3 upPlanet, float angle, bool alignUp)
{
    const float4 meanColor = materialColor.SampleLevel(materialSampler, float3(0.5, 0.5, slice), MATERIAL_LAST_MIP);
    const float meanHeight = materialSurface.SampleLevel(materialSampler, float3(0.5, 0.5, slice), MATERIAL_LAST_MIP).z;
    // The fine tile, while the pixel is small enough to see it.
    const float footprint = max(length(dqdx), length(dqdy));
    const float fine = TEXTURE_FINE * (1.0 - smoothstep(FINE_FADE.x, FINE_FADE.y, footprint));
    // Past a pixel of two tiles, a tile's mips hold nothing but its mean: it is not read, and fades to it before.
    const float coarse = 1.0 - smoothstep(tile, 2.0 * tile, footprint);
    const float4 fineMeanColor = materialColor.SampleLevel(materialSampler, float3(0.5, 0.5, fineSlice), MATERIAL_LAST_MIP);
    const float fineMeanHeight = materialSurface.SampleLevel(materialSampler, float3(0.5, 0.5, fineSlice), MATERIAL_LAST_MIP).z;
    float3 weights = max(abs(normalPlanet) - 0.45, 0.0);
    weights *= weights;
    weights /= weights.x + weights.y + weights.z; // at least 0.127^2 at the diagonal
    weights = max(weights - 0.01, 0.0); // a plane under 1 % is left out, the others take its share
    weights /= weights.x + weights.y + weights.z;

    Texture t;
    t.color = 0.0; t.slope = 0.0; t.cavity = 0.0; t.relief = 0.0;
    [unroll]
    for (int k = 0; k < 3; ++k)
    {
        const int a = k;
        const float3 b = Axis(a == 2 ? 0 : a + 1), c = Axis(a == 0 ? 2 : a - 1);
        float turn = angle;
        if (alignUp) // the tile's y axis, from the wind's level direction to the vertical's climb on this plane
        {
            const float2 climb = float2(dot(upPlanet, b), dot(upPlanet, c));
            const float2 level = float2(-sin(angle), cos(angle));
            const float2 axis = normalize(lerp(level, normalize(climb + 1e-6), smoothstep(0.2, 0.5, length(climb))) + 1e-6);
            turn = atan2(axis.y, axis.x) - 1.5707963;
        }
        // q, its steps and the anchor on this projection's plane.
        const float2 q2 = float2(dot(q, b), dot(q, c)), dq2dx = float2(dot(dqdx, b), dot(dqdx, c));
        const float2 dq2dy = float2(dot(dqdy, b), dot(dqdy, c));
        const int2 anchor2 = int2(dot(detailAnchor.xyz, (int3)b), dot(detailAnchor.xyz, (int3)c));
        MaterialTaps m;
        m.color = 1.0; m.cavity = 1.0; m.height = 0.5; m.slope = 0.0;
        if (weights[k] > 0.0 && coarse > 0.0)
        {
            m = ProjectMaterial(q2, dq2dx, dq2dy, anchor2, slice, tile, turn, meanColor, meanHeight);
            m.color = 1.0 + coarse * (m.color - 1.0);
            m.cavity = 1.0 + coarse * (m.cavity - 1.0);
            m.height = 0.5 + coarse * (m.height - 0.5);
            m.slope *= coarse;
        }
        if (weights[k] > 0.0 && fine > 0.0) // the fine tile on the coarse one: factors multiplied, heights added
        {
            const MaterialTaps f = ProjectMaterial(q2, dq2dx, dq2dy, anchor2, fineSlice, FINE_TILE, turn, fineMeanColor, fineMeanHeight);
            m.color *= 1.0 + fine * (f.color - 1.0);
            m.cavity *= 1.0 + fine * (f.cavity - 1.0);
            m.height += fine * (f.height - 0.5) * HEIGHT_RANGE[fineSlice] / HEIGHT_RANGE[slice];
            m.slope += fine * f.slope;
        }
        const float3 slope = m.slope.x * b + m.slope.y * c;
        t.color += weights[k] * m.color;
        t.cavity += weights[k] * m.cavity;
        t.relief += weights[k] * (m.height - 0.5) * HEIGHT_RANGE[slice];
        t.slope += weights[k] * slope;
    }
    return t;
}

// Wind ripples on sand, drawn per pixel rather than tiled: copies of a periodic pattern meet out of phase in
// the tiling's blends. A plane wave in space, across the planet's surface: its wave vector is the wind,
// tangent to the ground, rounded to an integer vector K of length about 8, within 4 degrees. With M ripples
// per 64 m along K, the anchor's 64 m always add whole ripples: the phase is exact everywhere, and no
// projection switches from one axis to another. Anchored noises of 16 m, 4 m and 2 m vary the spacing, bend
// the crests and split them where they crowd; others, of 16 m and 2 m, weaken them in places. Ripples 12.5 cm apart, 6 mm high, gentle on the
// windward side and steep on the lee side, darker heavy grains in the troughs. They fade out to their mean
// as they near 2 ripples per 5 pixels on screen, measured along their own direction.
Texture SandRipples(float3 q, float3 dqdx, float3 dqdy, float3 upPlanet, float windAngle)
{
    Texture t = FlatTexture();
    const float3 east = normalize(cross(float3(0.0, 1.0, 0.0), upPlanet) + 1e-6), north = cross(upPlanet, east);
    const float3 K = round(8.0 * (cos(windAngle) * east + sin(windAngle) * north));
    const float3 k = round(512.0 / length(K)) * K / 64.0; // cycles per m

    const int unitLog = (int)log2(detailOrigin.w);
    uint3 cell;
    float3 w;
    LatticePoint(q, unitLog - 4, cell, w); // 16 m: octave j has a wavelength of 64 m * 2^-j
    const float4 wide = NoiseValueGradient(cell + 0x51A3u, w);
    LatticePoint(q, unitLog - 2, cell, w); // 4 m
    const float4 middle = NoiseValueGradient(cell + 0x4D13u, w);
    LatticePoint(q, unitLog - 1, cell, w); // 2 m
    const float4 narrow = NoiseValueGradient(cell + 0x2C77u, w);
    const float3 phaseGradient = k + 5.0 * wide.xyz / 16.0 + 3.5 * middle.xyz / 4.0 + 2.0 * narrow.xyz / 2.0; // planet frame, per m
    const float cyclesPerPixel = max(abs(dot(phaseGradient, dqdx)), abs(dot(phaseGradient, dqdy)));
    const float fade = 1.0 - smoothstep(0.2, 0.4, cyclesPerPixel);
    if (fade <= 0.0)
        return t;
    LatticePoint(q, unitLog - 4, cell, w); // 16 m
    const float weak = Noise3(cell + 0x6E21u, w).x;
    LatticePoint(q, unitLog - 1, cell, w); // 2 m
    const float strength = lerp(0.25, 1.0, smoothstep(-0.55, 0.0, weak)) * (0.85 + 0.3 * Noise3(cell + 0x3B9Fu, w).x);

    const float phase = frac(dot(k, q) + 5.0 * wide.w + 3.5 * middle.w + 2.0 * narrow.w);
    const bool windward = phase < 0.7;
    const float rise = windward ? phase / 0.7 : (1.0 - phase) / 0.3, pi = 3.14159265;
    const float profile = 0.5 - 0.5 * cos(pi * rise);
    const float profileSlope = 0.5 * pi * sin(pi * rise) * (windward ? 1.0 / 0.7 : -1.0 / 0.3);

    LatticePoint(q, unitLog + 1, cell, w); // 50 cm: the crests rise and sink along each ripple
    const float amount = fade * strength * (0.75 + 0.6 * Noise3(cell + 0x1A2Bu, w).x);
    t.slope = amount * 0.006 * profileSlope * phaseGradient;
    t.relief = amount * 0.006 * (profile - 0.5);
    t.color = 1.0 + amount * (0.10 * (profile - 0.5) - 0.08 * (smoothstep(0.35, 0.0, profile) - 0.25));
    t.cavity = 1.0 - amount * 0.2 * (0.5 - profile);
    return t;
}

// A planet-frame slope, face-local, in the plane of the surface of normal n.
float3 TangentSlope(float3 planetSlope, float3 n)
{
    const float3 s = float3(dot(planetSlope, faceX.xyz), dot(planetSlope, faceY.xyz), dot(planetSlope, faceZ.xyz));
    return s - dot(s, n) * n;
}

// A material's weight, moved at its borders by the height of the texture it covers: where that texture
// rises above its mean (rise > 0), the material gives way. Unchanged where the weight is 0 or 1.
static const float BLEND_RISE = 0.3; // m: a texture risen this far above its mean moves a border by a full weight
float HeightBlend(float weight, float rise)
{
    return saturate(weight - 8.0 * weight * (1.0 - weight) * rise * gHeightBlend);
}

// The rock's kind by region (docs/spec-textures-generees.md): noises of 40 km to 500 m, for its place in a palette
// of real rocks, its iron and its desert varnish. Computed per vertex, filtered to the cell, interpolated.
float3 Geology(float3 q, float cellSize)
{
    return Fbm3(q, log2(40000.0), log2(500.0), log2(cellSize), 0.5, 37u);
}

// The kind of rock, by region (docs/spec-textures-generees.md): geology.x walks a palette of real rocks, linear
// reflectances, dark to light to red, so that neighbours blend into plausible rocks; geology.y reddens it with
// iron and, in dry lands, geology.z darkens it with desert varnish.
float3 RockColor(float3 geology, float humidity)
{
    const float3 palette[5] = { float3(0.08, 0.075, 0.07),  // basalt
                                float3(0.26, 0.25, 0.24),   // granite
                                float3(0.36, 0.34, 0.30),   // limestone
                                float3(0.38, 0.28, 0.18),   // ochre sandstone
                                float3(0.32, 0.16, 0.09) }; // red sandstone
    const float t = 4.0 * saturate(0.5 + 1.6 * geology.x);
    const int i = min((int)t, 3);
    float3 color = lerp(palette[i], palette[i + 1], smoothstep(0.0, 1.0, t - i));
    color *= lerp(1.0, float3(1.15, 0.9, 0.75), saturate(3.0 * geology.y));
    color *= lerp(1.0, float3(0.6, 0.55, 0.5), saturate(3.0 * geology.z) * (1.0 - smoothstep(0.15, 0.40, humidity)));
    return color;
}

// The ground's colour from the real Earth (docs/spec-photos-par-echelle.md): the palette measured on Blue Marble, by
// temperature and humidity, interpolated; w, the relative spread of brightness among the Earth's places of that
// climate. Over what the pixel holds of the temperature (sigma), its mean, three taps after the universal rule.
float4 BiomeColor(float temperature, float humidity, float sigma)
{
    const float h = saturate(humidity) * (BIOME_H_BINS - 1);
    const int h0 = min((int)h, BIOME_H_BINS - 2);
    float4 colour = 0.0;
    [unroll]
    for (int k = -1; k <= 1; ++k)
    {
        const float t = saturate((temperature + 1.7320508 * sigma * k - BIOME_T_MIN) / (BIOME_T_MAX - BIOME_T_MIN)) * (BIOME_T_BINS - 1);
        const int t0 = min((int)t, BIOME_T_BINS - 2);
        const float4 low = lerp(BIOME_PALETTE[t0 * BIOME_H_BINS + h0], BIOME_PALETTE[t0 * BIOME_H_BINS + h0 + 1], h - h0);
        const float4 high = lerp(BIOME_PALETTE[(t0 + 1) * BIOME_H_BINS + h0], BIOME_PALETTE[(t0 + 1) * BIOME_H_BINS + h0 + 1], h - h0);
        colour += (k == 0 ? 2.0 / 3.0 : 1.0 / 6.0) * lerp(low, high, t - t0);
    }
    return colour;
}

// How far the strata are raised (docs/spec-roche-organique.md, step 2), m, in w; its gradient, planet frame, in
// xyz. Never flat: one perturbation of the beds everywhere, from 8 km to 4 m, its slope STRATA_SLOPE at 8 km and 15 %
// less at each octave down, for folds and dips at the mountains' scale and gentle waves at the metre's. Where only some
// regions had a dip and folds, the others' beds lay level, contour lines laid on the mountains. Filtered by `cellSize`:
// the pixel's size for the pixels, which compute it (filtered by the mesh's cells, 13 pixels wide, its octaves came in
// plain to see and the strata slid on the way down).
float4 StrataShift(float3 q, float cellSize)
{
    const int unitLog = (int)log2(detailOrigin.w);
    float4 shift = 0.0;
    [loop]
    for (int j = unitLog - 13; j <= unitLog - 2; ++j) // octave j has a wavelength of 64 m * 2^-j
    {
        const float wavelength = exp2((float)(unitLog - j)), fade = OctaveFade(log2(wavelength), log2(cellSize));
        if (fade <= 0.0)
            break;
        uint3 cell;
        float3 w;
        LatticePoint(q, j, cell, w);
        const float strength = STRATA_SLOPE * pow(0.85, (float)(j - (unitLog - 13)));
        const float4 noise = NoiseValueGradient(cell + (uint)j * 0x9E3779B9u + 0x5713u, w);
        shift += strength * fade * float4(noise.xyz, wavelength * noise.w); // the gradient, in lattice units, per m
    }
    return shift;
}

// The stratigraphic column of the bedded rock (docs/spec-roche-organique.md, step 3), drawn along s, the height
// less StrataShift, the same everywhere in space: beds that run unbroken across a cliff and never repeat.
// One set of bedding planes along s: on a lattice of `spacing` m, a plane in each cell with probability `keep`,
// jittered within it, and always one in cells that are multiples of `every`, so that `every` cells either way
// hold the planes around s. The planes below and above s, and their cells, which name them.
void BeddingPlanes(float s, float spacing, float keep, int every, uint seed, out float below, out float above, out int belowName,
                   out int aboveName)
{
    const int c = (int)floor(s / spacing);
    below = -1e9; above = 1e9; belowName = c; aboveName = c;
    [loop]
    for (int k = c - every; k <= c + every; ++k)
    {
        uint h = (uint)k * 747796405u + seed * 2891336453u; // pcg, one component: two randoms in its halves
        h = ((h >> ((h >> 28u) + 4u)) ^ h) * 277803737u;
        h ^= h >> 22u;
        if (k % every != 0 && float(h & 0xFFFFu) > keep * 65535.0)
            continue;
        const float plane = (k + 0.15 + 0.7 * float(h >> 16u) / 65535.0) * spacing;
        if (plane <= s && plane > below) { below = plane; belowName = k; }
        if (plane > s && plane < above) { above = plane; aboveName = k; }
    }
}

// The lenses (docs/spec-roche-organique.md, step 5): a slow field in space, noises of 256 and 128 m, against which
// each bedding plane has its threshold: where the field falls below it, the plane's step dies out, and the beds
// on either side merge, so that beds end in lenses instead of crossing the whole cliff. Set by the pixels and the
// objects' placement before reading the materials.
float BedLenses(float3 q, float cellSize)
{
    const int unitLog = (int)log2(detailOrigin.w);
    float lens = 0.0;
    [unroll]
    for (int k = 0; k < 2; ++k) // octave j has a wavelength of 64 m * 2^-j
    {
        uint3 cell;
        float3 w;
        LatticePoint(q, unitLog - 8 + k, cell, w);
        lens += (k == 0 ? 0.67 : 0.33) * OctaveFade(8.0 - k, log2(cellSize)) * Noise3(cell + 0x4E1Du * (uint)(k + 1), w).x;
    }
    return lens;
}

// The universal rule for a limit on a one-dimensional field (docs/spec-rendu-lointain.md): the mean of
// smoothstep(lo, hi, x) over a pixel where x spreads by sigma (a normal law). The same centre, the half-width
// widened so that the transition's variance gains sigma^2: a smoothstep's slope, as a law, has the variance
// h^2 / 5 for a half-width h.
float SpreadStep(float lo, float hi, float x, float sigma)
{
    const float centre = 0.5 * (lo + hi), half = 0.5 * (hi - lo);
    const float wide = sqrt(half * half + 5.0 * sigma * sigma);
    return smoothstep(centre - wide, centre + wide, x);
}

// The shore (docs/recherche-cotes.md): its bands are heights of water above the sea, so that their widths come from
// the slope, as on real coasts. How the heights spread within a pixel there: those the mesh hides, and the pixel's own,
// its slope times its size, a uniform law (1/12 of the square); never under a millimetre.
float ShoreSpread(float elevationSpread, float slope, float pixel)
{
    const float own = slope * exp2(pixel);
    return sqrt(elevationSpread * elevationSpread + own * own / 12.0 + 1e-6);
}

// The pixel's share above the sea: the waterline sharp near the camera, the pixel's mean further.
float LandShare(float elevation, float sigma)
{
    return SpreadStep(0.0, 0.0, elevation, sigma);
}

// The share of the pixel's land below `top` (m), soft over +-soft: the share of the pixel between the sea and top, over
// its land, since the sea covers the rest (PixelShader.hlsl). Both scale with the coast's exposure to the waves,
// exposure.x; exposure.y, what the pixel cannot show of it, relative, widens the limit in proportion to the height.
float ShoreBelow(float top, float soft, float2 exposure, float elevation, float sigma, float land)
{
    const float spread = sqrt(sigma * sigma + top * top * exposure.y * exposure.y);
    return saturate(1.0 - SpreadStep(exposure.x * (top - soft), exposure.x * (top + soft), elevation, spread) / max(land, 1e-3));
}

static float gBedLens = 0.0;
// The pixels' strata (PixelShader.hlsl): StrataShift and BedLenses, filtered by gStrataCell, the pixel's size, computed only
// where the rock's column needs them, once (docs/optimisation.md, round 2); StrataShift's w raised by gStrataRaise. 0:
// the caller gives them to GroundMaterials.
static float gStrataCell = 0.0;
static float gStrataRaise = 0.0;
static bool gStrataDone = false;
static float4 gStrataShift = 0.0;
float4 PixelStrataShift(float3 q)
{
    [branch]
    if (!gStrataDone)
    {
        gStrataShift = StrataShift(q, gStrataCell);
        gStrataDone = true;
    }
    return gStrataShift;
}
// What the pixel cannot show of the lenses' finer field (GroundMaterials): their thresholds widen by it.
static float gBedLensSigma = 0.0;

// The shade a bedding plane gives the bed under it: keyed by the plane alone, and the lenses' field, so that both
// sides agree. softness: the share of soft beds under such planes; drop: its range (m), how much it shows; lens: the
// range of its threshold against gBedLens. Returns the drop, negative for a soft bed under it.
float PlaneDrop(int name, uint seed, float softness, float2 drop, float2 lens)
{
    const float3 r = 0.5 + 0.5 * LatticeRandom(uint3((uint)name, seed, 0x3A7Fu));
    const float threshold = lerp(lens.x, lens.y, r.z);
    // Most planes barely show; a few stand out (the drop's share cubed).
    return (r.x < softness ? -1.0 : 1.0) * lerp(0.15 * drop.x, drop.y, r.y * r.y * r.y)
         * SpreadStep(threshold - 0.15, threshold + 0.15, gBedLens, gBedLensSigma);
}

// The rock's stratigraphic column at s, its colour factor; ds: s's step from one pixel to the next (m), within which
// nothing must change. Formations of 10 to 60 m come in groups five times thicker, which give them their tint: the
// colours change by great masses, from white to red, each formation only nuanced around its group's
// (STRATA_FORMATION_CONTRAST); each its share of soft beds, and its bedding, from beds of 4 m to beds of 16 m, each
// bed its shade. Colour only: its risers, drawn, traced lines across whole faces (docs/journal-planete.md, 2026-10-24).
float3 StrataColumn(float s, float ds)
{
    const float formationSpacing = 20.0, bedSpacing = 4.0;
    const float2 drop = float2(0.6, 2.0);
    const uint seed = 0x51u;
    const int every = 3; // the thickest formation, in spacings
    const float groupSpacing = 5.0 * formationSpacing;
    if (ds > 0.5 * 3.0 * groupSpacing) // far enough that even the thickest group has faded out
        return 1.0;
    // White, buff, salmon, red, grey, at three quarters of their former contrast: at full, neighbouring groups stood
    // 15 in CIELAB apart, twice the real cliffs' 7 to 10 (docs/journal-planete.md, 2026-10-24).
    const float3 sandstones[5] = { float3(1.3375, 1.315, 1.225), float3(1.1875, 1.075, 0.8875), float3(1.1125, 0.865, 0.715),
                                   float3(1.0, 0.715, 0.5875), float3(0.8875, 0.8875, 0.91) };
    float groupBelow, groupAbove;
    int group, groupNext;
    BeddingPlanes(s, groupSpacing, 0.6, 3, seed + 7u, groupBelow, groupAbove, group, groupNext);
    const float groupPick = 4.0 * (0.5 + 0.5 * LatticeRandom(uint3((uint)group, seed + 8u, 0x2Du)).x);
    const int gi = min((int)groupPick, 3);
    const float groupBlend = smoothstep(0.3, 0.7, groupPick - gi);
    const float3 groupTint = lerp(sandstones[gi], sandstones[gi + 1], groupBlend);
    const float3 groupColor = lerp(1.0, groupTint, 1.0 - smoothstep(0.25, 0.5, ds / (groupAbove - groupBelow)));
    if (ds > 0.5 * every * formationSpacing) // far enough that even the thickest formation has faded out
        return groupColor;
    float formationBelow, formationAbove, bedBelow = -1e9, bedAbove = 1e9;
    int formation, formationNext, bedName = 0, bedNext = 0;
    BeddingPlanes(s, formationSpacing, 0.5, every, seed, formationBelow, formationAbove, formation, formationNext);
    const float3 f = 0.5 + 0.5 * LatticeRandom(uint3((uint)formation, seed + 1u, 0x77u));
    if (ds < 0.5 * 4.0 * bedSpacing) // beds, until even the thickest has faded out
        BeddingPlanes(s, bedSpacing, lerp(0.1, 0.7, f.x), 4, seed + 2u + (uint)formation, bedBelow, bedAbove, bedName, bedNext);
    const bool topIsFormation = formationAbove <= bedAbove;
    const float bottom = max(formationBelow, bedBelow), top = min(formationAbove, bedAbove);
    // Where s's step grows past what the beds' planes allow, their shades fade out; beds die out in lenses.
    const float bedFade = 1.0 - smoothstep(0.075, 0.15, ds / bedSpacing);
    const float dropAbove = topIsFormation ? 0.0 : bedFade * PlaneDrop(bedNext + 4096 * formation, seed + 3u, 0.6 * f.y, drop,
                                                                       float2(-0.6, 0.4));
    // The colours of beds and formations thinner than a few steps fade out, rather than alias.
    const float bedSeen = 1.0 - smoothstep(0.25, 0.5, ds / (top - bottom));
    const float formationSeen = 1.0 - smoothstep(0.25, 0.5, ds / (formationAbove - formationBelow));
    const float pick = 4.0 * f.z;
    const int i = min((int)pick, 3);
    const float blend = smoothstep(0.3, 0.7, pick - i);
    const float contrast = STRATA_FORMATION_CONTRAST;
    const float3 tint = lerp(groupTint, lerp(sandstones[i], sandstones[i + 1], blend), contrast);
    const float3 r = LatticeRandom(uint3((uint)(bedName + 4096 * formation), seed + 5u, 0x19u));
    return lerp(groupColor, tint * (1.0 + 0.1 * contrast * LatticeRandom(uint3((uint)formation, seed + 6u, 0x5u)).x), formationSeen)
         * (1.0 + bedSeen * saturate(abs(dropAbove) / drop.x) * (0.08 * r.x + (dropAbove < 0.0 ? float3(-0.04, -0.08, -0.1) : 0.0)));
}

// a plus t * b, field by field.
Texture AddTexture(Texture a, Texture b, float t)
{
    a.color += t * b.color;
    a.slope += t * b.slope;
    a.cavity += t * b.cavity;
    a.relief += t * b.relief;
    return a;
}

// How far the surface's slope spreads within a mesh cell (docs/spec-rendu-lointain.md): the slopes of the relief's
// octaves the mesh leaves out, log2(cell / DETAIL_MIN_WAVELENGTH) of them, each carrying about the same slope,
// OCTAVE_SLOPE on the mountains, less on gentler terrain (roughness). Measuring that slope on the mesh itself
// failed: a cell of several kilometres sees the continents' gentle bend, not the mountains' octaves.
static const float OCTAVE_SLOPE = 0.16;
float SlopeSpread(float roughness, float cellSize)
{
    return OCTAVE_SLOPE * roughness * sqrt(max(log2(cellSize / DETAIL_MIN_WAVELENGTH), 0.0));
}

// The share of an Fbm3's variance that a pixel of size 2^pixel (m) leaves out: its octaves too fine to show. The octaves
// are shown down to the one whose wavelength crosses pixel + 2, in part, and lost below it: geometric sums of their
// variances, gain^2 per octave, in closed form (docs/optimisation.md, round 2; the loop over the octaves gave the same).
float FbmLostShare(float widest, float finest, float pixel, float gain)
{
    const float unitLog = log2(detailOrigin.w);
    const int first = (int)ceil(unitLog - widest), last = min((int)floor(unitLog - finest), first + 15);
    const int n = last - first + 1, m = clamp((int)floor(unitLog - pixel - 2.0) + 1 - first, 0, max(n, 0)); // m: the first not all shown
    if (m >= n)
        return 0.0;
    const float g = gain * gain, shown = smoothstep(pixel + 1.0, pixel + 2.0, unitLog - (first + m));
    const float gm = pow(g, (float)m), gn = pow(g, (float)n);
    return saturate(((1.0 - shown * shown) * gm * (1.0 - g) + gm * g - gn) / (1.0 - gn)); // never under 0: a root is taken of it
}

// The coast's exposure to the waves, which scales every band of the shore, for the sea to share: of mean 1 and deviation
// 0.41, from the local noise's y, Fbm3(q, log2(8000.0), 0.0, pixel, 0.62, 23u) (GroundMaterials). y: what the pixel cannot
// show of it, relative.
float2 CoastExposure(float localY, float pixel)
{
    return float2(1.0 + 2.8 * localY, 2.8 * 0.146 * sqrt(FbmLostShare(log2(8000.0), 0.0, pixel, 0.62)));
}

// The open water down the coast's slope: three points on the sphere at BEACH_FETCH km, read at a fixed 3 km footprint.
// The map's ground is zero at sea; each point counts as open water as its ground falls from 10 m to 0, never by a
// threshold, which would move the beach's width by a step along the coast. Sheltered coasts keep BEACH.w of the
// exposure. A nearly level surface has no reliable offshore direction and keeps the full exposure.
float CoastFetch(float3 normalPlanet, float3 upPlanet)
{
    const float3 down = normalPlanet - dot(normalPlanet, upPlanet) * upPlanet;
    const float downSquared = dot(down, down);
    float fetch = 1.0;
    [branch]
    if (downSquared > 1e-8)
    {
        const float3 offshore = down * rsqrt(downSquared);
        float openWater = 0.0;
        [unroll]
        for (int i = 0; i < 3; ++i)
        {
            const float angle = BEACH_FETCH[i] / PLANET_RADIUS_KM;
            const float3 direction = normalize(cos(angle) * upPlanet + sin(angle) * offshore);
            const float ground = planetMap.SampleLevel(materialSampler, direction, MapLevel(direction, 3000.0)).x;
            openWater += 1.0 - smoothstep(0.0, 10.0, ground);
        }
        fetch = lerp(BEACH.w, 1.0, openWater / 3.0);
    }
    return fetch;
}

// The mean of smoothstep(lo, hi, |s|) over a pixel whose slope vector s (tangent of the slope angle) has the
// magnitude `slope` on average and spreads by `sigma` along each axis (docs/spec-rendu-lointain.md). Rock,
// scree and snow are decided on the slope; far away, a pixel holds slopes far steeper than its mean, and this
// is the share of them past the limit. A stratified polar quadrature: six radii at the middles of six equally
// likely bands of the spread's Rayleigh law, five angles over the half-plane; within 2 % of a Monte Carlo
// reference, where 3 x 3 Gauss-Hermite missed by up to 15 %. With sigma 0, the plain smoothstep.
float2 SlopeShares(float slope, float sigma, float4 limits) // limits: (lo, hi) of two shares
{
    const float angles[5] = { 1.0, 0.70710678, 0.0, -0.70710678, -1.0 }, weights[5] = { 1.0, 2.0, 2.0, 2.0, 1.0 };
    float2 share = 0.0;
    [unroll]
    for (int i = 0; i < 6; ++i)
    {
        const float r = sigma * sqrt(-2.0 * log(1.0 - (i + 0.5) / 6.0));
        [unroll]
        for (int k = 0; k < 5; ++k)
        {
            const float c = angles[k], magnitude = length(float2(slope + r * c, r * sqrt(1.0 - c * c)));
            share += weights[k] * float2(smoothstep(limits.x, limits.y, magnitude), smoothstep(limits.z, limits.w, magnitude));
        }
    }
    return share / 48.0;
}

// SlopeShares for a third limit (lo, hi) on the same slopes, the same quadrature (docs/optimisation.md, round 2).
float3 SlopeShares3(float slope, float sigma, float4 limits, float2 third)
{
    const float angles[5] = { 1.0, 0.70710678, 0.0, -0.70710678, -1.0 }, weights[5] = { 1.0, 2.0, 2.0, 2.0, 1.0 };
    float2 share = 0.0;
    float shareThird = 0.0;
    [unroll]
    for (int i = 0; i < 6; ++i)
    {
        const float r = sigma * sqrt(-2.0 * log(1.0 - (i + 0.5) / 6.0));
        [unroll]
        for (int k = 0; k < 5; ++k)
        {
            const float c = angles[k], magnitude = length(float2(slope + r * c, r * sqrt(1.0 - c * c)));
            share += weights[k] * float2(smoothstep(limits.x, limits.y, magnitude), smoothstep(limits.z, limits.w, magnitude));
            shareThird += weights[k] * smoothstep(third.x, third.y, magnitude);
        }
    }
    return float3(share / 48.0, shareThird / 48.0);
}

// The tangent of the slope angle of a surface of this flatness (cosine of the angle).
float SlopeOf(float flatness)
{
    const float f = clamp(flatness, 0.05, 1.0);
    return sqrt(1.0 - f * f) / f;
}

// The slope vector (tangent of the slope, along the steepest direction) of a surface of normal n under the vertical up.
float3 SlopeVector(float3 n, float3 up)
{
    const float c = max(dot(n, up), 0.05);
    return (n - c * up) / c;
}

// The ledges after the universal rule (docs/spec-rendu-lointain.md): over a pixel whose slope vector is m on
// average, spreading by sigma along each axis, the share of rock (its slope past rockLimits) and, within it, the
// shares flat enough for scree (under ledgeLimits) and soil (under soilLimits) once the rock texture's slope T is
// added, with what the pixel cannot show of that texture's slope, sigmaTex. Returns (rock, ledge, soil ledge), the
// last two shares of the whole pixel. Near the camera, sigma and sigmaTex vanish and this is the per-pixel test;
// far away, where the textures' slopes are lost to the mips, it keeps the ledges' mean instead of losing them all.
// The same polar quadrature as SlopeShares, over the whole circle, since T breaks the symmetry.
float3 RockShares(float2 m, float2 T, float sigma, float sigmaTex, float2 rockLimits, float2 ledgeLimits, float2 soilLimits)
{
    float3 share = 0.0;
    [branch]
    if (sigma < 0.02) // near the camera, the pixel hides no slope worth the quadrature: the point itself
    {
        const float rock = smoothstep(rockLimits.x, rockLimits.y, length(m)), textured = length(m + T);
        return rock * float3(1.0, 1.0 - SpreadStep(ledgeLimits.x, ledgeLimits.y, textured, sigmaTex),
                             1.0 - SpreadStep(soilLimits.x, soilLimits.y, textured, sigmaTex));
    }
    [unroll]
    for (int i = 0; i < 6; ++i)
    {
        const float r = sigma * sqrt(-2.0 * log(1.0 - (i + 0.5) / 6.0));
        [unroll]
        for (int k = 0; k < 8; ++k)
        {
            const float angle = 0.78539816 * k, ca = cos(angle), sa = sin(angle);
            const float2 v = m + r * float2(ca, sa);
            const float rock = smoothstep(rockLimits.x, rockLimits.y, length(v)), textured = length(v + T);
            share += rock * float3(1.0, 1.0 - SpreadStep(ledgeLimits.x, ledgeLimits.y, textured, sigmaTex),
                                   1.0 - SpreadStep(soilLimits.x, soilLimits.y, textured, sigmaTex));
        }
    }
    return share / 48.0;
}

// How far the heights spread within a mesh cell of this size, from the slopes it hides (SlopeSpread): each lost
// octave of wavelength 2 * cell * 2^-k carries the slope OCTAVE_SLOPE * roughness, so a height of that slope times
// its wavelength over 2 pi; summed, 0.37 times the slope times the cell.
float ElevationSpread(float slopeSpread, float cellSize)
{
    const float octaves = log2(cellSize / DETAIL_MIN_WAVELENGTH);
    return octaves > 0.0 ? 0.37 * slopeSpread / sqrt(octaves) * cellSize : 0.0;
}

// The mesh cell (m) at the point, set by the pixels and the objects' placement: the noises computed per vertex, filtered
// to it (Geology), leave out what it hides, which the limits drawn on them must widen by.
static float gCellSize = 0.0;

// The regional noises, 3 000 to 200 km: x and y pick the textures' variants, z the hue. The climate itself is the climate
// map's (Climate.hlsli).
float3 ClimateNoise(float3 q, float pixel)
{
    return Fbm3(q, log2(3.0e6), log2(2.0e5), pixel, 0.5, 11u);
}

// The rain's variation under the climate map's resolution, which carries what is over two of its cells, 100 km: soils,
// the relief's finer slopes, the storms' tracks. A noise of 100 to 6 km, as the relief's detail under the tectonic map,
// of deviation CLIMATE_LOCAL in humidity (x); y, what the pixel cannot show of it, which widens the limits drawn on the
// humidity. Shared by GroundMaterials and the plants' placement.
static const float CLIMATE_LOCAL = 0.08;
float2 LocalRain(float3 q, float pixel)
{
    return CLIMATE_LOCAL / 0.146 * float2(Fbm3(q, log2(1.0e5), log2(6000.0), pixel, 0.6, 41u).x,
                                          0.146 * sqrt(FbmLostShare(log2(1.0e5), log2(6000.0), pixel, 0.6)));
}

// The temperature (C) at a point: the climate map's at sea level (seaLevel, Climate.hlsli), less 5 C per km of altitude,
// colder on slopes facing the pole (poleTilt, the normal's poleward component), and the irregularity of the snow line,
// the detail noise. Shared by GroundMaterials and the plants' placement, which needs it before the materials
// (docs/recherche-vegetation.md).
float Temperature(float seaLevel, float elevation, float poleTilt, float detailX)
{
    return seaLevel - 5.0 * max(elevation, 0.0) / 1000.0 - 8.0 * poleTilt + 4.0 * detailX;
}

// The materials at a point, their textures and weights: shared by the pixels and the objects' placement.
struct Materials
{
    float3 regional, local; // the regional and local noises
    float temperature, humidity;
    float amplitude;        // the seasons' half amplitude (C), the climate map's
    float coldSigma;        // how the temperature spreads within the pixel (C), for the limits drawn on it
    float grassAmount, sandAmount, soilAmount; // the soils' shares: grass, sand and bare soil, the rest
    Texture soil;           // bare soil's texture
    Texture grass, sand, scree, stone;
    float screeWeight, rock, beach, snow;
    float rockAll;          // the rock, its covered ledges included
    float3 textureSlope;    // the textures' slope the pixels light, face-local
    float3 snowColor;       // the snow's detail bands (DetailBands): colour factor of mean 1
    float3 snowSlope;       // and slope, face-local
};

// q: planet point from the anchor; up, normal, shoreNormal: face-local; sinLat: sine of the latitude; poleward: the
// tangent direction towards the nearer pole, face-local; pixel: log2 of the pixel size (m); dqdx, dqdy: q's
// steps from one pixel to the next (or across a mesh cell), for the textures' filtering; slopeSpread: how the
// slope spreads within the mesh cell, elevationSpread how its heights do (m): far away, every limit drawn on
// them becomes the share of the pixel past it; strata: StrataShift, or the pixels' own (PixelStrataShift).
Materials GroundMaterials(float3 q, float elevation, float3 up, float3 normal, float3 shoreNormal, float sinLat, float3 poleward, float pixel,
                          float3 dqdx, float3 dqdy, float slopeSpread, float elevationSpread, float4 strata)
{
    const float3 regional = ClimateNoise(q, pixel);                              // the textures' variants, the hue
    const float3 upPlanet = up.x * faceX.xyz + up.y * faceY.xyz + up.z * faceZ.xyz;
    const float4 climate = ClimateAt(materialSampler, upPlanet, exp2(pixel));      // the year's rain, temperature, seasons
    const float3 local = Fbm3(q, log2(8000.0), 0.0, pixel, 0.62, 23u);           // snow, rock, brightness
    // The same at every distance (docs/spec-rendu-lointain.md): every limit between materials is a smoothstep
    // on a field, and a pixel shows that smoothstep's mean over what it covers. The limits' irregularity, a noise
    // of 2 km down to the texel, is the same at every distance; what the pixel cannot show of it (detailLost,
    // a deviation) widens the limits instead. x: temperature, y: the slope limits of rock and scree.
    const float3 detailNoise = Fbm3(q, log2(2000.0), 0.0, pixel, 0.62, 31u); // the limits of the snow, the rock, its photos
    const float detailLost = 0.146 * sqrt(FbmLostShare(log2(2000.0), 0.0, pixel, 0.62)); // 0.146: Fbm3's deviation
    // Temperature (C): the climate map's at sea level, altitude, colder on slopes facing the pole, and the irregularity
    // of the snow line, about 0.6 C.
    const float temperature = Temperature(climate.y, elevation, dot(normal, poleward), detailNoise.x);
    // The slopes within the pixel: those of the relief's octaves the mesh and the fine grid leave out, and the
    // spread of the rock limits' noise, about 0.8 in slope per unit (limits of 0.65 to 1.0, moved by 1.5 times it).
    const float slopeSigma = sqrt(slopeSpread * slopeSpread + (1.2 * detailLost) * (1.2 * detailLost));
    // The temperature's spread within the pixel, from every input it has: the snow line's noise the pixel cannot
    // show; the heights it holds, at 5 C per km; and the slopes it holds, which face the pole or away from it, at
    // 4 C per unit of the normal's tilt. Calibrated on the descent bench: the 8 C of the temperature's own pole
    // term overshot on both ranges measured, 0 undershot (docs/spec-rendu-lointain.md).
    const float hiddenTilt = slopeSpread / sqrt(1.0 + slopeSpread * slopeSpread);
    const float coldSigma = sqrt(16.0 * detailLost * detailLost + 2.5e-5 * elevationSpread * elevationSpread
                               + 16.0 * hiddenTilt * hiddenTilt);
    const float limitShift = 1.0 + 1.5 * detailNoise.y;
    // Humidity: the log of the climate map's precipitation, and its variation under the map; the deserts where the
    // circulation and the relief leave them.
    const float2 localRain = LocalRain(q, pixel);
    const float humidity = ClimateHumidity(climate.x, localRain.x);

    // Close-up textures of the materials found here (step D and voie B). Their heights move the borders:
    // sand fills between stones, rock bumps rise through sand, grass tufts and rock through thin snow.
    const float3 normalPlanet = normal.x * faceX.xyz + normal.y * faceY.xyz + normal.z * faceZ.xyz;
    // Rock on steep slopes, the limit varying with the local noise; scree on the slopes just below, and under
    // the rock where it breaks up. Where rock covers everything, no soil textures.
    // Rock past slopes of 0.65 to 1.0 (33 to 45 degrees), scree past 0.43 to 0.75, both limits moved by the noise.
    const float meshSlope = SlopeOf(dot(normal, up));
    // A city earthwork's bank keeps the ground it was cut from: its materials take 40 % of its slope, its light the
    // whole of it (CityGrade.hlsli). A 1:2 bank is soil and grass, not scree.
    const float groundSlope = meshSlope * (1.0 - 0.6 * CityBank(upPlanet, elevation));
    // On the same slopes, the snow's: shed past 1.0 to 1.7 (below).
    const float3 slopeShares = SlopeShares3(groundSlope, slopeSigma, float4(0.65, 1.0, 0.43, 0.75) * limitShift,
                                            float2(1.0, 1.7) * limitShift);
    const float rockBase = slopeShares.x, screeBase = TEXTURE_DETAIL * slopeShares.y;
#ifdef PIXEL_NEAR_DETAIL
    // The face photo's near detail (FACE_WARP, FACE_BANDS), here, before the textures, where few values are live: read
    // with the photos, the same noises cost 0.1 ms at 97 km, in registers, never run. Only the near permutations of the
    // terrain's pixels hold it (PixelShaderNear.hlsl), drawn under NearDetailClearance (D3DApp.h).
    float3 faceShift = 0.0; // q's shift for the face photo (m)
    Texture faceBands = FlatTexture();
    [branch] if (TEXTURE_DETAIL > 0.0 && rockBase > 0.01 && gMaterialTextures > 0.0 && pixel < log2(FACE_WARP.x) - 1.0)
    {
        if (log2(FACE_WARP.x) > pixel + 3.0)
        {
            uint3 cell;
            float3 w;
            LatticePoint(q, (int)round(log2(detailOrigin.w) - log2(FACE_WARP.x)), cell, w);
            faceShift = smoothstep(pixel + 3.0, pixel + 4.0, log2(FACE_WARP.x)) * FACE_WARP.y * NoiseValueGradient(cell + 0x5BD1E995u, w).xyz;
        }
        faceBands = DetailBands(q, pixel, FACE_BANDS.x, FACE_BANDS.y, FACE_BANDS.z, FACE_BANDS.w, 0x51A7u);
    }
#endif
    const float grassAmount = TEXTURE_DETAIL * SpreadStep(0.20, 0.45, humidity, localRain.y) * SpreadStep(-2.0, 6.0, temperature, coldSigma);
    Texture grass = FlatTexture();
    if (grassAmount > 0.01 && rockBase < 0.99 && gMaterialTextures > 0.0)
        grass = WithBands(GrassTexture(q, pixel), DetailBands(q, pixel, GRASS_BANDS.x, GRASS_BANDS.y, GRASS_BANDS.z, GRASS_BANDS.w, 0x6B3Du));
    // Sand: deserts and beaches, its ripples turned by a regional wind.
    // The shore's band (docs/recherche-cotes.md): heights of water up to the berm, scaled by the coast's exposure to
    // the waves (CoastExposure) and the open water offshore (CoastFetch). Each a share of the pixel's land after the
    // universal rule: from the heights it hides and its own, its slope times its size (ShoreSpread).
    // The fetch only near the sea, where a beach can stand: three reads of the planet map, not on every hill.
    const float shoreSigma = ShoreSpread(elevationSpread, meshSlope, pixel);
    const float shoreSlope = SlopeOf(dot(shoreNormal, up));
    float2 exposure = CoastExposure(local.y, pixel);
    [branch]
    if (elevation - 3.0 * shoreSigma < 3.0 * BEACH.x)
    {
        const float3 shorePlanet = shoreNormal.x * faceX.xyz + shoreNormal.y * faceY.xyz + shoreNormal.z * faceZ.xyz;
        exposure *= CoastFetch(shorePlanet, upPlanet);
    }
    const float land = LandShare(elevation, shoreSigma);
    const float beachTop = min(BEACH.x, BEACH.z * shoreSlope);
    // The softness shrinks with the capped height too: a metre of softness alone would span 500 m on a slope of 0.002.
    const float beachSoft = BEACH.y * beachTop / BEACH.x;
    const float beachBand = ShoreBelow(beachTop, beachSoft, exposure, elevation, shoreSigma, land);
    // The slope limit unmoved by the rock limits' noise: that noise's spread, calibrated for limits near 0.8, widened
    // this one fivefold and took two thirds of the beach away far off. The exposure already varies the beach.
    const float beachBase = beachBand * SpreadStep(0.0, 3.0, temperature, coldSigma)
                         * (1.0 - SlopeShares(meshSlope, slopeSpread, float4(BEACH_SLOPE, BEACH_SLOPE)).x);
    const float sandAmount = TEXTURE_DETAIL * max((1.0 - SpreadStep(0.08, 0.30, humidity, localRain.y)) * SpreadStep(0.0, 4.0, temperature, coldSigma),
                                                  beachBase);
    Texture sand = FlatTexture();
    if (sandAmount > 0.01 && rockBase < 0.99 && gMaterialTextures > 0.0)
    {
        sand = GeneratedTexture(MATERIAL_SAND, SAND_TILE, MATERIAL_FINE + MATERIAL_SAND, q, dqdx, dqdy, normalPlanet, upPlanet, 8.0 * regional.z, false);
        const Texture ripples = SandRipples(q, dqdx, dqdy, upPlanet, 8.0 * regional.z);
        sand.color *= ripples.color;
        sand.slope += ripples.slope;
        sand.cavity *= ripples.cavity;
        sand.relief += ripples.relief;
        sand = WithBands(sand, DetailBands(q, pixel, SAND_BANDS.x, SAND_BANDS.y, SAND_BANDS.z, SAND_BANDS.w, 0x2C51u));
    }
    // Bare soil: where it is too dry for grass and too damp or too cold for sand, the rest of the soils. It had no
    // texture at any scale, only the biome's colour: blurred from every distance (docs/spec-texturage-universel.md).
    // The sandy gravel's photo, a desert's stony soil, for its matter, without the sand's ripples; its detail bands.
    const float soilAmount = TEXTURE_DETAIL * saturate(1.0 - grassAmount - sandAmount);
    Texture soil = FlatTexture();
    if (soilAmount > 0.01 && rockBase < 0.99 && gMaterialTextures > 0.0)
        soil = WithBands(GeneratedTexture(MATERIAL_SAND, SAND_TILE, MATERIAL_FINE + MATERIAL_SAND, q, dqdx, dqdy, normalPlanet, upPlanet,
                                          8.0 * regional.z + 1.0, false),
                         DetailBands(q, pixel, SOIL_BANDS.x, SOIL_BANDS.y, SOIL_BANDS.z, SOIL_BANDS.w, 0x4D2Fu));
    Texture scree = FlatTexture();
    if (screeBase > 0.01 && rockBase < 0.99 && gMaterialTextures > 0.0)
        scree = WithBands(GeneratedTexture(MATERIAL_SCREE, SCREE_TILE, MATERIAL_FINE + MATERIAL_SCREE, q, dqdx, dqdy, normalPlanet, upPlanet, 8.0 * regional.x, false),
                          DetailBands(q, pixel, SCREE_BANDS.x, SCREE_BANDS.y, SCREE_BANDS.z, SCREE_BANDS.w, 0x7A19u));
    // The rock: its photos (docs/journal-planete.md, 2026-10-24, one rock), its detail bands, and its stratigraphic
    // column's colour. The column's risers drew lines across whole faces: colour only.
    Texture stone = FlatTexture();
    float3 bedColor = 1.0;
    if (TEXTURE_DETAIL > 0.0 && rockBase > 0.01 && gMaterialTextures > 0.0)
    {
        // The strata colour the rock's texture only: computed here alone (docs/optimisation.md, round 2); the pixels'
        // from the pixel's own (PixelStrataShift).
        if (gStrataCell > 0.0)
            strata = PixelStrataShift(q) + float4(0.0, 0.0, 0.0, gStrataRaise);
        // The beds thicken and thin along the cliff, and pinch out: of one thickness all along, they read as lines drawn
        // on the mountain. s is remapped by two sines of 23 m and 7.3 m whose phases wander over 32 to 256 m; their slopes
        // add up to at most 0.9, so that s keeps climbing and no bed folds back. Each sine fades out as the pixel nears a
        // fifth of its period: past a quarter of the longer one, both are 0, and their phases are not computed.
        const float s = elevation - strata.w, ds = exp2(pixel);
        if (ds < 0.25 * 23.0)
        {
            const float3 phase = 21.5 * Fbm3(q, log2(256.0), log2(32.0), pixel, 0.6, 61u); // about pi, deviation
            strata.w -= 1.65 * (1.0 - smoothstep(0.1, 0.2, ds / 23.0)) * sin(6.2831853 * s / 23.0 + phase.x)
                      + 0.52 * (1.0 - smoothstep(0.1, 0.2, ds / 7.3)) * sin(6.2831853 * s / 7.3 + phase.y);
        }
        const float3 sGradient = upPlanet - strata.xyz;
        // s's step: from the mesh cell, which spans about 13 pixels, in the pixels; screen derivatives jump from one
        // quad of pixels to the next, and the beds' colours, whose widths follow it, would break into zigzags.
        const float step = gMeshCell > 0.0 ? gMeshCell / 13.0 : exp2(pixel);
        const float columnStep = step * length(sGradient);
        // Then the lenses: the planes die out and come back along the cliff over 16 to 128 m, beyond the lenses of the
        // vertices' field; a threshold on a field, widened by what the pixel cannot show of it. They shade the beds
        // only, gone from a step of 0.6 m (StrataColumn): not computed beyond.
        if (columnStep < 0.66)
        {
            if (gStrataCell > 0.0)
                gBedLens = BedLenses(q, gStrataCell);
            gBedLens += 3.0 * Fbm3(q, log2(128.0), log2(16.0), pixel, 0.6, 47u).y;
            gBedLensSigma = 3.0 * 0.146 * sqrt(FbmLostShare(log2(128.0), log2(16.0), pixel, 0.6));
        }
        // A photo has the orientation it was shot in (docs/principes.md): the face photo on the rock steeper than 45
        // degrees, the top-down one on the gentler rock, over 40 to 50 degrees, the limit moved by the noise as the rock's
        // is, so that the two photos meet in patches, not along a contour; the share among the rock's slopes, after the
        // universal rule: the slopes the pixel hides widen the limit. The face photo stays level and unshifted: shifted
        // along the strata, it stretched without end on slopes along them; turned by them, it swirled.
        const float face = saturate(SlopeShares(meshSlope, slopeSigma, float4(0.84, 1.19, 0.84, 1.19) * (1.0 + 1.5 * detailNoise.z)).x / max(rockBase, 1e-4));
        const Texture bands = DetailBands(q, pixel, ROCK_BANDS.x, ROCK_BANDS.y, ROCK_BANDS.z, ROCK_BANDS.w, 0x3E71u);
        stone.color = 0.0; stone.cavity = 0.0;
        if (face > 0.0)
#ifdef PIXEL_NEAR_DETAIL
            stone = AddTexture(stone, WithBands(GeneratedTexture(MATERIAL_ROCK, ROCK_TILE, MATERIAL_FINE + MATERIAL_ROCK, q + faceShift, dqdx,
                                                                 dqdy, normalPlanet, upPlanet, 8.0 * regional.y, true),
                                                WithBands(bands, faceBands)), face);
#else
            stone = AddTexture(stone, WithBands(GeneratedTexture(MATERIAL_ROCK, ROCK_TILE, MATERIAL_FINE + MATERIAL_ROCK, q, dqdx, dqdy,
                                                                 normalPlanet, upPlanet, 8.0 * regional.y, true),
                                                bands), face);
#endif
        if (face < 1.0)
            stone = AddTexture(stone, WithBands(GeneratedTexture(MATERIAL_ROCK_TOP, ROCK_TOP_TILE, MATERIAL_FINE + MATERIAL_ROCK, q,
                                                                 dqdx, dqdy, normalPlanet, upPlanet, 8.0 * regional.y, false),
                                                bands), 1.0 - face);
        bedColor = StrataColumn(elevation - strata.w, columnStep);
    }

    // The borders compare the textures' true heights (m): a ripple of a few millimetres does not uncover the
    // rock in its trough, a rock bump of 20 cm does rise through the sand.
    const float soilRise = (grassAmount * grass.relief + sandAmount * sand.relief + soilAmount * soil.relief) / BLEND_RISE;
    const float screeRise = TEXTURE_DETAIL * scree.relief / BLEND_RISE;
    const float rockRise = TEXTURE_DETAIL * stone.relief / BLEND_RISE;
    const float screeWeight = HeightBlend(screeBase, soilRise - screeRise);
    const float rock = HeightBlend(rockBase, lerp(soilRise, screeRise, screeWeight) - rockRise);
    const float coveredRise = lerp(lerp(soilRise, screeRise, screeWeight), rockRise, rock); // what sand and snow lie on

    const float3 soilSlope = grassAmount * (1.0 - beachBase) * TangentSlope(grass.slope, normal)
                           + sandAmount * TangentSlope(sand.slope, normal) + soilAmount * TangentSlope(soil.slope, normal);
    const float3 stoneSlope = TEXTURE_DETAIL * TangentSlope(stone.slope, normal);
    const float3 textureSlope = lerp(lerp(soilSlope, TEXTURE_DETAIL * TangentSlope(scree.slope, normal), screeWeight),
                                     stoneSlope, rock);
    // Ledges (docs/spec-roche-organique.md, step 1): where the rock's own surface, its texture's slope on the
    // mesh's, levels out, scree covers it, then soil; bare rock keeps to the steep. Only what is seen: the
    // relief and the slope keep the rock's shape, which the cover lies on.
    // Within the rock, the ledges' share after the universal rule (RockShares): from the mesh's slope, the slopes the
    // pixel hides, and the rock texture's slope, explicit near the camera, its lost part (STONE_SLOPE_SIGMA, by the
    // octaves under the pixel, about thirteen of them from 1 cm to 64 m) far away.
    const float3 meshVector = SlopeVector(normal, up), textureVector = SlopeVector(normalize(normal - stoneSlope), up) - meshVector;
    const float meshSlopeLength = length(meshVector);
    const float3 e1 = meshSlopeLength > 1e-4 ? meshVector / meshSlopeLength
                    : normalize(cross(up, abs(up.x) < 0.9 ? float3(1.0, 0.0, 0.0) : float3(0.0, 1.0, 0.0)));
    const float3 e2 = cross(up, e1);
    const float textureLost = saturate((pixel + 1.0 - log2(0.01)) / 13.0);
    float3 shares = float3(1.0, 0.0, 0.0);
    [branch]
    if (rock > 0.001)
        shares = RockShares(float2(meshSlopeLength, 0.0), float2(dot(textureVector, e1), dot(textureVector, e2)), slopeSigma,
                                     STONE_SLOPE_SIGMA * sqrt(textureLost), float2(0.65, 1.0) * limitShift,
                                     float2(SlopeOf(LEDGE_SCREE.y), SlopeOf(LEDGE_SCREE.x)), float2(SlopeOf(LEDGE_SOIL.y), SlopeOf(LEDGE_SOIL.x)));
    const float ledge = rock * shares.y / max(shares.x, 1e-4);
    const float ledgeSoil = rock * shares.z / max(shares.x, 1e-4);

    // Beach near sea level, of varying width.
    const float beach = HeightBlend(beachBase, coveredRise);
    // Snow below -2 C, shed by steep slopes: patches, tongues and outcrops come from the noises above. The terrain's
    // slope alone sheds it: the textures' slopes, added near the camera and faded with the pixel, changed its share by
    // several points over the last few hundred metres, less on gentle slopes, more on steep rock (docs/journal-planete.md,
    // 2026-10-24).
    const float snow = HeightBlend((1.0 - SpreadStep(-3.0, -1.0, temperature, coldSigma)) * (1.0 - slopeShares.z), coveredRise);

    Materials m;
    m.regional = regional; m.local = local;
    m.temperature = temperature; m.humidity = humidity; m.coldSigma = coldSigma; m.amplitude = climate.z;
    m.grassAmount = grassAmount; m.sandAmount = sandAmount; m.soilAmount = soilAmount; m.soil = soil;
    stone.color *= bedColor;
    m.grass = grass; m.sand = sand; m.scree = scree; m.stone = stone;
    // Seen: the rock less its ledges; scree such that the soil gains what the flattest ledges give it.
    m.rock = rock - ledge;
    m.screeWeight = 1.0 - ((1.0 - rock) * (1.0 - screeWeight) + ledgeSoil) / max(1.0 - m.rock, 1e-4);
    m.beach = beach; m.snow = snow;
    m.rockAll = rock;
    m.textureSlope = textureSlope;
    // The snow's own detail: until now, none at any scale (docs/spec-texturage-universel.md, step 3).
    Texture snowTexture = FlatTexture();
    if (snow > 0.001 && gMaterialTextures > 0.0)
        snowTexture = DetailBands(q, pixel, SNOW_BANDS.x, SNOW_BANDS.y, SNOW_BANDS.z, SNOW_BANDS.w, 0x5A0Bu);
    m.snowColor = snowTexture.color;
    m.snowSlope = TangentSlope(snowTexture.slope, normal);
    return m;
}

// The soils' colour before their textures: the real Earth's reflectances by climate (BiomeColor), linear, brightened
// and darkened at every scale with a regional drift of hue: no two places alike. The Earth's places of a climate differ
// by biome.w in brightness, across continents and soils as much as within a region: the local noise (deviation about
// 0.15) carries half that spread, a quarter of its variance. The pixels' ground and the grass tufts share it.
float3 ClimateColor(Materials m)
{
    const float4 biome = BiomeColor(m.temperature, m.humidity, m.coldSigma);
    return biome.rgb * (1.0 + 0.5 * min(biome.w, 0.6) / 0.15 * m.local.z) * (1.0 + float3(0.4, 0.0, -0.4) * m.regional.z);
}

#endif
