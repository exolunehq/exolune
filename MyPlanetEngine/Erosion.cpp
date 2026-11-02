// Erosion.cpp - the erosion's level 0 (Erosion.h; docs/spec-erosion.md). Exolune's own code: Priority-Flood after Barnes,
// Lehman and Mulla 2014, as PlanetMap.cpp; the lakes' water balance, the stream power's steady state and the glaciers'
// mass balance after the papers the spec cites. Deterministic, on one thread. Compiled optimised even in Debug
// (MyPlanetEngine.vcxproj).
#include "Erosion.h"
#include "Tectonics.h"
#include "Climate.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <immintrin.h>

namespace Erosion
{
    namespace
    {
        const uint32_t None = 0xffffffffu;
        const double kNoOutlet = -1e30;
        // The stream power's steady state, S = ks A^-theta (Kirby and Whipple 2012), A the area drained at the reference
        // runoff: a drier basin is steeper. ks (m^0.9) has a background, the plains', and grows with the uplift U (mm/yr)
        // over the erodibility K as sqrt(U / K), the slope exponent n = 2 measured on Earth's ranges: 150 at 1 mm/yr, 330 at
        // 5, the Himalaya's.
        const double kTheta = 0.45, kSteepPlains = 30.0, kSteepUplift = 150.0, kReferenceRunoff = 0.5;
        // The incision reaches upstream at a finite pace, the knickpoints' (Tzathas et al. 2024: the stream power's
        // characteristics): their celerity K A^m, m = 0.5; over the time of the relief, a river of kReachArea (m2) at K = 1
        // has carried it kReach (m) from its outlet. Beyond, the ground keeps its form: plateaus whose edges only are cut.
        const double kReach = 1.0e6, kReachArea = 1.0e11;
        const double kLakeDepth = 1.0; // m: a cell of a depression is filled higher than this
        const double kLapse = 6.5e-3;  // K/m
        // The glacial valleys the relief shows are the last glacial maximum's, its equilibrium line some 900 m below
        // today's; the mass balance grows by 0.6 m/yr per 100 m, at most 2 m/yr and the precipitation.
        const double kGlacialLowering = 900.0, kBalanceGradient = 0.006, kMostAccumulation = 2.0;
        const double kSecondsPerYear = 3.15576e7;
        // A fan where a river leaves a valley deeper than kFanIncision (m) for a ground where it cuts less than kFanDrop of
        // that: the mountain front, where the slope falls and the load settles.
        const double kFanIncision = 200.0, kFanDrop = 0.25;

        struct V3 { double x, y, z; };

        // The computed year's precipitation (m/yr), sea-level temperature (C), as Erosion.hlsli.
        void ErosionClimate(const Climate::Map& climate, const V3& d, double& precipitation, double& seaTemperature)
        {
            const double direction[3] = { d.x, d.y, d.z };
            float fields[Climate::Channels];
            Climate::At(climate, direction, fields);
            precipitation = 0.001 * fields[Climate::Precipitation];
            seaTemperature = fields[Climate::Temperature];
        }

        // Potential evapotranspiration (m/yr) at a temperature (C).
        double Evaporation(double t) { return 0.1 + 0.05 * std::max(t, 0.0); }

        // The cube's cells, face by face, row by row, D3D's cube map layout, as Tectonics.cpp's.
        struct Cube
        {
            uint32_t n, cells;
            std::vector<V3> p; // each cell's centre on the unit sphere

