// Characters.hlsli - shared structs, buffers and shadow helpers for skinned characters.
// Must match Characters.h and tools/characters/cook.py (CHR1).
#ifndef CHARACTERS_HLSLI
#define CHARACTERS_HLSLI

cbuffer CharFrame : register(b2)
{
    float4x4 charShadow;    // face-local camera-relative -> character local shadow clip space (transposed)
    float4   charScreen;    // xy: render target dimensions, z: 1/shadowSize, w: actorCount
    float4   charShadowBox; // xyz: shadow volume centre in face-local, w: enabled (0 or 1)
};

cbuffer CharDraw : register(b3)
{
    uint charBaseVertex;
    uint charActorIndex;
    uint charDrawPad0;
    uint charDrawPad1;
};

struct CharRestVertex
{
    float3 pos;
    float3 normal;
    float4 tangent;
    float2 uv;
    uint2  joints;   // 4 x uint16 packed: (j0 | (j1<<16)), (j2 | (j3<<16))
    float4 weights;
    uint   material;
    uint   pad;
};

struct CharBone
{
    float4 c0, c1, c2, c3; // column-major 4x4 matching ozz::math::Float4x4
};

struct CharInstance
{
    float4x4 currModel;     // glTF local -> current face-local camera-relative (transposed)
    float4x4 prevClipModel; // glTF local -> previous frame clip space (transposed)
    float4   tint;          // rgb: per-instance wardrobe tint, w: scale
    uint4    meta;          // x: restFirstVertex, y: vertexCount, z: dstVertexOffset, w: boneBaseOffset
};

struct CharSkinnedVertex
{
    float3 pos;
    float  localY;   // glTF-local height above feet (m) for ground-contact ambient occlusion
    float3 normal;
    uint   material;
    float4 tangent;
    float4 prevClip;
    float2 uv;
    uint   actorIdx;
    uint   pad1;
};

struct CharMaterial
{
    float4 baseColor; // linear rgba factor
    float4 pbr;       // x: roughness, y: metallic, z: normalScale, w: role (0 cloth, 1 skin, 2 hair, 3 eye, 4 leather)
    int4   textures;  // x: colorTex, y: normalTex, z: ormTex, w: alphaMode (0 opaque, 1 dithered)
    float4 extra;     // x: sssStrength, y: sheenStrength, z: tintMask, w: unused
};

struct CharPixel
{
    float4 position : SV_POSITION;
    float3 pos      : POSITION;
    float3 normal   : NORMAL;
    float4 tangent  : TANGENT;
    float4 prevClip : TEXCOORD0;
    float2 uv       : TEXCOORD1;
    nointerpolation uint   material : TEXCOORD2;
    nointerpolation float4 tint     : TEXCOORD3;
    float  localY   : TEXCOORD4;
};

struct CharDualQuat
{
    float4 r; // unit rotation quaternion (x, y, z, w)
    float4 d; // dual translation quaternion
};

CharDualQuat CharBoneToDualQuat(CharBone b)
{
    const float m00 = b.c0.x, m10 = b.c0.y, m20 = b.c0.z;
    const float m01 = b.c1.x, m11 = b.c1.y, m21 = b.c1.z;
    const float m02 = b.c2.x, m12 = b.c2.y, m22 = b.c2.z;
    const float trace = m00 + m11 + m22;
    float4 q;
    if (trace > 0.0)
    {
        const float s = sqrt(max(trace + 1.0, 1e-12)) * 2.0;
        q = float4((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s);
    }
    else if (m00 > m11 && m00 > m22)
    {
        const float s = sqrt(max(1.0 + m00 - m11 - m22, 1e-12)) * 2.0;
        q = float4(0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s);
    }
    else if (m11 > m22)
    {
        const float s = sqrt(max(1.0 + m11 - m00 - m22, 1e-12)) * 2.0;
        q = float4((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s);
    }
    else
    {
        const float s = sqrt(max(1.0 + m22 - m00 - m11, 1e-12)) * 2.0;
        q = float4((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s);
    }
    q = normalize(q);

    const float3 t = b.c3.xyz;
    float4 d;
    d.x = 0.5 * ( t.x * q.w + t.y * q.z - t.z * q.y);
    d.y = 0.5 * (-t.x * q.z + t.y * q.w + t.z * q.x);
    d.z = 0.5 * ( t.x * q.y - t.y * q.x + t.z * q.w);
    d.w = 0.5 * (-t.x * q.x - t.y * q.y - t.z * q.z);

    CharDualQuat dq;
    dq.r = q;
    dq.d = d;
    return dq;
}

CharDualQuat CharBlendDualQuats(CharBone b0, CharBone b1, CharBone b2, CharBone b3, float4 w)
{
    const CharDualQuat dq0 = CharBoneToDualQuat(b0);
    const CharDualQuat dq1 = CharBoneToDualQuat(b1);
    const CharDualQuat dq2 = CharBoneToDualQuat(b2);
    const CharDualQuat dq3 = CharBoneToDualQuat(b3);

    float4 ref = dq0.r;
    if (w.y > w.x && w.y >= w.z && w.y >= w.w) ref = dq1.r;
    else if (w.z > w.x && w.z >= w.w) ref = dq2.r;
    else if (w.w > w.x) ref = dq3.r;

    const float s0 = dot(dq0.r, ref) < 0.0 ? -w.x : w.x;
    const float s1 = dot(dq1.r, ref) < 0.0 ? -w.y : w.y;
    const float s2 = dot(dq2.r, ref) < 0.0 ? -w.z : w.z;
    const float s3 = dot(dq3.r, ref) < 0.0 ? -w.w : w.w;

    float4 qr = dq0.r * s0 + dq1.r * s1 + dq2.r * s2 + dq3.r * s3;
    float4 qd = dq0.d * s0 + dq1.d * s1 + dq2.d * s2 + dq3.d * s3;
    const float invLen = rsqrt(max(dot(qr, qr), 1e-12));
    qr *= invLen;
    qd *= invLen;
    qd -= qr * dot(qr, qd);

    CharDualQuat outDq;
    outDq.r = qr;
    outDq.d = qd;
    return outDq;
}

float3 CharDQTransformDir(CharDualQuat dq, float3 v)
{
    return v + 2.0 * cross(dq.r.xyz, cross(dq.r.xyz, v) + dq.r.w * v);
}

float3 CharDQTransformPos(CharDualQuat dq, float3 p)
{
    const float3 t = 2.0 * (dq.r.w * dq.d.xyz - dq.d.w * dq.r.xyz + cross(dq.r.xyz, dq.d.xyz));
    return CharDQTransformDir(dq, p) + t;
}

float3 CharSkinPos(CharBone b, float3 p)
{
    return b.c0.xyz * p.x + b.c1.xyz * p.y + b.c2.xyz * p.z + b.c3.xyz;
}

float3 CharSkinDir(CharBone b, float3 d)
{
    return b.c0.xyz * d.x + b.c1.xyz * d.y + b.c2.xyz * d.z;
}

#endif
