// Shared renderer, selected physical stack. Variants compile out absent phenomena.
#ifdef AIRLESS_SURFACE
#include "AirlessRelief.hlsli"
#else
#include "Relief.hlsli"
#endif
