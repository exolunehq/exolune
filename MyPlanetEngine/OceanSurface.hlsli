// One parametric FFT surface for displacement, normal, roughness and foam.
#ifndef OCEAN_SURFACE_HLSLI
#define OCEAN_SURFACE_HLSLI
#include "OceanUniform.hlsli"
Texture2DArray<float4> oceanDisplacement : register(t11);
Texture2DArray<float4> oceanDerivatives : register(t12);
Texture2DArray<float4> oceanMoments : register(t13);
Texture2DArray<float4> oceanPores : register(t14);
Texture2DArray<float4> oceanFoam0 : register(t15);
Texture2DArray<float4> oceanFoam1 : register(t16);
SamplerState oceanSampler : register(s2);
float OceanDepthFade(uint c,float elevation) {
    return smoothstep(0.0,max(1.0,0.05*oceanLengths[c]),max(-elevation,0.0));
}
float3 OceanGeometry(float2 rest,float cell,float elevation) {
    float3 displacement=0.0;
    [unroll]for(uint c=0;c<OCEAN_CASCADES;++c) {
        float lod=log2(max(cell/(oceanLengths[c]/OCEAN_N),1.0))+0.5;
        if(lod<8.0) displacement+=OceanDepthFade(c,elevation)
            *oceanDisplacement.SampleLevel(oceanSampler,float3(rest/oceanLengths[c]+oceanOrigin[c].xy,c),lod).xyz;
    }
    return displacement;
}
struct OceanSurfaceData {
    float2 slope;float3 jacobian;float3 lost;float3 whole;
    float incidentHeight, heightLost, heightWhole; // before shoaling damping; shared FFT means and moments
};
OceanSurfaceData OceanRead(float2 rest,float2 dx,float2 dy,float elevation) {
    OceanSurfaceData r=(OceanSurfaceData)0;
    [unroll]for(uint c=0;c<OCEAN_CASCADES;++c) {
        float inv=1.0/oceanLengths[c], fade=OceanDepthFade(c,elevation);
        float3 uv=float3(rest*inv+oceanOrigin[c].xy,c);
        float4 d=oceanDerivatives.SampleGrad(oceanSampler,uv,dx*inv,dy*inv)*fade;
        float4 incident=oceanDisplacement.SampleGrad(oceanSampler,uv,dx*inv,dy*inv), a=incident*fade;
        float4 moments=oceanMoments.SampleGrad(oceanSampler,uv,dx*inv,dy*inv);
        float4 total=oceanMoments.SampleLevel(oceanSampler,float3(0.5,0.5,c),8.0);
        float3 m=moments.xyz*fade*fade;
        r.slope+=d.xy;r.jacobian+=float3(d.z,a.w,d.w);
        r.lost+=float3(max(m.x-d.x*d.x,0.0),max(m.y-d.y*d.y,0.0),m.z-d.x*d.y);
        r.whole+=total.xyz*fade*fade;
        r.incidentHeight+=incident.y;
        r.heightLost+=max(moments.w-incident.y*incident.y,0.0);
        r.heightWhole+=total.w;
    }
    return r;
}
float4 OceanStoredFoam(float2 rest,float2 dx,float2 dy,uint level) {
    float inv=1.0/oceanFoamOrigin[level].w;
    float3 uv=float3(rest*inv+oceanFoamOrigin[level].xy,level);
    if(oceanRender.x<0.5) return oceanFoam0.SampleGrad(oceanSampler,uv,dx*inv,dy*inv);
    return oceanFoam1.SampleGrad(oceanSampler,uv,dx*inv,dy*inv);
}
float3 TransformCovariance(float3 c,float3 inverseJ) {
    float a=inverseJ.x,b=inverseJ.y,d=inverseJ.z;
    return float3(a*a*c.x+b*b*c.y+2*a*b*c.z,
                  b*b*c.x+d*d*c.y+2*b*d*c.z,
                  a*b*c.x+b*d*c.y+(a*d+b*b)*c.z);
}
#endif
