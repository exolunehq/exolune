// Climate.cpp - a body's climate (Climate.h; docs/spec-climat.md). Exolune's own code, written from the spec and the papers
// it cites. The moisture and the sea air are carried by the winds to their steady state on a cube of a quarter of the map's
// resolution, then of half; the map's own resolution then gives the slopes their share of the rain. Deterministic: every
// pass computes each cell from the previous pass alone, whatever the threads. Compiled optimised even in Debug
// (MyPlanetEngine.vcxproj).
#include "Climate.h"
#include "Tectonics.h"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <functional>
#include <thread>
#include <immintrin.h>

namespace Climate
{
    namespace
    {
        const float kPi = 3.14159265f, kDay = 86400.0f;
        const uint32_t kTransport = Size / 2; // the winds' cube: 100 km at a face's centre
        // The circulation's three cells (Hadley, Ferrel, polar), their surface winds by latitude (m/s): the trades, the
        // westerlies, the polar easterlies; the Hadley cell's return flow converging within kItczWidth degrees of the
        // thermal equator, diverging from 12 to 30 degrees, where the deserts lie; the thermal equator kItczShift degrees
        // into the summer hemisphere. Earth's annual means (Peixoto and Oort 1992, Physics of Climate, chapter 7).
        const float kTrades = 6.5f, kWesterlies = 8.0f, kPolar = 3.5f;
        const float kHadley = 3.5f, kFerrel = 1.2f, kPolarCell = 1.0f, kItczWidth = 4.0f, kItczShift = 7.0f;
        const float kFriction = 0.25f; // the surface wind this much slower over land
        // The thermal lows and highs: the season's temperature departure from its latitude's mean, smoothed over about
        // 1 500 km, drives a wind kMonsoon m/s per K/m down its gradient, turned towards the isobars by the Coriolis force,
        // 55 degrees past the tropics, kMonsoonMax m/s at most.
        const float kMonsoon = 6e5f, kMonsoonMax = 5.0f;
        // The moisture (Climate::Build): the sea's column relaxes in kEvaporation to kSeaHumidity of its saturated column;
        // it rains in kResidence over the air's large-scale ascent factor, kAscent the convergence that triples it; lifted
        // up a slope, the share kOrographic of what the lift condenses; lowered, the rain fades over kLee m/s of descent.
        // Over the ground, the column holds what its air can above it, its vapour fading over kVapourHeight; the low flow,
        // blocked by the ranges (Froude numbers well under 1, Smith 1979), rises over kBlocking of their height on the mean,
        // the rest of it going round; what the column cannot hold rains in kExcess. A share kRecycling of the rain on warm
        // land evaporates again (Eltahir and Bras 1996: a quarter to a third).
        const float kEvaporation = 1.0f * kDay, kSeaHumidity = 0.5f, kResidence = 7.0f * kDay, kAscent = 1.5e-6f, kAscentMax = 1.5f;
        const float kOrographic = 0.2f, kLee = 0.03f, kRecycling = 0.35f, kVapourHeight = 2200.0f, kBlocking = 0.5f, kExcess = 0.2f * kDay;
        const float kEddies = 6e5f; // m2/s, the eddies' mixing of the moisture, strongest in the storm tracks near 50 degrees
        // The sea air (continentality): it fades over land in kInland, and across a mountain range over kBarrier m of rise.
        const float kInland = 4.0f * kDay, kBarrier = 1500.0f, kSeaAir = 0.3f * kDay, kAirMixing = 3e5f;
        // The cold currents: the Ekman transport offshore, wind driven, kUpwelling C colder at most, carried inland as the
        // sea air is, fading in kCoastal. Only a steady wind wells water up: the trades blow from one quarter 80 % of the time,
        // the westerlies far less; the great upwellings lie under the trades and the subtropical highs, 10 to 40 degrees.
        const float kUpwelling = 6.0f, kCoastal = 1.5f * kDay;
        // The temperatures (C): the planet's zonal law, 28 at the equator to -24 at the poles (Materials.hlsli before the
        // map); the seasons' half amplitude over the sea, and over land at the mean continentality kInlandMean the fit on
        // the Earth's land, TerraClimate 1991-2020 (tools/saisons_terre.py); the interiors colder at high latitudes.
        const float kZonal[2] = { 28.0f, 52.0f }, kSeaSeasons[2] = { 1.0f, 5.0f }, kLandSeasons[2] = { 3.5f, 18.0f };
        const float kInlandMean = 0.6f, kInlandCold = 12.0f;

