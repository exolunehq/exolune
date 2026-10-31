// Tectonics.cpp - a body's tectonic map (Tectonics.h). Exolune's own code, written from docs/recherche-relief.md and the
// papers it cites, never from the GPL or unlicensed projects it lists. Deterministic: each growth and each flood runs on
// one thread, the per-cell loops on all of them, each cell on its own. Compiled optimised even in Debug
// (MyPlanetEngine.vcxproj).
#include "Tectonics.h"
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <functional>
#include <thread>
#include <immintrin.h>

namespace Tectonics
{
    namespace
    {
        const uint32_t None = 0xffffffffu;
        const uint16_t NoRegion = 0xffffu;
        const double kPi = 3.14159265358979323846;
        // The map's texel, about (km): the map carries what is over two texels, 40 km, the noise the rest.
        const double kTexelKm = 20.0;
        // The fronts' cost, exp(contrast x fBm): half to twice its median at one standard deviation, so that the
        // boundaries wander.
        const float kCostContrast = 0.6f;
        // A boundary whose relative motion is within 66 degrees of its line is a transform fault.
        const float kTransform = 0.4f;
        const float kOldestCrust = 200.0f; // Ma, about the oldest ocean floor on Earth
        // Continental crust covers 40 to 44 % of the surface, as on Earth with its shelves (Cogley 1984): the land is
        // what the shelves, the slopes and the low basins leave, about a third.
        const float kContinentalShare = 0.40f, kContinentalSpread = 0.04f;
        const uint32_t kSmallest = 40; // cells: a smaller patch of either crust joins the one around it
        const float kCoastCost = 4.0f; // the plates' fronts this much slower across a coast
        const float kActiveGap = 700.0f; // km: a narrower ocean between a front and a continent behind it is consumed
        // A continental rift has been opening for kRiftMa, half to one and a half times by pair of plates: its width is its
        // divergence (mm/yr = km/Ma) times that. Past kSeaOpening km it has broken the continent, an ocean floor between two
        // young margins, a narrow sea like the Red Sea, kNarrowSea km at most; slower, it stays a rift valley. Some 5 % of
        // the boundaries stay rifts, against 12 to 21 % before, the plates' divergence being faster than Earth's rifts'.
        const float kRiftMa = 2.0f, kSeaOpening = 50.0f, kNarrowSea = 300.0f;
        // km: the distances to the boundaries and to the continents' edges stop there; farther, nothing they shape changes.
        const float kBoundaryReach = 1500.0f, kMarginReach = 2000.0f;

