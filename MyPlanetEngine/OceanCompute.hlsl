// Spectrum, FFT packing, and foam texture/update adapted from Noniv/web-ocean (MIT).
// Copyright (c) 2026 Maksymilian Dendura. Full notice: third_party/web-ocean/LICENSE.
#include "OceanUniform.hlsli"
cbuffer OceanPass : register(b2) { uint4 oceanPass; };
StructuredBuffer<float4> sourceA : register(t0);
StructuredBuffer<float4> sourceB : register(t1);
RWStructuredBuffer<float4> targetA : register(u0);
RWStructuredBuffer<float4> targetB : register(u1);
RWTexture2DArray<float4> output0 : register(u2);
RWTexture2DArray<float4> output1 : register(u3);
RWTexture2DArray<float4> output2 : register(u4);
Texture2DArray<float4> input0 : register(t2);
Texture2DArray<float4> input1 : register(t3);
Texture2DArray<float4> input2 : register(t4);
SamplerState oceanWrap : register(s0);
static const float OPI = 3.141592653589793;
uint OceanHash(uint v) {
    uint state=v*747796405u+2891336453u;
    uint word=((state>>((state>>28u)+4u))^state)*277803737u;
    return (word>>22u)^word;
}
float Rand01(uint s) { return ((OceanHash(s)>>8u)+0.5)/16777216.0; }
float2 Gaussian(uint seed) {
    float a=2.0*OPI*Rand01(seed*2u+18u+OceanHash(seed));
    return sqrt(-2.0*log(Rand01(seed*2u+17u)))*float2(cos(a),sin(a));
}
float2 Multiply(float2 a,float2 b) { return float2(a.x*b.x-a.y*b.y,a.x*b.y+a.y*b.x); }
float2 Imaginary(float2 v) { return float2(-v.y,v.x); }
float Omega(float k) { return sqrt(9.81*k+7.4e-5*k*k*k); }
float2 WaveVector(uint2 id,uint c) {
    int2 n=int2(id); n.x=id.x>=OCEAN_N/2?n.x-OCEAN_N:n.x; n.y=id.y>=OCEAN_N/2?n.y-OCEAN_N:n.y;
    return n*(2.0*OPI/oceanLengths[c]);
}
float WrapAngle(float a) { return a-2.0*OPI*floor((a+OPI)/(2.0*OPI)); }
float Jonswap(float w,float wp,float alpha,float gamma) {
    float sigma=w<=wp?0.07:0.09, d=(w-wp)/(sigma*wp), q=wp/w, q2=q*q;
    return alpha*9.81*9.81/pow(w,5.0)*exp(-1.25*q2*q2)*pow(gamma,exp(-0.5*d*d));
}
float Spreading(float theta,float w,float wp) {
    float r=w/wp, beta;
    if(r<0.95) beta=2.61*pow(r,1.3);
    else if(r<1.6) beta=2.28*pow(r,-1.3);
    else beta=pow(10.0,-0.4+0.8393*exp(-0.567*log(r*r)));
    float sh=1.0/cosh(clamp(beta*theta,-20.0,20.0));
    return beta/(2.0*tanh(beta*OPI))*sh*sh;
}
float Spectrum(float2 k) {
    float kl=length(k), w=Omega(kl), theta=atan2(k.y,k.x), sw=0.0;
    if(oceanWind.x>0.1) {
        float alpha=0.076*pow(oceanWind.x*oceanWind.x/(oceanWind.z*9.81),0.22);
        float wp=22.0*pow(9.81*9.81/(oceanWind.x*oceanWind.z),1.0/3.0);
        sw=Jonswap(w,wp,alpha,oceanWind.w)*Spreading(WrapAngle(theta-oceanWind.y),w,wp);
    }
    if(oceanSwell.x>0.001) {
        float ws=oceanSwell.z, hs4=oceanSwell.x*0.25;
        float alpha=hs4*hs4*5.0*pow(ws,4.0)/(9.81*9.81)*(1.0-0.287*log(6.0));
        float thetaS=WrapAngle(theta-oceanSwell.y);
        sw+=Jonswap(w,ws,alpha,6.0)*sqrt(oceanSwell.w+0.25)/(2.0*sqrt(OPI))
            *pow(abs(cos(thetaS*0.5)),2.0*oceanSwell.w);
    }
    return sw*exp(-kl*kl*oceanSettings.y*oceanSettings.y)
        *(9.81+3.0*7.4e-5*kl*kl)/(2.0*w*kl)*oceanTime.z;
}
float Amplitude(float2 k,uint c) {
    float kl=length(k);
    if(kl<1e-5 || kl<oceanKMin[c] || kl>=oceanKMax[c]) return 0.0;
    return sqrt(max(Spectrum(k),0.0))*(2.0*OPI/oceanLengths[c])*0.5;
}
[numthreads(16,16,1)]
void InitSpectrum(uint3 id:SV_DispatchThreadID) {
    uint c=id.z, index=(c*OCEAN_N+id.y)*OCEAN_N+id.x;
    if(id.x==OCEAN_N/2 || id.y==OCEAN_N/2) { targetA[index]=0.0; return; }
    float2 k=WaveVector(id.xy,c); uint2 mirror=(OCEAN_N-id.xy)%OCEAN_N;
    uint seed=(uint)oceanSettings.w*7919u+c*1000003u;
    float2 a=Gaussian(seed+id.y*OCEAN_N+id.x)*Amplitude(k,c);
    float2 b=Gaussian(seed+mirror.y*OCEAN_N+mirror.x)*Amplitude(-k,c);
    targetA[index]=float4(a,b.x,-b.y);
}
[numthreads(16,16,1)]
void Evolve(uint3 id:SV_DispatchThreadID) {
    uint c=id.z,index=(c*OCEAN_N+id.y)*OCEAN_N+id.x;
    float2 k=WaveVector(id.xy,c); float kl=length(k);
    if(kl<1e-5) { targetA[index]=0.0;targetB[index]=0.0;return; }
    float w0=2.0*OPI/oceanSettings.z, w=floor(Omega(kl)/w0)*w0;
    float ph=w*oceanTime.x; float2 e=float2(cos(ph),sin(ph));
    float4 init=sourceA[index];
    float2 h=Multiply(init.xy,float2(e.x,-e.y))+Multiply(init.zw,e), ih=Imaginary(h);
    // Short capillary ripples stay close to linear; they must not fold into whitecaps at every wrinkle.
    float chop=oceanSettings.x/(1.0+pow(kl/(2.0*OPI/0.4),2.0));
    float2 dx=ih*(chop*k.x/kl),dy=ih*(chop*k.y/kl);
    float2 jxy=h*(-chop*k.x*k.y/kl),sx=ih*k.x,sy=ih*k.y;
    float2 jxx=h*(-chop*k.x*k.x/kl),jyy=h*(-chop*k.y*k.y/kl);
    targetA[index]=float4(dx+Imaginary(dy),h+Imaginary(jxy));
    targetB[index]=float4(sx+Imaginary(sy),jxx+Imaginary(jyy));
}
groupshared float4 sharedA[OCEAN_N];
groupshared float4 sharedB[OCEAN_N];
void Butterflies(uint t) {
    [unroll]
    for(uint s=0;s<8;++s) {
        uint halfSize=1u<<s, pos=t&(halfSize-1u);
        uint i0=((t>>s)<<(s+1u))+pos,i1=i0+halfSize;
        float a=OPI*pos/halfSize;float2 w=float2(cos(a),sin(a));
        float4 a0=sharedA[i0],a1=sharedA[i1],b0=sharedB[i0],b1=sharedB[i1];
        float4 ta=float4(Multiply(a1.xy,w),Multiply(a1.zw,w));
        float4 tb=float4(Multiply(b1.xy,w),Multiply(b1.zw,w));
        sharedA[i0]=a0+ta;sharedA[i1]=a0-ta;sharedB[i0]=b0+tb;sharedB[i1]=b0-tb;
        GroupMemoryBarrierWithGroupSync();
    }
}
[numthreads(128,1,1)]
void FftRows(uint3 group:SV_GroupID,uint t:SV_GroupIndex) {
    uint base=(group.y*OCEAN_N+group.x)*OCEAN_N,e0=t,e1=t+128;
    sharedA[reversebits(e0)>>24u]=sourceA[base+e0];sharedA[reversebits(e1)>>24u]=sourceA[base+e1];
    sharedB[reversebits(e0)>>24u]=sourceB[base+e0];sharedB[reversebits(e1)>>24u]=sourceB[base+e1];
    GroupMemoryBarrierWithGroupSync();Butterflies(t);
    targetA[base+e0]=sharedA[e0];targetA[base+e1]=sharedA[e1];
    targetB[base+e0]=sharedB[e0];targetB[base+e1]=sharedB[e1];
}
void Emit(uint x,uint y,uint c,float4 a,float4 b) {
    output0[uint3(x,y,c)]=float4(a.x,a.z,a.y,a.w); // Dx, height, Dy, dDx/dy
    output1[uint3(x,y,c)]=b; // height slopes x,y, horizontal derivatives xx,yy
    // The spare fourth moment carries incident height energy through the same mip filter as displacement.
    output2[uint3(x,y,c)]=float4(b.x*b.x,b.y*b.y,b.x*b.y,a.z*a.z);
}
[numthreads(128,1,1)]
void FftColumns(uint3 group:SV_GroupID,uint t:SV_GroupIndex) {
    uint x=group.x,c=group.y,e0=t,e1=t+128;
    uint i0=(c*OCEAN_N+e0)*OCEAN_N+x,i1=(c*OCEAN_N+e1)*OCEAN_N+x;
    sharedA[reversebits(e0)>>24u]=sourceA[i0];sharedA[reversebits(e1)>>24u]=sourceA[i1];
    sharedB[reversebits(e0)>>24u]=sourceB[i0];sharedB[reversebits(e1)>>24u]=sourceB[i1];
    GroupMemoryBarrierWithGroupSync();Butterflies(t);
    Emit(x,e0,c,sharedA[e0],sharedB[e0]);Emit(x,e1,c,sharedA[e1],sharedB[e1]);
}
float4 Box0(uint3 id) {
    int4 p=int4(id.xy*2,id.z,0);
    return 0.25*(input0.Load(p)+input0.Load(p+int4(1,0,0,0))+input0.Load(p+int4(0,1,0,0))+input0.Load(p+int4(1,1,0,0)));
}
float4 Box1(uint3 id) {
    int4 p=int4(id.xy*2,id.z,0);
    return 0.25*(input1.Load(p)+input1.Load(p+int4(1,0,0,0))+input1.Load(p+int4(0,1,0,0))+input1.Load(p+int4(1,1,0,0)));
}
float4 Box2(uint3 id) {
    int4 p=int4(id.xy*2,id.z,0);
    return 0.25*(input2.Load(p)+input2.Load(p+int4(1,0,0,0))+input2.Load(p+int4(0,1,0,0))+input2.Load(p+int4(1,1,0,0)));
}
[numthreads(8,8,1)]
void MipWaves(uint3 id:SV_DispatchThreadID) {
    if(any(id.xy>=oceanPass.x)) return;
    output0[id]=Box0(id);output1[id]=Box1(id);output2[id]=Box2(id);
}
[numthreads(8,8,1)]
void MipSingle(uint3 id:SV_DispatchThreadID) {
    if(any(id.xy>=oceanPass.x)) return;output0[id]=Box0(id);
}
float2 HashGradient(int2 i) {
    uint h=OceanHash(asuint(i.x)*73856093u^OceanHash(asuint(i.y)*19349663u));
    float a=(h>>8u)*(2.0*OPI/16777216.0);return float2(cos(a),sin(a));
}
int2 WrapCell(int2 i,int per) { return (i%per+per)%per; }
float PeriodicNoise(float2 p,int per) {
    int2 i=(int2)floor(p);float2 f=frac(p),u=f*f*f*(f*(f*6.0-15.0)+10.0);
    float a=dot(HashGradient(WrapCell(i,per)),f);
    float b=dot(HashGradient(WrapCell(i+int2(1,0),per)),f-float2(1,0));
    float c=dot(HashGradient(WrapCell(i+int2(0,1),per)),f-float2(0,1));
    float d=dot(HashGradient(WrapCell(i+int2(1,1),per)),f-1.0);
    return lerp(lerp(a,b,u.x),lerp(c,d,u.x),u.y);
}
float PeriodicFbm(float2 p,int per,int octaves) {
    float s=0.0,a=0.5;
    [loop]for(int o=0;o<octaves;++o) { s+=a*PeriodicNoise(p,per);p*=2.0;per*=2;a*=0.5; }
    return s;
}
float2 Hash2(int2 i,uint salt) {
    uint h=OceanHash(asuint(i.x)*73856093u^OceanHash(asuint(i.y)*19349663u+salt));
    return float2(h>>8u,OceanHash(h+0x9e3779b9u)>>8u)/16777216.0;
}
float Bubbles(float2 uv,int period,uint salt,float rmin,float rmax) {
    int warpPeriod=max(period/2,1);
    float2 w=float2(PeriodicFbm(uv*warpPeriod,warpPeriod,3),PeriodicFbm(uv*warpPeriod+17.0,warpPeriod,3));
    float2 p=uv*period+w*0.9,fp=frac(p);int2 ip=(int2)floor(p);float v=9.0;
    [unroll]for(int j=-1;j<=1;++j) [unroll]for(int i=-1;i<=1;++i) {
        int2 o=int2(i,j),cell=WrapCell(ip+o,period);float2 hh=Hash2(cell,salt);
        float2 r=o+hh*0.9+0.05-fp;
        v=min(v,length(r)/lerp(rmin,rmax,Hash2(cell,salt+7u).x));
    }
    return smoothstep(0.8,1.25,v);
}
[numthreads(8,8,1)]
void CreatePores(uint3 id:SV_DispatchThreadID) {
    float2 uv=(id.xy+0.5)/512.0;
    float2 w1=float2(PeriodicFbm(uv*5.0,5,3),PeriodicFbm(uv*5.0+float2(3.7,9.1),5,3));
    float m1=smoothstep(-0.14,0.06,PeriodicFbm(uv*10.0+w1*1.4,10,5));
    float2 w2=float2(PeriodicFbm(uv*12.0+1.3,12,2),PeriodicFbm(uv*12.0+7.9,12,2));
    float m2=smoothstep(-0.16,0.04,PeriodicFbm(uv*27.0+w2*0.9,27,4));
    float b3=Bubbles(uv,29,37u,0.06,0.45),b4=Bubbles(uv,61,53u,0.05,0.42);
    float dens=PeriodicFbm(uv*4.0,4,5)*0.5+0.5,fineD=PeriodicFbm(uv*16.0,16,3)*0.5+0.5;
    float big=m1*(0.55+0.45*m2)*(0.75+0.25*b3);
    float fine=0.45+0.55*b3*(0.7+0.3*b4);
    float streak=PeriodicFbm(uv*float2(4.0,16.0),4,5)*0.5+0.5;
    output0[uint3(id.xy,0)]=saturate(float4(big*0.6+dens*0.4,fine*0.8+fineD*0.2,dens,streak));
}
int WrapIndex(int i,int lo) { return lo+((i-lo)%OCEAN_FOAM_N+OCEAN_FOAM_N)%OCEAN_FOAM_N; }
[numthreads(8,8,1)]
void UpdateFoam(uint3 id:SV_DispatchThreadID) {
    uint level=id.z;int4 snap=oceanFoamSnap[level];float texel=oceanFoamOrigin[level].z;
    int2 lo=snap.xy-OCEAN_FOAM_N/2;
    int2 g=int2(WrapIndex((int)id.x,lo.x),WrapIndex((int)id.y,lo.y));
    int2 oldLo=snap.zw-OCEAN_FOAM_N/2;
    bool valid=all(g>=oldLo)&&all(g<oldLo+OCEAN_FOAM_N)&&oceanRender.z<0.5;
    // Everything below is relative to the camera. Even the 25 cm clipmap stays precise on a whole planet.
    float2 p=(float2(g-snap.xy)+0.5)*texel-oceanFoamGrid[level].xy;
    float3 jac=0.0;
    [unroll]for(uint c=0;c<OCEAN_CASCADES;++c) {
        float lod=log2(max(texel/(oceanLengths[c]/OCEAN_N),1.0));
        if(lod<8.0) {
            float2 uv=p/oceanLengths[c]+oceanOrigin[c].xy;
            float4 d=input1.SampleLevel(oceanWrap,float3(uv,c),lod);
            float4 h=input0.SampleLevel(oceanWrap,float3(uv,c),lod);
            jac+=float3(d.z,h.w,d.w);
        }
    }
    float J=(1.0+jac.x)*(1.0+jac.z)-jac.y*jac.y;
    float2 drift=0.03*oceanWind.x*float2(cos(oceanWind.y),sin(oceanWind.y));
    float4 prev=0.0;
    if(valid) prev=input2.SampleLevel(oceanWrap,float3((id.xy+0.5-drift*oceanTime.y/texel)/OCEAN_FOAM_N,level),0);
    float inject=saturate((oceanFoamParams.x-J)*oceanFoamParams.y);
    float density=max(prev.x*exp(-oceanTime.y*oceanFoamParams.w),inject);
    density=min(density+inject*oceanTime.y*oceanFoamParams.z,1.6);
    float fresh=max(prev.y*exp(-oceanTime.y*1.6),inject);
    output0[id]=float4(density,fresh,J,1.0);
}

// Invert the horizontal map near the camera, as in the reference's water-height query.
// A single 16-byte readback piggybacks on the engine's existing frame fence.
[numthreads(1,1,1)]
void CameraHeight(uint3 id:SV_DispatchThreadID) {
    float2 rest=0.0;float3 d=0.0;
    [unroll]for(uint iteration=0;iteration<4;++iteration) {
        d=0.0;
        [unroll]for(uint c=0;c<OCEAN_CASCADES;++c) {
            float fade=smoothstep(0.0,max(1.0,0.05*oceanLengths[c]),max(-oceanRender.w,0.0));
            d+=fade*input0.SampleLevel(oceanWrap,float3(rest/oceanLengths[c]+oceanOrigin[c].xy,c),0.0).xyz;
        }
        rest=-d.xz;
    }
    targetA[0]=float4(d.y,d.x,d.z,0);
}
