#include "AirlessTerrain.h"
#include <algorithm>
#include <cmath>
namespace Airless {
double Dot(Vec a,Vec b){return a.x*b.x+a.y*b.y+a.z*b.z;}
double Length(Vec p){return std::sqrt(Dot(p,p));}
Vec Unit(Vec p){return p*(1/std::max(Length(p),1e-30));}
Vec Cross(Vec a,Vec b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
}
#include "AirlessField.hlsli"
namespace Airless {
double Surface::Height(Vec direction,double footprint) const {return AirlessField::AirlessHeight(direction,float(radius),seed,float(footprint));}
double Surface::Albedo(Vec direction,double footprint) const {return AirlessField::AirlessSample(direction,float(radius),seed,float(footprint)).albedo;}
Vec Surface::Point(Vec direction,double footprint) const {
    direction=Unit(direction); return direction*(radius+Height(direction,footprint));
}
Vec Surface::Normal(Vec direction,double footprint) const {
    const Vec n=Unit(direction),axis=std::abs(n.y)<.9?Vec{0,1,0}:Vec{1,0,0};
    const Vec x=Unit(Cross(axis,n)),y=Cross(n,x);
    const double step=std::max(footprint,.25);
    const Vec dx=Point(n+x*(step/radius),footprint)-Point(n-x*(step/radius),footprint);
    const Vec dy=Point(n+y*(step/radius),footprint)-Point(n-y*(step/radius),footprint);
    return Unit(Cross(dx,dy));
}
Vec Surface::Sweep(Vec start,Vec end,double hullRadius,unsigned* samplesRemaining) const {
    const unsigned limit=samplesRemaining?std::min(*samplesRemaining,ContactSamples):ContactSamples;
    const double padding=hullRadius*HullPadding;
    // The same hull support applies to placement, movement and the global clipping envelope.
    const double envelope=radius+16000+padding+2*ContactSkin;
    Vec position=start,remaining=end-start;
    unsigned queries=0;
    struct Account {
        unsigned* remaining;unsigned& used;
        ~Account(){if(remaining)*remaining-=used;}
    } account{samplesRemaining,queries};
    // A contact may redirect the unconsumed movement, but never gets a fresh query budget.
    for(unsigned response=0;response<5 && queries<limit;++response) {
        const double distance=Length(remaining);
        if(distance<1e-9) {
            if(Length(position)>envelope)return position;
            ++queries;
            const double gap=Length(position)-radius-Height(position)-padding;
            return gap<ContactSkin?position+Unit(position)*(2*ContactSkin-gap):position;
        }
        const Vec origin=position,direction=remaining*(1/distance),target=origin+remaining;
        const double along=Dot(origin,direction),disc=along*along-Dot(origin,origin)+envelope*envelope;
        if(disc<0)return target;
        double travelled=std::max(0.0,-along-std::sqrt(disc));
        const double last=std::min(distance,-along+std::sqrt(disc));
        if(travelled>last)return target;
        bool redirected=false;
        while(queries<limit) {
            const Vec p=origin+direction*travelled;
            const double gap=Length(p)-radius-Height(p)-padding;
            ++queries;position=p;
            // Existing contact blocks only its inward component, not tangent motion or retreat.
            // The small support margin also keeps repeated inward requests from pumping the eye up/down.
            if(gap<ContactSkin || (travelled==0 && gap<=2*ContactSkin+1e-6)) {
                const double recovery=gap<ContactSkin?2*ContactSkin-gap:0;
                position=p+Unit(p)*recovery;
                if(queries+4>limit)return position;
                const Vec normal=Normal(p,.25);queries+=4;
                const Vec rest=direction*(distance-travelled);
                const double into=Dot(rest,normal);
                const bool blocked=into<-1e-10*std::max(Length(rest),1.0);
                if(blocked || recovery>0) {
                    remaining=blocked?rest-normal*into:rest;
                    redirected=true;break;
                }
            }
            // The shared physical field has a conservative slope envelope of four.
            const double advance=gap/4.0;
            if(travelled+advance>=last)return target;
            travelled+=advance;
        }
        if(!redirected)return position;
    }
    return position;
}

}
