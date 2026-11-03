// Independent geometric contacts and storage checks; no renderer or performance benchmark.
#include "../../MyPlanetEngine/RootContact.hlsli"
#include "../../MyPlanetEngine/CanopyLighting.hlsli"
#include "../../MyPlanetEngine/FoliageCatalog.hlsli"
#include "../../MyPlanetEngine/FoliageSequence.hlsli"
#include "../../MyPlanetEngine/ObserverExposure.hlsli"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
static void Require(bool ok,const char* message) { if (!ok) { std::fprintf(stderr,"FAIL: %s\n",message); std::exit(1); } }
int main() {
    for(unsigned c=0;c<=100;++c) for(unsigned h=0;h<=100;++h) {
        const float cover=float(c)/100,altitude=float(h)*.5f;
        const float sheltered=ObserverCanopy(cover,altitude,20);
        Require(sheltered>=0&&sheltered<=cover,"observer cover remains physically bounded");
        if(altitude>=20) Require(sheltered==0,"observer adaptation vanishes above the canopy");
        const float gain=ObserverExposure(1,1-sheltered*.95f,.5f);
        Require(gain>=1&&gain<=4,"observer adaptation stays within two stops");
        Require(ObserverExposure(1,1-sheltered*.95f,-.1f)==1,"observer adaptation does not lift night");
    }
    unsigned octants[8]={};
    for(unsigned dimension=0;dimension<3;++dimension) {
        unsigned strata[64]={};
        for(unsigned frame=0;frame<64;++frame) {
            const float value=FoliageSequence(frame,dimension,0xa63b1e2du);
            Require(value>0&&value<1,"coverage sample stays inside the unit interval");
            ++strata[unsigned(value*64)];
        }
        for(unsigned count:strata) Require(count==1,"each coverage dimension visits every temporal stratum once");
    }
    for(unsigned frame=0;frame<64;++frame) {
        unsigned octant=0;
        for(unsigned dimension=0;dimension<3;++dimension) octant|=(FoliageSequence(frame,dimension,0x5c2d943au+dimension)>=.5f?1u:0u)<<dimension;
        ++octants[octant];
    }
    for(unsigned count:octants) Require(count==8,"alpha and both fades retain their independent joint coverage");
    for(unsigned coverage=0;coverage<256;++coverage) for(unsigned channel=0;channel<=1000;++channel) {
        const float colour=float(channel)/1000,cover=float(coverage)/255;
        const float packed=PackObjectCanopy(colour,cover),decoded=ObjectBlue(packed);
        Require(std::isfinite(packed)&&std::isfinite(decoded),"packed object cover remains finite");
        Require(ObjectCanopy(packed)==cover,"all 256 object canopy cover values survive storage");
        Require(decoded>=0&&decoded<=colour&&colour-decoded<=3.1e-5f*colour+1e-40f,"cover packing preserves object reflectance precision");
    }
    for(int c=0;c<=100;++c) for(float sun:{-.1f,.1f,.5f,1.0f}) {
        const float cover=float(c)/100;
        const auto floor=CanopyLight(cover,0,sun),top=CanopyLight(cover,1,sun);
        Require(std::isfinite(floor.direct)&&std::isfinite(floor.sky),"canopy light stays finite");
        Require(floor.direct>0&&floor.direct<=1&&floor.sky>.21f&&floor.sky<=1,"closed crowns retain sky transport without adding light outside a forest");
        Require(top.direct==1&&top.sky==1,"top of crown is not shaded by an opaque stand");
        Require(floor.sunScatter>=0&&floor.sunScatter<=.12f*std::max(sun,0.f),"canopy bounce is bounded by intercepted daylight");
        Require(top.sunScatter==0&&CanopyLight(0,0,sun).sunScatter==0,"canopy bounce vanishes above crowns and on open ground");
        if(c) { auto prior=CanopyLight(float(c-1)/100,0,sun);Require(floor.direct<=prior.direct&&floor.sky<=prior.sky,"transport changes monotonically with cover"); }
    }
    for(unsigned model=0;model<96;++model) for(unsigned bits=0;bits<65536;++bits) {
        float packed=float(model+1)+float(bits)/131072.0f;
        unsigned restored=unsigned(std::lround((packed-std::floor(packed))*131072.0f));
        Require(restored==bits&&unsigned(packed-1)==model,"expanded model identity and both coverages stay exact");
    }
    for(unsigned family=0;family<6;++family) for(unsigned variant=0;variant<5;++variant) {
        Require(FoliageModelSpecies(31+10*family+variant)==(family==0||family==3?0u:1u),"tree bank species agrees on CPU and GPU");
        Require(FoliageModelSpecies(36+10*family+variant)==2,"shrub bank species agrees on CPU and GPU");
    }
    std::mt19937 rng(90211);std::uniform_real_distribution<float> random(-1,1);
    for(float radius:{.14f,.5f,1.4f,2.4f,4.f,8.f,24.f}) {
        const unsigned flat=PackRootContacts(0,0,0,0,radius);
        Require(RootContactHeight(flat,0,0,radius)==0,"centre is fixed");
        for(int i=0;i<1000;++i) {
            const float sx=random(rng)*.6f,sy=random(rng)*.6f;
            unsigned data=PackRootContacts(sx*radius,-sx*radius,sy*radius,-sy*radius,radius);
            float stored;std::memcpy(&stored,&data,4);
            Require(std::isfinite(stored)&&std::fpclassify(stored)==FP_NORMAL,"packed contacts remain finite normal floats");
            const float x=random(rng)*radius,y=random(rng)*radius;
            const float height=RootContactHeight(data,x,y,radius);
            Require(std::abs(height-(sx*x+sy*y))<=radius*.025f,"a planar terrain is reproduced within quantization");
            Require(std::abs(RootContactHeight(data,radius,0,radius)-sx*radius)<=radius*.012f,"east endpoint follows its sample");
            Require(std::abs(RootContactHeight(data,-radius,0,radius)+sx*radius)<=radius*.012f,"west endpoint follows its sample");
            Require(std::abs(RootContactHeight(data,0,radius,radius)-sy*radius)<=radius*.012f,"north endpoint follows its sample");
        }
        const unsigned hollow=PackRootContacts(.4f*radius,.4f*radius,.2f*radius,.2f*radius,radius);
        Require(RootContactHeight(hollow,0,0,radius)==0,"curvature never moves the root origin");
        Require(RootContactHeight(hollow,.7f*radius,.7f*radius,radius)>0,"curved contact follows surrounding ground");
    }
    std::puts("Root contacts: 7,000 planes through 24 m radius, sampled endpoints, fixed origin, curved ground and finite packing pass.");
}
