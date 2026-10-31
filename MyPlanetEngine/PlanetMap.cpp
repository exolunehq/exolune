// PlanetMap.cpp - the planet map drained (PlanetMap.h). Compiled optimised even in Debug (MyPlanetEngine.vcxproj): the
// flood goes through 6.3 million cells at every startup. tools/banc_carte.py checks it against its own flood.
#include "PlanetMap.h"
#include <cmath>
#include <immintrin.h>

namespace PlanetMap
{
    namespace
    {
        const double kRadiusKm = 6378.0; // PLANET_RADIUS_KM

        // The direction of the point (s, t) of face f, not normalised; s and t past [-1, 1] go beyond the face's edge.
        // As CubeDirection in PlanetMap.hlsli.
        void FaceDirection(uint32_t f, double s, double t, double d[3])
        {
            const double table[6][3] = { { 1.0, -t, -s }, { -1.0, -t, s }, { s, 1.0, t }, { s, -1.0, -t }, { s, -t, 1.0 }, { -s, -t, -1.0 } };
            d[0] = table[f][0], d[1] = table[f][1], d[2] = table[f][2];
        }

        // The cell holding direction d: D3D's choice of face and coordinates for a cube map.
        uint32_t CellOf(const double d[3])
        {
            const double ax = std::fabs(d[0]), ay = std::fabs(d[1]), az = std::fabs(d[2]);
            uint32_t f;
            double ma, sc, tc;
            if (ax >= ay && ax >= az) f = d[0] > 0.0 ? 0 : 1, ma = ax, sc = d[0] > 0.0 ? -d[2] : d[2], tc = -d[1];
            else if (ay >= az)        f = d[1] > 0.0 ? 2 : 3, ma = ay, sc = d[0], tc = d[1] > 0.0 ? d[2] : -d[2];
            else                      f = d[2] > 0.0 ? 4 : 5, ma = az, sc = d[2] > 0.0 ? d[0] : -d[0], tc = -d[1];
            auto texel = [](double x) { return (uint32_t)std::fmin(std::fmax(std::floor((x + 1.0) * 0.5 * Size), 0.0), Size - 1.0); };
            return (f * Size + texel(tc / ma)) * Size + texel(sc / ma);
        }

        // Calls f with each of the 8 neighbours of cell c; across a face's edge, the cell beyond it. At the cube's corners
        // one neighbour comes twice.
        template <class F> void ForNeighbours(uint32_t c, F f)
        {
            const uint32_t face = c / (Size * Size), j = c / Size % Size, i = c % Size;
            for (int dj = -1; dj <= 1; ++dj)
                for (int di = -1; di <= 1; ++di) {
                    if (!di && !dj) continue;
                    const int ii = int(i) + di, jj = int(j) + dj;
                    if (ii >= 0 && jj >= 0 && ii < int(Size) && jj < int(Size)) { f(c + dj * int(Size) + di); continue; }
                    double d[3];
                    FaceDirection(face, (ii + 0.5) * 2.0 / Size - 1.0, (jj + 0.5) * 2.0 / Size - 1.0, d);
                    f(CellOf(d));
                }
        }
    }

    double CellArea(uint32_t c) // the cube's area element, (1 + s^2 + t^2)^-1.5
    {
        const double s = (c % Size + 0.5) * 2.0 / Size - 1.0, t = (c / Size % Size + 0.5) * 2.0 / Size - 1.0, r = 1.0 + s * s + t * t;
        return 4.0 / (double(Size) * Size) / (r * std::sqrt(r)) * kRadiusKm * kRadiusKm;
    }

