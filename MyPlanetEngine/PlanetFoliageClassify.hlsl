#include "Planet.hlsli"
#include "Objects.hlsli"
#include "PlanetFoliageLod.hlsli"
StructuredBuffer<ObjectInstance> finePlants : register(t0);
StructuredBuffer<ObjectInstance> coarsePlants : register(t1);
ByteAddressBuffer sourceCounts : register(t2);
RWStructuredBuffer<ObjectInstance> outputPlants : register(u0);
RWByteAddressBuffer arguments : register(u1);
cbuffer ClassifySettings : register(b1) { uint queueBaseLow, queueBaseHigh; };
static const uint SOURCE_CAPACITY=262144, QUEUE_CAPACITY=2*SOURCE_CAPACITY, STRIDE=28;
static const uint MODEL_COUNTS=784, MODEL_CURSORS=896;

void Place(ObjectInstance plant, uint species, uint model, uint rep) {
    uint command=model*2+rep;
#ifdef FOLIAGE_SCATTER
    uint slot; arguments.InterlockedAdd(MODEL_CURSORS+command*4,1,slot);
    uint count=arguments.Load(command*STRIDE+12);
    if (slot<count) {
        uint first=arguments.Load(command*STRIDE+24);
        outputPlants[(species*2+rep)*QUEUE_CAPACITY+first+slot]=plant;
    }
#else
    uint ignored; arguments.InterlockedAdd(MODEL_COUNTS+command*4,1,ignored);
#endif
}

[numthreads(64,1,1)]
void CSMain(uint id : SV_DispatchThreadID) {
    if (PlantsDisabled()) return;
    const bool coarse=id>=SOURCE_CAPACITY;
    uint index=coarse ? id-SOURCE_CAPACITY : id;
    uint count=min(sourceCounts.Load((coarse ? 31 : 23)*4),SOURCE_CAPACITY);
    if (index>=count) return;
    ObjectInstance plant;
    if (coarse) plant=coarsePlants[index]; else plant=finePlants[index];
    uint species=(plant.seed>>3)&3u;
    if (species>2 || plant.size<=0.0) return;
    uint model=species;
    if (species==2) model=2+2*ShrubFamily(plant)+ShrubVariant(plant.seed);
    // Le maillage de près, l'imposteur au loin (PlanetFoliageLod.hlsli). Dans la bande du fondu, la plante est dans les
    // deux files ; Transition trame les pixels.
    if (FoliageFadeEnabled()) {
        const float share=PlanetFoliageMeshShare(plant,species);
        if (share>0.0) Place(plant,species,model,0);
        if (share<1.0) Place(plant,species,model,1);
    } else Place(plant,species,model,PlanetFoliageMeshChoice(plant,species) ? 0 : 1);
}
