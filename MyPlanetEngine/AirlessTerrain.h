// CPU access to the physical impact field shared with the common terrain shaders.
// Distances are metres in the body's frame. No rendering or planet-specific dependencies.
#pragma once
#include <array>
#include <cstdint>
#include <memory>
#include <vector>
#include "CelestialManifest.h"

namespace Airless {
constexpr double ContactSkin=0.02,HullPadding=2.5;
constexpr unsigned ContactSamples=192;
struct Vec {
    double x=0,y=0,z=0;
    Vec()=default;
    Vec(double a,double b,double c):x(a),y(b),z(c) {}
    Vec operator+(Vec b) const { return {x+b.x,y+b.y,z+b.z}; }
    Vec operator-(Vec b) const { return {x-b.x,y-b.y,z-b.z}; }
    Vec operator*(double s) const { return {x*s,y*s,z*s}; }
};
double Dot(Vec a,Vec b);
double Length(Vec p);
Vec Unit(Vec p);
Vec Cross(Vec a,Vec b);

struct Surface {
    double radius=Celestial::Moons[0].radius;
    uint32_t seed=Celestial::Moons[0].seed;
    // The same filtered field supplies sliding-plane vertices, contact and the far proxy.
    double Height(Vec direction,double footprint=0.25) const;
    double Albedo(Vec direction,double footprint=0.25) const;
    Vec Normal(Vec direction,double footprint=0.5) const;
    Vec Point(Vec direction,double footprint=0.25) const;
    // Bounded conservative advancement, recovery and sliding. Only inward motion is rejected at contact.
    // All segments and contact normals share ContactSamples; exhaustion retains the last certified position.
    Vec Sweep(Vec start,Vec end,double hullRadius,unsigned* samplesRemaining=nullptr) const;
};

inline Surface MoonSurface(unsigned index) {
    const auto& manifest=Celestial::Moons.at(index);
    return {manifest.radius,manifest.seed};
}
// Metres in a shared inertial frame. Only one body owns the detailed terrain buffers.
inline int NearbyMoon(const std::array<Vec,Celestial::Moons.size()>& centres,Vec position) {
    int selected=-1;double closest=64;
    for(unsigned i=0;i<centres.size();++i) {
        const Vec d=position-centres[i];const double r=Celestial::Moons[i].radius;
        const double distance=Dot(d,d)/(r*r);
        if(distance<closest){selected=int(i);closest=distance;}
    }
    return selected;
}

}
