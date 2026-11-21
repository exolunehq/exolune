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
#define SHIP_PACK_POSES 11
#define SHIP_POSE_COUNT (SHIP_PACK_POSES + 4)
#define SHIP_MAX_IMAGES 16
#define SHIP_MANOEUVRING_JETS 6
// The offline fitter samples the actual shuttle glass in this angular chart.
#define SHUTTLE_PANE_COLUMNS 161
#define SHUTTLE_PANE_ROWS 81
#define SHUTTLE_PANE_CENTRE_Y .80f
#define SHUTTLE_PANE_CENTRE_Z -.88f
#define SHUTTLE_PANE_RADIUS 2.30f
#define SHUTTLE_WATER_WIDTH 3456
#define SHUTTLE_WATER_HEIGHT 1256
#define SHUTTLE_WATER_Y -.98f
#define SHUTTLE_WATER_TEXEL .00192f
#ifdef __cplusplus
#include <cstdint>

enum class ShipModel : uint32_t { Classique = 0, Chasseur = 1, Navigateur = 2, Navette = 3 };

// The water chart is centred laterally. The other origin coordinate and the pitch are in metres.
// The Navigator unwraps its panoramic field in azimuth/elevation, the other panes use the ship's plan.
struct CanopyAtlas {
    uint32_t width, height;
    float originY, texel;
};

struct FlightSurfaceLayout {
    float x, y, z, span, chord, sweep, thickness, retraction;
    float retroX, retroY, retroZ;
    float supportX, supportY, supportZ, supportSpacing;
};

struct ShipProfile {
    ShipModel model;
    const wchar_t* name;
    const wchar_t* packPath;
    float eyeAhead, eyeUp, centreY, centreZ;
    CanopyAtlas water;
    uint32_t jetCount, pivotCount;
    bool cockpit, sceneReflections;
    FlightSurfaceLayout surfaces;
};

static constexpr ShipProfile ClassicShip = {
    ShipModel::Classique, L"classique", L"assets\\vaisseau\\vaisseau.vsx",
    0.9192f, 1.07f, -2.15f, 0.05f, {1584, 3660, -4.05f, .0012f}, 13, 2, true, false,
    {}
};
static constexpr ShipProfile FighterShip = {
    ShipModel::Chasseur, L"chasseur", L"assets\\vaisseau\\chasseur\\vaisseau.vsx",
    0.9192f, 1.03f, -0.25f, 0.55f, {1684, 2450, -2.75f, .0012f}, 14, 6, true, false,
    {1.60f, 2.61f, .47f, 1.16f, .98f, .79f, .084f, 1.28f,
     1.17f, -1.26f, .35f, .94f, 2.88f, .07f, .67f}
};
static constexpr ShipProfile NavigatorShip = {
    ShipModel::Navigateur, L"navigateur", L"assets\\vaisseau\\navigateur\\vaisseau.vsx",
    0.65f, 0.7f, 0.0f, 0.0f, {2560, 1536, -.37f, .0018f}, 0, 0, true, true,
    {}
};
// The flight film's rider position and bare-metal nacelles. Mounts follow the outer reactor casings in metres.
static constexpr ShipProfile ShuttleShip = {
    ShipModel::Navette, L"navette", L"assets\\vaisseau\\navette\\vaisseau.vsx",
    3.47f, -.84f, 0, 0, {1, 1, 0, .0012f}, 2, SHIP_PACK_POSES, true, false,
    {2.32f, 1.57f, -.59f, 1.49f, 1.59f, 1.01f, .105f, 1.12f,
     2.05f, .27f, -.95f, 1.36f, 1.22f, -2.14f, 1.04f}
};
#endif
