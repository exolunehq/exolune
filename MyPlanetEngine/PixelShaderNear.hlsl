// The terrain's colour near the ground (D3DApp::Draw, NearDetailClearance): the rock's face photo with its near detail
// (Materials.hlsli, PIXEL_NEAR_DETAIL). Higher up, the permutations without its code: present, never run, it cost up to
// 0.1 ms in registers.
#define PIXEL_NEAR_DETAIL
#include "PixelShader.hlsl"