            explicit Cube(uint32_t size) : n(size), cells(6 * size * size), p(cells)
            {
                for (uint32_t c = 0; c < cells; ++c) {
                    const V3 d = Direction(c / (n * n), Coordinate(c % n), Coordinate(c / n % n));
                    const double l = std::sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
                    p[c] = { d.x / l, d.y / l, d.z / l };
                }
            }
            double Coordinate(int i) const { return (i + 0.5) * 2.0 / n - 1.0; }
            static V3 Direction(uint32_t f, double s, double t)
            {
                const V3 table[6] = { { 1.0, -t, -s }, { -1.0, -t, s }, { s, 1.0, t }, { s, -1.0, -t }, { s, -t, 1.0 }, { -s, -t, -1.0 } };
                return table[f];
            }
            uint32_t CellOf(const V3& d) const
            {
                const double ax = std::fabs(d.x), ay = std::fabs(d.y), az = std::fabs(d.z);
                uint32_t f;
                double ma, sc, tc;
                if (ax >= ay && ax >= az) f = d.x > 0.0 ? 0 : 1, ma = ax, sc = d.x > 0.0 ? -d.z : d.z, tc = -d.y;
                else if (ay >= az)        f = d.y > 0.0 ? 2 : 3, ma = ay, sc = d.x, tc = d.y > 0.0 ? d.z : -d.z;
                else                      f = d.z > 0.0 ? 4 : 5, ma = az, sc = d.z > 0.0 ? d.x : -d.x, tc = -d.y;
                auto texel = [&](double v) { return (uint32_t)std::min(std::max(std::floor((v / ma + 1.0) * 0.5 * n), 0.0), n - 1.0); };
                return (f * n + texel(tc)) * n + texel(sc);
            }
            // The 8 neighbours of c, row by row, dj then di from -1 to 1; across a face's edge, the cell beyond it. Their
            // index is the receiver's code (Erosion.hlsli).
            void Neighbours(uint32_t c, uint32_t* a) const
            {
                const uint32_t face = c / (n * n), j = c / n % n, i = c % n;
                if (i > 0 && j > 0 && i + 1 < n && j + 1 < n) { // inside the face, by their rows
                    a[0] = c - n - 1, a[1] = c - n, a[2] = c - n + 1, a[3] = c - 1, a[4] = c + 1, a[5] = c + n - 1, a[6] = c + n, a[7] = c + n + 1;
                    return;
                }
                for (int dj = -1; dj <= 1; ++dj)
                    for (int di = -1; di <= 1; ++di) {
                        if (!di && !dj) continue;
                        const int ii = int(i) + di, jj = int(j) + dj;
                        *a++ = ii >= 0 && jj >= 0 && ii < int(n) && jj < int(n) ? c + dj * int(n) + di
                                                                                 : CellOf(Direction(face, Coordinate(ii), Coordinate(jj)));
                    }
            }
            double Area(uint32_t c) const // on the unit sphere, the cube's area element (1 + s^2 + t^2)^-1.5
            {
                const double s = Coordinate(c % n), t = Coordinate(c / n % n), r = 1.0 + s * s + t * t;
                return 4.0 / (double(n) * n) / (r * std::sqrt(r));
            }
            double Chord(uint32_t a, uint32_t b) const
            {
                const double x = p[a].x - p[b].x, y = p[a].y - p[b].y, z = p[a].z - p[b].z;
                return std::sqrt(x * x + y * y + z * z);
            }
        };

        // Priority-Flood (Barnes, Lehman and Mulla 2014, algorithm 3), as PlanetMap::Drain: from the outlets, the sea and
        // the lakes at their levels, the lowest first; a cell not yet reached takes the level of the one reaching it if it
        // lies lower, a pit, or its own. Each cell's filled level, the cell it was reached from, and the flood's order.
        void Flood(const Cube& cube, const std::vector<double>& e, const std::vector<double>& outlet, std::vector<double>& filled,
                   std::vector<uint32_t>& from, std::vector<uint32_t>& order)
        {
            const uint32_t cells = cube.cells;
            filled.assign(cells, 0.0);
            from.assign(cells, None);
            order.clear();
            order.reserve(cells);
            std::vector<uint8_t> reached(cells, 0);
            std::vector<uint32_t> pit(cells), heapCell(cells);
            std::vector<double> heapLevel(cells);
            size_t pits = 0, next = 0, open = 0;
            auto push = [&](double level, uint32_t cell) {
                size_t i = open++;
                for (; i > 0 && heapLevel[(i - 1) / 2] > level; i = (i - 1) / 2) heapLevel[i] = heapLevel[(i - 1) / 2], heapCell[i] = heapCell[(i - 1) / 2];
                heapLevel[i] = level, heapCell[i] = cell;
            };
            auto pop = [&]() {
                const uint32_t top = heapCell[0], cell = heapCell[--open];
                const double level = heapLevel[open];
                size_t i = 0;
                for (size_t child; (child = 2 * i + 1) < open; i = child) {
                    if (child + 1 < open && heapLevel[child + 1] < heapLevel[child]) ++child;
                    if (heapLevel[child] >= level) break;
                    heapLevel[i] = heapLevel[child], heapCell[i] = heapCell[child];
                }
                heapLevel[i] = level, heapCell[i] = cell;
                return top;
            };
            for (uint32_t c = 0; c < cells; ++c)
                if (outlet[c] > kNoOutlet) reached[c] = 1, filled[c] = outlet[c], push(outlet[c], c);
            uint32_t around[8];
            for (;;) {
                uint32_t c;
                if (next < pits) c = pit[next++];
                else if (open > 0) c = pop();
                else break;
                order.push_back(c);
                const double level = filled[c];
                cube.Neighbours(c, around);
                for (uint32_t m : around) {
                    if (reached[m]) continue;
                    reached[m] = 1, from[m] = c;
                    if (e[m] <= level) filled[m] = level, pit[pits++] = m;
                    else filled[m] = e[m], push(e[m], m);
                }
            }
        }

