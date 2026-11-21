// Local response of the canopy to external entry light. The flowing, incandescent
// body of air lives outside these surfaces (ShipEntryVolume.hlsli).
#ifndef SHIP_ENTRY_HLSLI
#define SHIP_ENTRY_HLSLI

uint EntryHash(uint x)
{
    x ^= x >> 16; x *= 0x7feb352du;
    x ^= x >> 15; x *= 0x846ca68bu;
    return x ^ (x >> 16);
}

float EntryCorner(int2 cell)
{
    const uint2 u = asuint(cell);
    return (EntryHash(u.x * 0x9e3779b1u ^ u.y * 0x85ebca77u) >> 8) * (1.0 / 16777216.0);
}

// Neighbouring cells must compute the exact same value at a shared corner.
// Building the corner keys with integers also keeps negative coordinates continuous.
float EntryNoise(float2 p)
{
    const int2 cell = int2(floor(p));
    const float2 f = frac(p), t = f * f * f * (f * (f * 6.0 - 15.0) + 10.0);
    return lerp(lerp(EntryCorner(cell), EntryCorner(cell + int2(1, 0)), t.x),
                lerp(EntryCorner(cell + int2(0, 1)), EntryCorner(cell + int2(1, 1)), t.x), t.y);
}

float EntryIntensity()
{
    return shipAirflow.w * smoothstep(12.0, 90.0, shipAir.x) * smoothstep(1.e-9, 1.e-6, shipOptions.w);
}

StructuredBuffer<float> shipFieldRadii : register(t51); // Navigator's fitted outer skin (m), azimuth then elevation
float EntryFieldScale() { return shipFieldRadii[(SHIP_FIELD_COLUMNS / 2) * SHIP_FIELD_ROWS]; }

// The radii fit the outer shell from its VSX mesh at startup.
float3 EntryFieldPoint(float azimuth, float elevation)
{
    const float u = saturate(0.5 + 0.5 * azimuth / SHIP_FIELD_HALF_ANGLE) * (SHIP_FIELD_COLUMNS - 1);
    const uint i = min((uint)u, (uint)SHIP_FIELD_COLUMNS - 2);
    const float v = clamp((elevation - SHIP_FIELD_FLOOR) / SHIP_FIELD_ELEVATION_STEP, 0.0, (float)SHIP_FIELD_ROWS - 1.0);
    const uint j = min((uint)v, (uint)SHIP_FIELD_ROWS - 2);
    const uint at = i * SHIP_FIELD_ROWS + j;
    const float lo = lerp(shipFieldRadii[at], shipFieldRadii[at + SHIP_FIELD_ROWS], u - i);
    const float hi = lerp(shipFieldRadii[at + 1], shipFieldRadii[at + SHIP_FIELD_ROWS + 1], u - i);
    float sa, ca, se, ce;
    sincos(azimuth, sa, ca);
    sincos(elevation, se, ce);
    return lerp(lo, hi, v - j) * float3(sa * ce, -ca * ce, se);
}

float EntryRailLength()
{
    if (ShipShuttle()) return 0.5 * SHUTTLE_WATER_WIDTH * SHUTTLE_WATER_TEXEL;
    if (ShipNavigator()) return SHIP_FIELD_HALF_ANGLE * EntryFieldScale();
    return ShipClassic() ? CLASSIC_PANE_A.y - CLASSIC_PANE_F.y : FIGHTER_CANOPY_Y1 - FIGHTER_CANOPY_Y0;
}

// Along runs from the nose to the rear on each side. Inset crosses the pane from
// the seal towards its crown. Planar panes, the curved fighter glass and the field
// all retain their own real depth; only the shading law is shared.
float3 EntryPanePoint(float along, float side, float inset)
{
    if (ShipShuttle() && HasShuttlePane()) {
        const float column = saturate(0.5 + side * along / (2.0 * EntryRailLength())) * (SHUTTLE_PANE_COLUMNS - 1);
        const uint i = min((uint)column, SHUTTLE_PANE_COLUMNS - 2u);
        const uint at = SHUTTLE_PANE_COLUMNS * SHUTTLE_PANE_ROWS + i;
        const float2 q = lerp(shipPaneFit[at].xy, shipPaneFit[at + 1].xy, column - i) + float2(0, inset);
        float sa, ca, se, ce;
        sincos(q.x / SHUTTLE_PANE_RADIUS, sa, ca);
        sincos(q.y / SHUTTLE_PANE_RADIUS, se, ce);
        return SHUTTLE_PANE_CENTRE + length(ShuttlePaneAt(q).xyz) * float3(sa * ce, -ca * ce, se);
    }
    if (ShipNavigator()) {
        const float scale = max(EntryFieldScale(), 0.1);
        return EntryFieldPoint(side * along / scale, SHIP_FIELD_FLOOR + inset / scale);
    }
    if (ShipClassic()) {
        const float y = CLASSIC_PANE_F.y + along;
        float3 rail = y <= CLASSIC_PANE_S.y
            ? lerp(CLASSIC_PANE_F, CLASSIC_PANE_S, saturate(along / (CLASSIC_PANE_S.y - CLASSIC_PANE_F.y)))
            : lerp(CLASSIC_PANE_S, CLASSIC_PANE_A, saturate((y - CLASSIC_PANE_S.y) / (CLASSIC_PANE_A.y - CLASSIC_PANE_S.y)));
        rail.x *= side;
        const float3 crown = lerp(CLASSIC_PANE_F, CLASSIC_PANE_A, saturate(along / (CLASSIC_PANE_A.y - CLASSIC_PANE_F.y)));
        return lerp(rail, crown, saturate(inset / max(length(crown - rail), 0.001)));
    }
    const float y = FIGHTER_CANOPY_Y0 + along, d = y + FIGHTER_CANOPY_NOSE;
    const float width = FighterCanopyHalfWidth(y);
    // The front and side retainer is fastened to the deck, including the single
    // pole at the nose. The rear arch follows the bubble above the deck.
    if (d <= FIGHTER_CANOPY_DW && (inset == 0.0 || width < 0.0001))
        return float3(side * width, y, FighterCanopyDeck(d) + 0.004);
    const float crown = FighterCanopyCrown(d) - FighterCanopyDeck(d);
    const float angle = min(1.52, inset / max(0.10, 0.35 * width + 0.65 * crown));
    const float2 plan = float2(side * width * cos(angle), y);
    return float3(plan, FighterCanopyZ(plan) + 0.004); // cooker glass offset above the bubble
}

