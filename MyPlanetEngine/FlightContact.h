// Bounded flight-contact probes. The CPU plans a swept corridor; the GPU returns only its first contacts.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace FlightContact {
struct Vec {
    double x=0,y=0,z=0;
    Vec operator+(Vec v) const { return {x+v.x,y+v.y,z+v.z}; }
    Vec operator-(Vec v) const { return {x-v.x,y-v.y,z-v.z}; }
    Vec operator*(double a) const { return {x*a,y*a,z*a}; }
};
inline double Dot(Vec a,Vec b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
inline Vec Cross(Vec a,Vec b) { return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
inline double Length(Vec p) { return std::sqrt(Dot(p,p)); }
inline Vec Unit(Vec p) { return p*(1.0/Length(p)); }

constexpr unsigned RowsPerGroup=32, MaxColumns=33, MaxRows=8192, MaxGroups=MaxRows/RowsPerGroup;
constexpr double Cell=0.5, CameraRadius=0.25, PlanetRadius=6378000.0, MaximumHeight=10000.0;

struct Span {
    Vec begin,end,seaNormal;
    double first=0,last=1,sea=2;
    bool active=false;
    double Fraction(double local) const { return first+(last-first)*local; }
};

// The line interval inside a sphere. The stable quadratic root preserves a nearby entry on long chords.
inline bool SphereInterval(Vec begin,Vec delta,double radius,double& first,double& last) {
    const double a=Dot(delta,delta), b=Dot(begin,delta);
    const double length=Length(begin), c=(length-radius)*(length+radius);
    if (a<1e-20) { first=0; last=1; return c<=0; }
    const Vec nearest=begin+delta*(-b/a);
    const double inside=radius*radius-Dot(nearest,nearest);
    if (inside<0) return false;
    if (inside==0) { first=last=-b/a; return true; }
    const double root=std::sqrt(a*inside),q=-b-std::copysign(root,b);
    if (q==0) { first=last=-b/a; return true; }
    first=q/a; last=c/q;
    if (first>last) std::swap(first,last);
    return true;
}

inline Span Clip(Vec begin,Vec end,double bodyRadius) {
    Span s; s.begin=begin; s.end=end;
    const Vec delta=end-begin;
    double first,last;
    // Test the whole chord and its radius; clear endpoints alone never certify the intervening space.
    if (!SphereInterval(begin,delta,PlanetRadius+MaximumHeight+bodyRadius,first,last)
        || last<0 || first>1) return s;
    s.active=true; s.first=std::max(0.0,first); s.last=std::min(1.0,last);
    // Terrain contact includes sea level. A chord crossing the planet must stop on its near side;
    // a grazing chord stays in the thin terrain shell. Both leave a positive tangent projection.
    const double seaRadius=PlanetRadius+bodyRadius;
    if (Length(begin)<seaRadius && Dot(begin,delta)<0) {
        s.sea=0; s.seaNormal=Unit(begin); s.last=0;
    } else if (SphereInterval(begin,delta,seaRadius,first,last) && first>=0 && first<=1
        && first<last) {
        s.sea=first; s.seaNormal=Unit(begin+delta*first); s.last=std::min(s.last,first);
    }
    s.begin=begin+delta*s.first; s.end=begin+delta*s.last;
    return s;
}

struct Probe {
    // The layout is exactly the FlightGround constant buffer: five double4s, then two float4s.
    double up[4]={},across[4]={},along[4]={},grid[4]={},shape[4]={};
    float movement[4]={};
    uint32_t count[4]={};

    Vec WorldNormal(float x,float y,float z) const {
        return Vec{across[0],across[1],across[2]}*x+Vec{along[0],along[1],along[2]}*y+Vec{up[0],up[1],up[2]}*z;
    }
    unsigned Groups() const { return (count[1]+RowsPerGroup-1)/RowsPerGroup; }
};
static_assert(sizeof(Probe)==192,"FlightGround constants must match the HLSL layout.");

// Only the portion returned by Clip belongs in this tangent chart; an arbitrary planet-spanning chord does not.
inline Probe Corridor(const Span& span,double bodyRadius) {
    Probe p;
    const Vec begin=span.begin,end=span.end;
    const Vec up=Unit(begin), offset=end-begin;
    Vec along=offset-up*Dot(offset,up);
    if (Length(along)<1e-8) {
        along=Cross(up,{1,0,0});
        if (Length(along)<1e-6) along=Cross(up,{0,1,0});
    }
    along=Unit(along);
    const Vec across=Unit(Cross(along,up));
    const double z0=Length(begin),z1=Dot(end,up),y1=std::max(Dot(end,along),0.0);
    const double length=PlanetRadius*y1/z1;
    // Project the swept sphere's bounding boxes, not just their centre line. This includes the perspective
    // expansion at the far end of a long, grazing chord without relying on an arbitrary projection clamp.
    const double width=std::max(bodyRadius,PlanetRadius*bodyRadius/(std::min(z0,z1)-bodyRadius));
    const double beyond=PlanetRadius*(y1+bodyRadius)/(z1-bodyRadius)-length;
    const double padding=std::max(width,beyond);
    // Physical resolution in ordinary flight; bounded storage by a larger cell on exceptional long requests.
    // The first group also covers the complete starting footprint used only for teleport recovery.
    const double cellX=std::max(Cell,width/(MaxColumns/2-1));
    double cellY=std::max(std::max(Cell,padding/(RowsPerGroup/2-1)),(length+2*padding)/(MaxRows-4));
    unsigned behind=std::min(unsigned(std::ceil(padding/cellY)),RowsPerGroup/2-1)+1;
    unsigned rows=unsigned(std::ceil(length/cellY))+2*behind;
    if (rows>MaxRows) { cellY*=double(rows)/(MaxRows-2); behind=std::min(unsigned(std::ceil(padding/cellY)),RowsPerGroup/2-1)+1;
        rows=unsigned(std::ceil(length/cellY))+2*behind; }
    const unsigned half=std::min(unsigned(std::ceil(width/cellX)),MaxColumns/2-1)+1;
    const Vec axes[]={up,across,along}; double* arrays[]={p.up,p.across,p.along};
    for (unsigned i=0;i<3;++i) { arrays[i][0]=axes[i].x; arrays[i][1]=axes[i].y; arrays[i][2]=axes[i].z; }
    p.up[3]=Length(begin)-PlanetRadius;
    p.grid[0]=-double(half)*cellX; p.grid[1]=-double(behind)*cellY; p.grid[2]=cellX; p.grid[3]=cellY;
    p.shape[0]=PlanetRadius; p.shape[1]=bodyRadius; p.shape[2]=half; p.shape[3]=behind;
    p.movement[0]=float(Dot(offset,across)); p.movement[1]=float(Dot(offset,along)); p.movement[2]=float(Dot(offset,up));
    p.movement[3]=float(bodyRadius); p.count[0]=2*half+1; p.count[1]=rows;
    return p;
}
}
