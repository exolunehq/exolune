// Functional checks of the native force and telemetry path. No renderer or GPU.
#include "../../MyPlanetEngine/FlightDynamics.h"
#include <cstdio>
#include <cstdlib>

namespace {
using namespace FlightDynamics;
void Check(bool ok, const char* reason) {
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", reason); std::exit(1); }
}
constexpr double Radius = 6378000;
const Controls Level = {{0,0,1}, {1,0,0}, {0,1,0}, 0, 0, 0, false, false};
struct Flight {
    Vec3d position = {0, Radius + 500, 0}, velocity = {};
    Cues cues;
    Pilot pilot;
    Vec3d nose = Level.forward;
    Loads Run(const Field& field, Controls controls, int frames, int fps) {
        Loads loads;
        for (int i = 0; i < frames; ++i)
            loads = Advance(1.0 / fps, position, velocity, cues, controls, pilot, field);
        nose = controls.forward;
        return loads;
    }
};
Controls Wheel(double detents) {
    Controls controls = Level;
    controls.throttle = MoveThrottle(controls.throttle, detents);
    return controls;
}
double AngleBetween(Vec3d a, Vec3d b) {
    return std::atan2(Length(Cross(a, b)), Dot(a, b)) * (180 / 3.141592653589793);
}

void CheckManualThrust(const Field& planet, const Field& lunar) {
    Check(ThrottlePower(0)==0 && ThrottlePower(30)==1, "the control lever covers the full engine range");
    for (double n=.25; n<=30; n+=.25)
        Check(ThrottlePower(n)>ThrottlePower(n-.25) && CruiseSpeed(n)>CruiseSpeed(n-.25),
              "every fractional wheel notch increases cruise and thrust");
    Check(MoveThrottle(15,-18)==0 && MoveThrottle(15,18)==30 && MoveThrottle(15,-.25)==14.75,
          "the wheel reads fractional deltas, reverse scrolls and both stops");
    const Vec3d launch[] = {{0,Radius+1450,0}, {0,Radius+25,0},
                           lunar.moons[1]+Vec3d{0,Celestial::Moons[1].radius+25,0}, {0,1e12,0}};
    const char* names[] = {"land (+1450 m)", "sea (+25 m)", "moon 2 (+25 m)", "deep space"};
    Controls full = Level; full.throttle = 30;
    Controls key = Level; key.fullThrust = true;
    Controls boost = key; boost.boost = true;
    for (int i=0; i<4; ++i) {
        const Field& field = i==2 ? lunar : planet;
        Flight normal; normal.position=launch[i];
        Flight keyed=normal, boosted=normal;
        normal.Run(field,full,120,60); keyed.Run(field,key,120,60); boosted.Run(field,boost,60,60);
        Check(Length(normal.velocity-keyed.velocity)<1e-8, "the momentary full-thrust key matches full lever travel");
        Check(normal.velocity.z>4000 && boosted.velocity.z>18000, "full power and boost accelerate immediately over every surface");
        const double firstSpeed=normal.velocity.z;
        normal.Run(field,full,120,60);
        Check(normal.velocity.z>1.6*firstSpeed, "continuous thrust keeps building speed at the top notch");
        double measured[3] = {};
        for (int j=0; j<3; ++j) {
            const Controls trim=Wheel(1+2*j);
            Flight fine; fine.position=launch[i];
            fine.Run(field,trim,1,60);
            Check(fine.velocity.z>.20, "the first wheel event moves the hull on the very next step");
            fine.Run(field,trim,59,60);
            measured[j]=fine.velocity.z;
            Check(measured[j]>.89*CruiseSpeed(trim.throttle) && measured[j]<1.04*CruiseSpeed(trim.throttle),
                  "low wheel detents reach a useful and repeatable speed in one second");
        }
        Check(measured[0]>4.5 && measured[1]>14 && measured[2]>24, "wheel detents 1, 3 and 5 are distinct launch speeds");
        std::printf("%s: notches 1/3/5 at 1 s %.1f / %.1f / %.1f m/s; full 2 s %.0f, boost 1 s %.0f m/s.\n",
                    names[i], measured[0],measured[1],measured[2],firstSpeed,boosted.velocity.z);
    }

    Flight takeoff; takeoff.position=launch[1];
    Controls precision=Level; precision.throttle=5; precision.fullThrust=true;
    takeoff.Run(planet,precision,60,60);
    precision.fullThrust=false;
    const double beforeFine=takeoff.velocity.z;
    takeoff.Run(planet,precision,60,60);
    Check(takeoff.velocity.z<.25*beforeFine && takeoff.velocity.z>CruiseSpeed(5),
          "releasing full thrust backs down toward the parked wheel setting");
    takeoff.Run(planet,precision,300,60);
    Check(std::abs(takeoff.velocity.z-CruiseSpeed(5))<1, "the pilot can recover their fine speed after the burn");
    for (Controls throttle : {Wheel(25), Wheel(29), Wheel(3), Level}) {
        throttle.boost = throttle.throttle < 25;
        Flight fast; fast.position=launch[1]; fast.velocity={0,0,4e4};
        fast.Run(planet,throttle,12,60);
        Check(fast.velocity.z>40010, "upper detents and boost at low or zero wheel keep accelerating in dense air");
    }
    Flight lateral; lateral.position=launch[1]; lateral.velocity={4000,0,0};
    Controls side=Level; side.strafe=1;
    lateral.Run(planet,side,10,60);
    Check(lateral.velocity.x>4003, "manual lateral jets keep accelerating against dense air at high speed");

    Flight glide; glide.position=launch[1]; glide.velocity={0,0,5000};
    glide.Run(planet,Level,1,60);
    Check(glide.velocity.z>4900 && glide.velocity.z<5000 && glide.cues.engine==0,
          "cutting a fast atmospheric burn retains momentum on the first frame");
    glide.Run(planet,Level,59,60);
    Check(glide.velocity.z>2000 && glide.velocity.z<4400, "air bleeds speed progressively during a coast");
    std::printf("Sea-level coast: 5000 to %.0f m/s in 1 s, engines at %.0f.\n",glide.velocity.z,glide.cues.engine);
    Flight transfer; transfer.position=launch[3]; transfer.Run(planet,boost,30*60,60);
    Check(transfer.position.z>2.8e8, "the full drive can cover the outer moon's distance on a planetary timescale");
    for (Vec3d start : {launch[1],launch[2],launch[3]}) {
        Flight fast; fast.position=start; fast.velocity={0,0,5e8};
        fast.Run(lunar,full,1,60);
        Check(fast.velocity.z>5e8+10000 && std::isfinite(fast.cues.dynamicPressurePa),
              "a powered ship continues to accelerate above light speed with no world-dependent governor");
    }
    Controls stop=Level; stop.brake=true;
    Flight retro; retro.position=launch[3]; retro.velocity={2e6,-4e5,3e6};
    const double beforeStop=Length(retro.velocity);
    retro.Run(planet,stop,60,60);
    Check(Length(retro.velocity)<.22*beforeStop && Length(retro.velocity)>.18*beforeStop,
          "the powered brake scales to interplanetary cruise in every axis");
}

void CheckFlightAssist(const Field& field, const Field& lunar) {
    for (double notch : {1.0,15.0}) for (double degrees : {90.0,180.0}) for (bool powered : {false,true}) {
        const double cruiseSpeed=CruiseSpeed(notch);
        Flight flight; flight.position={0,1e12,0}; flight.velocity={0,0,cruiseSpeed};
        Controls turn=powered ? Wheel(notch) : Level;
        flight.Run(field,turn,1,60);
        FlightFrame::Turn(turn.forward,turn.up,degrees * (3.141592653589793/180),0,0);
        turn.right=Cross(turn.up,turn.forward);
        double lowest=cruiseSpeed;
        for (int frame=0; frame<60; ++frame) {
            flight.Run(field,turn,1,60);
            lowest=std::min(lowest,Length(flight.velocity));
        }
        const double error=AngleBetween(flight.velocity,turn.forward);
        Check(error<1 && lowest>cruiseSpeed-.01 && std::abs(Length(flight.velocity)-cruiseSpeed)<.01,
              "powered and coasting turns rotate the course through 90 or 180 degrees without stopping");
        std::printf("Vacuum %g-degree turn, wheel %g: %.2f degrees remaining at 1 s, minimum %.2f m/s.\n",
                    degrees,turn.throttle,error,lowest);
    }
    Flight movingStick; movingStick.position={0,1e12,0}; movingStick.velocity={0,0,100};
    Controls stick=Level;
    for (int frame=0; frame<90; ++frame) {
        FlightFrame::Turn(stick.forward,stick.up,1.0/60,0,0); // maximum mouse yaw from UpdateShip
        stick.right=Cross(stick.up,stick.forward);
        movingStick.Run(field,stick,1,60);
    }
    Check(AngleBetween(movingStick.velocity,stick.forward)<9, "a continuous full-stick turn carries the coasting course");
    movingStick.Run(field,stick,60,60);
    Check(AngleBetween(movingStick.velocity,stick.forward)<.2, "recentering the stick finishes a coasting turn");

    Flight flight; Controls cruise=Wheel(15);
    flight.Run(field,cruise,300,60);
    const double altitude=flight.position.y, cruiseSpeed=flight.velocity.z;
    flight.Run(field,cruise,300,60);
    Check(std::abs(cruiseSpeed-100)<.1 && std::abs(flight.velocity.z-cruiseSpeed)<.02 &&
          std::abs(flight.position.y-altitude)<1, "a level mid-lever cruise carries the ship's weight and holds its airspeed");
    cruise.throttle=MoveThrottle(cruise.throttle,-12);
    flight.Run(field,cruise,180,60);
    Check(flight.velocity.z>15 && flight.velocity.z<17 && flight.velocity.y < -7,
          "scrolling back slows the ship to its approach speed and unloads its wings");
    std::printf("Wing-borne cruise %.1f m/s; wheel 15 to 3, %.1f m/s forward and %.1f m/s vertical after 3 s.\n",
                cruiseSpeed,flight.velocity.z,flight.velocity.y);

    Flight twins; twins.velocity={0,0,100};
    Controls bank=Wheel(15);
    FlightFrame::Turn(bank.forward,bank.up,0,0,3.141592653589793/4);
    bank.right=Cross(bank.up,bank.forward);
    Flight mirror=twins;
    Controls left=bank; left.up.x*=-1; left.right=Cross(left.up,left.forward);
    const double startingY=twins.position.y;
    twins.Run(field,bank,300,60); mirror.Run(field,left,300,60);
    const double bankAngle=AngleBetween(twins.velocity,Level.forward);
    Check(twins.velocity.x>35 && std::abs(twins.velocity.x+mirror.velocity.x)<.03 &&
          AngleBetween(twins.nose,twins.velocity)<1 && std::abs(twins.position.y-startingY)<2,
          "a sustained bank curves heading and track together with bounded height loss");
    std::printf("Bank 45 degrees: heading change %.1f degrees in 5 s at 100 m/s, height change %.2f m.\n",
                bankAngle,twins.position.y-startingY);
    Flight moon; moon.position=lunar.moons[1]+Vec3d{0,Celestial::Moons[1].radius+50,0}; moon.velocity={0,0,100};
    bank.throttle=0;
    moon.Run(lunar,bank,180,60);
    Check(std::abs(moon.velocity.x)<1e-6 && AngleBetween(moon.nose,Level.forward)<1e-5 && moon.velocity.y<-.5,
          "rolling alone in lunar vacuum produces no aerodynamic turn or support");

    Field crosswind=field; crosswind.wind={16,0,0};
    Flight cross; cross.velocity={0,0,100};
    cross.Run(crosswind,Wheel(15),180,60);
    Check(cross.velocity.x>15.5 && std::abs(cross.cues.airVelocity.x)<.5,
          "sideslip closes relative to the moving air while the ground track drifts downwind");
    std::printf("Crosswind 16 m/s: ground drift %.2f m/s, remaining sideslip %.2f m/s.\n",
                cross.velocity.x,cross.cues.airVelocity.x);

    Flight onGround;
    Field pad=field; pad.supportNormal=Level.up; pad.supportOrigin=onGround.position;
    onGround.Run(pad,Wheel(1),15,60);
    Check(onGround.position.z>.2 && onGround.velocity.z>1.5 && onGround.velocity.y==0,
          "one wheel detent starts a supported hull despite ground friction");

    Flight a; a.position={0,1e12,0}; a.velocity={0,0,100}; a.pilot.previousNose=Level.forward;
    Flight b=a, d=a;
    Controls reverse=Level; reverse.forward=Level.forward * -1; reverse.right=Level.right * -1;
    a.Run(field,reverse,60,60); b.Run(field,reverse,10,10); d.Run(field,reverse,144,144);
    Check(Length(a.position-b.position)<1e-6 && Length(a.velocity-b.velocity)<1e-6 &&
          AngleBetween(a.velocity,d.velocity)<.1 && Length(a.position-d.position)<.1,
          "coasting half turns trace the same arc at 10, 60 and 144 Hz");
}
}

