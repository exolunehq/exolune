// Vegetation.hlsli - trees and shrubs from the climate (docs/recherche-vegetation.md). One source for the plants placed
// near the camera (ObjectPlacement.hlsl) and the ground's canopy beyond them (PixelShader.hlsl): what grows where, how
// much of the ground it covers, how tall; how much of it the objects draw at a distance, the ground showing the rest.
// Needs Planet.hlsli, PlanetSettings.hlsli, Materials.hlsli (and its materialSampler) and Objects.hlsli.
#ifndef VEGETATION_HLSLI
#define VEGETATION_HLSLI
#include "PlanetMap.hlsli"

struct Vegetation
{
    float trees;     // the climate's tree cover, the share of a region's ground under crowns
    float treeless;  // the land's share in the treeless state, and in the forest's (Hirota); the savanna's, the rest
    float forest;
    float open;      // the savanna's tree cover
    float shrubs;    // the shrubs' cover where they are
    float cold;      // how much the cold leaves of the trees, and of the shrubs, which go higher: the krummholz
    float shrubCold;
    float exposure;  // -1 in hollows to 1 on ridges and summits (Exposure)
    float wood;      // here (WoodsAt): the share in the savanna's or the forest's state, in the forest's, at its edge,
    float stand;     // and the shrubs' presence
    float edge;
    float shrub;
    float season;    // the growing season's mean temperature (C)
    float aridity;   // the precipitation over the potential evapotranspiration
    float height;    // the trees' canopy height (m), their crowns' flattening included
    float conifer;   // the conifers' share among the trees
    float spread;    // how much wider their crowns are than PLANT_CROWN: 1, to 3 for a savanna's flat crowns
    float able;      // the share of the ground plants can root in: neither bare rock, nor scree, nor a beach
};
#include "ShrubClimate.hlsli"

// The share of a normal law of mean m and deviation s below x: the universal rule's transition, its width 0 (SpreadStep).
float NormalBelow(float x, float m, float s)
{
    return 1.0 - SpreadStep(x - 1e-4, x + 1e-4, m, s);
}

// How exposed the ground is: its height over the regional ground, the planet map's at 16 km (PlanetMap.hlsli), over
// EXPOSURE_RELIEF m: -1 in hollows and valleys, 1 on ridges and summits. planetUp: the vertical, planet frame.
float Exposure(float3 planetUp, float elevation)
{
    const float regional = planetMap.SampleLevel(materialSampler, planetUp, MapLevel(planetUp, 16000.0)).x;
    return clamp((max(elevation, 0.0) - regional) / EXPOSURE_RELIEF, -1.0, 1.0);
}

