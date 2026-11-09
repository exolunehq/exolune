// The ship's opaque surfaces: the pack's materials, lit like the objects near the camera (ObjectPixel.hlsl) by the sun
// through the air and the whole sky, with a specular lobe for paint and metal. The ship's own maps shade them: the sun's
// for its cast shadows, the overhead one for the sky the hull hides from the cockpit. The sun's share goes to the second
// target, so that the clouds shade the ship as they shade the ground (AtmospherePass.hlsl).
#include "Planet.hlsli"
#include "PlanetSettings.hlsli"
#include "Atmosphere.hlsli"
#include "SceneExposure.hlsli"
#include "Ship.hlsli"
#include "ShipScreens.hlsli"
#include "ShipNavigator.hlsli"
#ifdef SHIP_SCENE_REFLECTIONS
#include "ShipReflections.hlsli"
#endif

struct Output
{
    float4 radiance : SV_Target0; // alpha: distance (km), for the atmosphere and the temporal smoothing
#ifndef SHIP_SCENE_REFLECTIONS
    float4 sunPart  : SV_Target1;
#endif
};

Output PSMain(ShipPixel input)
{
    const ShipMaterial m = shipMaterials[shipMaterial];
    // The dashboard's screens and dials show the flight (ShipScreens.hlsli), in their colour and their light alike.
    const bool screen = ShipIsScreen(m.role);
    float3 image = ShipImage(m.image[0], m.uv[0], input.uv, 1.0).rgb;
    [branch] if (screen)
        image = ShipScreen(m.role, input.uv.xy, image);
    float3 albedo = m.color.rgb * image;
    float3 instrumentEmission = 0.0;
    const bool navigatorDial = ShipNavigator() && m.role == 12;
    [branch] if (navigatorDial)
        NavigatorInstrument(input.local, albedo, instrumentEmission);
    const float4 metalRough = ShipImage(m.image[1], m.uv[1], input.uv, 1.0);
    const float roughness = clamp(m.roughness * metalRough.g, 0.05, 1.0), metallic = saturate(m.metallic * metalRough.b);
    const float occlusion = lerp(1.0, ShipImage(m.image[3], m.uv[3], input.uv, 1.0).r, m.occlusion);

    // Faces are seen from both sides, the cockpit's tub from inside, thin parts from behind: the normal faces the eye.
    const bool front = dot(input.normal, input.pos) < 0.0;
    float3 n = normalize(front ? input.normal : -input.normal);
    [branch] if (m.image[2] >= 0)
    {
        const float3 t = normalize(input.tangent.xyz - n * dot(n, input.tangent.xyz));
        // glTF's bitangent, cross(n, t) w in its right-handed frame: the left-handed planet frame turns the cross over.
        const float3 b = cross(n, t) * input.tangent.w * (front ? -1.0 : 1.0);
        const float3 bump = (ShipImage(m.image[2], m.uv[2], input.uv, 0.5).xyz * 2.0 - 1.0) * float3(m.normalScale, m.normalScale, 1.0);
        n = normalize(bump.x * t + bump.y * b + bump.z * n);
    }

    const float3 v = normalize(-input.pos), sun = lightDir.xyz, up = camVertical.xyz;
    const float h = max(shipUp.w, 0.0), muS = dot(up, sun), haze = RegionalGround(PlanetDirection(up));
    const float3 beam = SUN_ILLUMINANCE * SunTransmittance(h, muS, haze);
    const float3 sky = SkyIrradiance(h, muS, haze);

    // The sun: Lambert and GGX (Smith-Schlick visibility, Schlick's Fresnel), in the ship's own shadow.
    const float nl = saturate(dot(n, sun)), nv = saturate(dot(n, v)) + 1e-4;
    const float3 f0 = lerp(0.04, albedo, metallic), diffuse = albedo * (1.0 - metallic) / PI;
    const float3 hv = normalize(sun + v);
    const float a = roughness * roughness, a2 = a * a, nh = saturate(dot(n, hv));
    const float d = a2 / (PI * pow(nh * nh * (a2 - 1.0) + 1.0, 2.0));
    const float k = (roughness + 1.0) * (roughness + 1.0) / 8.0;
    const float visibility = 1.0 / ((nl * (1.0 - k) + k) * (nv * (1.0 - k) + k) * 4.0);
    const float3 fresnel = f0 + (1.0 - f0) * pow(1.0 - saturate(dot(hv, v)), 5.0);
    // The relief's shadow too, from the weather pass (ShipWeather.hlsl), one frame late.
    const float shadow = nl > 0.0 ? ShipLight(0, input.local, 0.0004, 1.5) * shipWeather[2].y : 0.0;
    float3 sunLit = (diffuse + d * visibility * fresnel) * beam * nl * shadow;
#ifdef SHIP_SCENE_REFLECTIONS
    sunLit *= shipWeather[2].z;
#endif

    // The sky: from above where the hull does not hide it, the ground's light from below, as on the objects. Under the
    // hull, a fifth of it still comes in, bounced by the cockpit itself.
    const float open = lerp(0.2, 1.0, ShipLight(1, input.local, 0.003, 5.0)), nu = dot(n, up);
    const float3 ground = beam * saturate(muS) + sky;
    const float3 skyE = (sky * (0.5 + 0.5 * nu) * open + GROUND_ALBEDO * ground * (0.5 - 0.5 * nu) * lerp(0.4, 1.0, open)) * occlusion;
    const float3 sheen = f0 + (max(1.0 - roughness, f0) - f0) * pow(saturate(1.0 - nv), 5.0);
    // saturate: nv carries 1e-4 more, and pow of a negative is NaN, a black disc where a panel faces the eye
    // The sky's mirror image along the reflection, as on the canopy (ShipGlass.hlsl): brighter towards the horizon, the
    // ground below it. Rough surfaces blur it into the sky's light; under the hull it dims with the sky.
    const float3 r = reflect(-v, n);
#ifdef SHIP_SCENE_REFLECTIONS
    const float3 env = ShipReflectedEnvironment(input.pos, n, r, roughness);
    const float3 skyLit = diffuse * skyE + sheen * env * occlusion * (1.0 - 0.28 * roughness);
#else
    const float ru = dot(r, up);
    const float3 env = lerp(GROUND_ALBEDO * ground / PI, sky / PI * (1.4 - 0.9 * saturate(ru)), smoothstep(-0.08, 0.08, ru));
    const float3 skyLit = diffuse * skyE
                        + sheen * lerp(env * lerp(0.2, 1.0, open) * occlusion, skyE / PI, sqrt(roughness)) * (1.0 - 0.5 * roughness);
#endif

    // The lights that the flight animates (Ship.hlsli's roles): the nozzles' cores with the gas, the white strobes'
    // double flash every 1.3 s, the red beacons' pulse, the top and the bottom one in turn.
    float glow = 1.0;
    const float clock = shipTurn.z;
    if (m.role == SHIP_ROLE_HOT)
        glow = 0.04 + 0.96 * pow(saturate(shipThrust.x), 1.5);
    else if (m.role == SHIP_ROLE_STROBE)
    {
        const float t = frac(clock / 1.3);
        glow = step(t, 0.035) + step(abs(t - 0.14), 0.0175);
    }
    else if (m.role == SHIP_ROLE_BEACON)
        glow = 0.03 + pow(saturate(sin(2.0 * PI * (clock * 0.8 + (input.local.z < 0.0 ? 0.5 : 0.0)))), 6.0);

    Output o;
    const bool dimmable=screen || navigatorDial || (m.role==0 && shipOptions.y>.5) || (ShipNavigator() && m.role==11);
    const float panelGain=dimmable?NightInstrumentGain():1.0;
    o.radiance = float4(sunLit + skyLit + panelGain*(instrumentEmission + glow * m.emission * (screen ? image : ShipImage(m.image[4], m.uv[4], input.uv, 1.0).rgb)),
                        length(input.pos) / 1000.0);
    if (ShipNavigator() && (m.role == 11 || navigatorDial))
    {
        const float3 localN = float3(dot(n, shipModel[0].xyz), dot(n, shipModel[1].xyz), dot(n, shipModel[2].xyz));
        const float3 localV = float3(dot(v, shipModel[0].xyz), dot(v, shipModel[1].xyz), dot(v, shipModel[2].xyz));
        o.radiance.rgb += panelGain*NavigatorCabinLights(input.local, localN, localV, albedo, metallic, roughness);
    }
#ifdef SHIP_SCENE_REFLECTIONS
    o.radiance.rgb = ReflectionAerial(o.radiance.rgb, input.pos);
    o.radiance.a = -max(o.radiance.a, 1e-6); // opaque overlay, included in the ship's temporal reprojection
#else
    o.sunPart = float4(sunLit, 0.0);
#endif
    return o;
}
