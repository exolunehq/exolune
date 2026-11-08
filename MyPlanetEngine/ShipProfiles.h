// The selectable ship assets and their matching camera, shadow and water dimensions.
// The shader profiles use the same id and geometry (ShipClassique.hlsli, ShipChasseur.hlsli).
#pragma once
#include <cstdint>

enum class ShipModel : uint32_t { Classique = 0, Chasseur = 1, Navigateur = 2 };

struct ShipProfile {
    ShipModel model;
    const wchar_t* name;
    const wchar_t* packPath;
    float eyeAhead, eyeUp, centreY, centreZ;
    uint32_t waterWidth, waterHeight, jetCount, pivotCount;
    bool cockpit, canopyWeather, sceneReflections;
};

static constexpr ShipProfile ClassicShip = {
    ShipModel::Classique, L"classique", L"assets\\vaisseau\\vaisseau.vsx",
    0.9192f, 1.07f, -2.15f, 0.05f, 1584, 3660, 13, 2, true, true, false
};
static constexpr ShipProfile FighterShip = {
    ShipModel::Chasseur, L"chasseur", L"assets\\vaisseau\\chasseur\\vaisseau.vsx",
    0.9192f, 1.03f, -0.25f, 0.55f, 1684, 2450, 14, 6, true, true, false
};
static constexpr ShipProfile NavigatorShip = {
    ShipModel::Navigateur, L"navigateur", L"assets\\vaisseau\\navigateur\\vaisseau.vsx",
    0.65f, 0.7f, 0.0f, 0.0f, 1, 1, 0, 0, true, false, true
};
