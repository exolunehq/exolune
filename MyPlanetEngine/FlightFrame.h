// World-space flight attitude. Translation and the choice of nearby body never rotate this frame.
#pragma once
#include <cmath>

// Double precision is shared with terrain placement and contact at astronomical distances.
struct Vec3d {
    double x, y, z;
    Vec3d operator+(const Vec3d& o) const { return {x+o.x,y+o.y,z+o.z}; }
    Vec3d operator-(const Vec3d& o) const { return {x-o.x,y-o.y,z-o.z}; }
    Vec3d operator*(double s) const { return {x*s,y*s,z*s}; }
};
inline double Dot(const Vec3d& a,const Vec3d& b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
inline Vec3d Cross(const Vec3d& a,const Vec3d& b) { return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
inline double Length(const Vec3d& v) { return std::sqrt(Dot(v,v)); }
inline Vec3d Normalize(const Vec3d& v) { return v*(1.0/Length(v)); }
inline Vec3d Rotate(const Vec3d& v,const Vec3d& axis,double angle) {
    const double c=std::cos(angle),s=std::sin(angle);
    return v*c+Cross(axis,v)*s+axis*(Dot(axis,v)*(1-c));
}

namespace FlightFrame {
inline void Orthonormalize(Vec3d& forward,Vec3d& up) {
    forward=Normalize(forward);
    up=up-forward*Dot(up,forward);
    if(Length(up)<1e-8) {
        const Vec3d fallback=std::abs(forward.y)<.9?Vec3d{0,1,0}:Vec3d{1,0,0};
        up=fallback-forward*Dot(fallback,forward);
    }
    up=Normalize(up);
}
// Angles act on the observer's own axes: positive yaw right, pitch down, roll right.
inline void Turn(Vec3d& forward,Vec3d& up,double yaw,double pitch,double roll) {
    Orthonormalize(forward,up);
    const Vec3d right=Normalize(Cross(up,forward));
    forward=Rotate(forward,right,pitch);
    up=Rotate(up,right,pitch);
    forward=Rotate(forward,up,yaw);
    up=Rotate(up,forward,-roll);
    Orthonormalize(forward,up);
}
// A placement supplies a complete frame, including at exact nadir or zenith.
inline void FromHeading(Vec3d vertical,Vec3d level,double pitchDown,Vec3d& forward,Vec3d& up) {
    forward=level*std::cos(pitchDown)-vertical*std::sin(pitchDown);
    up=vertical*std::cos(pitchDown)+level*std::sin(pitchDown);
    Orthonormalize(forward,up);
}
}