        // The cells in the order of the network, every receiver before the cells that drain into it: from the outlets, by
        // the reversed links.
        std::vector<uint32_t> Stack(const std::vector<uint32_t>& receiver)
        {
            const uint32_t cells = uint32_t(receiver.size());
            std::vector<uint32_t> start(cells + 1, 0), kids;
            for (uint32_t c = 0; c < cells; ++c) if (receiver[c] != None) ++start[receiver[c] + 1];
            for (uint32_t c = 0; c < cells; ++c) start[c + 1] += start[c];
            std::vector<uint32_t> at(start.begin(), start.end() - 1);
            kids.resize(start[cells]);
            for (uint32_t c = 0; c < cells; ++c) if (receiver[c] != None) kids[at[receiver[c]]++] = c;
            std::vector<uint32_t> order;
            order.reserve(cells);
            for (uint32_t c = 0; c < cells; ++c) if (receiver[c] == None) order.push_back(c);
            for (size_t head = 0; head < order.size(); ++head)
                for (uint32_t k = start[order[head]]; k < start[order[head] + 1]; ++k) order.push_back(kids[k]);
            return order;
        }

        uint32_t Level16(double m) { return uint32_t(std::min(std::max(std::lround((m + 8192.0) * 4.0), 0l), 65535l)); }
    }

