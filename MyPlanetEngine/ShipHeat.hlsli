// A heated refractory grille starts red, with a golden inner core as the afterburner opens.
#ifndef SHIP_HEAT_HLSLI
#define SHIP_HEAT_HLSLI
float3 ExhaustRadiance(float power,float peak)
{
    const float incandescence=smoothstep(0.02,0.69,power), afterburner=smoothstep(0.52,1.0,power);
    const float3 ember=float3(1.0,0.012,0.0015);
    const float3 flame=lerp(float3(1.0,0.16,0.008),float3(1.0,0.51,0.08),afterburner);
    // The colder refractory preserves the deep orange around the hotter core.
    return peak*power*(0.58+2.30*power*power)*lerp(ember,flame,incandescence);
}
float3 ExhaustScatter(float power)
{
    return lerp(float3(1.0,0.012,0.001),float3(1.0,0.19,0.012),smoothstep(.16,.90,power))
         * power * (0.46 + 4.8 * power);
}
#endif
