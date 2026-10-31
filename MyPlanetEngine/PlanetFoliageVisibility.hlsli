#ifndef PLANET_FOLIAGE_VISIBILITY_HLSLI
#define PLANET_FOLIAGE_VISIBILITY_HLSLI
uint PlanetFoliageVisibilityHash(uint seed) {
    uint h=seed ^ 0x9e3779b9u; h^=h>>16; h*=0x7feb352du; h^=h>>15; h*=0x846ca68bu; h^=h>>16;
    return h & ((1u<<20)-1u);
}
#endif
