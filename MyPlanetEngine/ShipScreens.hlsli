// ShipScreens.hlsli - the dashboard's live screens and dials (ShipPixel.hlsl), visual only: the pack's roles 1 to 6
// (assets/vaisseau/paquet_moteur.py). Their 512² images (assets/vaisseau/textures_cockpit.py) keep the frames and the
// labels; what the flight changes is wiped and drawn again here, in the images' texels, y down, with their colours.
#ifndef SHIP_SCREENS_HLSLI
#define SHIP_SCREENS_HLSLI

static const uint SCREEN_NAV = 1, SCREEN_FLIGHT = 2, SCREEN_SYSTEMS = 3, DIAL_GAS = 4, DIAL_PITCH = 5, DIAL_HEIGHT = 6; // roles

// The images' colours, decoded as the GPU decodes their sRGB texels: a power law would darken the dark ones.
float3 Srgb(float3 c) { c /= 255.0; return lerp(c / 12.92, pow((c + 0.055) / 1.055, 2.4), step(0.04045, c)); }
#define SRGB(r, g, b) Srgb(float3(r, g, b))
#define SCREEN_BACK SRGB(6, 16, 22)
#define SCREEN_GRID SRGB(10, 30, 36)
#define SCREEN_LINE SRGB(24, 74, 83)
#define SCREEN_TEXT SRGB(159, 218, 221)
#define SCREEN_CYAN SRGB(51, 208, 218)
#define SCREEN_AMBER SRGB(246, 171, 69)

static float screenPx; // texels per pixel: strokes stay a pixel wide at least, fainter instead

// Coverage of a stroke `width` texels wide at distance d; of a shape at signed distance d, negative inside.
float Stroke(float d, float width)
{
    const float w = max(width, screenPx);
    return saturate((0.5 * w - abs(d)) / screenPx + 0.5) * width / w;
}
float Fill(float d) { return saturate(0.5 - d / screenPx); }
void Paint(inout float3 c, float3 colour, float coverage) { c = lerp(c, colour, coverage); }
bool In(float2 p, float4 box) { return all(p >= box.xy) && all(p <= box.zw); }

float Segment(float2 p, float2 a, float2 b)
{
    const float2 pa = p - a, ba = b - a;
    return length(pa - ba * saturate(dot(pa, ba) / dot(ba, ba)));
}

float Triangle(float2 p, float2 a, float2 b, float2 c)
{
    const float d = min(Segment(p, a, b), min(Segment(p, b, c), Segment(p, c, a)));
    const float3 side = float3(cross(float3(b - a, 0), float3(p - a, 0)).z, cross(float3(c - b, 0), float3(p - b, 0)).z,
                               cross(float3(a - c, 0), float3(p - c, 0)).z);
    return all(side >= 0.0) || all(side <= 0.0) ? -d : d;
}

// The screens' background: textures_cockpit.py's grid, every 32 texels.
float3 ScreenBack(float2 p)
{
    const float2 g = abs(frac((p - float2(16.0, 48.0)) / 32.0 + 0.5) - 0.5) * 32.0;
    return lerp(SCREEN_BACK, SCREEN_GRID, Stroke(min(g.x, g.y), 1.0));
}

// Segment glyphs: a digit's seven (bits 0 to 6: top, top right, bottom right, bottom, bottom left, top left, middle),
// then three diagonals for N and W. Distance from q, texels from the glyph's top left, to its lit segments.
static const float4 GLYPH_SEGMENTS[10] = {
    float4(0, 0, 1, 0), float4(1, 0, 1, 0.5), float4(1, 0.5, 1, 1), float4(0, 1, 1, 1), float4(0, 0.5, 0, 1),
    float4(0, 0, 0, 0.5), float4(0, 0.5, 1, 0.5), float4(0, 0, 1, 1), float4(0, 1, 0.5, 0.5), float4(0.5, 0.5, 1, 1) };
static const uint DIGITS[10] = { 0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F };
static const uint GLYPH_N = 0xB6, GLYPH_E = 0x79, GLYPH_S = 0x6D, GLYPH_W = 0x336, GLYPH_MINUS = 0x40;

float Glyph(float2 q, float2 size, uint mask)
{
    float d = 1e5;
    [unroll] for (uint i = 0; i < 10; ++i)
        if (mask & (1u << i))
            d = min(d, Segment(q, GLYPH_SEGMENTS[i].xy * size, GLYPH_SEGMENTS[i].zw * size));
    return d;
}

