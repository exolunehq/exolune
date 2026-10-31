#ifndef SHRUB_CLIMATE_HLSLI
#define SHRUB_CLIMATE_HLSLI
// Seuils de direction artistique sur les mêmes champs que les arbres ; ils ne
// définissent pas des frontières géographiques. Les mélanges restent continus.
struct ShrubWeights { float3 first; float3 second; };
ShrubWeights ShrubClimate(Vegetation v, float temperature) {
    float mountain=saturate(max(1.0-smoothstep(5.5,9.0,v.season),
        smoothstep(0.1,0.7,v.exposure)*(1.0-smoothstep(11.0,16.0,v.season))));
    float rest=1.0-mountain;
    float boreal=rest*saturate(v.conifer); rest-=boreal;
    float desert=rest*(1.0-smoothstep(0.18,0.38,v.aridity)); rest-=desert;
    float steppe=rest*(1.0-smoothstep(0.55,1.05,v.aridity)); rest-=steppe;
    float tropical=rest*smoothstep(16.0,24.0,temperature)*smoothstep(0.55,1.05,v.aridity);
    float temperate=rest-tropical;
    ShrubWeights w;
    w.first=float3(boreal,desert,steppe);
    w.second=float3(mountain,temperate,tropical);
    return w;
}
uint ShrubClimateFamily(ShrubWeights w, uint seed) {
    uint h=seed ^ 0x9d8b126fu; h^=h>>16; h*=0x7feb352du; h^=h>>15; h*=0x846ca68bu; h^=h>>16;
    float choice=((h&0x00ffffffu)+0.5)/16777216.0;
    float3 a=w.first, b=w.second;
    if ((choice-=a.x)<0) return 0;
    if ((choice-=a.y)<0) return 1;
    if ((choice-=a.z)<0) return 2;
    if ((choice-=b.x)<0) return 3;
    if ((choice-=b.y)<0) return 4;
    return 5;
}
float ShrubClimateMeanHeight(ShrubWeights w) {
    return dot(w.first,float3(0.65,0.85,0.60))+dot(w.second,float3(0.30,1.0,1.15));
}
#endif