    // Priority-Flood (Barnes, Lehman and Mulla 2014, algorithm 3): the cells are taken from the sea upwards, the lowest
    // first; each cell not yet reached gets the level of the one that reaches it if it lies lower, a pit, or its own. A
    // pit's cells wait in a plain queue, taken before any higher cell: the flood crosses a lake in rings from its spill,
    // and the cell that reached each cell is where it drains to, down to the sea. Flats and lakes drain with the rest.
    // On plain arrays and a heap of its own: the STL's checked access and heap algorithms made a Debug build take 2.4 s.
    Drainage Drain(const std::vector<float>& elevation)
    {
        Drainage out;
        out.filled.assign(Cells, 0.0f);
        out.receiver.assign(Cells, None);
        out.area.assign(Cells, 0.0f);
        std::vector<uint8_t> reachedStore(Cells, 0);
        std::vector<uint32_t> orderStore(Cells), pitStore(Cells), heapCellStore(Cells);
        std::vector<float> heapLevelStore(Cells);
        const float* e = elevation.data();
        float* filled = out.filled.data();
        uint32_t* receiver = out.receiver.data();
        uint8_t* reached = reachedStore.data();
        uint32_t *order = orderStore.data(), *pit = pitStore.data(), *heapCell = heapCellStore.data();
        float* heapLevel = heapLevelStore.data();
        size_t ordered = 0, pits = 0, next = 0, open = 0;
        auto push = [&](float level, uint32_t cell) { // a binary heap, the lowest level on top
            size_t i = open++;
            for (; i > 0 && heapLevel[(i - 1) / 2] > level; i = (i - 1) / 2)
                heapLevel[i] = heapLevel[(i - 1) / 2], heapCell[i] = heapCell[(i - 1) / 2];
            heapLevel[i] = level, heapCell[i] = cell;
        };
        auto pop = [&]() {
            const uint32_t top = heapCell[0], cell = heapCell[--open];
            const float level = heapLevel[open];
            size_t i = 0;
            for (size_t child; (child = 2 * i + 1) < open; i = child) {
                if (child + 1 < open && heapLevel[child + 1] < heapLevel[child]) ++child;
                if (heapLevel[child] >= level) break;
                heapLevel[i] = heapLevel[child], heapCell[i] = heapCell[child];
            }
            heapLevel[i] = level, heapCell[i] = cell;
            return top;
        };
        for (uint32_t c = 0; c < Cells; ++c)
            if (e[c] < 0.0f) reached[c] = 1, pit[pits++] = c;
        for (;;) {
            uint32_t c;
            if (next < pits) c = pit[next++];
            else if (open > 0) c = pop();
            else break;
            order[ordered++] = c;
            const float level = filled[c];
            ForNeighbours(c, [&](uint32_t m) {
                if (reached[m]) return;
                reached[m] = 1;
                receiver[m] = c;
                if (e[m] <= level) filled[m] = level, pit[pits++] = m;
                else filled[m] = e[m], push(e[m], m);
            });
        }
        // Drained areas: the cells in the reverse order of the flood, from the heights down, each adding its own to its receiver's.
        float* area = out.area.data();
        for (uint32_t c = 0; c < Cells; ++c)
            if (e[c] >= 0.0f) area[c] = float(CellArea(c));
        for (size_t k = ordered; k-- > 0;)
            if (receiver[order[k]] != None) area[receiver[order[k]]] += area[order[k]];
        return out;
    }

    std::vector<uint16_t> Texels(const std::vector<float>& e, const Drainage& drainage)
    {
        // A texel's four floats in one register; each mip the means of 2 x 2 texels; halves rounded to nearest.
        std::vector<__m128> levelStore(Cells), smallerStore;
        for (uint32_t c = 0; c < Cells; ++c) {
            const float ground = std::fmax(e[c], 0.0f);
            levelStore[c] = _mm_setr_ps(ground, drainage.filled[c] - ground, std::log2(std::fmax(drainage.area[c], 1.0f)), 0.0f);
        }
        size_t offsets[6][Mips], total = 0;
        for (uint32_t f = 0; f < 6; ++f)
            for (uint32_t m = 0; m < Mips; ++m) offsets[f][m] = total, total += size_t(Size >> m) * (Size >> m) * 4;
        std::vector<uint16_t> out(total);
        for (uint32_t m = 0;; ++m) {
            const size_t n = Size >> m;
            const __m128* level = levelStore.data();
            for (uint32_t f = 0; f < 6; ++f) {
                uint16_t* face = out.data() + offsets[f][m];
                for (size_t k = 0; k < n * n; ++k)
                    _mm_storel_epi64((__m128i*)(face + 4 * k), _mm_cvtps_ph(level[f * n * n + k], 0));
            }
            if (m + 1 == Mips) break;
            const size_t h = n / 2;
            smallerStore.resize(6 * h * h);
            __m128* smaller = smallerStore.data();
            for (size_t f = 0; f < 6; ++f)
                for (size_t j = 0; j < h; ++j)
                    for (size_t i = 0; i < h; ++i) {
                        const __m128* a = level + (f * n + 2 * j) * n + 2 * i;
                        smaller[(f * h + j) * h + i] = _mm_mul_ps(_mm_set1_ps(0.25f), _mm_add_ps(_mm_add_ps(a[0], a[1]), _mm_add_ps(a[n], a[n + 1])));
                    }
            levelStore.swap(smallerStore);
        }
        return out;
    }
}
