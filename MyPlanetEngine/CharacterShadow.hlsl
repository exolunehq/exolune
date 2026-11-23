// CharacterShadow.hlsl - shadow depth pass reading already-skinned character vertices.
#include "Characters.hlsli"

StructuredBuffer<CharSkinnedVertex> skinnedVertices : register(t30);

float4 VSMain(uint id : SV_VertexID) : SV_POSITION
{
    const CharSkinnedVertex v = skinnedVertices[charBaseVertex + id];
    return mul(float4(v.pos, 1.0), charShadow);
}
