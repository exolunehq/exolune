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

void D3DApp::MeasureShipAir(Vec3d position, Vec3d velocity, double altitude, double dt) {
    const double density = FlightDynamics::DensityAtAltitude(altitude);
    mFlightCues.Measure(density, velocity, density > 0 ? ClimateWindAt(position) : Vec3d{});
    mFlightCues.AdvanceHeat(altitude, Dot(position, velocity) / std::max(1.0, PlanetRadius + altitude), dt);
}

// The wheel selects cruise speed, then sustained thrust. Up burns at full power, Shift boosts and X brakes.
// In vacuum a stick turn carries the inertial course. Atmospheric lift curves a banked ship's heading.
void D3DApp::UpdateShip(float dt) {
    const double eyeAhead = mShip.Profile().eyeAhead;
    const bool focused = GetForegroundWindow() == mhMainWnd;
    auto held = [focused](UINT vk) { return focused && (GetAsyncKeyState(vk) & 0x8000) ? 1.0 : 0.0; };
    const double dx = mRawDx, dy = mRawDy, rest = mView != View::Chase ? kHeadRest : 0.0;
    mRawDx = mRawDy = 0.0;
    if (mLooking || mHeadFree) {
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

    // The rates follow the stick and the keys within a tenth of a second.
    const double roll = held(mMoveKeys[5]) - held(mMoveKeys[4]);
    const Vec3d wantedRate = { -mStickY * 1.3, mStickX * 1.0, roll * 1.8 };
    const Vec3d eyeBefore = mShipForward * eyeAhead + mShipUp * mShip.Profile().eyeUp;
    const Vec3d rateBefore = mShipRate;
    mShipRate =mShipRate + (wantedRate - mShipRate) * (1.0 - std::exp(-dt / 0.1));
    FlightFrame::Turn(mShipForward,mShipUp,mShipRate.y*dt,-mShipRate.x*dt,mShipRate.z*dt);

    const double strafe = held(mMoveKeys[3]) - held(mMoveKeys[2]);
    const double lift = std::min(std::max(held(mMoveKeys[0]) + held(VK_SPACE) - held(mMoveKeys[1]) - held(VK_CONTROL), -1.0), 1.0);
    FlightDynamics::Controls controls = {mShipForward, Normalize(Cross(mShipUp, mShipForward)), mShipUp,
                                         mThrottle, strafe, lift, held(VK_SHIFT) > 0, held('X') > 0, held(VK_UP) > 0};
    Vec3d newPos = mShipPos;
    const auto loads = FlightDynamics::Advance(mSettings.Automated() ? 0 : dt, newPos, mShipVelocity,
                                                mFlightCues, controls, mFlightPilot, ShipField());
    mShipForward = controls.forward;
    mShipUp = controls.up;
    const Vec3d right = controls.right;
    mPlume += (loads.mainJet - mPlume) * (1.0 - std::exp(-dt / .18));
    // The flight corridor sweeps the hull before this candidate pose is accepted. Keep only the sea floor here.
    double minRadius = PlanetRadius + (mFlightContactPSO ? 0.0 : mGroundHeight) + 2.5;
    if (mOcean && !mWaveReset && mGroundHeight <= 0.0)
        minRadius = std::max(minRadius, PlanetRadius + double(mOcean->SurfaceHeight()) + 2.5);
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

    // The camera: the pilot's eye and head, or behind and above the ship, lagging behind its turns.
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
    mFlightPilot = {};
    mHeadTilt = mHeadTiltRate = mPlume = 0.0;
    for (double& jet : mJets) jet = 0.0;
    mStickX = mStickY = mHeadYaw = mThrottle = 0.0;
    mHeadPitch = mView != View::Chase ? kHeadRest : 0.0;
    mChaseOffset = mShipForward * -15.0 + mShipUp * 6.5;
    mPrevShipPos = mShipPos;
    mPrevShipForward = mShipForward;
    mPrevShipUp = mShipUp;
    mHistoryValid = false;
}

// The ship's views hold the mouse: hidden, kept in the window, read raw.
void D3DApp::HoldMouse(bool hold) {
    hold = hold && !mMouseFree;
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
    }
    if (view != View::Free && view != View::Walk && mView == View::Free) PlaceShipAtCamera(); // the ship comes to the free camera
    mView = view;
    mHeadYaw = 0.0;
    mHeadPitch = view == View::Cockpit || view == View::Bare ? kHeadRest : 0.0;
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
    ship.turn = { (float)mJets[3], (float)mJets[4], (float)std::fmod(mClock, 3600.0), 0.0f };
    // The dashboard's screens: the heading from the north, the place, the ground under the ship, the gas.
    const Vec3d vertical = SurfaceUp(mShipPos), pole = kNorth - vertical * Dot(kNorth, vertical);
    const Vec3d north = Length(pole) > 1e-6 ? Normalize(pole) : Vec3d{ 1.0, 0.0, 0.0 }, east = Cross(vertical, north);
    const double deg = 180.0 / XM_PI;
    ship.course = { (float)(std::atan2(Dot(mShipForward, east), Dot(mShipForward, north)) * deg),
                    (float)(std::asin(vertical.y) * deg), (float)(std::atan2(vertical.z, vertical.x) * deg), (float)((mCine.empty() ? mGroundHeight : mCineShipGround) / 1000.0) };
    const float lever = float(mThrottle / FlightDynamics::ThrottleNotches);
    ship.gauges = { lever, float(SurfaceAltitude(mShipPos)*.001), NearMoon(mShipPos)?1.0f:0.0f, float(mFlightCues.engine) };
    // The stick and the throttle (ShipPose): the stick leans back 12 degrees as the nose pitches up, aside with the roll,
    // and twists 15 degrees with the yaw; the throttle swings 40 degrees over its notches, forwards with the gas.
    auto pivoted = [](const Ship::Pivot& p, const XMMATRIX& r) {
        const XMVECTOR c = XMLoadFloat3(&p.point);
        return XMMatrixTranspose(XMMatrixTranslationFromVector(-c) * r * XMMatrixTranslationFromVector(c));
    };
    for (auto& pose : ship.pose) XMStoreFloat4x4(&pose, XMMatrixIdentity());
    const Ship::Pivot* pivots = mShip.pivots;
    if (mShip.Profile().pivotCount >= 2) {
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
}
