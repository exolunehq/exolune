#include "Audio.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cmath>
#pragma comment(lib, "xaudio2.lib")

// The tuning (docs/recherche-son.md): levels are the rms of each layer, before the master and its soft clip.
namespace {
    constexpr float Pi = 3.14159265f;
    constexpr float MasterGain = 0.7f;
    constexpr float RumbleGain = 0.22f, HumGain = 0.07f, RoarGain = 0.2f, WhineGain = 0.01f;
    constexpr float JetGain = 0.35f, JetHold = 0.28f;          // the puff's peak is about 1, held it drops to JetHold
    constexpr float JetCutoff[3] = { 3200.0f, 2600.0f, 1800.0f }; // roll, strafe, lift: the lift's jets are the biggest
    constexpr float WindGain = 0.25f, WindFull = 150.0f;        // m/s at sea level for the full wind; heard from 30 km/h
    constexpr float HullEngine = 650.0f, HullOther = 1400.0f;   // the cockpit's low-pass, Hz
    constexpr float Silence = 250.0f;                           // ms without Update before the ship falls silent

    float Smoothing(float seconds) { return 1.0f - std::exp(-1.0f / (seconds * 48000.0f)); }
    // White noise filtered to a band keeps this share of its rms (variance 1/3): the layers are normalized by it.
    float LowRms(float fc) { return std::sqrt(0.74f * fc / 48000.0f); }
    float BandRms(float fc, float q) { return std::sqrt(1.047f * fc / (q * 48000.0f)); }
}

// Simper's state-variable filter: low, band (unity peak once multiplied by 1/q) and high outputs.
void Audio::Svf::Run(float x, float fc, float q, float& low, float& band, float& high) {
    const float g = std::tan(Pi * std::min(fc, 21000.0f) / 48000.0f), k = 1.0f / q;
    const float a1 = 1.0f / (1.0f + g * (g + k)), a2 = g * a1, a3 = g * a2;
    const float v3 = x - b, v1 = a1 * a + a2 * v3, v2 = b + a2 * a + a3 * v3;
    a = 2.0f * v1 - a;
    b = 2.0f * v2 - b;
    low = v2;
    band = v1;
    high = x - k * v1 - v2;
}

float Audio::Noise() {
    mSeed ^= mSeed << 13;
    mSeed ^= mSeed >> 17;
    mSeed ^= mSeed << 5;
    return float(int32_t(mSeed)) * (1.0f / 2147483648.0f);
}

bool Audio::Initialize() {
    const std::wstring sample = FindAbove(L"assets\\audio\\step-soil-0.wav");
    if (sample.empty()) throw std::runtime_error("Audio bank missing: assets/audio/*.wav must be above the executable.");
    mWorld.Initialize(sample.substr(0, sample.find_last_of(L"\\/")));
    if (FAILED(XAudio2Create(&mXAudio, 0, XAUDIO2_DEFAULT_PROCESSOR))) return false;
    WAVEFORMATEX format = {};
    format.wFormatTag = WAVE_FORMAT_IEEE_FLOAT;
    format.nChannels = 2;
    format.nSamplesPerSec = Rate;
    format.wBitsPerSample = 32;
    format.nBlockAlign = format.nChannels * format.wBitsPerSample / 8;
    format.nAvgBytesPerSec = format.nSamplesPerSec * format.nBlockAlign;
    if (FAILED(mXAudio->CreateMasteringVoice(&mMaster)) || FAILED(mXAudio->CreateSourceVoice(&mVoice, &format, 0,
            XAUDIO2_DEFAULT_FREQ_RATIO, this)) || FAILED(mVoice->Start())) {
        Shutdown();
        return false;
    }
    return true;
}

void Audio::Shutdown() {
    if (mVoice) mVoice->DestroyVoice(); // waits for the callback
    if (mMaster) mMaster->DestroyVoice();
    if (mXAudio) mXAudio->Release();
    mVoice = nullptr;
    mMaster = nullptr;
    mXAudio = nullptr;
}

void Audio::Update(const ShipSound& s) {
    mThrust = std::min(std::max(s.thrust, 0.0f), 1.0f);
    mRoll = s.roll;
    mStrafe = s.strafe;
    mLift = s.lift;
    mWind = std::max(s.wind, 0.0f);
    mDensity = std::min(std::max(s.air, 0.0f), 1.0f);
    mCockpit = s.cockpit ? 1.0f : 0.0f;
    mNavigator = s.navigator;
    mLastUpdate = GetTickCount64();
}

