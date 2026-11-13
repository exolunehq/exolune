// The game's clouds: a volume of two layers, the low clouds from 2 to 8 km and the cirrus from 9 to 13 km, drawn from a
// planetary weather map (coverage, kind, cirrus; computed at startup from the climate, Climate::Weather) and two tiling
// noise volumes fixed on the planet (assets/clouds, manifest.json), carried east by the wind. Ray marched from the camera in double precision, lit by the sun through six
// steps toward it, a droplet Henyey-Greenstein phase, calibrated multiple scattering and the atmosphere's tables;
// seen far, a pixel integrates statistical cloud columns at its footprint's mip. The ground under them takes their shadow (t17, the terrain's sunlit part). Drawn by the single
// pass (RenderClouds, AtmospherePass.hlsl) or by the temporal pass (CloudsTemporal.hlsli); the frame, b1, is D3DApp's
// CloudFrame.
//
// Adapted from Wicked Engine's volumetric clouds, volumetricCloudsHF.hlsli and volumetricCloud_renderCS.hlsl (commit
// 5433f0a6), Copyright (c) 2026 Turánszki János, MIT license: third_party/WickedEngine/LICENSE.txt and NOTICE.
#ifndef CLOUDS_HLSLI
#define CLOUDS_HLSLI

Texture2D<float4> sunPart : register(t17); // the surface's direct sunlight (D3DApp's sunlit part): what the shadow takes off
SamplerState cloudWrap : register(s2);     // the noise volumes, wrapping

cbuffer CloudFrame : register(b1)
{
    double4 cloudCameraKm; // w: 1 with the clouds (key N)
    double4 cloudForward;
    double4 cloudRightTan;
    double4 cloudUpTan;
    double4 cloudWind;     // xy: the wind's angle, sine and cosine; z: 1 for the reference quality (key C)
    double4 cloudSun;
    // The cloud temporal pass (CloudsTemporal.hlsli): the previous camera's right, up and forward rows, w its
    // offset, applied to a current camera-relative offset (km); for a point carried by the weather, then fixed to the ground.
    float4 cloudPrevQ[3];
    float4 cloudPrevGround[3];
    float4 cloudTemporal; // xy: the pixel traced in each 4x4 tile this frame; z: 1 when the history is valid; w: reserved
};

Texture3D<float4> cloudShape : register(t24);    // R: low shape; G: cirrus fibres; B: twice the shape's subtexel sigma, computed at upload
Texture3D<float4> cloudDetail : register(t25);   // R: erosion; B: twice its subtexel sigma, computed at upload
Texture3D<float4> cloudProfiles : register(t26); // the vertical profiles, by kind and height
Texture2D<float4> cloudWeather : register(t27);  // the planet's weather: R coverage, G kind, B cirrus
SamplerState cloudWeatherSampler : register(s3);

// The clouds' diagnostic views (MYPLANETENGINE_VIEW, D3DApp): their opacity, drawn by CloudComposite in both passes; the
// weather map, flat over the screen, and the shadow they cast on every surface facing the sun, lit or not, drawn by the
// single pass only (RenderClouds). The ground's view, the terrain's 14th (PixelShader.hlsl), shows their silhouette over
// it (key B).
static const float CLOUD_OPACITY_VIEW = 32.0, CLOUD_WEATHER_VIEW = 33.0, CLOUD_SHADOW_VIEW = 34.0;
static const float CLOUD_SILHOUETTE_VIEW = 14.0;

static const double CLOUD_PLANET_RADIUS_KM = 6378.0l;
// Acceleration shell spanning the low cloud family and upper cirrus.
static const double CLOUD_SHELL_BOTTOM_KM = 2.0l;
static const double CLOUD_SHELL_TOP_KM = 13.0l;
static const float CLOUD_LOW_BOTTOM_KM = 2.0;
static const float CLOUD_LOW_TOP_KM = 8.0;
static const float CLOUD_CIRRUS_BOTTOM_KM = 9.0;
static const float CLOUD_CIRRUS_TOP_KM = 13.0;
static const float CLOUD_CIRRUS_DENSITY_SCALE = 0.018;
// Multiple scattering and whole-cloud reflectance, fitted to Monte Carlo slabs by tools/calage_orbite.py nuages.
// The source falls as a slab's diffuse transmission toward the sun, 1 / (1 + b tau_s) (two-stream): steep near a lit face,
// slow deep inside; an exponential fitted to the same slabs left a turret's shaded face at 57 % of its lit one, not 38.
// It builds up as 1 - e^(-k tau), tau the cloud's chord along the sun through the point: a slab's tau / mu.
static const float CLOUD_MULTI_WEIGHT = 3.40;
static const float CLOUD_MULTI_SUN_FALLOFF = 0.040;
static const float CLOUD_MULTI_THICKNESS = 0.061;
// At night, the build-up of the sky's light: a sixth of the sun's, so thin and thick tops differ under the moons.
static const float CLOUD_NIGHT_THICKNESS = 0.010;
// Diffuse light lost through a finite cloud's sides, fitted to Monte Carlo spheres
// (tools/calage_orbite.py relief); zero leakage in a plane slab.
static const float CLOUD_MULTI_LEAK = 0.20;
// The chord's samples away from the sun, doubling from 500 m: 3.5 km below a thick layer's top. Over 1.75 km, its
// build-up fell short of the slab's whole thickness: thick clouds greyed from orbit, 179 against 199 in sRGB.
static const uint CLOUD_BACK_SAMPLES = 3u;
// The cover from which an interval of the chord counts whole: a calibrated setting, judged on the views of
// 2026-11-02 (docs/spec-rendu-orbite.md); below it, the interval counts by its share.
static const float CLOUD_CHORD_COVER = 0.02;
// The march stops once this little of the light behind passes: the cloud's own light is then complete.
static const float CLOUD_OPAQUE = 0.003;
static const double CLOUD_ANCHOR_KM = 32.0l;
static const float CLOUD_SHAPE_TEXELS_PER_KM = 4.0;
static const float CLOUD_CIRRUS_SHAPE_TEXELS_PER_KM = 16.0;
static const float CLOUD_DETAIL_TEXELS_PER_KM = 8.0;
// The noises are read CLOUD_BAND_LIMIT pixels to a texel, as the relief keeps its octaves down to a few of its samples:
// at one pixel to a texel, their features of one or two pixels stood in the mean, the coverage's threshold made each pixel
// cloud or sky, and the grain moved with the view. Below the texel, the stored and unresolved deviations hold the rest.
static const float CLOUD_BAND_LIMIT = 4.0;
// Mean sigma of mip 1's 2x2x2 blocks: 0.0124 for shape, 0.0323 for erosion.
// Each finer octave halves the variance, so their unresolved sum equals this finest resolved octave.
static const float CLOUD_SHAPE_UNRESOLVED_SIGMA = 0.0124;
static const float CLOUD_DETAIL_UNRESOLVED_SIGMA = 0.033;
static const float2 CLOUD_WEATHER_SIZE = float2(1024.0, 512.0); // read at mip 0, 39 km: the map draws its forms down to 80 km
static const float CLOUD_SHADOW_MAX_SAMPLES = 256.0;
static const float CLOUD_SHADOW_MIN_STEP_KM = 0.25;
// The cirrus' fibres lie in a fixed east and north frame, the same over the whole planet.
static const double3 CLOUD_CIRRUS_ORIGIN_QKM =
    double3(-6062.570287960116l, 55.70147608612083l, 1996.203358654883l);
static const double3 CLOUD_CIRRUS_EAST_Q =
    double3(-0.31274939226952575l, 0.0l, -0.9498356792809177l);
static const double3 CLOUD_CIRRUS_NORTH_Q =
    double3(0.008288774772867049l, 0.9999619230641713l, -0.002729218673734891l);

