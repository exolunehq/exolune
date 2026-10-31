#ifndef PLANET_FOLIAGE_LOD_HLSLI
#define PLANET_FOLIAGE_LOD_HLSLI
#include "Planet.hlsli"
#include "Objects.hlsli"

float2 PlanetFoliageOwn(ObjectInstance o) {
    return 1.0 + float2(0.15,0.1)*(float2((o.seed >> uint2(8,16)) & 255u)/127.5-1.0);
}

// Encombrement de la couronne approximée par un cylindre vertical, à sa profondeur proche.
float PlanetFoliagePixels(ObjectInstance o, uint species) {
    float2 own=PlanetFoliageOwn(o);
    float3 up=normalize(o.pos+float3(camPlane.xy,faceParams.y+faceParams.z));
    float h=o.size*own.y*(species==2 ? ShrubHeight(ShrubFamily(o)) : 1.0);
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
#endif
