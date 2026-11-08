// Shared celestial photometry and geometry. Light is in the same units as SUN_ILLUMINANCE = pi.
#ifndef CELESTIAL_HLSLI
#define CELESTIAL_HLSLI
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
static const float CELESTIAL_PI=3.14159265359;
static const uint CELESTIAL_STARS=42000, CELESTIAL_BODIES=7;
static const float3 CELESTIAL_LUMA=float3(.2126,.7152,.0722);
static const float NIGHT_IRRADIANCE=2.0e-8; // about 0.8 millilux, natural sky without moons
static const float SKY_EYE_EXPOSURE=650000.0; // bounded point/diffuse-source response, not terrain exposure

uint CelestialHash(uint x) { x^=x>>16; x*=0x7feb352du; x^=x>>15; x*=0x846ca68bu; return x^(x>>16); }
float CelestialRandom(uint x) { return (CelestialHash(x)>>8)*(1.0/16777216.0); }
float CelestialNoise(float3 p) {
    const int3 cell=(int3)floor(p); const float3 f=frac(p),u=f*f*(3.0-2.0*f);
    const uint k=asuint(cell.x)*1597334677u+asuint(cell.y)*3812015801u+asuint(cell.z)*2798796415u;
    float v[8];
    [unroll] for(uint i=0;i<8;++i) v[i]=CelestialRandom(k+(i&1)*1597334677u+((i>>1)&1)*3812015801u+((i>>2)&1)*2798796415u);
    return lerp(lerp(lerp(v[0],v[1],u.x),lerp(v[2],v[3],u.x),u.y),
        lerp(lerp(v[4],v[5],u.x),lerp(v[6],v[7],u.x),u.y),u.z);
}
float3 CelestialWorld(float3 local) { return local.x*faceX.xyz+local.y*faceY.xyz+local.z*faceZ.xyz; }
float3 CelestialLocal(float3 world) { return float3(dot(world,faceX.xyz),dot(world,faceY.xyz),dot(world,faceZ.xyz)); }
// The same diffuse phase law serves resolved surfaces and the incident exposure meter.
float CelestialPhase(float cosine) {
    cosine=clamp(cosine,-1,1);
    const float angle=acos(cosine);
    return (sqrt(saturate(1-cosine*cosine))+(CELESTIAL_PI-angle)*cosine)/CELESTIAL_PI;
}
float PlanetShine(float3 towardPlanet,float3 normal) {
    const float distance=max(length(towardPlanet),PLANET_RADIUS_KM);
    const float3 direction=towardPlanet/distance;
    return .105*pow(PLANET_RADIUS_KM/distance,2)*CelestialPhase(dot(-direction,lightDir.xyz))
        *saturate(dot(normal,direction));
}
float3 CelestialRay(float2 pixel,float2 size) {
    float2 p=pixel/size*2.0-1.0;
    return normalize(camForward.xyz+p.x*camRight.w*camRight.xyz-p.y*camUp.w*camUp.xyz);
}
// A fixed inclined galactic frame; all stellar points and the emitting volume use it.
float3 GalaxyFrame(float3 d) {
    const float3 z=normalize(float3(.23,.72,.655)), x=normalize(cross(float3(0,1,0),z)), y=cross(z,x);
    return float3(dot(d,x),dot(d,y),dot(d,z));
}
float3 GalaxyWorld(float3 d) {
    const float3 z=normalize(float3(.23,.72,.655)), x=normalize(cross(float3(0,1,0),z)), y=cross(z,x);
    return d.x*x+d.y*y+d.z*z;
}
float MagnitudeFlux(float m) { return CELESTIAL_PI*pow(10.0,-.4*(m+26.74)); }
// Schaefer's rod/cone threshold: scene radiance -> cd/m2 -> nanolamberts -> stellar illuminance.
float PointThreshold(float background) {
    const float B=max(background,0.0)*(126000.0/CELESTIAL_PI)*314159.265;
    const float rods=pow(10.0,-9.8)*pow(1.0+sqrt(pow(10.0,-1.9)*B),2.0);
    const float cones=pow(10.0,-8.35)*pow(1.0+sqrt(pow(10.0,-5.9)*B),2.0);
    return MagnitudeFlux(-16.57-2.5*log10(max(min(rods,cones),1e-15)));
}
float BodyResolved(uint id,float pixelAngle) {
    return smoothstep(.65,1.5,celestialPosition[id].w/max(length(celestialPosition[id].xyz)*pixelAngle,1e-12));
}
#endif
