#include "PlanetFoliageCommon.hlsli"
#include "FoliageWind.hlsli"
#include "RootContact.hlsli"
StructuredBuffer<uint> meshOrder:register(t42);
struct ExtraVertex { float4 colour; float4 shoot; float4 leaf; float4 info; };
StructuredBuffer<ExtraVertex> vertexExtra:register(t43);
struct Vertex { float3 pos; float3 normal; float2 uv; float material; };
StructuredBuffer<Vertex> mesh : register(t30);
StructuredBuffer<float4> vertexVisibility : register(t39);
struct VOut { float4 position:SV_POSITION; float3 pos:POSITION; float3 normal:NORMAL; float2 uv:TEXCOORD0; nointerpolation float material:TEXCOORD1; nointerpolation uint instance:TEXCOORD2; float localHeight:TEXCOORD3; float4 visibility0:TEXCOORD4; float4 visibility1:TEXCOORD5; float rootBlend:TEXCOORD6; float4 tint:TEXCOORD7; nointerpolation float2 lodCoverage:TEXCOORD8; float3 barkPosition:TEXCOORD9; };
VOut VSMain(uint vertex:SV_VertexID, uint id:SV_InstanceID) {
    uint order=meshOrder[id],instance=order&0x7ffffu;
    float levelBlend=float((order>>19u)&511u)/511.0;
    ObjectInstance o=plants[instance]; Vertex v=mesh[vertex]; VOut r;
    // Extend only the bottom of the trunk to the placement's burial depth; the crown stays unchanged.
    // Material order belongs to the source asset; the catalogue identifies foliage.
    const bool trunk = (reserved & (1u << (uint)v.material)) == 0u;
    const bool rooted=species<SHRUB && (flags&32u)!=0u;
    // Authored roots and their trunk share one contact surface. The legacy
    // trunk extrusion otherwise pulls adjacent base vertices metres apart.
    const float burial = trunk && !rooted ? o.burial * (1.0 - smoothstep(0.0, 0.03, v.pos.y)) : 0.0;
    r.pos=ToWorld(v.pos,o)-PlantUp(o)*burial; r.normal=DirectionWorld(v.normal,o); r.rootBlend=0.0;
    float contactWeight=0.0;
    if (rooted && trunk) {
        const float3 up=PlantUp(o);
        float3 north=float3(faceX.y,faceY.y,faceZ.y); north-=up*dot(north,up);
        if (dot(north,north)<1e-10) north=float3(0,1,0)-up*up.y;
        north=normalize(north); const float3 east=cross(up,north);
        const float rootRadius=PlantRootRadius(o.size,species==BROADLEAF?o.axisY.y:1.0,o.seed);
        const float3 sourceScale=Scale(o);
        const float radial=length(v.pos.xz)/max(rootForm.z,1e-5);
        float3 delta=r.pos-o.pos, horizontal=delta-up*dot(up,delta);
        const float e=dot(horizontal,east), n=dot(horizontal,north);
        const uint contacts=asuint(o.albedo.z);
        const float flare=max(rootForm.y*sourceScale.y,1.5*rootForm.x*sourceScale.x);
        const float t=saturate((v.pos.y*sourceScale.y-flare)/max(2.0*flare,1e-5));
        const float fade=PlanetFoliageStoredWindShare(o);
        contactWeight=(1.0-t*t*(3.0-2.0*t))*fade;
        const float derivative=-3.0*t*(1.0-t)/max(flare,1e-5)*fade;
        const float correction=RootContactHeight(contacts,e,n,rootRadius)-min(0.25,0.025+0.025*rootRadius);
        r.pos+=up*contactWeight*correction;
        const float ge=abs(e)<rootRadius ? (0.5*(RootContactValue(contacts,0u,rootRadius)-RootContactValue(contacts,7u,rootRadius))
            +(RootContactValue(contacts,0u,rootRadius)+RootContactValue(contacts,7u,rootRadius))*e/rootRadius)/rootRadius : 0.0;
        const float gn=abs(n)<rootRadius ? (0.5*(RootContactValue(contacts,14u,rootRadius)-RootContactValue(contacts,21u,rootRadius))
            +(RootContactValue(contacts,14u,rootRadius)+RootContactValue(contacts,21u,rootRadius))*n/rootRadius)/rootRadius : 0.0;
        const float oldUp=dot(r.normal,up), newUp=oldUp/max(0.25,1.0+derivative*correction);
        r.normal=normalize(r.normal+up*(newUp-oldUp)-newUp*contactWeight*(east*ge+north*gn));
        r.rootBlend=smoothstep(0.30,0.95,radial)*contactWeight;
    }
    if (contactWeight<1.0) {
        const float3 anchored=r.pos,anchoredNormal=r.normal;
        if ((flags&64u)!=0u) {
            ExtraVertex extra=vertexExtra[vertex];
            AnimateFoliageWeighted(o,v.pos.y,(reserved&(1u<<(uint)v.material))!=0u,extra.shoot.w,extra.leaf.w,extra.info.x,r.pos,r.normal);
        } else AnimateFoliage(o,v.pos.y,(reserved&(1u<<(uint)v.material))!=0u,r.pos,r.normal);
        r.pos=lerp(r.pos,anchored,contactWeight);r.normal=normalize(lerp(r.normal,anchoredNormal,contactWeight));
    }
    r.barkPosition=v.pos*Scale(o); // rest position in metres; wind never slides the detail
    r.position=mul(float4(r.pos,1),viewProj);
    r.uv=v.uv; r.material=v.material; r.instance=instance; r.tint=(flags&64u)!=0u?vertexExtra[vertex].colour:float4(1,1,1,1); r.lodCoverage=(order&(1u<<28u))!=0u?float2(0,levelBlend):float2(levelBlend,1); r.localHeight=v.pos.y;
    r.visibility0=1; r.visibility1=float4(1,1,1,0);
    if ((flags&8u)!=0 && volumeParams.x>0) { r.visibility0=vertexVisibility[vertex*2]; r.visibility1=vertexVisibility[vertex*2+1]; }
    return r;
}
