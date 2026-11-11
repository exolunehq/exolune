#ifndef CITY_GENERATED_HLSLI
#define CITY_GENERATED_HLSLI
// Generated shells. The draft's atlas names one material class per texel and
// packed masks store the signed distance to each class border: R timber,
// G glazing, B light, A solar, then cladding in the alpha of the colour map;
// the shell is what remains. Each class renders with a shared city material
// in model space, so borders and texture detail do not depend on the atlas
// resolution (tools/city/surface_classes.py).
static const float CITY_MASK_TEXELS=8;   // The masks span +/- 4 texels: one texel moves the value by 1/8.
static const float CITY_FRAME=.06;       // Glazing border frame, metres.
static const float CITY_MULLION=.05;     // Mullion width, metres.
static const float CITY_SLAB=.32;        // Floor edge behind the glazing, metres.
struct CityShell {
    float3 albedo;float rough;float metal;
    float3 bump;     // Model-space perturbation of the normal, from the class detail.
    float baked;     // Strength of the atlas normal map.
    float3 emission;float glass;float3 tint;
    float metres;    // Surface metres per pixel.
};
void CityShellProject(float layer,float2 uv,float2 dx,float2 dy,float3 axisU,float3 axisV,float weight,
                      inout float3 tone,inout float3 bump,inout float rough){
    [branch]if(weight<.004)return;
    const float3 at=float3(uv,layer);
    const float3 n=cityNormal.SampleGrad(citySampler,at,dx,dy).xyz*2-1;
    tone+=weight*cityColor.SampleGrad(citySampler,at,dx,dy).rgb;
    // The detail normal derives from a height: its slope lies along the projected axes.
    bump+=weight*(axisU*n.x+axisV*n.y);
    rough+=weight*cityOrm.SampleGrad(citySampler,at,dx,dy).g;
}
void CityShellOpaque(inout CityShell s,CityMaterial k,float weight,float3 p,float3 dpx,float3 dpy,float3 facing){
    [branch]if(weight<=0)return;
    float3 tone=1,bump=0;float rough=1;
    [branch]if(k.texture.x>.5){
        const float3 q=p/k.texture.z,qx=dpx/k.texture.z,qy=dpy/k.texture.z;
        tone=0;rough=0;
        // Boards stand upright on walls and run along X on floors and soffits.
        CityShellProject(k.texture.x,q.zy,qx.zy,qy.zy,float3(0,0,1),float3(0,1,0),facing.x,tone,bump,rough);
        CityShellProject(k.texture.x,q.zx,qx.zx,qy.zx,float3(0,0,1),float3(1,0,0),facing.y,tone,bump,rough);
        CityShellProject(k.texture.x,q.xy,qx.xy,qy.xy,float3(1,0,0),float3(0,1,0),facing.z,tone,bump,rough);
    }
    s.albedo+=weight*k.color.rgb*tone;s.rough+=weight*k.properties.x*rough;s.metal+=weight*k.properties.y;
    s.bump+=weight*k.texture.y*bump;s.baked+=weight*k.texture.w;
}
// `m` is the shell material: color = mullion spacing, storey height, floor datum (metres);
// texture = atlas layer, normal strength, first class material, class count.
CityShell CityShellSurface(CityPixel input,CityMaterial m,float2 uv,float3 normal,float cladding){
    uint width,height,layers,levels;cityOrm.GetDimensions(0,width,height,layers,levels);
    const float2 dux=ddx(uv)*width,duy=ddy(uv)*width;
    const float3 p=input.model,dpx=ddx(p),dpy=ddy(p);
    const float texels=sqrt(.5*(dot(dux,dux)+dot(duy,duy)));   // Atlas texels per pixel.
    const float metres=sqrt(.5*(dot(dpx,dpx)+dot(dpy,dpy)));   // Surface metres per pixel.
    const float4 mask=cityOrm.Sample(citySampler,float3(uv,m.texture.x));
    // One pixel of antialiasing on each border at any magnification; plain coverage once minified.
    const float edge=clamp(texels/CITY_MASK_TEXELS,2./255,.5);
    float4 w=saturate((mask-.5)/edge+.5);
    float clad=saturate((cladding-.5)/edge+.5);
    float shell=saturate(1-dot(w,1)-clad);
    const float total=shell+dot(w,1)+clad;shell/=total;w/=total;clad/=total;
    float3 facing=pow(abs(normal),6);facing/=facing.x+facing.y+facing.z;
    const uint first=(uint)m.texture.z;
    CityShell s=(CityShell)0;s.tint=1;s.metres=metres;
    CityShellOpaque(s,cityMaterials[first],shell,p,dpx,dpy,facing);
    CityShellOpaque(s,cityMaterials[first+1],w.x,p,dpx,dpy,facing);
    CityShellOpaque(s,cityMaterials[first+5],clad,p,dpx,dpy,facing);
    // The remaining classes are arithmetic only. Their screen derivatives stay
    // outside dynamic branches, so borders between classes filter correctly.
    {
        const CityMaterial k=cityMaterials[first+3];
        s.albedo+=w.z*k.color.rgb;s.rough+=w.z*k.properties.x;s.emission+=w.z*k.color.rgb;
    }
    {
        const CityMaterial k=cityMaterials[first+4];
        // Photovoltaic cells and module frames follow the plan: the skin faces the sky.
        const float cells=max(CityLine(p.x/.166,.012),CityLine(p.y/.166,.012));
        const float modules=max(CityLine(p.x/.996,.006),CityLine(p.y/1.66,.004));
        float3 colour=lerp(k.color.rgb,float3(.24,.39,.47),cells*.45);
        colour=lerp(colour,float3(.45,.47,.48),modules*.8);
        s.albedo+=w.w*colour;s.rough+=w.w*lerp(k.properties.x,.4,modules);s.metal+=w.w*k.properties.y;s.baked+=w.w*k.texture.w;
    }
    {
        const CityMaterial k=cityMaterials[first+2];
        // Metric depth inside the glazing border, from the mask's known slope.
        const float inside=(mask.y-.5)*CITY_MASK_TEXELS*metres/max(texels,1e-6);
        float frame=(1-smoothstep(CITY_FRAME-metres,CITY_FRAME+metres,inside))*saturate(CITY_FRAME/max(metres,1e-6));
        // Mullions stand on the structural grid. Each family keeps its width on
        // the pane and fades where the pane runs along its planes.
        const float2 across=abs(normal.xy)/max(length(normal.xy),.2);
        const float halfWidth=.5*CITY_MULLION/m.color.x;
        frame=max(frame,CityLine(p.x/m.color.x,halfWidth*smoothstep(.64,.77,across.y)));
        frame=max(frame,CityLine(p.y/m.color.x,halfWidth*smoothstep(.64,.77,across.x)));
        frame=max(frame,CityLine((p.z-m.color.z)/m.color.y,.5*CITY_SLAB/m.color.y));
        const float metalwork=w.y*saturate(frame),pane=w.y-metalwork;
        s.glass+=pane;s.tint=k.color.rgb;
        s.albedo+=pane*k.color.rgb+metalwork*float3(.035,.04,.04);
        s.rough+=pane*k.properties.x+metalwork*.42;s.metal+=metalwork*.85;
    }
    return s;
}
// Interior mapping in model space (van Dongen, CGI 2008): rooms are boxes on
// the structural grid, three bays wide and one storey high. Curved and
// inclined panes need no parameterisation.
float3 CityShellRoom(float3 p,float3 ray,CityMaterial m,float metres,float seed,float3 tint,float facing,float3 sky){
    const float3 room=float3(3*m.color.x,3*m.color.x,m.color.y);
    // Enter just behind the pane: a wall never starts in the glass itself.
    const float3 q=(p-float3(0,0,m.color.z)+ray*.04)/room,cell=floor(q),st=q-cell;
    const float3 d=ray/room,edge=step(0,d);
    const float3 times=(edge-st)/(d+(edge*2-1)*1e-6);
    const float distance=min(times.x,min(times.y,times.z));
    const float3 hit=st+d*distance;
    const float roomSeed=CityHash(cell.xy+cell.z*17+seed*13);
    const float3 warm=float3(.64,.46,.28),plaster=float3(.64,.61,.51);
    const float3 hue=lerp(float3(.12,.27,.24),warm,roomSeed);
    float3 colour;
    if(distance==times.z){
        if(d.z<0){
            const float seam=max(CityLine(hit.x*room.x/.14,.02),CityLine(hit.y*room.y/1.9,.004));
            colour=warm*(.62-.14*seam);
        }else{
            const float2 lamp=abs(hit.xy-.5);
            colour=lerp(float3(.52,.50,.44),float3(1.6,1.3,.9),step(max(lamp.x,lamp.y*3),.16)*smoothstep(.28,.65,roomSeed));
        }
    }else{
        const float2 wall=float2(distance==times.x?hit.y:hit.x,hit.z);
        const float2 aa=max(float2(metres/room.x,metres/room.z),.0015);
        colour=lerp(plaster,hue,.22);
        // Low storage, a framed picture and a doorway: enough to read depth and scale.
        colour=lerp(colour,warm*.50,CityRect(wall,float2(.08,.0),float2(.40,.30),aa));
        colour=lerp(colour,float3(.13,.12,.09),CityRect(wall,float2(.50,.45),float2(.78,.76),aa));
        colour=lerp(colour,lerp(float3(.14,.32,.27),float3(.66,.48,.23),roomSeed),CityRect(wall,float2(.52,.48),float2(.76,.73),aa));
        colour=lerp(colour,plaster*.22,CityRect(wall,float2(.84,.0),float2(.97,.68),aa));
    }
    const float corner=min(min(hit.x,1-hit.x),min(hit.y,1-hit.y));
    const float depth=length(d*distance*room);
    // Daylight enters through the tinted pane and fades with depth. A lit room adds a warm lamp,
    // which keeps its colour: the city reads warm at dusk, as its other windows do.
    const float3 body=tint/max(max(tint.r,tint.g),max(tint.b,1e-4));
    float3 interior=colour*(sky/PI*.36*exp(-depth*.16)*(.55+.45*smoothstep(0,.18,corner))*body
        +float3(1,.70,.39)*smoothstep(.28,.65,roomSeed)*.040);
    // Fine room contents converge to a stable average instead of swimming.
    interior=lerp(float3(.33,.29,.22)*sky/PI*.25*body,interior,saturate(1-metres/room.x*6));
    const float fresnel=.12+.88*pow(1-saturate(facing),5);
    return interior*(1-fresnel)*.6;
}
// A room baked from the draft behind its window (tools/city/interior_bake.py).
// The shell names `count` records from `first` (m.color.w, m.properties.z). A
// record is an oriented box: color = window origin and box depth (metres, model
// space), properties.xyz = width axis, texture = layer and height axis; u x v
// faces outwards. Its colour layer holds the room seen from the window: RGB
// colour, A the first surface's depth over the box depth. A height-field march
// gives parallax without interior geometry; `found` stays false outside a window.
static const float CITY_BAKED_MIN_STEPS=12,CITY_BAKED_MAX_STEPS=96;
// Sixteen-bit depth in the normal layer: high byte in R, low byte in G. Eight bits
// step by 2.7 cm over a 7 m room, which a grazing ray turns into visible terraces.
float CityBakedDepth(float3 s,float layer,float2 gx,float2 gy){
    return dot(cityNormal.SampleGrad(citySampler,float3(saturate(s.x),1-saturate(s.y),layer),gx,gy).rg,float2(65280,255)/65535);
}
float3 CityShellBaked(float3 p,float3 ray,float3 dpx,float3 dpy,CityMaterial m,float seed,float3 tint,float facing,float3 sky,out bool found){
    found=false;
    const uint first=(uint)m.color.w,count=min((uint)m.properties.z,4u);
    [loop]for(uint i=0;i<count;++i){
        const CityMaterial k=cityMaterials[first+i];
        const float3 U=k.properties.xyz,V=k.texture.yzw,N=normalize(cross(U,V));
        const float uu=dot(U,U),vv=dot(V,V),depth=k.color.w,layer=k.texture.x;
        const float3 w=p-k.color.xyz;
        float3 a=float3(dot(w,U)/uu,dot(w,V)/vv,-dot(w,N)/depth);
        const float3 d=float3(dot(ray,U)/uu,dot(ray,V)/vv,-dot(ray,N)/depth);
        if(any(a.xy<0)||any(a.xy>1)||d.z<=1e-4)continue;
        found=true;
        // Window coordinates are linear in the model position: their screen gradients filter every sample.
        const float2 gx=float2(dot(dpx,U)/uu,-dot(dpx,V)/vv),gy=float2(dot(dpy,U)/uu,-dot(dpy,V)/vv);
        // A pane in front of the window plane enters the room at the plane.
        if(a.z<0)a+=d*(-a.z/d.z);
        // A grazing ray crosses more of the window per unit of depth: it takes more steps.
        const float steps=lerp(CITY_BAKED_MIN_STEPS,CITY_BAKED_MAX_STEPS,saturate(1-abs(dot(ray,N))));
        const float3 stride=d*((1-a.z)/d.z/steps);
        float3 b=a;float ha=CityBakedDepth(a,layer,gx,gy),hb=ha;bool side=false;
        [loop]for(float j=0;j<steps&&a.z<ha;++j){
            b=a+stride;
            // Leaving through a side, the floor or the ceiling: the box wall stops the ray.
            if(any(b.xy<0)||any(b.xy>1)){side=true;break;}
            hb=CityBakedDepth(b,layer,gx,gy);
            if(b.z>=hb)break;
            a=b;ha=hb;
        }
        // The surface crosses the ray between the last two samples: bisect, then intersect linearly.
        [unroll]for(uint r=0;r<4;++r){
            const float3 c=(a+b)*.5;const float hc=CityBakedDepth(c,layer,gx,gy);
            if(side||a.z>=ha)break;
            if(c.z>=hc){b=c;hb=hc;}else{a=c;ha=hc;}
        }
        const float above=ha-a.z,below=b.z-hb;
        const float3 hit=side?b:lerp(a,b,saturate(above/max(above+below,1e-5)));
        // A side wall, the floor or the ceiling beyond the bake: its averaged edge colour, in shade.
        const float3 colour=side?cityColor.SampleLevel(citySampler,float3(saturate(hit.x),1-saturate(hit.y),layer),5).rgb*.6
            :cityColor.SampleGrad(citySampler,float3(saturate(hit.x),1-saturate(hit.y),layer),gx,gy).rgb;
        // The draft painted its own room light: daylight through the tinted pane scales it,
        // fading gently with depth, and the room keeps a warm lamp that dominates at dusk.
        const float3 body=tint/max(max(tint.r,tint.g),max(tint.b,1e-4));
        const float lamp=.5+.5*smoothstep(.28,.65,CityHash(float2(seed*13,i)));
        const float3 interior=colour*(sky/PI*.9*exp(-hit.z*depth*.05)*body+float3(1,.70,.39)*lamp*.10);
        const float fresnel=.12+.88*pow(1-saturate(facing),5);
        return interior*(1-fresnel)*.6;
    }
    return 0;
}
#endif
