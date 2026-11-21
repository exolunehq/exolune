// The ship's own shadow maps, depth only, in the ship's frame: one towards the sun, one from overhead for the sky's light.
#include "Planet.hlsli"
#include "Ship.hlsli"

struct ShadowVertex { float4 position : SV_POSITION; float4 uv : TEXCOORD0; };

ShadowVertex VSMain(uint id : SV_VertexID)
{
    const ShipVertex v = ShipSkinnedVertex(id);
    ShadowVertex result;
    result.position = mul(mul(float4(v.pos, 1.0), ShipPose(v.pose)), shipShadow[shipShadowMap]);
    result.uv = float4(v.uv0, v.uv1);
    return result;
}
