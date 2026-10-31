// Tectonics.h - a body's tectonic map (docs/spec-relief-tectonique.md): its continents, its plates, their motions and their
// typed boundaries, computed once per seed at startup on a cube fixed on the body; then the fields the relief reads
// (Relief.hlsli), the diagnostic views and the level 0's inputs, uploaded as texture arrays (Tectonics.hlsli). One map per
// body, every body of the system at startup: the camera can cross the system in one frame, nothing is computed on the way.
#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace Tectonics
{
    // All the map depends on: the same body gives the same map.
    struct Body
    {
        uint32_t seed;
        double radiusKm;
    };

    // A boundary's type, from the plates' relative motion and the crusts on either side; Tectonics.hlsli has the same numbers.
    enum Boundary : uint8_t { OceanUnderContinent, OceanUnderOcean, Collision, Ridge, Rift, Transform };
    // The rock at the surface, by class; Tectonics.hlsli has the same numbers.
    enum Rock : uint8_t { OceanicCrust, Volcanic, YoungBelt, Sediments, OldBelt, Shield };

    // Each face's texels are padded by Pad on every side with the fields beyond its edges, so that a cubic B-spline reads one
    // face only; the shader blends the faces near their edges. Slices per face (Tectonics.hlsli has the layout): 0 the large
    // forms, 1 the boundaries' sharp profiles, 2 the transforms and the classes, the relief's, uploaded; 3 the diagnostics
    // and the uplift, 4 the erodibility, for the CPU port and the level 0. The views read slice 3 from a copy at a quarter
    // of the resolution, ViewPad texels of padding.
    const uint32_t Pad = 4, Slices = 5, ReliefSlices = 3, ViewScale = 4, ViewPad = 1;

    struct Plate
    {
        float pole[3];    // the Euler pole, a unit vector in the body's frame
        float rate;       // the rotation about it (rad/Ma)
        float area;       // its share of the surface
        float continental; // its share of continental crust
    };

    // A volcano (docs/spec-volcanisme.md), as the shader reads it (Volcanoes.hlsli): its edifice, its crater, its flows and
    // its field of small cones, evaluated point by point around it.
    struct Volcano
    {
        float at[3];   // its summit's direction, a unit vector in the body's frame
        float radius;  // its base's radius (km)
        float height;  // its height above the ground around it (m)
        float shape;   // its profile: 0 a stratovolcano's, concave, to 1 a shield's, convex
        float crater;  // its crater's or its caldera's radius (km), 0 none
        float depth;   // its crater's depth under the rim (m)
        float top;     // the level its top was planed to, a guyot's or an eroded island's (m above the sea); NoTop none
        float reef;    // the radius of the reef around it, an atoll's or a barrier's (km), 0 none
        float cones;   // its field of small cones: the share of the field's cells that hold one, 0 none
        float fresh;   // 1 a young edifice, its lava and its ash bare, to 0 an old one, weathered
        uint32_t seed; // its flows' and its cones' draw
    };
    static_assert(sizeof(Volcano) == 52, "Volcanoes.hlsli reads the same layout");
    const float NoTop = 1e9f;
    // The volcanoes' index: a cube of VolcanoGrid^2 cells per face, each listing the volcanoes that reach it.
    const uint32_t VolcanoGrid = 64;

    struct Map
    {
        uint32_t size = 0;           // texels per face side, padding left out
        std::vector<Plate> plates;
        float continental = 0.0f;    // the share of the surface under continental crust
        // RGBA half floats, (size + 2 Pad)^2 per array slice, array slice face * Slices + slice.
        std::vector<uint16_t> texels;
        // Slice 3 for the views: RGBA half floats, (size / ViewScale + 2 ViewPad)^2 per face.
        std::vector<uint16_t> views;
        // The volcanoes; their index: for each of its 6 VolcanoGrid^2 cells, D3D's cube map layout, the position of its
        // first volcano in this same array, then one more for the end; then the volcanoes' numbers, cell by cell.
        std::vector<Volcano> volcanoes;
        std::vector<uint32_t> volcanoIndex;
        uint32_t hotspots = 0;       // the mantle's plumes
        double ms = 0.0;             // the computation's time
        double volcanoMs = 0.0;      // the volcanism's share of it
    };

    Map Build(const Body& body);

    // The map to a file, for the CPU port of the relief (tools/hydro/cp.py): a header, then the texels, every slice.
    bool Save(const Map& map, uint32_t seed, const std::wstring& path);
    // The volcanoes to a file, for the same port: a header, the volcanoes, their index.
    bool SaveVolcanoes(const Map& map, uint32_t seed, const std::wstring& path);
}
