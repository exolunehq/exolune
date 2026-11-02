// Volcanoes.hlsli - the volcanoes (Tectonics.h; docs/spec-volcanisme.md), listed at startup with the tectonic map along the
// arcs, the rifts and the hotspots' chains, then evaluated point by point, never on the mesh: each one's edifice, concave
// for a stratovolcano, convex for a shield; its crater or its caldera; its flows; its field of small cones; an old
// island's top planed by the waves, a guyot; a reef around a sinking island, its lagoon, an atoll. A cube indexes them,
// each of its cells listing the volcanoes that reach it. Every profile at least two mesh cells wide, lower when wider,
// as the relief's (docs/principes.md). The CPU port: tools/hydro/cp.py.
#ifndef VOLCANOES_HLSLI
#define VOLCANOES_HLSLI
#include "PlanetSettings.hlsli"
#include "Noise.hlsli"
#include "Tectonics.hlsli"

// Tectonics::Volcano, 52 bytes.
struct Volcano
{
    float3 at;     // its summit's direction, a unit vector
    float radius;  // its base's radius (km)
    float height;  // its height above the ground around it (m)
    float shape;   // 0 a stratovolcano's profile, concave, to 1 a shield's, convex
    float crater;  // its crater's or its caldera's radius (km), 0 none
    float depth;   // its depth under the rim (m)
    float top;     // the level its top was planed to (m above the sea); over VOLCANO_NO_TOP, none
    float reef;    // its reef's radius (km), 0 none
    float cones;   // the share of its field's cells holding a small cone
    float fresh;   // 1 young, its lava and ash bare, to 0 old, weathered
    uint seed;
};
StructuredBuffer<Volcano> volcanoes : register(t21);
// The index: per cell of a cube of VOLCANO_GRID^2 cells per face, the position of its first volcano's number in this same
// array, then the end; then the numbers (Tectonics::Map::volcanoIndex).
StructuredBuffer<uint> volcanoIndex : register(t22);
static const uint VOLCANO_GRID = 64;       // Tectonics::VolcanoGrid
static const float VOLCANO_NO_TOP = 1e8;   // Tectonics::NoTop is over it
// A volcano reaches x times its radius, y km at least (Tectonics.cpp, the index): its apron to 1.3 radii, its outline
// 30 % wider at most; its profile, widened to two mesh cells, never wider than that over x.
static const float2 VOLCANO_REACH = float2(1.7, 80.0);

// The fresh volcanic ground of the last point evaluated, 0 to 1: bare lava, scoria and ash, dark (Materials.hlsli).
static float gVolcanic = 0.0;

// What the edifices leave to the end of the relief, after the detail (VolcanoFinish): the dominant volcano's planed top,
// its reef and its lagoon.
struct VolcanicFinish
{
    float top, topWeight;           // the level (m) and where it applies, 1 on the edifice
    float reef, crest;              // where the reef stands, 1 on its flat; the flat's level there (m), its islets on it
    float lagoon, lagoonLevel;      // where the lagoon is, 1 inside the reef; its floor there (m)
};

// The index's cell holding the direction d: D3D's cube map layout, as Tectonics.cpp's Cube.
uint VolcanoCell(float3 d)
{
    const float3 a = abs(d);
    const uint axis = a.x >= a.y && a.x >= a.z ? 0 : a.y >= a.z ? 1 : 2;
    const uint face = 2 * axis + (d[axis] < 0.0 ? 1 : 0);
    const float m = dot(d, TECTONIC_N[face]);
    const float2 st = float2(dot(d, TECTONIC_S[face]), dot(d, TECTONIC_T[face])) / m;
    const uint2 ij = (uint2)clamp(floor((st + 1.0) * 0.5 * VOLCANO_GRID), 0.0, VOLCANO_GRID - 1.0);
    return (face * VOLCANO_GRID + ij.y) * VOLCANO_GRID + ij.x;
}

// A volcano's profile at x, the distance from its summit over its base's radius, 1 at the summit: a stratovolcano's flanks
// concave, steep near the summit, gentle at the base, an exponential (Karátson et al. 2010), its apron to 1.3 radii; a
// shield's nearly straight from the floor to its broad flat top, 1 - x^1.3, its foot merging into the ground over the
// outer 40 % (Mauna Loa).
float VolcanoProfile(float x, float shape)
{
    const float strato = exp(-3.0 * x) * (1.0 - smoothstep(0.7, 1.3, x));
    const float shield = (1.0 - pow(saturate(x), 1.3)) * (1.0 - smoothstep(0.6, 1.0, x));
    return lerp(strato, shield, shape);
}