void Audio::SetMix(float master, float footsteps, float ambience, float ship) {
    mMasterGain = std::min(std::max(master, 0.0f), 1.0f);
    mShipGain = std::min(std::max(ship, 0.0f), 1.0f);
    mWorld.SetMix(footsteps, ambience);
}

// XAudio2 asks for what keeps the voice from starving: computed now, in the next blocks of the ring.
void Audio::OnVoiceProcessingPassStart(UINT32 bytesRequired) {
    for (UINT frames = bytesRequired / (2 * sizeof(float)); frames > 0;) {
        const UINT n = std::min(frames, BlockFrames);
        float* block = mBlocks[mNextBlock];
        mNextBlock = (mNextBlock + 1) % Blocks;
        Render(block, n);
        XAUDIO2_BUFFER buffer = {};
        buffer.AudioBytes = n * 2 * sizeof(float);
        buffer.pAudioData = reinterpret_cast<const BYTE*>(block);
        mVoice->SubmitSourceBuffer(&buffer);
        frames -= n;
    }
}

void Audio::Render(float* out, UINT frames) {
    const bool alive = float(GetTickCount64() - mLastUpdate.load()) < Silence;
    const float on = alive ? 1.0f : 0.0f, thrust = alive ? mThrust.load() : 0.0f, wind = alive ? mWind.load() : 0.0f,
        density = alive ? mDensity.load() : 0.0f;
    const float cockpit = mCockpit.load(), keys[3] = { alive ? mRoll.load() : 0.0f, alive ? mStrafe.load() : 0.0f,
                                                       alive ? mLift.load() : 0.0f };
    static const float kOn = Smoothing(0.3f), kRise = Smoothing(0.25f), kFall = Smoothing(0.12f), kAir = Smoothing(0.5f),
        kInside = Smoothing(0.08f), kGust = Smoothing(0.6f), kAttack = Smoothing(0.003f), kRelease = Smoothing(0.045f),
        kBurst = std::exp(-1.0f / (0.07f * 48000.0f)), kHold = Smoothing(0.04f);
    constexpr double Tau = 6.283185307179586, Dt = 1.0 / 48000.0;
    float low, band, high;
    const bool navigator = mNavigator.load();
    if (navigator) {
        mNavigatorSound.Render(out, frames, { thrust, keys[0], keys[1], keys[2], wind, density, cockpit > 0.5f, alive });
        const float gain = MasterGain * mShipGain.load(std::memory_order_relaxed);
        for (UINT i = 0; i < frames * 2; ++i) out[i] *= gain;
    }
    const bool dormant = !alive && mOn < 1e-5f;
    if (!navigator && dormant) std::fill(out,out+2*frames,0.0f);
    for (UINT i = 0; !navigator && !dormant && i < frames; ++i) {
        mOn += (on - mOn) * kOn;
        mPower += (thrust - mPower) * (thrust > mPower ? kRise : kFall);
        mAir += (wind - mAir) * kAir;
        mThin += (density - mThin) * kAir;
        mInside += (cockpit - mInside) * kInside;
        const float p = mPower;

        // The engine: a rumble that throbs, a hum of a few harmonics that wavers, a roar rising with the power.
        float fc = 45.0f + 220.0f * p;
        mRumbleFilter.Run(Noise(), fc, 0.6f, low, band, high);
        mWobble = std::fmod(mWobble + Tau * 0.23 * Dt, Tau);
        mThrob = std::fmod(mThrob + Tau * (3.0 + 5.0 * p) * Dt, Tau);
        const float throb = 1.0f + 0.15f * float(std::sin(mThrob));
        const float rumble = low / LowRms(fc) * RumbleGain * (0.06f + 0.94f * p) * throb;
        const double f0 = (34.0 + 40.0 * p) * (1.0 + 0.01 * std::sin(mWobble));
        mPhase = std::fmod(mPhase + Tau * f0 * Dt, Tau);
        mPhase2 = std::fmod(mPhase2 + Tau * f0 * 1.006 * Dt, Tau);
        float hum = 0.0f;
        for (int h = 1; h <= 6; ++h) hum += float(std::sin(h * mPhase) + std::sin(h * mPhase2)) / float(h);
        mHumFilter.Run(hum * 0.5f, 200.0f + 300.0f * p, 0.7f, low, band, high);
        hum = low * HumGain * (0.15f + 0.85f * p);
        mWhine = std::fmod(mWhine + Tau * (500.0 + 1300.0 * p) * Dt, Tau);
        const float whine = float(std::sin(mWhine)) * WhineGain * p;
        const float roarFc = 180.0f + 2200.0f * p * p, roarLevel = RoarGain * std::pow(p, 1.4f) / BandRms(roarFc, 0.7f);
        float engine[2];
        for (int c = 0; c < 2; ++c) {
            mRoar[c].Run(Noise(), roarFc, 0.7f, low, band, high);
            const float raw = rumble + hum + whine + band / 0.7f * roarLevel;
            mEngineHull[c].Run(raw, HullEngine + (16000.0f - HullEngine) * (1.0f - mInside), 0.7f, low, band, high);
            engine[c] = low;
        }

        // The thrusters: a puff at each press, a lower hiss while the key is held, a short tail when let go.
        float other[2] = { 0.0f, 0.0f };
        for (int j = 0; j < 3; ++j) {
            Jet& jet = mJets[j];
            const float key = keys[j];
            if (std::abs(key) > 0.5f && (std::abs(jet.key) <= 0.5f || key * jet.key < 0.0f)) {
                jet.peak = 0.8f + 0.15f * (Noise() + 1.0f);
                jet.fc = JetCutoff[j] * (1.0f + 0.25f * Noise());
                jet.pan = j == 0 ? (Noise() > 0.0f ? 0.6f : -0.6f) : j == 1 ? (key > 0.0f ? -0.6f : 0.6f) : 0.15f * Noise();
            }
            jet.key = key;
            jet.peak *= kBurst;
            const float hold = std::abs(key) > 0.5f ? JetHold : 0.0f;
            jet.env += (hold - jet.env) * kHold;
            const float target = jet.peak + jet.env;
            jet.level += (target - jet.level) * (target > jet.level ? kAttack : kRelease);
            if (jet.level < 1e-4f) continue;
            jet.filter.Run(Noise(), jet.fc, 0.7f, low, band, high);
            const float s = high * 1.8f * JetGain * jet.level, pan = jet.pan * (1.0f - 0.5f * mInside);
            other[0] += s * std::sqrt(0.5f * (1.0f - pan));
            other[1] += s * std::sqrt(0.5f * (1.0f + pan));
        }

        // The wind: a band of noise rising with the airspeed, swayed by slow gusts, and a buffeting at high speed; as
        // loud as the air is dense, so it fades out above some 30 km whatever the speed.
        if (++mGustCount >= 4800) {
            mGustCount = 0;
            mGustTarget = Noise();
        }
        mGust += (mGustTarget - mGust) * kGust;
        const float w = std::min(mAir / WindFull, 1.2f);
        if (w * mThin > 1e-3f) {
            const float windFc = (250.0f + 1600.0f * w) * (1.0f + 0.25f * mGust), q = 1.0f + 0.6f * mGust;
            const float level = WindGain * w * (1.0f + 0.35f * mGust) * mThin / BandRms(windFc, q);
            mWindLow.Run(Noise(), 60.0f, 0.7f, low, band, high);
            const float buffet = low / LowRms(60.0f) * 0.15f * w * w * mThin;
            for (int c = 0; c < 2; ++c) {
                mWindBand[c].Run(Noise(), windFc, q, low, band, high);
                other[c] += band / q * level + buffet;
            }
        }

        for (int c = 0; c < 2; ++c) {
            mHull[c].Run(other[c], HullOther + (16000.0f - HullOther) * (1.0f - mInside), 0.7f, low, band, high);
            out[2 * i + c] = MasterGain * mOn * mShipGain.load(std::memory_order_relaxed) * (engine[c] + low * (1.0f - 0.2f * mInside));
        }
    }
    mWorld.Render(out, frames);
    const float master = mMasterGain.load(), smooth = Smoothing(0.025f);
    for (UINT i = 0; i < frames; ++i) {
        mMasterLevel += (master - mMasterLevel) * smooth;
        out[2*i] = std::tanh(out[2*i] * mMasterLevel);
        out[2*i+1] = std::tanh(out[2*i+1] * mMasterLevel);
    }
}
