// The clouds traced over time (docs/optimisation.md, round 1). Each frame traces one pixel per 4x4 tile into the fresh
// images; the full-resolution resolve takes that pixel's fresh value, reprojects the others' from the history, anchored
// in the weather for the clouds and on the ground for their shadow, and composites the air at full resolution. Where the
// history is missing or has drifted, the resolve traces the pixel itself, as the single pass would; drifted below 14 km,
// as in a fast flight near the clouds, it rebuilds it from one pixel traced per 2x2 quad (round 7).
#ifndef CLOUDS_TEMPORAL_HLSLI
#define CLOUDS_TEMPORAL_HLSLI

Texture2D<float4> cloudFresh0 : register(t44);   // cloud light, transmittance; one texel per 4x4 tile
Texture2D<float4> cloudFresh1 : register(t45);   // cloud distance and its spread (km), shadow T (-1: none), clouds' end
Texture2D<float4> cloudHistory0 : register(t46); // light and transmittance per pixel, the previous frame's
Texture2D<float4> cloudHistory1 : register(t47); // distance, ray end, shadow T (-1: none), clouds' end
Texture2D<float2> cloudHistory2 : register(t48); // the distance's spread (km), the drift (pixels)
// The pixels whose history has drifted, traced one per 2x2 quad (PSCloudTraceHalf): light and transmittance; distance,
// spread, the clouds' end, w = -1 where the quad's pixel kept its history, 0 where traced.
Texture2D<float4> cloudHalf0 : register(t49);
Texture2D<float4> cloudHalf1 : register(t50);

// The tile, one pixel of which is traced per frame: D3DApp::CloudTileX and CloudTileY.
static const int2 CLOUD_TEMPORAL_TILE = int2(4, 4);
// The drift, in pixels, that a volume's reprojection may accumulate since its trace before the pixel is traced again.
// A fill from the fresh tiles would not do over such regions: it smooths the far clouds' grain into flat pale plates.
static const float CLOUD_TEMPORAL_DRIFT_PX = 1.0;
// The turn, in a frame, of the direction a cloud is seen from, past which its history is retraced (radians, 1 degree):
// a volume is not a surface, and seen from elsewhere it shows other sides. Past it, as at x5 in orbit, every frame's
// trace costs the single pass's; below, as in an ordinary flight, the history keeps up over the 16 frames.
static const float CLOUD_TEMPORAL_TURN = 0.0175;
// The change of the distance a cloud is seen from, since its trace, that its history tolerates (log, 20 %): diving toward
// it, its footprint shrinks while nothing slides on the screen, and its history was taken from farther away.
static const float CLOUD_TEMPORAL_ZOOM = 0.18;
static const float CLOUD_TEMPORAL_HALF_MAX_ALTITUDE_KM = 14.0;

// Two ray ends see the same surface, or both the sky (0).
bool CloudTemporalSameEnd(float a, float b, float tolerance)
{
    return a <= 0.0 ? b <= 0.0 : b > 0.0 && abs(a - b) <= tolerance * max(a, b) + 0.002;
}

// The ray's end as its clouds see it: 0, as the sky, where the ray has left the low layer through its bottom before the
// surface. Nothing of the clouds lies beyond: such rays see the same clouds whatever their surface's distance, which
// toward the horizon changes by 4 % from one row to the next; compared as surfaces, the history and the fills refused
// their neighbours along a line fixed on the screen, the horizon behind the clouds.
float CloudTemporalCloudEnd(float3 view, float rayEnd)
{
    const float3 cameraKm = (float3)cloudCameraKm.xyz;
    const float r0 = length(cameraKm), h0 = camVertical.w;
    const float mu = dot(cameraKm / r0, view);
    if (rayEnd <= 0.0 || h0 <= CLOUD_LOW_BOTTOM_KM || mu >= 0.0)
        return rayEnd;
    const float rb = (float)CLOUD_PLANET_RADIUS_KM + CLOUD_LOW_BOTTOM_KM;
    const float d = r0 * r0 * mu * mu - (h0 - CLOUD_LOW_BOTTOM_KM) * (r0 + rb); // r0^2 - rb^2 without the cancellation
    return d >= 0.0 && rayEnd > 1.02 * (-r0 * mu - sqrt(d)) + 0.05 ? 0.0 : rayEnd;
}

