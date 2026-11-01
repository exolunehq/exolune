// PlanetSettings.hlsli - every setting of the planet's terrain, in one place.
// Each change is logged in docs/journal-planete.md, with its measurements and its comparisons:
// changing a value here and rebuilding brings back any logged configuration.
#ifndef PLANET_SETTINGS_HLSLI
#define PLANET_SETTINGS_HLSLI

// ---------------------------------------------------------------------------------------------
// The relief (Relief.hlsli; docs/spec-relief-tectonique.md): the large forms from the tectonic map (Tectonics.h), the
// detail from the noise of Noise.hlsli, shaped by the map's geology. Lengths in km, heights in m.
// ---------------------------------------------------------------------------------------------

// The planet's seed: its tectonic map's and its noise's.
static const int   PLANET_SEED              = 0;
// The warp of the map's reading, so that no profile looks drawn: wavelengths from RELIEF_WARP_TOP (km) halving over
// RELIEF_WARP_OCTAVES octaves, the widest displacing by RELIEF_WARP (km) at one deviation.
static const float RELIEF_WARP_TOP          = 800.0;
static const int   RELIEF_WARP_OCTAVES      = 6;
static const float RELIEF_WARP              = 30.0;
// A boundary's segments: x their wavelength (km); the noise's share of the depth, y for trenches and rifts, z for the
// ridges' axial valleys, which come and go between their offsets.
static const float3 RELIEF_SEGMENTS         = float3(120.0, 0.25, 1.0);
// A trench's profile: half-width x (km) of its walls' exponential, a floor rounded over y (km).
static const float2 RELIEF_TRENCH           = float2(22.0, 6.0);
// A slow ridge's axial valley, a fast one's dome: their half-width (km).
static const float RELIEF_RIDGE_AXIS        = 10.0;
// A rift's graben: x its half-width, y its walls' half-width (km).
static const float2 RELIEF_GRABEN           = float2(25.0, 5.0);
// A transform's trough: x its half-width in the ocean, y on a continent (km).
static const float2 RELIEF_TRANSFORM        = float2(8.0, 4.0);
// The coasts, from 60 to 3 km: near the shore the level moves by a noise, so that the coastline moves by x km at one
// deviation on a steep coast, rocky or active, by y on a flat, sedimentary one; within z km of the shore along the large
// forms' slope and w m of the sea level.
static const float4 RELIEF_COAST            = float4(12.0, 8.0, 40.0, 300.0);
// The large forms' slope at the shore (m/km), x its least; a coast flat under y, rocky over z.
static const float3 RELIEF_COAST_SLOPE      = float3(0.3, 2.0, 8.0);
// The coast's noise: x its widest wavelength (km), y its octaves, lacunarity 2.2; each octave z of the one above on a
// flat coast, w on a rocky one, more indented.
static const float4 RELIEF_COAST_NOISE      = float4(60.0, 5.0, 0.62, 0.7);
// The finer octaves' share in drowned valleys, rias and estuaries: x on a rocky coast, y on a flat one.
static const float2 RELIEF_RIAS             = float2(0.6, 0.35);
// The flat coasts' barriers, along the smooth shore: x their distance offshore (km), y their half-width (km), z their crest
// above the sea (m); they line w of the flat coasts, by patches of RELIEF_BARRIER_GAPS.x km, in islands between inlets,
// the zeros of a noise of y km. RELIEF_BARRIER_FORM: x the share of the distance lost toward an inlet, the islands' arcs
// and recurved ends; y the inlets' half-width in that noise; z the dunes' wavelength (km), the low ones letting washover
// fans into the lagoon; w the octaves of the coast's noise and of the detail the smooth shore keeps. Lagoons behind.
static const float4 RELIEF_BARRIER          = float4(2.5, 0.6, 3.0, 0.5);
static const float2 RELIEF_BARRIER_GAPS     = float2(400.0, 15.0);
static const float4 RELIEF_BARRIER_FORM     = float4(0.6, 0.15, 4.0, 3.0);
// Near a flat coast, the relief left to the noise and the badlands' fall to x of their own within y km of the shore.
static const float2 RELIEF_COAST_QUIET      = float2(0.1, 12.0);
// The detail: RELIEF_OCTAVES octaves from RELIEF_DETAIL_TOP (km) down by RELIEF_LACUNARITY, to 13.5 m.
static const float RELIEF_DETAIL_TOP        = 50.0;
static const int   RELIEF_OCTAVES           = 12;
static const float RELIEF_LACUNARITY        = 2.11;
// The warp of the detail's widest octaves: x its widest wavelength, y its displacement (km), over 3 octaves.
static const float2 RELIEF_DETAIL_WARP      = float2(60.0, 5.0);
// The widest octaves stretched along the chains: x the stretch across them, y the distance (km) past which it levels off.
static const int   RELIEF_ORIENTED_OCTAVES  = 3;
static const float2 RELIEF_ORIENTATION      = float2(2.5, 450.0);
// The chains' folds: the widest ridged octave's crests along the level lines of the distance to the boundary, x km apart
// in the short set, shifted across by y times that by a noise of z km and three times less, the same shift for both sets,
// never as steep as the distance itself, so that no crest closes on itself; w their share of the octave,
// the next two octaves' crests halved as much. A long set, RELIEF_FOLD_SETS.x times wider, takes over from the short one
// over a noise of y km: the spacing varies twice, along the folds and across, and where one set dies out the other's
// crests relay it, en échelon. Their amplitude rises and falls by RELIEF_FOLD_SADDLES.x of its mean over a noise of y km:
// strong folds, faint ones, their ends plunging. They fade out from RELIEF_FOLD_REACH.x to .y km from the boundary, the
// widest cordilleras' far side included; where the distance stops growing, halfway between two boundaries, its level
// lines close on themselves, and where it turns sharply, where the nearest boundary changes, they would bend in chevrons:
// there too, measured by its gradient, under RELIEF_FOLD_REACH.w of its length, gone under z.
static const float4 RELIEF_FOLD             = float4(26.0, 0.35, 150.0, 1.0);
static const float2 RELIEF_FOLD_SETS        = float2(2.0, 120.0);
static const float2 RELIEF_FOLD_SADDLES     = float2(0.8, 50.0);
static const float4 RELIEF_FOLD_REACH       = float4(500.0, 800.0, 0.5, 0.7);
// Each octave weakened by the slope s (m/m) of the coarser ones, 1 / (1 + k s^2): smooth slopes, detailed hollows, the look
// of erosion; k RELIEF_EROSION on the hills, RELIEF_RIDGE_EROSION on the chains, whose slopes keep their crags.
static const float RELIEF_EROSION           = 1.5;
static const float RELIEF_RIDGE_EROSION     = 0.5;
// The crests of the oldest chains rounded over this much of the noise (deviation 0.4); the young ones' stay sharp.
static const float RELIEF_OLD_CREASE        = 0.3;
// The platforms' mesas: their own hills, x their relief (m), y their widest wavelength (km), z their octaves; then the
// flat-lying strata in steps, a step (m) and its riser's share of it, x to y, drawn by step: the cliffs and the slopes.
static const float3 RELIEF_MESAS            = float3(350.0, 12.0, 7.0);
static const float RELIEF_MESA_STEP         = 120.0;
static const float2 RELIEF_RISER            = float2(0.1, 0.6);
// Badlands in soft sediments: x their gullies' relief (m), y their widest wavelength (km), z their octaves.
static const float3 RELIEF_BADLANDS         = float3(45.0, 0.6, 6.0);
// The highest summits level off from x (m) over y (m), under MAX_TERRAIN_HEIGHT.
static const float2 RELIEF_HIGHEST          = float2(8000.0, 1000.0);
// The volcanoes (Volcanoes.hlsli; docs/spec-volcanisme.md), their places and edifices drawn at startup (Tectonics.cpp).
// Their flows: tongues x km wide at half the radius, twice on a shield, stretched along the slope over y radii, z m thick
// on a stratovolcano, w on a shield, on a young edifice.
static const float4 VOLCANO_FLOWS           = float4(1.5, 0.25, 40.0, 15.0);
// Their fields of small cones: a cone at most every VOLCANO_CONES km.
static const float VOLCANO_CONES            = 2.5;
// A reef: x its islets' height above its flat, 1.5 m under the sea (m); y its lagoon (m), shallow enough for its sand to
// show, 30 % deeper or shallower by patches; z the size of its islets and passes along it (km).
static const float3 VOLCANO_REEF            = float3(4.5, -12.0, 1.5);
// An edifice's outline: x its lobes, two octaves of a noise on the circle around it, at one deviation, as a share of its
// radius; its elongation along a drawn direction, up to y of its radius for a stratovolcano, z for a shield.
static const float3 VOLCANO_LOBES           = float3(0.12, 0.1, 0.35);
// The fresh volcanic ground's soil: ash and scoria, linear reflectance, dark grey (fresh tephra 0.05 to 0.1); the share
// of the soil it covers where the ground is wholly fresh. Its rock is basalt (VertexShader.hlsl).
static const float3 VOLCANIC_ASH            = float3(0.075, 0.07, 0.068);
static const float VOLCANIC_COVER           = 0.85;