// The share of a normal deviate over t, 1 - Phi(t).
float VolcanoOver(float t)
{
    const float e = RlErf(abs(t) * 0.70710678);
    return 0.5 * (t >= 0.0 ? 1.0 - e : 1.0 + e);
}

// Its flows: tongues down its flanks, tens of metres thick, their edges rounded. A noise in polar coordinates, on a circle
// across and stretched along the slope: (k cos a, k sin a, r / along), the tongues about VOLCANO_FLOWS.x km wide (more on
// a shield) at half the radius, VOLCANO_FLOWS.y radii long, warped by a coarser noise so that they wind. They start from
// a third of the radius, where they are half as wide, never converging into strips at the summit, its cone of ash and
// scoria; their share falls from there, where they cover most of the flank, to the base, where a few long ones reach.
// Their mean is the edifice's own: the tongues rise above it, the ground between them below, so that where they start no
// step rings the summit, and where the mesh cannot carry them, nothing is left. xy: the point in the volcano's plane (km);
// share: where they lie.
float VolcanoFlows(float2 xy, float r, Volcano v, float radius, float cellKm, out float share)
{
    share = 0.0;
    const float x = r / radius;
    const float envelope = smoothstep(max(0.25 * radius, v.crater), max(0.4 * radius, v.crater + 0.1 * radius), r) * (1.0 - smoothstep(1.0, 1.15, x));
    [branch] if (envelope <= 0.0 || v.fresh <= 0.0)
        return 0.0;
    const float across = VOLCANO_FLOWS.x * (1.0 + v.shape), k = 0.5 * radius / across;
    const float wide = max(r, 0.05 * radius) / k; // the tongues' width here (km)
    const float w = RlWeight(PLANET_RADIUS_KM / wide);
    const float threshold = -0.6 + 1.9 * x;
    const float e = max(0.6, 5.0 * cellKm / wide); // their edges at least two cells wide
    float lobe = VolcanoOver(threshold + 0.5 * e);
    [branch] if (w > 0.0)
    {
        const float2 c = xy / max(r, 1e-4);
        float3 q = float3(k * c, r / max(VOLCANO_FLOWS.y * radius, 3.0)) + float3(0.5, 0.25, 0.125);
        const float3 coarse = q * float3(0.4, 0.4, 1.5);
        q.xy += 0.5 * float2(RlGradientNoise(int3(0, 0, 0), coarse, v.seed + 1u, false), RlGradientNoise(int3(0, 0, 0), coarse, v.seed + 2u, false)) / RL_SIGMA;
        const float n = RlGradientNoise(int3(0, 0, 0), q, v.seed, true) / RL_SIGMA;
        lobe = lerp(lobe, smoothstep(threshold, threshold + e, n), w);
    }
    share = lobe * envelope;
    return v.fresh * lerp(VOLCANO_FLOWS.z, VOLCANO_FLOWS.w, v.shape) * envelope * (lobe - VolcanoOver(threshold + 0.5 * e));
}