// A point at a current camera-relative offset (km), in the previous frame's pixels; -1 behind the camera.
float2 CloudTemporalPrevPixel(float3 offsetKm, float4 row0, float4 row1, float4 row2, float2 size, out float distanceKm)
{
    const float3 c = float3(dot(row0.xyz, offsetKm) + row0.w, dot(row1.xyz, offsetKm) + row1.w,
                            dot(row2.xyz, offsetKm) + row2.w);
    distanceKm = length(c);
    if (c.z <= 1.0e-6)
        return -1.0;
    const float2 ndc = float2(c.x / (c.z * (float)cloudRightTan.w), c.y / (c.z * (float)cloudUpTan.w));
    return float2(0.5 * (ndc.x + 1.0) * size.x, 0.5 * (1.0 - ndc.y) * size.y);
}

bool CloudTemporalInside(float2 pixel, float2 size)
{
    return all(pixel >= 0.0) && all(pixel < size);
}

// Distance along the view to the cloud shell; 1e9 when the ray never reaches it. Conservative: never past the shell.
float CloudTemporalShellEntryKm(float3 view)
{
    const float3 cameraKm = (float3)cloudCameraKm.xyz;
    const float r0 = length(cameraKm), h0 = camVertical.w;
    const float mu = dot(cameraKm / r0, view);
    if (h0 >= (float)CLOUD_SHELL_BOTTOM_KM && h0 <= (float)CLOUD_SHELL_TOP_KM)
        return 0.0;
    const float shell = h0 < (float)CLOUD_SHELL_BOTTOM_KM ? (float)CLOUD_SHELL_BOTTOM_KM : (float)CLOUD_SHELL_TOP_KM;
    const float rs = (float)CLOUD_PLANET_RADIUS_KM + shell;
    const float c = (h0 - shell) * (r0 + rs); // r0^2 - rs^2 without the cancellation
    const float d = r0 * r0 * mu * mu - c;
    if (d < 0.0)
        return 1.0e9;
    const float t = h0 < shell ? -r0 * mu + sqrt(d) : -r0 * mu - sqrt(d);
    return t > 0.0 ? 0.98 * t - 0.05 : 1.0e9;
}

// The bilinear footprint of a position in pixels (centres at +0.5): its first texel and the four weights.
void CloudTemporalFootprint(float2 position, out int2 base, out float4 weights)
{
    const float2 p = position - 0.5;
    base = int2(floor(p));
    const float2 f = p - floor(p);
    weights = float4((1.0 - f.x) * (1.0 - f.y), f.x * (1.0 - f.y), (1.0 - f.x) * f.y, f.x * f.y);
}

int2 CloudTemporalTap(int2 base, int k, int2 size)
{
    return clamp(base + int2(k & 1, k >> 1), 0, size - 1);
}

// The ray end of a fresh tile's pixel, 0 for the sky.
float CloudTemporalFreshEnd(int2 tile, int2 offset, float2 size)
{
    return abs(hdr.Load(int3(min(tile * CLOUD_TEMPORAL_TILE + offset, int2(size) - 1), 0)).a);
}

// The clouds from this frame's fresh tiles around the pixel that see the same surface, where the history does not see
// it: thin strips, at the screen's edges or around what moves. False when no tile sees it.
bool CloudTemporalCloudFill(int2 pixel, float rayEnd, int2 offset, float2 size, out float4 light, out float depthKm,
                            out float spreadKm)
{
    const int2 grid = (int2(size) + CLOUD_TEMPORAL_TILE - 1) / CLOUD_TEMPORAL_TILE;
    int2 base;
    float4 bilinear;
    CloudTemporalFootprint(float2(pixel - offset) / float2(CLOUD_TEMPORAL_TILE) + 0.5, base, bilinear);
    light = 0.0;
    depthKm = 0.0;
    spreadKm = 0.0;
    float weightSum = 0.0, depthWeight = 0.0;
    [unroll]
    for (int k = 0; k < 4; ++k)
    {
        const int2 t = CloudTemporalTap(base, k, grid);
        const float4 tapData = cloudFresh1.Load(int3(t, 0));
        const float w = CloudTemporalSameEnd(rayEnd, tapData.w, 0.05) ? bilinear[k] : 0.0;
        light += w * cloudFresh0.Load(int3(t, 0));
        weightSum += w;
        const float wd = tapData.x > 0.0 ? w : 0.0;
        depthKm += wd * tapData.x;
        spreadKm += wd * tapData.y;
        depthWeight += wd;
    }
    if (weightSum < 1.0e-3)
    {
        // None of the four: the nearest of the 5x5 around that sees the same surface, as for the sky through leaves.
        float nearest = 1.0e9;
        [loop]
        for (int y = -2; y <= 2; ++y)
        {
            [loop]
            for (int x = -2; x <= 2; ++x)
            {
                const int2 t = clamp(base + int2(x, y), 0, grid - 1);
                const float2 toTile = float2(t * CLOUD_TEMPORAL_TILE + offset - pixel);
                if (dot(toTile, toTile) < nearest && CloudTemporalSameEnd(rayEnd, cloudFresh1.Load(int3(t, 0)).w, 0.05))
                {
                    nearest = dot(toTile, toTile);
                    light = cloudFresh0.Load(int3(t, 0));
                    depthKm = cloudFresh1.Load(int3(t, 0)).x;
                    spreadKm = cloudFresh1.Load(int3(t, 0)).y;
                }
            }
        }
        return nearest < 1.0e9;
    }
    light /= weightSum;
    depthKm = depthWeight > 0.0 ? depthKm / depthWeight : 0.0;
    spreadKm = depthWeight > 0.0 ? spreadKm / depthWeight : 0.0;
    return true;
}

