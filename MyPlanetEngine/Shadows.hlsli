// Shadows.hlsli - the sun's shadow cast by the relief (docs/recherche-ombres-relief.md). One march toward the sun over
// the mesh's heights, at each vertex: the terrain's horizon, for the ground, and the shadow height, for the air; the
// sun's share above the horizon, as the pixel's mean.
// Needs Planet.hlsli, PlanetSettings.hlsli and Materials.hlsli (SpreadStep); the march, for the passes that have the
// terrain, Mesh.hlsli and Terrain.hlsli before it.
#ifndef SHADOWS_HLSLI
#define SHADOWS_HLSLI

#ifdef TERRAIN_HLSLI

// The mesh the march reads; the horizon pass, which writes into it, reads it as a RWStructuredBuffer (Horizon.hlsl).
#ifndef SHADOW_MESH
#define SHADOW_MESH StructuredBuffer<FaceVertex>
#endif

// The mesh's height at the face-plane point xy (m, the sea's surface at 0), bilinear between the four vertices around
// it (MeshCell). False beyond the outermost ring. A culled vertex counts as the sea: its terrain was not needed
// (Terrain.hlsli, MaybeVisible).
bool MeshHeight(SHADOW_MESH verts, float2 xy, out float height)
{
    uint4 ids;
    float2 t;
    height = 0.0;
    if (!MeshCell(xy, ids, t))
        return false;
    height = Bilinear(max(float4(verts[ids.x].elevation, verts[ids.y].elevation, verts[ids.z].elevation, verts[ids.w].elevation), TERRAIN_MIN_HEIGHT), t);
    return true;
}

// The one march toward the sun, from p (camera-relative, face-local, m), at height h above the sea over the face-plane
// point xy, of vertical up. It gives the terrain's horizon that way (rad), the sphere's own at least, for the ground;
// and the column's shadow height (m above the sea), under which the relief hides the sun's centre, h at least, for the
// air (docs/recherche-rayons.md). The march follows the great circle toward the sun, a straight line on the face
// plane, in steps of HORIZON_STEP of the distance marched, never under the mesh's cell there. It stops once nothing
// beyond, even a summit of MAX_TERRAIN_HEIGHT, can rise above the horizon found and the sun's lower limb, nor above
// the sun's ray from the shadow height.
float SunHorizon(SHADOW_MESH verts, float2 xy, float3 p, float3 up, float h, out float shadow)
{
    const float R = faceParams.y, camAltitude = faceParams.z, n = faceParams.w;
    const float3 sun = lightDir.xyz;
    const float sinSun = clamp(dot(sun, up), -1.0, 1.0);
    const float lowerLimb = sin(asin(sinSun) - SUN_ANGULAR_RADIUS);
    // A point q (from p) of the sun's vertical plane hides its centre from the column up to dot(q, across) / cos^2 of
    // its elevation above p: its height over the sun's ray through p, across being normal to that ray.
    const float3 across = up - sinSun * sun;
    const float aboveFloor=max(h-TERRAIN_MIN_HEIGHT,0.0);
    float horizon = -sqrt(aboveFloor * (2.0 * (R+TERRAIN_MIN_HEIGHT) + aboveFloor)) / (R + h), rise = 0.0; // the sphere's horizon (sine); dot(q, across)
    shadow = h;
    float2 way = R * sun.xy - sun.z * xy; // the great circle's line on the face plane
    if (dot(way, way) < 1e-12 * R * R)
        return asin(horizon); // the sun straight up
    way = normalize(way);
    float u = 2.0 * max(faceParams.x, max(abs(xy.x), abs(xy.y))) / n; // the mesh's cell at p
    [loop]
    for (uint k = 0; k < 1024; ++k)
    {
        const float2 at = xy + u * way;
        float e;
        if (!MeshHeight(verts, at, e))
            break;
        float3 d;
        float r2, L;
        PlanePoint(at, R, d, r2, L);
        const float3 q = RelativePosition(d, r2, L, R, camAltitude, e) - p;
        const float3 top = RelativePosition(d, r2, L, R, camAltitude, TERRAIN_MAX_HEIGHT) - p;
        horizon = max(horizon, dot(q, up) * rsqrt(dot(q, q)));
        rise = max(rise, dot(q, across));
        if (dot(top, up) * rsqrt(dot(top, top)) < max(horizon, lowerLimb) && dot(top, across) < rise)
            break;
        u += max(2.0 * max(faceParams.x, max(abs(at.x), abs(at.y))) / n, HORIZON_STEP * u);
    }
    shadow = h + rise / max(1.0 - sinSun * sinSun, 1e-6);
    return asin(horizon);
}
#endif

// The share of the sun's disc above the horizon (rad), its mean over the pixel: sigma, the horizon's spread within it.
float SunAboveHorizon(float sinSun, float horizon, float sigma)
{
    return SpreadStep(-SUN_ANGULAR_RADIUS, SUN_ANGULAR_RADIUS, asin(clamp(sinSun, -1.0, 1.0)) - horizon, sigma);
}

// The share of the relief finer than the mesh that its own relief leaves in the sun: Smith's shadowing for slopes of
// deviation sigma along each axis (Beckmann's rational fit, Walter et al. 2007), the sun at cosine `cosine` from the
// mesh's surface. The mesh's march cannot see this relief; the light of a pixel is its mean over it.
float FinerReliefLit(float cosine, float sigma)
{
    const float a = max(cosine, 1e-4) / (1.41421356 * max(sigma, 1e-6) * sqrt(max(1.0 - cosine * cosine, 1e-8)));
    const float lambda = a < 1.6 ? (1.0 - 1.259 * a + 0.396 * a * a) / (3.535 * a + 2.181 * a * a) : 0.0;
    return 1.0 / (1.0 + lambda);
}

#endif
