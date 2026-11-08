// Production attitude algebra, without a renderer, GPU or synthetic input events.
#include "../../MyPlanetEngine/FlightFrame.h"
#include <cstdio>
#include <cstdlib>
#include <initializer_list>

namespace {
constexpr double Pi=3.14159265358979323846;
void require(bool valid,const char* message) {if(!valid){std::fprintf(stderr,"FAIL: %s\n",message);std::exit(1);}}
bool close(Vec3d a,Vec3d b,double tolerance=1e-10) {return Length(a-b)<tolerance;}
void validFrame(Vec3d f,Vec3d u) {
    require(std::isfinite(Length(f)) && std::isfinite(Length(u)),"finite attitude");
    require(std::abs(Length(f)-1)<1e-12 && std::abs(Length(u)-1)<1e-12,"unit axes");
    require(std::abs(Dot(f,u))<1e-12,"orthogonal attitude");
    require(close(Cross(f,Cross(u,f)),u),"consistent handedness");
}
}
int main() {
    Vec3d f={0,0,1},u={0,1,0};
    FlightFrame::Turn(f,u,0,Pi/2,0);
    require(close(f,{0,-1,0}) && close(u,{0,0,1}),"cross the former downward pitch limit");
    FlightFrame::Turn(f,u,Pi/2,0,0);
    require(close(f,{1,0,0}),"yaw still works after exact nadir");
    f={0,0,1};u={0,1,0};
    FlightFrame::Turn(f,u,0,-Pi/2,0);
    require(close(f,{0,1,0}) && close(u,{0,0,-1}),"exact zenith");
    FlightFrame::Turn(f,u,0,-Pi/2,0);
    require(close(f,{0,0,-1}) && close(u,{0,-1,0}),"continue past zenith without leveling");
    FlightFrame::Turn(f,u,0,-Pi,0);
    require(close(f,{0,0,1}) && close(u,{0,1,0}),"complete a full pitch loop");
    FlightFrame::Turn(f,u,0,0,Pi/2);
    require(close(f,{0,0,1}) && close(u,{1,0,0}),"roll does not steer the nose");
    const Vec3d rolledForward=f,rolledUp=u;
    for(int i=0;i<10000;++i)FlightFrame::Turn(f,u,0,0,0);
    require(close(f,rolledForward) && close(u,rolledUp),"idle frames preserve arbitrary roll");
    for(int i=0;i<20000;++i) {
        FlightFrame::Turn(f,u,.009*std::sin(i*.17),.013*std::cos(i*.11),.008*std::sin(i*.07));
        validFrame(f,u);
    }
    // Explicit placements must remain well defined at both geographic poles and all look pitches.
    for(double latitude:{-Pi/2,-1.1,0.0,.6,Pi/2})for(double longitude:{-.8,0.0,1.2})
        for(double heading:{0.0,.7,Pi})for(double pitch:{-Pi/2,0.0,Pi/2,3*Pi/4,Pi}) {
            const Vec3d vertical={std::cos(latitude)*std::cos(longitude),std::sin(latitude),std::cos(latitude)*std::sin(longitude)};
            const Vec3d north={-std::sin(latitude)*std::cos(longitude),std::cos(latitude),-std::sin(latitude)*std::sin(longitude)};
            const Vec3d east={-std::sin(longitude),0,std::cos(longitude)};
            FlightFrame::FromHeading(vertical,north*std::cos(heading)+east*std::sin(heading),pitch,f,u);
            validFrame(f,u);
            const Vec3d savedForward=f,savedUp=u;
            FlightFrame::Turn(f,u,0,0,0);
            require(close(f,savedForward) && close(u,savedUp),"placement survives first idle frame");
        }
    f={0,1,0};u=f;FlightFrame::Orthonormalize(f,u);validFrame(f,u);
    std::puts("PASS: nadir/zenith, full loops, roll, idle attitude, 20000 mixed turns and 225 geographic/look placements.");
}
