// Climate.hlsli - the climate map (Climate.h; docs/spec-climat.md): the planet's rain, temperatures and winds, computed once
// per seed at startup from the tectonic map's large forms, on a cube fixed on the planet. It is data, never geometry. Two
// cubes, mipmapped by 2 x 2 means, read by the hardware's filtering, continuous across the faces:
// - cube 0: x the year's precipitation (mm); y the year's mean temperature at sea level (C); z the seasons' half amplitude
//   (C); w the share of the rain in the warm half of the year.
// - cube 1: x and y the year's mean surface wind towards the east and the north (m/s); z the continentality, 0 over the
//   sea to 1 where no sea air reaches; w the cold currents' cooling of the sea (C).
// On the CPU: Climate::At (Climate.h); the CPU port: tools/hydro/cp.py, climate(p).
#ifndef CLIMATE_HLSLI
#define CLIMATE_HLSLI
#include "PlanetMap.hlsli"

TextureCubeArray<float4> climateMap : register(t20);
static const uint CLIMATE_SIZE = 256; // texels per face side: 50 km at a face's centre, 22 km in its corners

// The level of the mip whose texels span `size` (m) at the unit direction d (MapLevel's rule).
float ClimateLevel(float3 d, float size)
{
    const float m = max(abs(d.x), max(abs(d.y), abs(d.z)));
    return max(log2(size * CLIMATE_SIZE / (2.0 * 1000.0 * PLANET_RADIUS_KM)) - 1.5 * log2(m), 0.0);
}

// Cube `cube` at the unit planet direction d: the mean over `size` (m), the pixel's or the cell's.
float4 ClimateAt(SamplerState s, float3 d, float size, uint cube = 0)
{
    return climateMap.SampleLevel(s, float4(d, cube), ClimateLevel(d, size));
}

// The humidity the materials and the plants read: the log of the year's precipitation from 100 to 3 000 mm
// (BiomePalette.hlsli), moved by `local`, the rain's variation under the map's resolution (LocalRain, Materials.hlsli).
float ClimateHumidity(float precipitation, float local = 0.0)
{
    return saturate(log(max(precipitation, 1.0) / 100.0) / log(30.0) + local);
}

// ---------------------------------------------------------------------------------------------
// The diagnostic views (MYPLANETENGINE_VIEW, Settings.cpp), after the tectonic map's: precipitation, wind. The temperature's
// is the ground's own, `temperature`, with the materials' views.
// ---------------------------------------------------------------------------------------------
static const float CLIMATE_VIEW = 42.0;

// The view's colour, sRGB, at the unit direction d for a pixel of `footprint` m; the sea paler.
float3 ClimateColour(SamplerState s, float view, float3 d, float footprint, bool sea)
{
    float3 c;
    if (view < CLIMATE_VIEW + 0.5) // the year's precipitation, on a log scale: brown under 100 mm, sand, pale green at
    {                              // 500 mm, green, teal at 2 000 mm, blue over 4 000
        const float3 ramp[6] = { float3(0.45, 0.25, 0.08), float3(0.85, 0.7, 0.4), float3(0.85, 0.9, 0.7),
                                 float3(0.3, 0.7, 0.3), float3(0.05, 0.5, 0.5), float3(0.05, 0.15, 0.55) };
        const float x = saturate((log10(max(ClimateAt(s, d, footprint).x, 1.0)) - 1.7) / 1.95) * 5.0;
        const uint k = min((uint)x, 4u);
        c = lerp(ramp[k], ramp[k + 1], x - k);
    }
    else // the wind: its direction's hue (east red, north yellow-green, west cyan, south violet), brighter with its speed;
    {    // an arrow on each cell of 16 per face side, about 600 km, its length the speed, 12 m/s a cell's half-width
        const float2 w = ClimateAt(s, d, footprint, 1).xy;
        c = lerp(0.5, saturate(abs(frac(atan2(w.y, w.x) / 6.2831853 + float3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0) - 1.0),
                 saturate(length(w) / 8.0));
        const float3 a = abs(d);
        const uint axis = a.x >= a.y && a.x >= a.z ? 0 : a.y >= a.z ? 1 : 2, face = 2 * axis + (d[axis] < 0.0 ? 1 : 0);
        const float3 sc = face == 0 ? float3(-d.z, -d.y, a.x) : face == 1 ? float3(d.z, -d.y, a.x) : face == 2 ? float3(d.x, d.z, a.y)
                        : face == 3 ? float3(d.x, -d.z, a.y) : face == 4 ? float3(d.x, -d.y, a.z) : float3(-d.x, -d.y, a.z);
        const float cells = 16.0;
        const float2 centre = (floor((sc.xy / sc.z * 0.5 + 0.5) * cells) + 0.5) / cells * 2.0 - 1.0;
        const float3 middle = normalize(CubeDirection(face, centre));
        const float3 east = normalize(float3(-middle.z, 0.0, middle.x)), north = cross(east, middle);
        const float2 m = ClimateAt(s, middle, 300000.0, 1).xy;
        const float speed = length(m), reach = PLANET_RADIUS_KM / cells * 0.8; // km
        if (speed > 0.3)
        {
            const float3 along = (m.x * east + m.y * north) / speed, across = cross(middle, along);
            const float3 o = (d / dot(d, middle) - middle) * PLANET_RADIUS_KM; // km, in the plane at the cell's centre
            const float u = dot(o, along), v = abs(dot(o, across)), size = reach * saturate(speed / 12.0);
            const float width = max(1.5 * footprint / 1000.0, 0.03 * reach);
            const bool shaft = u > -size && u < 0.55 * size && v < width;
            const bool head = u >= 0.55 * size && u < size && v < 0.8 * (size - u) + width;
            if (shaft || head)
                c = 0.05;
        }
    }
    return sea ? lerp(c, 0.75, 0.35) : c;
}

#endif
