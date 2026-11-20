// Focused behavioural checks. No renderer, GPU, audio device, or performance/quality benchmark.
#include "../../MyPlanetEngine/WalkController.h"
#include "../../MyPlanetEngine/WorldAudio.h"
#include "../../MyPlanetEngine/Audio.h"
#include "../../MyPlanetEngine/CelestialManifest.h"
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <memory>
#include <limits>

static void Require(bool ok,const char* message) { if (!ok) { std::fprintf(stderr,"FAIL: %s\n",message); std::exit(1); } }
static void ContactChecks() {
    auto bare=GroundContactWeights(0.6f,0.3f,0.1f,0,0,0,0);
    Require(FootContact(bare).Primary()==unsigned(FootSurface::Soil),"residual soil wins over a weaker grass share");
    auto rock=GroundContactWeights(0,1,0,1,1,0,0);
    Require(rock.rock==1&&rock.gravel==0&&rock.grass==0,"exposed rock covers scree and grass");
    auto gravel=GroundContactWeights(0,1,0,1,0,0,0);
    Require(gravel.gravel==1&&gravel.rock==0,"scree has a distinct loose contact");
    auto beach=GroundContactWeights(0,1,0,1,1,1,0);
    Require(beach.sand==1&&beach.rock==0&&beach.gravel==0,"beach sand covers the hard substrate");
    auto snow=GroundContactWeights(0,1,0,1,1,1,1);
    Require(snow.snow==1&&snow.sand==0&&snow.rock==0,"snow covers beach and rock");
    auto blend=GroundContactWeights(1,0,0,0,1,0,0.7f);
    Require(std::abs(blend.snow-0.7f)<1e-6&&std::abs(blend.rock-0.3f)<1e-6,"partial snow keeps the uncovered rock share");
    for(float snowPart:{0.0f,0.3f,1.0f}) for(float beachPart:{0.0f,0.6f,1.0f})
        for(float rockPart:{0.0f,0.4f,1.0f}) for(float screePart:{0.0f,0.7f,1.0f}) {
            FootContact c(GroundContactWeights(0.8f,0.5f,0.1f,screePart,rockPart,beachPart,snowPart));
            float sum=0; for(float share:c.shares) { Require(share>=0&&share<=1,"contact shares are bounded"); sum+=share; }
            Require(std::abs(sum-1)<1e-6,"coatings conserve the contact area");
        }
    FootContact invalid; invalid.shares[1]=std::numeric_limits<float>::quiet_NaN();
    Require(invalid.Primary()==FootContact::Count,"missing or invalid probes never invent soil");
    std::printf("Contacts: residual soil, rock/scree separation, sand/snow coverage and normalized transitions pass.\n");
}

