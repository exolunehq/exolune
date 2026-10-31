// Planet.hlsli - shared by the terrain compute, vertex and pixel shaders.
// Must match D3DApp::FrameConstants and D3DApp::FaceVertex.
#ifndef PLANET_HLSLI
#define PLANET_HLSLI

cbuffer Frame : register(b0)
{
    float4x4 viewProj;   // face-local frame, camera at the origin
    float4   faceX;      // face-local axes, in planet coordinates
    float4   faceY;
    float4   faceZ;      // nadir direction: planet centre -> camera
    float4   faceParams; // x: face half-width (m), y: planet radius (m), z: camera height above the face's tangent point (m), w: cells per face side n
    float4   lightDir;   // xyz: sun direction, face-local; w: shading, 0 smooth, 1 faceted (key R), 2 wireframe
    double4  nadir;      // xyz: nadir direction in double precision, for the noise
    float4   ringParams; // x: ring count, y: half-width growth from one ring to the next; z: weight of the fine
                         // grid's normals (docs/spec-rendu-lointain.md), w: its cells per mesh cell
    float4   camRight;   // camera axes, face-local; camRight.w and camUp.w: tangents of the half fields of view
    float4   camUp;
    float4   camForward;
    float4   camPlane;   // xy: camera position on the face plane (m), 0 unless the mesh is frozen (key G); z: 1 when the
                         // mesh is the previous frame's, its computed vertices kept (TerrainCompute.hlsl)
    float4   detailOrigin; // xyz: camera minus the detail anchor, planet frame (m); w: anchor unit (m)
    int4     detailAnchor; // xyz: the detail anchor, the multiple of the anchor unit closest to the camera
    float4   camVertical;  // xyz: the camera's vertical, face-local; w: camera altitude above sea level (km)
    float4x4 reproject;    // face-local point (w 1) or direction (w 0) -> the previous frame's clip space
    float4   taa;          // x: temporal weight; y: diagnostic view; z: vegetation flags; w: pixel angle (rad)
    // Transported tangent plane for the FFT ocean; waveAxisX.w is its conservative culling margin.
    float4   waveAxisX;
    float4   waveAxisY;
    float4x4 reprojectShip; // the ship's pixels: face-local point -> previous frame's clip space, following the ship
    float4   shipSphere;    // xyz: the ship's centre, face-local from the camera (m); w: its radius, 0 without the ship
    float4x4 shipSunShadow; // face-local point -> the ship's map towards the sun, for its shadow on the ground
};

struct FaceVertex
{
    float3 pos;       // relative to the camera, face-local (m)
    float  elevation; // raw noise elevation (m), negative under the sea
    float3 dir;       // unit direction from the planet centre, face-local
    float  roughness; // the relief's roughness, 0 smooth plains to 1 young mountains (Relief.hlsli)
    float  volcanic;  // the fresh volcanic ground, 0 to 1: bare lava, scoria and ash (Volcanoes.hlsli, gVolcanic)
    float  horizon;   // the terrain's horizon toward the sun (rad), for its cast shadow (Horizon.hlsl)
    float  shadow;    // its column's shadow height (m above the sea), for the sun's shafts in the air (Horizon.hlsl)
};

struct PSInput
{
    float4 position  : SV_POSITION;
    float3 pos       : POSITION;
    float3 dir       : NORMAL;
    float  elevation : ELEVATION;
    float3 normal    : TEXCOORD1; // from the neighbouring vertices
    float  cellSize  : TEXCOORD2; // mesh cell size around the vertex (m)
    float3 chart     : TEXCOORD3; // spline normals: xy, coordinates in the mesh's chart; z, the chart, 0 the face, 1 the rings
    float  corner    : TEXCOORD4; // rings: cells to the ring's nearest corner
    float4 geology   : TEXCOORD5; // the rock's kind, iron and varnish, by region (Materials.hlsli, Geology); w the fresh
                                  // volcanic ground (FaceVertex)
    float  slopeSpread : TEXCOORD6; // how the slope spreads within the cell (Materials.hlsli, SlopeSpread)
    float3 decision  : TEXCOORD7; // the materials' normal, across DECISION_BASELINE at least (VertexShader.hlsl)
    float3 shore     : TEXCOORD8; // the beach's normal, across SHORE_BASELINE at least (VertexShader.hlsl)
    float2 seaParam : TEXCOORD12;
    float seaHeight : TEXCOORD13;
    float  horizon   : TEXCOORD11; // the terrain's horizon toward the sun (rad): the shadow it casts (Shadows.hlsli)
};

#endif
