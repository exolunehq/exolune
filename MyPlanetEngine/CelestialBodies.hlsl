// Finite bodies participate in scene depth before air/cloud integration and temporal reprojection.
#include "Celestial.hlsli"
#include "AirlessPhotometry.hlsli"
Texture2D<float4> airlessMaterial:register(t8); // selected body's cooked physical field
SamplerState lunarSampler:register(s0);
#include "DistantPlanet.hlsli"
cbuffer SelectedBody:register(b4) { uint selectedBody; uint proxyShell; };
// Radiance of the nearest resolved sphere, with antialiased coverage. No camera-facing cards.
float3 CelestialDiscs(float3 view,float pixelAngle,out float coverage,out float bodyDepth) {
    bodyDepth=0.0; float nearest=1e30; float3 radiance=0.0; coverage=0.0;
    [loop] for(uint i=selectedBody;i<selectedBody+1;++i) {
        const float3 c=celestialPosition[i].xyz;
        const float distance=length(c), radius=celestialPosition[i].w;
        const float along=dot(c,view);
        if(along<=0.0 || distance<=radius) continue;
        const float3 miss=c-view*along; // stable even for very small angular radii
        const float impact=length(miss), width=max(distance*pixelAngle,1e-6);
        float cover=saturate((radius-impact)/width+.5)*BodyResolved(i,pixelAngle);
        if(cover<=0.0) continue;
        const float depth=along-sqrt(max(0.0,radius*radius-impact*impact));
        if(depth>=nearest) continue;
        nearest=depth; coverage=cover; bodyDepth=depth;
        if(i==6) {
            const float mu=sqrt(saturate(1.0-impact*impact/(radius*radius)));
            radiance=celestialFlux[i].rgb/(CELESTIAL_PI*pow(radius/distance,2.0))*(.4+.6*mu)/.8;
        } else {
            const float3 n=normalize(view*depth-c);
            const float3 nw=CelestialWorld(n);
            float3 shadingNormal=nw;
            const float footprint=width/radius;
            float terrain=CelestialNoise(nw*4.0+float(i)*11.0);
            float fine=CelestialNoise(nw*37.0+float(i)*19.0);
            float surfacePattern=.70+.42*terrain+.16*(fine-.5)*(1.0-smoothstep(.015,.07,footprint));
            if(i<3) {
                const float2 uv=float2(atan2(nw.z,nw.x)/(2.0*CELESTIAL_PI)+.5,acos(clamp(nw.y,-1.0,1.0))/CELESTIAL_PI);
                const float latitudeScale=max(length(nw.xz),.05);
                const float lod=max(0.0,log2(max(footprint*2048.0/(2.0*CELESTIAL_PI*latitudeScale),1.0)));
                const float4 material=airlessMaterial.SampleLevel(lunarSampler,uv,lod);
                surfacePattern=material.r*2.0;
                const float3 east=float3(-nw.z,0,nw.x)/max(length(nw.xz),1e-5), north=cross(east,nw);
                const float2 slope=(material.gb*255.0-128.0)/127.0;
                shadingNormal=normalize(nw-east*slope.x-north*slope.y);
            } else if(i==5) {
                surfacePattern=.8+.20*sin(nw.y*65.0+7.0*terrain)+.12*fine;
            }
            const float mu=dot(CelestialLocal(shadingNormal),celestialLight[i].xyz);
            const float incidence=(i<3?AirlessDiffuse(mu,dot(CelestialLocal(shadingNormal),-view)):saturate(mu))
                *smoothstep(-.015,.025,dot(n,celestialLight[i].xyz));
            const float3 planetCentre=-camVertical.xyz*(PLANET_RADIUS_KM+camVertical.w);
            const float earthshine=PlanetShine(planetCentre-c,n);
            const float3 reflectance=celestialSurface[i].rgb*(i<3?.16/.145:1.0);
            radiance=reflectance*max(surfacePattern,.1)*(celestialLight[i].w*incidence+earthshine);
        }
    }
    return radiance*coverage;
}

struct BodyOutput {
    float4 scene:SV_TARGET0;
    float4 solar:SV_TARGET1;
    float depth:SV_DEPTH;
};
BodyOutput PSMain(float4 position:SV_POSITION) {
    const float2 size=float2(2.0*camRight.w,2.0*camUp.w)/taa.w;
    const float3 view=CelestialRay(position.xy,size);
    if(selectedBody==7) {
        const float3 centre=-camVertical.xyz*(PLANET_RADIUS_KM+camVertical.w);
        const float radius=PLANET_RADIUS_KM+float(proxyShell)*.001;
        const float along=dot(centre,view),impact=length(centre-view*along);
        clip(min(along,radius-impact));
        const float coverageDistance=along-sqrt(max(0,radius*radius-impact*impact));
        float distance=along-sqrt(max(0,PLANET_RADIUS_KM*PLANET_RADIUS_KM-impact*impact));
        float3 normal=normalize(view*distance-centre);
        const float3 world=CelestialWorld(normal);
        const float footprint=max(1000,distance*1000*taa.w);
        float elevation;
        const float3 albedo=DistantPlanetAlbedo(world,footprint,elevation);
        // Transport ends on the filtered physical surface, never on the expanded raster envelope.
        const float surfaceRadius=PLANET_RADIUS_KM+max(0,elevation)*.001;
        clip(surfaceRadius-impact);
        distance=along-sqrt(max(0,surfaceRadius*surfaceRadius-impact*impact));
        normal=normalize(view*distance-centre);
        const float daylight=saturate(dot(normal,lightDir.xyz));
        // The night side under the same light as the near ground: the natural night sky and the moons' beams
        // (Moonlight), instead of a fixed ambient ten times brighter than the moons that the night's local adaptation
        // then showed as a bright brown ball (docs/spec-ciel-celeste.md).
        float night=NIGHT_IRRADIANCE;
        [unroll] for(uint moon=0;moon<3;++moon)
            night+=dot(Moonlight(moon),CELESTIAL_LUMA)
                *saturate(dot(normal,MoonDirectionFrom(moon,normal*PLANET_RADIUS_KM)));
        const float3 radiance=albedo*(daylight+night/CELESTIAL_PI);
        const float drawDistance=proxyShell>0?coverageDistance:distance;
        const float4 projected=mul(float4(view*drawDistance*1000,1),viewProj);
        BodyOutput o;o.scene=float4(radiance,distance);o.solar=0;o.depth=projected.z/projected.w;return o;
    }
    float coverage,distance;
    const float3 light=CelestialDiscs(view,taa.w,coverage,distance);
    clip(coverage-.01);
    const float4 projected=mul(float4(view*distance*1000.0,1.0),viewProj);
    BodyOutput o;
    o.scene=float4(light,distance);
    o.solar=0;
    o.depth=projected.z/projected.w;
    return o;
}
