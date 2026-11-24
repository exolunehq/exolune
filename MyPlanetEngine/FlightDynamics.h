// Point-mass ship dynamics in world axes. Distances are metres and time is seconds.
#pragma once
#include "FlightFrame.h"
#include "TransportEquipment.h"
#include "CelestialManifest.h"
#include "AtmosphereProfile.hlsli"

namespace FlightDynamics {
constexpr double SeaLevelDensity = 1.225; // kg/m^3
constexpr double EntrySpace = 1000.0 * ATMOSPHERE_HEIGHT_KM;
constexpr double EntryInterface = EntrySpace - 1000.0 * RAYLEIGH_SCALE_HEIGHT;
constexpr double EntryIgnition = .78 * EntrySpace, EntryFloor = .40 * EntrySpace;
constexpr double EntryDuration = 12.0, EntryFade = 3.0;
constexpr double EntryMinimumDescent = 100.0, EntryExitFade = .85;
constexpr double FirstBurnNotch = 25, ThrottleNotches = 30, LaunchAcceleration = 1800, BoostFactor = 5;

inline double Clamp(double x, double lo, double hi) { return std::max(lo, std::min(x, hi)); }
inline double Smooth(double lo, double hi, double x) {
    const double t = Clamp((x - lo) / (hi - lo), 0, 1);
    return t * t * (3 - 2 * t);
}
inline double DensityAtAltitude(double metres) {
    const double height = std::max(0.0, metres) * .001;
    if (height >= ATMOSPHERE_HEIGHT_KM) return 0;
    // Close the rendering atmosphere continuously over its last scale height.
    return std::exp(-height / RAYLEIGH_SCALE_HEIGHT) *
        (1 - Smooth(ATMOSPHERE_HEIGHT_KM - RAYLEIGH_SCALE_HEIGHT, ATMOSPHERE_HEIGHT_KM, height));
}
inline Vec3d Gravity(Vec3d offset, double distance, double radius, double gm) {
    const double r = std::max(distance, radius);
    return offset * (-gm / (r * r * r));
}

struct Environment {
    Vec3d gravity;
    double density, altitude;
};
struct Field {
    double planetRadius;
    Vec3d wind = {};
    std::array<Vec3d, Celestial::Moons.size()> moons = {};
    bool moonsPlaced = false;
    // A confirmed hull tangent is valid very locally. The existing sweep still tests the complete displacement.
    Vec3d supportNormal = {}, supportOrigin = {};

    Environment At(Vec3d position) const {
        const double radius = Length(position), height = radius - planetRadius;
        Environment env = {Gravity(position, radius, planetRadius, Celestial::ExoluneGM * 1e9), DensityAtAltitude(height), height};
        if (moonsPlaced) for (size_t i = 0; i < moons.size(); ++i) {
            const auto& moon = Celestial::Moons[i];
            const Vec3d offset = position - moons[i];
            const double distance = Length(offset);
            if (distance >= Celestial::MoonFrameOuterRadii * moon.radius) continue;
            // The local frame already follows the moon's orbit. Use its own gravity near its surface.
            const double local = Celestial::MoonFrameWeight(distance, moon.radius);
            const Vec3d gravity = Gravity(offset, distance, moon.radius, moon.gravity * moon.radius * moon.radius);
            env.gravity = env.gravity + (gravity - env.gravity) * local;
        }
        return env;
    }
};

struct Cues {
    enum class Passage { Inside, Outside, Descending, Luminous };
    Vec3d airVelocity = {}; // ship velocity relative to air, in world axes
    double density = 0, equivalentAirspeed = 0, dynamicPressurePa = 0, heat = 0, engine = 0;
    Passage passage = Passage::Inside; // ordinary spawns below the atmosphere have no incoming trajectory
    double entrySeconds = 0;

