// HLSL has no double dot or sqrt intrinsic. Refine the float inverse length once in double precision.
double3 SurfaceProbeDirection(double3 p) {
    const double squared=p.x*p.x+p.y*p.y+p.z*p.z;
    double inverse=(double)rsqrt((float)squared);
    inverse*=1.5l-0.5l*squared*inverse*inverse;
    return p*inverse;
}
