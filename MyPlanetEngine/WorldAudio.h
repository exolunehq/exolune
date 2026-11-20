// Bounded environmental mixer: resident recordings, procedural air/water, and a single-producer event queue.
#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <string>
#include <vector>
#include "FootContact.h"

enum class SoundListener { Observer, Chase, Cockpit, Helmet };
inline bool HasRadio(SoundListener listener) {
    return listener == SoundListener::Cockpit || listener == SoundListener::Helmet;
}

struct WorldSound {
    float wind = 0, leaves = 0, rain = 0, surf = 0, birds = 0, insects = 0, frogs = 0;
    float presence = 0;
    SoundListener listener = SoundListener::Observer;
    float engine = 0, flightDensity = 0, equivalentAirspeed = 0, heat = 0, exertion = 0;
    float rollJet = 0, sideJet = 0, liftJet = 0;
    bool navigator = false;
    double position[3] = {};
    float right[3] = {1,0,0}, forward[3] = {0,0,1};
};

class WorldAudio {
public:
    static constexpr unsigned Rate = 48000;
    void Initialize(const std::wstring& directory);
    void Update(const WorldSound&, float dt); // game thread; also schedules sparse, world-anchored animal calls
    void Step(FootSurface surface, float strength = 1.0f);
    void Step(const FootContact&, float strength = 1.0f);
    void Reset(); // discard old-location calls after a teleport
    void SetMix(float footsteps, float ambience, float ship = 1.0f);
    void RequestRadio(); // edge-triggered headset reply, at most one transmission
    void Render(float* stereo, unsigned frames); // adds to existing PCM; audio thread, no locks/allocations/I/O

private:
    static constexpr unsigned FootVariants=6, BirdCount=6, Bird0=FootContact::Count*FootVariants,
        Frog=Bird0+BirdCount, Thunder=Frog+1, ClipCount=Thunder+1;
    enum { Wind, Rain, Surf, Insects, Presence, Insulation, TargetCount };
    struct Clip { std::vector<float> samples; };
    std::array<Clip,ClipCount> mClips;
    struct Event { unsigned clip = 0, epoch = 0; float gain = 0, pitch = 1, pan = 0, cutoff = 16000; bool foot = false; double position[3] = {}; };
    struct Voice { Event event; double cursor = 0; float gain[2] = {}, filter = 0, coefficient = 1; bool active = false; };
    static constexpr unsigned Queue = 32, Voices = 12;
    std::array<Event,Queue> mQueue = {};
    std::array<Voice,Voices> mVoices = {};
    std::atomic<unsigned> mRead{0}, mWrite{0}, mEpoch{0};
    std::array<std::atomic<float>,TargetCount> mTarget = {};
    std::array<float,TargetCount> mLevel = {};
    std::array<std::atomic<double>,3> mPosition = {};
    std::array<std::atomic<float>,3> mRight = {}, mForward = {};
    std::atomic<float> mFootMix{1}, mAmbienceMix{1}, mShipMix{1};
    std::atomic<uint64_t> mLastUpdate{0};
    uint32_t mGameSeed = 0xd5c87b91u, mAudioSeed = 0xa3fb1927u;
    float Random();
    float Noise();
    bool Push(const Event&);
    double mBirdWait = 2.0, mFrogWait = 4.0, mThunderWait = 20.0;
    unsigned mLastBird = Bird0;
    std::array<unsigned,FootContact::Count> mLastFoot = {{FootVariants,FootVariants,FootVariants,FootVariants,FootVariants,FootVariants}};
    bool mLeftFoot = false;
    float mLow[2] = {}, mAir[2] = {}, mWater[2] = {}, mHull[2] = {};
    float mGust = 0, mGustTarget = 0, mSurf = 0, mSurfTarget = 0;
    unsigned mControl = 0;
    double mInsectPhase = 0, mInsectPulse = 0;

    // The manifest owns each channel count, nominal gain and source take. Only targets cross threads.
    enum Layer { Reactor, Cabin, Airflow, Entry, Foliage, Breath, Radio, LayerCount };
    struct Stem {
        std::vector<float> pcm;
        unsigned channels = 1, frames = 0;
        float nominal = 0, level = 0, rate = 1, cutoff = 1, low[2] = {};
        double cursor = 0;
        std::atomic<float> gainTarget{0}, rateTarget{1}, filterTarget{1};
    };
    std::array<Stem,LayerCount> mStem;
    std::atomic<SoundListener> mListener{SoundListener::Observer};
    std::atomic<unsigned> mRadioRequest{0};
    unsigned mMixEpoch = 0, mRadioFrame = 0;
    bool mRadioPlaying = false;
    float mRadioDuck = 0;
    void UpdateImmersion(const WorldSound&);
    void RenderImmersion(float* stereo, unsigned frames, bool alive, unsigned epoch);
    static void SynthesizeLayer(Layer, Stem&);
};
