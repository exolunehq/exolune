#include "D3DApp.h"
#include "CelestialSystem.h"
#include <algorithm>
namespace {
Airless::Vec MoonVec(Vec3d p) {return {p.x,p.y,p.z};}
Vec3d WorldVec(Airless::Vec p) {return {p.x,p.y,p.z};}
}
int D3DApp::MoonAt(Vec3d position) const {
    return mMoonFrameValid?Airless::NearbyMoon(mMoonCentres,MoonVec(position)):-1;
}
bool D3DApp::NearMoon(Vec3d position) const {return MoonAt(position)>=0;}
void D3DApp::SelectMoon(int moon) {
    if(mActiveMoon!=moon) {
        mTerrainKept=mScreenKept=mHistoryValid=mCloudHistoryValid=false;mMeshFrozen=false;
        mWalkPatchValid=mWalkProbePending=false;mWorldValid=mWorldPending=false;
        mGroundHeight=0;mOceanElevation=-1000;mWaveReset=true;
        mPlanetPlantPlacement.Reset();mAudio.ResetWorld();ResetFlightContact();
    }
    mActiveMoon=moon;
    if(moon>=0){mMoonSurface=Airless::MoonSurface(unsigned(moon));mMoonCentre=WorldVec(mMoonCentres[moon]);}
}
Vec3d D3DApp::SurfaceCentre(Vec3d position) const {
    const int moon=MoonAt(position);return moon>=0?WorldVec(mMoonCentres[moon]):Vec3d{};
}
Vec3d D3DApp::SurfaceUp(Vec3d position) const {
    const Vec3d earth=Normalize(position);
    const int moon=MoonAt(position);if(moon<0)return earth;
    const Vec3d relative=position-WorldVec(mMoonCentres[moon]);
    const double radius=Celestial::Moons[moon].radius;
    double blend=std::min(std::max((8*radius-Length(relative))/(4*radius),0.0),1.0);
    blend=blend*blend*(3-2*blend);
    const Vec3d lunar=Normalize(relative);
    const double cosine=std::min(std::max(Dot(earth,lunar),-1.0),1.0);
    Vec3d axis=Cross(earth,lunar);
    if(Length(axis)<1e-8) {
        if(cosine>0)return earth;
        axis=Cross(std::abs(earth.y)<.9?Vec3d{0,1,0}:Vec3d{1,0,0},earth);
    }
    // A straight approach from Exolune has opposite verticals. Normalized linear interpolation
    // would vanish halfway through the handover and abruptly turn the observer upside down.
    return Normalize(Rotate(earth,Normalize(axis),std::acos(cosine)*blend));
}
double D3DApp::SurfaceRadius(Vec3d position) const {
    const int moon=MoonAt(position);return moon>=0?Celestial::Moons[moon].radius:PlanetRadius;
}
double D3DApp::SurfaceAltitude(Vec3d position) const {return Length(position-SurfaceCentre(position))-SurfaceRadius(position);}
bool D3DApp::CelestialRect(Vec3d centre,double radius,D3D12_RECT& rectangle) const {
    const Vec3d forward=Normalize(mCamForward),vertical=mCamUp;
    const Vec3d right=Normalize(Cross(vertical,forward)),up=Cross(forward,right),delta=centre-mCamPos;
    const double z=Dot(delta,forward);
    if(z+radius<=0)return false;
    rectangle={0,0,LONG(mClientWidth),LONG(mClientHeight)};
    if(z<=radius+.05)return true;
    const double tanY=std::tan(mCineFov*XM_PI/360),tanX=tanY*double(mClientWidth)/mClientHeight;
    auto bounds=[&](double v,double tangent,double size,bool invert) {
        double lo=1e30,hi=-1e30;
        for(double a:{v-radius,v+radius})for(double b:{z-radius,z+radius}) {
            const double p=(.5+(invert?-.5:.5)*a/(b*tangent))*size;
            lo=std::min(lo,p);hi=std::max(hi,p);
        }
        return std::array<LONG,2>{LONG(std::min(std::max(std::floor(lo)-2,0.0),size)),LONG(std::min(std::max(std::ceil(hi)+2,0.0),size))};
    };
    const auto x=bounds(Dot(delta,right),tanX,mClientWidth,false),y=bounds(Dot(delta,up),tanY,mClientHeight,true);
    rectangle={x[0],y[0],x[1],y[1]};return rectangle.right>rectangle.left && rectangle.bottom>rectangle.top;
}
void D3DApp::UpdateCelestialFrame() {
    const auto bodies=Celestial::System(mWeatherTime,{mSunDir.x,mSunDir.y,mSunDir.z});
    // Each observer follows its own nearby body; a free camera cannot tow a ship on another moon.
    // Distant spacecraft keep their inertial position. Cine supplies an explicit pose each frame.
    if(mMoonFrameValid && mCine.empty()) {
        auto transport=[&](Vec3d& position,Vec3d* previous=nullptr) {
            const int moon=MoonAt(position);if(moon<0)return;
            const auto& p=bodies[moon].position;
            const Vec3d motion=Vec3d{p.x*1000,p.y*1000,p.z*1000}-WorldVec(mMoonCentres[moon]);
            position=position+motion;if(previous)*previous=*previous+motion;
        };
        transport(mCamPos,&mPrevCamPos);transport(mShipPos,&mPrevShipPos);
        transport(mWalkFoot);transport(mWalkReturnPos);transport(mWalkPatchCentre);
    }
    for(unsigned i=0;i<Celestial::MoonCount;++i) {
        const auto& p=bodies[i].position;mMoonCentres[i]={p.x*1000,p.y*1000,p.z*1000};
    }
    mMoonFrameValid=true;SelectMoon(MoonAt(mCamPos));
    if(mActiveMoon>=0)mGroundHeight=mMoonSurface.Height(MoonVec(mCamPos-mMoonCentre));
}
void D3DApp::PlaceMoonCamera(double latitude,double longitude,double pitchDown,double heading,double clearance,unsigned moon) {
    UpdateCelestialFrame();
    PlaceCamera(latitude,longitude,pitchDown,heading,0);
    SelectMoon(int(moon));
    const Vec3d up=LatLonToDir(latitude,longitude);
    const double ground=mMoonSurface.Height(MoonVec(up));
    mCamPos=mMoonCentre+up*(mMoonSurface.radius+ground+clearance);
    mGroundHeight=ground;mOceanElevation=-1000;
    mHistoryValid=mCloudHistoryValid=false;mTerrainKept=false;mWaveReset=true;
    ResetFlightContact();
}
void D3DApp::MoonFlightContact(const FlightPose& before) {
    const bool ship=mView!=View::Free && mView!=View::Walk;
    if(mView==View::Walk || !mCine.empty())return;
    const Vec3d from=ship?before.ship:before.camera;
    const double hull=ship?double(Ship::Radius)+std::hypot(double(mShip.Profile().centreY),double(mShip.Profile().centreZ)):.25;
    unsigned samples=Airless::ContactSamples;
    for(unsigned i=0;i<Celestial::MoonCount;++i) {
        const Vec3d centre=WorldVec(mMoonCentres[i]),to=ship?mShipPos:mCamPos;
        const Vec3d relative=from-centre,delta=to-from;
        const double t=std::min(std::max(-Dot(relative,delta)/std::max(Dot(delta,delta),1e-12),0.0),1.0);
        const auto surface=Airless::MoonSurface(i);
        if(Length(relative+delta*t)>surface.radius+20000)continue;
        const Vec3d accepted=centre+WorldVec(surface.Sweep(MoonVec(relative),MoonVec(to-centre),hull,&samples));
        const Vec3d correction=accepted-to;
        mCamPos=mCamPos+correction;if(ship)mShipPos=accepted;
        if(Length(correction)>.001 && ship) {
            const Vec3d normal=WorldVec(surface.Normal(MoonVec(accepted-centre)));
            const double into=Dot(mShipVelocity,normal);
            if(into<0)mShipVelocity=mShipVelocity-normal*into;
        }
        if(mView==View::Chase) mCamPos=centre+WorldVec(surface.Sweep(MoonVec(before.camera-centre),MoonVec(mCamPos-centre),.25,&samples));
    }
    SelectMoon(MoonAt(mCamPos));
    if(mActiveMoon>=0)mGroundHeight=mMoonSurface.Height(MoonVec(mCamPos-mMoonCentre));
}
