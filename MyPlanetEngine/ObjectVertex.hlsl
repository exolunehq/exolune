// The objects near the camera (docs/spec-objets-proximite.md): one shape per instance, a rock's or, compiled from
// TuftVertex.hlsl, a tuft's, set on its foot, stretched a little, its share of height buried along its own up.
#include "Planet.hlsli"
#include "Objects.hlsli"

#ifndef SHAPE_VARIANTS
#define SHAPE_VARIANTS ROCK_VARIANTS
#define SHAPE_VERTICES ROCK_VERTICES
#endif

StructuredBuffer<ObjectInstance> instances : register(t0); // ObjectPlacement.hlsl's output, the class's
StructuredBuffer<ShapeVertex> shapes : register(t8);       // the class's shapes, D3DApp.cpp

ObjectPixel VSMain(uint vertexId : SV_VertexID, uint instanceId : SV_InstanceID)
{
    const ObjectInstance o = instances[instanceId];
    const ShapeVertex v = shapes[(o.seed % SHAPE_VARIANTS) * SHAPE_VERTICES + vertexId];
    const float3 stretch = 1.0 + float3(0.25, 0.2, 0.25) * (float3((o.seed >> uint3(8, 16, 24)) & 0xFFu) / 127.5 - 1.0);
    const float3 axisZ = cross(o.axisX, o.axisY);
    float3 local = v.pos * stretch;
    local.y -= o.burial * v.height * stretch.y;
    const float3 offset = o.size * local;
    const float3 normal = v.normal / stretch;

    ObjectPixel output;
    output.pos = o.pos + offset.x * o.axisX + offset.y * o.axisY + offset.z * axisZ;
    output.position = mul(float4(output.pos, 1.0), viewProj);
    output.normal = normalize(normal.x * o.axisX + normal.y * o.axisY + normal.z * axisZ);
    output.local = offset + 37.0 * float3((o.seed >> uint3(3, 11, 19)) & 0xFFu) / 255.0;
    output.localNormal = normal;
    output.albedo = o.albedo * v.shade;
    output.up = normalize(o.pos + float3(camPlane.xy, faceParams.y + faceParams.z));
    output.elevation = o.elevation;
    output.rise = local.y / (v.height * stretch.y);
    output.axisX = o.axisX;
    output.axisY = o.axisY;
    return output;
}
