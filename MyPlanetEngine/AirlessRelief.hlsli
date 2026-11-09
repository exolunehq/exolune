#ifndef AIRLESS_RELIEF_HLSLI
#define AIRLESS_RELIEF_HLSLI
#include "PlanetSettings.hlsli"
#include "AirlessField.hlsli"
static float gMaxFrequency=NO_LIMIT,gCreaseMaxFrequency=NO_LIMIT;
static bool gExactLattice=true;
static float gRoughness=.35,gVolcanic=0,gAirlessAlbedo=.145,gWaterLevel=-1e9,gWaterDistance=1e9;
static float3 gWaterFlow=0;
static float gWaterDepth=0,gWaterCoverage=0,gRiverBank=0,gRiverCellKm=0,gErosionNearReach=0;
static const uint EROSION_NEAR_UNKNOWN=0xffffffffu;
static uint gErosionNear=EROSION_NEAR_UNKNOWN;
void LoadGradients(uint lane,uint count) {}
bool ErosionRiverMapReady(){return false;}
float ErosionRiverMapCell(){return 1e30;}
float ReliefElevation(double3 p) {
    const AirlessGround sample=AirlessSample(p,faceParams.y,uint(nadir.w),max(.25,faceParams.y/(MESH_BAND_LIMIT*gMaxFrequency)));
    gAirlessAlbedo=sample.albedo;return sample.height;
}
#endif