static void WriteAudition(const std::wstring& path,const std::vector<float>& pcm) {
    FILE* file=nullptr; Require(_wfopen_s(&file,path.c_str(),L"wb")==0&&file,"audition file opens");
    const uint32_t bytes=uint32_t(pcm.size()*2), riff=36+bytes, format=16, rate=48000, byteRate=rate*4;
    const uint16_t kind=1,channels=2,align=4,bits=16;
    fwrite("RIFF",1,4,file); fwrite(&riff,4,1,file); fwrite("WAVEfmt ",1,8,file); fwrite(&format,4,1,file);
    fwrite(&kind,2,1,file); fwrite(&channels,2,1,file); fwrite(&rate,4,1,file); fwrite(&byteRate,4,1,file);
    fwrite(&align,2,1,file); fwrite(&bits,2,1,file); fwrite("data",1,4,file); fwrite(&bytes,4,1,file);
    for(float sample:pcm) { const int16_t value=int16_t(std::lround(std::min(std::max(sample,-1.0f),1.0f)*32767)); fwrite(&value,2,1,file); }
    fclose(file);
}
static void ImmersionChecks(const std::wstring& directory,const wchar_t* output) {
    WorldAudio baseline, repeated;
    baseline.Initialize(directory); repeated.Initialize(directory);
    WorldSound s;
    s.listener=SoundListener::Helmet;
    float a[960]={},b[960]={};
    double energy=0;
    for(unsigned block=0;block<290;++block) {
        baseline.Update(s,.01f); repeated.Update(s,.01f);
        if(block==10) { baseline.RequestRadio(); repeated.RequestRadio(); }
        if(block==35 || block==80) repeated.RequestRadio();
        std::fill(std::begin(a),std::end(a),0.0f); std::fill(std::begin(b),std::end(b),0.0f);
        baseline.Render(a,480); repeated.Render(b,480);
        Require(std::equal(std::begin(a),std::end(a),std::begin(b)),"a repeated radio command cannot restart or overlap speech");
        for(float v:a) energy+=v*v;
    }
    Require(std::sqrt(energy/(290*960))>.025,"a lunar headset plays the recorded breath and radio");
    auto engine=std::make_unique<Audio>(); // the XAudio2 output ring also exists when rendering offline
    Require(engine->Initialize(false),"production audio bank opens in the device-free mixer");
    std::vector<float> preview;
    float peak=0; double quiet=0,entry=0,forest=0;
    for(int block=0;block<2100;++block) {
        const float t=block*.01f;
        WorldSound scene;
        if(t<8) {
            scene.listener=SoundListener::Cockpit;
            scene.engine=.08f+.76f*std::min(t/4,1.0f);
            scene.flightDensity=std::min(1.0f,std::max(0.0f,(t-2)*.24f));
            scene.equivalentAirspeed=std::max(0.0f,(t-2)*66);
            scene.heat=std::min(1.0f,std::max(0.0f,(t-4)*.45f));
        } else if(t<11) {
            scene.listener=SoundListener::Chase;
            scene.engine=.85f; // no airborne transport outside the hull in vacuum
        } else {
            scene.listener=SoundListener::Helmet; scene.presence=1; scene.wind=.30f; scene.leaves=.74f;
            scene.exertion=t<16?.8f:.22f;
            if(block>=1120 && block<1600 && block%64==0) engine->Footstep(FootSurface::Grass);
            if(block==1550) engine->RequestRadio();
        }
        engine->SetMix(std::min(std::max(21-t,0.0f),1.0f),1,1,1);
        engine->Update(scene,.01f);
        engine->Render(a,480);
        for(float v:a) {
            Require(std::isfinite(v) && std::abs(v)<=1,"production immersion mix stays finite and bounded");
            peak=std::max(peak,std::abs(v));
            if(block>=660 && block<760) entry+=v*v;
            if(block>=1070 && block<1100) quiet+=v*v;
            if(block>=1400 && block<1500) forest+=v*v;
        }
        if(output) preview.insert(preview.end(),std::begin(a),std::end(a));
    }
    Require(std::sqrt(quiet/(30*960))<.0008,"chase vacuum silences a working reactor and entry air");
    Require(std::sqrt(entry/(100*960))>.025 && std::sqrt(forest/(100*960))>.004,"entry and a walking helmet yield audible mixes");
    if(output) WriteAudition(std::wstring(output)+L"\\immersion-vol-casque.wav",preview);
    std::printf("Immersion: radio retrigger, airless chase, cockpit entry, helmet foliage and complete mixer pass (peak %.3f).\n",peak);
}

struct Trial {
    Walker walker; double x=0,y=0,apex=0; unsigned steps=0; bool fell=false;
    std::function<double(double,double)> ground=[](double,double){return 10.0;};
    Trial() { walker.elevation=10; }
    void Frame(double dt,Walker::Input input) {
        WalkTerrain terrain;
        for(int j=0;j<WalkTerrain::Side;++j) for(int i=0;i<WalkTerrain::Side;++i)
            terrain.heights[j*WalkTerrain::Side+i]=float(ground(x+(i-4)*0.5,y+(j-4)*0.5));
        walker.x=walker.y=0; walker.Advance(dt,input,terrain);
        x+=walker.x; y+=walker.y; steps+=walker.steps;
        apex=std::max(apex,walker.elevation-10); fell|=!walker.grounded;
    }
    void Run(double seconds,int hz,Walker::Input input) { for(int i=0;i<int(seconds*hz);++i) Frame(1.0/hz,input); }
};

