#ifndef CITY_HLSLI
#define CITY_HLSLI
#include "PlanetSettings.hlsli"
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
// Displayed draft atlases, block compressed (material texture.w = -1): BC1 colour, BC5 normal, BC1 metal-roughness.
Texture2DArray<float4> cityAtlasColor:register(t37);
Texture2DArray<float2> cityAtlasNormal:register(t38);
Texture2DArray<float4> cityAtlasOrm:register(t39);
SamplerState citySampler:register(s5);
struct CityPixel {
    float4 position:SV_POSITION;float3 pos:POSITION;float3 normal:NORMAL;
    float3 local:TEXCOORD0;float2 uv:TEXCOORD1;nointerpolation uint material:TEXCOORD2;
    nointerpolation float3 detail:TEXCOORD3;
    float ambient:TEXCOORD4;
    // Model space: metric detail, glazing and rooms follow the building, not its placement.
    float3 model:TEXCOORD5;float3 modelNormal:TEXCOORD6;
    nointerpolation float4 eye:TEXCOORD7;   // xyz: camera in model space; w: instance yaw
};
float3 CityRotate(float3 p,float a){float s,c;sincos(a,s,c);return float3(c*p.x-s*p.y,s*p.x+c*p.y,p.z);}
// The city's frame is the tangent plane at its anchor, but its points stand on the planet: x and y give the ground's
// direction and z the height above sea level, as the terrain export samples them (CityGround.hlsl). A flat frame would
// lift everything by r^2/2R: 18 cm at 1.5 km from the anchor, 5 m at 8 km.
float3 CityBend(float3 p){
    const float R=PLANET_RADIUS_KM*1000.0,u=dot(p.xy,p.xy)/(R*R);
    return float3(p.xy*(1.0+p.z/R-0.5*u),p.z-0.5*u*(R+p.z));
}
float3 CityPoint(CityVertex v,CityInstance instance){return CityBend(CityRotate(v.pos,instance.originYaw.w)+instance.originYaw.xyz);}
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
