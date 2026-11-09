// Native audio behaviour and preview using exactly the production synth; no device or GPU.
#include "../../MyPlanetEngine/NavigatorSound.h"
#include <vector>
#include <fstream>
#include <iostream>
#include <cassert>
#include <cstring>

static void Wav(const char* path, const std::vector<float>& x) {
    std::ofstream f(path, std::ios::binary);
    auto u32 = [&](uint32_t v) { f.write((char*)&v, 4); };
    auto u16 = [&](uint16_t v) { f.write((char*)&v, 2); };
    f.write("RIFF",4); u32(uint32_t(x.size()*2+36)); f.write("WAVEfmt ",8); u32(16);
    u16(1); u16(2); u32(48000); u32(192000); u16(4); u16(16); f.write("data",4); u32(uint32_t(x.size()*2));
    for (float v : x) { const int16_t s=int16_t(std::round(std::tanh(v*.7f)*32766)); f.write((char*)&s,2); }
    assert(f.good());
}
int main(int argc, char** argv) {
    assert(argc==2);
    NavigatorSound whole, chunked;
    NavigatorSound::Controls c; c.power=.6f; c.wind=100;
    std::vector<float> a(48000*2), b(a.size());
    whole.Render(a.data(),48000,c);
    for (unsigned at=0; at<48000;) { unsigned n=std::min(127u,48000-at); chunked.Render(b.data()+2*at,n,c); at+=n; }
    assert(std::memcmp(a.data(),b.data(),a.size()*sizeof(float))==0); // callback size cannot change synthesis
    NavigatorSound sound;
    std::vector<float> preview(36*48000*2);
    double peak=0, energy=0;
    for (unsigned block=0; block<36*100; ++block) {
        const float t=block*.01f;
        c={}; c.power=.025f;
        if(t>=5 && t<10) { c.power=.025f+.975f*(t-5)/5; c.wind=150*(t-5)/5; }
        if(t>=10 && t<20) { c.power=.95f; c.wind=150; }
        if(t>=15 && t<20) { c.roll=std::sin((t-15)*2); c.lift=.7f; }
        if(t>=20 && t<24) { c.power=0; c.wind=150*(24-t)/4; }
        if(t>=28 && t<32) { c.inside=false; c.power=.6f; c.wind=140; }
        if(t>=32) c.active=false;
        sound.Render(preview.data()+block*480*2,480,c);
    }
    for(float v:preview) { assert(std::isfinite(v)); peak=std::max(peak,double(std::abs(v))); energy+=v*v; }
    assert(peak<.95 && peak>.05 && energy>10);
    double tail=0; for(unsigned i=35*48000*2;i<preview.size();++i) tail+=preview[i]*preview[i];
    assert(std::sqrt(tail/(48000*2))<1e-5);
    NavigatorSound vacuum;
    c={}; c.air=0; c.inside=false; c.power=1;
    std::vector<float> silence(5*48000*2); vacuum.Render(silence.data(),5*48000,c);
    double last=0; for(unsigned i=4*48000*2;i<silence.size();++i) last+=silence[i]*silence[i];
    assert(std::sqrt(last/(48000*2))<1e-5);
    Wav(argv[1],preview);
    std::cout<<"Navigator sound: callback invariance, finite output, bounded peak, stopped tail and exterior vacuum passed.\n"
             <<"Raw peak "<<peak<<", RMS "<<std::sqrt(energy/preview.size())<<"; preview "<<argv[1]<<"\n";
}