// The erosion (Erosion.hlsli, docs/spec-erosion.md). Each level 0 cell's node moves within it by up to EROSION_JITTER of
// a cell; a link's valley reaches EROSION_REACH cells at most.
static const float EROSION_JITTER           = 0.3;
static const float EROSION_REACH            = 0.6;
// The fluvial floor's half-width: x sqrt(Q) (m, Q in m3/s), widened under a slope of y up to z times.
static const float3 EROSION_FLOOR           = float3(2.0, 0.002, 15.0);
// The walls' slope, on soft ground to the young chains.
static const float2 EROSION_WALLS           = float2(0.25, 0.65);
// The glacial trough: half-width x (m) at an ice flux of 1e8 m3/yr, growing with its power y; deepened by z of its
// half-width; glacial from log2 of the flux w on. Its walls' slope.
static const float4 EROSION_GLACIER         = float4(600.0, 0.4, 0.3, 22.0);
static const float EROSION_GLACIER_WALLS    = 0.85;
// The valleys meet the coarse ground by a minimum smoothed over this (m); the coarse ground: the large forms and the
// detail's octaves wider than EROSION_COARSE (km).
static const float EROSION_SMOOTH           = 60.0;
static const float EROSION_COARSE           = 20.0;
// The gullies, from the detail's octave EROSION_GULLY_FIRST on, 11 km: EROSION_GULLY_SHARE of each octave's pattern on a
// steep ground; on a slope from x to y (m/m); none under z km. Their stripes keep their phase over EROSION_GULLY_PERIODS
// periods, 2: their lattice is the octave's, halved (Relief.hlsli).
static const int   EROSION_GULLY_FIRST      = 2;
static const float EROSION_GULLY_SHARE      = 0.85;
static const float3 EROSION_GULLY           = float3(0.02, 0.15, 0.1);
static const int   EROSION_GULLY_PERIODS    = 2;
// The stripes fade around their forks, where the sum of their waves, of unit weight, falls under this.
static const float EROSION_GULLY_FORK       = 0.3;
// Under the glaciers, the crests |x|^EROSION_GLACIAL_POWER, sharp, the troughs wide; E|cos|^power for the stripes' mean.
static const float EROSION_GLACIAL_POWER    = 0.7;
static const float EROSION_GLACIAL_POWER_MEAN = 0.7043;
// The glaciers over EROSION_GLACIAL_BAND m around the glacial maximum's equilibrium line; the folds fade where the level
// 0's valleys are deeper than x to y (m), in the chains' core.
static const float EROSION_GLACIAL_BAND     = 600.0;
// The valleys are read at a point warped by up to y km at one deviation, from x km down, so that the level 0's straight
// links wander; on a valley's walls, the detail's relief is at least EROSION_WALL_RELIEF of its depth.
static const float2 EROSION_WARP            = float2(40.0, 7.0);
static const float EROSION_WALL_RELIEF      = 0.35;
// A delta at a mouth whose discharge exceeds EROSION_DELTA_DISCHARGE (m3/s): its lobe x sqrt(Q) (m) seaward, y of that
// landward, z of it across; its plain w (m) above the sea, its front falling EROSION_DELTA_FRONT of its length per length.
static const float4 EROSION_DELTA           = float4(60.0, 0.3, 1.6, 3.0);
static const float EROSION_DELTA_DISCHARGE  = 300.0;
static const float EROSION_DELTA_FRONT      = 0.05;
// A fan at the mountain front: x sqrt(Q) (m) down its valley, y of that back up it, its cone falling z per length.
static const float3 EROSION_FAN             = float3(120.0, 0.2, 0.03);
static const float2 EROSION_FOLD_DEPTH      = float2(800.0, 2000.0);
// Wave erosion: x enables it; y is the accumulated retreat (km) at unit wave force and unit erodibility; z its maximum
// (km); w the along-coast variation, as a fraction of that distance (Sunamura 1992, force over rock resistance).
static const float4 EROSION_CLIFF_RETREAT   = float4(1.0, 1.2, 3.0, 0.45);
// The retreat noise's wavelength (km); bays displaced inland by x to y km lose their incoming waves entirely.
static const float EROSION_CLIFF_NOISE      = 2.4;
static const float2 EROSION_CLIFF_BAY       = float2(-12.0, -6.0);
// The inland reach adds x km and the detail's shoreline displacement to the retreat, capped by z km, fading over y km.
// Seaward, only the original proxy's absolute z km bound applies, with the same fade. No mesh-dependent reach.
static const float3 EROSION_CLIFF_REACH     = float3(1.0, 0.5, 8.0);
// The marine witness is at RETREAT.z km seaward on the uneroded terrain. x is its minimum water depth (m), the -50 m
// deep-sea criterion of the reach check; y is its smooth transition distance (km), converted by that coast's slope.
static const float2 EROSION_CLIFF_SEA       = float2(50.0, 0.25);
// The coastal height contour (m), from width times slope, bounded for common sea cliffs. 400 m is a calibration below
// Conachair's 426 m (NatureScot, Coastal cliffs); it is not a universal geological maximum.
static const float2 EROSION_CLIFF_HEIGHT    = float2(8.0, 400.0);
// Only detail octaves wider than this (km) set the cliff's slope: three maximum retreats, the first three octaves,
// 50, 23.7 and 11.2 km. The full ground is remapped; smaller spurs and gullies cannot move its height contour.
static const float EROSION_CLIFF_SLOPE_KM   = 9.0;
// The face's transition interval, as a share of its height, at least the height spanned by two cells on the coast.
static const float EROSION_CLIFF_FACE       = 0.1;
// Scree at 35 degrees, up to y of the contour's height, in discontinuous patches.
static const float2 EROSION_CLIFF_SCREE     = float2(0.7002, 0.22);
// The platform's foot (m), its nominal seaward slope (m/m), and maximum drop to the old shoreline (m), Trenhaile 1987.
static const float3 EROSION_CLIFF_PLATFORM = float3(-1.0, 0.02, 4.0);
// Remnants keep the original ground: half-width and noise wavelength (km), regional threshold in noise deviations.
static const float3 EROSION_CLIFF_STACK    = float3(0.065, 0.8, 1.4);
// The swell from every side, plus the directional waves; the westerlies' peak strength relative to the trades.
static const float2 EROSION_CLIFF_WAVES    = float2(0.28, 1.6);
// Highest possible terrain (m).
static const float MAX_TERRAIN_HEIGHT       = 10000.0;