    Map Build(const Tectonics::Map& tectonics, const Climate::Map& climate, const std::vector<float>& form, double radiusKm)
    {
        const auto start = std::chrono::steady_clock::now();
        Map map;
        const uint32_t n = tectonics.size, w = n + 2 * Tectonics::Pad;
        map.size = n;
        const Cube cube(n);
        const uint32_t cells = cube.cells;
        const double radius = radiusKm * 1000.0;

        // The inputs, by cell: the form, the uplift and the erodibility at the tectonic map's texel, the climate.
        auto texel = [&](uint32_t c, uint32_t slice, uint32_t channel) {
            const uint32_t face = c / (n * n), j = c / n % n + Tectonics::Pad, i = c % n + Tectonics::Pad;
            const uint16_t h = tectonics.texels[(((size_t(face) * Tectonics::Slices + slice) * w + j) * w + i) * 4 + channel];
            return _mm_cvtss_f32(_mm_cvtph_ps(_mm_cvtsi32_si128(h)));
        };
        std::vector<double> e(cells), area(cells), runoff(cells), evaporation(cells), precipitation(cells), seaT(cells);
        std::vector<uint8_t> sea(cells);
        for (uint32_t c = 0; c < cells; ++c) {
            e[c] = form[c], sea[c] = form[c] < 0.0f;
            area[c] = cube.Area(c) * radius * radius;
            ErosionClimate(climate, cube.p[c], precipitation[c], seaT[c]);
            const double t = seaT[c] - kLapse * std::max(e[c], 0.0), p = precipitation[c];
            // The runoff by Schreiber's curve; a lake evaporates more than the land, less the rain on it.
            runoff[c] = sea[c] || p <= 0.0 ? 0.0 : p * std::exp(-Evaporation(t) / p);
            evaporation[c] = sea[c] ? 0.0 : std::max(1.2 * Evaporation(t) + 0.2 - p, 0.0);
        }

        // 1. The drainage from the sea; the depressions, each filled higher than kLakeDepth. A body without a sea drains
        // to its lowest cell, a basin like the others.
        std::vector<double> outlet(cells), filled;
        std::vector<uint32_t> from, order;
        for (uint32_t c = 0; c < cells; ++c) outlet[c] = sea[c] ? 0.0 : kNoOutlet;
        if (std::find(sea.begin(), sea.end(), 1) == sea.end()) {
            const uint32_t lowest = uint32_t(std::min_element(e.begin(), e.end()) - e.begin());
            outlet[lowest] = e[lowest];
        }
        Flood(cube, e, outlet, filled, from, order);
        std::vector<uint32_t> region(cells, None), stackCells;
        uint32_t regions = 0, around[8];
        for (uint32_t s = 0; s < cells; ++s) {
            if (sea[s] || filled[s] - e[s] <= kLakeDepth || region[s] != None) continue;
            region[s] = regions, stackCells.assign(1, s);
            while (!stackCells.empty()) {
                const uint32_t c = stackCells.back();
                stackCells.pop_back();
                cube.Neighbours(c, around);
                for (uint32_t m : around)
                    if (region[m] == None && !sea[m] && filled[m] - e[m] > kLakeDepth) region[m] = regions, stackCells.push_back(m);
            }
            ++regions;
        }

        // 2. The lakes by their water balance: a depression keeps a terminal lake when the water reaching it is less than
        // what all of it would evaporate; the water of a closed depression stays there. Its level: its lowest cells, until
        // they evaporate what comes in. The others overflow, filled with sediments: plains.
        std::vector<uint32_t> entry(regions, None);
        std::vector<double> capacity(regions, 0.0), inflow(regions, 0.0), water(cells);
        std::vector<uint8_t> closed(regions, 0);
        for (uint32_t c : order) if (region[c] != None && entry[region[c]] == None) entry[region[c]] = c;
        for (uint32_t c = 0; c < cells; ++c) {
            water[c] = runoff[c] * area[c];
            if (region[c] != None) capacity[region[c]] += area[c] * evaporation[c];
        }
        for (size_t k = order.size(); k-- > 0;) {
            const uint32_t c = order[k], g = region[c];
            if (sea[c]) continue;
            if (g != None && entry[g] == c && water[c] < capacity[g]) { closed[g] = 1, inflow[g] = water[c]; continue; }
            if (from[c] != None) water[from[c]] += water[c];
        }
        struct Low { uint32_t region; double e; uint32_t cell; };
        std::vector<Low> lows;
        for (uint32_t c = 0; c < cells; ++c) if (region[c] != None && closed[region[c]]) lows.push_back({ region[c], e[c], c });
        std::sort(lows.begin(), lows.end(), [](const Low& a, const Low& b) { return a.region != b.region ? a.region < b.region : a.e != b.e ? a.e < b.e : a.cell < b.cell; });
        std::vector<double> lakeLevel(cells, kNoOutlet);
        for (size_t i = 0, j; i < lows.size(); i = j) {
            const uint32_t g = lows[i].region;
            double sum = 0.0, level = lows[i].e;
            for (j = i; j < lows.size() && lows[j].region == g; ++j)
                if (sum < inflow[g]) sum += area[lows[j].cell] * evaporation[lows[j].cell], level = lows[j].e;
            for (size_t k = i; k < j && lows[k].e <= level; ++k) lakeLevel[lows[k].cell] = level;
        }
        for (uint32_t c = 0; c < cells; ++c) outlet[c] = sea[c] ? 0.0 : std::max(lakeLevel[c], outlet[c]);
        std::vector<double> e2(e);
        for (uint32_t c = 0; c < cells; ++c) if (outlet[c] > kNoOutlet) e2[c] = outlet[c];
        Flood(cube, e2, outlet, filled, from, order);

        // 3. The routing: each cell to its steepest lower neighbour on the filled surface, a flat after the flood; the
        // area and the runoff drained. The eight directions' straight runs broken, after rho8 (Fairfield and Leymarie
        // 1991) but evenly: each neighbour's slope weighed by 1 +- 15 %, drawn by cell and neighbour, so that a path
        // wavers between the two directions around the slope and follows it in the mean.
        std::vector<uint32_t> receiver(cells, None);
        std::vector<double> length(cells, 0.0);
        for (uint32_t c = 0; c < cells; ++c) {
            if (outlet[c] > kNoOutlet) continue;
            cube.Neighbours(c, around);
            uint32_t best = None;
            double steepest = 0.0;
            for (uint32_t k = 0; k < 8; ++k) {
                const uint32_t m = around[k];
                uint32_t h = c * 8u + k;
                h ^= h >> 16, h *= 0x7feb352du, h ^= h >> 15, h *= 0x846ca68bu, h ^= h >> 16; // lowbias32
                const double s = (filled[c] - filled[m]) / cube.Chord(c, m) * (0.85 + 0.3 * double(h >> 8) / 16777216.0);
                if (s > steepest) steepest = s, best = m;
            }
            receiver[c] = best == None ? from[c] : best;
            length[c] = cube.Chord(c, receiver[c]) * radius;
        }
        order = Stack(receiver);
        std::vector<double> drained(cells), ice(cells);
        for (uint32_t c = 0; c < cells; ++c) drained[c] = outlet[c] > kNoOutlet ? 0.0 : runoff[c] * area[c];
        for (size_t k = order.size(); k-- > 0;) if (receiver[order[k]] != None) drained[receiver[order[k]]] += drained[order[k]];

        // 4. The water's level, from the outlets upstream: the steady state's slope over each link, never above the filled
        // surface; where the steady state would stand higher, the river flows on its plain. Past the knickpoints' reach,
        // the filled surface itself, over a quarter of the reach on either side.
        std::vector<double> level(cells), reach(cells, 0.0);
        for (uint32_t c : order) {
            if (receiver[c] == None) { level[c] = outlet[c]; continue; }
            const double u = std::max(double(texel(c, 3, 2)), 0.0), k = std::max(double(texel(c, 4, 0)), 0.05);
            const double steepness = std::sqrt(kSteepPlains * kSteepPlains + kSteepUplift * kSteepUplift * u) / std::sqrt(k);
            const double effective = std::max(drained[c] / kReferenceRunoff, area[c]);
            const double steady = std::min(filled[c], level[receiver[c]] + steepness * std::pow(effective, -kTheta) * length[c]);
            reach[c] = reach[receiver[c]] + length[c] / (k * std::sqrt(effective / kReachArea));
            const double t = std::min(std::max((reach[c] / kReach - 0.75) * 2.0, 0.0), 1.0);
            level[c] = steady + t * t * (3.0 - 2.0 * t) * (filled[c] - steady);
        }

        // A terminal lake's stage belongs to its whole catchment, including dry banks. The actual terrain determines
        // its detailed shoreline. The existing receiver order propagates the same stage upstream without a new solve.
        std::vector<double> terminalStage(cells, 0.0);
        std::vector<uint32_t> terminalBasin(cells, 0u);
        for (uint32_t c : order) {
            if (receiver[c] != None) {
                terminalStage[c] = terminalStage[receiver[c]];
                terminalBasin[c] = terminalBasin[receiver[c]];
            } else if (!sea[c] && lakeLevel[c] > kNoOutlet) {
                terminalStage[c] = lakeLevel[c];
                terminalBasin[c] = region[c] + 1u;
            }
        }

        // 5. The ice: under the glacial maximum's equilibrium line, the summer temperature there after the precipitation
        // (Ohmura, Kasser and Funk 1992: P = 645 + 296 T + 9 T^2, mm and C), the year's 8 C colder. Each cell's balance, then
        // downstream along the network: the ice that comes in, plus its own balance where it has ice.
        for (size_t k = order.size(); k-- > 0;) {
            const uint32_t c = order[k];
            if (outlet[c] > kNoOutlet) { ice[c] = 0.0; continue; }
            const double p = precipitation[c] * 1000.0;
            const double summer = (-296.0 + std::sqrt(296.0 * 296.0 - 36.0 * (645.0 - p))) / 18.0;
            const double line = (seaT[c] - (summer - 8.0)) / kLapse - kGlacialLowering;
            const double balance = std::min(kBalanceGradient * (e[c] - line), std::min(kMostAccumulation, precipitation[c]));
            ice[c] += balance > 0.0 || ice[c] > 0.0 ? balance * area[c] : 0.0;
            if (receiver[c] != None && ice[c] > 0.0) ice[receiver[c]] += ice[c];
        }

        // 6. The texels (Erosion.h).
        map.texels.assign(size_t(cells) * 4, 0u);
        double land = 0.0, lakes = 0.0, iced = 0.0;
        for (uint32_t c = 0; c < cells; ++c) {
            const bool lake = !sea[c] && lakeLevel[c] > kNoOutlet;
            const double ground = sea[c] ? e[c] : lake ? lakeLevel[c] : filled[c];
            uint32_t bits = (lake ? Lake : 0) | (sea[c] ? Sea : 0);
            if (receiver[c] != None) {
                cube.Neighbours(c, around);
                for (uint32_t k = 0; k < 8; ++k) if (around[k] == receiver[c]) { bits |= k | HasReceiver; break; }
                cube.Neighbours(receiver[c], around);
                for (uint32_t k = 0; k < 8; ++k) if (around[k] == c) { map.texels[2 * size_t(receiver[c]) + 1] |= 1u << (4 + k); break; }
                if (sea[receiver[c]]) bits |= Mouth;
                const double cut = filled[c] - level[c], below = filled[receiver[c]] - level[receiver[c]];
                if (outlet[receiver[c]] <= kNoOutlet && ice[receiver[c]] <= 0.0 && cut > kFanIncision && below < kFanDrop * cut) bits |= Fan;
            }
            const double q = drained[c] / kSecondsPerYear;
            bits |= uint32_t(std::min(std::max(std::lround(8.0 * (std::log2(std::max(q, 1e-9)) + 8.0)), 0l), 255l)) << 16;
            if (ice[c] > 0.0) bits |= uint32_t(std::min(std::max(std::lround(1.0 + 6.0 * (std::log2(ice[c]) - 10.0)), 1l), 255l)) << 24;
            map.texels[2 * size_t(c)] = Level16(level[c]) | Level16(ground) << 16;
            map.texels[2 * size_t(c) + 1] |= bits;
            map.texels[2 * size_t(cells + c)] = Level16(terminalStage[c]);
            map.texels[2 * size_t(cells + c) + 1] = terminalBasin[c];
            if (!sea[c]) land += area[c], lakes += lake ? area[c] : 0.0, iced += ice[c] > 0.0 ? area[c] : 0.0;
        }
        map.lakeShare = float(lakes / land), map.iceShare = float(iced / land);
        map.ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
        return map;
    }

