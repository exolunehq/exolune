// The terrain's colour under the screen relief at full weight (D3DApp::Draw): no pixel refines its contour there
// (PixelShader.hlsl, refine), and this permutation tells the compiler so: 0.4 to 1.1 ms less per frame in orbit.
#define PIXEL_SCREEN_RELIEF
#include "PixelShader.hlsl"
