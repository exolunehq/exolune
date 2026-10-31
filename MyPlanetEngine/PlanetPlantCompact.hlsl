#include "Planet.hlsli"
#include "Objects.hlsli"
#ifdef PLANET_PLANT_SCATTER
RWStructuredBuffer<uint2> masks : register(u0);
RWStructuredBuffer<ObjectInstance> scratch : register(u1);
RWStructuredBuffer<ObjectInstance> instances : register(u2);
RWStructuredBuffer<uint2> offsets : register(u3);
RWStructuredBuffer<uint2> totals : register(u4);
RWByteAddressBuffer counters : register(u5);
#else
RWStructuredBuffer<uint4> records : register(u0);
RWStructuredBuffer<uint2> values : register(u1);
RWStructuredBuffer<uint2> offsets : register(u2);
RWStructuredBuffer<uint2> totals : register(u3);
RWStructuredBuffer<uint4> tiles : register(u4);
RWByteAddressBuffer tileDispatch : register(u5);
RWByteAddressBuffer counters : register(u6);
RWStructuredBuffer<uint2> masks : register(u7);
#endif
cbuffer CompactSettings : register(b1) { uint length; uint capacity; };

#ifndef PLANET_PLANT_SCATTER
[numthreads(256,1,1)]
void CompactTiles(uint id : SV_DispatchThreadID) {
    if (id==0) {
        uint count=min(totals[0].x,capacity);
        tileDispatch.Store(0,(count+63)/64); tileDispatch.Store(4,1); tileDispatch.Store(8,1); tileDispatch.Store(12,count);
        counters.Store(37*4,totals[0].x-count);
    }
    if (id<length && values[id].x!=0 && offsets[id].x<capacity) tiles[offsets[id].x]=records[id];
}
[numthreads(256,1,1)]
void ClearPlants(uint id : SV_DispatchThreadID) {
    if (id<length) { values[id]=uint2(0,0); masks[id]=uint2(0,0); }
}
#else
[numthreads(256,1,1)]
void ScatterPlants(uint id : SV_DispatchThreadID) {
    if (id==0) {
        const uint2 total=totals[0];
        counters.Store(21*4,total.x); counters.Store(29*4,total.y);
        counters.Store(23*4,min(total.x,capacity)); counters.Store(31*4,min(total.y,capacity));
        counters.Store(38*4,total.x-min(total.x,capacity)); counters.Store(39*4,total.y-min(total.y,capacity));
    }
    if (id>=length) return;
    uint2 mask=masks[id], base=offsets[id];
    [unroll] for (uint i=0;i<16;++i) {
        uint bit=1u<<i, before=bit-1u;
        if ((mask.x&bit)!=0) {
            uint slot=base.x+countbits(mask.x&before);
            if (slot<capacity) instances[2*capacity+slot]=scratch[id*16+i];
        }
        if ((mask.y&bit)!=0) {
            uint slot=base.y+countbits(mask.y&before);
            if (slot<capacity) instances[3*capacity+slot]=scratch[id*16+i];
        }
    }
}
#endif
