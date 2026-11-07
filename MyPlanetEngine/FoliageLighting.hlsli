#ifndef FOLIAGE_LIGHTING_HLSLI
#define FOLIAGE_LIGHTING_HLSLI
// Unit-integral wrapped diffuse; a random leaf orientation retains the same
// mean (1/4) as Lambert. Both faces share this contract with the impostor.
float FoliageWrappedDiffuse(float cosine) {
    const float wrap=0.25;
    return max(cosine+wrap,0.0)/((1.0+wrap)*(1.0+wrap));
}
float FoliageSpecular(float3 normal,float3 view,float3 sun,float roughness) {
    const float nl=saturate(dot(normal,sun)),nv=max(saturate(dot(normal,view)),1e-4);
    float3 halfVector=view+sun;float length2=dot(halfVector,halfVector);
    if (nl<=0.0 || length2<1e-8) return 0.0;
    halfVector*=rsqrt(length2);
    const float nh=saturate(dot(normal,halfVector)),vh=saturate(dot(view,halfVector));
    const float alpha=max(roughness*roughness,0.16),a2=alpha*alpha;
    const float d=nh*nh*(a2-1.0)+1.0;
    const float distribution=a2/(PI*d*d);
    const float visibility=0.5/max(nl*sqrt(nv*nv*(1.0-a2)+a2)+nv*sqrt(nl*nl*(1.0-a2)+a2),1e-5);
    const float fresnel=0.035+0.965*pow(1.0-vh,5.0);
    return distribution*visibility*fresnel*nl;
}
#endif