// Its field of small cones, scoria cones (Wood 1980): a lattice of VOLCANO_CONES.x km in the volcano's plane, each cell
// holding a cone at the field's share, densest within 0.6 radii and none past 1.2; each 0.25 to 0.75 km in radius, its
// height a quarter of that, a crater of 0.4 radii, a third of its height deep. Where the mesh cannot carry them, their
// mean. xy: the point in the volcano's plane (km), in doubles: up to 120 km from its summit, a float steps by 8 mm, each
// cone's flank in stairs; each cone's own plane in floats. presence: where they stand.
float VolcanoCones(double2 xy, float r, Volcano v, float radius, float cellKm, inout float presence)
{
    const float spacing = VOLCANO_CONES.x;
    const float density = v.cones * (1.0 - smoothstep(0.6, 1.2, r / radius));
    [branch] if (density <= 0.0)
        return 0.0;
    const float w = RlWeight(PLANET_RADIUS_KM / spacing);
    float h = 0.0;
    [branch] if (w > 0.0)
    {
        const float2 g = floor((float2)xy / spacing); // to a cell, the 3 x 3 around it hold the point's cones
        [loop] for (int k = 0; k < 9; ++k)
        {
            const float2 cell = g + float2(k % 3 - 1, k / 3 - 1);
            const uint hash = RlRound1(RlRound1(v.seed ^ 0x165667B1u, asuint((int)cell.x)), asuint((int)cell.y));
            const float4 u = float4(RlMix1(hash) >> 8, RlMix1(hash + 1u) >> 8, RlMix1(hash + 2u) >> 8, RlMix1(hash + 3u) >> 8) / 16777216.0;
            const float2 centre = (cell + 0.15 + 0.7 * u.yz) * spacing, local = (float2)(xy - (double2)centre);
            [branch] if (u.x >= v.cones * (1.0 - smoothstep(0.6, 1.2, length(centre) / radius)))
                continue;
            const float size = 0.25 + 0.5 * u.w, wide = max(size, 2.0 * cellKm);
            const float height = 250.0 * size * (size / wide) * (size / wide), d = length(local) / wide;
            const float t = saturate((1.0 - d) / 0.6);
            float cone = height * t * t * (3.0 - 2.0 * t);
            const float rim = 0.4 * size, rimWide = max(rim, 2.0 * cellKm), u2 = length(local) / rimWide;
            [branch] if (u2 < 1.0) // its crater, at least two cells wide, shallower when wider
                cone -= 0.35 * height * (rim / rimWide) * (rim / rimWide) * (1.0 - u2 * u2) * (1.0 - u2 * u2);
            h = max(h, cone);
            // Its share as the relief's: its area kept once widened, its edge at least two cells wide. Whole at the widened
            // size, each cone of a field stood as a disc of two cells at any distance, its edge sharper than the samples:
            // seen from orbit, the field's discs came and went as the view moved.
            const float edge = max(0.3 * wide, 2.0 * cellKm);
            presence = max(presence, w * (size / wide) * (size / wide) * saturate((wide - length(local)) / edge));
        }
    }
    // The mean: the share times a cone's mean volume, pi 0.3 E[250 s^3] km^2 m, over a cell.
    return w * h + (1.0 - w) * density * 3.1415927 * 0.3 * 250.0 * 0.156 / (spacing * spacing);
}

// A noise on the circle around a volcano, in deviations: at the direction c, its features `km` apart along a circle of
// radius `around` (km).
float VolcanoAround(float2 c, float around, float km, uint seed)
{
    return RlGradientNoise(int3(0, 0, 0), float3(c * (around / km), 0.5), seed, true) / RL_SIGMA;
}