// The clouds from the history's texels around the previous pixel that see the same surface, where neither the history
// at that pixel nor this frame's fresh tiles see it: the sky through a new gap in the leaves. The nearest of the 5x5,
// else of a 9x9 grid every 6 texels, 24 pixels around: a dense search that far held the pass as a trace would. False when
// none does.
bool CloudTemporalHistoryFill(float2 prevPixel, float rayEnd, float2 size, out float4 light, out float depthKm,
                              out float spreadKm)
{
    light = 0.0;
    depthKm = 0.0;
    spreadKm = 0.0;
    const int2 centre = int2(prevPixel);
    float nearest = 1.0e9;
    [loop]
    for (int pass = 0; pass < 2 && nearest >= 1.0e9; ++pass)
    {
        const int reach = pass == 0 ? 2 : 24, step = pass == 0 ? 1 : 6;
        [loop]
        for (int y = -reach; y <= reach; y += step)
        {
            [loop]
            for (int x = -reach; x <= reach; x += step)
            {
                const int2 t = clamp(centre + int2(x, y), 0, int2(size) - 1);
                const float2 toTexel = float2(t) + 0.5 - prevPixel;
                const float4 data = cloudHistory1.Load(int3(t, 0));
                if (dot(toTexel, toTexel) < nearest && CloudTemporalSameEnd(rayEnd, data.w, 0.03))
                {
                    nearest = dot(toTexel, toTexel);
                    light = cloudHistory0.Load(int3(t, 0));
                    depthKm = data.x;
                    spreadKm = cloudHistory2.Load(int3(t, 0)).x;
                }
            }
        }
    }
    return nearest < 1.0e9;
}

// The shadow from this frame's fresh tiles around the pixel that see the same surface lit; -1 when none does. The
// clouds' shadow is smooth: unlike the clouds, a fill keeps it (where waves or swaying leaves change the surface).
float CloudTemporalShadowFill(int2 pixel, float rayEnd, int2 offset, float2 size)
{
    const int2 grid = (int2(size) + CLOUD_TEMPORAL_TILE - 1) / CLOUD_TEMPORAL_TILE;
    int2 base;
    float4 bilinear;
    CloudTemporalFootprint(float2(pixel - offset) / float2(CLOUD_TEMPORAL_TILE) + 0.5, base, bilinear);
    float sum = 0.0, weightSum = 0.0, anySum = 0.0, anyWeight = 0.0;
    [unroll]
    for (int k = 0; k < 4; ++k)
    {
        const int2 t = CloudTemporalTap(base, k, grid);
        const float4 tapData = cloudFresh1.Load(int3(t, 0));
        const float lit = tapData.z >= 0.0 ? bilinear[k] : 0.0;
        const float w = CloudTemporalSameEnd(rayEnd, CloudTemporalFreshEnd(t, offset, size), 0.05) ? lit : 0.0;
        sum += w * tapData.z;
        weightSum += w;
        anySum += lit * tapData.z; // a leaf and the ground beside it share the clouds' shadow
        anyWeight += lit;
    }
    return weightSum > 1.0e-3 ? sum / weightSum : anyWeight > 1.0e-3 ? anySum / anyWeight : -1.0;
}

