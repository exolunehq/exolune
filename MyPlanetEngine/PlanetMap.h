// PlanetMap.h - the planet map (PlanetMap.hlsli; docs/recherche-rivieres.md, step 1): the relief's elevation on a cube
// fixed on the planet, computed once at startup on the GPU (PlanetMap.hlsl), drained here, then uploaded as a cube map.
#pragma once
#include <cstdint>
#include <vector>

namespace PlanetMap
{
    const uint32_t Size = 1024; // texels per face side, must match PlanetMap.hlsli
    const uint32_t Mips = 11;   // 1024 down to 1
    const uint32_t Cells = 6 * Size * Size; // face by face, row by row, D3D's cube map layout
    const uint32_t None = 0xffffffffu;

    struct Drainage
    {
        std::vector<float> filled;      // the surface once every pit is filled to its spill (m), 0 over the sea
        std::vector<uint32_t> receiver; // the cell each cell drains into; None for the sea, where every river ends
        std::vector<float> area;        // the area drained through each cell, its own included (km2)
    };

    // The cell's area (km2).
    double CellArea(uint32_t cell);

    // Every pit filled to its spill and every cell's way to the sea, by one Priority-Flood: the sea, where the elevation
    // e < 0, is the outlet.
    Drainage Drain(const std::vector<float>& elevation);

    // The cube map's texels, every mip, RGBA half floats (PlanetMap.hlsli), subresource after subresource (mip + face * Mips).
    std::vector<uint16_t> Texels(const std::vector<float>& elevation, const Drainage& drainage);
}