double CloudDotDP(double3 a, double3 b)
{
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

double CloudFloorDP(double value)
{
    const int whole = (int)value;
    return (double)(value < (double)whole ? whole - 1 : whole);
}

double CloudSqrtDP(double value)
{
    if (value <= 0.0l)
        return 0.0l;
    double estimate = (double)sqrt((float)value);
    estimate = 0.5l * (estimate + value / estimate);
    estimate = 0.5l * (estimate + value / estimate);
    return estimate;
}

double3 CloudWeatherBackDP(double3 world, double2 windSinCos)
{
    const double s = windSinCos.x;
    const double c = windSinCos.y;
    return double3(c * world.x + s * world.z, world.y,
                   -s * world.x + c * world.z);
}

double3 CloudNormalizeDP(double3 value)
{
    const double lengthSquared = CloudDotDP(value, value);
    return lengthSquared > 0.0l ? value / CloudSqrtDP(lengthSquared) : double3(0.0l, 0.0l, 0.0l);
}

double CloudWrapDP(double value)
{
    return value - CloudFloorDP(value);
}

float3 CloudWrapDP3(double3 value)
{
    return (float3)double3(CloudWrapDP(value.x), CloudWrapDP(value.y),
                           CloudWrapDP(value.z));
}

bool CloudIntersectSphere(double3 origin, double3 direction, double radius,
                          out double nearDistance, out double farDistance)
{
    const double b = CloudDotDP(origin, direction);
    const double c = CloudDotDP(origin, origin) - radius * radius;
    const double discriminant = b * b - c;
    nearDistance = 0.0l;
    farDistance = 0.0l;
    if (discriminant <= 0.0l)
        return false;
    const double root = CloudSqrtDP(discriminant);
    const double q = -b - (b >= 0.0l ? root : -root);
    const double t0 = q;
    const double t1 = q != 0.0l ? c / q : -b + root;
    nearDistance = min(t0, t1);
    farDistance = max(t0, t1);
    return farDistance > max(nearDistance, 0.0l);
}

struct CloudContext
{
    float3 entryOffsetKm;
    float3 viewQ;
    float3 sunQ;
    float radiusAnchorKm;
    float altitudeAnchorKm;
    float3 upAnchor;
    float3 shapeBase;
    float3 shapeBigBase;
    float3 detailBase;
    float3 cirrusBase;
    float2 cirrusFrameKmBase;
};

CloudContext CloudPrepareContext(double3 entryQKm, double3 viewQ, double3 sunQ)
{
    CloudContext context = (CloudContext)0;
    const double3 grid = double3(
        CloudFloorDP(entryQKm.x / CLOUD_ANCHOR_KM),
        CloudFloorDP(entryQKm.y / CLOUD_ANCHOR_KM),
        CloudFloorDP(entryQKm.z / CLOUD_ANCHOR_KM));
    const double3 anchorQKm = grid * CLOUD_ANCHOR_KM;
    const double3 entryOffsetKm = entryQKm - anchorQKm;
    const double radiusAnchorKm = CloudSqrtDP(CloudDotDP(anchorQKm, anchorQKm));
    context.entryOffsetKm = (float3)entryOffsetKm;
    context.viewQ = (float3)viewQ;
    context.sunQ = (float3)sunQ;
    context.radiusAnchorKm = (float)radiusAnchorKm;
    context.altitudeAnchorKm = (float)(radiusAnchorKm - CLOUD_PLANET_RADIUS_KM);
    context.upAnchor = (float3)(anchorQKm / radiusAnchorKm);
    // Keep only the small local remainder in float; absolute planet coordinates never enter a float noise sample.
    context.shapeBase = CloudWrapDP3(anchorQKm / 32.0l);
    context.shapeBigBase = CloudWrapDP3(anchorQKm / 128.0l);
    context.detailBase = CloudWrapDP3(anchorQKm / 4.0l);
    // The cirrus' fixed east and north frame, accumulated in DP from the world anchor, never from the camera or from the
    // weather map's mapping.
    const double3 anchorFromScene = anchorQKm - CLOUD_CIRRUS_ORIGIN_QKM;
    context.cirrusBase = float3(
        (float)CloudWrapDP(CloudDotDP(anchorFromScene, CLOUD_CIRRUS_EAST_Q) / 64.0l),
        (float)CloudWrapDP(CloudDotDP(anchorFromScene, CLOUD_CIRRUS_NORTH_Q) / 16.0l),
        (float)CloudWrapDP((radiusAnchorKm - CLOUD_PLANET_RADIUS_KM) / 8.0l));
    context.cirrusFrameKmBase = float2(
        (float)CloudDotDP(anchorFromScene, CLOUD_CIRRUS_EAST_Q),
        (float)CloudDotDP(anchorFromScene, CLOUD_CIRRUS_NORTH_Q));
    return context;
}

float CloudAltitude(float3 pointOffsetKm, CloudContext context)
{
    const float radius = context.radiusAnchorKm;
    const float deltaSquared = 2.0 * radius * dot(context.upAnchor, pointOffsetKm)
        + dot(pointOffsetKm, pointOffsetKm);
    const float pointRadius = sqrt(max(radius * radius + deltaSquared, 1.0));
    return context.altitudeAnchorKm + deltaSquared / max(pointRadius + radius, 1.0);
}

float CloudRemap(float value, float oldMin, float oldMax, float newMin, float newMax)
{
    return newMin + ((value - oldMin) / max(oldMax - oldMin, 1.0e-6)) * (newMax - newMin);
}





float2 CloudWeatherUv(float3 pointOffsetKm, CloudContext context)
{
    const float3 up = normalize(context.upAnchor + pointOffsetKm / context.radiusAnchorKm);
    return float2(atan2(up.z, up.x) * (1.0 / (2.0 * PI)) + 0.5,
                  acos(clamp(up.y, -1.0, 1.0)) * (1.0 / PI));
}

float4 CloudSampleWeather(float3 pointOffsetKm, CloudContext context)
{
    const float2 uv = CloudWeatherUv(pointOffsetKm, context);
    // A cubic B-spline in four bilinear reads (Sigg and Hadwiger, GPU Gems 2, chapter 20): a map that carries a form
    // is not read bilinearly, its kinks would show once the coverage is thresholded (docs/principes.md).
    // https://developer.nvidia.com/gpugems/gpugems2/part-iii-high-quality-rendering/chapter-20-fast-third-order-texture-filtering
    const float2 position = uv * CLOUD_WEATHER_SIZE - 0.5;
    const float2 cell = floor(position);
    const float2 f = position - cell;
    const float2 f2 = f * f, f3 = f2 * f, g = 1.0 - f;
    const float2 w0 = g * g * g / 6.0;
    const float2 w1 = (3.0 * f3 - 6.0 * f2 + 4.0) / 6.0;
    const float2 w2 = (-3.0 * f3 + 3.0 * f2 + 3.0 * f + 1.0) / 6.0;
    const float2 w3 = f3 / 6.0;
    const float2 g0 = w0 + w1, g1 = w2 + w3;
    const float2 uv0 = (cell - 0.5 + w1 / g0) / CLOUD_WEATHER_SIZE;
    const float2 uv1 = (cell + 1.5 + w3 / g1) / CLOUD_WEATHER_SIZE;
    // The sampler wraps U and clamps V, the shifted reads at the poles included.
    const float4 s00 = cloudWeather.SampleLevel(cloudWeatherSampler, uv0, 0.0);
    const float4 s10 = cloudWeather.SampleLevel(cloudWeatherSampler, float2(uv1.x, uv0.y), 0.0);
    const float4 s01 = cloudWeather.SampleLevel(cloudWeatherSampler, float2(uv0.x, uv1.y), 0.0);
    const float4 s11 = cloudWeather.SampleLevel(cloudWeatherSampler, uv1, 0.0);
    return saturate(lerp(lerp(s00, s10, g1.x), lerp(s01, s11, g1.x), g1.y));
}

float CloudEmptyWeatherDistance(float2 uv, bool cirrus)
{
    const float2 mapUv = float2(frac(uv.x), saturate(uv.y));
    // Keep the B-spline's support, two texels of mip 0, inside the max-presence cell.
    // U wraps at the seam and V clamps at the poles.
    const float2 filterMarginUv = 2.0 / CLOUD_WEATHER_SIZE;

    [unroll]
    for (int mip = 7; mip >= 3; --mip)
    {
        const int width = (int)(1024u >> (uint)mip);
        const int height = (int)(512u >> (uint)mip);
        int2 cell = int2(floor(mapUv * float2((float)width, (float)height)));
        cell = clamp(cell, int2(0, 0), int2(width - 1, height - 1));
        const float2 inverseSize = 1.0 / float2((float)width, (float)height);
        const float2 safeLower = (float2)cell * inverseSize + filterMarginUv;
        const float2 safeUpper = (float2)(cell + 1) * inverseSize - filterMarginUv;
        if (any(mapUv <= safeLower) || any(mapUv >= safeUpper))
            continue;

        const float4 cellWeather = cloudWeather.Load(int3(cell, mip));
        const float cellCoverage = cirrus ? cellWeather.b : cellWeather.r;
        // Empty for the density itself: no cirrus, low coverage at most 0.03 (CloudLowDensity).
        if (cellCoverage > (cirrus ? 0.0 : 0.03))
            continue;

        // Cell edges are radial longitude planes and latitude cones. These
        // distances use the minimum planetary radius, so a ray cannot leave
        // the empty spherical cell before the returned step.
        const float latitude = (0.5 - mapUv.y) * PI;
        const float longitudeScaleKm = (float)CLOUD_PLANET_RADIUS_KM
            * max(cos(latitude), 0.0);
        const float westDistanceKm = longitudeScaleKm
            * abs(sin(2.0 * PI * (mapUv.x - safeLower.x)));
        const float eastDistanceKm = longitudeScaleKm
            * abs(sin(2.0 * PI * (safeUpper.x - mapUv.x)));
        const float northDistanceKm = (float)CLOUD_PLANET_RADIUS_KM
            * abs(sin(PI * (mapUv.y - safeLower.y)));
        const float southDistanceKm = (float)CLOUD_PLANET_RADIUS_KM
            * abs(sin(PI * (safeUpper.y - mapUv.y)));
        const float boundaryDistanceKm = min(min(westDistanceKm, eastDistanceKm),
            min(northDistanceKm, southDistanceKm));
        return min(50.0, 0.8 * boundaryDistanceKm);
    }

    return 0.0;
}

struct CloudDensitySample
{
    float fraction; // covered part of the footprint
    float density;  // density inside that covered part
};

// Normal CDF: polynomial approximation of erf, absolute error below 1e-4.
float CloudNormalCdf(float value)
{
    const float x = abs(value) * 0.70710678118;
    const float t = 1.0 / (1.0 + 0.3275911 * x);
    const float tail = 0.5 * t * (0.254829592 + t * (-0.284496736
        + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429)))) * exp(-x * x);
    return value >= 0.0 ? 1.0 - tail : tail;
}

