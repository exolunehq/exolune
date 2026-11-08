#include "Celestial.hlsli"
Texture2D<float4> skyScene : register(t0);
Texture2D<float4> skyTransport : register(t4);

// Kiloparsecs: the observer sits inside a stellar disk, behind nearer absorbing dust.
// Fixed quadrature through a 3D density field, not a painted sky dome or screen-space noise.
float3 GalacticRadiance(float3 world) {
    const float3 ray=GalaxyFrame(world), origin=float3(8.2,0,.025);
    float3 light=0.0, transmission=1.0;
    [loop] for(uint k=0;k<40;++k) {
        const float a=float(k)/40.0,b=float(k+1)/40.0;
        const float start=32.0*a*a,end=32.0*b*b,ds=end-start;
        const float3 p=origin+ray*(.5*(start+end));
        const float r=length(p.xy), theta=atan2(p.y,p.x);
        const float broad=CelestialNoise(p*.75);
        const float warp=.06*sin(p.x*.7)+.04*sin(p.y*.9)+.16*(broad-.5);
        const float z=p.z-warp;
        const float arms=pow(.5+.5*cos(4.0*theta-7.5*log(max(r,.4))),5.0);
        const float n=CelestialNoise(p*2.1), fine=CelestialNoise(p*6.8);
        const float disk=exp(-r/5.2)*exp(-abs(z)/.29);
        const float thick=exp(-r/4.2)*exp(-abs(z)/.85);
        const float bulge=exp(-length(p/float3(1.8,1.05,.8))*1.5);
        const float dust=exp(-abs(z)/(.065+.065*broad))*exp(-r/7.0)*(.2+2.5*arms)
            *(.08+pow(1.8*n,4.0))*(.5+fine)*2.1;
        const float3 optical=dust*float3(.72,1.0,1.38)*ds;
        const float3 stepT=exp(-optical);
        const float3 emission=(disk*(.32+2.1*arms)*(.25+1.3*n*n+.5*fine*fine)*float3(.78,.86,1.0)
            +.22*thick*float3(.85,.86,.90)+1.6*bulge*float3(1.0,.78,.50))*4.0e-8;
        const float3 integral=lerp(1.0-.5*optical,(1.0-stepT)/max(optical,1e-8),step(.001,optical));
        light+=transmission*emission*ds*integral;
        transmission*=stepT;
    }
    return light;
}

// Two remote stellar systems, inclined 3D ellipsoids with a thin dusty plane and central bulge.
float3 RemoteGalaxy(float3 ray,float3 centre,float scale,float tilt) {
    centre=normalize(centre);
    const float forward=dot(ray,centre);
    if(forward<=0.0) return 0.0;
    const float3 right=normalize(cross(float3(0,1,0),centre)), up=cross(centre,right);
    const float2 q=float2(dot(ray,right),dot(ray,up))/forward/scale;
    if(dot(q,q)>16.0) return 0.0;
    float3 light=0.0,transmission=1.0;
    [unroll] for(uint k=0;k<16;++k) {
        const float depth=-3.0+(k+.5)*.375;
        const float3 p=float3(q.x,q.y*cos(tilt)+depth*sin(tilt),depth*cos(tilt)-q.y*sin(tilt));
        const float r=length(p.xy),angle=atan2(p.y,p.x);
        const float arms=pow(.5+.5*cos(2.0*angle-5.0*log(max(r,.12))),4.0);
        const float disk=exp(-r*1.6)*exp(-abs(p.z)*12.0);
        const float bulge=exp(-length(p*float3(3,3,5))*2.0);
        const float dust=disk*(.3+2.0*arms)*1.5;
        const float3 emit=disk*(.35+arms)*float3(.65,.8,1.0)+bulge*float3(1.0,.8,.55);
        light+=transmission*emit*.375*8e-8;
        transmission*=exp(-dust*.375*float3(.7,1.0,1.4));
    }
    return light;
}
float4 PSMain(float4 position:SV_POSITION):SV_TARGET {
    float2 size; skyScene.GetDimensions(size.x,size.y);
    const int3 pixel=int3(position.xy,0);
    const float3 transport=skyTransport.Load(pixel).rgb;
    const float background=dot(skyScene.Load(pixel).rgb,CELESTIAL_LUMA);
    const float visibility=1.0/(1.0+pow(background/1.2e-7,1.25));
    if(taa.y>.5 || dot(transport,1.0/3.0)<.002 || visibility<.001) return 0.0;
    const float3 world=CelestialWorld(CelestialRay(position.xy,size));
    float3 radiance=GalacticRadiance(world);
    radiance+=RemoteGalaxy(world,float3(-.82,.42,.39),.023,1.04);
    radiance+=RemoteGalaxy(world,float3(.25,-.58,-.77),.007,.48);
    // Unresolved stellar background; no artificial parallax within a solar system.
    radiance+=float3(.75,.83,1.0)*1.2e-9;
    return float4(radiance*transport*visibility,0);
}
