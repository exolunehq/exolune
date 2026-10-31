// Close-up materials (docs/spec-textures-generees.md), generated once at startup. For each material, a
// seamless square tile in two textures: colour and cavity, slope and height. Mip 0 is drawn from the recipe;
// each further mip averages 2 x 2 texels of the previous one.
//
// Colour: rgb, the colour factor halved (mean about 0.5, so factors up to 2 fit); a, the cavity (1: open,
// 0: fully occluded). Surface: xy, the height slope along the tile's axes (m per m) * 0.25 + 0.5, which
// averages correctly into the mips; z, the height around 0.5, over each material's HEIGHT_RANGE; w, unused.
// Every recipe starts from one height field: colour and cavity follow it.

RWTexture2DArray<unorm float4> outColor : register(u0);
RWTexture2DArray<unorm float4> outSurface : register(u1);
RWTexture2DArray<unorm float4> inColor : register(u2);   // the previous mip
RWTexture2DArray<unorm float4> inSurface : register(u3);
cbuffer Pass : register(b0)
{
    uint mip;  // 0: draw the recipe; above: average the previous mip
    uint size; // texels per side at this mip
};

// Materials and their tiles (m), as in Materials.hlsli. A tile divides the pixel shader's 64 m anchor. Each
// material has a coarse tile, then a fine one of 1 m, 1 mm per texel, MATERIAL_FINE slices further, which holds
// only wavelengths under 3 cm: grains, crystals, grit.
// Every rock is one photo (docs/journal-planete.md, 2026-10-24): its drawn structures, granite, basalt and badlands,
// and its 64 m tile, are gone.
static const uint MATERIAL_SAND = 0, MATERIAL_ROCK = 1, MATERIAL_SCREE = 2, MATERIAL_FINE = 3;
// MATERIAL_ROCK_TOP, 6: the rock's top-down photo, a scan only (Scans.cpp, kScans); without it, the default recipe.
static const float TILES[7] = { 8.0, 8.0, 4.0, 1.0, 1.0, 1.0, 64.0 / 3.0 };
static const float HEIGHT_RANGE[7] = { 0.06, 0.6, 0.3, 0.01, 0.01, 0.02, 0.6 }; // m per height unit
static const float PI = 3.14159265;

uint Hash(uint3 v) // pcg3d, Jarzynski & Olano 2020, first component
{
    v = v * 1664525u + 1013904223u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    v ^= v >> 16u;
    v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
    return v.x;
}

float Random(int2 cell, uint seed) // in [-1, 1]
{
    return float(Hash(uint3(cell, seed)) >> 8) * (2.0 / 16777215.0) - 1.0;
}

int2 Wrap(int2 cell, int2 period)
{
    return (cell % period + period) % period;
}

// 2D gradient noise of period `period` lattice cells along each axis, at p in lattice units. Value in about
// [-0.7, 0.7].
float PeriodicNoise(float2 p, int2 period, uint seed)
{
    const int2 c = (int2)floor(p);
    const float2 f = p - c;
    const float2 u = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    float corners[4];
    [unroll]
    for (int k = 0; k < 4; ++k)
    {
        const int2 o = int2(k & 1, k >> 1);
        const float angle = PI * Random(Wrap(c + o, period), seed);
        corners[k] = dot(float2(cos(angle), sin(angle)), f - o);
    }
    return lerp(lerp(corners[0], corners[1], u.x), lerp(corners[2], corners[3], u.x), u.y);
}