// The clouds' history at a previous pixel: Catmull-Rom inside a surface, clamped to its four nearest texels; bilinear
// among the texels that see the same surface at an edge. False when none does.
bool CloudTemporalCloudHistory(float2 prevPixel, float rayEnd, float2 size, out float4 light, out float depthKm,
                               out float spreadKm, out float driftPx)
{
    light = 0.0;
    depthKm = 0.0;
    spreadKm = 0.0;
    driftPx = 0.0;
    if (!CloudTemporalInside(prevPixel, size))
        return false;
    int2 base;
    float4 weights;
    CloudTemporalFootprint(prevPixel, base, weights);
    const bool still = all(abs(prevPixel - floor(prevPixel) - 0.5) < 0.01);
    if (still) // a still camera reads its own texel exactly
    {
        base = int2(prevPixel);
        weights = float4(1.0, 0.0, 0.0, 0.0);
    }
    float4 lo = 1.0e30, hi = -1.0e30, bilinear = 0.0;
    float weightSum = 0.0, depthWeight = 0.0;
    [unroll]
    for (int k = 0; k < 4; ++k)
    {
        const int2 t = CloudTemporalTap(base, k, int2(size));
        const float4 tapData = cloudHistory1.Load(int3(t, 0));
        const float4 tapLight = cloudHistory0.Load(int3(t, 0));
        const float2 tapPlace = cloudHistory2.Load(int3(t, 0));
        const float w = CloudTemporalSameEnd(rayEnd, tapData.w, 0.03) ? weights[k] : 0.0;
        bilinear += w * tapLight;
        weightSum += w;
        lo = min(lo, tapLight);
        hi = max(hi, tapLight);
        const float wd = tapData.x > 0.0 ? w : 0.0;
        depthKm += wd * tapData.x;
        depthWeight += wd;
        // Means: a minimum or a maximum, resampled every frame, would erode or spread them over the whole image.
        spreadKm += w * tapPlace.x;
        driftPx += w * tapPlace.y;
    }
    if (weightSum < 0.05)
        return false;
    depthKm = depthWeight > 0.0 ? depthKm / depthWeight : 0.0;
    spreadKm /= weightSum;
    driftPx /= weightSum;
    if (still || weightSum < 0.999)
    {
        light = bilinear / weightSum;
        return true;
    }
    // Catmull-Rom in five bilinear taps (the corners dropped): it keeps the edges sharp while the camera moves.
    const float2 texPos1 = floor(prevPixel - 0.5) + 0.5;
    const float2 f = prevPixel - texPos1;
    const float2 w0 = f * (-0.5 + f * (1.0 - 0.5 * f));
    const float2 w1 = 1.0 + f * f * (-2.5 + 1.5 * f);
    const float2 w2 = f * (0.5 + f * (2.0 - 1.5 * f));
    const float2 w3 = f * f * (-0.5 + 0.5 * f);
    const float2 w12 = w1 + w2;
    const float2 p0 = (texPos1 - 1.0) / size, p3 = (texPos1 + 2.0) / size, p12 = (texPos1 + w2 / w12) / size;
    const float4 sum = cloudHistory0.SampleLevel(linearClamp, float2(p0.x, p12.y), 0.0) * (w0.x * w12.y)
                     + cloudHistory0.SampleLevel(linearClamp, float2(p12.x, p0.y), 0.0) * (w12.x * w0.y)
                     + cloudHistory0.SampleLevel(linearClamp, p12, 0.0) * (w12.x * w12.y)
                     + cloudHistory0.SampleLevel(linearClamp, float2(p3.x, p12.y), 0.0) * (w3.x * w12.y)
                     + cloudHistory0.SampleLevel(linearClamp, float2(p12.x, p3.y), 0.0) * (w12.x * w3.y);
    const float norm = w0.x * w12.y + w12.x * w0.y + w12.x * w12.y + w3.x * w12.y + w12.x * w3.y;
    light = clamp(sum / norm, lo, hi);
    return true;
}