// The vegetation's climate at a point of the ground: its temperature (C), humidity, the temperature's spread within the
// pixel or the cell (Materials), the seasons' half amplitude (C, the climate map's), its exposure. The ground plants can
// root in, and where each state and kind is (WoodsAt), apart.
Vegetation VegetationAt(float t, float humidity, float coldSigma, float amplitude, float exposure)
{
    Vegetation v;
    v.wood = v.stand = v.edge = v.shrub = 0.0;
    v.able = 1.0;
    v.exposure = exposure;
    // The seasons: a sine around the annual mean (tools/saisons_terre.py). The growing season, the days over
    // TREE_SEASON_START, and its mean; the biotemperature, the year's mean of the temperatures over 0 (Holdridge).
    const float theta = acos(clamp((TREE_SEASON_START - t) / amplitude, -1.0, 1.0));
    v.season = t + amplitude * sin(theta) / max(theta, 1e-4);
    const float warm = acos(clamp(-t / amplitude, -1.0, 1.0));
    const float biotemperature = (t * warm + amplitude * sin(warm)) / 3.14159265;
    // The humidity is the log of the annual precipitation from 100 to 3000 mm (BiomePalette.hlsli).
    v.aridity = 100.0 * pow(30.0, saturate(humidity)) / max(58.93 * biotemperature, 1.0);
    // The tree line, the shrubs' above it; exposed ground colder, hollows warmer; widened by the temperature the pixel
    // spreads over.
    const float season = v.season - EXPOSED_SEASON * exposure;
    v.cold = SpreadStep(TREE_LINE.x, TREE_LINE.y, season, coldSigma);
    v.shrubCold = SpreadStep(TREE_LINE.x - SHRUB_LINE_OFFSET, TREE_LINE.y - SHRUB_LINE_OFFSET, season, coldSigma);
    // The three states, by the rain at Hirota's evapotranspiration; the savanna's trees under Sankaran's ceiling.
    const float rain = 1414.0 * v.aridity;
    v.treeless = TREELESS_RAIN.z + (1.0 - TREELESS_RAIN.z) / (1.0 + exp((rain - TREELESS_RAIN.x) / TREELESS_RAIN.y));
    const float tail = 1.0 / (1.0 + exp(-(FOREST_RAIN.z - FOREST_RAIN.x) / FOREST_RAIN.y));
    v.forest = min(saturate((1.0 / (1.0 + exp(-(rain - FOREST_RAIN.x) / FOREST_RAIN.y)) - tail) / (1.0 - tail)), 1.0 - v.treeless);
    // The open land between the stands holds the savanna and the forest's clearings: the savanna's trees, at its share of it.
    const float savanna = min(saturate(TREE_CEILING.x * v.aridity - TREE_CEILING.y), TREE_COVER_MODES.y) * TREE_COVER_MODES.x / TREE_COVER_MODES.y;
    const float open = max(1.0 - v.treeless - v.forest * TREE_COVER_MODES.y / STAND_COVER, 1e-3);
    v.open = savanna * saturate((1.0 - v.treeless - v.forest) / open);
    v.trees = v.cold * (TREE_COVER_MODES.y * v.forest + savanna * (1.0 - v.treeless - v.forest));
    // The shrubs where they are: none in the hyper-arid, the desert's, the dry lands' scrub, the humid lands'.
    v.shrubs = SpreadStep(SHRUB_ARIDITY.x, SHRUB_ARIDITY.y, v.aridity, 0.0)
             * lerp(lerp(SHRUB_COVER.x, SHRUB_COVER.y, SpreadStep(SHRUB_ARIDITY.y, SHRUB_ARIDITY.z, v.aridity, 0.0)), SHRUB_COVER.z,
                    SpreadStep(SHRUB_ARIDITY.z, SHRUB_ARIDITY.w, v.aridity, 0.0));
    // The canopy's height: tall where the season is warm and the water plenty; the savanna's crowns lower and wider.
    v.height = CANOPY_HEIGHT * saturate(0.35 + 0.65 * (v.season - 6.4) / 20.0) * saturate(0.15 + 0.85 * (v.aridity - 0.1) / 1.2);
    const float flat = SpreadStep(17.0, 21.0, t, coldSigma) * (1.0 - SpreadStep(0.4, 1.0, v.aridity, 0.0));
    v.height *= 1.0 - 0.45 * flat;
    v.spread = 1.0 + 2.0 * flat;
    // Conifers in the cold, broadleaves in the warm: the boreal forest's border with the temperate, about 3 C (Whittaker).
    v.conifer = 1.0 - SpreadStep(0.0, 6.0, t, coldSigma);
    return v;
}

// The share of the ground plants can root in: neither bare rock, nor scree, nor a beach.
float PlantGround(Materials m)
{
    return (1.0 - m.rock) * (1.0 - m.screeWeight) * (1.0 - m.beach);
}

// Where a state or a kind of plant is, the one rule (docs/recherche-vegetation.md): a field of the planet's gradient
// noise, `widest` (PRESENCE_SCALES) to 8 m, of deviation PRESENCE_SIGMA, above the threshold that leaves `share` of the
// land, raised by `drive` deviations. sigma: what the pixel, or the scale it is seen at, cannot show of the field, which
// widens the threshold (the universal rule). Edges as sharp as the field's finest octave, 8 m.
static const float PRESENCE_SIGMA = 0.146;
// The bound of |Noise3| per unit of amplitude: 2.09 times, on each of its three axes, (2a - 3) d, at most a half once
// weighted by the corners (Materials.hlsli). A proof, far above its deviation, 0.40: only the eight gradients of a cell
// all lined up reach it.
static const float NOISE3_BOUND = 3.135;

