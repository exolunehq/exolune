// A small fictional system. Kilometres, seconds and linear reflectance; no camera-dependent placement.
#pragma once
#include <array>
#include <cmath>
#include <algorithm>
#include "AirlessPhotometry.hlsli"
#include "CelestialManifest.h"

namespace Celestial {
constexpr double Pi = 3.14159265358979323846, AU = 149597870.7, PlanetRadius = 6378.0;
constexpr unsigned MoonCount = unsigned(Moons.size()), BodyCount = 7, Sun = 6, StarCount = 42000;
struct Vector {
    double x, y, z;
    Vector operator+(Vector b) const { return {x+b.x,y+b.y,z+b.z}; }
    Vector operator-(Vector b) const { return {x-b.x,y-b.y,z-b.z}; }
    Vector operator*(double s) const { return {x*s,y*s,z*s}; }
};
inline double Dot(Vector a, Vector b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
inline double Length(Vector a) { return std::sqrt(Dot(a,a)); }
inline Vector Unit(Vector a) { return a*(1.0/std::max(Length(a),1e-20)); }
struct Body {
    Vector position, albedo, toSun;
    double radius, sunlight, kind;
};
inline double Clamp(double x,double lo,double hi) { return std::max(lo,std::min(hi,x)); }
inline double Phase(double cosine) {
    cosine=Clamp(cosine,-1.0,1.0);
    const double angle=std::acos(cosine);
    return (std::sin(angle)+(Pi-angle)*cosine)/Pi;
}
// Projected-disc integral of AirlessDiffuse, before the small grazing roughness bound.
// Unresolved flux follows the same particulate reflectance as a resolved or landable surface.
inline double AirlessDisc(double cosine) {
    const double angle=std::acos(Clamp(cosine,-1.0,1.0));
    const double ls=angle<1e-7?1:angle>Pi-1e-7?0:
        std::max(0.0,1-std::sin(angle*.5)*std::tan(angle*.5)*std::log(1/std::tan(angle*.25)));
    return .35*(2.0/3.0)*Phase(cosine)+.65*ls;
}
// Fraction of the solar disc not covered by Exolune, including the finite penumbra.
inline double Eclipse(Vector point, Vector sun) {
    const Vector a=sun-point, b=point*-1.0;
    const double ra=std::asin(std::min(1.0,695700.0/Length(a)));
    const double rb=std::asin(std::min(1.0,PlanetRadius/Length(b)));
    const double d=std::acos(Clamp(Dot(Unit(a),Unit(b)),-1.0,1.0));
    if(d>=ra+rb) return 1.0;
    if(d<=std::abs(rb-ra)) return rb>=ra?0.0:1.0-rb*rb/(ra*ra);
    const double x=Clamp((d*d+ra*ra-rb*rb)/(2*d*ra),-1.0,1.0);
    const double y=Clamp((d*d+rb*rb-ra*ra)/(2*d*rb),-1.0,1.0);
    const double area=ra*ra*std::acos(x)+rb*rb*std::acos(y)
        -0.5*std::sqrt(std::max(0.0,(-d+ra+rb)*(d+ra-rb)*(d-ra+rb)*(d+ra+rb)));
    return Clamp(1.0-area/(Pi*ra*ra),0.0,1.0);
}
inline std::array<Body,BodyCount> System(double seconds, Vector sunDirection) {
    const Vector sun=Unit(sunDirection)*AU;
    std::array<Body,BodyCount> bodies{};
    const double distance[6]={280000,110000,42000,0.68*AU,1.65*AU,4.7*AU};
    const double radii[6]={1800,700,260,6100,4200,63000};
    const double phase[6]={2.52,2.82,3.19,3.72,1.2,4.0};
    const double inclination[6]={0.19,-0.31,0.43,0.055,-0.025,0.035};
    const Vector albedo[6]={{.145,.1392,.13195},{.24,.255,.27},{.15,.115,.085},
        {.62,.57,.45},{.24,.105,.057},{.48,.39,.27}};
    for(unsigned i=0;i<6;++i) {
        const double gm=i<MoonCount?398600.4418:1.32712440018e11;
        const double omega=std::sqrt(gm/(distance[i]*distance[i]*distance[i]));
        const double a=phase[i]+std::remainder(seconds*omega,2*Pi);
        const double node=i<MoonCount?-0.4:0.0;
        const Vector p={std::cos(a)*std::cos(node)-std::sin(a)*std::cos(inclination[i])*std::sin(node),
            std::sin(a)*std::sin(inclination[i]),
            std::cos(a)*std::sin(node)+std::sin(a)*std::cos(inclination[i])*std::cos(node)};
        Body& b=bodies[i]; b.position=p*distance[i]+(i<MoonCount?Vector{}:sun);
        b.radius=radii[i]; b.albedo=albedo[i]; b.kind=double(i);
        if(i<MoonCount) {
            const auto& manifest=Moons[i];
            b.radius=manifest.radius*.001;
            b.albedo={manifest.reflectance[0],manifest.reflectance[1],manifest.reflectance[2]};
        }
        b.toSun=Unit(sun-b.position);
        b.sunlight=AU*AU/Dot(sun-b.position,sun-b.position)*Eclipse(b.position,sun);
    }
    bodies[Sun]={sun,{1,1,1},{0,0,0},695700,1,6};
    return bodies;
}
inline Vector Illuminance(const Body& b, Vector observer) {
    const Vector toward=observer-b.position;
    const double d2=std::max(Dot(toward,toward),b.radius*b.radius);
    if(b.kind==6) return Vector{Pi,Pi,Pi}*(AU*AU/d2);
    const double cosine=Dot(Unit(toward),b.toSun);
    const double disc=b.kind<MoonCount?AirlessDisc(cosine):(2.0/3.0)*Phase(cosine);
    return b.albedo*(Pi*b.sunlight*b.radius*b.radius/d2*disc);
}
}
