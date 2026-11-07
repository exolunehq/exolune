// PlantPlacement.hlsli - the plants' share of the objects' placement (ObjectPlacement.hlsl, docs/recherche-vegetation.md):
// a candidate in each cell of a quarter of its octave's height, a species drawn by the vegetation there, kept with the
// probability that gives the crowns' footprint. The cells go by tiles of 4 x 4, the octave's height square: the climate,
// the ground's materials and its exposure are decided once per tile, on its first cell's exact ground; where the woods and
// the shrubs are, once per plant, at its place on the tile's plane; its foot on the exact ground near the camera, on the
// ground the mesh draws far away. Needs ObjectPlacement.hlsl's helpers and buffers (PLANET_STABLE_PLANTS) and
// Vegetation.hlsli.
#ifndef PLANT_PLACEMENT_HLSLI
#define PLANT_PLACEMENT_HLSLI

// A crown's ground, on average over its octave, per d^2 of the octave's smallest height d: pi / 4 (crown spread)^2 E[h^2],
// its height h log-uniform over the octave, E[h^2] = 2.164 d^2.
float CrownArea(uint species, float spread)
{
    const float crown = PLANT_CROWN[species] * (species == BROADLEAF ? spread : 1.0);
    return 0.785398 * 2.164 * crown * crown;
}

// The footprints of the plants of octave k per unit of ground: x conifers, y broadleaves, z shrubs. Crowns placed at random
// cover 1 - exp(-footprint) of the ground (a Boolean canopy): the footprint that covers the share v gives.
float3 PlantFootprints(Vegetation v, int k)
{
    const float trees = -log(1.0 - TreesHere(v)) * OctaveShare(k, v.height);
    const float shrubs = -log(1.0 - ShrubsHere(v)) * OctaveShare(k, SHRUB_HEIGHT);
    return float3(trees * v.conifer, trees * (1.0 - v.conifer), shrubs);
}

// The vegetation's climate at a tile before its materials, on the mesh's ground and slope, with its cell's noise and the
// climate map, as GroundMaterials takes them: q from the anchor, the normal and poleward direction in the same frame,
// planetUp the vertical in the planet's.
Vegetation PlantClimate(float3 q, float elevation, float3 normal, float3 poleward, float pixel, float3 planetUp)
{
    const float4 climate = ClimateAt(materialSampler, planetUp, exp2(pixel));
    const float detail = Fbm3(q, log2(2000.0), 0.0, pixel, 0.62, 31u).x;
    const float lost = 0.146 * sqrt(FbmLostShare(log2(2000.0), 0.0, pixel, 0.62));
    const float t = Temperature(climate.y, elevation, dot(normal, poleward), detail);
    return VegetationAt(t, ClimateHumidity(climate.x, LocalRain(q, pixel).x), 4.0 * lost, climate.z, Exposure(planetUp, elevation));
}

// The species the candidate draws among the footprints, and its probability to be kept: the light pass and the heavy one
// draw alike.
float PlantChance(Candidate k, float3 footprints, float spread, out uint species)
{
    const float total = footprints.x + footprints.y + footprints.z;
    const float pick = (float(k.looks.x & 0xFFu) + 0.5) / 256.0 * total;
    species = pick < footprints.x ? CONIFER : pick < footprints.x + footprints.y ? BROADLEAF : SHRUB;
    return total * 1.47 * k.chance / CrownArea(species, spread);
}

// The most a tile's candidates can be kept with: every state and kind present wherever it may be (or everywhere), the
// narrowest crown.
float PlantBound(Candidate k, Vegetation v, bool everywhere)
{
    v.wood = v.wood > 0.0 || everywhere ? 1.0 : 0.0;
    v.stand = v.stand > 0.0 || everywhere ? 1.0 : 0.0;
    v.shrub = v.shrub > 0.0 || everywhere ? 1.0 : 0.0;
    const float3 f = PlantFootprints(v, k.octave);
    const float area = f.x > 0.0 ? CrownArea(CONIFER, 1.0) : f.y > 0.0 ? CrownArea(BROADLEAF, v.spread) : CrownArea(SHRUB, 1.0);
    return (f.x + f.y + f.z) * 1.47 * k.chance / area;
}