        struct V3 { float x, y, z; };
        V3 operator+(V3 a, V3 b) { return { a.x + b.x, a.y + b.y, a.z + b.z }; }
        V3 operator-(V3 a, V3 b) { return { a.x - b.x, a.y - b.y, a.z - b.z }; }
        V3 operator*(V3 a, float s) { return { a.x * s, a.y * s, a.z * s }; }
        float Dot(V3 a, V3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
        V3 Cross(V3 a, V3 b) { return { a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x }; }
        float Length(V3 a) { return std::sqrt(Dot(a, a)); }
        V3 Normalize(V3 a) { return a * (1.0f / Length(a)); }
        float Sat(float x) { return std::min(std::max(x, 0.0f), 1.0f); }
        float Bell(float x, float centre, float width) { const float u = (x - centre) / width; return std::exp(-u * u); }
        float Radians(float degrees) { return degrees * (kPi / 180.0f); }
        // The angle between two unit vectors, precise when small.
        float Angle(V3 a, V3 b) { return std::atan2(Length(Cross(a, b)), Dot(a, b)); }
        // The area of the spherical triangle abc (Van Oosterom and Strackee 1983).
        float Triangle(V3 a, V3 b, V3 c)
        {
            return 2.0f * std::atan2(std::fabs(Dot(a, Cross(b, c))), 1.0f + Dot(a, b) + Dot(b, c) + Dot(c, a));
        }

        // f(c) for every cell, on all the processor's threads: each cell's result must depend on that cell alone.
        template <class F> void ForCells(uint32_t cells, const F& f)
        {
            const uint32_t threads = std::max(1u, std::thread::hardware_concurrency());
            std::vector<std::thread> pool;
            for (uint32_t t = 0; t < threads; ++t)
                pool.emplace_back([&f, cells, threads, t] {
                    const uint32_t end = uint32_t(uint64_t(cells) * (t + 1) / threads);
                    for (uint32_t c = uint32_t(uint64_t(cells) * t / threads); c < end; ++c) f(c);
                });
            for (std::thread& thread : pool) thread.join();
        }

        // Independent jobs, each on its own thread.
        void Together(const std::vector<std::function<void()>>& jobs)
        {
            std::vector<std::thread> pool;
            for (const auto& job : jobs) pool.emplace_back(job);
            for (std::thread& thread : pool) thread.join();
        }

        // `rounds` rounds of f(c, round) for every cell on up to 8 threads, shared by `together` such loops at once, each
        // round's results depending on the previous round's alone: the threads started once and held together between the
        // rounds.
        template <class F> void ForRounds(uint32_t cells, int rounds, const F& f, uint32_t together = 1)
        {
            const uint32_t threads = std::max(1u, std::min(8u, std::max(1u, std::thread::hardware_concurrency())) / together);
            std::atomic<uint32_t> arrived{ 0 };
            std::vector<std::thread> pool;
            for (uint32_t t = 0; t < threads; ++t)
                pool.emplace_back([&, t] {
                    const uint32_t begin = uint32_t(uint64_t(cells) * t / threads), end = uint32_t(uint64_t(cells) * (t + 1) / threads);
                    for (int r = 0; r < rounds; ++r) {
                        for (uint32_t c = begin; c < end; ++c) f(c, r);
                        arrived.fetch_add(1);
                        while (arrived.load() < (r + 1) * threads) std::this_thread::yield();
                    }
                });
            for (std::thread& thread : pool) thread.join();
        }

        // Four cells and their bilinear weights.
        struct Taps { uint32_t cell[4]; float weight[4]; };

        // A cube of n x n cells per face, D3D's cube map layout: where a direction falls on it.
        struct Faces
        {
            uint32_t n;
            float Coordinate(int i) const { return (i + 0.5f) * 2.0f / n - 1.0f; }
            // The direction of the point (s, t) of face f, not normalised; s and t past [-1, 1] go beyond the face's edge.
            static V3 Direction(uint32_t f, float s, float t)
            {
                const V3 table[6] = { { 1.0f, -t, -s }, { -1.0f, -t, s }, { s, 1.0f, t }, { s, -1.0f, -t }, { s, -t, 1.0f }, { -s, -t, -1.0f } };
                return table[f];
            }
            // The face holding direction d, D3D's choice for a cube map, and d's texel coordinates on it: texel i's centre at i.
            void Locate(V3 d, uint32_t& f, float& x, float& y) const
            {
                const float ax = std::fabs(d.x), ay = std::fabs(d.y), az = std::fabs(d.z);
                float ma, sc, tc;
                if (ax >= ay && ax >= az) f = d.x > 0.0f ? 0 : 1, ma = ax, sc = d.x > 0.0f ? -d.z : d.z, tc = -d.y;
                else if (ay >= az)        f = d.y > 0.0f ? 2 : 3, ma = ay, sc = d.x, tc = d.y > 0.0f ? d.z : -d.z;
                else                      f = d.z > 0.0f ? 4 : 5, ma = az, sc = d.z > 0.0f ? d.x : -d.x, tc = -d.y;
                x = (sc / ma + 1.0f) * 0.5f * n - 0.5f;
                y = (tc / ma + 1.0f) * 0.5f * n - 0.5f;
            }
            uint32_t CellOf(V3 d) const
            {
                uint32_t f;
                float x, y;
                Locate(d, f, x, y);
                auto texel = [&](float v) { return (uint32_t)std::fmin(std::fmax(std::floor(v + 0.5f), 0.0f), n - 1.0f); };
                return (f * n + texel(y)) * n + texel(x);
            }
            // The bilinear taps at direction d on the face holding it, the texels past its edge taken on the next face.
            Taps Bilinear(V3 d) const
            {
                uint32_t f;
                float x, y;
                Locate(d, f, x, y);
                const float fx = std::floor(x), fy = std::floor(y), u = x - fx, v = y - fy;
                Taps taps;
                for (int k = 0; k < 4; ++k) {
                    const int ii = int(fx) + (k & 1), jj = int(fy) + (k >> 1);
                    taps.cell[k] = ii >= 0 && jj >= 0 && ii < int(n) && jj < int(n) ? (f * n + jj) * n + ii
                                 : CellOf(Direction(f, Coordinate(ii), Coordinate(jj)));
                    taps.weight[k] = ((k & 1) ? u : 1.0f - u) * ((k >> 1) ? v : 1.0f - v);
                }
                return taps;
            }
        };

        // The cube and what the winds need of it: each cell's centre, its area, its east and north, and its four edges,
        // exact on the sphere, with the neighbour beyond each.
        struct Grid : Faces
        {
            uint32_t cells;
            std::vector<V3> p, east, north;
            std::vector<float> area, latitude;     // m2, degrees
            std::vector<uint32_t> next;             // per cell, its neighbours beyond its edges: +s, -s, +t, -t
            std::vector<V3> normal;                 // per edge, its unit normal towards the neighbour, tangent to the sphere
            std::vector<float> length, distance;    // per edge, its length and the distance between the centres (m)

            Grid(uint32_t size, float radius) : Faces{ size }, cells(6 * size * size), p(cells), east(cells), north(cells), area(cells),
                latitude(cells), next(4 * cells), normal(4 * cells), length(4 * cells), distance(4 * cells)
            {
                const float h = 1.0f / n;
                ForCells(cells, [&](uint32_t c) {
                    const uint32_t f = c / (n * n), j = c / n % n, i = c % n;
                    const float s = Coordinate(i), t = Coordinate(j);
                    p[c] = Normalize(Direction(f, s, t));
                    east[c] = Normalize({ -p[c].z, 0.0f, p[c].x });
                    north[c] = Cross(east[c], p[c]);
                    latitude[c] = std::asin(std::min(std::max(p[c].y, -1.0f), 1.0f)) * (180.0f / kPi);
                    auto corner = [&](float ds, float dt) { return Normalize(Direction(f, s + ds, t + dt)); };
                    const V3 c00 = corner(-h, -h), c10 = corner(h, -h), c11 = corner(h, h), c01 = corner(-h, h);
                    area[c] = (Triangle(c00, c10, c11) + Triangle(c00, c11, c01)) * radius * radius;
                    const V3 edges[4][2] = { { c10, c11 }, { c00, c01 }, { c01, c11 }, { c00, c10 } };
                    const int steps[4][2] = { { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 } };
                    for (int q = 0; q < 4; ++q) {
                        const int ii = int(i) + steps[q][0], jj = int(j) + steps[q][1];
                        const uint32_t k = ii >= 0 && jj >= 0 && ii < int(n) && jj < int(n) ? (f * n + jj) * n + ii
                                         : CellOf(Direction(f, Coordinate(ii), Coordinate(jj)));
                        next[4 * c + q] = k;
                        const V3 a = edges[q][0], b = edges[q][1];
                        V3 m = Normalize(Cross(a, b));
                        if (Dot(m, Normalize(Direction(k / (n * n), Coordinate(k % n), Coordinate(k / n % n))) - p[c]) < 0.0f) m = m * -1.0f;
                        normal[4 * c + q] = m;
                        length[4 * c + q] = Angle(a, b) * radius;
                    }
                });
                ForCells(cells, [&](uint32_t c) {
                    for (int q = 0; q < 4; ++q) distance[4 * c + q] = Angle(p[c], p[next[4 * c + q]]) * radius;
                });
            }
            // The gradient of x at cell c, tangent to the sphere (per m): the mean over its edges (Green and Gauss).
            V3 Gradient(const std::vector<float>& x, uint32_t c) const
            {
                V3 g = { 0.0f, 0.0f, 0.0f };
                for (int q = 0; q < 4; ++q)
                    g = g + normal[4 * c + q] * (length[4 * c + q] * 0.5f * (x[c] + x[next[4 * c + q]]));
                g = g * (1.0f / area[c]);
                return g - p[c] * Dot(g, p[c]);
            }
            // The fields smoothed over about a cell per pass: each cell half its own, half its neighbours' mean.
            std::vector<float> Blur(std::vector<float> x, int passes) const
            {
                std::vector<float> y(cells);
                ForRounds(cells, passes, [&](uint32_t c, int r) {
                    const std::vector<float>& from = r & 1 ? y : x;
                    std::vector<float>& to = r & 1 ? x : y;
                    const uint32_t* k = &next[4 * c];
                    to[c] = 0.5f * from[c] + 0.125f * ((from[k[0]] + from[k[1]]) + (from[k[2]] + from[k[3]]));
                });
                return passes & 1 ? y : x;
            }
            V3 Wind(float towardsEast, float towardsNorth, uint32_t c) const { return east[c] * towardsEast + north[c] * towardsNorth; }
        };

        // The steady state of dx/dt = -div(U x) + div(D cap grad(x / cap)) + source - rate x, on the grid: upwind fluxes
        // through the cells' edges, the edge's wind the mean of its two cells'; the mixing on x / cap, through the smaller
        // cap of the two, so that it never carries moisture up a slope the wind could not. Pseudo-time steps local to each
        // cell, the largest its outflow allows: the steady state does not depend on them. local(c, x) gives the source and
        // the rate at c, from x at the previous round. `together`: how many transports run at once.
        template <class Local> std::vector<float> Transport(const Grid& g, const std::vector<V3>& wind, const std::vector<float>& mixing,
                                                            const std::vector<float>& cap, std::vector<float> x, int rounds, const Local& local,
                                                            uint32_t together = 1)
        {
            // Each round: x_c (1 - step outflow) plus step times the inflow from each neighbour, weight[e] x_k, and the source.
            std::vector<float> weight(4 * g.cells), keep(g.cells), step(g.cells);
            ForCells(g.cells, [&](uint32_t c) {
                float out = 0.0f, mix[4];
                for (int q = 0; q < 4; ++q) {
                    const uint32_t e = 4 * c + q, k = g.next[e];
                    const float across = g.length[e] / g.area[c], u = 0.5f * Dot(wind[c] + wind[k], g.normal[e]);
                    mix[q] = 0.5f * (mixing[c] + mixing[k]) * across / g.distance[e] * std::min(cap[c], cap[k]);
                    weight[e] = std::max(-u, 0.0f) * across + mix[q] / cap[k];
                    out += std::max(u, 0.0f) * across + mix[q] / cap[c];
                }
                step[c] = std::min(0.9f / (out + 1e-12f), 2.0f * kDay);
                keep[c] = 1.0f - step[c] * out;
                for (int q = 0; q < 4; ++q) weight[4 * c + q] *= step[c];
            });
            std::vector<float> y(g.cells);
            ForRounds(g.cells, rounds, [&](uint32_t c, int r) {
                const std::vector<float>& from = r & 1 ? y : x;
                std::vector<float>& to = r & 1 ? x : y;
                const uint32_t* k = &g.next[4 * c];
                const float* w = &weight[4 * c];
                const float sum = (w[0] * from[k[0]] + w[1] * from[k[1]]) + (w[2] * from[k[2]] + w[3] * from[k[3]]);
                float source, rate;
                local(c, from[c], source, rate);
                to[c] = (keep[c] * from[c] + sum + step[c] * source) / (1.0f + step[c] * rate);
            }, together);
            return rounds & 1 ? y : x;
        }

        // The circulation's surface wind (m/s, towards the east and the north) at `latitude`, the thermal equator at `shift`.
        void CellWind(float latitude, float shift, float& towardsEast, float& towardsNorth)
        {
            const float c = std::cos(Radians(latitude)), psi = latitude - shift * c * c, a = std::fabs(psi), side = psi < 0.0f ? -1.0f : 1.0f;
            towardsEast = -(a < 30.0f ? kTrades : a < 60.0f ? kWesterlies : kPolar) * std::sin(Radians(6.0f * a));
            const float x = Sat((a - 12.0f) / 18.0f);
            towardsNorth = a < 30.0f ? -kHadley * std::tanh(psi / kItczWidth) * (1.0f - x * x * (3.0f - 2.0f * x))
                         : a < 60.0f ? kFerrel * side * std::sin(Radians(6.0f * (a - 30.0f)))
                                     : -kPolarCell * side * std::sin(Radians(6.0f * (a - 60.0f)));
        }

        // The wind (towards the east and the north) turned clockwise by `angle` (radians), as on a map, north up.
        void Turn(float& e, float& n, float angle)
        {
            const float c = std::cos(angle), s = std::sin(angle), e0 = e;
            e = e0 * c + n * s;
            n = -e0 * s + n * c;
        }

        // The saturated column of water vapour over a surface at t (C), mm: 65 at 28 C, 6 % more per degree (Clausius and
        // Clapeyron at the lower troposphere's temperatures).
        float Saturated(float t) { return 65.0f * std::exp(0.06f * (t - 28.0f)); }

        float Zonal(float sinLatitude) { return kZonal[0] - kZonal[1] * sinLatitude * sinLatitude; }

        // The year's mean temperature at sea level (C): the zonal law, the cold currents' cooling over the sea, the cold sea
        // air carried over the land (coldAir), the interiors colder at high latitudes.
        float YearTemperature(float sinLatitude, float landShare, float inland, float cold, float coldAir)
        {
            return Zonal(sinLatitude) + cold + landShare * (coldAir - cold) - kInlandCold * sinLatitude * sinLatitude * (inland - kInlandMean) * landShare;
        }

        // The seasons' half amplitude (C): the sea's, and over land the Earth's fit at the mean continentality, more inland.
        float SeasonAmplitude(float sinLatitude, float landShare, float inland)
        {
            const float s2 = sinLatitude * sinLatitude, seaSide = kSeaSeasons[0] + kSeaSeasons[1] * s2;
            return seaSide + (kLandSeasons[0] + kLandSeasons[1] * s2 - seaSide) * std::min(std::max(inland / kInlandMean, 0.0f), 1.5f) * landShare;
        }

        // Per season: the rain (mm/yr), its rate (1/s) and the part of it the large-scale ascent sets, the wind (m/s).
        struct Season { std::vector<float> rain, rate, ascent, east, north; };

        // The winds' fields on a grid: the sea air and the cold sea air, the cold currents; per season, the moisture and
        // its rain.
        struct Solution
        {
            std::vector<float> seaAir, coldAir, upwelling, water[2];
            Season seasons[2];
        };

        // The fields on grid g from its ground and its share of land, to their steady state in `airRounds` and
        // `waterRounds` rounds of their transports; started from the coarser grid's solution, if any, bilinear.
        Solution Solve(const Grid& g, const std::vector<float>& ground, const std::vector<float>& land, const Grid* coarser,
                       const Solution* from, int airRounds, int waterRounds)
        {
            const uint32_t cells = g.cells;
            std::vector<float> sea(cells);
            for (uint32_t c = 0; c < cells; ++c) sea[c] = 1.0f - land[c];
            auto start = [&](const std::vector<float>& field, const std::vector<float>& otherwise) {
                if (!from) return otherwise;
                std::vector<float> x(cells);
                ForCells(cells, [&](uint32_t c) {
                    const Taps taps = coarser->Bilinear(g.p[c]);
                    float v = 0.0f;
                    for (int q = 0; q < 4; ++q) v += taps.weight[q] * field[taps.cell[q]];
                    x[c] = v;
                });
                return x;
            };
            const std::vector<float> one(cells, 1.0f), airMixing(cells, kAirMixing), none;
            Solution out;

            // The year's winds, slower over land.
            std::vector<V3> wind(cells);
            std::vector<float> rise(cells);
            ForCells(cells, [&](uint32_t c) {
                float e, nn;
                CellWind(g.latitude[c], 0.0f, e, nn);
                const float slow = 1.0f - kFriction * land[c];
                wind[c] = g.Wind(e * slow, nn * slow, c);
            });
            ForCells(cells, [&](uint32_t c) { rise[c] = std::max(Dot(wind[c], g.Gradient(ground, c)), 0.0f); }); // m/s

            // The cold currents: where the Ekman transport, 90 degrees to the right of the wind in the north, to the left in
            // the south, carries the surface water offshore, colder water wells up (Ekman 1905). Near a coast, by the gradient
            // of the land smoothed over about 200 km; fading at the equator, where the Coriolis force does. The smoothings
            // span the same distances on every grid.
            const float fineness = float(g.n) / kTransport;
            const std::vector<float> landSmooth = g.Blur(land, std::max(1, int(4.0f * fineness * fineness)));
            out.upwelling.resize(cells);
            ForCells(cells, [&](uint32_t c) {
                const V3 towardsLand = g.Gradient(landSmooth, c);
                const float steep = Length(towardsLand);
                float e = Dot(wind[c], g.east[c]), nn = Dot(wind[c], g.north[c]);
                Turn(e, nn, g.latitude[c] < 0.0f ? -0.5f * kPi : 0.5f * kPi);
                const float offshore = steep > 0.0f ? -Dot(g.Wind(e, nn, c), towardsLand) / steep : 0.0f;
                const float steady = 1.0f - 0.6f * Sat((std::fabs(g.latitude[c]) - 30.0f) / 12.0f);
                out.upwelling[c] = std::max(offshore, 0.0f) / kTrades * Sat(steep * 300e3f) * std::tanh(std::fabs(g.latitude[c]) / 8.0f) * steady * sea[c];
            });
            out.upwelling = g.Blur(out.upwelling, std::max(1, int(6.0f * fineness * fineness)));
            for (float& u : out.upwelling) u = -kUpwelling * Sat(2.5f * u);
            // The sea air: 1 over the sea, fading inland and across the ranges; the continentality, its complement. The cold
            // sea air: the cold currents' cooling, carried inland as the sea air is. Both at once.
            Together({ [&] {
                out.seaAir = Transport(g, wind, airMixing, one, start(from ? from->seaAir : none, sea), airRounds,
                    [&](uint32_t c, float, float& source, float& rate) {
                        source = sea[c] / kSeaAir;
                        rate = sea[c] / kSeaAir + land[c] / kInland + rise[c] / kBarrier;
                    }, 2);
            }, [&] {
                out.coldAir = Transport(g, wind, airMixing, one, start(from ? from->coldAir : none, std::vector<float>(cells, 0.0f)), airRounds,
                    [&](uint32_t c, float, float& source, float& rate) {
                        source = sea[c] / kSeaAir * out.upwelling[c];
                        rate = sea[c] / kSeaAir + land[c] / kCoastal + rise[c] / kBarrier;
                    }, 2);
            } });

            // The temperatures: the year's at sea level and the seasons' half amplitude.
            std::vector<float> yearT(cells), seasons(cells);
            ForCells(cells, [&](uint32_t c) {
                const float s = g.p[c].y, inland = Sat(1.0f - out.seaAir[c]);
                yearT[c] = YearTemperature(s, land[c], inland, out.upwelling[c], out.coldAir[c]);
                seasons[c] = SeasonAmplitude(s, land[c], inland);
            });

            // The two halves of the year, the northern summer then the southern: the thermal equator moved into the summer
            // hemisphere; the thermal lows over the warm lands and the highs over the cold, their winds; the moisture carried
            // to its steady state, and its rain. Both at once.
            auto season = [&](int h) {
                const float side = h ? -1.0f : 1.0f;
                std::vector<float> t(cells), departure(cells), latitudeMean(90, 0.0f), latitudeArea(90, 0.0f);
                ForCells(cells, [&](uint32_t c) { t[c] = yearT[c] + seasons[c] * std::tanh(g.latitude[c] / 8.0f) * side; });
                auto band = [&](uint32_t c) { return std::min(uint32_t((g.latitude[c] + 90.0f) * 0.5f), 89u); };
                for (uint32_t c = 0; c < cells; ++c) latitudeMean[band(c)] += t[c] * g.area[c], latitudeArea[band(c)] += g.area[c];
                ForCells(cells, [&](uint32_t c) { departure[c] = t[c] - latitudeMean[band(c)] / latitudeArea[band(c)]; });
                departure = g.Blur(departure, std::max(1, int(40.0f * fineness * fineness)));
                Season& z = out.seasons[h];
                for (std::vector<float>* f : { &z.rain, &z.rate, &z.ascent, &z.east, &z.north }) f->resize(cells);
                std::vector<V3> moving(cells), large(cells);
                ForCells(cells, [&](uint32_t c) {
                    const V3 warmer = g.Gradient(departure, c);
                    const float lat = g.latitude[c], cl = std::cos(Radians(lat)), push = kMonsoon * cl * cl;
                    float pe = push * Dot(warmer, g.east[c]), pn = push * Dot(warmer, g.north[c]);
                    Turn(pe, pn, Radians(55.0f) * std::tanh(lat / 12.0f));
                    const float speed = std::sqrt(pe * pe + pn * pn), cut = speed > kMonsoonMax ? kMonsoonMax / speed : 1.0f;
                    float e, nn;
                    CellWind(lat, kItczShift * side, e, nn);
                    e += pe * cut, nn += pn * cut;
                    const float slow = 1.0f - kFriction * land[c];
                    large[c] = g.Wind(e, nn, c);
                    moving[c] = large[c] * slow;
                    z.east[c] = e * slow, z.north[c] = nn * slow;
                });
                // The large-scale ascent: the convergence of the wind before the land slows it, smoothed over about 300 km.
                std::vector<float> convergence(cells), mixing(cells), cap(cells), target(cells), base(cells), lift(cells), fall(cells),
                    spill(cells), evaporation(cells);
                ForCells(cells, [&](uint32_t c) {
                    float div = 0.0f;
                    for (int q = 0; q < 4; ++q) {
                        const uint32_t e = 4 * c + q;
                        div += 0.5f * Dot(large[c] + large[g.next[e]], g.normal[e]) * g.length[e];
                    }
                    convergence[c] = -div / g.area[c];
                });
                convergence = g.Blur(convergence, std::max(1, int(10.0f * fineness * fineness)));
                ForCells(cells, [&](uint32_t c) {
                    const float up = Dot(moving[c], g.Gradient(ground, c)); // m/s
                    const float ascent = std::exp(std::min(std::max(convergence[c] / kAscent, -kAscentMax), kAscentMax));
                    const float air = yearT[c] + 0.4f * (t[c] - yearT[c]); // over the sea, the season damped
                    z.ascent[c] = ascent / kResidence;
                    base[c] = z.ascent[c] / (1.0f + std::max(-up, 0.0f) / kLee);
                    lift[c] = kOrographic * std::max(up, 0.0f) / kVapourHeight;
                    cap[c] = Saturated(t[c]) * std::exp(-kBlocking * ground[c] / kVapourHeight);
                    target[c] = kSeaHumidity * Saturated(std::max(air, -1.8f)) * std::min(std::max((air + 25.0f) / 15.0f, 0.2f), 1.0f);
                    const float kept = 1.0f - kRecycling * Sat((t[c] + 5.0f) / 25.0f) * land[c]; // the rain the land does not give back
                    fall[c] = (base[c] + lift[c]) * kept;
                    spill[c] = kept / kExcess;
                    evaporation[c] = sea[c] / kEvaporation;
                    mixing[c] = kEddies * (0.4f + Bell(std::fabs(g.latitude[c]), 50.0f, 18.0f));
                });
                std::vector<float> wet(cells);
                for (uint32_t c = 0; c < cells; ++c) wet[c] = 0.8f * target[c];
                out.water[h] = Transport(g, moving, mixing, cap, start(from ? from->water[h] : none, wet), waterRounds,
                    [&](uint32_t c, float x, float& source, float& rate) {
                        const float evaporating = x < target[c] ? evaporation[c] : 0.0f;
                        source = evaporating * target[c];
                        rate = fall[c] + std::max(x - cap[c], 0.0f) * spill[c] / std::max(x, 1e-6f) + evaporating;
                    }, 2);
                const std::vector<float>& water = out.water[h];
                ForCells(cells, [&](uint32_t c) {
                    const float excess = std::max(water[c] - cap[c], 0.0f) / kExcess;
                    z.rate[c] = base[c] + lift[c];
                    z.rain[c] = (water[c] * z.rate[c] + excess) * 365.0f * kDay; // mm/yr
                });
            };
            Together({ [&] { season(0); }, [&] { season(1); } });
            return out;
        }

        // The means of 2 x 2 cells: the next coarser grid's field.
        std::vector<float> Coarser(const std::vector<float>& x, uint32_t n)
        {
            const uint32_t m = n / 2;
            std::vector<float> y(6 * m * m);
            ForCells(6 * m * m, [&](uint32_t c) {
                const uint32_t f = c / (m * m), j = c / m % m, i = c % m, at = (f * n + 2 * j) * n + 2 * i;
                y[c] = 0.25f * ((x[at] + x[at + 1]) + (x[at + n] + x[at + n + 1]));
            });
            return y;
        }
    }