float CloudNormalPdf(float value)
{
    return 0.39894228040 * exp(-0.5 * value * value);
}

// inCloud: fetch the shape and erosion before the profile; otherwise after the early outs, which save them in clear air.
// Nearby lighting samples share the view sample's weather, but keep their own altitude, profile and noise.
// profileSpanKm: the height the sample stands for, a light interval's; its profile is that span's mean.
CloudDensitySample CloudLowDensity(float3 pointOffsetKm, CloudContext context,
                      float detailLod, float macroLod, bool inCloud,
                      float4 weather, float altitudeKm, float profileSpanKm = 0.0)
{
    CloudDensitySample result = (CloudDensitySample)0;
    if (altitudeKm + 0.5 * profileSpanKm <= CLOUD_LOW_BOTTOM_KM
        || altitudeKm - 0.5 * profileSpanKm >= CLOUD_LOW_TOP_KM)
        return result;

    // World-anchored, camera-independent 32/128 km shape and 4 km erosion fields.
    const float3 shapeUv = frac(context.shapeBase + pointOffsetKm / 32.0);
    // Permute axes so the two shape tilings do not align.
    const float3 shapeBigUv = frac(context.shapeBigBase + pointOffsetKm / 128.0).zxy;
    const float3 detailUv = frac(context.detailBase + pointOffsetKm / 4.0);
    float2 shape = 0.0;
    float2 shapeBig = 0.0;
    float2 detail = 0.0;
    [branch]
    if (inCloud)
    {
        shape = cloudShape.SampleLevel(cloudWrap, shapeUv, macroLod).rb;
        shapeBig = cloudShape.SampleLevel(cloudWrap, shapeBigUv, max(macroLod - 2.0, 0.0)).rb;
        detail = cloudDetail.SampleLevel(cloudWrap, detailUv, min(detailLod, 5.0)).rb;
    }
    const float coverage = weather.r;
    if (coverage <= 0.03)
        return result;

    const float type = saturate(weather.g);
    // The span within the layer, read at its middle in the slice of its width (D3DApp, UploadCloudVolume): a long light
    // interval sampled at its middle lit or dropped all of its length as that middle crossed a cumulus' flat base,
    // drawing planes at fixed heights across the clouds. Outside the layer, the span holds nothing.
    const float spanFraction = profileSpanKm / 6.0;
    const float spanBottom = saturate((altitudeKm - 2.0) / 6.0 - 0.5 * spanFraction);
    const float spanTop = saturate((altitudeKm - 2.0) / 6.0 + 0.5 * spanFraction);
    const float heightFraction = 0.5 * (spanBottom + spanTop);
    const float2 profileUv = (0.5 + 63.0 * float2(type, heightFraction)) / 64.0;
    // Fixed mip 0: the profile is a deliberately low-frequency vertical reference.
    float2 profile = cloudProfiles.SampleLevel(linearClamp,
        float3(profileUv, (0.5 + 63.0 * (spanTop - spanBottom)) / 64.0), 0.0).rg;
    profile.r *= spanFraction > 0.0 ? (spanTop - spanBottom) / spanFraction : 1.0;
    if (profile.r <= 0.0)
        return result;

    [branch]
    if (!inCloud)
    {
        shape = cloudShape.SampleLevel(cloudWrap, shapeUv, macroLod).rb;
        shapeBig = cloudShape.SampleLevel(cloudWrap, shapeBigUv, max(macroLod - 2.0, 0.0)).rb;
        detail = cloudDetail.SampleLevel(cloudWrap, detailUv, min(detailLod, 5.0)).rb;
    }
    const float p = saturate(profile.r), g = saturate(profile.g);
    const float shapeMean = 0.889; // Measured mean R of the shape volume.
    const float m = shape.x + (shapeBig.x - shapeMean) - (1.0 - coverage);
    // X ~ N(mu, sigma): include scales below the texture even at mip 0, then threshold its two moments.
    const float shapeVariance = 0.25 * shape.y * shape.y
        + 0.25 * shapeBig.y * shapeBig.y
        + CLOUD_SHAPE_UNRESOLVED_SIGMA * CLOUD_SHAPE_UNRESOLVED_SIGMA;
    const float sigma = sqrt(shapeVariance);
    const float alpha = -m / sigma, beta = (coverage - m) / sigma;
    const float cdfAlpha = CloudNormalCdf(alpha), cdfBeta = CloudNormalCdf(beta);
    const float pdfAlpha = CloudNormalPdf(alpha), pdfBeta = CloudNormalPdf(beta);
    const float interval = cdfBeta - cdfAlpha, upperTail = CloudNormalCdf(-beta);
    float baseMean = clamp(m * interval + sigma * (pdfAlpha - pdfBeta)
        + coverage * upperTail, 0.0, coverage);
    const float expectedSquare = m * m * interval + 2.0 * m * sigma * (pdfAlpha - pdfBeta)
        + shapeVariance * (interval - (beta * pdfBeta - alpha * pdfAlpha))
        + coverage * coverage * upperTail;
    // The moments' bounds hold their rounding.
    const float baseSecondMoment = clamp(expectedSquare, baseMean * baseMean, coverage * baseMean);
    const float baseVariance = max(baseSecondMoment - baseMean * baseMean, 0.0);
    // Var(p b) = p^2 Var(b), with no cancellation after the profile.
    baseMean *= p;

    // U = b - g D: the shape and the erosion both spread the margin over the erosion.
    const float erosionMean = g * detail.x;
    const float detailVariance = 0.25 * detail.y * detail.y
        + CLOUD_DETAIL_UNRESOLVED_SIGMA * CLOUD_DETAIL_UNRESOLVED_SIGMA;
    const float marginMean = baseMean - erosionMean;
    const float marginSigma = sqrt(p * p * baseVariance + g * g * detailVariance);
    float positiveMean;
    if (marginSigma < 1.0e-4)
    {
        // A negligible propagated variance reduces to the exact threshold and density.
        result.fraction = marginMean > 0.0 ? 1.0 : 0.0;
        positiveMean = max(marginMean, 0.0);
    }
    else
    {
        const float z = marginMean / marginSigma;
        result.fraction = CloudNormalCdf(z);
        positiveMean = max(marginMean * result.fraction + marginSigma * CloudNormalPdf(z), 0.0);
    }
    // A closed form keeps the domain of what it replaces: U+ <= c p, so the density inside the cloud stays in [0, 1]. A
    // share under 1e-4 of the pixel is none: its mean, a difference of tails, is only rounding there.
    if (result.fraction < 1.0e-4)
        result.fraction = 0.0;
    result.density = result.fraction > 0.0
        ? saturate(positiveMean / result.fraction / max(1.0 - erosionMean, 1.0e-6) / coverage) : 0.0;
    // Sparse cumuli and sheets carry about 0.1-0.2 g/m^3 of water, versus 0.5 in frontal and convective cores.
    // The weather map carries the regime: scale extinction from 20 to 80 /km.
    const float e = saturate((coverage - 0.28) / 0.62);
    result.density *= 0.25 + 0.75 * e;
    return result;
}

CloudDensitySample CloudLowDensity(float3 pointOffsetKm, CloudContext context,
                      float detailLod, float macroLod, bool inCloud,
                      out float altitudeKm, out float4 weather)
{
    altitudeKm = CloudAltitude(pointOffsetKm, context);
    weather = 0.0;
    if (altitudeKm <= CLOUD_LOW_BOTTOM_KM
        || altitudeKm >= CLOUD_LOW_TOP_KM)
        return (CloudDensitySample)0;

    weather = CloudSampleWeather(pointOffsetKm, context);
    return CloudLowDensity(pointOffsetKm, context, detailLod, macroLod, inCloud, weather, altitudeKm);
}

// localKm: the point in the cirrus' east and north frame.
float CloudCirrusHeightEnvelope(float2 localKm, float altitudeKm)
{
    const float centerKm = 11.0
        + 0.25 * sin(0.055 * localKm.x + 0.08 * localKm.y)
        + 0.10 * sin(0.025 * localKm.x - 0.06 * localKm.y + 1.1);
    const float halfThicknessKm = 0.475
        + 0.125 * sin(0.06 * localKm.x - 0.075 * localKm.y + 0.7);
    const float normalizedHeight = abs(altitudeKm - centerKm) / halfThicknessKm;
    return 1.0 - smoothstep(0.15, 1.0, normalizedHeight);
}

