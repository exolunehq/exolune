#ifndef FOLIAGE_SEQUENCE_HLSLI
#define FOLIAGE_SEQUENCE_HLSLI
// The depth bound uses this same minimum surviving filtered alpha.
#define FOLIAGE_PROXY_ALPHA_MIN (1.0f/1024.0f)
#ifdef __cplusplus
#include <cstdint>
using FoliageSequenceUint=std::uint32_t;
#define FOLIAGE_SEQUENCE_INLINE inline
#else
#define FoliageSequenceUint uint
#define FOLIAGE_SEQUENCE_INLINE
#endif
// Three independently digitally shifted Sobol dimensions: mesh/proxy relay,
// mesh-level relay, then leaf alpha. Powers-of-two frame groups retain balance;
// independent white samples had long visible runs of missing crown pixels.
FOLIAGE_SEQUENCE_INLINE float FoliageSequence(FoliageSequenceUint frame,FoliageSequenceUint dimension,FoliageSequenceUint scramble) {
    const FoliageSequenceUint directions[3][6]={
        {0x80000000u,0x40000000u,0x20000000u,0x10000000u,0x08000000u,0x04000000u},
        {0x80000000u,0xc0000000u,0xa0000000u,0xf0000000u,0x88000000u,0xcc000000u},
        {0x80000000u,0xc0000000u,0x60000000u,0x90000000u,0xe8000000u,0x5c000000u}};
    FoliageSequenceUint value=scramble;
#ifndef __cplusplus
    [unroll]
#endif
    for(FoliageSequenceUint bit=0;bit<6;++bit) if((frame&(1u<<bit))!=0u) value^=directions[dimension][bit];
    return (float(value>>8u)+0.5f)/16777216.0f;
}
#undef FOLIAGE_SEQUENCE_INLINE
#ifndef __cplusplus
#undef FoliageSequenceUint
#endif
#endif