    Map Build(const Tectonics::Map& tectonics, double radiusKm)
    {
        const auto begin = std::chrono::steady_clock::now();
        const float radius = float(radiusKm * 1000.0);
        const uint32_t n = Size, w = tectonics.size + 2 * Tectonics::Pad, k = tectonics.size / n;
        const Grid fine(n, radius), coarse(kTransport, radius), coarsest(kTransport / 2, radius);

        // The large forms (the tectonic map's slice 0, x), k x k of its texels per cell: the ground under the air, the sea's
        // surface over the sea, and the share of land; then the means of 2 x 2 of those on the winds' grids.
        std::vector<float> ground(fine.cells), land(fine.cells);
        ForCells(fine.cells, [&](uint32_t c) {
            const uint32_t f = c / (n * n), j = c / n % n, i = c % n;
            float sum = 0.0f, dry = 0.0f;
            for (uint32_t b = 0; b < k; ++b)
                for (uint32_t a = 0; a < k; ++a) {
                    const size_t at = ((size_t(f) * Tectonics::Slices * w + j * k + b + Tectonics::Pad) * w + i * k + a + Tectonics::Pad) * 4;
                    const float e = _mm_cvtss_f32(_mm_cvtph_ps(_mm_cvtsi32_si128(tectonics.texels[at])));
                    sum += std::max(e, 0.0f), dry += e > 0.0f ? 1.0f : 0.0f;
                }
            ground[c] = sum / (k * k), land[c] = dry / (k * k);
        });
        const std::vector<float> groundC = Coarser(ground, n), landC = Coarser(land, n);

        // The winds' transports, on a grid of 200 km first, whose solution starts the one of 100 km: what spreads slowly, by
        // the eddies' mixing where the winds are calm, settles there in a quarter of the rounds, each a quarter of the cost.
        // The rounds: within 0.02 of the steady state's humidity at the 99th percentile, 0.07 C of its temperature
        // (docs/spec-climat.md, the measures).
        const Solution rough = Solve(coarsest, Coarser(groundC, coarse.n), Coarser(landC, coarse.n), nullptr, nullptr, 300, 400);
        const Solution solution = Solve(coarse, groundC, landC, &coarsest, &rough, 100, 150);

        // The map's own resolution: the coarse fields bilinear; the year's temperature and seasons from the fine land; the
        // rain shared out by the fine slopes, each cell's rate against the coarse one's, within half to twice.
        Map map;
        map.size = n;
        map.cells.resize(size_t(fine.cells) * Channels);
        ForCells(fine.cells, [&](uint32_t c) {
            const Taps taps = coarse.Bilinear(fine.p[c]);
            auto at = [&](const std::vector<float>& field) {
                float v = 0.0f;
                for (int q = 0; q < 4; ++q) v += taps.weight[q] * field[taps.cell[q]];
                return v;
            };
            const float s = fine.p[c].y, inland = Sat(1.0f - at(solution.seaAir)), lat = fine.latitude[c];
            float* out = &map.cells[size_t(c) * Channels];
            out[Temperature] = YearTemperature(s, land[c], inland, at(solution.upwelling), at(solution.coldAir));
            out[Amplitude] = SeasonAmplitude(s, land[c], inland);
            out[Continentality] = inland * land[c];
            out[Upwelling] = at(solution.upwelling);
            const V3 slope = fine.Gradient(ground, c);
            float rain[2], east = 0.0f, north = 0.0f;
            for (int h = 0; h < 2; ++h) {
                const Season& z = solution.seasons[h];
                const float e = at(z.east), nn = at(z.north), up = Dot(fine.Wind(e, nn, c), slope);
                const float rate = at(z.ascent) / (1.0f + std::max(-up, 0.0f) / kLee) + kOrographic * std::max(up, 0.0f) / kVapourHeight;
                rain[h] = at(z.rain) * std::min(std::max(rate / std::max(at(z.rate), 1e-12f), 0.5f), 2.0f);
                east += 0.5f * e, north += 0.5f * nn;
            }
            out[Precipitation] = 0.5f * (rain[0] + rain[1]);
            out[Summer] = 0.5f + 0.5f * std::tanh(lat / 8.0f) * (rain[0] - rain[1]) / std::max(rain[0] + rain[1], 1e-3f);
            out[WindEast] = east, out[WindNorth] = north;
        });
        map.ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - begin).count();
        return map;
    }

