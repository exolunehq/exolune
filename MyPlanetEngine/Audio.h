#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <xaudio2.h>
#include <atomic>
#include <cstdint>
#include "WorldAudio.h"

// What the ship sounds like this frame, filled in D3DApp::UpdateShip (docs/recherche-son.md).
struct ShipSound {
    float thrust = 0.0f;  // the engine's demanded power, 0 to 1: full beyond a threshold
    float roll = 0.0f;    // the roll thrusters' keys, -1 left to 1 right
    float strafe = 0.0f;  // the sideways thrusters' keys, -1 left to 1 right
    float lift = 0.0f;    // the up and down thrusters' keys, -1 down to 1 up
    float wind = 0.0f;    // the airspeed brought to sea level, m/s
    float air = 0.0f;     // the air's density, 1 at sea level: thin air carries little sound, none in space
    bool cockpit = true;  // heard through the hull: muffled
};

// The ship's sound, synthesized: engine, thrusters and wind, played by XAudio2. The game only sets targets; XAudio2's
// thread computes the samples it asks for and smooths the targets. Without an Update for a quarter second (the free
// camera), the ship falls silent.
class Audio : private IXAudio2VoiceCallback {
public:
    ~Audio() { Shutdown(); }
    bool Initialize(); // false: no sound device, the app goes on silent
    void Shutdown();
    void Update(const ShipSound&);
    void UpdateWorld(const WorldSound& s, float dt) { mWorld.Update(s, dt); }
    void Footstep(FootSurface s, float strength = 1.0f) { mWorld.Step(s, strength); }
    void Footstep(const FootContact& c, float strength = 1.0f) { mWorld.Step(c, strength); }
    void ResetWorld() { mWorld.Reset(); }
    void SetMix(float master, float footsteps, float ambience, float ship);

private:
    static constexpr UINT Rate = 48000, Blocks = 16, BlockFrames = 4096;
    void STDMETHODCALLTYPE OnVoiceProcessingPassStart(UINT32 bytesRequired) override;
    void STDMETHODCALLTYPE OnVoiceProcessingPassEnd() override {}
    void STDMETHODCALLTYPE OnStreamEnd() override {}
    void STDMETHODCALLTYPE OnBufferStart(void*) override {}
    void STDMETHODCALLTYPE OnBufferEnd(void*) override {}
    void STDMETHODCALLTYPE OnLoopEnd(void*) override {}
    void STDMETHODCALLTYPE OnVoiceError(void*, HRESULT) override {}
    void Render(float* out, UINT frames);

    IXAudio2* mXAudio = nullptr;
    IXAudio2MasteringVoice* mMaster = nullptr;
    IXAudio2SourceVoice* mVoice = nullptr;
    float mBlocks[Blocks][BlockFrames * 2] = {};
    UINT mNextBlock = 0;

    // The targets, written by the game's thread.
    std::atomic<float> mThrust{0.0f}, mRoll{0.0f}, mStrafe{0.0f}, mLift{0.0f}, mWind{0.0f}, mDensity{0.0f}, mCockpit{1.0f};
    std::atomic<uint64_t> mLastUpdate{0};

    // The synthesis, on XAudio2's thread only.
    struct Svf { float a = 0.0f, b = 0.0f; void Run(float x, float fc, float q, float& low, float& band, float& high); };
    struct Jet { float key = 0.0f, peak = 0.0f, env = 0.0f, level = 0.0f, fc = 3000.0f, pan = 0.0f; Svf filter; };
    uint32_t mSeed = 0x9e3779b9u;
    float Noise();
    float mOn = 0.0f, mPower = 0.0f, mAir = 0.0f, mThin = 0.0f, mInside = 1.0f, mGust = 0.0f, mGustTarget = 0.0f;
    double mPhase = 0.0, mPhase2 = 0.0, mWhine = 0.0, mWobble = 0.0, mThrob = 0.0;
    UINT mGustCount = 0;
    Svf mRumbleFilter, mRoar[2], mWindBand[2], mWindLow, mHull[2], mEngineHull[2], mHumFilter;
    Jet mJets[3]; // roll, strafe, lift
    WorldAudio mWorld;
    std::atomic<float> mMasterGain{1.0f}, mShipGain{1.0f};
    float mMasterLevel = 1.0f;
};
