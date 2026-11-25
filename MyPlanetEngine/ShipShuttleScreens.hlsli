// Native instruments on the shuttle's 5:4 glass. The fixed print and the neutral pose
// in the GLB are authored in the same 640 by 512 drawing coordinates in textures_poste.py.
#ifndef SHIP_SHUTTLE_SCREENS_HLSLI
#define SHIP_SHUTTLE_SCREENS_HLSLI

#define SHUTTLE_GOLD SRGB(250, 177, 80)
#define SHUTTLE_IVORY SRGB(223, 217, 192)
#define SHUTTLE_MINOR SRGB(121, 145, 143)

float3 ShuttlePaper(float y) { return Srgb(lerp(float3(15,33,43), float3(20,43,53), saturate(y/512.0))); }

// The receiver takes over the drawing area of the console. Preserve the outer bezel
// and the printed instrument header. The lamp holds during pauses, the VU follows speech.
float3 ShuttleReceiver(float2 p, float3 image)
{
    if (!In(p, float4(22,74,618,416))) return image;
    float3 ink = ShuttlePaper(p.y) * 0.80;
    const float2 q = p - float2(146,234);
    const float radius = length(q);
    Paint(ink, SCREEN_CYAN, Stroke(radius - 61, 5.0) * 0.75);
    Paint(ink, SHUTTLE_GOLD, Fill(radius - 26) * (0.57 + 0.43 * shipRadio.y));
    const float2 speaker = float2(abs(q.x), q.y);
    Paint(ink, SHUTTLE_GOLD, Stroke(Segment(speaker,float2(11,83),float2(36,83)),4.0));
    if (In(p, float4(263,159,576,300))) {
        const float column = floor((p.x - 263) / 24);
        const float h = 12 + 4.0 * column;
        const float2 d = abs(float2(fmod(p.x-263,24.0)-10, p.y-231)) - float2(7,h);
        const float level = saturate(shipRadio.y * 13.0 - column);
        Paint(ink, lerp(SRGB(38,68,75), column < 10 ? SCREEN_CYAN : SHUTTLE_GOLD, level), Fill(max(d.x,d.y)));
    }
    Paint(ink, SCREEN_LINE, Stroke(Segment(p,float2(60,349),float2(582,349)),3.0));
    return lerp(image, ink, shipRadio.x);
}

