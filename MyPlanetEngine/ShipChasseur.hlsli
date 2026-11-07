// Fighter geometry, paired with assets/vaisseau/chasseur and FighterShip in ShipProfiles.h.
#ifndef SHIP_CHASSEUR_HLSLI
#define SHIP_CHASSEUR_HLSLI
static const float3 FIGHTER_SHIP_CENTRE = float3(0.0, -0.25, 0.55); // the shadow maps' sphere, ship frame (m)
// The canopy (assets/vaisseau/chasseur/forme_chasseur.py, which this must match), d the distance from the nose tip, y = d - 5.32:
// in the plan, a blunt nose widening almost straight to 2 m wide at d = 4.55, then a round tail, the rear frame; over
// the deck a round section, (1 - s^2)^0.55, up to the crown. The deck's and the crown's heights, every 1/32 of its length.
static const float FIGHTER_CANOPY_NOSE = 5.32, FIGHTER_CANOPY_D0 = 2.58, FIGHTER_CANOPY_DW = 4.55, FIGHTER_CANOPY_D1 = 5.5;
static const float FIGHTER_CANOPY_Y0 = FIGHTER_CANOPY_D0 - FIGHTER_CANOPY_NOSE, FIGHTER_CANOPY_Y1 = FIGHTER_CANOPY_D1 - FIGHTER_CANOPY_NOSE, FIGHTER_CANOPY_W = 1.0;
static const float FIGHTER_CANOPY_DECK[33] = { 0.7484, 0.7511, 0.7533, 0.7554, 0.7580, 0.7616, 0.7662, 0.7717, 0.7777, 0.7837, 0.7895, 0.7950, 0.8003, 0.8055, 0.8106, 0.8159, 0.8212, 0.8268, 0.8326, 0.8388, 0.8454, 0.8526, 0.8605, 0.8689, 0.8776, 0.8865, 0.8954, 0.9046, 0.9159, 0.9279, 0.9389, 0.9469, 0.9500 };
static const float FIGHTER_CANOPY_CROWN[33] = { 0.8100, 0.8562, 0.9025, 0.9478, 0.9914, 1.0336, 1.0705, 1.1036, 1.1342, 1.1624, 1.1880, 1.2115, 1.2334, 1.2539, 1.2730, 1.2907, 1.3072, 1.3236, 1.3394, 1.3538, 1.3658, 1.3747, 1.3811, 1.3867, 1.3914, 1.3953, 1.3986, 1.4012, 1.4033, 1.4051, 1.4067, 1.4083, 1.4100 };
// The water map's rectangle in the ship's plan (m), around the bubble, and its size (texels, 1.2 mm). Must match
// FighterShip.waterWidth, waterHeight.
static const float2 FIGHTER_WATER_ORIGIN = float2(-1.01, FIGHTER_CANOPY_Y0 - 0.01);
static const uint2 FIGHTER_WATER_SIZE = uint2(1684, 2450);

float FighterCanopyDeck(float d)
{
    const float f = saturate((d - FIGHTER_CANOPY_D0) / (FIGHTER_CANOPY_D1 - FIGHTER_CANOPY_D0)) * 32.0; const uint i = min((uint)f, 31u);
    return lerp(FIGHTER_CANOPY_DECK[i], FIGHTER_CANOPY_DECK[i + 1], f - i);
}
float FighterCanopyCrown(float d)
{
    const float f = saturate((d - FIGHTER_CANOPY_D0) / (FIGHTER_CANOPY_D1 - FIGHTER_CANOPY_D0)) * 32.0; const uint i = min((uint)f, 31u);
    return lerp(FIGHTER_CANOPY_CROWN[i], FIGHTER_CANOPY_CROWN[i + 1], f - i);
}
// The bubble's half-width at the deck, before its tail (forme_chasseur.bulle_l).
float FighterCanopyBase(float d)
{
    if (d <= FIGHTER_CANOPY_D0) return 0.0;
    if (d >= FIGHTER_CANOPY_DW) return 1.0;
    return (1.0 - 0.6 * pow(max(0.0, (4.7 - d) / 2.0), 1.6)) * pow(saturate(1.0 - pow(max(0.0, (FIGHTER_CANOPY_D0 + 0.2 - d) / 0.2), 2.5)), 0.4);
}
// The glass's outline: the bubble's sides, then its round tail (x_cadre).
float FighterCanopyHalfWidth(float y)
{
    const float d = y + FIGHTER_CANOPY_NOSE;
    if (d <= FIGHTER_CANOPY_DW) return FighterCanopyBase(d);
    return pow(saturate(1.0 - pow(saturate((d - FIGHTER_CANOPY_DW) / (FIGHTER_CANOPY_D1 - FIGHTER_CANOPY_DW)), 2.3)), 1.0 / 2.3);
}
// Inside the outline, with a margin (m): the half-width's excess over its slope, a distance near the outline.
float FighterCanopyInside(float2 p)
{
    const float e = 0.005, g = (FighterCanopyHalfWidth(p.y + e) - FighterCanopyHalfWidth(p.y - e)) / (2.0 * e);
    return (FighterCanopyHalfWidth(p.y) - abs(p.x)) / sqrt(1.0 + g * g);
}
bool FighterOnCanopy(float2 p, float margin) { return FighterCanopyInside(p) > margin; }
// The bubble's height over a point of the plan.
float FighterCanopyZ(float2 p)
{
    const float d = p.y + FIGHTER_CANOPY_NOSE, deck = FighterCanopyDeck(d), s = saturate(abs(p.x) / max(FighterCanopyBase(d), 1e-4));
    return deck + (FighterCanopyCrown(d) - deck) * pow(saturate(1.0 - s * s), 0.55);
}
// The bubble's outward normal, ship frame, by its slopes over 5 mm; its flanks stand near the vertical by the rim.
float3 FighterCanopyNormal(float2 p)
{
    const float e = 0.005;
    const float dx = FighterCanopyZ(p + float2(e, 0.0)) - FighterCanopyZ(p - float2(e, 0.0)), dy = FighterCanopyZ(p + float2(0.0, e)) - FighterCanopyZ(p - float2(0.0, e));
    return normalize(float3(-dx, -dy, 2.0 * e));
}

// The nozzles' lips, along +y (assets/vaisseau/chasseur/forme_chasseur.py, GRANDE and PETITE): the two big engines in their
// cowls, the two small ones in the wing roots; w, the lip's inner radius (m).
static const float4 FIGHTER_NOZZLE[4] = { float4(0.93, 4.78, 0.50, 0.31), float4(-0.93, 4.78, 0.50, 0.31),
                                  float4(1.85, 3.60, 0.36, 0.20), float4(-1.85, 3.60, 0.36, 0.20) };
// The attitude jets, flush in the skin (design_chasseur.py prints them, JETS): at the wing tips, up and down; on the
// engine cowls, outward; at the nose, up, down and to each side.
static const float3 FIGHTER_JET_AT[10] = {
    float3(3.05, 1.632, 0.297), float3(3.05, 1.632, 0.22), float3(1.378, 4.28, 0.5),
    float3(-3.05, 1.632, 0.297), float3(-3.05, 1.632, 0.22), float3(-1.378, 4.28, 0.5),
    float3(0.0, -4.12, 0.542), float3(0.0, -4.12, 0.032), float3(0.45, -4.12, 0.31), float3(-0.45, -4.12, 0.31) };
#endif
