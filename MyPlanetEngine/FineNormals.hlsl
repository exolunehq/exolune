// The fine grid's normals (docs/spec-rendu-lointain.md, step 2), by centred differences over its neighbours,
// as the vertex shader takes the mesh's. A neighbour off screen or off the grid is the point itself.
#include "Planet.hlsli"

StructuredBuffer<float4> fine : register(t0);       // FineTerrain.hlsl's output
RWStructuredBuffer<float4> outNormals : register(u0); // xyz: unit normal, face-local, 0 off screen; w: elevation (m)

bool Culled(float3 p) // NaN position, which the compiler cannot drop
{
    return (asuint(p.x) & 0x7fffffffu) > 0x7f800000u;
}

float3 FinePosition(int2 c, int n, float3 self)
{
    if (any(c < 0) || any(c > n))
        return self;
    const float3 p = fine[c.y * (n + 1) + c.x].xyz;
    return Culled(p) ? self : p;
}

[numthreads(64, 1, 1)]
void CSMain(uint3 threadId : SV_DispatchThreadID)
{
    const uint id = threadId.x;
    const int n = (int)(faceParams.w * ringParams.w);
    if (id >= (uint)((n + 1) * (n + 1)))
        return;
    const float3 self = fine[id].xyz;
    if (Culled(self))
    {
        outNormals[id] = 0.0;
        return;
    }
    const int2 c = int2(id % (n + 1), id / (n + 1));
    float3 normal = cross(FinePosition(c + int2(1, 0), n, self) - FinePosition(c - int2(1, 0), n, self),
                          FinePosition(c + int2(0, 1), n, self) - FinePosition(c - int2(0, 1), n, self));
    const float length2 = dot(normal, normal);
    normal = length2 > 0.0 ? normal * rsqrt(length2) : float3(0.0, 0.0, 1.0);
    if (normal.z < 0.0) // face-local z points up, away from the planet's centre
        normal = -normal;
    outNormals[id] = float4(normal, fine[id].w);
}
