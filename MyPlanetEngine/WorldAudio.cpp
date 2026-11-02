#include "WorldAudio.h"
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <stdexcept>

namespace {
    constexpr float Pi = 3.14159265358979323846f;
    float Clamp(float x) { return std::min(std::max(x,0.0f),1.0f); }
    float Coefficient(float hz) { return 1.0f - std::exp(-2.0f*Pi*hz/48000.0f); }
    std::vector<float> LoadWave(const std::wstring& file) {
        FILE* f = nullptr;
        if (_wfopen_s(&f,file.c_str(),L"rb") || !f) throw std::runtime_error("Missing audio recording: run assets/audio/prepare.py.");
        char header[12];
        if (fread(header,1,12,f)!=12 || std::memcmp(header,"RIFF",4) || std::memcmp(header+8,"WAVE",4)) {
            fclose(f); throw std::runtime_error("Invalid audio RIFF header.");
        }
        bool format = false;
        std::vector<float> samples;
        for (char id[4]; fread(id,1,4,f)==4;) {
            uint32_t size = 0;
            if (fread(&size,4,1,f)!=1 || size > 8*1024*1024) break;
            if (!std::memcmp(id,"fmt ",4)) {
                struct Format { uint16_t kind,channels; uint32_t rate,bytes; uint16_t align,bits; } fmt = {};
                if (size < sizeof(fmt) || fread(&fmt,sizeof(fmt),1,f)!=1) break;
                format = fmt.kind==1 && fmt.channels==1 && fmt.rate==48000 && fmt.bits==16 && fmt.align==2;
                fseek(f,long(size-sizeof(fmt)),SEEK_CUR);
            } else if (!std::memcmp(id,"data",4)) {
                if (!format || size % 2) break;
                std::vector<int16_t> pcm(size/2);
                if (fread(pcm.data(),1,size,f)!=size) break;
                samples.resize(pcm.size());
                for (size_t i=0;i<pcm.size();++i) samples[i]=pcm[i]/32768.0f;
            } else fseek(f,size,SEEK_CUR);
            if (size & 1) fseek(f,1,SEEK_CUR);
        }
        fclose(f);
        if (samples.size()<64) throw std::runtime_error("Audio recording must be mono PCM16 at 48 kHz.");
        return samples;
    }
}

float WorldAudio::Random() {
    mGameSeed ^= mGameSeed<<13; mGameSeed ^= mGameSeed>>17; mGameSeed ^= mGameSeed<<5;
    return float(mGameSeed>>8)*(1.0f/16777216.0f);
}
float WorldAudio::Noise() {
    mAudioSeed ^= mAudioSeed<<13; mAudioSeed ^= mAudioSeed>>17; mAudioSeed ^= mAudioSeed<<5;
    return float(int32_t(mAudioSeed))*(1.0f/2147483648.0f);
}

void WorldAudio::Initialize(const std::wstring& directory) {
    const wchar_t* names[] = {L"soil",L"grass",L"gravel",L"rock",L"sand",L"snow"};
    static_assert(sizeof(names)/sizeof(names[0])==FootContact::Count,"Footstep banks must match the contact contract.");
    for (unsigned surface=0;surface<FootContact::Count;++surface)
        for (unsigned take=0;take<FootVariants;++take)
            mClips[surface*FootVariants+take].samples=LoadWave(directory+L"\\step-"+names[surface]+L"-"+std::to_wstring(take)+L".wav");
    for (unsigned i=0;i<BirdCount;++i) mClips[Bird0+i].samples=LoadWave(directory+L"\\bird"+std::to_wstring(i)+L".wav");
    // A small resonant wetland call; procedural, not a recording of a species absent from the simulation.
    auto& frog=mClips[Frog].samples; frog.resize(Rate);
    double phase=0;
    for (unsigned i=0;i<frog.size();++i) {
        const double t=double(i)/Rate, pulse=std::pow(std::max(std::sin(2*Pi*6*t),0.0),3.0);
        phase+=2*Pi*(270+70*std::exp(-t*6))/Rate;
        frog[i]=float(0.3*pulse*std::sin(Pi*t)*std::sin(phase+1.7*std::sin(phase*2)));
    }
    auto& thunder=mClips[Thunder].samples; thunder.resize(Rate*6);
    float low=0, high=0;
    const float kl=Coefficient(110), kh=Coefficient(600);
    for (unsigned i=0;i<thunder.size();++i) {
        const float t=float(i)/Rate, n=Noise(); low+=(n-low)*kl; high+=(n-high)*kh;
        const float envelope=(1-std::exp(-t*3))*std::exp(-t*0.8f)*std::min((6-t)*2,1.0f);
        thunder[i]=(low*7+high)*envelope*0.6f;
    }
}

