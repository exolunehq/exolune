#include "FoliageCatalog.hlsli"
RWByteAddressBuffer arguments:register(u1);
cbuffer ClassifySettings:register(b1) { uint queueBaseLow,queueBaseHigh,orderBaseLow,orderBaseHigh; };
static const uint STRIDE=28,CAPACITY=524288,ORDER_CAPACITY=2*CAPACITY;
[numthreads(1,1,1)]
void CSMain(uint id:SV_DispatchThreadID) {
    for (uint species=0;species<3;++species) {
        uint meshTotal=0,proxyTotal=0,uniqueTotal=0;
        for (uint model=0;model<FOLIAGE_MAX_MODELS;++model) {
            if (FoliageModelSpecies(model)!=species) continue;
            uniqueTotal+=arguments.Load(FOLIAGE_UNIQUE_COUNTS+model*4);
            for (uint level=0;level<FOLIAGE_REPRESENTATIONS;++level) {
                bool proxy=level==FOLIAGE_MESH_LODS;
                uint command=model*FOLIAGE_REPRESENTATIONS+level;
                uint n=arguments.Load(FOLIAGE_MODEL_COUNTS+command*4),limit=proxy?CAPACITY:ORDER_CAPACITY;
                uint start=min(proxy?proxyTotal:meshTotal,limit),accepted=min(n,limit-start);
                uint offset=proxy?((species*2+1)*CAPACITY+min(start,CAPACITY-1))*64:(species*ORDER_CAPACITY+min(start,ORDER_CAPACITY-1))*4;
                uint base=proxy?queueBaseLow:orderBaseLow,address=base+offset;
                arguments.Store(command*STRIDE,address);
                arguments.Store(command*STRIDE+4,(proxy?queueBaseHigh:orderBaseHigh)+(address<base?1u:0u));
                arguments.Store(command*STRIDE+12,accepted);arguments.Store(command*STRIDE+24,start);
                if (proxy) proxyTotal+=n;else meshTotal+=n;
            }
        }
        arguments.Store(FOLIAGE_AGGREGATE_COUNTS+(species*2)*4,min(uniqueTotal,CAPACITY));
        arguments.Store(FOLIAGE_AGGREGATE_COUNTS+(species*2+1)*4,min(proxyTotal,CAPACITY));
        arguments.Store(FOLIAGE_OVERFLOW+(species*2)*4,meshTotal>ORDER_CAPACITY?meshTotal-ORDER_CAPACITY:0);
        arguments.Store(FOLIAGE_OVERFLOW+(species*2+1)*4,proxyTotal>CAPACITY?proxyTotal-CAPACITY:0);
    }
}