// Periodic Voronoi on a lattice of `period` cells per tile, at p in lattice units: the nearest random point
// (one per cell, jittered within it) and its cell, the second nearest, and the distance to the border between
// them (Quilez: along their bisector, a true distance). The lattice is warped by a periodic noise of half and an
// eighth of a cell, so that the borders wander: straight from corner to corner, the cracks, crystals and stones drawn
// on them read as polygons, a drawing (docs/principes.md, no structure drawn at one stroke).
void Voronoi(float2 p, int period, uint seed, out float2 nearest, out int2 nearestCell, out float border, out int2 nextCell)
{
    p += 0.6 * float2(PeriodicNoise(p * 2.0, period * 2, seed + 11u), PeriodicNoise(p * 2.0, period * 2, seed + 12u))
       + 0.15 * float2(PeriodicNoise(p * 8.0, period * 8, seed + 13u), PeriodicNoise(p * 8.0, period * 8, seed + 14u));
    const int2 c = (int2)floor(p);
    float best = 1e9, second = 1e9;
    float2 next = 0.0;
    nearest = 0.0;
    nearestCell = 0;
    nextCell = 0;
    for (int y = -2; y <= 2; ++y)
        for (int x = -2; x <= 2; ++x)
        {
            const int2 cell = c + int2(x, y), wrapped = Wrap(cell, period);
            const float2 site = cell + 0.5 + 0.4 * float2(Random(wrapped, seed), Random(wrapped, seed + 1u));
            const float d2 = dot(site - p, site - p);
            if (d2 < best)
            {
                second = best; next = nearest; nextCell = nearestCell;
                best = d2; nearest = site; nearestCell = wrapped;
            }
            else if (d2 < second)
            {
                second = d2; next = site; nextCell = wrapped;
            }
        }
    border = dot(0.5 * (nearest + next) - p, normalize(next - nearest));
}

// Round grains on a lattice of `period` cells per tile, at p in lattice units: one in a cell with probability
// `density`, its centre jittered by a quarter cell, its radius (cells) between radius.x and radius.y, at most
// half a cell. Each is a sphere sunk to 40% of its radius; where two meet, the higher wins. Returns the
// height (cells) and the grain's cell, (-1, -1) for none.
float Grains(float2 p, int period, uint seed, float density, float2 radius, out int2 grain)
{
    const int2 c = (int2)floor(p);
    float best = 0.0;
    grain = int2(-1, -1);
    for (int y = -1; y <= 1; ++y)
        for (int x = -1; x <= 1; ++x)
        {
            const int2 cell = c + int2(x, y), wrapped = Wrap(cell, period);
            if (0.5 + 0.5 * Random(wrapped, seed) > density)
                continue;
            const float2 centre = cell + 0.5 + 0.25 * float2(Random(wrapped, seed + 1u), Random(wrapped, seed + 2u));
            const float r = lerp(radius.x, radius.y, 0.5 + 0.5 * Random(wrapped, seed + 3u));
            const float h = r * max(sqrt(saturate(1.0 - dot(p - centre, p - centre) / (r * r))) - 0.4, 0.0);
            if (h > best)
            {
                best = h;
                grain = wrapped;
            }
        }
    return best;
}

// The colour factor of a mineral grain: mostly the sand's own, some light quartz, some dark, some red.
float3 GrainColor(int2 grain, uint seed)
{
    const float kind = 0.5 + 0.5 * Random(grain, seed), shade = 1.0 + 0.15 * Random(grain, seed + 1u);
    if (kind < 0.2)
        return shade * float3(0.45, 0.42, 0.40);
    if (kind < 0.45)
        return shade * float3(1.45, 1.42, 1.36);
    if (kind < 0.6)
        return shade * float3(1.15, 0.85, 0.70);
    return shade * float3(1.0, 0.97, 0.93);
}

// What a recipe gives at a point: the height (m), and the colour factor and cavity there.
struct Sample
{
    float height;
    float3 color;
    float cavity;
};

// Sand, on an 8 m tile: its mottling and gentle bumps; the grain is in the fine tile. The ripples are drawn
// per pixel by Materials.hlsli (SandRipples): a periodic pattern does not survive the tiling's blends.
Sample Sand(float2 p)
{
    const float mottle = PeriodicNoise(p, 8, 16u) + 0.5 * PeriodicNoise(p * 4.0, 32, 17u);
    Sample s;
    s.height = 0.02 * PeriodicNoise(p * 0.5, 4, 15u);
    s.color = (1.0 + 0.06 * mottle) * float3(1.0, 0.99, 0.97);
    s.cavity = 1.0;
    return s;
}

