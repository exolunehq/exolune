// A height-field character controller. Metres, seconds; independent of rendering and the planet's reference frame.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>

struct WalkTerrain {
    static constexpr int Side = 9, Count = Side * Side;
    static constexpr double Cell = 0.5;
    std::array<float, Count> heights = {};

    bool Sample(double x, double y, double& h, double& sx, double& sy) const {
        const double gx = x / Cell + Side / 2, gy = y / Cell + Side / 2;
        if (gx < 0 || gy < 0 || gx >= Side - 1 || gy >= Side - 1) return false;
        const int ix = int(gx), iy = int(gy);
        const double u = gx - ix, v = gy - iy;
        const double a = heights[iy * Side + ix], b = heights[iy * Side + ix + 1];
        const double c = heights[(iy + 1) * Side + ix], d = heights[(iy + 1) * Side + ix + 1];
        h = (a + (b - a) * u) * (1 - v) + (c + (d - c) * u) * v;
        sx = ((b - a) * (1 - v) + (d - c) * v) / Cell;
        sy = ((c - a) * (1 - u) + (d - b) * u) / Cell;
        return std::isfinite(h) && std::isfinite(sx) && std::isfinite(sy);
    }
};

struct Walker {
    static constexpr double Eye = 1.68, CrouchEye = 1.05, Radius = 0.25, MaxSlope = 1.0;
    struct Input { double x = 0, y = 0; bool sprint = false, crouch = false, jump = false; };
    double x = 0, y = 0, elevation = 0, vx = 0, vy = 0, vertical = 0, eye = Eye;
    double stride = 0, distance = 0;
    bool grounded = true;
    unsigned steps = 0;
    float landing = 0;

    // The caller rebases x/y and vx/vy into each new patch before advancing. No motion beyond sampled ground.
    void Advance(double dt, Input in, const WalkTerrain& terrain) {
        steps = 0; landing = 0;
        dt = std::min(std::max(dt, 0.0), 0.1);
        const double magnitude = std::hypot(in.x, in.y);
        if (magnitude > 1.0) { in.x /= magnitude; in.y /= magnitude; }
        const double speed = in.crouch ? 0.75 : in.sprint ? 3.6 : 1.5;
        const double strideLength = in.crouch ? 0.6 : in.sprint ? 1.1 : 0.78;
        if (in.jump && grounded && !in.crouch) { vertical = 4.0; grounded = false; }
        for (double remaining = dt; remaining > 1e-8;) {
            const double step = std::min(remaining, 1.0 / 120.0); remaining -= step;
            eye += ((in.crouch ? CrouchEye : Eye) - eye) * (1.0 - std::exp(-step / 0.12));
            const double response = 1.0 - std::exp(-step / (grounded ? 0.1 : 0.6));
            vx += (in.x * speed - vx) * response; vy += (in.y * speed - vy) * response;
            const double oldX = x, oldY = y, oldElevation = elevation;
            double h = 0, sx = 0, sy = 0;
            auto allowed = [&](double nx, double ny) {
                if (!terrain.Sample(nx, ny, h, sx, sy) || h < 0.15) return false; // swimming is a separate mode
                double edge, dx, dy;
                for (const auto& p : std::array<std::array<double, 2>, 4>{{{{Radius,0}},{{-Radius,0}},{{0,Radius}},{{0,-Radius}}}})
                    if (!terrain.Sample(nx + p[0], ny + p[1], edge, dx, dy) || edge > std::max(elevation, h) + 0.30)
                        return false;
                // A steep face blocks ascent; downhill motion and motion along the face remain possible.
                return !(std::hypot(sx, sy) > MaxSlope && sx * (nx - x) + sy * (ny - y) > 1e-6
                         && h > elevation - 0.02);
            };
            double nx = x + vx * step, ny = y + vy * step;
            if (!allowed(nx, ny)) {
                // Remove the uphill component, so contact slides along a wall rather than sticking to it.
                const double norm = sx * sx + sy * sy, into = vx * sx + vy * sy;
                if (norm > 1e-8 && into > 0) { vx -= sx * into / norm; vy -= sy * into / norm; }
                nx = x + vx * step; ny = y + vy * step;
                if (!allowed(nx, ny)) { nx = x; ny = y; vx = vy = 0; }
            }
            x = nx; y = ny;
            if (!terrain.Sample(x, y, h, sx, sy)) { x = oldX; y = oldY; vx = vy = 0; break; }
            const double travel = std::hypot(x - oldX, y - oldY);
            // Stay attached on ordinary descending slopes; a ledge starts a gravitational fall.
            if (grounded && h >= elevation - (0.04 + 1.2 * travel)) {
                elevation = h; vertical = 0;
            } else {
                grounded = false;
                vertical -= 9.81 * step;
                elevation += vertical * step;
                if (elevation <= h && vertical <= 0) {
                    landing = std::max(landing, float(std::min(-vertical / 5.0, 1.5)));
                    elevation = h; vertical = 0; grounded = true;
                }
            }
            if (grounded && travel > 1e-7) {
                const double length = std::hypot(travel, elevation - oldElevation);
                distance += length; stride += length;
                if (stride >= strideLength) { stride = std::fmod(stride, strideLength); ++steps; }
            }
        }
    }
};
