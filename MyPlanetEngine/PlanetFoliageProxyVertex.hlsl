#include "PlanetFoliageCommon.hlsli"
#include "PlanetFoliageVisibility.hlsli"
#include "PlanetFoliageDepth.hlsli"
ByteAddressBuffer foliageVisibility : register(t41);
struct VOut {
    float4 position:SV_POSITION; float3 ray:TEXCOORD0; nointerpolation uint instance:TEXCOORD1;
    nointerpolation float4 azTrig:TEXCOORD2; nointerpolation float4 elTrig:TEXCOORD3;
    nointerpolation uint4 viewIndex:TEXCOORD4; nointerpolation float2 viewBlend:TEXCOORD5;
};

// Une projection dont le support coupe le plan proche ne possède pas de borne finie en NDC.
void IncludeClip(float4 c, inout float2 lo, inout float2 hi, inout bool nearClip) {
    if (c.w <= 1e-5 || c.z > c.w) { nearClip = true; return; }
    float2 ndc = c.xy / c.w;
    lo = min(lo, ndc); hi = max(hi, ndc);
}

VOut VSMain(uint vertex:SV_VertexID,uint id:SV_InstanceID) {
    const float2 corners[4]={float2(-1,-1),float2(-1,1),float2(1,-1),float2(1,1)};
    ObjectInstance o=plants[id];
    uint visibilityBit=PlanetFoliageVisibilityHash(o.seed);
    if ((flags&16u)!=0 && (foliageVisibility.Load((visibilityBit>>5)*4)&(1u<<(visibilityBit&31)))==0) {
        VOut empty=(VOut)0; empty.position=float4(0,0,0,1); empty.instance=id; return empty;
    }
    if (o.size < 1e-4) { VOut empty=(VOut)0; empty.position=float4(0,0,0,1); empty.instance=id; return empty; }

    float3 up=PlantUp(o), side=o.axisX, axisZ=cross(side,up), scale=Scale(o);
    float4 base=mul(float4(o.pos,1),viewProj);
    float4 x=mul(float4(side*scale.x,0),viewProj);
    float4 y=mul(float4(up*scale.y,0),viewProj);
    float4 z=mul(float4(axisZ*scale.z,0),viewProj);
    float2 lo=1e20, hi=-1e20; bool nearClip=false;

    // Les mips et le mélange de vues peuvent étendre l'alpha hors de l'AABB.
    // Les quatre carrés entiers bornent le domaine de toutes les lectures UV.
    float3 origin=float3(dot(-o.pos,side),dot(-o.pos,up),dot(-o.pos,axisZ))/scale;
    float3 direction=normalize(origin-float3(0,0.5,0));
    float az=frac(atan2(direction.x,direction.z)/6.28318530718)*viewsX;
    float el=saturate(asin(clamp(direction.y,0.0,1.0))/1.57079632679)*(viewsY-1);
    uint a0=(uint)floor(az)%viewsX, a1=(a0+1)%viewsX;
    uint e0=(uint)floor(el), e1=min(e0+1,viewsY-1);
    float sa0,ca0,sa1,ca1,se0,ce0,se1,ce1;
    sincos(6.28318530718*a0/viewsX,sa0,ca0);
    sincos(6.28318530718*a1/viewsX,sa1,ca1);
    sincos(1.57079632679*e0/max(viewsY-1,1),se0,ce0);
    sincos(1.57079632679*e1/max(viewsY-1,1),se1,ce1);
    float4 azTrig=float4(sa0,ca0,sa1,ca1), elTrig=float4(se0,ce0,se1,ce1);
    uint4 viewIndex=uint4(a0,a1,e0,e1); float2 viewBlend=frac(float2(az,el));
    float4 centre=base+0.5*y;
    [unroll] for (uint v=0; v<4; ++v) {
        float sa=(v&1) ? sa1 : sa0, ca=(v&1) ? ca1 : ca0;
        float se=(v&2) ? se1 : se0, ce=(v&2) ? ce1 : ce0;
        float4 right=radius*(ca*x-sa*z);
        float4 viewUp=radius*(-sa*se*x+ce*y-ca*se*z);
        [unroll] for (uint k=0; k<4; ++k)
            IncludeClip(centre+corners[k].x*right+corners[k].y*viewUp,lo,hi,nearClip);
    }

    // Le quad précédent est parallèle à l'écran : ses déplacements n'affectent
    // que les coordonnées x et y en clip, sans changer sa profondeur ni son w.
    float3 mid=(boundsMin+boundsMax)*0.5;
    float4 oldCentre=base+mid.x*x+mid.y*y+mid.z*z;
    float r=max(length((boundsMax-boundsMin)*scale)*0.75,0.01);
    float2 oldLo=1e20, oldHi=-1e20; bool oldNear=false;
    [unroll] for (uint k=0; k<4; ++k)
        IncludeClip(oldCentre+float4(r*corners[k].x/camRight.w,r*corners[k].y/camUp.w,0,0),oldLo,oldHi,oldNear);
    float2 padding=float2(taa.w/camRight.w,taa.w/camUp.w);
    if (oldNear) { VOut empty=(VOut)0; empty.position=float4(0,0,0,1); empty.instance=id; return empty; }
    if (nearClip) { lo=oldLo-padding; hi=oldHi+padding; }
    else { lo=max(lo-padding,oldLo-padding); hi=max(min(hi+padding,oldHi+padding),lo); }

    float2 ndc=lerp(lo,hi,corners[vertex]*0.5+0.5);
    // Le quad à la profondeur la plus proche que l'imposteur puisse reconstruire, la borne du HiZ : le pixel la déclare
    // au plus aussi proche (SV_DepthLessEqual), et le test de profondeur rejette avant son shader ce qui est déjà caché.
    // Sans borne, le plan proche : aucun rejet.
    CullModel model;
    model.width=width; model.height=height; model.viewsX=viewsX; model.viewsY=viewsY;
    model.boundsMin=boundsMin; model.radius=radius; model.boundsMax=boundsMax; model.crown=crown;
    model.species=species; model.reserved=reserved; model.materialCount=materialCount; model.flags=flags;
    model.volumeParams=volumeParams; model.depthBounds=depthBounds; model.rootForm=rootForm;
    float nearestDepth; float2 boundLo, boundHi;
    if (!ImpostorDepthBound(o,model,nearestDepth,boundLo,boundHi)) nearestDepth=1.0;
    VOut result; result.position=float4(ndc,nearestDepth,1);
    result.ray=camForward.xyz+ndc.x*camRight.w*camRight.xyz+ndc.y*camUp.w*camUp.xyz;
    result.azTrig=azTrig; result.elTrig=elTrig; result.viewIndex=viewIndex; result.viewBlend=viewBlend;
    result.instance=id; return result;
}