    void Measure(double densityRatio, Vec3d velocity, Vec3d wind) {
        density = densityRatio;
        airVelocity = density > 0 ? velocity - wind : Vec3d{};
        const double equivalentSquared = density * Dot(airVelocity, airVelocity);
        dynamicPressurePa = .5 * SeaLevelDensity * equivalentSquared;
        equivalentAirspeed = std::sqrt(equivalentSquared);
    }
    void AdvanceHeat(double altitude, double verticalSpeed, double dt) {
        if (altitude >= EntrySpace || altitude <= EntryFloor) {
            passage = altitude >= EntrySpace ? Passage::Outside : Passage::Inside;
            entrySeconds = heat = 0;
            return;
        }
        if (dt <= 0) return;
        const double airspeed = Length(airVelocity);
        // Consume the inbound crossing once. The lower retention thresholds let a shallow
        // approach vary in slope, while levelling or applying power later inside cannot relight it.
        if (verticalSpeed >= -25.0 || airspeed < 1400.0)
            passage = Passage::Inside;
        else if (passage == Passage::Outside && altitude <= EntryInterface)
            passage = verticalSpeed <= -EntryMinimumDescent && airspeed >= 1800.0 ? Passage::Descending : Passage::Inside;
        // Sutton-Graves scaling at fixed nose radius gives the relative brightness within a passage.
        const double speedRatio = std::min(airspeed / 2500, 32.0);
        const double flux = std::sqrt(density) * speedRatio * speedRatio * speedRatio;
        if (passage == Passage::Descending && altitude <= EntryIgnition && flux >= .22) {
            passage = Passage::Luminous;
            entrySeconds = 0;
        }
        if (passage != Passage::Luminous) {
            heat = std::max(0.0, heat - dt / EntryExitFade);
            return;
        }
        entrySeconds += dt;
        const double target = Smooth(.055, .52, flux);
        heat += (target - heat) * (-std::expm1(-dt / .70));
        const double end = 1 - Smooth(EntryDuration - EntryFade, EntryDuration, entrySeconds);
        heat = std::min(heat, end * Smooth(EntryFloor, EntryFloor + 6000, altitude));
        if (entrySeconds >= EntryDuration) {
            passage = Passage::Inside;
            heat = 0;
        }
    }

    // An explicitly labelled review pose supplies the preceding steady descent.
    // Its declared radial speed and air flux must pass all the live crossing gates.
    void ReplayIncoming(double altitude, double verticalSpeed, Vec3d velocity, Vec3d wind) {
        *this = {};
        if (altitude > EntryFloor && altitude < EntrySpace && verticalSpeed <= -EntryMinimumDescent) {
            const double duration = (EntrySpace - altitude) / -verticalSpeed;
            const int steps = std::max(1, int(std::ceil(duration * 30)));
            const double dt = duration / steps;
            AdvanceHeat(EntrySpace, verticalSpeed, 0);
            for (int i = 1; i <= steps; ++i) {
                const double height = EntrySpace + verticalSpeed * (i * dt);
                Measure(DensityAtAltitude(height), velocity, wind);
                AdvanceHeat(height, verticalSpeed, dt);
            }
        }
        Measure(DensityAtAltitude(altitude), velocity, wind);
    }
};

struct Controls {
    Vec3d forward, right, up;
    double throttle, strafe, lift; // throttle 0..30, manoeuvring controls -1..1
    bool boost, brake, fullThrust = false;
    double yaw = 0, roll = 0; // pilot rates, positive to the right
    TransportEquipment* transport = nullptr;
    double terrainClearance = 0, descentRate = 0;
    bool supported = false;
};
inline double MoveThrottle(double notch, double detents) {
    return Clamp(notch + detents, 0, ThrottleNotches);
}
inline double Follow(double value, double target, double dt, double response) {
    return value + (target - value) * (-std::expm1(-dt / response));
}
struct Surfaces {
    double wings = 0, airbrakes = 0;

