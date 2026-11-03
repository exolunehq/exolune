// The objects near the camera (docs/spec-objets-proximite.md): the ground's rock colour at their place, the rock's photo
// and its fine tile laid on them in their own frame, lit like the ground, through the atmosphere.
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "Materials.hlsli"
#include "Objects.hlsli"
#include "CanopyLighting.hlsli"

float4 PSMain(ObjectPixel input, out float4 sunOut : SV_TARGET1) : SV_TARGET0
{
    sunOut=0.0;
    if (taa.y > 24.5) // the height and distance views (PixelShader.hlsl): on the ground, as is
        return float4((taa.y > 25.5 ? saturate(length(input.pos) / 4000.0) : 0.0).xxx, 1e-3);
    if (taa.y > 0.5) // the objects' diagnostic view: white on the black ground
        return float4(1.0, 1.0, 1.0, 1e-3);

    // The rock's photo taken from above and its fine tile, on the planes of the object's own frame, as the ground's
    // materials lie on the planet's (GeneratedTexture): colour factors of mean 1, and the slopes of their relief.
    const float3 localNormal = normalize(input.localNormal);
    float3 weights = max(abs(localNormal) - 0.3, 0.0);
    weights *= weights;
    weights /= weights.x + weights.y + weights.z;
    const uint fineSlice = MATERIAL_FINE + MATERIAL_ROCK;
    const float4 mean = materialColor.SampleLevel(materialSampler, float3(0.5, 0.5, MATERIAL_ROCK_TOP), MATERIAL_LAST_MIP);
    const float4 fineMean = materialColor.SampleLevel(materialSampler, float3(0.5, 0.5, fineSlice), MATERIAL_LAST_MIP);
    float3 colour = 0.0, bump = 0.0;
    [unroll]
    for (int k = 0; k < 3; ++k)
    {
        const float3 b = Axis(k == 2 ? 0 : k + 1), c = Axis(k == 0 ? 2 : k - 1);
        const float2 uv = float2(dot(input.local, b), dot(input.local, c));
        const float4 photo = materialColor.Sample(materialSampler, float3(uv / ROCK_TOP_TILE, MATERIAL_ROCK_TOP));
        const float4 fine = materialColor.Sample(materialSampler, float3(uv / FINE_TILE, fineSlice));
        const float2 slope = (materialSurface.Sample(materialSampler, float3(uv / ROCK_TOP_TILE, MATERIAL_ROCK_TOP)).xy - 0.5) * 4.0
                           + (materialSurface.Sample(materialSampler, float3(uv / FINE_TILE, fineSlice)).xy - 0.5) * 4.0;
        colour += weights[k] * photo.rgb / mean.rgb * fine.rgb / fineMean.rgb;
        bump += weights[k] * (slope.x * b + slope.y * c);
    }
    const float3 axisZ = cross(input.axisX, input.axisY);
    const float3 bumpFace = bump.x * input.axisX + bump.y * input.axisY + bump.z * axisZ;
    // Its facets: the triangles' own normal, half of it, so that the planes' cuts read as faces and edges.
    float3 facet = normalize(cross(ddy(input.pos), ddx(input.pos)));
    if (dot(facet, input.normal) < 0.0)
        facet = -facet;
    float3 normal = normalize(normalize(input.normal) + facet);
    normal = normalize(normal - (bumpFace - dot(bumpFace, normal) * normal));
    const float3 albedo = saturate(input.albedo * colour);

    // Lit like the ground (PixelShader.hlsl): the sun through the air above, the whole sky's light, less where the
    // stone meets the ground, which hides the sky from its foot; and the light the ground sends back on its sides and
    // underside, GROUND_ALBEDO of what reaches the ground. Without it, the faces in the shade were black.
    const float3 up = normalize(input.up), sun = lightDir.xyz;
    const float h = max(input.elevation, 0.0) / 1000.0, muS = dot(up, sun), haze = RegionalGround(PlanetDirection(up));
    const float foot = lerp(0.5, 1.0, smoothstep(0.0, 0.3, input.rise));
    const CanopyTransport transport=CanopyLight(input.canopy,0,muS);
    const float3 beam=SUN_ILLUMINANCE*SunTransmittance(h,muS,haze);
    const float3 bounce=beam*transport.sunScatter*float3(0.45,0.65,0.32);
    const float3 sunLight=beam*transport.direct*saturate(dot(normal,sun));
    const float3 sky=SkyIrradiance(h,muS,haze)*transport.sky;
    const float3 solarGround=beam*transport.direct*saturate(muS)+bounce,ground=solarGround+sky;
    const float3 skyLight = ((sky+bounce) * (0.5 + 0.5 * dot(normal, up)) + GROUND_ALBEDO * ground * (0.5 - 0.5 * dot(normal, up))) * foot;
    sunOut=float4(albedo/PI*(sunLight+(bounce*(0.5+0.5*dot(normal,up))+GROUND_ALBEDO*solarGround*(0.5-0.5*dot(normal,up)))*foot),0.0);
    return float4(albedo / PI * (sunLight + skyLight), length(input.pos) / 1000.0);
}
