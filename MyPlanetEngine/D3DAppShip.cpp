// D3DAppShip.cpp - D3DApp's ship (Ship.h): its flight, the views around it, and its frame for the shaders.
#include "D3DApp.h"
#include "Ocean.h"
#include <algorithm>

namespace
{
    // The selected profile supplies both pilot eye offsets.
    // The head rests 4.5 degrees down: the horizon through the canopy, the displays below it.
    const double kHeadRest = -0.08;
}

FlightDynamics::Field D3DApp::ShipField() const {
    FlightDynamics::Field field = {};
    field.planetRadius = PlanetRadius;
    if (Length(mShipPos) - PlanetRadius < ATMOSPHERE_HEIGHT_KM * 1000)
        field.wind = ClimateWindAt(mShipPos);
    field.moonsPlaced = mMoonFrameValid;
    for (size_t i = 0; i < field.moons.size(); ++i)
        field.moons[i] = {mMoonCentres[i].x, mMoonCentres[i].y, mMoonCentres[i].z};
    if (mFlightSlideBody == 1) {
        field.supportNormal = mFlightSlideNormal;
        field.supportOrigin = mFlightSlideOrigin;
    }
    return field;
}

double D3DApp::TransportClearance() const {
    const int moon=MoonAt(mShipPos);
    if (moon>=0) {
        const Vec3d p=mShipPos-SurfaceCentre(mShipPos);
        return Length(p)-SurfaceRadius(mShipPos)-Airless::MoonSurface(moon).Height({p.x,p.y,p.z});
    }
    const double ground=mTransportGroundKnown ? mTransportGround : mGroundHeight;
    return SurfaceAltitude(mShipPos) - (mCine.empty() ? ground : mCineShipGround);
}

Vec3d D3DApp::TransportPad(unsigned i, Vec3d origin, Vec3d forward, Vec3d up) const {
    const Vec3d left=Cross(forward,up);
    return origin+left*(i==0 ? -1.64 : i==1 ? 1.64 : 0.0)+forward*(i==2 ? 3.37 : -1.18)
        -up*TransportEquipment::PadDepth;
}

D3DApp::LandingSite D3DApp::SiteFromPads(const Vec3d (&points)[3], bool dry, Vec3d vertical) const {
    LandingSite site;
    const Vec3d n=Cross(points[1]-points[0],points[2]-points[0]);
    if (!(Length(n)>1e-5)) return site;
    site.normal=Normalize(n)*(Dot(n,vertical)<0 ? -1.0 : 1.0);
    site.point=(points[0]+points[1]+points[2])*(1./3);
    site.sampled=true; site.dry=dry;
    return site;
}

D3DApp::LandingSite D3DApp::CurrentLandingSite() const {
    const int moon=MoonAt(mShipPos);
    if (moon<0) return mLandingSite;
    if (TransportClearance()>600) return {};
    const Vec3d centre=SurfaceCentre(mShipPos);
    const auto surface=Airless::MoonSurface(moon);
    Vec3d points[3];
    for (unsigned i=0;i<3;++i) {
        const Vec3d d=Normalize(TransportPad(i,mShipPos-centre,mShipForward,mShipUp));
        points[i]=centre+d*(surface.radius+surface.Height({d.x,d.y,d.z}));
    }
    return SiteFromPads(points,true,Normalize(mShipPos-centre));
}

bool D3DApp::Landable(const LandingSite& site) const {
    if (!site.sampled || !site.dry) return false;
    const Vec3d up=SurfaceUp(mShipPos), delta=mShipPos-site.point;
    return Dot(up,site.normal)>=std::cos(12*XM_PI/180) && Length(delta-up*Dot(up,delta))<5;
}

bool D3DApp::TransportInView() const {
    return mShip.HasTransportRig() && mView!=View::Free && mView!=View::Walk;
}

double D3DApp::PadGap(const LandingSite& site, Vec3d origin, Vec3d forward, Vec3d up) const {
    double gap=1e9;
    for (unsigned i=0;i<3;++i)
        gap=std::min(gap,Dot(TransportPad(i,origin,forward,up)-site.point,site.normal));
    return gap;
}

void D3DApp::TransportNotice(const wchar_t* notice) {
    mTransportNotice=notice;
    mTransportNoticeUntil=mClock+5;
    mTransportPanelRefresh=-1;
}