// The shadow's history at a previous pixel, among the texels that saw this very ground point lit.
bool CloudTemporalShadowHistory(float2 prevPixel, float prevDistanceKm, float2 size, out float shadowT)
{
    shadowT = -1.0;
    if (!CloudTemporalInside(prevPixel, size))
        return false;
    int2 base;
    float4 weights;
    CloudTemporalFootprint(prevPixel, base, weights);
    float weightSum = 0.0, sum = 0.0;
    [unroll]
    for (int k = 0; k < 4; ++k)
    {
        const float4 tapData = cloudHistory1.Load(int3(CloudTemporalTap(base, k, int2(size)), 0));
        const float w = tapData.z >= 0.0 && CloudTemporalSameEnd(prevDistanceKm, tapData.y, 0.02) ? weights[k] : 0.0;
        sum += w * tapData.z;
        weightSum += w;
    }
    if (weightSum < 0.05)
        return false;
    shadowT = sum / weightSum;
    return true;
}

// The clouds' history reprojected to a pixel, with the history valid: true when it holds, false when it has drifted or
// turned, seen false when no texel sees the pixel's surface. The drift, as accumulated by this frame's reprojection.
bool CloudTemporalLookup(int2 pixel, float3 view, float rayEnd, float entryKm, float2 size, out bool seen,
                         out float4 historyLight, out float historyDepthKm, out float historySpreadKm,
                         out float driftPx, out float2 prevPixelOut)
{
    // The cloud's distance from the history at this pixel, then at the pixel it reprojects to.
    float guessKm = cloudHistory1.Load(int3(pixel, 0)).x;
    if (guessKm <= 0.0)
        guessKm = max(entryKm, 1.0);
    float prevDistanceKm;
    float2 prevPixel = CloudTemporalPrevPixel(view * guessKm, cloudPrevQ[0], cloudPrevQ[1], cloudPrevQ[2],
        size, prevDistanceKm);
    // The history keeps distances from the previous camera: the point at that distance from it lies at
    // currentKm from this one, the camera's move along the view apart (one Newton step, |dc/dd| ~ 1).
    float moveKm = 0.0;
    if (CloudTemporalInside(prevPixel, size))
    {
        const float refinedKm = cloudHistory1.Load(int3(prevPixel, 0)).x;
        if (refinedKm > 0.0)
        {
            CloudTemporalPrevPixel(view * refinedKm, cloudPrevQ[0], cloudPrevQ[1], cloudPrevQ[2], size,
                prevDistanceKm);
            moveKm = refinedKm - prevDistanceKm;
            guessKm = refinedKm + moveKm;
            prevPixel = CloudTemporalPrevPixel(view * guessKm, cloudPrevQ[0], cloudPrevQ[1],
                cloudPrevQ[2], size, prevDistanceKm);
        }
    }
    float historyDriftPx;
    prevPixelOut = prevPixel;
    seen = CloudTemporalCloudHistory(prevPixel, rayEnd, size, historyLight, historyDepthKm,
        historySpreadKm, historyDriftPx);
    // A volume is not at one distance: its light comes from a spread of them, measured by the trace. One
    // spread either side moves by this much in this frame's reprojection; the drift adds up until the
    // pixel's next trace.
    const float reachKm = min(historySpreadKm, 0.5 * guessKm);
    float unused;
    const float2 nearPixel = CloudTemporalPrevPixel(view * (guessKm - reachKm), cloudPrevQ[0],
        cloudPrevQ[1], cloudPrevQ[2], size, unused);
    const float2 farPixel = CloudTemporalPrevPixel(view * (guessKm + reachKm), cloudPrevQ[0],
        cloudPrevQ[1], cloudPrevQ[2], size, unused);
    // The camera's move across the line of sight turns the direction the cloud is seen from.
    const float3 move = float3(cloudPrevQ[0].w, cloudPrevQ[1].w, cloudPrevQ[2].w);
    float prevKm;
    CloudTemporalPrevPixel(view * guessKm, cloudPrevQ[0], cloudPrevQ[1], cloudPrevQ[2], size, prevKm);
    const float3 sight = float3(dot(cloudPrevQ[0].xyz, view), dot(cloudPrevQ[1].xyz, view),
        dot(cloudPrevQ[2].xyz, view)); // this frame's view, in the previous camera's axes
    const float turn = length(move - dot(move, sight) * sight) / max(prevKm, 1.0e-3);
    driftPx = historyDriftPx + 0.5 * length(farPixel - nearPixel)
        + CLOUD_TEMPORAL_DRIFT_PX * abs(log(max(prevKm, 1.0e-3) / max(guessKm, 1.0e-3))) / CLOUD_TEMPORAL_ZOOM;
    if (historyDepthKm > 0.0)
        historyDepthKm = max(historyDepthKm + moveKm, 1.0e-3); // from this camera, as it is stored
    return seen && driftPx <= CLOUD_TEMPORAL_DRIFT_PX && turn <= CLOUD_TEMPORAL_TURN;
}

