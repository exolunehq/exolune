#include "Planet.hlsli"
#include "Objects.hlsli"
#include "PlanetFoliageLod.hlsli"
#include "PlanetFoliageVisibility.hlsli"
#include "PlanetFoliageDepth.hlsli"


StructuredBuffer<ObjectInstance> queues : register(t0);
ByteAddressBuffer arguments : register(t1);
Texture2D<float> hiZ : register(t2);
StructuredBuffer<CullModel> models : register(t3);
RWByteAddressBuffer visibility : register(u0);
RWByteAddressBuffer stats : register(u1);
cbuffer Dimensions : register(b1) { uint hiZWidth, hiZHeight, hiZMips, viewportWidth, viewportHeight; };
static const uint CAPACITY=524288, AGGREGATE=1008;

[numthreads(64,1,1)]
void Clear(uint id : SV_DispatchThreadID) {
    if (id<32768) visibility.Store(id*4,0);
    if (id==0) { stats.Store(0,0); stats.Store(4,0); stats.Store(8,0); }
}

bool Hidden(ObjectInstance plant, CullModel m) {
    if (!hiZWidth || !hiZHeight || !hiZMips || !viewportWidth || !viewportHeight) return false;
    float depth; float2 lo, hi;
    if (!ImpostorDepthBound(plant,m,depth,lo,hi)) return false;
    float2 padding=float2(taa.w/camRight.w,taa.w/camUp.w);
    lo-=padding; hi+=padding;
    float2 pixelLo=float2((lo.x*0.5+0.5)*viewportWidth,(0.5-hi.y*0.5)*viewportHeight)-2.0;
    float2 pixelHi=float2((hi.x*0.5+0.5)*viewportWidth,(0.5-lo.y*0.5)*viewportHeight)+2.0;
    if (!Finite2(pixelLo) || !Finite2(pixelHi) || any(pixelLo<0) ||
        pixelHi.x>=(float)viewportWidth || pixelHi.y>=(float)viewportHeight || any(pixelHi<pixelLo)) return false;
    float span=max(pixelHi.x-pixelLo.x+1,pixelHi.y-pixelLo.y+1);
    uint mip=(uint)max(0.0,ceil(log2(max(span,1.0))));
    if (mip>=hiZMips) return false;
    uint2 p0=uint2(floor(pixelLo/(1u<<mip))), p1=uint2(floor(pixelHi/(1u<<mip)));
    uint2 dimensions=max(uint2(hiZWidth,hiZHeight)>>mip,1u);
    if (any(p1>=dimensions) || any(p1-p0>1)) return false;
    float d0=hiZ.Load(int3(p0,mip)), d1=hiZ.Load(int3(uint2(p1.x,p0.y),mip));
    float d2=hiZ.Load(int3(uint2(p0.x,p1.y),mip)), d3=hiZ.Load(int3(p1,mip));
    return AllFinite4(float4(d0,d1,d2,d3)) && min(min(d0,d1),min(d2,d3))>depth;
}

groupshared uint groupTested, groupRejected;
[numthreads(64,1,1)]
void Cull(uint3 id : SV_DispatchThreadID, uint lane : SV_GroupIndex, uint3 group : SV_GroupID) {
    uint species=group.y;
    uint count=min(arguments.Load(AGGREGATE+(species*2+1)*4),CAPACITY);
    if (group.x*64>=count) return; // decision uniforme du groupe
    if (lane==0) { groupTested=0; groupRejected=0; }
    GroupMemoryBarrierWithGroupSync();
    if (id.x<count) {
        ObjectInstance plant=queues[(species*2+1)*CAPACITY+id.x];
        uint model=species;
        if (species==2) model=2+2*ShrubFamily(plant)+ShrubVariant(plant.seed);
        bool hidden=Hidden(plant,models[model]);
        uint ignored; InterlockedAdd(groupTested,1,ignored);
        if (hidden) InterlockedAdd(groupRejected,1,ignored);
        else { uint bit=PlanetFoliageVisibilityHash(plant.seed); visibility.InterlockedOr((bit>>5)*4,1u<<(bit&31),ignored); }
    }
    GroupMemoryBarrierWithGroupSync();
    if (lane==0 && groupTested) { uint ignored; stats.InterlockedAdd(0,groupTested,ignored); stats.InterlockedAdd(4,groupRejected,ignored); }
}

// Le masque est désormais complet ; ce compte tient compte des collisions.
[numthreads(64,1,1)]
void CountMasked(uint3 id : SV_DispatchThreadID, uint lane : SV_GroupIndex, uint3 group : SV_GroupID) {
    uint species=group.y;
    uint count=min(arguments.Load(AGGREGATE+(species*2+1)*4),CAPACITY);
    if (group.x*64>=count) return; // decision uniforme du groupe
    if (lane==0) groupRejected=0;
    GroupMemoryBarrierWithGroupSync();
    if (id.x<count) {
        ObjectInstance plant=queues[(species*2+1)*CAPACITY+id.x];
        uint bit=PlanetFoliageVisibilityHash(plant.seed);
        if ((visibility.Load((bit>>5)*4)&(1u<<(bit&31)))==0) { uint ignored; InterlockedAdd(groupRejected,1,ignored); }
    }
    GroupMemoryBarrierWithGroupSync();
    if (lane==0 && groupRejected) { uint ignored; stats.InterlockedAdd(8,groupRejected,ignored); }
}
