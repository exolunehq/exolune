// The common screen sampling/reconstruction rung with an impact-only physical stack.
#define AIRLESS_SURFACE
#include "Planet.hlsli"
#include "SurfaceStack.hlsli"
#include "Terrain.hlsli"
#include "TerrainRay.hlsli"
RWStructuredBuffer<ScreenSample> outScreen:register(u0);
[numthreads(8,8,1)]
void CSMain(uint3 id:SV_DispatchThreadID) {
    const uint w=uint(screenRelief.x),h=uint(screenRelief.y);
    if(id.x>=w || id.y>=h)return;
    const float2 uv=(float2(id.xy)+.5)/float2(w,h)*2-1;
    const float3 ray=normalize(camForward.xyz+uv.x*camRight.w*camRight.xyz-uv.y*camUp.w*camUp.xyz);
    ScreenSample sample=(ScreenSample)0;sample.terrain=asfloat(0x7fc00000u).xxxx;
    float2 xy;float footprint,elevation=0;float3 direction,position;
    for(uint pass=0;pass<2;++pass) {
        if(!PlaneHit(ray,faceParams.y,faceParams.z,elevation,taa.w*screenRelief.w,xy,footprint)) {
            outScreen[id.y*w+id.x]=sample;return;
        }
        gMaxFrequency=faceParams.y/(MESH_BAND_LIMIT*max(footprint,.25));
        elevation=TerrainAt(xy,faceParams.y,faceParams.z,direction,position);
    }
    sample.terrain=float4(position,elevation);sample.ground=float4(gRoughness,gAirlessAlbedo,0,0);
    outScreen[id.y*w+id.x]=sample;
}
