// Camera and ship attitude in world space.
#pragma once
#include <algorithm>
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
enum class CameraMode : unsigned { Free = 1, Horizon, FixedAltitude }; // codes also used by the on-screen hint
inline CameraMode NextCameraMode(CameraMode mode) {
    if (mode == CameraMode::Free) return CameraMode::Horizon;
    if (mode == CameraMode::Horizon) return CameraMode::FixedAltitude;
    return CameraMode::Free;
}

// Forward follows the full sightline. The caller chooses screen up or the body's vertical for lift.
inline Vec3d ViewTravel(Vec3d forward, Vec3d screenUp, Vec3d liftAxis, double ahead, double sideways, double rise) {
    return forward * ahead + Normalize(Cross(screenUp, forward)) * sideways + liftAxis * rise;
}

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

// A tangent heading stays defined when the observer looks straight up or down.
struct Orbit {
    Vec3d vertical = {0,1,0}, heading = {0,0,1};
    double pitchDown = 0;

    void Align(Vec3d offset, Vec3d forward, Vec3d up) {
        vertical = Length(offset) > 0 ? Normalize(offset) : up;
        const double rise = Dot(forward, vertical);
        const Vec3d flat = forward - vertical * rise;
        const double horizontal = Length(flat);
        // Near vertical the screen's right axis still carries the entry heading.
        heading = horizontal > 1e-7 ? flat * (1.0 / horizontal) : Normalize(Cross(Cross(up, forward), vertical));
        pitchDown = std::atan2(-rise, horizontal);
    }

    void Look(double yaw, double pitch) {
        constexpr double halfPi = 1.5707963267948966;
        heading = Rotate(heading, vertical, yaw);
        pitchDown = std::max(-halfPi, std::min(halfPi, pitchDown + pitch));
    }

    void View(Vec3d& forward, Vec3d& up) const {
        FromHeading(vertical, heading, pitchDown, forward, up);
    }

    Vec3d MoveAtFixedAltitude(Vec3d offset, double ahead, double sideways, double rise, double floorRadius) const {
        if (ahead == 0 && sideways == 0 && rise == 0) return offset;
        const double radius = Length(offset);
        const Vec3d tangent = heading * ahead + Cross(vertical, heading) * sideways;
        const Vec3d radial = Normalize(vertical * std::max(radius, 1.0) + tangent);
        return radial * std::max(radius + rise, std::min(radius, floorRadius));
    }

    // Parallel transport along the accepted displacement, including a partial terrain slide.
    void Follow(Vec3d offset) {
        if (Length(offset) == 0) return;
        const Vec3d next = Normalize(offset);
        const Vec3d axis = Cross(vertical, next);
        const double sine = Length(axis);
        if (sine > 1e-12)
            heading = Rotate(heading, axis * (1.0 / sine), std::atan2(sine, Dot(vertical, next)));
        vertical = next;
        heading = Normalize(heading - vertical * Dot(heading, vertical));
    }
};
}