// The threshold Presence draws on its field for this share and drive; none where the share is 0.
float PresenceThreshold(float share, float drive)
{
    if (share <= 0.0)
        return 1e30;
    share = min(share, 1.0 - 1e-3);
    return PRESENCE_SIGMA * (log((1.0 - share) / share) / 1.702 - drive);
}

// How far from its threshold the field must lie for every Presence drawn on it with this sigma or less to be 0 or 1:
// SpreadStep's half-width, with a margin for the rounding.
float PresenceReach(float sigma)
{
    return 1.01 * sqrt(1.1e-8 + 5.0 * sigma * sigma) + 1e-5;
}

// The field, its octaves summed only until the rest of them can no longer bring it within `reach` of `threshold`
// (docs/optimisation.md, round 2): past it, every Presence drawn there is 0 or 1 whatever the rest, as with all of them.
// Fbm3's sum otherwise, its x alone, the same octaves in the same order.
float PresenceField(float3 q, float pixel, uint seed, float widest, float threshold, float reach)
{
    const float unitLog = log2(detailOrigin.w), gain = 0.6;
    const int first = (int)ceil(unitLog - log2(widest)), last = (int)floor(unitLog - log2(8.0));
    const float norm = (1.0 - gain) / (1.0 - pow(gain, (float)(last - first + 1)));
    float sum = 0.0, amplitude = 1.0;
    [loop]
    for (int j = first; j <= min(last, first + 15); ++j)
    {
        const float wavelength = unitLog - j;
        if (wavelength <= pixel + 1.0)
            break;
        uint3 cell;
        float3 w;
        LatticePoint(q, j, cell, w);
        sum += amplitude * smoothstep(pixel + 1.0, pixel + 2.0, wavelength) * Noise3(cell + (uint)j * 0x9E3779B9u + seed, w).x;
        amplitude *= gain;
        if (abs(sum * norm - threshold) > 1.01 * NOISE3_BOUND * amplitude / (1.0 - gain) * norm + reach)
            break;
    }
    return sum * (1.0 - gain) / (1.0 - pow(gain, (float)(last - first + 1)));
}

float PresenceSigma(float pixel, float widest)
{
    return PRESENCE_SIGMA * sqrt(FbmLostShare(log2(widest), log2(8.0), pixel, 0.6));
}

float Presence(float field, float sigma, float share, float drive)
{
    if (share <= 0.0)
        return 0.0;
    share = min(share, 1.0 - 1e-3);
    const float threshold = PRESENCE_SIGMA * (log((1.0 - share) / share) / 1.702 - drive);
    return SpreadStep(threshold - 1e-4, threshold + 1e-4, field, sigma);
}

// The share of the land in stands: the forest's state, where the crowns cover its mode, TREE_COVER_MODES.y, with the
// clearings between its stands (the rest, open land).
float Stands(Vegetation v)
{
    return v.forest * TREE_COVER_MODES.y / STAND_COVER;
}

// Where the woods are at q, from the anchor, seen at a pixel or a lattice cell of log2 size `pixel` (m), on two fields as
// the stones' (PRESENCE_SCALES): the regions', the land in the savanna's or the forest's state, the rest without a tree;
// the patches', within the woods, the forest's stands, the rest its clearings. Both lowered on exposed ground. The
// forest's edge, the stands seen at FOREST_EDGE.x m; the shrubs, on a patches' field of their own, raised at the edge.
void WoodsAt(float3 q, float pixel, inout Vegetation v)
{
    const float drive = -EXPOSED_DRIVE * v.exposure, woods = 1.0 - v.treeless, stands = Stands(v) / max(woods, 1e-3);
    const float edge = max(pixel, log2(FOREST_EDGE.x));
    const float2 regionSigma = float2(PresenceSigma(pixel, PRESENCE_SCALES.x), PresenceSigma(edge, PRESENCE_SCALES.x));
    const float2 patchSigma = float2(PresenceSigma(pixel, PRESENCE_SCALES.y), PresenceSigma(edge, PRESENCE_SCALES.y));
    const float region = PresenceField(q, pixel, 79u, PRESENCE_SCALES.x, PresenceThreshold(woods, drive), PresenceReach(regionSigma.y));
    v.wood = Presence(region, regionSigma.x, woods, drive);
    const float woodSeen = Presence(region, regionSigma.y, woods, drive);
    const float patch = v.wood > 0.0 || woodSeen > 0.0 // none out of the woods
                      ? PresenceField(q, pixel, 81u, PRESENCE_SCALES.y, PresenceThreshold(stands, drive), PresenceReach(patchSigma.y)) : 0.0;
    v.stand = v.wood * Presence(patch, patchSigma.x, stands, drive);
    const float seen = woodSeen * Presence(patch, patchSigma.y, stands, drive);
    v.edge = 4.0 * seen * (1.0 - seen);
    const float shrubDrive = FOREST_EDGE.y * v.edge;
    v.shrub = v.shrubs * v.shrubCold > 0.0
            ? Presence(PresenceField(q, pixel, 89u, PRESENCE_SCALES.y, PresenceThreshold(SHRUB_LAND, shrubDrive), PresenceReach(patchSigma.x)),
                       patchSigma.x, SHRUB_LAND, shrubDrive) : 0.0;
}

