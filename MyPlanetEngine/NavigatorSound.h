// Original continuous antigravity synthesis. No movie samples, loops or external audio dependencies.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>

class NavigatorSound {
public:
    static constexpr unsigned Rate = 48000;
    struct Controls {
        float power = 0, roll = 0, strafe = 0, lift = 0, wind = 0, air = 1;
        bool inside = true, active = true;
    };
    void Render(float* stereo, unsigned frames, const Controls& c) {
        const float target = Clamp(c.power), motion = Clamp((std::abs(c.roll) + std::abs(c.strafe) + std::abs(c.lift)) * 0.5f);
        for (unsigned i = 0; i < frames; ++i) {
            Smooth(mOn, c.active ? 1.0f : 0.0f, 0.18f);
            Smooth(mPower, target, target > mPower ? 0.65f : 0.32f);
            Smooth(mMotion, motion, 0.11f);
            Smooth(mWind, std::min(std::max(c.wind, 0.0f) / 220.0f, 1.2f), 0.4f);
            Smooth(mAir, Clamp(c.air), 0.4f);
            Smooth(mInside, c.inside ? 1.0f : 0.0f, 0.12f);
            const float drift = float(Osc(6, 0.071)), breathe = float(Osc(7, 0.123));
            // A quiet sub floor stays almost fixed in pitch. Power changes texture and brightness, not RPM.
            const float sub = float(Osc(0,38.17) + Osc(1,53.83)) * 0.0015f;
            const float bandwidth = 1800.0f + 900.0f * mPower + 650.0f * mMotion;
            const float washGain = (0.0015f + 0.003f * mPower + 0.002f * mMotion) /
                std::sqrt(1.047f * bandwidth / (0.65f * Rate));
            float dry[2];
            for (unsigned ch = 0; ch < 2; ++ch) {
                // Broad noise-excited resonances avoid a persistent synthesized musical note or combustion pulse.
                static constexpr float centres[3]={164.9f,437.7f,1031.3f}, q[3]={18.0f,23.0f,29.0f};
                const float excite=Noise();
                float resonance=0;
                for(unsigned r=0;r<3;++r) {
                    const float fc=centres[r]*(1.0f+0.003f*drift+0.0012f*float(ch));
                    const float level=(r==0 ? .008f+.003f*mPower : r==1 ? .006f+.004f*mPower : .003f+.003f*mPower*mPower);
                    resonance+=mResonance[ch][r].Band(excite,fc,q[r])*level/std::sqrt(1.047f*fc/(q[r]*Rate));
                }
                const float low=mBody[ch].Band(Noise(),83.0f,0.65f)*.0035f/std::sqrt(1.047f*83.0f/(.65f*Rate));
                const float wash = mWash[ch].Band(Noise(), bandwidth, 0.65f) * washGain;
                // Environmental wind is handled by WorldAudio. The ship itself has no nozzle or exhaust layer.
                dry[ch] = (low + resonance + wash)*(0.98f+0.02f*breathe) + sub;
            }
            // Short damped reflections suggest a resonant metal cavity without periodic sample playback.
            const unsigned tapL = (mDelayAt + Delay - 1297) % Delay, tapR = (mDelayAt + Delay - 1601) % Delay;
            const float wetL = mDelay[0][tapL], wetR = mDelay[1][tapR];
            mDelay[0][mDelayAt] = dry[0] * 0.24f + wetR * 0.17f;
            mDelay[1][mDelayAt] = dry[1] * 0.24f + wetL * 0.17f;
            mDelayAt = (mDelayAt + 1) % Delay;
            const float coupling = mInside + (1.0f - mInside) * mAir;
            for (unsigned ch = 0; ch < 2; ++ch) {
                const float raw = dry[ch] + (ch == 0 ? wetL : wetR) * (0.4f + 0.35f * mInside);
                const float cutoff = 14000.0f - 9300.0f * mInside;
                mLow[ch] += (raw - mLow[ch]) * (1.0f - std::exp(-Tau * cutoff / Rate));
                stereo[2 * i + ch] = mLow[ch] * mOn * coupling;
            }
        }
    }
private:
    static constexpr float Tau = 6.283185307179586f;
    static constexpr unsigned Delay = 2048;
    struct Filter {
        float a = 0, b = 0;
        float Band(float x, float fc, float q) {
            const float g = std::tan(3.14159265f * fc / Rate), k = 1.0f / q;
            const float a1 = 1.0f / (1.0f + g * (g + k)), a2 = g * a1, a3 = g * a2;
            const float v3 = x - b, v1 = a1 * a + a2 * v3, v2 = b + a2 * a + a3 * v3;
            a = 2 * v1 - a; b = 2 * v2 - b;
            return v1 / q;
        }
    };
    static float Clamp(float v) { return std::min(std::max(v, 0.0f), 1.0f); }
    static void Smooth(float& value, float target, float seconds) {
        value += (target - value) * (1.0f - std::exp(-1.0f / (seconds * Rate)));
    }
    double Osc(unsigned i, double hz) {
        mPhase[i] += 6.283185307179586 * hz / Rate;
        if (mPhase[i] >= 6.283185307179586) mPhase[i] -= 6.283185307179586;
        return std::sin(mPhase[i]);
    }
    float Noise() {
        mSeed ^= mSeed << 13; mSeed ^= mSeed >> 17; mSeed ^= mSeed << 5;
        return float(int32_t(mSeed)) / 2147483648.0f;
    }
    uint32_t mSeed = 0x7248ab15u;
    std::array<double, 8> mPhase = {};
    Filter mWash[2], mWindFilter[2], mBody[2], mResonance[2][3];
    std::array<float, Delay> mDelay[2] = {};
    unsigned mDelayAt = 0;
    float mOn = 0, mPower = 0, mMotion = 0, mWind = 0, mAir = 1, mInside = 1, mLow[2] = {};
};