    void Advance(const Cues& air, double deceleration, double dt) {
        const double pressure = air.dynamicPressurePa;
        const double atmosphere = Smooth(.000035, .00034, air.density);
        const double flight = atmosphere * Smooth(20, 62, air.equivalentAirspeed);
        const double load = Smooth(22000, 85000, pressure);
        const double hot = Smooth(.30, .90, air.heat);
        // Under aerodynamic load, sweep back to a useful exposed planform.
        // Reserve full retraction for hover, vacuum and the hot phase of entry.
        const double extension = flight * (1 - .48 * load) * (1 - hot);
        const double brake = Smooth(2, 16, deceleration) * Smooth(90, 850, pressure) *
                             Smooth(.25, .72, wings) * atmosphere * (1 - std::max(load, hot));
        airbrakes = Follow(airbrakes, brake, dt, brake > airbrakes ? .27 : .20);
        // Give an open brake time to clear its frame before the wing sweeps into the nacelle.
        const double target = std::max(extension, .72 * airbrakes);
        wings = Follow(wings, target, dt, target > wings ? .36 : .52);
    }
};
struct Pilot {
    Vec3d previousNose = {};
    double steeringTime = 0; // finish a commanded turn after the stick recentres
    double bank = 0, deceleration = 0;
    double heldNotch = 0;
    bool holding = false, rollReferenceSet = false;
    double rollReference = 0; // unassisted bank last selected by the pilot
    Surfaces surfaces;
};
struct Loads {
    double mainJet = 0, sideJet = 0, liftJet = 0, retroJet = 0;
    Vec3d supportThrust = {};
    Vec3d seatAcceleration = {}; // specific acceleration, including surface support and excluding free fall
};

// Rotate a unit course on the sphere. A half turn follows the pilot's right side when both arcs are equal.
inline Vec3d TurnCourse(Vec3d course, Vec3d target, Vec3d right, double fraction, double maxAngle) {
    const double cosine = Clamp(Dot(course, target), -1, 1);
    if (cosine > 1 - 1e-13 || fraction <= 0) return course;
    Vec3d tangent = target - course * cosine;
    const double sine = Length(tangent);
    if (sine < 1e-8) tangent = right - course * Dot(right, course);
    const double angle = std::min(maxAngle, fraction * std::atan2(sine, cosine));
    return course * std::cos(angle) + Normalize(tangent) * std::sin(angle);
}

inline double WingLift(const Cues& air, const Controls& c, Vec3d flow, Vec3d gravity, double wings) {
    const double weight = Length(gravity);
    const double bankCos = weight > 1e-8 ? std::abs(Dot(c.up, gravity)) / weight : 1;
    const double trim = weight * Smooth(22, 80, air.equivalentAirspeed) / std::max(.60, bankCos);
    const double incidence = -Dot(flow, c.up);
    const double forwards = std::max(0.0, Dot(flow, c.forward));
    return Clamp((trim + (.008 + .003 * wings) * air.dynamicPressurePa * incidence) * forwards * forwards, -40, 40);
}

inline void AssistBank(Controls& c, Pilot& pilot, const Cues& air, Vec3d gravity, double dt) {
    const double weight = Length(gravity);
    const double pitch = weight > 1e-8 ? std::abs(Dot(c.forward, gravity)) / weight : 0;
    const double authority = Smooth(28, 85, air.equivalentAirspeed)
                           * (1 - Smooth(.62, .92, pitch)) * (1 - Smooth(.05, .50, std::abs(c.roll)));
    const double target = pilot.holding ? 0 : .43 * authority * Clamp(c.yaw, -1, 1);
    const double bank = Follow(pilot.bank, target, dt, .34);
    double unwind = 0;
    if (pitch < .92 && weight > 1e-8) {
        const Vec3d levelRight = Normalize(Cross(gravity * (-1 / weight), c.forward));
        const Vec3d levelUp = Cross(c.forward, levelRight);
        const double residual = std::remainder(std::atan2(Dot(c.up,levelRight), Dot(c.up,levelUp)) - pilot.bank,
                                               6.283185307179586);
        if (!pilot.rollReferenceSet || std::abs(c.roll) > .05) {
            pilot.rollReference = residual;
            pilot.rollReferenceSet = true;
        }
        const double drift = std::remainder(residual - pilot.rollReference, 6.283185307179586);
        unwind = Clamp(drift, -.56, .56) * -std::expm1(-authority * dt / 1.15);
    }
    c.up = Rotate(c.up, c.forward, pilot.bank - bank + unwind);
    c.right = Cross(c.up, c.forward);
    pilot.bank = bank;
}

inline void BankTurn(Controls& c, Vec3d flow, double airspeed, double wingLift, Vec3d gravity, double dt) {
    const double weight = Length(gravity);
    if (weight < 1e-8 || airspeed < 1 || wingLift == 0) return;
    const Vec3d vertical = gravity * (-1 / weight);
    const Vec3d right = Cross(vertical, c.forward);
    const double horizontal = Length(right);
    if (horizontal < .1) return;
    const Vec3d liftAxis = c.up - flow * Dot(c.up, flow);
    const double rate = wingLift * Dot(liftAxis, right) / (airspeed * horizontal * horizontal);
    if (std::abs(rate) < 1e-9) return;
    const double angle = Clamp(rate, -1.2, 1.2) * dt;
    c.forward = Rotate(c.forward, vertical, angle);
    c.up = Rotate(c.up, vertical, angle);
    c.right = Cross(c.up, c.forward);
}

inline Vec3d AerodynamicDelta(const Cues& air, const Controls& c, Vec3d flow, double speed,
                              double wingLift, double airbrakes, double dt) {
    if (speed < 1e-7) return {};
    const double axial = Dot(flow, c.forward), upFlow = Dot(flow, c.up);
    // A broadside hull presents four times its axial drag area. The exact quadratic decay cannot reverse the flow.
    const double inverseBallistic = (1 + 3 * (1 - axial * axial)) / 2400.0; // m^2/kg
    const double dragRate = .5 * SeaLevelDensity * air.density * speed * inverseBallistic;
    const double panelRate = .5 * SeaLevelDensity * air.density * speed * airbrakes / 850.0;
    // Blend into finite fractional deceleration at arcade transfer speeds. Cutting power still leaves a coast.
    const double effectiveRate = dragRate / (1 + dragRate / 1.2) + panelRate / (1 + panelRate / .4);
    const double afterDrag = speed / (1 + effectiveRate * dt);
    // The fin removes sideslip sooner than the wings remove angle of attack. Jets can deliberately slide the hull.
    const double grip = Smooth(18, 75, air.equivalentAirspeed) *
                        (1 - std::max(std::abs(c.strafe), std::abs(c.lift)));
    const Vec3d straight = Normalize(c.forward * std::max(.1, axial) + c.up * (.70 * upFlow));
    const Vec3d tracking = TurnCourse(flow, straight, c.right, -std::expm1(-3.4 * grip * dt), 2.4 * dt);
    const Vec3d liftAxis = c.up - tracking * Dot(tracking, c.up);
    const Vec3d turned = tracking + liftAxis * (wingLift * dt / speed);
    return Normalize(turned) * afterDrag - air.airVelocity;
}

inline Vec3d Limited(Vec3d v, double limit) {
    const double magnitude = Length(v);
    return magnitude > limit ? v * (limit / magnitude) : v;
}
inline Vec3d SurfaceVelocity(Vec3d velocity, Vec3d normal) {
    const double into = Dot(velocity, normal);
    if (into >= 0) return velocity;
    const Vec3d tangent = velocity - normal * into;
    // Coulomb friction uses the support impulse. Gentle slopes and a light crosswind allow a landed hull to rest.
    return tangent - Limited(tangent, -.55 * into);
}

inline double ThrottlePower(double notch) {
    // Retain the old 35% spacing and make both ends exact, including fractional wheel detents.
    static const double range = std::expm1(std::log(1.35) * ThrottleNotches);
    return std::expm1(std::log(1.35) * Clamp(notch, 0, ThrottleNotches)) / range;
}
inline double CruiseSpeed(double notch) {
    // Low detents start at walking speed, reach 100 m/s at 15, then increase by 35% per notch.
    const double n = Clamp(notch, 0, ThrottleNotches);
    if (n < 15) return 5 * n + 25 * std::expm1(std::log(1.35) * n) / std::expm1(std::log(1.35) * 15);
    return 100 * std::pow(1.35, n - 15);
}
inline double TransferAcceleration(double speed) {
    // A high-power burn gains authority as it picks up speed. Only the extra acceleration approaches an asymptote.
    return .5 * speed / (1 + speed / 5e6);
}
inline double ThrustAgainstAir(double demand, double airAcceleration) {
    if (demand == 0) return 0;
    const double opposition = -std::copysign(1.0, demand) * airAcceleration;
    // Allow air to consume up to one fifth of a commanded thrust. Uncommanded axes keep their full aerodynamic force.
    return demand + std::copysign(std::max(0.0, opposition - .2 * std::abs(demand)), demand);
}

inline double BrakeLimit(double speed) {
    return 19 + 31 * Smooth(20, 190, speed) + 64 * Smooth(200, 1700, speed)
        + .42 * speed * Smooth(2600, 45000, speed);
}

inline Loads Advance(double seconds, Vec3d& position, Vec3d& velocity, Cues& cues,
                     Controls& c, Pilot& pilot, const Field& field) {
    Loads loads;
    const double duration = Clamp(seconds, 0, .1);
    const int steps = std::max(1, int(std::ceil(60 * duration - 1e-6)));
    const double dt = duration / steps;
    const double notch = c.fullThrust ? ThrottleNotches : c.throttle;
    const double target = CruiseSpeed(notch);
    const bool translating = c.strafe != 0 || c.lift != 0;
    const bool burn = notch >= FirstBurnNotch || (c.boost && (notch > 0 || !translating));
    const double power = std::max(ThrottlePower(notch), burn && c.boost ? .65 : 0.0);
    const double boost = c.boost ? BoostFactor : 1;
    const double jetAxes = std::max(1.0, std::hypot(c.strafe, c.lift));
    const Vec3d turn = c.forward - pilot.previousNose;
    const bool firstPose = Dot(pilot.previousNose, pilot.previousNose) < .5;
    const bool turned = firstPose ? Dot(velocity, c.forward) < .999 * Length(velocity) : Dot(turn, turn) > 1e-12;
    if (turned || translating) pilot.steeringTime = 1.8;
    if (!c.brake && (c.throttle != pilot.heldNotch || translating || c.fullThrust || c.boost))
        pilot.holding = false;
    for (int i = 0; i < steps && dt > 0; ++i) {
        const Environment env = field.At(position);
        cues.Measure(env.density, velocity, field.wind);
        cues.AdvanceHeat(env.altitude, Dot(position, velocity) / std::max(1.0, field.planetRadius + env.altitude), dt);
        const double airspeed = Length(cues.airVelocity);
        const Vec3d flow = airspeed > 1e-7 ? cues.airVelocity * (1 / airspeed) : Vec3d{};
        const double speed = Length(velocity);
        const double atmosphere = std::max(Smooth(.0001, .02, env.density), Smooth(60, 1800, cues.dynamicPressurePa));
        if (c.brake && !pilot.holding && speed <= .22) {
            pilot.holding = true;
            pilot.heldNotch = c.throttle;
        }
        const bool braking = c.brake || pilot.holding;
        const double overrun = notch > 0 && !burn
            ? std::max(0.0, Dot(velocity - field.wind * atmosphere, c.forward) - target) : 0;
        const double excess = pilot.holding ? 0 : c.brake ? speed : overrun;
        const double requested = std::min(BrakeLimit(speed), 1.55 * excess);
        pilot.deceleration = Follow(pilot.deceleration, requested, dt, .33);
        if (c.transport) {
            c.transport->Advance(dt, c.terrainClearance, c.descentRate, speed, cues.density,
                cues.equivalentAirspeed, cues.dynamicPressurePa, cues.heat, pilot.deceleration,
                c.brake, !pilot.holding && (burn || c.throttle > 0 || c.lift > 0), c.supported);
            pilot.surfaces.wings = Smooth(.27, .91, c.transport->position[TransportEquipment::Wings]);
            pilot.surfaces.airbrakes = c.transport->position[TransportEquipment::Brake];
        } else pilot.surfaces.Advance(cues, pilot.deceleration, dt);
        AssistBank(c, pilot, cues, env.gravity, dt);
        const double liftForce = WingLift(cues, c, flow, env.gravity, pilot.surfaces.wings);
        if (!braking) BankTurn(c, flow, airspeed, liftForce, env.gravity, dt);
        const Vec3d airDelta = AerodynamicDelta(cues, c, flow, airspeed, liftForce, pilot.surfaces.airbrakes, dt);
        const Vec3d air = airDelta * (1 / dt), passive = env.gravity + air;
        // A stick or throttle command steers through an arc. Once it settles, an unpowered ship can orbit freely.
        const double guide = (!braking && !translating && (notch > 0 || burn || pilot.steeringTime > 0)) ?
                             (1 - atmosphere) * Smooth(.02, .5, speed) : 0;
        Vec3d steering = {}, engineAxis = c.forward;
        if (guide > 0) {
            const Vec3d course = velocity * (1 / speed);
            if (Dot(course, c.forward) < .9999985) {
                const Vec3d guided = TurnCourse(course, c.forward, c.right, -std::expm1(-7 * guide * dt), 5.6 * dt);
                steering = (guided - course) * (speed / dt);
                engineAxis = TurnCourse(c.forward, guided, c.right, guide, 3.141592653589793);
            }
        }
        pilot.steeringTime = std::max(0.0, pilot.steeringTime - dt);
        // Midpoint power sampling keeps sustained burns consistent at different frame rates.
        const double initialDrive = LaunchAcceleration * power + TransferAcceleration(speed) * power * power;
        const double transfer = TransferAcceleration(speed + .5 * dt * initialDrive * boost);
        const double drive = LaunchAcceleration * power + transfer * power * power;
        const double jets = 24 + .4 * drive;
        double mainReference = burn ? LaunchAcceleration + transfer : std::max(24.0, target / .35);
        double jetReference = jets;
        Vec3d thrust, stopped = {};
        loads.supportThrust = {};
        loads.retroJet = 0;
        if (pilot.holding) {
            // At zero speed the stabilizers cancel external forces, including the climate wind.
            stopped = Limited(velocity, std::max(0.0, speed - 8 * dt));
            thrust = (stopped - velocity) * (1 / dt) - passive;
            loads.supportThrust = thrust;
            mainReference = jetReference = 24;
        } else if (c.brake) {
            const double support = 1 - Smooth(1, 17, speed);
            loads.supportThrust = env.gravity * (-support);
            const Vec3d glide = velocity + (passive + loads.supportThrust) * dt;
            stopped = Limited(glide, std::max(0.0, speed - pilot.deceleration * dt));
            const Vec3d reverse = (stopped - glide) * (1 / dt);
            thrust = reverse + loads.supportThrust;
            mainReference = jetReference = std::max(24.0, pilot.deceleration);
            loads.retroJet = Clamp(Length(reverse) / mainReference, 0, 1);
        } else {
            const double forwardSpeed = Dot(velocity + steering * dt - field.wind * atmosphere, engineAxis);
            const double cruise = (target - forwardSpeed) * (-std::expm1(-dt / .35) / dt);
            double ahead = 0;
            if (burn)
                ahead = ThrustAgainstAir(std::max(drive * boost, cruise), Dot(air, engineAxis));
            else if (notch > 0) {
                const double natural = Dot(passive, engineAxis);
                ahead = forwardSpeed > target
                    ? std::min(0.0, -std::min(pilot.deceleration, (forwardSpeed - target) / dt) - natural)
                    : cruise - natural;
                loads.retroJet = Clamp(-ahead / std::max(24.0, pilot.deceleration), 0, 1);
            }
            const double side = ThrustAgainstAir(c.strafe / jetAxes * jets * boost, Dot(air, c.right));
            const double lift = ThrustAgainstAir(c.lift / jetAxes * jets * boost, Dot(air, c.up));
            thrust = engineAxis * ahead + c.right * side + c.up * lift + steering;
        }
        const double axialJet = Clamp(Dot(thrust, c.forward) / mainReference, -1, 1);
        loads.mainJet = braking ? 0 : std::max(0.0, axialJet);
        loads.sideJet = Clamp(Dot(thrust, c.right) / jetReference, -1, 1);
        loads.liftJet = Clamp(Dot(thrust, c.up) / jetReference, -1, 1);
        cues.engine = braking ? Clamp(Length(thrust) / mainReference, 0, 1) :
            Clamp(std::hypot(axialJet, std::hypot(loads.sideJet, loads.liftJet)), 0, 1);

        Vec3d next = braking ? stopped : velocity + (passive + thrust) * dt;
        const Vec3d fromSupport = position - field.supportOrigin;
        if (Dot(field.supportNormal, field.supportNormal) > .5 && Dot(fromSupport, fromSupport) < 1 &&
            Dot(fromSupport, field.supportNormal) < .02)
            next = SurfaceVelocity(next, field.supportNormal);
        loads.seatAcceleration = loads.seatAcceleration + (next - velocity - env.gravity * dt) * (1 / duration);
        position = position + (velocity + next) * (.5 * dt);
        velocity = next;
    }
    pilot.previousNose = c.forward;
    cues.Measure(DensityAtAltitude(Length(position) - field.planetRadius), velocity, field.wind);
    return loads;
}
}
