#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "Materials.hlsli"
#include "Shadows.hlsli"
#include "Objects.hlsli"
#include "Vegetation.hlsli"
#include "Sea.hlsli"
#define RELIEF_PIXEL
#include "Relief.hlsli"

// The colours below are reflectances written in sRGB, as picked on screen: converted to linear light.
float3 SrgbToLinear(float3 c)
{
    return c <= 0.04045 ? c / 12.92 : pow((c + 0.055) / 1.055, 2.4);
}

#include "Tectonics.hlsli"

// ---------------------------------------------------------------------------------------------
// Spline normals (docs/spec-normales-spline.md): the cubic B-spline surface through the vertices, from the
// positions of the 4 x 4 nearest ones. It does not depend on where the sliding vertices fall.
// ---------------------------------------------------------------------------------------------

StructuredBuffer<FaceVertex> splineVertices : register(t4); // the mesh's vertices, the vertex shader's

// Weights of the four coefficients at offsets -1 to 2 from a cell's first vertex, at the fraction t of the
// cell; and their derivatives along the cell.
float4 SplineWeights(float t)
{
    const float s = 1.0 - t;
    return float4(s * s * s, (3.0 * t - 6.0) * t * t + 4.0, ((-3.0 * t + 3.0) * t + 3.0) * t + 1.0, t * t * t) / 6.0;
}

float4 SplineSlopes(float t)
{
    const float s = 1.0 - t;
    return float4(-s * s, (3.0 * t - 4.0) * t, (-3.0 * t + 2.0) * t + 1.0, t * t) * 0.5;
}

// The spline surface's normal at the pixel's chart coordinates, its elevation for the materials, and their
// weight against the vertex values: 0 within 3 cells of a chart's edge or of a ring's corner, 1 beyond 5,
// and 0 on the triangles between the face and the first ring, which mix both charts.
float3 SplineNormal(float3 chart, float corner, float3 up, out float3 surface, out float elevation, out float weight)
{
    const uint n = (uint)faceParams.w, ringCount = (uint)ringParams.x;
    const bool rings = chart.z > 0.999;
    weight = 0.0;
    elevation = 0.0;
    surface = 0.0;
    if (SPLINE_NORMALS <= 0.0 || (chart.z > 0.001 && !rings))
        return up;
    const float edge = rings ? min(corner, min(chart.y - 1.0, ringCount - chart.y))
                             : min(min(chart.x, chart.y), min(n - chart.x, n - chart.y));
    weight = SPLINE_NORMALS * saturate((edge - 3.0) * 0.5);
    if (weight <= 0.0)
        return up;

    const float2 cell = floor(chart.xy), t = chart.xy - cell;
    const float4 wu = SplineWeights(t.x), wv = SplineWeights(t.y), su = SplineSlopes(t.x), sv = SplineSlopes(t.y);
    float3 du = 0.0, dv = 0.0; // derivatives along the chart's two axes
    [unroll]
    for (int y = 0; y < 4; ++y)
    {
        float3 row = 0.0, rowSlope = 0.0;
        float rowElevation = 0.0;
        const int v = (int)cell.y + y - 1;
        [unroll]
        for (int x = 0; x < 4; ++x)
        {
            const int u = (int)cell.x + x - 1;
            const uint id = rings ? (n + 1) * (n + 1) + (uint)(clamp(v, 1, (int)ringCount) - 1) * 4 * n + (uint)(u + 4 * n) % (4 * n)
                                  : (uint)clamp(v, 0, (int)n) * (n + 1) + (uint)clamp(u, 0, (int)n);
            const FaceVertex c = splineVertices[id];
            row += wu[x] * c.pos;
            rowSlope += su[x] * c.pos;
            rowElevation += wu[x] * c.elevation;
        }
        du += wv[y] * rowSlope;
        dv += sv[y] * row;
        surface += wv[y] * row;
        elevation += wv[y] * rowElevation;
    }
    float3 normal = cross(du, dv);
    const float length2 = dot(normal, normal);
    if ((asuint(length2) & 0x7fffffffu) >= 0x7f800000u || !(length2 > 0.0)) // a culled vertex (NaN) was read
    {
        weight = 0.0;
        return up;
    }
    normal *= rsqrt(length2);
    return dot(normal, up) < 0.0 ? -normal : normal;
}

// ---------------------------------------------------------------------------------------------
// Materials (docs/log/spec-rendu.md, step C): a simple climate picks the ground, noises break every border.
// ---------------------------------------------------------------------------------------------

struct Ground
{
    float3 albedo;      // linear reflectance
    float  detailScale; // fine detail of the normal: stronger on rock, softer on snow and sand
    float3 slope;       // the close-up textures' slope, face-local, in the plane of the surface
    float  cavity;      // factor on the sky's light
    float  diagnostic;  // the weight the diagnostic view shows (MYPLANETENGINE_VIEW), 0 to 1
    float  under;       // the share of the ground under the plants' crowns: their shade on it
    float  canopy;      // the share of the pixel the canopy beyond the objects covers, seen from the camera
    float  nearer;      // how much nearer the camera than the ground the canopy is met, on average over the pixel (m)
    float3 canopyAlbedo;
};

// The view of the pixel, for the plants the objects draw (Vegetation.hlsli): its distance (m), its angle (rad), the
// cosine of its ray to the vertical. Set by PSMain.
static float3 gPlantView = float3(0.0, 1.0, 1.0);
static float3 gRay = float3(0.0, 0.0, -1.0); // the view ray, face-local