float CloudCirrusDensity(float3 pointOffsetKm, CloudContext context,
                         float macroLod, float altitudeKm, float4 weather)
{
    if (altitudeKm <= CLOUD_CIRRUS_BOTTOM_KM
        || altitudeKm >= CLOUD_CIRRUS_TOP_KM)
        return 0.0;

    const float coverage = weather.b;
    if (coverage <= 0.0)
        return 0.0;
    const float2 localKm = context.cirrusFrameKmBase + float2(
        dot((float3)CLOUD_CIRRUS_EAST_Q, pointOffsetKm),
        dot((float3)CLOUD_CIRRUS_NORTH_Q, pointOffsetKm));
    const float heightEnvelope = CloudCirrusHeightEnvelope(localKm, altitudeKm);
    const float northShearKm = 0.35 * sin(6.28318530718 * (localKm.x / 19.0 + altitudeKm / 8.0))
        + 0.15 * sin(6.28318530718 * (localKm.x / 37.0 - localKm.y / 32.0
            + altitudeKm / 10.0 + 0.17));
    const float3 cirrusUv = frac(context.cirrusBase + float3(
        dot((float3)CLOUD_CIRRUS_EAST_Q, pointOffsetKm) / 64.0,
        (dot((float3)CLOUD_CIRRUS_NORTH_Q, pointOffsetKm) + northShearKm) / 16.0,
        (altitudeKm - context.altitudeAnchorKm) / 8.0));
    const float fibers = cloudShape.SampleLevel(cloudWrap, cirrusUv, macroLod).g;
    return fibers * coverage * heightEnvelope * CLOUD_CIRRUS_DENSITY_SCALE;
}

CloudDensitySample CloudDensity(float3 pointOffsetKm, CloudContext context,
                   float detailLod, float macroLod, bool inCloud,
                   float4 weather, out float altitudeKm, out bool cirrus, float profileSpanKm = 0.0)
{
    altitudeKm = CloudAltitude(pointOffsetKm, context);
    cirrus = altitudeKm > CLOUD_CIRRUS_BOTTOM_KM
        && altitudeKm < CLOUD_CIRRUS_TOP_KM;
    if (cirrus)
    {
        CloudDensitySample result;
        result.fraction = 1.0; // thin cirrus retain their mean density
        result.density = CloudCirrusDensity(pointOffsetKm, context, macroLod, altitudeKm, weather);
        return result;
    }
    return CloudLowDensity(pointOffsetKm, context, detailLod, macroLod, inCloud, weather, altitudeKm, profileSpanKm);
}

CloudDensitySample CloudDensity(float3 pointOffsetKm, CloudContext context,
                   float detailLod, float macroLod, bool inCloud,
                   out float altitudeKm, out float4 weather, out bool cirrus)
{
    altitudeKm = CloudAltitude(pointOffsetKm, context);
    cirrus = altitudeKm > CLOUD_CIRRUS_BOTTOM_KM
        && altitudeKm < CLOUD_CIRRUS_TOP_KM;
    weather = 0.0;
    if (cirrus)
    {
        weather = CloudSampleWeather(pointOffsetKm, context);
        CloudDensitySample result;
        result.fraction = 1.0; // thin cirrus retain their mean density
        result.density = CloudCirrusDensity(pointOffsetKm, context, macroLod, altitudeKm, weather);
        return result;
    }
    return CloudLowDensity(pointOffsetKm, context, detailLod, macroLod, inCloud, altitudeKm, weather);
}

// Ground shadows and ship weather consume the mean liquid water, rather than an in-cloud column.
float CloudMeanDensity(float3 pointOffsetKm, CloudContext context,
                       float detailLod, float macroLod, bool inCloud,
                       out float altitudeKm, out float4 weather, out bool cirrus)
{
    const CloudDensitySample sample = CloudDensity(pointOffsetKm, context, detailLod, macroLod,
        inCloud, altitudeKm, weather, cirrus);
    return sample.fraction * sample.density;
}

float CloudHenyeyGreenstein(float cosine, float g)
{
    const float gg = g * g;
    const float denominator = max(1.0 + gg - 2.0 * g * cosine, 1.0e-4);
    return (1.0 - gg) / (4.0 * PI * denominator * sqrt(denominator));
}

// The air along the view from beginKm to endKm, seen through the accumulated transmission. In float, from the
// camera's altitude along the ray (HeightAlong): an absolute position in float is only 0.5 m precise, and doubles
// cost the composite more than its air. view and sun in the planet's frame; viewFace, the same view in the face's,
// for the relief's shadow in the air, its shafts, and the haze over the regional ground along it (ShadowRay), as the
// atmosphere pass of main had them.
float3 CloudAirPiece(float3 view, float3 viewFace, float3 sun, float beginKm, float endKm, uint steps,
                     inout float3 transmission, out bool hitsGround)
{
    hitsGround = false;
    if (endKm <= beginKm)
        return 0.0;
    const float h0 = camVertical.w;
    const float3 up0 = normalize((float3)cloudCameraKm.xyz);
    const float mu0 = dot(up0, view), muSun0 = dot(up0, sun), nu = dot(view, sun);
    const float h = max(HeightAlong(h0, mu0, beginKm), 0.0);
    const float r0 = BOTTOM + h0, r = BOTTOM + h;
    const float mu = clamp((r0 * mu0 + beginKm) / r, -1.0, 1.0);
    const float muSun = clamp((r0 * muSun0 + beginKm * nu) / r, -1.0, 1.0);
    ShadowRay shadow;
    shadow.origin = camVertical.xyz * (BOTTOM + camVertical.w) + beginKm * viewFace;
    shadow.direction = viewFace;
    shadow.on = true;
    float3 airTransmission;
    const float3 airLight = IntegrateScattering(h, mu, muSun, nu, endKm - beginKm,
        steps, true, shadow, airTransmission, hitsGround);
    const float3 result = transmission * airLight;
    transmission *= airTransmission;
    return result;
}

struct CloudSegment
{
    double beginKm;
    double endKm;
};

uint CloudLayerSegments(double3 originQKm, double3 viewQ,
                        double bottomKm, double topKm,
                        bool localHit, double localNear, double localFar,
                        double rayEnd,
                        out CloudSegment first,
                        out CloudSegment second)
{
    first = (CloudSegment)0;
    second = (CloudSegment)0;
    if (!localHit)
        return 0u;

    double outerNear, outerFar;
    if (!CloudIntersectSphere(originQKm, viewQ,
            CLOUD_PLANET_RADIUS_KM + topKm, outerNear, outerFar))
        return 0u;

    const double beginKm = max(max(outerNear, 0.0l), max(localNear, 0.0l));
    const double endKm = min(min(outerFar, localFar), rayEnd);
    if (endKm <= beginKm)
        return 0u;

    double innerNear, innerFar;
    const bool innerHit = CloudIntersectSphere(originQKm, viewQ,
        CLOUD_PLANET_RADIUS_KM + bottomKm, innerNear, innerFar);
    if (!innerHit)
    {
        first.beginKm = beginKm;
        first.endKm = endKm;
        return 1u;
    }

    uint count = 0u;
    const double firstEndKm = min(endKm, innerNear);
    if (firstEndKm > beginKm)
    {
        first.beginKm = beginKm;
        first.endKm = firstEndKm;
        ++count;
    }
    const double secondBeginKm = max(beginKm, innerFar);
    if (endKm > secondBeginKm)
    {
        if (count == 0u)
        {
            first.beginKm = secondBeginKm;
            first.endKm = endKm;
        }
        else
        {
            second.beginKm = secondBeginKm;
            second.endKm = endKm;
        }
        ++count;
    }
    return count;
}

// The night's key light, set for each pixel by CloudTracePixel: the brightest moon over the camera, its direction in the
// weather's frame, its light on Exolune and its elevation at the camera's vertical. Without it, CloudMarch keeps the sun.
static float3 gCloudMoonQ = float3(0.0, 1.0, 0.0);
static float3 gCloudMoonLight = 0.0;
static float gCloudMoonMuCamera = 0.0;

