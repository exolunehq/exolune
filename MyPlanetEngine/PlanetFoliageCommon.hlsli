#include "Planet.hlsli"
#include "Atmosphere.hlsli"
#include "Objects.hlsli"
#include "PlanetFoliageLod.hlsli"
#include "CanopyLighting.hlsli"
#include "FoliageLighting.hlsli"
#include "FoliageSequence.hlsli"
StructuredBuffer<ObjectInstance> plants : register(t0);
cbuffer PlanetFoliageSettings : register(b1) { // PlanetFoliage::Settings
    uint width, height, viewsX, viewsY;
    float3 boundsMin; float radius;
    float3 boundsMax; float crown;
    uint species, reserved, materialCount, flags; // flags : 1 matériaux, 8 lumière précalculée, 16 masqué par le HiZ
    float4 volumeParams; // force, variation de couleur par plante, réservés
    float4 depthBounds;  // imposteurs : profondeur reconstruite min, max, validité, erreur (PlanetFoliageDepth.hlsli)
    float4 rootForm;
    float4 lodForm; // current mesh level, level count, reserved
};
float3 PlantUp(ObjectInstance o) { return normalize(o.pos + float3(camPlane.xy, faceParams.y + faceParams.z)); }
float3 Scale(ObjectInstance o) {
    float2 own = PlanetFoliageOwn(o);
    float sourceWidth = rootForm.w>0.0 ? rootForm.w : max(max(boundsMax.x-boundsMin.x, boundsMax.z-boundsMin.z), 1e-5);
    float spread=species==2 ? 1.0 : o.axisY.y;
    const float height=GameVegetation() && species<SHRUB ? 1.0 : o.albedo.y>0.0 ? o.albedo.y : volumeParams.z;
    return o.size * float3(crown * spread * own.x / sourceWidth, own.y*height, crown * spread * own.x / sourceWidth);
}
float3 ToWorld(float3 p, ObjectInstance o) {
    float3 up = PlantUp(o), side = o.axisX, axisZ = cross(side, up), s = Scale(o);
    return o.pos + side*p.x*s.x + up*p.y*s.y + axisZ*p.z*s.z;
}
float3 ToLocalVector(float3 p, ObjectInstance o) {
    float3 up = PlantUp(o), s = Scale(o);
    return float3(dot(p,o.axisX),dot(p,up),dot(p,cross(o.axisX,up))) / s;
}
float3 DirectionWorld(float3 n, ObjectInstance o) {
    const float3 up=PlantUp(o), s=Scale(o);
    float3 v = o.axisX*(n.x/s.x) + up*(n.y/s.y) + cross(o.axisX,up)*(n.z/s.z);
    return dot(v,v)>1e-12 ? normalize(v) : up;
}
uint FoliagePixelHash(float2 pixel, uint seed, uint salt) {
    uint2 p=uint2(pixel); uint h=p.x*0x8da6b343u ^ p.y*0xd8163841u ^ seed ^ salt;
    h^=h>>16; h*=0x7feb352du; h^=h>>15; h*=0x846ca68bu; h^=h>>16;
    return h;
}
float RandomPixel(float2 pixel,uint seed,uint salt) {
    return ((FoliagePixelHash(pixel,seed,salt)&0x00ffffffu)+0.5)/16777216.0;
}
float FoliageCoverageSample(float2 pixel,uint seed,uint dimension) {
    const uint salts[3]={0x2f6b1c3du,0xa3c59ac3u,0x86e6b841u};
    if((((uint)(taa.z+0.5))&8192u)!=0u)
        return RandomPixel(pixel,seed^(FoliageFadeFrame()*0x9e3779b9u),salts[dimension]);
    return FoliageSequence(FoliageFadeFrame(),dimension,FoliagePixelHash(pixel,seed,salts[dimension]));
}
void ClipFoliageCoverage(float2 pixel,float coverage,ObjectInstance o) {
    if(coverage>=1.0) return;
    if(coverage<=0.0) discard;
    const float threshold=FoliageTemporalEnabled()
        ? FoliageCoverageSample(pixel,o.seed,2u) : 0.5;
    clip(coverage-threshold);
}
void Transition(float2 pixel, ObjectInstance o, bool mesh) {
    // Une seule représentation par plante, sauf dans la bande du fondu (touche H).
    // Le tramage change à chaque image : l'œil le fond, et l'antialiasing temporel quand il est actif (touche T).
    if (!FoliageFadeEnabled()) return;
    float share=PlanetFoliageStoredMeshShare(o);
    if (share>=1.0) { if (!mesh) discard;return; }
    if (share<=0.0) { if (mesh) discard;return; }
    float r=FoliageCoverageSample(pixel,o.seed,0u);
    if (mesh ? r>=share : r<share) discard;
}
float3 Light(float3 colour, float3 normal, float3 position, ObjectInstance o, float localHeight, float dispersion, out float3 sunRadiance) {
    const float3 up=PlantUp(o), sunDir=lightDir.xyz;
    const float muS=dot(up,sunDir), h=max(o.elevation,0.0)/1000.0;
    const float haze=RegionalGround(PlanetDirection(up));
    const CanopyTransport canopyLight=CanopyLight(o.axisY.z,localHeight,muS);
    const float3 sun=SUN_ILLUMINANCE*SunTransmittance(h,muS,haze)*o.axisY.x*canopyLight.direct;
    const float3 sky=SkyIrradiance(h,muS,haze)*canopyLight.sky, ground=sun*saturate(muS)+sky;
    const float3 canopyBounce=SUN_ILLUMINANCE*SunTransmittance(h,muS,haze)*o.axisY.x*canopyLight.sunScatter*float3(0.45,0.65,0.32);
    normal=normalize(normal); if(dot(normal,position)>0.0) normal=-normal;
#if defined(PLANET_FOLIAGE_IMPOSTOR)
    // L'imposteur sans visibilités précalculées : la même espérance que dans OutputVolume, k = 1 - dispersion.
    const float k=1.0-saturate(dispersion), nl=dot(normal,sunDir), lit=0.5*k*nl+0.5*lerp(0.5,abs(nl),k);
    const float normalUp=dot(normal,up)*k;
#else
    const float lit=lerp(saturate(dot(normal,sunDir)),0.25,saturate(dispersion));
    const float normalUp=dot(normal,up)*(1.0-saturate(dispersion));
#endif
    sunRadiance=colour/PI*(sun*(lit+GROUND_ALBEDO*saturate(muS)*(0.5-0.5*normalUp))+canopyBounce*(0.5+0.5*normalUp));
    return colour/PI*(sun*lit+(sky+canopyBounce)*(0.5+0.5*normalUp)+GROUND_ALBEDO*ground*(0.5-0.5*normalUp));
}
// Matériaux étendus du maillage : le modèle atmosphérique reste celui des proxies.
float3 LightMaterial(float3 colour, float3 normal, float3 position, ObjectInstance o,
                     float localHeight, float ao, float roughness, float transmission, out float3 sunRadiance) {
    const float3 up=PlantUp(o), sunDir=lightDir.xyz;
    const float muS=dot(up,sunDir), h=max(o.elevation,0.0)/1000.0;
    const float haze=RegionalGround(PlanetDirection(up));
    const CanopyTransport canopyLight=CanopyLight(o.axisY.z,localHeight,muS);
    const float3 sun=SUN_ILLUMINANCE*SunTransmittance(h,muS,haze)*o.axisY.x*canopyLight.direct;
    const float3 sky=SkyIrradiance(h,muS,haze)*canopyLight.sky, ground=sun*saturate(muS)+sky;
    normal=normalize(normal); if(dot(normal,position)>0.0) normal=-normal;
    const float3 view=normalize(-position);
    const float normalUp=dot(normal,up), nl=dot(normal,sunDir);
    const float ambient=lerp(0.45,1.0,saturate(ao));
    const float leaf=saturate(transmission),lit=lerp(saturate(nl),FoliageWrappedDiffuse(nl),leaf);
    const float back=FoliageWrappedDiffuse(-nl)*lerp(0.55,1.0,pow(saturate(dot(-sunDir,view)),4.0));
    const float3 bounce=SUN_ILLUMINANCE*SunTransmittance(h,muS,haze)*o.axisY.x*canopyLight.sunScatter*float3(0.45,0.65,0.32);
    const float3 diffuse=colour/PI*(sun*(lit+0.45*leaf*back)
        +ambient*((sky+bounce)*(0.5+0.5*normalUp)+GROUND_ALBEDO*ground*(0.5-0.5*normalUp)));
    const float specular=FoliageSpecular(normal,view,sunDir,lerp(saturate(roughness),0.62,0.55*leaf));
    sunRadiance=colour/PI*(sun*(lit+0.45*leaf*back+ambient*GROUND_ALBEDO*saturate(muS)*(0.5-0.5*normalUp))
        +ambient*bounce*(0.5+0.5*normalUp))+sun*specular;
    return diffuse+sun*specular;
}
// The direct solar attachment must be overwritten at the same depth and alpha
// coverage as colour, otherwise cloud shadows reuse the ground behind the plant.
struct Result { float4 colour : SV_TARGET0; float4 solar : SV_TARGET1; float depth : SV_DEPTH; };
Result Output(float3 colour,float3 normal,float3 position,ObjectInstance o,float localHeight,float dispersion) {
    Result result=(Result)0;
    if (taa.y > 24.5) {
        float value = taa.y > 25.5 ? saturate(length(position)/4000.0) : saturate(localHeight*Scale(o).y/64.0);
        result.colour=float4(value.xxx,1e-3);
    } else if (abs(taa.y-13.0)<0.5 || abs(taa.y-18.0)<0.5) {
        result.colour=float4(1,1,1,1e-3);
    } else if (taa.y > 0.5) {
        discard;
        result.colour=0;
    } else {
        float3 solar;
        result.colour=float4(Light(colour,normal,position,o,localHeight,dispersion,solar),length(position)/1000.0);
        result.solar=float4(solar,0.0);
    }
    float4 c=mul(float4(position,1),viewProj); result.depth=c.z/c.w; return result;
}
Result OutputMaterial(float3 colour,float3 normal,float3 position,ObjectInstance o,float localHeight,
                      float ao,float roughness,float transmission) {
    Result result=(Result)0;
    if (taa.y > 0.5) result=Output(colour,normal,position,o,localHeight,0.0);
    else {
        float3 solar;
        result.colour=float4(LightMaterial(colour,normal,position,o,localHeight,ao,roughness,transmission,solar),length(position)/1000.0);
        result.solar=float4(solar,0.0);
        float4 c=mul(float4(position,1),viewProj); result.depth=c.z/c.w;
    }
    return result;
}

