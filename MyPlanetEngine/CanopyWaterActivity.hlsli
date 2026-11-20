// Shared by the GPU water passes and the functional dry/rain/dry fixture.
#ifndef CANOPY_WATER_ACTIVITY_HLSLI
#define CANOPY_WATER_ACTIVITY_HLSLI
#ifdef __cplusplus
#include <cmath>
#endif

static const float CANOPY_MAX_TRACK_UM = 100.0f;
static const float CANOPY_VISIBLE_FILM_UM = 0.5f;

inline float CanopyFilmRetention(float dt, float air, float wet, float vacuum)
{
    const float decay = -dt * (1.0f + air / 100.0f + 20.0f * vacuum) / (5.0f + 7.0f * wet);
#ifdef __cplusplus
    return std::exp(decay);
#else
    return exp(decay);
#endif
}

struct CanopyWaterWork {
    float filmUpper;
    bool active, reset;
};

inline CanopyWaterWork CanopyActivity(float previousFilm, bool liveDrops, bool source,
                                      bool vacuum, bool placement, float retention)
{
    // Film can be deposited by a drop that evaporates this very frame. The upper
    // bound uses the deposition limit and exactly the same retention as the atlas.
    CanopyWaterWork step;
    step.filmUpper = (liveDrops || source ? CANOPY_MAX_TRACK_UM : previousFilm) * retention;
    step.active = !vacuum && (liveDrops || source || step.filmUpper >= CANOPY_VISIBLE_FILM_UM);
    step.reset = placement || (!step.active && (previousFilm > 0.0f || liveDrops));
    if (!step.active) step.filmUpper = 0.0f;
    return step;
}
#endif
