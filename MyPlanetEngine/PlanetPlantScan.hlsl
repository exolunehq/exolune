RWStructuredBuffer<uint2> inputValues : register(u0);
RWStructuredBuffer<uint2> offsets : register(u1);
RWStructuredBuffer<uint2> blockSums : register(u2);
cbuffer ScanSettings : register(b0) { uint length; };
groupshared uint2 sharedValues[256];

[numthreads(256,1,1)]
void ScanMain(uint3 group : SV_GroupID, uint lane : SV_GroupIndex) {
    uint index=group.x*256+lane;
    uint2 value=index<length ? inputValues[index] : uint2(0,0);
    sharedValues[lane]=value; GroupMemoryBarrierWithGroupSync();
    [unroll] for (uint step=1;step<256;step*=2) {
        uint2 add=uint2(0,0);
        if (lane>=step) add=sharedValues[lane-step];
        GroupMemoryBarrierWithGroupSync(); sharedValues[lane]+=add; GroupMemoryBarrierWithGroupSync();
    }
    if (index<length) offsets[index]=sharedValues[lane]-value;
    if (lane==255) blockSums[group.x]=sharedValues[255];
}
[numthreads(256,1,1)]
void AddMain(uint id : SV_DispatchThreadID) {
    if (id<length) offsets[id]+=inputValues[id/256];
}
