#include "Planet.hlsli"
#include "City.hlsli"
CityPixel VSMain(uint id:SV_VertexID,uint instanceId:SV_InstanceID){
    CityVertex v=cityVertices[id];CityInstance inst=cityInstances[instanceId];CityPixel o;
    o.local=CityPoint(v,inst);o.pos=mul(float4(o.local,1),cityModel).xyz;
    o.normal=mul(float4(CityRotate(v.normal,inst.originYaw.w),0),cityModel).xyz;
    o.uv=v.uv;o.material=(uint)v.material;o.detail=inst.detail.xyz;o.ambient=v.ambient;
    o.position=mul(float4(o.pos,1),viewProj);return o;
}