// One interval of a light's chord from a lit point (CloudMarch). x: its optical depth, by the view's column share;
// y: the cloud it holds where it exists, its density in the cloud: averaged with the clear sky of a coarse interval, a
// cumulus would turn grey; below 2 % covered, by its share: the density in the cloud does not vanish with its cover, and
// its 1e-4 floor drew a plane at a fixed height. z: the light crossing a partly covered interval leaks out of its sides:
// the interval's own covered part f, not its share of the view's column, a pixel's quantity whose isosurfaces drew bright
// veins; only the scales the interval resolves, the finer ones are the view's own fringes.
float3 CloudChordStep(float3 pointOffsetKm, CloudContext context, float3 direction, float distanceKm, float stepKm,
                      float verticalRate, float detailLod, float macroLod, float columnFraction, float4 weather)
{
    const float3 offsetKm = pointOffsetKm + direction * (distanceKm + 0.5 * stepKm);
    const float lodAltitudeKm = CloudAltitude(offsetKm, context);
    const float shapeTexelsPerKm = lodAltitudeKm >= CLOUD_CIRRUS_BOTTOM_KM
        ? CLOUD_CIRRUS_SHAPE_TEXELS_PER_KM
        : CLOUD_SHAPE_TEXELS_PER_KM;
    const float stepShapeLod = clamp(log2(max(stepKm * shapeTexelsPerKm, 1.0)), 0.0, 7.0);
    const float stepDetailLod = max(detailLod, clamp(log2(max(stepKm * CLOUD_DETAIL_TEXELS_PER_KM, 1.0)), 0.0, 5.0));
    float altitudeKm;
    bool cirrus;
    const CloudDensitySample sample = CloudDensity(offsetKm, context, stepDetailLod, max(macroLod, stepShapeLod), true,
        weather, altitudeKm, cirrus, verticalRate * stepKm);
    return float3(saturate(sample.fraction / max(columnFraction, 1.0e-4)) * sample.density * stepKm,
        saturate(sample.fraction / CLOUD_CHORD_COVER) * sample.density * stepKm,
        saturate(1.0 + stepShapeLod - macroLod) * (1.0 - sample.fraction) * sample.fraction * sample.density * stepKm);
}

// A light's chord through a lit point: six doubling intervals toward it, taken at their middle, 7.875 km, the whole low
// layer; then CLOUD_BACK_SAMPLES of them away from it from 500 m, the rest of the cloud's chord along it. x: the optical
// depth toward the light; y: the cloud the whole chord holds; z: the side leak toward it; w: the optical depth away from
// it. Unrolled: the samples are independent, their fetches overlap.
float4 CloudChord(float3 pointOffsetKm, CloudContext context, float3 direction, float verticalRate, float detailLod,
                  float macroLod, float columnFraction, float4 weather)
{
    float4 chord = 0.0;
    float distanceKm = 0.0;
    [unroll]
    for (uint s = 0u; s < 6u + CLOUD_BACK_SAMPLES; ++s)
    {
        const bool back = s >= 6u;
        if (s == 6u)
            distanceKm = 0.0;
        const float stepKm = 0.125 * (float)(1u << (back ? s - 4u : s));
        const float3 interval = CloudChordStep(pointOffsetKm, context, back ? -direction : direction, distanceKm, stepKm,
            verticalRate, detailLod, macroLod, columnFraction, weather);
        chord += back ? float4(0.0, interval.y, 0.0, interval.x) : float4(interval.x, interval.y, interval.z, 0.0);
        distanceKm += stepKm;
    }
    return chord;
}