// Distance to a number: `cells` digits from `at` (top left), `height` tall, `decimals` after a point; leading zeros blank
// unless `zeros`, a minus before a negative number.
float Number(float2 p, float2 at, float height, float value, int cells, int decimals, bool zeros)
{
    const float advance = height * 0.62;
    const int cell = (int)floor((p.x - at.x) / advance);
    if (cell < 0 || cell >= cells)
        return 1e5;
    const float n = round(abs(value) * pow(10.0, decimals)), place = pow(10.0, cells - 1 - cell);
    uint mask = DIGITS[(uint)fmod(floor((n + 0.5) / place), 10.0)];
    if (!zeros && n < place && cell < cells - 1 - decimals)
        mask = value < 0.0 && n >= place / 10.0 ? GLYPH_MINUS : 0;
    const float2 q = p - float2(at.x + cell * advance, at.y);
    float d = Glyph(q, float2(height * 0.45, height), mask);
    if (decimals > 0 && cell == cells - 1 - decimals)
        d = min(d, length(q - float2(height * 0.535, height)));
    return d;
}

// A readout: its box wiped, the number drawn again.
void Readout(inout float3 c, float2 p, float4 box, float2 at, float height, float value, int cells, int decimals,
             bool zeros, float3 colour)
{
    if (!In(p, box))
        return;
    c = ScreenBack(p);
    Paint(c, colour, Stroke(Number(p, at, height, value, cells, decimals, zeros), height * 0.12));
}

// The ship's pitch (deg) and the vertical seen from the seat, in the images' frame (y down).
float ShipPitch() { return degrees(asin(clamp(-normalize(shipUp.xyz).y, -1.0, 1.0))); }
float2 ShipVertical()
{
    const float3 u = normalize(shipUp.xyz);
    const float2 v = float2(-u.x, -u.z); // the pilot's right is -x, the image's down -z
    return dot(v, v) > 1e-8 ? normalize(v) : float2(0.0, -1.0);
}

// FLIGHT / ATTITUDE: the horizon and its pitch ladder (5.8 texels a degree), the heading's rose turning under a fixed
// index, the speed (km/h), the altitude above the sea (km), the heading and the clock's minutes and seconds.
float3 FlightScreen(float2 p, float3 c)
{
    const float2 q = p - float2(256.0, 246.0);
    const float r = length(q);
    if (r < 180.0)
    {
        const float2 up = ShipVertical(), along = float2(-up.y, up.x);
        const float m = dot(q, up) / 5.8 + ShipPitch(), a = dot(q, along); // degrees above the horizon, texels along it
        float3 o = lerp(SRGB(4, 10, 13), SRGB(10, 38, 50), Fill(-m * 5.8));
        Paint(o, SCREEN_CYAN, Stroke(m * 5.8, 3.0));
        const float k = round(m / 5.0) * 5.0;
        if (k != 0.0 && abs(k) <= 90.0)
        {
            const bool ten = fmod(k, 10.0) == 0.0;
            const float2 l = float2(a, -(m - k) * 5.8);
            Paint(o, SCREEN_TEXT, Stroke(Segment(l, float2(ten ? -32.0 : -16.0, 0.0), float2(ten ? 32.0 : 16.0, 0.0)), 2.0));
            if (ten)
                Paint(o, SCREEN_TEXT, Stroke(Number(l, float2(38.0, -5.0), 10.0, abs(k), 2, 0, false), 1.2));
        }
        o = lerp(ScreenBack(p), o, Fill(r - 142.0));
        Paint(o, SCREEN_CYAN, Stroke(r - 143.0, 2.0));
        Paint(o, SCREEN_LINE, Stroke(r - 166.5, 3.0));

        // The rose: a tick every 10°, longer every 30°, the cardinal points' letters, north in amber.
        const float bearing = degrees(atan2(q.x, -q.y)) + shipCourse.x, t = round(bearing / 10.0) * 10.0;
        const int tick = ((int)t % 360 + 360) % 360;
        const float arc = radians(bearing - t) * r;
        if (tick % 90 == 0)
        {
            const uint letters[4] = { GLYPH_N, GLYPH_E, GLYPH_S, GLYPH_W };
            Paint(o, tick == 0 ? SCREEN_AMBER : SCREEN_TEXT, Stroke(Glyph(float2(arc + 3.5, 158.0 - r), float2(7.0, 11.0), letters[tick / 90]), 1.6));
        }
        else
        {
            const bool major = tick % 30 == 0;
            Paint(o, major ? SCREEN_CYAN : SCREEN_LINE, Stroke(Segment(float2(arc, r), float2(0.0, major ? 147.0 : 154.0), float2(0.0, 159.0)), 2.0));
        }
        Paint(o, SCREEN_AMBER, Fill(Triangle(p, float2(249.0, 66.0), float2(263.0, 66.0), float2(256.0, 77.0))));

        // The printed aircraft symbol, the only amber inside the dial, stays.
        c = lerp(o, c, saturate((c.r - c.b - 0.1) * 2.5));
    }
    Readout(c, p, float4(14, 112, 100, 142), float2(20, 118), 20.0, shipVelocity.w * 3.6, 5, 0, false, SCREEN_CYAN);
    Readout(c, p, float4(415, 112, 505, 142), float2(421, 118), 18.0, shipUp.w, 5, 2, false, SCREEN_CYAN);
    Readout(c, p, float4(258, 420, 300, 442), float2(263, 424), 13.0, fmod(round(shipCourse.x) + 360.0, 360.0), 3, 0, true, SCREEN_AMBER);
    if (In(p, float4(262, 463, 300, 481)))
    {
        const float clock = shipAir.z;
        c = ScreenBack(p);
        float d = min(Number(p, float2(263, 467), 9.0, floor(clock / 60.0), 2, 0, true),
                      Number(p, float2(282, 467), 9.0, floor(fmod(clock, 60.0)), 2, 0, true));
        d = min(d, min(length(p - float2(277.5, 469.5)), length(p - float2(277.5, 474.0))));
        Paint(c, SCREEN_TEXT, Stroke(d, 1.2));
    }
    return c;
}

