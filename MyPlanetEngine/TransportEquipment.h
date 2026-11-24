// Transport equipment shares one set of physical positions with flight, cockpit and renderer.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>

struct TransportEquipment {
    enum Part { Wings, Gear, Brake, Hatch, Count };
    std::array<double, Count> position{};
    std::array<int, Count> manual{{-1,-1,-1,-1}};
    std::array<bool, Count> target{};
    bool initialized = false, cruise = false, approach = false;
    double stoppedTime = 0;

    void Toggle(Part part) { manual[part] = (manual[part]>=0 ? manual[part]!=0 : target[part]) ? 0 : 1; }
    void Automatic() { manual.fill(-1); }
    unsigned ManualMask() const {
        unsigned mask = 0;
        for (unsigned i=0; i<Count; ++i) if (manual[i]>=0) mask |= 1u<<i;
        return mask;
    }
    void Advance(double dt, double clearance, double descent, double speed, double density,
                 double airspeed, double pressure, double heat, double decel, bool braking, bool powered, bool supported) {
        const double approachHeight = std::max(80.0,std::min(380.0,80.0+descent*5));
        if (clearance <= approachHeight && speed < 135) approach = true;
        if (clearance > approachHeight+90 || (clearance > 18 && speed > 175)) approach = false;
        if (density > .00022 && airspeed > 42 && pressure < 62000 && heat < .22) cruise = true;
        if (density < .00008 || airspeed < 24 || pressure > 85000 || heat > .48) cruise = false;
        const bool parked = supported && speed < 1.2 && !powered;
        stoppedTime = parked ? stoppedTime+dt : 0;
        target = {cruise, approach, density > .0001 && (braking || decel > 3) && pressure > 75, stoppedTime >= 1.0};
        for (unsigned i=0; i<Count; ++i) if (manual[i]>=0) target[i] = manual[i]!=0;
        if (!initialized) {
            position[Gear] = approach ? 1.0 : 0.0;
            initialized = true;
        }
        // Keep the airstair clear of the ground until the ship is supported.
        target[Hatch] = target[Hatch] && parked && position[Gear]>=1.0;
        if (supported || position[Hatch] > 0) target[Gear] = true;
        constexpr double duration[Count] = {4.0,3.5,1.25,3.0};
        for (unsigned i=0; i<Count; ++i) {
            const double step = dt/duration[i];
            position[i] += std::max(-step,std::min(step,double(target[i])-position[i]));
        }
    }
};
