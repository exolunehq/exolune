// CharacterVertex.hlsl - opaque forward vertex pass reading compute-skinned character vertices.
#include "Planet.hlsli"
#include "Characters.hlsli"

StructuredBuffer<CharSkinnedVertex> skinnedVertices : register(t30);
StructuredBuffer<CharInstance>      charInstances   : register(t31);

CharPixel VSMain(uint id : SV_VertexID)
{
    const CharSkinnedVertex v = skinnedVertices[charBaseVertex + id];
    const CharInstance inst = charInstances[charActorIndex];
    CharPixel o;
    o.pos        = v.pos;
    o.normal     = v.normal;
    o.tangent    = v.tangent;
    o.prevClip   = v.prevClip;
    o.uv         = v.uv;
    o.material   = v.material;
    o.tint       = inst.tint;
    o.localY     = v.localY;
    o.restPos    = v.restPos;
    o.restNormal = v.restNormal;
    o.skinX      = v.skinX;
    o.skinY      = v.skinY;
    o.skinZ      = float3(v.skinZx, v.skinZy, v.skinZz);
    o.position   = mul(float4(v.pos, 1.0), viewProj);
    return o;
}
