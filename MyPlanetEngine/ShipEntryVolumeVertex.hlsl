#include "Planet.hlsli"
#include "ShipEntryVolume.hlsli"

// The clipped back faces cover the projected hull once, including from the cockpit.
static const uint corners[36] = {0,1,3, 0,3,2, 4,6,7, 4,7,5, 0,4,5, 0,5,1,
                                 2,3,7, 2,7,6, 0,2,6, 0,6,4, 1,5,7, 1,7,3};
EntryVolumePixel VSMain(uint id : SV_VertexID)
{
    const uint c = corners[id];
    const float3 sign = float3(c & 1, (c >> 1) & 1, c >> 2) * 2.0 - 1.0;
    EntryVolumePixel o;
    o.local = EntryShockCentre() + sign * EntryShockBounds();
    o.position = mul(float4(mul(float4(o.local, 1.0), shipModel).xyz, 1.0), viewProj);
    return o;
}