    void At(const Map& map, const double d[3], float fields[Channels])
    {
        const Taps taps = Faces{ map.size }.Bilinear({ float(d[0]), float(d[1]), float(d[2]) });
        for (uint32_t f = 0; f < Channels; ++f) {
            fields[f] = 0.0f;
            for (int q = 0; q < 4; ++q) fields[f] += taps.weight[q] * map.cells[size_t(taps.cell[q]) * Channels + f];
        }
    }

    std::vector<uint16_t> Texels(const Map& map)
    {
        const uint32_t n = map.size;
        size_t perSlice = 0;
        for (uint32_t mip = 0; mip < Mips; ++mip) perSlice += size_t(n >> mip) * (n >> mip) * 4;
        std::vector<uint16_t> texels(12 * perSlice);
        ForCells(12, [&](uint32_t slice) {
            const uint32_t face = slice % 6, first = slice / 6 * 4;
            std::vector<float> level(size_t(n) * n * 4), half;
            for (uint32_t t = 0; t < n * n; ++t)
                for (uint32_t k = 0; k < 4; ++k) level[4 * t + k] = map.cells[(size_t(face) * n * n + t) * Channels + first + k];
            uint16_t* out = texels.data() + slice * perSlice;
            for (uint32_t mip = 0, m = n; mip < Mips; ++mip, m /= 2) {
                if (mip > 0) { // the means of 2 x 2
                    half.assign(size_t(m) * m * 4, 0.0f);
                    for (uint32_t j = 0; j < m; ++j)
                        for (uint32_t i = 0; i < m; ++i)
                            for (uint32_t k = 0; k < 4; ++k)
                                half[(j * m + i) * 4 + k] = 0.25f * (level[((2 * j) * 2 * m + 2 * i) * 4 + k] + level[((2 * j) * 2 * m + 2 * i + 1) * 4 + k]
                                                                   + level[((2 * j + 1) * 2 * m + 2 * i) * 4 + k] + level[((2 * j + 1) * 2 * m + 2 * i + 1) * 4 + k]);
                    level.swap(half);
                }
                for (size_t t = 0; t < size_t(m) * m * 4; t += 4, out += 4)
                    _mm_storel_epi64((__m128i*)out, _mm_cvtps_ph(_mm_loadu_ps(&level[t]), 0));
            }
        });
        return texels;
    }

    bool Save(const Map& map, uint32_t seed, const std::wstring& path)
    {
        FILE* f = nullptr;
        if (_wfopen_s(&f, (path + L".tmp").c_str(), L"wb") != 0 || !f) return false;
        const char magic[8] = { 'E', 'X', 'O', 'C', 'L', 'I', 'M', '1' };
        const uint32_t header[4] = { seed, map.size, Channels, 6 };
        bool ok = fwrite(magic, 1, 8, f) == 8 && fwrite(header, 4, 4, f) == 4
               && fwrite(map.cells.data(), 4, map.cells.size(), f) == map.cells.size();
        ok = fclose(f) == 0 && ok;
        if (!ok) return false;
        _wremove(path.c_str());
        return _wrename((path + L".tmp").c_str(), path.c_str()) == 0;
    }

    // ---------------------------------------------------------------------------------------------
    // The clouds' weather map (Climate::Weather; docs/spec-nuages.md, the weather): a cloud climatology drawn from the
    // climate, and one moment of its weather, the storm tracks' cyclones placed by the seed. Each texel computed alone.
    // ---------------------------------------------------------------------------------------------
    namespace
    {
        float Smooth(float e0, float e1, float x) { const float t = Sat((x - e0) / (e1 - e0)); return t * t * (3.0f - 2.0f * t); }

        // Gradient noise of 3D lattice points: one of the 12 directions to a cube's edges at each node, quintic weights.
        float Gradient3(float x, float y, float z, uint32_t seed)
        {
            static const float g[12][3] = { { 1, 1, 0 }, { -1, 1, 0 }, { 1, -1, 0 }, { -1, -1, 0 }, { 1, 0, 1 }, { -1, 0, 1 },
                                            { 1, 0, -1 }, { -1, 0, -1 }, { 0, 1, 1 }, { 0, -1, 1 }, { 0, 1, -1 }, { 0, -1, -1 } };
            const float fx = std::floor(x), fy = std::floor(y), fz = std::floor(z);
            const int ix = int(fx), iy = int(fy), iz = int(fz);
            const float u[3] = { x - fx, y - fy, z - fz };
            float w[3];
            for (int k = 0; k < 3; ++k) w[k] = u[k] * u[k] * u[k] * (u[k] * (u[k] * 6.0f - 15.0f) + 10.0f);
            float sum = 0.0f;
            for (int corner = 0; corner < 8; ++corner) {
                const int dx = corner & 1, dy = (corner >> 1) & 1, dz = corner >> 2;
                uint32_t h = (uint32_t(ix + dx) * 73856093u) ^ (uint32_t(iy + dy) * 19349663u) ^ (uint32_t(iz + dz) * 83492791u) ^ seed;
                h ^= h >> 16; h *= 0x7feb352du; h ^= h >> 15; h *= 0x846ca68bu; h ^= h >> 16;
                const float* d = g[h % 12];
                const float value = d[0] * (u[0] - dx) + d[1] * (u[1] - dy) + d[2] * (u[2] - dz);
                sum += value * (dx ? w[0] : 1.0f - w[0]) * (dy ? w[1] : 1.0f - w[1]) * (dz ? w[2] : 1.0f - w[2]);
            }
            return 1.4f * sum;
        }

        // Octaves of gradient noise on the unit sphere, the widest of wavelength `km` on a body of `radiusKm`, each half the
        // previous, each on its own lattice, offset from the others; `stretch` squeezes the polar axis, drawing the features
        // out east to west. About -1 to 1.
        float SphereNoise(V3 p, float km, int octaves, uint32_t seed, float radiusKm, float stretch = 1.0f)
        {
            float sum = 0.0f, amplitude = 1.0f, total = 0.0f;
            for (int o = 0; o < octaves; ++o, amplitude *= 0.5f) {
                const uint32_t s = seed + 101u * o;
                const float f = radiusKm / (km / float(1 << o)), shift = float(s % 97u);
                sum += amplitude * Gradient3(p.x * f + 0.31f * shift + 17.0f, p.y * f * stretch + 0.57f * shift + 17.0f,
                                             p.z * f + 0.83f * shift + 17.0f, s);
                total += amplitude;
            }
            return sum / total;
        }

        // Voronoi interiors: the gap to the two nearest jittered nodes, zero at a cell's rim. Nodes move by at most
        // .2 cells, so these 27 contain both nearest nodes. Only active decks pay for the cellular texture.
        float CellCore(V3 p, float frequency, uint32_t seed)
        {
            p = p * frequency + V3{ 17.31f, 29.57f, 43.83f };
            const int ix = int(std::floor(p.x + 0.5f)), iy = int(std::floor(p.y + 0.5f)), iz = int(std::floor(p.z + 0.5f));
            p = p - V3{ float(ix), float(iy), float(iz) };
            float first = 100.0f, second = 100.0f;
            for (int z = -1; z <= 1; ++z)
                for (int y = -1; y <= 1; ++y)
                    for (int x = -1; x <= 1; ++x) {
                        uint32_t hash = (uint32_t(ix + x) * 73856093u) ^ (uint32_t(iy + y) * 19349663u)
                                      ^ (uint32_t(iz + z) * 83492791u) ^ seed;
                        hash ^= hash >> 16; hash *= 0x7feb352du; hash ^= hash >> 15; hash *= 0x846ca68bu; hash ^= hash >> 16;
                        const V3 d = { x + float(hash & 1023u) * (0.4f / 1023.0f) - 0.2f - p.x,
                                       y + float((hash >> 10) & 1023u) * (0.4f / 1023.0f) - 0.2f - p.y,
                                       z + float((hash >> 20) & 1023u) * (0.4f / 1023.0f) - 0.2f - p.z };
                        const float d2 = Dot(d, d);
                        if (d2 < first) second = first, first = d2;
                        else second = std::min(second, d2);
                    }
            return Smooth(0.0f, 0.25f, std::sqrt(second) - std::sqrt(first));
        }

        // The two warped thickness octaves vary a class by up to .18, within its own water-content range.
        float Thickness(float nominal, float detail, float low, float high)
        {
            return std::min(high, std::max(low, nominal + 0.18f * detail));
        }

