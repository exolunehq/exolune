#include "Planet.hlsli"
#include "Ship.hlsli"

void PSMain(float4 position : SV_POSITION, float4 uv : TEXCOORD0)
{
    const ShipMaterial m = shipMaterials[shipMaterial];
    clip(ShipImage(m.image[0], m.uv[0], uv, 1.0).a - m.color.a);
}