void D3DApp::TransportLandingCommand() {
    using Phase=TransportEquipment::Phase;
    switch (mTransport.phase) {
    case Phase::Flight:
        if (TransportClearance()-TransportEquipment::PadDepth>TransportEquipment::MaxApproachHeight ||
            Length(mShipVelocity)*3.6>TransportEquipment::MaxApproachKmh) {
            TransportNotice(L"Pour atterrir, passez sous 5 km et 1 200 km/h sol.");
            return;
        }
        mTransport.SetPhase(Phase::Approach);
        mSearchTime=0;
        break;
    case Phase::Approach:
        mTransport.SetPhase(Phase::Flight);
        mSearchTime=0;
        break;
    case Phase::Parked: mTransport.SetPhase(Phase::Closing); break;
    case Phase::Closing: mTransport.SetPhase(Phase::Parked); break;
    case Phase::Takeoff: return;
    }
    mTransportNoticeUntil=0;
    mThrottle=mStickX=mStickY=0; mShipRate={};
    mFlightPilot.holding=mTransport.phase==Phase::Flight && Length(mShipVelocity)<3;
    mFlightPilot.heldNotch=0;
    if (mTransport.phase==Phase::Flight)
        TransportNotice(mFlightPilot.holding ? L"Stationnaire. Vous avez les commandes." : L"Approche interrompue. Vous avez les commandes.");
    mTransportPanelRefresh=-1;
}

void D3DApp::TransportToggle(TransportEquipment::Part part) {
    if (mTransport.Toggle(part)) { mTransportNoticeUntil=0; mTransportPanelRefresh=-1; return; }
    if (part==TransportEquipment::Hatch) TransportNotice(L"L\u2019escalier se commande une fois la navette pos\u00e9e.");
    else if (mTransport.phase!=TransportEquipment::Phase::Flight) TransportNotice(L"\u00c9quipement verrouill\u00e9 pendant la man\u0153uvre ou au sol.");
    else TransportNotice(L"Ailes prot\u00e9g\u00e9es en vol spatial ou pendant la rentr\u00e9e.");
}

void D3DApp::GroundTransport(const LandingSite& site) {
    if (!Landable(site) || mTransport.position[TransportEquipment::Gear]!=1 ||
        Dot(mShipUp,site.normal)<.97 || Length(mShipVelocity)>1.6) return;
    const double gap=Dot(mShipPos-site.point,site.normal)-TransportEquipment::PadDepth;
    const double lowest=PadGap(site,mShipPos,mShipForward,mShipUp);
    if (lowest<-.25 || lowest>.10) return;
    mShipPos=mShipPos-site.normal*gap;
    mShipUp=site.normal;
    mShipForward=Normalize(mShipForward-mShipUp*Dot(mShipForward,mShipUp));
    mTransport.SetPhase(TransportEquipment::Phase::Parked);
    mTransportExhaust={}; mFlightLoads={}; mFlightPilot={};
    mShipRate=mShipVelocity=mShipContactImpulse=mHeadSway=mHeadSwayRate=mEyeSpin={};
    mPlume=mStickX=mStickY=mThrottle=mHeadTilt=mHeadTiltRate=mFlightCues.engine=0;
    for (auto& jet:mJets) jet=0;
    mTransportPanelRefresh=-1;
}

double D3DApp::TransportDepth(Vec3d forward, Vec3d up, Vec3d vertical) const {
    return mShip.TransportDepth({float(Dot(Cross(forward,up),vertical)),-float(Dot(forward,vertical)),
                                 float(Dot(up,vertical))},mTransport);
}

void D3DApp::AdvanceEntryFlow(double dt) {
    if (mFlightCues.heat > 0)
        mEntryFlowPhase += dt * (1.0 + 2.8 * FlightDynamics::Smooth(80, 1100, mFlightCues.equivalentAirspeed));
    else mEntryFlowPhase = 0.0;
}

void D3DApp::MeasureShipAir(Vec3d position, Vec3d velocity, double altitude, double dt) {
    const double density = FlightDynamics::DensityAtAltitude(altitude);
    mFlightCues.Measure(density, velocity, density > 0 ? ClimateWindAt(position) : Vec3d{});
    mFlightCues.AdvanceHeat(altitude, Dot(position, velocity) / std::max(1.0, PlanetRadius + altitude), dt);
    mFlightPilot.surfaces.Advance(mFlightCues, 0, dt);
    AdvanceEntryFlow(dt);
}