// ---------------------------------------------------------------------------------------------
// Optimisations. Frequencies are on the unit sphere; NO_LIMIT switches a cap off.
// ---------------------------------------------------------------------------------------------

static const float NO_LIMIT = 3.4e38;

// The lattice split runs in double precision only for vertices with cells smaller than this, in metres.
// Farther, float's 0.4 m precision on the planet does not show. NO_LIMIT: double everywhere.
static const float EXACT_LATTICE_MAX_CELL = 4.0;

// Creases of the billow and the ridged multifractal rounded over about this many mesh cells, so that a sliding mesh does not
// make them flicker. 0 keeps them infinitely sharp. See docs/log/spec-stabilite.md.
static const float CREASE_ROUNDING = 2.0;
// The creases are never sharper than for cells of CREASE_MIN_CELL (m), however close the camera: the relief has
// no octave under 13.5 m, and a crease a few centimetres wide turned the surface's normal from one vertex to the
// next, and with it the projection of the materials' metre-high relief, raising blades along every crest.
static const float CREASE_MIN_CELL = 2.0;
// Shortest wavelength the mesh carries, in cells: each octave fades out from twice that down to it. 2 is
// the sampling limit; above, less relief detail, and less trembling (docs/log/pistes-glissement.md).
static const float MESH_BAND_LIMIT = 2.0;

