// Acoustic contact areas, in the same order as SurfaceWeights. A contact may straddle two visible materials.
#pragma once
#include <array>
#include <cmath>
#include "SurfaceWeights.hlsli"
enum class FootSurface { Soil, Grass, Gravel, Rock, Sand, Snow, Count };
struct FootContact {
    static constexpr unsigned Count=unsigned(FootSurface::Count);
    std::array<float,Count> shares = {};
    float wetness=0.0f;
    FootContact() = default;
    explicit FootContact(FootSurface surface) { if (unsigned(surface)<Count) shares[unsigned(surface)]=1.0f; }
    explicit FootContact(const SurfaceWeights& w) : shares{{w.soil,w.grass,w.gravel,w.rock,w.sand,w.snow}} {}
    // Return Count for an unavailable probe; never invent a sound while the contact data is invalid.
    unsigned Primary() const {
        unsigned result=Count; float largest=0;
        for (unsigned i=0;i<Count;++i) if (std::isfinite(shares[i]) && shares[i]>largest) { largest=shares[i]; result=i; }
        return result;
    }
};
