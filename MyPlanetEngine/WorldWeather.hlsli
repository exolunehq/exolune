// The shared cloud-water query for the canopy and the listener. Requires Clouds.hlsli.
#ifndef WORLD_WEATHER_HLSLI
#define WORLD_WEATHER_HLSLI
float3 WorldWeather(double3 positionKm) // rain, cloud droplets, extinction per km
{
    if (cloudCameraKm.w < 0.5l) return 0.0;
    const double3 originQ = CloudWeatherBackDP(positionKm, cloudWind.xy);
    const double3 upQ = CloudNormalizeDP(originQ);
    const CloudContext context = CloudPrepareContext(originQ, upQ, upQ);
    const float h = CloudAltitude(context.entryOffsetKm, context);
    float altitude, depth = 0.0;
    float4 weather;
    bool cirrus;
    const float density = CloudMeanDensity(context.entryOffsetKm, context, 0.0, 0.0, false, altitude, weather, cirrus);
    [loop] for (int i = 0; i < 8; ++i) {
        const float above = max(CLOUD_LOW_BOTTOM_KM - h, 0.0) + (i + 0.5) * 0.75;
        depth += 80.0 * 0.75 * CloudMeanDensity(context.entryOffsetKm + context.viewQ * above, context, 2.0, 2.0,
                                              false, altitude, weather, cirrus);
    }
    const float extinction = 80.0 * density;
    const float cumulus = CloudSampleWeather(context.entryOffsetKm, context).g;
    const float shower = smoothstep(0.6, 0.9, cumulus) * smoothstep(15.0, 60.0, depth);
    return float3(shower * (h < CLOUD_LOW_BOTTOM_KM ? 1.0 : 0.6), saturate(extinction / 20.0), extinction);
}
#endif
