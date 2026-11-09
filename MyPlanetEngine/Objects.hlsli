// Objects.hlsli - the objects near the camera (docs/spec-objets-proximite.md): an instance as the placement pass
// (ObjectPlacement.hlsl) writes it and the object shaders read it, and the shapes generated at startup (D3DApp.cpp,
// BuildRocks, BuildTufts). Must match D3DApp::ObjectInstance and D3DApp::ShapeVertex.
#ifndef OBJECTS_HLSLI
#define OBJECTS_HLSLI
#include "FoliageCatalog.hlsli"

// Frame taa.z : bit 0 masque les plantes (MYPLANETENGINE_NO_PLANTS, ou pas de catalogue) ; bit 1 le fondu
// imposteur-maillage (touche H) ; bit 2, pas de catalogue : aucune végétation, ni dessinée ni en canopée ; bits 3 et plus :
// l'image, modulo 64, pour son tramage.
bool PlantsDisabled() { return (((uint)(taa.z + 0.5)) & 1u) != 0u; }
bool FoliageFadeEnabled() { return (((uint)(taa.z + 0.5)) & 2u) != 0u; }
bool VegetationAbsent() { return (((uint)(taa.z + 0.5)) & 4u) != 0u; }
bool FoliageTemporalEnabled() { return (((uint)(taa.z + 0.5)) & 4096u) != 0u; }
// A changing coverage pattern needs a temporal consumer. Keep it stationary
// when smoothing is disabled, including native diagnostic captures.
uint FoliageFadeFrame() { return FoliageTemporalEnabled() ? ((((uint)(taa.z + 0.5)) >> 3) & 63u) : 0u; }
bool DiverseVegetation() { return (((uint)(taa.z + 0.5)) & 512u) != 0u; }
bool GameVegetation() { return (((uint)(taa.z + 0.5)) & 1024u) != 0u; }
bool GeneratedVegetationBank() { return (((uint)(taa.z + 0.5)) & 2048u) != 0u; }

struct ObjectInstance
{
    float3 pos;       // its foot, on the exact ground, relative to the camera, face-local (m)
    float  size;      // its width (m), times its fade: 0 as it appears
    float3 axisX;     // its frame, face-local: x, then up; z = cross(x, up)
    float  burial;    // the share of its height under the ground (OBJECT_BURIAL)
    float3 axisY;
    float  elevation; // of its foot (m), for the light through the air
    float3 albedo;    // linear reflectance: the ground's rock at its place
    uint   seed;      // its shape and stretch
};

// A shape's vertex, its foot at y = 0, its width about 1: a rock, an icosphere of 642 vertices cut by random planes; a
// grass tuft, 40 blades of 7 vertices.
struct ShapeVertex
{
    float3 pos;
    float  height; // the shape's whole height, the same for all its vertices
    float3 normal;
    float  shade;  // its colour's factor: a blade's own
};
static const uint ROCK_VARIANTS = 8, ROCK_VERTICES = 642, TUFT_VARIANTS = 4, TUFT_VERTICES = 40 * 7;
// The instances: the stones', then the tufts' from CLASS_CAPACITY (D3DApp::ObjectClassCapacity), the plants' from twice it,
// the plants' coarse ones from three times it.
static const uint CLASS_CAPACITY = 262144;

// The plants (docs/recherche-vegetation.md, PlantPlacement.hlsli): conifer, broadleaf, shrub. Seen from above, the crown
// covers the disc of PLANT_CROWN times the height, the ratios of the Tallo database's trees (Jucker et al. 2022): temperate
// conifers 0.31, temperate broadleaves 0.36 to Mediterranean ones 0.53, drylands' shrubs 1.07.
// A plant's instance: size is its height; burial, the depth (m) its trunk reaches under its foot; axisY holds the sun's
// share at its foot, its crown's widening, or a shrub's climate family plus 1, the trees' cover around it; seed: its
// species in bits 3 and 4, the rest for its looks.
static const uint CONIFER = 0, BROADLEAF = 1, SHRUB = 2;
static const float PLANT_CROWN[3] = { 0.3, 0.45, 1.1 };

uint ShrubFamily(ObjectInstance o) { return min((uint)max(o.axisY.y - 1.0, 0.0),5u); }
float ShrubHeight(uint family) {
    const float heights[6] = {0.65,0.85,0.60,0.30,1.0,1.15};
    return heights[min(family,5u)];
}
uint ShrubVariant(uint seed) {
    uint h=seed ^ 0xb153a471u; h^=h>>16; h*=0x7feb352du; h^=h>>15; h*=0x846ca68bu; h^=h>>16;
    return h & 1u;
}

// Plant-only metadata occupies the otherwise unused rock albedo: model+1, height factor, crown factor.
// Seed and position remain the plant's identity through both representations.
uint FoliageModel(ObjectInstance o) {
    uint species=(o.seed>>3)&3u;
    if (DiverseVegetation() && o.albedo.x>=1.0) return min((uint)(o.albedo.x-1.0),FOLIAGE_MAX_MODELS-1u);
    return species==SHRUB ? 2u+2u*ShrubFamily(o)+ShrubVariant(o.seed) : species;
}
bool GroundPlant(ObjectInstance o) {
    const uint model=FoliageModel(o);
    return model>=23u && model<=30u;
}
float PlantHeightFactor(ObjectInstance o,uint species) {
    if (GameVegetation() && species<SHRUB) return 1.0; // tree metadata carries contact colour instead of an unused height
    return o.albedo.y>0.0 ? o.albedo.y : species==SHRUB ? ShrubHeight(ShrubFamily(o)) : 1.0;
}
float PlantRootRadius(float size,float spread,uint seed) {
    float own=1.0+0.15*(float((seed>>8)&255u)/127.5-1.0);
    return max(0.085*size*spread*own,0.14);
}
uint PackPlantGroundColour(float3 colour,float moss) {
    uint3 rgb=(uint3)round(saturate(colour)*127.0);
    return 0x3f000000u | rgb.x | (rgb.y<<7u) | (rgb.z<<14u) | ((uint)round(saturate(moss)*7.0)<<21u);
}
float3 PlantGroundColour(ObjectInstance o) {
    uint rgb=asuint(o.albedo.y);
    return float3(rgb&127u,(rgb>>7u)&127u,(rgb>>14u)&127u)/127.0;
}
float PlantMoss(ObjectInstance o) { return float((asuint(o.albedo.y)>>21u)&7u)/7.0; }

// From the object vertex shader to its pixels.
struct ObjectPixel
{
    float4 position  : SV_POSITION;
    float3 pos       : POSITION;  // relative to the camera, face-local (m)
    float3 normal    : NORMAL;    // face-local
    float3 local     : TEXCOORD0; // in its own frame (m), shifted per object: its texture's coordinates
    float3 localNormal : TEXCOORD1;
    float3 albedo    : TEXCOORD2;
    float3 up        : TEXCOORD3; // the vertical at its foot, face-local
    float  elevation : TEXCOORD4;
    float  rise      : TEXCOORD5; // height above the ground, in shares of its height: the shade at its foot
    float3 axisX     : TEXCOORD6; // its frame, face-local
    float3 axisY     : TEXCOORD7;
    nointerpolation float canopy : TEXCOORD8; // ordinary objects only; decoded canopy cover
    nointerpolation float moss : TEXCOORD9;
};

#endif