        struct V3 { float x, y, z; };
        V3 operator+(V3 a, V3 b) { return { a.x + b.x, a.y + b.y, a.z + b.z }; }
        V3 operator-(V3 a, V3 b) { return { a.x - b.x, a.y - b.y, a.z - b.z }; }
        V3 operator*(V3 a, float s) { return { a.x * s, a.y * s, a.z * s }; }
        float Dot(V3 a, V3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
        V3 Cross(V3 a, V3 b) { return { a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x }; }
        float Length(V3 a) { return std::sqrt(Dot(a, a)); }
        V3 Normalize(V3 a) { return a * (1.0f / Length(a)); }
        float Sat(float x) { return std::min(std::max(x, 0.0f), 1.0f); }
        float Lerp(float a, float b, float t) { return a + (b - a) * t; }
        float Smooth(float e0, float e1, float x) { const float t = Sat((x - e0) / (e1 - e0)); return t * t * (3.0f - 2.0f * t); }
        float Bell(float x, float centre, float width) { const float u = (x - centre) / width; return std::exp(-u * u); }
        // floor for |x| < 2^31, as std::floor, without its call.
        float Floor(float x) { const float f = float(int(x)); return f > x ? f - 1.0f : f; }

        // A random sequence, SplitMix64.
        struct Random
        {
            uint64_t state;
            uint64_t Next()
            {
                uint64_t z = state += 0x9E3779B97F4A7C15ull;
                z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
                z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
                return z ^ (z >> 31);
            }
            float Uniform() { return float(Next() >> 40) * (1.0f / 16777216.0f); } // [0, 1)
            V3 Direction() // uniform on the sphere
            {
                const float z = 2.0f * Uniform() - 1.0f, a = float(2.0 * kPi) * Uniform(), r = std::sqrt(1.0f - z * z);
                return { r * std::cos(a), r * std::sin(a), z };
            }
        };

        uint32_t Hash(uint32_t x) // lowbias32
        {
            x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15; x *= 0x846ca68bu; x ^= x >> 16;
            return x;
        }

        // Gradient noise, about -1 to 1, at four points at once (SSE 4.1): at each lattice node one of the 12 directions to
        // a cube's edges, picked by the node's hash, lowbias32 modulo 12; quintic weights between the nodes.
        const float kGradients[12][3] = { { 1, 1, 0 }, { -1, 1, 0 }, { 1, -1, 0 }, { -1, -1, 0 }, { 1, 0, 1 }, { -1, 0, 1 },
                                          { 1, 0, -1 }, { -1, 0, -1 }, { 0, 1, 1 }, { 0, -1, 1 }, { 0, 1, -1 }, { 0, -1, -1 } };
        struct V4 { __m128 x, y, z; }; // four points

        __m128 Noise(const V4& p, uint32_t seed)
        {
            const __m128 fx = _mm_floor_ps(p.x), fy = _mm_floor_ps(p.y), fz = _mm_floor_ps(p.z);
            const __m128 x = _mm_sub_ps(p.x, fx), y = _mm_sub_ps(p.y, fy), z = _mm_sub_ps(p.z, fz), one = _mm_set1_ps(1.0f);
            const __m128i ix = _mm_cvttps_epi32(fx), iy = _mm_cvttps_epi32(fy), iz = _mm_cvttps_epi32(fz), next = _mm_set1_epi32(1);
            auto scale = [](__m128i v, uint32_t m) { return _mm_mullo_epi32(v, _mm_set1_epi32(int(m))); };
            const __m128i hx[2] = { scale(ix, 73856093u), scale(_mm_add_epi32(ix, next), 73856093u) };
            const __m128i hy[2] = { scale(iy, 19349663u), scale(_mm_add_epi32(iy, next), 19349663u) };
            const __m128i hz[2] = { _mm_xor_si128(scale(iz, 83492791u), _mm_set1_epi32(int(seed))),
                                    _mm_xor_si128(scale(_mm_add_epi32(iz, next), 83492791u), _mm_set1_epi32(int(seed))) };
            auto corner = [&](int i, int j, int k) {
                __m128i h = _mm_xor_si128(_mm_xor_si128(hx[i], hy[j]), hz[k]); // lowbias32
                h = _mm_xor_si128(h, _mm_srli_epi32(h, 16)), h = _mm_mullo_epi32(h, _mm_set1_epi32(0x7feb352d));
                h = _mm_xor_si128(h, _mm_srli_epi32(h, 15)), h = _mm_mullo_epi32(h, _mm_set1_epi32(int(0x846ca68bu)));
                h = _mm_xor_si128(h, _mm_srli_epi32(h, 16));
                // h / 12 = (h 0xAAAAAAAB) >> 35, on the even lanes then the odd ones
                const __m128i m = _mm_set1_epi32(int(0xAAAAAAABu));
                const __m128i even = _mm_srli_epi64(_mm_mul_epu32(h, m), 35), odd = _mm_srli_epi64(_mm_mul_epu32(_mm_srli_epi64(h, 32), m), 35);
                h = _mm_sub_epi32(h, _mm_mullo_epi32(_mm_or_si128(even, _mm_slli_epi64(odd, 32)), _mm_set1_epi32(12)));
                alignas(16) int32_t d[4];
                _mm_store_si128((__m128i*)d, h);
                const __m128 gx = _mm_setr_ps(kGradients[d[0]][0], kGradients[d[1]][0], kGradients[d[2]][0], kGradients[d[3]][0]);
                const __m128 gy = _mm_setr_ps(kGradients[d[0]][1], kGradients[d[1]][1], kGradients[d[2]][1], kGradients[d[3]][1]);
                const __m128 gz = _mm_setr_ps(kGradients[d[0]][2], kGradients[d[1]][2], kGradients[d[2]][2], kGradients[d[3]][2]);
                return _mm_add_ps(_mm_add_ps(_mm_mul_ps(gx, i ? _mm_sub_ps(x, one) : x), _mm_mul_ps(gy, j ? _mm_sub_ps(y, one) : y)),
                                  _mm_mul_ps(gz, k ? _mm_sub_ps(z, one) : z));
            };
            auto fade = [](__m128 t) {
                return _mm_mul_ps(_mm_mul_ps(_mm_mul_ps(t, t), t),
                                  _mm_add_ps(_mm_mul_ps(t, _mm_sub_ps(_mm_mul_ps(t, _mm_set1_ps(6.0f)), _mm_set1_ps(15.0f))), _mm_set1_ps(10.0f)));
            };
            auto lerp = [](__m128 a, __m128 b, __m128 t) { return _mm_add_ps(a, _mm_mul_ps(_mm_sub_ps(b, a), t)); };
            const __m128 u = fade(x), v = fade(y), w = fade(z);
            return lerp(lerp(lerp(corner(0, 0, 0), corner(1, 0, 0), u), lerp(corner(0, 1, 0), corner(1, 1, 0), u), v),
                        lerp(lerp(corner(0, 0, 1), corner(1, 0, 1), u), lerp(corner(0, 1, 1), corner(1, 1, 1), u), v), w);
        }

        // Octaves of gradient noise from `frequency` on the unit sphere, each with its own seed and lattice; or only the
        // octaves from `first` on. At four points.
        __m128 Fbm(const V4& p, float frequency, int octaves, uint32_t seed, int first = 0)
        {
            __m128 sum = _mm_setzero_ps();
            float amplitude = 0.5f;
            for (int k = 0; k < octaves; ++k, frequency *= 2.03f, amplitude *= 0.5f) {
                if (k < first) continue;
                const __m128 f = _mm_set1_ps(frequency);
                const V4 q = { _mm_add_ps(_mm_mul_ps(p.x, f), _mm_set1_ps(0.31f * k)), _mm_add_ps(_mm_mul_ps(p.y, f), _mm_set1_ps(0.57f * k)),
                               _mm_add_ps(_mm_mul_ps(p.z, f), _mm_set1_ps(0.83f * k)) };
                sum = _mm_add_ps(sum, _mm_mul_ps(_mm_set1_ps(amplitude), Noise(q, Hash(seed + k))));
            }
            return sum;
        }

        // Four points from p[0 .. 3]; a V4 moved by s times w.
        V4 Gather(const V3* p) { return { _mm_setr_ps(p[0].x, p[1].x, p[2].x, p[3].x), _mm_setr_ps(p[0].y, p[1].y, p[2].y, p[3].y),
                                           _mm_setr_ps(p[0].z, p[1].z, p[2].z, p[3].z) }; }
        V4 Moved(const V4& p, const V4& w, float s)
        {
            const __m128 k = _mm_set1_ps(s);
            return { _mm_add_ps(p.x, _mm_mul_ps(w.x, k)), _mm_add_ps(p.y, _mm_mul_ps(w.y, k)), _mm_add_ps(p.z, _mm_mul_ps(w.z, k)) };
        }
        float Lane(__m128 v, int k) { alignas(16) float f[4]; _mm_store_ps(f, v); return f[k]; }

        // f(c) for every cell, on all the processor's threads but `spared`: each cell's result must depend on that cell alone.
        template <class F> void ForCells(uint32_t cells, const F& f, uint32_t spared = 0)
        {
            const uint32_t threads = std::max(1u, std::thread::hardware_concurrency() - std::min(spared, std::thread::hardware_concurrency() - 1));
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

        // `rounds` rounds of f(i) for i in [0, count) on up to 8 threads, then g() once, each round's results depending on
        // the previous round's alone: the threads started once and held together between the rounds.
        template <class F, class G> void ForRounds(uint32_t count, int rounds, const F& f, const G& g)
        {
            const uint32_t threads = std::min(8u, std::max(1u, std::thread::hardware_concurrency()));
            std::atomic<uint32_t> arrived{ 0 };
            std::vector<std::thread> pool;
            for (uint32_t t = 0; t < threads; ++t)
                pool.emplace_back([&, t] {
                    uint32_t phase = 0;
                    auto wait = [&] { phase += threads; arrived.fetch_add(1); while (arrived.load() < phase) std::this_thread::yield(); };
                    const uint32_t begin = uint32_t(uint64_t(count) * t / threads), end = uint32_t(uint64_t(count) * (t + 1) / threads);
                    for (int r = 0; r < rounds; ++r) {
                        for (uint32_t i = begin; i < end; ++i) f(i);
                        wait();
                        if (t == 0) g();
                        wait();
                    }
                });
            for (std::thread& thread : pool) thread.join();
        }

        // The cube's cells, face by face, row by row: D3D's cube map layout, as PlanetMap's.
        struct Cube
        {
            uint32_t n, cells, bits; // n = 2^bits: a cell's face, row and column by shifts, not divisions
            std::vector<V3> p;       // each cell's centre, on the unit sphere

            explicit Cube(uint32_t size) : n(size), cells(6 * size * size), bits(0), p(cells)
            {
                while ((1u << bits) < n) ++bits;
                ForCells(cells, [&](uint32_t c) { p[c] = Normalize(Direction(c / (n * n), Coordinate(c % n), Coordinate(c / n % n))); });
            }
            float Coordinate(int i) const { return (i + 0.5f) * 2.0f / n - 1.0f; }
            // The direction of the point (s, t) of face f, not normalised; s and t past [-1, 1] go beyond the face's edge.
            static V3 Direction(uint32_t f, float s, float t)
            {
                const V3 table[6] = { { 1.0f, -t, -s }, { -1.0f, -t, s }, { s, 1.0f, t }, { s, -1.0f, -t }, { s, -t, 1.0f }, { -s, -t, -1.0f } };
                return table[f];
            }
            // The face holding direction d, D3D's choice for a cube map, and d's texel coordinates on it, continuous: the
            // centre of texel i is at i.
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
                auto texel = [&](float v) { return (uint32_t)std::fmin(std::fmax(Floor(v + 0.5f), 0.0f), n - 1.0f); };
                return (f * n + texel(y)) * n + texel(x);
            }
            // A field of four channels at direction d: bilinear on the face holding d, the texels past its edge taken on
            // the next face, so that the reading is continuous across the cube's edges.
            __m128 Bilinear(const std::vector<__m128>& field, V3 d) const
            {
                uint32_t f;
                float x, y;
                Locate(d, f, x, y);
                const float fx = Floor(x), fy = Floor(y);
                const int i = int(fx), j = int(fy);
                auto at = [&](int ii, int jj) {
                    if (ii >= 0 && jj >= 0 && ii < int(n) && jj < int(n)) return field[(f * n + jj) * n + ii];
                    return field[CellOf(Direction(f, Coordinate(ii), Coordinate(jj)))];
                };
                const __m128 u = _mm_set1_ps(x - fx), a = at(i, j), b = at(i, j + 1);
                const __m128 top = _mm_add_ps(a, _mm_mul_ps(u, _mm_sub_ps(at(i + 1, j), a)));
                const __m128 bottom = _mm_add_ps(b, _mm_mul_ps(u, _mm_sub_ps(at(i + 1, j + 1), b)));
                return _mm_add_ps(top, _mm_mul_ps(_mm_set1_ps(y - fy), _mm_sub_ps(bottom, top)));
            }
            // Calls f with each of the 8 neighbours of cell c, row by row; across a face's edge, the cell beyond it. At the
            // cube's corners one neighbour comes twice. Inside a face, by their rows: short enough to be inlined.
            template <class F> void ForNeighbours(uint32_t c, const F& f) const
            {
                uint32_t around[8];
                Neighbours(c, around);
                for (uint32_t m : around) f(m);
            }
            void Neighbours(uint32_t c, uint32_t* a) const
            {
                const uint32_t j = (c >> bits) & (n - 1), i = c & (n - 1);
                if (i > 0 && j > 0 && i + 1 < n && j + 1 < n)
                    a[0] = c - n - 1, a[1] = c - n, a[2] = c - n + 1, a[3] = c - 1, a[4] = c + 1, a[5] = c + n - 1, a[6] = c + n, a[7] = c + n + 1;
                else Rim(c, a);
            }
            // The 8 neighbours of a cell on a face's edge.
            __declspec(noinline) void Rim(uint32_t c, uint32_t* around) const
            {
                const uint32_t face = c >> (2 * bits), j = (c >> bits) & (n - 1), i = c & (n - 1);
                for (int dj = -1; dj <= 1; ++dj)
                    for (int di = -1; di <= 1; ++di) {
                        if (!di && !dj) continue;
                        const int ii = int(i) + di, jj = int(j) + dj;
                        *around++ = ii >= 0 && jj >= 0 && ii < int(n) && jj < int(n) ? c + dj * int(n) + di
                                                                                       : CellOf(Direction(face, Coordinate(ii), Coordinate(jj)));
                    }
            }
            float Area(uint32_t c) const // on the unit sphere, the cube's area element (1 + s^2 + t^2)^-1.5
            {
                const float s = Coordinate(c & (n - 1)), t = Coordinate((c >> bits) & (n - 1)), r = 1.0f + s * s + t * t;
                return 4.0f / (float(n) * n) / (r * std::sqrt(r));
            }
            // Fields smoothed over about a texel per pass, field k passes[k] times: each cell half its own, half its
            // neighbours' mean. The fields share the passes and each cell's neighbours.
            void Blur(const std::vector<std::vector<float>*>& fields, const std::vector<int>& passes) const
            {
                std::vector<std::vector<float>> out(fields.size(), std::vector<float>(cells));
                const int most = *std::max_element(passes.begin(), passes.end());
                for (int pass = 0; pass < most; ++pass) {
                    std::vector<const float*> from;
                    std::vector<float*> to;
                    for (size_t k = 0; k < fields.size(); ++k)
                        if (pass < passes[k]) from.push_back(fields[k]->data()), to.push_back(out[k].data());
                    ForCells(cells, [&](uint32_t c) {
                        uint32_t a[8];
                        Neighbours(c, a);
                        for (size_t k = 0; k < from.size(); ++k) { // the sum as a tree, its additions side by side
                            const float* f = from[k];
                            to[k][c] = (((f[a[0]] + f[a[1]]) + (f[a[2]] + f[a[3]])) + ((f[a[4]] + f[a[5]]) + (f[a[6]] + f[a[7]])) + 8.0f * f[c]) * 0.0625f;
                        }
                    });
                    for (size_t k = 0; k < fields.size(); ++k) if (pass < passes[k]) fields[k]->swap(out[k]);
                }
            }
        };

        // A priority queue on a key that never falls below the last one taken, Dial's buckets of `width`: the items come
        // out in the key's order to within `width`, much cheaper than a heap. An item pushed under the current bucket goes
        // to the current one.
        template <class T> struct Buckets
        {
            float width, limit = INFINITY; // keys past the limit are left out
            size_t at = 0;
            std::vector<std::vector<T>> bucket;
            void Push(float key, const T& item)
            {
                if (key > limit) return;
                const size_t k = std::max(size_t(key / width), at);
                if (k >= bucket.size()) bucket.resize(k + 1);
                bucket[k].push_back(item);
            }
            // f(item) for every item, f pushing others; each bucket freed once taken.
            template <class F> void Run(const F& f)
            {
                for (at = 0; at < bucket.size(); ++at) {
                    for (size_t i = 0; i < bucket[at].size(); ++i) {
                        const T item = bucket[at][i];
                        f(item);
                    }
                    std::vector<T>().swap(bucket[at]);
                }
            }
        };

        // A field to zero mean and unit deviation.
        void Standardise(std::vector<float>& field)
        {
            double sum = 0.0, squares = 0.0;
            for (float v : field) sum += v, squares += double(v) * v;
            const double mean = sum / field.size(), deviation = std::sqrt(std::max(squares / field.size() - mean * mean, 1e-12));
            for (float& v : field) v = float((v - mean) / deviation);
        }

        // Competitive growth: fronts leave the seeds together, and each cell goes to the first that reaches it. A front
        // runs at its seed's speed, slowed where the cost field is high: where fronts meet, the boundaries wander with
        // it, never along great circles. A front stays within its seed's domain, if any. Each region is connected. The
        // fronts' order to within a tenth of the fastest front's time across a texel.
        std::vector<uint16_t> Grow(const Cube& cube, const std::vector<uint32_t>& seeds, const std::vector<float>& speed,
                                   const std::vector<float>& cost, const uint16_t* domain)
        {
            struct Front { float time; uint32_t cell; uint16_t region; };
            std::vector<uint16_t> region(cube.cells, NoRegion);
            std::vector<float> best(cube.cells, INFINITY);
            Buckets<Front> open{ 0.2f / (cube.n * *std::max_element(speed.begin(), speed.end())) };
            for (uint16_t r = 0; r < seeds.size(); ++r) best[seeds[r]] = 0.0f, open.Push(0.0f, { 0.0f, seeds[r], r });
            open.Run([&](const Front& f) {
                if (region[f.cell] != NoRegion) return;
                region[f.cell] = f.region;
                const uint16_t inside = domain ? domain[seeds[f.region]] : 0;
                cube.ForNeighbours(f.cell, [&](uint32_t m) {
                    if (region[m] != NoRegion || (domain && domain[m] != inside)) return;
                    const float t = f.time + Length(cube.p[m] - cube.p[f.cell]) * 0.5f * (cost[f.cell] + cost[m]) / speed[f.region];
                    if (t < best[m]) best[m] = t, open.Push(t, { t, m, f.region });
                });
            });
            return region;
        }

        // A point of a line, beside one of its cells.
        struct Source { uint32_t cell; V3 at; };

        // The chord on the unit sphere of an arc of `angle` radians.
        float Chord(float angle) { return 2.0f * std::sin(0.5f * std::min(angle, float(kPi))); }

        // Each cell's nearest source within its domain: Dijkstra's order, to within a quarter of a texel, on the distance
        // to the source carried from cell to cell, a nearest-seed propagation, exact but for rare cells. chord: the
        // distance to it on the unit sphere. None where no source shares the cell's domain, or none is within `reach`.
        std::vector<uint32_t> Nearest(const Cube& cube, const std::vector<Source>& sources, const uint16_t* domain,
                                      std::vector<float>& chord, float reach = INFINITY)
        {
            struct Step { float chord; uint32_t cell; };
            std::vector<uint32_t> nearest(cube.cells, None);
            chord.assign(cube.cells, INFINITY);
            Buckets<Step> open{ 0.5f / cube.n, reach };
            for (uint32_t s = 0; s < sources.size(); ++s) {
                const uint32_t c = sources[s].cell;
                const float d = Length(cube.p[c] - sources[s].at);
                if (d < chord[c]) chord[c] = d, nearest[c] = s, open.Push(d, { d, c });
            }
            const float settled = 3.0f / cube.n; // more than the chord between two neighbours
            open.Run([&](const Step& step) {
                if (step.chord > chord[step.cell]) return;
                const uint32_t s = nearest[step.cell];
                const V3 at = sources[s].at;
                cube.ForNeighbours(step.cell, [&](uint32_t m) {
                    if (chord[m] <= step.chord - settled || (domain && domain[m] != domain[step.cell])) return; // no nearer
                    const float d = Length(cube.p[m] - at);
                    if (d < chord[m]) chord[m] = d, nearest[m] = s, open.Push(d, { d, m });
                });
            });
            return nearest;
        }

        // Calls f with every cell within `steps` neighbour steps of c, c included; seen[cell] == mark once visited.
        template <class F> void Around(const Cube& cube, uint32_t c, int steps, std::vector<uint32_t>& seen, uint32_t mark,
                                       std::vector<uint32_t>& walk, const F& f)
        {
            walk.assign(1, c);
            seen[c] = mark;
            for (size_t begin = 0; steps-- > 0;) {
                const size_t end = walk.size();
                for (size_t k = begin; k < end; ++k)
                    cube.ForNeighbours(walk[k], [&](uint32_t m) { if (seen[m] != mark) seen[m] = mark, walk.push_back(m); });
                begin = end;
            }
            for (uint32_t k : walk) f(k);
        }

        // Each connected patch of either crust smaller than kSmallest cells joins the crust around it.
        void Clean(const Cube& cube, std::vector<uint8_t>& continental)
        {
            std::vector<uint32_t> label(cube.cells, None), patch;
            for (uint32_t c = 0; c < cube.cells; ++c) {
                if (label[c] != None) continue;
                patch.assign(1, c);
                label[c] = c;
                for (size_t k = 0; k < patch.size(); ++k)
                    cube.ForNeighbours(patch[k], [&](uint32_t m) {
                        if (label[m] == None && continental[m] == continental[c]) label[m] = c, patch.push_back(m);
                    });
                if (patch.size() < kSmallest)
                    for (uint32_t k : patch) continental[k] ^= 1;
            }
        }

        // A cell beside another plate: the boundary there.
        struct Edge
        {
            uint32_t cell, across;    // the boundary's cell, and one beyond it on the other plate
            uint16_t plate, other, under; // under: a convergent boundary's plate that goes under, the subducting one
            V3 at, normal;            // the boundary's point; its normal, from the plate towards the other
            float convergence;        // the relative motion across it (mm/yr), > 0 where the plates converge
            float along;              // the relative motion's speed (mm/yr)
            float crust, crustAcross; // the continental share on either side, along the boundary
            int family;               // the profile family it feeds (Family), -1 for none
            float drive;              // its family's motion (mm/yr) smoothed along the stretch, falling to 0 at its ends
            float shear;              // the share of transform motion around it
            Boundary type;
        };

        // The rock's erodibility, relative to the young chains' fractured rock, by class (Rock): several orders of magnitude
        // apart on Earth from soft sediments to crystalline basement (Stock and Montgomery 1999); a factor of ten here, the
        // level 0 calibrating its own constant.
        const float kErodibility[] = { 1.0f, 0.6f, 1.0f, 1.6f, 0.45f, 0.25f };

        // The ocean floor's depth (m, < 0) at an age (Ma): Stein and Stein 1992, GDH1, less the sediments' load, which grows
        // with the age and flattens the abyssal plains.
        float OceanDepth(float age)
        {
            const float t = std::max(age, 0.0f);
            const float depth = t < 20.0f ? 2600.0f + 365.0f * std::sqrt(t) : 5651.0f - 2473.0f * std::exp(-0.0278f * t);
            return -(depth - 800.0f * (1.0f - std::exp(-t / 60.0f)));
        }

        // The boundary families whose profiles the relief draws, each its own distance within the plates; and the ridges.
        enum Family { Overriding, Subducting, Colliding, Rifting, Families, Spreading = Families };

        // The relief's warp of its reading of the map, unfiltered: RlTurbulence of Noise.hlsli, its hash, its gradients and
        // its lattice, with PlanetSettings.hlsli's RELIEF_WARP_TOP, RELIEF_WARP_OCTAVES and RELIEF_WARP. A volcano placed on
        // the map's forms is moved back by it, to stand where the shader draws them (Relief.hlsli).
        const double kWarpTopKm = 800.0, kWarpKm = 30.0;
        const int kWarpOctaves = 6;
        const float kNoiseSigma = 0.4f, kNoiseScale = 2.1935f; // RL_SIGMA, RL_SCALE_STANDARD

        uint32_t XxRound(uint32_t h, uint32_t v) { h += v * 0x85EBCA77u; h = (h << 13) | (h >> 19); return h * 0x9E3779B1u; }
        uint32_t XxMix(uint32_t h) { h ^= h >> 15; h *= 0x85EBCA77u; h ^= h >> 13; h *= 0xC2B2AE3Du; return h ^ (h >> 16); }

        // Noise.hlsli's gradients: 256 directions on a Fibonacci spiral, rounded to floats.
        struct Gradients
        {
            float g[256][3];
            Gradients()
            {
                for (int i = 0; i < 256; ++i) {
                    const double z = 1.0 - (2.0 * i + 1.0) / 256.0, r = std::sqrt(1.0 - z * z), a = i * (kPi * (3.0 - std::sqrt(5.0)));
                    g[i][0] = float(r * std::cos(a)), g[i][1] = float(r * std::sin(a)), g[i][2] = float(z);
                }
            }
        };

        // The warp's three noises at a lattice cell and its remainder, seeds seed, + 16, + 32, standard quality: RlCorners.
        void Corners(const Gradients& G, const int c[3], const float q[3], uint32_t seed, float out[3])
        {
            uint32_t h[8]; // bit 0 x + 1, bit 1 y + 1, bit 2 z + 1
            for (uint32_t k = 0; k < 8; ++k)
                h[k] = XxRound(XxRound(XxRound(0x165667B1u, uint32_t(c[0]) + (k & 1)), uint32_t(c[1]) + (k >> 1 & 1)), uint32_t(c[2]) + (k >> 2));
            float s[3];
            for (int a = 0; a < 3; ++a) s[a] = q[a] * q[a] * (3.0f - 2.0f * q[a]);
            for (uint32_t j = 0; j < 3; ++j) {
                const uint32_t key = (seed + 16u * j) * 0x27D4EB2Fu;
                float n[8];
                for (uint32_t k = 0; k < 8; ++k) {
                    const float* g = G.g[XxMix(h[k] + key) >> 24];
                    n[k] = g[0] * (k & 1 ? q[0] - 1.0f : q[0]) + g[1] * (k & 2 ? q[1] - 1.0f : q[1]) + g[2] * (k & 4 ? q[2] - 1.0f : q[2]);
                }
                const float x0 = n[0] + s[0] * (n[1] - n[0]), x1 = n[2] + s[0] * (n[3] - n[2]);
                const float x2 = n[4] + s[0] * (n[5] - n[4]), x3 = n[6] + s[0] * (n[7] - n[6]);
                const float y0 = x0 + s[1] * (x1 - x0), y1 = x2 + s[1] * (x3 - x2);
                out[j] = y0 + s[2] * (y1 - y0);
            }
        }

        // Where the relief reads the map for the point p of the unit sphere: p + power d(p), as RlTurbulence, in doubles.
        void Warp(const Gradients& G, const double p[3], uint32_t seed, double radiusKm, double out[3])
        {
            const float step[3] = { 0.7548776662f, 0.5698402910f, 0.4142135624f }; // RlShift
            double f = radiusKm / kWarpTopKm;
            float amplitude = kNoiseScale, d[3] = { 0.0f, 0.0f, 0.0f };
            for (int o = 0; o < kWarpOctaves; ++o, f *= 2.0, amplitude *= 0.5f) {
                int c[3];
                float q[3], n[3];
                for (int a = 0; a < 3; ++a) {
                    const double x = p[a] * f;
                    const float cf = std::floor(float(x)), shift = float(o) * step[a] - std::floor(float(o) * step[a]);
                    const float r = float(x - double(cf)) + shift, fl = std::floor(r);
                    c[a] = int(cf) + int(fl), q[a] = r - fl;
                }
                Corners(G, c, q, seed + uint32_t(o), n);
                for (int a = 0; a < 3; ++a) d[a] += amplitude * n[a];
            }
            const double power = kWarpKm / (kNoiseSigma * radiusKm);
            for (int a = 0; a < 3; ++a) out[a] = p[a] + power * d[a];
        }

        // The point of the unit sphere whose reading of the map is at the direction m: the warp undone, by fixed-point steps.
        V3 Unwarp(const Gradients& G, V3 m, uint32_t seed, double radiusKm)
        {
            double p[3] = { m.x, m.y, m.z }, w[3];
            for (int k = 0; k < 6; ++k) {
                Warp(G, p, seed, radiusKm, w);
                const double lw = std::sqrt(w[0] * w[0] + w[1] * w[1] + w[2] * w[2]), mm[3] = { m.x, m.y, m.z };
                double l = 0.0;
                for (int a = 0; a < 3; ++a) p[a] += mm[a] - w[a] / lw, l += p[a] * p[a];
                for (int a = 0; a < 3; ++a) p[a] /= std::sqrt(l);
            }
            return { float(p[0]), float(p[1]), float(p[2]) };
        }
    }

