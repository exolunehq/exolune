#include "../../MyPlanetEngine/AirlessTerrain.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
using namespace Airless;
void Require(bool okay,const char* message) {if(!okay){std::fprintf(stderr,"FAIL: %s\n",message);std::exit(1);}}
int main() {
    Surface surface;
    double low=1e9,high=-1e9;
    for(unsigned i=0;i<600;++i) {
        const double y=1-2*(i+.5)/600,angle=i*2.399963229728653;
        Vec n={std::sqrt(1-y*y)*std::cos(angle),y,std::sqrt(1-y*y)*std::sin(angle)};
        const double h=surface.Height(n);low=std::min(low,h);high=std::max(high,h);
        Require(std::isfinite(h) && std::abs(h)<16000,"relief stays in its conservative envelope");
        Require(h==surface.Height(n),"terrain is deterministic");
        Require(surface.Albedo(n)>=.055 && surface.Albedo(n)<=.241,"reflectance stays within the dark regolith envelope");
        Require(Dot(surface.Normal(n),n)>.45,"contact normals face outwards");
    }
    Require(low<-1000 && high>100,"the moon has excavated basins and raised terrain");
    // Sliding planes supply body directions; neither origin nor parameterization changes the physical field.
    for(unsigned i=0;i<80;++i) {
        const Vec n=Unit({1,(i-40.0)/40,1});
        Require(std::abs(surface.Height(n)-surface.Height(n*surface.radius))<.002,"field is independent of radial representation");
        for(double footprint:{.25,1.,10.,100.,1000.,10000.}) {
            const double a=surface.Height(n,footprint),b=surface.Height(n,footprint*(1+1e-5));
            Require(std::abs(a-b)<.3,"continuous sampling footprint has no LOD switch");
            Require(std::abs(surface.Albedo(n,footprint)-surface.Albedo(n,footprint*(1+1e-5)))<.0001,
                "impact colour filters continuously with the physical relief");
        }
    }
    const Vec start={0,0,surface.radius+100000},end={0,0,-surface.radius-100000};
    const Vec stopped=surface.Sweep(start,end,4);
    Require(stopped.z>surface.radius-16000,"orbital chord cannot tunnel through the moon");
    Require(Length(stopped)-surface.radius-surface.Height(stopped)>9.9,"swept hull remains outside terrain");
    const Vec escaped=surface.Sweep(stopped,stopped+Unit(stopped),4);
    Require(Dot(escaped-stopped,Unit(stopped))>.9,"a stopped hull can immediately retreat from contact");
    const Vec tangent={100000,0,surface.radius+100000};
    Require(Length(surface.Sweep(start,tangent,4)-tangent)<.001,"clear orbital motion is preserved");
    Surface other=surface;other.seed+=1;
    Require(std::abs(other.Height({1,0,0})-surface.Height({1,0,0}))>1,"body seed changes its field");
    const std::array<Vec,3> centres={Vec{280000000,0,0},Vec{0,110000000,0},Vec{0,0,42000000}};
    Require(NearbyMoon(centres,{6378000,0,0})==-1,"Exolune does not activate a moon's terrain");
    for(unsigned i=0;i<Celestial::Moons.size();++i) {
        const auto body=MoonSurface(i);
        Require(NearbyMoon(centres,centres[i]+Vec{body.radius+100,0,0})==int(i),"each moon selects its own detailed stack");
        Require(NearbyMoon(centres,centres[i]+Vec{8*body.radius+1,0,0})==-1,"distant moons leave the shared terrain slot");
        Surface sameSize=body;sameSize.seed=Celestial::Moons[(i+1)%3].seed;
        Require(std::abs(body.Height({1,0,0})-sameSize.Height({1,0,0}))>1,"manifest seeds produce distinct surfaces at the same radius");
        for(unsigned sample=0;sample<200;++sample) {
            const double y=1-2*(sample+.5)/200,angle=sample*2.399963229728653;
            const Vec n={std::sqrt(1-y*y)*std::cos(angle),y,std::sqrt(1-y*y)*std::sin(angle)};
            Require(std::isfinite(body.Height(n)) && std::abs(body.Height(n))<16000,"every manifest stays in the shared geometry envelope");
        }
        unsigned remaining=ContactSamples;
        const Vec from={0,0,body.radius+100000},to={0,0,-body.radius-100000};
        const auto accepted=body.Sweep(from,to,4,&remaining);
        Require(remaining<ContactSamples && remaining<=ContactSamples,"a body consumes the shared sweep budget");
        Require(accepted.z>body.radius-16000,"each manifest blocks a planet-spanning chord");
        unsigned empty=0;
        Require(Length(body.Sweep(accepted,to,4,&empty)-accepted)==0,"an exhausted shared budget cannot authorize unsampled motion");
    }
    unsigned contacts=0;
    for(unsigned profile=0;profile<6;++profile) {
        Surface body=surface;body.radius*=.5+.5*profile;body.seed+=profile;
        if(profile>=3)body=MoonSurface(profile-3);
        for(unsigned i=0;i<8;++i)for(double hull:{.25,4.0}) {
            const double y=1-2*i/7.0,angle=i*2.399963229728653;
            const Vec up={std::sqrt(std::max(0.0,1-y*y))*std::cos(angle),y,std::sqrt(std::max(0.0,1-y*y))*std::sin(angle)};
            const Vec ground=body.Point(up);
            auto gap=[&](Vec p){return Length(p)-body.radius-body.Height(p)-HullPadding*hull;};
            const Vec touch=body.Sweep(ground+up*50,ground-up*50,hull);
            Require(gap(touch)>=-.002,"contact remains outside the conservative hull support");
            const Vec tiny=body.Sweep(touch,touch+Unit(touch)*.0001,hull);
            Require(Dot(tiny-touch,Unit(touch))>.00008,"submillimetre outward input is never swallowed");
            const Vec normal=body.Normal(touch,.25);
            const Vec axis=std::abs(normal.y)<.9?Vec{0,1,0}:Vec{1,0,0};
            const Vec side=Unit(Cross(normal,axis));
            const Vec slide=body.Sweep(touch,touch+side*.2-normal*.2,hull);
            Require(Dot(slide-touch,side)>.04,"diagonal contact retains tangential motion");
            Require(gap(slide)>=-.002,"a redirected slide is swept against subsequent relief");
            // A long swept descent can slide away from the first impact and end above a hollow.
            // Establish actual support before testing repeated inward requests.
            const Vec restingGround=body.Point(Unit(touch));
            Vec held=body.Sweep(restingGround,restingGround,hull);
            const Vec settled=held;
            for(unsigned frame=0;frame<20;++frame)held=body.Sweep(held,held-body.Normal(held,.25)*.05,hull);
            if(Length(held-settled)>=.01)std::fprintf(stderr,"contact fixture profile=%u site=%u hull=%g initialGap=%g finalGap=%g movement=%g\n",profile,i,hull,gap(settled),gap(held),Length(held-settled));
            Require(Length(held-settled)<.01,"holding against the support does not pump the camera");
            const Vec retreat=body.Sweep(held,held+Unit(held)*2,hull);
            Require(Dot(retreat-held,Unit(held))>1.9,"retreat remains available after repeated inward requests");
            const Vec overlap=ground-up*.1,recovered=body.Sweep(overlap,overlap,hull);
            Require(gap(recovered)>=ContactSkin,"stationary overlap uses the same support as moving contact");
            Require(Length(body.Sweep(recovered,recovered,hull)-recovered)<.001,"recovered idle position is stable");
            Require(Dot(body.Sweep(recovered,recovered+up,hull)-recovered,up)>.9,"placement recovery cannot latch the next movement");
            ++contacts;
        }
    }
    std::printf("PASS: shared relief/filtering, orbital chords and %u contact sequences: tiny retreat, sliding, repeated contact and overlap recovery.\n",contacts);
}
