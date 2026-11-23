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
// Red light travels about 1.2 cm under the skin, green a third and blue a sixth of that. A shading falloff softens over
// the angle this distance spans on the surface, `bend`: wide on a nose, narrow on a cheek. A fixed wide wrap reddens
// every half-lit cheek and forehead.
float3 SkinDiffuseWrap(float ndl, float sss, float bend)
{
    // Capped at a quarter turn's sine: creases such as eyelids and nostrils curve tighter than any scattering shows.
    const float3 scatter = float3(1.0, 0.33, 0.17) * min(bend, 0.25) * sss;
    const float3 wrapped = saturate((ndl + scatter) / (1.0 + scatter));
    const float3 blood = float3(0.95, 0.28, 0.14) * sss * exp(-pow((ndl - 0.08) / 0.22, 2.0)) * 0.2 * min(bend, 0.25);
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

Output PSMain(CharPixel input)
{
    const CharMaterial m = charMaterials[input.material];
    const uint role = (uint)(m.pbr.w + 0.5);

    float4 texColor = float4(1.0, 1.0, 1.0, 1.0);
    if (m.textures.x >= 0)
        texColor = charTextures[NonUniformResourceIndex(m.textures.x)].Sample(charSampler, input.uv);

    // Dithered alpha for hair cards, eyebrows and eyelashes (matches FoliageSequence temporal pattern).
    bool cornea = false;
    if (m.textures.w > 0)
    {
        const uint2 pixel = uint2(input.position.xy);
        uint hash = pixel.x * 0x8da6b343u ^ pixel.y * 0xd8163841u;
        hash ^= hash >> 16; hash *= 0x7feb352du; hash ^= hash >> 15; hash *= 0x846ca68bu; hash ^= hash >> 16;
        const uint flags = (uint)(taa.z + 0.5);
        const uint phase = (flags & 4096u) != 0 ? ((flags >> 3) & 63u) : 0u;
        const float alpha = texColor.a * m.baseColor.a;
        const float noise = FoliageSequence(phase, 1, hash);
        // An eye's cornea shell is clear: dithered, its faint tinted glass veiled the iris. Only its catchlight shows.
        cornea = role == 3 && alpha < 0.5;
        if (role != 3 && (alpha < 0.08 || noise >= saturate((alpha - 0.08) / 0.72)))
            discard;
    }

    float3 albedo = m.baseColor.rgb * texColor.rgb;
    if (m.extra.z > 0.01)
        albedo *= lerp(float3(1.0, 1.0, 1.0), input.tint.rgb, m.extra.z);

    float ao = 1.0;
    float rough = clamp(m.pbr.x, 0.04, 0.98);
    float detailMask = 1.0;
    if (m.textures.z >= 0)
    {
        const float3 orm = charTextures[NonUniformResourceIndex(m.textures.z)].Sample(charSampler, input.uv).rgb;
        ao = lerp(1.0, orm.r, 0.88);
        rough = clamp(orm.g, 0.035, 0.98);
        detailMask = orm.b;
    }
    const float metal = saturate(m.pbr.y);

    const float3 v = normalize(-input.pos);
    float3 n = normalize(input.normal);
    const bool back = dot(n, v) < 0.0;
    if (back)
        n = -n;
    const float3 nGeo = n;
    // The surface's curvature (1/m) times the red scattering distance: the angle that distance spans.
    const float bend = 0.012 * length(fwidth(n)) / max(length(fwidth(input.pos)), 1e-6);

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
    // A painter's catchlight: one crisp spot on the convex cornea, up from its apex towards the sun's side of the view,
    // so every eye looks alive. The iris under it is a concave bowl, which held the spot at its foot.
    if (cornea && dot(nGeo, normalize(v + 0.30 * normalize(up - v * dot(up, v) + 0.7 * (sun - v * dot(sun, v)) + 1e-5))) < 0.987)
        discard;
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
    // An eye takes its face's light: its own brow's shadow left it a dark hole. The lid's shadow is painted below.
    if (charShadowBox.w > 0.5 && role != 3)
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
    // The cornea's index is 1.376: it reflects 2.5 % at normal incidence.
    const float f0Base = (role == 1) ? 0.028 : (role == 2) ? 0.024 : (role == 3) ? 0.025 : 0.04;
    const float3 f0 = lerp(f0Base, albedo, metal);
    const float3 fresnel = f0 + (1.0 - f0) * pow(1.0 - vh, 5.0);
    float3 spec = d * vis * fresnel * nl;

    // Role-specific physically grounded naturalist shading (Milestone 2).
    // Painted style: a brushed surface takes the light stroke by stroke, so the edge of its shadow follows the brush.
    // The strokes are the colour texture's own variation, about its linear mean of 0.70.
    const bool painted = (role == 0 || role == 4) && m.textures.x >= 0;
    const float stroke = dot(texColor.rgb, float3(0.3333, 0.3333, 0.3333));
    const float nlPaint = painted ? saturate(ndlRaw + (stroke - 0.70) * 1.0) : nl;
    float3 diffTerm = albedo * (1.0 - metal) / PI * nlPaint;
    float eyeShade = 1.0;
    if (role == 1)
    {
        // Skin: Pre-Integrated Penner RGB diffuse wrap + dual-lobe dermal/epidermal oil specular.
        const float sss = m.extra.x * detailMask;
        diffTerm = albedo / PI * SkinDiffuseWrap(ndlRaw, sss, bend);
        const float r2 = clamp(rough * 0.50, 0.18, 0.34);
        const float a2s = (r2 * r2) * (r2 * r2);
        const float d2 = a2s / (PI * pow(nh * nh * (a2s - 1.0) + 1.0, 2.0));
        spec = (spec * 0.80 + d2 * vis * fresnel * nl * 0.20) * lerp(0.55, 1.0, ao);
    }
    else if (role == 3)
    {
        // Painted eyes read at a glance in any light; the cook paints the iris clear and the white a muted grey.
        // The eye takes its face's light, wrapped round the eyeball. The white is shaded as the ball it is, lighter
        // round the iris and darker into the corners, and the upper lid lays a narrow band of shadow over its top.
        // The concave iris faces the light with its foot, which comes out lighter on its own.
        const float ball = lerp(0.5, 1.0, smoothstep(0.3, 0.9, nv)) * lerp(1.0, 0.35, smoothstep(0.10, 0.40, dot(n, up)));
        eyeShade = lerp(1.0, ball, 1.0 - detailMask);
        const float wrap = saturate(ndlRaw * 0.5 + 0.5);
        diffTerm = albedo / PI * wrap * wrap * eyeShade;
        // The concave iris lies under the cornea and mirrors nothing: the catchlight stands for the cornea's glint.
        spec *= 1.0 - detailMask;
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
        // Hair: a fibre's two reflections along the card's strand direction (Kajiya-Kay lobes for Marschner's R and TRT).
        // R is the uncoloured surface reflection: 4.6 % of the light (index 1.55), a quarter of it towards the eye,
        // over an 8.6 deg lobe, 0.045 at its peak. TRT crossed the fibre and takes its colour. They replace the
        // surface lobe: a card is no surface, and the two together whitened dark hair in full sun.
        const float3 t = normalize(input.tangent.xyz - n * dot(n, input.tangent.xyz) + 1e-6);
        const float3 bHair = normalize(cross(n, t));
        // Each strand sits at its own slight angle: its tone shifts where its highlight falls, so a head of hair
        // shows streaks along its locks where one shared direction draws a single flat band.
        const float lean = 0.6 * (texColor.g - 0.45);
        const float3 t1 = normalize(bHair + n * (0.10 + lean));
        const float3 t2 = normalize(bHair - n * (0.16 - lean));
        const float sin1 = sqrt(saturate(1.0 - dot(t1, hv) * dot(t1, hv)));
        const float sin2 = sqrt(saturate(1.0 - dot(t2, hv) * dot(t2, hv)));
        const float primary = pow(sin1, 44.0) * 0.045;
        const float secondary = pow(sin2, 14.0) * 0.16;
        const float rim = pow(1.0 - nv, 3.0) * saturate(dot(-v, sun) * 0.5 + 0.5) * 0.04;
        // Painted hair keeps its lobes and takes a little warmth in its second one: raised, dark hair turned blond.
        spec = (float3(1.0, 0.97, 0.93) * primary + lerp(albedo, float3(1.0, 0.80, 0.60), 0.12) * (secondary + rim)) * nl;
    }

    // Painted light: warm where the sun falls, cool in the shade, as a painter mixes them. Not on the eyes.
    const float sunLit = saturate(nlPaint * 1.5) * shadow;
    const bool tinted = role != 3;
    if (tinted && role != 2)
    {
        // Cloth, leather and skin read the sun through three painted values: a warm light, a tinted halftone and a
        // core shadow left to the sky's fill. The brush shows in the light and along the terminator only; the shadow
        // stays one flat mass. A brush relief lit everywhere read as crumpled paper.
        const float halfL = saturate(ndlRaw * 0.5 + 0.5) * lerp(0.45, 1.0, shadow);
        const float band = 1.0 - abs(2.0 * halfL - 1.0);
        const float t = saturate(halfL + (painted ? (stroke - 0.70) * 0.6 * band : 0.0));
        const float lightW = smoothstep(0.60, 0.68, t);
        const float halfW = smoothstep(0.42, 0.50, t) - lightW;
        const float3 flatCol = m.baseColor.rgb * 0.70 * (m.extra.z > 0.01 ? lerp(float3(1.0, 1.0, 1.0), input.tint.rgb, m.extra.z) : float3(1.0, 1.0, 1.0));
        const float3 paintCol = painted ? lerp(flatCol, albedo, saturate(t * 1.6 - 0.4)) : albedo;
        // Skin keeps warmth down into its shadow, as blood shows through it; cloth turns cool there.
        const float3 halfHue = role == 1 ? float3(1.08, 0.82, 0.74) * 0.60 : float3(0.92, 0.94, 1.04) * 0.45;
        const float3 coreHue = role == 1 ? float3(1.0, 0.62, 0.52) * 0.10 : float3(0.0, 0.0, 0.0);
        const float coreW = 1.0 - lightW - halfW;
        // A painter lifts the planes that face the light most, warm and clear: forehead, nose, cheekbones on a face.
        const float hiW = role == 1 ? smoothstep(0.80, 0.90, t) * 0.45 : 0.0;
        diffTerm = paintCol * (1.0 - metal) / PI * (lightW * float3(1.08, 1.0, 0.88) + halfW * halfHue + coreW * coreHue
                 + hiW * float3(1.20, 0.92, 0.62));
        albedo = paintCol;
    }
    else if (tinted)
        diffTerm *= lerp(float3(0.86, 0.90, 1.08), float3(1.10, 1.0, 0.86), sunLit);
    const float3 direct = (diffTerm + spec) * beam * shadow;

    // Sky hemisphere + warm ground bounce + baked cavity AO + soft ground-contact foot grounding AO.
    const float groundAo = lerp(0.68, 1.0, smoothstep(0.0, 0.22, input.localY));
    const float totalAo = ao * groundAo;
    const float hemisphere = 0.5 + 0.5 * dot(n, up);
    const float3 ground = (sky + beam * max(mu, 0.0)) * 0.17;
    const float3 hemiLight = sky * hemisphere + ground * (1.0 - hemisphere);
    float3 ambient = albedo * (1.0 - metal) / PI * hemiLight * totalAo;
    if (tinted)
        ambient *= lerp(float3(0.90, 0.94, 1.10), float3(1.0, 1.0, 1.0), sunLit);
    if (role == 3)
    {
        ambient *= eyeShade;
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
        // The eye's white mirrors the sky at the cornea's own reflectance; the iris, under the cornea, mirrors nothing.
        ambient += env * envFresnel * (1.0 - 0.5 * rough) * (role == 3 ? 1.0 - detailMask : 0.85) * specAo;
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
    o.radiance = float4(cornea ? (beam * shadow + sky) / PI * 0.9 : direct + ambient, length(input.pos) / 1000.0);
    o.sunPart  = float4(direct, 0.0);
    o.velocity = vel;
    return o;
}
