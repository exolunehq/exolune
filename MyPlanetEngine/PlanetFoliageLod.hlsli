#ifndef PLANET_FOLIAGE_LOD_HLSLI
#define PLANET_FOLIAGE_LOD_HLSLI
#include "Planet.hlsli"
#include "Objects.hlsli"

float2 PlanetFoliageOwn(ObjectInstance o) {
    return 1.0 + float2(0.15,0.1)*(float2((o.seed >> uint2(8,16)) & 255u)/127.5-1.0);
}

// Two 8-bit coverages remain exact in float32 through 127 logical roles.
uint PlanetFoliageCoverageBits(ObjectInstance o) { return (uint)round(frac(o.albedo.x)*131072.0); }
float PlanetFoliageStoredMeshShare(ObjectInstance o) { return float(PlanetFoliageCoverageBits(o)&255u)/255.0; }
float PlanetFoliageStoredWindShare(ObjectInstance o) { return float((PlanetFoliageCoverageBits(o)>>8u)&255u)/255.0; }

// Encombrement de la couronne approximée par un cylindre vertical, à sa profondeur proche.
float PlanetFoliagePixels(ObjectInstance o, uint species) {
    float2 own=PlanetFoliageOwn(o);
    float3 up=normalize(o.pos+float3(camPlane.xy,faceParams.y+faceParams.z));
    float h=o.size*own.y*PlantHeightFactor(o,species);
    float radius=0.5*o.size*PLANT_CROWN[species]*(species==2 ? 1.0 : o.axisY.y)*own.x;
    float3 centre=o.pos+up*(0.5*h);
    float3 alignment=float3(dot(up,camRight.xyz),dot(up,camUp.xyz),dot(up,camForward.xyz));
    float3 extent=0.5*h*abs(alignment)+radius*sqrt(saturate(1.0-alignment*alignment));
    float depth=max(dot(centre,camForward.xyz)-extent.z,1e-4);
    return 2.0*max(extent.x,extent.y)/max(depth*taa.w,1e-6);
}

float PlanetFoliageThreshold(ObjectInstance o) {
    uint h=o.seed ^ 0x71c4a9bdu;
    h^=h>>16; h*=0x7feb352du; h^=h>>15; h*=0x846ca68bu; h^=h>>16;
    return 96.0+32.0*((h & 0x00ffffffu)+0.5)/16777216.0;
}

bool PlanetFoliageMeshChoice(ObjectInstance o, uint species) {
    precise float threshold=PlanetFoliageThreshold(o);
    precise float pixels=PlanetFoliagePixels(o,species);
    // Une seule représentation par plante ; un léger saut reste possible au seuil.
    return pixels>=threshold;
}

// Fondu au relais (touche H) : part du maillage, de 0 à 0,8 seuil à 1 à 1,25 seuil.
float PlanetFoliageMeshShare(ObjectInstance o, uint species) {
    precise float threshold=PlanetFoliageThreshold(o);
    precise float pixels=PlanetFoliagePixels(o,species);
    return smoothstep(0.8*threshold,1.25*threshold,pixels);
}
// Narrow complementary transitions between neighbouring mesh levels.
float PlanetFoliageGeometryPixels(ObjectInstance o,uint species) {
    float3 up=normalize(o.pos+float3(camPlane.xy,faceParams.y+faceParams.z));
    float2 own=PlanetFoliageOwn(o);
    float height=o.size*own.y*PlantHeightFactor(o,species);
    float radius=.5*o.size*PLANT_CROWN[species]*(species==2?1.0:o.axisY.y)*own.x;
    float3 nearestAxis=o.pos+up*clamp(dot(-o.pos,up),0.0,height);
    // A near-plane-crossing crown must not force every hidden tree to L0.
    return max(height,2*radius)/max(length(nearestAxis)*taa.w,1e-5);
}
void PlanetFoliageMeshLevels(ObjectInstance o,uint species,uint count,out uint a,out uint b,out float blend) {
    a=0; b=0; blend=0;
    uint forced=count>>8u;count&=255u;
    if (forced>0u) { a=min(forced-1u,count-1u);b=a;return; }
    if (count<=1u) return;
    // Extra intermediate levels preserve the nearby master instead of pushing
    // its activation four times closer when a catalogue gains two levels.
    const float octave=count>5u ? 0.6322682 : 1.0; // log2(1.55)
    float value=clamp((float)(count-1u)-log2(max(PlanetFoliageGeometryPixels(o,species),1e-5)/PlanetFoliageThreshold(o))/octave,0.0,(float)(count-1u));
    a=(uint)floor(value); b=min(a+1u,count-1u);
    blend=smoothstep(0.35,0.65,frac(value));
    if (!FoliageFadeEnabled()) { a=blend<0.5?a:b; b=a; blend=0; }
}
float2 PlanetFoliageLevelCoverage(ObjectInstance o,uint species,uint level,uint count) {
    uint a,b; float blend; PlanetFoliageMeshLevels(o,species,count,a,b,blend);
    if (a==b) return float2(0,1);
    return level==a?float2(blend,1):float2(0,blend);
}
#endif
