// CharacterPixel.hlsl - naturalist Forward HDR shading for rigged characters in Exolune.
// Writes radiance (+distance km in alpha), direct sunlight (for cloud shadows in AtmospherePass)
// and screen-space TAA velocity (delta prevUv - currUv, or -4 when disoccluded).
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "PlanetMap.hlsli"
#include "FoliageSequence.hlsli"
#include "Characters.hlsli"

StructuredBuffer<CharMaterial> charMaterials : register(t32);
Texture2D<float> charShadowMap : register(t33);
Texture2D<float> cityShadowMap : register(t34);
Texture2D<float> shipShadowMap : register(t35);
Texture2D<float4> charTextures[96] : register(t0, space1);

SamplerComparisonState charShadowSampler : register(s4);
SamplerState charSampler : register(s5);

struct Output
{
    float4 radiance : SV_TARGET0;
    float4 sunPart  : SV_TARGET1;
    float2 velocity : SV_TARGET2;
};

float SampleShadowPcf(Texture2D<float> map, float4x4 mat, float3 p, float3 n, float biasOffset, float depthBias, float invSize)
{
    float4 c = mul(float4(p + n * biasOffset, 1.0), mat);
    c.xyz /= max(c.w, 1e-6);
    const float2 uv = c.xy * float2(0.5, -0.5) + 0.5;
    if (any(uv < 0.0) || any(uv > 1.0) || c.z < 0.0 || c.z > 1.0)
        return 1.0;
    float lit = 0.0;
    [unroll] for (int y = -1; y <= 1; ++y)
    [unroll] for (int x = -1; x <= 1; ++x)
        lit += map.SampleCmpLevelZero(charShadowSampler, uv + float2(x, y) * invSize, c.z - depthBias);
    const float edge = min(min(uv.x, uv.y), min(1.0 - uv.x, 1.0 - uv.y));
    return lerp(1.0, lit / 9.0, smoothstep(0.0, 0.045, edge));
}

// Pre-Integrated Skin diffuse approximation (Penner): warm subsurface scattering wrap across the terminator
// while conserving energy and staying 100% compatible with sunPart cloud shadow attenuation.
float3 SkinDiffuseWrap(float ndl, float sss)
{
    const float3 scatter = float3(0.42, 0.14, 0.07) * sss;
    const float3 wrapped = saturate((ndl + scatter) / (1.0 + scatter));
    const float3 blood = float3(0.95, 0.28, 0.14) * sss * exp(-pow((ndl - 0.08) / 0.34, 2.0)) * 0.22;
    return wrapped + blood;
}

// Charlie microfiber sheen (Estevez & Kulla 2017) for natural cloth grazing backscatter.
float CharlieSheen(float nh, float rough)
{
    const float r = max(rough, 0.12);
    const float invR = 1.0 / r;
    const float sin2h = max(1.0 - nh * nh, 1e-4);
    return (2.0 + invR) * pow(sin2h, 0.5 * invR) / (2.0 * PI);
}

// Seamless 3D triplanar oil-brush sampling anchored in rest-pose character coordinates.
// Sharp exponent (12.0) keeps flat brushstrokes crisp on sleeves, chest & cheeks without blur.
void SampleOilTriplanar(int texIdx, float3 pChar, float3 nChar, float scale,
                        float3 pDdx, float3 pDdy, out float3 dNChar, out float paintB, out float paintV)
{
    float3 bw = pow(abs(nChar), 12.0);
    bw /= max(bw.x + bw.y + bw.z, 1e-5);

    const float2 uvXY = float2(pChar.x, -pChar.y) * scale;
    const float2 uvZY = float2(pChar.z, -pChar.y) * scale;
    const float2 uvXZ = float2(pChar.x,  pChar.z) * scale;

    const float2 dxXY = float2(pDdx.x, -pDdx.y) * scale;
    const float2 dyXY = float2(pDdy.x, -pDdy.y) * scale;
    const float2 dxZY = float2(pDdx.z, -pDdx.y) * scale;
    const float2 dyZY = float2(pDdy.z, -pDdy.y) * scale;
    const float2 dxXZ = float2(pDdx.x,  pDdx.z) * scale;
    const float2 dyXZ = float2(pDdy.x,  pDdy.z) * scale;

    const float4 sXY = charTextures[NonUniformResourceIndex(texIdx)].SampleGrad(charSampler, uvXY, dxXY, dyXY);
    const float4 sZY = charTextures[NonUniformResourceIndex(texIdx)].SampleGrad(charSampler, uvZY, dxZY, dyZY);
    const float4 sXZ = charTextures[NonUniformResourceIndex(texIdx)].SampleGrad(charSampler, uvXZ, dxXZ, dyXZ);

    const float2 gXY = sXY.rg * 2.0 - 1.0;
    const float2 gZY = sZY.rg * 2.0 - 1.0;
    const float2 gXZ = sXZ.rg * 2.0 - 1.0;

    const float3 nXY = float3(gXY.x, gXY.y, 0.0);
    const float3 nZY = float3(0.0, gZY.y, gZY.x);
    const float3 nXZ = float3(gXZ.x, 0.0, gXZ.y);

    dNChar = nXY * bw.z + nZY * bw.x + nXZ * bw.y;
    paintB = sXY.b * bw.z + sZY.b * bw.x + sXZ.b * bw.y;
    paintV = sXY.a * bw.z + sZY.a * bw.x + sXZ.a * bw.y;
}