// ---------------------------------------------------------------------------------------------
// Lighting
// ---------------------------------------------------------------------------------------------

// Fine detail drawn per pixel, for the wavelengths the vertex normals cannot carry without flickering:
// the slope it adds at each octave. 0 switches it off. See docs/log/spec-stabilite.md.
static const float DETAIL_SLOPE = 0.08;
// Weight of the spline normals, reconstructed per pixel from the 4 x 4 nearest vertices, against the vertex
// normals: 1 on, 0 off. See docs/spec-normales-spline.md.
static const float SPLINE_NORMALS = 1.0;
// 1: the materials and the fine detail are looked up on the spline surface, where the view ray meets it,
// rather than on the triangle. 0: on the triangle.
static const float SPLINE_SURFACE = 1.0;
// The fine grid's normals (docs/spec-rendu-lointain.md, step 2) light the ground from face cells of this size (m), fully
// at twice it; below, the spline normals and the grain. The materials' decisions take the fine grid down to cells of
// 3.4 m (FineMinCell, D3DApp.h). Lit by it down there too, crests drew thin lines, the scale ladder's gap p95 at 800 m
// rose by 1 dB on snow and soil, and the flicker at 1.3 km by 40 % (docs/journal-planete.md, 2026-10-24).
static const float FINE_LIGHT_MIN_CELL = 20.0;
// The materials are decided on a normal across at least this much either way (m), read on the mesh's surface: across two
// cells of a few centimetres, the vertices' normal followed the mesh's millimetres, and snow and rock flickered as it slid
// (VertexShader.hlsl). The relief's finest octave, 13.5 m, keeps 96 % of its slope across it.
static const float DECISION_BASELINE = 1.0;
// The beach's width follows the slope across its own width, not the metre's bumps. Read the shore normal across
// at least this much either way (m) on the mesh's surface (VertexShader.hlsl).
static const float SHORE_BASELINE = 60.0;
// The relief's finest octave (m), RELIEF_DETAIL_TOP over RELIEF_LACUNARITY^11: the detail fades out below.
static const float DETAIL_MIN_WAVELENGTH = 13.5;
// Widest wavelength of the fine detail drawn per pixel (m): the relief's octaves under it.
static const float DETAIL_MAX_WAVELENGTH = 6000.0;
// Close-up textures of the materials, colour and slope, below the terrain's finest octave: grass and rock
// so far. 1 on, 0 off.
// See docs/log/spec-rendu.md, step D.
static const float TEXTURE_DETAIL = 1.0;
// The materials' fine tiles, 1 mm per texel (docs/spec-textures-generees.md): 1 lays them on the coarse ones
// near the camera, 0 leaves them out.
static const float TEXTURE_FINE = 1.0;
// The relief's shadow, on the ground and in the air (Shadows.hlsli): each step of the march toward the sun, this share
// of the distance already marched. The ground's horizon counts a height missed between two steps over its distance; the
// air's shadow height counts it whole. 0.05 gave the ground the same shadows, but the shafts trembled more than with
// the polar grid's half cells (docs/journal-planete.md, 2026-10-25).
static const float HORIZON_STEP = 0.02;
// Ledges (docs/spec-roche-organique.md, step 1): the flatness of the rock's own surface, the cosine of its slope,
// over which scree, then soil, covers it.
static const float2 LEDGE_SCREE = float2(0.72, 0.82);
static const float2 LEDGE_SOIL = float2(0.84, 0.92);
// The rock texture's slope, its deviation along each axis: how it spreads the ledges far away, where the mips lose it.
static const float STONE_SLOPE_SIGMA = 0.6;
// The beach (Materials.hlsli, docs/recherche-cotes.md): x the berm's height (m), y its softness on either side (m),
// z the maximum width (m), w the exposure factor of a sheltered coast. On very flat coasts, both height and softness
// shrink with the width cap; the coast's exposure scales them together.
static const float4 BEACH = float4(2.5, 1.0, 120.0, 0.4);
// The beach's slope limit, from fully sandy to too steep, as tangents of the slope angle.
static const float2 BEACH_SLOPE = float2(0.12, 0.22);
// The fetch samples' distances offshore (km), along the ground normal's horizontal component on the sphere.
static const float3 BEACH_FETCH = float3(3.0, 10.0, 30.0);
// The strata's perturbation (Materials.hlsli, StrataShift): the beds' slope scale in their 8 km octave, 15 % less at
// each octave down to 4 m. It replaced a regional dip and folds, which left the other regions' beds level.
static const float STRATA_SLOPE = 0.4;
// The materials' detail bands (Materials.hlsli, DetailBands; docs/spec-texturage-universel.md), the scales their
// other sources leave empty, measured by tools/valide_bandes.py: x, y the log2 of their finest and widest wavelengths
// (m); z the slope of each octave, about -49 dB of contrast for 0.05; w its colour change, about -40 dB for 0.04.
// Snow, 1 cm to 16 m: it had no detail at all; beyond, it smooths the ground, which the relief draws.
static const float4 SNOW_BANDS = float4(-6.6439, 4.0, 0.08, 0.015);
// Sand, 50 cm to 32 m: its photo stops at 50 cm, the relief's light starts at 16 m.
static const float4 SAND_BANDS = float4(-1.0, 5.0, 0.05, 0.04);
// Grass, 25 cm to 128 m: between its tufts and patches, and from its 4 m bumps up to the relief's light.
static const float4 GRASS_BANDS = float4(-2.0, 7.0, 0.06, 0.2);
// Rock, 8 to 64 m, above its photos, in place of the drawn 64 m tile, their slope carried on: STONE_SLOPE_SIGMA
// over thirteen octaves, 0.12 per axis and octave, the noise's gradient 0.5 per axis. Far away, the rule takes those octaves
// as there (RockShares); at 0.05 near the camera, they were not, and every face was its photo's even carpet.
static const float4 ROCK_BANDS = float4(3.0, 6.0, 0.24, 0.06);
// Scree, 4 to 64 m: its tile stops at 4 m.
static const float4 SCREE_BANDS = float4(2.0, 6.0, 0.05, 0.06);
// Bare soil, 50 cm to 64 m, over the sandy gravel's photo: where it is too dry for grass and too damp or cold for sand,
// the ground had no texture at all.
static const float4 SOIL_BANDS = float4(-1.0, 6.0, 0.05, 0.05);
// How far a formation's tint strays from its group's, 0 to 1: colours change by great masses.
static const float STRATA_FORMATION_CONTRAST = 0.3;