        // A field on the latitude and longitude grid, row 0 north.
        struct LatLon
        {
            uint32_t w, h;
            float texelKm;
            std::vector<float> latitude; // per row, radians
            // Box blurs over about `km` in every direction, three passes: the rows wrap, the columns stop at the poles.
            std::vector<float> Blur(std::vector<float> f, float km) const
            {
                const int passes = 3, ry = std::max(1, int(std::lround(km / texelKm / std::sqrt(float(passes)))));
                std::vector<float> g(f.size());
                // Reuse one worker pool for the six independent line passes.
                ForRounds(std::max(w, h), 2 * passes, [&](uint32_t line, int pass) {
                    if ((pass & 1) == 0 && line < w) {
                        const uint32_t i = line;
                        double sum = 0.0;
                        auto at = [&](int j) { return f[size_t(std::min(std::max(j, 0), int(h) - 1)) * w + i]; };
                        for (int j = -ry; j <= ry; ++j) sum += at(j);
                        for (uint32_t j = 0; j < h; ++j) {
                            g[size_t(j) * w + i] = float(sum / (2 * ry + 1));
                            sum += at(int(j) + ry + 1) - at(int(j) - ry);
                        }
                    }
                    if ((pass & 1) != 0 && line < h) {
                        const uint32_t j = line;
                        const float c = std::max(std::cos(latitude[j]), 1e-3f);
                        const int rx = std::min(int(w) / 2 - 1, std::max(1, int(std::lround(km / (texelKm * c) / std::sqrt(float(passes))))));
                        const float* row = &g[size_t(j) * w];
                        auto at = [&](int i) { return row[(i % int(w) + int(w)) % int(w)]; };
                        double sum = 0.0;
                        for (int i = -rx; i <= rx; ++i) sum += at(i);
                        for (uint32_t i = 0; i < w; ++i) {
                            f[size_t(j) * w + i] = float(sum / (2 * rx + 1));
                            sum += at(int(i) + rx + 1) - at(int(i) - rx);
                        }
                    }
                });
                return f;
            }
            float Sample(const std::vector<float>& f, V3 d) const
            {
                const float x = (std::atan2(d.z, d.x) / (2.0f * kPi) + 0.5f) * w - 0.5f;
                const float y = std::min(std::max((0.5f - std::asin(std::min(std::max(d.y, -1.0f), 1.0f)) / kPi) * h - 0.5f, 0.0f), h - 1.0f);
                return SampleAt(f, x, y);
            }
            float SampleAt(const std::vector<float>& f, float x, float y) const
            {
                const int ix = int(std::floor(x)), iy = int(y);
                const float u = x - std::floor(x), v = y - iy;
                const uint32_t x0 = (ix % int(w) + int(w)) % w, x1 = (x0 + 1) % w, y1 = std::min(uint32_t(iy) + 1, h - 1);
                return (1.0f - v) * ((1.0f - u) * f[iy * w + x0] + u * f[iy * w + x1])
                     + v * ((1.0f - u) * f[y1 * w + x0] + u * f[y1 * w + x1]);
            }
            uint32_t TexelOf(V3 d) const
            {
                const float lon = std::atan2(d.z, d.x), lat = std::asin(std::min(std::max(d.y, -1.0f), 1.0f));
                const uint32_t i = uint32_t(std::min(std::max((lon / (2.0f * kPi) + 0.5f) * w, 0.0f), w - 1.0f));
                const uint32_t j = uint32_t(std::min(std::max((0.5f - lat / kPi) * h, 0.0f), h - 1.0f));
                return j * w + i;
            }
        };

        // R selects the occupied area of the shader's 32 and 128 km shape, its water following e (Clouds.hlsli, 238439c).
        // Measured opacity, 6 km column: R = .08 .10 .12 .14 .16 .18 .20 .22 .24 .26 .28:
        // .06 .13 .21 .32 .44 .55 .66 .75 .82 .88 .92. A thin sheet at R = .28 keeps its 8% of holes.
        // Interpolate from the empty origin too. Organized opaque columns spend R >= .28 on their thickness.
        float CloudControl(float c, float thickness)
        {
            static const float opacity[] = { 0.0f, 0.06f, 0.13f, 0.21f, 0.32f, 0.44f, 0.55f, 0.66f, 0.75f, 0.82f, 0.88f, 0.92f };
            static const float control[] = { 0.0f, 0.08f, 0.10f, 0.12f, 0.14f, 0.16f, 0.18f, 0.20f, 0.22f, 0.24f, 0.26f, 0.28f };
            if (c < 0.03f) return 0.0f;
            if (c >= 0.97f) return 0.28f + 0.62f * Sat(thickness);
            if (c >= 0.92f) return 0.28f;
            int k = 0;
            while (c > opacity[k + 1]) ++k;
            return control[k] + (control[k + 1] - control[k]) * (c - opacity[k]) / (opacity[k + 1] - opacity[k]);
        }

        struct CloudField { float coverage, family, thickness; };

        // A fourth-power smooth maximum; the eighth-power weights let the strongest shape supply its family gently.
        struct Clouds
        {
            float fourth = 0.0f, weight = 0.0f, family = 0.0f, thickness = 0.0f, noise = 0.0f;
            void Add(float c, float g, float e, float n = 0.0f)
            {
                const float c2 = c * c, c4 = c2 * c2, c8 = c4 * c4;
                fourth += c4, weight += c8, family += c8 * g, thickness += c8 * e, noise += c8 * n;
            }
            void Merge(const Clouds& other, float fraction = 1.0f)
            {
                const float f2 = fraction * fraction, f4 = f2 * f2, f8 = f4 * f4;
                fourth += other.fourth * f4, weight += other.weight * f8, family += other.family * f8;
                thickness += other.thickness * f8, noise += other.noise * f8;
            }
            CloudField Resolve(float limit = 1.0f) const
            {
                const float inverse = 1.0f / std::max(weight, 1e-12f);
                return { std::min(limit, std::sqrt(std::sqrt(fourth))), family * inverse, thickness * inverse };
            }
        };

        // Empirical area CDF, accumulated north-to-south and west-to-east in double precision, once per field.
        // Only the application is parallel: thread count never changes a histogram sum or a texel's rank.
        void UniformArea(std::vector<float>& field, const LatLon& grid)
        {
            const int bins = 2048;
            const auto range = std::minmax_element(field.begin(), field.end());
            const float low = *range.first, scale = (bins - 1.001f) / std::max(*range.second - low, 1e-6f);
            std::vector<double> histogram(bins), cumulative(bins + 1);
            for (uint32_t j = 0; j < grid.h; ++j) {
                const double area = std::cos(double(grid.latitude[j]));
                for (uint32_t i = 0; i < grid.w; ++i) histogram[int((field[j * grid.w + i] - low) * scale)] += area;
            }
            for (int k = 0; k < bins; ++k) cumulative[k + 1] = cumulative[k] + histogram[k];
            ForCells(uint32_t(field.size()), [&](uint32_t t) {
                const float x = (field[t] - low) * scale;
                const int k = int(x);
                field[t] = float((cumulative[k] + (x - k) * histogram[k]) / cumulative[bins]);
            });
        }

        // A short great-circle step, its heading tangent to the departure point.
        V3 Step(V3 p, V3 heading, float km, float radius)
        {
            return p * std::cos(km / radius) + heading * std::sin(km / radius);
        }

        struct FrontSegment { V3 a, delta, middle, normal; float inverseLength2, reach, along, waveA, waveB; };
        struct Cyclone
        {
            V3 c, east, north, wake, wakeEast, wakeNorth;
            float scale, stage, turnCos, turnSin, strength, reach, headReach, headKm, frontReach, wakeKm, wakeReach, pitch, spiralNormal;
            bool south;
            int arms;
            std::vector<FrontSegment> front;
        };

        // A random sequence, SplitMix64.
        struct Random
        {
            uint64_t state;
            float Uniform()
            {
                uint64_t z = state += 0x9E3779B97F4A7C15ull;
                z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
                z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
                return float((z ^ (z >> 31)) >> 40) * (1.0f / 16777216.0f);
            }
        };
    }

