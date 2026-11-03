#ifndef PLANET_FOLIAGE_DEPTH_HLSLI
#define PLANET_FOLIAGE_DEPTH_HLSLI
#include "Planet.hlsli"
#include "Objects.hlsli"
#include "PlanetFoliageLod.hlsli"
#include "FoliageSequence.hlsli"

// Les reglages d'un modele d'imposteur, tels que le dessin les recoit (PlanetFoliage.h, Settings), et la borne de la
// profondeur reconstruite de ses moments : min, max, validite, erreur de filtrage.
struct CullModel {
    uint width, height, viewsX, viewsY;
    float3 boundsMin; float radius;
    float3 boundsMax; float crown;
    uint species, reserved, materialCount, flags;
    float4 volumeParams;
    float4 depthBounds;
    float4 rootForm;
    float4 lodForm;
};

bool Finite(float x) { return (asuint(x)&0x7f800000u)!=0x7f800000u; }
bool Finite2(float2 x) { return Finite(x.x) && Finite(x.y); }
bool Finite3(float3 x) { return Finite(x.x) && Finite(x.y) && Finite(x.z); }
bool AllFinite4(float4 x) { return Finite(x.x) && Finite(x.y) && Finite(x.z) && Finite(x.w); }

// La boite d’écran reunit les quatre carrés de lecture ; la profondeur englobe
// tous les moments HALF des mips ainsi que la contribution des alphas infimes.
// Toute situation mal conditionnee laisse la plante visible.
// La profondeur la plus proche que puisse reconstruire un imposteur, en Z inverse, et le rectangle de ses quatre vues en
// NDC : la borne du test HiZ, qui sert aussi de profondeur conservatrice au dessin (optimisation.md, round 3).
// Faux si une situation est mal conditionnee : aucune borne.
bool ImpostorDepthBound(ObjectInstance plant, CullModel m, out float depth, out float2 lo, out float2 hi) {
    depth=1; lo=-1; hi=1;
    if (m.depthBounds.z<0.5 || !m.viewsX || !m.viewsY || plant.size<1e-4 ||
        !Finite(plant.size) || !Finite(m.radius) || m.radius<=0) return false;
    float3 up=normalize(plant.pos+float3(camPlane.xy,faceParams.y+faceParams.z));
    float3 side=plant.axisX, axisZ=cross(side,up);
    float2 own=PlanetFoliageOwn(plant);
    float sourceWidth=m.rootForm.w>0.0 ? m.rootForm.w : max(max(m.boundsMax.x-m.boundsMin.x,m.boundsMax.z-m.boundsMin.z),1e-5);
    float spread=m.species==2 ? 1.0 : plant.axisY.y;
    float height=GameVegetation() && m.species<SHRUB?1.0:plant.albedo.y>0.0?plant.albedo.y:m.volumeParams.z;
    float3 scale=plant.size*float3(m.crown*spread*own.x/sourceWidth,own.y*height,m.crown*spread*own.x/sourceWidth);
    if (!Finite3(scale) || any(scale<=1e-6) ||
        max(max(scale.x,scale.y),scale.z)>8.0*min(min(scale.x,scale.y),scale.z)) return false;
    float3 origin=float3(dot(-plant.pos,side),dot(-plant.pos,up),dot(-plant.pos,axisZ))/scale;
    float3 delta=origin-float3(0,0.5,0);
    if (!Finite3(origin) || dot(delta,delta)<1e-10) return false;
    float3 direction=normalize(delta);
    float az=frac(atan2(direction.x,direction.z)/6.28318530718)*m.viewsX;
    float el=saturate(asin(clamp(direction.y,0.0,1.0))/1.57079632679)*(m.viewsY-1);
    if (!Finite(az) || !Finite(el)) return false;
    // Les arrondis de atan2/asin ne doivent pas changer le couple de vues
    // entre compute et vertex. Les vues sous l'horizon sont saturees a zero.
    float azFraction=frac(az), elFraction=frac(el);
    if (azFraction<0.01 || azFraction>0.99) return false;
    if (direction.y>0.999 || elFraction>0.99 || (el>=1.0 && elFraction<0.01)) return false;
    uint a0=(uint)floor(az)%m.viewsX, a1=(a0+1)%m.viewsX;
    uint e0=(uint)floor(el), e1=min(e0+1,m.viewsY-1);
    float sa0,ca0,sa1,ca1,se0,ce0,se1,ce1;
    sincos(6.28318530718*a0/m.viewsX,sa0,ca0); sincos(6.28318530718*a1/m.viewsX,sa1,ca1);
    sincos(1.57079632679*e0/max(m.viewsY-1,1),se0,ce0); sincos(1.57079632679*e1/max(m.viewsY-1,1),se1,ce1);
    float4 base=mul(float4(plant.pos,1),viewProj);
    float4 x=mul(float4(side*scale.x,0),viewProj), y=mul(float4(up*scale.y,0),viewProj), z=mul(float4(axisZ*scale.z,0),viewProj);
    float3 worldOrigin=plant.pos+side*origin.x*scale.x+up*origin.y*scale.y+axisZ*origin.z*scale.z;
    float4 clipOrigin=mul(float4(worldOrigin,1),viewProj);
    if (!AllFinite4(base) || !AllFinite4(x) || !AllFinite4(y) || !AllFinite4(z) || !AllFinite4(clipOrigin)) return false;
    float4 centre=base+0.5*y;
    lo=1e20; hi=-1e20;
    float nearest=1e20, maxAbsK=0;
    [unroll] for (uint v=0;v<4;++v) {
        float sa=(v&1) ? sa1 : sa0, ca=(v&1) ? ca1 : ca0;
        float se=(v&2) ? se1 : se0, ce=(v&2) ? ce1 : ce0;
        float3 viewDir=float3(sa*ce,se,ca*ce);
        float3 toCentre=float3(0,0.5,0)-origin;
        float C=dot(toCentre,viewDir);
        // sincos peut varier entre deux shaders. Encadrer ses produits avant
        // toute division, et refuser les plans de vue trop rasants.
        float errorC=0.01*dot(abs(toCentre),float3(1,1,1))+1e-5;
        if (!Finite(C) || abs(C)<0.1*max(1.0,length(origin)) || abs(C)<=errorC) return false;
        float c0=C-errorC, c1=C+errorC;
        float4 factors=1.0+float4(m.depthBounds.x/c0,m.depthBounds.x/c1,m.depthBounds.y/c0,m.depthBounds.y/c1);
        if (!AllFinite4(factors)) return false;
        float fmin=min(min(factors.x,factors.y),min(factors.z,factors.w));
        float fmax=max(max(factors.x,factors.y),max(factors.z,factors.w));
        if (fmin<0.25 || fmax>4.0) return false;
        float3 localRight=float3(ca,0,-sa), localUp=float3(-sa*se,ce,-ca*se);
        float determinant=dot(localRight,cross(localUp,viewDir));
        if (!Finite(determinant) || abs(determinant)<0.9) return false;
        // SampleColour utilise des produits scalaires : inverser la base tient
        // compte de sa non-orthogonalite en flottant.
        float3 inverseRight=cross(localUp,viewDir)/determinant;
        float3 inverseUp=cross(viewDir,localRight)/determinant;
        float4 supportRight=m.radius*(inverseRight.x*x+inverseRight.y*y+inverseRight.z*z);
        float4 supportUp=m.radius*(inverseUp.x*x+inverseUp.y*y+inverseUp.z*z);
        float4 right=m.radius*(ca*x-sa*z), viewUp=m.radius*(-sa*se*x+ce*y-ca*se*z);
        float4 trigError=0.03*m.radius*(abs(x)+abs(y)+abs(z));
        float wlo=centre.w-abs(supportRight.w)-abs(supportUp.w)-trigError.w;
        float whi=centre.w+abs(supportRight.w)+abs(supportUp.w)+trigError.w;
        float slope=max(abs(wlo-clipOrigin.w),abs(whi-clipOrigin.w))/min(abs(c0),abs(c1));
        if (!Finite(slope)) return false;
        maxAbsK=max(maxAbsK,slope);
        float4 candidates=clipOrigin.w+float4((wlo-clipOrigin.w)*fmin,(wlo-clipOrigin.w)*fmax,
                                              (whi-clipOrigin.w)*fmin,(whi-clipOrigin.w)*fmax);
        if (!AllFinite4(candidates)) return false;
        float vnear=min(min(candidates.x,candidates.y),min(candidates.z,candidates.w));
        // Les vues ignorees par SampleAux pèsent au plus 4e-6 de la somme.
        vnear=min(vnear,lerp(vnear,clipOrigin.w,4e-6));
        nearest=min(nearest,vnear);
        [unroll] for (uint k=0;k<4;++k) {
            float4 p=centre+((k&1)?right:-right)+((k&2)?viewUp:-viewUp);
            if (!AllFinite4(p) || !AllFinite4(trigError) || p.w-trigError.w<=1e-5 ||
                p.z+trigError.z>p.w-trigError.w) return false;
            float2 ndc=p.xy/p.w;
            float2 error=(trigError.xy+abs(ndc)*trigError.w)/(p.w-trigError.w);
            if (!Finite2(error)) return false;
            lo=min(lo,ndc-error); hi=max(hi,ndc+error);
        }
    }
    // Temporal coverage keeps fractional silhouette alpha below the former
    // half-alpha test. Bound reconstruction error at its actual minimum alpha.
    // La marge finale englobe aussi les arrondis de cette penalite.
    nearest-=(1.01/FOLIAGE_PROXY_ALPHA_MIN)*maxAbsK*m.depthBounds.w;
    nearest-=0.001*max(abs(nearest),1.0)+0.001;
    if (!Finite(nearest) || nearest<=1e-4) return false;
    float4 nearClip=mul(float4(camForward.xyz*nearest,1),viewProj);
    if (!AllFinite4(nearClip) || nearClip.w<=1e-5 || nearClip.z>nearClip.w) return false;
    depth=nearClip.z/nearClip.w+1e-6;
    if (!Finite(depth) || depth<=0 || depth>=1) return false;
    return true;
}
#endif
