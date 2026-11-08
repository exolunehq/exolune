#include "Celestial.hlsli"
Texture2D<float4> skyScene : register(t0);
struct StarImage {
    float4 position:SV_POSITION;
    noperspective float2 offset:TEXCOORD0;
    nointerpolation float3 flux:TEXCOORD1;
    nointerpolation float solidAngle:TEXCOORD2;
};
float StarMagnitude(uint k) {
    const float counts[10]={1,4,16,49,171,513,1600,4800,15000,42000};
    const float magnitudes[10]={-1.46,0,1,2,3,4,5,6,7,8};
    float magnitude=8.0;
    [unroll] for(uint j=1;j<10;++j) if(k+1>=counts[j-1] && k+1<=counts[j])
        magnitude=lerp(magnitudes[j-1],magnitudes[j],log(float(k+1)/counts[j-1])/log(counts[j]/counts[j-1]));
    return magnitude;
}
StarImage VSMain(uint vertex:SV_VertexID,uint id:SV_InstanceID) {
    float2 size; skyScene.GetDimensions(size.x,size.y);
    float3 direction,flux;
    if(id<CELESTIAL_STARS) {
        const uint key=CelestialHash(id+953u);
        const float phi=6.2831853*CelestialRandom(key), z=2.0*CelestialRandom(key+1)-1.0;
        float latitude=z;
        if(id>171 && CelestialRandom(key+2)<.55)
            latitude=clamp(.12*sqrt(-2.0*log(max(CelestialRandom(key+3),1e-6)))*cos(6.2831853*CelestialRandom(key+4)),-1.0,1.0);
        const float r=sqrt(max(0.0,1.0-latitude*latitude));
        direction=CelestialLocal(GalaxyWorld(float3(r*cos(phi),r*sin(phi),latitude)));
        const float tint=CelestialRandom(key+5);
        float3 color=lerp(float3(.64,.78,1.0),float3(1.0,.68,.39),tint*tint);
        color/=dot(color,CELESTIAL_LUMA);
        flux=MagnitudeFlux(StarMagnitude(id))*color;
    } else {
        const uint body=id-CELESTIAL_STARS;
        direction=normalize(celestialPosition[body].xyz);
        flux=celestialFlux[body].rgb*(1.0-BodyResolved(body,2.0*camUp.w/size.y));
    }
    const float forward=dot(direction,camForward.xyz);
    const float2 ndc=float2(dot(direction,camRight.xyz)/camRight.w,dot(direction,camUp.xyz)/camUp.w)/max(forward,1e-6);
    const float2 corners[6]={float2(-1,-1),float2(-1,1),float2(1,1),float2(-1,-1),float2(1,1),float2(1,-1)};
    const float radius=clamp(4.0+log2(1.0+dot(flux,CELESTIAL_LUMA)/1e-12),4.0,22.0);
    const float2 offset=corners[vertex]*radius;
    StarImage o;
    o.position=float4(ndc+offset*2.0/size,0,1);
    if(forward<=0.0 || any(abs(ndc)>1.1) || max(flux.r,max(flux.g,flux.b))<=0.0) o.position=float4(2,2,0,1);
    o.offset=offset;
    o.flux=flux;
    o.solidAngle=4.0*camRight.w*camUp.w/(size.x*size.y)*pow(max(forward,1e-6),3.0);
    return o;
}