bool WorldAudio::Push(const Event& e) {
    const unsigned write=mWrite.load(std::memory_order_relaxed), next=(write+1)%Queue;
    if (next==mRead.load(std::memory_order_acquire)) return false;
    mQueue[write]=e;
    mWrite.store(next,std::memory_order_release);
    return true;
}

void WorldAudio::Reset() { mEpoch.fetch_add(1); mBirdWait=2; mFrogWait=4; mThunderWait=20; }
void WorldAudio::SetMix(float steps,float ambience) { mFootMix=Clamp(steps); mAmbienceMix=Clamp(ambience); }

void WorldAudio::Step(FootSurface surface,float strength) {
    Step(FootContact(surface),strength);
}

void WorldAudio::Step(const FootContact& contact,float strength) {
    const unsigned primary=contact.Primary();
    if (primary==FootContact::Count) return;
    unsigned secondary=FootContact::Count; float other=0;
    for (unsigned i=0;i<FootContact::Count;++i)
        if (i!=primary && std::isfinite(contact.shares[i]) && contact.shares[i]>other) { secondary=i; other=contact.shares[i]; }
    const float first=contact.shares[primary];
    // Preserve one clear contact on uniform ground. Blend only a substantial second coating, aligned at its onset.
    if (other/(first+other)<0.15f) { secondary=FootContact::Count; other=0; }
    mLeftFoot=!mLeftFoot;
    const float gain=(0.43f+0.04f*Random())*std::min(std::max(strength,0.0f),1.8f);
    for (unsigned layer=0;layer<2;++layer) {
        const unsigned surface=layer==0?primary:secondary;
        if (surface==FootContact::Count) continue;
        const unsigned previous=mLastFoot[surface];
        unsigned take=unsigned(Random()*(previous<FootVariants?FootVariants-1:FootVariants));
        if (previous<FootVariants && take>=previous) ++take;
        mLastFoot[surface]=take;
        Event e; e.epoch=mEpoch.load(); e.foot=true; e.clip=surface*FootVariants+take;
        e.pitch=0.985f+0.03f*Random(); e.pan=mLeftFoot?-0.08f:0.08f;
        e.gain=gain*std::sqrt((layer==0?first:other)/(first+other));
        // Damp a wet sole gently; rain does not imply a puddle or change the material into mud.
        e.cutoff=18000.0f-6000.0f*Clamp(contact.wetness);
        Push(e);
    }
}

void WorldAudio::Update(const WorldSound& s,float dt) {
    const float fields[TargetCount]={s.wind,s.leaves,s.rain,s.surf,s.birds,s.insects,s.frogs,s.presence,s.cockpit};
    for (unsigned i=0;i<TargetCount;++i) mTarget[i]=Clamp(fields[i]);
    for (int i=0;i<3;++i) { mPosition[i]=s.position[i]; mRight[i]=s.right[i]; mForward[i]=s.forward[i]; }
    mLastUpdate=GetTickCount64();
    if (s.presence<0.01f || dt<=0) return;
    auto animal=[&](unsigned clip,float level,float minDistance,float range) {
        const float angle=Random()*2*Pi, d=minDistance+range*Random();
        Event e; e.clip=clip; e.epoch=mEpoch.load(); e.gain=level; e.pitch=0.94f+Random()*0.12f;
        for (int i=0;i<3;++i) e.position[i]=s.position[i]+d*(std::cos(angle)*s.right[i]+std::sin(angle)*s.forward[i]);
        Push(e);
    };
    // Variable intervals include silence. A voice stays at its world position when the listener moves or turns.
    mBirdWait-=dt*s.birds;
    if (mBirdWait<=0) {
        unsigned clip=Bird0+unsigned(Random()*(BirdCount-1)); if (clip>=mLastBird) ++clip;
        mLastBird=clip; animal(clip,0.22f,12,28); mBirdWait=3+Random()*9;
    }
    mFrogWait-=dt*s.frogs;
    if (mFrogWait<=0) { animal(Frog,0.18f,8,18); mFrogWait=4+Random()*10; }
    mThunderWait-=dt*std::max(0.0f,(s.rain-0.55f)*2.0f);
    if (mThunderWait<=0) { animal(Thunder,0.32f,20,40); mThunderWait=25+Random()*40; }
}

