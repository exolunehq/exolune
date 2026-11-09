// At subpixel relief scale, read the existing world maps instead of running a local terrain stack.
#include "PlanetMap.hlsli"
#include "Climate.hlsli"
#include "BiomePalette.hlsli"
float3 DistantPlanetAlbedo(float3 direction,float footprint,out float elevation) {
    elevation=planetMap.SampleLevel(lunarSampler,direction,MapLevel(direction,footprint)).x;
    const float4 climate=ClimateAt(lunarSampler,direction,footprint);
    const float temperature=climate.y-.0065*elevation;
    const float t=saturate((temperature-BIOME_T_MIN)/(BIOME_T_MAX-BIOME_T_MIN))*(BIOME_T_BINS-1);
    const float h=saturate(ClimateHumidity(climate.x))*(BIOME_H_BINS-1);
    const uint ti=min((uint)t,BIOME_T_BINS-2),hi=min((uint)h,BIOME_H_BINS-2);
    const float3 a=lerp(BIOME_PALETTE[ti*BIOME_H_BINS+hi].rgb,BIOME_PALETTE[ti*BIOME_H_BINS+hi+1].rgb,frac(h));
    const float3 b=lerp(BIOME_PALETTE[(ti+1)*BIOME_H_BINS+hi].rgb,BIOME_PALETTE[(ti+1)*BIOME_H_BINS+hi+1].rgb,frac(h));
    const float3 land=lerp(lerp(a,b,frac(t)),float3(.65,.68,.70),1-smoothstep(-8,1,temperature));
    return lerp(float3(.007,.021,.033),land,smoothstep(0,20,elevation));
}
