// The water on the canopy (docs/recherche-eau-verriere.md): drops simulated as particles in the panes' plane, then
// drawn into a map that the glass reads (ShipGlass.hlsl). Three passes a frame, after the weather (ShipWeather.hlsl):
// WATER_PASS 0 moves the drops, 1 clears the map and dries the film, 2 draws the drops into the map.
#include "Planet.hlsli"
#include "Ship.hlsli"

// A drop: where (the ship's plan, m), how fast (m/s), its radius (m), whether it lives, its seed, and its heading: the
// angle (rad) it runs off the force that drives it, since it last met a flaw in the glass.
struct Drop
{
    float2 p;
    float2 v;
    float r;
    uint alive;
    uint seed;
    float heading;
};

RWStructuredBuffer<float4> weatherState : register(u0); // ShipWeather.hlsl's, written before
RWStructuredBuffer<Drop> drops : register(u1);
RWTexture2D<uint> waterMap : register(u2);
RWTexture2D<float> waterFilm : register(u3);
RWStructuredBuffer<uint> gathered : register(u4); // volume merged into each drop this frame (mm3 / 1000)

static const uint DROP_COUNT = 8192;
static const float3 PANE_F = float3(0.0, -4.02, 0.697), PANE_S = float3(0.937, -0.516, 0.83), PANE_A = float3(0.0, 0.32, 1.655);

uint WaterHash(uint x)
{
    x ^= x >> 16; x *= 0x7feb352dU; x ^= x >> 15; x *= 0x846ca68bU; x ^= x >> 16;
    return x;
}
float WaterRandom(inout uint state) { state = WaterHash(state); return float(state & 0xFFFFFF) / 16777216.0; }

// The pane under a point of the plan: its outward normal, the right pane's mirrored for the left.
float3 PaneNormal(float2 p)
{
    const float3 n = normalize(cross(PANE_S - PANE_F, PANE_A - PANE_F));
    return float3(p.x < 0.0 ? -abs(n.x) : abs(n.x), n.y, abs(n.z));
}

// Inside the canopy's outline, with a margin (m).
bool OnCanopy(float2 p, float margin)
{
    const float2 q = float2(abs(p.x), p.y), f = PANE_F.xy, s = PANE_S.xy, a = PANE_A.xy;
    const float e1 = (s.x - f.x) * (q.y - f.y) - (s.y - f.y) * (q.x - f.x);
    const float e2 = (a.x - s.x) * (q.y - s.y) - (a.y - s.y) * (q.x - s.x);
    return e1 * sign((s.x - f.x) * (a.y - f.y) - (s.y - f.y) * (a.x - f.x)) > margin * length(s - f)
        && e2 * sign((a.x - s.x) * (f.y - s.y) - (a.y - s.y) * (f.x - s.x)) > margin * length(a - s);
}

int2 WaterTexel(float2 p) { return int2(floor((p - WATER_ORIGIN) / WATER_TEXEL)); }
bool InMap(int2 t) { return all(t >= 0) && all(t < int2(WATER_SIZE)); }

// A drop's volume, as a spherical cap twice as wide as high: about 0.785 r^3.
float DropVolume(float r) { return 0.785 * r * r * r; }