// The wheel selects cruise speed, then sustained thrust. Up burns at full power, Shift boosts and X brakes.
// In vacuum a stick turn carries the inertial course. Atmospheric lift curves a banked ship's heading.
void D3DApp::UpdateShip(float dt) {
    const double eyeAhead = mShip.Profile().eyeAhead;
    const bool focused = GetForegroundWindow() == mhMainWnd;
    // A remote pilot sends the same raw mouse counts, wheel detents and buttons as the window.
    const auto& input = mFlightTake.input;
    if (mFlightTake.Connected()) {
        mRawDx = input[FlightTake::MouseX];
        mRawDy = input[FlightTake::MouseY];
        if (!TransportInView() || mTransport.phase==TransportEquipment::Phase::Flight)
            mThrottle = FlightDynamics::MoveThrottle(mThrottle, input[FlightTake::Wheel]);
        const bool looking = input[FlightTake::Look] != 0;
        if (mLooking && !looking) mHeadKept = true;
        mLooking = looking;
        if (input[FlightTake::CentreHead] != 0) mHeadKept = false;
    }
    auto held = [&](UINT vk) -> double {
        if (!mFlightTake.Connected()) return focused && (GetAsyncKeyState(vk) & 0x8000) ? 1.0 : 0.0;
        if (vk == 'X') return input[FlightTake::Brake] != 0;
        if (vk == VK_UP) return input[FlightTake::Burn] != 0;
        if (vk == VK_SHIFT) return input[FlightTake::Boost] != 0;
        if (vk == mMoveKeys[5]) return input[FlightTake::Roll] > 0;
        if (vk == mMoveKeys[4]) return input[FlightTake::Roll] < 0;
        return 0.0;
    };
    const double dx = mRawDx, dy = mRawDy, rest = mView != View::Chase ? (mShip.HasTransportRig() ? -.265 : kHeadRest) : 0.0;
    mRawDx = mRawDy = 0.0;
    const bool transport=TransportInView();
    using Phase=TransportEquipment::Phase;
    const bool flying=transport && !mTransport.GroundLocked();
    const double clearance=flying ? TransportClearance() : 0;
    const auto site=flying && clearance<600 ? CurrentLandingSite() : LandingSite{};
    if (flying && mTransport.phase!=Phase::Takeoff && clearance<7) GroundTransport(site);
    if (mLooking || mHeadFree || (transport && mTransport.phase!=Phase::Flight)) {
        if (mView == View::Chase) { // all around the ship, from below to above
            mHeadYaw = std::remainder(mHeadYaw + dx * 0.003, 2.0 * XM_PI);
            mHeadPitch = std::min(std::max(mHeadPitch - dy * 0.003, -1.45), 1.45);
        } else {
            mHeadYaw = std::min(std::max(mHeadYaw + dx * 0.003, -2.6), 2.6);
            mHeadPitch = std::min(std::max(mHeadPitch - dy * 0.003, -1.2), 1.3);
        }
    } else {
        const double back = mHeadKept ? 0.0 : 1.0 - std::exp(-dt / 0.15);
        mHeadYaw -= mHeadYaw * back;
        mHeadPitch += (rest - mHeadPitch) * back;
        mStickX = std::min(std::max(mStickX + dx * 0.004, -1.0), 1.0);
        mStickY = std::min(std::max(mStickY + dy * 0.004, -1.0), 1.0);
    }
    const double centre = std::exp(-dt / 0.15);
    mStickX *= centre;
    mStickY *= centre;

    if (transport && mTransport.GroundLocked()) {
        MeasureShipAir(mShipPos,{},Length(mShipPos)-PlanetRadius,dt);
        mTransport.Advance(dt,TransportClearance(),0,0,mFlightCues.density,mFlightCues.equivalentAirspeed,
            mFlightCues.dynamicPressurePa,mFlightCues.heat,0,false);
        if (mTransport.phase==Phase::Closing && mTransport.position[TransportEquipment::Hatch]==0)
            mTransport.SetPhase(Phase::Takeoff);
        UpdateShipCamera(dt);
        return;
    }

    // The rates follow the stick and the keys within a tenth of a second.
    const bool guided=transport && mTransport.Guided();
    const double roll = guided ? 0 : held(mMoveKeys[5]) - held(mMoveKeys[4]);
    const Vec3d wantedRate = { -mStickY * 1.3, mStickX * 1.0, roll * 1.8 };
    const Vec3d eyeBefore = mShipForward * eyeAhead + mShipUp * mShip.Profile().eyeUp;
    const Vec3d rateBefore = mShipRate;
    mShipRate =mShipRate + (wantedRate - mShipRate) * (1.0 - std::exp(-dt / 0.1));
    // The pilot works on the unassisted frame. Apply the bank again about the updated nose.
    mShipUp = Rotate(mShipUp, mShipForward, mFlightPilot.bank);
    FlightFrame::Turn(mShipForward,mShipUp,mShipRate.y*dt,-mShipRate.x*dt,mShipRate.z*dt);
    mShipUp = Rotate(mShipUp, mShipForward, -mFlightPilot.bank);

    if (guided) {
        const Vec3d vertical=SurfaceUp(mShipPos);
        Vec3d targetUp=vertical;
        if (mTransport.phase==Phase::Approach && clearance<10 && Landable(site)) targetUp=site.normal;
        const Vec3d axis=Cross(mShipUp,targetUp);
        const double angle=std::atan2(Length(axis),Dot(mShipUp,targetUp));
        if (angle>1e-7) {
            const Vec3d turn=Length(axis)>1e-7 ? Normalize(axis) : mShipForward;
            const double step=std::min(angle,double(dt)*1.5);
            mShipUp=Rotate(mShipUp,turn,step); mShipForward=Rotate(mShipForward,turn,step);
        }
        mFlightPilot.bank=0; mFlightPilot.holding=false;
    }

    const double strafe = mFlightTake.Connected() ? mFlightTake.strafe : held(mMoveKeys[3]) - held(mMoveKeys[2]);
    const double lift = mFlightTake.Connected() ? mFlightTake.lift :
        std::min(std::max(held(mMoveKeys[0]) + held(VK_SPACE) - held(mMoveKeys[1]) - held(VK_CONTROL), -1.0), 1.0);
    FlightDynamics::Controls controls = {mShipForward, Normalize(Cross(mShipUp, mShipForward)), mShipUp,
                                         mThrottle, strafe, lift, held(VK_SHIFT) > 0, held('X') > 0, held(VK_UP) > 0,
                                         mShipRate.y, mShipRate.z};
    if (mShip.HasTransportRig()) {
        controls.transport = &mTransport;
        controls.terrainClearance = clearance;
        controls.descentRate = -Dot(mShipVelocity,SurfaceUp(mShipPos));
        controls.localUp=SurfaceUp(mShipPos);
        if (guided) {
            controls.throttle=controls.lift=controls.strafe=0;
            controls.brake=controls.boost=controls.fullThrust=false;
            controls.landingSite=Landable(site);
            if (mTransport.phase==Phase::Approach && !controls.landingSite && controls.terrainClearance<12 &&
                Length(mShipVelocity)<9 && site.sampled) {
                const Vec3d relative=mShipPos-SurfaceCentre(mShipPos);
                if (mSearchTime==0) mSearchOrigin=relative;
                mSearchTime+=dt;
                const double angle=std::sqrt(1+1.3*mSearchTime)-1, radius=2.8*angle;
                const Vec3d target=mSearchOrigin+(mShipForward*std::cos(angle)+controls.right*std::sin(angle))*radius;
                const Vec3d offset=target-relative;
                controls.landingDrift=FlightDynamics::Limited(offset-controls.localUp*Dot(offset,controls.localUp),2);
                if (mSearchTime>=90) {
                    mTransport.SetPhase(Phase::Flight);
                    mFlightPilot.holding=true; mFlightPilot.heldNotch=0;
                    TransportNotice(L"Aucun sol praticable proche. Stationnaire, pilotage manuel.");
                }
            }
        }
    }
    Vec3d newPos = mShipPos;
    mFlightLoads = FlightDynamics::Advance(mSettings.Automated() ? 0 : dt, newPos, mShipVelocity,
                                           mFlightCues, controls, mFlightPilot, ShipField());
    AdvanceEntryFlow(dt);
    const auto& loads = mFlightLoads;
    mShipForward = controls.forward;
    mShipUp = controls.up;
    const Vec3d right = controls.right;
    mPlume += (loads.mainJet - mPlume) * (1.0 - std::exp(-dt / .18));
    if (controls.transport) {
        mTransportExhaust.Advance(dt, loads.axialJet, loads.liftJet, loads.sideJet, false);
        if (mTransport.phase==Phase::Takeoff && Length(mShipVelocity)<.25 &&
            std::abs(controls.terrainClearance-TransportEquipment::PadDepth-TransportEquipment::HoverHeight)<.12) {
            mTransport.SetPhase(Phase::Flight);
            mFlightPilot.holding=true; mFlightPilot.heldNotch=0;
            TransportNotice(L"Stationnaire \u00e9tabli. Vous avez les commandes.");
        }
    }
    // The flight corridor sweeps the hull before this candidate pose is accepted. Keep only the sea floor here.
    const double keel=mShip.HasTransportRig() && TransportClearance()<10000
        ? TransportDepth(mShipForward,mShipUp,SurfaceUp(mShipPos)) : 2.5;
    const bool resting = mShip.HasTransportRig() && mTransportGroundKnown && Length(mShipVelocity)<6 && TransportClearance()<10;
    const double groundFloor = resting ? mTransportGround : (mFlightContactPSO ? 0.0 : mGroundHeight);
    double minRadius = PlanetRadius + groundFloor + keel;
    if (mOcean && !mWaveReset && mGroundHeight <= 0.0)
        minRadius = std::max(minRadius, PlanetRadius + double(mOcean->SurfaceHeight()) + keel);
    const double newRadius = Length(newPos);
    if (newRadius < minRadius) {
        const Vec3d n = newRadius > 0 ? newPos * (1 / newRadius) : Normalize(mShipPos);
        newPos = n * minRadius;
        const double into = Dot(mShipVelocity, n);
        if (into < 0.0) {
            mShipContactImpulse = mShipContactImpulse - n * into;
            mShipVelocity = mShipVelocity - n * into;
        }
    }
    mShipPos = newPos;

    // The head spring feels the seat load and the displaced eye's rotation. Free fall carries the pilot with the ship.
    // Logarithmic compression keeps near-ground acceleration visible and bounds the response to a fast transfer.
    if (dt > 0.0f) {
        const Vec3d spin = (mShipForward * eyeAhead + mShipUp * mShip.Profile().eyeUp - eyeBefore) * (1.0 / dt);
        const Vec3d a = loads.seatAcceleration + (spin - mEyeSpin + mShipContactImpulse) * (1.0 / dt);
        mShipContactImpulse = {};
        mEyeSpin = spin;
        const Vec3d local = { Dot(a, right), Dot(a, mShipUp), Dot(a, mShipForward) };
        const double felt = Length(local);
        const double push = felt > 1e-6 ? std::tanh(std::log1p(felt / 2.0) / 3.0) / felt : 0.0;
        const Vec3d sway = { -local.x * push * 0.03, -local.y * push * 0.03, -local.z * push * 0.06 };
        const double w = 2.0 * XM_PI * 1.4, zeta = 0.6; // 1.4 Hz, slightly underdamped
        mHeadSwayRate = mHeadSwayRate + ((sway - mHeadSway) * (w * w) - mHeadSwayRate * (2.0 * zeta * w)) * dt;
        mHeadSway = mHeadSway + mHeadSwayRate * dt;
        const Vec3d turning = (mShipRate - rateBefore) * (1.0 / dt); // pitch up, yaw right, roll right (rad/s2)
        const double tilt = std::copysign(0.05 * std::tanh(std::log1p(std::abs(turning.z) / 2.0) / 3.0), turning.z);
        mHeadTiltRate += ((tilt - mHeadTilt) * (w * w) - mHeadTiltRate * (2.0 * zeta * w)) * dt;
        mHeadTilt += mHeadTiltRate * dt;

        // Translational jets follow manoeuvring and station keeping. Rotational jets follow angular acceleration.
        const double jets[5] = { loads.sideJet, loads.liftJet, turning.z / 6.0, turning.x / 6.0, turning.y / 6.0 };
        for (int k = 0; k < 5; ++k) mJets[k] = std::min(std::max(jets[k], -1.0), 1.0);
    }

    UpdateShipCamera(dt);
}