// q: planet point from the anchor; up, normal, shoreNormal: face-local; sinLat: sine of the latitude; poleward: the
// tangent direction towards the nearer pole, face-local; pixel: log2 of the pixel size (m).
Ground GroundAt(float3 q, float elevation, float3 up, float3 normal, float3 shoreNormal, float sinLat, float3 poleward, float pixel,
               float3 dqdx, float3 dqdy, float3 geology, float volcanic, float slopeSpread, float elevationSpread,
               float cellSize, float footprint)
{
    const Materials m = GroundMaterials(q, elevation, up, normal, shoreNormal, sinLat, poleward, pixel, dqdx, dqdy, slopeSpread,
                                        elevationSpread, 0.0); // gMesh* and gStrata* set by PSMain

    // Vegetation (docs/recherche-vegetation.md): the plants' canopy over the open land, below.
    Vegetation v = VegetationAt(m.temperature, m.humidity, m.coldSigma, m.amplitude, Exposure(PlanetDirection(up), elevation));
    v.able = PlantGround(m);
    // Where neither trees nor shrubs can grow, nor root, their fields change nothing (TreesHere, ShrubsHere): not computed.
    [branch]
    if (v.able > 0.0 && (v.trees > 0.0 || v.shrubs * v.shrubCold > 0.0))
        WoodsAt(q, pixel, v);
    float3 color = ClimateColor(m);
    color *= lerp(1.0, m.grass.color, m.grassAmount) * lerp(1.0, m.sand.color, m.sandAmount) * lerp(1.0, m.soil.color, m.soilAmount);
    // On fresh volcanic ground (Volcanoes.hlsli), the soil gives way to ash and scoria, dark grey, under their textures.
    const float3 ash = VOLCANIC_ASH * lerp(1.0, m.sand.color, m.sandAmount) * lerp(1.0, m.soil.color, m.soilAmount);
    color = lerp(color, ash, VOLCANIC_COVER * volcanic);

    float3 rockColor = RockColor(geology, m.humidity) * (1.0 + 0.7 * m.local.z);
    color = lerp(color, 1.15 * rockColor * lerp(1.0, m.scree.color, TEXTURE_DETAIL), m.screeWeight);
    color = lerp(color, rockColor * lerp(1.0, m.stone.color, TEXTURE_DETAIL), m.rock);

    color = lerp(color, lerp(float3(0.50, 0.42, 0.30), VOLCANIC_ASH, volcanic) * lerp(1.0, m.sand.color, m.sandAmount), m.beach); // beach, black on lava
    color = lerp(color, float3(0.85, 0.86, 0.90) * m.snowColor, m.snow);
    // The canopy the objects do not draw, the trees' in their stands and the shrubs' in the open, a Boolean canopy: of the
    // footprint -log(1 - cover), the share not drawn; the ground under a drawn crown is hidden by it anyway; seen from the
    // side, more crowns hide the ground. The trees stand at their height (docs/recherche-vegetation.md, v3): the crowns of
    // those not drawn, as high as they are (PlantsDrawn), which the view ray crosses before it meets the ground at q. Three
    // slabs of crowns, each with the share of the woods near its own foot, seen at its distance from q (the universal rule):
    // a forest's edge stands as a wall, hides the clearing behind it, and the crowns move with the parallax of their
    // height, as the plants that take over from them, whole, do. The shrubs, low, at q.
    const float trees = TreesHere(v), shrubs = ShrubsHere(v);
    float3 slabs = 0.0, depth = 0.0, shrubSlabs = SHRUB_HEIGHT, shrubDepth;
    const bool wooded = v.trees * v.cold * v.able > 0.0;
    const float treesDrawn = wooded ? PlantsDrawn(v.height, gPlantView.x, gPlantView.y, cellSize, slabs, depth) : 0.0;
    const float shrubsDrawn = shrubs > 0.0 ? PlantsDrawn(SHRUB_HEIGHT, gPlantView.x, gPlantView.y, cellSize, shrubSlabs, shrubDepth) : 0.0;
    shrubSlabs *= ShrubClimateMeanHeight(ShrubClimate(v, m.temperature));
    const float shrubsFar = 1.0 - pow(saturate(1.0 - shrubs), 1.0 - shrubsDrawn);
    const float seenAngle = max(gPlantView.z, 0.2), rayAngle = max(gPlantView.z, 0.05);
    const float3 ray = gRay.x * faceX.xyz + gRay.y * faceY.xyz + gRay.z * faceZ.xyz; // planet frame, as q
    const float3 level = (ray + gPlantView.z * (up.x * faceX.xyz + up.y * faceY.xyz + up.z * faceZ.xyz)) / rayAngle; // per m of height
    float treesFar = 0.0, treesThrough = 1.0, hit = 0.0, hitHeight = 0.0;
    float3 hitAt = 0.0;
    if (wooded && treesDrawn < 1.0)
    {
        // The woods at the middle slab's foot, seen at its distance from q; the top slab's the same, the low one's between
        // it and q's. Where the slabs' feet lie within the pixel, q's for all.
        const float shift = slabs.y / rayAngle;
        float middle = trees;
        if (shift > footprint)
        {
            Vegetation slab = v;
            slab.shrubs = 0.0; // the woods only
            WoodsAt(q - level * slabs.y, max(pixel, log2(shift)), slab);
            middle = TreesHere(slab);
        }
        const float3 woods = float3(middle, middle, lerp(trees, middle, slabs.z / max(slabs.y, 1e-3)));
        [unroll]
        for (int i = 0; i < 3; ++i)
        {
            const float z = slabs[i];
            const float3 at = q - level * z;
            const float far = 1.0 - pow(saturate(1.0 - woods[i]), 1.0 - treesDrawn);
            const float through = pow(saturate(1.0 - far), depth[i] / seenAngle);
            const float w = treesThrough * (1.0 - through);
            hit += w;
            hitHeight += w * z;
            hitAt += w * at;
            treesThrough *= through;
            treesFar += far * depth[i];
        }
    }
    const float shrubsThrough = pow(saturate(1.0 - shrubsFar), 1.0 / seenAngle);
    const float canopy = 1.0 - (1.0 - treesFar) * (1.0 - shrubsFar);
    const float canopySeen = 1.0 - treesThrough * shrubsThrough;
    const float canopyHeight = hitHeight + treesThrough * (1.0 - shrubsThrough) * shrubSlabs.y; // seen over the ground
    // The relief is the trees' crowns', 2 to 16 m, where the ray meets them: a thicket of shrubs, low and fine, reads
    // smooth beside a forest.
    Texture crowns = FlatTexture();
    const float tall = treesFar / max(canopy, 1e-6);
    if (canopySeen > 0.0)
        crowns = DetailBands(hit > 1e-4 ? hitAt / hit : q, pixel, 1.0, 4.0, CANOPY_RELIEF.x * tall, CANOPY_RELIEF.y * tall, 0x51C3u);
    const float3 species = float3(treesFar * v.conifer, treesFar * (1.0 - v.conifer), shrubsFar) / max(treesFar + shrubsFar, 1e-6);

    Ground g;
    g.under = PlantCover(trees, shrubs);
    g.canopy = canopySeen;
    g.nearer = hitHeight / rayAngle;
    g.canopyAlbedo = saturate(CanopyColor(m, species, v.aridity) * crowns.color);
    g.albedo = saturate(color);
    g.detailScale = lerp(lerp(1.0, 2.0, m.rock), 0.5, max(m.snow, m.beach));
    g.slope = lerp(m.textureSlope * (1.0 - m.snow) + m.snow * m.snowSlope, TangentSlope(crowns.slope, normal), canopySeen);
    const float cavity = lerp(lerp(lerp(1.0, m.sand.cavity, m.sandAmount) * lerp(1.0, m.soil.cavity, m.soilAmount), lerp(1.0, m.scree.cavity, TEXTURE_DETAIL), m.screeWeight),
                              lerp(1.0, m.stone.cavity, TEXTURE_DETAIL), m.rock);
    g.cavity = lerp(1.0, cavity, 1.0 - m.snow);
    // The diagnostic views, in the order of D3DApp's names: the decisions' weights, before the layers cover
    // each other, and the fields they are made of.
    const float view = taa.y;
    g.diagnostic = view < 1.5 ? m.snow : view < 2.5 ? m.rock : view < 3.5 ? saturate(elevation / 6000.0)
                 : view < 4.5 ? saturate(slopeSpread) : view < 5.5 ? m.screeWeight : view < 6.5 ? m.grassAmount
                 : view < 7.5 ? m.sandAmount : view < 8.5 ? m.beach : view < 9.5 ? smoothstep(0.30, 0.55, m.humidity)
                 : view < 11.5 ? m.rockAll : view > 25.5 ? saturate(gPlantView.x / 4000.0) : view > 24.5 ? saturate(canopyHeight / 64.0)
                 : view > 23.5 ? saturate(elevation / 6000.0) : view > 22.5 ? saturate((v.season + 30.0) / 70.0)
                 : view > 21.5 ? saturate(m.humidity) : view > 20.5 ? saturate((m.temperature + 30.0) / 70.0) : view > 19.5 ? treesFar
                 : view > 18.5 ? BiomeClass(v, m.temperature) / 8.0 : view > 17.5 ? canopy
                 : 0.0; // the objects' view: black ground; the forest's, the canopy; the biome's, its class; the climate's
                        // temperature and growing season, -30 to 40 C, and humidity; the elevation, 0 to 6 km; the height
                        // of the surface seen over the ground, 0 to 64 m, the canopy's; the distance, 0 to 4 km, as is
    return g;
}

