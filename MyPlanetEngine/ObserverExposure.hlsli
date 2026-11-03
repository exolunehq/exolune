#ifndef OBSERVER_EXPOSURE_HLSLI
#define OBSERVER_EXPOSURE_HLSLI
#ifdef __cplusplus
#include <algorithm>
#define OBSERVER_INLINE inline
OBSERVER_INLINE float ObserverClamp(float x) { return std::min(std::max(x,0.0f),1.0f); }
OBSERVER_INLINE float ObserverMax(float x,float y) { return std::max(x,y); }
#else
#define OBSERVER_INLINE
float ObserverClamp(float x) { return saturate(x); }
float ObserverMax(float x,float y) { return max(x,y); }
#endif
OBSERVER_INLINE float ObserverSmooth(float a,float b,float x) {
    const float t=ObserverClamp((x-a)/(b-a));return t*t*(3.0f-2.0f*t);
}
// This is an observer response, separate from radiance and material reflectance.
// Frame camPlane.w carries this world-derived cover; the framing never meters it.
OBSERVER_INLINE float ObserverCanopy(float cover,float clearance,float canopyHeight) {
    const float h=ObserverMax(canopyHeight,0.1f);
    return ObserverClamp(cover)*(1.0f-ObserverSmooth(0.4f*h,h,clearance));
}
OBSERVER_INLINE float ObserverExposure(float openIrradiance,float shelteredIrradiance,float sunCosine) {
    const float ratio=ObserverMax(openIrradiance,0.0f)/ObserverMax(shelteredIrradiance,1e-12f);
    const float bounded=1.0f+3.0f*ObserverClamp((ratio-1.0f)/3.0f);
    return 1.0f+(bounded-1.0f)*ObserverSmooth(-0.08f,0.05f,sunCosine);
}
#undef OBSERVER_INLINE
#endif
