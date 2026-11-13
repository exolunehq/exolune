// Compact body descriptions. All three moons select the same airless stack and renderer.
#pragma once
#include <array>
#include <cstdint>
namespace Celestial {
struct AirlessManifest {
    const char* id;
    unsigned version;
    double radius; // metres
    uint32_t seed;
    double gravity; // m/s2
    std::array<double,3> reflectance; // nominal mean, including the body's material tint
    const char* atlas;
};
constexpr std::array<AirlessManifest,3> Moons={{
    {"moon-1",1,1800000,9173,1.62,{.145,.1392,.13195},"airless.rgba8mips"},
    {"moon-2",1,700000,28411,.63,{.24,.255,.27},"airless-2.rgba8mips"},
    {"moon-3",1,260000,60149,.234,{.15,.115,.085},"airless-3.rgba8mips"}
}};
// Fixed prototype residency, independent of detailed terrain allocations.
constexpr unsigned AirlessAtlasSlots=3;
static_assert(Moons.size()<=AirlessAtlasSlots,"Add a bounded residency cache before expanding the catalogue.");
struct AirlessAtlasHeader {
    uint32_t magic,layout,field,seed;
    double radius;
    uint32_t width,height;
};
static_assert(sizeof(AirlessAtlasHeader)==32,"Stable cooked atlas header.");
constexpr unsigned AirlessAtlasBytes=11184812;
inline constexpr AirlessAtlasHeader AtlasHeader(const AirlessManifest& body) {
    return {0x534c5241,1,3,body.seed,body.radius,2048,1024};
}
}
