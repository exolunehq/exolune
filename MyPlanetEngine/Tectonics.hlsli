// Tectonics.hlsli - the tectonic map (Tectonics.h; docs/spec-relief-tectonique.md): a body's continents, plates and
// boundaries as fields on a cube fixed on it, computed once per seed at startup. A texture array, three slices per face,
// array slice face * 3 + slice; each face padded by TECTONIC_PAD texels with the fields beyond its edges:
// - slice 0, the large forms (Relief.hlsli): x the elevation (m); y the relief left to the noise (m); z its youth, 1 on a
//   young chain, 0 on old or worn ground; w the strata, > 0 flat-lying on a platform, < 0 soft sediments.
// - slice 1, the boundaries' sharp profiles: x the distance to the nearest plate boundary (km); y a trench's depth there
//   (m); z a ridge's or a rift's axial relief (m), < 0 a valley; w a transform's trough (m).
// - slice 2: x the distance to the boundary signed by the plates' order, within 300 km, for a transform's offset; y the
//   distance to the boundary smoothed over 40 km, along whose level lines the chains stretch (km); then two classes,
//   read at the nearest texel: z the rock
//   (Tectonics::Rock) + 8 on continental crust; w the plate + 32 x the nearest boundary's type (Tectonics::Boundary) + 256
//   where the plate goes under it.
// - slice 3, for the views, in a second array at a quarter of the resolution, one slice per face, padded by
//   TECTONIC_VIEW_PAD: x the ocean floor's age (Ma); y the distance to the continent's edge (km), + on continental crust,
//   within 2 000 km; z the uplift (mm/yr); w the distance to the nearest ancient suture (km). The CPU port reads it
//   at full resolution, with slice 4, the erodibility, from the engine's file.
// Read as a cubic B-spline, continuous to its second derivative, on each face; near an edge the faces' readings blend
// (TectonicFields). The CPU port: tools/hydro/cp.py.
#ifndef TECTONICS_HLSLI
#define TECTONICS_HLSLI
#include "PlanetSettings.hlsli"

Texture2DArray<float4> tectonicMap : register(t18);
Texture2DArray<float4> tectonicViews : register(t19);
static const int TECTONIC_PAD = 4;
static const uint TECTONIC_SLICES = 3;
static const int TECTONIC_VIEW_PAD = 1;
// The band, in texels, over which a face's reading fades out past its edge.
static const float TECTONIC_BLEND = 1.5;

// Each face's normal and its texel axes, D3D's cube map layout: the face's point (s, t) is the direction n + s es + t et.
static const float3 TECTONIC_N[6] = { float3(1, 0, 0), float3(-1, 0, 0), float3(0, 1, 0), float3(0, -1, 0), float3(0, 0, 1), float3(0, 0, -1) };
static const float3 TECTONIC_S[6] = { float3(0, 0, -1), float3(0, 0, 1), float3(1, 0, 0), float3(1, 0, 0), float3(1, 0, 0), float3(-1, 0, 0) };
static const float3 TECTONIC_T[6] = { float3(0, -1, 0), float3(0, -1, 0), float3(0, 0, 1), float3(0, 0, -1), float3(0, -1, 0), float3(0, -1, 0) };

// The map's fields used by the relief: slices 0 to 2; on the sphere, per radian, the gradients of the elevation of the
// large forms, slice 0's x, and of slice 2's x and y. `along`, slice 2's y again in doubles: hundreds of km in a float
// went by steps of a few cm, which the chains' lift and folds made into walls every half metre near the ground.
struct TectonicSample
{
    float4 forms, sharp, side;
    float3 formsGradient, sideGradient, orientationGradient;
    double along;
    float erodibility; // The rock converted per texel before interpolation, never an interpolated class.
};

uint TectonicSize()
{
    uint width, height, layers;
    tectonicMap.GetDimensions(width, height, layers);
    return width - 2 * TECTONIC_PAD;
}

// The cubic B-spline's four weights at the fraction f, and their derivatives.
void TectonicWeights(float f, out float4 w, out float4 dw)
{
    const float g = 1.0 - f, f2 = f * f;
    w = float4(g * g * g, 3.0 * f2 * f - 6.0 * f2 + 4.0, -3.0 * f2 * f + 3.0 * f2 + 3.0 * f + 1.0, f2 * f) / 6.0;
    dw = float4(-g * g, 3.0 * f2 - 4.0 * f, -3.0 * f2 + 2.0 * f + 1.0, f2) * 0.5;
}

