#ifndef FOLIAGE_WIND_HLSLI
#define FOLIAGE_WIND_HLSLI
float WindWave(float x) {
    float a=abs(frac(x+0.5)*2.0-1.0);
    return 2.0*a*a*(3.0-2.0*a)-1.0;
}
// Near meshes only: both wind layers reach zero before the mesh/impostor relay.
// The two material passes receive identical time, seed and vertices. No simulation state or CPU work per plant.
void AnimateFoliageWeighted(ObjectInstance o,float localHeight,bool leaf,float shootWeight,float leafWeight,float sourcePhase,inout float3 position,inout float3 normal) {
    const uint kind=(o.seed>>3)&3u;
    float visible=PlanetFoliageStoredWindShare(o);
    float speed=length(foliageWind.xyz), force=min(speed/6.0,2.0)*visible;
    if (force<=0.0) return;
    float3 up=PlantUp(o), direction=foliageWind.xyz-up*dot(up,foliageWind.xyz);
    direction*=rsqrt(max(dot(direction,direction),1e-8));
    uint hash=o.seed*0x9e3779b9u; hash^=hash>>16;
    float phase=(hash&65535u)/65536.0, t=foliageWind.w;
    float gust=0.65+0.25*WindWave(t*0.125+phase)+0.10*WindWave(t*0.375+phase);
    float height=saturate(localHeight), flexibility=kind==SHRUB ? 0.048 : 0.012;
    float amplitude=force*flexibility*gust;
    const float physicalHeight=Scale(o).y;
    position+=direction*(physicalHeight*height*height*amplitude);
    normal=normalize(normal-up*(2.0*height*amplitude*dot(normal,direction)));
    if (leaf) {
        float flutter=WindWave(t*1.875+phase*7.0+height*0.5+sourcePhase)*min(0.018,0.012*physicalHeight)*height*force;
        position+=normal*(flutter*shootWeight);
        position+=up*(WindWave(t*2.625+phase*5.0+sourcePhase)*min(0.008,0.004*physicalHeight)*height*force*leafWeight);
    }
}
void AnimateFoliage(ObjectInstance o,float localHeight,bool leaf,inout float3 position,inout float3 normal) {
    AnimateFoliageWeighted(o,localHeight,leaf,1.0,0.0,0.0,position,normal);
}
#endif