void CloudMarch(double3 originQKm, double3 viewQ, double3 sunQ,
                float2 size, double beginKm, double endKm,
                inout float3 cloudLight, inout float3 transmission,
                inout float weightedDepth, inout float depthWeightSum, inout float weightedDepthSq)
{
    if (endKm <= beginKm || all(transmission < CLOUD_OPAQUE))
        return;

    const double3 entryQKm = originQKm + viewQ * beginKm;
    const CloudContext context = CloudPrepareContext(entryQKm, viewQ, sunQ);
    const float segmentKm = (float)(endKm - beginKm);
    const float begin = (float)beginKm;
    const bool referenceQuality = cloudWind.z > 0.5l;
    const float nearStepKm = referenceQuality ? 0.024 : 0.048;
    const float farStepKm = referenceQuality ? 0.16 : 0.24;
    const float pixelAngle = 2.0 * (float)cloudUpTan.w / max(size.y, 1.0);
    float traveledKm = 0.0;
    float opticalStepKm = 1.0e9;
    bool retryingStep = false;
    // Maximum overlap within one ground footprint; successive columns overlap independently.
    // Clear sky joins a column when its covered fraction grows.
    float columnBeginKm = 0.0, segmentT = 1.0;
    float columnFraction = 0.0, columnT = 1.0;
    float3 columnLight = 0.0, segmentLight = 0.0;
    float segmentDepth = 0.0, segmentDepthSq = 0.0, segmentDepthWeight = 0.0;

    bool inCloud = false;
    // The exact shell interval is consumed; there is no fixed iteration cap that lengthens the step.
    [loop]
    while (traveledKm < segmentKm
        && any(transmission * segmentT * (1.0 - columnFraction * (1.0 - columnT)) >= CLOUD_OPAQUE))
    {
        const float centerDistanceKm = begin + traveledKm;
        const float footprintKm = max(centerDistanceKm * pixelAngle, nearStepKm);
        // Half the footprint along the ray, the LOD's Nyquist step; at most farStepKm of altitude per step, so that a
        // grazing ray still resolves the vertical profile without marching the full length at that step.
        const float3 startOffsetKm = context.entryOffsetKm + context.viewQ * traveledKm;
        const float verticalRate = abs(dot(normalize(context.upAnchor + startOffsetKm / context.radiusAnchorKm),
            context.viewQ));
        const float horizontalRate = sqrt(saturate(1.0 - verticalRate * verticalRate));
        if ((traveledKm - columnBeginKm) * horizontalRate > footprintKm)
        {
            // Close between accepted intervals, preserving the resolved ray's sampling and Beer integral.
            segmentLight += segmentT * columnFraction * columnLight;
            segmentT *= 1.0 - columnFraction * (1.0 - columnT);
            columnBeginKm = traveledKm;
            columnFraction = 0.0;
            columnT = 1.0;
            columnLight = 0.0;
        }
        const float stepKm = min(min(min(max(0.5 * footprintKm, nearStepKm), farStepKm / max(verticalRate, 0.02)),
            segmentKm - traveledKm), opticalStepKm);
        const float sampleDistanceKm = traveledKm + 0.5 * stepKm;
        const float3 pointOffsetKm = context.entryOffsetKm + context.viewQ * sampleDistanceKm;
        float altitudeKm;
        float4 weather;
        bool cirrus;
        const float detailLod = clamp(log2(max(CLOUD_BAND_LIMIT * footprintKm * CLOUD_DETAIL_TEXELS_PER_KM, 1.0)), 0.0, 5.0);
        const float lodAltitudeKm = CloudAltitude(pointOffsetKm, context);
        const float shapeTexelsPerKm = lodAltitudeKm >= CLOUD_CIRRUS_BOTTOM_KM
            ? CLOUD_CIRRUS_SHAPE_TEXELS_PER_KM
            : CLOUD_SHAPE_TEXELS_PER_KM;
        const float macroLod = clamp(log2(max(CLOUD_BAND_LIMIT * footprintKm * shapeTexelsPerKm, 1.0)), 0.0, 7.0);
        const CloudDensitySample sample = CloudDensity(pointOffsetKm, context, detailLod,
            macroLod, inCloud, altitudeKm, weather, cirrus);
        const bool columnWidened = sample.fraction > columnFraction + 0.02;
        const float nextFraction = columnWidened ? sample.fraction : columnFraction;
        const float density = nextFraction > 0.0
            ? min(sample.fraction, nextFraction) / nextFraction * sample.density : 0.0;
        inCloud = density > 0.0;
        const bool needsLight = columnWidened || columnT >= 0.003;
        // Droplets: 80 km^-1 per density unit, 0.5 g/m^3 at 10 um (Bohren and Huffman).
        const float extinctionPerKm = density * 80.0;
        opticalStepKm = inCloud && columnT >= 0.003 ? 1.0 / extinctionPerKm : 1.0e9;
        // Retry once from the interval's beginning, directly at the discarded sample's reciprocal extinction.
        if (!retryingStep && stepKm > opticalStepKm)
        {
            retryingStep = true;
            continue;
        }
        retryingStep = false;
        // Commit the widening only after accepting this interval: a retried midpoint contributes nothing.
        if (columnWidened)
        {
            const float oldShare = columnFraction / sample.fraction;
            columnT = oldShare * columnT + (1.0 - oldShare);
            columnLight *= oldShare;
            columnFraction = sample.fraction;
        }
        if (density > 0.0)
        {
            const float attenuation = exp(-extinctionPerKm * stepKm);
            const float3 up = normalize(context.upAnchor + pointOffsetKm / context.radiusAnchorKm);
            const float muSun = dot(up, context.sunQ);
            // A sheet receives projected sunlight; a cumulus averages its lit hemisphere.
            const float mu = cirrus ? max(muSun, 0.05)
                : max(max(muSun, 0.5 * saturate(weather.g)), 0.05);
            const float depthWeight = segmentT * columnFraction * columnT * (1.0 - attenuation);
            // An opaque partial column still marches: a larger f can expose fresh clear sky to the light.
            [branch]
            if (needsLight)
            {
                // The night's key light: no cloud sees the sun once it is 3.4 degrees below the point's horizon; from
                // there to 8 degrees, the chord turns to the brightest moon (CloudTracePixel), if that moon is up.
                const float muMoon = dot(up, gCloudMoonQ);
                const float moonWeight = any(gCloudMoonLight > 0.0)
                    ? (1.0 - smoothstep(-0.14, -0.06, muSun)) * smoothstep(-0.1, 0.05, muMoon) : 0.0;
                // The sun's chord; the moon's alone once no cloud sees the sun; both in the narrow band between.
                const bool moonOnly = moonWeight >= 1.0;
                const float4 sunChord = CloudChord(pointOffsetKm, context, moonOnly ? gCloudMoonQ : context.sunQ,
                    abs(moonOnly ? muMoon : muSun), detailLod, macroLod, columnFraction, weather);
                float4 moonChord = sunChord;
                [branch]
                if (moonWeight > 0.0 && !moonOnly)
                    moonChord = CloudChord(pointOffsetKm, context, gCloudMoonQ, abs(muMoon), detailLod, macroLod,
                        columnFraction, weather);
                const float sunDepth = sunChord.x, sunLeak = sunChord.z;
                const float moonDepth = moonChord.x, moonLeak = moonChord.z;

                const float3 directTransmittance = exp(-sunDepth * 80.0);
                const float3 sunRadiance = SUN_ILLUMINANCE * SunTransmittance(altitudeKm, muSun);
                // The moon's beam leaves the sky's light as it becomes the key light: SkyIrradiance holds it at the
                // camera's vertical (Atmosphere.hlsli).
                float3 moonRadiance = 0.0, moonBeam = 0.0;
                [branch]
                if (moonWeight > 0.0)
                {
                    moonRadiance = moonWeight * gCloudMoonLight * SunTransmittance(altitudeKm, muMoon);
                    moonBeam = moonWeight * gCloudMoonLight * SunTransmittance(altitudeKm, gCloudMoonMuCamera)
                        * saturate(gCloudMoonMuCamera);
                }
                const float3 skyIrradiance = max(SkyIrradiance(altitudeKm, muSun) - moonBeam, 0.0);
                const float3 ambientRadiance = 0.18 * SUN_ILLUMINANCE * MultiScattering(altitudeKm, muSun)
                    + 0.04 * skyIrradiance;
                // Water-droplet anisotropy (Bohren and Huffman).
                const float phase = CloudHenyeyGreenstein(dot(context.viewQ, context.sunQ), 0.85);
                const float moonPhase = CloudHenyeyGreenstein(dot(context.viewQ, gCloudMoonQ), 0.85);
                const float3 scatteringPerKm = extinctionPerKm;
                const float3 oneOrderSource = scatteringPerKm * (sunRadiance * directTransmittance * phase
                    + moonRadiance * exp(-moonDepth * 80.0) * moonPhase + ambientRadiance / (4.0 * PI));
                const float3 oneOrderIntegral = oneOrderSource * (1.0 - attenuation)
                    / max(extinctionPerKm, 1.0e-5);

                // The multiple scattering of this point, from the cloud around it: what the sun's chord through it
                // holds, both sides, builds it up (F); the light falls toward the sun as a slab's diffuse transmission
                // and leaks out of a finite cloud's sides. Neither the pixel's seen point nor its column enters the
                // build-up or the leak: they drew their isosurfaces as rims and veins.
                const float buildUp = 1.0 - exp(-CLOUD_MULTI_THICKNESS * 80.0 * sunChord.y);
                const float sunShape = buildUp * exp(-CLOUD_MULTI_LEAK * 80.0 * sunLeak)
                    / (1.0 + CLOUD_MULTI_SUN_FALLOFF * sunDepth * 80.0);
                // The key moon lights the cloud as the sun does, along its own chord.
                const float moonBuildUp = 1.0 - exp(-CLOUD_MULTI_THICKNESS * 80.0 * moonChord.y);
                const float moonShape = moonBuildUp * exp(-CLOUD_MULTI_LEAK * 80.0 * moonLeak)
                    / (1.0 + CLOUD_MULTI_SUN_FALLOFF * moonDepth * 80.0);
                const float moonMu = cirrus ? max(muMoon, 0.05) : max(max(muMoon, 0.5 * saturate(weather.g)), 0.05);
                // Once the sun has set, the sky's light (the other moons, the airglow) comes from above: its falloff
                // follows the chord upwards, away from the set sun or toward the key moon, not the chord down towards
                // the set sun, which darkened thick tops inside bright rims.
                // Moonlit tops brighten with the cloud's thickness, as its albedo does: a softer build-up than the
                // sun's, which saturates on any cumulus and left them flat white.
                const float nightChord = lerp(sunChord.y, moonChord.y, moonWeight);
                const float skywardDepth = lerp(sunChord.w, moonDepth, moonWeight);
                const float nightShape = (1.0 - exp(-CLOUD_NIGHT_THICKNESS * 80.0 * nightChord))
                    / (1.0 + 2.0 * CLOUD_MULTI_SUN_FALLOFF * skywardDepth * 80.0);
                const float skyShape = lerp(sunShape, nightShape, 1.0 - smoothstep(-0.12, 0.02, muSun));
                const float3 multiSource = scatteringPerKm * (sunRadiance * mu * sunShape + skyIrradiance * skyShape
                    + moonRadiance * moonMu * moonShape) * CLOUD_MULTI_WEIGHT / (4.0 * PI);
                const float3 multiIntegral = multiSource * (1.0 - attenuation)
                    / max(extinctionPerKm, 1.0e-5);

                columnLight += columnT * (oneOrderIntegral + multiIntegral);
            }
            segmentDepth += depthWeight * (begin + sampleDistanceKm);
            segmentDepthSq += depthWeight * (begin + sampleDistanceKm) * (begin + sampleDistanceKm);
            segmentDepthWeight += depthWeight;
            columnT *= attenuation;
        }
        // An opaque column keeps the geometric step, even as it widens.
        if (columnT < 0.003)
            opticalStepKm = 1.0e9;
        const float weatherCoverage = cirrus ? weather.b : weather.r;
        const float emptyCoverageThreshold = cirrus ? 0.0 : 0.03;
        if (density <= 0.0 && altitudeKm > (float)CLOUD_SHELL_BOTTOM_KM
            && altitudeKm < (float)CLOUD_SHELL_TOP_KM
            && weatherCoverage <= emptyCoverageThreshold)
        {
            const float2 weatherUv = CloudWeatherUv(pointOffsetKm, context);
            const float emptyDistanceKm = CloudEmptyWeatherDistance(weatherUv, cirrus);
            if (emptyDistanceKm > stepKm)
            {
                const float skipKm = min(emptyDistanceKm, segmentKm - sampleDistanceKm);
                if (skipKm > 0.0)
                {
                    // Advance from the point whose empty sector was proved, not from the segment start.
                    traveledKm = sampleDistanceKm + skipKm;
                    continue;
                }
            }
        }
        traveledKm += stepKm;
    }

    // The last column joins the closed ones.
    const float3 light = segmentLight + segmentT * columnFraction * columnLight;
    // Segments overlap independently; compose their premultiplied light and moments in ray order.
    cloudLight += transmission * light;
    const float incomingWeight = max(transmission.r, max(transmission.g, transmission.b));
    weightedDepth += incomingWeight * segmentDepth;
    weightedDepthSq += incomingWeight * segmentDepthSq;
    depthWeightSum += incomingWeight * segmentDepthWeight;
    transmission *= segmentT * (1.0 - columnFraction * (1.0 - columnT));
}

struct CloudTraceResult
{
    float3 cloudLight;
    float3 transmission;
    float weightedDepth;
    float depthWeightSum;
    float weightedDepthSq;
};

CloudTraceResult CloudTraceRay(double3 originQKm, double3 viewQ, double3 sunQ,
                               float2 size, double sceneDepthKm)
{
    CloudTraceResult result = (CloudTraceResult)0;
    result.transmission = 1.0;

    double groundNear, groundFar;
    const bool groundHit = CloudIntersectSphere(originQKm, viewQ, CLOUD_PLANET_RADIUS_KM,
        groundNear, groundFar);
    double localNear = 0.0l;
    double localFar = 1.0e300l;
    bool localHit = true;
    double rayEnd = sceneDepthKm > 0.0l ? sceneDepthKm : 1.0e300l;
    if (groundHit)
    {
        const double groundDistance = groundNear >= 0.0l ? groundNear : groundFar;
        if (groundDistance >= 0.0l)
            rayEnd = min(rayEnd, groundDistance);
    }

    if (localHit)
    {
        CloudSegment segments[4];
        [unroll]
        for (uint clearIndex = 0u; clearIndex < 4u; ++clearIndex)
            segments[clearIndex] = (CloudSegment)0;
        uint segmentCount = 0u;

        CloudSegment lowFirst, lowSecond;
        const uint lowCount = CloudLayerSegments(originQKm, viewQ,
            CLOUD_LOW_BOTTOM_KM, CLOUD_LOW_TOP_KM,
            localHit, localNear, localFar, rayEnd, lowFirst, lowSecond);
        if (lowCount > 0u)
        {
            segments[segmentCount++] = lowFirst;
            if (lowCount > 1u)
                segments[segmentCount++] = lowSecond;
        }

        CloudSegment cirrusFirst, cirrusSecond;
        const uint cirrusCount = CloudLayerSegments(originQKm, viewQ,
            CLOUD_CIRRUS_BOTTOM_KM, CLOUD_CIRRUS_TOP_KM,
            localHit, localNear, localFar, rayEnd, cirrusFirst, cirrusSecond);
        if (cirrusCount > 0u)
        {
            segments[segmentCount++] = cirrusFirst;
            if (cirrusCount > 1u)
                segments[segmentCount++] = cirrusSecond;
        }

        [unroll]
        for (uint i = 0u; i < 3u; ++i)
        {
            [unroll]
            for (uint j = 0u; j < 3u - i; ++j)
            {
                if (j + 1u < segmentCount
                    && segments[j + 1u].beginKm < segments[j].beginKm)
                {
                    const CloudSegment swap = segments[j];
                    segments[j] = segments[j + 1u];
                    segments[j + 1u] = swap;
                }
            }
        }

        [loop]
        for (uint i = 0u; i < segmentCount; ++i)
        {
            if (segments[i].endKm > segments[i].beginKm)
                CloudMarch(originQKm, viewQ, sunQ, size,
                    segments[i].beginKm, segments[i].endKm,
                    result.cloudLight, result.transmission,
                    result.weightedDepth, result.depthWeightSum, result.weightedDepthSq);
        }
    }
    // Light is never negative. ponytail: a NaN, 163 pixels in 2 million at ground level in the single pass, whose cause
    // the instrumentation hides; max() turns it to 0 before the history spreads it into blocks. Find it if it shows.
    result.cloudLight = max(result.cloudLight, 0.0);
    return result;
}

