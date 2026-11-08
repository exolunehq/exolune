#include "Planet.hlsli"
#include "Atmosphere.hlsli"
#include "PlanetMap.hlsli"
#include "City.hlsli"
#include "FoliageSequence.hlsli"

float CityPulseIntegral(float x,float width){return floor(x)*width+min(frac(x),width);}
float CityLine(float q,float width){
    float span=max(fwidth(q),1e-4),duty=saturate(width*2);
    // Exact box-filtered periodic stripe. At distance, fine seams converge to
    // their area coverage instead of flashing or turning half the surface grey.
    return saturate((CityPulseIntegral(q+width+span*.5,duty)-CityPulseIntegral(q+width-span*.5,duty))/span);
}
#include "CityInteriors.hlsli"
struct Output {float4 radiance:SV_TARGET0;float4 sunPart:SV_TARGET1;};
Output PSMain(CityPixel input){
    uint2 pixel=uint2(input.position.xy);uint hash=pixel.x*0x8da6b343u^pixel.y*0xd8163841u;
    hash^=hash>>16;hash*=0x7feb352du;hash^=hash>>15;hash*=0x846ca68bu;hash^=hash>>16;
    uint flags=(uint)(taa.z+.5);uint phase=(flags&4096u)!=0?((flags>>3)&63u):0;
    const float noise=FoliageSequence(phase,1,hash);
    if(input.detail.z>.5){if(noise<abs(input.detail.y))discard;}else if(noise>=input.detail.y)discard;
    const CityMaterial m=cityMaterials[input.material];uint role=(uint)m.properties.w;
    // The manufactured border owns the path edge. Interpolated distance from
    // boundary-only vertices is zero across a narrow polygon and must never
    // be used to discard its interior.
    float2 uv=input.uv;
    if(role==12||role==13||role==14)uv=input.local.xy*.5;
    const float3 texcoord=float3(uv,m.texture.x);
    float3 albedo=m.color.rgb*input.detail.x*cityColor.Sample(citySampler,texcoord).rgb;
    float3 orm=cityOrm.Sample(citySampler,texcoord).rgb;
    float rough=max(.14,m.properties.x*orm.g),metal=m.properties.y*orm.b;
    float3 n=normalize(input.normal),v=normalize(-input.pos),up=camVertical.xyz;
    if(dot(n,v)<0)n=-n;
    if(m.texture.x>.5){
        float3 dp1=ddx(input.pos),dp2=ddy(input.pos);float2 du1=ddx(uv),du2=ddy(uv);
        float determinant=du1.x*du2.y-du1.y*du2.x;
        if(abs(determinant)>1e-10){
            float3 t=(dp1*du2.y-dp2*du1.y)/determinant,b=(dp2*du1.x-dp1*du2.x)/determinant;
            t=normalize(t-n*dot(n,t));b=normalize(b-n*dot(n,b));
            float3 detail=cityNormal.Sample(citySampler,texcoord).xyz*2-1;
            detail.xy*=m.texture.y;n=normalize(t*detail.x+b*detail.y+n*detail.z);
        }
        // Normal-map variance widens highlights once detail falls below a pixel.
        rough=saturate(sqrt(rough*rough+.25*max(dot(ddx(n),ddx(n)),dot(ddy(n),ddy(n)))));
    }
    // Metric, derivative-filtered surface detail has no distance-dependent phase.
    if(role==3){float cells=max(CityLine(input.uv.x*8,.011),CityLine(input.uv.y*8,.011));albedo=lerp(albedo,float3(.24,.39,.47),cells*.60);rough=.22;}
    // Ceramic joints use the same height-derived normal/albedo/roughness tile.
    // Timber grain uses the same generated PBR sheet in every channel.
    if(role==7){float joint=max(CityLine(input.uv.x*1.2,.006),CityLine(input.uv.y*1.2,.006));albedo*=1-.22*joint;}
    if(role==12){float grain=frac(sin(dot(floor(input.local.xy*32),float2(12.9898,78.233)))*43758.5453);
        albedo*=1+(grain-.5)*.20*saturate(1-length(fwidth(input.local.xy))*12);}
    if(role==13){float joint=max(CityLine(uv.x*3.6,.025),CityLine(uv.y*3.6,.025));albedo*=1-.25*joint;}
    if(role==14){float joint=max(CityLine(uv.x*1.6,.012),CityLine(uv.y*1.6,.012));albedo*=1-.28*joint;}
    if(role==19){float brushing=sin(uv.y*440)*saturate(1-fwidth(uv.y*440));rough=saturate(rough+.07*brushing);}
    if(role==8){float variation=.90+.10*sin(input.local.x*19+input.local.y*13);albedo*=variation;}
    const float altitude=max(camVertical.w,0),mu=dot(up,lightDir.xyz),haze=RegionalGround(PlanetDirection(up));
    const float3 beam=SUN_ILLUMINANCE*SunTransmittance(altitude,mu,haze),sky=SkyIrradiance(altitude,mu,haze);
    const float nl=saturate(dot(n,lightDir.xyz)),nv=max(dot(n,v),.001);
    float3 halfv=normalize(lightDir.xyz+v);float nh=saturate(dot(n,halfv)),vh=saturate(dot(v,halfv));
    float alpha=rough*rough,a2=alpha*alpha,d=a2/(PI*pow(nh*nh*(a2-1)+1,2));
    float k=(rough+1)*(rough+1)/8;float visibility=1/max(4*(nl*(1-k)+k)*(nv*(1-k)+k),1e-5);
    float3 f0=lerp(.04,albedo,metal),f=f0+(1-f0)*pow(1-vh,5);
    float3 normalLocal=mul(float4(n,0),transpose(cityModel)).xyz;
    float shadow=CitySunVisibility(input.local,normalLocal);
    const bool roomGlass=role==15||role==16||role==17;
    const float3 diffuseColor=roomGlass?float3(0,0,0):albedo;
    const float3 direct=(diffuseColor*(1-metal)/PI+d*visibility*f)*beam*nl*shadow;
    const float hemisphere=.5+.5*dot(n,up);
    const float3 ground=(sky+beam*max(mu,0))*.16;
    float3 ambient=diffuseColor*(1-metal)/PI*(sky*hemisphere+ground*(1-hemisphere));
    float3 r=reflect(-v,n);float ru=dot(r,up);
    float3 env=lerp(ground/PI,sky/PI*(1.3-.65*saturate(ru)),smoothstep(-.08,.08,ru));
    float3 sheen=f0+(max(1-rough,f0)-f0)*pow(1-nv,5);
    ambient+=env*sheen*(1-.5*rough);
    // Visibility is baked against the master, reused by every LOD, and bounded.
    // Direct sunlight and emission are never multiplied by cavity darkness.
    ambient*=lerp(.40,1,saturate(input.ambient*orm.r));
    if(roomGlass){
        ambient+=CityInterior(input,v,n,sky,beam,mu,role)*lerp(.65,1,saturate(input.ambient));
    }
    // Architectural glazing is a recessed reflective exterior material in v1.
    // Emissive seams remain part of the asset, with the scene's physical exposure.
    // Exterior lighting dims in daylight. A thin luminous strip must not
    // dominate the entire distant building under the shared solar exposure.
    float trimRadiance=lerp(.30,.055,smoothstep(-.08,.18,mu));
    float3 emission=role==6?float3(1,.43,.10)*trimRadiance:0;
    if(role==20){
        float2 q=frac(uv);float rows=CityLine(q.y*7,.07);
        emission=float3(.18,.75,.66)*(.06+.09*rows);
    }
    if(role==22){
        float2 q=frac(uv),fw=max(fwidth(uv),.001);
        float screen=smoothstep(.18-fw.x,.18+fw.x,q.x)*(1-smoothstep(.82-fw.x,.82+fw.x,q.x))
            *smoothstep(.18-fw.y,.18+fw.y,q.y)*(1-smoothstep(.57-fw.y,.57+fw.y,q.y));
        emission=float3(.18,.75,.66)*.065*screen;
    }
    Output o;o.radiance=float4(direct+ambient+emission,length(input.pos)/1000);
    o.sunPart=float4(direct,0);return o;
}
