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
#include "CityGenerated.hlsli"
struct Output {float4 radiance:SV_TARGET0;float4 sunPart:SV_TARGET1;};
Output PSMain(CityPixel input){
    uint2 pixel=uint2(input.position.xy);uint hash=pixel.x*0x8da6b343u^pixel.y*0xd8163841u;
    hash^=hash>>16;hash*=0x7feb352du;hash^=hash>>15;hash*=0x846ca68bu;hash^=hash>>16;
    uint flags=(uint)(taa.z+.5);uint phase=(flags&4096u)!=0?((flags>>3)&63u):0;
    const float noise=FoliageSequence(phase,1,hash);
    if(input.detail.z>.5){if(noise<abs(input.detail.y))discard;}else if(noise>=input.detail.y)discard;
    const CityMaterial m=cityMaterials[input.material];uint role=(uint)m.properties.w;
    // Model-space gradients stay outside branches: baked rooms filter with them.
    const float3 modelDx=ddx(input.model),modelDy=ddy(input.model);
    // The manufactured border owns the path edge. Interpolated distance from
    // boundary-only vertices is zero across a narrow polygon and must never
    // be used to discard its interior.
    float2 uv=input.uv;
    if(role==12||role==13||role==14)uv=input.local.xy*.5;
    const float3 texcoord=float3(uv,m.texture.x);
    const bool atlas=m.texture.w<-.5;
    const float4 colour=atlas?cityAtlasColor.Sample(citySampler,texcoord):cityColor.Sample(citySampler,texcoord);
    float3 albedo=m.color.rgb*input.detail.x*colour.rgb;
    float3 orm=atlas?cityAtlasOrm.Sample(citySampler,texcoord).rgb:cityOrm.Sample(citySampler,texcoord).rgb;
    float rough=max(.14,m.properties.x*orm.g),metal=m.properties.y*orm.b;
    float3 n=normalize(input.normal),v=normalize(-input.pos),up=camVertical.xyz;
    const bool back=dot(n,v)<0;
    if(back)n=-n;
    // A generated shell chooses a shared material per pixel from its class masks.
    const bool generated=role==24;
    CityShell shell=(CityShell)0;
    if(generated){
        shell=CityShellSurface(input,m,uv,normalize(input.modelNormal)*(back?-1:1),colour.a);
        albedo=shell.albedo*input.detail.x;orm=1;rough=max(.05,shell.rough);metal=shell.metal;
    }
    const float3 pane=n;
    if(m.texture.x>.5||atlas){
        float3 dp1=ddx(input.pos),dp2=ddy(input.pos);float2 du1=ddx(uv),du2=ddy(uv);
        float determinant=du1.x*du2.y-du1.y*du2.x;
        if(abs(determinant)>1e-10){
            float3 t=(dp1*du2.y-dp2*du1.y)/determinant,b=(dp2*du1.x-dp1*du2.x)/determinant;
            t=normalize(t-n*dot(n,t));b=normalize(b-n*dot(n,b));
            float3 detail;
            if(atlas){detail.xy=cityAtlasNormal.Sample(citySampler,texcoord)*2-1;detail.z=sqrt(saturate(1-dot(detail.xy,detail.xy)));}
            else detail=cityNormal.Sample(citySampler,texcoord).xyz*2-1;
            detail.xy*=m.texture.y*(generated?shell.baked:1);n=normalize(t*detail.x+b*detail.y+n*detail.z);
        }
        if(generated)n=normalize(n+mul(float4(CityRotate(shell.bump,input.eye.w),0),cityModel).xyz);
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
    if(role==26){
        // Coursed stone in metres: 0.32 m courses, staggered blocks of 0.45-1.1 m,
        // a tint per block and recessed mortar joints, box-filtered like every seam.
        const float2 q=uv*2;const float course=floor(q.y/.32);
        const float row=frac(sin(course*12.9898)*43758.5453);
        const float along=q.x/(.45+.65*row)+row*7.3;
        const float tint=frac(sin(dot(float2(floor(along),course),float2(12.9898,78.233)))*43758.5453);
        const float joint=max(CityLine(q.y/.32,.045),CityLine(along,.035));
        // A weathered, darker stone: built path sides and risers read as masonry, not as white render.
        albedo*=.62*(.84+.24*tint)*(1-.55*joint);rough=saturate(rough+.10*joint);
    }
    if(role==27){
        // Crop rows 0.75 m apart along the terrace (uv x) over tilled brown soil, darker in the furrows between them;
        // plants swell and thin along each row; each 40 m of field ripens on its own. Matte and box-filtered: at
        // distance a field keeps its mean colour, without the sky's sheen at grazing angles.
        const float2 q=uv*2;const float row=q.y/.75;const float lane=floor(row);
        const float plant=.5+.5*sin(q.x*5.3+lane*2.1)*sin(q.x*1.7+lane*.9);
        const float cover=CityLine(row,.27),furrow=CityLine(row+.5,.12);
        // Each 40 m of field has its own state: a quarter freshly tilled, the rest bright green to ripe gold, so a field
        // reads apart from the meadow around it.
        const float field=frac(sin(dot(floor(input.local.xy/40),float2(39.346,11.135)))*43758.5453);
        const float ripe=saturate((field-.45)*2.5);const float grown=field<.25?0:cover;
        const float3 leaf=lerp(float3(.055,.12,.022),float3(.30,.24,.07),ripe)*(.70+.6*plant);
        const float3 soil=float3(.095,.066,.042)*(.75+.5*dot(colour.rgb,float3(.3,.4,.3)))*(1-.35*furrow);
        albedo=lerp(soil,leaf,grown);rough=.95;
    }
    const float altitude=max(camVertical.w,0),mu=dot(up,lightDir.xyz),haze=RegionalGround(PlanetDirection(up));
    const float3 beam=SUN_ILLUMINANCE*SunTransmittance(altitude,mu,haze),sky=SkyIrradiance(altitude,mu,haze);
    const float nl=saturate(dot(n,lightDir.xyz)),nv=max(dot(n,v),.001);
    float3 halfv=normalize(lightDir.xyz+v);float nh=saturate(dot(n,halfv)),vh=saturate(dot(v,halfv));
    float alpha=rough*rough,a2=alpha*alpha,d=a2/(PI*pow(nh*nh*(a2-1)+1,2));
    float k=(rough+1)*(rough+1)/8;float visibility=1/max(4*(nl*(1-k)+k)*(nv*(1-k)+k),1e-5);
    float3 f0=lerp(.04,albedo,metal);
    // An insulated, coated unit reflects about three times a single pane.
    if(generated)f0=lerp(f0,.12,shell.glass);
    float3 f=f0+(1-f0)*pow(1-vh,5);
    float3 normalLocal=mul(float4(n,0),transpose(cityModel)).xyz;
    float shadow=CitySunVisibility(input.local,normalLocal);
    const bool roomGlass=role==15||role==16||role==17;
    const float3 diffuseColor=albedo*(1-(generated?shell.glass:roomGlass?1.:0.));
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
    if(generated&&shell.glass>0){
        // A room baked from the draft where the shell has one; the procedural room elsewhere.
        const float3 ray=normalize(input.model-input.eye.xyz);
        bool baked=false;float3 room=0;
        [branch]if(m.properties.z>.5)room=CityShellBaked(input.model,ray,modelDx,modelDy,m,input.detail.x,shell.tint,dot(pane,v),sky,baked);
        if(!baked)room=CityShellRoom(input.model,ray,m,shell.metres,input.detail.x,shell.tint,dot(pane,v),sky);
        ambient+=shell.glass*room*lerp(.65,1,saturate(input.ambient));
    }
    // Architectural glazing is a recessed reflective exterior material in v1.
    // Emissive seams remain part of the asset, with the scene's physical exposure.
    // Exterior lighting dims in daylight. A thin luminous strip must not
    // dominate the entire distant building under the shared solar exposure.
    float trimRadiance=lerp(.30,.055,smoothstep(-.08,.18,mu));
    // A generated light line is a lit diffuser: it still reads as lit in the shade of its own shell.
    float3 emission=role==6?float3(1,.43,.10)*trimRadiance:shell.emission*max(trimRadiance,.22);
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