// The tile's cell i, 0 to 15.
int2 TileCell(int2 tile, uint i)
{
    return tile * 4 + int2(i % 4, i / 4);
}

// The light pass for the plants: every tile of every slice's window. A tile may be seen if one of its plants may be, by
// the reach of the octave's tallest and the tile's size, and the vegetation on the mesh's ground there bounds them all.
void ListGroundMiss(uint4 record);
void CullPlantTile(uint3 id, uint slice, uint plane)
{
    const int octave = SliceOctave(slice);
    const float d = exp2((float)octave);
    const int window = Window(PLANTS);
    const float2 pixels = PlantPixelRange();
    const int2 tile = (planes[plane].zw >> (int)round(log2(d / FINEST_CELL))) + (int2)id.xy - window / 2;
    if (id.x >= (uint)window || id.y >= (uint)window || PlantsDisabled() || (flags & 2u) != 0) // the census: stones and tufts only
        return;
    // The tile's middle, in its plane's ground or not: too far or out of view for any of its plants, whatever the ground's
    // height, the tile is left before its sixteen cells.
    Candidate k;
    MakeCandidate(slice, plane, TileCell(tile, 5), k);
    const float3 middle = FaceLocal((float3)(k.p - Double3(camX, camY, camZ))), vertical = FaceLocal(k.up);
    if (length(middle - dot(middle, vertical) * vertical) > 2.0 * d / (pixels.x * pixelAngle) + 3.0 * d
        || !MaybeVisible(middle, middle + vertical * (MAX_TERRAIN_HEIGHT + 2.0 * d), 0.0, 4.5 * d))
        return;
    // Its sixteen cells in the plane's ground, each with its point on the sphere in doubles, the light pass's dearest
    // step (docs/optimisation.md, round 3). Unless the plane's axis leads the vertical at the middle by more than the tile
    // can turn it: no candidate is farther than 4 cells, d sqrt 2, from the middle's on the plane, sqrt 3 times that on
    // the sphere at most (the axis leads: |up.a| > 1 / sqrt 3); each component of the vertical turns by as much over R.
    // Twice that, and the float's rounding, and every cell is in.
    const float upA = dot(k.up, Axis(k.axis)), lead = abs(upA) - max(abs(dot(k.up, Axis(k.b))), abs(dot(k.up, Axis(k.c))));
    uint inside = 0, first = 16;
    if (upA * planes[plane].y > 0.0 && lead > 2.0 * 2.45 * d * (float)INV_R + 1e-5)
    {
        inside = 0xFFFFu;
        first = 0;
    }
    else
        for (uint i = 0; i < 16; ++i)
            if (MakeCandidate(slice, plane, TileCell(tile, i), k))
            {
                inside |= 1u << i;
                first = min(first, i);
            }
    if (inside == 0)
        return;
    MakeCandidate(slice, plane, TileCell(tile, first), k);
    const float R = faceParams.y;
    const float3 sea = FaceLocal((float3)(k.p - Double3(camX, camY, camZ))), upFace = FaceLocal(k.up);
    const float3 centred = sea + float3(camPlane.xy, R + faceParams.z);
    const float2 xy = R * centred.xy / centred.z;
    if (MeshCell(xy) > OBJECT_CELLS.y * 2.0 * d) // the mesh cannot carry the tallest's foot
        return;
    float meshElevation, horizon;
    float3 meshNormal;
    if (!MeshElevationAt(xy, meshElevation, horizon, meshNormal) || meshElevation <= 0.0)
        return;
    const float margin = 1.0 + 0.05 * length(sea + upFace * meshElevation);
    const float low = max(meshElevation - margin, 0.0), high = meshElevation + margin;
    const float reach = 2.0 * d / (pixels.x * pixelAngle) + 1.5 * d;
    const float along = clamp(-dot(sea, upFace), low, high);
    if (length(sea + along * upFace) > reach || !MaybeVisible(sea + low * upFace, sea + (high + 2.0 * d) * upFace, 0.0, 3.5 * d))
        return;
    // The vegetation on the mesh's ground, seen at the tile: its plants bounded.
    const double3 footPoint = k.p + (double3)(k.up * meshElevation);
    const float3 q = (float3)(footPoint - (double3)detailAnchor.xyz * (double)detailOrigin.w);
    const float sinLat = k.up.y; // the planet's north is its y axis
    const float3 poleward = (sinLat < 0.0 ? -1.0 : 1.0) * normalize(float3(0.0, 1.0, 0.0) - sinLat * k.up + 1e-6);
    const float3 normal = meshNormal.x * faceX.xyz + meshNormal.y * faceY.xyz + meshNormal.z * faceZ.xyz;
    Vegetation v = PlantClimate(q, meshElevation, normal, poleward, log2(d), k.up);
    WoodsAt(q, log2(d), v);
    const float bound = 1.15 * PlantBound(k, v, false) + 0.01;
    bool any = false;
    for (uint j = 0; j < 16; ++j)
        if (inside & (1u << j))
        {
            Candidate c;
            MakeCandidate(slice, plane, TileCell(tile, j), c);
            any = any || c.accept < bound;
        }
    if (!any)
        return;
    const uint tileIndex = (((6u - id.z / planeCount) * planeCount + plane) * 512u + id.y) * 512u + id.x;
    const uint4 record = uint4(slice * 4 + plane | first << 8 | f32tof16(horizon) << 16, (uint)tile.x, (uint)tile.y, asuint(bound));
    stableTileRecords[tileIndex] = record;
    stableValues[tileIndex] = uint2(1, 0);
    ListGroundMiss(record);
}

