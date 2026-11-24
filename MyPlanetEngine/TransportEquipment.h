// Transport equipment shares one set of physical positions with flight, cockpit and renderer.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>

struct TransportExhaust {
    static constexpr double TrimShare = .22; // fraction of hover support carried by the ventral jets
    double ahead = 0, lift = 0, side = 0, trim = 0;

    void Advance(double dt, double axial, double vertical, double lateral, bool parked, double trimLoad = 0) {
        const double response = -std::expm1(-dt / .085);
        ahead += ((parked ? 0.0 : axial) - ahead) * response;
        lift += ((parked ? 0.0 : vertical) - lift) * response;
        side += ((parked ? 0.0 : lateral) - side) * response;
        trim += ((parked ? 0.0 : trimLoad) - trim) * response;
    }
    double MainPower() const {
        return std::sqrt(std::min(1.0, std::hypot(std::max(0.0, ahead), std::max(0.0, lift - trim))));
    }
    double Deflection() const {
        return std::atan2(std::max(0.0, lift - trim), std::max(0.0, ahead));
    }
};

struct TransportEquipment {
    enum Part { Wings, Gear, Brake, Hatch, Count };
    enum class Phase { Flight, Approach, Parked, Closing, Takeoff };
    static constexpr int WingOpenKmh = 150, WingCloseKmh = 90;
    static constexpr int WingProtectKmh = 1340, WingRearmKmh = 1140;
    static constexpr int MaxApproachHeight = 5000, MaxApproachKmh = 1200;
    static constexpr double PadDepth = 2.6388, HoverHeight = 8;
    static constexpr double AtmosphericControlDensity = .00022; // ratio to sea-level density
    Phase phase = Phase::Flight;
    std::array<double, Count> position{};
    std::array<int, Count> manual{{-1,-1,-1,-1}};
    std::array<bool, Count> target{};
    bool initialized = false, cruise = false, gearNearGround = false, wingProtected = false;
    bool precisionHover = false, brakeToHover = false;
    double parkedTime = 0;
    double airAuthority = 0; // fraction of attitude control carried by the docked wings
    double leftElevon = 0, rightElevon = 0, rudder = 0;
    static constexpr double ElevonRadians = .384; // 22 degrees

    void SetAirflow(double indicatedSpeed, double forwardCosine, bool holding) {
        auto ramp = [](double t) { t=std::max(0.0,std::min(1.0,t)); return t*t*(3-2*t); };
        const double docked = ramp((position[Wings]-.90)/.08);
        const double flow = ramp((3.6*indicatedSpeed*forwardCosine-WingCloseKmh)/(WingOpenKmh-WingCloseKmh));
        const double attached = ramp((forwardCosine-.55)/.35);
        airAuthority = phase==Phase::Flight && !holding && !precisionHover && !wingProtected ? docked*flow*attached : 0;
    }
    struct Helm { double pitch, yaw, roll; }; // nose up, yaw right, roll right
    static double Signed(double x) { return std::max(-1.0,std::min(1.0,x)); }
    Helm Steer(Helm pilot, double climb, double slide) const {
        const double pitch=Signed(pilot.pitch+.45*climb);
        const double left=Signed(pitch-pilot.roll), right=Signed(pitch+pilot.roll);
        return {pilot.pitch + airAuthority*(.5*(right+left)-pilot.pitch),
                pilot.yaw + airAuthority*(Signed(pilot.yaw+.5*slide)-pilot.yaw),
                pilot.roll + airAuthority*(.5*(right-left)-pilot.roll)};
    }
    void Deflect(Helm motion) {
        leftElevon=airAuthority*Signed(motion.pitch-motion.roll);
        rightElevon=airAuthority*Signed(motion.pitch+motion.roll);
        rudder=airAuthority*Signed(motion.yaw);
    }
    double TailPhase(int side) const {
        // Differential opening uses the same two panels and cylinders as the speed brake.
        return std::max(0.0,std::min(1.0,position[Brake]+side*.52*rudder));
    }

    bool GroundLocked() const { return phase == Phase::Parked || phase == Phase::Closing; }
    bool Guided() const { return phase == Phase::Approach || phase == Phase::Takeoff; }
    bool CanWalk() const { return phase == Phase::Parked && position[Hatch] == 1; }
    void SetPhase(Phase next) {
        phase = next;
        if (next!=Phase::Flight) airAuthority=leftElevon=rightElevon=rudder=0;
        precisionHover = brakeToHover = false;
        if (next == Phase::Parked) parkedTime = 0;
        if (next != Phase::Flight) Automatic();
    }
    bool Toggle(Part part) {
        if (part == Hatch ? phase != Phase::Parked : phase != Phase::Flight) return false;
        if (part == Wings && wingProtected) return false;
        manual[part] = (manual[part]>=0 ? manual[part]!=0 : target[part]) ? 0 : 1;
        return true;
    }
    void Automatic() { manual.fill(-1); }
    unsigned ManualMask() const {
        unsigned mask = 0;
        for (unsigned i=0; i<Count; ++i) if (manual[i]>=0) mask |= 1u<<i;
        return mask;
    }
    void Advance(double dt, double clearance, double descent, double speed, double density,
                 double airspeed, double pressure, double heat, double decel, bool braking) {
        const double approachHeight = std::max(80.0,std::min(380.0,80.0+descent*5));
        if (clearance <= approachHeight && speed < 135) gearNearGround = true;
        if (clearance > approachHeight+90 || (clearance > 18 && speed > 175)) gearNearGround = false;
        const double indicated=airspeed*3.6;
        if (density < .00008 || indicated >= WingProtectKmh || heat >= .48) wingProtected = true;
        else if (density > .00022 && indicated <= WingRearmKmh && heat <= .22) wingProtected = false;
        if (indicated >= WingOpenKmh) cruise = true;
        if (indicated <= WingCloseKmh || wingProtected) cruise = false;
        if (phase == Phase::Parked) parkedTime += dt;
        target = {cruise, gearNearGround, density > .0001 && (braking || decel > 3) && pressure > 75,
                  phase == Phase::Parked && parkedTime >= .4};
        for (unsigned i=0; i<Count; ++i) if (manual[i]>=0) target[i] = manual[i]!=0;
        if (wingProtected) target[Wings] = false;
        if (phase != Phase::Flight) {
            target[Wings] = false;
            target[Gear] = true;
            target[Brake] = phase == Phase::Approach && speed*speed-descent*descent > 12*12 && pressure > 75;
        }
        if (phase != Phase::Parked) target[Hatch] = false;
        if (!initialized) {
            position[Gear] = target[Gear] ? 1.0 : 0.0;
            initialized = true;
        }
        target[Hatch] = target[Hatch] && position[Gear] == 1;
        constexpr double duration[Count] = {4.0,3.5,1.25,3.0};
        for (unsigned i=0; i<Count; ++i) {
            const double step = dt/duration[i];
            position[i] += std::max(-step,std::min(step,double(target[i])-position[i]));
        }
    }
};