int wmain(int argc,wchar_t** argv) {
    ContactChecks();
    Trial idle; idle.Run(2,60,{}); Require(idle.steps==0&&idle.x==0,"idle has no footsteps or drift");
    Trial walk,diagonal,slow,fast;
    walk.Run(2,60,{1,0}); diagonal.Run(2,60,{1,1}); slow.Run(2,30,{1,0}); fast.Run(2,144,{1,0});
    Require(std::abs(walk.walker.vx-1.5)<0.001,"walking reaches 1.5 m/s");
    Require(std::abs(std::hypot(diagonal.x,diagonal.y)-walk.x)<0.01,"diagonal speed is normalized");
    Require(std::abs(slow.x-fast.x)<0.012,"movement is stable across frame rates");
    Require(walk.steps>=3&&walk.steps<=4,"footsteps follow distance");
    walk.Run(1,60,{}); const double rest=walk.x; walk.Run(1,60,{}); Require(walk.x-rest<0.001,"release brakes to rest");
    Trial run,crouch; run.Run(1,60,{1,0,true}); crouch.Run(1,60,{1,0,false,true});
    Require(idle.walker.exertion==0 && run.walker.exertion>3*crouch.walker.exertion,
        "helmet effort follows actual running and crouching speed");
    Require(std::abs(run.walker.vx-3.6)<0.001,"running reaches 3.6 m/s");
    Require(std::abs(crouch.walker.eye-1.05)<0.001&&crouch.walker.vx<0.751,"crouching lowers the eye and pace");
    Trial jump; jump.Frame(1.0/60,{0,0,false,false,true}); jump.Run(2,60,{});
    Require(jump.apex>0.75&&jump.apex<0.83,"jump follows gravity with an approximately 0.8 m apex");
    Require(jump.walker.grounded&&std::abs(jump.walker.elevation-10)<0.001&&jump.steps==0,"landing settles without airborne footsteps");
    Trial lunarJump;lunarJump.walker.gravity=1.62;
    lunarJump.Frame(1.0/60,{0,0,false,false,true});lunarJump.Run(6,60,{});
    Require(lunarJump.apex>4.85 && lunarJump.apex<5.0 && lunarJump.walker.grounded,"airless gravity gives a longer jump and a stable landing");
    for(const auto& body:Celestial::Moons) {
        Trial bodyJump;bodyJump.walker.gravity=body.gravity;
        bodyJump.Frame(1.0/60,{0,0,false,false,true});bodyJump.Run(2*4.0/body.gravity+1,60,{});
        const double expected=4.0*4.0/(2*body.gravity);
        Require(std::abs(bodyJump.apex-expected)<.08 && bodyJump.walker.grounded,"each manifest's gravity gives the expected ballistic arc and landing");
    }
    Trial lunarCrater;lunarCrater.ground=[](double,double){return -500.0;};lunarCrater.walker.elevation=-500;
    lunarCrater.walker.gravity=1.62;lunarCrater.walker.waterFloor=-1e10;lunarCrater.Run(2,60,{1,0});
    Require(lunarCrater.x>2.7 && lunarCrater.walker.elevation==-500,"an airless crater below the datum is walkable dry ground");
    for(int hz:{30,60,240}) {
        Trial wall; wall.ground=[](double x,double){return 10+3*std::max(x-0.5,0.0);};
        wall.Run(2,hz,{1,0}); Require(wall.x<0.55&&wall.walker.elevation<10.06,"steep ascent blocks at every frame rate");
        const unsigned contacts=wall.steps; const float effort=wall.walker.exertion;
        wall.Run(1,hz,{1,0}); Require(wall.steps==contacts,"pushing a wall emits no footsteps");
        Require(wall.walker.exertion<effort,"effort recovers while held controls are blocked by terrain");
    }
    Trial slope; slope.ground=[](double x,double){return 10+0.5*x;}; slope.Run(1,60,{1,0});
    Require(slope.x>1.2&&std::abs(slope.walker.elevation-slope.ground(slope.x,slope.y))<0.001,"walkable slope remains grounded");
    Trial shore; shore.ground=[](double x,double){return 10-20*std::max(x-0.5,0.0);}; shore.Run(2,60,{1,0});
    Require(shore.x<1.01&&shore.walker.elevation>=0.15,"submerged ground cannot become a walking surface");
    if(argc>1) {
        WorldAudio audio; audio.Initialize(argv[1]); WorldSound sound; sound.presence=1;
        WorldAudio wet; wet.Initialize(argv[1]); wet.SetMix(1,0);
        audio.SetMix(1,0);
        float pcm[960*2]={}, damp[960*2]={};
        const wchar_t* names[]={L"terre",L"herbe",L"gravier",L"roche",L"sable",L"neige"};
        for(unsigned surface=0;surface<FootContact::Count;++surface) {
            double energy=0,wetEnergy=0,cross=0; float peak=0;
            std::vector<float> audition;
            for(int take=0;take<6;++take) {
              audio.Update(sound,0.02f); audio.Step(FootSurface(surface));
              FootContact contact{FootSurface(surface)}; contact.wetness=1;
              wet.Update(sound,0.02f); wet.Step(contact);
              for(int block=0;block<32;++block) {
                std::fill(std::begin(pcm),std::end(pcm),0.0f); audio.Update(sound,0.02f); audio.Render(pcm,960);
                std::fill(std::begin(damp),std::end(damp),0.0f); wet.Update(sound,0.02f); wet.Render(damp,960);
                for(unsigned j=0;j<960*2;++j) {
                    Require(std::isfinite(pcm[j])&&std::isfinite(damp[j]),"audio samples stay finite");
                    energy+=pcm[j]*pcm[j]; wetEnergy+=damp[j]*damp[j]; cross+=pcm[j]*damp[j]; peak=std::max(peak,std::abs(pcm[j]));
                }
                audition.insert(audition.end(),std::begin(pcm),std::end(pcm));
              }
            }
            Require(energy>0.1&&peak<1.0f,"each material produces audible bounded PCM");
            Require(cross/std::sqrt(energy*wetEnergy)>0.95,"rain dampens the same material instead of replacing it with mud");
            if(argc>2) WriteAudition(std::wstring(argv[2])+L"\\pas-"+names[surface]+L".wav",audition);
        }
        audio.Reset(); audio.Update(sound,0.02f); audio.Step(FootContact{});
        std::fill(std::begin(pcm),std::end(pcm),0.0f); audio.Render(pcm,960);
        for(float f:pcm) Require(std::abs(f)<1e-6,"an unavailable contact emits no fallback step");
        FootContact transition(GroundContactWeights(0,1,0,0,1,0,0.6f));
        audio.Step(transition,1.8f);
        double blendedEnergy=0;
        for(int block=0;block<32;++block) {
            std::fill(std::begin(pcm),std::end(pcm),0.0f); audio.Update(sound,0.02f); audio.Render(pcm,960);
            for(float f:pcm) { Require(std::isfinite(f)&&std::abs(f)<1,"mixed coatings remain unclipped"); blendedEnergy+=f*f; }
        }
        Require(blendedEnergy>0.1,"a mixed snow/rock contact remains audible");
        audio.SetMix(1,1);
        audio.Reset(); sound={}; audio.Update(sound,0.02f);
        for(int i=0;i<80;++i) { std::fill(std::begin(pcm),std::end(pcm),0.0f); audio.Update(sound,0.02f); audio.Render(pcm,960); }
        for(float f:pcm) Require(std::abs(f)<1e-6,"teleport to vacuum discards old sounds");
        sound.presence=1; sound.wind=sound.leaves=sound.rain=sound.surf=sound.birds=sound.insects=sound.frogs=1;
        for(int block=0;block<250;++block) {
            std::fill(std::begin(pcm),std::end(pcm),0.0f); audio.Update(sound,0.02f); audio.Render(pcm,960);
            for(float f:pcm) Require(std::isfinite(f)&&std::abs(f)<1,"combined environmental layers remain finite and unclipped");
        }
        audio.SetMix(0,0); audio.Reset();
        std::fill(std::begin(pcm),std::end(pcm),0.0f); audio.Step(FootSurface::Gravel); audio.Update(sound,0.02f); audio.Render(pcm,960);
        for(int i=0;i<50;++i) { std::fill(std::begin(pcm),std::end(pcm),0.0f); audio.Update(sound,0.02f); audio.Render(pcm,960); }
        for(float f:pcm) Require(std::abs(f)<1e-6,"independent category gains mute the mix");
        std::printf("Audio: six distinct banks, wet/dry contacts, mixed coatings, habitat, teleport reset and independent gains pass.\n");
        ImmersionChecks(argv[1],argc>2?argv[2]:nullptr);
    }
    std::printf("Walking: idle, pace, diagonals, frame rates, steps, crouch, gravity, slopes, wall and water checks pass.\n");
}
