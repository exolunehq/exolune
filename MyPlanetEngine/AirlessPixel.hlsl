#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "AirlessMaterial.hlsli"
#include "Shadows.hlsli"
#include "TerrainNormals.hlsli"
#include "TerrainShipShadow.hlsli"
// The common terrain's map slot holds this body's cooked field when its profile is airless.
// Materials.hlsli's terrestrial cube is unused by this entry point and is removed by the compiler.
Texture2D<float4> airlessOrbitalMap:register(t29);
float4 PSMain(PSInput input,out float4 solar:SV_TARGET1):SV_TARGET0 {
    solar=0;
    const float3 up=normalize(input.dir),dx=ddx(input.pos),dy=ddy(input.pos);
    float3 splinePosition;float splineHeight,splineWeight;
    const float3 spline=SplineNormal(input.chart,input.corner,up,splinePosition,splineHeight,splineWeight);
    float fineWeight,fineHeight,uncertainty;float4 inland;float3 flow;uint4 near;
    const float3 fine=FineNormal(input.chart,fineWeight,fineHeight,inland,flow,uncertainty,near);
    const float lightWeight=fineWeight*smoothstep(FINE_LIGHT_MIN_CELL,2*FINE_LIGHT_MIN_CELL,2*faceParams.x/faceParams.w);
    float screenWeight,screenHeight;float4 screenInland,screenGround;float3 screenPosition,screenFlow;
    const float3 screen=ScreenNormal(input.position.xy,up,screenWeight,screenHeight,screenInland,screenPosition,screenGround,screenFlow);
    float3 normal=normalize(lerp(normalize(lerp(normalize(lerp(normalize(input.normal),spline,splineWeight)),fine,lightWeight)),screen,screenWeight));
    if(lightDir.w>.5) {normal=normalize(cross(dy,dx));normal*=dot(normal,up)<0?-1:1;}
    float3 surface=input.pos;
    const float3 ray=normalize(input.pos);
    const float along=dot(ray,spline);
    if(SPLINE_SURFACE>0 && splineWeight>0 && abs(along)>.05)
        surface+=ray*(SPLINE_SURFACE*splineWeight*dot(splinePosition-input.pos,spline)/along);
    surface=lerp(surface,screenPosition,screenWeight);
    const float3 q=detailOrigin.xyz+CelestialWorld(surface);
    float albedo=lerp(lerp(input.geology.x,inland.w,lightWeight),screenGround.y,screenWeight);
    const float3 qx=ddx(q),qy=ddy(q);
    const float resolved=lerp(lerp(input.cellSize,2*faceParams.x/(faceParams.w*ringParams.w),lightWeight),
        max(length(qx),length(qy))*screenRelief.w,screenWeight);
    const float atlasCell=faceParams.y*CELESTIAL_PI/1024;
    [branch] if(resolved>atlasCell) {
        const float3 worldUp=CelestialWorld(up);
        const float latitudeScale=max(length(worldUp.xz),.05);
        const float2 uv=float2(atan2(worldUp.z,worldUp.x)/(2*CELESTIAL_PI)+.5,
            acos(clamp(worldUp.y,-1.0,1.0))/CELESTIAL_PI);
        const float pixelFootprint=max(length(qx),length(qy));
        const float fineLevel=max(0,log2(max(pixelFootprint/(atlasCell*latitudeScale),1)));
        const float coarseLevel=max(fineLevel,log2(resolved/(atlasCell*latitudeScale)));
        const float4 detail=airlessOrbitalMap.SampleLevel(materialSampler,uv,fineLevel);
        const float4 coarse=airlessOrbitalMap.SampleLevel(materialSampler,uv,coarseLevel);
        const float weight=smoothstep(atlasCell,2*atlasCell,resolved);
        const float2 residual=(detail.gb-coarse.gb)*(255.0/127.0);
        const float3 east=float3(-worldUp.z,0,worldUp.x)/max(length(worldUp.xz),1e-5);
        normal=normalize(normal-weight*CelestialLocal(east*residual.x+cross(east,worldUp)*residual.y));
        albedo=lerp(albedo,.32*detail.r,weight);
    }
    const AirlessMaterial material=SampleAirlessMaterial(q,qx,qy,normal,up,albedo,resolved);
    const float spread=sqrt((ddx(input.horizon)*ddx(input.horizon)+ddy(input.horizon)*ddy(input.horizon))/12);
    const float visible=SunAboveHorizon(dot(up,lightDir.xyz),input.horizon,spread)*ShipShadowOn(input.pos);
    return float4(material.albedo*AirlessIrradiance(material.normal,up,-ray,visible,material.cavity),length(input.pos)*.001);
}