void D3DApp::UpdateShipCamera(float dt) {
    const double eyeAhead=mShip.Profile().eyeAhead;
    Vec3d look = Rotate(mShipForward, mShipUp, mHeadYaw);
    const Vec3d headRight = Normalize(Cross(mShipUp, look));
    look = Rotate(look, headRight, -mHeadPitch);
    const Vec3d headUp = Rotate(mShipUp, headRight, -mHeadPitch);
    if (mView != View::Chase) {
        mCamPos = mShipPos + mShipForward * (eyeAhead + mHeadSway.z) + mShipUp * (mShip.Profile().eyeUp + mHeadSway.y)
                + Normalize(Cross(mShipUp, mShipForward)) * mHeadSway.x;
        mCamForward = look;
        mCamUp = Rotate(headUp, look, mHeadTilt); // towards the left: behind a roll to the right
    } else {
        const Vec3d wantedOffset = look * -15.0 + headUp * 6.5;
        mChaseOffset = mChaseOffset + (wantedOffset - mChaseOffset) * (1.0 - std::exp(-dt / 0.12));
        mCamPos = mShipPos + mChaseOffset;
        const double cameraFloor=PlanetRadius+(mFlightContactPSO?0.0:mGroundHeight)+1.0;
        if (Length(mCamPos) < cameraFloor) mCamPos=Normalize(mCamPos)*cameraFloor;
        mCamForward = Normalize(mShipPos + mShipForward * 2.0 - mCamPos);
        mCamUp = Normalize(headUp - mCamForward * Dot(headUp, mCamForward));
    }
}