StructuredBuffer<FineSample> fineNormals : register(t7); // the fine grid's normals and water (FineNormals.hlsl)

// Reconstruct one cubic height surface from the fine grid, and differentiate that SAME surface for its normal.
// Linear heights and independently interpolated normals exposed the sliding grid in distant mountains: the
// height's slope jumped at every cell border. Positive B-spline weights keep the source height range. Water
// retains its premultiplied four-tap reconstruction and separate physical contour query below.
// Weight fades over the face's last eight cells; no fine grid on rings or culled samples.
float3 FineNormal(float3 chart, out float weight, out float elevation, out float4 inland)
{
    weight = 0.0;
    elevation = 0.0;
    inland = 0.0;
    if (ringParams.z <= 0.0 || chart.z > 0.5)
        return 0.0;
    const float n = faceParams.w;
    const int fineCells = (int)(n * ringParams.w);
    const float2 f = chart.xy * ringParams.w;
    // Clamped both ways: at the face's border the interpolated chart dips a hair below 0, and a root
    // descriptor has no bounds check, so a read out of the buffer would bring the GPU down.
    const int2 c = clamp((int2)floor(f), 0, fineCells - 1);
    const float2 t = saturate(f - c);
    const uint i = c.y * (fineCells + 1) + c.x;
    const FineSample sa = fineNormals[i], sb = fineNormals[i + 1], sd = fineNormals[i + fineCells + 1], se = fineNormals[i + fineCells + 2];
    const float4 a = sa.terrain, b = sb.terrain, d = sd.terrain, e = se.terrain;
    if (dot(a.xyz, a.xyz) * dot(b.xyz, b.xyz) * dot(d.xyz, d.xyz) * dot(e.xyz, e.xyz) == 0.0) // a point off screen
        return 0.0;
    inland = lerp(lerp(sa.inland, sb.inland, t.x), lerp(sd.inland, se.inland, t.x), t.y);
    const float4 wu = SplineWeights(t.x), wv = SplineWeights(t.y), su = SplineSlopes(t.x), sv = SplineSlopes(t.y);
    float height = 0.0;
    float2 slope = 0.0;
    bool valid = true;
    [unroll] for (int y = 0; y < 4; ++y)
    {
        float row = 0.0, rowSlope = 0.0;
        [unroll] for (int x = 0; x < 4; ++x)
        {
            const int2 tap = clamp(c + int2(x - 1, y - 1), 0, fineCells);
            const float4 sample = fineNormals[tap.y * (fineCells + 1) + tap.x].terrain;
            valid = valid && dot(sample.xyz, sample.xyz) > 0.0;
            // Derivative weights sum to zero; subtract a nearby height before accumulating them.
            row += wu[x] * (sample.w - a.w);
            rowSlope += su[x] * (sample.w - a.w);
        }
        height += wv[y] * row;
        slope += float2(wv[y] * rowSlope, sv[y] * row);
    }
    const float4 mixed = lerp(lerp(a, b, t.x), lerp(d, e, t.x), t.y);
    elevation = valid ? a.w + height : mixed.w;
    weight = ringParams.z * saturate(min(min(chart.x, n - chart.x), min(chart.y, n - chart.y)) / 8.0);
    if (!valid) return normalize(mixed.xyz);
    const float fineCell = 2.0 * faceParams.x / fineCells;
    slope /= fineCell;
    const float2 xy = (f / fineCells * 2.0 - 1.0) * faceParams.x;
    const float3 radial = float3(xy, faceParams.y);
    const float radius = length(radial);
    const float3 up = radial / radius;
    const float stretch = (faceParams.y + elevation) / radius;
    const float3 du = stretch * (float3(1.0, 0.0, 0.0) - up.x * up) + slope.x * up;
    const float3 dv = stretch * (float3(0.0, 1.0, 0.0) - up.y * up) + slope.y * up;
    return normalize(cross(du, dv));
}

