#ifndef CITY_HLSLI
#define CITY_HLSLI
cbuffer CityFrame : register(b2) {
    float4x4 cityModel;
    float4x4 cityShadow;
    float4 citySun;
    float4 cityCamera;
};
struct CityVertex { float3 pos;float3 normal;float2 uv;float material;float ambient; };
struct CityInstance { float4 originYaw;float4 detail; };
struct CityMaterial { float4 color;float4 properties;float4 texture; };
StructuredBuffer<CityVertex> cityVertices:register(t30);
StructuredBuffer<CityInstance> cityInstances:register(t31);
StructuredBuffer<CityMaterial> cityMaterials:register(t32);
Texture2D<float> cityShadowMap:register(t33);
SamplerComparisonState cityShadowSampler:register(s4);
Texture2DArray<float4> cityColor:register(t34);
Texture2DArray<float4> cityNormal:register(t35);
Texture2DArray<float4> cityOrm:register(t36);
SamplerState citySampler:register(s5);
struct CityPixel {
    float4 position:SV_POSITION;float3 pos:POSITION;float3 normal:NORMAL;
    float3 local:TEXCOORD0;float2 uv:TEXCOORD1;nointerpolation uint material:TEXCOORD2;
    nointerpolation float3 detail:TEXCOORD3;
    float ambient:TEXCOORD4;
};
float3 CityRotate(float3 p,float a){float s,c;sincos(a,s,c);return float3(c*p.x-s*p.y,s*p.x+c*p.y,p.z);}
float3 CityPoint(CityVertex v,CityInstance instance){return CityRotate(v.pos,instance.originYaw.w)+instance.originYaw.xyz;}
float CitySunVisibility(float3 local,float3 normal){
    float4 p=mul(float4(local+normal*.045,1),cityShadow);p.xyz/=p.w;
    float2 uv=p.xy*float2(.5,-.5)+.5;
    if(any(uv<0)||any(uv>1)||p.z<0||p.z>1)return 1;
    float lit=0;
    [unroll]for(int y=-1;y<=1;++y)[unroll]for(int x=-1;x<=1;++x)
        lit+=cityShadowMap.SampleCmpLevelZero(cityShadowSampler,uv+float2(x,y)/4096,p.z-.000035);
    float edge=min(min(uv.x,uv.y),min(1-uv.x,1-uv.y));
    return lerp(1,lit/9,smoothstep(0,.045,edge));
}
#endif