double3 CloudViewWorld(float2 pixel, float2 size)
{
    const double ndcX = 2.0l * (double)pixel.x / (double)size.x - 1.0l;
    const double ndcY = 1.0l - 2.0l * (double)pixel.y / (double)size.y;
    return CloudNormalizeDP(cloudForward.xyz
        + ndcX * cloudRightTan.w * cloudRightTan.xyz
        + ndcY * cloudUpTan.w * cloudUpTan.xyz);
}

float3 CloudViewFloat(float2 pixel, float2 size)
{
    const float2 ndc = float2(2.0 * pixel.x / size.x - 1.0, 1.0 - 2.0 * pixel.y / size.y);
    return normalize((float3)cloudForward.xyz
        + ndc.x * (float)cloudRightTan.w * (float3)cloudRightTan.xyz
        + ndc.y * (float)cloudUpTan.w * (float3)cloudUpTan.xyz);
}

float CloudShadowSegment(double3 receiverQKm, double3 sunQ,
                         double beginKm, double endKm)
{
    if (endKm <= beginKm)
        return 1.0;

    const double3 entryQKm = receiverQKm + sunQ * beginKm;
    const CloudContext context = CloudPrepareContext(entryQKm, sunQ, sunQ);
    const float segmentKm = (float)(endKm - beginKm);
    const float stepKm = max(CLOUD_SHADOW_MIN_STEP_KM,
        segmentKm / CLOUD_SHADOW_MAX_SAMPLES);
    float traveledKm = 0.0;
    float transmittance = 1.0;
    bool inCloud = false;

    // Deterministic world-space midpoint samples; the step is bounded by 256 samples per shell.
    [loop]
    while (traveledKm < segmentKm && transmittance >= 0.003)
    {
        const float step = min(stepKm, segmentKm - traveledKm);
        const float sampleDistanceKm = traveledKm + 0.5 * step;
        const float3 pointOffsetKm = context.entryOffsetKm + context.viewQ * sampleDistanceKm;
        const float altitudeKm = CloudAltitude(pointOffsetKm, context);
        const float shapeTexelsPerKm = altitudeKm >= CLOUD_CIRRUS_BOTTOM_KM
            ? CLOUD_CIRRUS_SHAPE_TEXELS_PER_KM
            : CLOUD_SHAPE_TEXELS_PER_KM;
        const float detailLod = clamp(log2(max(step * CLOUD_DETAIL_TEXELS_PER_KM, 1.0)),
            0.0, 5.0);
        const float shapeLod = clamp(log2(max(step * shapeTexelsPerKm, 1.0)), 0.0, 7.0);
        float densityAltitudeKm;
        float4 weather;
        bool cirrus;
        const float density = CloudMeanDensity(pointOffsetKm, context,
            detailLod, shapeLod, inCloud, densityAltitudeKm, weather, cirrus);
        inCloud = density > 0.0;
        if (density > 0.0)
        {
            transmittance *= exp(-80.0 * density * step);
        }
        else if (densityAltitudeKm > (float)CLOUD_SHELL_BOTTOM_KM
            && densityAltitudeKm < (float)CLOUD_SHELL_TOP_KM)
        {
            const float coverage = cirrus ? weather.b : weather.r;
            const float emptyThreshold = cirrus ? 0.0 : 0.03;
            if (coverage <= emptyThreshold)
            {
                const float2 weatherUv = CloudWeatherUv(pointOffsetKm, context);
                const float emptyDistanceKm = CloudEmptyWeatherDistance(weatherUv, cirrus);
                if (emptyDistanceKm > step)
                {
                    traveledKm = sampleDistanceKm
                        + min(emptyDistanceKm, segmentKm - sampleDistanceKm);
                    continue;
                }
            }
        }
        traveledKm += step;
    }
    return transmittance;
}

float CloudTraceShadow(double3 receiverQKm, double3 sunQ)
{
    double localNear = 0.0l;
    double localFar = 1.0e300l;
    bool localHit = true;

    CloudSegment segments[4];
    [unroll]
    for (uint clearIndex = 0u; clearIndex < 4u; ++clearIndex)
        segments[clearIndex] = (CloudSegment)0;
    uint segmentCount = 0u;

    CloudSegment lowFirst, lowSecond;
    const uint lowCount = CloudLayerSegments(receiverQKm, sunQ,
        CLOUD_LOW_BOTTOM_KM, CLOUD_LOW_TOP_KM,
        localHit, localNear, localFar, 1.0e300l, lowFirst, lowSecond);
    if (lowCount > 0u)
    {
        segments[segmentCount++] = lowFirst;
        if (lowCount > 1u)
            segments[segmentCount++] = lowSecond;
    }

    CloudSegment cirrusFirst, cirrusSecond;
    const uint cirrusCount = CloudLayerSegments(receiverQKm, sunQ,
        CLOUD_CIRRUS_BOTTOM_KM, CLOUD_CIRRUS_TOP_KM,
        localHit, localNear, localFar, 1.0e300l, cirrusFirst, cirrusSecond);
    if (cirrusCount > 0u)
    {
        segments[segmentCount++] = cirrusFirst;
        if (cirrusCount > 1u)
            segments[segmentCount++] = cirrusSecond;
    }

    [unroll]
    for (uint i = 0u; i < 3u; ++i)
    {
        [unroll]
        for (uint j = 0u; j < 3u - i; ++j)
        {
            if (j + 1u < segmentCount
                && segments[j + 1u].beginKm < segments[j].beginKm)
            {
                const CloudSegment swap = segments[j];
                segments[j] = segments[j + 1u];
                segments[j + 1u] = swap;
            }
        }
    }

    float transmittance = 1.0;
    [loop]
    for (uint i = 0u; i < segmentCount && transmittance >= 0.003; ++i)
    {
        transmittance *= CloudShadowSegment(receiverQKm, sunQ,
            segments[i].beginKm, segments[i].endKm);
    }
    return transmittance;
}

// The clouds seen through one pixel: premultiplied light, Beer transmission, their weighted distance, the cloud
// transmittance toward the sun at the surface behind them (1 where there is no lit surface).
struct CloudPixel
{
    float3 cloudLight;
    float3 transmission;
    float depthKm;
    float depthSpreadKm; // the standard deviation of the distance its light comes from
    float surfaceShadowT;
};

