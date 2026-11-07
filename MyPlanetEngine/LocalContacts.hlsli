// Bounded, current-frame contact lighting. AO removes indirect light only;
// short sun rays remove direct light only. No temporal history or scene colour
// is used to choose an occluder. This is a screen-space approximation.
#include "Planet.hlsli"

float3 ContactRay(float2 pixel,float2 dimensions) {
    const float2 ndc=(pixel+0.5)/dimensions*float2(2,-2)+float2(-1,1);
    return normalize(camForward.xyz+camRight.xyz*(ndc.x*camRight.w)+camUp.xyz*(ndc.y*camUp.w));
}

#ifndef CONTACT_RESOLVE
Texture2D<float4> contactScene:register(t0);
RWTexture2D<float2> contactOutput:register(u2);

float3 ContactPoint(int2 pixel,uint2 dimensions) {
    pixel=clamp(pixel,int2(0,0),int2(dimensions)-1);
    return ContactRay(pixel,dimensions)*(abs(contactScene.Load(int3(pixel,0)).a)*1000.0);
}

[numthreads(8,8,1)]
void CSMain(uint2 id:SV_DispatchThreadID) {
    uint width,height;contactScene.GetDimensions(width,height);
    const uint2 dimensions=uint2(width,height);
    if (any(id>=(dimensions+1)/2)) return;
    const int2 pixel=min(int2(id*2+1),int2(dimensions)-1);
    contactOutput[id]=1.0;
    const float signedDepth=contactScene.Load(int3(pixel,0)).a;
    const float depth=signedDepth*1000.0;
    if (depth<=0.1 || depth>=192.0) return; // sky, water and distant scene
    const float3 p=ContactRay(pixel,dimensions)*depth;
    const float3 left=ContactPoint(pixel-int2(2,0),dimensions)-p,right=ContactPoint(pixel+int2(2,0),dimensions)-p;
    const float3 above=ContactPoint(pixel-int2(0,2),dimensions)-p,below=ContactPoint(pixel+int2(0,2),dimensions)-p;
    const float3 dx=dot(left,left)<dot(right,right)?-left:right;
    const float3 dy=dot(above,above)<dot(below,below)?-above:below;
    float3 normal=cross(dy,dx);const float length2=dot(normal,normal);
    // Thin alpha silhouettes with unrelated depth neighbours cannot establish
    // a surface normal; keep them neutral instead of making a black fringe.
    if (length2<1e-12 || max(length(dx),length(dy))>max(0.10,0.08*depth)) return;
    normal*=rsqrt(length2);if (dot(normal,p)>0.0) normal=-normal;
    const float radius=1.2;
    const float pixelRadius=min(radius/max(depth*taa.w,1e-4),128.0);
    const float2 directions[8]={float2(1,0),float2(.7071,.7071),float2(0,1),float2(-.7071,.7071),
        float2(-1,0),float2(-.7071,-.7071),float2(0,-1),float2(.7071,-.7071)};
    float obscurance=0.0;
    [unroll] for (uint direction=0;direction<8;++direction) {
        float horizon=0.0;
        [unroll] for (uint step=0;step<3;++step) {
            const float fraction=(float(step)+1.0)/3.0;
            const int2 samplePixel=pixel+int2(round(directions[direction]*max(2.0,pixelRadius*fraction*fraction)));
            if (any(samplePixel<0) || any(samplePixel>=int2(dimensions))) continue;
            const float sampleDepth=contactScene.Load(int3(samplePixel,0)).a*1000.0;
            if (sampleDepth<=0.1) continue;
            const float3 delta=ContactRay(samplePixel,dimensions)*sampleDepth-p;
            const float distance2=dot(delta,delta);
            if (distance2<1e-6 || distance2>radius*radius) continue;
            const float angle=max(dot(normal,delta)*rsqrt(distance2)-0.05,0.0);
            horizon=max(horizon,angle*sqrt(saturate(1.0-distance2/(radius*radius))));
        }
        obscurance+=horizon*horizon;
    }
    float ao=saturate(1.0-0.85*obscurance/8.0),sunVisibility=1.0;
    const float bias=max(0.015,depth*taa.w*0.5);
    [unroll] for (uint step=0;step<6;++step) {
        const float distance=0.04*exp2(float(step));
        const float3 probe=p+normal*bias+lightDir.xyz*distance;
        const float4 clip=mul(float4(probe,1),viewProj);
        const float2 uv=clip.xy/max(clip.w,1e-6)*float2(0.5,-0.5)+0.5;
        if (clip.w<=0 || any(uv<=0) || any(uv>=1)) continue;
        const int2 samplePixel=int2(uv*dimensions);
        const float sceneDepth=contactScene.Load(int3(samplePixel,0)).a*1000.0;
        if (sceneDepth<=0.1) continue;
        const float delta=length(probe)-sceneDepth,thickness=0.04+distance*0.06;
        const float blocked=smoothstep(bias,bias+0.02,delta)*(1.0-smoothstep(thickness,thickness*2.0,delta));
        const float border=min(min(uv.x,1-uv.x)*width,min(uv.y,1-uv.y)*height);
        sunVisibility=min(sunVisibility,1.0-blocked*saturate(border/12.0));
    }
    const float fade=1.0-smoothstep(96.0,192.0,depth);
    contactOutput[id]=lerp(1.0,float2(ao,sunVisibility),fade);
}
#else
Texture2D<float2> contactInput:register(t1);
RWTexture2D<float4> contactHdr:register(u0);
RWTexture2D<float4> contactSun:register(u1);

[numthreads(8,8,1)]
void CSMain(uint2 pixel:SV_DispatchThreadID) {
    uint width,height;contactHdr.GetDimensions(width,height);
    if (pixel.x>=width || pixel.y>=height) return;
    const float4 scene=contactHdr[pixel];const float depth=scene.a*1000.0;
    if (depth<=0.1 || depth>=192.0) return;
    uint cw,ch;contactInput.GetDimensions(cw,ch);
    const float2 uv=(float2(pixel)+0.5)*0.5-0.5;
    const int2 base=int2(floor(uv));const float2 fraction=frac(uv);
    float2 visibility=0;float total=0;
    [unroll] for (uint y=0;y<2;++y) [unroll] for (uint x=0;x<2;++x) {
        const int2 q=clamp(base+int2(x,y),int2(0,0),int2(cw,ch)-1);
        const uint2 sourcePixel=min(uint2(q)*2+1,uint2(width,height)-1);
        // Alpha is immutable in this pass. Threads read neighbours' distance
        // only; each thread alone reads and writes its own RGB values.
        const float neighbour=contactHdr[sourcePixel].a*1000.0;
        const float spatial=(x?fraction.x:1-fraction.x)*(y?fraction.y:1-fraction.y);
        const float weight=spatial*exp2(-abs(neighbour-depth)/max(0.03,0.015*depth));
        visibility+=contactInput.Load(int3(q,0))*weight;total+=weight;
    }
    visibility=total>1e-5?saturate(visibility/total):1.0;
    const float4 solar=contactSun[pixel];
    const float3 direct=min(max(solar.rgb,0.0),max(scene.rgb,0.0));
    const float3 indirect=max(scene.rgb-direct,0.0);
    contactHdr[pixel]=float4(indirect*visibility.x+direct*visibility.y,scene.a);
    contactSun[pixel]=float4(solar.rgb*visibility.y,solar.a);
}
#endif