// ---------------------------------------------------------------------------------------------
// Objects near the camera (docs/spec-objets-proximite.md): the ground's detail, the small loose things lying on it, each
// at a fixed place on the planet's lattice: stones and pebbles, grass tufts. Bedrock and its relief are the geometry's.
// One lattice level per octave of sizes: octave k holds objects of 2^k to 2^(k+1) m. Stones: one candidate in each cell
// of 4 x 2^k m. Tufts, denser: cells of 2 x 2^k m, in windows twice as many cells wide (D3DApp must match).
// ---------------------------------------------------------------------------------------------

static const int2 OBJECT_OCTAVES = int2(-5, 0);
static const int2 TUFT_OCTAVES = int2(-3, -2);
// Where debris lies at all: a field of the planet's gradient noise, regions of 0.5 to 32 km, of deviation 0.29, raised by
// OBJECT_STONY.z times what strips the ground of its fines or feeds it debris: three times the scree's share, bare ground
// the drier, the slope's tangent. Debris from OBJECT_STONY.x, wholly past y: none on 80 % of the meadows, half the dry sands
// and soils, a tenth of the scree; stony regions, patches of it.
static const float3 OBJECT_STONY = float3(0.27, 0.42, 0.22);
// The ground cover of each ground, where it is stony, as the two reference photos count it, at their low end
// (cible-sol-*.jpg, docs/spec-objets-proximite.md). Gravel under 3 cm is the textures' (FINE_TILE), not objects.
// Sand and bare soil: pebbles, PEBBLES.x of the ground per octave, fading past PEBBLES.y m: small ones common, larger
// ones less, cobbles rare; in clumps.
static const float2 PEBBLES = float2(0.02, 0.08);
// Grass: rocks half-buried in the soil in patches, Golombek and Rapp's law (below) at the abundance GRASS_ROCKS.
static const float GRASS_ROCKS = 0.03;
// Scree, ledges included, and rockfall at the true foot of cliffs: Golombek and Rapp's law, measured on Earth and Mars,
// the rocks of width D or more covering k exp(-q D) of the ground, q = 1.79 + 0.152 / k; k the abundance, x on scree, y
// at the foot of ground steeper than 35 to 45 degrees, where the ground eases under OBJECT_GATHER degrees.
static const float2 DEBRIS_ABUNDANCE = float2(0.05, 0.25);
static const float2 OBJECT_GATHER = float2(10.0, 20.0);
// Tufts: the share of the ground they cover in each octave, x in grass, y on sand and bare soil, dry and few.
static const float2 TUFT_COVER = float2(0.2, 0.01);
// The ground's form, read over OBJECT_LANDFORM m around a stone: the mean slope above it, and its curvature, the
// Laplacian of the height (1/m). Below -OBJECT_CREST.x, from x to y, a crest or a cliff top, which loose debris leaves:
// a share OBJECT_CREST.z of scree's and rockfall's there.
static const float OBJECT_LANDFORM = 16.0;
static const float3 OBJECT_CREST = float3(0.004, 0.02, 0.1);
// Rocks lie in patches: a field of the planet's gradient noise, 8 to 64 m, keeps them where it passes OBJECT_PATCHES.x,
// wholly past y; z its mean over the ground, which the patches gather without changing. Pebbles and tufts clump, softer:
// OBJECT_CLUMPS.z times their mean where the field is under OBJECT_CLUMPS.x, 2 - z times past y.
static const float3 OBJECT_PATCHES = float3(0.05, 0.25, 0.26);
static const float3 OBJECT_CLUMPS = float3(-0.15, 0.15, 0.4);
// No loose rock rests past its angle of repose: OBJECT_REPOSE.x degrees for the smallest octave, OBJECT_REPOSE.y fewer at
// each octave up, as a talus sorts its blocks; the share fades over OBJECT_REPOSE.z degrees below.
static const float3 OBJECT_REPOSE = float3(38.0, 1.0, 3.0);
// The share of an object's height under the ground: x on bare rock, barely seated, y on soft ground, soil, sand, grass,
// scree's fines, half buried; never less than z m, more than the gap measured to the ground the mesh draws.
static const float3 OBJECT_BURIAL = float3(0.08, 0.4, 0.003);
// An object appears as it spans OBJECT_PIXELS.x pixels on screen, growing out of the ground to its whole size at
// OBJECT_PIXELS.y: no pop, and no object under the pixel's size.
static const float2 OBJECT_PIXELS = float2(6.0, 9.0);
// And only where the mesh carries its foot: where the mesh's cells are under OBJECT_CELLS.y times its width, whole under
// OBJECT_CELLS.x. Coarser cells draw the ground too far from the exact one: up to 84 cm under 2 m blocks seen from 200 m,
// in cells of 4 m (docs/spec-objets-proximite.md).
static const float2 OBJECT_CELLS = float2(1.0, 1.5);

