// The selectable ship assets and their matching camera, shadow and water dimensions.
// The shader profiles use the same id and geometry (ShipClassique.hlsli, ShipChasseur.hlsli).
#pragma once
// The Navigator's cabin opens over thirteen of the twenty-eight wall sectors, above -0.2 rad.
// The outer skin is sampled over this same aperture for the particle trajectories.
#define SHIP_FIELD_HALF_ANGLE (13.0f * 3.14159265f / 28.0f)
#define SHIP_FIELD_FLOOR (-0.2f)
#define SHIP_FIELD_COLUMNS 53
#define SHIP_FIELD_ROWS 32
#define SHIP_FIELD_ELEVATION_STEP 0.022f
#ifdef __cplusplus
#include <cstdint>

enum class ShipModel : uint32_t { Classique = 0, Chasseur = 1, Navigateur = 2 };

// The water chart is centred laterally. The other origin coordinate and the pitch are in metres.
// The Navigator unwraps its panoramic field in azimuth/elevation, the other panes use the ship's plan.
struct CanopyAtlas {
    uint32_t width, height;
    float originY, texel;
};

struct ShipProfile {
    ShipModel model;
    const wchar_t* name;
    const wchar_t* packPath;
    float eyeAhead, eyeUp, centreY, centreZ;
    CanopyAtlas water;
    uint32_t jetCount, pivotCount;
    bool cockpit, sceneReflections;
};

static constexpr ShipProfile ClassicShip = {
    ShipModel::Classique, L"classique", L"assets\\vaisseau\\vaisseau.vsx",
    0.9192f, 1.07f, -2.15f, 0.05f, {1584, 3660, -4.05f, .0012f}, 13, 2, true, false
};
static constexpr ShipProfile FighterShip = {
    ShipModel::Chasseur, L"chasseur", L"assets\\vaisseau\\chasseur\\vaisseau.vsx",
    0.9192f, 1.03f, -0.25f, 0.55f, {1684, 2450, -2.75f, .0012f}, 14, 6, true, false
};
static constexpr ShipProfile NavigatorShip = {
    ShipModel::Navigateur, L"navigateur", L"assets\\vaisseau\\navigateur\\vaisseau.vsx",
    0.65f, 0.7f, 0.0f, 0.0f, {2560, 1536, -.37f, .0018f}, 0, 0, true, true
};
#endif
