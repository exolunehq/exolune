// Ejecta peel from the aperture while bright knots shed directly from the windward gas.
// The centre, surface and hot patches come from the same fitted hull as the visible shock.
#include "Planet.hlsli"
#include "Ship.hlsli"
#include "ShipEntry.hlsli"
#include "ShipEntryVolume.hlsli"

float ParticleUnit(uint key) { return (EntryHash(key) >> 8) * (1.0 / 16777216.0); }

struct GrainPath {
    float3 source, windward, radial, sideways;
    float angle, speed, drift, phase, radius;
};

float3 GrainAt(GrainPath path, float age, float heat)
{
    const float travel = age * (1.0 + 1.20 * age);
    // A small lateral drift grows only after release. Local turns follow the fitted skin.
    const float bend = path.drift * age * (sin(path.phase + 10.0 * age) - sin(path.phase));
    float sb, cb, sa, ca;
    sincos(bend, sb, cb);
    const float angle = min(2.78, path.angle + path.speed * travel);
    sincos(angle, sa, ca);
    const float3 direction = path.windward * ca + (path.radial * cb + path.sideways * sb) * sa;
    const float across = lerp(0.30, 0.94, smoothstep(0.0, 0.32, age));
    const float3 gas = EntryShockPoint(direction, across, heat);
    // A solid grain crosses the stand-off gap from the aperture. An already
    // luminous parcel starts at the compressed gas itself and moves downstream.
    const float3 parcel = lerp(path.source, gas, smoothstep(0.0, 0.095, age));
    // Only the detached particle on the downstream shoulder enters the free wake.
    const float carry = smoothstep(1.52, 2.18, angle) * (0.34 * age + 2.3 * age * age);
    return parcel + path.radius * (direction * (0.075 * age + 0.20 * age * age) - path.windward * carry);
}

