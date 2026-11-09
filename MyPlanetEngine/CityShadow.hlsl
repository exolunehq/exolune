#include "City.hlsli"
float4 VSMain(uint id:SV_VertexID,uint instanceId:SV_InstanceID):SV_POSITION {
    return mul(float4(CityPoint(cityVertices[id],cityInstances[instanceId]),1),cityShadow);
}
