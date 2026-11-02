// CPU behavioural fixtures for the exact contact algebra compiled by FlightGround.hlsl. No renderer or benchmark.
#include "../../MyPlanetEngine/FlightContact.h"
#include <cstdio>
#include <cstdlib>
#include <limits>

namespace Sweep {
struct float3 {
    float x,y,z;
    float3(float a,float b,float c):x(a),y(b),z(c) {}
    float3():x(0),y(0),z(0) {}
    float3 operator+(float3 v) const { return {x+v.x,y+v.y,z+v.z}; }
    float3 operator-(float3 v) const { return {x-v.x,y-v.y,z-v.z}; }
    float3 operator-() const { return {-x,-y,-z}; }
    float3 operator+(float s) const { return {x+s,y+s,z+s}; }
    float3 operator-(float s) const { return {x-s,y-s,z-s}; }
    float3 operator*(float s) const { return {x*s,y*s,z*s}; }
    float3 operator/(float s) const { return {x/s,y/s,z/s}; }
    float3& operator*=(float s) { x*=s;y*=s;z*=s;return *this; }
};
inline float dot(float3 a,float3 b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
inline float3 cross(float3 a,float3 b) { return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
using std::min; using std::max; using std::sqrt; using std::abs;
inline float3 min(float3 a,float3 b) { return {min(a.x,b.x),min(a.y,b.y),min(a.z,b.z)}; }
inline float3 max(float3 a,float3 b) { return {max(a.x,b.x),max(a.y,b.y),max(a.z,b.z)}; }
#include "../../MyPlanetEngine/FlightSweep.hlsli"
}

static void Require(bool condition,const char* description) {
    if (!condition) { std::fprintf(stderr,"FAIL: %s\n",description);std::exit(1); }
}
static void Near(double actual,double expected,double tolerance,const char* description) {
    if (std::abs(actual-expected)>tolerance) {
        std::fprintf(stderr,"FAIL: %s: %.12g vs %.12g\n",description,actual,expected);std::exit(1);
    }
}

int main() {
    using namespace Sweep;
    const float3 a(5,-10,-10),b(5,10,-10),c(5,0,10);
    for (float radius:{.25f,2.5f,6.7f}) {
        const float distance=radius+3;
        auto h=FlightTriangle(a+float3(distance-5,0,0),b+float3(distance-5,0,0),c+float3(distance-5,0,0),{12,0,0},radius);
        Near(h.fraction,.25,1e-6,"face contact stops at the body's surface");
        Near(h.normal.x,-1,1e-6,"wall normal opposes travel");
    }
    auto wall=FlightTriangle(a,b,c,{10,0,0},.25);
    Near(wall.fraction,.475,1e-6,"a sweep catches a wall with both endpoints outside its contact band");
    auto back=FlightTriangle(a,b,c,{-10,0,0},.25);
    Require(back.fraction>1,"moving away does not collide");
    auto graze=FlightTriangle({.25f,-10,-10},{.25f,10,-10},{.25f,0,10},{0,5,0},.25);
    Require(graze.fraction>1,"tangent motion on a plane remains free");
    auto retreat=FlightTriangle({.24f,-10,-10},{.24f,10,-10},{.24f,0,10},{-1,0,0},.25);
    Require(retreat.fraction>1,"a shallow initial overlap can retreat");
    auto edge=FlightTriangle({5,.5f,-5},{5,.5f,5},{10,.5f,0},{10,0,0},1);
    Near(edge.fraction,(5-std::sqrt(.75))/10,2e-6,"edge capsule contact");
    auto vertex=FlightTriangle({5,.6f,.8f},{7,2,3},{7,3,2},{10,0,0},1.25);
    Near(vertex.fraction,(5-.75)/10,2e-6,"vertex sphere contact");
    auto narrow=FlightTriangle({5000,-.1f,-50},{5000,.1f,-50},{5000,0,50},{10000,0,0},.25);
    Near(narrow.fraction,(5000-.25)/10000,1e-6,"long sweep retains a narrow encountered triangle");
    auto degenerate=FlightTriangle({5,0,0},{5,0,0},{5,0,0},{10,0,0},.25);
    Near(degenerate.fraction,.475,1e-6,"a collapsed triangle still has vertex contact");

    using FlightContact::Vec;
    const double outer=FlightContact::PlanetRadius+FlightContact::MaximumHeight;
    Require(FlightContact::Clip({outer+100,0,0},{-outer-100,0,0},.25).active,"clear endpoints do not prove the chord clear");
    Require(!FlightContact::Clip({outer+100,0,0},{outer+100,1000,0},6.7).active,"a high tangent segment misses the whole terrain envelope");
    Require(FlightContact::Clip({outer+1,0,0},{outer+1,1000,0},2.5).active,"the envelope includes body radius");
    const auto through=FlightContact::Clip({outer+100,0,0},{-outer-100,0,0},.25);
    Require(through.active && through.first>0 && through.last<.5,"a planet-spanning chord is probed only on its near side");
    Near(FlightContact::Length(through.begin),outer+.25,1e-8,"clipped chord enters the terrain envelope");
    Near(FlightContact::Length(through.end),FlightContact::PlanetRadius+.25,1e-8,"sea contact terminates a planet-spanning chord");
    Near(through.sea,through.last,1e-15,"analytic sea contact retains the full movement fraction");
    Near(through.Fraction(.5),.5*(through.first+through.last),1e-15,"local terrain contact maps back to the original chord");
    const auto voidPath=FlightContact::Clip({outer+100,0,0},{outer+100,1000,0},8.9);
    Require(!voidPath.active,"a wholly exterior path needs no terrain probe");
    const auto grazeSea=FlightContact::Clip({FlightContact::PlanetRadius+.25,-10000,0},
        {FlightContact::PlanetRadius+.25,10000,0},.25);
    Require(grazeSea.active && grazeSea.sea>1,"analytic sea tangency does not create an obstacle");
    const auto beneath=FlightContact::Clip({FlightContact::PlanetRadius-1,0,0},
        {FlightContact::PlanetRadius+5,0,0},.25);
    Require(beneath.active && beneath.last==1 && beneath.sea>1,"an initial sea overlap can retreat outward");
    const auto deeper=FlightContact::Clip({FlightContact::PlanetRadius-1,0,0},
        {FlightContact::PlanetRadius-5,0,0},.25);
    Require(deeper.active && deeper.last==0 && deeper.sea==0,"an initial sea overlap blocks inward movement");
    const auto underTangent=FlightContact::Clip({FlightContact::PlanetRadius-1,0,0},
        {FlightContact::PlanetRadius-1,100,0},.25);
    Require(underTangent.active && underTangent.sea>1,"an initial sea overlap permits tangential escape");
    unsigned maxVertices=0;
    for (double radius:{.25,2.5,6.7,7.3,12.}) for (double distance:{0.,.01,1.,100.,4096.,10000.,1000000.}) {
        const Vec begin={FlightContact::PlanetRadius+100,0,0},end=begin+Vec{0,distance,-10};
        const auto span=FlightContact::Clip(begin,end,radius);
        const auto p=FlightContact::Corridor(span,radius);
        Require(p.count[0]<=FlightContact::MaxColumns && p.count[1]<=FlightContact::MaxRows,"probe dimensions stay bounded");
        Require(p.Groups()<=FlightContact::MaxGroups,"contact reduction stays bounded");
        Require(-p.grid[0]>radius && -p.grid[1]>radius,"corridor covers the starting sphere");
        const Vec up=FlightContact::Unit(span.begin),along={p.along[0],p.along[1],p.along[2]};
        const double projected=FlightContact::PlanetRadius*FlightContact::Dot(span.end,along)/FlightContact::Dot(span.end,up);
        Require(p.grid[1]+p.count[1]*p.grid[3]>=projected+radius,"the full clipped corridor remains covered at long range");
        Require(p.shape[3]<=FlightContact::RowsPerGroup/2,"the first group contains the initial recovery footprint");
        maxVertices=std::max(maxVertices,p.count[0]*(p.count[1]+1));
    }
    // Oblique chords, including both clear endpoints and a grazing shell. No point before a possible first contact
    // may escape the tangent chart or its projected transverse/longitudinal bounds.
    unsigned shellCases=0;
    for (double radius:{.25,8.850581}) for (double altitude:{-100.,0.,1.,100.,5000.,9999.,10001.,10000000.})
        for (double spanLength:{100.,10000.,1000000.,40000000.}) {
        const Vec begin={FlightContact::PlanetRadius+altitude,-spanLength*.5,0};
        const Vec end={FlightContact::PlanetRadius+altitude,spanLength*.5,0};
        const auto span=FlightContact::Clip(begin,end,radius);
        if (!span.active) continue;
        const auto p=FlightContact::Corridor(span,radius);
        const Vec up={p.up[0],p.up[1],p.up[2]},along={p.along[0],p.along[1],p.along[2]},across={p.across[0],p.across[1],p.across[2]};
        Require(FlightContact::Dot(span.end,up)>FlightContact::PlanetRadius*.99,"clipped trajectory stays in its tangent hemisphere");
        Require(p.count[0]<=FlightContact::MaxColumns && p.count[1]<=FlightContact::MaxRows,"oblique corridor dimensions stay bounded");
        for (unsigned i=0;i<=16;++i) {
            const Vec centre=span.begin+(span.end-span.begin)*(i/16.);
            for (double x:{-radius,radius}) for (double y:{-radius,radius}) for (double z:{-radius,radius}) {
                const Vec corner=centre+across*x+along*y+up*z;
                const double factor=FlightContact::PlanetRadius/FlightContact::Dot(corner,up);
                const double px=FlightContact::Dot(corner,across)*factor,py=FlightContact::Dot(corner,along)*factor;
                Require(px>=p.grid[0] && px<=p.grid[0]+(p.count[0]-1)*p.grid[2],"projected capsule width is covered");
                Require(py>=p.grid[1] && py<=p.grid[1]+p.count[1]*p.grid[3],"projected capsule length is covered");
            }
        }
        ++shellCases;
    }
    std::printf("Flight contact: faces, edges, vertices, tangency, retreat, narrow crossing and global chord clipping pass (%u shell cases). Max vertices: %u.\n",shellCases,maxVertices);
}