EntryParticlePixel VSMain(uint id : SV_VertexID, uint slot : SV_InstanceID)
{
    EntryParticlePixel o = (EntryParticlePixel)0;
    o.position = float4(0, 0, -1, 1);
    const float heat = EntryIntensity();
    if (heat < 0.004) return o;
    // Integer event counts per hour keep the same release alive when the simulation clock wraps.
    const uint count = 1840u + EntryHash(slot + 19u) % 1601u;
    const float cycles = shipTurn.z * (count / 3600.0) + ParticleUnit(slot + 423u);
    const uint event = ((uint)floor(cycles) % count) * 256u + slot;
    const float age = frac(cycles) * (3600.0 / count);
    const float filament = smoothstep(0.88, 0.97, ParticleUnit(event + 419u));
    const float lifetime = lerp(0.25, 0.51, ParticleUnit(event + 731u)) + 0.105 * filament;
    const float threshold = 0.045 + 0.68 * ParticleUnit(event + 57u);
    const float activity = smoothstep(threshold - 0.045, threshold + 0.045, heat);
    if (age >= lifetime || activity <= 0) return o;

    const uint site = EntryHash(event + 101u) % 72u;
    GrainPath path;
    path.windward = -normalize(shipAirflow.xyz);
    const float3 reference = abs(path.windward.z) < 0.92 ? float3(0, 0, 1) : float3(0, 1, 0);
    const float3 flank = normalize(cross(reference, path.windward)), crown = cross(path.windward, flank);
    const float azimuth = 6.2831853 * ParticleUnit(site + 309u) + 0.16 * (ParticleUnit(event + 127u) - 0.5);
    float sa, ca;
    sincos(azimuth, sa, ca);
    path.radial = flank * ca + crown * sa;
    path.angle = lerp(0.18, 1.49, ParticleUnit(site + 29u)) + 0.09 * (ParticleUnit(event + 47u) - 0.5);
    float3 sourceDirection = path.windward * cos(path.angle) + path.radial * sin(path.angle);
    const bool atAperture = site % 3u == 0u && (!ShipShuttle() || HasShuttlePane());
    float3 aperture = 0;
    if (atAperture) {
        // Some persistent sites straddle the shoulders beside the real cockpit aperture, also visible from outside.
        const float rail = EntryRailLength();
        const float along = rail * saturate(lerp(0.07, 0.79, ParticleUnit(site + 233u)) +
                                            0.045 * (ParticleUnit(event + 353u) - 0.5));
        const float side = ParticleUnit(site + 179u) < 0.5 ? -1.0 : 1.0;
        const float inset = rail * lerp(0.012, 0.075, ParticleUnit(site + 29u));
        aperture = EntryPanePoint(along, side, inset);
        sourceDirection = normalize(aperture - EntryShockCentre());
        const float projected = dot(sourceDirection, path.windward);
        const float3 radial = sourceDirection - projected * path.windward;
        if (projected < -0.16) return o;
        const float radiusSquared = dot(radial, radial);
        if (radiusSquared > 1.e-8) path.radial = radial * rsqrt(radiusSquared);
        path.angle = atan2(sqrt(radiusSquared), projected);
    }
    const float birth = fmod(shipTurn.z - age + 3600.0, 3600.0);
    const float feed = EntryShockFeed(sourceDirection, birth);
    const float ignition = smoothstep(0.015, 0.20, feed - 0.74 * ParticleUnit(event + 13u));
    if (ignition <= 0) return o;
    path.sideways = cross(path.windward, path.radial);
    path.speed = lerp(1.25, 2.55, ParticleUnit(event + 247u)) * lerp(0.94, 1.65, smoothstep(80.0, 1100.0, shipAir.x));
    path.drift = lerp(-0.21, 0.21, ParticleUnit(event + 389u));
    path.phase = 6.2831853 * ParticleUnit(event + 83u);
    path.source = atAperture ? aperture + 0.006 * sourceDirection : EntryShockPoint(sourceDirection, 0.30, heat);
    path.radius = length(path.source - EntryShockCentre());

    // Rasterise an actual grain head even when its velocity points directly at the eye.
    const float grainShape = ParticleUnit(event + 131u);
    const float exposureTime = lerp(0.0024, 0.0070, grainShape) + 0.009 * filament;
    const float3 tipLocal = GrainAt(path, age, heat);
    const float sideWeight = ShipShuttle() ? EntryFlank(tipLocal) : 1.0;
    const float streak = ShipShuttle() ? sideWeight * smoothstep(80.0, 1050.0, shipAir.x) : 0.0;
    const float3 tip = mul(float4(tipLocal, 1), shipModel).xyz;
    const float3 past = mul(float4(GrainAt(path, max(0.0, age - exposureTime * (1.0 + 2.5 * streak)), heat), 1), shipModel).xyz;
    const float tipZ = dot(tip, camForward.xyz), pastZ = dot(past, camForward.xyz);
    if (min(tipZ, pastZ) < 0.035) return o;
    const float3 slope = tip / tipZ - past / pastZ;
    const float2 screenMotion = float2(dot(slope, camRight.xyz), dot(slope, camUp.xyz));
    const float screenLength = length(screenMotion);
    const float2 axis = screenLength > 1.e-7 ? screenMotion / screenLength : float2(1, 0);
    const float3 alongScreen = axis.x * camRight.xyz + axis.y * camUp.xyz;
    const float3 acrossScreen = axis.x * camUp.xyz - axis.y * camRight.xyz;
    const float pixelAngle = max(taa.w, 1.e-6);
    const float physicalRadius = lerp(0.0014, 0.0058, ParticleUnit(event + 947u));
    const float radiusPixels = clamp(physicalRadius / (pixelAngle * tipZ), 0.85, 1.65);
    // A short copper afterimage identifies a moving hot grain even at cabin-film resolution.
    const float trailPixels = min(screenLength / pixelAngle, lerp(lerp(1.1, 3.15, grainShape), 7.0, filament) * (1.0 + 3.2 * streak));
    const float fraction = saturate(trailPixels * pixelAngle / max(screenLength, 1.e-8));
    const float alongPath = fraction * tipZ / lerp(pastZ, tipZ, fraction);
    const float3 tail = lerp(tip, past, alongPath);

    const uint corners[6] = {0, 1, 2, 2, 1, 3};
    const uint corner = corners[id];
    const bool head = (corner & 1u) != 0;
    const float edge = head ? 1.42 : -1.42, sideEdge = (corner & 2u) ? 1.42 : -1.42;
    const float3 end = head ? tip : tail;
    const float radius = dot(end, camForward.xyz) * pixelAngle * radiusPixels;
    const float3 p = end + radius * (edge * alongScreen + sideEdge * acrossScreen);
    o.position = mul(float4(p, 1), viewProj);
    o.uv = float2(edge - (head ? 0.0 : trailPixels / radiusPixels), sideEdge);
    const float phase = age / lifetime;
    const float envelope = smoothstep(0.0, 0.085, phase) * (1.0 - smoothstep(0.44, 1.0, phase));
    const float coverage = 0.58 + 0.42 * saturate(physicalRadius / (pixelAngle * tipZ));
    o.light = float3(heat * activity * ignition * envelope * coverage * (ShipShuttle() ? lerp(0.035, 1.75, sideWeight) : 1.0) * (2.6 + 5.6 * feed),
                     saturate(phase + 0.13 * ParticleUnit(event + 617u)), trailPixels / radiusPixels);
    return o;
}