void CheckFlightDynamics() {
    Field field = {};
    field.planetRadius = Radius;
    const double g = Celestial::ExoluneGM * 1e9 / (Radius * Radius);
    Check(std::abs(Length(field.At({0,2*Radius,0}).gravity) - g*.25) < 1e-9, "inverse-square planetary gravity");
    Check(DensityAtAltitude(0) == 1 && std::abs(DensityAtAltitude(8000) - std::exp(-1.0)) < 1e-14, "atmosphere scale height");
    Check(DensityAtAltitude(99999) < 1e-11 && DensityAtAltitude(100000) == 0, "continuous top of the atmosphere");
    Field lunar = field;
    lunar.moonsPlaced = true;
    for (size_t i = 0; i < lunar.moons.size(); ++i) lunar.moons[i] = {double(i+1)*1e8,0,0};
    for (size_t i = 0; i < lunar.moons.size(); ++i) {
        const auto& moon = Celestial::Moons[i];
        const auto local = lunar.At(lunar.moons[i] + Vec3d{0,moon.radius,0});
        Check(Length(local.gravity - Vec3d{0,-moon.gravity,0}) < 1e-9 && local.density == 0, "airless moon's manifest gravity");
        const Vec3d atEdge = lunar.moons[i] + Vec3d{0,Celestial::MoonFrameOuterRadii*moon.radius,0};
        Check(Length(lunar.At(atEdge-Vec3d{0,1,0}).gravity-lunar.At(atEdge+Vec3d{0,1,0}).gravity) < 1e-6,
              "continuous primary to lunar handover");
    }
    CheckManualThrust(field,lunar);
    CheckFlightAssist(field,lunar);

    Cues air;
    const Vec3d wind = {12,0,0};
    air.Measure(1,wind,wind);
    Check(air.dynamicPressurePa == 0, "comoving with the wind produces no aerodynamic pressure");
    air.Measure(.25,wind+Vec3d{0,0,100},wind);
    Check(std::abs(air.equivalentAirspeed-50) < 1e-9 && std::abs(air.dynamicPressurePa-.5*SeaLevelDensity*2500) < 1e-9,
          "equivalent airspeed and pressure share the relative flow");
    air.Measure(1,{0,0,200},{});
    const Vec3d gravity={0,-9.81,0};
    auto aerodynamic=[&](const Controls& hull) {
        const Vec3d flow=Normalize(air.airVelocity);
        return AerodynamicDelta(air,hull,flow,Length(air.airVelocity),WingLift(air,hull,flow,gravity),.1);
    };
    const Vec3d upright = aerodynamic(Level);
    Controls bank = Level; bank.up = Level.right; bank.right = Level.up * -1;
    const Vec3d rolled = aerodynamic(bank);
    Check(upright.y>0 && rolled.x>0 && upright.z<0 && std::abs(rolled.y)<1e-9, "lift banks with the hull and drag opposes the flow");
    air.Measure(1,{0,0,2e7},{});
    const Vec3d slowed = air.airVelocity + aerodynamic(Level);
    Check(slowed.z>0 && Length(slowed)<Length(air.airVelocity), "a high-speed entry cannot reverse quadratic drag");

    Flight coast;
    coast.position={0,1e12,0}; coast.velocity={0,0,180};
    const auto freeFall = coast.Run(field,Level,120,60);
    Check(Length(coast.velocity-Vec3d{0,0,180})<1e-6 && coast.cues.engine==0 && coast.cues.dynamicPressurePa==0,
          "cut engines conserve straight-line velocity in deep space");
    Check(Length(freeFall.seatAcceleration)<1e-9, "free fall has no seat load");
    Flight orbit;
    orbit.position = {0,Radius+250000,0};
    const double orbitRadius = Length(orbit.position);
    orbit.velocity = {0,0,std::sqrt(Celestial::ExoluneGM*1e9/orbitRadius)};
    orbit.Run(field,Level,1200,10);
    Check(std::abs(Length(orbit.position)-orbitRadius)<2 && orbit.position.z>900000 &&
          orbit.cues.engine==0 && orbit.cues.heat==0, "an unpowered orbital arc curves under gravity in vacuum");
    Flight fall;
    fall.Run(field,Level,120,60);
    Check(fall.velocity.y < -18 && fall.position.y < Radius+482, "the idle hull falls in air");
    Flight landed;
    Field support = field;
    support.supportNormal = {0,1,0}; support.supportOrigin = landed.position; support.wind = wind;
    const auto resting = landed.Run(support,Level,120,60);
    Check(Length(landed.position-support.supportOrigin)<1e-9 && Length(landed.velocity)<1e-12 &&
          resting.seatAcceleration.y > 9 && landed.cues.engine==0, "a settled hull rests on its support in a crosswind");
    Controls rise = Level; rise.lift = 1;
    landed.Run(support,rise,120,60);
    Check(landed.position.y>support.supportOrigin.y+12 && landed.cues.engine>.1, "a low-speed vertical jet can lift off");

    Controls brake = Level; brake.brake = true;
    Flight held;
    const Vec3d start = held.position;
    held.Run(field,brake,120,60);
    Check(Length(held.position-start)<1e-9 && held.cues.engine>.2, "powered hold balances gravity");
    held.Run(field,Level,60,60);
    Check(held.position.y<start.y-4 && held.cues.engine==0, "releasing hold restores descent");
    Flight braking; braking.velocity={45,-2,90};
    const double beforeBrake = Length(braking.velocity);
    braking.Run(field,brake,1,60);
    Check(Length(braking.velocity)<beforeBrake && Length(braking.velocity)>beforeBrake*.95 && braking.cues.engine>.9,
          "a transverse braking burn has finite authority");
    braking.Run(field,brake,420,60);
    Check(Length(braking.velocity)<.5, "sustained braking settles all three axes");
    Controls cruise = Level; cruise.throttle=22; cruise.strafe=.5;
    Flight ref; ref.velocity={30,0,95};
    Flight slow=ref, fast=ref;
    ref.Run(field,cruise,240,60); slow.Run(field,cruise,40,10); fast.Run(field,cruise,576,144);
    Check(Length(ref.position-slow.position)<1e-5 && Length(ref.velocity-slow.velocity)<1e-6,
          "a tenth-second frame subdivides into the same six flight steps");
    Check(Length(ref.position-fast.position)<1 && Length(ref.velocity-fast.velocity)<.5,
          "flight response converges at high frame rates");
    std::puts("PASS: gravity, wind, inertial coasting, surface support, VTOL, braking and frame pacing.");
}
