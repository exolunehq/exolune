// The same scheduling rule and film decay used by the GPU.
#include "../../MyPlanetEngine/CanopyWaterActivity.hlsli"
#include <cstdio>
#include <cstdlib>

namespace {
void Check(bool condition, const char* message) {
    if (!condition) { std::fprintf(stderr, "FAIL: %s\n", message); std::exit(1); }
}
}

void CheckCanopyWater() {
    const float dt = 1.0f / 60.0f;
    const float dry = CanopyFilmRetention(dt, 0.0f, 0.0f, 0.0f);
    const float wet = CanopyFilmRetention(dt, 0.0f, 1.0f, 0.0f);
    CanopyWaterWork step = CanopyActivity(0.0f, false, false, false, true, dry);
    Check(step.reset && !step.active, "initial placement clears an empty atlas once");
    step = CanopyActivity(step.filmUpper, false, false, false, false, dry);
    Check(!step.active && !step.reset, "a dry pane schedules zero groups");
    step = CanopyActivity(step.filmUpper, false, true, false, false, wet);
    Check(step.active && !step.reset, "precipitation wakes a dry pane");
    for (unsigned frame = 0; frame < 3600; ++frame) {
        step = CanopyActivity(step.filmUpper, true, false, false, false, dry);
        Check(step.active && !step.reset, "a live stationary bead survives the end of rain");
    }
    // The last bead may have deposited the maximum film on the last wet frame.
    float thickest = step.filmUpper;
    unsigned frames = 0;
    do {
        thickest *= dry;
        step = CanopyActivity(step.filmUpper, false, false, false, false, dry);
        Check((thickest >= CANOPY_VISIBLE_FILM_UM) == step.active, "film activity follows its actual optical cutoff");
        ++frames;
    } while (step.active && frames < 1800);
    Check(step.reset && !step.active && frames > 1500 && frames < 1700, "last visible still-air film dries at 26.5 seconds");
    step = CanopyActivity(step.filmUpper, false, false, false, false, dry);
    Check(!step.active && !step.reset, "the fully dry pane returns to zero groups");
    step = CanopyActivity(85.0f, true, true, true, false, wet);
    Check(step.reset && !step.active && step.filmUpper == 0.0f, "vacuum clears wet history even with a forced rain source");
    Check(CanopyFilmRetention(dt, 100.0f, 0.0f, 0.0f) < dry && dry < wet, "airflow and humidity order track drying");
    std::puts("PASS: canopy placement, dry/wet wake, retained beads, film drying, vacuum and zero-work idle.");
}