// The ship takes the camera's position and attitude, including roll.
void D3DApp::PlaceShipAtCamera() {
    mShip.ResetSurfaceWeather();
    mShipForward=mCamForward;mShipUp=mCamUp;
    FlightFrame::Orthonormalize(mShipForward,mShipUp);
    mShipPos = mCamPos - mShipForward * mShip.Profile().eyeAhead - mShipUp * mShip.Profile().eyeUp;
    mShipVelocity = mShipRate = mHeadSway = mHeadSwayRate = mEyeSpin = {};
    mShipContactImpulse = {};
    mFlightCues = {};
    mTransport = {};
    mTransportExhaust = {};
    mTransportGroundKnown = false;
    mLandingSite={}; mSearchTime=0; mTransportNoticeUntil=0; mTransportPanelRefresh=-1;
    mEntryFlowPhase = 0.0;
    mFlightPilot = {};
    mFlightLoads = {};
    mThrottleLever = 0.0f;
    mHeadTilt = mHeadTiltRate = mPlume = 0.0;
    for (double& jet : mJets) jet = 0.0;
    mStickX = mStickY = mHeadYaw = mThrottle = 0.0;
    mHeadPitch = mView != View::Chase ? (mShip.HasTransportRig() ? -.265 : kHeadRest) : 0.0;
    mChaseOffset = mShipForward * -15.0 + mShipUp * 6.5;
    mPrevShipPos = mShipPos;
    mPrevShipForward = mShipForward;
    mPrevShipUp = mShipUp;
    mHistoryValid = false;
}

