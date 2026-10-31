#include "PlanetFoliageCommon.hlsli"
Texture2DArray<float4> meshColour : register(t34);
Texture2DArray<float4> meshNormal : register(t35);
Texture2DArray<float4> meshMask : register(t36);
SamplerState meshAnisotropicWrap : register(s1);
struct VOut { float4 position:SV_POSITION; float3 pos:POSITION; float3 normal:NORMAL; float2 uv:TEXCOORD0; nointerpolation float material:TEXCOORD1; nointerpolation uint instance:TEXCOORD2; float localHeight:TEXCOORD3; float4 visibility0:TEXCOORD4; float4 visibility1:TEXCOORD5; };

float3 MaterialNormal(float3 normal, float3 map, float3 position, float3 dpdx, float3 dpdy, float2 duvdx, float2 duvdy) {
    float n2=dot(normal,normal);
    float3 n=n2>1e-12 ? normal*rsqrt(n2) : float3(0,1,0);
    float det=duvdx.x*duvdy.y-duvdx.y*duvdy.x;
    float uvScale=sqrt(dot(duvdx,duvdx)*dot(duvdy,duvdy));
    if (uvScale<1e-20 || abs(det)<1e-5*uvScale) return n;
    // Le signe du déterminant conserve l'orientation des UV en miroir.
    float signDet=det<0 ? -1.0 : 1.0;
    float3 tangent=(dpdx*duvdy.y-dpdy*duvdx.y)*signDet;
    float3 bitangent=(dpdy*duvdx.x-dpdx*duvdy.x)*signDet;
    tangent-=n*dot(n,tangent);
    float t2=dot(tangent,tangent), b2=dot(bitangent,bitangent);
    if (t2<1e-20 || b2<1e-20) return n;
    tangent*=rsqrt(t2);
    float3 b=cross(n,tangent);
    b*=dot(b,bitangent)<0 ? -1.0 : 1.0;
    float3 detail=map*2.0-1.0;
    // Une perturbation bornée évite qu'une carte trop contrastée retourne la feuille.
    detail.xy*=0.55; detail.z=max(detail.z,0.35);
    float xyLength=length(detail.xy);
    detail.xy*=min(1.0,0.8*detail.z/max(xyLength,1e-6));
    float3 mapped=normalize(tangent*detail.x+b*detail.y+n*detail.z);
    // Orienter les deux faces d'après la normale du maillage, puis éviter qu'un
    // détail à ras de la vue ne provoque un retournement de l'éclairage entier.
    float face=dot(n,position)>0.0 ? -1.0 : 1.0;
    mapped*=face; n*=face;
    return dot(mapped,position)>0.0 ? n : mapped;
}

Result PSMain(VOut i) {
    // Avant les rejets, afin de conserver des dérivées cohérentes aux bords alpha.
    float3 dpdx=ddx(i.pos), dpdy=ddy(i.pos);
    float2 duvdx=ddx(i.uv), duvdy=ddy(i.uv);
    ObjectInstance o=plants[i.instance]; Transition(i.position.xy,o,true);
    uint material=min((uint)i.material,materialCount-1);
    // UV continues, une couche par matériau : le matériel choisit les mips et le filtrage anisotrope.
    float3 uv=float3(i.uv,material);
    float4 colour=meshColour.SampleGrad(meshAnisotropicWrap,uv,duvdx,duvdy);
    clip(colour.a-0.5);
    if ((flags&1u)==0) return OutputVolume(colour.rgb,i.normal,i.pos,o,i.localHeight,false,1,1,0,i.visibility0,i.visibility1);
    float3 normalMap=meshNormal.SampleGrad(meshAnisotropicWrap,uv,duvdx,duvdy).xyz;
    float3 mask=meshMask.SampleGrad(meshAnisotropicWrap,uv,duvdx,duvdy).xyz;
    float3 normal=MaterialNormal(i.normal,normalMap,i.pos,dpdx,dpdy,duvdx,duvdy);
    return OutputVolume(colour.rgb,normal,i.pos,o,i.localHeight,true,mask.x,mask.y,mask.z,i.visibility0,i.visibility1);
}