#if WATER_PASS == 0
[numthreads(64, 1, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    const uint i = id.x;
    Drop d = drops[i];
    const float dt = shipAir.y, air = shipAir.x;
    const float4 w = weatherState[0];
    const float catching = weatherState[2].x;
    uint state = WaterHash(i * 9781u + asuint(shipAir.z) * 6271u);

    if (d.alive == 0)
    {
        // Rain lands as drops of 1 to 3 mm, more of them the faster the ship meets it; a cloud's water gathers on the
        // glass into drops of 1 to 2.4 mm, which then grow as more is caught. Each free slot is taken with the share of
        // the rate it stands for.
        const float rain = w.y * 250.0 * (1.0 + air / 30.0), cloud = catching * 3000.0;
        const float chance = (rain + cloud) * dt / DROP_COUNT;
        if (WaterRandom(state) >= chance)
            return;
        float2 p;
        [loop] for (int k = 0; k < 4; ++k) // a point of the canopy's rectangle, kept when on a pane
        {
            p = float2(lerp(-0.94, 0.94, WaterRandom(state)), lerp(-4.0, 0.3, WaterRandom(state)));
            if (OnCanopy(p, 0.004)) break;
        }
        if (!OnCanopy(p, 0.004))
            return;
        const bool fromRain = WaterRandom(state) * (rain + cloud) < rain;
        d.p = p;
        d.v = 0.0;
        d.r = fromRain ? lerp(1.0e-3, 3.0e-3, pow(WaterRandom(state), 2.0)) : lerp(1.0e-3, 2.4e-3, pow(WaterRandom(state), 1.5));
        d.alive = 1;
        d.seed = WaterHash(state);
        d.heading = 0.0;
        gathered[i] = 0;
        drops[i] = d;
        return;
    }

    // What merged into it last frame, and the water it gathers from the cloud or the rain around it: in a cloud a drop
    // grows by about half a millimetre a second, until it is heavy enough to run.
    uint more;
    InterlockedExchange(gathered[i], 0, more);
    const float grown = dt * (0.5e-3 * catching + 0.3e-3 * w.y) * saturate((4.0e-3 - d.r) / 1e-3);
    d.r = pow((DropVolume(d.r) + float(more) * 1e-12) / 0.785, 1.0 / 3.0) + grown;

    // Touching a bigger drop (the map's last frame: the highest drop there), it joins it.
    const int2 here = WaterTexel(d.p);
    if (InMap(here))
    {
        const uint top = waterMap[here], other = top & 0xFFFF;
        if (top != 0 && other != i && drops[other].alive != 0
            && (drops[other].r > d.r || (drops[other].r == d.r && other > i)))
        {
            InterlockedAdd(gathered[other], uint(DropVolume(d.r) * 1e12));
            d.alive = 0;
            drops[i] = d;
            return;
        }
    }

    // The forces in the pane's plane, per unit of mass: gravity, and the air's push, which grows with the airspeed up to
    // 100 km/h and then stays as it is there, so that the water keeps streaming back at any speed, in proportion to the
    // drop's section over its mass (1/r). Against them, the contact line holds the drop until they pass a threshold that
    // grows as it shrinks (r^-2): on glass, a 2.6 mm drop just starts to slide down a 35 degree slope. A wet track holds
    // less.
    const float3 n = PaneNormal(d.p);
    const float3 g = -shipUp.xyz * 9.81, alongAir = normalize(float3(0.0, 1.0, 0.0) - n * n.y);
    const float flow = saturate(air / 27.8);
    const float3 a3 = g - n * dot(g, n) + alongAir * (0.08 * flow / d.r);
    float2 a = a3.xy;
    const float film = InMap(here) ? waterFilm[here] : 0.0;
    const float hold = 5.7 * pow(2.6e-3 / d.r, 2.0) * lerp(1.0, 0.5, saturate(film / 60.0));
    const float speed = length(d.v), push = length(a);
    if (speed < 1e-3 && push < hold)
    {
        d.v = 0.0;
    }
    else
    {
        // Moving, it runs straight, along the force turned by its heading, and leans a little towards a wet track.
        const float c = cos(d.heading), s = sin(d.heading);
        a = float2(a.x * c - a.y * s, a.x * s + a.y * c);
        const float2 ahead = speed > 1e-3 ? d.v / speed : a / max(push, 1e-6), side = float2(-ahead.y, ahead.x);
        const int2 left = WaterTexel(d.p + side * 0.003), right = WaterTexel(d.p - side * 0.003);
        const float wetLeft = InMap(left) ? waterFilm[left] : 0.0, wetRight = InMap(right) ? waterFilm[right] : 0.0;
        a += side * push * 0.3 * clamp((wetLeft - wetRight) / 30.0, -1.0, 1.0);
        // Sliding friction, and the water's own drag on the glass, stronger as it runs faster: a 3 mm drop creeps down
        // at a few centimetres a second; from 100 km/h the air drives the runners at 30 to 50 cm/s, the small ones
        // quickest.
        d.v += (a - ahead * hold * 0.8) * dt;
        d.v *= exp(-dt * (30.0 + 50.0 * length(d.v)));
        if (dot(d.v, ahead) < 0.0) d.v = 0.0;
    }

    // Along its way it leaves a trail as wide as itself, a film (um) thicker under a bigger drop, which then dries
    // (pass 1). It loses that water: small drops thin out and stop.
    const float2 step = d.v * dt;
    const float travel = length(step);
    const uint steps = min(uint(ceil(travel / WATER_TEXEL)), 64u);
    const int half = int(ceil(0.95 * d.r / WATER_TEXEL));
    const float laid = 40.0 + 60.0 * saturate(d.r / 3e-3);
    for (uint k = 0; k < steps; ++k)
    {
        const float2 at = d.p + step * (k + 0.5) / steps;
        const int2 c = WaterTexel(at);
        for (int y = -half; y <= half; ++y)
        for (int x = -half; x <= half; ++x)
        {
            const int2 t = c + int2(x, y);
            const float2 o = WATER_ORIGIN + (float2(t) + 0.5) * WATER_TEXEL - at;
            const float u = dot(o, o) / (0.9 * d.r * d.r); // (0.95 r)^2
            if (u < 1.0 && InMap(t))
                waterFilm[t] = max(waterFilm[t], laid * (1.0 - u * u));
        }
    }
    // The glass has flaws, about one 5 mm cell in twelve: running into one, the drop catches, slows, and sets off on a
    // new heading, up to 45 degrees off; its heading then eases back towards the force over some 5 cm.
    const int2 cellBefore = int2(floor(d.p / 0.005)), cellAfter = int2(floor((d.p + step) / 0.005));
    if (any(cellBefore != cellAfter))
    {
        uint flaw = WaterHash(uint(cellAfter.x) * 73856093u ^ uint(cellAfter.y) * 19349663u);
        if ((flaw & 255u) < 21u)
        {
            uint turn = flaw ^ d.seed;
            d.heading = clamp(0.3 * d.heading + (WaterRandom(turn) * 2.0 - 1.0) * 0.8, -0.8, 0.8);
            d.v *= 0.3;
        }
    }
    d.heading *= exp(-travel / 0.05);
    d.p += step;
    const float left = DropVolume(d.r) - d.r * 0.3e-6 * travel; // a 1 mm drop runs some 2.6 m, bigger ones across
    // Drying, none in the rain or a cloud: the drops the air cannot move (under 0.5 mm) go in a minute or so in still air,
    // in some seven seconds in fast air; in the thin air of space they boil off in two or three.
    const float dry = (5e-6 + 55e-6 * saturate(air / 100.0)) * (1.0 - saturate(max(w.y, weatherState[1].x) * 3.0))
                    + 1e-3 * ShipVacuum();
    d.r = pow(max(left, 0.0) / 0.785, 1.0 / 3.0) - dry * dt;
    if (d.r < 0.15e-3 || !OnCanopy(d.p, 0.0))
        d.alive = 0;
    drops[i] = d;
}
#elif WATER_PASS == 1
[numthreads(8, 8, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    if (any(id.xy >= WATER_SIZE))
        return;
    waterMap[id.xy] = 0;
    // The trails dry in some five seconds, faster in fast air, slower in rain or a cloud, at once in space: thinning, they
    // break up (ShipGlass.hlsl).
    const float air = shipAir.x, wet = saturate(max(weatherState[0].y, weatherState[1].x) * 3.0);
    waterFilm[id.xy] *= exp(-shipAir.y / lerp(5.0, 12.0, wet) * (1.0 + air / 100.0 + 20.0 * ShipVacuum()));
}
#else
[numthreads(64, 1, 1)]
void CSMain(uint3 id : SV_DispatchThreadID)
{
    const uint i = id.x;
    const Drop d = drops[i];
    if (d.alive == 0)
        return;
    // A drop sits on glass with steep sides, rounded, its outline never quite a circle; running, a tear, its head round
    // and full, its tail drawn out, narrower and lower towards its end. Each texel keeps the highest drop and its number.
    const float speed = length(d.v);
    const float2 ahead = speed > 1e-4 ? d.v / speed : float2(0.0, 1.0);
    const float stretch = 1.0 + min(speed / (d.r * 40.0), 3.0);
    const int reach = int(ceil(d.r * stretch / WATER_TEXEL)) + 1;
    const int2 centre = WaterTexel(d.p);
    for (int y = -reach; y <= reach; ++y)
    for (int x = -reach; x <= reach; ++x)
    {
        const int2 t = centre + int2(x, y);
        if (!InMap(t))
            continue;
        const float2 o = WATER_ORIGIN + (float2(t) + 0.5) * WATER_TEXEL - d.p;
        float along = dot(o, ahead), across = dot(o, float2(-ahead.y, ahead.x));
        const float tail = along < 0.0 ? saturate(-along / (d.r * stretch)) : 0.0;
        if (along < 0.0) along /= stretch;
        across /= 1.0 - 0.15 * tail * saturate(stretch - 1.0);
        const float angle = atan2(across, along);
        const float outline = 1.0 + 0.1 * sin(2.0 * angle + float(d.seed & 63)) + 0.06 * sin(3.0 * angle + float(d.seed >> 6 & 63));
        const float q = (along * along + across * across) / (d.r * d.r * outline * outline);
        if (q >= 1.0)
            continue;
        // Running, the drop spreads into its trail: flatter, no fatter than the track it leaves.
        const uint h = uint(0.5 * d.r * sqrt(1.0 - q) * (1.0 - 0.4 * tail) * lerp(1.0, 0.55, saturate(stretch - 1.0)) * 1e6); // um
        InterlockedMax(waterMap[t], (min(h, 65535u) << 16) | i);
    }
}
#endif
