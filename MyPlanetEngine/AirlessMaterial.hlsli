// Shared photo tiles, anchored grain and filtering; no water, wind ripples or biological cover.
#ifndef AIRLESS_MATERIAL_HLSLI
#define AIRLESS_MATERIAL_HLSLI
#include "Materials.hlsli"
#include "Celestial.hlsli"
#include "AirlessPhotometry.hlsli"
struct AirlessMaterial {float3 albedo,normal;float cavity;};
AirlessMaterial SampleAirlessMaterial(float3 q,float3 dx,float3 dy,float3 normal,float3 up,float albedo,float resolvedCell) {
    const float3 worldNormal=CelestialWorld(normal),worldUp=CelestialWorld(up);
    const float pixel=log2(max(max(length(dx),length(dy)),.0001));
    const float rock=smoothstep(.18,.65,1-saturate(dot(normal,up)));
    Texture fines=GeneratedTexture(MATERIAL_SAND,SAND_TILE,MATERIAL_FINE+MATERIAL_SAND,q,dx,dy,worldNormal,worldUp,0,false);
    // The common filtered bands bridge grains to the unresolved rubble between physical impact forms.
    const float widest=min(13.0,log2(max(2*resolvedCell,.01)));
    const float whole=floor(widest);
    Texture bands=DetailBands(q,pixel,-7,whole,.065,.10,0x5a91u);
    if(whole<13) {
        const Texture next=DetailBands(q,pixel,whole+1,whole+1,.065,.10,0x5a91u);
        const float blend=smoothstep(0,1,widest-whole);
        bands.slope+=blend*next.slope;bands.color*=lerp(1,next.color,blend);
    }
    fines=WithBands(fines,bands);
    Texture stones=GeneratedTexture(MATERIAL_ROCK_TOP,ROCK_TOP_TILE,MATERIAL_FINE+MATERIAL_ROCK,q,dx,dy,worldNormal,worldUp,0,false);
    stones=WithBands(stones,DetailBands(q,pixel,ROCK_BANDS.x,ROCK_BANDS.y,ROCK_BANDS.z,ROCK_BANDS.w,0x3e71u));
    const float factor=lerp(dot(fines.color,CELESTIAL_LUMA),dot(stones.color,CELESTIAL_LUMA),rock);
    const float3 slope=CelestialLocal(lerp(fines.slope,stones.slope,rock));
    AirlessMaterial m;m.albedo=saturate(albedo*factor)*(celestialSurface[erosionMode.w-1].rgb/.145);
    m.normal=normalize(normal-(slope-dot(slope,normal)*normal));m.cavity=lerp(fines.cavity,stones.cavity,rock);return m;
}
float3 AirlessIrradiance(float3 normal,float3 up,float3 view,float sunlight,float cavity) {
    const uint body=erosionMode.w-1;
    const float3 sun=celestialLight[body].xyz;
    const float3 earth=-camVertical.xyz*(PLANET_RADIUS_KM+camVertical.w)-celestialPosition[body].xyz;
    const float earthshine=PlanetShine(earth,normal);
    const float beam=celestialLight[body].w*sunlight;
    const float bounce=.025*beam*saturate(dot(up,sun))*(.5-.5*dot(normal,up))*cavity;
    return (beam*AirlessDiffuse(dot(normal,sun),dot(normal,view))+earthshine*cavity+bounce).xxx;
}
#endif
