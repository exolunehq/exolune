#ifndef BARK_DETAIL_HLSLI
#define BARK_DETAIL_HLSLI
#include "Materials.hlsli"
// Metric, rest-pose detail. The source UV map retains the tree's large bark
// structures; these millimetre/centimetre bands fill its missing close scales.
float BarkNoise(float3 p) {
    const float3 cell=floor(p);
    // The same gradient noise as ground materials; no value-noise plateaus.
    return 0.5*Noise3(uint3(int3(cell)),p-cell).x;
}
float2 BarkBands(float3 metres,float footprint) {
    float2 result=0;
    const float3 frequencies[3]={float3(18,3,18),float3(64,24,64),float3(200,120,200)};
    const float heights[3]={0.008,0.0012,0.0002};
    const float colours[3]={0.20,0.08,0.02};
    [unroll] for(uint band=0;band<3;++band) {
        const float weight=1.0-smoothstep(0.35,0.85,footprint*frequencies[band].x);
        if(weight>0.0) {
            const float value=BarkNoise(metres*frequencies[band]+float3(17*band,31*band,7*band));
            result+=value*weight*float2(heights[band],colours[band]);
        }
    }
    return result;
}
float3 BarkSurfaceNormal(float3 normal,float3 dx,float3 dy,float2 heightDerivative) {
    const float3 a=cross(dy,normal),b=cross(normal,dx);
    const float determinant=dot(dx,a);
    if(abs(determinant)<1e-12) return normal;
    float3 gradient=(heightDerivative.x*a+heightDerivative.y*b)/determinant;
    const float magnitude=length(gradient);gradient*=min(1.0,0.55/max(magnitude,1e-6));
    return normalize(normal-gradient);
}
#endif