// The exact ground, kept from frame to frame (docs/optimisation.md, round 3): a tile's, at its first cell and half a tile
// away along its two axes, and a near plant's. Functions of their cells on the planet's lattice, but for the last bits
// of the camera's rounding; three exact grounds per tile were three quarters of the placement. Read from the last
// frame's table, written to this frame's, each slot claimed by one writer: no thread reads a record another is
// writing. Four slots per bucket; a key without a slot is computed again.
static const uint GROUND_BUCKETS = 1u << 18;
bool GroundCached(uint3 key, out float3 e)
{
    e = 0.0;
    const uint bucket = Hash(key).x & (GROUND_BUCKETS - 1u);
    [unroll] for (uint s = 0; s < 4; ++s)
    {
        const uint slot = 4u * bucket + s;
        const uint4 a = groundRead[2u * slot];
        if (all(a.xyz == key))
        {
            e = float3(asfloat(a.w), asfloat(groundRead[2u * slot + 1u].xy));
            return true;
        }
    }
    return false;
}
void KeepGround(uint3 key, float3 e)
{
    const uint bucket = Hash(key).x & (GROUND_BUCKETS - 1u);
    [loop] for (uint s = 0; s < 4; ++s)
    {
        const uint slot = 4u * bucket + s;
        uint taken;
        groundClaims.InterlockedExchange(4u * slot, 1u, taken);
        if (taken == 0u)
        {
            groundWrite[2u * slot] = uint4(key, asuint(e.x));
            groundWrite[2u * slot + 1u] = uint4(asuint(e.yz), 0u, 0u);
            return;
        }
    }
}
// This frame's, kept by PlanetPlantGround before the heavy pass: no thread of the heavy pass writes its key.
bool GroundKept(uint3 key, out float3 e)
{
    e = 0.0;
    const uint bucket = Hash(key).x & (GROUND_BUCKETS - 1u);
    [unroll] for (uint s = 0; s < 4; ++s)
    {
        const uint slot = 4u * bucket + s;
        const uint4 a = groundWrite[2u * slot];
        if (all(a.xyz == key))
        {
            e = float3(asfloat(a.w), asfloat(groundWrite[2u * slot + 1u].xy));
            return true;
        }
    }
    return false;
}