// The ship's views hold the mouse: hidden, kept in the window, read raw.
void D3DApp::HoldMouse(bool hold) {
    hold = hold && !mMouseFree && !mTransportMenu;
    if (hold == mMouseHeld) return;
    mMouseHeld = hold;
    if (hold) {
        RECT r;
        GetClientRect(mhMainWnd, &r);
        MapWindowPoints(mhMainWnd, nullptr, reinterpret_cast<POINT*>(&r), 2);
        ClipCursor(&r);
        while (ShowCursor(FALSE) >= 0) {}
    } else {
        ClipCursor(nullptr);
        while (ShowCursor(TRUE) < 0) {}
    }
    mRawDx = mRawDy = 0.0;
}

void D3DApp::SetView(View view) {
    ResetFlightContact();
    mCameraBody = -1;
    if (view == View::Cockpit && !mShip.Profile().cockpit) view = View::Chase;
    if (mView == View::Walk) {
        mWalkProbePending=mWalkPatchValid=false; mWalkJump=false;
        mFlightPilot = {};
        mFlightLoads = {};
    }
    if (view != View::Free && view != View::Walk && mView == View::Free) PlaceShipAtCamera(); // the ship comes to the free camera
    mView = view;
    mHeadYaw = 0.0;
    mHeadPitch = view == View::Cockpit || view == View::Bare ? (mShip.HasTransportRig() ? -.265 : kHeadRest) : 0.0;
    mHeadFree = mHeadKept = false;
    FlightFrame::Orthonormalize(mCamForward,mCamUp);
    mHistoryValid = false;
    HoldMouse(view != View::Free && GetForegroundWindow() == mhMainWnd && !(GetAsyncKeyState(VK_MENU)&0x8000));
}

