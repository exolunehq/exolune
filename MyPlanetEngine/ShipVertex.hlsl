// The ship's vertices, pulled from the pack by index, into the face-local frame of the camera.
#include "Planet.hlsli"
#include "Ship.hlsli"

ShipPixel VSMain(uint id : SV_VertexID)
{
    const ShipVertex v = shipVertices[id];
    const float4x4 pose = ShipPose(v.pose), model = mul(pose, shipModel);
    ShipPixel o;
    o.local = mul(float4(v.pos, 1.0), pose).xyz;
    o.pos = mul(float4(v.pos, 1.0), model).xyz;
    o.normal = mul(float4(v.normal, 0.0), model).xyz;
    o.tangent = float4(mul(float4(v.tangent.xyz, 0.0), model).xyz, v.tangent.w);
    o.uv = float4(v.uv0, v.uv1);
    o.position = mul(float4(o.pos, 1.0), viewProj);
    return o;
}
