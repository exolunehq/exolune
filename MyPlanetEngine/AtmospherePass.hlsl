// The atmosphere pass, full screen: the clouds and the air over the scene, in linear light, into the composite image.
// Here the single full-resolution pass, PSMain (MYPLANETENGINE_CLOUD_FULL, the clouds' diagnostic views); otherwise the
// clouds' temporal pass, whose entry points the wrappers CloudTrace.hlsl, CloudTraceHalf.hlsl and CloudResolve.hlsl
// compile from this file (CloudsTemporal.hlsli).
#include "Planet.hlsli"
#include "Atmosphere.hlsli"

Texture2D<float4> hdr : register(t0); // alpha: surface distance (km), negative when ocean motion is visible

#include "Clouds.hlsli"

float4 PreserveOceanMotion(float4 result, float inputAlpha)
{
    result.a = inputAlpha < 0.0 ? -abs(result.a) : abs(result.a);
    return result;
}

float4 PSMain(float4 position : SV_POSITION, out float4 skyTransport : SV_TARGET1) : SV_TARGET0
{
    const float4 scene = hdr.Load(int3(position.xy, 0));
    const float4 cloudScene = float4(scene.rgb, abs(scene.a)); // cloud rays always consume a positive distance
    float2 size;
    hdr.GetDimensions(size.x, size.y);
    return PreserveOceanMotion(RenderClouds(cloudScene, position.xy, size, skyTransport), scene.a);
}

#include "CloudsTemporal.hlsli"