// ---------------------------------------------------------------------------------------------
// Vegetation (docs/recherche-vegetation.md): trees and shrubs from the climate, objects near the camera on the same
// lattice, the ground's canopy beyond. Every value below comes from a published law or a measure; the doc gives each.
// ---------------------------------------------------------------------------------------------

// The seasons: the annual cycle's half amplitude comes from the climate map (Climate.hlsli); a sine around the annual mean
// gives the growing season of 92 % of the Earth's land cells as their months do (tools/saisons_terre.py).
// The tree line (Körner and Paulsen 2004, Paulsen and Körner 2014): trees need a growing season, the days over 0.9 C, of
// 6.4 C on average; the sites spread by 0.7 C around it, the width of the change from forest to none.
static const float  TREE_SEASON_START = 0.9;
static const float2 TREE_LINE = float2(5.7, 7.1);
// The water: woody cover's ceiling, 0.14 MAP - 14.2 % from 101 to 650 mm in African savannas (Sankaran et al. 2005),
// written with the aridity, precipitation over Holdridge's potential evapotranspiration, 58.93 mm per degree of
// biotemperature: 1414 mm at their 24 C (TREE_CEILING); the savanna's trees cover at most its mode, 20 %.
static const float2 TREE_CEILING = float2(1.98, 0.142);
// The land in three states (Hirota et al. 2011, fig. 1B, MODIS tree cover from 35 S to 15 N): treeless, under 5 % of tree
// cover; savanna, about 20 %; forest, about 80 %. The treeless share falls from 0.95 at 300 mm to 0.05 at 1500 mm, never
// under 0.02: a logistic of centre x and width y mm, floor z. The forest's rises from 0.1 at 1500 mm to 0.5 at 2100 and
// 0.9 at 3000: centre and width; none under z mm, where forest and savanna are not yet bistable (Staver et al. 2011): the
// logistic's tail left deserts a forest's patches. Savanna the rest. Written with the aridity at their evapotranspiration,
// 1414 mm.
static const float3 TREELESS_RAIN = float3(820.0, 190.0, 0.02);
static const float3 FOREST_RAIN = float3(2100.0, 380.0, 1000.0);
static const float2 TREE_COVER_MODES = float2(0.2, 0.8);
// Where each state lies (Vegetation.hlsli, WoodsAt): two fields of the planet's gradient noise, as the stones' regions and
// patches (OBJECT_STONY, OBJECT_PATCHES), each above the threshold that leaves its state its share. The regions', from
// PRESENCE_SCALES.x m down to 8 m: the woods, savanna or forest, the rest of the land without a tree, whatever its ground;
// regions of tens of km, patches whose sizes follow a power law, as forests' do (Taubert et al. 2018, exponent 1.9 to 2.0).
// The patches', from y m down to 8 m, within the woods: the forest's stands, the rest its clearings, of 30 m to 1 km, in
// every forest. Within the stands, the crowns cover STAND_COVER of the ground; the stands fill the share of the forest's
// land that gives its mode, 80 %: at least a tenth of any forest is clearings.
static const float2 PRESENCE_SCALES = float2(32768.0, 1024.0);
static const float STAND_COVER = 0.9;
// Shrubs (a patches' field of their own, the same rule): thickets on SHRUB_LAND of the land, the rest bare of them; where
// they are, they cover SHRUB_COVER.x of the ground in deserts (Larrea, 14 % alone, 24 % with the others, Santa Rita), y in
// dry lands' scrub (chaparral, 60 to 100 %), z in humid lands' clearings and woods; under a forest's canopy, w, the
// understorey. From the hyper-arid's none (aridity SHRUB_ARIDITY.x to y), dry to humid from z to w. The land's share and
// the humid lands' and the understorey's cover are estimates, to check on photos.
static const float  SHRUB_LAND = 0.5;
static const float4 SHRUB_COVER = float4(0.2, 0.6, 0.35, 0.25);
static const float4 SHRUB_ARIDITY = float4(0.03, 0.12, 0.3, 1.0);
// The forest's edge: its mantle of shrubs, where the stands, seen at FOREST_EDGE.x m, are neither in nor out: shrub belts
// of 5 to 10 m, whole edges of 25 to 40 m (Swiss and Austrian forest edge guides); the shrubs' field raised there by y
// deviations, a mantle on nearly every edge.
static const float2 FOREST_EDGE = float2(32.0, 2.0);
// Above the tree line, the krummholz: shrubs and stunted trees over a band of 300 m and more (Swiss tree line transition
// zone), 1.5 C of growing season at 5 C per km: the shrubs' cold limit under the trees'.
static const float  SHRUB_LINE_OFFSET = 1.5;
// Ridges and summits, hollows: the ground's height over the planet map's at 16 km (PlanetMap.hlsli), over EXPOSURE_RELIEF
// m, from -1 in hollows to 1 on ridges. Exposed ground loses its trees first: the tree line 70 to 130 m lower on wind-swept
// convex ground than in hollows (Broll et al. 2007), 100 to 250 m under the local summit (Case and Buckley 2015), so the
// growing season EXPOSED_SEASON C colder at full exposure, warmer in hollows; and both woods' fields lowered by
// EXPOSED_DRIVE deviations there, raised in hollows (an estimate; curvature leads tree line models, Case and Buckley 2015):
// a humid forest keeps a fifth of its trees on a full ridge, fills its hollows.
static const float  EXPOSURE_RELIEF = 300.0;
static const float  EXPOSED_SEASON = 0.5;
static const float  EXPOSED_DRIVE = 2.0;
// The canopy's height (m): its top, in a warm and wet climate, 40 m (tropical forests, Lang et al. 2023), less with the
// growing season's warmth and with the water, to 15 to 20 m in the boreal forest and 8 to 12 m in savannas (Simard et al.
// 2011, Tallo); the trees' heights spread around 0.7 of it by PLANT_HEIGHT_SPREAD octaves. Shrubs about 1.5 m (Larrea).
static const float  CANOPY_HEIGHT = 40.0;
static const float  SHRUB_HEIGHT = 1.5;
static const float  PLANT_HEIGHT_SPREAD = 0.6;
// A canopy's own colour, linear reflectance: the Amazon's, the dark anchor of the climate's palette (tools/palette_biomes.py,
// from satellite measures), for a broadleaf canopy. Conifers' darker, about 0.7 of it as their albedos are (Cescatti et al.
// 2012: evergreen needleleaf forests 0.05 to 0.11, deciduous broadleaf 0.11 to 0.15). Dry lands' shrubs, sclerophylls and
// desert shrubs, grey and olive, lighter than a forest's canopy: SHRUB_ALBEDO, an estimate to check on photos. The open
// land keeps the climate's colour (BiomeColor).
static const float3 CANOPY_ALBEDO = float3(0.03, 0.06, 0.025);
static const float2 PLANT_TINT = float2(0.7, 1.0);
static const float3 SHRUB_ALBEDO = float3(0.055, 0.063, 0.042);
// Seen from the side, the drawn plants show their crowns' shaded flanks and the shade under their neighbours: their light,
// over the ground's canopy's, measured against the view's elevation e (tools/banc_vegetation.py relais, two forests, two
// suns), is 1 - x (1 - sin e)^y, the canopy's light so (PixelShader.hlsl): 1 from above, 0.85 at 5 degrees.
static const float2 CANOPY_SIDE_LIGHT = float2(0.2, 3.0);
// The ground's canopy beyond the objects, its crowns' relief and colour from 2 to 16 m, per octave (DetailBands): slope,
// colour change.
static const float2 CANOPY_RELIEF = float2(0.6, 0.2);
// The plants are objects on the planet's lattice, one octave of heights per level, from 0.5 to 64 m: a candidate in each
// cell of a quarter of the octave's height. They are drawn from 5 pixels high (Vegetation.hlsli, PlantPixelRange); the
// ground's canopy shows the rest. Their reach in pixels keeps their number, and the placement's cost, in hand.
static const int2   PLANT_OCTAVES = int2(-1, 5);
// The far ones, under PLANT_LOD_PIXELS.y pixels high, stand on the ground the mesh draws; from y up to x, they move to the
// exact ground (PlantPlacement.hlsli).
static const float2 PLANT_LOD_PIXELS = float2(64.0, 48.0);