// Les visibilités sont précalculées dans le repère de la plante et interpolées
// avec ses sommets ou les vues d'imposteur. Aucun assombrissement d'albédo.
Result OutputVolume(float3 colour,float3 normal,float3 position,ObjectInstance o,float localHeight,
                    bool material,float ao,float roughness,float transmission,float4 visibility0,float4 visibility1
#if defined(PLANET_FOLIAGE_IMPOSTOR)
                    ,float coherence
#endif
                    ) {
    Result result=(Result)0;
    if (abs(taa.y-44.0)<0.5 || abs(taa.y-45.0)<0.5) {
        float3 shown=colour;
        if (abs(taa.y-45.0)<0.5) {
#if defined(PLANET_FOLIAGE_IMPOSTOR)
            shown=float3(0.8,0.05,0.8);
#else
            const float3 levels[7]={float3(1,0.05,0.02),float3(1,0.4,0.02),float3(0.8,0.8,0.03),float3(0.05,0.8,0.1),float3(0.03,0.7,0.8),float3(0.03,0.2,1),float3(0.5,0.1,1)};
            shown=levels[min((uint)lodForm.x,6u)];
#endif
        }
        result.colour=float4(shown,1e-3);float4 projected=mul(float4(position,1),viewProj);result.depth=projected.z/projected.w;return result;
    }
    if ((flags&8u)==0 || volumeParams.x<=0.0 || taa.y>0.5) {
        if (material) result=OutputMaterial(colour,normal,position,o,localHeight,ao,roughness,transmission);
#if defined(PLANET_FOLIAGE_IMPOSTOR)
        else result=Output(colour,normal,position,o,localHeight,1.0-saturate(coherence));
#else
        else result=Output(colour,normal,position,o,localHeight,0.0);
#endif
    } else {
    float strength=saturate(volumeParams.x);
    float3 localSun=normalize(ToLocalVector(lightDir.xyz,o));
    float3 axisWeight=abs(localSun);
    axisWeight/=max(axisWeight.x+axisWeight.y+axisWeight.z,1e-6);
    float3 sunByAxis=float3(localSun.x>=0 ? visibility0.y : visibility0.z,
                            localSun.y>=0 ? visibility0.w : visibility1.x,
                            localSun.z>=0 ? visibility1.y : visibility1.z);
    // Remove the acquisition floors before applying the renderer's porous
    // transport. The old double floor left every crown nearly uniformly lit.
    float sunVisibility=lerp(1.0,0.025+0.975*saturate((dot(axisWeight,sunByAxis)-0.20)/0.80),strength);
    float skyVisibility=lerp(1.0,0.28+0.72*saturate((visibility0.x-0.30)/0.70),strength);
    float leaf=saturate(visibility1.w);
    uint hash=o.seed ^ 0xd32a9b5du; hash^=hash>>16; hash*=0x7feb352du; hash^=hash>>15;
    float variation=(((hash&65535u)/65535.0)*2.0-1.0)*min(volumeParams.y,0.06)*strength;
    colour*=float3(1.0+variation,1.0+0.35*variation,1.0-0.55*variation);
    const float3 up=PlantUp(o), sunDir=lightDir.xyz;
    const float muS=dot(up,sunDir), h=max(o.elevation,0.0)/1000.0;
    const float haze=RegionalGround(PlanetDirection(up));
    const CanopyTransport canopyLight=CanopyLight(o.axisY.z,localHeight,muS);
    const float3 sun=SUN_ILLUMINANCE*SunTransmittance(h,muS,haze)*o.axisY.x*canopyLight.direct;
    const float3 sky=SkyIrradiance(h,muS,haze)*canopyLight.sky, ground=sun*saturate(muS)+sky;
    normal=normalize(normal); if(dot(normal,position)>0.0) normal=-normal;
    float nl=dot(normal,sunDir), normalUp=dot(normal,up);
    float3 view=normalize(-position);
#if defined(PLANET_FOLIAGE_IMPOSTOR)
    // L'imposteur : sa normale est la moyenne des feuilles qu'il couvre, de longueur k. Renormalisée, elle tourne vers la
    // caméra, et l'imposteur s'éclairait comme une carte face à l'œil : sombre en contre-jour et sous un soleil haut,
    // clair soleil dans le dos. On prend l'espérance sur ces feuilles : E[max(0,x)] = E[x]/2 + E|x|/2, E[x] linéaire en
    // la moyenne, E|x| entre 1/2, feuilles dispersées, et |x|, une seule feuille (docs/vegetation-planetaire.md).
    const float k=saturate(coherence), spread=0.5*lerp(0.5,abs(nl),k);
    const float lit=lerp(0.5*k*nl+spread,lerp(0.25,FoliageWrappedDiffuse(nl),k),leaf);
    normalUp*=k;
    float back=lerp(spread-0.5*k*nl,lerp(0.25,FoliageWrappedDiffuse(-nl),k),leaf)*lerp(0.55,1.0,pow(saturate(dot(-sunDir,view)),4.0));
#else
    const float lit=lerp(saturate(nl),FoliageWrappedDiffuse(nl),leaf);
    float back=FoliageWrappedDiffuse(-nl)*lerp(0.55,1.0,pow(saturate(dot(-sunDir,view)),4.0));
#endif
    float transmitted=material ? saturate(transmission)*leaf : leaf;
    float ambient=material ? lerp(0.45,1.0,saturate(ao)) : 1.0;
#if defined(PLANET_FOLIAGE_IMPOSTOR)
    float3 radiance=colour/PI*(sun*sunVisibility*(lit+0.45*transmitted*back)
        +ambient*skyVisibility*(sky*(0.5+0.5*normalUp)+GROUND_ALBEDO*ground*(0.5-0.5*normalUp)));
    float3 solar=colour/PI*sun*(sunVisibility*(lit+0.45*transmitted*back)
        +ambient*skyVisibility*GROUND_ALBEDO*saturate(muS)*(0.5-0.5*normalUp));
#else
    float3 radiance=colour/PI*(sun*sunVisibility*(lit+0.45*transmitted*back)
        +ambient*skyVisibility*(sky*(0.5+0.5*normalUp)+GROUND_ALBEDO*ground*(0.5-0.5*normalUp)));
    float3 solar=colour/PI*sun*(sunVisibility*(lit+0.45*transmitted*back)
        +ambient*skyVisibility*GROUND_ALBEDO*saturate(muS)*(0.5-0.5*normalUp));
#endif
    if (material) {
        float rough=lerp(saturate(roughness),0.62,0.55*leaf);
        float specular=FoliageSpecular(normal,view,sunDir,rough);
        radiance+=sun*sunVisibility*specular;
        solar+=sun*sunVisibility*specular;
    }
    const float3 canopyBounce=SUN_ILLUMINANCE*SunTransmittance(h,muS,haze)*o.axisY.x*canopyLight.sunScatter*float3(0.45,0.65,0.32);
    const float3 scattered=colour/PI*ambient*skyVisibility*canopyBounce*(0.5+0.5*normalUp);
    radiance+=scattered;solar+=scattered;
    result.colour=float4(radiance,length(position)/1000.0);
    result.solar=float4(solar,0.0);
    float4 c=mul(float4(position,1),viewProj); result.depth=c.z/c.w;
    }
    return result;
}
