// FFT ocean spike: shared displacement derivatives, LEAN slope moments and persistent foam.
// The atmospheric reflection and shallow-water optics remain the engine's common water functions.
// Foam material adapted from Noniv/web-ocean (MIT); see third_party/web-ocean/LICENSE.
#ifndef SEA_HLSLI
#define SEA_HLSLI
#include "OceanSurface.hlsli"
float2 CoxMunk(float u) { return float2(0.00316*u,0.003+0.00192*u); }
float Whitecaps(float u) { return min(3.84e-6*pow(u,3.41),0.5); }
// The normal law's tail beyond z, times e^(z^2 / 2), for z >= 0: erfcx, Abramowitz and Stegun 7.1.26, within 1.5e-7.
float3 ScaledTail(float3 z)
{
    const float3 t = 1.0 / (1.0 + 0.3275911 * 0.70710678 * z);
    return 0.5 * t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
}

// log of the normal law's tail beyond z, for any z, and that log plus z^2 / 2 where z >= 0, without overflow.
float3 LogTail(float3 z)
{
    const float3 t = ScaledTail(abs(z));
    return z >= 0.0 ? log(t) - 0.5 * z * z : log(1.0 - t * exp(-0.5 * z * z));
}

// The water's reflectance seen from above, as a diffuse albedo (docs/recherche-mer.md, section 4). Deep water's own,
// by type: clear ocean blue, cold and coastal water greener with plankton and sediment. Then the bottom seen through the
// water, Maritorena, Morel and Gentili 1994: R = R_deep + (A - R_deep) e^(-2 K d). Its mean over the sea part of the pixel,
// whose elevations spread normally by `spread` around `elevation` (m): the exact mean of e^(2 K e) over e < 0.
float3 WaterAlbedo(float elevation, float spread, float type)
{
    const float3 deep = lerp(float3(0.0015, 0.0049, 0.033), float3(0.003, 0.012, 0.012), type);
    const float3 k = lerp(float3(0.36, 0.07, 0.022), float3(0.5, 0.2, 0.3), type); // diffuse attenuation (1/m)
    const float3 bottom = 0.54 * float3(0.30, 0.25, 0.18); // wet sand, through the surface
    const float s = max(spread, 0.01), z0 = elevation / s;
    const float3 z1 = (elevation + 2.0 * k * s * s) / s;
    const float3 logNumerator = z1 >= 0.0 ? -0.5 * z0 * z0 + log(ScaledTail(abs(z1)))
                                          : 2.0 * k * (elevation + k * s * s) + LogTail(z1);
    const float3 seen = exp(min(logNumerator - LogTail(z0).x, 0.0));
    return deep + (bottom - deep) * seen;
}

// What a water surface reflects (docs/recherche-mer.md, section 4), the sea's as a wet shore's film: the sun's glint after
// Cox and Munk, the sky after Bruneton 2010. Its facets' slopes spread normally around those of `normal`, the surface the
// pixel shows, by `lost` along and across `along`; `whole`, the whole surface's spread, masks them at grazing angles.
// view, sun: towards the eye and the sun; height: the water's altitude (km); sunLight: the sun's light there.
struct WaterReflection
{
    float3 radiance; // the glint and the sky, reflected
    float3 sunRadiance; // only the direct solar glint, for cloud shadows
    float  fresnel;  // the share of the sky's light reflected: the rest enters the water
    float  glint;    // the glint as a reflectance, pi L / (E mu_s), without the air: the diagnostic view
};