// ---------------------------------------------------------------------------------------------
// Atmosphere: the Earth's, after Hillaire 2020. Distances in km, coefficients per km.
// See docs/log/spec-rendu.md, step B.
// ---------------------------------------------------------------------------------------------

static const float  PLANET_RADIUS_KM       = 6378.0; // must match D3DApp::PlanetRadius
static const float  ATMOSPHERE_HEIGHT_KM   = 100.0;
static const float3 RAYLEIGH_SCATTERING    = float3(5.802e-3, 13.558e-3, 33.1e-3);
static const float  RAYLEIGH_SCALE_HEIGHT  = 8.0;
// The aerosols (docs/recherche-profondeur-atmospherique.md): one setting, the meteorological visibility at sea level
// (km), the distance at which a black object keeps 2 % of its contrast against the horizon (Koschmieder: 3.912 over the
// extinction at 550 nm). Bruneton's demo air, which Hillaire and Unreal keep, gave 217 km: the air of a very clear
// mountain day, where an ordinary fine day gives 20 to 60 km, and the planes did not part. Their extinction, the
// visibility's less Rayleigh's at 550 nm; scattering 90 % of it; their colour after Angstrom's law, an exponent of 1.3,
// as the continents' aerosols; their phase a little less forward than the demo's 0.8.
static const float  VISIBILITY_KM          = 40.0;
static const float3 MIE_EXTINCTION         = (3.912 / VISIBILITY_KM - 13.558e-3) * float3(0.7590, 1.0, 1.3366); // 680, 550, 440 nm
static const float3 MIE_SCATTERING         = 0.9 * MIE_EXTINCTION;
// They fill the boundary layer, mixed by day from the ground up to its top, HAZE_TOP_KM, where they thin out over about
// HAZE_TOP_WIDTH_KM: the band of haze seen from a plane, and its clear air above (the demo's exponential of 1.2 km left
// only 4 % of it to a ground at 4 km). At 40 km of visibility, an optical depth of 0.17, near the continents' 0.19.
static const float  HAZE_TOP_KM            = 2.0;
static const float  HAZE_TOP_WIDTH_KM      = 0.3;
// The layer stands on the regional ground, the planet map's smoothed over this deviation (km; Atmosphere.hlsli,
// RegionalGround): a plateau much wider than the layer is deep grows its own, a ridge or a valley a few times its depth
// does not, and the layer's top stays level over them (De Wekker and Kossmann 2015). At 10 km, a 100 km plateau keeps 82 %
// of its height, a range of ridges 20 km apart under 1 %: the haze thins over the summits and fills the valleys.
static const float  HAZE_GROUND_SCALE_KM   = 10.0;
static const float  MIE_ASYMMETRY          = 0.7;
static const float3 OZONE_ABSORPTION       = float3(0.650e-3, 1.881e-3, 0.085e-3);
static const float  OZONE_CENTRE_KM        = 25.0; // tent profile, 30 km wide
static const float  OZONE_HALF_WIDTH_KM    = 15.0;
static const float  GROUND_ALBEDO          = 0.3;  // for the light the ground sends back into the sky
// Clear-sky planetary mean: 70% ocean at 0.06, land near 0.25.
// ponytail: use regional ocean or land albedo if deserts or the sea require it.
static const float  AIR_GROUND_ALBEDO      = 0.12;
// Sun illuminance at the top of the atmosphere: pi, so that a white surface facing the sun outside
// the atmosphere has radiance 1.
static const float3 SUN_ILLUMINANCE        = float3(3.14159, 3.14159, 3.14159);
static const float  SUN_ANGULAR_RADIUS     = 0.004675; // rad, the Sun seen from the Earth

