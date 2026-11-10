// Compact, original 5 x 7 bitmap glyphs for the screenshot coordinates. No font texture or OS overlay.
// Low bit: top-left pixel, rows follow. The final pass draws this after tone mapping, outside temporal history.
#ifndef COORDINATES_HLSLI
#define COORDINATES_HLSLI
static const uint2 COORDINATE_GLYPHS[39] = {
    uint2(0xa33ae62eu, 0x3u), // 0
    uint2(0x884210c4u, 0x3u), // 1
    uint2(0xc444422eu, 0x7u), // 2
    uint2(0xe107420fu, 0x3u), // 3
    uint2(0x11f4a988u, 0x2u), // 4
    uint2(0xe107843fu, 0x3u), // 5
    uint2(0xa317842eu, 0x3u), // 6
    uint2(0x8422221fu, 0x0u), // 7
    uint2(0xa317462eu, 0x3u), // 8
    uint2(0xa10f462eu, 0x3u), // 9
    uint2(0x631fc62eu, 0x4u), // A
    uint2(0xe317c62fu, 0x3u), // B
    uint2(0x8210843eu, 0x7u), // C
    uint2(0xe318c62fu, 0x3u), // D
    uint2(0xc217843fu, 0x7u), // E
    uint2(0x4217843fu, 0x0u), // F
    uint2(0xa31e843eu, 0x7u), // G
    uint2(0x631fc631u, 0x4u), // H
    uint2(0x8842108eu, 0x3u), // I
    uint2(0x9284211cu, 0x1u), // J
    uint2(0x52519531u, 0x4u), // K
    uint2(0xc2108421u, 0x7u), // L
    uint2(0x631ad771u, 0x4u), // M
    uint2(0x631cd671u, 0x4u), // N
    uint2(0xa318c62eu, 0x3u), // O
    uint2(0x4217c62fu, 0x0u), // P
    uint2(0x9358c62eu, 0x5u), // Q
    uint2(0x5257c62fu, 0x4u), // R
    uint2(0xe107043eu, 0x3u), // S
    uint2(0x0842109fu, 0x1u), // T
    uint2(0xa318c631u, 0x3u), // U
    uint2(0x1518c631u, 0x1u), // V
    uint2(0xab5ac631u, 0x2u), // W
    uint2(0x62a22a31u, 0x4u), // X
    uint2(0x08422a31u, 0x1u), // Y
    uint2(0xc222221fu, 0x7u), // Z
    uint2(0x08000000u, 0x1u), // .
    uint2(0x000f8000u, 0x0u), // -
    uint2(0x00000000u, 0x0u), // space
};

float3 CoordinateOverlay(float3 color, int2 pixel, int2 size)
{
    [branch] if (coordinateInfo.x == 0u) return color;
    const int scale = clamp(size.x / 640, 1, 3), padding = 6 * scale;
    const int length = int(max(coordinateInfo.x, coordinateInfo.y));
    const int columns = max(1, min(length, (size.x - 2 * padding) / (6 * scale)));
    const int wraps = (length + columns - 1) / columns, lineHeight = 10 * scale;
    const int2 extent = int2(columns * 6 * scale + 2 * padding, 2 * wraps * lineHeight + 2 * padding);
    const int2 origin = int2(0, size.y - extent.y);
    const int2 local = pixel - origin;
    [branch] if (any(local < 0) || any(local >= extent)) return color;
    const float3 background = color * 0.12;
    const int2 q = local - padding;
    if (any(q < 0) || q.x >= columns * 6 * scale || q.y >= 2 * wraps * lineHeight) return background;
    const int row = q.y / lineHeight, sourceRow = row / wraps;
    const int column = (row % wraps) * columns + q.x / (6 * scale);
    if (column >= int(coordinateInfo[sourceRow])) return background;
    const int index = sourceRow * 64 + column;
    const uint packed = coordinateText[index / 16][(index / 4) % 4];
    const uint character = (packed >> ((index % 4) * 8)) & 255u;
    const uint glyph = character >= 48u && character <= 57u ? character - 48u
                     : character >= 65u && character <= 90u ? character - 65u + 10u
                     : character == 46u ? 36u : character == 45u ? 37u : 38u;
    const int2 cell = int2((q.x / scale) % 6, (q.y % lineHeight) / scale);
    if (cell.x >= 5 || cell.y >= 7) return background;
    const uint bit = uint(cell.y * 5 + cell.x);
    const uint ink = (COORDINATE_GLYPHS[glyph][bit / 32u] >> (bit % 32u)) & 1u;
    return ink != 0u ? float3(0.9, 0.95, 1.0) : background;
}

