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

void checkOrbit() {
    const Vec3d vertical = {1,0,0}, north = {0,1,0};
    FlightFrame::Orbit orbit;
    Vec3d f, u;
    for (double pitch : {-Pi/2, -.65, 0.0, .7, Pi/2, 2.2}) {
        FlightFrame::FromHeading(vertical, north, pitch, f, u);
        FlightFrame::Turn(f, u, 0, 0, 2.1);
        const Vec3d aim = f;
        orbit.Align(vertical, f, u);
        orbit.View(f, u);
        validFrame(f, u);
        require(close(f, aim), "entering orbit preserves aim from a banked or inverted view");
        require(std::abs(Dot(Cross(u,f), vertical)) < 1e-12 && Dot(u, vertical) > -1e-12, "level horizon");
        const Vec3d right = Cross(orbit.vertical, orbit.heading);
        require(close(FlightFrame::ViewTravel(f, u, orbit.vertical, 100, 0, 0), aim*100), "advance along the full sightline");
        require(close(FlightFrame::ViewTravel(f, u, orbit.vertical, -100, 3, 5), aim*(-100) + right*3 + vertical*5),
                "retreat, horizontal strafe and radial lift combine independently");
        FlightFrame::Turn(f, u, 0, 0, 0);
        require(close(f, aim), "releasing orbit preserves aim");
    }

    for (double radius : {285000.0, 2500000.0, 6778000.0, 63000000.0}) {
        Vec3d offset = vertical * radius;
        FlightFrame::FromHeading(vertical, north, .4, f, u);
        orbit.Align(offset, f, u);
        for (double pitch : {-Pi/2, -.6, .6, Pi/2}) {
            orbit.Look(0, pitch - orbit.pitchDown);
            orbit.View(f, u);
            const Vec3d endpoint = offset + FlightFrame::ViewTravel(f, u, orbit.vertical, 100, 0, 0);
            const double radialStep = Dot(endpoint-offset, vertical);
            require(std::abs(radialStep + 100*std::sin(pitch)) < 1e-8, "pitch sets the radial part of forward flight");
            require(pitch > 0 ? Length(endpoint) < radius : Length(endpoint) > radius, "look down to descend, up to climb");
            const Vec3d survey = orbit.MoveAtFixedAltitude(offset, 100, 0, 0, 1);
            require(std::abs(Length(survey)-radius) < 1e-7, "same input at fixed altitude preserves radius");
            orbit.Follow(endpoint);
            orbit.View(f, u);
            require(std::abs(Dot(Cross(u,f), Normalize(endpoint))) < 1e-12, "horizon stays level during approach");
            orbit.Follow(offset);
        }
        orbit.Look(0, .4 - orbit.pitchDown);
        const double stride = radius * std::tan(Pi/180);
        for (int degree = 1; degree <= 360; ++degree) {
            offset = orbit.MoveAtFixedAltitude(offset, stride, 0, 0, 1);
            orbit.Follow(offset);
            const double angle = degree * Pi/180;
            require(close(orbit.vertical, {std::cos(angle),std::sin(angle),0}), "orbit crosses both geographic poles");
            require(std::abs(Length(offset)-radius) < radius*1e-12, "constant orbit radius");
            orbit.View(f, u);
            validFrame(f, u);
            require(std::abs(Dot(f,orbit.vertical) + std::sin(.4)) < 1e-12, "constant local pitch");
        }
        require(close(orbit.heading, north), "full orbit restores heading");
        orbit.Look(.3, 10);
        require(orbit.pitchDown == Pi/2, "orbit look stops at nadir");
        orbit.Look(.4, -.1);
        require(close(orbit.heading, Rotate(north, vertical, .7)), "yaw and pitch recover at nadir");
        orbit.Look(0, -10);
        require(orbit.pitchDown == -Pi/2, "orbit look stops at zenith");
        const Vec3d candidate = orbit.MoveAtFixedAltitude(offset, 0, stride, 150.0, 1);
        require(std::abs(Length(candidate)-radius-150) < radius*1e-12, "strafe and radial climb are independent");
        const Vec3d accepted = offset + (candidate-offset)*.25;
        orbit.Follow(accepted);
        require(close(orbit.vertical, Normalize(accepted)), "follow the accepted terrain slide");
        require(close(orbit.MoveAtFixedAltitude(accepted, 0, 0, 0, 1), accepted), "idle orbit keeps its exact position");
        const double floor = Length(accepted) - 10;
        require(std::abs(Length(orbit.MoveAtFixedAltitude(accepted, 0, 0, -2*radius, floor)) - floor) < 1e-6,
                "fast radial descent stops on the near side of a visual planet");
        require(close(orbit.MoveAtFixedAltitude(accepted, 0, 0, -100, floor+20), accepted, 1e-6),
                "an observer already below the floor stays in place on a descent request");
    }
}
}
int main() {
    using FlightFrame::CameraMode;
    CameraMode mode = CameraMode::Free;
    for (CameraMode expected : {CameraMode::Horizon, CameraMode::FixedAltitude, CameraMode::Free}) {
        mode = FlightFrame::NextCameraMode(mode);
        require(mode == expected, "Home cycles through all three camera modes");
    }
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
    require(close(FlightFrame::ViewTravel(f,u,u,0,0,2), {2,0,0}), "free flight lifts along its rolled screen axis");
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
    checkOrbit();
    std::puts("PASS: three camera modes, free roll, horizon-aligned dives and climbs, fixed altitude, poles and contact.");
}