// Fine sand, on a 1 m tile: a dense spread of mineral grains of 1.5 to 3 mm, some gravel of 5 to 9 mm, the
// finest grain at the texel, and micro-bumps of 3 cm and 8 mm.
Sample FineSand(float2 p)
{
    const float speck = Random(Wrap((int2)floor(p * 1024.0), 1024), 60u);
    int2 grain, pebble;
    const float grainHeight = Grains(p * 256.0, 256, 61u, 0.7, float2(0.2, 0.4), grain) / 256.0;
    const float pebbleHeight = Grains(p * 64.0, 64, 65u, 0.12, float2(0.15, 0.3), pebble) / 64.0;
    Sample s;
    s.height = 0.0006 * PeriodicNoise(p * 32.0, 32, 69u) + 0.0003 * PeriodicNoise(p * 128.0, 128, 70u)
             + 0.00015 * speck + max(grainHeight, pebbleHeight);
    s.color = (1.0 + 0.12 * speck) * (1.0 + 0.04 * PeriodicNoise(p * 32.0, 32, 71u));
    if (pebbleHeight > grainHeight)
        s.color *= GrainColor(pebble, 66u);
    else if (grainHeight > 0.0)
        s.color *= GrainColor(grain, 62u);
    s.cavity = 1.0;
    return s;
}

// Rock, on an 8 m tile, strata along y (the pixel shader turns y towards the local vertical, so y climbs
// the cliffs), as a cliff is built (docs/spec-textures-generees.md): layers of about 0.5 m, one in three soft
// and receding a little, grouped into beds of 0.5 to 2 m; each bed cut by joints across the layers, 0.8 to
// 4 m apart, wavy, shifted from one bed to the next. Each block a plane tilted and raised a little. One
// joint or bedding plane in four is an open crack, one in thirteen a crevice of a few centimetres, chamfered;
// the others only a slight step. Lumps of 1 m and 25 cm, roughness down to the texel. Colour: each block its own
// shade, each layer its own tint from pale to rust; red iron stains; dark varnish in streaks running down the
// cliff, lighter weathered crusts; lichen crusts in colonies; cracks, crevices and recesses dark and occluded.
bool BedBottom(int layer, int layers, uint seed) // whether a bed starts at this layer (wrapped): at least every fourth
{
    const int wrapped = (layer % layers + layers) % layers;
    return wrapped % 4 == 0 || Random(int2(wrapped, 5), seed) > 0.0;
}

// The joints of a bed along u, in joint spacings (n per tile): joint k at k plus a jitter of up to 0.35. The
// block u lies in, between joints left and right, and the nearest joint.
void Joints(float u, int n, int bed, uint seed, out int k, out int joint, out float left, out float right)
{
    const int k0 = (int)floor(u);
    left = k0 + 0.35 * Random(int2(Wrap(int2(k0, 0), int2(n, 1)).x, bed), seed);
    const float nextLeft = k0 + 1 + 0.35 * Random(int2(Wrap(int2(k0 + 1, 0), int2(n, 1)).x, bed), seed);
    k = k0;
    right = nextLeft;
    if (u < left)
    {
        k = k0 - 1;
        right = left;
        left = k0 - 1 + 0.35 * Random(int2(Wrap(int2(k0 - 1, 0), int2(n, 1)).x, bed), seed);
    }
    else if (u >= nextLeft)
    {
        k = k0 + 1;
        left = nextLeft;
        right = k0 + 2 + 0.35 * Random(int2(Wrap(int2(k0 + 2, 0), int2(n, 1)).x, bed), seed);
    }
    joint = Wrap(int2(u - left < right - u ? k : k + 1, 0), int2(n, 1)).x;
}

