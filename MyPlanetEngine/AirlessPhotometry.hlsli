#ifndef AIRLESS_PHOTOMETRY_HLSLI
#define AIRLESS_PHOTOMETRY_HLSLI
#ifdef __cplusplus
#include <algorithm>
inline
#endif
// A particulate surface's single scattering plus a diffuse component.
// The same law lights the detailed surface, its objects and its distant filtered representation.
// Normal incidence is one; the denominator is bounded by the finite roughness of regolith.
float AirlessDiffuse(float incidence,float emission) {
#ifdef __cplusplus
    using std::max;using std::min;
    incidence=min(max(incidence,0.0f),1.0f);emission=min(max(emission,0.0f),1.0f);
#else
    incidence=saturate(incidence);emission=saturate(emission);
#endif
    return incidence*(.35f+.65f*2/max(incidence+emission,.08f));
}
#endif