// The drifted pixels, one per 2x2 quad below 14 km: retain the altitude gate of round 7.
// Above it, retrace the pixel itself instead of interpolating the quads.
bool CloudTemporalHalfOn()
{
    return camVertical.w <= CLOUD_TEMPORAL_HALF_MAX_ALTITUDE_KM;
}

// This frame's pixel of each 2x2 quad: the 4x4 tile's pixel, halved, visits the four in turn.
int2 CloudTemporalHalfPixel()
{
    return int2(cloudTemporal.xy) >> 1;
}

// One pixel per 2x2 quad, traced where the history of one of the quad's pixels has drifted or turned, as in a fast
// flight: the resolve rebuilds the others from these quads (CloudTemporalHalfFill) instead of tracing each.
float4 PSCloudTraceHalf(float4 position : SV_POSITION, out float4 data : SV_TARGET1) : SV_TARGET0
{
    float2 size;
    hdr.GetDimensions(size.x, size.y);
    const int2 quad = int2(position.xy) * 2, pixel = quad + CloudTemporalHalfPixel();
    data = float4(0.0, 0.0, -1.0, -1.0); // w < 0: not traced
    if (any(pixel >= int2(size)) || cloudTemporal.z < 0.5 || cloudCameraKm.w < 0.5l || !CloudTemporalHalfOn())
        return float4(0.0, 0.0, 0.0, 1.0);
    bool drifted = false;
    [loop]
    for (int k = 0; k < 4 && !drifted; ++k)
    {
        const int2 p = min(quad + int2(k & 1, k >> 1), int2(size) - 1);
        const float end = abs(hdr.Load(int3(p, 0)).a);
        const float3 v = CloudViewFloat(float2(p) + 0.5, size);
        const float entryKm = CloudTemporalShellEntryKm(v);
        if (entryKm < (end > 0.0 ? end : 1.0e9))
        {
            bool seen;
            float4 unusedLight;
            float unusedDepth, unusedSpread, unusedDrift;
            float2 unusedPrev;
            const bool found = CloudTemporalLookup(p, v, CloudTemporalCloudEnd(v, end), entryKm, size, seen,
                unusedLight, unusedDepth, unusedSpread, unusedDrift, unusedPrev);
            drifted = seen && !found;
        }
    }
    [branch]
    if (!drifted)
        return float4(0.0, 0.0, 0.0, 1.0);
    const float4 scene = hdr.Load(int3(pixel, 0));
    const CloudPixel clouds = CloudTracePixel(float4(scene.rgb, abs(scene.a)), float2(pixel) + 0.5, size,
        true, false, false);
    data = float4(clouds.depthKm, clouds.depthSpreadKm,
        CloudTemporalCloudEnd(CloudViewFloat(float2(pixel) + 0.5, size), abs(scene.a)), 0.0); // z: the clouds' end
    return float4(clouds.cloudLight, dot(clouds.transmission, 1.0 / 3.0));
}

// A drifted pixel's clouds from this frame's traced quads around it that see the same surface: bilinear among them,
// exact at the quad's own pixel. False when none does.
bool CloudTemporalHalfFill(int2 pixel, float rayEnd, float2 size, out float4 light, out float depthKm,
                           out float spreadKm)
{
    const int2 grid = (int2(size) + 1) / 2, offset = CloudTemporalHalfPixel();
    int2 base;
    float4 bilinear;
    CloudTemporalFootprint(float2(pixel - offset) / 2.0 + 0.5, base, bilinear);
    light = 0.0;
    depthKm = 0.0;
    spreadKm = 0.0;
    float weightSum = 0.0, depthWeight = 0.0;
    [unroll]
    for (int k = 0; k < 4; ++k)
    {
        const int2 t = CloudTemporalTap(base, k, grid);
        const float4 tapData = cloudHalf1.Load(int3(t, 0));
        const float w = tapData.w >= 0.0 && CloudTemporalSameEnd(rayEnd, tapData.z, 0.05) ? bilinear[k] : 0.0;
        light += w * cloudHalf0.Load(int3(t, 0));
        weightSum += w;
        const float wd = tapData.x > 0.0 ? w : 0.0;
        depthKm += wd * tapData.x;
        spreadKm += wd * tapData.y;
        depthWeight += wd;
    }
    if (weightSum < 1.0e-3)
        return false;
    light /= weightSum;
    depthKm = depthWeight > 0.0 ? depthKm / depthWeight : 0.0;
    spreadKm = depthWeight > 0.0 ? spreadKm / depthWeight : 0.0;
    return true;
}