Sample Rock(float2 p)
{
    const float tile = TILES[MATERIAL_ROCK];
    const float layers = 16.0; // per tile
    const float strata = p.y * (layers / tile) + 0.6 * PeriodicNoise(p * 0.25, 2, 25u) + 0.15 * PeriodicNoise(p, 8, 26u);
    const int rawLayer = (int)floor(strata);
    const int layer = (rawLayer % (int)layers + (int)layers) % (int)layers;
    const float within = frac(strata);
    const float hardness = Random(int2(layer, 0), 27u) > 0.35 ? 1.0 : 0.5 + 0.25 * Random(int2(layer, 2), 34u);
    const float recess = (1.0 - hardness) * smoothstep(0.0, 0.12, within) * smoothstep(1.0, 0.88, within);

    // The bed: from the bed bottom at or below this layer to the next one above.
    int bottom = rawLayer, top = rawLayer + 1;
    [unroll] for (int b = 0; b < 3 && !BedBottom(bottom, 16, 36u); ++b) bottom -= 1;
    [unroll] for (int t = 0; t < 3 && !BedBottom(top, 16, 36u); ++t) top += 1;
    const int bed = (bottom % (int)layers + (int)layers) % (int)layers;
    const float bedThickness = (top - bottom) * (tile / layers); // m
    const float bedV = (strata - bottom) / (top - bottom);

    // The joints of this bed: n per tile, each jittered and wavy, the bed's pattern shifted.
    const int n = 2 + (int)(4.5 + 4.49 * Random(int2(bed, 6), 37u)); // 2 to 10
    const float u = p.x * (n / tile) + n * (0.5 + 0.5 * Random(int2(bed, 7), 38u))
                  + 0.25 * PeriodicNoise(float2(p.x * 0.5, p.y * 2.0), int2(4, 16), 58u);
    int k, joint;
    float left, right;
    Joints(u, n, bed, 59u, k, joint, left, right);
    const float jointDistance = min(u - left, right - u) * (tile / n); // m
    const float bedDistance = min(bedV, 1.0 - bedV) * bedThickness;
    const bool onJoint = jointDistance < bedDistance;
    const float border = min(jointDistance, bedDistance);
    const int2 block = int2(Wrap(int2(k, 0), int2(n, 1)).x, bed);

    const float2 tilt = 0.10 * float2(Random(block, 22u), Random(block, 23u));
    const float facet = 0.04 * Random(block, 24u) + tilt.x * ((u - 0.5 * (left + right)) * (tile / n)) + tilt.y * (bedV - 0.5) * bedThickness;
    // A joint or bedding plane is open, a crevice or closed; its width varies along it.
    const float kind = onJoint ? Random(int2(joint, bed), 39u) : Random(int2(bedV < 0.5 ? bed : (top % (int)layers + (int)layers) % (int)layers, 8), 39u);
    const float along = 0.5 + 0.5 * PeriodicNoise(p * 2.0, 16, 40u) / 0.7;
    const float width = kind > 0.85 ? 0.02 + 0.03 * along : (kind > 0.5 ? 0.006 + 0.012 * along : 0.0);
    const float crack = width > 0.0 ? 1.0 - smoothstep(0.3 * width, width, border) : 0.0;
    const float crevice = kind > 0.85 ? crack : 0.0;
    const float chamfer = width > 0.0 ? 1.0 - smoothstep(0.0, 0.10, border) : 0.0;

    const float rough = 0.07 * PeriodicNoise(p, 8, 50u) + 0.035 * PeriodicNoise(p * 4.0, 32, 28u)
                      + 0.010 * PeriodicNoise(p * 16.0, 128, 29u) + 0.004 * PeriodicNoise(p * 64.0, 512, 30u);
    // Streaks: a noise stretched down the cliff. Crusts: patches of about 1 m.
    const float streak = smoothstep(0.05, 0.45, PeriodicNoise(float2(p.x * 2.0, p.y * 0.25), int2(16, 2), 46u)
                                               + 0.4 * PeriodicNoise(float2(p.x * 8.0, p.y * 0.5), int2(64, 4), 47u));
    const float crust = smoothstep(0.1, 0.4, PeriodicNoise(p, 8, 48u) + 0.5 * PeriodicNoise(p * 4.0, 32, 49u));
    // Iron stains: patches of 30 to 60 cm. Lichens: crusts of 2 to 4 cm in colonies of about a metre, grey green
    // or orange from one colony to the next.
    const float stain = smoothstep(0.25, 0.45, PeriodicNoise(p * 2.0, 16, 51u) + 0.5 * PeriodicNoise(p * 8.0, 64, 52u));
    const float colony = smoothstep(0.0, 0.2, PeriodicNoise(p, 8, 53u) + 0.5 * PeriodicNoise(p * 4.0, 32, 54u));
    const float lichen = colony * smoothstep(0.15, 0.22, PeriodicNoise(p * 24.0, 192, 55u) + 0.5 * PeriodicNoise(p * 64.0, 512, 56u));
    const float3 lichenColor = lerp(float3(1.35, 1.4, 1.2), float3(1.6, 1.05, 0.45), smoothstep(-0.1, 0.1, PeriodicNoise(p * 0.5, 4, 57u)));
    Sample s;
    s.height = 0.6 * facet - 0.03 * chamfer * chamfer - 0.05 * crack - 0.08 * crevice - 0.06 * recess + rough;
    s.color = (1.0 + 0.10 * Random(block, 31u)) * (1.0 + float3(0.05, 0.0, -0.05) * Random(block, 33u))
            * (1.0 + 0.15 * Random(int2(layer, 1), 32u))
            * lerp(float3(1.08, 1.05, 1.0), float3(1.12, 0.88, 0.7), 0.5 + 0.5 * Random(int2(layer, 3), 35u))
            * lerp(1.0, float3(1.15, 0.7, 0.5), 0.8 * stain) * lerp(1.0, float3(0.6, 0.55, 0.5), streak)
            * (1.0 + 0.30 * crust) * (1.0 - 0.35 * crack) * (1.0 - 0.15 * recess);
    s.color = lerp(s.color, lichenColor, lichen);
    s.cavity = 1.0 - 0.35 * crack - 0.2 * crevice - 0.08 * chamfer * chamfer - 0.15 * recess;
    return s;
}