    Map Build(const Body& body)
    {
        const auto start = std::chrono::steady_clock::now();
        const float radius = float(body.radiusKm);
        Map map;
        map.size = 1u << std::min(std::max(int(std::lround(std::log2(kPi / 2.0 * body.radiusKm / kTexelKm))), 6), 10);
        const Cube cube(map.size);
        const uint32_t cells = cube.cells;
        Random random{ 0x5DEECE66Dull * (uint64_t(body.seed) + 1) };
        auto arc = [&](float chord) { return 2.0f * std::asin(std::min(0.5f * chord, 1.0f)) * radius; }; // km

        // The noise fields, at every scale from 3 000 to 60 km, each standardised: the plates' fronts' cost; the
        // continents' potential, an fBm whose first octaves have the continents' size, warped so that they stretch and
        // bend. What is all over 300 km on a cube of half the resolution, read bilinearly: the potential's warp, over
        // 1 000 km, and the first octaves of the two; the regional variations, the cratons' fronts' cost and the relief's.
        enum { CratonCost, ShieldZ, ShelfZ, InteriorZ, VaryZ, ReliefZ, MesaZ, SoftZ, OceanZ, RegionalFields };
        std::vector<float> costZ(cells), potential(cells);
        const uint32_t noiseSeed = uint32_t(random.Next());
        const Cube coarse(map.size / 2);
        std::vector<__m128> warp(coarse.cells), first(coarse.cells); // the warp; the potential's and the cost's first octaves
        const int potentialCoarse = 5, costCoarse = 3;
        ForCells(coarse.cells / 4, [&](uint32_t q) {
            const V4 p = Gather(&coarse.p[4 * q]);
            const V4 w = { Fbm(p, 1.5f, 3, noiseSeed + 303u), Fbm(p, 1.5f, 3, noiseSeed + 304u), Fbm(p, 1.5f, 3, noiseSeed + 305u) };
            const __m128 potentialFirst = Fbm(Moved(p, w, 0.6f), 1.2f, potentialCoarse, noiseSeed + 306u), costFirst = Fbm(p, 3.0f, costCoarse, noiseSeed);
            for (int k = 0; k < 4; ++k)
                warp[4 * q + k] = _mm_setr_ps(Lane(w.x, k), Lane(w.y, k), Lane(w.z, k), 0.0f),
                first[4 * q + k] = _mm_setr_ps(Lane(potentialFirst, k), Lane(costFirst, k), 0.0f, 0.0f);
        });
        ForCells(cells / 4, [&](uint32_t q) {
            const V4 p = Gather(&cube.p[4 * q]);
            alignas(16) float l[4][4], m[4][4];
            for (int k = 0; k < 4; ++k)
                _mm_store_ps(l[k], coarse.Bilinear(first, cube.p[4 * q + k])), _mm_store_ps(m[k], coarse.Bilinear(warp, cube.p[4 * q + k]));
            const V4 w = { _mm_setr_ps(m[0][0], m[1][0], m[2][0], m[3][0]), _mm_setr_ps(m[0][1], m[1][1], m[2][1], m[3][1]),
                           _mm_setr_ps(m[0][2], m[1][2], m[2][2], m[3][2]) };
            const __m128 fine = Fbm(Moved(p, w, 0.6f), 1.2f, 8, noiseSeed + 306u, potentialCoarse), costFine = Fbm(p, 3.0f, 6, noiseSeed, costCoarse);
            for (int k = 0; k < 4; ++k)
                potential[4 * q + k] = l[k][0] + Lane(fine, k), costZ[4 * q + k] = l[k][1] + Lane(costFine, k);
        });
        Standardise(costZ), Standardise(potential);
        std::vector<float> cost(cells);
        for (uint32_t c = 0; c < cells; ++c) cost[c] = std::exp(kCostContrast * costZ[c]);
        std::vector<__m128> regional[3];
        auto computeRegional = [&] { // beside the plates' growth: two threads spared, a core for it
            std::vector<std::vector<float>> z(RegionalFields, std::vector<float>(coarse.cells));
            ForCells(coarse.cells / 4, [&](uint32_t q) {
                const V4 p = Gather(&coarse.p[4 * q]);
                const __m128 v[RegionalFields] = { Fbm(p, 3.0f, 6, noiseSeed + 101u), Fbm(p, 4.0f, 4, noiseSeed + 202u),
                                                   Fbm(p, 5.0f, 3, noiseSeed + 307u), Fbm(p, 4.0f, 4, noiseSeed + 308u),
                                                   Fbm(p, 9.0f, 3, noiseSeed + 309u), Fbm(p, 12.0f, 3, noiseSeed + 310u),
                                                   Fbm(p, 10.0f, 3, noiseSeed + 311u), Fbm(p, 14.0f, 3, noiseSeed + 312u),
                                                   Fbm(p, 3.0f, 4, noiseSeed + 313u) };
                for (int f = 0; f < RegionalFields; ++f) _mm_storeu_ps(&z[f][4 * q], v[f]);
            }, 2);
            for (auto& field : z) Standardise(field);
            for (int k = 0; k < 3; ++k) {
                regional[k].resize(coarse.cells);
                for (uint32_t c = 0; c < coarse.cells; ++c)
                    regional[k][c] = _mm_setr_ps(z[4 * k][c], 4 * k + 1 < RegionalFields ? z[4 * k + 1][c] : 0.0f,
                                                 4 * k + 2 < RegionalFields ? z[4 * k + 2][c] : 0.0f, 4 * k + 3 < RegionalFields ? z[4 * k + 3][c] : 0.0f);
            }
        };
        // The regional variations at direction d, by RegionalFields' order.
        auto readRegional = [&](V3 d, float* z) { for (int k = 0; k < 3; ++k) _mm_storeu_ps(z + 4 * k, coarse.Bilinear(regional[k], d)); };

        // The continents, by place, not by plate: the potential's highest cells up to the drawn share. A plate carries
        // continents and oceans; a boundary can cross a continent, a rift that opens it or a collision that welds two.
        const float target = kContinentalShare + kContinentalSpread * random.Uniform();
        std::vector<uint8_t> continental(cells, 0);
        {
            const int bins = 8192;
            float low = INFINITY, high = -INFINITY;
            for (float v : potential) low = std::min(low, v), high = std::max(high, v);
            std::vector<double> histogram(bins, 0.0);
            auto bin = [&](float v) { return std::min(int((v - low) / (high - low) * bins), bins - 1); };
            for (uint32_t c = 0; c < cells; ++c) histogram[bin(potential[c])] += cube.Area(c) / (4.0 * kPi);
            double above = 0.0;
            int b = bins - 1;
            while (b > 0 && above + histogram[b] < target) above += histogram[b--];
            const float threshold = low + (b + float((above + histogram[b] - target) / std::max(histogram[b], 1e-12))) * (high - low) / bins;
            for (uint32_t c = 0; c < cells; ++c) continental[c] = potential[c] > threshold;
            Clean(cube, continental);
        }

        // Ancient sutures: the continents cut into cratons by the same growth, one per 2 % of the surface; where two
        // cratons meet, a suture of their own age, 100 to 1 000 Ma. The history drawn by seed, not simulated
        // (docs/recherche-relief.md, 6.2): the cratons are the continents' before the plates move, their accreted margins
        // and their rifts left out. Their seeds have their own sequence; their growth and their flood a thread of their own,
        // after the regional variations, from the plates' growth on, while the plates are grown and classified.
        const std::vector<uint16_t> crustDomain(continental.begin(), continental.end());
        std::vector<Source> sutures;
        std::vector<float> sutureAge, sutureChord;
        std::vector<uint32_t> suture;
        auto growCratons = [&] {
            computeRegional();
            Random draw{ 0x2545F4914F6CDD1Dull * (uint64_t(body.seed) + 1) };
            std::vector<uint32_t> land, seeds;
            std::vector<float> speeds, cratonCost(cells);
            float share = 0.0f;
            for (uint32_t c = 0; c < cells; ++c)
                if (crustDomain[c]) land.push_back(c), share += cube.Area(c) / float(4.0 * kPi);
            const int count = std::min(std::max(int(share * 50.0f), 1), 32);
            for (int j = 0; j < count && !land.empty(); ++j) {
                uint32_t best = 0;
                float bestGap = -1.0f;
                for (int k = 0; k < 16; ++k) {
                    const uint32_t c = land[draw.Next() % land.size()];
                    float gap = 4.0f;
                    for (uint32_t s : seeds) gap = std::min(gap, Length(cube.p[c] - cube.p[s]));
                    if (gap > bestGap) bestGap = gap, best = c;
                }
                seeds.push_back(best);
                speeds.push_back(std::exp2(draw.Uniform() - 0.5f));
            }
            for (uint32_t c = 0; c < cells; ++c) cratonCost[c] = std::exp(kCostContrast * _mm_cvtss_f32(coarse.Bilinear(regional[0], cube.p[c])));
            const std::vector<uint16_t> craton = Grow(cube, seeds, speeds, cratonCost, crustDomain.data());
            for (uint32_t c = 0; c < cells; ++c) {
                if (craton[c] == NoRegion) continue;
                uint32_t beyond = None;
                cube.ForNeighbours(c, [&](uint32_t m) { if (beyond == None && craton[m] != NoRegion && craton[m] != craton[c]) beyond = m; });
                if (beyond == None) continue;
                sutures.push_back({ c, Normalize(cube.p[c] + cube.p[beyond]) });
                const uint32_t a = std::min(craton[c], craton[beyond]), b = std::max(craton[c], craton[beyond]);
                sutureAge.push_back(100.0f + 900.0f * float(Hash(a * 65536u + b + body.seed) >> 8) / 16777216.0f);
            }
            suture = Nearest(cube, sutures, nullptr, sutureChord, Chord(1000.0f / radius));
        };

        // The plates' fronts slowed across the coasts, a band of two cells each side: some boundaries settle along them,
        // the active margins, where an ocean goes under a continent; the others cross the continents or stay at sea.
        std::vector<float> plateCost(cost);
        {
            std::vector<uint8_t> coast(cells, 0), next(cells, 0);
            ForCells(cells, [&](uint32_t c) { cube.ForNeighbours(c, [&](uint32_t m) { if (continental[m] != continental[c]) coast[c] = 1; }); });
            ForCells(cells, [&](uint32_t c) { next[c] = coast[c]; cube.ForNeighbours(c, [&](uint32_t m) { next[c] |= coast[m]; }); });
            for (uint32_t c = 0; c < cells; ++c) plateCost[c] *= next[c] ? kCoastCost : 1.0f;
        }

        // The plates: 12 to 20 seeds, each the farthest from the others among a few drawn (Mitchell's best candidate),
        // grown at speeds from 0.4 to 2.5: some plates large, others small, 0.3 to 18 % of the surface.
        const uint32_t plateCount = 12 + uint32_t(random.Next() % 9);
        std::vector<uint32_t> seeds;
        std::vector<float> speed;
        std::vector<V3> seedAt;
        for (uint32_t i = 0; i < plateCount; ++i) {
            V3 best = {};
            float bestGap = -1.0f;
            for (int k = 0; k < 24; ++k) {
                const V3 d = random.Direction();
                float gap = 4.0f;
                for (const V3& s : seedAt) gap = std::min(gap, Length(d - s));
                if (gap > bestGap) bestGap = gap, best = d;
            }
            seedAt.push_back(best);
            seeds.push_back(cube.CellOf(best));
            speed.push_back(std::exp2(2.6f * random.Uniform() - 1.3f));
        }
        std::thread cratons(growCratons);
        const std::vector<uint16_t> plate = Grow(cube, seeds, speed, plateCost, nullptr);
        map.plates.resize(plateCount);
        for (uint32_t c = 0; c < cells; ++c) map.plates[plate[c]].area += cube.Area(c) / float(4.0 * kPi);

        for (uint32_t c = 0; c < cells; ++c)
            if (continental[c]) {
                const float a = cube.Area(c) / float(4.0 * kPi);
                map.continental += a, map.plates[plate[c]].continental += a;
            }
        for (Plate& p : map.plates) p.continental /= std::max(p.area, 1e-9f);

        // Their motions: an Euler pole each, drawn on the sphere, and a speed 90 degrees from it: 40 to 100 mm/yr for an
        // oceanic plate, 10 to 40 for a continental one, between them by its share of continent (mm/yr = km/Ma).
        std::vector<V3> omega(plateCount); // rad/Ma
        for (uint32_t i = 0; i < plateCount; ++i) {
            Plate& p = map.plates[i];
            const V3 pole = random.Direction();
            p.pole[0] = pole.x, p.pole[1] = pole.y, p.pole[2] = pole.z;
            const float u = random.Uniform();
            p.rate = Lerp(40.0f + 60.0f * u, 10.0f + 30.0f * u, p.continental) / radius;
            omega[i] = pole * p.rate;
        }

        // The boundaries: every cell beside another plate, with the plate it borders most; the boundary's point halfway
        // to that plate's cells.
        std::vector<Edge> edges;
        std::vector<uint8_t> beside(cells, 0);
        ForCells(cells, [&](uint32_t c) { cube.ForNeighbours(c, [&](uint32_t m) { beside[c] |= plate[m] != plate[c]; }); });
        for (uint32_t c = 0; c < cells; ++c) {
            if (!beside[c]) continue;
            uint16_t others[8];
            uint32_t across[8];
            int counts[8], kinds = 0;
            V3 sums[8];
            cube.ForNeighbours(c, [&](uint32_t m) {
                if (plate[m] == plate[c]) return;
                int k = 0;
                while (k < kinds && others[k] != plate[m]) ++k;
                if (k == kinds) others[k] = plate[m], across[k] = m, counts[k] = 0, sums[k] = {}, ++kinds;
                sums[k] = sums[k] + cube.p[m], ++counts[k];
            });
            if (!kinds) continue;
            const int k = int(std::max_element(counts, counts + kinds) - counts);
            Edge e = {};
            e.cell = c, e.across = across[k], e.plate = plate[c], e.other = others[k];
            e.at = Normalize(cube.p[c] + sums[k] * (1.0f / counts[k]));
            e.crust = continental[c], e.crustAcross = continental[e.across];
            edges.push_back(e);
        }
        const uint32_t edgeCount = uint32_t(edges.size());
        std::vector<uint32_t> seen(cells, None), walk, edgeOf(cells, None);
        for (uint32_t i = 0; i < edgeCount; ++i) edgeOf[edges[i].cell] = i;
        // Calls f(j, same) with each boundary cell beside edge i between the same two plates, `same` when it is on i's side.
        auto forPair = [&](uint32_t i, const auto& f) {
            const uint16_t a = edges[i].plate, b = edges[i].other;
            cube.ForNeighbours(edges[i].cell, [&](uint32_t m) {
                const uint32_t j = edgeOf[m];
                if (j == None) return;
                if (edges[j].plate == a && edges[j].other == b) f(j, true);
                else if (edges[j].plate == b && edges[j].other == a) f(j, false);
            });
        };
        // The boundary's points smoothed along it, on both sides: the line runs between the cells, not from cell to cell.
        {
            std::vector<V3> next(edgeCount);
            ForRounds(edgeCount, 4, [&](uint32_t i) {
                V3 sum = edges[i].at;
                forPair(i, [&](uint32_t j, bool) { sum = sum + edges[j].at; });
                next[i] = Normalize(sum);
            }, [&] { for (uint32_t i = 0; i < edgeCount; ++i) edges[i].at = next[i]; });
        }
        // Each boundary's normal, from the plate towards the other, between their cells within 4 steps: wider than the 8
        // neighbours' 45 degrees. The relative motion across it, and its speed.
        // Within 4 steps: a window of 9 x 9 cells inside a face, the walk near its edges.
        std::vector<float> across(edgeCount), along(edgeCount);
        auto normalOf = [&](uint32_t i, const auto& within) {
            Edge& e = edges[i];
            const V3 up = cube.p[e.cell];
            V3 normal = {};
            within([&](uint32_t k) {
                if (plate[k] == e.other) normal = normal + (cube.p[k] - up);
                else if (plate[k] == e.plate) normal = normal - (cube.p[k] - up);
            });
            normal = normal - up * Dot(normal, up);
            e.normal = Length(normal) > 0.0f ? Normalize(normal) : Normalize(cube.p[e.across] - up);
            const V3 relative = Cross(omega[e.plate] - omega[e.other], e.at) * radius; // km/Ma
            across[i] = Dot(relative, e.normal), along[i] = Length(relative);
        };
        const uint32_t n = map.size;
        auto inside = [&](uint32_t c) { const uint32_t i = c & (n - 1), j = (c >> cube.bits) & (n - 1); return i >= 4 && j >= 4 && i + 4 < n && j + 4 < n; };
        ForCells(edgeCount, [&](uint32_t i) {
            const uint32_t c = edges[i].cell;
            if (inside(c))
                normalOf(i, [&](const auto& f) { for (int dj = -4; dj <= 4; ++dj) for (int di = -4; di <= 4; ++di) f(c + dj * int(n) + di); });
        });
        for (uint32_t i = 0; i < edgeCount; ++i)
            if (!inside(edges[i].cell))
                normalOf(i, [&](const auto& f) { Around(cube, edges[i].cell, 4, seen, i, walk, f); });
        // The motions and the crusts averaged along the boundary, over about 100 km, by 32 rounds among the neighbouring
        // cells of the same two plates, on either side: its type then holds over its stretches and on both sides,
        // instead of changing from cell to cell where it is oblique or where a coast runs along it. Again once the active
        // margins are drawn.
        auto classify = [&] {
            std::vector<float> ac(across), al(along), ca(edgeCount), cb(edgeCount);
            std::vector<float> nextAcross(edgeCount), nextAlong(edgeCount), nextA(edgeCount), nextB(edgeCount);
            for (uint32_t i = 0; i < edgeCount; ++i) ca[i] = continental[edges[i].cell], cb[i] = continental[edges[i].across];
            ForRounds(edgeCount, 32, [&](uint32_t i) {
                float sumAcross = ac[i], sumAlong = al[i], sumA = ca[i], sumB = cb[i], count = 1.0f;
                forPair(i, [&](uint32_t j, bool same) {
                    sumAcross += ac[j], sumAlong += al[j], ++count;
                    sumA += same ? ca[j] : cb[j], sumB += same ? cb[j] : ca[j];
                });
                nextAcross[i] = sumAcross / count, nextAlong[i] = sumAlong / count, nextA[i] = sumA / count, nextB[i] = sumB / count;
            }, [&] { ac.swap(nextAcross), al.swap(nextAlong), ca.swap(nextA), cb.swap(nextB); });
            for (uint32_t i = 0; i < edgeCount; ++i) {
                Edge& e = edges[i];
                e.convergence = ac[i], e.along = al[i], e.crust = ca[i], e.crustAcross = cb[i];
                const bool x = e.crust > 0.5f, y = e.crustAcross > 0.5f;
                e.type = std::fabs(e.convergence) < kTransform * al[i] ? Transform
                       : e.convergence > 0.0f ? (x && y ? Collision : x || y ? OceanUnderContinent : OceanUnderOcean)
                       : x && y ? Rift : Ridge;
            }
        };
        classify();

        // The ocean floor's age: its distance to its plate's nearest ridge, over the plate's half spreading rate, the mean
        // along its ridges, so that it never jumps within a plate; on a plate without a ridge, to the nearest ridge over
        // the mean rate; 200 Ma at most. The field once the boundaries are settled; meanwhile, at the boundaries, for
        // which plate goes under, by a search over the ridges' cells.
        std::vector<float> age(cells, 0.0f);
        std::vector<Source> ridges;
        std::vector<float> halfRate(plateCount + 1, 0.0f); // the plate's, then the mean, for a plate without a ridge
        std::vector<std::vector<V3>> plateRidges(plateCount);
        auto spreading = [&] {
            ridges.clear();
            for (auto& r : plateRidges) r.clear();
            std::vector<float> count(plateCount + 1, 0.0f);
            std::fill(halfRate.begin(), halfRate.end(), 0.0f);
            for (const Edge& e : edges)
                if (e.type == Ridge) {
                    ridges.push_back({ e.cell, e.at }), plateRidges[e.plate].push_back(e.at);
                    halfRate[e.plate] -= 0.5f * e.convergence, ++count[e.plate], halfRate[plateCount] -= 0.5f * e.convergence, ++count[plateCount];
                }
            for (uint32_t i = 0; i <= plateCount; ++i) halfRate[i] = count[i] > 0.0f ? halfRate[i] / count[i] : 20.0f;
        };
        auto crustAge = [&](uint32_t c) {
            const bool own = !plateRidges[plate[c]].empty();
            float chord = INFINITY;
            if (own) for (const V3& r : plateRidges[plate[c]]) chord = std::min(chord, Length(cube.p[c] - r));
            else for (const Source& r : ridges) chord = std::min(chord, Length(cube.p[c] - r.at));
            const float km = chord < INFINITY ? arc(chord) : 4000.0f;
            return std::min(km / std::max(halfRate[own ? plate[c] : plateCount], 5.0f), kOldestCrust);
        };

        // Which plate goes under wherever the plates converge, oblique or not, one choice per pair: the oceanic side under
        // the continental; of two oceanic plates, the older crust; of two continents, the one that advances more into the
        // other. Then the profiles' families, by the sign of the motion across the boundary, not by its type: an oblique
        // boundary still raises its chain, weaker, and its stretch is never cut where the motion turns. Each family's
        // motion smoothed along the plate's boundary over about 200 km by 48 rounds, the other families' cells counting 0:
        // it falls to 0 at a stretch's ends, so that its chain or its trench tapers there. The transforms' share likewise.
        auto decide = [&] {
            spreading();
            std::vector<float> under(size_t(plateCount) * plateCount, 0.0f); // > 0: the row's plate under the column's
            for (const Edge& e : edges) {
                if (e.convergence <= 0.0f) continue;
                const bool x = e.crust > 0.5f, y = e.crustAcross > 0.5f;
                if (!x && !y) under[e.plate * plateCount + e.other] += crustAge(e.cell) - crustAge(e.across);
                if (x && y) under[e.plate * plateCount + e.other] += Dot(Cross(omega[e.plate] + omega[e.other], e.at), e.normal);
            }
            for (Edge& e : edges) {
                const float s = under[e.plate * plateCount + e.other] - under[e.other * plateCount + e.plate];
                const bool x = e.crust > 0.5f, y = e.crustAcross > 0.5f;
                e.under = x != y ? (x ? e.other : e.plate) : s > 0.0f || (s == 0.0f && e.plate < e.other) ? e.plate : e.other;
            }
            std::vector<float> drive(edgeCount), shear(edgeCount), next(edgeCount), nextShear(edgeCount);
            for (uint32_t i = 0; i < edgeCount; ++i) {
                Edge& e = edges[i];
                const bool x = e.crust > 0.5f, y = e.crustAcross > 0.5f;
                e.family = e.convergence > 2.0f ? (x && y ? Colliding : e.under == e.plate ? Subducting : Overriding)
                         : e.convergence < -2.0f ? (x && y ? Rifting : Spreading) : -1;
                drive[i] = e.family < 0 ? 0.0f : std::fabs(e.convergence);
                shear[i] = e.type == Transform ? 1.0f : 0.0f;
            }
            ForRounds(edgeCount, 48, [&](uint32_t i) {
                float sum = drive[i], sumShear = shear[i], count = 1.0f;
                cube.ForNeighbours(edges[i].cell, [&](uint32_t m) {
                    const uint32_t j = edgeOf[m];
                    if (j == None || edges[j].plate != edges[i].plate) return;
                    sum += edges[j].family == edges[i].family ? drive[j] : 0.0f, sumShear += shear[j], ++count;
                });
                next[i] = sum / count, nextShear[i] = sumShear / count;
            }, [&] { drive.swap(next), shear.swap(nextShear); });
            for (uint32_t i = 0; i < edgeCount; ++i) edges[i].drive = drive[i], edges[i].shear = shear[i];
        };
        decide();

        // The active margins: an ocean between a front that its plate overrides and a continent of that plate, less than
        // kActiveGap km across, was consumed: the continent reaches the trench and the ocean goes under it, as under the
        // Andes. Farther, the arc stays at sea, a marginal sea behind it, as Japan's.
        // The rifts that have broken their continent: an ocean floor across their opening, younger towards the axis, whose
        // boundary becomes a ridge and whose edges young margins.
        std::vector<uint8_t> rifted(cells, 0);
        {
            std::vector<Source> overriding, coasts, breaks;
            std::vector<float> opening, breakRate;
            for (const Edge& e : edges) {
                if (e.family == Overriding && e.crust < 0.5f) overriding.push_back({ e.cell, e.at });
                if (e.type != Rift) continue;
                const uint32_t a = std::min(e.plate, e.other), b = std::max(e.plate, e.other);
                const float ma = kRiftMa * (0.5f + float(Hash(a * 65536u + b + 7919u * body.seed) >> 8) / 16777216.0f);
                const float width = std::min(-e.convergence * ma, kNarrowSea);
                if (width >= kSeaOpening) breaks.push_back({ e.cell, e.at }), opening.push_back(width), breakRate.push_back(-e.convergence);
            }
            // The coasts seen from each plate's oceans, the only cells whose margin is decided here.
            std::vector<uint32_t> beyond(cells, None);
            std::vector<uint16_t> sea(cells);
            ForCells(cells, [&](uint32_t c) {
                sea[c] = continental[c] ? NoRegion : plate[c];
                if (!continental[c])
                    cube.ForNeighbours(c, [&](uint32_t m) { if (beyond[c] == None && plate[m] == plate[c] && continental[m]) beyond[c] = m; });
            });
            for (uint32_t c = 0; c < cells; ++c) if (beyond[c] != None) coasts.push_back({ c, Normalize(cube.p[c] + cube.p[beyond[c]]) });
            std::vector<float> frontChord, coastChord, breakChord;
            std::vector<uint32_t> toFront, toCoast, toBreak;
            const float gap = Chord(kActiveGap / radius);
            Together({ [&] { toFront = Nearest(cube, overriding, plate.data(), frontChord, gap); },
                       [&] { toCoast = Nearest(cube, coasts, sea.data(), coastChord, gap); },
                       [&] { toBreak = Nearest(cube, breaks, nullptr, breakChord, Chord(0.5f * kNarrowSea / radius)); } });
            ForCells(cells, [&](uint32_t c) {
                if (!continental[c] && toFront[c] != None && toCoast[c] != None && arc(frontChord[c]) + arc(coastChord[c]) < kActiveGap)
                    continental[c] = 1;
                else if (continental[c] && toBreak[c] != None && arc(breakChord[c]) < 0.5f * opening[toBreak[c]])
                    continental[c] = 0, rifted[c] = 1, age[c] = std::max(2.0f * arc(breakChord[c]) / breakRate[toBreak[c]], 0.5f);
            });
            Clean(cube, continental);
            map.continental = 0.0f;
            for (Plate& p : map.plates) p.continental = 0.0f;
            for (uint32_t c = 0; c < cells; ++c)
                if (continental[c]) {
                    const float share = cube.Area(c) / float(4.0 * kPi);
                    map.continental += share, map.plates[plate[c]].continental += share / map.plates[plate[c]].area;
                    rifted[c] = 0;
                }
        }

        // The floods, independent of one another, each on its thread: the continents' margins', as soon as the crust is
        // settled; every boundary's, within the plates; each family of boundaries on its own, within the plates, so that a
        // chain's profile follows its own front, never cut where another boundary becomes the nearest.
        std::vector<Source> fronts, margins;
        std::vector<uint8_t> marginYoung;
        std::vector<float> ridgeChord, globalChord;
        std::vector<uint32_t> ridge, globalRidge;
        std::vector<float> frontChord, marginChord;
        std::vector<uint32_t> front, margin;
        {
            std::vector<uint32_t> beyond(cells, None);
            ForCells(cells, [&](uint32_t c) {
                cube.ForNeighbours(c, [&](uint32_t m) { if (beyond[c] == None && continental[m] != continental[c]) beyond[c] = m; });
            });
            for (uint32_t c = 0; c < cells; ++c)
                if (beyond[c] != None)
                    margins.push_back({ c, Normalize(cube.p[c] + cube.p[beyond[c]]) }), marginYoung.push_back(rifted[c] | rifted[beyond[c]]);
        }
        std::thread edgesOfContinents([&] { margin = Nearest(cube, margins, nullptr, marginChord, Chord(kMarginReach / radius)); });
        classify();
        decide();
        for (const Edge& e : edges) fronts.push_back({ e.cell, e.at });
        std::vector<Source> familySources[Families];
        std::vector<uint32_t> familyEdges[Families], familyNearest[Families];
        std::vector<float> familyChord[Families];
        for (uint32_t i = 0; i < edgeCount; ++i) {
            const int f = edges[i].family;
            if (f < 0 || f >= Families) continue;
            familySources[f].push_back({ edges[i].cell, edges[i].at });
            familyEdges[f].push_back(i);
        }
        {
            std::vector<std::function<void()>> jobs = { [&] { front = Nearest(cube, fronts, plate.data(), frontChord, Chord(kBoundaryReach / radius)); },
                                                        [&] { ridge = Nearest(cube, ridges, plate.data(), ridgeChord); } };
            if (std::any_of(plateRidges.begin(), plateRidges.end(), [](const std::vector<V3>& r) { return r.empty(); }))
                jobs.push_back([&] { globalRidge = Nearest(cube, ridges, nullptr, globalChord); });
            for (int f = 0; f < Families; ++f)
                jobs.push_back([&, f] { familyNearest[f] = Nearest(cube, familySources[f], plate.data(), familyChord[f], Chord(1500.0f / radius)); });
            Together(jobs);
        }
        cratons.join();
        edgesOfContinents.join();
        ForCells(cells, [&](uint32_t c) {
            if (continental[c] || rifted[c]) return;
            const bool own = ridge[c] != None;
            const float km = own ? arc(ridgeChord[c]) : !globalRidge.empty() && globalRidge[c] != None ? arc(globalChord[c]) : 4000.0f;
            age[c] = std::min(km / std::max(halfRate[own ? plate[c] : plateCount], 5.0f), kOldestCrust);
        });
        cube.Blur({ &age }, { 2 });

        // The margins: active where the continent's edge is a subduction under it, young where a rift has just broken it,
        // passive elsewhere, the shelves wide.
        std::vector<float> marginKm(cells), active(cells), youngMargin(cells);
        {
            std::vector<float> sourceActive(margins.size());
            for (size_t s = 0; s < margins.size(); ++s) {
                const uint32_t c = margins[s].cell;
                sourceActive[s] = front[c] != None && arc(frontChord[c]) < 60.0f && edges[front[c]].family == Overriding;
            }
            ForCells(cells, [&](uint32_t c) {
                marginKm[c] = (continental[c] ? 1.0f : -1.0f) * (margin[c] == None ? kMarginReach : arc(marginChord[c]));
                active[c] = margin[c] == None ? 0.0f : sourceActive[margin[c]];
                youngMargin[c] = margin[c] == None ? 0.0f : marginYoung[margin[c]];
            });
            cube.Blur({ &marginKm, &active, &youngMargin }, { 2, 3, 3 });
        }

        // The fields, cell by cell (Tectonics.hlsli): the large forms from published profiles, the relief's amplitude and
        // character, the sharp profiles' amplitudes, the classes; the uplift and the erodibility, the level 0's inputs.
        enum { Elevation, Relief, Youth, Strata, Axis, Trench, Divergent, Shear, Side, Orientation, RockClass, PlateClass,
               AgeMa, MarginKm, UpliftMm, SutureKm, Erodibility, Empty, Fields };
        std::vector<std::vector<float>> field(Fields, std::vector<float>(cells, 0.0f));
        ForCells(cells, [&](uint32_t c) {
            const float dc = marginKm[c], t = age[c], young = youngMargin[c], steep = std::max(active[c], young);
            // The regional variations, bounded: tanh of the standardised noise.
            float z[12];
            readRegional(cube.p[c], z);
            const float zi = std::tanh(z[InteriorZ]), zs = z[ShelfZ], zv = std::tanh(z[VaryZ]), zr = std::tanh(z[ReliefZ]);
            const float land = Smooth(-100.0f, 60.0f, dc); // 0 on oceanic crust, 1 on a continent, across its margin

            // The crust and its margin (Kennett, Marine Geology): the slope from its foot, at the continent's edge, to the
            // shelf break; the shelf, 50 to 250 km wide on a passive margin, 12 on an active or a young one; then the
            // coastal plain. A narrow sea is shallower, its young floor lifted and filled: 1.5 to 3 km, as the Red Sea's.
            const float slopeKm = Lerp(70.0f, 35.0f, steep), shelfKm = Lerp(Lerp(50.0f, 250.0f, Smooth(-1.2f, 1.2f, zs)), 12.0f, steep);
            const float shelfBreak = Lerp(-140.0f, -250.0f, steep), foot = Lerp(-3300.0f, -1800.0f, young), coastKm = slopeKm + shelfKm;
            const float interior = 280.0f + 220.0f * zi + 120.0f * Sat(dc / 2000.0f);
            float e;
            // The ocean floor swells and sags by a few hundred metres over thousands of km, as the mantle below moves.
            if (dc <= 0.0f) e = Lerp(foot, OceanDepth(t) + 400.0f * std::tanh(z[OceanZ]) + 1000.0f * young, Smooth(0.0f, 160.0f, -dc));
            else if (dc < slopeKm) { const float u = dc / slopeKm; e = Lerp(foot, shelfBreak, u * u * u * (u * (u * 6.0f - 15.0f) + 10.0f)); }
            else if (dc < coastKm) e = Lerp(shelfBreak, 0.0f, (dc - slopeKm) / shelfKm);
            else e = interior * (1.0f - std::exp(-(dc - coastKm) / Lerp(160.0f, 60.0f, steep)));

            // The uplifts of the chains, arcs and shoulders combine as a smooth maximum, (sum of u^4)^(1/4): where two
            // stand together, the higher one, never their sum. Their relief and their uplift rate likewise: each form
            // rises at a share of its convergence (mm/yr), where it stands, as the level 0 needs it (sink: the subsidence).
            float lift = 0.0f, liftRelief = 0.0f, rise = 0.0f, sink = 0.0f;
            float old = 0.0f, youngAge = 1.0f, volcanic = 0.0f, foreland = 0.0f, graben = 0.0f;
            auto raise = [&](float u, float r, float rate) { lift += u * u * u * u, liftRelief += r * r * r * r, rise += rate * rate * rate * rate; };
            auto family = [&](int f, float& x) -> const Edge* {
                const uint32_t k = familyNearest[f][c];
                if (k == None) return nullptr;
                x = arc(familyChord[f][c]);
                return x < 1500.0f ? &edges[familyEdges[f][k]] : nullptr;
            };
            float x;
            // Over a subduction: a cordillera on a continent, 150 to 400 km wide, to 4.5 km in the mean, an arc on its
            // crest; an island arc on an ocean, 150 to 200 km from the trench (Stern 2002).
            if (const Edge* b = family(Overriding, x)) {
                const float cc = Sat(b->drive / 60.0f), v = Sat(b->drive / 10.0f);
                const float h = (1400.0f + 1800.0f * cc) * (1.0f + 0.2f * zv) * v * land, w = 150.0f + 250.0f * cc, x0 = 90.0f + 30.0f * cc;
                const float shape = Smooth(x0, x0 + 100.0f, x) * (1.0f - Smooth(x0 + 100.0f + w, x0 + 240.0f + w, x));
                raise(h * shape, (1000.0f + 1300.0f * cc) * (1.0f + 0.2f * zr) * v * land * Smooth(x0 - 40.0f, x0 + 80.0f, x)
                                 * (1.0f - Smooth(x0 + 100.0f + w, x0 + 300.0f + w, x)), 0.04f * b->drive * v * land * shape);
                const float arcShape = v * (1.0f - land) * Bell(x, 175.0f, 55.0f);
                raise((3300.0f + 900.0f * Sat(b->drive / 80.0f)) * arcShape, 1500.0f * v * (1.0f - land) * Bell(x, 175.0f, 75.0f),
                      0.03f * b->drive * arcShape);
                volcanic = std::max(volcanic, v * std::max(Bell(x, 175.0f, 60.0f) * (1.0f - land), Bell(x, x0 + 80.0f, 50.0f) * land));
            }
            // Under a subduction: the outer rise, the plate's flexure before the trench, a few hundred metres 100 to 200 km
            // out (Turcotte and Schubert, Geodynamics, 3.17).
            if (const Edge* b = family(Subducting, x))
                e += 380.0f * Sat(b->drive / 50.0f) * (1.0f - land) * Bell(x, 150.0f, 65.0f);
            // A collision: a chain 200 to 400 km wide, 3 to 5 km in the mean; behind it, where the convergence is strong,
            // a plateau of 4.6 km up to 900 km wide (Tibet); before it, the foreland's flexure, filled with sediments.
            if (const Edge* b = family(Colliding, x)) {
                const float cc = Sat(b->drive / 40.0f), v = Sat(b->drive / 8.0f) * land;
                const float h = (1700.0f + 1300.0f * cc) * (1.0f + 0.2f * zv) * v;
                const float ridgeRelief = (1200.0f + 1100.0f * cc) * (1.0f + 0.2f * zr) * v;
                if (b->under == b->plate) {
                    const float flexure = Sat(b->drive / 30.0f) * v * Bell(x, 240.0f, 90.0f);
                    e -= 450.0f * flexure, sink -= 0.02f * b->drive * flexure;
                    const float shape = 1.0f - Smooth(40.0f, 170.0f, x);
                    raise(h * shape, ridgeRelief * (1.0f - Smooth(50.0f, 200.0f, x)), 0.12f * b->drive * v * shape);
                    foreland = std::max(foreland, v * Bell(x, 250.0f, 110.0f));
                } else {
                    const float pc = Sat((b->drive - 15.0f) / 25.0f), wp = (150.0f + 650.0f * pc) * (1.0f + 0.3f * zr);
                    const float plateau = pc * v * (1.0f - Smooth(0.4f * wp, wp + 300.0f, x)), shape = 1.0f - Smooth(60.0f, 210.0f, x);
                    raise(h * shape, ridgeRelief * (1.0f - Smooth(70.0f, 230.0f, x)), 0.12f * b->drive * v * shape);
                    raise(4000.0f * (1.0f + 0.15f * zv) * plateau, 800.0f * plateau, 0.03f * b->drive * plateau);
                }
            }
            // A continental rift, emerged: a broad thermal dome, 1.2 km over some 400 km, as East Africa's; its shoulders,
            // up to 1.1 km 50 km from the axis; the graben is the shader's, its floor above the sea.
            if (const Edge* b = family(Rifting, x)) {
                const float v = land * Sat(b->drive / 5.0f);
                raise(1100.0f * v * Bell(x, 55.0f, 35.0f), 450.0f * v * Bell(x, 55.0f, 45.0f), 0.08f * b->drive * v * Bell(x, 55.0f, 35.0f));
                raise(1200.0f * v * Bell(x, 0.0f, 220.0f), 250.0f * v * Bell(x, 0.0f, 250.0f), 0.04f * b->drive * v * Bell(x, 0.0f, 220.0f));
                graben = std::max(graben, v * (1.0f - Smooth(20.0f, 70.0f, x)));
                sink -= 0.1f * b->drive * v * (1.0f - Smooth(20.0f, 40.0f, x));
            }
            // A narrow sea's young margins: the rift's shoulders above their coasts, as the Red Sea's.
            const float shoulder = young * land * Bell(dc, coastKm + 40.0f, 40.0f);
            raise(1100.0f * shoulder, 450.0f * shoulder, 0.5f * shoulder);
            // The old chains, along the sutures: their height falls with their age, A0 exp(-age / 250 Ma), 750 m in the mean
            // at 300 Ma, as the Appalachians and the Urals.
            const float sutureKm = suture[c] == None ? 20000.0f : arc(sutureChord[c]);
            const float sutureMa = suture[c] == None ? 0.0f : sutureAge[suture[c]];
            if (suture[c] != None) {
                const float a = 2600.0f * std::exp(-sutureMa / 250.0f) * land;
                raise(0.5f * a * Bell(sutureKm, 0.0f, 110.0f), 0.0f, 0.0f);
                old = 0.75f * a * Bell(sutureKm, 0.0f, 150.0f);
                youngAge = std::exp(-sutureMa / 180.0f);
            }
            e += std::sqrt(std::sqrt(lift));
            const float chains = std::sqrt(std::sqrt(liftRelief));
            // The relief left to the noise where no chain stands: the ocean floor's abyssal hills, rougher on young crust;
            // the shields' hills; the platforms' low swells; the shelves, smooth.
            const float shield = Smooth(0.2f, 1.0f, z[ShieldZ]);
            const float continentRelief = Lerp(30.0f, 70.0f + 220.0f * shield, Smooth(coastKm, coastKm + 150.0f, dc));
            const float base = Lerp(110.0f + 200.0f * std::exp(-t / 25.0f), continentRelief, land);
            const float mesas = Smooth(0.3f, 1.0f, z[MesaZ]);

            // Flat-lying strata on the stable platforms, mesas where they are cut; soft sediments in the forelands, the
            // grabens and the coastal plains, badlands where they are cut.
            const float platform = land * (1.0f - shield) * (1.0f - Sat(chains / 300.0f)) * (1.0f - Sat(old / 400.0f))
                                 * Smooth(coastKm, coastKm + 200.0f, dc);
            const float relief = base + chains + old;
            const float soft = land * std::max(std::max(foreland, graben), 0.6f * (1.0f - Smooth(coastKm + 30.0f, coastKm + 250.0f, dc)) * Smooth(coastKm - 20.0f, coastKm, dc))
                             * Smooth(0.5f, 1.2f, z[SoftZ]);
            field[Strata][c] = platform * mesas - soft;
            field[Elevation][c] = e;
            field[Relief][c] = relief;
            field[Youth][c] = (chains + old * youngAge) / relief;

            // The nearest boundary: the sharp profiles' amplitudes there, faded beyond 150 km; its distance, signed across a
            // transform by the plates' order. Past kBoundaryReach, none.
            const Edge& b = edges[front[c] == None ? 0 : front[c]];
            const float d = front[c] == None ? kBoundaryReach : arc(frontChord[c]), fade = 1.0f - Smooth(150.0f, 300.0f, d);
            const float drive = Sat(b.drive / 10.0f);
            const bool goesUnder = b.type <= Collision && b.under == plate[c];
            if (b.family == Overriding || b.family == Subducting) {
                const float subducted = age[b.under == b.plate ? b.cell : b.across];
                field[Trench][c] = (2100.0f + 1500.0f * Sat(b.drive / 70.0f) + 700.0f * Sat(subducted / 100.0f)) * drive * fade;
            }
            if (b.family == Spreading) // an axial valley on a slow ridge, a dome on a fast one (Macdonald 1982); half in a narrow sea
                field[Divergent][c] = Lerp(-1600.0f, 350.0f, Sat((-0.5f * b.convergence - 15.0f) / 35.0f)) * drive * fade * (1.0f - 0.5f * young);
            if (b.family == Rifting)
                field[Divergent][c] = -(500.0f + 300.0f * Sat(b.drive / 20.0f)) * Sat(b.drive / 5.0f) * fade;
            // a fracture zone's trough in the ocean, a fault's valley on a continent
            field[Shear][c] = (b.crust > 0.5f && b.crustAcross > 0.5f ? 600.0f : 1200.0f) * Smooth(0.2f, 0.7f, b.shear) * fade;
            field[Axis][c] = d;
            field[Side][c] = (b.plate < b.other ? 1.0f : -1.0f) * std::min(d, 300.0f);
            field[SutureKm][c] = sutureKm;

            // The rock at the surface, by class; its erodibility, the softest sediments twice the others'.
            Rock rock = OceanicCrust;
            if (!continental[c]) rock = volcanic > 0.4f ? Volcanic : OceanicCrust;
            else if (volcanic > 0.5f) rock = Volcanic;
            else if (chains > 600.0f) rock = YoungBelt;
            else if (old > 300.0f) rock = OldBelt;
            else if (shield > 0.5f) rock = Shield;
            else rock = Sediments;
            field[RockClass][c] = float(rock + 8 * continental[c]);
            field[PlateClass][c] = float(plate[c] + 32 * b.type + 256 * goesUnder);
            field[AgeMa][c] = continental[c] ? 0.0f : t;
            field[MarginKm][c] = dc;
            field[UpliftMm][c] = std::sqrt(std::sqrt(rise)) + sink;
            field[Erodibility][c] = kErodibility[rock] * (1.0f + soft);
            field[Orientation][c] = d;
        });

        // The volcanism (docs/spec-volcanisme.md): the volcanoes listed, each with its edifice, for the shader to evaluate
        // point by point (Volcanoes.hlsli); the hotspots' swells and their plume heads' lava plateaus in the fields; then
        // the volcanoes' index. Every volcano is placed where the map holds the form it belongs to, then moved back by the
        // relief's warp of its reading of the map, to stand on that form as the shader draws it.
        const auto volcanism = std::chrono::steady_clock::now();
        {
            const Gradients gradients;
            const float texelKm = float(kPi / 2.0) * radius / n; // at a face's centre, more than anywhere else
            auto uniform = [&](uint32_t a, uint32_t b) { return float(Hash(Hash(a * 0x9E3779B9u + body.seed) + b * 0x85EBCA77u) >> 8) / 16777216.0f; };
            // The point `km` from `from` on the great circle towards `towards`.
            auto toward = [&](V3 from, V3 towards, float km) {
                V3 t = towards - from * Dot(towards, from);
                const float l = Length(t);
                if (l < 1e-9f) return from;
                const float a = km / radius;
                return from * std::cos(a) + t * (std::sin(a) / l);
            };
            struct Draft { V3 at; uint32_t cell; Volcano v; }; // at, cell: where it reads the map
            std::vector<Draft> drafts;
            Volcano blank = {};
            blank.top = NoTop;

            // Along the arcs and the rifts, candidates thinned in the order of their keys: each kept unless a kept one lies
            // within its spacing.
            struct Candidate { V3 at; uint32_t cell; float spacing; uint32_t key; };
            auto thin = [&](std::vector<Candidate>& list) {
                std::sort(list.begin(), list.end(), [](const Candidate& a, const Candidate& b) { return a.key < b.key || (a.key == b.key && a.cell < b.cell); });
                std::vector<Candidate> kept;
                for (const Candidate& c : list) {
                    const float chord = Chord(c.spacing / radius);
                    if (std::none_of(kept.begin(), kept.end(), [&](const Candidate& k) { return Length(k.at - c.at) < chord; })) kept.push_back(c);
                }
                return kept;
            };
            // Each cell's candidates of the three kinds on all the threads, then gathered in the cells' order.
            std::vector<Candidate> found(3 * size_t(cells));
            std::vector<uint8_t> has(3 * size_t(cells), 0);
            ForCells(cells, [&](uint32_t c) {
                // Over a subduction, the volcanic front: where the slab reaches some 100 km down, 140 to 230 km from the
                // trench, as the map's arc (Stern 2002); none where the slab lies flat, by stretches. Behind it on a
                // continent, fields of small cones.
                const uint32_t k = familyNearest[Overriding][c], r = familyNearest[Rifting][c];
                if (k != None) {
                    const float x = arc(familyChord[Overriding][c]);
                    const Edge& b = edges[familyEdges[Overriding][k]];
                    if (x < 400.0f && b.drive > 5.0f) {
                        float z[12];
                        readRegional(cube.p[c], z);
                        const float land = Smooth(-100.0f, 60.0f, marginKm[c]), cc = Sat(b.drive / 60.0f);
                        const float front = Lerp(175.0f, 170.0f + 30.0f * cc, land) + 25.0f * std::tanh(z[VaryZ]);
                        const V3 source = familySources[Overriding][k].at;
                        if (z[ReliefZ] > -1.2f && std::fabs(x - front) < 0.7f * texelKm)
                            has[3 * c] = 1, found[3 * c] = { toward(source, cube.p[c], front), c, 35.0f + 45.0f * uniform(c, 1), Hash(c ^ 0xA5C3u) };
                        if (land > 0.5f && std::fabs(x - front - 110.0f) < 0.7f * texelKm && uniform(c, 2) < 0.5f)
                            has[3 * c + 1] = 1, found[3 * c + 1] = { toward(source, cube.p[c], front + 110.0f), c, 180.0f + 120.0f * uniform(c, 3), Hash(c ^ 0x5A3Cu) };
                    }
                }
                // Along a continental rift, within 60 km of its axis (the East African rift).
                if (r != None && continental[c]) {
                    const Edge& b = edges[familyEdges[Rifting][r]];
                    if (arc(familyChord[Rifting][c]) < 60.0f && b.drive > 2.5f)
                        has[3 * c + 2] = 1, found[3 * c + 2] = { cube.p[c], c, 70.0f + 80.0f * uniform(c, 4), Hash(c ^ 0x3CA5u) };
                }
            });
            std::vector<Candidate> arcs, backArcs, rifts;
            for (uint32_t c = 0; c < cells; ++c) {
                if (has[3 * c]) arcs.push_back(found[3 * c]);
                if (has[3 * c + 1]) backArcs.push_back(found[3 * c + 1]);
                if (has[3 * c + 2]) rifts.push_back(found[3 * c + 2]);
            }
            // A stratovolcano: 2 to 4 km high, its flanks concave (Karátson et al. 2010), its height a sixth to a ninth of
            // its base's diameter; a crater of 0.4 to 1.1 km; some collapsed in a caldera of 4 to 10 km (Crater Lake). At
            // sea, a quarter higher, built from the foot of the arc's ridge, 1 to 2 km under the sea (the Aleutians).
            for (const Candidate& a : thin(arcs)) {
                Volcano v = blank;
                auto u = [&](uint32_t i) { return uniform(a.cell, 16 + i); };
                const bool caldera = u(0) < 0.12f;
                v.height = (2000.0f + 2000.0f * u(1)) * (caldera ? 0.75f : 1.0f) * Lerp(1.25f, 1.0f, Smooth(-100.0f, 60.0f, marginKm[a.cell]));
                v.radius = v.height / 1000.0f * (caldera ? 7.0f + 3.0f * u(2) : 4.5f + 3.0f * u(2));
                v.shape = 0.15f * u(3);
                v.crater = caldera ? 2.0f + 3.0f * u(4) : 0.2f + 0.35f * u(4);
                v.depth = caldera ? 400.0f + 500.0f * u(5) : 100.0f + 200.0f * u(5);
                v.cones = u(6) < 0.35f ? 0.15f + 0.3f * u(7) : 0.0f;
                v.fresh = 0.6f + 0.4f * u(8);
                drafts.push_back({ a.at, a.cell, v });
            }
            // A field of small cones on a low shield of flows (the Michoacán-Guanajuato field).
            for (const Candidate& a : thin(backArcs)) {
                Volcano v = blank;
                auto u = [&](uint32_t i) { return uniform(a.cell, 32 + i); };
                v.height = 100.0f + 150.0f * u(0), v.radius = 20.0f + 20.0f * u(1), v.shape = 1.0f;
                v.cones = 0.4f + 0.4f * u(2), v.fresh = 0.5f + 0.5f * u(3);
                drafts.push_back({ a.at, a.cell, v });
            }
            // Along a rift: stratovolcanoes up to 4.5 km above the plain (Kilimanjaro), shields, calderas (Menengai), each in
            // its field of cones.
            for (const Candidate& a : thin(rifts)) {
                Volcano v = blank;
                auto u = [&](uint32_t i) { return uniform(a.cell, 48 + i); };
                const float kind = u(0);
                if (kind < 0.4f)
                    v.height = 1500.0f + 3000.0f * u(1), v.radius = v.height / 1000.0f * (5.0f + 3.0f * u(2)), v.shape = 0.15f,
                    v.crater = 0.3f + 0.4f * u(3), v.depth = 100.0f + 200.0f * u(4);
                else if (kind < 0.65f)
                    v.height = 600.0f + 900.0f * u(1), v.radius = v.height / 1000.0f * (14.0f + 6.0f * u(2)), v.shape = 1.0f,
                    v.crater = 0.5f + 1.0f * u(3), v.depth = 50.0f + 100.0f * u(4);
                else
                    v.height = 500.0f + 700.0f * u(1), v.radius = 12.0f + 10.0f * u(2), v.shape = 0.3f,
                    v.crater = 3.0f + 3.0f * u(3), v.depth = 250.0f + 250.0f * u(4);
                v.cones = 0.2f + 0.5f * u(5), v.fresh = 0.5f + 0.5f * u(6);
                drafts.push_back({ a.at, a.cell, v });
            }

            // The hotspots: plumes fixed in the mantle, 8 to 16, the plates moving over them (Wilson 1963, Morgan 1971). Each
            // leaves a chain along its plate's motion, a volcano every 40 to 90 km at sea, the youngest over the plume; the
            // chain ends where its plate's crust is younger than the volcano would be, at the plate's boundary, or at the
            // plume's head, 30 to 130 Ma old, whose flood of lava made a plateau: traps on a continent (the Deccan), an
            // oceanic plateau at sea (Ontong Java).
            Random draw{ 0x9FB21C651E98DF25ull * (uint64_t(body.seed) + 1) };
            map.hotspots = 8 + uint32_t(draw.Next() % 9);
            struct Stop { V3 at; uint32_t cell; float age, strength; };
            struct Plume { std::vector<Stop> stops; V3 at; float reach; }; // reach: a chord around it holding its swell
            const float swellAge = 25.0f, swellChord = Chord(1200.0f / radius);
            struct Province { V3 at; float km, height, chord; bool land; };
            std::vector<Plume> plumes;
            std::vector<Province> provinces;
            std::vector<V3> placed;
            for (uint32_t h = 0; h < map.hotspots; ++h) {
                V3 plume = {};
                float bestGap = -1.0f;
                for (int k = 0; k < 16; ++k) {
                    const V3 d = draw.Direction();
                    float gap = 4.0f;
                    for (const V3& s : placed) gap = std::min(gap, Length(d - s));
                    if (gap > bestGap) bestGap = gap, plume = d;
                }
                placed.push_back(plume);
                const float strength = 0.4f + 0.6f * draw.Uniform(), started = 30.0f + 100.0f * draw.Uniform();
                const uint16_t P = plate[cube.CellOf(plume)];
                const float rate = Length(omega[P]), speed = std::max(Length(Cross(omega[P], plume)) * radius, 5.0f); // km/Ma
                const V3 axis = rate > 0.0f ? omega[P] * (1.0f / rate) : V3{ 0.0f, 1.0f, 0.0f };
                auto carried = [&](float t) { // where the plate has carried the point over the plume t Ma ago (Rodrigues)
                    const float a = rate * t, ca = std::cos(a), sa = std::sin(a);
                    return plume * ca + Cross(axis, plume) * sa + axis * (Dot(axis, plume) * (1.0f - ca));
                };
                Plume chain = { {}, plume, 0.0f };
                bool whole = true;
                for (float t = 0.0f; t <= started;) {
                    const V3 p = carried(t);
                    const uint32_t c = cube.CellOf(p);
                    if (plate[c] != P || (!continental[c] && age[c] < t) || chain.stops.size() >= 64) { whole = false; break; }
                    chain.stops.push_back({ p, c, t, strength });
                    if (t < swellAge) chain.reach = std::max(chain.reach, Length(p - plume));
                    t += (continental[c] ? 120.0f + 80.0f * draw.Uniform() : 40.0f + 50.0f * draw.Uniform()) / speed;
                }
                chain.reach += swellChord;
                plumes.push_back(chain);
                if (!whole) continue;
                const V3 head = carried(started);
                const uint32_t c = cube.CellOf(head);
                if (plate[c] != P || (!continental[c] && age[c] < started)) continue;
                const float km = continental[c] ? 300.0f + 400.0f * draw.Uniform() : 300.0f + 300.0f * draw.Uniform();
                const float height = continental[c] ? (800.0f + 800.0f * draw.Uniform()) * std::exp(-started / 200.0f) : 1500.0f + 1000.0f * draw.Uniform();
                provinces.push_back({ head, km, height, Chord(1.2f * km / radius), continental[c] != 0 });
            }
            // The swell around a plume and along its young chain, some 1 km over 400 km on either side, fading as the plate
            // carries the chain away (the Hawaiian swell); weaker under a continent. The plateaus: the traps a stack of flows,
            // in steps (the platforms' mesas, Relief.hlsli), with an escarpment at their edge; an oceanic plateau a broad dome.
            ForCells(cells, [&](uint32_t c) {
                const V3 p = cube.p[c];
                const float land = Smooth(-100.0f, 60.0f, marginKm[c]);
                float swell = 0.0f;
                for (const Plume& plume : plumes) {
                    if (Length(p - plume.at) > plume.reach) continue;
                    for (const Stop& s : plume.stops) {
                        if (s.age >= swellAge) break; // the stops come in their age's order
                        const float d = Length(p - s.at);
                        if (d < swellChord) swell = std::max(swell, (600.0f + 700.0f * s.strength) * std::exp(-s.age / 10.0f) * Bell(arc(d), 0.0f, 380.0f));
                    }
                }
                float e = swell * Lerp(1.0f, 0.6f, land);
                for (const Province& v : provinces) {
                    const float d = Length(p - v.at);
                    if (d > v.chord) continue;
                    const float km = arc(d);
                    if (v.land) {
                        const float plateau = land * (1.0f - Smooth(0.75f * v.km, v.km, km));
                        e += v.height * plateau;
                        field[Strata][c] = std::max(field[Strata][c], 0.8f * plateau);
                        if (plateau > 0.4f) field[RockClass][c] = float(Volcanic + 8 * continental[c]), field[Erodibility][c] = kErodibility[Volcanic];
                    } else
                        e += v.height * (1.0f - land) * (1.0f - Smooth(0.4f * v.km, v.km, km));
                }
                field[Elevation][c] += e;
            });
            // The chains' volcanoes. At sea, shields 4 to 9 km above the floor, most of them weak hotspots' seamounts, an
            // eighth of their base's radius, their flanks nearly straight, their summit 4.5 km above the sea at most
            // (Mauna Loa, Mauna Kea);
            // the youngest with its caldera and its cones. As the plate carries them away they subside, by the swell's decay
            // and the plate's cooling, about 1 km in 30 Ma; an island's top is planed by the waves meanwhile, then sinks: a
            // guyot. In the tropics, a reef mostly settles on the island's platform cut by the waves, half as wide as the
            // island at 1.5 Ma, and keeps at the sea's level as it sinks: a barrier, then an atoll (Darwin 1842). On a continent, a caldera every 120 to 200 km for 15 Ma (the Snake River
            // Plain to Yellowstone).
            auto subsided = [](float t) { return 1000.0f * (1.0f - std::exp(-t / 15.0f)) + 6.0f * t; }; // m
            for (uint32_t h = 0; h < plumes.size(); ++h)
                for (size_t k = 0; k < plumes[h].stops.size(); ++k) {
                    const Stop& s = plumes[h].stops[k];
                    Volcano v = blank;
                    auto u = [&](uint32_t i) { return uniform(h * 1024u + uint32_t(k), 64 + i); };
                    v.fresh = std::exp(-s.age / 3.0f);
                    if (continental[s.cell]) {
                        if (s.age > 15.0f) continue;
                        v.height = 400.0f + 400.0f * s.strength, v.radius = 40.0f + 30.0f * u(0), v.shape = 1.0f;
                        v.crater = 10.0f + 15.0f * u(1), v.depth = (300.0f + 400.0f * u(2)) * std::exp(-s.age / 6.0f), v.cones = 0.3f;
                        drafts.push_back({ s.at, s.cell, v });
                        continue;
                    }
                    v.height = (3500.0f + 5500.0f * s.strength * s.strength) * (k == 0 ? 1.0f : 0.6f + 0.4f * u(0));
                    v.radius = v.height / 1000.0f * (7.0f + 3.0f * u(1)), v.shape = 1.0f;
                    v.height = std::min(v.height, 4500.0f - field[Elevation][s.cell]);
                    if (s.age < 2.0f) v.crater = 1.5f + 1.5f * u(2), v.depth = 100.0f + 150.0f * u(3), v.cones = 0.25f;
                    const float bottom = field[Elevation][s.cell], sunk = subsided(s.age), built = bottom + sunk + v.height;
                    if (built > 0.0f && s.age > 0.5f) v.top = built * std::exp(-s.age / 4.0f) - sunk;
                    // The reef: half the radius of the shore at 1.5 Ma, where a shield's profile, 1 - x^1.3 (Volcanoes.hlsli),
                    // stood at the sea's level then; some drowned all the same.
                    const float g = -(bottom + sunk - subsided(1.5f)) / v.height;
                    if (built > 0.0f && s.age > 1.5f && std::fabs(s.at.y) < std::sin(26.0f * float(kPi) / 180.0f) && g > 0.0f && g < 0.8f && u(4) < 0.7f)
                        v.reef = 0.5f * v.radius * std::pow(1.0f - g, 1.0f / 1.3f);
                    drafts.push_back({ s.at, s.cell, v });
                }

            // The volcanoes in their place, their rock volcanic around them, their seeds.
            std::vector<uint32_t> seenBy(cells, None), walk;
            std::vector<float> reach;
            for (uint32_t i = 0; i < drafts.size(); ++i) {
                Volcano v = drafts[i].v;
                v.seed = Hash(i * 0x632BE5ABu + body.seed);
                const V3 at = Unwarp(gradients, drafts[i].at, body.seed * 4096u, radius); // ReliefSeed(0)
                v.at[0] = at.x, v.at[1] = at.y, v.at[2] = at.z;
                map.volcanoes.push_back(v);
                const int steps = std::min(int(0.6f * v.radius / texelKm) + 1, 6);
                Around(cube, drafts[i].cell, steps, seenBy, i, walk, [&](uint32_t c) {
                    field[RockClass][c] = float(Volcanic + 8 * continental[c]), field[Erodibility][c] = kErodibility[Volcanic];
                });
                reach.push_back(Chord((std::max(1.7f * v.radius, 80.0f) + 5.0f) / radius));
            }
            // The index: each of its cells lists the volcanoes within their reach of it, the larger of 1.7 times their
            // radius and 80 km (VOLCANO_REACH in Volcanoes.hlsli), plus a margin for the rounding.
            const uint32_t G = VolcanoGrid;
            const Cube grid(G);
            std::vector<std::vector<uint32_t>> lists(grid.cells);
            ForCells(grid.cells, [&](uint32_t g) {
                const uint32_t f = g / (G * G), j = g / G % G, i = g % G;
                float circum = 0.0f;
                for (int corner = 0; corner < 4; ++corner) {
                    const float s = grid.Coordinate(i) + ((corner & 1) ? 1.0f : -1.0f) / G, t = grid.Coordinate(j) + ((corner & 2) ? 1.0f : -1.0f) / G;
                    circum = std::max(circum, Length(Normalize(Cube::Direction(f, s, t)) - grid.p[g]));
                }
                for (uint32_t v = 0; v < map.volcanoes.size(); ++v) {
                    const Volcano& w = map.volcanoes[v];
                    const V3 at = { w.at[0], w.at[1], w.at[2] };
                    if (Length(at - grid.p[g]) < circum + reach[v]) lists[g].push_back(v);
                }
            });
            map.volcanoIndex.resize(grid.cells + 1);
            uint32_t at = grid.cells + 1;
            for (uint32_t g = 0; g < grid.cells; ++g) map.volcanoIndex[g] = at, at += uint32_t(lists[g].size());
            map.volcanoIndex[grid.cells] = at;
            for (const auto& list : lists) map.volcanoIndex.insert(map.volcanoIndex.end(), list.begin(), list.end());
        }
        map.volcanoMs = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - volcanism).count();

