// Contact area after the renderer's coatings: base soils, scree, rock, beach, snow.
// Plain scalar C++/HLSL so the exact composition can be checked without a GPU.
#ifndef SURFACE_WEIGHTS_HLSLI
#define SURFACE_WEIGHTS_HLSLI
#ifdef __cplusplus
#include <algorithm>
inline float SurfaceUnit(float x) { return std::min(std::max(x,0.0f),1.0f); }
#define SURFACE_INLINE inline
#else
float SurfaceUnit(float x) { return saturate(x); }
#define SURFACE_INLINE
#endif
struct SurfaceWeights { float soil, grass, gravel, rock, sand, snow; };
SURFACE_INLINE SurfaceWeights GroundContactWeights(float soil,float grass,float sand,float scree,float rock,float beach,float snow) {
    SurfaceWeights w;
    snow=SurfaceUnit(snow); beach=SurfaceUnit(beach); rock=SurfaceUnit(rock); scree=SurfaceUnit(scree);
    soil=SurfaceUnit(soil); grass=SurfaceUnit(grass); sand=SurfaceUnit(sand);
    // Soil modifiers may overlap in colour. Normalize their contact areas before applying the upper coatings.
    const float sum=soil+grass+sand;
    if (sum>1e-6f) { soil/=sum; grass/=sum; sand/=sum; }
    else { soil=1.0f; grass=sand=0.0f; }
    const float under=(1.0f-snow)*(1.0f-beach), loose=under*(1.0f-rock), base=loose*(1.0f-scree);
    w.soil=base*soil; w.grass=base*grass; w.gravel=loose*scree; w.rock=under*rock;
    w.sand=(1.0f-snow)*beach+base*sand; w.snow=snow;
    return w;
}
#undef SURFACE_INLINE
#endif
