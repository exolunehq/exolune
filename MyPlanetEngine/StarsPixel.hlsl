#include "Celestial.hlsli"
Texture2D<float4> skyScene : register(t0);
Texture2D<float4> skyTransport : register(t4);
float4 PSMain(float4 position:SV_POSITION,noperspective float2 offset:TEXCOORD0,
    nointerpolation float3 flux:TEXCOORD1,nointerpolation float solidAngle:TEXCOORD2):SV_TARGET {
    const int3 pixel=int3(position.xy,0);
    const float3 transmission=skyTransport.Load(pixel).rgb;
    const float background=dot(skyScene.Load(pixel).rgb,CELESTIAL_LUMA);
    const float3 received=flux*transmission;
    const float energy=dot(received,CELESTIAL_LUMA);
    const float visible=saturate(1.0-PointThreshold(background+NIGHT_IRRADIANCE/CELESTIAL_PI)/max(energy,1e-30));
    // Pixel integral of a normalized Moffat point image; four fixed quadrature samples, no flicker clock.
    float psf=0.0;
    [unroll] for(uint i=0;i<4;++i) {
        const float2 p=offset+float2((i&1)?.25:-.25,(i&2)?.25:-.25);
        psf+=pow(1.0+dot(p,p)/(1.35*1.35),-3.0);
    }
    psf*=.25*2.0/(CELESTIAL_PI*1.35*1.35);
    return float4(received*visible*psf/max(solidAngle,1e-15),0);
}
