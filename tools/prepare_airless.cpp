// Cook the distant proxy from the landing terrain itself; no independent lunar photograph.
#include "../MyPlanetEngine/AirlessTerrain.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <cstdio>
#include <filesystem>
int Cook(const std::filesystem::path& path,unsigned body) {
    constexpr unsigned Width=2048,Height=1024;
    constexpr double Pi=3.14159265358979323846;
    const auto surface=Airless::MoonSurface(body);
    std::vector<unsigned char> pixels(Width*Height*4);
    for(unsigned y=0;y<Height;++y)for(unsigned x=0;x<Width;++x) {
        const double latitude=Pi*(y+.5)/Height,longitude=2*Pi*((x+.5)/Width-.5);
        const Airless::Vec n={std::sin(latitude)*std::cos(longitude),std::cos(latitude),std::sin(latitude)*std::sin(longitude)};
        const Airless::Vec east={-std::sin(longitude),0,std::cos(longitude)},north=Airless::Cross(east,n);
        const auto normal=surface.Normal(n,surface.radius*Pi/Height);
        const double radial=std::max(.1,Airless::Dot(normal,n));
        const double values[]={255*surface.Albedo(n,surface.radius*Pi/Height)/.32,128-127*Airless::Dot(normal,east)/radial,
            128-127*Airless::Dot(normal,north)/radial,255};
        for(unsigned c=0;c<4;++c)pixels[4*(y*Width+x)+c]=(unsigned char)std::clamp(std::lround(values[c]),0L,255L);
    }
    std::ofstream out(path,std::ios::binary);if(!out)return 3;
    const auto header=Celestial::AtlasHeader(Celestial::Moons[body]);
    out.write(reinterpret_cast<const char*>(&header),sizeof(header));
    unsigned w=Width,h=Height;
    for(;;) {
        out.write(reinterpret_cast<const char*>(pixels.data()),pixels.size());
        if(w==1 && h==1)break;
        const unsigned nw=std::max(1u,w/2),nh=std::max(1u,h/2);std::vector<unsigned char> next(nw*nh*4);
        for(unsigned y=0;y<nh;++y)for(unsigned x=0;x<nw;++x)for(unsigned c=0;c<4;++c) {
            unsigned sum=0;for(unsigned dy=0;dy<2;++dy)for(unsigned dx=0;dx<2;++dx)
                sum+=pixels[4*(std::min(2*y+dy,h-1)*w+std::min(2*x+dx,w-1))+c];
            next[4*(y*nw+x)+c]=(unsigned char)((sum+2)/4);
        }
        pixels=std::move(next);w=nw;h=nh;
    }
    std::printf("Cooked %s: seed %u, radius %.0f m, 2048 x 1024 and twelve mip levels.\n",Celestial::Moons[body].id,surface.seed,surface.radius);
    std::fflush(stdout);
    return out?0:4;
}
int main(int argc,char** argv) {
    if(argc!=2)return 2;
    for(unsigned i=0;i<Celestial::Moons.size();++i) {
        const int result=Cook(std::filesystem::path(argv[1])/Celestial::Moons[i].atlas,i);
        if(result)return result;
    }
    return 0;
}
