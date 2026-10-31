#include "PlanetFoliageCommon.hlsli"
struct Vertex { float3 pos; float3 normal; float2 uv; float material; };
StructuredBuffer<Vertex> mesh : register(t30);
StructuredBuffer<float4> vertexVisibility : register(t39);
struct VOut { float4 position:SV_POSITION; float3 pos:POSITION; float3 normal:NORMAL; float2 uv:TEXCOORD0; nointerpolation float material:TEXCOORD1; nointerpolation uint instance:TEXCOORD2; float localHeight:TEXCOORD3; float4 visibility0:TEXCOORD4; float4 visibility1:TEXCOORD5; };
VOut VSMain(uint vertex:SV_VertexID, uint id:SV_InstanceID) {
    ObjectInstance o=plants[id]; Vertex v=mesh[vertex]; VOut r;
    // Extend only the bottom of the trunk to the placement's burial depth; the crown stays unchanged.
    const bool trunk = species == 1 ? abs(v.material - 1.0) < 0.5 : v.material < 0.5;
    const float burial = trunk ? o.burial * (1.0 - smoothstep(0.0, 0.03, v.pos.y)) : 0.0;
    r.pos=ToWorld(v.pos,o)-PlantUp(o)*burial; r.position=mul(float4(r.pos,1),viewProj); r.normal=DirectionWorld(v.normal,o);
    r.uv=v.uv; r.material=v.material; r.instance=id; r.localHeight=v.pos.y;
    r.visibility0=1; r.visibility1=float4(1,1,1,0);
    if ((flags&8u)!=0 && volumeParams.x>0) { r.visibility0=vertexVisibility[vertex*2]; r.visibility1=vertexVisibility[vertex*2+1]; }
    return r;
}