// Fine rock, on a 1 m tile: crystals of about 2.5 mm, each its own shade, a few dark and a few light ones;
// roughness of 4 mm and 2 mm; pits of 3 to 8 mm.
Sample FineRock(float2 p)
{
    float2 nearest;
    int2 crystal, unused;
    float border;
    Voronoi(p * 400.0, 400, 80u, nearest, crystal, border, unused);
    const float kind = 0.5 + 0.5 * Random(crystal, 81u);
    const float shade = (kind < 0.1 ? 0.6 : (kind > 0.9 ? 1.25 : 1.0)) * (1.0 + 0.10 * Random(crystal, 82u));
    int2 pit;
    const float pitDepth = 0.6 * Grains(p * 64.0, 64, 84u, 0.1, float2(0.1, 0.25), pit) / 64.0;
    const float pitted = saturate(pitDepth / 0.001);
    Sample s;
    s.height = 0.0015 * PeriodicNoise(p * 256.0, 256, 85u) + 0.0006 * PeriodicNoise(p * 512.0, 512, 86u)
             + 0.0001 * Random(crystal, 83u) - pitDepth;
    s.color = shade * (1.0 - 0.3 * pitted);
    s.cavity = 1.0 - 0.4 * pitted;
    return s;
}

// Angular stones on dust, `period` per tile of `tile` m: each its Voronoi cell shrunk by a wide gap,
// bevelled, with its own tilt, height and shade; four cells in ten empty. Stones never cross their cell, so
// none is cut. Darker dust at their feet.
void Stones(float2 p, float tile, float period, uint seed, inout Sample s)
{
    const float cell = tile / period;
    float2 nearest;
    int2 stone, unused;
    float border;
    Voronoi(p / cell, (int)period, seed, nearest, stone, border, unused);
    border *= cell; // m
    const float gap = cell * (0.22 + 0.16 * (0.5 + 0.5 * Random(stone, seed + 1u)));
    const float bevel = 0.10 * cell;
    const bool present = Random(stone, seed + 4u) > -0.2;
    const float2 tilt = 0.45 * float2(Random(stone, seed + 5u), Random(stone, seed + 6u));
    const float top = cell * (0.25 + 0.15 * Random(stone, seed + 7u)) + dot(tilt, p - nearest * cell);
    const float rise = present ? saturate((border - gap) / bevel) : 0.0;
    const float height = top * rise * rise * (3.0 - 2.0 * rise);
    if (height > s.height)
    {
        s.height = height;
        s.color = 0.85 + 0.25 * Random(stone, seed + 2u) + float3(0.04, 0.0, -0.04) * Random(stone, seed + 3u);
    }
    if (present) // the stone's foot, in the dust around it
        s.cavity = min(s.cavity, 1.0 - 0.45 * (1.0 - smoothstep(0.0, gap, border)) * (border < gap ? 1.0 : 0.0));
}