WaterReflection ReflectOnWater(float3 up, float3 normal, float3 view, float3 sun, float3 along, float2 lost, float2 whole,
                               float height, float3 sunLight)
{
    WaterReflection r;
    const float3 across = cross(up, along), slope3 = up - normal / max(dot(normal, up), 0.05); // the shown slope
    const float muS = dot(up, sun), muV = max(dot(up, view), 1e-3);

    // The sun's glint, Cox and Munk: the facets' slopes, normal around the shown slope with the lost variance, the share
    // that turns the sun towards the eye; Fresnel at the facet, Schlick's with water's 0.0204; Smith's masking of the whole
    // surface's slopes towards the sun and the eye (Beckmann, Walter 2007).
    const float3 halfway = normalize(view + sun);
    const float hUp = max(dot(halfway, up), 1e-3);
    const float2 facet = -float2(dot(halfway, along), dot(halfway, across)) / hUp - float2(dot(slope3, along), dot(slope3, across));
    const float density = exp(-0.5 * (facet.x * facet.x / lost.x + facet.y * facet.y / lost.y)) / (6.2831853 * sqrt(lost.x * lost.y));
    const float fresnel = 0.0204 + 0.9796 * pow(1.0 - saturate(dot(view, halfway)), 5.0);
    float masking = 1.0;
    {
        const float3 directions[2] = { view, sun };
        [unroll]
        for (int i = 0; i < 2; ++i)
        {
            const float mu = dot(directions[i], up);
            const float3 flat = directions[i] - mu * up;
            const float c2 = dot(flat, along) * dot(flat, along) / max(dot(flat, flat), 1e-9);
            const float sigma2 = whole.x * c2 + whole.y * (1.0 - c2);
            const float m = mu / sqrt(max(2.0 * sigma2 * (1.0 - mu * mu), 1e-9));
            masking += m < 1.6 ? (1.0 - 1.259 * m + 0.396 * m * m) / (3.535 * m + 2.181 * m * m) : 0.0;
        }
        masking = 1.0 / masking;
    }
    const float glint = fresnel * density * masking / (4.0 * muV * hUp * hUp * hUp * hUp);
    r.glint = muS > 0.0 ? PI * glint / muS : 0.0;

    // The sky's reflection, along the mirror of the view about the shown normal, kept above the horizon; Fresnel averaged
    // over the lost slopes seen along the view (Bruneton 2010). The sky is the atmosphere's, marched from the water.
    float3 reflected = reflect(-view, normal);
    reflected = normalize(reflected + max(0.02 - dot(reflected, up), 0.0) * up);
    const float3 viewFlat = view - dot(view, up) * up;
    const float alongV = dot(viewFlat, along) * dot(viewFlat, along) / max(dot(viewFlat, viewFlat), 1e-9);
    const float sigmaV = sqrt(lost.x * alongV + lost.y * (1.0 - alongV));
    const float cosV = saturate(dot(view, normal));
    r.fresnel = 0.0204 + 0.9796 * pow(1.0 - cosV, 5.0 * exp(-2.69 * sigmaV)) / (1.0 + 22.7 * pow(sigmaV, 1.5));
    ShadowRay noShadow;
    noShadow.origin = 0.0;
    noShadow.direction = 0.0;
    noShadow.on = false;
    float3 skyTransmittance;
    bool hitsGround;
    const float3 sky = IntegrateScattering(height, dot(reflected, up), muS, dot(reflected, sun), 1e9, 6, true, noShadow,
                                           skyTransmittance, hitsGround);
    r.sunRadiance = sunLight * glint;
    r.radiance = r.fresnel * sky + r.sunRadiance;
    return r;
}


struct SeaSurface {
    float3 radiance;float3 sunRadiance;float foam;float glint;float2 wind;float moving;
    float foamFresh;float foamOld;float crest;
};
// Inland water uses the drainage stage, not ocean displacement. Two advected, cross-faded phases keep the
// small ripples continuous when their local clock wraps; unresolved ripples remain reflection roughness.
SeaSurface InlandWaterAt(float3 pos, float3 q, float pixel, float3 up, float level, float depth, float3 flow, float sunShare)
{
    SeaSurface water = (SeaSurface)0;
    const float phase = frac(oceanTime.x / 64.0), other = frac(phase + 0.5);
    const float blend = 0.5 - 0.5 * cos(6.2831853 * phase);
    const float3 drift = flow + float3(0.17, 0.0, 0.11);
    const float3 ripple = lerp(Fbm3(q - drift * (other * 64.0), 2.0, 0.0, pixel, 0.5, 731u),
                               Fbm3(q - drift * (phase * 64.0), 2.0, 0.0, pixel, 0.5, 731u), blend);
    float3 slope = 0.11 * float3(dot(ripple, faceX.xyz), dot(ripple, faceY.xyz), dot(ripple, faceZ.xyz));
    slope -= dot(slope, up) * up;
    const float3 normal = normalize(up - slope), sun = lightDir.xyz;
    const float3 axis = normalize(waveAxisX.xyz - dot(waveAxisX.xyz, up) * up);
    const float height = level / 1000.0, muS = dot(up, sun);
    const float3 sunLight = SUN_ILLUMINANCE * SunTransmittance(height, muS, 0.0) * sunShare;
    const float3 direct = sunLight * max(muS, 0.0), sky = SkyIrradiance(height, muS, 0.0);
    const float2 roughness = float2(0.002, 0.003) + 0.0005 * min(length(flow), 4.0);
    const WaterReflection reflection = ReflectOnWater(up, normal, -normalize(pos), sun, axis,
                                                      roughness, roughness + 0.001, height, sunLight);
    const float3 albedo = WaterAlbedo(-max(depth, 0.0), 0.01, 0.85);
    water.radiance = reflection.radiance + (1.0 - reflection.fresnel) * albedo / PI * (direct + sky);
    water.sunRadiance = reflection.sunRadiance + (1.0 - reflection.fresnel) * albedo / PI * direct;
    water.glint = reflection.glint;
    water.moving = 1.0 - smoothstep(0.0, 2.0, pixel);
    return water;
}