// The ground's share under the trees' crowns here: the forest's stands, the savanna's trees, the cold's toll. And under
// the shrubs': fewer under a forest's canopy, the understorey; above the tree line, the krummholz.
// Without the plants' catalogue, no plant at all, neither drawn nor in the ground's canopy, which only stands for plants
// that are not drawn: seen from under its crowns, it stood as a curtain at the edge of their range.
float TreesHere(Vegetation v)
{
    return VegetationAbsent() ? 0.0 : v.cold * v.able * (STAND_COVER * v.stand + v.open * (v.wood - v.stand));
}

float ShrubsHere(Vegetation v)
{
    return VegetationAbsent() ? 0.0 : v.shrubCold * v.able * v.shrub * lerp(v.shrubs, min(v.shrubs, SHRUB_COVER.w), v.stand * v.cold);
}

// Les empreintes des arbres et des arbustes peuvent se recouvrir.
float PlantCover(float trees, float shrubs)
{
    return 1.0 - (1.0 - saturate(trees)) * (1.0 - saturate(shrubs));
}

// The share of the plants of canopy height `height` whose own height falls in octave k, 2^k to 2^(k+1) m: their log2 a
// normal law around 0.7 of the canopy's, PLANT_HEIGHT_SPREAD octaves wide.
float OctaveShare(int k, float height)
{
    const float centre = log2(0.7 * height);
    return NormalBelow((float)(k + 1), centre, PLANT_HEIGHT_SPREAD) - NormalBelow((float)k, centre, PLANT_HEIGHT_SPREAD);
}

// The share of the plants of height `size` the objects draw (PlantPlacement.hlsli), each whole from a threshold of its own:
// by their height on screen, from 5 to 8 pixels (none while they are off), and where the mesh, of cells `meshCell`, can
// carry their foot (OBJECT_CELLS, on their height: their trunk goes deep). A plant never grows: the rest stand in the
// ground's canopy at their height.
float2 PlantPixelRange()
{
    return PlantsDisabled() ? 0.0 : float2(5.0, 8.0);
}

float PlantFade(float size, float distance, float pixelAngle, float meshCell)
{
    const float2 pixels = PlantPixelRange();
    return smoothstep(pixels.x, pixels.y, size / (distance * pixelAngle))
         * smoothstep(OBJECT_CELLS.y, OBJECT_CELLS.x, meshCell / size);
}