    const char kMagic[8] = { 'E', 'X', 'O', 'E', 'R', 'O', 'S', '3' };

    bool Save(const Map& map, uint32_t seed, uint64_t key, const std::wstring& path)
    {
        FILE* f = nullptr;
        if (_wfopen_s(&f, (path + L".tmp").c_str(), L"wb") != 0 || !f) return false;
        const uint32_t header[2] = { seed, map.size };
        bool ok = fwrite(kMagic, 1, 8, f) == 8 && fwrite(header, 4, 2, f) == 2 && fwrite(&key, 8, 1, f) == 1
               && fwrite(map.texels.data(), 4, map.texels.size(), f) == map.texels.size();
        ok = fclose(f) == 0 && ok;
        if (!ok) return false;
        _wremove(path.c_str());
        return _wrename((path + L".tmp").c_str(), path.c_str()) == 0;
    }

    bool Load(Map& map, uint64_t key, const std::wstring& path)
    {
        FILE* f = nullptr;
        if (_wfopen_s(&f, path.c_str(), L"rb") != 0 || !f) return false;
        char magic[8] = {};
        uint32_t header[2] = {};
        uint64_t stored = 0;
        bool ok = fread(magic, 1, 8, f) == 8 && std::equal(magic, magic + 8, kMagic) && fread(header, 4, 2, f) == 2
               && fread(&stored, 8, 1, f) == 1 && stored == key;
        if (ok) {
            map.size = header[1];
            map.texels.resize(size_t(6) * map.size * map.size * 4);
            ok = fread(map.texels.data(), 4, map.texels.size(), f) == map.texels.size();
        }
        fclose(f);
        return ok;
    }

    uint64_t Key(const std::vector<float>& form, const Climate::Map& climate, uint32_t seed, uint64_t executableTime)
    {
        uint64_t h = 0xcbf29ce484222325ull; // FNV-1a, 64 bits
        auto add = [&](const void* data, size_t bytes) {
            for (size_t i = 0; i < bytes; ++i) h = (h ^ static_cast<const uint8_t*>(data)[i]) * 0x100000001b3ull;
        };
        add(form.data(), form.size() * sizeof(float));
        add(&climate.size, sizeof(climate.size));
        add(climate.cells.data(), climate.cells.size() * sizeof(float));
        add(&seed, sizeof(seed));
        add(&executableTime, sizeof(executableTime));
        return h;
    }
}
