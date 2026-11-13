// The shared incident meter, used by the eye response and automatic cockpit backlight control.
#ifndef SCENE_EXPOSURE_HLSLI
#define SCENE_EXPOSURE_HLSLI
#include "Atmosphere.hlsli"
#include "CanopyLighting.hlsli"
#include "ObserverExposure.hlsli"
// An incident meter, independent of the frame. The ground reference remains below the air; as that air falls below
// the observer, the direct beam is metered at the observer instead. Ground sunset must not trigger night exposure
// while an orbital observer remains in sunlight. Diffuse night light and the perceptual darkness key remain shared.
float Exposure()
{
    const float muS = dot(camVertical.xyz, lightDir.xyz);
    // camVertical.w: the camera's altitude above the sea, km (D3DApp::Draw).
    const float height=max(camVertical.w,0.0);
    const float airBelow = 1.0 - exp(-height / RAYLEIGH_SCALE_HEIGHT);
    // Above the air, the visible solar disc through the air its rays cross (SunDiscAboveAir), as on every lit surface.
    float3 sunMeter=SUN_ILLUMINANCE*lerp(SunTransmittance(0.0,muS,0.0),SunTransmittance(height,muS,0.0),airBelow);
    float3 skyMeter=SkyIrradiance(0.0,muS,0.0);
    if(erosionMode.w!=0u) {
        const uint body=erosionMode.w-1;
        const float moonDistance=length(celestialPosition[body].xyz),moonRadius=celestialPosition[body].w;
        const float3 vertical=-normalize(celestialPosition[body].xyz);
        const float elevation=asin(clamp(dot(vertical,celestialLight[body].xyz),-1,1));
        const float dip=acos(saturate(moonRadius/max(moonDistance,moonRadius)));
        const float cut=clamp((-dip-elevation)/SUN_ANGULAR_RADIUS,-1,1);
        const float visible=(acos(cut)-cut*sqrt(saturate(1-cut*cut)))/PI;
        sunMeter=SUN_ILLUMINANCE*visible*celestialLight[body].w;
        const float3 planet=-camVertical.xyz*(PLANET_RADIUS_KM+camVertical.w);
        const float earthshine=PlanetShine(planet,vertical);
        skyMeter=SUN_ILLUMINANCE*earthshine;
    }
    const float3 daylight = sunMeter+skyMeter;
    const float compensation = lerp(EXPOSURE_COMPENSATION, EXPOSURE_COMPENSATION_ORBIT, airBelow);
    float observer=1.0;
    if(camPlane.w>0.0) {
        const CanopyTransport transport=CanopyLight(camPlane.w,0.0,muS);
        const float3 sheltered=sunMeter*transport.direct+skyMeter*transport.sky
            +sunMeter*transport.sunScatter*float3(0.45,0.65,0.32);
        observer=ObserverExposure(dot(daylight,CELESTIAL_LUMA),dot(sheltered,CELESTIAL_LUMA),dot(camVertical.xyz,lightDir.xyz));
    }
    const float illuminance=max(dot(daylight,CELESTIAL_LUMA),NIGHT_IRRADIANCE);
    const float adaptationLuminance=illuminance*(126000.0/PI)*.18/PI;
    const float key=(1.03-2.0/(2.0+log10(adaptationLuminance+1.0)))/.69;
    return observer*exp2(compensation)*PI/illuminance*min(key,1.0);
}

// Dimmable instruments follow the same world illumination as the observer; external beacons keep their flux.
float NightInstrumentGain() {
    const float3 vertical=erosionMode.w!=0u?-normalize(celestialPosition[max(erosionMode.w,1u)-1].xyz):camVertical.xyz;
    const float night=1.0-smoothstep(-.02,.03,dot(vertical,lightDir.xyz));
    return lerp(1.0,min(1.0,2.0/max(Exposure(),1.0)),night);
}
#endif
