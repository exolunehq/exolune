#ifndef CITY_INTERIORS_HLSLI
#define CITY_INTERIORS_HLSLI
// Interior Mapping (van Dongen, CGI 2008): intersect a virtual room behind the
// window. This adds no interior geometry and never changes exterior depth.
float CityHash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
float CityRect(float2 p,float2 lo,float2 hi,float2 aa){
    float2 a=smoothstep(lo-aa,lo+aa,p)*(1-smoothstep(hi-aa,hi+aa,p));return a.x*a.y;
}
float3 CityInterior(CityPixel input,float3 v,float3 n,float3 sky,float3 beam,float mu,uint role){
    // Stored glTF/D3D texture V runs downwards. Virtual room coordinates must
    // run from floor to ceiling; otherwise the floor/ceiling hits are swapped.
    float2 uv=float2(input.uv.x,1-input.uv.y),cell=floor(uv),st=frac(uv);
    float3 dp1=ddx(input.pos),dp2=ddy(input.pos);float2 du1=ddx(uv),du2=ddy(uv);
    float determinant=du1.x*du2.y-du1.y*du2.x;
    if(abs(determinant)<1e-10)return 0;
    float3 tx=(dp1*du2.y-dp2*du1.y)/determinant;
    float3 ty=(dp2*du1.x-dp1*du2.x)/determinant;
    tx-=n*dot(n,tx);ty-=n*dot(n,ty);
    // The source UV span defines the metric room, including curved house
    // wings whose shared glass spans several mullions. Do not force every
    // aperture into an unrelated 3.2 m cubicle.
    const float width=clamp(length(tx),.6,16.0),height=clamp(length(ty),1.0,4.5);
    tx=normalize(tx);ty=normalize(ty);
    const float cabin=role==16?1:0;
    const float depth=lerp(4.0,2.4,cabin);
    float3 direction=float3(-dot(v,tx)/width,-dot(v,ty)/height,max(dot(v,n),.035)/depth);
    float2 edge=step(0,direction.xy);
    float2 times=(edge-st)/((edge*2-1)*max(abs(direction.xy),1e-5));
    float back=1/direction.z;
    float distance=min(back,min(times.x,times.y));
    float3 hit=float3(st,0)+direction*distance;
    float roomSeed=CityHash(cell+input.detail.x*13);
    float3 warm=float3(.64,.46,.28),plaster=float3(.64,.61,.51);
    float3 tint=lerp(float3(.12,.27,.24),warm,roomSeed);
    float2 wall=hit.xy,aa=max(fwidth(uv),.0015);
    float3 color=plaster;
    if(distance==times.y){
        wall=hit.xz;
        if(direction.y<0){
            float seam=max(CityLine(wall.x*7,.014),CityLine(wall.y*2,.010));
            color=warm*(.65-.15*seam);
        }else color=float3(.47,.36,.23);
    }else if(distance==times.x){
        wall=hit.zy;color=lerp(plaster*.70,tint,.26);
    }else{
        // Recessed storage, framed artwork, a low seat and soft curtains.
        float cabinet=CityRect(wall,float2(.08,.10),float2(.34,.88),aa);
        float shelving=CityLine(wall.y*7,.018);
        float books=CityLine(wall.x*29+floor(wall.y*7)*.3,.20);
        color=lerp(color,warm*(.42+.24*books)*(1-.3*shelving),cabinet);
        float art=CityRect(wall,float2(.54,.46),float2(.86,.79),aa);
        float inner=CityRect(wall,float2(.556,.48),float2(.844,.77),aa);
        color=lerp(color,float3(.13,.12,.09),art);
        color=lerp(color,lerp(float3(.14,.32,.27),float3(.66,.48,.23),smoothstep(.25,.6,wall.y+.15*sin(wall.x*13))),inner);
        float seat=CityRect(wall,float2(.46,.08),float2(.92,.29),aa);
        color=lerp(color,tint*.86,seat);
        if(cabin>.5){
            float seats=CityRect(float2(frac(wall.x*4),wall.y),float2(.10,.10),float2(.88,.58),aa*float2(4,1));
            color=lerp(plaster*.58,float3(.58,.31,.095),seats);
        }
    }
    float corner=min(min(hit.x,1-hit.x),min(hit.y,1-hit.y));
    float cavity=.54+.46*smoothstep(0,.18,corner);
    // Exolune uses a normalized solar illuminance of PI, not lux. Emission
    // must share those radiometric units; literal cd/m2 values burn out windows.
    // Indirect skylight stays separate from the renderer's solar-share buffer.
    float3 illumination=sky/PI*.32;
    float lit=smoothstep(.28,.65,roomSeed);
    float3 interior=color*illumination*cavity+color*float3(1,.70,.39)*lit*.055;
    float curtain=1-smoothstep(.05,.20,st.x);
    curtain*=.35+.65*smoothstep(.25,.75,roomSeed);
    interior=lerp(interior,warm*illumination*(.70+.10*cos(st.x*120)),curtain*.64);
    float mullion=max(CityLine(uv.x,.007),CityLine(uv.y,.008));
    // Fine room contents converge to a stable average instead of swimming.
    float filtered=saturate(1-max(fwidth(uv.x),fwidth(uv.y))*6);
    interior=lerp(float3(.33,.29,.22)*illumination,interior,filtered);
    float fresnel=.04+.96*pow(1-saturate(dot(n,v)),5);
    return interior*(1-fresnel)*(1-.92*mullion);
}
#endif
