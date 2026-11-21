// Integrate incandescent air along the actual optical path in metres. The medium
// has no samples inside the hull. Glass and its fine reflections are composed later.
#include "Planet.hlsli"
#include "SceneExposure.hlsli"
#include "ShipEntryVolume.hlsli"

Texture2D<float4> sceneComposite : register(t47); // radial distance (km), includes the sky, atmosphere and terrain
Texture3D<float4> gasShape : register(t24);        // the existing periodic 128³ shape and fibre noise
Texture3D<float4> gasDetail : register(t25);
SamplerState gasWrap : register(s2);

struct VolumeOutput {
    float4 radiance : SV_Target0;
    float4 transmission : SV_Target1; // second source for blending into the single ship overlay
};

// The integral of the compact core profile (1-x²)². Its derivative is zero
// at both edges, so a march interval can cross the entire filament smoothly.
float CoreIntegral(float x)
{
    x = clamp(x, -1.0, 1.0);
    return x * (1.0 + x*x * (-2.0 / 3.0 + 0.20 * x*x));
}

VolumeOutput PSMain(EntryVolumePixel input)
{
    const float3 eye = mul((float3x3)shipModel, -shipModel[3].xyz);
    const float3 offset = input.local - eye;
    const float toFace = length(offset), heat = EntryIntensity();
    const float3 ray = offset / toFace, origin = eye - EntryShockCentre();
    const float3 safeRay = (2.0 * step(0.0, ray) - 1.0) * max(abs(ray), 0.000001);
    const float3 bounds = EntryShockBounds();
    const float3 a = (-bounds - origin) / safeRay, b = (bounds - origin) / safeRay;
    const float3 nearFace = min(a,b), farFace = max(a,b);
    const float begin = max(0.0, max(nearFace.x, max(nearFace.y, nearFace.z)));
    const float endBox = min(farFace.x, min(farFace.y, farFace.z));
    if (toFace < (begin + endBox) * 0.5 || endBox <= begin || heat < 0.002) discard;

    // Both distances use the very same jittered projection as the back face.
    // The ratio cancels the clip near plane and the cosine of the view angle.
    const int3 pixel = int3(input.position.xy, 0);
    const float opaque = ShipOpaqueDistance(input.position, toFace);
    const float scene = abs(sceneComposite.Load(pixel).a) * 1000.0;
    const float end = min(endBox, min(opaque, scene > 0.0 ? scene : 1.e20));
    if (end <= begin) discard;

    const float3 flow = shipAirflow.xyz;
    const float time = shipTurn.z;
    const float noseRadius = shipShockHull.SampleLevel(shipSampler, -flow, 0.0).x;
    float3 light = 0.0;
    float transmittance = 1.0, t = begin + 0.018;
    [loop] for (uint k = 0; k < 64 && t < end && transmittance > 0.035; ++k) {
        const float3 p = EntryShockUnadvect(origin + t * ray);
        const float r = max(length(p), 0.0001);
        const float3 direction = r > 0.0002 ? p / r : -flow;
        const EntryShockSection s = EntryShockProfile(direction, heat);
        const float height = (r - s.radius) / s.radialScale - s.gap;
        const float outside = max(-height, height - s.thickness);
        // A conservative clearance step through empty space, fine samples across the layer.
        float step = clamp(0.20 * s.thickness + 0.60 * max(outside, 0.0), 0.060, 1.25);
        const float3 azimuthal = cross(flow, p);
        const float radiusSquared = dot(azimuthal, azimuthal);
        const float turnRate = abs(dot(azimuthal, ray)) / max(radiusSquared, 0.10);
        const float incidence = abs(dot(ray, s.normal));
        const float refinement = 1.0 - smoothstep(0.21, 0.58, abs(height / s.thickness - 0.30));
        // Only a rapid crossing of a fibre or of the compressed core needs
        // smaller intervals. Retain the long clearance steps everywhere else.
        if (refinement > 0.0) {
            const float along = 0.020 / max(turnRate, 0.10);
            const float across = 0.069 * s.thickness / max(incidence, 0.16);
            step = lerp(step, clamp(min(along, across), 0.022, step), refinement);
        }
        step = min(step, end - t);
        if (outside < 0.0) {
            const float u = height / s.thickness;
            const float fore = dot(direction, -flow);
            const float downwind = smoothstep(-0.96, -0.43, fore);
            const float feed = EntryShockFeed(direction, time);
            const float nose = smoothstep(0.68, 1.04, dot(p, -flow) / max(noseRadius, 0.1));
            const float ram = nose * (0.34 + 0.66 * smoothstep(0.10, 0.91, s.incidence));
            // Large rolls carve open channels. Finer, faster structures stretch along the
            // flow and split into filaments. The cloud volumes have distinct measured ranges.
            const float3 stretched = p - 0.68 * dot(p, flow) * flow;
            const float roll = smoothstep(0.837, 0.943, gasShape.SampleLevel(gasWrap,
                0.074 * stretched - flow * (0.023 * time) + float3(0.23,0.47,0.11), 0.0).r);
            const float curl = smoothstep(0.57, 0.83, gasDetail.SampleLevel(gasWrap,
                0.41 * stretched - flow * (0.139 * time) + float3(0.13,-0.10,0.07) * roll, 0.0).r);
            // A parcel turning around the bow keeps its meridian for metres. Two
            // ridges of one smooth azimuthal field separate as the shear grows.
            // Unlike Cartesian noise blobs, each remains connected towards the shoulder.
            const float3 lateral = direction + fore * flow;
            const float3 meridian = lateral / max(length(lateral), 0.20);
            const float angularDrift = (0.13 * (roll - 0.5) + 0.085 * (curl - 0.5));
            const float3 lane = 0.26 * (meridian + cross(flow, meridian) * angularDrift) +
                                flow * (0.013 * dot(p, flow) - 0.012 * time) + float3(0.61,0.17,0.42);
            const float pixelAngle = max(t * taa.w, 0.0) * rsqrt(max(radiusSquared, 0.10));
            const float laneLod = log2(max(1.0, 128.0 * 0.26 * max(step * turnRate, pixelAngle)));
            const float thread = smoothstep(0.830, 0.947, gasShape.SampleLevel(gasWrap, lane, laneLod).r);
            const float mainLine = (thread - 0.61) / 0.17;
            const float splitting = smoothstep(0.27, 0.80, curl + 0.18 * (roll - 0.5));
            const float daughter = (thread - 0.60 + 0.27 * splitting) / 0.115;
            const float filaments = max(exp2(-1.7 * mainLine * mainLine),
                                        0.57 * splitting * exp2(-2.0 * daughter * daughter));
            const float openings = smoothstep(0.29, 0.72, 0.49 * roll + 0.31 * curl + 0.20 * feed);
            const float veins = filaments * (0.30 + 0.70 * openings);
            const float ripple = 0.095 * (roll - 0.5) + 0.072 * (curl - 0.5);
            // Integrate the fibre thickness over the sample's projected footprint.
            // A head-on ray must not acquire stripes when one march sample moves.
            const float width = 1.51 * (0.116 + 0.048 * curl);
            const float span = max(0.012, 0.5 * step * incidence / (s.thickness * width));
            const float depthCore = (u - 0.30 - ripple) / width;
            const float core = (CoreIntegral(depthCore + span) - CoreIntegral(depthCore - span)) / (2.0 * span);
            const float edge = smoothstep(0.0, 0.18, u) * (1.0 - smoothstep(0.57, 1.0, u));
            const float front = (0.027 + 0.16 * s.bow + 0.14 * ram) * (0.70 + 0.30 * roll);
            const float hot = core * (front + (0.22 + 0.35 * s.bow) * veins) * (0.76 + 0.24 * feed);
            const float outer = edge * (0.006 + 0.065 * veins + 0.056 * veins * curl * (1.0 - ram));
            const float density = heat * downwind * (hot + outer);
            const float kept = exp(-density * step);
            const float white = smoothstep(0.40, 0.92, veins * (0.58 + 0.56 * ram));
            const float3 amber = lerp(float3(1.83, 0.38, 0.044), float3(3.75, 2.15, 0.83), white);
            const float3 source = (hot * amber + outer * float3(1.20, 0.137, 0.044)) / max(hot + outer, 0.0001);
            light += transmittance * (1.0 - kept) * source;
            transmittance *= kept;
        }
        t += step;
    }
    if (transmittance > 0.99995) discard;
    VolumeOutput o;
    // Negative destination alpha is the distance to the Navigator's late chrome.
    // Preserve it exactly while applying the gas transmission to its actual colour.
    const bool chrome = ShipNavigator() && shipOptions.y < 0.5 && opaque <= endBox &&
                        (scene == 0.0 || opaque + 0.01 < scene);
    o.radiance = float4(light * min(1.0, 1.3 / max(Exposure(), 1.0)), chrome ? 1.0 : transmittance);
    o.transmission = float4(0, 0, 0, transmittance);
    return o;
}