// The same weights in doubles.
double4 TectonicWeightsD(double f)
{
    const double g = 1.0 - f, f2 = f * f;
    return double4(g * g * g, 3.0 * f2 * f - 6.0 * f2 + 4.0, -3.0 * f2 * f + 3.0 * f2 + 3.0 * f + 1.0, f2 * f)
         * 0.16666666666666666;
}

// The fields at q on face `face`, its own texels only: q's texel coordinates in doubles, so that a point moves its reading
// by a fraction of a millimetre; 1 / m in a float, refined by a Newton step in doubles, since doubles do not divide.
TectonicSample TectonicFace(double3 q, uint face, uint n)
{
    // q along the face's normal and its texel axes (TECTONIC_N, _S, _T), written out: their entries are 0 and +-1.
    const uint axis = face / 2;
    const double sign = (face & 1) ? -1.0 : 1.0;
    const double m = sign * (axis == 0 ? q.x : axis == 1 ? q.y : q.z);
    const double u = face == 0 ? -q.z : face == 1 ? q.z : face == 5 ? -q.x : q.x;
    const double v = face == 2 ? q.z : face == 3 ? -q.z : -q.y;
    double r = (double)(1.0 / (float)m);
    r = r * (2.0 - m * r);
    const double half = 0.5 * (double)n;
    const double x = (u * r + 1.0) * half - 0.5 + (double)TECTONIC_PAD;
    const double y = (v * r + 1.0) * half - 0.5 + (double)TECTONIC_PAD;
    const float2 c = floor(float2((float)x, (float)y));
    const float2 f = float2((float)(x - (double)c.x), (float)(y - (double)c.y));
    float4 wx, wy, dx, dy;
    TectonicWeights(f.x, wx, dx);
    TectonicWeights(f.y, wy, dy);
    const double4 wxd = TectonicWeightsD(x - (double)c.x), wyd = TectonicWeightsD(y - (double)c.y);
    const int2 origin = (int2)c - 1;
    const uint layer = face * TECTONIC_SLICES;
    TectonicSample s = (TectonicSample)0;
    float2 formsGradient = 0.0, gradient = 0.0, orientationGradient = 0.0;
    [unroll] for (int j = 0; j < 4; ++j)
    {
        float4 forms = 0.0, sharp = 0.0, side = 0.0, sideDx = 0.0;
        float formsDx = 0.0;
        double along = 0.0;
        [unroll] for (int i = 0; i < 4; ++i)
        {
            const int2 at = origin + int2(i, j);
            const float4 f = tectonicMap.Load(int4(at, layer, 0));
            forms += wx[i] * f;
            formsDx += dx[i] * f.x;
            sharp += wx[i] * tectonicMap.Load(int4(at, layer + 1, 0));
            const float4 v = tectonicMap.Load(int4(at, layer + 2, 0));
            // Tectonics.cpp's relative resistance, with soft strata up to twice as erodible. Converting the class
            // before the spline keeps the coast continuous across rocks and cube faces; no fourth GPU slice is needed.
            const float resistance[6] = { 1.0, 0.6, 1.0, 1.6, 0.45, 0.25 };
            const uint rock = min(((uint)(v.z + 0.5)) % 8u, 5u);
            s.erodibility += wy[j] * wx[i] * resistance[rock] * (1.0 + saturate(-f.w));
            side += wx[i] * v;
            sideDx += dx[i] * v;
            along += wxd[i] * (double)v.y;
        }
        s.forms += wy[j] * forms;
        s.sharp += wy[j] * sharp;
        s.side += wy[j] * side;
        s.along += wyd[j] * along;
        formsGradient += float2(wy[j] * formsDx, dy[j] * forms.x);
        gradient += float2(wy[j] * sideDx.x, dy[j] * side.x);
        orientationGradient += float2(wy[j] * sideDx.y, dy[j] * side.y);
    }
    // Per unit of s and t: n / 2 texels; on the sphere, about the same per radian near the face's centre.
    const float perRadian = 0.5 * (float)n;
    s.formsGradient = (formsGradient.x * TECTONIC_S[face] + formsGradient.y * TECTONIC_T[face]) * perRadian;
    s.sideGradient = (gradient.x * TECTONIC_S[face] + gradient.y * TECTONIC_T[face]) * perRadian;
    s.orientationGradient = (orientationGradient.x * TECTONIC_S[face] + orientationGradient.y * TECTONIC_T[face]) * perRadian;
    return s;
}

