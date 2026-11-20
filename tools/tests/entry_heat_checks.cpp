// Functional checks of the same passage signal used by the glass, particles, gauge and audio.
#include "../../MyPlanetEngine/FlightDynamics.h"
#include <cstdio>
#include <cstdlib>

namespace {
using namespace FlightDynamics;
constexpr double Radius = 6378000, Rad = 3.14159265358979323846 / 180;

void Require(bool ok, const char* message) {
    if (!ok) { std::fprintf(stderr, "FAIL: %s\n", message); std::exit(1); }
}
Vec3d Velocity(double speed, double vertical) {
    return {0, vertical, std::sqrt(std::max(0.0, speed * speed - vertical * vertical))};
}
void Sample(Cues& cues, double altitude, double vertical, double speed, double dt) {
    cues.Measure(DensityAtAltitude(altitude), Velocity(speed, vertical), {});
    cues.AdvanceHeat(altitude, vertical, dt);
}
struct PassageResult { double first = -1, last = 0, peak = 0, firstHeight = 0, lastHeight = 0, endSpeed = 0; };
PassageResult Fly(double angle, double speed, int fps) {
    Field field = {}; field.planetRadius = Radius;
    Vec3d position = {0, Radius + EntrySpace + 2000, 0};
    Vec3d velocity = Velocity(speed, -speed * std::sin(angle * Rad));
    Controls coast = {}; coast.forward = velocity * (1 / speed); coast.right = {1,0,0};
    coast.up = Cross(coast.forward, coast.right);
    Pilot pilot; pilot.previousNose = coast.forward;
    const double dt = 1.0 / fps;
    Cues cues;
    PassageResult result;
    bool ended = false;
    for (int i = 0; i < 220 * fps; ++i) {
        Advance(dt, position, velocity, cues, coast, pilot, field);
        const double altitude = Length(position) - Radius, time = (i + 1) * dt;
        if (cues.heat > 0) {
            Require(!ended && altitude <= EntryIgnition + 1 && cues.dynamicPressurePa > 0 && cues.engine == 0,
                    "only one unpowered, pressure-bearing entry in a continuous descent");
            if (result.first < 0) {
                result.first = time;
                result.firstHeight = altitude;
            }
            result.peak = std::max(result.peak, cues.heat);
            result.last = time;
            result.lastHeight = altitude;
        } else if (result.first >= 0 && !ended) {
            ended = true;
            result.endSpeed = Length(velocity);
        }
        if (altitude < EntryFloor - 1000) break;
    }
    Require(ended && result.peak > .35 && result.last - result.first <= EntryDuration + dt,
            "a genuine atmospheric transit produces a visible, time-limited pulse");
    std::printf("Unpowered %.0f deg at %g km/s: heat %.2f over %.2f s from %.1f to %.1f km, %.0f m/s at extinction.\n",
                angle, speed * .001, result.peak, result.last - result.first,
                result.firstHeight * .001, result.lastHeight * .001, result.endSpeed);
    return result;
}
}

void CheckEntryHeat() {
    using namespace FlightDynamics;
    for (double altitude : {1500.0, 57000.0, 79000.0}) {
        Cues spawn;
        for (int i = 0; i < 100; ++i) Sample(spawn, altitude - i, -400.0, 5e5, .1);
        Require(spawn.heat == 0, "an unlabelled fast spawn lacks an incoming crossing");
    }
    Cues slow;
    Sample(slow, 105000, -150, 250, .1); Sample(slow, 91000, -150, 250, .1);
    for (int i = 0; i < 50; ++i) Sample(slow, 70000 - i * 100.0, -1000, 15000, .1);
    Require(slow.heat == 0, "a slow crossing followed by atmospheric acceleration remains cold");
    Cues paused;
    Sample(paused, 105000, -500, 7750, .1); Sample(paused, 96000, -500, 7750, .1);
    Sample(paused, 95000, 0, 7750, .1); Sample(paused, 91000, -1500, 7750, .1);
    for (int i = 0; i < 50; ++i) Sample(paused, 73000 - i * 100.0, -1000, 7750, .1);
    Require(paused.heat == 0, "stopping the descent in the top of the atmosphere consumes the approach");

    const PassageResult shallow = Fly(5, 7750, 60);
    const PassageResult oblique = Fly(8, 7750, 60);
    const PassageResult steep = Fly(45, 8500, 60);
    const PassageResult finer = Fly(5, 7750, 144);
    Require(shallow.endSpeed > 6000 && oblique.endSpeed > 6000 && steep.peak > .75,
            "shallow entries end at high airspeed and the steep review route reaches strong heat");
    Require(std::abs(shallow.first - finer.first) < .12 && std::abs(shallow.peak - finer.peak) < .025,
            "entry onset and brightness converge at different frame rates");

    const double speed = 8100, vertical = -1800;
    Cues mid;
    mid.ReplayIncoming(66000, vertical, Velocity(speed, vertical), {});
    Require(mid.heat > .45, "a tagged mid-entry pose reconstructs a qualified approach");
    for (double exitRate : {0.0, 800.0}) {
        Cues exit = mid;
        for (int i = 0; i < 60; ++i) Sample(exit, 66000 + exitRate * i / 60, exitRate, speed, 1.0 / 60);
        Require(exit.heat == 0, "levelling or ascending extinguishes the pulse within one second");
        Sample(exit, 97000, 1000, speed, .1);
        for (int i = 0; i < 50; ++i) Sample(exit, 76000 - i * 100.0, -1000, speed, .1);
        Require(exit.heat == 0, "a climb short of space cannot rearm a spent pulse");
        Sample(exit, 103000, 1000, speed, .1); Sample(exit, 91000, -1000, speed, .1);
        for (int i = 0; i < 50; ++i) Sample(exit, 76000 - i * 100.0, -1000, speed, .1);
        Require(exit.heat > .25, "reaching space rearms the next genuine descending crossing");
    }
    for (double boundary : {EntryFloor, EntrySpace, 3.84e8}) {
        Cues exit = mid;
        Sample(exit, boundary, -1200, speed, 0);
        Require(exit.heat == 0, "low flight and vacuum, including the moons, immediately extinguish the effect");
    }
    for (double rate : {0.0, 500.0}) {
        Cues placed;
        placed.ReplayIncoming(57000, rate, Velocity(speed, rate), {});
        Require(placed.heat == 0, "a label cannot heat a level or outward-looking trajectory");
    }
    Cues early;
    early.ReplayIncoming(1000, -1500, Velocity(speed, -1500), {});
    Require(early.heat == 0, "even an explicit test label cannot heat a low flyby");
    std::puts("PASS: thermal crossing, shallow and steep approaches, cutoff, rearming, fast spawns and review history.");
}
