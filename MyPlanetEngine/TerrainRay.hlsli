#ifndef TERRAIN_RAY_HLSLI
#define TERRAIN_RAY_HLSLI
// Distance along the unit ray from the camera to the sphere of radius R + h, or -1 when it misses. The camera sits
// at (camPlane.xy, R + camAltitude) from the planet's centre; the radii's difference is taken apart, without cancellation.
float RayToSphere(float3 ray, float R, float camAltitude, float h)
{
    const float3 eye = float3(camPlane.xy, R + camAltitude);
    const float b = dot(ray, eye);
    const float c = (camAltitude - h) * (2.0 * R + camAltitude + h) + dot(camPlane.xy, camPlane.xy);
    const float disc = b * b - c;
    return disc < 0.0 ? -1.0 : -b - sqrt(disc);
}

// The face-plane point under the ray's hit on the sphere of radius R + h, and its footprint (m): the texel's angle at
// that distance, stretched along the view by the incidence. False when the ray misses.
bool PlaneHit(float3 ray, float R, float camAltitude, float h, float texelAngle, out float2 xy, out float footprint)
{
    xy = 0.0;
    footprint = 0.0;
    const float t = RayToSphere(ray, R, camAltitude, h);
    if (t <= 0.0)
        return false;
    const float3 d = normalize(float3(camPlane.xy, R + camAltitude) + t * ray);
    if (d.z <= 0.05)
        return false;
    xy = R * d.xy / d.z;
    footprint = t * texelAngle / max(-dot(ray, d), 0.1);
    return true;
}

#endif
