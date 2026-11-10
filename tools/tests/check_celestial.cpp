// Functional invariants of the actual system model; no GPU or performance measurements.
#include "../../MyPlanetEngine/CelestialSystem.h"
#include <cassert>
#include <iostream>
int main() {
    using namespace Celestial;
    assert(std::abs(Phase(1)-1)<1e-12);
    assert(Phase(-1)<1e-12);
    assert(std::abs(Phase(0)-1/Pi)<1e-12);
    // Integrate the actual shader's surface law over the projected disc, independently of its analytic flux.
    for(double phase:{0.0,Pi/3,2*Pi/3}) {
        double average=0;
        for(unsigned r=0;r<320;++r)for(unsigned a=0;a<720;++a) {
            const double radial=std::sqrt((r+.5)/320),mu=std::sqrt(1-radial*radial),angle=2*Pi*(a+.5)/720;
            const double mu0=radial*std::cos(angle)*std::sin(phase)+mu*std::cos(phase);
            average+=AirlessDiffuse(float(mu0),float(mu));
        }
        assert(std::abs(average/(320*720)-AirlessDisc(std::cos(phase)))<.003);
    }
    const Vector sun={AU,0,0};
    assert(Eclipse({-280000,0,0},sun)<1e-12);
    assert(Eclipse({280000,0,0},sun)>1-1e-12);
    assert(Eclipse({-280000,50000,0},sun)>1-1e-12);
    double previous=0;
    for(unsigned k=0;k<=1000;++k) {
        double e=Eclipse({-280000,6000+k*2.0,0},sun);
        assert(std::isfinite(e) && e>=previous-1e-10 && e<=1.0);
        previous=e;
    }
    assert(previous>0.999);
    const auto system=System(0,{1,0,0});
    const auto later=System(86400,{1,0,0});
    for (const auto& epoch : {system, later}) {
        assert(NearestOrbitBody(epoch, {PlanetRadius+400,0,0}) == Exolune);
        assert(NearestOrbitBody(epoch, epoch[Sun].position) != int(Sun));
        for (unsigned i=0; i<Sun; ++i) {
            const auto& body = epoch[i];
            assert(NearestOrbitBody(epoch, body.position+Vector{0,body.radius+800,0}) == int(i));
        }
    }
    for(unsigned i=0;i<BodyCount;++i) {
        const auto& b=system[i];
        assert(b.radius>0 && Length(b.position)>PlanetRadius+b.radius);
        assert(b.sunlight>=0 && std::isfinite(b.sunlight));
        const auto flux=Illuminance(b,{0,0,0});
        assert(flux.x>=0 && std::isfinite(flux.x));
        if(i<MoonCount) {
            assert(std::abs(b.radius*1000-Moons[i].radius)<1e-6);
            const auto full=Illuminance(b,b.position+b.toSun*(100*b.radius));
            assert(std::abs(full.x-b.albedo.x*Pi*b.sunlight/10000*AirlessDisc(1))<1e-12);
            assert(std::abs(Length(later[i].position)-Length(b.position))<1e-6);
            assert(Length(later[i].position-b.position)>1000);
        }
    }
    Body witness={{0,0,0},{.2,.2,.2},{1,0,0},100,1,0};
    const auto close=Illuminance(witness,{10000,0,0}),far=Illuminance(witness,{20000,0,0});
    assert(std::abs(close.x/far.x-4)<1e-12);
    assert(Illuminance(witness,{-10000,0,0}).x<1e-20);
    const Vector a={system[0].position.x*.90,system[0].position.y*.90,system[0].position.z*.90};
    const Vector b=a+Vector{1000,0,0};
    assert(Length(Unit(system[0].position-a)-Unit(system[0].position-b))>0.001);
    std::cout<<"PASS: phase, finite solar penumbra, circular orbits, inverse-square flux, parallax and camera targets\n";
}