float3 ShuttleScreen(uint role, float2 texel, float3 c)
{
    const float2 p = texel * float2(1.25, 1);
    const float heading = frac(shipCourse.x / 360.0) * 360.0;
    const float altitude = shipGauges.z > 0.0 ? shipGauges.y : shipUp.w;
    if (shipAutomation.y > .5 && role == SCREEN_SYSTEMS) {
        const int row = clamp((int)floor((p.y-91.0)/79.0),0,3);
        const float baseline = 124.0 + 79.0*row;
        if (abs(p.y-baseline)<16 && p.x>=186 && p.x<508) {
            const float cell=floor((p.x-186)/16.0);
            float ink=shipEquipment[row]*20.0-cell;
            const float2 d=abs(float2(fmod(p.x-186,16.0)-7.5,p.y-baseline))-float2(6,10);
            Paint(c,lerp(SRGB(35,64,70),SCREEN_CYAN,saturate(ink)),Fill(max(d.x,d.y)));
        }
        if (abs(p.y-baseline)<23 && p.x>516)
            Paint(c,SHUTTLE_IVORY,Stroke(Number(p,float2(530,baseline-12),22,shipEquipment[row]*100,3,0,false),2.7));
        const bool manual=((uint)shipAutomation.x & (1u<<row))!=0;
        Paint(c,manual?SHUTTLE_GOLD:SCREEN_CYAN,Fill(length(p-float2(165,baseline))-5.5));
        if (p.y>445 && p.y<492 && p.x<328) {
            const bool engine=p.x>158;
            Paint(c,SHUTTLE_IVORY,Stroke(Number(p,float2(engine?175:28,452),20,
                100*(engine?shipGauges.w:shipGauges.x),3,0,false),2.3));
        }
        Paint(c,lerp(SCREEN_LINE,SHUTTLE_GOLD,shipRadio.x),Fill(length(p-float2(494,34))-4.5));
        if (shipRadio.x>.01 && In(p,float4(506,25,550,43)))
            Paint(c,SCREEN_CYAN,Fill(p.x-506-shipRadio.y*44));
        Paint(c,SCREEN_CYAN,Fill(length(p-float2(364,447))-4.5));
        Paint(c,SHUTTLE_GOLD,Fill(length(p-float2(492,447))-4.5));
        return c;
    }
    if (shipAutomation.y > .5 && role == SCREEN_NAV && In(p, float4(19,119,145,154)))
        Paint(c,SHUTTLE_IVORY,Stroke(Number(p,float2(27,123),16,shipCourse.z,6,1,false),2.0));
    if (p.y > 461.0 && p.y < 501.0)
    {
        const bool right = p.x > 330.0;
        const float2 start = float2(right ? 365.0 : 28.0, 466.0);
        if (p.x >= start.x - 3.0 && p.x < start.x + 190.0)
        {
            const float value = role == SCREEN_FLIGHT ? (right ? altitude : shipVelocity.w * 3.6)
                : role == SCREEN_NAV ? (right ? shipCourse.y : fmod(round(heading),360.0))
                : (right ? shipAir.x : 100.0 * shipGauges.x);
            const int decimals = right && role != SCREEN_SYSTEMS ? (role == SCREEN_FLIGHT ? 2 : 1) : 0;
            const bool padded = !right && role == SCREEN_NAV;
            c = ShuttlePaper(p.y);
            Paint(c, right || role == SCREEN_FLIGHT ? SHUTTLE_IVORY : SHUTTLE_GOLD,
                Stroke(Number(p, start, 22.0, value, padded ? 3 : 6, decimals, padded), 2.6));
        }
        return c;
    }
    if (role == SCREEN_FLIGHT)
    {
        const float2 q = p - float2(320,242);
        const float r = length(q);
        if (r < 143.0)
        {
            const float2 up = ShipVertical(), side = float2(-up.y, up.x);
            const float above = dot(q,up) + 5.2 * ShipPitch();
            const float x = dot(q,side);
            const float gradient = 1.0 - saturate(abs(above) / 142.0);
            float3 sky = lerp(SRGB(37,102,139), SRGB(51,145,185), gradient);
            float3 earth = lerp(SRGB(141,68,38), SRGB(204,123,58), gradient);
            float3 glass = lerp(earth, sky, Fill(-above));
            Paint(glass, SHUTTLE_IVORY, Stroke(above, 3.0));
            const float tick = round(above / 26.0);
            if (abs(tick) >= 1.0 && abs(tick) <= 18.0)
            {
                const float halfWidth = fmod(abs(tick), 2.0) < 0.5 ? 29.0 : 15.0;
                Paint(glass, SHUTTLE_IVORY, Stroke(Segment(float2(x, above-tick*26.0),
                    float2(-halfWidth,0), float2(halfWidth,0)), 2.1));
            }
            const float2 wing = float2(abs(q.x),q.y);
            float mark = min(Segment(wing,float2(22,17),float2(35,6)), Segment(wing,float2(35,6),float2(79,6)));
            mark = min(mark, abs(length(q-float2(0,7))-5.0));
            Paint(glass, SHUTTLE_GOLD, Stroke(mark,4.5));
            c = lerp(c,glass,Fill(r-142.0));
        }
        if (In(p,float4(32,232,89,254)) || In(p,float4(552,232,609,254)))
        {
            const bool left = p.x<320.0;
            const float display = left ? shipVelocity.w * 3.6 : altitude;
            c = ShuttlePaper(p.y);
            Paint(c, SHUTTLE_IVORY, Stroke(Number(p,float2(left ? 34 : 554,237),12.0,display,6,left?0:1,false),1.7));
        }
    }
    else if (role == SCREEN_NAV)
    {
        const float2 q = p - float2(320,241);
        const float r = length(q);
        if (r < 164.5)
        {
            const float bearing = degrees(atan2(q.x,-q.y)) + heading;
            const float tick = round(bearing / 5.0);
            const float arc = radians(bearing - tick*5.0)*r;
            const bool major = fmod(abs(tick),6.0)<0.5;
            const float inside = major ? 141.0 : (fmod(abs(tick),2.0)<0.5 ? 150.0 : 155.0);
            c = ShuttlePaper(p.y);
            const float grid = abs(frac((bearing+22.5) / 45.0)-.5)*r*radians(45.0);
            Paint(c,SRGB(46,72,76), Stroke(grid,1.1)*saturate((139.0-r)/5.0));
            Paint(c,SRGB(95,95,74), Stroke(min(abs(r-46.0),abs(r-123.0)),1.1));
            Paint(c,SRGB(176,129,72), Stroke(min(abs(r-92.0),abs(r-151.0)),2.0));
            Paint(c,major?SHUTTLE_GOLD:SHUTTLE_MINOR, Stroke(Segment(float2(arc,r),float2(0,inside),float2(0,161)),2.2));
            const float cardinal = round(bearing/90.0);
            const uint letters[4] = {GLYPH_N,GLYPH_E,GLYPH_S,GLYPH_W};
            const uint index = (uint)(((int)cardinal % 4 + 4) % 4);
            const float2 axis = float2(sin(radians(90.0*cardinal-heading)),-cos(radians(90.0*cardinal-heading)));
            Paint(c,SHUTTLE_GOLD,Stroke(Glyph(q-axis*121.0+float2(4.5,7),float2(9,14),letters[index]),2.0));
            float mark = Segment(q,float2(0,-82),float2(0,48));
            mark=min(mark,Segment(float2(abs(q.x),q.y),float2(0,-9),float2(20,7)));
            Paint(c,SHUTTLE_GOLD,Stroke(mark,3.0));
            Paint(c,SHUTTLE_IVORY,Fill(length(q)-4.0));
        }
    }
    else if (In(p,float4(171,344,567,392)))
    {
        const bool lower = p.y>370.0;
        const float y = lower?386.0:350.0;
        const float value = lower?saturate(shipAir.x/400.0):saturate(shipGauges.x);
        const float cell = floor((p.x-171.0)/20.0);
        float2 d=abs(float2(p.x-(179.0+cell*20.0),p.y-y))-float2(8.0,5.0);
        const float within=Fill(max(d.x,d.y));
        if (abs(p.y-y)<6.0)
        {
            c=ShuttlePaper(p.y);
            Paint(c,lerp(SRGB(46,72,76),SHUTTLE_GOLD,saturate(value*20.0-cell)),within);
        }
    }
    return c;
}
#endif