// The share of the plants of canopy height `height` that the objects draw, seen from a distance with a pixel of angle
// `pixelAngle`, four heights per octave. And where the crowns of those they leave to the ground's canopy are, each from
// CROWN_BASE of its height to its top: three heights through them, from near the top of the tallest tenth of them down,
// and the share of their crowns' depth at each, 1 in all: what a ray seen from the side meets first is the tallest.
static const float CROWN_BASE = 0.45;
float PlantsDrawn(float height, float distance, float pixelAngle, float meshCell, out float3 slabs, out float3 depth)
{
    float rest[28]; // the share of the plants of each height left to the canopy: four per octave of PLANT_OCTAVES
    float drawn = 0.0, left = 0.0;
    // Far enough that even the tallest, under 2^(PLANT_OCTAVES.y + 1) m, stands under the drawn plants' pixels: their fades
    // are all 0, and not computed (docs/optimisation.md, round 2).
    [branch]
    if (exp2(PLANT_OCTAVES.y + 1.0) > PlantPixelRange().x * distance * pixelAngle)
    {
        [unroll]
        for (int k = PLANT_OCTAVES.x; k <= PLANT_OCTAVES.y; ++k)
        {
            const float w = 0.25 * OctaveShare(k, height);
            [unroll]
            for (int i = 0; i < 4; ++i)
            {
                const float f = PlantsDisabled() || w < 2.5e-4 ? 0.0 : PlantFade(exp2(k + (i + 0.5) / 4.0), distance, pixelAngle, meshCell); // none drawn: MYPLANETENGINE_NO_PLANTS
                drawn += w * f;
                rest[4 * (k - PLANT_OCTAVES.x) + i] = w * (1.0 - f);
                left += w * (1.0 - f);
            }
        }
    }
    else
    {
        [unroll]
        for (int k = PLANT_OCTAVES.x; k <= PLANT_OCTAVES.y; ++k)
        {
            const float w = 0.25 * OctaveShare(k, height);
            [unroll]
            for (int i = 0; i < 4; ++i)
            {
                rest[4 * (k - PLANT_OCTAVES.x) + i] = w;
                left += w;
            }
        }
    }
    float top = 0.0, below = 0.0; // the height under which nine tenths of those left stand
    [unroll]
    for (int j = 0; j < 28; ++j)
    {
        below += rest[j];
        if (top == 0.0 && below >= 0.9 * left)
            top = exp2(PLANT_OCTAVES.x + (j + 0.5) / 4.0);
    }
    slabs = top * float3(0.95, 0.75, 0.55);
    depth = 0.0;
    [unroll]
    for (int n = 0; n < 28; ++n)
    {
        const float h = exp2(PLANT_OCTAVES.x + (n + 0.5) / 4.0);
        depth += rest[n] * step(CROWN_BASE * h, slabs) * step(slabs, h) / ((1.0 - CROWN_BASE) * h);
    }
    depth /= max(depth.x + depth.y + depth.z, 1e-6);
    return drawn;
}

// The biome, for the measures (tools/banc_vegetation.py), from Holdridge's provinces of humidity, the aridity 1 and 0.25,
// and Whittaker's temperatures, the boreal under 3 C, the tropical over 19 C: 1 tundra and alpine, where no tree grows;
// 2 boreal; 3 temperate humid; 4 temperate dry, woodland, scrub, steppe; 5 tropical humid; 6 savanna and tropical dry;
// 7 desert.
float BiomeClass(Vegetation v, float temperature)
{
    return v.season < 6.4 ? 1.0 : v.aridity < 0.25 ? 7.0 : temperature < 3.0 ? 2.0
         : temperature < 19.0 ? (v.aridity >= 1.0 ? 3.0 : 4.0) : (v.aridity >= 1.0 ? 5.0 : 6.0);
}

// A canopy's colour, its own, not the climate's mean (ClimateColor), which holds the open land and Earth's own forests
// alike: CANOPY_ALBEDO for the trees, darker for conifers (PLANT_TINT); for the shrubs, SHRUB_ALBEDO in dry lands, the
// broadleaves' in humid ones (SHRUB_ARIDITY.z to w); a little brighter or darker from place to place as the ground's
// colour is, its hue drifting with it by region. species: conifer, broadleaf, shrub, or a mix as weights (x, y, z).
float3 CanopyColor(Materials m, float3 species, float aridity)
{
    const float3 shrub = lerp(SHRUB_ALBEDO, CANOPY_ALBEDO, SpreadStep(SHRUB_ARIDITY.z, SHRUB_ARIDITY.w, aridity, 0.0));
    return (CANOPY_ALBEDO * (species.x * PLANT_TINT.x + species.y) + shrub * species.z) * (1.0 + m.local.z)
         * (1.0 + float3(0.4, 0.0, -0.4) * m.regional.z);
}

#endif