// The ship's frame for its shaders, in the face-local frame of the camera (faceX, faceY, faceZ), and its shadow on the
// ground in the frame's constants.
void D3DApp::UpdateShipFrame(float dt, const Vec3d& faceX, const Vec3d& faceY, const Vec3d& faceZ) {
    auto toLocal = [&](const Vec3d& v) {
        return XMVectorSet((float)Dot(v, faceX), (float)Dot(v, faceY), (float)Dot(v, faceZ), 0.0f);
    };
    // The planet frame is left-handed (east x north = down): Cross(up, forward) is the right, as for the camera.
    const Vec3d shipLeft = Cross(mShipForward, mShipUp), shipBack = mShipForward * -1.0;
    // Blender's x the pilot's left, y aft, z up.
    Ship::Constants& ship = mShip.Frame();
    const XMMATRIX model(toLocal(shipLeft), toLocal(shipBack), toLocal(mShipUp), XMVectorSetW(toLocal(mShipPos - mCamPos), 1.0f));
    XMStoreFloat4x4(&ship.model, XMMatrixTranspose(model));
    auto inShip = [&](const Vec3d& v) { return XMFLOAT3((float)Dot(v, shipLeft), (float)Dot(v, shipBack), (float)Dot(v, mShipUp)); };
    const XMFLOAT3 sunInShip = inShip(mSunDir), upInShip = inShip(SurfaceUp(mShipPos));
    mShip.SetLights(sunInShip, upInShip);
    // The ground's points into that map, through the ship's frame: its shadow on the ground (PixelShader.hlsl).
    XMStoreFloat4x4(&mConstants->shipSunShadow, XMMatrixTranspose(XMMatrixInverse(nullptr, model)
                                                * XMMatrixTranspose(XMLoadFloat4x4(&ship.shadow[0]))));
    ship.sun = { sunInShip.x, sunInShip.y, sunInShip.z, 0.0f };
    ship.up = { upInShip.x, upInShip.y, upInShip.z, (float)((Length(mShipPos) - PlanetRadius) / 1000.0) };
    const double speed = Length(mShipVelocity);
    ship.air = { float(mFlightCues.equivalentAirspeed), dt, (float)std::fmod(mClock, 3600.0), mSettings.glassTest };
    ship.options = { mHud ? 1.0f : 0.0f, mView == View::Cockpit ? 1.0f : 0.0f, float(mShip.Profile().model), float(mFlightCues.density) };
    const double airspeed = Length(mFlightCues.airVelocity);
    const XMFLOAT3 flow = inShip(airspeed > 0.01 ? mFlightCues.airVelocity * (-1.0 / airspeed) : Vec3d{});
    ship.airflow = { flow.x, flow.y, flow.z, float(mFlightCues.heat) };
    ship.thrust = { (float)mPlume,(float)mJets[2], (float)mJets[1], (float)mJets[0] };
    ship.turn = { (float)mJets[3], (float)mJets[4], (float)std::fmod(mClock, 3600.0), (float)mEntryFlowPhase };
    // The dashboard's screens: the heading from the north, the place, the ground under the ship, the gas.
    const Vec3d vertical = SurfaceUp(mShipPos), pole = kNorth - vertical * Dot(kNorth, vertical);
    const Vec3d north = Length(pole) > 1e-6 ? Normalize(pole) : Vec3d{ 1.0, 0.0, 0.0 }, east = Cross(vertical, north);
    const double deg = 180.0 / XM_PI;
    ship.course = { (float)(std::atan2(Dot(mShipForward, east), Dot(mShipForward, north)) * deg),
                    (float)(std::asin(vertical.y) * deg), (float)(std::atan2(vertical.z, vertical.x) * deg), (float)((mCine.empty() ? mGroundHeight : mCineShipGround) / 1000.0) };
    const float lever = float(mThrottle / FlightDynamics::ThrottleNotches);
    ship.gauges = { lever, float(SurfaceAltitude(mShipPos)*.001), NearMoon(mShipPos)?1.0f:0.0f, float(mFlightCues.engine) };
    const float rx = mFlightTake.radioLevel >= 0 ? mFlightTake.radioLevel :
                     (RadioAvailable() ? mAudio.RadioLevel() : -1.0f);
    const float amplitude = std::max(rx, 0.0f);
    mRadioLamp += ((rx >= 0 ? 1.0f : 0.0f) - mRadioLamp) * -std::expm1(-dt / .12f);
    mRadioEnvelope += (amplitude - mRadioEnvelope) * -std::expm1(-dt / (amplitude > mRadioEnvelope ? .028f : .095f));
    ship.radio = {mRadioLamp, mRadioEnvelope, 0, 0};
    const auto& surfaces = mFlightPilot.surfaces;
    ship.airframe = {float(surfaces.wings), float(surfaces.airbrakes), float(mFlightLoads.retroJet),
                     mFlightPilot.holding ? 1.0f : 0.0f};
    const double support = Length(mFlightLoads.supportThrust);
    const XMFLOAT3 exhaust = support > 1e-6 ? inShip(mFlightLoads.supportThrust * (-1 / support)) : XMFLOAT3(0, 0, -1);
    ship.supportExhaust = {exhaust.x, exhaust.y, exhaust.z,
        mShip.Profile().surfaces.span > 0 ? float(FlightDynamics::Clamp(support / 14, 0, 1)) : 0.0f};
    // The stick and the throttle (ShipPose): the stick leans back 12 degrees as the nose pitches up, aside with the roll,
    // and twists 15 degrees with the yaw; the throttle swings 40 degrees over its notches, forwards with the gas.
    auto pivoted = [](const Ship::Pivot& p, const XMMATRIX& r) {
        const XMVECTOR c = XMLoadFloat3(&p.point);
        return XMMatrixTranspose(XMMatrixTranslationFromVector(-c) * r * XMMatrixTranslationFromVector(c));
    };
    for (auto& pose : ship.pose) XMStoreFloat4x4(&pose, XMMatrixIdentity());
    const Ship::Pivot* pivots = mShip.pivots;
    if (mShip.HasTransportRig()) {
        const float roll=float(FlightDynamics::Clamp(mShipRate.z/1.8,-1,1));
        XMStoreFloat4x4(&ship.pose[0],pivoted(pivots[0], XMMatrixRotationZ(-.19f*float(mStickX)) *
            XMMatrixRotationX(.30f*float(mStickY)) * XMMatrixRotationY(-.28f*roll-.15f*float(mStickX))));
        const float response = mCine.empty() ? -std::expm1(-dt/.085f) : 1.0f;
        mThrottleLever += (lever-mThrottleLever)*response;
        XMStoreFloat4x4(&ship.pose[1],pivoted(pivots[1],XMMatrixRotationX(.64f*(mThrottleLever-.5f))));
    } else if (mShip.Profile().model == ShipModel::Navette) {
        const float bank = float(FlightDynamics::Clamp((mShipRate.z + mFlightPilot.bank) / 1.8, -1, 1));
        XMStoreFloat4x4(&ship.pose[0], pivoted(pivots[0], XMMatrixRotationAxis(XMLoadFloat3(&pivots[0].axis), -.31f * bank)
            * XMMatrixTranslation(0, -.018f * float(mStickY), 0)));
        const float response = mCine.empty() ? -std::expm1(-dt / .085f) : 1.0f;
        mThrottleLever += (lever - mThrottleLever) * response;
        const auto stops = mShip.throttleStops;
        const auto& throttle = pivots[SHIP_PACK_POSES - 1];
        const float angle = stops.x + (stops.y - stops.x) * mThrottleLever;
        XMStoreFloat4x4(&ship.pose[SHIP_PACK_POSES - 1],
            pivoted(throttle, XMMatrixRotationAxis(XMLoadFloat3(&throttle.axis), angle)));
    } else if (mShip.Profile().pivotCount >= 2) {
        XMStoreFloat4x4(&ship.pose[0], pivoted(pivots[0], XMMatrixRotationAxis(XMLoadFloat3(&pivots[0].axis), -0.26f * (float)mStickX)
            * XMMatrixRotationX(0.21f * (float)mStickY) * XMMatrixRotationY(-0.21f * (float)(mShipRate.z / 1.8))));
        XMStoreFloat4x4(&ship.pose[1], pivoted(pivots[1], XMMatrixRotationAxis(XMLoadFloat3(&pivots[1].axis), 0.7f * (lever - 0.5f))));
    }
    // The elevons (design_chasseur.py), inner and outer on each wing: the pitch and the roll mixed, as the ship turns,
    // both ways, 20 degrees at most. Trailing edge up for the nose up, and on the side the ship rolls towards. Their
    // hinges run outwards: a positive turn lifts the left's trailing edge and lowers the right's.
    const double pitchUp = mShipRate.x / 1.3, rollRight = mShipRate.z / 1.8;
    const double elevon[2] = { std::min(std::max(pitchUp - rollRight, -1.0), 1.0), std::min(std::max(pitchUp + rollRight, -1.0), 1.0) };
    for (int side = 0; mShip.Profile().model == ShipModel::Chasseur && side < 2; ++side) { // the pilot's left, then right
        const float angle = (side == 0 ? 0.35f : -0.35f) * (float)elevon[side];
        for (int k : { 2 + side, 4 + side })
            XMStoreFloat4x4(&ship.pose[k], pivoted(pivots[k], XMMatrixRotationAxis(XMLoadFloat3(&pivots[k].axis), angle)));
    }
    XMStoreFloat4(&ship.velocity, toLocal(speed > 1e-3 ? mShipVelocity * (1.0 / speed) : mShipForward));
    ship.velocity.w = (float)speed;
    ship.equipment = ship.automation = {};
    if (mShip.HasTransportRig()) {
        if (!mCine.empty() || mView == View::Walk)
            mTransport.Advance(dt, TransportClearance(), -Dot(mShipVelocity,vertical), speed, mFlightCues.density,
                mFlightCues.equivalentAirspeed, mFlightCues.dynamicPressurePa, mFlightCues.heat, 0, false);
        const auto& p=mTransport.position;
        ship.equipment={float(p[0]),float(p[1]),float(p[2]),float(p[3])};
        ship.automation={float(mTransport.ManualMask()),1,float(mTransportExhaust.Deflection()),0};
        ship.thrust.x = float(mTransportExhaust.MainPower());
        ship.thrust.z = float(mTransportExhaust.lift);
        ship.thrust.w = float(mTransportExhaust.side);
        ship.airframe.z = float(std::max(0.0, -mTransportExhaust.ahead));
        mShip.SetTransportPose(mTransport);
    } else mShip.SetFlightSurfaces(ship.airframe.x, ship.airframe.y);
}
