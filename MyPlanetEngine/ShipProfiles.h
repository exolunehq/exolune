// The selectable ship assets and their matching camera, shadow and water dimensions.
// The shader profiles use the same id and geometry (ShipClassique.hlsli, ShipChasseur.hlsli).
#pragma once
#include <cstdint>

enum class ShipModel : uint32_t { Classique = 0, Chasseur = 1 };

struct ShipProfile {
    ShipModel model;
    const wchar_t* name;
    const wchar_t* packPath;
    float eyeUp, centreY, centreZ;
    uint32_t waterWidth, waterHeight, jetCount, pivotCount;
};

static constexpr ShipProfile ClassicShip = {
    ShipModel::Classique, L"classique", L"assets\\vaisseau\\vaisseau.vsx",
    1.07f, -2.15f, 0.05f, 1584, 3660, 13, 2
};
static constexpr ShipProfile FighterShip = {
    ShipModel::Chasseur, L"chasseur", L"assets\\vaisseau\\chasseur\\vaisseau.vsx",
    1.03f, -0.25f, 0.55f, 1684, 2450, 14, 6
};
