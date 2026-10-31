// The jets' boxes (ShipPlume.hlsli): one instance per jet, a box around its cone; a jet at rest is dropped.
#include "ShipPlume.hlsli"

static const uint CUBE[36] = { 0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1,
                               2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3 };

PlumePixel VSMain(uint id : SV_VertexID, uint j : SV_InstanceID)
{
    const Jet jet = JetOf(j);
    float3 u, v;
    JetFrame(jet, u, v);
    const uint corner = CUBE[id];
    const float half = jet.radius + jet.spread * jet.length + 0.05;
    PlumePixel o;
    o.local = jet.at + jet.to * (((corner >> 2) & 1) * (jet.length + 0.05) - 0.05)
            + u * ((corner & 1) ? half : -half) + v * (((corner >> 1) & 1) ? half : -half);
    o.position = jet.power > 0.01 ? mul(float4(mul(float4(o.local, 1.0), shipModel).xyz, 1.0), viewProj) : 0.0;
    o.jet = j;
    return o;
}
