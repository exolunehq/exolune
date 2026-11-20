#pragma once

#include "FlightFrame.h"

namespace TerrainFocus {
// Sample the centre and the lower part of the actual view. Each ray that reaches
// the reference surface contributes its tangent-plane hit, fading at the limb.
inline Vec3d Offset(Vec3d camera, Vec3d forward, Vec3d viewUp, double tanHalfFov,
                   double aspect, double radius, double groundHeight, double limit) {
    if (limit <= 0.0) return {};
    const double eyeRadius = Length(camera);
    const Vec3d up = camera * (1.0 / eyeRadius);
    FlightFrame::Orthonormalize(forward, viewUp);
    const Vec3d right = Cross(viewUp, forward);
    const double surface = std::min(radius + groundHeight, eyeRadius - 0.01);
    const double c = (eyeRadius - surface) * (eyeRadius + surface);
    const double limbToward = std::sqrt(c);
    const double limbWidth = 0.035 * surface; // about two degrees at the limb, from the ground or from orbit
    auto aim = [&](double x, double y) {
        const Vec3d ray = Normalize(forward + (right * (x * aspect) + viewUp * y) * tanHalfFov);
        const double toward = -Dot(ray, camera);
        const double inside = toward - limbToward;
        if (inside <= 0.0) return Vec3d{};
        const double disc = inside * (toward + limbToward);
        const double distance = c / (toward + std::sqrt(disc));
        const Vec3d hit = camera + ray * distance;
        const double radial = Dot(hit, up);
        const double limb = std::min(1.0, inside / limbWidth);
        const double weight = limb * limb * (3.0 - 2.0 * limb);
        const Vec3d offset = (ray - up * Dot(ray, up)) * (radius * distance / radial);
        return offset * (weight * limit / std::hypot(limit, Length(offset)));
    };
    const double vertical = Dot(forward, up);
    const double horizon = std::max(0.0, 1.0 - vertical * vertical);
    return aim(0.0, 0.0) * 0.54
        + (aim(-0.36, -0.28 * horizon) + aim(0.36, -0.28 * horizon)) * 0.17
        + aim(0.0, -0.63 * horizon) * 0.12;
}
}