// Its reef (Darwin 1842), set on the edifice it crowns: along the edifice's own outline, its lobes and its elongation, at
// the level where the island's shore stood, v.reef km from the summit of a round edifice; spurs and bays of a few hundred
// metres on it. Its flat 1.5 m under the sea, shallows over the sand, never a beach, 0.25 to 0.8 km wide, wider on the
// windward side, the trade winds' east; islets on it, motus, separate, most of them and the widest to windward; passes
// through it, most of them to leeward; the lagoon inside, its floor deeper or shallower by patches. Where the mesh
// cannot carry the rim's features, their mean; the flat at least two cells wide, lower when wider. xy, r: the point in
// the volcano's plane, east and north (km); lobes: the outline's radius there, over the base's.
void VolcanoReef(Volcano v, float2 xy, float r, float lobes, float cellKm, inout VolcanicFinish f)
{
    f.reef = f.lagoon = 0.0;
    [branch] if (v.reef <= 0.0)
        return;
    const float2 c = xy / max(r, 1e-4);
    const float rim = VOLCANO_REEF.z, w = RlWeight(PLANET_RADIUS_KM / rim), windward = 0.5 + 0.5 * c.x;
    const float shore = v.reef * lobes + 0.35 * rim * w * VolcanoAround(c, v.reef, 2.0 * rim, v.seed + 10u);
    const float flat0 = lerp(0.25, 0.8, windward) * (1.0 + 0.5 * w * VolcanoAround(c, v.reef, 3.0 * rim, v.seed + 11u));
    // Its edges ragged and its islets cut by a noise of the plane, VOLCANO_REEF.z / 2.5 km: grooves, spurs, islets of
    // their own shapes.
    const float wp = RlWeight(PLANET_RADIUS_KM * 2.5 / rim);
    const float ragged = wp * RlGradientNoise(int3(0, 0, 0), float3(xy * (2.5 / rim), 4.3), v.seed + 15u, true) / RL_SIGMA;
    const float cut = wp * RlGradientNoise(int3(0, 0, 0), float3(xy * (2.5 / rim), 7.9), v.seed + 16u, true) / RL_SIGMA;
    const float flat = max(flat0, 2.0 * cellKm), u = (r - shore) / flat + 0.25 * ragged;
    [branch] if (u > 1.0)
        return;
    f.reef = 1.0 - smoothstep(0.6, 1.0, abs(u));
    f.lagoon = 1.0 - smoothstep(-1.0, -0.5, u);
    // Passes where a noise along the rim is in its lowest quarter to leeward, its lowest fourteenth to windward; motus where
    // another is in its highest eighth to leeward, its highest third to windward, never in a pass, a third of the flat
    // wide in its middle: islets of 150 to 500 m across, a few km long at most.
    const float passLimit = lerp(-0.6, -1.5, windward), motuLimit = lerp(1.2, 0.3, windward);
    float open = VolcanoOver(passLimit + 0.15), motu = VolcanoOver(motuLimit + 0.15);
    [branch] if (w > 0.0)
    {
        open = lerp(open, smoothstep(passLimit, passLimit + 0.3, VolcanoAround(c, v.reef, rim, v.seed + 12u)), w);
        motu = lerp(motu, smoothstep(motuLimit, motuLimit + 0.3, 0.8 * VolcanoAround(c, v.reef, rim, v.seed + 13u) + 0.6 * cut), w);
    }
    f.crest = (lerp(-8.0, -1.5, open) + VOLCANO_REEF.x * motu * open * (1.0 - smoothstep(0.15, 0.45, abs(u + 0.15 * cut)))) * flat0 / flat;
    const float wl = RlWeight(PLANET_RADIUS_KM / (2.0 * rim));
    f.lagoonLevel = VOLCANO_REEF.y * (1.0 + 0.3 * wl * tanh(RlGradientNoise(int3(0, 0, 0), float3(xy / (2.0 * rim), 9.1), v.seed + 14u, true) / RL_SIGMA));
}