// Scree and gravel, on a 4 m tile: stones of about 25 cm and 10 cm scattered on lighter dust.
Sample Scree(float2 p)
{
    Sample s;
    s.height = 0.0;
    s.color = 1.35; // dust
    s.cavity = 1.0;
    Stones(p, TILES[MATERIAL_SCREE], 10.0, 41u, s);
    Stones(p, TILES[MATERIAL_SCREE], 24.0, 48u, s);
    return s;
}

// Fine scree, on a 1 m tile: grit of about 2 cm and 8 mm, and mineral grains, on dust speckled at the texel.
Sample FineScree(float2 p)
{
    const float speck = Random(Wrap((int2)floor(p * 1024.0), 1024), 90u);
    Sample s;
    s.height = 0.00015 * speck;
    s.color = 1.0 + 0.08 * speck;
    s.cavity = 1.0;
    int2 grain;
    const float grainHeight = Grains(p * 256.0, 256, 91u, 0.3, float2(0.2, 0.4), grain) / 256.0;
    if (grainHeight > 0.0)
    {
        s.height += grainHeight;
        s.color *= GrainColor(grain, 95u);
    }
    Stones(p, 1.0, 50.0, 100u, s);
    Stones(p, 1.0, 120.0, 108u, s);
    return s;
}

Sample Recipe(uint material, float2 p)
{
    if (material == MATERIAL_SAND)
        return Sand(p);
    if (material == MATERIAL_ROCK)
        return Rock(p);
    if (material == MATERIAL_SCREE)
        return Scree(p);
    if (material == MATERIAL_FINE + MATERIAL_SAND)
        return FineSand(p);
    if (material == MATERIAL_FINE + MATERIAL_ROCK)
        return FineRock(p);
    return FineScree(p);
}

[numthreads(8, 8, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    if (id.x >= size || id.y >= size)
        return;
    if (mip > 0)
    {
        float4 color = 0.0, surface = 0.0;
        [unroll]
        for (uint k = 0; k < 4; ++k)
        {
            const uint3 source = uint3(id.xy * 2 + uint2(k & 1, k >> 1), id.z);
            color += inColor[source];
            surface += inSurface[source];
        }
        outColor[id] = 0.25 * color;
        outSurface[id] = 0.25 * surface;
        return;
    }

    // Material id.z at mip 0. Slope by centred differences over one texel, wrapping around the tile.
    const float tile = TILES[id.z], texel = tile / size;
    const float2 p = (id.xy + 0.5) * texel;
    const Sample s = Recipe(id.z, p);
    const float2 slope = float2(Recipe(id.z, p + float2(texel, 0.0)).height - Recipe(id.z, p - float2(texel, 0.0)).height,
                                Recipe(id.z, p + float2(0.0, texel)).height - Recipe(id.z, p - float2(0.0, texel)).height)
                       / (2.0 * texel);
    outColor[id] = float4(saturate(0.5 * s.color), saturate(s.cavity));
    outSurface[id] = float4(saturate(slope * 0.25 + 0.5), saturate(s.height / HEIGHT_RANGE[id.z] + 0.5), 0.0);
}