    std::vector<uint8_t> Weather(const Map& climate, const Tectonics::Map& tectonics, uint32_t seed, double radiusKm,
                                 std::vector<float>* listed)
    {
        const uint32_t w = WeatherWidth, h = WeatherHeight, texels = w * h;
        const float R = float(radiusKm);
        // The map organizes masses at 250 km and above; the shader alone draws the small cumulus grains.
        const float kClusterKm = 600.0f, kTearKm = 250.0f;
        const float kDeckBlurKm = 500.0f, kDeckCarryKm = 1600.0f, kItczHalfWidth = 4.0f;
        const float kTradeFadeKm = 1250.0f; // the broken deck's last downstream cumulus, then clear sky
        const float kThicknessKm = 250.0f, kThicknessFineKm = 80.0f, kDeckCellKm = 120.0f;
        const float kEdgeKm = 60.0f, kEdgeWarpKm = 20.0f, kEdgeMaxKm = kEdgeKm + kEdgeWarpKm;
        // Synoptic scales: the spiral's outer radius and arm width, the cold front's length and tapering width.
        const float kLowMinKm = 1500.0f, kLowMaxKm = 2200.0f;
        const float kFrontMinKm = 2500.0f, kFrontMaxKm = 5000.0f, kFrontNearKm = 600.0f, kFrontTailKm = 220.0f;
        const float kFrontStepKm = 120.0f, kLowSeparationKm = 2500.0f;
        const float kFrontReachKm = 1100.0f; // includes the warm sector, cold lane and contour warp
        LatLon grid{ w, h, 2.0f * kPi * R / w, std::vector<float>(h) };
        for (uint32_t j = 0; j < h; ++j) grid.latitude[j] = (0.5f - (j + 0.5f) / h) * kPi;

        std::vector<V3> p(texels), east(texels), north(texels);
        std::vector<float> rain(texels), temperature(texels), cold(texels), windE(texels), windN(texels), ground(texels), land(texels);
        std::vector<float> nLarge(texels), nMeso(texels), nFine(texels), warp(texels), clusters(texels);
        std::vector<float> textureConv(texels), textureDeck(texels);
        std::vector<float> nThickness(texels), nEdge(texels);
        const Faces tect{ tectonics.size };
        const uint32_t tw = tectonics.size + 2 * Tectonics::Pad;
        ForCells(texels, [&](uint32_t t) {
            const float lat = grid.latitude[t / w], lon = ((t % w + 0.5f) / w - 0.5f) * 2.0f * kPi;
            const V3 d = { std::cos(lat) * std::cos(lon), std::sin(lat), std::cos(lat) * std::sin(lon) };
            p[t] = d;
            east[t] = { -std::sin(lon), 0.0f, std::cos(lon) };
            north[t] = { -std::sin(lat) * std::cos(lon), std::cos(lat), -std::sin(lat) * std::sin(lon) };
            const double dd[3] = { d.x, d.y, d.z };
            float f[Channels];
            At(climate, dd, f);
            rain[t] = f[Precipitation], temperature[t] = f[Temperature], cold[t] = std::max(-f[Upwelling], 0.0f);
            windE[t] = f[WindEast], windN[t] = f[WindNorth];
            // The existing large forms and land fraction, bilinear on the padded tectonic face.
            uint32_t face;
            float x, y;
            tect.Locate(d, face, x, y);
            const int i0 = int(std::floor(x)), j0 = int(std::floor(y));
            const float u = x - i0, v = y - j0;
            auto e = [&](int i, int j) {
                const size_t at = ((size_t(face) * Tectonics::Slices * tw + j + Tectonics::Pad) * tw + i + Tectonics::Pad) * 4;
                return _mm_cvtss_f32(_mm_cvtph_ps(_mm_cvtsi32_si128(tectonics.texels[at])));
            };
            const float elevation = (1 - v) * ((1 - u) * e(i0, j0) + u * e(i0 + 1, j0)) + v * ((1 - u) * e(i0, j0 + 1) + u * e(i0 + 1, j0 + 1));
            ground[t] = std::max(elevation, 0.0f), land[t] = Smooth(-100.0f, 100.0f, elevation);
            nLarge[t] = SphereNoise(d, 1500.0f, 1, seed ^ 11u, R);
            nMeso[t] = SphereNoise(d, kClusterKm, 2, seed ^ 23u, R);
            nFine[t] = SphereNoise(d, kTearKm, 1, seed ^ 41u, R);
            warp[t] = SphereNoise(d, 650.0f, 2, seed ^ 53u, R);
            clusters[t] = Smooth(-0.25f, 0.35f, nMeso[t] + 0.35f * nLarge[t]);
            const V3 warped = Normalize(d + east[t] * (100.0f / R * warp[t]) + north[t] * (90.0f / R * nLarge[t]));
            textureConv[t] = SphereNoise(warped, 500.0f, 2, seed ^ 101u, R);
            textureDeck[t] = SphereNoise(warped, 800.0f, 2, seed ^ 107u, R);
            // Cartesian displacements stay continuous across the poles as well as the longitude seam.
            V3 thicknessDomain = Normalize(d + V3{ 35.0f * warp[t], 30.0f * nFine[t], 30.0f * nMeso[t] } * (1.0f / R));
            const float coarse = SphereNoise(thicknessDomain, kThicknessKm, 1, seed ^ 127u, R);
            thicknessDomain = Normalize(thicknessDomain + V3{ 12.0f * coarse, 10.0f * nMeso[t], 10.0f * nFine[t] } * (1.0f / R));
            nEdge[t] = SphereNoise(thicknessDomain, kThicknessFineKm, 1, seed ^ 131u, R);
            nThickness[t] = std::min(1.0f, std::max(-1.0f, 2.0f * (0.65f * coarse + 0.35f * nEdge[t])));
        });
        std::vector<float> sea(texels);
        for (uint32_t t = 0; t < texels; ++t) sea[t] = 1.0f - land[t];
        const std::vector<float> coldWide = grid.Blur(cold, kDeckBlurKm), sea150 = grid.Blur(sea, 150.0f),
                                 sea800 = grid.Blur(sea, 800.0f), groundWide = grid.Blur(ground, 120.0f),
                                 clustersWide = grid.Blur(clusters, 150.0f);

        // The rain maximum on land as well as sea locates the ITCZ. Three circular box passes keep the line continuous,
        // including the longitude seam; a 2000 km smoothing length, independent of the camera or the weather seed.
        std::vector<float> itcz(w), line(w);
        for (uint32_t i = 0; i < w; ++i) {
            float most = -1.0f;
            for (uint32_t j = 0; j < h; ++j)
                if (std::fabs(grid.latitude[j]) <= Radians(25.0f) && rain[j * w + i] > most)
                    most = rain[j * w + i], itcz[i] = grid.latitude[j];
        }
        const int lineRadius = std::max(1, int(2000.0f / (grid.texelKm * std::sqrt(3.0f))));
        for (int pass = 0; pass < 3; ++pass) {
            double sum = 0.0;
            auto at = [&](int i) { return itcz[(i % int(w) + int(w)) % int(w)]; };
            for (int i = -lineRadius; i <= lineRadius; ++i) sum += at(i);
            for (uint32_t i = 0; i < w; ++i) {
                line[i] = float(sum / (2 * lineRadius + 1));
                sum += at(int(i) + lineRadius + 1) - at(int(i) - lineRadius);
            }
            itcz.swap(line);
        }

        // The westerlies locate the rails. Their cold maritime background is continuous between individual systems.
        std::vector<float> track(texels);
        ForCells(texels, [&](uint32_t t) {
            const float a = std::fabs(grid.latitude[t / w]) * (180.0f / kPi);
            // Southern maritime fronts reach farther equatorward; the northern rail has a narrower subtropical edge.
            const bool south = grid.latitude[t / w] < 0.0f;
            track[t] = Smooth(south ? 20.0f : 35.0f, south ? 36.0f : 54.0f, a) * (1.0f - Smooth(67.0f, 75.0f, a))
                     * (0.8f + 0.2f * Smooth(-4.0f, 1.0f, windE[t]));
        });
        std::vector<Cyclone> cyclones;
        Random random{ 0x5EEDC10Dull ^ (uint64_t(seed) * 0x9E3779B97F4A7C15ull) };
        const int southern = 8 + int(3.0f * random.Uniform()), northern = 6 + int(3.0f * random.Uniform());
        const float phase = 2.0f * kPi * random.Uniform();
        auto place = [&](float lat, float lon, float stage) {
            Cyclone q{};
            q.c = { std::cos(lat) * std::cos(lon), std::sin(lat), std::cos(lat) * std::sin(lon) };
            q.east = { -std::sin(lon), 0.0f, std::cos(lon) }, q.north = Cross(q.east, q.c);
            q.south = lat < 0.0f;
            q.scale = kLowMinKm + (kLowMaxKm - kLowMinKm) * random.Uniform(), q.stage = stage;
            // A near-constant total synoptic area along the ring, whether it contains eight systems or ten.
            q.scale *= q.south ? 0.94f * std::sqrt(9.0f / southern) : 1.02f;
            const float turn = 0.3f * (random.Uniform() - 0.5f);
            q.turnCos = std::cos(turn), q.turnSin = std::sin(turn), q.strength = 0.96f + 0.04f * random.Uniform();
            q.arms = random.Uniform() < 0.5f ? 2 : 3;
            q.headKm = std::max(1.6f * q.scale + 200.0f, 0.9f * q.scale + 1900.0f);
            q.headReach = std::cos(q.headKm / R);
            q.pitch = std::log(1.0f / 0.02f) / (2.0f * kPi * (1.0f + 0.75f * q.stage));
            q.spiralNormal = q.pitch / std::sqrt(1.0f + q.pitch * q.pitch);
            // The cold front starts on the outer arm, southeast of the low. Small great-circle steps turn from SSW
            // towards WSW (mirrored in the south), with slowly varying curvature; no planar Bezier at planetary scale.
            const float outerAngle = -0.5f;
            const V3 startHeading = q.east * std::cos(outerAngle - turn)
                                  + q.north * (std::sin(outerAngle - turn) * (q.south ? -1.0f : 1.0f));
            V3 a = Step(q.c, startHeading, q.scale, R);
            const float target = Radians(25.0f + 6.0f * random.Uniform());
            const float length = std::min(kFrontMaxKm, std::max(kFrontMinKm, (std::fabs(lat) - target) * R / 0.70f - 0.5f * q.scale));
            const int steps = int(std::ceil(length / kFrontStepKm));
            float farthest = 0.0f;
            float waveA = std::min(1.0f, std::max(-1.0f, 2.0f * SphereNoise(a, 800.0f, 2, seed ^ 149u, R)));
            for (int k = 0; k < steps; ++k) {
                const float u = (k + 0.5f) / steps;
                const V3 e = Normalize({ -a.z, 0.0f, a.x }), n = Cross(e, a);
                const float bend = Smooth(target + Radians(4.0f), target, std::fabs(std::asin(a.y)));
                const float heading = Radians(196.0f + 55.0f * u + 5.0f * std::sin(5.0f * u + stage * 6.0f)) * (1.0f - bend)
                                    + Radians(270.0f) * bend - turn * (1.0f - bend);
                const V3 direction = e * std::sin(heading) + n * (std::cos(heading) * (q.south ? -1.0f : 1.0f));
                const V3 b = Step(a, direction, length / steps, R), delta = b - a, middle = Normalize(a + b);
                V3 normal = Normalize(Cross(a, b));
                // East and equatorward stays the warm side even where the tail turns due west (east alone is singular).
                if (Dot(normal, e - n * (q.south ? -0.35f : 0.35f)) < 0.0f) normal = normal * -1.0f;
                const float waveB = std::min(1.0f, std::max(-1.0f, 2.0f * SphereNoise(b, 800.0f, 2, seed ^ 149u, R)));
                q.front.push_back({ a, delta, middle, normal, 1.0f / Dot(delta, delta), std::cos((length / steps + kFrontReachKm) / R), u, waveA, waveB });
                farthest = std::max(farthest, Angle(q.c, b) * R + kFrontReachKm);
                a = b, waveA = waveB;
            }
            q.frontReach = std::cos(std::min(farthest / R, kPi));
            q.reach = std::min(q.frontReach, q.headReach);
            cyclones.push_back(q);
            if (listed)
                listed->insert(listed->end(), { lat * (180.0f / kPi), lon * (180.0f / kPi), q.scale, q.stage });
        };
        if (listed) listed->clear();
        // A jittered ring guarantees 8-10 southern systems, 30-45 degrees apart even across the seam.
        for (int k = 0; k < southern; ++k) {
            const float lon = phase + (k + 0.04f * (random.Uniform() - 0.5f)) * (2.0f * kPi / southern);
            float best = -1.0f, bestLat = 0.0f;
            for (int trial = 0; trial < 12; ++trial) {
                const float lat = -Radians(45.0f + 17.0f * random.Uniform());
                const V3 c = { std::cos(lat) * std::cos(lon), std::sin(lat), std::cos(lat) * std::sin(lon) };
                const uint32_t t = grid.TexelOf(c);
                const float score = 0.35f * track[t] + 0.25f * sea800[t] + 0.40f * random.Uniform();
                if (score > best) best = score, bestLat = lat;
            }
            place(bestLat, std::atan2(std::sin(lon), std::cos(lon)), (k + random.Uniform()) / southern);
        }
        // Best maritime candidate among sequential trials, subject to the hard separation. Ocean preference cannot
        // starve a rail on a planet with a northern supercontinent; the winds still decide its preferred latitude.
        for (int k = 0; k < northern; ++k) {
            float best = -1.0f, bestLat = 0.0f, bestLon = 0.0f;
            for (int trial = 0; trial < 256; ++trial) {
                const float lat = Radians(38.0f + 24.0f * random.Uniform()), lon = (2.0f * random.Uniform() - 1.0f) * kPi;
                const V3 c = { std::cos(lat) * std::cos(lon), std::sin(lat), std::cos(lat) * std::sin(lon) };
                bool apart = true;
                for (const Cyclone& q : cyclones) if (!q.south && Dot(c, q.c) > std::cos(kLowSeparationKm / R)) apart = false;
                if (!apart) continue;
                const uint32_t t = grid.TexelOf(c);
                const float score = 0.75f * sea800[t] + 0.20f * track[t] + 0.15f * random.Uniform();
                if (score > best) best = score, bestLat = lat, bestLon = lon;
            }
            if (best >= 0.0f) place(bestLat, bestLon, (k + random.Uniform()) / northern);
        }
        // The maritime cold sector fills the interval back to the preceding low in each rail, rather than sharing
        // the compact spiral's radius. Give it its own spherical bound so the large wake costs nothing elsewhere.
        for (Cyclone& q : cyclones) {
            float previous = 2.0f * kPi;
            q.wakeKm = kLowSeparationKm;
            const float lon = std::atan2(q.c.z, q.c.x);
            for (const Cyclone& other : cyclones) {
                if (&other == &q || other.south != q.south) continue;
                const float west = std::fmod(lon - std::atan2(other.c.z, other.c.x) + 2.0f * kPi, 2.0f * kPi);
                if (west < previous) previous = west, q.wakeKm = Angle(q.c, other.c) * R;
            }
            const V3 heading = Normalize(q.east * -1.0f - q.north * (q.south ? -0.2f : 0.2f));
            q.wake = Step(q.c, heading, 0.5f * q.wakeKm, R);
            q.wakeEast = Normalize({ -q.wake.z, 0.0f, q.wake.x }), q.wakeNorth = Cross(q.wakeEast, q.wake);
            const float reachKm = 1.4f * std::max(0.6f * q.wakeKm, 1400.0f) + 200.0f; // include the contour warp
            q.wakeReach = std::cos(std::min(reachKm / R, kPi));
            q.reach = std::min(q.reach, std::cos(std::min((reachKm + 0.5f * q.wakeKm) / R, kPi)));
        }

        std::vector<uint8_t> base(size_t(texels) * 4);
        std::vector<CloudField> smallField(texels), massField(texels), layerField(texels);
        std::vector<float> textureField(texels), cirrusField(texels);
        ForCells(texels, [&](uint32_t t) {
            const uint32_t j = t / w, i = t % w;
            const float T0 = temperature[t], lat = grid.latitude[j], L = land[t], S = sea[t];
            const float hum = Sat(std::log(std::max(rain[t], 1.0f) / 100.0f) / std::log(30.0f));
            const float broken = Sat(0.5f + 0.8f * nLarge[t] + 0.3f * nMeso[t]);
            const float detail = nThickness[t];
            Clouds small, layers, shields, connected;
            float clearing = 0.0f, warmClearing = 0.0f;

            // Clear by default. Small opaque grains belong only to wet warm land, broken decks, their downstream
            // trades, and the maritime cold sectors. Every regime fades to zero; no marine, land or rail background.
            small.Add(L * Smooth(1000.0f, 1600.0f, rain[t]) * Smooth(15.0f, 22.0f, T0)
                       * (0.20f + 0.10f * broken), 0.85f, 0.25f);

            // Only organized layers get mesoscale holes: a line of convective clusters, wet land convection,
            // stratocumulus decks, polar stratus, and the windward banks. The two textures have no stretched streets.
            const float width = Radians(kItczHalfWidth * (1.0f + 0.20f * nLarge[t]));
            const float fromItcz = (lat - itcz[i] - Radians(0.7f) * warp[t] - (70.0f / R) * nFine[t]) / width;
            const float itczBand = std::exp(-fromItcz * fromItcz);
            const float convCore = Smooth(0.10f, -0.30f, textureConv[t]);
            const float convE = Thickness(0.4f + 0.6f * convCore, detail, 0.4f + 0.45f * convCore, 1.0f);
            layers.Add(itczBand * (0.46f + 0.22f * clusters[t]), 0.95f, convE, textureConv[t]);
            // Rain also locates the scattered convection away from the line, stronger over warm wet land.
            layers.Add((0.33f * S + 0.70f * L) * Smooth(1500.0f, 2400.0f, rain[t]) * Smooth(20.0f, 25.0f, T0)
                       * (0.85f + 0.15f * clusters[t]), 0.9f, convE, textureConv[t]);
            float B = 0.23f * std::exp(-fromItcz * fromItcz / 1.5f) * Smooth(0.58f, 0.88f, clustersWide[t]);

            // Sample the 500 km mean upwelling only where a warm marine deck can occur. The downstream breakup
            // becomes partial small-cloud cover; its 250-800 km deck holes alone are realized on the map.
            if (S > 0.01f && T0 > 2.0f && T0 < 26.0f) {
                const float speed = std::sqrt(windE[t] * windE[t] + windN[t] * windN[t]);
                const V3 flow = speed > 0.1f ? (east[t] * windE[t] + north[t] * windN[t]) * (1.0f / speed) : east[t];
                const float source0 = coldWide[t];
                const float source1 = grid.Sample(coldWide, Step(p[t], flow, -0.5f * kDeckCarryKm, R));
                const float source2 = grid.Sample(coldWide, Step(p[t], flow, -kDeckCarryKm, R));
                const float source = std::max(source0, std::max(0.86f * source1, 0.60f * source2));
                // The inversion is strongest over a cool subtropical sea beneath warm subsiding air.
                const float inversion = 1.8f - 1.10f * Smooth(12.0f, 20.0f, T0) * Smooth(26.0f, 22.0f, T0);
                const float deck = Smooth(0.35f, inversion, source + 0.18f * warp[t]) * sea150[t] * Smooth(2.0f, 12.0f, T0);
                const float open = Smooth(0.15f, 1.1f, source2 - source0) * (1.0f - Smooth(0.7f, 1.8f, source0));
                float deckE = 0.0f;
                if (deck > 0.0f) {
                    const V3 cells = Normalize(p[t] + V3{ 18.0f * warp[t], 16.0f * nMeso[t], 18.0f * nFine[t] } * (1.0f / R));
                    deckE = CellCore(cells, R / kDeckCellKm, seed ^ 137u) * Thickness(0.14f, detail, 0.0f, 0.2f);
                }
                layers.Add(deck * (1.0f - 0.8f * open) * 0.90f, 0.05f, deckE, textureDeck[t]);
                small.Add(deck * open * (0.30f + 0.20f * broken), 0.85f, 0.25f);
                if (windE[t] < -1.0f && source0 < 0.5f && source2 < 0.7f) {
                    const float tail = grid.Sample(coldWide, Step(p[t], flow, -kDeckCarryKm - kTradeFadeKm, R));
                    const float trades = Smooth(0.15f, 0.9f, tail) * (1.0f - Smooth(0.15f, 0.7f, source2))
                                       * (1.0f - Smooth(0.15f, 0.5f, source0)) * Smooth(-1.0f, -5.0f, windE[t]);
                    small.Add(sea150[t] * trades * (0.10f + 0.15f * broken), 0.85f, 0.25f);
                }
            }
            layers.Add(0.31f * S * Smooth(-8.0f, -18.0f, T0) + 0.29f * L * Smooth(-6.0f, -18.0f, T0),
                       0.1f, Thickness(0.175f, detail, 0.1f, 0.25f), textureDeck[t]);

            // Keep the slope metric and lift thresholds of the existing 120 km orographic law.
            const float dy = (groundWide[size_t(std::min(j + 1, h - 1)) * w + i] - groundWide[size_t(j > 0 ? j - 1 : 0) * w + i])
                           / (-(float(std::min(j + 1, h - 1)) - float(j > 0 ? j - 1 : 0)) * kPi * R * 1000.0f / h);
            const float dx = (groundWide[size_t(j) * w + (i + 1) % w] - groundWide[size_t(j) * w + (i + w - 1) % w])
                           / (2.0f * 2.0f * kPi * R * 1000.0f / w * std::max(std::cos(lat), 0.05f));
            const float up = windE[t] * dx + windN[t] * dy;
            layers.Add(0.82f * Smooth(0.02f, 0.12f, up) * Smooth(0.1f, 0.6f, hum), 0.45f,
                       Thickness(0.30f + 0.20f * Smooth(0.02f, 0.12f, up), detail, 0.3f, 0.5f), textureDeck[t]);
            const float lee = 1.0f - 0.85f * Smooth(0.015f, 0.1f, -up);

            for (const Cyclone& q : cyclones) {
                const float dot = Dot(p[t], q.c);
                if (dot < q.reach) continue;
                if (dot > q.headReach) {
                    const float ex = Dot(p[t], q.east), ny = Dot(p[t], q.north) * (q.south ? -1.0f : 1.0f);
                    const float sine = std::sqrt(ex * ex + ny * ny), distanceKm = R * std::atan2(sine, dot);
                    const float metric = distanceKm / std::max(sine, 1e-6f);
                    const float fade = 1.0f - Smooth(q.headKm - 500.0f, q.headKm, distanceKm);
                    const float X = (metric * (q.turnCos * ex - q.turnSin * ny) + 0.16f * q.scale * warp[t] + 60.0f * nFine[t]) / q.scale;
                    const float Y = (metric * (q.turnSin * ex + q.turnCos * ny) + 0.15f * q.scale * nMeso[t] + 60.0f * nFine[t]) / q.scale;
                    const float r = std::sqrt(X * X + Y * Y), theta = std::atan2(Y, X);
                    const float period = 2.0f * kPi / q.arms;
                    float phase = theta + 0.5f - std::log(1.0f / std::max(r, 0.02f)) / q.pitch;
                    phase -= period * std::round(phase / period);
                    const float d = std::fabs(phase) * r * q.scale * q.spiralNormal;
                    // The more closely spaced southern systems leave room for narrow intervening dry slots.
                    const float armWidth = (q.south ? 0.60f : 0.65f) * q.scale * (0.22f + 0.10f * q.stage)
                                         * (0.60f + 0.40f * std::min(r, 1.0f)) * (0.9f + 0.2f * clusters[t]);
                    const float arm = (1.0f - Smooth(0.55f * armWidth, armWidth, d))
                                    * (1.0f - Smooth(0.90f + 0.1f * warp[t], 1.25f + 0.1f * warp[t], r));
                    const float headE = Thickness(1.0f - 0.2f * Smooth(0.05f, 0.35f, r), detail, 0.8f, 1.0f);
                    const float head = 1.0f - Smooth(0.30f, 0.35f, r);
                    const float armE = Thickness(0.70f - 0.25f * Sat(r), detail, 0.45f, 0.7f);
                    connected.Add(fade * arm, 0.5f, (1.0f - head) * armE + head * headE);
                    connected.Add(Smooth(0.25f, 0.85f, q.stage) * (1.0f - Smooth(0.18f, 0.38f, r)), 0.5f, headE);
                    const float middle = 0.5f * period * r * q.scale * q.spiralNormal;
                    const float gapWidth = 0.065f * q.scale * (0.30f + 0.70f * std::min(r, 1.0f));
                    const float slot = (1.0f - Smooth(0.3f * gapWidth, gapWidth, std::fabs(middle - d)))
                                     * Smooth(0.15f, 0.25f, r) * (1.0f - Smooth(0.95f, 1.2f, r)) * (1.0f - arm);
                    clearing = std::max(clearing, slot);

                    // A connected warm shield, broader than the head's inner arms; cirrus only on its leading edge.
                    const float shieldScale = q.south ? 0.90f : 1.0f;
                    const float sx = (X - 0.65f) * q.scale / (1350.0f * shieldScale);
                    const float sy = (Y - 0.45f) * q.scale / (1000.0f * shieldScale);
                    const float shieldRadius = std::sqrt(sx * sx + sy * sy) + 0.12f * warp[t] + 0.08f * nFine[t];
                    shields.Add(fade * (1.0f - Smooth(0.65f, 1.15f, shieldRadius)), 0.45f,
                                Thickness(0.60f - 0.25f * Sat(r / 1.8f), detail, 0.35f, 0.6f));
                    B = std::max(B, 0.22f * fade * std::exp(-sx * sx - sy * sy) * Smooth(0.75f, 1.55f, X + 0.3f * Y));
                    const float warm = std::exp(-((X - 0.65f) * (X - 0.65f) + (Y + 0.9f) * (Y + 0.9f)) / 0.49f);
                    warmClearing = std::max(warmClearing, fade * warm);
                }
                if (S > 0.01f && Dot(p[t], q.wake) > q.wakeReach) {
                    const float ex = Dot(p[t], q.wakeEast), ny = Dot(p[t], q.wakeNorth) * (q.south ? -1.0f : 1.0f);
                    const float sine = std::sqrt(ex * ex + ny * ny);
                    const float metric = R * std::atan2(sine, Dot(p[t], q.wake)) / std::max(sine, 1e-6f);
                    const float wx = (ex * metric + 100.0f * warp[t]) / (0.6f * q.wakeKm), wy = (ny * metric + 100.0f * nMeso[t]) / 1400.0f;
                    // Distance westward from this low in units of the interval to the preceding one. Open cells
                    // begin behind the front, then fade before the inter-system ridge halfway along the interval.
                    const float back = 0.5f - 0.6f * wx;
                    const float wake = Smooth(-0.10f, 0.15f, back) * (1.0f - Smooth(0.25f, 0.60f, back))
                                     * (1.0f - Smooth(0.35f, 1.05f, std::fabs(wy)));
                    small.Add(S * wake * (0.35f + 0.15f * broken), 0.9f, 0.25f);
                }
                if (dot < q.frontReach) continue;
                float best = 1e30f, along = 0.0f, side = 0.0f, wave = 0.0f;
                for (const FrontSegment& segment : q.front) {
                    if (Dot(p[t], segment.middle) < segment.reach) continue;
                    const float u = Sat(Dot(p[t] - segment.a, segment.delta) * segment.inverseLength2);
                    const V3 delta = p[t] - (segment.a + segment.delta * u);
                    const float d2 = Dot(delta, delta);
                    if (d2 < best) {
                        best = d2, along = segment.along + (u - 0.5f) / float(q.front.size()), side = Dot(p[t], segment.normal);
                        wave = (1.0f - u) * segment.waveA + u * segment.waveB;
                    }
                }
                if (best < 1e29f) {
                    // A chord on a 120 km arc differs from its spherical foot by less than .3 km on Earth.
                    const float distance = 2.0f * R * std::asin(std::min(1.0f, 0.5f * std::sqrt(best)));
                    const float width = 0.5f * (kFrontNearKm + (kFrontTailKm - kFrontNearKm) * along)
                                      * (0.85f + 0.3f * clusters[t]) * (q.south ? 1.30f : 1.0f);
                    const float signedDistance = (side < 0.0f ? -distance : distance) + 0.15f * width * warp[t] + 45.0f * nFine[t];
                    const float end = 1.0f - Smooth(0.88f, 1.0f, along);
                    const float profile = 1.0f - Smooth(0.60f * width, width, std::fabs(signedDistance));
                    // Parallel flanks thin to .35; the axis varies over 400-800 km, from .75-1 down to .5 at the tail.
                    const float core = 1.0f - Smooth(0.0f, 0.85f, std::fabs(signedDistance) / width);
                    const float axis = (1.0f - along) * (0.875f + 0.125f * wave) + 0.50f * along;
                    const float frontE = Thickness(0.35f + (axis - 0.35f) * core, detail * core,
                                                   0.35f + (0.40f - 0.25f * along) * core,
                                                   0.35f + (0.65f - 0.50f * along) * core);
                    connected.Add(profile * end, 0.6f, frontE);
                    const float laneWidth = q.south ? 130.0f + 80.0f * clusters[t] : 180.0f + 100.0f * clusters[t];
                    const float laneCentre = width + 0.65f * laneWidth;
                    const float lane = 1.0f - Smooth(0.3f * laneWidth, 0.6f * laneWidth, std::fabs(signedDistance + laneCentre));
                    clearing = std::max(clearing, lane * end * (1.0f - profile));
                    const float warm = Smooth(width, width + 150.0f, signedDistance)
                                     * (1.0f - Smooth(width + 300.0f, width + 500.0f, signedDistance));
                    warmClearing = std::max(warmClearing, warm * end);
                }
            }
            const float a = std::fabs(lat) * (180.0f / kPi), jetBelt = Bell(a, 31.0f, 5.0f) * Smooth(-4.0f, 2.0f, windE[t]);
            if (jetBelt > 0.01f) {
                const float jet = SphereNoise(p[t], 700.0f, 2, seed ^ 71u, R, 4.0f);
                B = std::max(B, 0.20f * jetBelt * Smooth(0.18f, 0.48f, jet));
            }
            const float leeRetention = 1.0f - (1.0f - lee) * (1.0f - Smooth(2.0f, -12.0f, T0));
            const float desert = L * Smooth(5.0f, 10.0f, T0) * (1.0f - Smooth(250.0f, 280.0f, rain[t]));
            CloudField grains = small.Resolve(0.50f);
            // Shallow grains reform in the lee; organized banks retain the full clearing below.
            grains.coverage *= 0.40f + 0.60f * leeRetention;
            // Subsidence removes cloud; clearing never adds a floor of small grains back into empty sky.
            grains.coverage *= (1.0f - warmClearing) * (1.0f - clearing) * (1.0f - desert);
            smallField[t] = grains;
            CloudField bank = layers.Resolve();
            bank.coverage *= leeRetention * (1.0f - clearing) * (1.0f - 0.8f * warmClearing) * (1.0f - desert);
            layerField[t] = bank;
            textureField[t] = layers.weight > 1e-12f ? layers.noise / layers.weight : textureDeck[t];
            Clouds masses;
            masses.Merge(shields, (1.0f - clearing) * (1.0f - 0.8f * warmClearing));
            masses.Merge(connected);
            CloudField mass = masses.Resolve();
            mass.coverage = Smooth(0.20f, 0.80f, mass.coverage) * (1.0f - desert);
            massField[t] = mass;
            cirrusField[t] = B * Smooth(0.025f, 0.12f, B);
        });
        UniformArea(textureField, grid);
        std::vector<CloudField> resolvedField(texels);
        ForCells(texels, [&](uint32_t t) {
            const CloudField small = smallField[t], mass = massField[t], layer = layerField[t];
            const float o = layer.coverage >= 0.97f ? 1.0f : Sat((layer.coverage - textureField[t]) / 0.07f + 0.5f);
            Clouds result;
            result.Add(small.coverage, small.family, small.thickness);
            result.Add(mass.coverage, mass.family, mass.thickness);
            result.Add(o, layer.family, layer.thickness);
            resolvedField[t] = result.Resolve();
        });

        // Distance to the existing opaque contour, in km, without changing its coverage. Circular row sweeps find
        // the nearest clear texel; a few adjacent rows complete the 80 km distance to its footprint. No iterative fill.
        std::vector<float> edgeSquared(texels);
        ForCells(h, [&](uint32_t j) {
            const float dx = grid.texelKm * std::cos(grid.latitude[j]);
            const int limit = int(std::ceil(kEdgeMaxKm / dx)) + 1;
            const size_t row = size_t(j) * w;
            int run = limit;
            for (int k = 0; k < 2 * int(w); ++k) {
                const uint32_t i = uint32_t(k) % w;
                run = resolvedField[row + i].coverage < 0.97f ? 0 : std::min(run + 1, limit);
                const float d = std::min(kEdgeMaxKm, std::max(0.0f, (run - 0.5f) * dx));
                if (k >= int(w)) edgeSquared[row + i] = d * d;
            }
            run = limit;
            for (int k = 2 * int(w) - 1; k >= 0; --k) {
                const uint32_t i = uint32_t(k) % w;
                run = resolvedField[row + i].coverage < 0.97f ? 0 : std::min(run + 1, limit);
                const float d = std::min(kEdgeMaxKm, std::max(0.0f, (run - 0.5f) * dx));
                if (k < int(w)) edgeSquared[row + i] = std::min(edgeSquared[row + i], d * d);
            }
        });
        const int edgeRows = int(std::ceil(kEdgeMaxKm / grid.texelKm));
        ForCells(texels, [&](uint32_t t) {
            const CloudField all = resolvedField[t];
            float e = all.thickness;
            if (all.coverage >= 0.97f) {
                float d2 = kEdgeMaxKm * kEdgeMaxKm;
                for (int dj = -edgeRows; dj <= edgeRows; ++dj) {
                    int j = int(t / w) + dj;
                    uint32_t i = t % w;
                    // Across either pole, north continues half a longitude turn away.
                    if (j < 0) j = -1 - j, i = (i + w / 2) % w;
                    if (j >= int(h)) j = 2 * int(h) - 1 - j, i = (i + w / 2) % w;
                    const float dy = std::max(0.0f, (std::fabs(float(dj)) - 0.5f) * grid.texelKm);
                    d2 = std::min(d2, edgeSquared[size_t(j) * w + i] + dy * dy);
                }
                const float width = kEdgeKm + kEdgeWarpKm * std::min(1.0f, std::max(-1.0f, 2.0f * nEdge[t]));
                e *= Smooth(0.0f, width, std::sqrt(d2));
            }
            const float control = CloudControl(all.coverage, e);
            uint8_t* out = &base[size_t(t) * 4];
            out[0] = uint8_t(std::nearbyint(control * 255.0f));
            out[1] = control > 0.0f ? uint8_t(std::nearbyint(Sat(all.family) * 255.0f)) : 0;
            out[2] = uint8_t(std::nearbyint(std::min(cirrusField[t], 73.0f / 255.0f) * 255.0f));
            out[3] = 0;
        });

        // The mips: 2 x 2 means; from mip 2, R and B the maxima, so that a cell's emptiness is proven (Clouds.hlsli).
        std::vector<uint8_t> all(base);
        size_t from = 0;
        for (uint32_t level = 1, pw = w, ph = h; level < WeatherMips; ++level) {
            const uint32_t nw = std::max(pw / 2, 1u), nh = std::max(ph / 2, 1u), fx = pw > 1 ? 2 : 1, fy = ph > 1 ? 2 : 1;
            const size_t to = all.size();
            all.resize(to + size_t(nw) * nh * 4);
            for (uint32_t j = 0; j < nh; ++j)
                for (uint32_t i = 0; i < nw; ++i)
                    for (int c = 0; c < 4; ++c) {
                        float sum = 0.0f;
                        uint8_t most = 0;
                        for (uint32_t b = 0; b < fy; ++b)
                            for (uint32_t a = 0; a < fx; ++a) {
                                const uint8_t value = all[from + (size_t(j * fy + b) * pw + i * fx + a) * 4 + c];
                                sum += value, most = std::max(most, value);
                            }
                        all[to + (size_t(j) * nw + i) * 4 + c] = level >= 2 && (c == 0 || c == 2) ? most
                                                                : uint8_t(std::nearbyint(sum / float(fx * fy)));
                    }
            from = to, pw = nw, ph = nh;
        }
        return all;
    }
}
