// The ship's own shadow maps, depth only, in the ship's frame: one towards the sun, one from overhead for the sky's light.
#include "Planet.hlsli"
#include "Ship.hlsli"

float4 VSMain(uint id : SV_VertexID) : SV_POSITION
{
    const ShipVertex v = shipVertices[id];
    return mul(mul(float4(v.pos, 1.0), ShipPose(v.pose)), shipShadow[shipShadowMap]);
}
