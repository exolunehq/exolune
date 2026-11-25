// CharacterSkin.hlsl - compute skinning pass executed once per frame before shadows and opaque shading.
// Computes current-frame face-local geometry and exact previous-frame clip position for TAA velocity.
#include "Characters.hlsli"

StructuredBuffer<CharRestVertex>   restVertices : register(t0);
StructuredBuffer<CharBone>         bonesCurr    : register(t1);
StructuredBuffer<CharBone>         bonesPrev    : register(t2);
StructuredBuffer<CharInstance>     instances    : register(t3);
RWStructuredBuffer<CharSkinnedVertex> skinnedOut : register(u0);

cbuffer SkinDispatch : register(b0)
{
    uint actorIndex;
    uint vertexCount;
    uint pad0;
    uint pad1;
};

[numthreads(64, 1, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    const uint localIdx = id.x;
    if (localIdx >= vertexCount)
        return;

    const CharInstance inst = instances[actorIndex];
    const CharRestVertex v = restVertices[inst.meta.x + localIdx];

    const uint j0 = v.joints.x & 0xffffu;
    const uint j1 = v.joints.x >> 16;
    const uint j2 = v.joints.y & 0xffffu;
    const uint j3 = v.joints.y >> 16;
    const uint bBase = inst.meta.w;
    const float4 w = v.weights;

    const CharBone bc0 = bonesCurr[bBase + j0];
    const CharBone bc1 = bonesCurr[bBase + j1];
    const CharBone bc2 = bonesCurr[bBase + j2];
    const CharBone bc3 = bonesCurr[bBase + j3];

    // Volume-preserving Dual Quaternion Skinning (Kavan et al. 2008) prevents shoulder/wrist/elbow candy-wrapper collapse.
    const CharDualQuat dqCurr = CharBlendDualQuats(bc0, bc1, bc2, bc3, w);
    const float3 pCurr = CharDQTransformPos(dqCurr, v.pos);
    const float3 nCurr = normalize(CharDQTransformDir(dqCurr, v.normal) + 1e-6);
    const float3 tCurr = normalize(CharDQTransformDir(dqCurr, v.tangent.xyz) + 1e-6);

    const CharBone bp0 = bonesPrev[bBase + j0];
    const CharBone bp1 = bonesPrev[bBase + j1];
    const CharBone bp2 = bonesPrev[bBase + j2];
    const CharBone bp3 = bonesPrev[bBase + j3];

    const CharDualQuat dqPrev = CharBlendDualQuats(bp0, bp1, bp2, bp3, w);
    const float3 pPrev = CharDQTransformPos(dqPrev, v.pos);

    const float3 worldPos = mul(float4(pCurr, 1.0), inst.currModel).xyz;
    const float3 worldN   = normalize(mul(float4(nCurr, 0.0), inst.currModel).xyz + 1e-6);
    const float3 worldT   = normalize(mul(float4(tCurr, 0.0), inst.currModel).xyz + 1e-6);

    CharSkinnedVertex o;
    o.pos      = worldPos;
    o.localY   = pCurr.y;
    o.normal   = worldN;
    o.material = v.material;
    o.tangent  = float4(worldT, v.tangent.w);
    o.prevClip = mul(float4(pPrev, 1.0), inst.prevClipModel);
    o.uv       = v.uv;
    o.actorIdx = actorIndex;
    o.pad1     = 0u;
    skinnedOut[inst.meta.z + localIdx] = o;
}
