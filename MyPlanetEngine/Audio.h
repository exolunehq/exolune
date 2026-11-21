#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <xaudio2.h>
#include <atomic>
#include <cstdint>
#include "WorldAudio.h"
#include "NavigatorSound.h"

// One listener frame drives the synthesized ships and resident environmental bank on the same XAudio2 stream.
class Audio : private IXAudio2VoiceCallback {
public:
    ~Audio() { Shutdown(); }
    bool Initialize(bool startDevice = true); // device-free authoring loads the same bank
    void Shutdown();
    void Update(const WorldSound&, float dt);
    float RadioLevel() const { return mWorld.RadioLevel(); }
    void RequestRadio() { mWorld.RequestRadio(); }
    void Footstep(FootSurface s, float strength = 1.0f) { mWorld.Step(s, strength); }
    void Footstep(const FootContact& c, float strength = 1.0f) { mWorld.Step(c, strength); }
    void ResetWorld() { mLastUpdate=0; mWorld.Reset(); }
    void SetMix(float master, float footsteps, float ambience, float ship);
    void Render(float* stereo, UINT frames); // XAudio2 callback, or offline after Initialize(false)

private:
    static constexpr UINT Rate = 48000, Blocks = 16, BlockFrames = 4096;
    void STDMETHODCALLTYPE OnVoiceProcessingPassStart(UINT32 bytesRequired) override;
    void STDMETHODCALLTYPE OnVoiceProcessingPassEnd() override {}
    void STDMETHODCALLTYPE OnStreamEnd() override {}
    void STDMETHODCALLTYPE OnBufferStart(void*) override {}
    void STDMETHODCALLTYPE OnBufferEnd(void*) override {}
    void STDMETHODCALLTYPE OnLoopEnd(void*) override {}
    void STDMETHODCALLTYPE OnVoiceError(void*, HRESULT) override {}

    IXAudio2* mXAudio = nullptr;
    IXAudio2MasteringVoice* mMaster = nullptr;
    IXAudio2SourceVoice* mVoice = nullptr;
    float mBlocks[Blocks][BlockFrames * 2] = {};
    UINT mNextBlock = 0;

    // The targets, written by the game's thread.
    std::atomic<float> mThrust{0.0f}, mRoll{0.0f}, mStrafe{0.0f}, mLift{0.0f}, mDensity{0.0f}, mCockpit{1.0f};
    std::atomic<uint64_t> mLastUpdate{0};

    // The synthesis, on XAudio2's thread only.
    struct Svf { float a = 0.0f, b = 0.0f; void Run(float x, float fc, float q, float& low, float& band, float& high); };
    struct Jet { float key = 0.0f, peak = 0.0f, env = 0.0f, level = 0.0f, fc = 3000.0f, pan = 0.0f; Svf filter; };
    uint32_t mSeed = 0x9e3779b9u;
    float Noise();
    float mOn = 0.0f, mPower = 0.0f, mThin = 0.0f, mInside = 1.0f;
    double mPhase = 0.0, mPhase2 = 0.0, mWhine = 0.0, mWobble = 0.0, mThrob = 0.0;
    Svf mRumbleFilter, mRoar[2], mHull[2], mEngineHull[2], mHumFilter;
    Jet mJets[3]; // roll, strafe, lift
    WorldAudio mWorld;
    NavigatorSound mNavigatorSound;
    std::atomic<bool> mNavigator{false};
    std::atomic<float> mMasterGain{1.0f}, mShipGain{1.0f};
    float mMasterLevel = 1.0f;
};