// A tile's key and its three exact grounds: at its first cell and half a tile away along its two axes.
uint3 TileGroundKey(uint slice, uint plane, int2 tile, uint first)
{
    return uint3((uint)tile.x, (uint)tile.y, 0x80000000u | slice | first << 4 | (uint)planes[plane].x << 8 | (planes[plane].y > 0 ? 1u << 10 : 0u));
}
float3 TileGround(Candidate k)
{
    const float3 up = k.up, t1 = normalize(Axis(k.b) - up * dot(up, Axis(k.b))), t2 = cross(up, t1);
    const double3 u = k.p * INV_R;
    const float half = 0.5 * k.d;
    return float3(ExactElevation(u), ExactElevation(u + (double3)t1 * (half * INV_R)), ExactElevation(u + (double3)t2 * (half * INV_R)));
}

// The light pass's survivors whose ground the last frame did not keep, for PlanetPlantGround: their rivers computed by
// full waves of them, not by a lone lane of each heavy wave, the others idle (candidateList, dispatch: the objects' own).
void ListGroundMiss(uint4 record)
{
    const uint slice = (record.x & 0xFFu) / 4, plane = record.x % 4, first = (record.x >> 8) & 0xFFu;
    float3 e;
    if (GroundCached(TileGroundKey(slice, plane, int2(record.yz), first), e))
        return;
    uint slot;
    dispatch.InterlockedAdd(12, 1u, slot);
    if (slot >= CANDIDATES)
        return;
    if (slot % 64 == 0)
        dispatch.InterlockedAdd(0, 1u);
    candidateList.Store4(16 * slot, record);
}

// PlanetPlantGround: a listed tile's exact ground, kept for this frame's heavy pass and the next frame.
void PlantTileGround(uint4 record)
{
    const uint slice = (record.x & 0xFFu) / 4, plane = record.x % 4, first = (record.x >> 8) & 0xFFu;
    Candidate k;
    MakeCandidate(slice, plane, TileCell(int2(record.yz), first), k);
    KeepGround(TileGroundKey(slice, plane, int2(record.yz), first), TileGround(k));
}