uint ContactCharacter(uint surface,uint column) {
    const uint soil[18]={84,69,82,82,69,32,45,32,65,76,84,32,83,79,85,82,73,83};
    const uint grass[18]={72,69,82,66,69,32,45,32,65,76,84,32,83,79,85,82,73,83};
    const uint gravel[18]={71,82,65,86,73,69,82,32,65,76,84,32,83,79,85,82,73,83};
    const uint rock[18]={82,79,67,72,69,32,45,32,65,76,84,32,83,79,85,82,73,83};
    const uint sand[18]={83,65,66,76,69,32,45,32,65,76,84,32,83,79,85,82,73,83};
    const uint snow[18]={78,69,73,71,69,32,45,32,65,76,84,32,83,79,85,82,73,83};
    const uint wait[18]={83,79,76,32,69,78,32,65,84,84,69,78,84,69,32,32,32,32};
    return surface==1?soil[column]:surface==2?grass[column]:surface==3?gravel[column]:surface==4?rock[column]
        :surface==5?sand[column]:surface==6?snow[column]:wait[column];
}

// Interactive actions use existing frame metadata; no font, texture, or extra render pass.
// Pixel rectangles match D3DApp::MsgProc, including at the smallest supported resolution.
float3 ActionOverlay(float3 color, int2 pixel, int2 size)
{
    const uint flags = coordinateInfo.z;
    [branch] if ((flags & 1u) == 0u) return color;
    const int scale = clamp(size.x / 640,1,3);
    const int2 p = pixel / scale;
    const bool button0 = p.x >= 12 && p.x < 114 && p.y >= 12 && p.y < 33;
    const bool button1 = p.x >= 118 && p.x < 220 && p.y >= 12 && p.y < 33;
    const bool hint = p.x >= 12 && p.x < 220 && p.y >= 35 && p.y < 47;
    if (!button0 && !button1 && !hint) return color;
    const int2 origin = button0 ? int2(18,19) : button1 ? int2(124,19) : int2(16,38);
    const int2 q = p-origin;
    const float3 background = color*0.15 + float3(0.015,0.02,0.025);
    if ((button0 || button1) && (p.y==12 || p.y==32 || p.x==(button0?12:118) || p.x==(button0?113:219)))
        return float3(0.3,0.42,0.45);
    if (any(q<0) || q.y>=7) return background;
    const uint walk[12] = {74,32,32,77,65,82,67,72,69,82,32,32};
    const uint ship[12] = {74,32,32,86,65,73,83,83,69,65,85,32};
    const uint sound[12] = {89,32,32,83,79,78,32,65,67,84,73,70};
    const uint mute[12] = {89,32,32,83,79,78,32,67,79,85,80,69};
    const uint cursor[18] = {65,76,84,32,67,85,82,83,69,85,82,32,32,32,32,32,32,32};
    const uint blocked[18] = {83,79,76,32,73,77,80,82,65,84,73,67,65,66,76,69,32,32};
    const uint freeCam[18] = {67,65,77,32,76,73,66,82,69,32,45,32,68,69,66,85,84,32}; // CAM LIBRE - DEBUT
    const uint horizonCam[18] = {72,79,82,73,90,79,78,32,45,32,68,69,66,85,84,32,32,32}; // HORIZON - DEBUT
    const uint fixedCam[18] = {65,76,84,32,70,73,88,69,32,45,32,68,69,66,85,84,32,32}; // ALT FIXE - DEBUT
    const uint cameraMode = flags >> 4;
    const uint c = q.x/6;
    if (c >= (hint?18u:12u) || q.x%6>=5) return background;
    const uint ch = hint ? ((flags&8u)!=0u?blocked[c]:(flags&2u)!=0u?ContactCharacter(coordinateInfo.w,c):
                            cameraMode==3u?fixedCam[c]:cameraMode==2u?horizonCam[c]:cameraMode==1u?freeCam[c]:cursor[c])
        : button0 ? ((flags&2u)!=0u?ship[c]:walk[c]) : ((flags&4u)!=0u?mute[c]:sound[c]);
    const uint glyph = ch>=65u && ch<=90u ? ch-65u+10u : ch==45u ? 37u : 38u;
    const uint bit = uint(q.y*5+q.x%6);
    return ((COORDINATE_GLYPHS[glyph][bit/32u]>>(bit%32u))&1u)!=0u ? float3(0.9,0.95,1.0) : background;
}
#endif
