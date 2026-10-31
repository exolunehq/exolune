// PlanetMap.hlsli - the planet map (docs/recherche-rivieres.md, step 1): the relief's elevation on a cube fixed on the
// planet, computed once at startup (PlanetMap.hlsl), drained on the CPU (PlanetMap.cpp), then read as a cube map. It is
// data, never geometry: it moves no vertex. Its users: the boundary layer's haze, which follows its ground
// (Atmosphere.hlsli), and the lakes and rivers to come. D3D's cube map layout; PlanetMap.cpp has the same.
#ifndef PLANET_MAP_HLSLI
#define PLANET_MAP_HLSLI
#include "PlanetSettings.hlsli"

static const uint PLANET_MAP_SIZE = 1024; // texels per face side: 9.8 km at a face's centre, 4.6 km in its corners

// x: the ground, max(e, 0), the sea's surface over the sea (m); y: the water over it once every pit is filled to its
// spill, the lakes (m); z: log2 of the area drained through the texel (km2), the rivers. Mipmapped, by 2 x 2 means.
TextureCube<float4> planetMap : register(t29);

// The direction of the point (s, t) of face `face`, s and t from -1 to 1 along the texels' x and y, not normalised.
float3 CubeDirection(uint face, float2 st)
{
    const float s = st.x, t = st.y;
    return face == 0 ? float3(1.0, -t, -s) : face == 1 ? float3(-1.0, -t, s) : face == 2 ? float3(s, 1.0, t)
         : face == 3 ? float3(s, -1.0, -t) : face == 4 ? float3(s, -t, 1.0) : float3(-s, -t, -1.0);
}

// The level of the mip whose texels span `size` (m) at the unit direction d: a texel's side is (2 R / N) m^1.5, m the
// largest of |d|'s components, the cube's area element.
float MapLevel(float3 d, float size)
{
    const float m = max(abs(d.x), max(abs(d.y), abs(d.z)));
    return max(log2(size * PLANET_MAP_SIZE / (2.0 * 1000.0 * PLANET_RADIUS_KM)) - 1.5 * log2(m), 0.0);
}

#endif