float4 PSCloudTrace(float4 position : SV_POSITION, out float4 data : SV_TARGET1) : SV_TARGET0
{
    float2 size;
    hdr.GetDimensions(size.x, size.y);
    const int2 pixel = int2(position.xy) * CLOUD_TEMPORAL_TILE + int2(cloudTemporal.xy);
    data = float4(0.0, 0.0, -1.0, 0.0);
    if (any(pixel >= int2(size)))
        return float4(0.0, 0.0, 0.0, 1.0);
    const float4 scene = hdr.Load(int3(pixel, 0));
    const float4 cloudScene = float4(scene.rgb, abs(scene.a));
    const CloudPixel clouds = CloudTracePixel(cloudScene, float2(pixel) + 0.5, size,
        true, true, false);
    const float3 sunRGB = sunPart.Load(int3(pixel, 0)).rgb;
    const bool lit = cloudScene.a > 0.0 && max(sunRGB.r, max(sunRGB.g, sunRGB.b)) > 1.0e-6;
    data = float4(clouds.depthKm, clouds.depthSpreadKm, lit ? clouds.surfaceShadowT : -1.0,
        CloudTemporalCloudEnd(CloudViewFloat(float2(pixel) + 0.5, size), cloudScene.a));
    return float4(clouds.cloudLight, dot(clouds.transmission, 1.0 / 3.0));
}

struct CloudResolveOutput
{
    float4 composite : SV_TARGET0;
    float4 history0 : SV_TARGET1;
    float4 history1 : SV_TARGET2;
    float2 history2 : SV_TARGET3;
};

