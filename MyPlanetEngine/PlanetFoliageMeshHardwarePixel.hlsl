#include "PlanetFoliageMeshPixel.hlsl"

// Meme couleur et memes rejets alpha que le shader de reference ; la profondeur
// provient du rasteriseur au lieu d'etre recalculee depuis i.pos.
struct HardwareResult { float4 colour : SV_TARGET0; float4 solar : SV_TARGET1; };
HardwareResult PSNoDepth(VOut i) {
    Result shaded=PSMain(i);
    HardwareResult result;
    result.colour=shaded.colour; result.solar=shaded.solar;
    return result;
}