SeaSurface SeaSurfaceAt(float3 pos,float3 dpdx,float3 dpdy,float3 q,float pixel,float3 up,float temperature,float height,
    float elevation,float spread,float sunShare,float2 rest,float2 dx,float2 dy,float waveHeight) {
    SeaSurface sea=(SeaSurface)0;
    float3 view=-normalize(pos),sun=lightDir.xyz;
    float3 axisX=normalize(waveAxisX.xyz-dot(waveAxisX.xyz,up)*up);
    float3 axisY=normalize(waveAxisY.xyz-dot(waveAxisY.xyz,up)*up);
    float2 wind=float2(cos(oceanWind.y),sin(oceanWind.y));
    float2 crossWind=float2(-wind.y,wind.x);
    OceanSurfaceData waterSurface=OceanRead(rest,dx,dy,elevation);
    float3 j=waterSurface.jacobian;float jxx=max(1.0+j.x,0.15),jyy=max(1.0+j.z,0.15);
    float determinant=(1.0+j.x)*(1.0+j.z)-j.y*j.y;
    float safeDet=max(jxx*jyy-j.y*j.y,0.08);
    float3 inverseJ=float3(jyy,-j.y,jxx)/safeDet;
    float2 slope=float2(dot(inverseJ.xy,waterSurface.slope),dot(inverseJ.yz,waterSurface.slope));
    float len=length(slope);slope*=min(1.0,4.0/max(len,1e-6));
    // Unrepresented capillaries retain the wind's measured roughness; the resolved spectrum keeps its own moments.
    float2 cox=CoxMunk(oceanWind.x);
    float alongVar=dot(wind*wind,waterSurface.whole.xy)+2.0*wind.x*wind.y*waterSurface.whole.z;
    float acrossVar=dot(crossWind*crossWind,waterSurface.whole.xy)+2.0*crossWind.x*crossWind.y*waterSurface.whole.z;
    float2 missing=max(cox-float2(alongVar,acrossVar),0.00015);
    float3 capillary=float3(missing.x*wind.x*wind.x+missing.y*wind.y*wind.y,
        missing.x*wind.y*wind.y+missing.y*wind.x*wind.x,(missing.x-missing.y)*wind.x*wind.y);
    float3 covariance=TransformCovariance(waterSurface.lost,inverseJ)+capillary;
    float3 whole=waterSurface.whole+capillary;
    // Diagonalize the unresolved covariance for the common anisotropic reflection function.
    float angle=0.5*atan2(2.0*covariance.z,covariance.x-covariance.y);
    float2 principal=float2(cos(angle),sin(angle));
    float delta=sqrt(0.25*(covariance.x-covariance.y)*(covariance.x-covariance.y)+covariance.z*covariance.z);
    float2 lost=max(float2(0.5*(covariance.x+covariance.y)+delta,0.5*(covariance.x+covariance.y)-delta),1e-5);
    float2 wholePrincipal=float2(dot(principal*principal,whole.xy)+2*principal.x*principal.y*whole.z,
        principal.y*principal.y*whole.x+principal.x*principal.x*whole.y-2*principal.x*principal.y*whole.z);
    wholePrincipal=max(wholePrincipal,lost);
    float3 normal=normalize(up-slope.x*axisX-slope.y*axisY);
    float3 principalAxis=normalize(principal.x*axisX+principal.y*axisY);
    float muS=dot(up,sun);
    float3 sunLight=SUN_ILLUMINANCE*SunTransmittance(height,muS,0.0)*sunShare;
    float3 skyIrradiance=SkyIrradiance(height,muS,0.0);
    float3 irradiance=sunLight*max(muS,0.0)+skyIrradiance;
    WaterReflection reflection=ReflectOnWater(up,normal,view,sun,principalAxis,lost,wholePrincipal,height,sunLight);
    sea.glint=reflection.glint;
    float type=smoothstep(20.0,6.0,temperature)*(0.6+0.4*SpreadStep(-200.0,-50.0,elevation,spread));
    float3 waterAlbedo=WaterAlbedo(elevation,spread,type);
    float3 body=waterAlbedo/PI*irradiance;
    float3 bodySun=waterAlbedo/PI*(sunLight*max(muS,0.0));
    float crest=saturate((waveHeight-0.05)/0.9),toSun=max(dot(sun,-view),0.0);
    float thin=pow(saturate(0.5-0.5*dot(sun,normal)),3.0);
    float transmission=2.0*crest*crest*pow(toSun,4.0)*thin*exp(-length(pos)/600.0);
    body+=float3(0.035,0.12,0.085)/PI*sunLight*transmission;
    bodySun+=float3(0.035,0.12,0.085)/PI*sunLight*transmission;
    float cheb=max(abs(rest.x),abs(rest.y));
    float w0=1.0-smoothstep(0.3*oceanFoamOrigin[0].w,0.45*oceanFoamOrigin[0].w,cheb);
    float w1=1.0-smoothstep(0.3*oceanFoamOrigin[1].w,0.45*oceanFoamOrigin[1].w,cheb);
    float4 stored=lerp(OceanStoredFoam(rest,dx,dy,1),OceanStoredFoam(rest,dx,dy,0),w0)*w1;
    float fresh=saturate((oceanFoamParams.x-determinant)*oceanFoamParams.y);
    float cover=clamp((max(stored.x,fresh*(1.0-w1*0.7))+0.6*stored.y)*oceanRender.y,0.0,1.5);
    float2 wd=float2(dot(rest,wind),dot(rest,crossWind));
    float2 sdx=float2(dot(dx,wind),dot(dx,crossWind))*float2(0.035,0.11);
    float2 sdy=float2(dot(dy,wind),dot(dy,crossWind))*float2(0.035,0.11);
    float streak=oceanPores.SampleGrad(oceanSampler,float3(wd*float2(0.035,0.11)+oceanStreakOrigin.xy,0),sdx,sdy).w;
    float freshK=saturate(stored.y*2.0+fresh);
    cover*=lerp(smoothstep(0.25,0.75,streak)*1.5,1.0,freshK);
    float a=oceanPores.SampleGrad(oceanSampler,float3(rest*0.23+oceanPoreOrigin.xy,0),dx*0.23,dy*0.23).x;
    float b=oceanPores.SampleGrad(oceanSampler,float3(rest*0.71+oceanPoreOrigin.zw,0),dx*0.71,dy*0.71).y;
    float pat=0.78*a+0.22*b;
    float footprint=exp2(pixel),aa=0.03+0.12*saturate(footprint/0.5);
    float soft=0.04+0.14*(1.0-saturate(cover));
    float fm=smoothstep(1.0-cover-aa-soft,1.0-cover+aa+soft,pat);
    float foam=saturate(fm*smoothstep(0.0,0.5,cover))*(0.68+0.32*smoothstep(0.3,0.9,cover));
    foam=max(foam,smoothstep(0.35,0.9,stored.y)*smoothstep(0.25,0.6,pat+0.25)*0.95);
    foam*=smoothstep(0.0,3.0,max(-elevation,0.0));
    float3 foamAlbedo=float3(0.82,0.87,0.92)*(0.78+0.3*b);
    float3 foamLight=foamAlbedo/PI*(sunLight*max(dot(normal,sun),0.0)*0.5
        +skyIrradiance*(0.75+0.25*saturate(dot(normal,up))));
    body+=float3(0.035,0.12,0.085)/PI*(sunLight*0.05+skyIrradiance*0.35)*saturate(cover);
    bodySun+=float3(0.035,0.12,0.085)/PI*(sunLight*0.05)*saturate(cover);
    float3 clear=(reflection.radiance+(1.0-reflection.fresnel)*body);
    float3 nearby=lerp(clear,foamLight,foam*0.95);
    float3 clearSun=reflection.sunRadiance+(1.0-reflection.fresnel)*bodySun;
    float3 foamSun=foamAlbedo/PI*(sunLight*max(dot(normal,sun),0.0)*0.5);
    float3 nearbySun=lerp(clearSun,foamSun,foam*0.95);
    // The spike's far field uses the same wind and the unresolved whitecap coverage.
    float farShare=smoothstep(0.5,2.0,footprint);
    float mean=Whitecaps(oceanWind.x);
    float3 statistical=(1.0-mean)*clear+mean*FOAM_ALBEDO/PI*irradiance;
    float3 statisticalSun=(1.0-mean)*clearSun+mean*FOAM_ALBEDO/PI*(sunLight*max(muS,0.0));
    sea.radiance=lerp(nearby,statistical,farShare);
    sea.sunRadiance=lerp(nearbySun,statisticalSun,farShare);
    sea.foam=lerp(foam,mean,farShare);
    sea.foamFresh=lerp(foam*freshK,0.0,farShare);sea.foamOld=sea.foam-sea.foamFresh;
    sea.crest=saturate(1.0-determinant);
    float3 pole=float3(faceX.y,faceY.y,faceZ.y),east=cross(up,pole);
    east=dot(east,east)>1e-12?normalize(east):axisX;
    float3 north=normalize(cross(east,up));
    float3 windWorld=normalize(wind.x*axisX+wind.y*axisY);
    sea.wind=float2(oceanWind.x,atan2(dot(windWorld,north),dot(windWorld,east)));
    sea.moving=saturate(1.0-(waterSurface.lost.x+waterSurface.lost.y)/max(waterSurface.whole.x+waterSurface.whole.y,1e-6));
    return sea;
}
#endif
