// Erosion.h - the erosion's level 0 (docs/spec-erosion.md): on the tectonic map's cube, once per body at startup, the
// drainage to the sea, the lakes by their water balance, the discharge, the water's level by the stream power's steady
// state, the glaciers' ice flux. Relief and inland water share this network (Erosion.hlsli).
// Exolune's own code, from the papers cited in the spec.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace Tectonics { struct Map; }
namespace Climate { struct Map; }

namespace Erosion
{
    constexpr uint32_t Slices = 24;
    // A cell's two words, the texture's texel (Erosion.hlsli has the same layout):
    // - x: the water's level at the cell's node, bits 0-15, and the ground's, bits 16-31, both (m + 8192) x 4;
    // - y: bits 0-2 the receiver among the 8 neighbours, bit 3 set when there is one; bits 4-11 the neighbours that drain
    //   into it; bit 12 a lake, 13 the sea, 14 a fan's apex, 15 a mouth; bits 16-23 the discharge,
    //   8 (log2 Q + 8), Q in m3/s; bits 24-31 the ice flux, 0 without ice, else 1 + 6 (log2 I - 10), I in m3/yr.
    enum Bits : uint32_t { HasReceiver = 8, Lake = 1u << 12, Sea = 1u << 13, Fan = 1u << 14, Mouth = 1u << 15 };

    struct Map
    {
        uint32_t size = 0;            // cells per face side, the tectonic map's
        // First six slices: the two network words above. Next six: terminal lake stage (Level16) and basin ID.
        // ID zero drains to the ocean; a lake's stage is constant across its complete catchment.
        // Their high halves, step B's courses (docs/spec-erosion.md, the corridors): x bits 16-31 the conditioned stage at
        // the node (Level16; the level 0's until Condition); y bits 0-15 the basin ID, at most 65535, bits 16-23 the
        // corridor's wall width / 25 m, bits 24-27 the meanders' sinuosity from RIVER_SINUOUS.z to 1 in 15 steps, bits
        // 28-31 log2 of the valley floor's factor over RIVER_FLOOR_LOG2 in 15 steps (PlanetSettings.hlsli).
        // Next six: four UNORM16 first-water limits, main upstream/downstream halves, connector and outlet.
        // Last six: effective node and outgoing-midpoint discharge bytes, and original local runoff (float m3/s).
        std::vector<uint32_t> texels;
        double ms = 0.0;              // the computation's time
        float lakeShare = 0.0f, iceShare = 0.0f; // shares of the land under a terminal lake, under ice
    };

    // The level 0 of a body from its tectonic map and its form before erosion at the centres of the map's cells (m),
    // face by face, row by row.
    Map Build(const Tectonics::Map& tectonics, const Climate::Map& climate, const std::vector<float>& form, double radiusKm);

    // Step B: what ErosionStages.hlsl measures along each cell's courses, and ErosionNodes.hlsl's pair per cell, the
    // sinuosity's and floor's byte with the erodibility x 64 above it, and the relief amplitude's float bits.
    struct Course { float main, connector, relief; uint32_t flags; float length; };
    enum CourseFlags : uint32_t { MainCourse = 1, LargestInflow = 2, Rerouted = 4 };
    struct Contacts { float upstream, downstream, connector, outlet; };

    // The sinuosity's and floor's bytes into the map.
    void SetSinuosity(Map& map, const std::vector<uint32_t>& nodes);

    // The courses' stages conditioned on the relief they cross, as tools/hydro/couloirs.py's condition: never above the
    // lowest relief met upstream plus a fill, drops spread upstream; and their corridors' wall widths.
    void Condition(Map& map, const std::vector<Course>& courses, const std::vector<uint32_t>& nodes);
    void StopAtWater(Map& map, const std::vector<Contacts>& contacts, const std::vector<Course>& courses);

    // The map to a file, the cache per seed and the CPU port's (tools/hydro/cp.py): a header, the seed, the size and the
    // key of what it was computed from, then the texels.
    bool Save(const Map& map, uint32_t seed, uint64_t key, const std::wstring& path);

    // The map from that file when its key is `key`.
    bool Load(Map& map, uint64_t key, const std::wstring& path);

    // The cache's key: the form and climate read, the seed and the executable's time, which changes with the code; and the
    // startup passes' compiled shaders, which change with their settings.
    uint64_t Key(const std::vector<float>& form, const Climate::Map& climate, uint32_t seed, uint64_t executableTime,
                 uint64_t passes);
}
