// The terrain under a point of the face plane, and whether a vertex can be on screen: shared by the mesh
// (TerrainCompute.hlsl) and the fine grid (FineTerrain.hlsl). Needs Planet.hlsli and Relief.hlsli.
#ifndef TERRAIN_HLSLI
#define TERRAIN_HLSLI

#ifdef AIRLESS_SURFACE
static const float TERRAIN_MIN_HEIGHT=-16000, TERRAIN_MAX_HEIGHT=16000;
#else
static const float TERRAIN_MIN_HEIGHT=0, TERRAIN_MAX_HEIGHT=MAX_TERRAIN_HEIGHT;
#endif

// Camera-relative position, face-local, of the vertex of direction d raised to elevation h.
// The camera sits at (camPlane.xy, R + camAltitude). z = d.z * (R + h) - (R + camAltitude), rewritten so
// that no two ~6e6 m floats get subtracted.
float3 RelativePosition(float3 d, float r2, float L, float R, float camAltitude, float h)
{
    return float3(d.xy * (R + h) - camPlane.xy, h * d.z - camAltitude - R * r2 / (L * (R + L)));
}

// Direction on the sphere of the face-plane point xy, normalised, and the terms RelativePosition needs.
void PlanePoint(float2 xy, float R, out float3 d, out float r2, out float L)
{
    r2 = dot(xy, xy);
    L = sqrt(r2 + R * R);
    d = float3(xy / L, R / L);
}

// Elevation (m) of the terrain under the face-plane point xy, its direction and its camera-relative
// position. The noise sees the planet's fixed frame: rotating the face never moves the terrain.
float TerrainAt(float2 xy, float R, float camAltitude, out float3 d, out float3 pos)
{
    float r2, L;
    PlanePoint(xy, R, d, r2, L);
    // Point = nadir (double) + offset from the nadir, without cancellation: d.z - 1 = -r2 / (L * (R + L)).
    const float3 offset = d.x * faceX.xyz + d.y * faceY.xyz - (r2 / (L * (R + L))) * faceZ.xyz;
    const float e = ReliefElevation(nadir.xyz + (double3)offset);
    pos = RelativePosition(d, r2, L, R, camAltitude, max(e, gWaterLevel));
    return e;
}

// False when the vertex cannot be on screen, whatever its elevation between sea level and the highest
// summit, nor cast its shadow on what can: its column swept by `sweep` (ShadowSweep), 0 for the view alone. The
// margin keeps every vertex of a triangle that crosses the edge of the screen. The test: the column's two ends and
// their swept copies all beyond the same side of the view.
bool MaybeVisible(float3 low, float3 high, float3 sweep, float margin)
{
    const float3x3 view = float3x3(camRight.xyz, camUp.xyz, camForward.xyz);
    const float3 a = mul(view, low), b = mul(view, high), c = mul(view, sweep);
    const float4 x = float4(a.x, b.x, a.x + c.x, b.x + c.x), y = float4(a.y, b.y, a.y + c.y, b.y + c.y),
                 z = float4(a.z, b.z, a.z + c.z, b.z + c.z);
    const float tanX = camRight.w, tanY = camUp.w;
    const float limitX = -margin * sqrt(1.0 + tanX * tanX); // plane distances are not normalised
    const float limitY = -margin * sqrt(1.0 + tanY * tanY);
    return !(all(z * tanX - x < limitX) || all(z * tanX + x < limitX) || all(z * tanY - y < limitY)
          || all(z * tanY + y < limitY) || all(z < -margin)); // the last: behind the camera
}

// Where the shadow of a column of terrain of direction d can fall, sea level to the highest summit
// (docs/recherche-ombres-relief.md): away from the sun, until the sun's lower limb, seen from sea level, clears the
// summit. The sun sinks along the way: the reach is taken again with the sun lower by the distance found. 0 when no
// ground can see the sun.
float3 ShadowSweep(float3 d)
{
    const float R = faceParams.y, lowest = -sqrt(2.0 * (TERRAIN_MAX_HEIGHT-TERRAIN_MIN_HEIGHT) / R); // the highest summit's horizon
    const float3 sun = lightDir.xyz;
    const float sinSun = dot(sun, d), elevation = asin(clamp(sinSun, -1.0, 1.0)) - SUN_ANGULAR_RADIUS;
    const float3 away = sinSun * d - sun;
    if (elevation < lowest || dot(away, away) < 1e-12)
        return 0.0;
    float reach = 0.0;
    [unroll]
    for (int i = 0; i < 2; ++i)
    {
        const float t = tan(max(elevation - reach / R, lowest));
        reach = R * (sqrt(t * t + 2.0 * (TERRAIN_MAX_HEIGHT-TERRAIN_MIN_HEIGHT) / R) - t);
    }
    return normalize(away) * reach - d * (0.5 * reach * reach / R); // along the sphere
}

#endif
