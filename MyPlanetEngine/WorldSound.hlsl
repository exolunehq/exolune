// Listener habitat and weather. Reads the renderer's material textures, coatings and vegetation fields.
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "Relief.hlsli"
#include "Terrain.hlsli"
#include "Mesh.hlsli"
#include "SurfaceProbe.hlsli"
#include "Materials.hlsli"
#include "Objects.hlsli"
#include "Vegetation.hlsli"
#include "Shadows.hlsli"
#include "Clouds.hlsli"
#include "WorldWeather.hlsli"
#include "SurfaceWeights.hlsli"
RWStructuredBuffer<float4> habitat : register(u0);
groupshared float e[9];
groupshared float waterDepth;

[numthreads(64,1,1)]
void CSMain(uint lane : SV_GroupIndex) {
    LoadGradients(lane,64);
    if (lane < 9) {
        const float2 offsets[9] = { float2(0,0),float2(1,0),float2(-1,0),float2(0,1),float2(0,-1),
            float2(60,0),float2(-60,0),float2(0,60),float2(0,-60) };
        const double3 p = nadir.xyz * (double)faceParams.y + (double3)faceX.xyz * offsets[lane].x + (double3)faceY.xyz * offsets[lane].y;
        const double3 d = SurfaceProbeDirection(p);
        gExactLattice = true; gMaxFrequency = NO_LIMIT;
        gCreaseMaxFrequency = PLANET_RADIUS_KM * 1000.0 / (MESH_BAND_LIMIT * CREASE_MIN_CELL);
        e[lane] = ReliefElevation(d);
        if (lane == 0) waterDepth = gWaterLevel - e[lane];
    }
    GroupMemoryBarrierWithGroupSync();
    if (lane != 0) return;
    if (e[0] <= 0.15 || waterDepth > 0.02) {
        const float4 climate = ClimateAt(materialSampler,(float3)nadir.xyz,0.5);
        habitat[0] = 0.0;
        habitat[1] = float4(0.0,ClimateHumidity(climate.x),climate.y,e[0]);
        habitat[2] = float4(WorldWeather(cloudCameraKm.xyz),0.0);
        habitat[3] = habitat[4] = 0.0;
        return; // submerged terrain is never a source of land vegetation or fauna
    }
    const float3 up = float3(0,0,1), normal = normalize(float3((e[2]-e[1])*0.5,(e[4]-e[3])*0.5,1));
    const float3 shore = normalize(float3((e[6]-e[5])/120,(e[8]-e[7])/120,1));
    const double3 foot = nadir.xyz * ((double)faceParams.y + (double)e[0]);
    const float3 q = (float3)(foot - (double3)detailAnchor.xyz * (double)detailOrigin.w);
    const float3 north = float3(faceX.y,faceY.y,faceZ.y);
    const float sinLat = north.z;
    const float3 pole = (sinLat < 0 ? -1.0 : 1.0) * normalize(north - up * sinLat + float3(1e-8,0,0));
    // A boot-sized footprint reads the same texture heights which expose rock through sand and thin snow.
    const float sole=0.12, pixel=log2(sole);
    gMaterialTextures = 1.0; gHeightBlend = 1.0; gCellSize = sole; gBedLens = BedLenses(q,sole);
    gStrataCell=sole; gStrataRaise=0.0;
    const Materials m = GroundMaterials(q,e[0],up,normal,shore,sinLat,pole,pixel,faceX.xyz*sole,faceY.xyz*sole,0,0,StrataShift(q,sole));
    Vegetation v = VegetationAt(m.temperature,m.humidity,m.coldSigma,m.amplitude,Exposure((float3)nadir.xyz,e[0]));
    WoodsAt(q,-1.0,v); v.able = PlantGround(m);
    const float cover = PlantCover(TreesHere(v),ShrubsHere(v));
    const SurfaceWeights w=GroundContactWeights(m.soilAmount,m.grassAmount,m.sandAmount,m.screeWeight,m.rock,m.beach,m.snow);
    habitat[0] = float4(w.grass,w.sand,w.rock+w.gravel,w.snow);
    habitat[1] = float4(cover,m.humidity,m.temperature,e[0]);
    habitat[2] = float4(WorldWeather(cloudCameraKm.xyz),m.beach);
    habitat[3] = float4(w.soil,w.grass,w.gravel,w.rock);
    habitat[4] = float4(w.sand,w.snow,habitat[2].x,0.0);
}
