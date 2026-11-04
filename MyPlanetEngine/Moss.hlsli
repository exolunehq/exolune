#ifndef MOSS_HLSLI
#define MOSS_HLSLI
#include "Materials.hlsli"

float MossClimate(float waterBalance, float growingSeason) {
    return smoothstep(0.58,1.18,waterBalance)*smoothstep(4.5,8.0,growingSeason);
}
float MossShelter(float canopy) { return smoothstep(0.07,0.42,canopy); }

struct MossMaterial { float weight; float3 albedo; float3 slope; };

// Separate patch boundaries from the millimetre relief of the cushion.
MossMaterial LocalMoss(float3 p, float footprint, float site, float bias) {
    MossMaterial moss=(MossMaterial)0;
    const float fade=1.0-smoothstep(0.055,0.18,footprint);
    if (site*fade<=0.001) return moss;
    float3 patch=p*5.0, cell=floor(patch);
    const float3 uneven=Noise3(uint3(int3(cell))+0x68cdu,patch-cell);
    moss.weight=site*fade*smoothstep(-0.13,0.27,uneven.x+bias);
    if (moss.weight<=0.001) return moss;
    const float fineWeight=1.0-smoothstep(0.23,0.5,footprint*36.0);
    float fine=0.0;
    if (fineWeight>0.0) {
        const float3 grain=p*36.0;
        cell=floor(grain);
        const uint3 key=uint3(int3(cell))+0x257fu;
        fine=Noise3(key,grain-cell).x*fineWeight;
        moss.slope=0.26*fineWeight*NoiseGradient(key,grain-cell);
    }
    moss.albedo=lerp(float3(0.058,0.087,0.021),float3(0.16,0.222,0.057),
                     saturate(0.48+0.42*uneven.y+0.30*fine));
    return moss;
}

// Soil patches follow the planet lattice instead of an object's frame.
MossMaterial GroundMoss(float3 q, float pixel, float site) {
    MossMaterial moss=(MossMaterial)0;
    const float fade=1.0-smoothstep(-3.0,-0.5,pixel);
    if (site*fade<=0.001) return moss;
    const float3 patches=Fbm3(q,2.0,-1.0,pixel,0.52,0x32d9u);
    if (patches.x<-.14) return moss;
    const int octave=(int)round(log2(detailOrigin.w))+2;
    uint3 cell;
    float3 fraction;
    LatticePoint(q,octave,cell,fraction);
    const float3 edge=Noise3(cell+0x54efu,fraction)*OctaveFade(-2.0,pixel);
    moss.weight=site*fade*smoothstep(0.06,0.28,patches.x+0.22*edge.x);
    if (moss.weight<=0.001) return moss;
    const Texture mat=DetailBands(q,pixel,-7.0,-3.0,0.16,0.19,0x257fu);
    moss.albedo=lerp(float3(0.052,0.073,0.019),float3(0.122,0.170,0.038),
                     saturate(0.5+patches.y+0.33*edge.y))*mat.color;
    moss.slope=mat.slope;
    return moss;
}
#endif
