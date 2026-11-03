#define PLANET_FOLIAGE_IMPOSTOR // l'éclairage par la dispersion des feuilles (OutputVolume)
#include "PlanetFoliageCommon.hlsli"
struct VOut {
    // Centroïde sans perspective : exigé avec SV_DepthLessEqual ; sans multiéchantillonnage, le centre du pixel, comme avant.
    noperspective centroid float4 position : SV_POSITION; float3 ray : TEXCOORD0; nointerpolation uint instance : TEXCOORD1;
    nointerpolation float4 azTrig:TEXCOORD2; nointerpolation float4 elTrig:TEXCOORD3;
    nointerpolation uint4 viewIndex:TEXCOORD4; nointerpolation float2 viewBlend:TEXCOORD5;
};
Texture2DArray<float4> impostorColour : register(t32);
Texture2DArray<float4> impostorNormalDepth : register(t33);
Texture2DArray<float4> impostorVisibility0 : register(t37);
Texture2DArray<float4> impostorVisibility1 : register(t38);
struct ViewSample { float4 color; float3 location; float lod; float t; float denominator; };
void SampleColour(uint az, uint el, float sa, float ca, float se, float ce, float3 origin, float3 ray, out ViewSample sample) {
    float3 v = float3(sa*ce, se, ca*ce);
    float3 right = float3(ca, 0, -sa);
    float3 up = float3(-sa*se, ce, -ca*se);
    float3 centre = float3(0, 0.5, 0);
    float denominator = dot(ray, v);
    float t = abs(denominator) > 1e-6 ? dot(centre - origin, v) / denominator : -1;
    float3 p = origin + ray * t - centre;
    float2 uv = float2(dot(p, right), -dot(p, up)) / (2 * radius) + 0.5;
    float2 dx = ddx(uv) * float2(width, height), dy = ddy(uv) * float2(width, height);
    float lod = clamp(log2(max(max(length(dx), length(dy)), 1.0)), 0.0, log2((float)max(width,height)));
    sample.color=0; sample.location=float3(uv, el * viewsX + az);
    sample.lod=lod; sample.t=t; sample.denominator=denominator;
    if (t <= 0 || any(uv < 0) || any(uv >= 1)) return;
    float4 accum = impostorColour.SampleLevel(linearClamp, sample.location, lod);
    sample.color.a = accum.a;
    if (accum.a > 1e-6) {
        sample.color.rgb = accum.rgb / accum.a;
    }
}
void SampleAux(ViewSample sample, out float3 normal, out float distance, out float4 vis0, out float4 vis1) {
    normal=0; distance=0; vis0=0; vis1=0;
    if (sample.color.a > 1e-6) {
        float4 nd=impostorNormalDepth.SampleLevel(linearClamp,sample.location,sample.lod);
        normal=nd.xyz/sample.color.a;
        distance=sample.t+(nd.w/sample.color.a)/sample.denominator;
        if ((flags&8u)!=0 && volumeParams.x>0) {
            vis0=impostorVisibility0.SampleLevel(linearClamp,sample.location,sample.lod)/sample.color.a;
            vis1=impostorVisibility1.SampleLevel(linearClamp,sample.location,sample.lod)/sample.color.a;
        }
    }
}
Result PSMain(VOut input) {
    ObjectInstance i = plants[input.instance]; clip(i.size - 1e-4); Transition(input.position.xy, i, false);
    float3 origin = ToLocalVector(-i.pos, i), ray = normalize(ToLocalVector(input.ray, i));
    uint a0=input.viewIndex.x, a1=input.viewIndex.y, e0=input.viewIndex.z, e1=input.viewIndex.w;
    float2 f = input.viewBlend;
    ViewSample samples[4];
    SampleColour(a0,e0,input.azTrig.x,input.azTrig.y,input.elTrig.x,input.elTrig.y,origin,ray,samples[0]);
    SampleColour(a1,e0,input.azTrig.z,input.azTrig.w,input.elTrig.x,input.elTrig.y,origin,ray,samples[1]);
    SampleColour(a0,e1,input.azTrig.x,input.azTrig.y,input.elTrig.z,input.elTrig.w,origin,ray,samples[2]);
    SampleColour(a1,e1,input.azTrig.z,input.azTrig.w,input.elTrig.z,input.elTrig.w,origin,ray,samples[3]);
    float4 c[4]={samples[0].color,samples[1].color,samples[2].color,samples[3].color};
    float4 w = float4((1-f.x)*(1-f.y), f.x*(1-f.y), (1-f.x)*f.y, f.x*f.y);
    float4 covered = w * float4(c[0].a,c[1].a,c[2].a,c[3].a);
    float alpha = dot(covered, 1.0); clip(alpha - FOLIAGE_PROXY_ALPHA_MIN);
    // Une vue proche peut soutenir une silhouette absente des autres vues.
    // Son influence s'annule continûment lorsque son poids tend vers zéro.
    float4 support=float4(c[0].a,c[1].a,c[2].a,c[3].a)*saturate(2.0*w);
    float coverage=max(alpha,max(max(support.x,support.y),max(support.z,support.w)));
    // Filtered mip alpha is area coverage. Accumulate it instead of cutting
    // every distant crown into a hard half-alpha silhouette.
    ClipFoliageCoverage(input.position.xy,coverage,i);
    float4 vis0[4], vis1[4]; float3 n[4]; float d[4];
    SampleAux(samples[0],n[0],d[0],vis0[0],vis1[0]); SampleAux(samples[1],n[1],d[1],vis0[1],vis1[1]);
    SampleAux(samples[2],n[2],d[2],vis0[2],vis1[2]); SampleAux(samples[3],n[3],d[3],vis0[3],vis1[3]);
    float3 colour = (c[0].rgb*covered.x+c[1].rgb*covered.y+c[2].rgb*covered.z+c[3].rgb*covered.w) / alpha;
    float3 norm = n[0]*covered.x+n[1]*covered.y+n[2]*covered.z+n[3]*covered.w;
    float distance = dot(covered, float4(d[0],d[1],d[2],d[3])) / alpha;
    float3 surfacePos = ToWorld(origin + ray * distance, i);
    float4 visibility0=(vis0[0]*covered.x+vis0[1]*covered.y+vis0[2]*covered.z+vis0[3]*covered.w)/alpha;
    float4 visibility1=(vis1[0]*covered.x+vis1[1]*covered.y+vis1[2]*covered.z+vis1[3]*covered.w)/alpha;
    // La cohérence des normales des feuilles couvertes : 1 pour une seule feuille, vers 0 quand elles se dispersent.
    const float coherence=saturate(length(norm)/alpha);
    return OutputVolume(colour, DirectionWorld(norm, i), surfacePos, i, (origin + ray * distance).y, false,1,1,0,visibility0,visibility1,coherence);
}
// La profondeur reconstruite, jamais plus proche que celle du quad (PlanetFoliageProxyVertex.hlsl) : le rejet précoce.
struct ConservativeResult { float4 colour : SV_TARGET0; float4 solar : SV_TARGET1; float depth : SV_DepthLessEqual; };
ConservativeResult PSConservative(VOut input) {
    const Result r = PSMain(input);
    ConservativeResult c; c.colour=r.colour; c.solar=r.solar; c.depth=r.depth; return c;
}
