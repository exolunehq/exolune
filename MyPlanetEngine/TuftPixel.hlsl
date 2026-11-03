// The grass tufts (docs/spec-objets-proximite.md): the ground's grass colour at their place, darker at the foot where
// the blades shade each other, lighter at the tips; lit like the ground and the stones (ObjectPixel.hlsl), on both
// faces, with the sun's light through the blades.
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "Objects.hlsli"
#include "CanopyLighting.hlsli"

float4 PSMain(ObjectPixel input, out float4 sunOut : SV_TARGET1) : SV_TARGET0
{
    sunOut=0.0;
    if (taa.y > 24.5) // the height and distance views (PixelShader.hlsl): on the ground, as is
        return float4((taa.y > 25.5 ? saturate(length(input.pos) / 4000.0) : 0.0).xxx, 1e-3);
    if (taa.y > 0.5) // the objects' diagnostic view: white on the black ground
        return float4(1.0, 1.0, 1.0, 1e-3);

    // The face seen, its normal bent two thirds of the way to the vertical: a tuft is lit as a whole, as the ground under
    // it, not blade by blade, which would read as noise.
    const float3 up = normalize(input.up), sun = lightDir.xyz;
    float3 normal = normalize(input.normal);
    if (dot(normal, input.pos) > 0.0)
        normal = -normal;
    normal = normalize(normal + 2.0 * up);
    const float rise = saturate(input.rise);
    const float3 albedo = saturate(input.albedo * lerp(0.7, 1.6, rise)); // the tips paler, drier, than the ground's mean

    const float h = max(input.elevation, 0.0) / 1000.0, muS = dot(up, sun), haze = RegionalGround(PlanetDirection(up));
    const float shade = lerp(0.6, 1.0, rise); // the tuft's own shade, deep at its foot
    const CanopyTransport transport=CanopyLight(input.canopy,0,muS);
    const float3 beam=SUN_ILLUMINANCE*SunTransmittance(h,muS,haze);
    const float3 bounce=beam*transport.sunScatter*float3(0.45,0.65,0.32);
    const float3 sunColour = beam*transport.direct;
    const float3 sunLight = sunColour * (saturate(dot(normal, sun)) + 0.3 * saturate(muS)) * shade;
    const float3 sky = SkyIrradiance(h, muS, haze)*transport.sky,solarGround=sunColour*saturate(muS)+bounce,ground=solarGround+sky;
    const float3 skyLight = ((sky+bounce) * (0.5 + 0.5 * dot(normal, up)) + GROUND_ALBEDO * ground * (0.5 - 0.5 * dot(normal, up))) * shade;
    sunOut=float4(albedo/PI*(sunLight+(bounce*(0.5+0.5*dot(normal,up))+GROUND_ALBEDO*solarGround*(0.5-0.5*dot(normal,up)))*shade),0.0);
    return float4(albedo / PI * (sunLight + skyLight), length(input.pos) / 1000.0);
}