CloudResolveOutput PSCloudResolve(float4 position : SV_POSITION)
{
    const int2 pixel = int2(position.xy);
    const float4 scene = hdr.Load(int3(pixel, 0));
    const float4 cloudScene = float4(scene.rgb, abs(scene.a));
    const float rayEnd = cloudScene.a;
    float2 size;
    hdr.GetDimensions(size.x, size.y);
    const int2 offset = int2(cloudTemporal.xy);
    const bool historyValid = cloudTemporal.z > 0.5;

    float4 light = float4(0.0, 0.0, 0.0, 1.0);
    float depthKm = 0.0, spreadKm = 0.0, shadowT = -1.0, driftPx = 0.0, cloudEnd = rayEnd;
    if (cloudCameraKm.w > 0.5l)
    {
        const bool fresh = all(pixel % CLOUD_TEMPORAL_TILE == offset);
        const int2 tile = pixel / CLOUD_TEMPORAL_TILE;
        const float4 freshLight = cloudFresh0.Load(int3(tile, 0));
        const float4 freshData = cloudFresh1.Load(int3(tile, 0));
        const float freshSpreadKm = freshData.y;
        const float3 view = CloudViewFloat(position.xy, size);
        cloudEnd = CloudTemporalCloudEnd(view, rayEnd);
        bool fillClouds = false, traceClouds = false, traceShadow = false;

        const float entryKm = CloudTemporalShellEntryKm(view);
        if (entryKm < (rayEnd > 0.0 ? rayEnd : 1.0e9)) // otherwise nothing to see before the surface
        {
            // The cloud's distance from the history at this pixel, then at the pixel it reprojects to.
            float4 historyLight = 0.0;
            float historyDepthKm = 0.0, historySpreadKm = 0.0;
            bool found = false;
            float2 prevPixel = -1.0;
            if (historyValid && !fresh)
            {
                bool seen;
                found = CloudTemporalLookup(pixel, view, cloudEnd, entryKm, size, seen, historyLight, historyDepthKm,
                    historySpreadKm, driftPx, prevPixel);
                fillClouds = !seen;
            }
            if (fresh)
            {
                light = freshLight;
                depthKm = freshData.x;
                spreadKm = freshSpreadKm;
                driftPx = 0.0;
            }
            else if (found)
            {
                light = historyLight;
                depthKm = historyDepthKm;
                spreadKm = historySpreadKm;
            }
            else if (fillClouds && CloudTemporalCloudFill(pixel, cloudEnd, offset, size, light, depthKm, spreadKm))
                driftPx = 0.75 * CLOUD_TEMPORAL_DRIFT_PX; // unseen by the history: from the fresh tiles, a stand-in
                                                          // that motion soon has traced, before it spreads
            // Under the gate, nor by the fresh tiles, as the sky through a new gap in the leaves: from the history's
            // texels nearby. Traced here, alone in its wave, a few dozen such pixels a frame held the whole pass, up to
            // 3 ms in a fast flight (round 8). A gap of sky the history does not see either stays clear for this frame,
            // then the quads retrace it; a surface is traced, its clouds in front differ from its neighbours'.
            else if (fillClouds && CloudTemporalHalfOn() && CloudTemporalInside(prevPixel, size))
            {
                // (Nested: HLSL's && evaluates both sides.)
                if (CloudTemporalHistoryFill(prevPixel, cloudEnd, size, light, depthKm, spreadKm))
                    driftPx = 0.75 * CLOUD_TEMPORAL_DRIFT_PX;
                else if (rayEnd <= 0.0)
                {
                    light = float4(0.0, 0.0, 0.0, 1.0);
                    driftPx = CLOUD_TEMPORAL_DRIFT_PX;
                }
                else
                    traceClouds = true;
            }
            else if (historyValid && !fillClouds && CloudTemporalHalfOn())
            {
                // Drifted or turned, under the gate: from this frame's quads traced for it. Rebuilt, a stand-in as
                // the fill; the quad's own pixel is exact. (Nested: HLSL's && evaluates both sides.)
                if (CloudTemporalHalfFill(pixel, cloudEnd, size, light, depthKm, spreadKm))
                {
                    driftPx = all(pixel % 2 == CloudTemporalHalfPixel()) ? 0.0 : 0.75 * CLOUD_TEMPORAL_DRIFT_PX;
                }
                else
                    traceClouds = true;
            }
            else
                traceClouds = true; // after a jump, or drifted above the gate: traced
        }

        const float3 sunRGB = sunPart.Load(int3(pixel, 0)).rgb;
        if (rayEnd > 0.0 && max(sunRGB.r, max(sunRGB.g, sunRGB.b)) > 1.0e-6)
        {
            if (fresh)
                shadowT = freshData.z;
            else
            {
                float prevDistanceKm;
                const float2 prevPixel = CloudTemporalPrevPixel(view * rayEnd, cloudPrevGround[0], cloudPrevGround[1],
                    cloudPrevGround[2], size, prevDistanceKm);
                if (!historyValid || !CloudTemporalShadowHistory(prevPixel, prevDistanceKm, size, shadowT))
                    shadowT = CloudTemporalShadowFill(pixel, rayEnd, offset, size);
                traceShadow = shadowT < 0.0;
            }
        }

        [branch]
        if (traceClouds || traceShadow)
        {
            // Where the history is missing or drifted, trace the central ray now, as in the single pass.
            const CloudPixel traced = CloudTracePixel(cloudScene, position.xy, size, traceClouds,
                traceShadow, false);
            if (traceClouds)
            {
                light = float4(traced.cloudLight, dot(traced.transmission, 1.0 / 3.0));
                depthKm = traced.depthKm;
                spreadKm = traced.depthSpreadKm;
                driftPx = 0.0;
            }
            if (traceShadow)
                shadowT = traced.surfaceShadowT;
        }
    }

    CloudPixel clouds;
    clouds.cloudLight = light.rgb;
    clouds.transmission = light.a;
    clouds.depthKm = depthKm;
    clouds.depthSpreadKm = spreadKm;
    clouds.surfaceShadowT = shadowT >= 0.0 ? shadowT : 1.0;
    CloudResolveOutput output;
    output.composite = PreserveOceanMotion(CloudComposite(cloudScene, position.xy, size, clouds), scene.a);
    output.history0 = light;
    output.history1 = float4(depthKm, rayEnd, shadowT, cloudEnd);
    output.history2 = float2(spreadKm, driftPx);
    return output;
}

#endif // CLOUDS_TEMPORAL_HLSLI