// The edifices at the unit vector `position`, to add to the large forms before the detail (Relief.hlsli): their smooth
// maximum, (sum of e^4)^(1/4), as the map's chains; a caldera's floor under the ground around it, their lowest. quiet:
// the share of the detail's relief their young flanks smooth away. finish: what VolcanoFinish applies after the detail.
// Writes gVolcanic.
float VolcanoEdifices(double3 position, float cellKm, out float quiet, out VolcanicFinish finish)
{
    quiet = 0.0;
    finish = (VolcanicFinish)0;
    finish.top = VOLCANO_NO_TOP;
    gVolcanic = 0.0;
    const uint cell = VolcanoCell((float3)position);
    const uint first = volcanoIndex[cell], last = volcanoIndex[cell + 1];
    float rise = 0.0, sink = 0.0, cones = 0.0, dominant = 0.0, presence = 0.0;
    [loop] for (uint i = first; i < last; ++i)
    {
        const Volcano v = volcanoes[volcanoIndex[i]];
        const double3 offsetD = (position - (double3)v.at) * (double)PLANET_RADIUS_KM; // km, the chord: the arc within 1e-4
        const float3 offset = (float3)offsetD;
        const float reach = max(VOLCANO_REACH.x * v.radius, VOLCANO_REACH.y), r = length(offset);
        [branch] if (r >= reach)
            continue;
        // The volcano's plane: east and north at its summit.
        const float3 east = normalize(cross(v.at, abs(v.at.y) < 0.99 ? float3(0.0, 1.0, 0.0) : float3(1.0, 0.0, 0.0)));
        const float3 north = cross(east, v.at);
        const double2 xyD = double2(offsetD.x * east.x + offsetD.y * east.y + offsetD.z * east.z,
                                    offsetD.x * north.x + offsetD.y * north.y + offsetD.z * north.z);
        const float2 xy = (float2)xyD;
        // Its edifice, at least two cells wide, lower when wider, its volume kept. Its outline as rift zones, flows and
        // flank collapses draw it: elongated along a drawn direction, up to VOLCANO_LOBES.y of its radius for a
        // stratovolcano, .z for a shield; lobed and angular, two octaves of a noise on the circle around it, VOLCANO_LOBES.x
        // at one deviation; 30 % at most. Its crater, its reef and its planed top follow it.
        const float base = min(max(v.radius, 2.0 * cellKm), reach / VOLCANO_REACH.x);
        const float height = v.height * (v.radius / base) * (v.radius / base);
        const float2 c = xy / max(r, 1e-4);
        const float angle = 6.2831853 * (float)(RlMix1(v.seed + 6u) >> 8) / 16777216.0;
        const float stretch = lerp(VOLCANO_LOBES.y, VOLCANO_LOBES.z, v.shape) * (float)(RlMix1(v.seed + 7u) >> 8) / 16777216.0;
        const float lobes = clamp(1.0 + VOLCANO_LOBES.x * (VolcanoAround(c, 1.0, 1.0, v.seed + 4u) + 0.35 * VolcanoAround(c, 2.5, 1.0, v.seed + 5u)) / 1.06
                                  + stretch * ((c.x * c.x - c.y * c.y) * cos(2.0 * angle) + 2.0 * c.x * c.y * sin(2.0 * angle)), 0.7, 1.3);
        const float radius = base * lobes, x = r / radius;
        float e = height * VolcanoProfile(x, v.shape);
        // Its crater or its caldera: the edifice drawn towards the floor, H profile(crater) - depth, a bowl for a
        // crater, (1 - u^2)^2; a flat floor between steep walls for a caldera, 1 - u^8. At least two cells wide, shallower
        // in proportion of the area when wider.
        [branch] if (v.crater > 0.0)
        {
            const float wide = max(v.crater, 2.0 * cellKm), u = r / wide;
            [branch] if (u < 1.0)
            {
                const float caldera = smoothstep(0.8, 2.5, v.crater), b = 1.0 - pow(u, lerp(2.0, 8.0, caldera));
                const float bowl = lerp(b * b, b, caldera) * (v.crater / wide) * (v.crater / wide);
                e = lerp(e, height * VolcanoProfile(v.crater / base, v.shape) - v.depth, bowl); // a level floor
            }
        }
        float flowing;
        e += VolcanoFlows(xy, r, v, radius, cellKm, flowing);
        cones = max(cones, VolcanoCones(xyD, r, v, base, cellKm, presence)); // each cone whole: its field round
        rise += e > 0.0 ? e * e * e * e : 0.0;
        sink = min(sink, e);
        // The detail quieted on young flanks. Their ground fresh: a stratovolcano's cone of ash and scoria, a shield's
        // summit, the flows.
        const float core = 1.0 - smoothstep(0.2, 1.3, x), summit = 1.0 - smoothstep(lerp(0.4, 0.15, v.shape), lerp(0.8, 0.35, v.shape), x);
        quiet = max(quiet, (0.3 + 0.5 * v.fresh) * core);
        gVolcanic = max(gVolcanic, v.fresh * max(0.8 * summit, flowing));
        // The finish follows the volcano whose edifice dominates here.
        [branch] if (e > dominant)
        {
            dominant = e;
            finish.top = v.top;
            finish.topWeight = v.top < VOLCANO_NO_TOP ? 1.0 - smoothstep(0.9, 1.05, x) : 0.0;
            VolcanoReef(v, xy, r, lobes, cellKm, finish);
        }
    }
    gVolcanic = max(gVolcanic, presence);
    return sqrt(sqrt(rise)) + sink + cones;
}

// The end of the relief, after the detail: an old island's top planed by the waves, flat under the sea, a guyot,
// rounded over it; then its reef (VolcanoReef), the lagoon inside it: a barrier reef around an island still above the sea,
// an atoll once it has sunk (Darwin 1842).
float VolcanoFinish(float h, VolcanicFinish f)
{
    [branch] if (f.topWeight > 0.0) // a smooth minimum over k m: flat on a guyot, rounded on an island
    {
        const float k = clamp(f.top, 20.0, 400.0), low = min(h, f.top) - max(k - abs(h - f.top), 0.0) * max(k - abs(h - f.top), 0.0) / (4.0 * k);
        h = lerp(h, low, f.topWeight);
    }
    h = lerp(h, max(h, f.lagoonLevel), f.lagoon);
    h = max(h, lerp(h, f.crest, f.reef));
    return h;
}

#endif