// NAV / TERRAIN: a contour map turning with the heading under the ship's mark, 40 m a texel, its contours those of a
// made-up relief that rolls by with the ship; the latitude and longitude.
float3 NavScreen(float2 p, float3 c)
{
    const float h = radians(shipCourse.x), lat = radians(shipCourse.y);
    const float2 ahead = float2(sin(h), cos(h)), right = float2(cos(h), -sin(h)); // east, north
    const float2 q = (p - float2(256.0, 300.0)) * float2(1.0, -1.0);
    const float2 w = float2(radians(shipCourse.z) * cos(lat), lat) * 6378.0 + (q.x * right + q.y * ahead) * 0.04; // km
    const float relief = sin(w.x * 0.9 + 1.7 * sin(w.y * 0.31)) + sin(w.y * 0.73 + 1.2 * sin(w.x * 0.27 + 1.0))
                       + 0.5 * sin((w.x + w.y) * 1.3);
    const float v = relief / 0.7, slope = max(length(float2(ddx(v), ddy(v))) / screenPx, 1e-5); // contours, per texel
    if (In(p, float4(16, 44, 496, 392)))
    {
        c = ScreenBack(p);
        const bool fourth = fmod(abs(round(v)), 4.0) == 0.0;
        Paint(c, fourth ? SRGB(36, 140, 137) : SRGB(24, 95, 93), Stroke(abs(frac(v + 0.5) - 0.5) / slope, fourth ? 2.0 : 1.5));
        Paint(c, SCREEN_CYAN, Stroke(Segment(p, float2(256, 286), float2(256, 48)), 2.0));
        Paint(c, SCREEN_AMBER, Fill(Triangle(p, float2(256, 284), float2(246, 310), float2(266, 310))));
    }
    // Below the map, the printed contours go, the text stays.
    if (In(p, float4(16, 392, 496, 460)))
        c = lerp(ScreenBack(p), c, saturate((c.g - 0.15) / 0.4));
    Readout(c, p, float4(72, 398, 150, 420), float2(75, 403), 12.0, abs(shipCourse.y), 5, 3, true, SCREEN_TEXT);
    Readout(c, p, float4(72, 423, 150, 445), float2(75, 428), 12.0, abs(shipCourse.z), 6, 3, true, SCREEN_TEXT);
    if (In(p, float4(130, 398, 150, 445)))
    {
        const bool lower = p.y > 421.0;
        const uint letter = lower ? (shipCourse.z < 0.0 ? GLYPH_W : GLYPH_E) : (shipCourse.y < 0.0 ? GLYPH_S : GLYPH_N);
        Paint(c, SCREEN_TEXT, Stroke(Glyph(p - float2(137, lower ? 428 : 403), float2(6.0, 12.0), letter), 1.4));
    }
    return c;
}