// ---------------------------------------------------------------------------------------------
// The sea (Sea.hlsli, docs/recherche-mer.md)
// ---------------------------------------------------------------------------------------------

// The FFT spike has its own spectrum constants (OceanUniform.hlsli and Ocean.cpp).
// Whitecaps' reflectance: 0.22 on average, fresh foam and old (Koepke 1984), slightly less in the red (Frouin 1996).
static const float3 FOAM_ALBEDO           = float3(0.196, 0.22, 0.22);

// ---------------------------------------------------------------------------------------------
// Optics: the lens's glare (GlareDown.hlsl, GlareUp.hlsl; docs/recherche-halo.md)
// ---------------------------------------------------------------------------------------------

// The straylight parameter s = theta^2 L / E, in deg^2/sr: a point source of illuminance E veils the image at theta
// degrees from it with a luminance s E / theta^2. The law of the far glare of the eye (Stiles-Holladay, CIE) and of the
// scatter of polished optics (Harvey). 0.3: a recent camera lens, 0.13 to 0.19 % of veiling glare (ISO 18844, Koren
// 2018). The camera systems measured by McCann and Rizzi give 1.4 to 11, a young eye 10, which the viewer's own eye
// already adds to what the screen shows. 0 switches the glare off.
static const float  GLARE_STRAYLIGHT       = 0.3;

// ---------------------------------------------------------------------------------------------
// Tones: from the scene's light to the screen (ToneMap.hlsl, docs/recherche-tons-exposition.md).
// ---------------------------------------------------------------------------------------------

// The exposure follows the daylight under the camera, as an incident light meter turned towards the sun: a grey card
// facing the sun shows its reflectance, then this compensation, in stops, as on a camera. One stop brings the median
// ground of our day views to that of the sunny photos, docs/images/cible-*.jpg (tools/banc_tons.py).
static const float  EXPOSURE_COMPENSATION  = 1.0;
// Photos of the Earth from space expose for its clouds: 0 stop, measured on Apollo 17's Blue Marble.
static const float  EXPOSURE_COMPENSATION_ORBIT = 0.0;
// The film curve's contrast: its slope in the shadows, in stops of the screen per stop of the scene; 0.82 of it through
// the grey card. 1 adds none. 1.5 puts 1.23 through the grey card: the contrast an image needs on a screen in a dim
// room, 1.2 to 1.25 (Hunt; ITU-R BT.2100), under ACES 1's 1.55.
static const float  FILM_CONTRAST          = 1.5;

#endif