void WorldAudio::Render(float* stereo,unsigned frames) {
    const bool alive=GetTickCount64()-mLastUpdate.load()<250;
    float target[TargetCount];
    for (unsigned i=0;i<TargetCount;++i) target[i]=alive?mTarget[i].load():0.0f;
    const float stepMix=mFootMix.load(), ambienceMix=mAmbienceMix.load();
    const unsigned epoch=mEpoch.load();
    for (auto& v:mVoices) if (v.active && (v.event.epoch!=epoch || !alive)) v.active=false;
    unsigned read=mRead.load(std::memory_order_relaxed);
    while (read!=mWrite.load(std::memory_order_acquire)) {
        const Event e=mQueue[read]; read=(read+1)%Queue;
        if (!alive || e.epoch!=epoch) continue;
        // Keep foot contacts audible under fauna; never steal another footstep to add an ambient call.
        Voice* slot=nullptr;
        for (auto& v:mVoices) if (!v.active) { slot=&v; break; }
        if (!slot && e.foot) for (auto& v:mVoices) if (!v.event.foot) { slot=&v; break; }
        if (slot) { *slot={}; slot->event=e; slot->active=true; }
    }
    mRead.store(read,std::memory_order_release);
    double pos[3]; float right[3],forward[3];
    for (int j=0;j<3;++j) { pos[j]=mPosition[j].load(); right[j]=mRight[j].load(); forward[j]=mForward[j].load(); }
    for (auto& v:mVoices) if (v.active) {
        float pan=v.event.pan, distance=1, front=1;
        if (!v.event.foot) {
            double d2=0; float side=0,ahead=0;
            for (int j=0;j<3;++j) { const double d=v.event.position[j]-pos[j]; d2+=d*d; side+=float(d)*right[j]; ahead+=float(d)*forward[j]; }
            distance=float(std::sqrt(d2)); pan=std::min(std::max(side/std::max(distance,1.0f),-0.92f),0.92f);
            front=ahead/std::max(distance,1.0f);
        }
        const float gain=v.event.gain*(v.event.foot?stepMix:ambienceMix*12.0f/std::max(distance,12.0f)*mLevel[Presence]);
        v.gain[0]=gain*std::sqrt(0.5f*(1-pan)); v.gain[1]=gain*std::sqrt(0.5f*(1+pan));
        const float cutoff=v.event.foot?v.event.cutoff:std::min(v.event.cutoff,12000.0f/(1+distance*0.015f))*(front<0?0.65f:1.0f);
        v.coefficient=Coefficient(cutoff);
    }
    constexpr double Tau=6.283185307179586;
    const float smooth=1-std::exp(-1.0f/(Rate*0.6f)), presenceSmooth=1-std::exp(-1.0f/(Rate*0.1f));
    const float kl=Coefficient(140),ka=Coefficient(1400),kleaf=Coefficient(5200),kwater=Coefficient(800);
    const float hull=Coefficient(1800+14000*(1-target[Cockpit]));
    for (unsigned i=0;i<frames;++i) {
        for (unsigned j=0;j<TargetCount;++j) mLevel[j]+=(target[j]-mLevel[j])*(j==Presence?presenceSmooth:smooth);
        if (++mControl>=4800) { mControl=0; mGustTarget=Noise(); mSurfTarget=Noise(); }
        mGust+=(mGustTarget-mGust)*0.000025f; mSurf+=(mSurfTarget-mSurf)*0.000006f;
        const float wind=mLevel[Wind]*(0.8f+0.3f*mGust), leaf=mLevel[Leaves]*(0.7f+0.4f*mGust);
        mInsectPhase=std::fmod(mInsectPhase+Tau*4100.0/Rate,Tau);
        mInsectPulse=std::fmod(mInsectPulse+Tau*27.3/Rate,Tau);
        const float insects=float(std::sin(mInsectPhase))*std::max(0.0f,float(std::sin(mInsectPulse)))*0.007f*mLevel[Insects];
        float out[2]={};
        for (int c=0;c<2;++c) {
            const float n=Noise(); mLow[c]+=(n-mLow[c])*kl; mAir[c]+=(n-mAir[c])*ka;
            mLeaf[c]+=(n-mLeaf[c])*kleaf; mWater[c]+=(n-mWater[c])*kwater;
            const float air=(mLow[c]*0.35f+mAir[c]*0.1f)*wind;
            const float rustle=(mLeaf[c]-mAir[c])*leaf*0.06f;
            const float rain=(n-mAir[c])*mLevel[Rain]*0.045f+mWater[c]*mLevel[Rain]*0.09f;
            const float surf=mWater[c]*mLevel[Surf]*(0.35f+0.18f*mSurf);
            out[c]=(air+rustle+rain+surf+insects)*mLevel[Presence]*ambienceMix;
        }
        for (auto& v:mVoices) if (v.active) {
            const auto& pcm=mClips[v.event.clip].samples;
            const size_t index=size_t(v.cursor);
            if (index+1>=pcm.size()) { v.active=false; continue; }
            const float sample=pcm[index]+(pcm[index+1]-pcm[index])*float(v.cursor-index);
            v.filter+=(sample-v.filter)*v.coefficient;
            out[0]+=v.filter*v.gain[0]; out[1]+=v.filter*v.gain[1];
            v.cursor+=v.event.pitch;
        }
        for (int c=0;c<2;++c) {
            mHull[c]+=(out[c]-mHull[c])*hull;
            stereo[2*i+c]+=mHull[c]*(1.0f-0.75f*mLevel[Cockpit]);
        }
    }
}