// The fields at the direction q, not necessarily normalised: the face that holds q, blended near its edges with the next
// faces, each read on its own texels, by weights that only depend on q: continuous across the cube's edges and corners.
TectonicSample TectonicFields(double3 q)
{
    const uint n = TectonicSize();
    const float3 f = (float3)q, a = abs(f);
    const uint axis = a.x >= a.y && a.x >= a.z ? 0 : a.y >= a.z ? 1 : 2;
    const float largest = a[axis], from = 1.0 - 2.0 * TECTONIC_BLEND / (float)n;
    TectonicSample sum = TectonicFace(q, 2 * axis + (f[axis] < 0.0 ? 1 : 0), n);
    float total = 1.0, alongShift = 0.0; // `along`: the other faces' small differences, so that a float can carry them
    const double along = sum.along;
    [unroll] for (uint k = 1; k < 3; ++k)
    {
        const uint other = (axis + k) % 3;
        const float w = smoothstep(from, 1.0, a[other] / largest);
        [branch] if (w > 0.0)
        {
            const TectonicSample s = TectonicFace(q, 2 * other + (f[other] < 0.0 ? 1 : 0), n);
            sum.forms += w * s.forms;
            sum.sharp += w * s.sharp;
            sum.side += w * s.side;
            sum.erodibility += w * s.erodibility;
            sum.formsGradient += w * s.formsGradient;
            sum.sideGradient += w * s.sideGradient;
            sum.orientationGradient += w * s.orientationGradient;
            alongShift += w * (float)(s.along - along);
            total += w;
        }
    }
    sum.along = along + (double)(alongShift / total);
    sum.forms /= total;
    sum.sharp /= total;
    sum.side /= total;
    sum.erodibility /= total;
    sum.formsGradient /= total;
    sum.sideGradient /= total;
    sum.orientationGradient /= total;
    return sum;
}

// ---------------------------------------------------------------------------------------------
// The diagnostic views (MYPLANETENGINE_VIEW, Settings.cpp), in this order from here: plates, boundaries, boundarydist,
// crustage, rocktype, uplift; then relief.
// ---------------------------------------------------------------------------------------------
static const float TECTONIC_VIEW = 35.0;
// The relief's view, after the map's: hypsometric tints and the sun's light, the sea floor included (PixelShader.hlsl).
static const float TECTONIC_RELIEF_VIEW = 41.0;

// The relief's tints, sRGB, by elevation (m): the sea floor from navy at -10 km to pale at the shore; the land green,
// tan, brown, grey, white over 6 km.
float3 ReliefTint(float e)
{
    const float shallow = saturate(1.0 + e / 10000.0);
    if (e < 0.0)
        return lerp(float3(0.02, 0.05, 0.25), float3(0.45, 0.75, 0.95), shallow * shallow * shallow);
    const float3 tints[6] = { float3(0.25, 0.5, 0.25), float3(0.55, 0.65, 0.35), float3(0.8, 0.7, 0.45),
                              float3(0.6, 0.45, 0.3), float3(0.6, 0.58, 0.56), float3(1.0, 1.0, 1.0) };
    const float x = saturate(e / 6500.0) * 5.0;
    const uint k = min((uint)x, 4u);
    return lerp(tints[k], tints[k + 1], x - k);
}

