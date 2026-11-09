// One physical impact field, compiled by both C++ contact/cooking and HLSL surface sampling.
#ifndef AIRLESS_FIELD_HLSLI
#define AIRLESS_FIELD_HLSLI
#ifdef __cplusplus
namespace AirlessField {
using double3=Airless::Vec;
using uint=uint32_t;
using std::sqrt; using std::exp; using std::abs;
inline float min(float a,float b){return std::min(a,b);}
inline float max(float a,float b){return std::max(a,b);}
#endif
double AirlessDot(double3 a,double3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
float AirlessSmooth(float t) {t=min(max(t,0.0f),1.0f);return t*t*(3.0f-2.0f*t);}
uint AirlessHash(uint h){h^=h>>16;h*=0x7feb352du;h^=h>>15;h*=0x846ca68bu;return h^(h>>16);}
uint AirlessCellHash(int x,int y,int z,uint seed){return AirlessHash(uint(x)*0x8da6b343u^uint(y)*0xd8163841u^uint(z)*0xcb1ab31fu^seed);}
float AirlessRandom(uint h){return float(h&0xffffffu)/16777216.0f;}
int AirlessFloor(double x){const int i=int(x);return i-(x<double(i)?1:0);}
double AirlessInverseLength(double3 p) {
    const double q=AirlessDot(p,p);
    double r=double(1.0f/sqrt(float(q)));
    r=r*(1.5-0.5*q*r*r);return r*(1.5-0.5*q*r*r);
}
float AirlessNoise(double3 p,uint seed) {
    const int ix=AirlessFloor(p.x),iy=AirlessFloor(p.y),iz=AirlessFloor(p.z);
    const float u=AirlessSmooth(float(p.x-ix)),v=AirlessSmooth(float(p.y-iy)),w=AirlessSmooth(float(p.z-iz));
    float n=0;
    for(int z=0;z<2;++z)for(int y=0;y<2;++y)for(int x=0;x<2;++x)
        n+=AirlessRandom(AirlessCellHash(ix+x,iy+y,iz+z,seed))*(x?u:1-u)*(y?v:1-v)*(z?w:1-w);
    return n;
}
float AirlessImpact(float u,float r,float age,float fracture) {
    if(u>=1.65f)return 0;
    const float complex=AirlessSmooth((r-2000.0f)/16000.0f);
    const float depth=.25f*r/(1+sqrt(r/2500.0f))*(2-complex)*(1-.65f*age);
    // Large impacts have broad floors and steep walls; old impacts have filled floors and worn rims.
    const float shaped=u*(1+(.06f+.16f*complex)*fracture),floorRadius=.05f+.54f*complex;
    const float wall=AirlessSmooth((shaped-floorRadius)/(1-floorRadius));
    const float rim=(shaped-1)/(.045f+.16f*age),apron=(shaped-1.12f)/.33f;
    const float rimHeight=.035f*r/(1+sqrt(r/80000.0f));
    const float rugged=.20f*depth*fracture*wall*(1-wall)*4;
    const float peak=.65f*depth*complex*(1-.7f*age);
    const float summit=max(0.0f,1-shaped/(.26f+.10f*fracture));
    return (-depth*(1-wall)+rimHeight*(1-.75f*age)*exp(-rim*rim)
        +.18f*rimHeight*exp(-apron*apron)+rugged
        +peak*summit*summit)*(1-AirlessSmooth((u-1.4f)/.25f));
}
struct AirlessGround {float height,albedo;};
AirlessGround AirlessCraters(double3 p,float bodyRadius,float scale,float footprint,uint seed) {
    const double3 q=p*double(1.0f/scale);
    const int ix=AirlessFloor(q.x),iy=AirlessFloor(q.y),iz=AirlessFloor(q.z);
    float excavation=0,deposit=0,bright=0,dark=0;
    for(int z=iz-1;z<=iz+1;++z)for(int y=iy-1;y<=iy+1;++y)for(int x=ix-1;x<=ix+1;++x) {
        const uint a=AirlessCellHash(x,y,z,seed),b=AirlessHash(a),c=AirlessHash(b),d=AirlessHash(c);
        if((a&7u)==0)continue;
        double3 centre=double3(double(x)+double(.15f+.7f*AirlessRandom(a)),double(y)+double(.15f+.7f*AirlessRandom(b)),
                              double(z)+double(.15f+.7f*AirlessRandom(c)))*double(scale);
        const double inverse=AirlessInverseLength(centre);
        if(abs(float(AirlessDot(centre,centre)*inverse-double(bodyRadius)))>.3f*scale)continue;
        // Overlapping size ranges: no empty decade between large basins and small impacts.
        const float draw=AirlessRandom(d);
        const float radius=scale*(.07f+.38f*draw*draw);
        const float filter=AirlessSmooth((radius/max(footprint,.01f)-.5f)/1.5f);
        if(filter==0)continue;
        centre=centre*(double(bodyRadius)*inverse);
        const double3 delta=p-centre;
        const float distance2=float(AirlessDot(delta,delta));
        if(distance2>=radius*radius*1.65f*1.65f)continue;
        const float fracture=2*AirlessNoise(delta*double(3.0f/radius),seed+a)-1;
        const float age=AirlessRandom(AirlessHash(d)),u=sqrt(distance2)/radius;
        const float impact=filter*AirlessImpact(u,radius,age,fracture);
        // Overlapping impacts cut a common floor instead of adding an unbounded number of deep bowls.
        excavation=min(excavation,impact);deposit=max(deposit,impact);
        // Excavated bright material and old, flooded impact floors belong to the same impact as its relief.
        const float fresh=(1-age)*(1-age)*(1-age);
        const float ejecta=exp(-((u-1.02f)/.38f)*((u-1.02f)/.38f));
        bright=max(bright,filter*.075f*fresh*ejecta*(.65f+.7f*fracture));
        const float basinDistance=u*(1+.35f*fracture);
        dark=max(dark,filter*.042f*AirlessSmooth((radius-60000)/140000)*AirlessSmooth((age-.35f)/.35f)
            *(1-AirlessSmooth((basinDistance-.45f)/.45f))*(.75f+.4f*fracture));
    }
    AirlessGround result;result.height=excavation+deposit;result.albedo=bright-dark;return result;
}
AirlessGround AirlessSample(double3 direction,float radius,uint seed,float footprint) {
    const double3 p=direction*(AirlessInverseLength(direction)*double(radius));
    float h=1300*(AirlessNoise(p*double(1.0f/320000.0f),seed)-.5f)
        +550*(AirlessNoise(p*double(1.0f/73000.0f),seed+1)-.5f);
    float albedo=.145f+.014f*(AirlessNoise(p*double(1.0f/32000.0f),seed+91)-.5f);
    // Keep the largest possible impact smaller than its body; metre-scale detail keeps the same filtering.
    float scale=min(1000000.0f,.6f*radius);
    for(uint i=0;i<9;++i,scale/=5) {
        if(scale<footprint)break;
        const AirlessGround impact=AirlessCraters(p,radius,scale,footprint,seed+53*i);
        h+=impact.height;albedo+=impact.albedo;
        const float rubble=AirlessNoise(p*double(3.0f/scale),seed+101+i)-.5f;
        const float fade=AirlessSmooth(scale/(4*max(footprint,.01f))-1);
        h+=min(1000.0f,.018f*scale)*rubble*fade;
    }
    AirlessGround result;result.height=h;result.albedo=min(max(albedo,.055f),.24f);return result;
}
float AirlessHeight(double3 direction,float radius,uint seed,float footprint) {
    return AirlessSample(direction,radius,seed,footprint).height;
}
float AirlessAlbedo(double3 direction,float radius,uint seed) {
    return AirlessSample(direction,radius,seed,.25f).albedo;
}
#ifdef __cplusplus
}
#endif
#endif
