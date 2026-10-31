// DX12 FFT ocean spike. Layout matches Ocean::Constants, independent of the planet's Frame.
#ifndef OCEAN_UNIFORM_HLSLI
#define OCEAN_UNIFORM_HLSLI
#define OCEAN_N 256
#define OCEAN_CASCADES 4
#define OCEAN_FOAM_N 512
cbuffer OceanConstants : register(b1)
{
    float4 oceanLengths;
    float4 oceanKMin;
    float4 oceanKMax;
    float4 oceanWind;       // speed, direction (radians in carried plane), fetch (m), JONSWAP gamma
    float4 oceanSwell;      // Hs, direction, peak angular frequency, spreading
    float4 oceanSettings;   // choppiness, short-wave cutoff (m), time loop (s), seed
    float4 oceanTime;       // looped time, dt, spectrum gain, unused
    float4 oceanOrigin[4];  // camera origin modulo each cascade, in UV units; no large world floats
    float4 oceanFoamOrigin[2]; // xy: camera origin modulo clip size; z: texel size; w: clip size
    float4 oceanFoamGrid[2];   // xy: camera fraction within a texel (m); zw unused
    int4 oceanFoamSnap[2];    // xy: current global camera texel; zw: previous
    float4 oceanFoamParams; // Jacobian threshold, gain, growth, decay rate
    float4 oceanRender;     // active foam ping, amount, reset marker, camera seabed elevation
    float4 oceanPoreOrigin; // origin for two pore scales, modulo 1
    float4 oceanStreakOrigin; // wind-aligned streak UV origin, unused
};
#endif