Texture2D<float> shipSunMap : register(t44); // the ship's own map towards the sun (Ship.h)

// The ship's shadow on the ground and the sea: its map towards the sun, read beyond its sphere along the sun. The sun's
// disc blurs it with the distance behind the ship, its penumbra 0.0093 rad wide: the mean of 16 taps over that disc.
// Some kilometre back the penumbra is as wide as the ship, and the shadow fades out.
float ShipShadowOn(float3 p)
{
    [branch] if (shipSphere.w <= 0.0)
        return 1.0;
    const float4 c = mul(float4(p, 1.0), shipSunShadow);
    const float behind = c.z * 39.9 + 0.1 - 20.0; // m behind the ship's centre (Ship.cpp, LightFrame: 0.1 to 40 m)
    const float2 uv = c.xy * float2(0.5, -0.5) + 0.5;
    if (c.z < 0.0 || behind > 3000.0 || any(abs(uv - 0.5) > 0.5 + 0.00465 * behind / 13.4))
        return 1.0;
    const float radius = max(0.7107 * behind, 1.0); // the penumbra's, in the map's 6.5 mm texels
    float lit = 0.0;
    [loop] for (uint k = 0; k < 16; ++k)
    {
        const float r = sqrt((k + 0.5) / 16.0) * radius, a = k * 2.39996; // Vogel's disc
        const int2 t = int2(uv * 2048.0 + r * float2(cos(a), sin(a)));
        const float depth = all(t >= 0) && all(t < 2048) ? shipSunMap.Load(int3(t, 0)) : 1.0;
        lit += depth < min(c.z, 0.999) - 0.002 ? 0.0 : 1.0;
    }
    return lerp(lit / 16.0, 1.0, smoothstep(1000.0, 3000.0, behind));
}