struct EntrySection {
    float3 rail;
    float along, across, side;
};

EntrySection EntryAt(float3 local)
{
    EntrySection e;
    e.side = local.x < 0.0 ? -1.0 : 1.0;
    if (ShipShuttle()) {
        const float2 q = CanopyChart(local);
        e.along = min(abs(q.x), EntryRailLength());
        e.rail = HasShuttlePane() ? EntryPanePoint(e.along, e.side, 0.0) : local + float3(0, 0, 100);
        e.across = HasShuttlePane() ? abs(ShuttlePaneAt(q).w) * length(local - SHUTTLE_PANE_CENTRE) / SHUTTLE_PANE_RADIUS : 100.0;
        return e;
    }
    if (ShipNavigator()) {
        const float azimuth = clamp(atan2(local.x, -local.y), -SHIP_FIELD_HALF_ANGLE, SHIP_FIELD_HALF_ANGLE);
        e.along = abs(azimuth) * EntryFieldScale();
    } else {
        e.along = clamp(local.y - (ShipClassic() ? CLASSIC_PANE_F.y : FIGHTER_CANOPY_Y0), 0.0, EntryRailLength());
    }
    e.rail = EntryPanePoint(e.along, e.side, 0.0);
    e.across = length(local - e.rail);
    return e;
}

// Small variations along the real seal split the grazing reflections into patches.
float EntryFeed(float s, float time)
{
    const float sites = 0.68 * EntryNoise(float2(2.1 * s + 3.27, 8.51))
                      + 0.32 * EntryNoise(float2(4.9 * s - 3.12, 20.3));
    const float pulse = EntryNoise(float2(3.5 * s + 0.23 * time, 0.62 * time + 13.6));
    return 0.055 + 0.945 * smoothstep(0.33, 0.72, sites + 0.17 * (pulse - 0.5));
}

float3 EntrySealReflection(EntrySection e, float heat)
{
    const float scale = ShipNavigator() ? 1.85 : 1.0;
    const float feed = EntryFeed(e.side * e.along / scale, shipTurn.z);
    return heat * float3(0.74, 0.23, 0.06) * exp2(-e.across * 112.0 / scale) * (0.15 + 0.85 * feed);
}

float3 EntryRetainerLight(float3 local, float3 normal, float3 view, float3 albedo, float roughness, bool innerField, float heat)
{
    const EntrySection e = EntryAt(local);
    // The Navigator's manufactured inner walls sit at .875 of the outer skin
    // (cabine_maillage.py). Its sensor and instruments have their own depth.
    const float3 rim = (innerField ? 0.875 : 1.0) * e.rail, toRim = rim - local;
    const float gap = length(toRim);
    const float3 light = toRim / max(gap, 0.001);
    const float falloff = 1.0 - smoothstep(0.007, innerField ? 0.15 : 0.10, gap);
    const float feed = EntryFeed(e.side * e.along / (ShipNavigator() ? 1.85 : 1.0), shipTurn.z);
    const float facing = saturate(dot(normal, light));
    const float specular = pow(saturate(dot(reflect(-light, normal), view)), lerp(90.0, 8.0, roughness));
    const float3 reflected = (0.06 + 0.62 * albedo) * facing + (0.36 * (1.0 - roughness) * specular);
    const float rimHot = exp2(-gap * 138.0) * (0.12 + 0.88 * feed);
    return 0.53 * heat * (float3(1.0, 0.26, 0.055) * reflected * falloff * falloff * (0.25 + 1.7 * feed)
                 + float3(1.0, 0.46, 0.14) * rimHot * feed);
}

struct EntryParticlePixel {
    float4 position : SV_Position;
    float2 uv : TEXCOORD0; // tail to head, across the streak
    nointerpolation float3 light : TEXCOORD1; // radiance, age, projected tail length in head radii
};
#endif
