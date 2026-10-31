// Climate.h - a body's climate (docs/spec-climat.md): its prevailing winds, the moisture they carry from the seas and rain
// out on the slopes facing them, its temperatures and their seasons, computed once per seed at startup from the tectonic
// map's large forms (Tectonics.h), on a cube fixed on the body. The ground's materials and plants read it (Climate.hlsli),
// the CPU through At, the CPU port and the level 0 through the file beside the executable (tools/hydro/cp.py).
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace Tectonics { struct Map; }

namespace Climate
{
    const uint32_t Size = 256; // texels per face side: 50 km at a face's centre, 22 km in its corners
    const uint32_t Mips = 9;   // 256 down to 1

    // Each texel's fields, in this order; Climate.hlsli has the same, two RGBA cubes.
    enum Field : uint32_t
    {
        Precipitation,  // the year's (mm)
        Temperature,    // the year's mean at sea level (C): the ground's subtracts its lapse rate
        Amplitude,      // the seasons' half amplitude (C), the mean of the warmest month less the year's
        Summer,         // the share of the year's precipitation that falls in the warm half of the year
        WindEast,       // the year's mean surface wind (m/s), towards the east and the north
        WindNorth,
        Continentality, // 0 over the sea to 1 where no sea air reaches
        Upwelling,      // the sea's temperature lowered by the cold currents (C), <= 0
        Channels
    };

    struct Map
    {
        uint32_t size = 0;
        std::vector<float> cells; // Channels floats per texel, face by face, row by row: D3D's cube map layout
        double ms = 0.0;          // the computation's time
    };

    Map Build(const Tectonics::Map& tectonics, double radiusKm);

    // The fields at the direction d, not necessarily normalised: bilinear on the face holding d, the texels past its edge
    // taken on the next face. For the level 0 and the CPU tools.
    void At(const Map& map, const double d[3], float fields[Channels]);

    // The two cubes' texels, every mip, RGBA half floats, subresource after subresource (mip + slice * Mips): slices 0 to
    // 5 the first four fields, 6 to 11 the next four.
    std::vector<uint16_t> Texels(const Map& map);

    // The map to a file, for the CPU port (tools/hydro/cp.py): a header, then the fields as floats.
    bool Save(const Map& map, uint32_t seed, const std::wstring& path);

    // The clouds' weather map (Clouds.hlsli, t27; docs/spec-nuages.md), from the climate and the large forms: the ITCZ's
    // convection, the subtropical highs' clear skies, the stratocumulus off the cold coasts, the storm tracks' cyclones,
    // the windward slopes' banks. RGBA8, latitude and longitude, row 0 north, x fastest, mip after mip down to 1 x 1: R the
    // low clouds' coverage, G their family, 0 a sheet to 1 a cumulus, B the cirrus; from mip 2, R and B the maxima.
    const uint32_t WeatherWidth = 1024, WeatherHeight = 512, WeatherMips = 11;
    // cyclones, if given, receives each cyclone's latitude and longitude (degrees), scale (km) and stage, 0 a wave to 1 occluded.
    std::vector<uint8_t> Weather(const Map& climate, const Tectonics::Map& tectonics, uint32_t seed, double radiusKm,
                                 std::vector<float>* cyclones = nullptr);
}