        // Smoothed over about two texels: where a profile ends at a boundary's end or where the nearest boundary changes.
        // The chains' direction: the distance to the plate's boundary, smoothed over about 40 km so that it never creases
        // where two boundaries are as near; the noise stretches along its level lines (Relief.hlsli).
        cube.Blur({ &field[Elevation], &field[Relief], &field[Youth], &field[Strata], &field[Trench], &field[Divergent],
                    &field[Shear], &field[UpliftMm], &field[Axis], &field[Erodibility], &field[Orientation] },
                  { 4, 4, 4, 4, 4, 4, 4, 4, 2, 2, 8 });

        // The texture arrays (Tectonics.hlsli): each face padded with what lies beyond its edges, bilinear from the next
        // face, the classes from the nearest texel; slice 3 again at a quarter of the resolution, for the views.
        const int slices[Slices][4] = { { Elevation, Relief, Youth, Strata }, { Axis, Trench, Divergent, Shear },
                                        { Side, Orientation, RockClass, PlateClass }, { AgeMa, MarginKm, UpliftMm, SutureKm },
                                        { Erodibility, Empty, Empty, Empty } };
        const uint32_t w = n + 2 * Pad, nv = n / ViewScale, wv = nv + 2 * ViewPad;
        map.texels.resize(size_t(6) * Slices * w * w * 4);
        map.views.resize(size_t(6) * wv * wv * 4);
        std::vector<__m128> packed(cells);
        for (uint32_t s = 0; s < Slices; ++s) {
            ForCells(cells, [&](uint32_t c) {
                packed[c] = _mm_setr_ps(field[slices[s][0]][c], field[slices[s][1]][c], field[slices[s][2]][c], field[slices[s][3]][c]);
            });
            ForCells(6 * w, [&](uint32_t row) {
                const uint32_t face = row / w, j = row % w;
                uint16_t* out = map.texels.data() + ((size_t(face) * Slices + s) * w + j) * w * 4;
                for (uint32_t i = 0; i < w; ++i, out += 4) {
                    const int ii = int(i) - int(Pad), jj = int(j) - int(Pad);
                    __m128 v;
                    if (ii >= 0 && jj >= 0 && ii < int(n) && jj < int(n)) v = packed[(face * n + jj) * n + ii];
                    else {
                        const V3 d = Cube::Direction(face, cube.Coordinate(ii), cube.Coordinate(jj));
                        v = cube.Bilinear(packed, d);
                        if (s == 2) {
                            const __m128 nearest = packed[cube.CellOf(d)];
                            v = _mm_shuffle_ps(v, nearest, _MM_SHUFFLE(3, 2, 1, 0));
                        }
                    }
                    _mm_storel_epi64((__m128i*)out, _mm_cvtps_ph(v, 0));
                }
            });
            if (s == 3)
                ForCells(6 * wv, [&](uint32_t row) {
                    const uint32_t face = row / wv, j = row % wv;
                    uint16_t* out = map.views.data() + (size_t(face) * wv + j) * wv * 4;
                    for (uint32_t i = 0; i < wv; ++i, out += 4) {
                        auto at = [&](uint32_t k) { return (int(k) - int(ViewPad) + 0.5f) * 2.0f / nv - 1.0f; };
                        _mm_storel_epi64((__m128i*)out, _mm_cvtps_ph(cube.Bilinear(packed, Cube::Direction(face, at(i), at(j))), 0));
                    }
                });
        }
        map.ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
        return map;
    }

