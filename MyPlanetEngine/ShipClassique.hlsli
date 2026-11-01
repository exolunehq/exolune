// The original triangular ship, paired with assets/vaisseau and ClassicShip in ShipProfiles.h.
#ifndef SHIP_CLASSIQUE_HLSLI
#define SHIP_CLASSIQUE_HLSLI
static const float3 CLASSIC_CENTRE = float3(0.0, -2.15, 0.05);
static const float2 CLASSIC_WATER_ORIGIN = float2(-0.95, -4.05);
static const uint2 CLASSIC_WATER_SIZE = uint2(1584, 3660);
static const float3 CLASSIC_PANE_F = float3(0.0, -4.02, 0.697),
                    CLASSIC_PANE_S = float3(0.937, -0.516, 0.83),
                    CLASSIC_PANE_A = float3(0.0, 0.32, 1.655);

float3 ClassicCanopyNormal(float2 p)
{
    const float3 n = normalize(cross(CLASSIC_PANE_S - CLASSIC_PANE_F, CLASSIC_PANE_A - CLASSIC_PANE_F));
    return float3(p.x < 0.0 ? -abs(n.x) : abs(n.x), n.y, abs(n.z));
}

// Signed distances to the two outer pane edges; symmetry supplies the centre ridge.
bool ClassicOnCanopy(float2 p, float margin)
{
    const float2 q = float2(abs(p.x), p.y), f = CLASSIC_PANE_F.xy, s = CLASSIC_PANE_S.xy, a = CLASSIC_PANE_A.xy;
    const float e1 = (s.x - f.x) * (q.y - f.y) - (s.y - f.y) * (q.x - f.x);
    const float e2 = (a.x - s.x) * (q.y - s.y) - (a.y - s.y) * (q.x - s.x);
    return e1 * sign((s.x - f.x) * (a.y - f.y) - (s.y - f.y) * (a.x - f.x)) > margin * length(s - f)
        && e2 * sign((a.x - s.x) * (f.y - s.y) - (a.y - s.y) * (f.x - s.x)) > margin * length(a - s);
}

float ClassicSillDistance(float3 local)
{
    const float2 p = float2(abs(local.x), local.y), F = float2(0.0, -4.02), S = float2(0.9375, -0.523), A = float2(0.0, 0.32);
    const float2 fs = S - F, sa = A - S;
    const float d1 = length(p - F - fs * saturate(dot(p - F, fs) / dot(fs, fs)));
    const float d2 = length(p - S - sa * saturate(dot(p - S, sa) / dot(sa, sa)));
    return min(d1, d2);
}

// The nozzles' exits, 35 cm wide, square to the stern's plane y + 0.125 z = 2.6 (assets/vaisseau/design_v2.py).
static const float3 CLASSIC_NOZZLE_AXIS = float3(0.0, 0.99228, 0.12403);
// The attitude jets: at the stern's two tips, up, down and outward; at the nose, up, down and to each side.
static const float3 CLASSIC_JET_AT[10] = {
    float3(3.0, 2.4, 0.15), float3(3.0, 2.4, -0.05), float3(3.05, 2.4, 0.05),
    float3(-3.0, 2.4, 0.15), float3(-3.0, 2.4, -0.05), float3(-3.05, 2.4, 0.05),
    float3(0.0, -5.6, 0.52), float3(0.0, -5.6, -0.47), float3(0.72, -5.6, 0.02), float3(-0.72, -5.6, 0.02) };
#endif
