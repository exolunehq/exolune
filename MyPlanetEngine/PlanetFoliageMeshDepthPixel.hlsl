#include "PlanetFoliageMeshPixel.hlsl"

// La profondeur seule des maillages proches (optimisation.md, round 3) : les memes rejets alpha que PSMain, rien d'autre ;
// la couleur suit en profondeur egale (PlanetFoliageMeshHardwarePixel.hlsl), une fois par pixel montre.
void PSDepthOnly(VOut i) {
    const Result unused=PSMain(i);
}
