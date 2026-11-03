// Four terrain contacts around a rooted plant. The 28-bit payload stays in a finite, normal float container.
#ifndef ROOT_CONTACT_HLSLI
#define ROOT_CONTACT_HLSLI
#ifdef __cplusplus
#include <algorithm>
#include <cmath>
#define ROOT_INLINE inline
#define ROOT_UINT unsigned
ROOT_INLINE float RootClamp(float v,float a,float b) { return std::min(std::max(v,a),b); }
ROOT_INLINE unsigned RootRound(float x) { return unsigned(std::lround(x)); }
#else
#define ROOT_INLINE
#define ROOT_UINT uint
float RootClamp(float v,float a,float b) { return clamp(v,a,b); }
uint RootRound(float x) { return (uint)round(x); }
#endif
ROOT_INLINE ROOT_UINT RootCode(float value,float radius) {
    return RootRound(63.0f+63.0f*RootClamp(value/(1.5f*radius),-1.0f,1.0f));
}
ROOT_INLINE ROOT_UINT PackRootContacts(float east,float west,float north,float south,float radius) {
    radius=RootClamp(radius,0.01f,1000000.0f);
    return 0x30000000u | RootCode(east,radius) | (RootCode(west,radius)<<7u)
        | (RootCode(north,radius)<<14u) | (RootCode(south,radius)<<21u);
}
ROOT_INLINE float RootContactValue(ROOT_UINT packed,ROOT_UINT shift,float radius) {
    return (float((packed>>shift)&127u)-63.0f)*(1.5f*radius/63.0f);
}
ROOT_INLINE float RootContactHeight(ROOT_UINT packed,float east,float north,float radius) {
    const float x=RootClamp(east/radius,-1.0f,1.0f), y=RootClamp(north/radius,-1.0f,1.0f);
    const float a=RootContactValue(packed,0u,radius), b=RootContactValue(packed,7u,radius);
    const float c=RootContactValue(packed,14u,radius), d=RootContactValue(packed,21u,radius);
    // Smooth, separable quadratic through the centre and the four measured endpoints.
    return 0.5f*((a-b)*x+(a+b)*x*x+(c-d)*y+(c+d)*y*y);
}
#undef ROOT_INLINE
#undef ROOT_UINT
#endif