float3 TectonicHue(float h)
{
    return saturate(abs(frac(h + float3(0.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0);
}

// A slice's texel nearest to the unit direction d, and the bilinear mean around it, on the face that holds d; slice 3 from
// the views' array.
float4 TectonicTexel(float3 d, uint slice, bool nearest)
{
    const bool views = slice == 3;
    uint width, height, layers;
    if (views) tectonicViews.GetDimensions(width, height, layers);
    else tectonicMap.GetDimensions(width, height, layers);
    const int pad = views ? TECTONIC_VIEW_PAD : TECTONIC_PAD;
    const uint n = width - 2 * pad;
    const float3 a = abs(d);
    const uint axis = a.x >= a.y && a.x >= a.z ? 0 : a.y >= a.z ? 1 : 2;
    const uint face = 2 * axis + (d[axis] < 0.0 ? 1 : 0);
    const float m = dot(d, TECTONIC_N[face]);
    const float2 x = (float2(dot(d, TECTONIC_S[face]), dot(d, TECTONIC_T[face])) / m + 1.0) * 0.5 * n - 0.5 + pad;
    const uint layer = views ? face : face * TECTONIC_SLICES + slice;
    if (nearest)
        return tectonicMap.Load(int4(int2(floor(x + 0.5)), layer, 0));
    const float2 c = floor(x), u = x - c;
    const int2 i = (int2)c;
    float4 t[4];
    [unroll] for (int k = 0; k < 4; ++k)
    {
        const int4 at = int4(i + int2(k & 1, k >> 1), layer, 0);
        t[k] = views ? tectonicViews.Load(at) : tectonicMap.Load(at);
    }
    return lerp(lerp(t[0], t[1], u.x), lerp(t[2], t[3], u.x), u.y);
}

// The view's colour, sRGB, at the unit direction d for a pixel of `footprint` km; the classes in steps of 20 km seen
// from near.
float3 TectonicColour(float view, float3 d, float footprint)
{
    const float4 sharp = TectonicTexel(d, 1, false), side = TectonicTexel(d, 2, false), info = TectonicTexel(d, 3, false);
    const float4 classes = TectonicTexel(d, 2, true);
    const uint rock = (uint)(classes.z + 0.5), code = (uint)(classes.w + 0.5);
    const bool continental = rock >= 8, under = code >= 256;
    const uint plate = code % 32, type = code / 32 % 8;
    const float stroke = max(1.5 * footprint, 15.0); // a line's half-width (km), two pixels at least
    float3 c;
    if (view < TECTONIC_VIEW + 0.5) // each plate its colour, darker on the oceans; the plates' boundaries in black, the
    {                               // continents' edges in white
        c = lerp(0.5, TectonicHue(frac(plate * 0.618 + 0.1)), 0.6) * (continental ? 1.0 : 0.55);
        if (abs(info.y) < 0.6 * stroke)
            c = 1.0;
        if (sharp.x < stroke)
            c = 0.0;
    }
    else if (view < TECTONIC_VIEW + 1.5) // the nearest boundary's type, half as bright on the plate that goes under it;
    {                                    // the sutures in brown
        const float3 types[6] = { float3(0.95, 0.15, 0.1), float3(1.0, 0.6, 0.0), float3(0.85, 0.2, 0.85),
                                  float3(0.1, 0.8, 0.95), float3(1.0, 0.95, 0.2), float3(0.3, 0.85, 0.3) };
        const float w = saturate(1.0 - sharp.x / 250.0);
        c = lerp(continental ? 0.62 : 0.22, types[min(type, 5u)] * (under ? 0.5 : 1.0), w * w);
        if (continental && info.w < stroke)
            c = float3(0.45, 0.3, 0.15);
    }
    else if (view < TECTONIC_VIEW + 2.5) // the distance to the continents' edge up to 2 000 km, orange on continental
    {                                    // crust, blue on oceanic; a line every 250 km
        const float t = saturate(abs(info.y) / 2000.0);
        c = lerp(1.0, info.y > 0.0 ? float3(0.8, 0.4, 0.0) : float3(0.0, 0.35, 0.9), t);
        if (abs(abs(info.y) - 250.0 * round(abs(info.y) / 250.0)) < 0.5 * stroke)
            c *= 0.4;
    }
    else if (view < TECTONIC_VIEW + 3.5) // the ocean floor's age, red at the ridges to violet at 200 Ma; on the
    {                                    // continents, the old chains along the sutures, brown
        c = continental ? 0.7.xxx : TectonicHue(0.75 * saturate(info.x / 200.0)) * 0.9 + 0.05;
        if (continental && info.w < 60.0)
            c = lerp(float3(0.45, 0.3, 0.15), 0.7.xxx, saturate(info.w / 60.0));
    }
    else if (view < TECTONIC_VIEW + 4.5) // the rock: oceanic crust, volcanic, young chains, sediments, old belts, shields
    {
        const float3 rocks[6] = { float3(0.15, 0.2, 0.35), float3(0.85, 0.2, 0.15), float3(0.6, 0.35, 0.2),
                                  float3(0.85, 0.78, 0.5), float3(0.45, 0.55, 0.3), float3(0.85, 0.55, 0.7) };
        c = rocks[min(rock % 8, 5u)];
    }
    else // the uplift, orange up to 6 mm/yr, blue down to -6, its root to show the weak
    {
        const float u = sign(info.z) * sqrt(saturate(abs(info.z) / 6.0));
        c = lerp(continental ? 0.45 : 0.15, u > 0.0 ? float3(1.0, 0.35, 0.05) : float3(0.1, 0.4, 1.0), abs(u));
    }
    return c;
}

#endif