Output PSMain(CharPixel input)
{
    const CharMaterial m = charMaterials[input.material];
    const uint role = (uint)(m.pbr.w + 0.5);
    const bool isPainterlyTripo = (role == 5 && m.extra.w > 0.5);
    const float2 uvDdx = ddx(input.uv);
    const float2 uvDdy = ddy(input.uv);
    const float3 restDdx = ddx(input.restPos);
    const float3 restDdy = ddy(input.restPos);

    float4 texColor = float4(1.0, 1.0, 1.0, 1.0);
    if (m.textures.x >= 0)
        texColor = charTextures[NonUniformResourceIndex(m.textures.x)].Sample(charSampler, input.uv);

    // Dithered alpha for hair cards, eyebrows and eyelashes (matches FoliageSequence temporal pattern).
    if (m.textures.w > 0)
    {
        const uint2 pixel = uint2(input.position.xy);
        uint hash = pixel.x * 0x8da6b343u ^ pixel.y * 0xd8163841u;
        hash ^= hash >> 16; hash *= 0x7feb352du; hash ^= hash >> 15; hash *= 0x846ca68bu; hash ^= hash >> 16;
        const uint flags = (uint)(taa.z + 0.5);
        const uint phase = (flags & 4096u) != 0 ? ((flags >> 3) & 63u) : 0u;
        const float alpha = texColor.a * m.baseColor.a;
        const float noise = FoliageSequence(phase, 1, hash);
        if (alpha < 0.08 || noise >= saturate((alpha - 0.08) / 0.72))
            discard;
    }

    float3 albedo = m.baseColor.rgb * texColor.rgb;
    if (!isPainterlyTripo && m.extra.z > 0.01)
        albedo *= lerp(float3(1.0, 1.0, 1.0), input.tint.rgb, m.extra.z);

    float ao = 1.0;
    float rough = clamp(m.pbr.x, 0.04, 0.98);
    float detailMask = 1.0;
    float metal = saturate(m.pbr.y);
    if (m.textures.z >= 0)
    {
        const float3 orm = charTextures[NonUniformResourceIndex(m.textures.z)].Sample(charSampler, input.uv).rgb;
        ao = lerp(1.0, orm.r, 0.88);
        if (isPainterlyTripo)
        {
            rough = clamp(orm.g * m.pbr.x, 0.035, 0.98);
            metal = saturate(orm.b * m.pbr.y);
        }
        else
        {
            rough = clamp(orm.g, 0.035, 0.98);
            detailMask = orm.b;
        }
    }

    const float3 v = normalize(-input.pos);
    float3 n = normalize(input.normal);
    const bool back = dot(n, v) < 0.0;
    if (back)
        n = -n;

    if (isPainterlyTripo)
    {
        // Validated Iteration 2 painterly constants calibrated against Exolune sunlight reference.
        const float brushScale = 2.60;
        const float brushColor = 0.52;
        const float brushFacet = 0.24;
        const float paintBands = 0.36;
        const float termBreak  = 0.48;
        const float paintSmear = 0.15;
        const float mattePaint = 0.94;
        const float skinPaint  = 0.54;
        const float coolShadow = 0.54;

        const float hs = max(m.extra.x, 0.5);
        const float eyeY = m.extra.y;
        const float noseZ = m.extra.z;
        const int oilTexIdx = (int)(m.extra.w + 0.5) - 1;
        const float eyeX = 0.032 * hs;
        const float lipY = eyeY - 0.068 * hs;
        const float neckY = eyeY - 0.215 * hs;

        const float ax = abs(input.restPos.x);
        const float y = input.restPos.y;
        const float z = input.restPos.z;

        const float edx = max(0.0, abs(ax - eyeX) - 0.36 * eyeX);
        const float edy = max(0.0, abs(y - eyeY) - 0.008 * hs);
        const float edz = max(0.0, (noseZ - 0.064 * hs) - z);
        const float isEye = 1.0 - smoothstep(0.0, 0.007 * hs, sqrt(edx * edx + edy * edy + edz * edz));

        const float ldx = max(0.0, ax - 0.032 * hs);
        const float ldy = max(0.0, abs(y - lipY) - 0.008 * hs);
        const float ldz = max(0.0, (noseZ - 0.058 * hs) - z);
        const float isLip = 1.0 - smoothstep(0.0, 0.008 * hs, sqrt(ldx * ldx + ldy * ldy + ldz * ldz));

        const float protMask = max(isEye, isLip);
        const float skinChroma = smoothstep(0.025, 0.09, albedo.r - albedo.b);
        const float corneaMask = isEye * (1.0 - skinChroma);

        const float faceBand = smoothstep(neckY - 0.035 * hs, neckY, y)
                             * smoothstep(noseZ - 0.135 * hs, noseZ - 0.105 * hs, z)
                             * (1.0 - smoothstep(0.08 * hs, 0.105 * hs, ax));
        const float armZone = smoothstep(0.22 * hs, 0.30 * hs, ax) * (1.0 - smoothstep(1.08 * hs, 1.24 * hs, y));
        const float armSkinTone = smoothstep(0.03, 0.18, albedo.r - albedo.b) * smoothstep(0.01, 0.12, albedo.r - albedo.g * 0.85);
        const float skinMask = saturate(max(faceBand, armZone * armSkinTone) * (1.0 - corneaMask));

        const float nonProt = 1.0 - protMask;
        const float nonCornea = 1.0 - corneaMask;
        const float clothWeight = saturate(nonCornea * (1.0 - skinMask));
        const float pStrength = nonProt * (clothWeight + skinMask * skinPaint);

        // Edge-preserving 5-tap directional brushstroke smoothing on ColorMap (zero cross-seam bleed).
        if (m.textures.x >= 0 && paintSmear > 0.01 && pStrength > 0.02)
        {
            const float2 duv = uvDdx * 0.85 + uvDdy * 0.55;
            const float duvLen = length(duv);
            if (duvLen > 1e-6)
            {
                const float2 stepUv = (duv / duvLen) * min(0.0024, max(duvLen * 2.2, 0.0007)) * paintSmear * nonProt;
                const float3 baseRgb = texColor.rgb;
                float3 accC = baseRgb;
                float accW = 1.0;
                [unroll] for (int si = -2; si <= 2; ++si)
                {
                    if (si == 0) continue;
                    const float3 smp = charTextures[NonUniformResourceIndex(m.textures.x)]
                        .SampleGrad(charSampler, input.uv + stepUv * float(si), uvDdx, uvDdy).rgb;
                    const float3 diffRgb = smp - baseRgb;
                    const float dc2 = dot(diffRgb, diffRgb);
                    const float w = exp(-dc2 * 48.0) * (1.0 - 0.16 * abs(float(si)));
                    accC += smp * w;
                    accW += w;
                }
                const float3 smeared = accC / accW;
                albedo = lerp(albedo, m.baseColor.rgb * smeared, saturate(pStrength * 1.15));
            }
        }

        if (m.textures.y >= 0)
        {
            const float3 t = normalize(input.tangent.xyz - n * dot(n, input.tangent.xyz) + 1e-6);
            const float3 b = cross(n, t) * input.tangent.w * (back ? 1.0 : -1.0);
            const float2 rawRg = charTextures[NonUniformResourceIndex(m.textures.y)].SampleGrad(charSampler, input.uv, uvDdx, uvDdy).rg * 2.0 - 1.0;
            const float2 rg = rawRg * (m.pbr.z * lerp(1.0, 0.48, nonProt));
            const float3 bump = float3(rg, sqrt(saturate(1.0 - dot(rawRg, rawRg))));
            n = normalize(bump.x * t + bump.y * b + bump.z * n);
        }

        // Normal-map variance widens highlights as fine detail falls below a pixel (skip crisp wet cornea).
        if (corneaMask < 0.5)
            rough = saturate(sqrt(rough * rough + 0.25 * max(dot(ddx(n), ddx(n)), dot(ddy(n), ddy(n)))));

        // Rest-pose 3D triplanar flat-brush sampling (broad on cloth, readable 1.38x on face/skin).
        float3 dNCharBroad, dNCharFine;
        float bBroad, vBroad, bFine, vFine;
        SampleOilTriplanar(oilTexIdx, input.restPos, normalize(input.restNormal), brushScale / hs, restDdx, restDdy, dNCharBroad, bBroad, vBroad);
        SampleOilTriplanar(oilTexIdx, input.restPos, normalize(input.restNormal), (brushScale * 1.38) / hs, restDdx, restDdy, dNCharFine, bFine, vFine);

        const float3 dNChar = lerp(dNCharBroad, dNCharFine, skinMask);
        const float paintB = lerp(bBroad, bFine, skinMask);
        const float paintV = lerp(vBroad, vFine, skinMask);
        const float strokeTone = (paintV - 0.5) * 0.58 + (paintB - 0.5) * 0.58;

        // Matte diffuse brushstroke faceting: tilts ONLY diffuse normal nDiff while keeping n smooth (zero glossy bump).
        const float3 dNW = normalize(input.skinX) * dNChar.x + normalize(input.skinY) * dNChar.y + normalize(input.skinZ) * dNChar.z;
        const float3 dNPerp = dNW - n * dot(n, dNW);
        const float facetAmp = brushFacet * pStrength * (1.0 - 0.75 * metal);
        const float3 nDiff = normalize(n + dNPerp * facetAmp);

        // Matte gouache/oil roughness (high matte, zero plastic shine).
        rough = lerp(rough, clamp(lerp(rough, 0.91, 0.82 * mattePaint), 0.35, 0.96), pStrength * (1.0 - metal));

        // Bristle-visible oil-pigment modulation + dry-brush pale bristle highlights on coats.
        const float luma0 = dot(albedo, float3(0.2126, 0.7152, 0.0722));
        const float strokeVal = strokeTone * brushColor * pStrength;
        const float3 clothHue = float3(0.26, 0.08, -0.26) * strokeTone * (0.30 + 0.70 * luma0);
        const float3 skinStrokeHue = float3(0.14, 0.06, -0.04) * strokeTone * (0.35 + 0.65 * luma0);
        const float3 strokeHue = lerp(clothHue, skinStrokeHue, skinMask) * coolShadow * pStrength;
        const float dryBrushLift = max(0.0, paintB - 0.56) * 0.14 * brushColor * clothWeight * (1.0 - metal);
        albedo = max(albedo * (1.0 + strokeVal) + strokeHue * brushColor + float3(1.0, 0.98, 0.95) * dryBrushLift, float3(0.0, 0.0, 0.0));

        const float3 sun = lightDir.xyz;
        const float3 up = camVertical.xyz;
        const float altitude = max(camVertical.w, 0.0);
        const float mu = dot(up, sun);
        const float haze = RegionalGround(PlanetDirection(up));
        const float3 beam = SUN_ILLUMINANCE * SunTransmittance(altitude, mu, haze);
        const float3 sky = SkyIrradiance(altitude, mu, haze);

        // 4-tier brush-stepped tonal planes & brush-broken shadow terminator.
        const float ndlRaw = dot(nDiff, sun);
        const float ndlBrush = ndlRaw + strokeTone * termBreak * pStrength;
        const float nlPhys = saturate(dot(n, sun));

        const float t1 = smoothstep(-0.16, 0.02, ndlBrush);
        const float t2 = smoothstep( 0.06, 0.26, ndlBrush);
        const float t3 = smoothstep( 0.42, 0.62, ndlBrush);
        const float nlStepped = 0.03 + 0.24 * t1 + 0.35 * t2 + 0.38 * t3;
        const float nl = lerp(nlPhys, nlStepped, paintBands * pStrength);

        // Luminous portrait skin highlights (warm golden-amber lit / sienna shadow) & cloth sunlight warmth.
        const float luma = dot(albedo, float3(0.2126, 0.7152, 0.0722));
        const float lightZone = smoothstep(0.24, 0.66, ndlBrush);
        const float termZone = exp(-pow((ndlBrush - 0.06) / 0.22, 2.0));
        const float3 litShift = lerp(float3(1.06, 1.01, 0.90), float3(1.10, 1.00, 0.86), skinMask);
        float3 warmAl = albedo * lerp(float3(1.0, 1.0, 1.0), litShift, lightZone * 0.75 * coolShadow * pStrength);
        warmAl = lerp(float3(luma, luma, luma), warmAl, 1.0 + 0.26 * termZone * coolShadow * pStrength);
        albedo = max(warmAl, float3(0.0, 0.0, 0.0));

        const float nv = max(dot(n, v), 0.001);
        const float3 hv = normalize(sun + v);
        const float nh = saturate(dot(n, hv));
        const float vh = saturate(dot(v, hv));

        // Self & peer shadows (local 0-35m map) + city building/canopy shadows + ship shadow.
        float shadow = 1.0;
        if (charShadowBox.w > 0.5)
            shadow *= SampleShadowPcf(charShadowMap, charShadow, input.pos, n, 0.025, 0.00055, charScreen.z);
        if (cityLandGrid.w > 0.5)
            shadow *= SampleShadowPcf(cityShadowMap, citySunShadow, input.pos, n, 0.045, 0.00004, 1.0 / 4096.0);
        if (shipSphere.w > 0.0)
            shadow *= SampleShadowPcf(shipShadowMap, shipSunShadow, input.pos, n, 0.03, 0.0004, 1.0 / 2048.0);

        // Suppress plastic/glossy specular on ALL non-corneal, non-metallic painted surfaces.
        const float specKeep = lerp(1.0, 1.0 - 0.96 * mattePaint, nonCornea * (1.0 - metal));

        const float alphaR = rough * rough;
        const float a2 = alphaR * alphaR;
        const float d = a2 / (PI * pow(nh * nh * (a2 - 1.0) + 1.0, 2.0));
        const float k = (rough + 1.0) * (rough + 1.0) / 8.0;
        const float vis = 1.0 / max(4.0 * (nlPhys * (1.0 - k) + k) * (nv * (1.0 - k) + k), 1e-5);
        float f0Base = lerp(0.04, 0.028, skinMask);
        f0Base = lerp(f0Base, 0.048, corneaMask);
        const float3 f0 = lerp(float3(f0Base, f0Base, f0Base), albedo, metal);
        const float3 fresnel = f0 + (1.0 - f0) * pow(1.0 - vh, 5.0);
        float3 spec = d * vis * fresnel * nlPhys * specKeep;

        // Diffuse: warm SkinDiffuseWrap driven by painterly brushstroke light on cheeks, nose, forehead & lips.
        const float3 diffLambert = albedo * (1.0 - metal) / PI * nl;
        const float3 wrapRaw = SkinDiffuseWrap(dot(n, sun), 0.52);
        const float3 wrapPainted = SkinDiffuseWrap(ndlBrush, 0.52);
        const float3 skinToneCurve = lerp(wrapPainted, lerp(wrapPainted * 0.34, float3(1.05, 1.00, 0.93), nlStepped), 0.72 * paintBands);
        const float3 diffSkin = albedo / PI * lerp(wrapRaw, skinToneCurve, skinPaint * nonProt);
        const float3 diffEye = albedo / PI * max(nlPhys, saturate((dot(n, sun) + 0.35) / 1.35) * 0.45);
        float3 diffTerm = lerp(diffLambert, diffSkin, skinMask);
        diffTerm = lerp(diffTerm, diffEye, corneaMask);

        // Cloth Charlie sheen suppressed cleanly in matte painting mode.
        const float sheenD = CharlieSheen(nh, rough);
        const float3 sheenTint = lerp(float3(1.0, 1.0, 1.0), albedo, 0.35);
        spec += sheenTint * sheenD * 0.38 * 0.14 * nlPhys * clothWeight * (1.0 - metal) * specKeep;

        // Wet eye corneal reflection strictly on sclera/iris (corneaMask).
        const float rc = 0.042;
        const float ac2 = (rc * rc) * (rc * rc);
        const float dc = ac2 / (PI * pow(nh * nh * (ac2 - 1.0) + 1.0, 2.0));
        spec = lerp(spec, max(spec, dc * vis * fresnel * nlPhys * 1.05), corneaMask);

        const float3 direct = (diffTerm + spec) * beam * shadow;

        // Sky hemisphere + warm ground bounce + cool sky-indigo cloth shadows & warm sienna skin shadows.
        const float groundAo = lerp(0.68, 1.0, smoothstep(0.0, 0.22, input.localY));
        const float totalAo = ao * groundAo;
        const float hemisphere = 0.5 + 0.5 * lerp(dot(n, up), dot(nDiff, up), 0.6 * pStrength);
        const float3 ground = (sky + beam * max(mu, 0.0)) * 0.17;
        const float3 hemiLight = sky * hemisphere + ground * (1.0 - hemisphere);

        const float shadowZone = max(1.0 - smoothstep(-0.08, 0.34, ndlBrush), (1.0 - shadow) * 0.75);
        const float3 shadowTint = lerp(float3(1.0, 1.0, 1.0), lerp(float3(0.76, 0.88, 1.20), float3(0.92, 0.74, 0.64), skinMask),
                                      shadowZone * coolShadow * pStrength);
        const float shadowLift = 1.0 + 0.28 * coolShadow * shadowZone * pStrength;
        float3 ambient = albedo * (1.0 - metal) / PI * hemiLight * totalAo * shadowTint * shadowLift;
        ambient += albedo * float3(0.14, 0.045, 0.02) / PI * hemiLight * 0.52 * totalAo * skinMask;
        ambient *= lerp(1.0, 1.12, corneaMask);

        const float3 refl = reflect(-v, n);
        const float ru = dot(refl, up);
        const float3 env = lerp(ground / PI, sky / PI * (1.35 - 0.65 * saturate(ru)), smoothstep(-0.08, 0.08, ru));
        const float3 envFresnel = f0 + (max(1.0 - rough, f0) - f0) * pow(1.0 - nv, 5.0);
        const float specAo = saturate(totalAo + 0.25);
        ambient += env * envFresnel * (1.0 - 0.5 * rough) * lerp(0.85, 1.45, corneaMask) * specAo * specKeep;

        float2 vel = float2(-4.0, -4.0);
        if (input.prevClip.w > 1e-4)
        {
            const float2 prevUv = input.prevClip.xy / input.prevClip.w * float2(0.5, -0.5) + 0.5;
            if (all(prevUv >= 0.0) && all(prevUv <= 1.0))
            {
                const float2 currUv = input.position.xy / max(charScreen.xy, float2(1.0, 1.0));
                vel = clamp(prevUv - currUv, float2(-2.0, -2.0), float2(2.0, 2.0));
            }
        }

        Output o;
        o.radiance = float4(direct + ambient, length(input.pos) / 1000.0);
        o.sunPart  = float4(direct, 0.0);
        o.velocity = vel;
        return o;
    }

    if (m.textures.y >= 0)
    {
        const float3 t = normalize(input.tangent.xyz - n * dot(n, input.tangent.xyz) + 1e-6);
        // glTF bitangent in left-handed Exolune planet frame (matches ShipPixel.hlsl).
        const float3 b = cross(n, t) * input.tangent.w * (back ? 1.0 : -1.0);
        const float2 rg = charTextures[NonUniformResourceIndex(m.textures.y)].Sample(charSampler, input.uv).rg * 2.0 - 1.0;
        const float3 bump = float3(rg * m.pbr.z, sqrt(saturate(1.0 - dot(rg, rg))));
        n = normalize(bump.x * t + bump.y * b + bump.z * n);
    }

    // Normal-map variance widens highlights as fine detail falls below a pixel (prevents distant sparkle).
    if (role != 3)
        rough = saturate(sqrt(rough * rough + 0.25 * max(dot(ddx(n), ddx(n)), dot(ddy(n), ddy(n)))));

    const float3 sun = lightDir.xyz;
    const float3 up = camVertical.xyz;
    const float altitude = max(camVertical.w, 0.0);
    const float mu = dot(up, sun);
    const float haze = RegionalGround(PlanetDirection(up));
    const float3 beam = SUN_ILLUMINANCE * SunTransmittance(altitude, mu, haze);
    const float3 sky = SkyIrradiance(altitude, mu, haze);

    const float ndlRaw = dot(n, sun);
    const float nl = saturate(ndlRaw);
    const float nv = max(dot(n, v), 0.001);
    const float3 hv = normalize(sun + v);
    const float nh = saturate(dot(n, hv));
    const float vh = saturate(dot(v, hv));

    // Self & peer shadows (local 0-35m map) + city building/canopy shadows + ship shadow.
    float shadow = 1.0;
    if (charShadowBox.w > 0.5)
        shadow *= SampleShadowPcf(charShadowMap, charShadow, input.pos, n, 0.025, 0.00055, charScreen.z);
    if (cityLandGrid.w > 0.5)
        shadow *= SampleShadowPcf(cityShadowMap, citySunShadow, input.pos, n, 0.045, 0.00004, 1.0 / 4096.0);
    if (shipSphere.w > 0.0)
        shadow *= SampleShadowPcf(shipShadowMap, shipSunShadow, input.pos, n, 0.03, 0.0004, 1.0 / 2048.0);

    // GGX primary specular lobe.
    const float alpha = rough * rough;
    const float a2 = alpha * alpha;
    const float d = a2 / (PI * pow(nh * nh * (a2 - 1.0) + 1.0, 2.0));
    const float k = (rough + 1.0) * (rough + 1.0) / 8.0;
    const float vis = 1.0 / max(4.0 * (nl * (1.0 - k) + k) * (nv * (1.0 - k) + k), 1e-5);
    const float f0Base = (role == 1) ? 0.028 : (role == 2) ? 0.024 : (role == 3) ? 0.048 : 0.04;
    const float3 f0 = lerp(f0Base, albedo, metal);
    const float3 fresnel = f0 + (1.0 - f0) * pow(1.0 - vh, 5.0);
    float3 spec = d * vis * fresnel * nl;

    // Role-specific physically grounded naturalist shading (Milestone 2).
    float3 diffTerm = albedo * (1.0 - metal) / PI * nl;
    if (role == 1)
    {
        // Skin: Pre-Integrated Penner RGB diffuse wrap + dual-lobe dermal/epidermal oil specular.
        const float sss = m.extra.x * detailMask;
        diffTerm = albedo / PI * SkinDiffuseWrap(ndlRaw, sss);
        const float r2 = clamp(rough * 0.50, 0.18, 0.34);
        const float a2s = (r2 * r2) * (r2 * r2);
        const float d2 = a2s / (PI * pow(nh * nh * (a2s - 1.0) + 1.0, 2.0));
        spec = (spec * 0.80 + d2 * vis * fresnel * nl * 0.20) * lerp(0.55, 1.0, ao);
    }
    else if (role == 3)
    {
        // Wet Eye: crisp glossy cornea reflection + soft backlit iris caustic scatter so eyes look alive.
        const float irisScatter = saturate((ndlRaw + 0.35) / 1.35) * detailMask;
        diffTerm = albedo / PI * lerp(nl, max(nl, irisScatter * 0.55), detailMask);
        const float rc = 0.042, ac2 = (rc * rc) * (rc * rc);
        const float dc = ac2 / (PI * pow(nh * nh * (ac2 - 1.0) + 1.0, 2.0));
        spec = max(spec, dc * vis * fresnel * nl * 1.15);
    }
    else if (role == 0 && m.extra.y > 0.01)
    {
        // Fabric: Charlie microfiber sheen (Estevez & Kulla) weighted by weave/cavity mask.
        const float sheenD = CharlieSheen(nh, rough);
        const float3 sheenTint = lerp(float3(1.0, 1.0, 1.0), albedo, 0.35);
        spec += sheenTint * sheenD * m.extra.y * detailMask * 0.14 * nl;
    }
    else if (role == 2)
    {
        // Hair: dual-band anisotropic Kajiya-Kay / Marschner-inspired sheen along hair card tangent/bitangent.
        const float3 t = normalize(input.tangent.xyz - n * dot(n, input.tangent.xyz) + 1e-6);
        const float3 bHair = normalize(cross(n, t));
        const float3 t1 = normalize(bHair + n * 0.10);
        const float3 t2 = normalize(bHair - n * 0.16);
        const float sin1 = sqrt(saturate(1.0 - dot(t1, hv) * dot(t1, hv)));
        const float sin2 = sqrt(saturate(1.0 - dot(t2, hv) * dot(t2, hv)));
        const float primary = pow(sin1, 44.0) * 0.20;
        const float secondary = pow(sin2, 14.0) * 0.16;
        const float rim = pow(1.0 - nv, 3.0) * saturate(dot(-v, sun) * 0.5 + 0.5) * 0.14;
        spec += (float3(1.0, 0.97, 0.93) * primary + lerp(albedo, float3(1.0, 0.92, 0.82), 0.25) * (secondary + rim)) * nl;
    }

    const float3 direct = (diffTerm + spec) * beam * shadow;

    // Sky hemisphere + warm ground bounce + baked cavity AO + soft ground-contact foot grounding AO.
    const float groundAo = lerp(0.68, 1.0, smoothstep(0.0, 0.22, input.localY));
    const float totalAo = ao * groundAo;
    const float hemisphere = 0.5 + 0.5 * dot(n, up);
    const float3 ground = (sky + beam * max(mu, 0.0)) * 0.17;
    const float3 hemiLight = sky * hemisphere + ground * (1.0 - hemisphere);
    float3 ambient = albedo * (1.0 - metal) / PI * hemiLight * totalAo;
    if (role == 1)
    {
        // Subtle warm dermal scatter in shadow/overcast so faces keep healthy life without flat lighting.
        ambient += albedo * float3(0.14, 0.045, 0.02) / PI * hemiLight * m.extra.x * detailMask * totalAo;
    }
    else if (role == 3)
    {
        // Clean moist sclera & vivid iris visibility in ambient/socket lighting.
        ambient *= 1.18;
    }
    const float3 refl = reflect(-v, n);
    const float ru = dot(refl, up);
    const float3 env = lerp(ground / PI, sky / PI * (1.35 - 0.65 * saturate(ru)), smoothstep(-0.08, 0.08, ru));
    const float3 envFresnel = f0 + (max(1.0 - rough, f0) - f0) * pow(1.0 - nv, 5.0);
    const float specAo = saturate(totalAo + 0.25);
    if (role == 2)
    {
        // Hair ambient sheen: subdued and softly tinted by strand albedo (prevents silver-grey grazing sky halo).
        const float3 hairTint = lerp(albedo, float3(1.0, 0.96, 0.92), 0.20);
        ambient += env * envFresnel * hairTint * (1.0 - 0.5 * rough) * 0.20 * totalAo;
    }
    else
    {
        ambient += env * envFresnel * (1.0 - 0.5 * rough) * (role == 3 ? 2.25 : 0.85) * specAo;
    }

    // Exact screen-space TAA velocity: delta (prevUv - currUv), or -4 sentinel when disoccluded.
    float2 vel = float2(-4.0, -4.0);
    if (input.prevClip.w > 1e-4)
    {
        const float2 prevUv = input.prevClip.xy / input.prevClip.w * float2(0.5, -0.5) + 0.5;
        if (all(prevUv >= 0.0) && all(prevUv <= 1.0))
        {
            const float2 currUv = input.position.xy / max(charScreen.xy, float2(1.0, 1.0));
            vel = clamp(prevUv - currUv, float2(-2.0, -2.0), float2(2.0, 2.0));
        }
    }

    Output o;
    o.radiance = float4(direct + ambient, length(input.pos) / 1000.0);
    o.sunPart  = float4(direct, 0.0);
    o.velocity = vel;
    return o;
}