// withClouds, withShadow: what to trace, the clouds through the pixel, the shadow on its surface; shadowEverywhere: the
// shadow on any surface facing the sun, lit or not, for its view.
CloudPixel CloudTracePixel(float4 scene, float2 pixel, float2 size, bool withClouds, bool withShadow,
                           bool shadowEverywhere)
{
    const double3 viewWorld = CloudViewWorld(pixel, size);
    const double3 originWorldKm = cloudCameraKm.xyz;
    const double2 windSinCos = cloudWind.xy;
    const double3 sunWorld = CloudNormalizeDP(cloudSun.xyz);
    const double3 originQKm = CloudWeatherBackDP(originWorldKm, windSinCos);
    const double3 viewQ = CloudNormalizeDP(CloudWeatherBackDP(viewWorld, windSinCos));
    const double3 sunQ = CloudNormalizeDP(CloudWeatherBackDP(sunWorld, windSinCos));
    const double sceneDepthKm = scene.a > 0.0 ? (double)scene.a : 0.0l;
    const bool cloudsOn = cloudCameraKm.w > 0.5l && withClouds;
    // The night's key light (CloudMarch): the brightest moon over the camera, seen from Exolune.
    float brightest = 0.0;
    [unroll]
    for (uint moon = 0u; moon < 3u; ++moon)
    {
        const float3 direction = MoonDirectionFrom(moon, camVertical.xyz * PLANET_RADIUS_KM);
        const float muCamera = dot(direction, camVertical.xyz);
        const float weight = dot(Moonlight(moon), CELESTIAL_LUMA) * saturate(muCamera + 0.2);
        if (weight > brightest)
        {
            brightest = weight;
            gCloudMoonLight = Moonlight(moon);
            gCloudMoonMuCamera = muCamera;
            gCloudMoonQ = (float3)CloudNormalizeDP(CloudWeatherBackDP((double3)CelestialWorld(direction), windSinCos));
        }
    }

    CloudTraceResult resolvedTrace = (CloudTraceResult)0;
    resolvedTrace.transmission = 1.0;
    if (cloudsOn)
        resolvedTrace = CloudTraceRay(originQKm, viewQ, sunQ, size, sceneDepthKm);

    CloudPixel result;
    result.cloudLight = resolvedTrace.cloudLight;
    result.transmission = resolvedTrace.transmission;
    result.depthKm = resolvedTrace.depthWeightSum > 1.0e-6
        ? resolvedTrace.weightedDepth / resolvedTrace.depthWeightSum : 0.0;
    result.depthSpreadKm = resolvedTrace.depthWeightSum > 1.0e-6 ? sqrt(max(resolvedTrace.weightedDepthSq
        / resolvedTrace.depthWeightSum - result.depthKm * result.depthKm, 0.0)) : 0.0;
    result.surfaceShadowT = 1.0;
    if (scene.a > 0.0 && cloudCameraKm.w > 0.5l && withShadow)
    {
        const double3 receiverQKm = originQKm + viewQ * (double)scene.a;
        const double3 receiverUpQ = CloudNormalizeDP(receiverQKm);
        const double muSun = CloudDotDP(receiverUpQ, sunQ);
        if (muSun > 0.0l)
        {
            const float3 sunRGB = sunPart.Load(int3(pixel, 0)).rgb;
            if (shadowEverywhere || max(sunRGB.r, max(sunRGB.g, sunRGB.b)) > 1.0e-6)
                result.surfaceShadowT = CloudTraceShadow(receiverQKm, sunQ);
        }
    }
    return result;
}

// What the clouds let through to what lies behind them. The march stops once CLOUD_OPAQUE passes; behind an opaque
// cloud that remainder would still show the Sun or a moon's disc, ten to a hundred thousand times brighter than the
// cloud, as a sharp circle. Taken off, continuously: a thin cloud still shows the disc, a thick one hides it.
float3 CloudBeyond(float3 transmission)
{
    return saturate((transmission - CLOUD_OPAQUE) / (1.0 - CLOUD_OPAQUE));
}

// The atmosphere over the scene with the clouds at their distance, at the pixel's centre.
float4 CloudComposite(float4 scene, float2 pixel, float2 size, CloudPixel clouds, out float4 skyTransport)
{
    skyTransport=0.0;
    if (abs(taa.y - CLOUD_OPACITY_VIEW) < 0.5)
        return float4((1.0 - dot(clouds.transmission, 1.0 / 3.0)).xxx, 0.0);
    // The terrain's diagnostic views are measures, not light: neither clouds nor air over them (the benches), but the
    // ground's, the clouds' silhouette.
    if (taa.y > 0.5 && abs(taa.y - CLOUD_SILHOUETTE_VIEW) >= 0.5)
        return scene;
    const float3 view = CloudViewFloat(pixel, size);
    const float2 ndc = float2(2.0 * pixel.x / size.x - 1.0, 1.0 - 2.0 * pixel.y / size.y);
    const float3 viewFace = normalize(camForward.xyz + ndc.x * camRight.w * camRight.xyz + ndc.y * camUp.w * camUp.xyz);
    const float3 sun = normalize((float3)cloudSun.xyz);
    float3 surfaceSceneRgb = scene.rgb;
    if (scene.a > 0.0 && clouds.surfaceShadowT < 1.0)
    {
        // The solar attachment is half precision. Bound the removed light by
        // the full surface radiance, and preserve scene exactly when T is 1.
        const float3 sunRGB = sunPart.Load(int3(pixel, 0)).rgb;
        surfaceSceneRgb = scene.rgb - min(max(sunRGB, 0.0), max(scene.rgb, 0.0))
            * (1.0 - clouds.surfaceShadowT);
    }

    const float endKm = scene.a > 0.0 ? scene.a : 1.0e9;
    float3 airTransmission = 1.0;
    bool hitsGround;
    // 12 steps to a surface and 24 to the sky, as the atmosphere pass, along the air the view crosses
    // (IntegrateScattering). The cloud cuts in two only the step it lies in; the others keep the samples of a single
    // march. The air is then continuous in the cloud's distance: where the cloud is faint, it shows no seam as that
    // distance changes (the temporal pass reprojects an older one; split into two halves of the steps, the air's own
    // samples moved with it and drew plates).
    const uint steps = scene.a > 0.0 ? 12u : 24u;
    float3 light = 0.0;
    const float h0 = camVertical.w, r0 = BOTTOM + h0;
    const float mu0 = dot(normalize((float3)cloudCameraKm.xyz), view);
    const float topDisc = r0 * r0 * (mu0 * mu0 - 1.0) + TOP * TOP;
    float airBeginKm = 0.0, airEndKm = 0.0;
    const float groundDisc = r0 * r0 * mu0 * mu0 - h0 * (2.0 * BOTTOM + h0);
    const bool seesGround = mu0 < 0.0 && groundDisc >= 0.0; // the view meets the planet at sea level
    if (topDisc >= 0.0)
    {
        airBeginKm = h0 > ATMOSPHERE_HEIGHT_KM ? max(0.0, -r0 * mu0 - sqrt(topDisc)) : 0.0;
        airEndKm = min(endKm, -r0 * mu0 + sqrt(topDisc));
        if (seesGround)
            airEndKm = min(airEndKm, -r0 * mu0 - sqrt(groundDisc));
    }
    const float dt = (airEndKm - airBeginKm) / steps;
    if (clouds.depthKm > 0.0 && dt > 0.0)
    {
        const float cloudKm = clamp(clouds.depthKm, airBeginKm, airEndKm);
        const uint k = (uint)min(floor((cloudKm - airBeginKm) / dt), steps - 1.0);
        const float stepBeginKm = airBeginKm + k * dt, stepEndKm = stepBeginKm + dt;
        if (k > 0u)
            light += CloudAirPiece(view, viewFace, sun, 0.0, stepBeginKm, k, airTransmission, hitsGround);
        light += CloudAirPiece(view, viewFace, sun, stepBeginKm, cloudKm, 1u, airTransmission, hitsGround);
        light += airTransmission * clouds.cloudLight;
        airTransmission *= CloudBeyond(clouds.transmission);
        light += CloudAirPiece(view, viewFace, sun, cloudKm, stepEndKm, 1u, airTransmission, hitsGround);
        if (k + 1u < steps)
            light += CloudAirPiece(view, viewFace, sun, stepEndKm, endKm, steps - k - 1u, airTransmission, hitsGround);
    }
    else
    {
        light += airTransmission * clouds.cloudLight;
        airTransmission *= CloudBeyond(clouds.transmission);
        light += CloudAirPiece(view, viewFace, sun, 0.0, endKm, steps, airTransmission, hitsGround);
    }
    if (scene.a > 0.0)
        light += airTransmission * surfaceSceneRgb;
    else if (!seesGround)
        skyTransport=float4(airTransmission,0.0);
    return float4(light, scene.a);
}

// The clouds and the air over the scene, the single full-resolution pass; or one of the clouds' diagnostic views.
float4 RenderClouds(float4 scene, float2 pixel, float2 size, out float4 skyTransport)
{
    skyTransport=0.0;
    if (abs(taa.y - CLOUD_WEATHER_VIEW) < 0.5)
    {
        // North up, the whole planet: blue to orange the low clouds' coverage by their kind, magenta the cirrus.
        const float2 uv = float2(pixel.x / max(size.x, 1.0), pixel.y / max(size.y, 1.0));
        const float4 weather = saturate(cloudWeather.SampleLevel(cloudWeatherSampler, uv, 0.0));
        const float3 background = float3(0.008, 0.018, 0.075);
        const float3 lowerColor = lerp(float3(0.16, 0.58, 0.96), float3(0.96, 0.48, 0.16), weather.g);
        const float3 cirrusColor = float3(0.84, 0.20, 0.69);
        return float4(saturate(background + lowerColor * weather.r + cirrusColor * weather.b), scene.a);
    }
    const bool shadowView = abs(taa.y - CLOUD_SHADOW_VIEW) < 0.5;
    const CloudPixel clouds = CloudTracePixel(scene, pixel, size, true, true, shadowView);
    if (shadowView)
        return float4(clouds.surfaceShadowT.xxx, scene.a);
    return CloudComposite(scene, pixel, size, clouds, skyTransport);
}

#endif // CLOUDS_HLSLI
