// Bounded environmental mixer: resident recordings, procedural air/water, and a single-producer event queue.
#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <string>
#include <vector>
#include "FootContact.h"

struct WorldSound {
    float wind = 0, leaves = 0, rain = 0, surf = 0, birds = 0, insects = 0, frogs = 0;
    float presence = 0, cockpit = 0;
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
    void SetMix(float footsteps, float ambience);
    void Render(float* stereo, unsigned frames); // adds to existing PCM; audio thread, no locks/allocations/I/O

private:
    static constexpr unsigned FootVariants=6, BirdCount=6, Bird0=FootContact::Count*FootVariants,
        Frog=Bird0+BirdCount, Thunder=Frog+1, ClipCount=Thunder+1;
    enum { Wind, Leaves, Rain, Surf, Birds, Insects, Frogs, Presence, Cockpit, TargetCount };
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
    std::atomic<float> mFootMix{1}, mAmbienceMix{1};
    std::atomic<uint64_t> mLastUpdate{0};
    uint32_t mGameSeed = 0xd5c87b91u, mAudioSeed = 0xa3fb1927u;
    float Random();
    float Noise();
    bool Push(const Event&);
    double mBirdWait = 2.0, mFrogWait = 4.0, mThunderWait = 20.0;
    unsigned mLastBird = Bird0;
    std::array<unsigned,FootContact::Count> mLastFoot = {{FootVariants,FootVariants,FootVariants,FootVariants,FootVariants,FootVariants}};
    bool mLeftFoot = false;
    float mLow[2] = {}, mAir[2] = {}, mLeaf[2] = {}, mWater[2] = {}, mHull[2] = {};
    float mGust = 0, mGustTarget = 0, mSurf = 0, mSurfTarget = 0;
    unsigned mControl = 0;
    double mInsectPhase = 0, mInsectPulse = 0;
};
