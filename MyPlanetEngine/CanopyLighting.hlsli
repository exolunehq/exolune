#ifndef CANOPY_LIGHTING_HLSLI
#define CANOPY_LIGHTING_HLSLI
#ifdef __cplusplus
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#define CANOPY_INLINE inline
CANOPY_INLINE float CanopyClamp(float x) { return std::clamp(x,0.0f,1.0f); }
CANOPY_INLINE float CanopyPower(float x,float y) { return std::pow(x,y); }
CANOPY_INLINE float CanopyMax(float x,float y) { return std::max(x,y); }
using CanopyUint=std::uint32_t;
CANOPY_INLINE CanopyUint CanopyBits(float x) { CanopyUint bits;std::memcpy(&bits,&x,4);return bits; }
CANOPY_INLINE float CanopyFloat(CanopyUint bits) { float x;std::memcpy(&x,&bits,4);return x; }
#else
#define CANOPY_INLINE
#define CanopyUint uint
float CanopyClamp(float x) { return saturate(x); }
float CanopyPower(float x,float y) { return pow(x,y); }
float CanopyMax(float x,float y) { return max(x,y); }
uint CanopyBits(float x) { return asuint(x); }
float CanopyFloat(uint bits) { return asfloat(bits); }
#endif
// Ordinary rock/tuft instances keep their 64-byte layout. Eight low mantissa
// bits carry cover, with less than 0.0031% relative colour loss after decoding.
CANOPY_INLINE float PackObjectCanopy(float blue,float cover) {
    return CanopyFloat((CanopyBits(blue)&0xffffff00u)|CanopyUint(CanopyClamp(cover)*255.0f+0.5f));
}
CANOPY_INLINE float ObjectCanopy(float blue) { return float(CanopyBits(blue)&255u)/255.0f; }
CANOPY_INLINE float ObjectBlue(float blue) { return CanopyFloat(CanopyBits(blue)&0xffffff00u); }
struct CanopyTransport { float direct; float sky; float sunScatter; };
// Crown envelopes overlap without forming an opaque roof. Diffuse transport
// includes a bounded single-scatter approximation, always lit by the actual sky.
CANOPY_INLINE CanopyTransport CanopyLight(float cover,float relativeHeight,float muSun) {
    const float above=CanopyClamp(cover)*(1.0f-CanopyClamp(relativeHeight));
    const float gap=1.0f-0.82f*above;
    CanopyTransport t;
    t.direct=CanopyPower(gap,1.0f/CanopyMax(muSun,0.15f));
    // Diffuse light crosses both leaf faces and returns between foliage layers.
    // Sum that bounded geometric series instead of treating every intercepted
    // sky direction as almost black. Open ground stays exactly unchanged.
    const float leafDiffuse=0.28f,intercepted=1.0f-gap;
    t.sky=(gap+leafDiffuse*intercepted)/(1.0f-0.5f*leafDiffuse*intercepted);
    // A bounded canopy bounce comes from intercepted sunlight, never exposure.
    t.sunScatter=0.12f*above*(1.0f-t.direct)*CanopyMax(muSun,0.0f);
    return t;
}
#undef CANOPY_INLINE
#ifndef __cplusplus
#undef CanopyUint
#endif
#endif