// The heavy pass for a tile: the exact ground, its slope and materials at its first cell; the climate there; then each
// plant of its cells: where the woods and shrubs are at its place, its species drawn, kept or not, its foot on the ground,
// drawn or not by its fade; its instance, whole, fine or coarse by its height on screen (PLANT_LOD_PIXELS).
void PlacePlantTile(uint4 record, uint tileIndex)
{
    uint fineMask = 0, coarseMask = 0;
    const uint slice = (record.x & 0xFFu) / 4, plane = record.x % 4, first = (record.x >> 8) & 0xFFu;
    const int2 tile = int2(record.yz);
    const float horizon = f16tof32(record.x >> 16);
    const float R = faceParams.y;
    const double3 cam = Double3(camX, camY, camZ);
    Candidate k;
    MakeCandidate(slice, plane, TileCell(tile, first), k);
    counters.InterlockedAdd(COUNT_EVALUATED * 4, 1u);
    // The exact ground at the tile's first cell and half a tile away along its two axes: its slope at the tile's scale,
    // for the decisions.
    const float3 up = k.up, t1 = normalize(Axis(k.b) - up * dot(up, Axis(k.b))), t2 = cross(up, t1);
    const double3 u = k.p * INV_R;
    const float half = 0.5 * k.d;
    // A function of the tile alone, kept from frame to frame (GroundCached); else computed by PlanetPlantGround this frame
    // (GroundKept); else here, past its list's capacity.
    const uint3 groundKey = TileGroundKey(slice, plane, tile, first);
    float3 e;
    if (GroundCached(groundKey, e))
        KeepGround(groundKey, e);
    else if (!GroundKept(groundKey, e))
    {
        e = TileGround(k);
        KeepGround(groundKey, e);
    }
    const float e0 = e.x, e1 = e.y, e2 = e.z;
    if (max(e0, max(e1, e2)) <= 0.0)
        return;
    const float2 slope = float2(e1 - e0, e2 - e0) / half;
    const float3 normal = normalize(cross(t1 * (1.0 + e1 / R) + up * slope.x, t2 * (1.0 + e2 / R) + up * slope.y));
    const float3 upLocal = FaceLocal(up), normalLocal = FaceLocal(normal);
    const float3 q0 = (float3)(k.p + (double3)(up * e0) - (double3)detailAnchor.xyz * (double)detailOrigin.w);
    const float3 north = float3(faceX.y, faceY.y, faceZ.y);
    const float sinLat = dot(upLocal, north);
    const float3 tangentNorth = north - sinLat * upLocal;
    const float3 poleward = (sinLat < 0.0 ? -1.0 : 1.0) * tangentNorth * rsqrt(max(dot(tangentNorth, tangentNorth), 1e-12));
    gHeightBlend = 0.0;
    gMaterialTextures = 0.0;
    gBedLens = 0.0;
    gCellSize = k.d;
    // No normal across SHORE_BASELINE is available here; the tile's normal is taken at roughly the mesh cell's scale.
    const Materials m = GroundMaterials(q0, e0, upLocal, normalLocal, normalLocal, sinLat, poleward, log2(k.d),
                                        t1 * k.d, t2 * k.d, 0.0, 0.0, 0.0);
    Vegetation tileV = VegetationAt(m.temperature, m.humidity, m.coldSigma, m.amplitude, Exposure(up, e0));
    tileV.able = PlantGround(m);
    // The quick refusal: every state present on the exact ground, and the light pass's bound, where they are on the mesh's.
    const float bound = min(PlantBound(k, tileV, true) * 1.0001, asfloat(record.w));
    const float sunShare = SunAboveHorizon(dot(upLocal, lightDir.xyz), horizon, 0.0);

    const double3 p0 = k.p;
    for (uint i = 0; i < 16; ++i)
    {
        if (!MakeCandidate(slice, plane, TileCell(tile, i), k) || k.accept >= bound)
            continue;
        // Where the woods and the shrubs are at its place, on the tile's plane: their fields' finest octave, 8 m, moves by
        // a hundredth of their deviation for the metres the plane strays. Its species, kept or not, before its exact ground.
        Vegetation v = tileV;
        const float3 along = (float3)(k.p - p0);
        const double3 planeFoot = k.p + (double3)(k.up * (e0 + slope.x * dot(along, t1) + slope.y * dot(along, t2)));
        WoodsAt((float3)(planeFoot - (double3)detailAnchor.xyz * (double)detailOrigin.w), log2(k.cell), v);
        uint species;
        if (k.accept >= PlantChance(k, PlantFootprints(v, k.octave), v.spread, species))
            continue;
        // Its foot on the ground the mesh draws, far away, where the plant is drawn coarse: it stands on the ground seen,
        // and follows it; near the camera, from PLANT_LOD_PIXELS.y to x pixels high, on the exact ground, never on the
        // mesh, which slides under the near plants by metres on mountains. The exact ground, one per plant, is the
        // placement's dearest step: a tenth of the plants need it.
        const float3 centre = FaceLocal((float3)(k.p - cam)) + float3(camPlane.xy, R + faceParams.z);
        const float2 xy = R * centre.xy / centre.z;
        float drawn, unusedHorizon, waterLevel;
        float3 unusedNormal;
        if (!MeshElevationAt(xy, drawn, unusedHorizon, unusedNormal, waterLevel))
            continue;
        float e = drawn;
        float3 pos = FaceLocal((float3)(k.p + (double3)(k.up * e) - cam));
        float span = k.size / (length(pos) * pixelAngle);
        if (span > PLANT_LOD_PIXELS.y)
        {
            // Its exact ground, kept as the tile's: its cell's key.
            const uint3 plantKey = groundKey | uint3(0u, 0u, 1u << 11 | i << 12);
            float3 exact;
            if (!GroundCached(plantKey, exact))
            {
                const float height = ExactElevation(k.p * INV_R);
                exact = float3(height, gWaterLevel, 0.0); // cache the same water decision as the ground query
            }
            KeepGround(plantKey, exact);
            e = lerp(drawn, exact.x, smoothstep(PLANT_LOD_PIXELS.y, PLANT_LOD_PIXELS.x, span));
            waterLevel = lerp(waterLevel, exact.y, smoothstep(PLANT_LOD_PIXELS.y, PLANT_LOD_PIXELS.x, span));
            pos = FaceLocal((float3)(k.p + (double3)(k.up * e) - cam));
            span = k.size / (length(pos) * pixelAngle);
        }
        const float meshCell = MeshCell(xy);
        const float2 pixels = PlantPixelRange();
        const float fade = flags & 1u ? step(lerp(pixels.x, pixels.y, 0.5), span) * step(meshCell / k.size, lerp(OBJECT_CELLS.x, OBJECT_CELLS.y, 0.5))
                                      : PlantFade(k.size, length(pos), pixelAngle, meshCell);
        // Drawn whole or not at all, never growing: from its own threshold of the fade, so that the plants drawn are the
        // fade's share of them, as the ground's canopy counts them (PlantsDrawn), the rest standing in it at their height.
        if (fade <= (float(k.looks.y & 0xFFu) + 0.5) / 256.0 || e <= 0.0 || e < waterLevel - 0.02
            || !MaybeVisible(pos, pos, 0.0, k.size))
            continue;
        // Its foot in the ground, 3 % of its height; its trunk goes on below, to 0.15 of its whole height, whatever its
        // fade (PlanetFoliageMeshVertex.hlsl), and to a quarter of the mesh's cell there: deeper than the gap to the ground the mesh
        // draws, which grows with its cells (measured: none floats by half a pixel, tools/banc_vegetation.py tests).
        const float burial = max(0.15 * k.size, 0.25 * meshCell);
        const float gap = (e - drawn - burial - 0.03 * k.size) / (length(pos) * pixelAngle); // px, > 0: floating
        counters.InterlockedMax(PLANT_GAP * 4, (uint)(max(gap, 0.0) * 100.0));
        if (gap > 0.5)
            counters.InterlockedAdd(PLANT_FLOATING * 4, 1u);
        // Fine near the camera, coarse far away.
        const bool coarse = span < PLANT_LOD_PIXELS.y;
        const float turn = 6.2831853 * float(k.looks.y >> 8) / 16777216.0;
        const float3 side = normalize(cross(upLocal, abs(upLocal.z) < 0.9 ? float3(0.0, 0.0, 1.0) : float3(1.0, 0.0, 0.0)));
        ObjectInstance o = (ObjectInstance)0;
        o.pos = pos;
        o.size = k.size;
        o.axisX = cos(turn) * side + sin(turn) * cross(upLocal, side);
        o.burial = burial;
        o.axisY = float3(sunShare, species == BROADLEAF ? v.spread : 1.0, TreesHere(v));
        o.elevation = e;
        o.seed = (k.looks.z & 0xFFFFFFE0u) | species << 3 | (k.looks.z >> 29);
        if (species == SHRUB)
            o.axisY.y = 1.0 + ShrubClimateFamily(ShrubClimate(v, m.temperature), o.seed);
        stablePlantScratch[tileIndex * 16u + i] = o;
        if (coarse) coarseMask |= 1u << i; else fineMask |= 1u << i;
    }
    stableMasks[tileIndex] = uint2(fineMask, coarseMask);
    stableValues[tileIndex] = uint2(countbits(fineMask), countbits(coarseMask));
}

#endif