// sunOut: the light the sun alone gives, for the clouds' shade in the atmosphere pass (Clouds.hlsli, CloudShadeAt).
float4 PSMain(PSInput input, out float4 sunOut : SV_TARGET1) : SV_TARGET
{
    sunOut = 0.0;
    if (lightDir.w > 1.5) // wireframe: bright lines, unlit (screen-space derivatives mean nothing on lines)
        return float4(SrgbToLinear(input.elevation < 0.0 ? float3(0.3, 0.6, 1.0) : float3(0.6, 1.0, 0.5)), 1e-3);

    // Smooth shading from the vertices' normals, plus the fine detail. The faceted normal, from the
    // triangles, is kept to compare (key R): each triangle flickers as its vertices move.
    const float3 up = normalize(input.dir);
    const float3 dpdx = ddx(input.pos), dpdy = ddy(input.pos);
    const float2 seaDx=ddx(input.seaParam),seaDy=ddy(input.seaParam);
    const float footprint = sqrt(max(dot(dpdx, dpdx), dot(dpdy, dpdy))); // pixel size (m)
    // The relief's view (Tectonics.hlsli): the ground and the sea floor in hypsometric tints, lit by the sun over the relief
    // exaggerated with the pixel's size, the water left out: the large forms from orbit, the ocean floor anywhere.
    if (abs(taa.y - TECTONIC_RELIEF_VIEW) < 0.5)
    {
        const float e = input.elevation, exaggeration = clamp(footprint / 300.0, 1.0, 15.0);
        const float3 px = dpdx + up * (exaggeration * ddx(e) - ddx(max(e, 0.0)));
        const float3 py = dpdy + up * (exaggeration * ddy(e) - ddy(max(e, 0.0)));
        float3 n = normalize(cross(py, px));
        n *= dot(n, up) < 0.0 ? -1.0 : 1.0;
        return float4(SrgbToLinear(saturate(ReliefTint(e) * (0.3 + 0.7 * saturate(dot(n, lightDir.xyz))))), 1e-3);
    }
    // The sun's share the relief leaves lit (Shadows.hlsli): its disc above the mesh's horizon, interpolated between the
    // vertices, its mean over the horizons the pixel spans; times what the relief finer than the mesh leaves lit.
    const float horizonSpread = sqrt((ddx(input.horizon) * ddx(input.horizon) + ddy(input.horizon) * ddy(input.horizon)) / 12.0);
    const float sunShare = SunAboveHorizon(dot(up, lightDir.xyz), input.horizon, horizonSpread)
                         * FinerReliefLit(dot(normalize(input.normal), lightDir.xyz), input.slopeSpread)
                         * ShipShadowOn(input.pos);
    float3 splineSurface;
    float splineElevation, splineWeight;
    const float3 splineNormal = SplineNormal(input.chart, input.corner, up, splineSurface, splineElevation, splineWeight);
    float fineWeight, fineElevation;
    float4 fineInland;
    const float3 fineNormal = FineNormal(input.chart, fineWeight, fineElevation, fineInland);
    // The fine grid lights the ground from face cells of FINE_LIGHT_MIN_CELL; the materials are decided on it further down.
    const float lightWeight = fineWeight * smoothstep(FINE_LIGHT_MIN_CELL, 2.0 * FINE_LIGHT_MIN_CELL, 2.0 * faceParams.x / faceParams.w);
    const float3 vertexNormal = normalize(lerp(normalize(lerp(normalize(input.normal), splineNormal, splineWeight)), fineNormal,
                                               lightWeight));
    // The grain starts below the lighting's cells, and fewer slopes hide within them.
    const float cellSize = input.cellSize / lerp(1.0, ringParams.w, lightWeight);
    const float slopeSpread = input.slopeSpread * sqrt(max(log2(cellSize / DETAIL_MIN_WAVELENGTH), 0.0)
                                                       / max(log2(input.cellSize / DETAIL_MIN_WAVELENGTH), 1e-3));
    float elevation = lerp(lerp(input.elevation, splineElevation, splineWeight), fineElevation, fineWeight);
    const float4 inlandSample = lerp(input.inland, fineInland, fineWeight);
    float waterLevel = inlandSample.y / max(inlandSample.x, 1e-8);
    float waterDepth = inlandSample.z / max(inlandSample.x, 1e-8);
    float3 waterFlow = input.water.xyz;
    // Independent water coverages: a dry positive vertex cannot reclassify a whole coastal triangle as a lake.
    // Premultiplication excludes dry heights from the water stage; the fine grid supplies its own wetness.
    const float elevationSpread = ElevationSpread(slopeSpread, cellSize);
    float oceanCoverage = 1.0 - SpreadStep(-1.0, 1.0, elevation, elevationSpread);
    const float shoreAA = max(abs(ddx(inlandSample.z)) + abs(ddy(inlandSample.z)), 0.05);
    float inlandCoverage = saturate(inlandSample.x) * smoothstep(0.02, 0.02 + shoreAA, waterDepth);
    // Grid wetness is a candidate, never the final contour. In particular a narrow river can pass between every
    // dry sample. Refine its conservative distance band with the SAME terrain rule at pixel scale. This also
    // prevents a moving grid's linear height approximation from drawing polygonal coastlines in orbit.
    const float sampleCell = input.cellSize / lerp(1.0, ringParams.w, fineWeight);
    const float pixelCell = max(0.5 * footprint, CREASE_MIN_CELL);
    const float unresolved = smoothstep(1.0, 2.0, sampleCell / pixelCell);
    const float heightBand = max(elevationSpread, max(abs(ddx(elevation)), abs(ddy(elevation)))
                                  * sampleCell / max(footprint, 1e-3)) + 0.02 * sampleCell + 2.0;
    const float coastSupport = 1.0 - smoothstep(2.0 * heightBand, 3.0 * heightBand, abs(elevation));
    const float riverSupport = 1.0 - smoothstep(2.0 * sampleCell, 3.0 * sampleCell, abs(inlandSample.w));
    const float mixedShore = smoothstep(0.0, 0.02, inlandSample.x) * (1.0 - smoothstep(0.98, 1.0, inlandSample.x));
    const float refine = unresolved * max(coastSupport, max(riverSupport, mixedShore));
    const float dryBound = max(2.0 * footprint, 20.0);
    float preciseElevation = elevation, preciseClearance = -dryBound;
    float preciseLevel = waterLevel, preciseDepth = waterDepth;
    float3 preciseFlow = waterFlow;
    // Two fine-derivative reductions broadcast any candidate across its 2x2 quad, without requiring wave ops.
    const float candidate = refine > 0.0 ? 1.0 : 0.0;
    const float rowCandidate = saturate(candidate + abs(ddx_fine(candidate)));
    const float evaluateContour = rowCandidate + abs(ddy_fine(rowCandidate));
    [branch] if (evaluateContour > 0.0)
    {
        gMaxFrequency = (1000.0 * PLANET_RADIUS_KM) / (MESH_BAND_LIMIT * pixelCell);
        gCreaseMaxFrequency = gMaxFrequency;
        gExactLattice = pixelCell < EXACT_LATTICE_MAX_CELL;
        // Keep the cancellation-free nadir offset used by TerrainAt; no planet-sized float position.
        const float3 offset = up.x * faceX.xyz + up.y * faceY.xyz
                            - (dot(up.xy, up.xy) / max(1.0 + up.z, 1e-6)) * faceZ.xyz;
        preciseElevation = ReliefElevation(nadir.xyz + (double3)offset);
        preciseLevel = gWaterLevel;
        preciseDepth = max(preciseLevel - preciseElevation, 0.0);
        preciseClearance = max(gWaterClearance, -dryBound);
        preciseFlow = gWaterFlow;
    }
    // Every lane of a derivative quad evaluates together, including a mixed lake shore at the end of a candidate
    // band. A dry fallback must never participate in a derivative of the freshly evaluated water field.
    const float oceanAA = max(abs(ddx(preciseElevation)) + abs(ddy(preciseElevation)), 0.02);
    const float liquidAA = max(abs(ddx(preciseClearance)) + abs(ddy(preciseClearance)), 0.02);
    const float preciseOcean = 1.0 - smoothstep(-0.5 * oceanAA, 0.5 * oceanAA, preciseElevation);
    // A dry plane can coincide exactly with its drainage stage. Zero clearance is dry, never half water;
    // centre-symmetric AA would flood every such floor with a 50% reflective ribbon in distant views.
    const float preciseInland = smoothstep(0.0, 0.5 * liquidAA, preciseClearance);
    oceanCoverage = lerp(oceanCoverage, preciseOcean, refine);
    inlandCoverage = lerp(inlandCoverage, preciseInland, refine);
    // The contour query decides water, not the bandwidth of land materials or their existing fine normals.
    // Feeding its finer height to coarse snow/material decisions introduces a new high-frequency pattern in orbit.
    const float waterBedElevation = lerp(elevation, preciseElevation, refine);
    waterLevel = lerp(waterLevel, preciseLevel, refine);
    waterDepth = lerp(waterDepth, preciseDepth, refine);
    waterFlow = lerp(waterFlow, preciseFlow, refine);
    const float sea = inlandCoverage + (1.0 - inlandCoverage) * oceanCoverage;
    // The point the materials and the fine detail are looked up at: on the spline surface, where the view ray
    // meets it, one Newton step from the triangle; on the triangle where the spline does not apply.
    float3 surfacePos = input.pos;
    const float3 ray = normalize(input.pos);
    const float along = dot(ray, splineNormal);
    if (SPLINE_SURFACE > 0.0 && splineWeight > 0.0 && abs(along) > 0.05)
        surfacePos += ray * (SPLINE_SURFACE * splineWeight * dot(splineSurface - input.pos, splineNormal) / along);
    const float3 q = detailOrigin.xyz + surfacePos.x * faceX.xyz + surfacePos.y * faceY.xyz + surfacePos.z * faceZ.xyz;
    const float3 dqdx = ddx(q), dqdy = ddy(q); // here, outside any branch
    float3 normal = vertexNormal;
    float3 detail = 0.0; // the fine detail's slope along the surface, face-local
    if (lightDir.w > 0.5)
    {
        normal = normalize(cross(ddy(input.pos), ddx(input.pos)));
        if (dot(normal, up) < 0.0)
            normal = -normal;
    }
    else if (DETAIL_SLOPE > 0.0 && sea < 1.0) // the dry fraction keeps terrain detail; water has its own ripples
    {
        const float3 planetSlope = DetailSlope(q, cellSize, footprint);
        detail = float3(dot(planetSlope, faceX.xyz), dot(planetSlope, faceY.xyz), dot(planetSlope, faceZ.xyz));
        detail -= dot(detail, vertexNormal) * vertexNormal;
        normal = normalize(vertexNormal - detail);
    }

    // North, the planet's y axis, in the face frame.
    const float3 north = float3(faceX.y, faceY.y, faceZ.y);
    const float sinLat = dot(up, north);
    float3 albedo = 0.0; // the ground's
    float cavity = 1.0, under = 0.0, canopy = 0.0, nearer = 0.0;
    float3 canopyAlbedo = 0.0;
    gPlantView = float3(length(input.pos), taa.w, saturate(-dot(ray, up))); // the placement's pixel angle
    gRay = ray;
    float diagnostic = 0.0; // the diagnostic view's weight
    if (sea < 1.0)
    {
        // The tangent direction towards the nearer pole.
        const float3 tangentNorth = north - sinLat * up;
        const float3 poleward = (sinLat < 0.0 ? -1.0 : 1.0) * tangentNorth * rsqrt(max(dot(tangentNorth, tangentNorth), 1e-12));
        gMeshCell = input.cellSize;
        // Borders moved by the textures' heights are sharper than their texels: once a pixel covers more than
        // about 25 cm, they would alias into stripes (rock and snow bed by bed). They fade into plain blends.
        gHeightBlend = 1.0 - smoothstep(-2.0, 1.0, log2(footprint));
        // The strata and lenses, filtered by the pixel rather than by the mesh's cells, 13 pixels wide: their octaves
        // came in plain to see as the cells shrank, and the strata slid on the way down (docs/spec-parois-minerales.md).
        // The geology, regional, stays the vertices' (VertexShader.hlsl).
        const float3 geology = input.geology.xyz;
        // Computed only where the rock needs them (Materials.hlsli, PixelStrataShift). From the vertices' own elevation,
        // not the spline's, which smooths the relief differently: the column's beds would jump from one cell to the next.
        gStrataCell = footprint;
        gStrataRaise = elevation - input.elevation;
        gCellSize = input.cellSize;
        // The materials are decided on the normal across DECISION_BASELINE (VertexShader.hlsl), the fine grid's far away, and
        // the textures' whole slope.
        float3 decisionNormal = normalize(lerp(normalize(input.decision), fineNormal, fineWeight));
        if (lightDir.w < 0.5)
            decisionNormal = normalize(decisionNormal - (detail - dot(detail, decisionNormal) * decisionNormal));
        // The beach's normal, across SHORE_BASELINE (VertexShader.hlsl), the fine grid's far away once its cells span the
        // baseline: the face's cells there no longer resolve a cordon's sides, and the vertices' normal on its crest stood
        // level; finer, the grid would bring back the bumps the baseline leaves out.
        const float fineCell = 2.0 * faceParams.x / (faceParams.w * ringParams.w);
        const float3 shoreNormal = normalize(lerp(normalize(input.shore), fineNormal,
                                                  fineWeight * smoothstep(0.5 * SHORE_BASELINE, SHORE_BASELINE, fineCell)));
        const Ground ground = GroundAt(q, elevation, up, decisionNormal, shoreNormal, sinLat, poleward, log2(footprint),
                                       dqdx, dqdy, geology, input.geology.w, slopeSpread, elevationSpread, input.cellSize, footprint);
        albedo = ground.albedo;
        cavity = ground.cavity;
        under = ground.under * (1.0 - sea);
        canopy = ground.canopy * (1.0 - sea);
        nearer = ground.nearer * (1.0 - sea);
        canopyAlbedo = ground.canopyAlbedo;
        diagnostic = ground.diagnostic * (1.0 - sea);
        if (lightDir.w < 0.5)
            normal = normalize(vertexNormal - ground.detailScale * detail - ground.slope);
    }

    // The sea's surface (Sea.hlsli): the water's own normal, its waves on the vertical, never the coast's.
    SeaSurface water = (SeaSurface)0;
    if (oceanCoverage > 0.0 && inlandCoverage < 1.0)
        water = SeaSurfaceAt(input.pos, dpdx, dpdy, q, log2(footprint), up, ClimateAt(materialSampler, PlanetDirection(up), footprint).y,
                             0.0, waterBedElevation, elevationSpread, sunShare,input.seaParam,seaDx,seaDy,input.seaHeight);
    if (inlandCoverage > 0.0)
    {
        const SeaSurface river = InlandWaterAt(input.pos, q, log2(footprint), up, waterLevel, waterDepth, waterFlow, sunShare);
        const float blend = inlandCoverage / max(sea, 1e-8);
        water.radiance = lerp(water.radiance, river.radiance, blend);
        water.sunRadiance = lerp(water.sunRadiance, river.sunRadiance, blend);
        water.foam = lerp(water.foam, river.foam, blend);
        water.glint = lerp(water.glint, river.glint, blend);
        water.wind = lerp(water.wind, river.wind, blend);
        water.moving = lerp(water.moving, river.moving, blend);
        water.foamFresh = lerp(water.foamFresh, river.foamFresh, blend);
        water.foamOld = lerp(water.foamOld, river.foamOld, blend);
        water.crest = lerp(water.crest, river.crest, blend);
    }

    // Diagnostic views (tools/banc_descente.py): each pixel white with the probability of the weight shown,
    // unlit, so that the share of white pixels is that weight's mean, at any distance. The sea's views are measures
    // (tools/banc_mer.py), on the sea only: the glint's, its reflectance over 4, the wind's speed over 32 m/s, its direction
    // modulo pi from 0.02; the foam's, the root of the whitecaps' share, in red.
    if(abs(taa.y-31.0)<0.5) return float4(sea>0.5?water.crest.xxx:0.0,1e-3);
    if(abs(taa.y-30.0)<0.5) return float4(sea>0.5?float3(sqrt(water.foamOld),0,0):0.0,1e-3);
    if(abs(taa.y-29.0)<0.5) return float4(sea>0.5?float3(sqrt(water.foamFresh),0,0):0.0,1e-3);
    if (abs(taa.y - 28.0) < 0.5)
        return float4(sea > 0.5 ? float3(0.25 * water.glint, water.wind.x / 32.0, 0.02 + 0.96 * frac(water.wind.y / PI)) : 0.0, 1e-3);
    if (abs(taa.y - 27.0) < 0.5)
        return float4(sea > 0.5 ? float3(sqrt(water.foam), 0.0, 0.0) : 0.0, 1e-3);
    const float3 planetUp = PlanetDirection(up); // for the planet map
    if (taa.y > CLIMATE_VIEW - 0.5) // the climate map's views (Climate.hlsli), unlit, to be seen from orbit
        return float4(SrgbToLinear(saturate(ClimateColour(materialSampler, taa.y, planetUp, footprint, input.elevation < 0.0))), 1e-3);
    if (taa.y > TECTONIC_VIEW - 0.5) // the tectonic map's views (Tectonics.hlsli), unlit, to be seen from orbit
        return float4(SrgbToLinear(saturate(TectonicColour(taa.y, planetUp, footprint / 1000.0))), 1e-3);

    // Diagnostic views (tools/banc_descente.py): each pixel white with the probability of the weight shown,
    // unlit, so that the share of white pixels is that weight's mean, at any distance.
    if (abs(taa.y - 32.0) < 0.5) // cloud coverage is drawn by the atmosphere pass; keep the surface distance for its rays
        return float4(0.0.xxx, length(input.pos) / 1000.0);
    if (abs(taa.y - 19.0) < 0.5 || taa.y > 20.5) // the biomes' and the climate's views: their values, as is (tools/banc_vegetation.py)
        return float4(diagnostic.xxx, 1e-3);
    if (taa.y > 0.5)
    {
        // The planet map's views (PlanetMap.hlsli), the mean of what the pixel covers: its ground and the haze's, up to
        // 6 km; its lakes from 10 m deep; its rivers out of the lakes, from 100 km2 drained up to a million.
        const float4 map = planetMap.SampleLevel(linearClamp, planetUp, MapLevel(planetUp, footprint));
        const float mapView = taa.y < 14.5 ? map.x / 6000.0 : taa.y < 15.5 ? RegionalGround(planetUp) / 6.0
                            : taa.y < 16.5 ? map.y / 10.0 : (map.z - log2(100.0)) / log2(1e4) * saturate(1.0 - map.y);
        const float weight = taa.y > 13.5 && taa.y < 17.5 ? saturate(mapView) : abs(taa.y - 10.0) < 0.5 ? sea
                           : abs(taa.y - 12.0) < 0.5 ? saturate(dot(normal, lightDir.xyz)) * sunShare : diagnostic;
        const float threshold = frac(sin(dot(floor(input.position.xy), float2(12.9898, 78.233))) * 43758.5453);
        return float4((weight > threshold ? 1.0 : 0.0).xxx, 1e-3);
    }

    // Lighting through the atmosphere (docs/log/spec-rendu.md, step B): the sun, filtered by the air above the
    // point, plus the light of the whole sky, less on slopes that face away from it.
    const float3 sun = lightDir.xyz;
    const float h = max(input.elevation, 0.0) / 1000.0, muS = dot(up, sun), ground = RegionalGround(planetUp);
    // Micro-shadows: the cavity closes a cone around the normal that also cuts the sun's light (after Naughty
    // Dog, Uncharted 4), relative to the cavity's mean so that far ground, where textures fade, keeps its light.
    const float lit = abs(dot(normal, sun)), occlusion = saturate(0.85 * cavity);
    const float microShadow = saturate(saturate(lit + 2.0 * occlusion * occlusion - 1.0) / max(saturate(lit + 2.0 * 0.85 * 0.85 - 1.0), 1e-3));
    const float3 sunLight = SUN_ILLUMINANCE * SunTransmittance(h, muS, ground) * saturate(dot(normal, sun)) * sunShare;
    const float3 skyLight = SkyIrradiance(h, muS, ground) * (0.5 + 0.5 * dot(normal, up));
    // Under the plants' crowns, drawn or not, which cast no shadow: the ground's light through their gaps, toward the sun
    // and the sky, as a Boolean canopy lets it through; the canopy beyond the objects over it (docs/recherche-vegetation.md).
    const float3 floorLight = sunLight * microShadow * pow(saturate(1.0 - under), 1.0 / max(muS, 0.1)) + skyLight * cavity * (1.0 - under);
    const float sideLight = 1.0 - CANOPY_SIDE_LIGHT.x * pow(1.0 - gPlantView.z, CANOPY_SIDE_LIGHT.y); // as the drawn plants seen from there
    const float3 groundRadiance = lerp(albedo * floorLight, canopyAlbedo * (sunLight + skyLight) * sideLight, canopy) / PI;

    // The direct solar share is kept separately for cloud shadows (AtmospherePass.hlsl). For water, include its
    // specular sun glint; the reflected sky remains in the non-solar part and is not darkened by the cloud.
    const float3 groundSunLight = sunLight * microShadow * pow(saturate(1.0 - under), 1.0 / max(muS, 0.1));
    const float3 groundSunRadiance = lerp(albedo * groundSunLight,
        canopyAlbedo * sunLight * sideLight, canopy) / PI;
    sunOut = float4(lerp(groundSunRadiance, water.sunRadiance, sea), 0.0);

    const float3 radiance = lerp(groundRadiance, water.radiance, sea);
    return float4(radiance, (sea > 0.5 && water.moving > 0.02 ? -1.0 : 1.0) * (length(input.pos) - nearer) / 1000.0);
}