// SHIP / SYSTEMS: the bars follow the gas, the speed and the clock; the core's output and the hull's temperature, the
// standard air's warmed by the speed.
float3 SystemsScreen(float2 p, float3 c)
{
    const float clock = shipAir.z, gas = shipGauges.x, air = shipAir.x;
    const int row = clamp((int)floor((p.y - 70.0) / 62.0), 0, 4);
    const float y = 76.0 + row * 62.0;
    const float values[5] = { 0.3 + 0.6 * gas + 0.015 * sin(clock * 1.7), gas, 0.9 + 0.03 * sin(clock * 0.53),
                              0.76 + 0.02 * sin(clock * 0.21), 0.25 + 0.35 * gas + air / 3000.0 };
    const float value = saturate(values[row]);
    if (In(p, float4(182.5, y + 4.5, 459.5, y + 13.5)))
    {
        c = ScreenBack(p);
        const float2 centre = float2(184.0 + 135.0 * value, y + 9.0), half = float2(135.0 * value, 3.0);
        const float2 e = abs(p - centre) - half;
        Paint(c, value > 0.55 ? SCREEN_CYAN : SCREEN_AMBER, Fill(max(e.x, e.y)) * step(0.004, value));
    }
    Readout(c, p, float4(393, y + 21, 416, y + 35), float2(395, y + 24), 9.0, value * 100.0, 3, 0, false, SCREEN_TEXT);
    const float altitude = shipUp.w;
    Readout(c, p, float4(93, 404, 130, 426), float2(95, 409), 12.0, 97.6 + 1.5 * gas + 0.3 * sin(clock * 0.9), 3, 1, false, SCREEN_CYAN);
    Readout(c, p, float4(243, 404, 282, 426), float2(253 - 7.44, 409), 12.0,
            288.15 - 6.5 * min(altitude, 11.0) + air * air / 2010.0 + 30.0 * gas, 4, 0, false, SCREEN_CYAN);
    return c;
}

// The analogue dials, 0 to 8 over 240°: the printed needle taken out, its share read from its red over blue, which the
// face and the ticks have not; a new needle at the value.
float3 Dial(float2 p, float3 c, float value)
{
    const float3 printed = SRGB(243, 184, 89);
    const float share = saturate((c.r - 1.15 * c.b) / (printed.r - 1.15 * printed.b));
    c = lerp(saturate((c - share * printed) / max(1.0 - share, 0.1)), SRGB(20, 27, 27), smoothstep(0.6, 0.9, share));
    const float a = radians(-120.0 + 30.0 * clamp(value, 0.0, 8.0));
    Paint(c, SRGB(243, 184, 89), Stroke(Segment(p, 256.0, 256.0 + float2(sin(a), -cos(a)) * 150.0), 6.0));
    Paint(c, SRGB(224, 225, 207), Fill(length(p - 256.0) - 12.0));
    return c;
}

bool ShipIsScreen(uint role) { return role >= SCREEN_NAV && role <= DIAL_HEIGHT; }

// The role's image at uv, `image` its printed colour, linear: what the screen shows now.
float3 ShipScreen(uint role, float2 uv, float3 image)
{
    const float2 p = uv * 512.0;
    screenPx = max(max(length(ddx(p)), length(ddy(p))), 1e-3);
    switch (role)
    {
    case SCREEN_NAV:     return NavScreen(p, image);
    case SCREEN_FLIGHT:  return FlightScreen(p, image);
    case SCREEN_SYSTEMS: return SystemsScreen(p, image);
    case DIAL_GAS:       return Dial(p, image, shipGauges.x * 8.0);       // THRUST %
    case DIAL_PITCH:     return Dial(p, image, 4.0 + ShipPitch() / 22.5); // ATT DEG: level at 4, ±90° at the ends
    default:             return Dial(p, image, shipUp.w - shipCourse.w);  // ALT KM: above the ground
    }
}
#endif