    bool Save(const Map& map, uint32_t seed, const std::wstring& path)
    {
        FILE* f = nullptr;
        if (_wfopen_s(&f, (path + L".tmp").c_str(), L"wb") != 0 || !f) return false;
        const char magic[8] = { 'E', 'X', 'O', 'T', 'E', 'C', 'T', '2' };
        const uint32_t header[5] = { seed, map.size, Pad, Slices, 6 };
        bool ok = fwrite(magic, 1, 8, f) == 8 && fwrite(header, 4, 5, f) == 5
               && fwrite(map.texels.data(), 2, map.texels.size(), f) == map.texels.size();
        ok = fclose(f) == 0 && ok;
        if (!ok) return false;
        _wremove(path.c_str());
        return _wrename((path + L".tmp").c_str(), path.c_str()) == 0;
    }

    bool SaveVolcanoes(const Map& map, uint32_t seed, const std::wstring& path)
    {
        FILE* f = nullptr;
        if (_wfopen_s(&f, (path + L".tmp").c_str(), L"wb") != 0 || !f) return false;
        const char magic[8] = { 'E', 'X', 'O', 'V', 'O', 'L', 'C', '1' };
        const uint32_t header[5] = { seed, uint32_t(map.volcanoes.size()), VolcanoGrid, uint32_t(map.volcanoIndex.size()), map.hotspots };
        bool ok = fwrite(magic, 1, 8, f) == 8 && fwrite(header, 4, 5, f) == 5
               && fwrite(map.volcanoes.data(), sizeof(Volcano), map.volcanoes.size(), f) == map.volcanoes.size()
               && fwrite(map.volcanoIndex.data(), 4, map.volcanoIndex.size(), f) == map.volcanoIndex.size();
        ok = fclose(f) == 0 && ok;
        if (!ok) return false;
        _wremove(path.c_str());
        return _wrename((path + L".tmp").c_str(), path.c_str()) == 0;
    }
}
