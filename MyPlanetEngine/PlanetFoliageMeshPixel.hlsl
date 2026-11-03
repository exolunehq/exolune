#include "PlanetFoliageCommon.hlsli"
#include "BarkDetail.hlsli"
Texture2DArray<float4> meshColour : register(t34);
Texture2DArray<float4> meshNormal : register(t35);
Texture2DArray<float4> meshMask : register(t36);
SamplerState meshAnisotropicWrap : register(s1);
struct VOut { float4 position:SV_POSITION; float3 pos:POSITION; float3 normal:NORMAL; float2 uv:TEXCOORD0; nointerpolation float material:TEXCOORD1; nointerpolation uint instance:TEXCOORD2; float localHeight:TEXCOORD3; float4 visibility0:TEXCOORD4; float4 visibility1:TEXCOORD5; float rootBlend:TEXCOORD6; float4 tint:TEXCOORD7; nointerpolation float2 lodCoverage:TEXCOORD8; float3 barkPosition:TEXCOORD9; };

float3 MaterialNormal(float3 normal, float3 map, float3 position, float3 dpdx, float3 dpdy, float2 duvdx, float2 duvdy,float strength) {
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
    detail.xy*=strength; detail.z=max(detail.z,0.35);
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
    ObjectInstance o=plants[i.instance];
    const bool wood=(reserved&(1u<<(uint)i.material))==0u;
    const float footprint=max(length(ddx(i.barkPosition)),length(ddy(i.barkPosition)));
    const float2 bark=wood?BarkBands(i.barkPosition,footprint):0.0;
    const float2 barkDerivative=float2(ddx(bark.x),ddy(bark.x));
    if (i.lodCoverage.x>0.0 || i.lodCoverage.y<1.0) {
        float r=FoliageCoverageSample(i.position.xy,o.seed,1u);
        if (r<i.lodCoverage.x || r>=i.lodCoverage.y) discard;
    }
    uint material=min((uint)i.material,materialCount-1);
    // UV continues, une couche par matériau : le matériel choisit les mips et le filtrage anisotrope.
    float3 uv=float3(i.uv,material);
    float4 colour=meshColour.SampleGrad(meshAnisotropicWrap,uv,duvdx,duvdy);
    colour*=i.tint;
    const float alphaWidth=max(fwidth(colour.a),1e-3);
    Transition(i.position.xy,o,true);
    // Curved cutout leaves need subpixel coverage at their edges, not a
    // binary outline. Depth and material passes use the same seed and frame.
    ClipFoliageCoverage(i.position.xy,saturate((colour.a-0.5)/alphaWidth+0.5),o);
    if (GameVegetation() && species<SHRUB && i.rootBlend>0.0)
        colour.rgb=lerp(colour.rgb,PlantGroundColour(o),0.72*saturate(i.rootBlend));
    if (GameVegetation() && FoliageModel(o)>=23u) {
        const float green=smoothstep(0.0,0.06,colour.g-max(colour.r,colour.b));
        const float luminance=dot(colour.rgb,float3(0.2126,0.7152,0.0722));
        colour.rgb=lerp(colour.rgb,luminance*float3(1.30,0.99,0.52),green*saturate(o.albedo.z));
    }
    if ((flags&1u)==0) return OutputVolume(colour.rgb,i.normal,i.pos,o,i.localHeight,false,1,1,0,i.visibility0,i.visibility1);
    float3 normalMap=meshNormal.SampleGrad(meshAnisotropicWrap,uv,duvdx,duvdy).xyz;
    float3 mask=meshMask.SampleGrad(meshAnisotropicWrap,uv,duvdx,duvdy).xyz;
    float3 normal=MaterialNormal(i.normal,normalMap,i.pos,dpdx,dpdy,duvdx,duvdy,wood?1.0:0.55);
    if(wood) {
        normal=BarkSurfaceNormal(normal,dpdx,dpdy,barkDerivative);
        colour.rgb*=1.0+bark.y;
        mask.y=max(mask.y,0.78);
    }
    return OutputVolume(colour.rgb,normal,i.pos,o,i.localHeight,true,mask.x,mask.y,mask.z,i.visibility0,i.visibility1);
}
