#include "Planet.hlsli"
#include "Objects.hlsli"
#include "PlanetFoliageLod.hlsli"
StructuredBuffer<ObjectInstance> finePlants:register(t0);
StructuredBuffer<ObjectInstance> coarsePlants:register(t1);
ByteAddressBuffer sourceCounts:register(t2);
StructuredBuffer<uint> modelLevels:register(t3);
RWStructuredBuffer<ObjectInstance> outputPlants:register(u0);
RWByteAddressBuffer arguments:register(u1);
RWStructuredBuffer<uint> meshOrder:register(u2);
cbuffer ClassifySettings:register(b1) { uint queueBaseLow,queueBaseHigh,orderBaseLow,orderBaseHigh; };
static const uint SOURCE_CAPACITY=262144,QUEUE_CAPACITY=524288,ORDER_CAPACITY=2*QUEUE_CAPACITY,STRIDE=28;
void Place(ObjectInstance plant,uint species,uint model,uint level,uint sourceId) {
    uint command=model*FOLIAGE_REPRESENTATIONS+level;
#ifdef FOLIAGE_SCATTER
    uint slot;arguments.InterlockedAdd(FOLIAGE_MODEL_CURSORS+command*4,1,slot);
    uint count=arguments.Load(command*STRIDE+12),first=arguments.Load(command*STRIDE+24);
    if (slot<count) {
        if (level==FOLIAGE_MESH_LODS) outputPlants[(species*2+1)*QUEUE_CAPACITY+first+slot]=plant;
        else meshOrder[species*ORDER_CAPACITY+first+slot]=sourceId;
    }
#else
    uint ignored;arguments.InterlockedAdd(FOLIAGE_MODEL_COUNTS+command*4,1,ignored);
#endif
}
[numthreads(64,1,1)]
void CSMain(uint id:SV_DispatchThreadID) {
    if (PlantsDisabled()) return;
    bool coarse=id>=SOURCE_CAPACITY;uint index=coarse?id-SOURCE_CAPACITY:id;
    if (index>=min(sourceCounts.Load((coarse?31:23)*4),SOURCE_CAPACITY)) return;
    ObjectInstance plant;
    if (coarse) plant=coarsePlants[index];else plant=finePlants[index];
    uint species=(plant.seed>>3)&3u;
    if (species>2 || plant.size<=0) return;
    uint model=FoliageModel(plant);
    float share=FoliageFadeEnabled()?PlanetFoliageMeshShare(plant,species):(PlanetFoliageMeshChoice(plant,species)?1:0);
    // The unused fractional model metadata carries shared mesh/proxy coverage.
    // Model identity still uses its integer part; source instances stay untouched.
    uint meshCoverage=(uint)round(share*255.0);
    uint windCoverage=(uint)round(smoothstep(160.0,320.0,PlanetFoliagePixels(plant,species))*255.0);
    plant.albedo.x=floor(plant.albedo.x)+float(meshCoverage|(windCoverage<<8u))/131072.0;
    if (share>0) {
#ifdef FOLIAGE_SCATTER
        // One object per source even when two neighbouring mesh levels draw it.
        outputPlants[(species*2)*QUEUE_CAPACITY+id]=plant;
#else
        uint ignored;arguments.InterlockedAdd(FOLIAGE_UNIQUE_COUNTS+model*4,1,ignored);
#endif
        uint a,b;float blend;PlanetFoliageMeshLevels(plant,species,max(modelLevels[model],1u),a,b,blend);
        uint coverage=(uint)round(blend*511.0);
        if (a==b || blend<1) Place(plant,species,model,a,id|(coverage<<19u));
        if (a!=b && blend>0) Place(plant,species,model,b,id|(coverage<<19u)|(1u<<28u));
    }
    if (share<1) Place(plant,species,model,FOLIAGE_MESH_LODS,id);
}
