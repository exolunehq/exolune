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
        std::vector<uint32_t> texels;
        double ms = 0.0;              // the computation's time
        float lakeShare = 0.0f, iceShare = 0.0f; // shares of the land under a terminal lake, under ice
    };

    // The level 0 of a body from its tectonic map and its form before erosion at the centres of the map's cells (m),
    // face by face, row by row.
    Map Build(const Tectonics::Map& tectonics, const Climate::Map& climate, const std::vector<float>& form, double radiusKm);

    // The map to a file, the cache per seed and the CPU port's (tools/hydro/cp.py): a header, the seed, the size and the
    // key of what it was computed from, then the texels.
    bool Save(const Map& map, uint32_t seed, uint64_t key, const std::wstring& path);

    // The map from that file when its key is `key`.
    bool Load(Map& map, uint64_t key, const std::wstring& path);

    // The cache's key: the form and climate read, the seed and the executable's time, which changes with the code.
    uint64_t Key(const std::vector<float>& form, const Climate::Map& climate, uint32_t seed, uint64_t executableTime);
}
