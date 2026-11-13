// D3DApp.cpp - the application: the window, the device and its resources, the frame (Draw), the free camera and the
// input. The benches, the test views and the ship are in D3DAppBench.cpp, D3DAppTests.cpp and D3DAppShip.cpp.
#include "D3DApp.h"
#include "ObserverExposure.hlsli"
#include "CelestialSystem.h"
#include <d3d12sdklayers.h>
#include "Ocean.h"
#include "GpuHelpers.h"
#include "d3dx12.h"
#include "PlanetMap.h"
#include "Scans.h"
#include "Tectonics.h"
#include "Climate.h"
#include "Erosion.h"
#include <windowsx.h>
#include <future>
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
#include <map>
#pragma comment(lib, "d3dcompiler.lib")

namespace
{
    // Highest terrain, about the relief's highest summits (RELIEF_HIGHEST, PlanetSettings.hlsli): mountains this high rise
    // above the horizon.
    const double kMaxElevation = 8192.0;
    // One face plane covers at most this angle around the nadir.
    const double kMaxCoverage = XM_PI / 3.0;
    // Unit of the fine detail's anchor (m), a power of two: the anchor stays within 55 m of the camera.
    const double kDetailUnit = 64.0;
    // Background: alpha 0 tells the tone map pass to draw the sky there.
    const float kClearColor[4] = { 0.0f, 0.0f, 0.0f, 0.0f };

    // The shader visible descriptor heap.
    // Materials: their two arrays (SRVs), then for each mip the two arrays' UAVs.
    // The terrain's sunlit part (t17) and the clouds' four textures (t24..t27), then the planetary map, ocean and foliage
    // resources.
    enum Descriptor : UINT { HdrSrv = 0, LutSrv = 1, LutUav = 4, CompositeSrv = 7, HistorySrv = 8, MaterialSrv = 10,
                             MaterialUav = 12, SunSrv = 12 + 2 * 11, CloudSrv = SunSrv + 1,
                             PlanetMapSrv = CloudSrv + 4, OceanSrv = PlanetMapSrv + 1,
                             PlanetImpostorSrv = OceanSrv + Ocean::DescriptorCount,
                             FoliageHiZSrv = PlanetImpostorSrv + PlanetFoliage::DescriptorCount,
                             CloudTemporalSrv = FoliageHiZSrv + 32, // per history read: fresh, history's, drifted's
                             ShipSrv = CloudTemporalSrv + 14, TectonicSrv = ShipSrv + Ship::DescriptorCount, // its views, the climate,
                             ContactSrv = TectonicSrv + 7, ContactUav = ContactSrv + 1, // after the volcanoes, their index, erosion and its courses
                             ContactHdrUav = ContactSrv + 2, ContactSunUav = ContactSrv + 3,
                             SkyTransportSrv = ContactSrv + 4, CelestialSrv = SkyTransportSrv + 1,
                             AirlessMaterialSrv = CelestialSrv + 1,
                             CitySrv = AirlessMaterialSrv + Celestial::AirlessAtlasSlots,
                             GlareSrv = CitySrv + City::DescriptorCount, // the summed glare, then an empty view without it
                             AdaptationSrv = GlareSrv + 2, // the local adaptation's pyramid (Adaptation.h)
                             DescriptorCount = AdaptationSrv + 1 };
    // Render target views: the back buffers, then the HDR image, the composite image, the two histories and the terrain's
    // sunlit part, for the clouds' shade.
    // Then the cloud temporal pass's fresh light and data, its two histories, light, data and offset each, and the light
    // and data of its drifted pixels.
    enum RenderTarget : UINT { HdrRtv = 2, CompositeRtv = 3, HistoryRtv = 4, SunRtv = 6, CloudFreshRtv = 7,
                               CloudHistoryRtv = 9, CloudHalfRtv = 15, SkyTransportRtv = 17, CelestialRtv = 18, RtvCount = 19 };
    // Must match Atmosphere.hlsli: each table's size, and its slices for the haze's ground, GROUND_SLICES.
    const UINT kLutSizes[3][2] = { { 256, 64 }, { 32, 32 }, { 64, 16 } }, kLutGroundSlices = 25;

    // Index of the vertex number b of the face's border, going round like the rings: bottom, right, top, left.
    UINT FaceBorderVertex(UINT b, UINT n)
    {
        const UINT side = b / n, t = b % n;
        const UINT i = side == 0 ? t : side == 1 ? n : side == 2 ? n - t : 0;
        const UINT j = side == 0 ? 0 : side == 1 ? t : side == 2 ? n : n - t;
        return j * (n + 1) + i;
    }

    // The clouds' noise volumes (assets/clouds): RGBA8, x fastest, their mips one after the other; repacked to D3D12's
    // footprints.
    void UploadCloudVolume(ID3D12Device* device, ID3D12GraphicsCommandList* list, const std::wstring& path,
        UINT side, UINT mipLevels, ID3D12Resource* texture, std::vector<ComPtr<ID3D12Resource>>& uploads,
        bool noiseStatistics = false, bool profileWindows = false)
    {
        size_t expectedBytes = 0;
        for (UINT level = 0, width = side; level < mipLevels; ++level, width = std::max(width >> 1, 1u))
            expectedBytes += size_t(width) * width * width * 4;
        HANDLE file = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (file == INVALID_HANDLE_VALUE) throw std::runtime_error("A cloud texture is missing from assets/clouds.");
        LARGE_INTEGER fileSize = {};
        if (!GetFileSizeEx(file, &fileSize) || fileSize.QuadPart != static_cast<LONGLONG>(expectedBytes)) {
            CloseHandle(file); throw std::runtime_error("A cloud texture of assets/clouds has an unexpected byte count.");
        }
        std::vector<BYTE> source(expectedBytes);
        size_t readOffset = 0;
        while (readOffset < source.size()) {
            const DWORD request = static_cast<DWORD>(std::min(source.size() - readOffset, size_t(MAXDWORD)));
            DWORD received = 0;
            if (!ReadFile(file, source.data() + readOffset, request, &received, nullptr) || received == 0) {
                CloseHandle(file); throw std::runtime_error("A cloud texture of assets/clouds could not be read.");
            }
            readOffset += received;
        }
        CloseHandle(file);
        if (profileWindows) {
            // Mip 0's slice z holds the profiles' mean over a window of z texels of height, centred on each texel: a
            // light sample standing for a long interval reads its whole height span, not its middle (Clouds.hlsli,
            // CloudLowDensity). On disk the profiles do not vary along z; only mip 0 is read, the others stay as loaded.
            const std::vector<BYTE> slice(source.begin(), source.begin() + size_t(side) * side * 4);
            std::vector<double> v(side), sum(side);
            for (UINT x = 0; x < side; ++x) for (UINT c = 0; c < 2; ++c) {
                for (UINT y = 0; y < side; ++y) v[y] = slice[4 * (size_t(y) * side + x) + c];
                sum[0] = 0.0;
                for (UINT y = 1; y < side; ++y) sum[y] = sum[y - 1] + 0.5 * (v[y - 1] + v[y]);
                // The integral of the piecewise-linear profile from texel 0 to t; its end values continue it.
                const double last = double(side - 1);
                auto integral = [&](double t) {
                    if (t <= 0.0) return v[0] * t;
                    if (t >= last) return sum[side - 1] + v[side - 1] * (t - last);
                    const UINT j = UINT(t); const double f = t - j;
                    return sum[j] + v[j] * f + 0.5 * (v[j + 1] - v[j]) * f * f;
                };
                for (UINT z = 0; z < side; ++z) for (UINT y = 0; y < side; ++y) {
                    const double mean = z == 0 ? v[y] : (integral(y + 0.5 * z) - integral(y - 0.5 * z)) / z;
                    source[4 * ((size_t(z) * side + y) * side + x) + c]
                        = static_cast<BYTE>(std::lround(std::min(std::max(mean, 0.0), 255.0)));
                }
            }
        }
        if (noiseStatistics) {
            // B: the noise's standard deviation under the texel, from mip 0's R, computed at upload.
            // Wrapping blocks of 2^L texels a side; the file on disk and its manifest are unchanged.
            size_t mipOffset = 0;
            for (UINT level = 0, width = side; level < mipLevels; ++level, width = std::max(width >> 1, 1u)) {
                const UINT block = 1u << level;
                const double count = double(block) * block * block;
                for (UINT z = 0; z < width; ++z) for (UINT y = 0; y < width; ++y) for (UINT x = 0; x < width; ++x) {
                    double sum = 0.0, squareSum = 0.0;
                    if (level > 0) {
                        for (UINT dz = 0; dz < block; ++dz) for (UINT dy = 0; dy < block; ++dy) for (UINT dx = 0; dx < block; ++dx) {
                            const size_t index = (size_t((z * block + dz) % side) * side
                                + (y * block + dy) % side) * side + (x * block + dx) % side;
                            const double value = source[4 * index];
                            sum += value;
                            squareSum += value * value;
                        }
                    }
                    const double mean = sum / count;
                    const double sigma = std::sqrt(std::max(squareSum / count - mean * mean, 0.0)) / 255.0;
                    source[mipOffset + 4 * ((size_t(z) * width + y) * width + x) + 2]
                        = static_cast<BYTE>(std::lround(255.0 * std::min(2.0 * sigma, 1.0)));
                }
                mipOffset += size_t(width) * width * width * 4;
            }
        }
        std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(mipLevels);
        const D3D12_RESOURCE_DESC textureDesc = texture->GetDesc();
        UINT64 uploadBytes = 0;
        device->GetCopyableFootprints(&textureDesc, 0, mipLevels, 0, footprints.data(), nullptr, nullptr, &uploadBytes);
        uploads.push_back(CreateBuffer(device, uploadBytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ));
        BYTE* mapped = nullptr; CD3DX12_RANGE noRead(0, 0);
        Check(uploads.back()->Map(0, &noRead, reinterpret_cast<void**>(&mapped)), "Cloud texture upload map failed.");
        size_t sourceOffset = 0;
        for (UINT level = 0, width = side; level < mipLevels; ++level, width = std::max(width >> 1, 1u)) {
            const auto& fp = footprints[level]; const size_t rowBytes = size_t(width) * 4;
            const size_t slicePitch = size_t(fp.Footprint.RowPitch) * fp.Footprint.Height;
            for (UINT z = 0; z < width; ++z) for (UINT y = 0; y < width; ++y)
                memcpy(mapped + fp.Offset + size_t(z) * slicePitch + size_t(y) * fp.Footprint.RowPitch,
                    source.data() + sourceOffset + (size_t(z) * width + y) * rowBytes, rowBytes);
            sourceOffset += size_t(width) * width * width * 4;
            const CD3DX12_TEXTURE_COPY_LOCATION dst(texture, level), src(uploads.back().Get(), fp);
            list->CopyTextureRegion(&dst, 0, 0, 0, &src, nullptr);
        }
        uploads.back()->Unmap(0, nullptr);
    }

    // The clouds' weather map over the planet (Climate::Weather): RGBA8, x fastest, its mips one after the other.
    void UploadCloudMap(ID3D12Device* device, ID3D12GraphicsCommandList* list, const std::vector<uint8_t>& source,
        UINT width, UINT height, UINT mipLevels, ID3D12Resource* texture, std::vector<ComPtr<ID3D12Resource>>& uploads)
    {
        const D3D12_RESOURCE_DESC desc = texture->GetDesc();
        std::vector<D3D12_PLACED_SUBRESOURCE_FOOTPRINT> footprints(mipLevels);
        UINT64 uploadBytes = 0;
        device->GetCopyableFootprints(&desc, 0, mipLevels, 0, footprints.data(), nullptr, nullptr, &uploadBytes);
        uploads.push_back(CreateBuffer(device, uploadBytes, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ));
        BYTE* mapped = nullptr; CD3DX12_RANGE noRead(0, 0);
        Check(uploads.back()->Map(0, &noRead, reinterpret_cast<void**>(&mapped)), "Cloud weather upload map failed.");
        size_t sourceOffset = 0;
        for (UINT level = 0, w = width, h = height; level < mipLevels;
            ++level, w = std::max(w >> 1, 1u), h = std::max(h >> 1, 1u)) {
            const auto& fp = footprints[level]; const size_t rowBytes = size_t(w) * 4;
            for (UINT y = 0; y < h; ++y)
                memcpy(mapped + fp.Offset + size_t(y) * fp.Footprint.RowPitch, source.data() + sourceOffset + size_t(y) * rowBytes, rowBytes);
            sourceOffset += size_t(w) * h * 4;
            const CD3DX12_TEXTURE_COPY_LOCATION dst(texture, level), src(uploads.back().Get(), fp);
            list->CopyTextureRegion(&dst, 0, 0, 0, &src, nullptr);
        }
        uploads.back()->Unmap(0, nullptr);
    }
    // The objects' placement constants (ObjectPlacement.hlsl, cbuffer Placement): its doubles read as pairs of uints.
    struct PlacementConstants { double cam[3], foot[3]; float pixelAngle; UINT flags, planeCount, sliceBase; INT32 planes[3][4]; };
    static_assert(sizeof(PlacementConstants) == 28 * 4, "ObjectPlacement.hlsl's cbuffer Placement");

    std::wstring FormatDistance(double meters)
    {
        wchar_t text[32];
        if (std::fabs(meters) >= 1000.0) swprintf_s(text, L"%.1f km", meters / 1000.0);
        else swprintf_s(text, L"%.1f m", meters);
        return text;
    }
}

constexpr double D3DApp::PlanetRadius; // C++14: std::min binds it by reference

// The rock shapes (docs/spec-objets-proximite.md), RockVariants of them: an icosphere of RockVertices vertices, its
// radius cut by a few random planes, a block of flat faces whose edges their smooth minimum rounds, roughened by a few
// waves, squashed; its foot at y = 0, its width 1. One index list for all.
void D3DApp::BuildRocks(std::vector<ShapeVertex>& vertices, std::vector<UINT>& indices) {
    const double t = (1.0 + std::sqrt(5.0)) / 2.0;
    std::vector<Vec3d> dirs = { { -1, t, 0 }, { 1, t, 0 }, { -1, -t, 0 }, { 1, -t, 0 }, { 0, -1, t }, { 0, 1, t },
                                { 0, -1, -t }, { 0, 1, -t }, { t, 0, -1 }, { t, 0, 1 }, { -t, 0, -1 }, { -t, 0, 1 } };
    indices = { 0, 11, 5, 0, 5, 1, 0, 1, 7, 0, 7, 10, 0, 10, 11, 1, 5, 9, 5, 11, 4, 11, 10, 2, 10, 7, 6, 7, 1, 8,
                3, 9, 4, 3, 4, 2, 3, 2, 6, 3, 6, 8, 3, 8, 9, 4, 9, 5, 2, 4, 11, 6, 2, 10, 8, 6, 7, 9, 8, 1 };
    for (Vec3d& d : dirs) d = Normalize(d);
    for (int level = 0; level < 3; ++level) {
        std::map<std::pair<UINT, UINT>, UINT> middles;
        auto middle = [&](UINT a, UINT b) {
            const auto key = std::make_pair(std::min(a, b), std::max(a, b));
            const auto found = middles.find(key);
            if (found != middles.end()) return found->second;
            dirs.push_back(Normalize(dirs[a] + dirs[b]));
            return middles[key] = UINT(dirs.size() - 1);
        };
        std::vector<UINT> finer;
        for (size_t i = 0; i < indices.size(); i += 3) {
            const UINT a = indices[i], b = indices[i + 1], c = indices[i + 2];
            const UINT ab = middle(a, b), bc = middle(b, c), ca = middle(c, a);
            finer.insert(finer.end(), { a, ab, ca, b, bc, ab, c, ca, bc, ab, bc, ca });
        }
        indices.swap(finer);
    }
    if (dirs.size() != RockVertices) throw std::runtime_error("Rock shape: unexpected vertex count.");

    UINT state = 0x2545F491u;
    auto random = [&state]() { state = state * 1664525u + 1013904223u; return double(state >> 8) / 16777216.0; };
    auto randomDirection = [&random]() {
        for (;;) {
            const Vec3d v = { 2.0 * random() - 1.0, 2.0 * random() - 1.0, 2.0 * random() - 1.0 };
            if (Dot(v, v) > 0.01 && Dot(v, v) <= 1.0) return Normalize(v);
        }
    };
    auto smoothMin = [](double a, double b, double k) { // polynomial, Quilez
        const double h = std::max(k - std::fabs(a - b), 0.0) / k;
        return std::min(a, b) - h * h * k * 0.25;
    };
    for (UINT variant = 0; variant < RockVariants; ++variant) {
        struct Plane { Vec3d normal; double offset; };
        std::vector<Plane> planes(8 + variant % 5);
        for (Plane& p : planes) p = { randomDirection(), 0.55 + 0.3 * random() };
        struct Wave { Vec3d k; double phase, amplitude; };
        Wave waves[6];
        for (int w = 0; w < 6; ++w)
            waves[w] = { randomDirection() * (w < 3 ? 2.5 + 2.0 * random() : 6.0 + 4.0 * random()), 6.2831853 * random(),
                         w < 3 ? 0.025 : 0.01 };
        const Vec3d squash = { 1.0, 0.5 + 0.25 * random(), 0.75 + 0.25 * random() };
        std::vector<Vec3d> pos(dirs.size());
        Vec3d low = { 1e9, 1e9, 1e9 }, high = { -1e9, -1e9, -1e9 };
        for (size_t i = 0; i < dirs.size(); ++i) {
            const Vec3d& n = dirs[i];
            double r = 1.2;
            for (const Plane& p : planes) {
                const double c = Dot(n, p.normal);
                if (c > 1e-3) r = smoothMin(r, p.offset / c, 0.05);
            }
            for (const Wave& w : waves) r *= 1.0 + w.amplitude * std::sin(Dot(w.k, n) + w.phase);
            pos[i] = { n.x * r * squash.x, n.y * r * squash.y, n.z * r * squash.z };
            low = { std::min(low.x, pos[i].x), std::min(low.y, pos[i].y), std::min(low.z, pos[i].z) };
            high = { std::max(high.x, pos[i].x), std::max(high.y, pos[i].y), std::max(high.z, pos[i].z) };
        }
        // Its foot at the origin, its width 1.
        const double width = std::max(high.x - low.x, high.z - low.z);
        const Vec3d centre = { 0.5 * (low.x + high.x), low.y, 0.5 * (low.z + high.z) };
        std::vector<Vec3d> normals(dirs.size(), Vec3d{ 0.0, 0.0, 0.0 });
        for (size_t i = 0; i < indices.size(); i += 3) {
            const UINT a = indices[i], b = indices[i + 1], c = indices[i + 2];
            const Vec3d n = Cross(pos[b] - pos[a], pos[c] - pos[a]); // area-weighted
            normals[a] = normals[a] + n; normals[b] = normals[b] + n; normals[c] = normals[c] + n;
        }
        for (size_t i = 0; i < dirs.size(); ++i) {
            Vec3d n = Normalize(normals[i]);
            if (Dot(n, dirs[i]) < 0.0) n = n * -1.0; // outwards, whatever the winding
            const Vec3d p = (pos[i] - centre) * (1.0 / width);
            vertices.push_back({ XMFLOAT3(float(p.x), float(p.y), float(p.z)), float((high.y - low.y) / width),
                                 XMFLOAT3(float(n.x), float(n.y), float(n.z)), 1.0f });
        }
    }
}

// The grass tufts (docs/spec-objets-proximite.md), TuftVariants of them: TuftBlades blades from a disc of 0.2 at the
// foot, 0.4 to 0.9 long, leaning out 0 to 30 degrees and bending as they rise, tapered to a point, a little darker or
// lighter each (shade); three segments, seven vertices each. Its foot at y = 0, its dense part about 1 wide. One index
// list for all.
void D3DApp::BuildTufts(std::vector<ShapeVertex>& vertices, std::vector<UINT>& indices) {
    for (UINT b = 0; b < TuftBlades; ++b) {
        const UINT v = 7 * b;
        indices.insert(indices.end(), { v, v + 2, v + 1, v + 1, v + 2, v + 3, v + 2, v + 4, v + 3, v + 3, v + 4, v + 5,
                                        v + 4, v + 6, v + 5 });
    }
    UINT state = 0x68E31DA4u;
    auto random = [&state]() { state = state * 1664525u + 1013904223u; return double(state >> 8) / 16777216.0; };
    for (UINT variant = 0; variant < TuftVariants; ++variant) {
        const size_t first = vertices.size();
        double top = 0.0;
        for (UINT b = 0; b < TuftBlades; ++b) {
            const double around = 6.2831853 * random(), r = 0.2 * std::sqrt(random());
            const double azimuth = around + 0.8 * (random() - 0.5), lean = 0.52 * random();
            const double length = 0.4 + 0.5 * random(), width = 0.04 + 0.03 * random(), shade = 0.8 + 0.4 * random();
            const Vec3d base = { r * std::cos(around), 0.0, r * std::sin(around) };
            const Vec3d out = { std::cos(azimuth), 0.0, std::sin(azimuth) }, side = { -out.z, 0.0, out.x }, up = { 0.0, 1.0, 0.0 };
            for (int s = 0; s <= 3; ++s) {
                const double u = s / 3.0;
                const Vec3d p = base + out * (length * (u * std::sin(lean) + 0.3 * u * u)) + up * (length * (u * std::cos(lean) - 0.25 * u * u));
                const Vec3d along = out * (std::sin(lean) + 0.6 * u) + up * (std::cos(lean) - 0.5 * u);
                const Vec3d n = Normalize(Cross(along, side)); // facing out and up
                const double w = 0.5 * width * (1.0 - u);
                for (int e = s < 3 ? -1 : 0; e <= (s < 3 ? 1 : 0); e += 2) {
                    const Vec3d q = p + side * (w * e);
                    vertices.push_back({ XMFLOAT3(float(q.x), float(q.y), float(q.z)), 0.0f, XMFLOAT3(float(n.x), float(n.y), float(n.z)),
                                         float(shade) });
                }
                top = std::max(top, p.y);
            }
        }
        for (size_t i = first; i < vertices.size(); ++i) vertices[i].height = float(top);
    }
    if (vertices.size() != TuftVariants * TuftVertices) throw std::runtime_error("Tuft shape: unexpected vertex count.");
}

D3DApp::D3DApp(HINSTANCE hInstance, double startAltitude, double latitude, double longitude, double pitchDown, double heading)
    : mhAppInst(hInstance), mSettings(ReadSettings())
{
    QueryPerformanceFrequency(&mFrequency);
    mFullscreen = mSettings.fullscreen;
    mClientWidth = mSettings.width;
    mClientHeight = mSettings.height;
    mWireframe = mSettings.wireframe;
    mFaceted = mSettings.faceted;
    mTaa = mSettings.taa; // preference; TemporalAA bypasses diagnostics without resetting key T
    mDiagnosticView = mSettings.view;
    mCloudsOn = mSettings.clouds;
    mCoordinates = mSettings.coordinates;
    mWeatherTime = mSettings.weatherTime;
    mLabel = mSettings.label;
    mErosionMode = mSettings.erosionMode;
    ReadTests();
    ReadBatch(); // before MYPLANETENGINE_FACE_FACTOR: a job that gives no face factor takes the default one
    ReadCine();
    mFaceFactor = mSettings.faceFactor;
    mSunDir = mStartSunDir = LatLonToDir(mSettings.sunLatitude, mSettings.sunLongitude);
    mSeaTime = mSettings.seaTime;
    mSeaTimeRate = mSettings.seaTimeRate;
    mOceanSpeed = mSettings.oceanSpeed;
    mOceanDirection = mSettings.oceanDirection;
    mOceanSwell = mSettings.oceanSwell;
    PlaceCamera(latitude, longitude, pitchDown, heading, startAltitude);

    // The first view: the cockpit when flown, the free camera for the benches, unless MYPLANETENGINE_VAISSEAU says.
    mView = mSettings.Automated() ? View::Free : mShip.Profile().cockpit ? View::Cockpit : View::Chase;
    if (mSettings.shipSet) {
        const wchar_t* choice = mSettings.ship.c_str();
        mStartWalking = !wcscmp(choice, L"marche");
        if (!wcscmp(choice, L"orbite")) mCameraMode = CameraMode::Horizon;
        if (!wcscmp(choice, L"altitude-fixe")) mCameraMode = CameraMode::FixedAltitude;
        mView = !wcscmp(choice, L"poursuite") ? View::Chase : (mCameraMode != CameraMode::Free || !wcscmp(choice, L"libre")) ? View::Free
              : !wcscmp(choice, L"sans") ? View::Bare : View::Cockpit;
    }
    if (mView == View::Cockpit && !mShip.Profile().cockpit) mView = View::Chase;
    PlaceShipAtCamera();
}

// The camera above (latitude, longitude) at `altitude` m above the sea, looking heading degrees east of north and
// pitchDown degrees below the horizon.
void D3DApp::PlaceCamera(double latitude, double longitude, double pitchDown, double heading, double altitude) {
    ResetFlightContact();
    mCameraBody = -1;
    const Vec3d up = LatLonToDir(latitude, longitude);
    const double lat=latitude*XM_PI/180.0,lon=longitude*XM_PI/180.0,cap=heading*XM_PI/180.0;
    const Vec3d north={-std::sin(lat)*std::cos(lon),std::cos(lat),-std::sin(lat)*std::sin(lon)};
    const Vec3d east = { -std::sin(lon), 0.0, std::cos(lon) }; // towards growing longitudes
    const double pitch = pitchDown * XM_PI / 180.0;
    mCamPos = up * (PlanetRadius + altitude);
    FlightFrame::FromHeading(up,north*std::cos(cap)+east*std::sin(cap),pitch,mCamForward,mCamUp);
    mWaveReset = true;
    mWorldPending = mWorldValid = mWalkProbePending = mWalkPatchValid = false;
    mAudio.ResetWorld();
}

// The sea's waves (Sea.hlsli, docs/recherche-mer.md). Their plane rides tangent at the camera, carried along the shortest
// way as it flies, without turning; its origin keeps the distance flown, in double. Each wave's phase at the origin then
// runs with the time and with that distance: a point of the sea keeps its waves wherever the camera goes, to a few
// millimetres per kilometre flown at 50 km away. A jump of the camera starts the plane afresh, east and north.
void D3DApp::UpdateOceanPlane(double dt, const Vec3d& faceX, const Vec3d& faceY, const Vec3d& faceZ) {
    mSeaTime += dt * mSeaTimeRate;
    const Vec3d up = Normalize(mCamPos);
    if (mWaveReset) {
        mWaveX = Cross(up, kNorth);
        mWaveX = Normalize(Length(mWaveX) > 1e-6 ? mWaveX : Cross(up, Vec3d{ 1.0, 0.0, 0.0 }));
        mWaveY = Cross(mWaveX, up);
        // The origin from the place, east and north, so that two places do not start with the same waves.
        mWaveOrigin[0] = PlanetRadius * std::atan2(up.z, up.x) * std::sqrt(1.0 - up.y * up.y);
        mWaveOrigin[1] = PlanetRadius * std::asin(up.y);
        mWaveReset = false;
    }
    else {
        const Vec3d previous = Normalize(mWaveCamera), axis = Cross(previous, up);
        const double s = Length(axis);
        if (s > 1e-15) {
            const double angle = std::asin(std::min(s, 1.0));
            mWaveX = Rotate(mWaveX, axis * (1.0 / s), angle);
            mWaveY = Rotate(mWaveY, axis * (1.0 / s), angle);
        }
        mWaveX = Normalize(mWaveX - up * Dot(mWaveX, up)); // against rounding, frame after frame
        mWaveY = Normalize(Cross(mWaveX, up));
        const Vec3d travel = (up - previous) * PlanetRadius; // the nadir's: rising does not move the waves
        mWaveOrigin[0] += Dot(travel, mWaveX);
        mWaveOrigin[1] += Dot(travel, mWaveY);
    }
    mWaveCamera = mCamPos;
    auto toLocal = [&](const Vec3d& v) {
        return XMFLOAT4((float)Dot(v, faceX), (float)Dot(v, faceY), (float)Dot(v, faceZ), 0.0f);
    };
    mConstants->waveAxisX = toLocal(mWaveX);
    mConstants->waveAxisY = toLocal(mWaveY);
    mConstants->waveAxisX.w=std::min(128.0f,16.0f+0.05f*mOceanSpeed*mOceanSpeed+3.0f*mOceanSwell);

}

D3DApp::~D3DApp() {
    if (mCommandQueue && mFence && mSwapChain) WaitForPreviousFrame();
    if (mFenceEvent) CloseHandle(mFenceEvent);
}

bool D3DApp::Initialize() {
    if (!InitWindow()) return false;
    if (!InitDirect3D()) return false;
    UpdateCelestialFrame();
    if(mSettings.firstTest && mSettings.firstTest<=mTests.size())GoToTest(mSettings.firstTest-1);
    if (!mSettings.Automated()) mAudioReady = mAudio.Initialize(); // offline films stay silent
    mAudio.SetMix(mSettings.audioMaster,mSettings.audioFootsteps,mSettings.audioAmbience,mSettings.audioShip);
    return true;
}

int D3DApp::Run() {
    MainLoop();
    return 0;
}

void D3DApp::MainLoop() {
    MSG msg = {};
    while (msg.message != WM_QUIT) {
        if (PeekMessage(&msg, nullptr, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
        }
        else {
            Draw();
        }
    }
}

bool D3DApp::InitWindow() {
    WNDCLASS wc = {};
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = mhAppInst;
    wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
    wc.lpszClassName = L"MyD3DWindowClass";
    RegisterClass(&wc);

    // Render dimensions are chosen once. A borderless toggle stretches the same
    // swap chain, without recreating the volume, HiZ or scene resources in flight.
    if (mSettings.Automated()) mFullscreen=false;
    MONITORINFO monitor={sizeof(monitor)};
    GetMonitorInfo(MonitorFromPoint(POINT{0,0},MONITOR_DEFAULTTOPRIMARY),&monitor);
    if (mFullscreen && !mSettings.explicitResolution) {
        mClientWidth=monitor.rcMonitor.right-monitor.rcMonitor.left;
        mClientHeight=monitor.rcMonitor.bottom-monitor.rcMonitor.top;
    }
    const DWORD style = WS_OVERLAPPEDWINDOW & ~(WS_THICKFRAME | WS_MAXIMIZEBOX);
    const LONG windowWidth=std::min<LONG>(mClientWidth,1280);
    const LONG windowHeight=LONG(double(windowWidth)*mClientHeight/mClientWidth);
    RECT r = { 0, 0, mFullscreen ? windowWidth : (LONG)mClientWidth, mFullscreen ? windowHeight : (LONG)mClientHeight };
    AdjustWindowRect(&r, style, FALSE);
    const LONG x=monitor.rcWork.left+std::max<LONG>(0,(monitor.rcWork.right-monitor.rcWork.left-(r.right-r.left))/2);
    const LONG y=monitor.rcWork.top+std::max<LONG>(0,(monitor.rcWork.bottom-monitor.rcWork.top-(r.bottom-r.top))/2);
    mWindowedRect={x,y,x+r.right-r.left,y+r.bottom-r.top};
    const RECT placement=mFullscreen ? monitor.rcMonitor : mWindowedRect;
    mhMainWnd = CreateWindow(wc.lpszClassName, mMainWndCaption.c_str(), mFullscreen ? WS_POPUP : style,
        placement.left,placement.top,placement.right-placement.left,placement.bottom-placement.top,
        nullptr,nullptr,mhAppInst,this);
    if (!mhMainWnd) return false;
    // The benches (capture, tremble) render without showing the window: it never takes the user's focus, and
    // the title goes to a file next to the capture instead.
    if (!mSettings.Automated()) {
        ShowWindow(mhMainWnd, SW_SHOW);
        CreateTestsWindow();
    }

    // The ship's views read the mouse's raw motion: the cursor is hidden and kept in the window while they fly.
    const RAWINPUTDEVICE mouse = { 0x01, 0x02, 0, mhMainWnd };
    RegisterRawInputDevices(&mouse, 1, sizeof(mouse));

    // Bind movement to key positions, so that ZQSD works on AZERTY and WASD on QWERTY.
    const UINT scanCodes[6] = { 0x11, 0x1F, 0x1E, 0x20, 0x10, 0x12 }; // W S A D Q E
    for (int i = 0; i < 6; ++i)
        mMoveKeys[i] = MapVirtualKey(scanCodes[i], MAPVK_VSC_TO_VK);
    return true;
}

void D3DApp::ToggleFullscreen() {
    // Moving the window must not turn the camera if mouse-look was captured.
    mLooking=false; mMouseDx=0; mMouseDy=0;
    if (GetCapture()==mhMainWnd) ReleaseCapture();
    const DWORD windowedStyle=WS_OVERLAPPEDWINDOW & ~(WS_THICKFRAME | WS_MAXIMIZEBOX);
    if (!mFullscreen) {
        GetWindowRect(mhMainWnd,&mWindowedRect);
        MONITORINFO monitor={sizeof(monitor)};
        GetMonitorInfo(MonitorFromWindow(mhMainWnd,MONITOR_DEFAULTTONEAREST),&monitor);
        SetWindowLongPtr(mhMainWnd,GWL_STYLE,WS_POPUP | WS_VISIBLE);
        SetWindowPos(mhMainWnd,HWND_TOP,monitor.rcMonitor.left,monitor.rcMonitor.top,
            monitor.rcMonitor.right-monitor.rcMonitor.left,monitor.rcMonitor.bottom-monitor.rcMonitor.top,SWP_FRAMECHANGED);
        if (mTestsWnd) ShowWindow(mTestsWnd,SW_HIDE);
    } else {
        SetWindowLongPtr(mhMainWnd,GWL_STYLE,windowedStyle | WS_VISIBLE);
        SetWindowPos(mhMainWnd,nullptr,mWindowedRect.left,mWindowedRect.top,
            mWindowedRect.right-mWindowedRect.left,mWindowedRect.bottom-mWindowedRect.top,SWP_NOZORDER | SWP_FRAMECHANGED);
    }
    mFullscreen=!mFullscreen;
    if (!mFullscreen) {
        if (!mTestsWnd) CreateTestsWindow();
        else ShowWindow(mTestsWnd,SW_SHOWNOACTIVATE);
    }
    if (mMouseHeld) { HoldMouse(false); HoldMouse(true); } // the ship's clip follows the window
    mHistoryValid=false;
}

bool D3DApp::InitDirect3D() {
    mGpuBreadcrumbs = GetEnvironmentVariableW(L"MYPLANETENGINE_GPU_BREADCRUMBS", nullptr, 0) != 0;
    if (mGpuBreadcrumbs) {
        ComPtr<ID3D12Debug> debug;
        if(SUCCEEDED(D3D12GetDebugInterface(IID_PPV_ARGS(&debug))))debug->EnableDebugLayer();
        ComPtr<ID3D12DeviceRemovedExtendedDataSettings1> dred;
        if (SUCCEEDED(D3D12GetDebugInterface(IID_PPV_ARGS(&dred)))) {
            dred->SetAutoBreadcrumbsEnablement(D3D12_DRED_ENABLEMENT_FORCED_ON);
            dred->SetBreadcrumbContextEnablement(D3D12_DRED_ENABLEMENT_FORCED_ON);
            dred->SetPageFaultEnablement(D3D12_DRED_ENABLEMENT_FORCED_ON);
        }
    }
#ifdef _DEBUG
    ComPtr<ID3D12Debug> debug;
    if (SUCCEEDED(D3D12GetDebugInterface(IID_PPV_ARGS(&debug)))) debug->EnableDebugLayer();
#endif

    ComPtr<IDXGIFactory6> factory;
    Check(CreateDXGIFactory2(0, IID_PPV_ARGS(&factory)), "DXGI factory creation failed.");

    ComPtr<IDXGIAdapter1> adapter;
    Check(factory->EnumAdapterByGpuPreference(0, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE, IID_PPV_ARGS(&adapter)), "No high-performance DXGI adapter found.");
    Check(D3D12CreateDevice(adapter.Get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&md3dDevice)), "D3D12 device creation failed.");
    DXGI_ADAPTER_DESC1 adapterDesc={};
    if (SUCCEEDED(adapter->GetDesc1(&adapterDesc))) mGpuName=adapterDesc.Description;
    BOOL tearing=FALSE;
    mAllowTearing=SUCCEEDED(factory->CheckFeatureSupport(DXGI_FEATURE_PRESENT_ALLOW_TEARING,&tearing,sizeof(tearing))) && tearing;

    // The terrain noise splits its lattice positions in double precision.
    D3D12_FEATURE_DATA_D3D12_OPTIONS options = {};
    md3dDevice->CheckFeatureSupport(D3D12_FEATURE_D3D12_OPTIONS, &options, sizeof(options));
    if (!options.DoublePrecisionFloatShaderOps)
        throw std::runtime_error("This GPU has no double precision shader support, needed by the terrain noise.");

    D3D12_COMMAND_QUEUE_DESC queueDesc = {};
    queueDesc.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
    Check(md3dDevice->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&mCommandQueue)), "Command queue creation failed.");

    DXGI_SWAP_CHAIN_DESC1 swapChainDesc = {};
    swapChainDesc.BufferCount = FrameCount;
    swapChainDesc.Width = mClientWidth;
    swapChainDesc.Height = mClientHeight;
    swapChainDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    swapChainDesc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    swapChainDesc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD;
    swapChainDesc.SampleDesc.Count = 1;
    swapChainDesc.Scaling = DXGI_SCALING_STRETCH;
    swapChainDesc.Flags = mAllowTearing ? DXGI_SWAP_CHAIN_FLAG_ALLOW_TEARING : 0;

    ComPtr<IDXGISwapChain1> swapChain;
    Check(factory->CreateSwapChainForHwnd(mCommandQueue.Get(), mhMainWnd, &swapChainDesc, nullptr, nullptr, &swapChain),
        "Swap chain creation failed.");
    swapChain.As(&mSwapChain);
    Check(factory->MakeWindowAssociation(mhMainWnd,DXGI_MWA_NO_ALT_ENTER), "DXGI window association failed.");
    mFrameIndex = mSwapChain->GetCurrentBackBufferIndex();

    D3D12_DESCRIPTOR_HEAP_DESC rtvHeapDesc = {};
    rtvHeapDesc.NumDescriptors = RtvCount;
    rtvHeapDesc.Type = D3D12_DESCRIPTOR_HEAP_TYPE_RTV;
    Check(md3dDevice->CreateDescriptorHeap(&rtvHeapDesc, IID_PPV_ARGS(&mRtvHeap)), "RTV heap creation failed.");
    mRtvDescriptorSize = md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV);

    // Back buffers through sRGB views: the tone map writes linear light, the hardware encodes it.
    D3D12_RENDER_TARGET_VIEW_DESC srgbView = {};
    srgbView.Format = DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
    srgbView.ViewDimension = D3D12_RTV_DIMENSION_TEXTURE2D;
    CD3DX12_CPU_DESCRIPTOR_HANDLE rtvHandle(mRtvHeap->GetCPUDescriptorHandleForHeapStart());
    for (UINT i = 0; i < FrameCount; i++) {
        mSwapChain->GetBuffer(i, IID_PPV_ARGS(&mRenderTargets[i]));
        md3dDevice->CreateRenderTargetView(mRenderTargets[i].Get(), &srgbView, rtvHandle);
        rtvHandle.Offset(1, mRtvDescriptorSize);
    }

    // The HDR image: render target for the scene, then shader resource for the tone map.
    CD3DX12_HEAP_PROPERTIES hdrHeapProps(D3D12_HEAP_TYPE_DEFAULT);
    CD3DX12_RESOURCE_DESC hdrDesc = CD3DX12_RESOURCE_DESC::Tex2D(HdrFormat, mClientWidth, mClientHeight, 1, 1, 1, 0,
        D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET | D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    D3D12_CLEAR_VALUE hdrClear = {};
    hdrClear.Format = HdrFormat;
    memcpy(hdrClear.Color, kClearColor, sizeof(kClearColor));
    Check(md3dDevice->CreateCommittedResource(&hdrHeapProps, D3D12_HEAP_FLAG_NONE, &hdrDesc,
        D3D12_RESOURCE_STATE_RENDER_TARGET, &hdrClear, IID_PPV_ARGS(&mHdrTarget)), "HDR target creation failed.");
    md3dDevice->CreateRenderTargetView(mHdrTarget.Get(), nullptr, rtvHandle);

    D3D12_DESCRIPTOR_HEAP_DESC srvHeapDesc = {};
    srvHeapDesc.NumDescriptors = DescriptorCount;
    srvHeapDesc.Type = D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;
    srvHeapDesc.Flags = D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
    Check(md3dDevice->CreateDescriptorHeap(&srvHeapDesc, IID_PPV_ARGS(&mSrvHeap)), "SRV heap creation failed.");
    const UINT srvSize = md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    auto cpuDescriptor = [&](UINT i) { return CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(), i, srvSize); };
    auto gpuDescriptor = [&](UINT i) { return CD3DX12_GPU_DESCRIPTOR_HANDLE(mSrvHeap->GetGPUDescriptorHandleForHeapStart(), i, srvSize); };
    md3dDevice->CreateShaderResourceView(mHdrTarget.Get(), nullptr, cpuDescriptor(HdrSrv));
    md3dDevice->CreateUnorderedAccessView(mHdrTarget.Get(),nullptr,nullptr,cpuDescriptor(ContactHdrUav));

    // Composite and history images, same format as the HDR image. The first history starts readable.
    auto createImage = [&](ComPtr<ID3D12Resource>& image, D3D12_RESOURCE_STATES state, UINT rtv, UINT srv) {
        Check(md3dDevice->CreateCommittedResource(&hdrHeapProps, D3D12_HEAP_FLAG_NONE, &hdrDesc, state, &hdrClear,
            IID_PPV_ARGS(&image)), "Image creation failed.");
        md3dDevice->CreateRenderTargetView(image.Get(), nullptr,
            CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), rtv, mRtvDescriptorSize));
        md3dDevice->CreateShaderResourceView(image.Get(), nullptr, cpuDescriptor(srv));
    };
    createImage(mComposite, D3D12_RESOURCE_STATE_RENDER_TARGET, CompositeRtv, CompositeSrv);
    createImage(mSkyTransport, D3D12_RESOURCE_STATE_RENDER_TARGET, SkyTransportRtv, SkyTransportSrv);
    createImage(mCelestialTarget, D3D12_RESOURCE_STATE_RENDER_TARGET, CelestialRtv, CelestialSrv);
    const auto airlessDesc=CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R8G8B8A8_UNORM,2048,1024,1,12);
    for(unsigned i=0;i<Celestial::MoonCount;++i) {
        Check(md3dDevice->CreateCommittedResource(&hdrHeapProps,D3D12_HEAP_FLAG_NONE,&airlessDesc,
            D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&mAirlessMaterial[i])),"Airless material creation failed.");
        md3dDevice->CreateShaderResourceView(mAirlessMaterial[i].Get(),nullptr,cpuDescriptor(AirlessMaterialSrv+i));
    }
    createImage(mHistory[0], D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, HistoryRtv, HistorySrv);
    createImage(mHistory[1], D3D12_RESOURCE_STATE_RENDER_TARGET, HistoryRtv + 1, HistorySrv + 1);

    // The cloud temporal pass (CloudsTemporal.hlsli): fresh tiles, one texel per 4x4 pixels, the drifted pixels,
    // one texel per 2x2, and two full histories; light and transmittance in half floats, distances in floats, and the
    // distance's spread and the reprojection's drift in half floats. The first history starts readable.
    if (mSettings.cloudTemporal) {
        const DXGI_FORMAT formats[3] = { DXGI_FORMAT_R16G16B16A16_FLOAT, DXGI_FORMAT_R32G32B32A32_FLOAT,
                                         DXGI_FORMAT_R16G16_FLOAT };
        auto createCloudImage = [&](ComPtr<ID3D12Resource>& image, UINT format, UINT width, UINT height,
                                    D3D12_RESOURCE_STATES state, UINT rtv) {
            const auto desc = CD3DX12_RESOURCE_DESC::Tex2D(formats[format], width, height, 1, 1, 1, 0,
                D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET);
            Check(md3dDevice->CreateCommittedResource(&hdrHeapProps, D3D12_HEAP_FLAG_NONE, &desc, state, nullptr,
                IID_PPV_ARGS(&image)), "Cloud temporal image creation failed.");
            md3dDevice->CreateRenderTargetView(image.Get(), nullptr,
                CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), rtv, mRtvDescriptorSize));
        };
        for (UINT i = 0; i < 2; ++i) {
            createCloudImage(mCloudFresh[i], i, (mClientWidth + CloudTileX - 1) / CloudTileX,
                (mClientHeight + CloudTileY - 1) / CloudTileY, D3D12_RESOURCE_STATE_RENDER_TARGET, CloudFreshRtv + i);
            createCloudImage(mCloudFresh[2 + i], i, (mClientWidth + 1) / 2, (mClientHeight + 1) / 2,
                D3D12_RESOURCE_STATE_RENDER_TARGET, CloudHalfRtv + i);
        }
        for (UINT h = 0; h < 2; ++h)
            for (UINT i = 0; i < 3; ++i)
                createCloudImage(mCloudHistory[h][i], i, mClientWidth, mClientHeight, h == 0
                    ? D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE : D3D12_RESOURCE_STATE_RENDER_TARGET, CloudHistoryRtv + 3 * h + i);
        for (UINT h = 0; h < 2; ++h) // t44..t50
            for (UINT i = 0; i < 7; ++i)
                md3dDevice->CreateShaderResourceView(i < 2 ? mCloudFresh[i].Get() : i < 5 ? mCloudHistory[h][i - 2].Get()
                    : mCloudFresh[i - 3].Get(), nullptr, cpuDescriptor(CloudTemporalSrv + 7 * h + i));
    }

    // Atmosphere tables: written once by compute shaders, read by the terrain and the sky. A slice per haze's ground.
    for (UINT i = 0; i < 3; ++i) {
        CD3DX12_RESOURCE_DESC lutDesc = CD3DX12_RESOURCE_DESC::Tex3D(i==2?HdrFormat:DXGI_FORMAT_R16G16B16A16_FLOAT, kLutSizes[i][0],
            kLutSizes[i][1], kLutGroundSlices, 1, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        Check(md3dDevice->CreateCommittedResource(&hdrHeapProps, D3D12_HEAP_FLAG_NONE, &lutDesc,
            D3D12_RESOURCE_STATE_UNORDERED_ACCESS, nullptr, IID_PPV_ARGS(&mAtmosphereLuts[i])), "Atmosphere table creation failed.");
        md3dDevice->CreateShaderResourceView(mAtmosphereLuts[i].Get(), nullptr, cpuDescriptor(LutSrv + i));
        md3dDevice->CreateUnorderedAccessView(mAtmosphereLuts[i].Get(), nullptr, nullptr, cpuDescriptor(LutUav + i));
    }

    // Close-up materials: written once by the generator, mip after mip, then read by the terrain's pixels.
    for (UINT t = 0; t < 2; ++t) {
        CD3DX12_RESOURCE_DESC materialDesc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R8G8B8A8_UNORM, MaterialSize,
            MaterialSize, MaterialCount, MaterialMips, 1, 0, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        Check(md3dDevice->CreateCommittedResource(&hdrHeapProps, D3D12_HEAP_FLAG_NONE, &materialDesc,
            D3D12_RESOURCE_STATE_UNORDERED_ACCESS, nullptr, IID_PPV_ARGS(&mMaterials[t])), "Material creation failed.");
        D3D12_SHADER_RESOURCE_VIEW_DESC srvDesc = {};
        srvDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
        srvDesc.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2DARRAY;
        srvDesc.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srvDesc.Texture2DArray.MipLevels = MaterialMips;
        srvDesc.Texture2DArray.ArraySize = MaterialCount;
        md3dDevice->CreateShaderResourceView(mMaterials[t].Get(), &srvDesc, cpuDescriptor(MaterialSrv + t));
        for (UINT m = 0; m < MaterialMips; ++m) {
            D3D12_UNORDERED_ACCESS_VIEW_DESC uavDesc = {};
            uavDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
            uavDesc.ViewDimension = D3D12_UAV_DIMENSION_TEXTURE2DARRAY;
            uavDesc.Texture2DArray.MipSlice = m;
            uavDesc.Texture2DArray.ArraySize = MaterialCount;
            md3dDevice->CreateUnorderedAccessView(mMaterials[t].Get(), nullptr, &uavDesc, cpuDescriptor(MaterialUav + 2 * m + t));
        }
    }

    // The terrain's sunlit part, a second render target of the scene, for the clouds' shadow (t17).
    {
        D3D12_CLEAR_VALUE sunClear = {};
        sunClear.Format = SunFormat;
        const CD3DX12_RESOURCE_DESC sunDesc = CD3DX12_RESOURCE_DESC::Tex2D(SunFormat, mClientWidth, mClientHeight, 1, 1, 1, 0,
            D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET | D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        Check(md3dDevice->CreateCommittedResource(&hdrHeapProps, D3D12_HEAP_FLAG_NONE, &sunDesc, D3D12_RESOURCE_STATE_RENDER_TARGET,
            &sunClear, IID_PPV_ARGS(&mSunPart)), "Sunlit part creation failed.");
        md3dDevice->CreateRenderTargetView(mSunPart.Get(), nullptr,
            CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), SunRtv, mRtvDescriptorSize));
        md3dDevice->CreateShaderResourceView(mSunPart.Get(), nullptr, cpuDescriptor(SunSrv));
        md3dDevice->CreateUnorderedAccessView(mSunPart.Get(),nullptr,nullptr,cpuDescriptor(ContactSunUav));
    }
    {
        const auto desc=CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R16G16_FLOAT,(mClientWidth+1)/2,(mClientHeight+1)/2,1,1,1,0,D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        Check(md3dDevice->CreateCommittedResource(&hdrHeapProps,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_UNORDERED_ACCESS,nullptr,IID_PPV_ARGS(&mLocalContacts)),"Contact lighting image creation failed.");
        md3dDevice->CreateShaderResourceView(mLocalContacts.Get(),nullptr,cpuDescriptor(ContactSrv));
        md3dDevice->CreateUnorderedAccessView(mLocalContacts.Get(),nullptr,nullptr,cpuDescriptor(ContactUav));
        wchar_t enabled[8]={};const DWORD length=GetEnvironmentVariableW(L"MYPLANETENGINE_LOCAL_CONTACTS",enabled,8);
        mLocalContactsEnabled=!(length==1 && enabled[0]==L'0');
        for (DXGI_FORMAT format:{HdrFormat,SunFormat}) {
            D3D12_FEATURE_DATA_FORMAT_SUPPORT support={format};
            if (FAILED(md3dDevice->CheckFeatureSupport(D3D12_FEATURE_FORMAT_SUPPORT,&support,sizeof(support))) || !(support.Support2&D3D12_FORMAT_SUPPORT2_UAV_TYPED_LOAD)) mLocalContactsEnabled=false;
        }
    }
    // The clouds' textures (assets/clouds), t24..t27: three noise volumes, then the planet's weather map.
    auto createCloudVolume = [&](ComPtr<ID3D12Resource>& texture, UINT side, UINT mips, UINT descriptor) {
        const auto desc = CD3DX12_RESOURCE_DESC::Tex3D(DXGI_FORMAT_R8G8B8A8_UNORM, side, side,
            static_cast<UINT16>(side), static_cast<UINT16>(mips));
        Check(md3dDevice->CreateCommittedResource(&hdrHeapProps, D3D12_HEAP_FLAG_NONE, &desc,
            D3D12_RESOURCE_STATE_COPY_DEST, nullptr, IID_PPV_ARGS(&texture)), "Cloud texture creation failed.");
        D3D12_SHADER_RESOURCE_VIEW_DESC srv = {}; srv.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
        srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE3D; srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture3D.MipLevels = mips; md3dDevice->CreateShaderResourceView(texture.Get(), &srv, cpuDescriptor(descriptor));
    };
    createCloudVolume(mCloudShape, 128u, 8u, CloudSrv);
    createCloudVolume(mCloudDetail, 32u, 6u, CloudSrv + 1);
    createCloudVolume(mCloudProfiles, 64u, 7u, CloudSrv + 2);
    const auto weatherDesc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R8G8B8A8_UNORM, 1024u, 512u, 1u, 11u);
    Check(md3dDevice->CreateCommittedResource(&hdrHeapProps, D3D12_HEAP_FLAG_NONE, &weatherDesc,
        D3D12_RESOURCE_STATE_COPY_DEST, nullptr, IID_PPV_ARGS(&mCloudWeather)), "Cloud weather map creation failed.");
    D3D12_SHADER_RESOURCE_VIEW_DESC weatherSrv = {};
    weatherSrv.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    weatherSrv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
    weatherSrv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    weatherSrv.Texture2D.MipLevels = 11;
    md3dDevice->CreateShaderResourceView(mCloudWeather.Get(), &weatherSrv, cpuDescriptor(CloudSrv + 3));

    // Depth buffer, reversed Z: 1 at the near plane, 0 at the far plane, cleared to 0.
    D3D12_DESCRIPTOR_HEAP_DESC dsvHeapDesc = {};
    dsvHeapDesc.NumDescriptors = 1;
    dsvHeapDesc.Type = D3D12_DESCRIPTOR_HEAP_TYPE_DSV;
    Check(md3dDevice->CreateDescriptorHeap(&dsvHeapDesc, IID_PPV_ARGS(&mDsvHeap)), "DSV heap creation failed.");

    CD3DX12_HEAP_PROPERTIES depthHeapProps(D3D12_HEAP_TYPE_DEFAULT);
    CD3DX12_RESOURCE_DESC depthDesc = CD3DX12_RESOURCE_DESC::Tex2D(
        DXGI_FORMAT_R32_TYPELESS, mClientWidth, mClientHeight, 1, 1, 1, 0, D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL);
    D3D12_CLEAR_VALUE depthClear = {};
    depthClear.Format = DXGI_FORMAT_D32_FLOAT;
    depthClear.DepthStencil.Depth = 0.0f;
    Check(md3dDevice->CreateCommittedResource(&depthHeapProps, D3D12_HEAP_FLAG_NONE, &depthDesc,
        D3D12_RESOURCE_STATE_DEPTH_WRITE, &depthClear, IID_PPV_ARGS(&mDepthStencilBuffer)), "Depth buffer creation failed.");
    D3D12_DEPTH_STENCIL_VIEW_DESC depthView = {};
    depthView.Format = DXGI_FORMAT_D32_FLOAT; depthView.ViewDimension = D3D12_DSV_DIMENSION_TEXTURE2D;
    md3dDevice->CreateDepthStencilView(mDepthStencilBuffer.Get(), &depthView, mDsvHeap->GetCPUDescriptorHandleForHeapStart());

    Check(md3dDevice->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT, IID_PPV_ARGS(&mCommandAllocator)),
        "Command allocator creation failed.");
    Check(md3dDevice->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, mCommandAllocator.Get(), nullptr,
        IID_PPV_ARGS(&mCommandList)), "Command list creation failed.");
    mCommandList->Close();

    Check(md3dDevice->CreateFence(0, D3D12_FENCE_FLAG_NONE, IID_PPV_ARGS(&mFence)), "Fence creation failed.");
    mFenceEvent = CreateEvent(nullptr, FALSE, FALSE, nullptr);

    // Root signatures. Graphics: frame constants, face vertices (SRV), atmosphere tables, the face vertices again for the
    // pixels' spline normals. Terrain compute: frame constants, face vertices (UAV).
    const CD3DX12_STATIC_SAMPLER_DESC linearClamp(0, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
        D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP);
    CD3DX12_DESCRIPTOR_RANGE lutRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 3, 1); // t1..t3
    CD3DX12_DESCRIPTOR_RANGE materialRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 2, 5); // t5, t6
    const CD3DX12_STATIC_SAMPLER_DESC samplers[4] = { linearClamp,
        CD3DX12_STATIC_SAMPLER_DESC(1, D3D12_FILTER_ANISOTROPIC),
        CD3DX12_STATIC_SAMPLER_DESC(2, D3D12_FILTER_MIN_MAG_MIP_LINEAR),
        CD3DX12_STATIC_SAMPLER_DESC(4, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
            D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP) }; // s4: erosion's climate
    CD3DX12_DESCRIPTOR_RANGE oceanRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,6,11);
    CD3DX12_DESCRIPTOR_RANGE planetMapRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 29);
    CD3DX12_DESCRIPTOR_RANGE shipSunRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 44); // the ship's map towards the sun
    // The tectonic map and its views (Tectonics.hlsli), the climate map (Climate.hlsli), the volcanoes and their index
    // (Volcanoes.hlsli), and the erosion map (Erosion.hlsli): t18..t23.
    // The courses built at startup follow them in the same table (Erosion.hlsli, ErosionCourseRecord): t60.
    const CD3DX12_DESCRIPTOR_RANGE tectonicRanges[2] = { CD3DX12_DESCRIPTOR_RANGE(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 6, 18),
                                                         CD3DX12_DESCRIPTOR_RANGE(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 60) };
    CD3DX12_DESCRIPTOR_RANGE citySunRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,53);
    CD3DX12_ROOT_PARAMETER params[14];
    params[0].InitAsConstantBufferView(0);
    params[1].InitAsShaderResourceView(0, 0, D3D12_SHADER_VISIBILITY_VERTEX);
    params[2].InitAsDescriptorTable(1, &lutRange, D3D12_SHADER_VISIBILITY_PIXEL);
    params[3].InitAsShaderResourceView(4, 0, D3D12_SHADER_VISIBILITY_PIXEL);
    params[4].InitAsDescriptorTable(1, &materialRange, D3D12_SHADER_VISIBILITY_PIXEL);
    params[5].InitAsShaderResourceView(7, 0, D3D12_SHADER_VISIBILITY_PIXEL); // the fine grid's normals
    params[6].InitAsShaderResourceView(8, 0, D3D12_SHADER_VISIBILITY_VERTEX); // the objects' shapes
    params[7].InitAsDescriptorTable(1, &planetMapRange, D3D12_SHADER_VISIBILITY_PIXEL);
    params[8].InitAsConstantBufferView(1);
    params[9].InitAsDescriptorTable(1,&oceanRange);
    params[10].InitAsDescriptorTable(1, &shipSunRange, D3D12_SHADER_VISIBILITY_PIXEL);
    params[11].InitAsDescriptorTable(2, tectonicRanges, D3D12_SHADER_VISIBILITY_PIXEL);
    params[12].InitAsShaderResourceView(52, 0, D3D12_SHADER_VISIBILITY_PIXEL); // the screen relief
    params[13].InitAsDescriptorTable(1,&citySunRange,D3D12_SHADER_VISIBILITY_PIXEL);
    mRootSignature = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(14, params, 4, samplers));
    // Terrain compute: frame constants, its output (UAV), the tectonic map the relief reads (Relief.hlsli).
    CD3DX12_ROOT_PARAMETER computeParams[3];
    computeParams[0].InitAsConstantBufferView(0);
    computeParams[1].InitAsUnorderedAccessView(0);
    computeParams[2].InitAsDescriptorTable(2, tectonicRanges);
    mComputeRootSignature = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(3, computeParams, 1, &samplers[3]));
    CD3DX12_ROOT_PARAMETER screenParams[8];
    screenParams[0].InitAsConstantBufferView(0);
    screenParams[1].InitAsUnorderedAccessView(0);
    screenParams[2].InitAsDescriptorTable(2, tectonicRanges);
    screenParams[3].InitAsUnorderedAccessView(1);
    screenParams[4].InitAsConstants(1, 1);
    for (UINT i = 0; i != 3; ++i) screenParams[5 + i].InitAsUnorderedAccessView(2 + i); // the wide queries (ScreenRiverTasks.hlsli)
    mScreenRootSignature = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(8, screenParams, 1, &samplers[3]));
    // Fine grid normals: frame constants, the grid's positions (SRV), its normals (UAV). Its positions use the
    // terrain compute's signature.
    CD3DX12_ROOT_PARAMETER fineParams[3];
    fineParams[0].InitAsConstantBufferView(0);
    fineParams[1].InitAsShaderResourceView(0);
    fineParams[2].InitAsUnorderedAccessView(0);
    mFineRootSignature = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(3, fineParams));
    // Objects' placement, both passes: frame constants, the mesh as drawn (SRV), instances and counters (UAVs), the
    // materials and their sampler, the placement's constants; the candidates' list and the second pass's dispatch, written
    // by the first (UAVs), read by the second (SRVs).
    CD3DX12_ROOT_PARAMETER objectParams[19];
    objectParams[0].InitAsConstantBufferView(0);
    objectParams[1].InitAsShaderResourceView(0);
    objectParams[2].InitAsUnorderedAccessView(0);
    objectParams[3].InitAsUnorderedAccessView(1);
    objectParams[4].InitAsDescriptorTable(1, &materialRange);
    objectParams[5].InitAsConstants(sizeof(PlacementConstants) / 4, 1);
    objectParams[6].InitAsUnorderedAccessView(2);
    objectParams[7].InitAsUnorderedAccessView(3);
    objectParams[8].InitAsShaderResourceView(1);
    objectParams[9].InitAsShaderResourceView(2);
    objectParams[10].InitAsDescriptorTable(1, &planetMapRange); // the plants' exposure (Vegetation.hlsli)
    for (UINT i = 0; i < 4; ++i) objectParams[11 + i].InitAsUnorderedAccessView(4 + i); // stable plant scratch
    for (UINT i = 0; i < 3; ++i) objectParams[15 + i].InitAsUnorderedAccessView(8 + i); // the plant tiles' kept ground (PlanetPlantPlacement)
    objectParams[18].InitAsDescriptorTable(2, tectonicRanges); // the relief's tectonic map, for the exact ground
    const CD3DX12_STATIC_SAMPLER_DESC objectSamplers[2] = { samplers[1], samplers[3] };
    mObjectRootSignature = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(19, objectParams, 2, objectSamplers));
    // The atmosphere pass, full screen: frame constants, HDR and atmosphere tables, the relief shadow mesh, the terrain's
    // sunlit part, the clouds' frame (b1) and textures, the planet map, then the cloud temporal pass's images.
    CD3DX12_DESCRIPTOR_RANGE postRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 4, 0); // t0..t3
    CD3DX12_DESCRIPTOR_RANGE sunRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 17); // t17
    CD3DX12_DESCRIPTOR_RANGE cloudRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 4, 24); // t24..t27
    CD3DX12_DESCRIPTOR_RANGE temporalRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 7, 44); // t44..t50
    CD3DX12_ROOT_PARAMETER postParams[8];
    postParams[0].InitAsConstantBufferView(0);
    postParams[1].InitAsDescriptorTable(1, &postRange, D3D12_SHADER_VISIBILITY_PIXEL);
    postParams[2].InitAsShaderResourceView(9, 0, D3D12_SHADER_VISIBILITY_PIXEL);
    postParams[3].InitAsDescriptorTable(1, &sunRange, D3D12_SHADER_VISIBILITY_PIXEL);
    postParams[4].InitAsConstantBufferView(1, 0, D3D12_SHADER_VISIBILITY_PIXEL);
    postParams[5].InitAsDescriptorTable(1, &cloudRange, D3D12_SHADER_VISIBILITY_PIXEL);
    postParams[6].InitAsDescriptorTable(1, &planetMapRange, D3D12_SHADER_VISIBILITY_PIXEL);
    postParams[7].InitAsDescriptorTable(1, &temporalRange, D3D12_SHADER_VISIBILITY_PIXEL);
    const CD3DX12_STATIC_SAMPLER_DESC postSamplers[3] = {
        linearClamp, CD3DX12_STATIC_SAMPLER_DESC(2, D3D12_FILTER_MIN_MAG_MIP_LINEAR),
        CD3DX12_STATIC_SAMPLER_DESC(3, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_WRAP,
            D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP) };
    mPostRootSignature = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(8, postParams, 3, postSamplers));
    // Temporal smoothing and tone map: frame constants, the composite image, the previous result, the atmosphere
    // tables (the exposure's daylight).
    CD3DX12_DESCRIPTOR_RANGE compositeRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 0), historyRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 4),
        glassRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 5);
    CD3DX12_DESCRIPTOR_RANGE celestialRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 2, 6), glareRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 8),
        adaptationRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 9);
    CD3DX12_ROOT_PARAMETER resolveParams[8];
    resolveParams[0].InitAsConstantBufferView(0);
    resolveParams[1].InitAsDescriptorTable(1, &compositeRange, D3D12_SHADER_VISIBILITY_PIXEL);
    resolveParams[2].InitAsDescriptorTable(1, &historyRange, D3D12_SHADER_VISIBILITY_PIXEL);
    resolveParams[3].InitAsDescriptorTable(1, &lutRange, D3D12_SHADER_VISIBILITY_PIXEL);
    resolveParams[4].InitAsDescriptorTable(1, &glassRange, D3D12_SHADER_VISIBILITY_PIXEL); // the ship's glass (Ship.h)
    resolveParams[5].InitAsDescriptorTable(1, &celestialRange, D3D12_SHADER_VISIBILITY_PIXEL);
    resolveParams[6].InitAsDescriptorTable(1, &glareRange, D3D12_SHADER_VISIBILITY_PIXEL); // the summed glare (Glare.h)
    resolveParams[7].InitAsDescriptorTable(1, &adaptationRange, D3D12_SHADER_VISIBILITY_PIXEL); // local adaptation
    mResolveRootSignature = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(8, resolveParams, 1, &linearClamp));
    CD3DX12_DESCRIPTOR_RANGE skyTransportRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 4);
    CD3DX12_DESCRIPTOR_RANGE lunarRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,8);
    CD3DX12_DESCRIPTOR_RANGE distantPlanetRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,29),distantClimateRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,20);
    CD3DX12_ROOT_PARAMETER celestialParams[7];
    celestialParams[0].InitAsConstantBufferView(0);
    celestialParams[1].InitAsDescriptorTable(1, &compositeRange);
    celestialParams[2].InitAsDescriptorTable(1, &skyTransportRange);
    celestialParams[3].InitAsDescriptorTable(1,&lunarRange,D3D12_SHADER_VISIBILITY_PIXEL);
    celestialParams[4].InitAsConstants(2,4,0,D3D12_SHADER_VISIBILITY_PIXEL);
    celestialParams[5].InitAsDescriptorTable(1,&distantPlanetRange,D3D12_SHADER_VISIBILITY_PIXEL);
    celestialParams[6].InitAsDescriptorTable(1,&distantClimateRange,D3D12_SHADER_VISIBILITY_PIXEL);
    const CD3DX12_STATIC_SAMPLER_DESC lunarSampler(0,D3D12_FILTER_MIN_MAG_MIP_LINEAR,
        D3D12_TEXTURE_ADDRESS_MODE_WRAP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP,D3D12_TEXTURE_ADDRESS_MODE_CLAMP);
    mCelestialRoot = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(7, celestialParams, 1, &lunarSampler));
    // Atmosphere tables: the ones already computed, and the three outputs.
    CD3DX12_DESCRIPTOR_RANGE lutUavRange(D3D12_DESCRIPTOR_RANGE_TYPE_UAV, 3, 0); // u0..u2
    CD3DX12_ROOT_PARAMETER lutParams[2];
    lutParams[0].InitAsDescriptorTable(1, &lutRange);
    lutParams[1].InitAsDescriptorTable(1, &lutUavRange);
    ComPtr<ID3D12RootSignature> lutRootSignature =
        CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(2, lutParams, 1, &linearClamp));
    // Material generator: the mip and its size, the mip's two arrays, the previous mip's two arrays.
    CD3DX12_DESCRIPTOR_RANGE materialOutRange(D3D12_DESCRIPTOR_RANGE_TYPE_UAV, 2, 0); // u0, u1
    CD3DX12_DESCRIPTOR_RANGE materialInRange(D3D12_DESCRIPTOR_RANGE_TYPE_UAV, 2, 2);  // u2, u3
    CD3DX12_ROOT_PARAMETER generatorParams[3];
    generatorParams[0].InitAsConstants(2, 0);
    generatorParams[1].InitAsDescriptorTable(1, &materialOutRange);
    generatorParams[2].InitAsDescriptorTable(1, &materialInRange);
    ComPtr<ID3D12RootSignature> generatorRootSignature =
        CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(3, generatorParams));

    // Pipelines. No input layout: the vertex shader reads the face vertices by SV_VertexID.
    ComPtr<ID3DBlob> vs = LoadShader(L"VertexShader.cso");
    ComPtr<ID3DBlob> ps = LoadShader(L"PixelShader.cso");
    ComPtr<ID3DBlob> cs = LoadShader(L"TerrainCompute.cso");

    D3D12_GRAPHICS_PIPELINE_STATE_DESC psoDesc = {};
    psoDesc.pRootSignature = mRootSignature.Get();
    psoDesc.VS = CD3DX12_SHADER_BYTECODE(vs.Get());
    psoDesc.PS = CD3DX12_SHADER_BYTECODE(ps.Get());
    psoDesc.RasterizerState = CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);
    psoDesc.RasterizerState.CullMode = D3D12_CULL_MODE_NONE;
    psoDesc.BlendState = CD3DX12_BLEND_DESC(D3D12_DEFAULT);
    psoDesc.DepthStencilState = CD3DX12_DEPTH_STENCIL_DESC(D3D12_DEFAULT);
    psoDesc.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_GREATER; // reversed Z
    psoDesc.SampleMask = UINT_MAX;
    psoDesc.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    psoDesc.NumRenderTargets = 2;
    psoDesc.RTVFormats[0] = HdrFormat;
    psoDesc.RTVFormats[1] = SunFormat; // the sunlit part, for the clouds' shade
    psoDesc.DSVFormat = DXGI_FORMAT_D32_FLOAT;
    psoDesc.SampleDesc.Count = 1;
    // The terrain's costly pixels run once per pixel it shows (docs/optimisation.md, round 2): its depth first, with the
    // same vertex shader, then its colour after the plants, on the depth it wrote, not over itself nor under the plants.
    {
        D3D12_GRAPHICS_PIPELINE_STATE_DESC depthDesc = psoDesc;
        depthDesc.PS = {};
        depthDesc.NumRenderTargets = 0;
        depthDesc.RTVFormats[0] = depthDesc.RTVFormats[1] = DXGI_FORMAT_UNKNOWN;
        Check(md3dDevice->CreateGraphicsPipelineState(&depthDesc, IID_PPV_ARGS(&mTerrainDepthPSO)), "Terrain depth PSO creation failed.");
        D3D12_GRAPHICS_PIPELINE_STATE_DESC shadeDesc = psoDesc;
        shadeDesc.DepthStencilState.DepthFunc = D3D12_COMPARISON_FUNC_EQUAL;
        shadeDesc.DepthStencilState.DepthWriteMask = D3D12_DEPTH_WRITE_MASK_ZERO;
        Check(md3dDevice->CreateGraphicsPipelineState(&shadeDesc, IID_PPV_ARGS(&mTerrainShadePSO)), "Terrain shade PSO creation failed.");
        ComPtr<ID3DBlob> screenPs = LoadShader(L"PixelShaderScreen.cso");
        shadeDesc.PS = CD3DX12_SHADER_BYTECODE(screenPs.Get());
        Check(md3dDevice->CreateGraphicsPipelineState(&shadeDesc, IID_PPV_ARGS(&mTerrainShadeScreenPSO)),
            "Terrain screen shade PSO creation failed.");
        ComPtr<ID3DBlob> nearPs = LoadShader(L"PixelShaderNear.cso"), screenNearPs = LoadShader(L"PixelShaderScreenNear.cso");
        shadeDesc.PS = CD3DX12_SHADER_BYTECODE(nearPs.Get());
        Check(md3dDevice->CreateGraphicsPipelineState(&shadeDesc, IID_PPV_ARGS(&mTerrainShadeNearPSO)),
            "Terrain near shade PSO creation failed.");
        shadeDesc.PS = CD3DX12_SHADER_BYTECODE(screenNearPs.Get());
        Check(md3dDevice->CreateGraphicsPipelineState(&shadeDesc, IID_PPV_ARGS(&mTerrainShadeScreenNearPSO)),
            "Terrain screen near shade PSO creation failed.");
    }
    { // Same topology, resources and depth/shading schedule; only the physical surface program differs.
        auto lunar=psoDesc;
        const auto av=LoadShader(L"AirlessVertex.cso"),ap=LoadShader(L"AirlessPixel.cso");
        lunar.VS=CD3DX12_SHADER_BYTECODE(av.Get());lunar.PS=CD3DX12_SHADER_BYTECODE(ap.Get());
        lunar.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_EQUAL;lunar.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ZERO;
        Check(md3dDevice->CreateGraphicsPipelineState(&lunar,IID_PPV_ARGS(&mAirlessShadePSO)),"Impact surface shading failed.");
        lunar.DepthStencilState=psoDesc.DepthStencilState;lunar.RasterizerState.FillMode=D3D12_FILL_MODE_WIREFRAME;
        Check(md3dDevice->CreateGraphicsPipelineState(&lunar,IID_PPV_ARGS(&mAirlessWirePSO)),"Impact wireframe failed.");
        lunar.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;lunar.PS={};lunar.NumRenderTargets=0;
        lunar.RTVFormats[0]=lunar.RTVFormats[1]=DXGI_FORMAT_UNKNOWN;
        Check(md3dDevice->CreateGraphicsPipelineState(&lunar,IID_PPV_ARGS(&mAirlessDepthPSO)),"Impact surface depth failed.");
    }
    psoDesc.RasterizerState.FillMode = D3D12_FILL_MODE_WIREFRAME;
    Check(md3dDevice->CreateGraphicsPipelineState(&psoDesc, IID_PPV_ARGS(&mWirePSO)), "Wireframe PSO creation failed.");
    // The objects: the terrain's signature, their instances in place of its vertices (t0), their shapes at t8.
    ComPtr<ID3DBlob> objectVs = LoadShader(L"ObjectVertex.cso"), objectPs = LoadShader(L"ObjectPixel.cso");
    psoDesc.RasterizerState.FillMode = D3D12_FILL_MODE_SOLID;
    psoDesc.VS = CD3DX12_SHADER_BYTECODE(objectVs.Get());
    psoDesc.PS = CD3DX12_SHADER_BYTECODE(objectPs.Get());
    Check(md3dDevice->CreateGraphicsPipelineState(&psoDesc, IID_PPV_ARGS(&mObjectPSO)), "Object PSO creation failed.");
    {
        const auto shader=LoadShader(L"AirlessObjectPixel.cso");auto objects=psoDesc;
        objects.PS=CD3DX12_SHADER_BYTECODE(shader.Get());
        Check(md3dDevice->CreateGraphicsPipelineState(&objects,IID_PPV_ARGS(&mAirlessObjectPSO)),"Impact debris shading failed.");
    }
    ComPtr<ID3DBlob> tuftVs = LoadShader(L"TuftVertex.cso"), tuftPs = LoadShader(L"TuftPixel.cso");
    psoDesc.VS = CD3DX12_SHADER_BYTECODE(tuftVs.Get());
    psoDesc.PS = CD3DX12_SHADER_BYTECODE(tuftPs.Get());
    Check(md3dDevice->CreateGraphicsPipelineState(&psoDesc, IID_PPV_ARGS(&mTuftPSO)), "Tuft PSO creation failed.");

    ComPtr<ID3DBlob> fullscreen = LoadShader(L"Fullscreen.cso");
    ComPtr<ID3DBlob> toneMap = LoadShader(L"ToneMap.cso");
    ComPtr<ID3DBlob> atmosphere = LoadShader(L"AtmospherePass.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC postDesc = {};
    postDesc.pRootSignature = mPostRootSignature.Get();
    postDesc.VS = CD3DX12_SHADER_BYTECODE(fullscreen.Get());
    postDesc.PS = CD3DX12_SHADER_BYTECODE(atmosphere.Get());
    postDesc.RasterizerState = CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);
    postDesc.BlendState = CD3DX12_BLEND_DESC(D3D12_DEFAULT);
    postDesc.DepthStencilState.DepthEnable = FALSE;
    postDesc.SampleMask = UINT_MAX;
    postDesc.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    postDesc.NumRenderTargets = 2;
    postDesc.RTVFormats[0] = HdrFormat;
    postDesc.RTVFormats[1] = HdrFormat;
    postDesc.SampleDesc.Count = 1;
    Check(md3dDevice->CreateGraphicsPipelineState(&postDesc, IID_PPV_ARGS(&mAtmospherePSO)), "Atmosphere PSO creation failed.");
    if (mLocalContactsEnabled) {
        CD3DX12_DESCRIPTOR_RANGE sceneRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,0),contactRange(D3D12_DESCRIPTOR_RANGE_TYPE_SRV,1,1),
            outputRange(D3D12_DESCRIPTOR_RANGE_TYPE_UAV,1,2),resolveRange(D3D12_DESCRIPTOR_RANGE_TYPE_UAV,2,0);
        CD3DX12_ROOT_PARAMETER parameters[5];parameters[0].InitAsConstantBufferView(0);
        parameters[1].InitAsDescriptorTable(1,&sceneRange);parameters[2].InitAsDescriptorTable(1,&contactRange);
        parameters[3].InitAsDescriptorTable(1,&outputRange);parameters[4].InitAsDescriptorTable(1,&resolveRange);
        mLocalContactRoot=CreateRootSignature(md3dDevice.Get(),CD3DX12_ROOT_SIGNATURE_DESC(5,parameters));
        const auto trace=LoadShader(L"LocalContacts.cso"),resolve=LoadShader(L"LocalContactsResolve.cso");
        D3D12_COMPUTE_PIPELINE_STATE_DESC compute={};compute.pRootSignature=mLocalContactRoot.Get();compute.CS=CD3DX12_SHADER_BYTECODE(trace.Get());
        Check(md3dDevice->CreateComputePipelineState(&compute,IID_PPV_ARGS(&mLocalContactPso)),"Contact lighting pipeline failed.");
        compute.CS=CD3DX12_SHADER_BYTECODE(resolve.Get());
        Check(md3dDevice->CreateComputePipelineState(&compute,IID_PPV_ARGS(&mLocalContactResolvePso)),"Contact lighting resolve pipeline failed.");
    }
    if (mSettings.cloudTemporal) {
        ComPtr<ID3DBlob> tracePs = LoadShader(L"CloudTrace.cso");
        ComPtr<ID3DBlob> resolvePs = LoadShader(L"CloudResolve.cso");
        ComPtr<ID3DBlob> halfPs = LoadShader(L"CloudTraceHalf.cso");
        postDesc.PS = CD3DX12_SHADER_BYTECODE(tracePs.Get());
        postDesc.NumRenderTargets = 2;
        postDesc.RTVFormats[0] = DXGI_FORMAT_R16G16B16A16_FLOAT;
        postDesc.RTVFormats[1] = DXGI_FORMAT_R32G32B32A32_FLOAT;
        Check(md3dDevice->CreateGraphicsPipelineState(&postDesc, IID_PPV_ARGS(&mCloudTracePSO)),
            "Cloud trace PSO creation failed.");
        postDesc.PS = CD3DX12_SHADER_BYTECODE(halfPs.Get());
        Check(md3dDevice->CreateGraphicsPipelineState(&postDesc, IID_PPV_ARGS(&mCloudHalfPSO)),
            "Cloud half trace PSO creation failed.");
        postDesc.PS = CD3DX12_SHADER_BYTECODE(resolvePs.Get());
        postDesc.NumRenderTargets = 5;
        postDesc.RTVFormats[0] = HdrFormat;
        postDesc.RTVFormats[1] = DXGI_FORMAT_R16G16B16A16_FLOAT;
        postDesc.RTVFormats[2] = DXGI_FORMAT_R32G32B32A32_FLOAT;
        postDesc.RTVFormats[3] = DXGI_FORMAT_R16G16_FLOAT;
        postDesc.RTVFormats[4] = HdrFormat;
        Check(md3dDevice->CreateGraphicsPipelineState(&postDesc, IID_PPV_ARGS(&mCloudResolvePSO)),
            "Cloud resolve PSO creation failed.");
        postDesc.RTVFormats[2] = postDesc.RTVFormats[3] = postDesc.RTVFormats[4] = DXGI_FORMAT_UNKNOWN;
    }
    postDesc.pRootSignature = mResolveRootSignature.Get();
    postDesc.PS = CD3DX12_SHADER_BYTECODE(toneMap.Get());
    postDesc.NumRenderTargets = 2; // the screen, and the next history
    postDesc.RTVFormats[0] = DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;
    postDesc.RTVFormats[1] = HdrFormat;
    Check(md3dDevice->CreateGraphicsPipelineState(&postDesc, IID_PPV_ARGS(&mToneMapPSO)), "Tone map PSO creation failed.");
    {   // The local adaptation's first level: the tone map's bindings, one target at a quarter of its resolution.
        const auto seed = LoadShader(L"AdaptSeed.cso");
        auto seedDesc = postDesc;
        seedDesc.PS = CD3DX12_SHADER_BYTECODE(seed.Get());
        seedDesc.NumRenderTargets = 1;
        seedDesc.RTVFormats[0] = Adaptation::Format;
        seedDesc.RTVFormats[1] = DXGI_FORMAT_UNKNOWN;
        Check(md3dDevice->CreateGraphicsPipelineState(&seedDesc, IID_PPV_ARGS(&mAdaptSeedPSO)),
            "Adaptation seed PSO creation failed.");
    }
    {
        const auto galaxy = LoadShader(L"CelestialSky.cso"), starsVS = LoadShader(L"Stars.cso"), starsPS = LoadShader(L"StarsPixel.cso");
        const auto bodies=LoadShader(L"CelestialBodies.cso");
        auto bodyDesc=postDesc;
        bodyDesc.pRootSignature=mCelestialRoot.Get(); bodyDesc.PS=CD3DX12_SHADER_BYTECODE(bodies.Get());
        bodyDesc.RTVFormats[0]=HdrFormat; bodyDesc.RTVFormats[1]=SunFormat;
        bodyDesc.DepthStencilState=CD3DX12_DEPTH_STENCIL_DESC(D3D12_DEFAULT);
        bodyDesc.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_GREATER;
        bodyDesc.DSVFormat=DXGI_FORMAT_D32_FLOAT;
        auto& bodyBlend=bodyDesc.BlendState.RenderTarget[0];bodyBlend.BlendEnable=TRUE;
        bodyBlend.SrcBlend=D3D12_BLEND_BLEND_FACTOR;bodyBlend.DestBlend=D3D12_BLEND_INV_BLEND_FACTOR;
        // Alpha is a physical distance, sometimes signed for ocean motion, never an interpolated colour.
        bodyBlend.SrcBlendAlpha=D3D12_BLEND_ONE;bodyBlend.DestBlendAlpha=D3D12_BLEND_ZERO;
        // The second target contains light/adaptation coverage, not distance; retain its gradual blend.
        bodyDesc.BlendState.IndependentBlendEnable=TRUE;
        bodyDesc.BlendState.RenderTarget[1]=bodyBlend;
        bodyDesc.BlendState.RenderTarget[1].SrcBlendAlpha=D3D12_BLEND_BLEND_FACTOR;
        bodyDesc.BlendState.RenderTarget[1].DestBlendAlpha=D3D12_BLEND_INV_BLEND_FACTOR;
        Check(md3dDevice->CreateGraphicsPipelineState(&bodyDesc,IID_PPV_ARGS(&mCelestialBodiesPSO)),"Celestial body pipeline failed.");
        // The expanded transition envelope covers detailed terrain but must not replace its depth buffer.
        bodyDesc.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ZERO;
        Check(md3dDevice->CreateGraphicsPipelineState(&bodyDesc,IID_PPV_ARGS(&mEarthProxyBlendPSO)),"Planet transition pipeline failed.");
        postDesc.pRootSignature = mCelestialRoot.Get();
        postDesc.NumRenderTargets = 1; postDesc.RTVFormats[0] = HdrFormat; postDesc.RTVFormats[1] = DXGI_FORMAT_UNKNOWN;
        postDesc.PS = CD3DX12_SHADER_BYTECODE(galaxy.Get());
        Check(md3dDevice->CreateGraphicsPipelineState(&postDesc, IID_PPV_ARGS(&mGalaxyPSO)), "Galaxy pipeline creation failed.");
        postDesc.VS = CD3DX12_SHADER_BYTECODE(starsVS.Get()); postDesc.PS = CD3DX12_SHADER_BYTECODE(starsPS.Get());
        postDesc.RasterizerState.CullMode = D3D12_CULL_MODE_NONE;
        auto& blend = postDesc.BlendState.RenderTarget[0]; blend.BlendEnable = TRUE;
        blend.SrcBlend = blend.DestBlend = D3D12_BLEND_ONE; blend.BlendOp = D3D12_BLEND_OP_ADD;
        blend.SrcBlendAlpha = D3D12_BLEND_ONE; blend.DestBlendAlpha = D3D12_BLEND_ZERO; blend.BlendOpAlpha = D3D12_BLEND_OP_ADD;
        Check(md3dDevice->CreateGraphicsPipelineState(&postDesc, IID_PPV_ARGS(&mStarsPSO)), "Stellar pipeline creation failed.");
    }
    if (mSettings.glare) mGlare.Initialize(md3dDevice.Get(), mClientWidth, mClientHeight, HdrFormat, mComposite.Get());
    {   // The tone map's t8: the summed glare, or a null view that reads zero when no glare was drawn this frame.
        const UINT srvStep = md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
        const CD3DX12_CPU_DESCRIPTOR_HANDLE first(mSrvHeap->GetCPUDescriptorHandleForHeapStart(), GlareSrv, srvStep);
        D3D12_SHADER_RESOURCE_VIEW_DESC none = {};
        none.Format = HdrFormat;
        none.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
        none.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        none.Texture2D.MipLevels = 1;
        md3dDevice->CreateShaderResourceView(nullptr, &none, CD3DX12_CPU_DESCRIPTOR_HANDLE(first, 1, srvStep));
        if (mSettings.glare) mGlare.CreateSummedSrv(md3dDevice.Get(), first);
        else md3dDevice->CreateShaderResourceView(nullptr, &none, first);
        mAdaptation.Initialize(md3dDevice.Get(), mClientWidth, mClientHeight);
        mAdaptation.CreateSrv(md3dDevice.Get(), CD3DX12_CPU_DESCRIPTOR_HANDLE(first, AdaptationSrv - GlareSrv, srvStep));
    }

    D3D12_COMPUTE_PIPELINE_STATE_DESC computeDesc = {};
    computeDesc.pRootSignature = mComputeRootSignature.Get();
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(cs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mComputePSO)), "Compute PSO creation failed.");
    ComPtr<ID3DBlob> pairsCs = LoadShader(L"TerrainComputePairs.cso");
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(pairsCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mComputePairsPSO)), "Compute PSO creation failed.");
    ComPtr<ID3DBlob> horizonCs = LoadShader(L"Horizon.cso"); // the same signature: it writes into the terrain's vertices
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(horizonCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mHorizonPSO)), "Horizon PSO creation failed.");
    ComPtr<ID3DBlob> fineTerrainCs = LoadShader(L"FineTerrain.cso");
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(fineTerrainCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mFineTerrainPSO)), "Fine terrain PSO creation failed.");
    ComPtr<ID3DBlob> fineNormalsCs = LoadShader(L"FineNormals.cso");
    computeDesc.pRootSignature = mFineRootSignature.Get();
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(fineNormalsCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mFineNormalsPSO)), "Fine normals PSO creation failed.");
    {
        // The face's cells sorted by the pixel shader they need: frame constants, the mesh and the fine grid as drawn
        // (SRVs), the cells' indices and their draws' arguments (UAVs).
        CD3DX12_ROOT_PARAMETER cellParams[5];
        cellParams[0].InitAsConstantBufferView(0);
        cellParams[1].InitAsShaderResourceView(0);
        cellParams[2].InitAsShaderResourceView(1);
        cellParams[3].InitAsUnorderedAccessView(0);
        cellParams[4].InitAsUnorderedAccessView(1);
        mContourCellsRootSignature = CreateRootSignature(md3dDevice.Get(), CD3DX12_ROOT_SIGNATURE_DESC(5, cellParams));
        ComPtr<ID3DBlob> cellsCs = LoadShader(L"TerrainContourCells.cso");
        D3D12_COMPUTE_PIPELINE_STATE_DESC cellsDesc = {};
        cellsDesc.pRootSignature = mContourCellsRootSignature.Get();
        cellsDesc.CS = CD3DX12_SHADER_BYTECODE(cellsCs.Get());
        Check(md3dDevice->CreateComputePipelineState(&cellsDesc, IID_PPV_ARGS(&mContourCellsPSO)), "Contour cells PSO creation failed.");
    }
    ComPtr<ID3DBlob> screenReliefCs = LoadShader(L"ScreenRelief.cso"); // the terrain compute's signature
    computeDesc.pRootSignature = mScreenRootSignature.Get();
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(screenReliefCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mScreenReliefPSO)), "Screen relief PSO creation failed.");
    ComPtr<ID3DBlob> screenRiversCs = LoadShader(L"ScreenRivers.cso");
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(screenRiversCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mScreenRiversPSO)), "Screen rivers PSO creation failed.");
    ComPtr<ID3DBlob> screenRiverTexelCs = LoadShader(L"ScreenRiverTexel.cso");
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(screenRiverTexelCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mScreenRiverTexelPSO)), "Screen river texel PSO creation failed.");
    ComPtr<ID3DBlob> screenRiverArgsCs = LoadShader(L"ScreenRiverArgs.cso");
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(screenRiverArgsCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mScreenRiverArgsPSO)), "Screen river arguments PSO creation failed.");
    ComPtr<ID3DBlob> placementCs = LoadShader(L"ObjectPlacement.cso");
    computeDesc.pRootSignature = mObjectRootSignature.Get();
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(placementCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mObjectPlacementPSO)), "Placement PSO creation failed.");
    ComPtr<ID3DBlob> candidatesCs = LoadShader(L"ObjectCandidates.cso");
    computeDesc.CS = CD3DX12_SHADER_BYTECODE(candidatesCs.Get());
    Check(md3dDevice->CreateComputePipelineState(&computeDesc, IID_PPV_ARGS(&mObjectCandidatesPSO)), "Candidates PSO creation failed.");
    auto surfaceProgram=[&](const wchar_t* name,ID3D12RootSignature* root,ComPtr<ID3D12PipelineState>& pipeline) {
        const auto shader=LoadShader(name);auto program=computeDesc;program.pRootSignature=root;
        program.CS=CD3DX12_SHADER_BYTECODE(shader.Get());
        Check(md3dDevice->CreateComputePipelineState(&program,IID_PPV_ARGS(&pipeline)),"Surface stack pipeline failed.");
    };
    surfaceProgram(L"AirlessCompute.cso",mComputeRootSignature.Get(),mAirlessComputePSO);
    surfaceProgram(L"AirlessFine.cso",mComputeRootSignature.Get(),mAirlessFinePSO);
    surfaceProgram(L"AirlessHorizon.cso",mComputeRootSignature.Get(),mAirlessHorizonPSO);
    surfaceProgram(L"AirlessScreen.cso",mScreenRootSignature.Get(),mAirlessScreenPSO);
    surfaceProgram(L"AirlessObjectCandidates.cso",mObjectRootSignature.Get(),mAirlessObjectCandidatesPSO);
    surfaceProgram(L"AirlessObjectPlacement.cso",mObjectRootSignature.Get(),mAirlessObjectPlacementPSO);

    // One indirect draw of the objects: its instance count written by the placement.
    D3D12_INDIRECT_ARGUMENT_DESC drawArgument = {};
    drawArgument.Type = D3D12_INDIRECT_ARGUMENT_TYPE_DRAW_INDEXED;
    D3D12_COMMAND_SIGNATURE_DESC signatureDesc = {};
    signatureDesc.ByteStride = sizeof(D3D12_DRAW_INDEXED_ARGUMENTS);
    signatureDesc.NumArgumentDescs = 1;
    signatureDesc.pArgumentDescs = &drawArgument;
    Check(md3dDevice->CreateCommandSignature(&signatureDesc, nullptr, IID_PPV_ARGS(&mObjectCommandSignature)),
        "Command signature creation failed.");
    // And one indirect dispatch of the placement's second pass: its group count written by the first.
    drawArgument.Type = D3D12_INDIRECT_ARGUMENT_TYPE_DISPATCH;
    signatureDesc.ByteStride = sizeof(D3D12_DISPATCH_ARGUMENTS);
    Check(md3dDevice->CreateCommandSignature(&signatureDesc, nullptr, IID_PPV_ARGS(&mObjectDispatchSignature)),
        "Command signature creation failed.");

    ComPtr<ID3DBlob> generatorCs = LoadShader(L"MaterialGenerator.cso");
    D3D12_COMPUTE_PIPELINE_STATE_DESC generatorDesc = {};
    generatorDesc.pRootSignature = generatorRootSignature.Get();
    generatorDesc.CS = CD3DX12_SHADER_BYTECODE(generatorCs.Get());
    ComPtr<ID3D12PipelineState> generatorPSO;
    Check(md3dDevice->CreateComputePipelineState(&generatorDesc, IID_PPV_ARGS(&generatorPSO)), "Material PSO creation failed.");

    const wchar_t* lutShaders[3] = { L"AtmosphereTransmittance.cso", L"AtmosphereMultiScattering.cso", L"AtmosphereSkyIrradiance.cso" };
    ComPtr<ID3D12PipelineState> lutPSOs[3];
    for (UINT i = 0; i < 3; ++i) {
        ComPtr<ID3DBlob> lutCs = LoadShader(lutShaders[i]);
        D3D12_COMPUTE_PIPELINE_STATE_DESC lutDesc = {};
        lutDesc.pRootSignature = lutRootSignature.Get();
        lutDesc.CS = CD3DX12_SHADER_BYTECODE(lutCs.Get());
        Check(md3dDevice->CreateComputePipelineState(&lutDesc, IID_PPV_ARGS(&lutPSOs[i])), "Atmosphere PSO creation failed.");
    }

    // Buffers.
    mConstantBuffer = CreateBuffer(md3dDevice.Get(), (sizeof(FrameConstants) + 255) & ~255, D3D12_HEAP_TYPE_UPLOAD,
        D3D12_RESOURCE_STATE_GENERIC_READ);
    CD3DX12_RANGE noRead(0, 0);
    mConstantBuffer->Map(0, &noRead, reinterpret_cast<void**>(&mConstants));
    static const XMFLOAT4 reliefGradients[256] = {
#define RELIEF_GRADIENT(x, y, z) { float(x), float(y), float(z), 0.0f },
#include "ReliefGradients.inl"
#undef RELIEF_GRADIENT
    };
    std::memcpy(mConstants->reliefGradients, reliefGradients, sizeof(reliefGradients));
    mNadirConstantBuffer = CreateBuffer(md3dDevice.Get(), (sizeof(FrameConstants) + 255) & ~255, D3D12_HEAP_TYPE_UPLOAD,
        D3D12_RESOURCE_STATE_GENERIC_READ);
    mNadirConstantBuffer->Map(0, &noRead, reinterpret_cast<void**>(&mNadirConstants));
    mCloudConstantBuffer = CreateBuffer(md3dDevice.Get(), (sizeof(CloudFrame) + 255) & ~255, D3D12_HEAP_TYPE_UPLOAD,
        D3D12_RESOURCE_STATE_GENERIC_READ);
    mCloudConstantBuffer->Map(0, &noRead, reinterpret_cast<void**>(&mCloudConstants));
    mShipCloudConstantBuffer = CreateBuffer(md3dDevice.Get(), (sizeof(CloudFrame) + 255) & ~255, D3D12_HEAP_TYPE_UPLOAD,
        D3D12_RESOURCE_STATE_GENERIC_READ);
    Check(mShipCloudConstantBuffer->Map(0, &noRead, reinterpret_cast<void**>(&mShipCloudConstants)), "Ship weather constants map failed.");

    mFaceVertexBuffer = CreateBuffer(md3dDevice.Get(), sizeof(FaceVertex) * MaxVertexCount, D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mReadbackBuffer = CreateBuffer(md3dDevice.Get(), sizeof(FaceVertex), D3D12_HEAP_TYPE_READBACK, D3D12_RESOURCE_STATE_COPY_DEST);
    mFinePositions = CreateBuffer(md3dDevice.Get(), FineSampleBytes * FineVertexCount, D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mFineNormals = CreateBuffer(md3dDevice.Get(), FineSampleBytes * FineVertexCount, D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mScreenPositions = CreateBuffer(md3dDevice.Get(), ScreenSampleBytes * ScreenReliefMaxTexels, D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    {
        // The face's cells in two lists (TerrainContourCells.hlsl): room for every cell in each, and the two draws'
        // arguments, reset every frame from their starting values: no index yet, the second list from 6 n^2.
        const UINT faceIndices = 6 * FaceCells * FaceCells;
        mContourCellLists = CreateBuffer(md3dDevice.Get(), UINT64(2) * faceIndices * sizeof(UINT), D3D12_HEAP_TYPE_DEFAULT,
            D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        mContourCellView = { mContourCellLists->GetGPUVirtualAddress(), 2 * faceIndices * UINT(sizeof(UINT)), DXGI_FORMAT_R32_UINT };
        mContourCellArgs = CreateBuffer(md3dDevice.Get(), 2 * sizeof(D3D12_DRAW_INDEXED_ARGUMENTS), D3D12_HEAP_TYPE_DEFAULT,
            D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
        mContourCellArgsStart = CreateBuffer(md3dDevice.Get(), 2 * sizeof(D3D12_DRAW_INDEXED_ARGUMENTS), D3D12_HEAP_TYPE_UPLOAD,
            D3D12_RESOURCE_STATE_GENERIC_READ);
        const D3D12_DRAW_INDEXED_ARGUMENTS start[2] = { { 0, 1, 0, 0, 0 }, { 0, 1, faceIndices, 0, 0 } };
        void* bytes = nullptr;
        mContourCellArgsStart->Map(0, &noRead, &bytes);
        memcpy(bytes, start, sizeof(start));
        mContourCellArgsStart->Unmap(0, nullptr);
    }

    if (!mSettings.capturePath.empty() && GetEnvironmentVariableW(L"MYPLANETENGINE_SCREEN_DUMP", nullptr, 0))
        mScreenCaptureBuffer = CreateBuffer(md3dDevice.Get(), ScreenSampleBytes * ScreenReliefMaxTexels,
            D3D12_HEAP_TYPE_READBACK, D3D12_RESOURCE_STATE_COPY_DEST);

    // Objects: their instances, the draw's arguments and the measures, the candidates and the second pass's dispatch,
    // reset every frame from an upload copy; the shapes, uploaded below.
    mObjectInstances = CreateBuffer(md3dDevice.Get(), sizeof(ObjectInstance) * ObjectCapacity, D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mObjectCounters = CreateBuffer(md3dDevice.Get(), ObjectCounters * sizeof(UINT), D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mObjectCandidates = CreateBuffer(md3dDevice.Get(), 16 * ObjectCandidates, D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mObjectDispatch = CreateBuffer(md3dDevice.Get(), 4 * sizeof(UINT), D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mObjectCountersReset = CreateBuffer(md3dDevice.Get(), (ObjectCounters + 4) * sizeof(UINT), D3D12_HEAP_TYPE_UPLOAD,
        D3D12_RESOURCE_STATE_GENERIC_READ);
    mObjectReadback = CreateBuffer(md3dDevice.Get(), ObjectCounters * sizeof(UINT), D3D12_HEAP_TYPE_READBACK,
        D3D12_RESOURCE_STATE_COPY_DEST);
    // MYPLANETENGINE_OBJECT_LIST, in batch mode: the objects of each capture, for the pop measure (tools/banc_objets.py).
    if (mSettings.batch && (mSettings.objectCensus || mSettings.objectList))
        mObjectInstancesReadback = CreateBuffer(md3dDevice.Get(), sizeof(ObjectInstance) * ObjectCapacity, D3D12_HEAP_TYPE_READBACK,
            D3D12_RESOURCE_STATE_COPY_DEST);
    std::vector<ShapeVertex> shapeVertices, tuftVertices;
    std::vector<UINT> shapeIndices, tuftIndices;
    BuildRocks(shapeVertices, shapeIndices);
    BuildTufts(tuftVertices, tuftIndices);
    const UINT rockIndexCount = UINT(shapeIndices.size());
    mTuftShapeOffset = sizeof(ShapeVertex) * shapeVertices.size();
    shapeVertices.insert(shapeVertices.end(), tuftVertices.begin(), tuftVertices.end());
    shapeIndices.insert(shapeIndices.end(), tuftIndices.begin(), tuftIndices.end());
    {
        UINT* reset = nullptr;
        CD3DX12_RANGE none(0, 0);
        mObjectCountersReset->Map(0, &none, reinterpret_cast<void**>(&reset));
        std::fill(reset, reset + ObjectCounters + 4, 0u);
        reset[0] = rockIndexCount; // the indices per instance; the instance count at 0
        reset[TuftArguments] = UINT(tuftIndices.size());
        reset[TuftArguments + 2] = rockIndexCount; // the tufts' first index
        reset[ObjectCounters + 1] = reset[ObjectCounters + 2] = 1; // the dispatch: no group, 1, 1; no candidate
        mObjectCountersReset->Unmap(0, nullptr);
    }

    // GPU timestamps.
    D3D12_QUERY_HEAP_DESC queryDesc = {};
    queryDesc.Type = D3D12_QUERY_HEAP_TYPE_TIMESTAMP;
    queryDesc.Count = ScreenTimestampCount;
    Check(md3dDevice->CreateQueryHeap(&queryDesc, IID_PPV_ARGS(&mTimestampHeap)), "Timestamp heap creation failed.");
    mTimestampBuffer = CreateBuffer(md3dDevice.Get(), queryDesc.Count * sizeof(UINT64), D3D12_HEAP_TYPE_READBACK, D3D12_RESOURCE_STATE_COPY_DEST);
    mCommandQueue->GetTimestampFrequency(&mTimestampFrequency);

    if (mSettings.Automated()) {
        const D3D12_RESOURCE_DESC backBufferDesc = mRenderTargets[0]->GetDesc();
        UINT64 captureSize = 0;
        md3dDevice->GetCopyableFootprints(&backBufferDesc, 0, 1, 0, &mCaptureFootprint, nullptr, nullptr, &captureSize);
        mCaptureBuffer = CreateBuffer(md3dDevice.Get(), captureSize, D3D12_HEAP_TYPE_READBACK, D3D12_RESOURCE_STATE_COPY_DEST);
    }

    // Index buffer, built once for the face and every ring: the vertices move, the topology never does.
    // Each ring joins the previous one vertex to vertex, so the mesh has no seam. Drawing fewer rings
    // just means drawing fewer indices.
    const UINT n = FaceCells;
    std::vector<UINT> indices;
    indices.reserve(6 * (n * n + MaxRings * RingVertexCount));
    for (UINT y = 0; y < n; ++y) {
        for (UINT x = 0; x < n; ++x) {
            const UINT v0 = y * (n + 1) + x, v1 = v0 + 1, v2 = v0 + n + 1, v3 = v2 + 1;
            indices.insert(indices.end(), { v0, v2, v1, v2, v3, v1 });
        }
    }
    auto ringVertex = [&](UINT ring, UINT b) {
        b %= RingVertexCount;
        return ring == 0 ? FaceBorderVertex(b, n) : FaceVertexCount + (ring - 1) * RingVertexCount + b;
    };
    for (UINT ring = 1; ring <= MaxRings; ++ring) {
        for (UINT b = 0; b < RingVertexCount; ++b) {
            const UINT inner0 = ringVertex(ring - 1, b), inner1 = ringVertex(ring - 1, b + 1);
            const UINT outer0 = ringVertex(ring, b), outer1 = ringVertex(ring, b + 1);
            indices.insert(indices.end(), { inner0, outer0, outer1, inner0, outer1, inner1 });
        }
    }
    const UINT64 indexBufferSize = sizeof(UINT) * indices.size();
    mIndexBuffer = CreateBuffer(md3dDevice.Get(), indexBufferSize, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON);
    ComPtr<ID3D12Resource> indexUpload = CreateBuffer(md3dDevice.Get(), indexBufferSize, D3D12_HEAP_TYPE_UPLOAD,
        D3D12_RESOURCE_STATE_GENERIC_READ);
    void* mapped = nullptr;
    indexUpload->Map(0, &noRead, &mapped);
    memcpy(mapped, indices.data(), indexBufferSize);
    indexUpload->Unmap(0, nullptr);

    // The shapes, uploaded with the index buffer.
    auto upload = [&](ComPtr<ID3D12Resource>& buffer, const void* data, UINT64 size) {
        buffer = CreateBuffer(md3dDevice.Get(), size, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON);
        ComPtr<ID3D12Resource> staging = CreateBuffer(md3dDevice.Get(), size, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
        void* bytes = nullptr;
        staging->Map(0, &noRead, &bytes);
        memcpy(bytes, data, size_t(size));
        staging->Unmap(0, nullptr);
        return staging;
    };
    const ComPtr<ID3D12Resource> shapeVertexUpload = upload(mShapeVertices, shapeVertices.data(), sizeof(ShapeVertex) * shapeVertices.size());
    const ComPtr<ID3D12Resource> shapeIndexUpload = upload(mShapeIndices, shapeIndices.data(), sizeof(UINT) * shapeIndices.size());
    mShapeIndexView = { mShapeIndices->GetGPUVirtualAddress(), UINT(sizeof(UINT) * shapeIndices.size()), DXGI_FORMAT_R32_UINT };

    mCommandAllocator->Reset();
    mCommandList->Reset(mCommandAllocator.Get(), nullptr);
    mCommandList->CopyResource(mIndexBuffer.Get(), indexUpload.Get());
    mCommandList->CopyResource(mShapeVertices.Get(), shapeVertexUpload.Get());
    mCommandList->CopyResource(mShapeIndices.Get(), shapeIndexUpload.Get());
    // The selected ship's cooked package, found above the executable (ShipProfiles.h).
    const std::wstring shipPack = FindAbove(mShip.Profile().packPath);
    if (!shipPack.empty()) mShip.Load(shipPack);
    mShip.Initialize(md3dDevice.Get(), mCommandList.Get(), mSrvHeap.Get(), ShipSrv, mClientWidth, mClientHeight, HdrFormat, SunFormat);
    mCity.Initialize(md3dDevice.Get(),mCommandList.Get(),mSrvHeap.Get(),CitySrv,mSettings.cityAssets,mSettings.seed,HdrFormat,SunFormat);
    if (!mShip.Ready()) mView = View::Free;
    // The plants' catalogue (docs/arbustes-climatiques.md): MYPLANETENGINE_FOLIAGE_ASSETS; else the first built one above
    // the executable, the repository's, then the one shared beside the repositories, `plantes`, which tools\plantes.ps1
    // publishes and every worktree finds, as the scans. Without it, no plant at all: the planet bare, the title says why.
    std::wstring catalogue = mSettings.foliageAssets;
    if (catalogue.empty()) {
        const std::wstring game=FindAbove(L"assets\\foliage\\game_biomes_v1\\biomes.txt");
        if (!game.empty()) {
            const auto root=game.substr(0,game.size()-std::wstring(L"\\biomes.txt").size());
            if (GetFileAttributesW((root+L"\\game_fir\\mesh.bin").c_str())!=INVALID_FILE_ATTRIBUTES) catalogue=root;
        }
    }
    if (catalogue.empty()) {
        const std::wstring biomes=FindAbove(L"assets\\foliage\\biomes_v1\\biomes.txt");
        if (!biomes.empty()) {
            const auto root=biomes.substr(0,biomes.size()-std::wstring(L"\\biomes.txt").size());
            if (GetFileAttributesW((root+L"\\game_fir\\mesh.bin").c_str())!=INVALID_FILE_ATTRIBUTES) catalogue=root;
        }
    }
    if (catalogue.empty()) {
        const std::wstring built = FindAbove(L"assets\\foliage\\climate_shrubs_v2\\game_fir\\mesh.bin");
        catalogue = !built.empty() ? built.substr(0, built.size() - std::wstring(L"\\game_fir\\mesh.bin").size())
                                   : FindAbove(L"plantes\\climate_shrubs_v2");
    }
    if (catalogue.empty()) catalogue = L"assets\\foliage\\climate_shrubs_v2";
    try {
        mPlanetFoliage.Initialize(md3dDevice.Get(), mCommandList.Get(), catalogue, HdrFormat, SunFormat, DXGI_FORMAT_D32_FLOAT,
            CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(), PlanetImpostorSrv,
                md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)),
            GpuDescriptor(PlanetImpostorSrv),mSettings.foliageTestLod);
    } catch (const std::exception& e) {
        wchar_t reason[512] = {};
        MultiByteToWideChar(CP_UTF8, 0, e.what(), -1, reason, _countof(reason));
        mLabel += (mLabel.empty() ? L"" : L" | ") + (L"v\u00E9g\u00E9tation absente : " + std::wstring(reason));
    }
    if (mPlanetFoliage.Enabled()) {
        mPlanetPlantPlacement.Initialize(md3dDevice.Get(), mObjectRootSignature.Get());
        if (FoliageHiZ::DescriptorCount(mClientWidth, mClientHeight) > 32) throw std::runtime_error("Hi-Z descriptor reservation exceeded.");
        mFoliageHiZ.Initialize(md3dDevice.Get(), mClientWidth, mClientHeight, mDepthStencilBuffer.Get(),
            CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(), FoliageHiZSrv,
                md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)), GpuDescriptor(FoliageHiZSrv));
    }

    // Atmosphere tables, once: they depend only on the atmosphere's settings. Each reads the previous ones.
    ID3D12DescriptorHeap* heaps[] = { mSrvHeap.Get() };
    mCommandList->SetDescriptorHeaps(1, heaps);
    mCommandList->SetComputeRootSignature(lutRootSignature.Get());
    mCommandList->SetComputeRootDescriptorTable(0, gpuDescriptor(LutSrv));
    mCommandList->SetComputeRootDescriptorTable(1, gpuDescriptor(LutUav));
    for (UINT i = 0; i < 3; ++i) {
        mCommandList->SetPipelineState(lutPSOs[i].Get());
        mCommandList->Dispatch((kLutSizes[i][0] + 7) / 8, (kLutSizes[i][1] + 7) / 8, kLutGroundSlices);
        auto toRead = CD3DX12_RESOURCE_BARRIER::Transition(mAtmosphereLuts[i].Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
        mCommandList->ResourceBarrier(1, &toRead);
    }

    // Close-up materials, once: mip 0 from the recipes, then each mip from the previous one.
    mCommandList->SetComputeRootSignature(generatorRootSignature.Get());
    mCommandList->SetPipelineState(generatorPSO.Get());
    for (UINT m = 0; m < MaterialMips; ++m) {
        const UINT constants[2] = { m, MaterialSize >> m };
        mCommandList->SetComputeRoot32BitConstants(0, 2, constants, 0);
        mCommandList->SetComputeRootDescriptorTable(1, gpuDescriptor(MaterialUav + 2 * m));
        mCommandList->SetComputeRootDescriptorTable(2, gpuDescriptor(MaterialUav + 2 * (m > 0 ? m - 1 : 0)));
        mCommandList->Dispatch((constants[1] + 7) / 8, (constants[1] + 7) / 8, MaterialCount);
        const CD3DX12_RESOURCE_BARRIER mipDone[2] = { CD3DX12_RESOURCE_BARRIER::UAV(mMaterials[0].Get()),
                                                      CD3DX12_RESOURCE_BARRIER::UAV(mMaterials[1].Get()) };
        mCommandList->ResourceBarrier(2, mipDone);
    }
    // Then the scans over their generated slices (docs/log/spec-hybride-scans.md); a scan missing leaves its generated tile.
    const CD3DX12_RESOURCE_BARRIER materialsToCopy[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mMaterials[0].Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_COPY_DEST),
        CD3DX12_RESOURCE_BARRIER::Transition(mMaterials[1].Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_COPY_DEST) };
    mCommandList->ResourceBarrier(2, materialsToCopy);
    std::vector<ComPtr<ID3D12Resource>> scanUploads;
    ID3D12Resource* const materials[2] = { mMaterials[0].Get(), mMaterials[1].Get() };
    const std::wstring missing = LoadScans(md3dDevice.Get(), mCommandList.Get(), materials, MaterialSize, MaterialMips,
        mSettings.scans, scanUploads);
    if (!missing.empty()) mLabel += (mLabel.empty() ? L"" : L" | ") + (L"scans absents : " + missing);
    const CD3DX12_RESOURCE_BARRIER materialsToRead[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mMaterials[0].Get(), D3D12_RESOURCE_STATE_COPY_DEST,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mMaterials[1].Get(), D3D12_RESOURCE_STATE_COPY_DEST,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE) };
    mCommandList->ResourceBarrier(2, materialsToRead);
    // The clouds' textures, found above the executable as the ship is.
    const std::wstring cloudAssets = FindAbove(L"assets\\clouds");
    if (cloudAssets.empty()) throw std::runtime_error("The clouds' textures are missing: assets/clouds.");
    std::vector<ComPtr<ID3D12Resource>> cloudUploads;
    for(unsigned i=0;i<Celestial::MoonCount;++i) {
        const std::string name=Celestial::Moons[i].atlas;
        const auto path=FindAbove((L"assets\\celestial\\"+std::wstring(name.begin(),name.end())).c_str());
        ComPtr<ID3DBlob> bytes;
        Check(D3DReadFileToBlob(path.c_str(),&bytes),"Airless proxy missing: run tools/prepare_airless.ps1.");
        const auto expected=Celestial::AtlasHeader(Celestial::Moons[i]);
        if(bytes->GetBufferSize()!=sizeof(expected)+Celestial::AirlessAtlasBytes ||
            std::memcmp(bytes->GetBufferPointer(),&expected,sizeof(expected))!=0)
            throw std::runtime_error("Airless proxy does not match its body manifest; run tools/prepare_airless.ps1.");
        const auto begin=static_cast<const uint8_t*>(bytes->GetBufferPointer())+sizeof(expected);
        UploadCloudMap(md3dDevice.Get(),mCommandList.Get(),std::vector<uint8_t>(begin,begin+Celestial::AirlessAtlasBytes),2048,1024,12,mAirlessMaterial[i].Get(),cloudUploads);
        const auto ready=CD3DX12_RESOURCE_BARRIER::Transition(mAirlessMaterial[i].Get(),D3D12_RESOURCE_STATE_COPY_DEST,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
        mCommandList->ResourceBarrier(1,&ready);
    }
    UploadCloudVolume(md3dDevice.Get(), mCommandList.Get(), cloudAssets + L"\\shape128.rgba8mips", 128u, 8u, mCloudShape.Get(), cloudUploads, true);
    UploadCloudVolume(md3dDevice.Get(), mCommandList.Get(), cloudAssets + L"\\detail32.rgba8mips", 32u, 6u, mCloudDetail.Get(), cloudUploads, true);
    UploadCloudVolume(md3dDevice.Get(), mCommandList.Get(), cloudAssets + L"\\weather64.rgba8mips", 64u, 7u, mCloudProfiles.Get(), cloudUploads, false, true);
    // Their weather map comes from the climate (CreateClimateMap).
    const CD3DX12_RESOURCE_BARRIER cloudsToRead[3] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mCloudShape.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mCloudDetail.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mCloudProfiles.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE) };
    mCommandList->ResourceBarrier(3, cloudsToRead);
    mCommandList->Close();
    ID3D12CommandList* lists[] = { mCommandList.Get() };
    mCommandQueue->ExecuteCommandLists(1, lists);
    WaitForPreviousFrame();
    mShip.ReleaseUploads();
    mCity.ReleaseUploads();
    mPlanetFoliage.ReleaseUploads();

    mOcean=std::make_unique<Ocean>();
    mOcean->Initialize(md3dDevice.Get(),mSrvHeap.Get(),OceanSrv);
    mOcean->SetWind(mOceanSpeed,mOceanDirection,mOceanSwell);
    mIndexBufferView.BufferLocation = mIndexBuffer->GetGPUVirtualAddress();
    mIndexBufferView.SizeInBytes = static_cast<UINT>(indexBufferSize);
    mIndexBufferView.Format = DXGI_FORMAT_R32_UINT;
    // The relief reads the tectonic map and the erosion's, the planet map with them. The erosion's form pass is compiled
    // while the tectonic map is computed: neither depends on the other.
    std::future<ComPtr<ID3D12PipelineState>> erosionForm = std::async(std::launch::async, [this] {
        ComPtr<ID3DBlob> shader = LoadShader(L"ErosionForm.cso");
        D3D12_COMPUTE_PIPELINE_STATE_DESC psoDesc = {};
        psoDesc.pRootSignature = mComputeRootSignature.Get();
        psoDesc.CS = CD3DX12_SHADER_BYTECODE(shader.Get());
        ComPtr<ID3D12PipelineState> pso;
        Check(md3dDevice->CreateComputePipelineState(&psoDesc, IID_PPV_ARGS(&pso)), "Erosion form PSO creation failed.");
        return pso;
    });
    const Tectonics::Map tectonics = CreateTectonicMap();
    CreateErosionMap(tectonics, erosionForm.get().Get());
    if (!mSettings.cityProbe.empty()) { ExportCityGround(GpuDescriptor(TectonicSrv)); PostQuitMessage(0); return true; }
    InitCine(GpuDescriptor(TectonicSrv));
    CreatePlanetMap();
    InitializeWorld(GpuDescriptor(TectonicSrv),GpuDescriptor(PlanetMapSrv),GpuDescriptor(CloudSrv),GpuDescriptor(MaterialSrv));
    InitializeFlightContact();
    return true;
}

// The planet map (PlanetMap.h, PlanetMap.hlsli), once: the relief's elevation on the GPU, read back, drained on the
// CPU, uploaded as a cube map with its mips. MYPLANETENGINE_MAP=<file> also saves there the elevation, the filled
// surface, the drained area and the receivers, four arrays of PlanetMap::Cells, and the times in <file>.txt
// (tools/banc_carte.py).
void D3DApp::CreatePlanetMap() {
    ComPtr<ID3DBlob> shader = LoadShader(L"PlanetMap.cso");
    D3D12_COMPUTE_PIPELINE_STATE_DESC psoDesc = {};
    psoDesc.pRootSignature = mComputeRootSignature.Get();
    psoDesc.CS = CD3DX12_SHADER_BYTECODE(shader.Get());
    ComPtr<ID3D12PipelineState> pso;
    Check(md3dDevice->CreateComputePipelineState(&psoDesc, IID_PPV_ARGS(&pso)), "Planet map PSO creation failed.");
    const UINT64 bytes = sizeof(float) * PlanetMap::Cells;
    ComPtr<ID3D12Resource> elevation = CreateBuffer(md3dDevice.Get(), bytes, D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    ComPtr<ID3D12Resource> readback = CreateBuffer(md3dDevice.Get(), bytes, D3D12_HEAP_TYPE_READBACK, D3D12_RESOURCE_STATE_COPY_DEST);
    LARGE_INTEGER t0, t1, tDrain, t2, t3;
    QueryPerformanceCounter(&t0);
    mCommandAllocator->Reset();
    mCommandList->Reset(mCommandAllocator.Get(), pso.Get());
    auto toWrite = CD3DX12_RESOURCE_BARRIER::Transition(elevation.Get(), D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    mCommandList->ResourceBarrier(1, &toWrite);
    ID3D12DescriptorHeap* heaps[] = { mSrvHeap.Get() };
    mCommandList->SetDescriptorHeaps(1, heaps);
    mCommandList->SetComputeRootSignature(mComputeRootSignature.Get());
    mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(1, elevation->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(2, GpuDescriptor(TectonicSrv));
    mCommandList->Dispatch(PlanetMap::Size * PlanetMap::Size / 64, 6, 1);
    auto toCopy = CD3DX12_RESOURCE_BARRIER::Transition(elevation.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_COPY_SOURCE);
    mCommandList->ResourceBarrier(1, &toCopy);
    mCommandList->CopyResource(readback.Get(), elevation.Get());
    mCommandList->Close();
    ID3D12CommandList* lists[] = { mCommandList.Get() };
    mCommandQueue->ExecuteCommandLists(1, lists);
    WaitForPreviousFrame();
    QueryPerformanceCounter(&t1);

    std::vector<float> e(PlanetMap::Cells);
    void* mapped = nullptr;
    CD3DX12_RANGE readRange(0, bytes), noWrite(0, 0);
    Check(readback->Map(0, &readRange, &mapped), "Planet map readback failed.");
    memcpy(e.data(), mapped, bytes);
    readback->Unmap(0, &noWrite);
    const PlanetMap::Drainage drainage = PlanetMap::Drain(e);
    QueryPerformanceCounter(&tDrain);
    const std::vector<uint16_t> texels = PlanetMap::Texels(e, drainage);
    QueryPerformanceCounter(&t2);

    const UINT subresources = 6 * PlanetMap::Mips;
    CD3DX12_HEAP_PROPERTIES defaultHeap(D3D12_HEAP_TYPE_DEFAULT);
    CD3DX12_RESOURCE_DESC mapDesc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R16G16B16A16_FLOAT, PlanetMap::Size,
        PlanetMap::Size, 6, PlanetMap::Mips);
    Check(md3dDevice->CreateCommittedResource(&defaultHeap, D3D12_HEAP_FLAG_NONE, &mapDesc, D3D12_RESOURCE_STATE_COPY_DEST,
        nullptr, IID_PPV_ARGS(&mPlanetMap)), "Planet map creation failed.");
    ComPtr<ID3D12Resource> upload = CreateBuffer(md3dDevice.Get(), GetRequiredIntermediateSize(mPlanetMap.Get(), 0, subresources),
        D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    std::vector<D3D12_SUBRESOURCE_DATA> data(subresources);
    size_t at = 0;
    for (UINT face = 0; face < 6; ++face)
        for (UINT mip = 0; mip < PlanetMap::Mips; ++mip) {
            const UINT n = PlanetMap::Size >> mip;
            data[mip + face * PlanetMap::Mips] = { &texels[at], LONG_PTR(n) * 8, LONG_PTR(n) * n * 8 };
            at += size_t(n) * n * 4;
        }
    mCommandAllocator->Reset();
    mCommandList->Reset(mCommandAllocator.Get(), nullptr);
    UpdateSubresources(mCommandList.Get(), mPlanetMap.Get(), upload.Get(), 0, 0, subresources, data.data());
    auto toRead = CD3DX12_RESOURCE_BARRIER::Transition(mPlanetMap.Get(), D3D12_RESOURCE_STATE_COPY_DEST,
        D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    mCommandList->ResourceBarrier(1, &toRead);
    mCommandList->Close();
    mCommandQueue->ExecuteCommandLists(1, lists);
    WaitForPreviousFrame();
    D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
    srv.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
    srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURECUBE;
    srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.TextureCube.MipLevels = PlanetMap::Mips;
    md3dDevice->CreateShaderResourceView(mPlanetMap.Get(), &srv, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
        PlanetMapSrv, md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)));
    QueryPerformanceCounter(&t3);

    const std::wstring& path = mSettings.map;
    if (path.empty()) return;
    FILE* f = nullptr;
    if (_wfopen_s(&f, path.c_str(), L"wb") == 0 && f) {
        fwrite(e.data(), sizeof(float), e.size(), f);
        fwrite(drainage.filled.data(), sizeof(float), e.size(), f);
        fwrite(drainage.area.data(), sizeof(float), e.size(), f);
        fwrite(drainage.receiver.data(), sizeof(uint32_t), e.size(), f);
        fclose(f);
    }
    auto ms = [&](LARGE_INTEGER a, LARGE_INTEGER b) { return 1000.0 * double(b.QuadPart - a.QuadPart) / mFrequency.QuadPart; };
    if (_wfopen_s(&f, (path + L".txt").c_str(), L"w") == 0 && f) {
        fprintf(f, "gpu %.1f ms\ndrain %.1f ms\ntexels %.1f ms\nupload %.1f ms\ntexture %.1f MB\n", ms(t0, t1),
                ms(t1, tDrain), ms(tDrain, t2), ms(t2, t3),
                texels.size() * 2.0 / (1024.0 * 1024.0));
        fclose(f);
    }
}

// The tectonic map (Tectonics.h, Tectonics.hlsli), once, before the planet map: the planet's continents, plates and fields
// computed on the CPU, the relief's slices uploaded as a texture array, the views' slice as another at a quarter of the
// resolution; every slice saved beside the executable for the relief's CPU port and the level 0 (tools/hydro/cp.py),
// tectonique-<seed>.bin. The volcanoes and their index as two buffers, saved beside it too, volcans-<seed>.bin. Its time
// and its size on the GPU go to the title. The planet's seed is PLANET_SEED (PlanetSettings.hlsli).
Tectonics::Map D3DApp::CreateTectonicMap() {
    const uint32_t seed = mSettings.seed;
    const Tectonics::Map map = Tectonics::Build({ seed, PlanetRadius / 1000.0 });
    mTectonicMs = map.ms;
    wchar_t exePath[MAX_PATH] = {};
    GetModuleFileNameW(nullptr, exePath, MAX_PATH);
    std::wstring cache(exePath);
    cache = cache.substr(0, cache.find_last_of(L"\\/") + 1) + L"tectonique-" + std::to_wstring(seed) + L".bin";
    Tectonics::Save(map, seed, cache);
    Tectonics::SaveVolcanoes(map, seed, cache.substr(0, cache.find_last_of(L"\\/") + 1) + L"volcans-" + std::to_wstring(seed) + L".bin");
    const UINT width = map.size + 2 * Tectonics::Pad, viewWidth = map.size / Tectonics::ViewScale + 2 * Tectonics::ViewPad;
    const UINT layers = 6 * Tectonics::ReliefSlices;
    CD3DX12_HEAP_PROPERTIES defaultHeap(D3D12_HEAP_TYPE_DEFAULT);
    auto create = [&](UINT w, UINT count, ComPtr<ID3D12Resource>& texture) {
        CD3DX12_RESOURCE_DESC desc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R16G16B16A16_FLOAT, w, w, UINT16(count), 1);
        Check(md3dDevice->CreateCommittedResource(&defaultHeap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_COPY_DEST,
            nullptr, IID_PPV_ARGS(&texture)), "Tectonic map creation failed.");
    };
    create(width, layers, mTectonicMap);
    create(viewWidth, 6, mTectonicViews);
    const UINT64 volcanoBytes = std::max<size_t>(map.volcanoes.size(), 1) * sizeof(Tectonics::Volcano), indexBytes = map.volcanoIndex.size() * 4;
    mVolcanoes = CreateBuffer(md3dDevice.Get(), volcanoBytes, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COPY_DEST);
    mVolcanoIndex = CreateBuffer(md3dDevice.Get(), indexBytes, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COPY_DEST);
    ComPtr<ID3D12Resource> volcanoUpload = CreateBuffer(md3dDevice.Get(), volcanoBytes + indexBytes, D3D12_HEAP_TYPE_UPLOAD,
        D3D12_RESOURCE_STATE_GENERIC_READ);
    {
        uint8_t* to = nullptr;
        volcanoUpload->Map(0, nullptr, reinterpret_cast<void**>(&to));
        memcpy(to, map.volcanoes.data(), map.volcanoes.size() * sizeof(Tectonics::Volcano));
        memcpy(to + volcanoBytes, map.volcanoIndex.data(), indexBytes);
        volcanoUpload->Unmap(0, nullptr);
    }
    mTectonicMb = ((double(width) * width * layers + double(viewWidth) * viewWidth * 6) * 8.0 + double(volcanoBytes + indexBytes)) / (1024.0 * 1024.0);
    ComPtr<ID3D12Resource> upload = CreateBuffer(md3dDevice.Get(), GetRequiredIntermediateSize(mTectonicMap.Get(), 0, layers),
        D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    ComPtr<ID3D12Resource> viewUpload = CreateBuffer(md3dDevice.Get(), GetRequiredIntermediateSize(mTectonicViews.Get(), 0, 6),
        D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    std::vector<D3D12_SUBRESOURCE_DATA> data(layers), views(6);
    for (UINT face = 0; face < 6; ++face) {
        for (UINT s = 0; s < Tectonics::ReliefSlices; ++s)
            data[face * Tectonics::ReliefSlices + s] = { &map.texels[(size_t(face) * Tectonics::Slices + s) * width * width * 4],
                                                         LONG_PTR(width) * 8, LONG_PTR(width) * width * 8 };
        views[face] = { &map.views[size_t(face) * viewWidth * viewWidth * 4], LONG_PTR(viewWidth) * 8, LONG_PTR(viewWidth) * viewWidth * 8 };
    }
    mCommandAllocator->Reset();
    mCommandList->Reset(mCommandAllocator.Get(), nullptr);
    UpdateSubresources(mCommandList.Get(), mTectonicMap.Get(), upload.Get(), 0, 0, layers, data.data());
    UpdateSubresources(mCommandList.Get(), mTectonicViews.Get(), viewUpload.Get(), 0, 0, 6, views.data());
    mCommandList->CopyBufferRegion(mVolcanoes.Get(), 0, volcanoUpload.Get(), 0, volcanoBytes);
    mCommandList->CopyBufferRegion(mVolcanoIndex.Get(), 0, volcanoUpload.Get(), volcanoBytes, indexBytes);
    ID3D12Resource* resources[4] = { mTectonicMap.Get(), mTectonicViews.Get(), mVolcanoes.Get(), mVolcanoIndex.Get() };
    D3D12_RESOURCE_BARRIER toRead[4];
    for (int k = 0; k < 4; ++k)
        toRead[k] = CD3DX12_RESOURCE_BARRIER::Transition(resources[k], D3D12_RESOURCE_STATE_COPY_DEST,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
    mCommandList->ResourceBarrier(4, toRead);
    mCommandList->Close();
    ID3D12CommandList* lists[] = { mCommandList.Get() };
    mCommandQueue->ExecuteCommandLists(1, lists);
    WaitForPreviousFrame();
    D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
    srv.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
    srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2DARRAY;
    srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.Texture2DArray.MipLevels = 1;
    srv.Texture2DArray.ArraySize = layers;
    const UINT step = md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    md3dDevice->CreateShaderResourceView(mTectonicMap.Get(), &srv, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
        TectonicSrv, step));
    srv.Texture2DArray.ArraySize = 6;
    md3dDevice->CreateShaderResourceView(mTectonicViews.Get(), &srv, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
        TectonicSrv + 1, step));
    D3D12_SHADER_RESOURCE_VIEW_DESC buffer = {};
    buffer.Format = DXGI_FORMAT_UNKNOWN;
    buffer.ViewDimension = D3D12_SRV_DIMENSION_BUFFER;
    buffer.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    buffer.Buffer.NumElements = UINT(std::max<size_t>(map.volcanoes.size(), 1));
    buffer.Buffer.StructureByteStride = sizeof(Tectonics::Volcano);
    md3dDevice->CreateShaderResourceView(mVolcanoes.Get(), &buffer, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
        TectonicSrv + 3, step));
    buffer.Buffer.NumElements = UINT(map.volcanoIndex.size());
    buffer.Buffer.StructureByteStride = 4;
    md3dDevice->CreateShaderResourceView(mVolcanoIndex.Get(), &buffer, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
        TectonicSrv + 4, step));
    mVolcanoCount = UINT(map.volcanoes.size());
    mVolcanoMs = map.volcanoMs;
    CreateClimateMap(map, seed, cache.substr(0, cache.find_last_of(L"\\/") + 1) + L"climat-" + std::to_wstring(seed) + L".bin");
    // The pre-erosion pass never reads erosion; reserve its slot until the network is ready.
    srv.Format = DXGI_FORMAT_R32G32_UINT;
    md3dDevice->CreateShaderResourceView(nullptr, &srv, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
        TectonicSrv + 5, step));
    return map;
}

// The erosion level 0: pre-erosion ground on the GPU, drainage on the CPU, uploaded at t23. When the cache is stale, step
// B's courses are then measured on the GPU where they are drawn, their sinuosity (ErosionNodes.hlsl) and the relief they
// cross (ErosionStages.hlsl), their stages conditioned on the CPU (Erosion::Condition) and the map uploaded again.
void D3DApp::CreateErosionMap(const Tectonics::Map& tectonics, ID3D12PipelineState* pso) {
    LARGE_INTEGER t0, t1, tc = {};
    QueryPerformanceCounter(&t0);
    const uint32_t seed = mSettings.seed, n = tectonics.size, cells = 6 * n * n;
    const UINT64 bytes = sizeof(Erosion::Course) * cells; // the largest pass's
    ComPtr<ID3D12Resource> target = CreateBuffer(md3dDevice.Get(), bytes, D3D12_HEAP_TYPE_DEFAULT,
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    ComPtr<ID3D12Resource> readback = CreateBuffer(md3dDevice.Get(), bytes, D3D12_HEAP_TYPE_READBACK, D3D12_RESOURCE_STATE_COPY_DEST);
    ID3D12CommandList* lists[] = { mCommandList.Get() };
    // One pass over the cells into `target`, read back into `out`; buffers decay to COMMON after each execution.
    auto run = [&](ID3D12PipelineState* pass, void* out, UINT64 size) {
        mCommandAllocator->Reset();
        mCommandList->Reset(mCommandAllocator.Get(), pass);
        auto toWrite = CD3DX12_RESOURCE_BARRIER::Transition(target.Get(), D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        mCommandList->ResourceBarrier(1, &toWrite);
        ID3D12DescriptorHeap* heaps[] = { mSrvHeap.Get() };
        mCommandList->SetDescriptorHeaps(1, heaps);
        mCommandList->SetComputeRootSignature(mComputeRootSignature.Get());
        mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
        mCommandList->SetComputeRootUnorderedAccessView(1, target->GetGPUVirtualAddress());
        mCommandList->SetComputeRootDescriptorTable(2, GpuDescriptor(TectonicSrv));
        mCommandList->Dispatch(n * n / 64, 6, 1);
        auto toCopy = CD3DX12_RESOURCE_BARRIER::Transition(target.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_COPY_SOURCE);
        mCommandList->ResourceBarrier(1, &toCopy);
        mCommandList->CopyBufferRegion(readback.Get(), 0, target.Get(), 0, size);
        mCommandList->Close();
        mCommandQueue->ExecuteCommandLists(1, lists);
        WaitForPreviousFrame();
        void* mapped = nullptr;
        CD3DX12_RANGE readRange(0, size), noWrite(0, 0);
        Check(readback->Map(0, &readRange, &mapped), "Erosion readback failed.");
        memcpy(out, mapped, size);
        readback->Unmap(0, &noWrite);
    };
    mErosionSize = n;
    auto courseView = [&](ID3D12Resource* resource, UINT elements) {
        D3D12_SHADER_RESOURCE_VIEW_DESC view = {};
        view.Format = DXGI_FORMAT_UNKNOWN;
        view.ViewDimension = D3D12_SRV_DIMENSION_BUFFER;
        view.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        view.Buffer.NumElements = elements;
        view.Buffer.StructureByteStride = ErosionCourseBytes;
        md3dDevice->CreateShaderResourceView(resource, &view, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
            TectonicSrv + 6, md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)));
    };
    courseView(nullptr, 1);
    std::vector<float> e(cells);
    run(pso, e.data(), sizeof(float) * cells);

    // Step B's passes: their compiled code is in the cache's key, as their settings are.
    auto compute = [&](ID3DBlob* shader) {
        D3D12_COMPUTE_PIPELINE_STATE_DESC psoDesc = {};
        psoDesc.pRootSignature = mComputeRootSignature.Get();
        psoDesc.CS = CD3DX12_SHADER_BYTECODE(shader);
        ComPtr<ID3D12PipelineState> pass;
        Check(md3dDevice->CreateComputePipelineState(&psoDesc, IID_PPV_ARGS(&pass)), "Erosion pass PSO creation failed.");
        return pass;
    };
    const ComPtr<ID3DBlob> nodesShader = LoadShader(L"ErosionNodes.cso"), stagesShader = LoadShader(L"ErosionStages.cso");
    const ComPtr<ID3DBlob> contactsShader = LoadShader(L"ErosionContacts.cso");
    uint64_t passes = 0xcbf29ce484222325ull; // FNV-1a over the three startup shaders
    for (ID3DBlob* blob : { nodesShader.Get(), stagesShader.Get(), contactsShader.Get() })
        for (size_t i = 0; i < blob->GetBufferSize(); ++i)
            passes = (passes ^ static_cast<const uint8_t*>(blob->GetBufferPointer())[i]) * 0x100000001b3ull;

    // The network from the cache when the form, climate, seed, executable's time and passes agree; else computed.
    wchar_t exePath[MAX_PATH] = {};
    GetModuleFileNameW(nullptr, exePath, MAX_PATH);
    WIN32_FILE_ATTRIBUTE_DATA exeInfo = {};
    GetFileAttributesExW(exePath, GetFileExInfoStandard, &exeInfo);
    const uint64_t key = Erosion::Key(e, mClimateCpu, seed,
        uint64_t(exeInfo.ftLastWriteTime.dwHighDateTime) << 32 | exeInfo.ftLastWriteTime.dwLowDateTime, passes);
    std::wstring cache(exePath);
    cache = cache.substr(0, cache.find_last_of(L"\\/") + 1) + L"erosion-" + std::to_wstring(seed) + L".bin";
    Erosion::Map map;
    const bool cached = Erosion::Load(map, key, cache);
    std::vector<uint32_t> nodes;
    mErosionCoursesMs = 0.0;
    if (!cached) {
        map = Erosion::Build(tectonics, mClimateCpu, e, PlanetRadius / 1000.0);
        QueryPerformanceCounter(&tc);
        nodes.resize(2 * size_t(cells));
        run(compute(nodesShader.Get()).Get(), nodes.data(), sizeof(uint32_t) * nodes.size());
        Erosion::SetSinuosity(map, nodes);
    }
    mErosionBuildMs = map.ms;

    // The physical cache retains its 24 slices. Six GPU-only slices hold exact 8x8 activity masks, six the node bounds,
    // six the rivers' map for wide footprints (ErosionRiverMap.hlsl). They share t23 in every terrain consumer.
    const UINT gpuSlices = Erosion::Slices + 18;
    std::vector<uint32_t> activity(size_t(cells) * 2, 0u);
    std::vector<uint32_t> eligible(size_t(cells) * 2, 0u);
    std::vector<uint32_t> rivers(size_t(cells) * 2, 0u);
    // The map at t23: created once, uploaded again once the stages are conditioned.
    CD3DX12_HEAP_PROPERTIES defaultHeap(D3D12_HEAP_TYPE_DEFAULT);
    CD3DX12_RESOURCE_DESC desc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R32G32_UINT, n, n, gpuSlices, 1);
    Check(md3dDevice->CreateCommittedResource(&defaultHeap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_COPY_DEST,
        nullptr, IID_PPV_ARGS(&mErosionMap)), "Erosion map creation failed.");
    mErosionMb = double(cells) * 56.0 / (1024.0 * 1024.0);
    ComPtr<ID3D12Resource> upload = CreateBuffer(md3dDevice.Get(), GetRequiredIntermediateSize(mErosionMap.Get(), 0, gpuSlices),
        D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    const D3D12_RESOURCE_STATES readable = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;
    bool uploaded = false;
    auto send = [&]() {
        std::vector<D3D12_SUBRESOURCE_DATA> data(gpuSlices);
        for (UINT face = 0; face < Erosion::Slices; ++face)
            data[face] = { &map.texels[size_t(face) * n * n * 2], LONG_PTR(n) * 8, LONG_PTR(n) * n * 8 };
        for (UINT face = 0; face < 6; ++face)
            data[Erosion::Slices + face] = { &activity[size_t(face) * n * n * 2], LONG_PTR(n) * 8, LONG_PTR(n) * n * 8 };
        for (UINT face = 0; face < 6; ++face)
            data[Erosion::Slices + 6 + face] = { &eligible[size_t(face) * n * n * 2], LONG_PTR(n) * 8, LONG_PTR(n) * n * 8 };
        for (UINT face = 0; face < 6; ++face)
            data[Erosion::Slices + 12 + face] = { &rivers[size_t(face) * n * n * 2], LONG_PTR(n) * 8, LONG_PTR(n) * n * 8 };
        mCommandAllocator->Reset();
        mCommandList->Reset(mCommandAllocator.Get(), nullptr);
        if (uploaded) {
            auto toCopy = CD3DX12_RESOURCE_BARRIER::Transition(mErosionMap.Get(), readable, D3D12_RESOURCE_STATE_COPY_DEST);
            mCommandList->ResourceBarrier(1, &toCopy);
        }
        UpdateSubresources(mCommandList.Get(), mErosionMap.Get(), upload.Get(), 0, 0, gpuSlices, data.data());
        auto toRead = CD3DX12_RESOURCE_BARRIER::Transition(mErosionMap.Get(), D3D12_RESOURCE_STATE_COPY_DEST, readable);
        mCommandList->ResourceBarrier(1, &toRead);
        mCommandList->Close();
        mCommandQueue->ExecuteCommandLists(1, lists);
        WaitForPreviousFrame();
        uploaded = true;
    };
    send();
    D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
    srv.Format = DXGI_FORMAT_R32G32_UINT;
    srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2DARRAY;
    srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.Texture2DArray.MipLevels = 1;
    srv.Texture2DArray.ArraySize = gpuSlices;
    md3dDevice->CreateShaderResourceView(mErosionMap.Get(), &srv, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
        TectonicSrv + 5, md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)));
    if (!cached) {
        std::vector<Erosion::Course> courses(cells);
        run(compute(stagesShader.Get()).Get(), courses.data(), sizeof(Erosion::Course) * cells);
        Erosion::Condition(map, courses, nodes);
        send();
        std::vector<Erosion::Contacts> contacts(cells);
        run(compute(contactsShader.Get()).Get(), contacts.data(), sizeof(Erosion::Contacts) * cells);
        Erosion::StopAtWater(map, contacts, courses);
        send();
        LARGE_INTEGER td;
        QueryPerformanceCounter(&td);
        mErosionCoursesMs = 1000.0 * double(td.QuadPart - tc.QuadPart) / mFrequency.QuadPart;
        Erosion::Save(map, seed, key, cache);
    }
    if (n >= 8 && n % 8 == 0) {
        const ComPtr<ID3DBlob> activityShader = LoadShader(L"ErosionActivity.cso");
        run(compute(activityShader.Get()).Get(), eligible.data(), sizeof(uint32_t) * eligible.size());
        // Each eligible node's courses, numbered: its main course, then its connectors (ErosionCourseBuild.hlsl).
        uint32_t courseCount = 0;
        for (size_t c = 0; c < cells; ++c)
            if (eligible[2 * c] & 1u) {
                const uint32_t connectors = eligible[2 * c] >> 1;
                eligible[2 * c] = 1u | courseCount << 1;
                courseCount += 1 + connectors;
            }
        // The word keeps 18 bits for its first course (Erosion.hlsli, EROSION_FIRST_MASK).
        if (courseCount > 0x3ffffu) throw std::runtime_error("Too many river courses for the node words.");
        activity = eligible;
        send();
        {
            mErosionCourses = CreateBuffer(md3dDevice.Get(), UINT64(std::max(courseCount, 1u)) * ErosionCourseBytes,
                D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
            const ComPtr<ID3DBlob> courseShader = LoadShader(L"ErosionCourseBuild.cso");
            const ComPtr<ID3D12PipelineState> coursePass = compute(courseShader.Get());
            mCommandAllocator->Reset();
            mCommandList->Reset(mCommandAllocator.Get(), coursePass.Get());
            auto toWrite = CD3DX12_RESOURCE_BARRIER::Transition(mErosionCourses.Get(), D3D12_RESOURCE_STATE_COMMON,
                D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
            mCommandList->ResourceBarrier(1, &toWrite);
            ID3D12DescriptorHeap* heaps[] = { mSrvHeap.Get() };
            mCommandList->SetDescriptorHeaps(1, heaps);
            mCommandList->SetComputeRootSignature(mComputeRootSignature.Get());
            mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
            mCommandList->SetComputeRootUnorderedAccessView(1, mErosionCourses->GetGPUVirtualAddress());
            mCommandList->SetComputeRootDescriptorTable(2, GpuDescriptor(TectonicSrv));
            mCommandList->Dispatch(n * n / 64, 6, 1);
            auto toRead = CD3DX12_RESOURCE_BARRIER::Transition(mErosionCourses.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, readable);
            mCommandList->ResourceBarrier(1, &toRead);
            mCommandList->Close();
            mCommandQueue->ExecuteCommandLists(1, lists);
            WaitForPreviousFrame();
            courseView(mErosionCourses.Get(), std::max(courseCount, 1u));
            mErosionCourseCount = courseCount;
        }
        // Each node's word marks whether one of its courses can carry a channel: the water contour lists no other.
        const ComPtr<ID3DBlob> wetShader = LoadShader(L"ErosionCourseWet.cso");
        run(compute(wetShader.Get()).Get(), eligible.data(), sizeof(uint32_t) * eligible.size());
        const ComPtr<ID3DBlob> tilesShader = LoadShader(L"ErosionActivityTiles.cso");
        run(compute(tilesShader.Get()).Get(), activity.data(), sizeof(uint32_t) * activity.size());
        activity[2 * (size_t(n) * n - 1)] = 0x45524934u; // ERI4: original chart, conservative projected course bounds, built courses
        wchar_t activityDump[MAX_PATH] = {};
        if (GetEnvironmentVariableW(L"MYPLANETENGINE_EROSION_ACTIVITY_DUMP", activityDump, MAX_PATH)) {
            FILE* file = nullptr;
            if (_wfopen_s(&file, activityDump, L"wb") || !file) throw std::runtime_error("Cannot write erosion activity diagnostic.");
            const bool ok = fwrite(&n, sizeof(n), 1, file) == 1
                && fwrite(eligible.data(), sizeof(uint32_t), eligible.size(), file) == eligible.size()
                && fwrite(activity.data(), sizeof(uint32_t), activity.size(), file) == activity.size();
            const int closed = fclose(file);
            if (!ok || closed) throw std::runtime_error("Cannot complete erosion activity diagnostic.");
        }
        send();
    }
    // Then the rivers' map, from the complete evaluation with the index above; frames read it once it is there.
    if (n > 2 * 4) {
        LARGE_INTEGER tr0, tr1;
        QueryPerformanceCounter(&tr0);
        const ComPtr<ID3DBlob> riverShader = LoadShader(L"ErosionRiverMap.cso");
        run(compute(riverShader.Get()).Get(), rivers.data(), sizeof(uint32_t) * rivers.size());
        send();
        mErosionRiverMap = true;
        QueryPerformanceCounter(&tr1);
        mErosionRiverMapMs = 1000.0 * double(tr1.QuadPart - tr0.QuadPart) / mFrequency.QuadPart;
    }
    QueryPerformanceCounter(&t1);
    mErosionMs = 1000.0 * double(t1.QuadPart - t0.QuadPart) / mFrequency.QuadPart;
}

// The climate map (Climate.h, Climate.hlsli), once, from the tectonic map's large forms: computed on the CPU, saved beside
// the executable for the CPU port and the level 0 (tools/hydro/cp.py), uploaded as two cube maps with their mips; the
// ship's weather reads it too. Then the clouds' weather map from it (Climate::Weather), its first mip saved beside it,
// meteo-<seed>.bin. Their times and the climate's size on the GPU go to the title.
void D3DApp::CreateClimateMap(const Tectonics::Map& tectonics, uint32_t seed, const std::wstring& cache) {
    mClimateCpu = Climate::Build(tectonics, PlanetRadius / 1000.0);
    const Climate::Map& climate = mClimateCpu;
    mClimateMs = climate.ms;
    Climate::Save(climate, seed, cache);
    const auto weatherStart = std::chrono::steady_clock::now();
    std::vector<float> cyclones;
    const std::vector<uint8_t> weather = Climate::Weather(climate, tectonics, seed, PlanetRadius / 1000.0, &cyclones);
    mWeatherMapMs = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - weatherStart).count();
    const std::wstring weatherPath = cache.substr(0, cache.find_last_of(L"\\/") + 1) + L"meteo-" + std::to_wstring(seed);
    FILE* weatherFile = nullptr;
    if (_wfopen_s(&weatherFile, (weatherPath + L".bin").c_str(), L"wb") == 0 && weatherFile) {
        const uint32_t header[3] = { seed, Climate::WeatherWidth, Climate::WeatherHeight };
        fwrite("EXOMETEO", 1, 8, weatherFile);
        fwrite(header, 4, 3, weatherFile);
        fwrite(weather.data(), 1, size_t(Climate::WeatherWidth) * Climate::WeatherHeight * 4, weatherFile);
        fclose(weatherFile);
    }
    // Its cyclones, for the test views: latitude, longitude, scale (km), stage.
    if (_wfopen_s(&weatherFile, (weatherPath + L".txt").c_str(), L"w") == 0 && weatherFile) {
        for (size_t k = 0; k + 3 < cyclones.size(); k += 4)
            fprintf(weatherFile, "%.3f %.3f %.0f %.2f\n", cyclones[k], cyclones[k + 1], cyclones[k + 2], cyclones[k + 3]);
        fclose(weatherFile);
    }
    const std::vector<uint16_t> texels = Climate::Texels(climate);
    const UINT subresources = 12 * Climate::Mips;
    CD3DX12_HEAP_PROPERTIES defaultHeap(D3D12_HEAP_TYPE_DEFAULT);
    const CD3DX12_RESOURCE_DESC desc = CD3DX12_RESOURCE_DESC::Tex2D(DXGI_FORMAT_R16G16B16A16_FLOAT, Climate::Size, Climate::Size, 12,
        Climate::Mips);
    Check(md3dDevice->CreateCommittedResource(&defaultHeap, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_COPY_DEST, nullptr,
        IID_PPV_ARGS(&mClimateMap)), "Climate map creation failed.");
    mClimateMb = texels.size() * 2.0 / (1024.0 * 1024.0);
    ComPtr<ID3D12Resource> upload = CreateBuffer(md3dDevice.Get(), GetRequiredIntermediateSize(mClimateMap.Get(), 0, subresources),
        D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    std::vector<D3D12_SUBRESOURCE_DATA> data(subresources);
    size_t at = 0;
    for (UINT slice = 0; slice < 12; ++slice)
        for (UINT mip = 0; mip < Climate::Mips; ++mip) {
            const UINT n = Climate::Size >> mip;
            data[mip + slice * Climate::Mips] = { &texels[at], LONG_PTR(n) * 8, LONG_PTR(n) * n * 8 };
            at += size_t(n) * n * 4;
        }
    mCommandAllocator->Reset();
    mCommandList->Reset(mCommandAllocator.Get(), nullptr);
    UpdateSubresources(mCommandList.Get(), mClimateMap.Get(), upload.Get(), 0, 0, subresources, data.data());
    std::vector<ComPtr<ID3D12Resource>> weatherUploads;
    UploadCloudMap(md3dDevice.Get(), mCommandList.Get(), weather, Climate::WeatherWidth, Climate::WeatherHeight, Climate::WeatherMips,
        mCloudWeather.Get(), weatherUploads);
    const CD3DX12_RESOURCE_BARRIER toRead[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mClimateMap.Get(), D3D12_RESOURCE_STATE_COPY_DEST,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mCloudWeather.Get(), D3D12_RESOURCE_STATE_COPY_DEST,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE) };
    mCommandList->ResourceBarrier(2, toRead);
    mCommandList->Close();
    ID3D12CommandList* lists[] = { mCommandList.Get() };
    mCommandQueue->ExecuteCommandLists(1, lists);
    WaitForPreviousFrame();
    D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
    srv.Format = DXGI_FORMAT_R16G16B16A16_FLOAT;
    srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURECUBEARRAY;
    srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.TextureCubeArray.MipLevels = Climate::Mips;
    srv.TextureCubeArray.NumCubes = 2;
    md3dDevice->CreateShaderResourceView(mClimateMap.Get(), &srv, CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(),
        TectonicSrv + 2, md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)));
    md3dDevice->CreateShaderResourceView(mClimateMap.Get(), &srv, mShip.ClimateDescriptor());
}

void D3DApp::UpdateCamera(float dt) {
    // Keys only count when the window has the focus; the ground clamp below always applies.
    const bool focused = GetForegroundWindow() == mhMainWnd;
    auto held = [focused](UINT vk) { return focused && (GetAsyncKeyState(vk) & 0x8000) ? 1.0 : 0.0; };
    const double arrows = held(VK_RIGHT) - held(VK_LEFT);
    const bool freeLook = mCameraMode == CameraMode::Free;
    const bool rolling = freeLook && held(VK_SHIFT);
    const double forward = held(mMoveKeys[0]) + held(VK_UP) - held(mMoveKeys[1]) - held(VK_DOWN);
    const double strafe = held(mMoveKeys[3]) - held(mMoveKeys[2]) + (rolling ? 0.0 : arrows);
    const double rise = held(mMoveKeys[5]) + held(VK_PRIOR) - held(mMoveKeys[4]) - held(VK_NEXT);

    const Vec3d offset = mCamPos - mCameraCentre;
    const bool localTerrain = mCameraBody == (mActiveMoon >= 0 ? mActiveMoon : Celestial::Exolune);
    const double clearance = Length(offset) - mCameraRadius - (localTerrain ? mGroundHeight : 0.0);
    const double step = mSpeedFactor * std::max(clearance, 1.0) * dt;
    if (freeLook) {
        FlightFrame::Turn(mCamForward, mCamUp, mMouseDx * .003, mMouseDy * .003, rolling ? arrows * 1.8 * dt : 0.0);
    } else {
        mOrbitFrame.Follow(offset); // include the previous frame's accepted terrain contact
        mOrbitFrame.Look(mMouseDx * .003, mMouseDy * .003);
        mOrbitFrame.View(mCamForward, mCamUp);
    }
    mMouseDx = mMouseDy = 0;

    Vec3d newPos;
    if (mCameraMode == CameraMode::FixedAltitude) {
        const bool visualPlanet = mCameraBody >= int(Celestial::MoonCount) && mCameraBody != Celestial::Exolune;
        newPos = mCameraCentre + mOrbitFrame.MoveAtFixedAltitude(offset, forward * step, strafe * step, rise * step,
            visualPlanet ? mCameraRadius + 1.0 : 1.0);
    } else {
        const Vec3d liftAxis = freeLook ? mCamUp : mOrbitFrame.vertical;
        newPos = mCamPos + FlightFrame::ViewTravel(mCamForward, mCamUp, liftAxis, forward, strafe, rise) * step;
    }

    // Terrain contact is swept before accepting the candidate pose. Only the global sea floor is local here.
    double minRadius = PlanetRadius + (mFlightContactPSO ? 0.0 : mGroundHeight) + 1.0;
    if(mOcean && !mWaveReset && mGroundHeight<=0.0 && mSettings.tremblePath.empty())
        minRadius=std::max(minRadius,PlanetRadius+double(mOcean->SurfaceHeight())+0.75); // the ground with the materials' relief
    const double newRadius = Length(newPos);
    if (newRadius < minRadius)
        newPos = (newRadius > 0 ? newPos * (1.0 / newRadius) : Normalize(mCamPos)) * minRadius;

    mCamPos = newPos;
}

void D3DApp::ApplyLocalContacts()
{
    if (!mLocalContactsEnabled || mDiagnosticView>0.5f || mWireframe) return;
    mCommandList->SetComputeRootSignature(mLocalContactRoot.Get());
    mCommandList->SetComputeRootConstantBufferView(0,mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(1,GpuDescriptor(HdrSrv));
    mCommandList->SetComputeRootDescriptorTable(2,GpuDescriptor(ContactSrv));
    mCommandList->SetComputeRootDescriptorTable(3,GpuDescriptor(ContactUav));
    mCommandList->SetComputeRootDescriptorTable(4,GpuDescriptor(ContactHdrUav));
    mCommandList->SetPipelineState(mLocalContactPso.Get());
    mCommandList->Dispatch(((mClientWidth+1)/2+7)/8,((mClientHeight+1)/2+7)/8,1);
    constexpr auto sceneRead=D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;
    const D3D12_RESOURCE_BARRIER resolve[3]={
        CD3DX12_RESOURCE_BARRIER::Transition(mLocalContacts.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mHdrTarget.Get(),sceneRead,D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
        CD3DX12_RESOURCE_BARRIER::Transition(mSunPart.Get(),sceneRead,D3D12_RESOURCE_STATE_UNORDERED_ACCESS)};
    mCommandList->ResourceBarrier(3,resolve);
    mCommandList->SetPipelineState(mLocalContactResolvePso.Get());
    mCommandList->Dispatch((mClientWidth+7)/8,(mClientHeight+7)/8,1);
    const D3D12_RESOURCE_BARRIER ready[3]={
        CD3DX12_RESOURCE_BARRIER::Transition(mLocalContacts.Get(),D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE,D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
        CD3DX12_RESOURCE_BARRIER::Transition(mHdrTarget.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,sceneRead),
        CD3DX12_RESOURCE_BARRIER::Transition(mSunPart.Get(),D3D12_RESOURCE_STATE_UNORDERED_ACCESS,sceneRead)};
    mCommandList->ResourceBarrier(3,ready);
}

void D3DApp::Draw() {
    LARGE_INTEGER cpuMarks[5]; // the CPU's frame: start, recording, submission, present, the GPU waited for
    QueryPerformanceCounter(&cpuMarks[0]);
    ++mFrameNumber;
    const bool trembleTest = !mSettings.tremblePath.empty() && mFrameNumber > TrembleWarmup;

    // Terrain height under the camera, written by the previous frame (the CPU waits for every frame).
    FaceVertex* nadir = nullptr;
    CD3DX12_RANGE readRange(0, sizeof(FaceVertex));
    if (SUCCEEDED(mReadbackBuffer->Map(0, &readRange, reinterpret_cast<void**>(&nadir)))) {
        // A teleport invalidates the previous frame's nadir as well as the cached CPU height.
        if (!NearMoon(mCamPos) && !mMeshFrozen && !trembleTest && !mWaveReset && std::isfinite(nadir->elevation)) {
            mGroundHeight = std::max({0.0, (double)nadir->elevation, (double)nadir->water.w});
            mOceanElevation=nadir->elevation;
        }
        CD3DX12_RANGE noWrite(0, 0);
        mReadbackBuffer->Unmap(0, &noWrite);
    }

    if (!BeginBatchFrame() || !BeginCineFrame()) return;
    ReadFlightContact();
    ReadWalkGround();
    ReadWorldSound();
    if (mStartWalking) {
        mStartWalking = false; ToggleWalking();
    }

    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    const double elapsed = mLastTime.QuadPart ? double(now.QuadPart - mLastTime.QuadPart) / mFrequency.QuadPart : 0.0;
    const float dt = (float)(!mCine.empty() ? 1.0 / mCineFps : std::min(elapsed, 0.1));
    mLastTime = now;
    if (!mSettings.Automated() && !mWeatherPaused) mWeatherTime += elapsed * mWeatherRate;
    // Sun input also moves the outer planets. Resolve their positions before moving an attached camera.
    if (mView == View::Free && GetForegroundWindow() == mhMainWnd) {
        const int turn = int(GetAsyncKeyState('P') < 0) - int(GetAsyncKeyState('O') < 0);
        mSunDir = Rotate(mSunDir, kNorth, turn * 0.2 * dt);
    }
    UpdateCelestialFrame();
    mClock += dt;
    const FlightPose flightBefore=FlightPoseNow();
    if (mCine.empty()) {
        if (mView == View::Walk) UpdateWalking(dt);
        else if (mView == View::Free) UpdateCamera(dt);
        else UpdateShip(dt);
    }
    PrepareFlightContact(flightBefore);
    if (mView == View::Free && mCameraMode != CameraMode::Free) {
        mOrbitFrame.Follow(mCamPos - mCameraCentre);
        mOrbitFrame.View(mCamForward, mCamUp);
    }
    UpdateWorldSound(dt);
    const bool shipDrawn = mView != View::Free && mView != View::Bare && mShip.Ready()
        && (mView != View::Walk || Length(mShipPos-mCamPos)<250.0);

    // The mesh reaches the horizon, plus the highest mountains that can rise above it, capped at what
    // one face plane can cover. The face is centred on the nadir, its half-width proportional to the
    // height above the ground; the rings fill the rest.
    const bool airless=NearMoon(mCamPos);
    const Vec3d bodyCamera=mCamPos-(airless?mMoonCentre:Vec3d{});
    const double bodyRadius=airless?mMoonSurface.radius:PlanetRadius;
    const double heightEnvelope=airless?16000:kMaxElevation;
    const Vec3d up=Normalize(bodyCamera);
    const double camAltitude=Length(bodyCamera)-bodyRadius;
    const double clearance=std::max(camAltitude-mGroundHeight,.01);
    const double pixelAngle=2*std::tan(mCineFov*XM_PI/360)/mClientHeight;
    const double reliefPixels=kMaxElevation/(Length(mCamPos)*pixelAngle);
    const double proxyRise=mDiagnosticView!=0?0:std::min(std::max((.5-reliefPixels)/.25,0.0),1.0);
    const float earthProxy=airless?1.0f:float(proxyRise*proxyRise*(3-2*proxyRise));
    const bool earthDetailed=!airless && earthProxy<1;
    D3D12_RECT bodyBounds;
    const bool surfaceDetailed=earthDetailed || (airless && CelestialRect(mMoonCentre,bodyRadius+heightEnvelope,bodyBounds));
    if(mMoonMesh!=mActiveMoon){mTerrainKept=mScreenKept=mHistoryValid=false;mMeshFrozen=false;}
    mMoonMesh=mActiveMoon;

    // Tremble test: the mesh is placed as if the camera flew forward, while the camera stays still.
    Vec3d meshUp = up;
    if (trembleTest) {
        const Vec3d horizontal = Normalize(mCamForward - up * Dot(mCamForward, up));
        const double distance = mSettings.trembleSpeed * clearance / 60.0 * (mFrameNumber - TrembleWarmup);
        meshUp = Normalize(Rotate(mCamPos, Normalize(Cross(up, horizontal)), distance / Length(mCamPos)));
    }

    if (!mMeshFrozen) {
        const double horizon = std::acos(std::min(1.0,(bodyRadius-(airless?16000:0))/Length(bodyCamera)));
        const double mountains = std::acos(bodyRadius / (bodyRadius + heightEnvelope));
        const double extent = bodyRadius * std::tan(std::min(horizon + mountains, kMaxCoverage));

        // The face: centred on the nadir, half-width proportional to the height above the ground. It slides
        // continuously with the camera: this is what refines the mesh progressively, without any step.
        // On a moon, that ground is read at the face's own scale: finer relief rescaled every vertex each frame
        // (docs/log/spec-stabilite.md, cause 2). Contact, speed and the title keep the exact ground.
        const double meshGround = airless ? mMoonSurface.Height(Airless::Vec{ bodyCamera.x, bodyCamera.y, bodyCamera.z },
            std::max(.25, mFaceFactor * clearance)) : mGroundHeight;
        mMeshHalfWidth = std::min(mFaceFactor * std::max(camAltitude - meshGround, .01), extent);
        mMeshRingCount = std::min(MaxRings, (UINT)std::ceil(std::log(extent / mMeshHalfWidth) / std::log(RingGrowth)));

        // Face frame: z is the nadir, x is anchored on the north so the face does not twist with the heading.
        mMeshZ = meshUp;
        mMeshX = Cross(kNorth, meshUp);
        if (Length(mMeshX) < 1e-6) mMeshX = Cross({ 1.0, 0.0, 0.0 }, meshUp); // ponytail: the face spins over the poles
        mMeshX = Normalize(mMeshX);
        mMeshY = Cross(meshUp, mMeshX);
    }
    const Vec3d faceX = mMeshX, faceY = mMeshY, faceZ = mMeshZ;
    const double halfWidth = mMeshHalfWidth;
    const UINT ringCount = mMeshRingCount;
    const UINT vertexCount = FaceVertexCount + ringCount * RingVertexCount;
    const UINT indexCount = 6 * (FaceCells * FaceCells + ringCount * RingVertexCount);
    auto toLocal = [&](const Vec3d& v) {
        return XMVectorSet((float)Dot(v, faceX), (float)Dot(v, faceY), (float)Dot(v, faceZ), 0.0f);
    };
    // Camera on the face frame, in double precision: right above the face's centre unless the mesh is frozen.
    const double camHeight = Dot(bodyCamera, faceZ) - bodyRadius;
    mConstants->camPlane = { (float)Dot(bodyCamera, faceX), (float)Dot(bodyCamera, faceY), 0.0f, 0.0f };
    const float observerTarget=mWorldValid && Length(mCamPos-mWorldProbePos)<250
        ? ObserverCanopy(mHabitat[5].x,float(clearance),mHabitat[5].y) : 0.0f;
    // Hidden stills use the settled world value. Interactive response converges
    // in real time, with no framing-dependent luminance histogram.
    mObserverCanopy=mSettings.Automated()?observerTarget:
        mObserverCanopy+(observerTarget-mObserverCanopy)*(1.0f-std::exp(-dt/0.35f));
    mConstants->camPlane.w=mObserverCanopy;

    // Anchor of the fine detail drawn in the pixels: the multiple of kDetailUnit closest to the camera.
    // Pixels work from it in float, with exact lattice indices at the planet's scale.
    const double ax = std::round(bodyCamera.x / kDetailUnit), ay = std::round(bodyCamera.y / kDetailUnit),
        az = std::round(bodyCamera.z / kDetailUnit);
    mConstants->detailAnchor = { (int32_t)ax, (int32_t)ay, (int32_t)az, 0 };
    mConstants->detailOrigin = { (float)(bodyCamera.x - ax * kDetailUnit), (float)(bodyCamera.y - ay * kDetailUnit),
        (float)(bodyCamera.z - az * kDetailUnit), (float)kDetailUnit };

    // Rendering happens in the face frame with the camera at the origin: no large float coordinates.
    // Screenshot coordinates use the actual camera, updated every frame, including while the clock is paused.
    // Keep the text out of temporal history and the terrain; ToneMap draws it after the film curve.
    mConstants->coordinateInfo = {};
    mConstants->coordinateInfo.z = mSettings.Automated() ? 0u : 1u | (mView==View::Walk ? 2u : 0u)
        | (mAudioMuted || !mAudioReady ? 4u : 0u) | (mClock<mWalkNoticeUntil ? 8u : 0u)
        | (mView == View::Free ? unsigned(mCameraMode) << 4 : 0u);
    if (mView==View::Walk) {
        const unsigned surface=CurrentFootContact().Primary();
        mConstants->coordinateInfo.w=surface<FootContact::Count?surface+1:0;
    }
    if (mCoordinates) {
        const bool orbit = mView == View::Free && mCameraMode != CameraMode::Free;
        const int body = orbit ? mCameraBody : (airless ? mActiveMoon : Celestial::Exolune);
        const bool lunar = body >= 0 && body < int(Celestial::MoonCount);
        const Vec3d up = orbit ? mOrbitFrame.vertical : SurfaceUp(mCamPos);
        const double lon = std::atan2(up.z, up.x), toDegrees = 180.0 / XM_PI;
        const Vec3d north = { -up.y * std::cos(lon), std::hypot(up.x, up.z), -up.y * std::sin(lon) };
        const Vec3d east = { -std::sin(lon), 0.0, std::cos(lon) };
        const Vec3d forward = Normalize(mCamForward);
        const double pitch = -std::asin(std::min(std::max(Dot(forward, up), -1.0), 1.0)) * toDegrees;
        const Vec3d facing = orbit ? mOrbitFrame.heading : forward;
        const double heading = std::atan2(Dot(facing, east), Dot(facing, north)) * toDegrees;
        char lines[2][64] = {};
        const double lat = std::asin(std::min(std::max(up.y, -1.0), 1.0)) * toDegrees;
        if (lunar || body == Celestial::Exolune)
            snprintf(lines[0], sizeof(lines[0]), "LAT %.6f  LON %.6f  GRAINE %u",
                lat, lon * toDegrees, lunar ? Celestial::Moons[body].seed : mSettings.seed);
        else
            snprintf(lines[0], sizeof(lines[0]), "LAT %.6f  LON %.6f", lat, lon * toDegrees);
        if (body == Celestial::Exolune)
            snprintf(lines[1], sizeof(lines[1]), "ALT MER %.1f M  TANGAGE %.2f  CAP %.2f",
                Length(mCamPos) - PlanetRadius, pitch, heading);
        else if (lunar && body == mActiveMoon)
            snprintf(lines[1], sizeof(lines[1]), "LUNE %d ALT SOL %.1f M  TANGAGE %.2f  CAP %.2f",
                body + 1, SurfaceAltitude(mCamPos) - mGroundHeight, pitch, heading);
        else
            snprintf(lines[1], sizeof(lines[1]), "%s %d ALT %.1f M  TANGAGE %.2f  CAP %.2f",
                lunar ? "LUNE" : "PLANETE", lunar ? body + 1 : body - int(Celestial::MoonCount) + 1,
                Length(mCamPos - mCameraCentre) - mCameraRadius, pitch, heading);
        mConstants->coordinateInfo.x = UINT(std::strlen(lines[0]));
        mConstants->coordinateInfo.y = UINT(std::strlen(lines[1]));
        static_assert(sizeof(lines) == sizeof(mConstants->coordinateText), "Coordinate text packing must match HLSL.");
        std::memcpy(mConstants->coordinateText, lines, sizeof(lines));
    }
    const float fovY = XMConvertToRadians((float)mCineFov);
    const float aspect = float(mClientWidth) / float(mClientHeight);
    const Vec3d viewUp = mCamUp;
    const XMMATRIX view = XMMatrixLookToLH(XMVectorZero(), toLocal(mCamForward), toLocal(viewUp));
    const auto celestialBodies=Celestial::System(mWeatherTime,{mSunDir.x,mSunDir.y,mSunDir.z});
    const Celestial::Vector celestialCamera={mCamPos.x*.001,mCamPos.y*.001,mCamPos.z*.001};
    // Fixed 5 cm near plane preserves nearby cliffs; infinite reversed Z also preserves astronomical bodies.
    const float nearZ=0.05f;
    const float focal=1.0f/std::tan(fovY*.5f);
    const XMMATRIX proj=XMMatrixSet(focal/aspect,0,0,0, 0,focal,0,0, 0,0,0,1, 0,0,nearZ,0);

    // Camera axes, as XMMatrixLookToLH builds them, for the culling in the compute shader.
    const XMVECTOR camForward = XMVector3Normalize(toLocal(mCamForward));
    const XMVECTOR camRight = XMVector3Normalize(XMVector3Cross(toLocal(viewUp), camForward));
    const XMVECTOR camUp = XMVector3Cross(camForward, camRight);
    XMStoreFloat4(&mConstants->camForward, camForward);
    XMStoreFloat4(&mConstants->camRight, camRight);
    XMStoreFloat4(&mConstants->camUp, camUp);
    mConstants->camUp.w = std::tan(fovY * 0.5f);
    mConstants->camRight.w = mConstants->camUp.w * aspect;
    XMStoreFloat4x4(&mConstants->viewProj, XMMatrixTranspose(view * proj));

    // Temporal smoothing: from the current face frame, camera at the origin, to the previous frame's clip
    // space. Rotation between the two face frames, and the camera's move, both computed in double.
    const Vec3d move = mCamPos - mPrevCamPos;
    const Vec3d axes[3] = { faceX, faceY, faceZ };
    XMFLOAT4X4 toPrevious = {};
    for (int i = 0; i < 3; ++i)
        toPrevious.m[i][0] = (float)Dot(mPrevFaceX, axes[i]), toPrevious.m[i][1] = (float)Dot(mPrevFaceY, axes[i]),
        toPrevious.m[i][2] = (float)Dot(mPrevFaceZ, axes[i]);
    toPrevious.m[3][0] = (float)Dot(mPrevFaceX, move);
    toPrevious.m[3][1] = (float)Dot(mPrevFaceY, move);
    toPrevious.m[3][2] = (float)Dot(mPrevFaceZ, move);
    toPrevious.m[3][3] = 1.0f;
    XMStoreFloat4x4(&mConstants->reproject, XMMatrixTranspose(XMLoadFloat4x4(&toPrevious) * mPrevViewProj));
    // The ship's pixels follow the ship: a point fixed in its frame, carried from this frame's ship to the previous
    // one's, then into the previous camera (ToneMap.hlsl, inside shipSphere).
    // The planet frame is left-handed (east x north = down): Cross(up, forward) is the right, as for the camera.
    const Vec3d shipLeft = Cross(mShipForward, mShipUp), shipBack = mShipForward * -1.0;
    mConstants->shipSphere = { 0.0f, 0.0f, 0.0f, 0.0f };
    if (shipDrawn) {
        const Vec3d prevLeft = Cross(mPrevShipForward, mPrevShipUp), prevBack = mPrevShipForward * -1.0;
        auto carry = [&](const Vec3d& w) {
            return prevLeft * Dot(w, shipLeft) + prevBack * Dot(w, shipBack) + mPrevShipUp * Dot(w, mShipUp);
        };
        XMFLOAT4X4 toPreviousShip = {};
        for (int i = 0; i < 3; ++i) {
            const Vec3d w = carry(axes[i]);
            toPreviousShip.m[i][0] = (float)Dot(mPrevFaceX, w), toPreviousShip.m[i][1] = (float)Dot(mPrevFaceY, w),
            toPreviousShip.m[i][2] = (float)Dot(mPrevFaceZ, w);
        }
        const Vec3d shift = (mPrevShipPos - mPrevCamPos) + carry(mCamPos - mShipPos);
        toPreviousShip.m[3][0] = (float)Dot(mPrevFaceX, shift);
        toPreviousShip.m[3][1] = (float)Dot(mPrevFaceY, shift);
        toPreviousShip.m[3][2] = (float)Dot(mPrevFaceZ, shift);
        toPreviousShip.m[3][3] = 1.0f;
        XMStoreFloat4x4(&mConstants->reprojectShip, XMMatrixTranspose(XMLoadFloat4x4(&toPreviousShip) * mPrevViewProj));
        XMStoreFloat4(&mConstants->shipSphere, toLocal(mShipPos - mCamPos + shipBack * mShip.Profile().centreY + mShipUp * mShip.Profile().centreZ));
        mConstants->shipSphere.w = Ship::Radius;
    }
    if (mShip.Ready()) UpdateShipFrame(dt, faceX, faceY, faceZ);
    UpdateCityFrame(faceX,faceY,faceZ,view*proj);
    const double windAngle = std::fmod(mWeatherTime * kWeatherWindSpeed / PlanetRadius, 2.0 * XM_PI);
    {
        const Vec3d localUp=Normalize(mCamPos);
        Vec3d east=Cross(localUp,kNorth);
        if (Length(east)<1e-6) east=Cross(localUp,{1.0,0.0,0.0});
        east=Normalize(east);
        const Vec3d north=Cross(east,localUp);
        const double direction[]={localUp.x,localUp.y,localUp.z};
        float climate[Climate::Channels]={}; Climate::At(mClimateCpu,direction,climate);
        const Vec3d wind=east*climate[Climate::WindEast]+north*climate[Climate::WindNorth];
        XMStoreFloat4(&mConstants->foliageWind,toLocal(wind));
        mConstants->foliageWind.w=float(std::fmod(mWeatherTime,4096.0));
    }
    {
        const auto& bodies = celestialBodies;
        const auto& camera = celestialCamera;
        for (unsigned i=0;i<Celestial::BodyCount;++i) {
            const auto& body=bodies[i]; const auto offset=body.position-camera;
            XMStoreFloat4(&mConstants->celestialPosition[i],toLocal({offset.x,offset.y,offset.z}));
            mConstants->celestialPosition[i].w=float(body.radius);
            mConstants->celestialSurface[i]={float(body.albedo.x),float(body.albedo.y),float(body.albedo.z),float(body.kind)};
            XMStoreFloat4(&mConstants->celestialLight[i],toLocal({body.toSun.x,body.toSun.y,body.toSun.z}));
            mConstants->celestialLight[i].w=float(body.sunlight);
            const auto flux=Celestial::Illuminance(body,camera);
            // w: the body's illuminance on Exolune's ground below the camera, per unit albedo. The moons light Exolune
            // from there; at the camera, one flying beside a moon lit the whole night side seven hundredfold.
            const auto ground=Celestial::Illuminance(body,Celestial::Unit(camera)*Celestial::PlanetRadius);
            mConstants->celestialFlux[i]={float(flux.x),float(flux.y),float(flux.z),
                float(ground.y/std::max(body.albedo.y,1e-9))};
        }
    }
    mConstants->taa = { TemporalAA() && mHistoryValid ? 0.1f : 1.0f, mDiagnosticView,
                        (mSettings.noPlants || !mPlanetFoliage.Enabled() ? 1.0f : 0.0f) + (mFoliageFade ? 2.0f : 0.0f)
                            + (mPlanetFoliage.Enabled() ? 0.0f : 4.0f) + 8.0f * float(mFoliageFadeFrame++ & 63u)
                            + (mPlanetFoliage.Diverse() ? 512.0f : 0.0f) + (mPlanetFoliage.ArtDirected() ? 1024.0f : 0.0f)
                            + (mPlanetFoliage.GeneratedBank() ? 2048.0f : 0.0f) + (TemporalAA() ? 4096.0f : 0.0f)
                            + (mSettings.foliageWhiteNoise ? 8192.0f : 0.0f),
                        2.0f * std::tan(fovY * 0.5f) / float(mClientHeight) };
    // The clouds' frame (Clouds.hlsli, b1). Their diagnostic views of the weather map and of their shadow take the single
    // pass, whatever MYPLANETENGINE_CLOUD_FULL.
    const bool cloudTemporal = mSettings.cloudTemporal && mDiagnosticView != CloudWeatherView && mDiagnosticView != CloudShadowView;
    // The view's own axes, rolled with the ship's: the clouds' rays must be the image's.
    const Vec3d planetForward = Normalize(mCamForward);
    const Vec3d planetRight = Normalize(Cross(viewUp, planetForward));
    const Vec3d planetViewUp = Cross(planetForward, planetRight);
    auto writeVector = [](double (&target)[4], const Vec3d& value, double w) {
        target[0] = value.x; target[1] = value.y; target[2] = value.z; target[3] = w;
    };
    writeVector(mCloudConstants->cameraKm, mCamPos * 0.001, 0.0);
    mCloudConstants->cameraKm[3] = mCloudsOn ? 1.0 : 0.0;
    writeVector(mCloudConstants->forward, planetForward, 0.0);
    writeVector(mCloudConstants->rightTan, planetRight, mConstants->camRight.w);
    writeVector(mCloudConstants->upTan, planetViewUp, mConstants->camUp.w);
    mCloudConstants->wind[0] = std::sin(windAngle);
    mCloudConstants->wind[1] = std::cos(windAngle);
    mCloudConstants->wind[2] = mCloudsReference ? 1.0 : 0.0;
    mCloudConstants->wind[3] = 0.0;
    writeVector(mCloudConstants->sun, Normalize(mSunDir), 0.0);
    if (cloudTemporal) {
        // The previous camera sees a current camera-relative offset r (km) at R r + (R c - c'): R turns a point
        // carried by the weather from this frame's wind to the previous one's (CloudWeatherBackDP), and is
        // the identity on the ground. In double, then as rows of the previous camera's axes.
        const Vec3d cam = mCamPos * 0.001;
        const Vec3d axes[3] = { planetRight, planetViewUp, planetForward };
        auto turn = [](const Vec3d& v, double from, double to) {
            const Vec3d q = { std::cos(from) * v.x + std::sin(from) * v.z, v.y, -std::sin(from) * v.x + std::cos(from) * v.z };
            return Vec3d{ std::cos(to) * q.x - std::sin(to) * q.z, q.y, std::sin(to) * q.x + std::cos(to) * q.z };
        };
        auto writeRows = [&](float (&rows)[3][4], double prevWind) {
            const Vec3d offset = turn(cam, windAngle, prevWind) - mCloudPrevCam;
            for (int i = 0; i < 3; ++i) {
                const Vec3d row = turn(mCloudPrevAxes[i], prevWind, windAngle); // the axis a, as R^T a
                rows[i][0] = (float)row.x; rows[i][1] = (float)row.y; rows[i][2] = (float)row.z;
                rows[i][3] = (float)Dot(mCloudPrevAxes[i], offset);
            }
        };
        writeRows(mCloudConstants->prevQ, mCloudPrevWind);
        writeRows(mCloudConstants->prevGround, windAngle);
        // The history holds while the view continues: no teleport, the same trace, the sun within a degree.
        const bool enabled = mCloudsOn;
        const bool valid = mHistoryValid && mCloudHistoryValid && mCloudPrevReference == mCloudsReference
            && mCloudPrevEnabled == enabled && Dot(Normalize(mSunDir), mCloudPrevSun) > std::cos(XM_PI / 180.0);
        // The pixel traced in each tile: the frame's bits reversed, dealt in turn to y and x, so that consecutive
        // frames spread over the tile (Bayer's order for 4x4) and every pixel comes in CloudTileX * CloudTileY frames.
        UINT tileX = 0, tileY = 0, bitsX = 0, bitsY = 0;
        const UINT tileFrames = CloudTileX * CloudTileY;
        for (UINT bit = tileFrames >> 1, b = 0; bit > 0; bit >>= 1, ++b)
            if ((b % 2 == 0 && (1u << bitsY) < CloudTileY) || (1u << bitsX) >= CloudTileX)
                tileY |= (mCloudFrame % tileFrames & bit ? 1u : 0u) << bitsY++;
            else
                tileX |= (mCloudFrame % tileFrames & bit ? 1u : 0u) << bitsX++;
        mCloudConstants->temporal[0] = (float)tileX;
        mCloudConstants->temporal[1] = (float)tileY;
        mCloudConstants->temporal[2] = valid ? 1.0f : 0.0f;
        mCloudConstants->temporal[3] = 0.0f; // reserved
        ++mCloudFrame;
        mCloudPrevCam = cam;
        for (int i = 0; i < 3; ++i) mCloudPrevAxes[i] = axes[i];
        mCloudPrevWind = windAngle;
        mCloudPrevSun = Normalize(mSunDir);
        mCloudPrevReference = mCloudsReference;
        mCloudPrevEnabled = enabled;
        mCloudHistoryValid = true;
    }
    else
        mCloudHistoryValid = false; // the history waits for the temporal pass's own next frame
    mPrevViewProj = view * proj;
    mPrevCamPos = mCamPos;
    mPrevFaceX = faceX;
    mPrevFaceY = faceY;
    mPrevFaceZ = faceZ;
    mPrevShipPos = mShipPos;
    mPrevShipForward = mShipForward;
    mPrevShipUp = mShipUp;
    mConstants->faceX = { (float)faceX.x, (float)faceX.y, (float)faceX.z, 0.0f };
    mConstants->faceY = { (float)faceY.x, (float)faceY.y, (float)faceY.z, 0.0f };
    mConstants->faceZ = { (float)faceZ.x, (float)faceZ.y, (float)faceZ.z, 0.0f };
    mConstants->faceParams = { (float)halfWidth, (float)bodyRadius, (float)camHeight, (float)FaceCells };
    const double faceCell = 2.0 * halfWidth / FaceCells, fineRise = std::min(std::max(faceCell / FineMinCell - 1.0, 0.0), 1.0);
    const float fineWeight = surfaceDetailed?(float)(fineRise * fineRise * (3.0 - 2.0 * fineRise)):0.0f;
    mConstants->ringParams = { (float)ringCount, (float)RingGrowth, fineWeight, (float)FineSubdivision };
    // The screen relief, from orbit down to where the fine grid and the per-pixel detail carry the relief to the pixel.
    bool screenCovers = false;
    {
        const UINT across = (mClientWidth + ScreenReliefScale - 1) / ScreenReliefScale;
        const UINT down = std::min((mClientHeight + ScreenReliefScale - 1) / ScreenReliefScale, ScreenReliefMaxTexels / across);
        const double rise = std::min(std::max((camAltitude - ScreenReliefLow) / (ScreenReliefHigh - ScreenReliefLow), 0.0), 1.0);
        const float weight = surfaceDetailed?(float)(rise * rise * (3.0 - 2.0 * rise)):0.0f;
        mConstants->screenRelief = { (float)across, (float)down, weight, (float)ScreenReliefScale };
        // At full weight on every row, the pixel reads the fine grid only at the limb (FineTerrain.hlsl).
        screenCovers = weight >= 1.0f && down * ScreenReliefScale >= mClientHeight;
    }
    mConstants->erosionMode = { mErosionMode, screenCovers ? 1u : 0u, mErosionRiverMap ? 1u : 0u, unsigned(mActiveMoon+1) };
    XMStoreFloat4(&mConstants->lightDir, toLocal(mSunDir));
    XMStoreFloat4(&mConstants->camVertical, toLocal(Normalize(mCamPos)));
    mConstants->camVertical.w = (float)((Length(mCamPos)-PlanetRadius) / 1000.0);
    mConstants->lightDir.w = mWireframe ? 2.0f : mFaceted ? 1.0f : 0.0f; // shading mode, see Planet.hlsli
    mConstants->nadir[0] = faceZ.x;
    mConstants->nadir[1] = faceZ.y;
    mConstants->nadir[2] = faceZ.z;
    mConstants->nadir[3] = airless?double(mMoonSurface.seed):0.0;
    // The sea's time: the clock's, or a 60 fps frame's when frames are captured, so that captures repeat.
    const bool oceanReset=mWaveReset;
    UpdateOceanPlane(!mCine.empty() ? 1.0 / mCineFps : mSettings.Automated() ? 1.0 / 60.0 : dt, faceX, faceY, faceZ);
    // The terrain's inputs against the previous frame's (docs/optimisation.md, round 4). The same mesh: each vertex
    // computed then keeps its terrain, only those newly needed are computed, as when the camera turns on the spot. The
    // same view and sun too: nothing of the terrain's compute changes, and it is not run.
    const TerrainInputs terrainInputs = { mConstants->faceX, mConstants->faceY, mConstants->faceZ, mConstants->faceParams,
        { mConstants->nadir[0], mConstants->nadir[1], mConstants->nadir[2], mConstants->nadir[3] }, mConstants->ringParams,
        mConstants->camPlane, mConstants->lightDir, mConstants->camRight, mConstants->camUp, mConstants->camForward,
        { 0.0f, 0.0f, 0.0f, mConstants->waveAxisX.w } };
    bool sameMesh = mTerrainKept && std::memcmp(&terrainInputs, &mTerrainInputs, offsetof(TerrainInputs, lightDir)) == 0;
    bool sameTerrain = sameMesh && std::memcmp(&terrainInputs, &mTerrainInputs, sizeof(TerrainInputs)) == 0;
    mTerrainInputs = terrainInputs;
    mTerrainKept = true;
    // In a flight, the mesh slid this frame and the previous one: the lattice split in pairs of floats, the vertex under
    // the camera aside (round 8), where some vertices split it in doubles, cells under EXACT_LATTICE_MAX_CELL, 4 m
    // (PlanetSettings.hlsli). Not after a jump: a still view is the exact one from its first frame. Stopped after a
    // flight, the mesh is computed again in doubles, all of it: what is kept is always exact.
    const bool latticePairs = !airless && !sameMesh && mTerrainSlid && faceCell < 4.0;
    mTerrainSlid = !sameMesh;
    if (mTerrainPairs && sameMesh)
        sameMesh = sameTerrain = false;
    mTerrainPairs = latticePairs;
    mConstants->camPlane.z = sameMesh ? 1.0f : 0.0f;

    QueryPerformanceCounter(&cpuMarks[1]);
    mCommandAllocator->Reset();
    mCommandList->Reset(mCommandAllocator.Get(), nullptr);
    QueueFlightContact();
    auto gpuStage = [&](const wchar_t* label) {
        if (mGpuBreadcrumbs) mCommandList->SetMarker(0, label, UINT((wcslen(label) + 1) * sizeof(wchar_t)));
    };
    if (mView==View::Walk) QueueWalkGround();
    QueueWorldSound();
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 0);

    const double oceanStep=!mCine.empty()?1.0/mCineFps:mSettings.Automated()?1.0/60.0:dt;
    mCommandList->EndQuery(mTimestampHeap.Get(),D3D12_QUERY_TYPE_TIMESTAMP,6);
    if(earthDetailed)mOcean->Update(mCommandList.Get(),mWaveOrigin[0],mWaveOrigin[1],mSeaTime,float(oceanStep*mSeaTimeRate),oceanReset,mOceanElevation);
    mCommandList->EndQuery(mTimestampHeap.Get(),D3D12_QUERY_TYPE_TIMESTAMP,7);

    // 1. Compute: elevations of the whole mesh, every frame its inputs change. Buffers are back to COMMON after each frame.
    if(surfaceDetailed) {
    gpuStage(L"Terrain mesh");
    auto toUav = CD3DX12_RESOURCE_BARRIER::Transition(mFaceVertexBuffer.Get(),
        D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    mCommandList->ResourceBarrier(1, &toUav);
    ID3D12DescriptorHeap* terrainHeaps[] = { mSrvHeap.Get() }; // the ocean's pass set its own
    mCommandList->SetDescriptorHeaps(1, terrainHeaps);
    mCommandList->SetComputeRootSignature(mComputeRootSignature.Get());
    mCommandList->SetPipelineState(airless?mAirlessComputePSO.Get():latticePairs?mComputePairsPSO.Get():mComputePSO.Get());
    mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(1, mFaceVertexBuffer->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(2, GpuDescriptor(TectonicSrv));
    // By 8 x 8 tiles of vertices (TerrainCompute.hlsl): the face's grid, then its rings by 8; 4 n vertices a ring.
    static_assert(FaceCells % 2 == 0, "the rings' tiles take 8 of their 4 n vertices");
    const UINT meshGroups = ((FaceCells + 8) / 8) * ((FaceCells + 8) / 8) + ((ringCount + 7) / 8) * (FaceCells / 2);
    if (!sameTerrain) mCommandList->Dispatch(meshGroups, 1, 1);
    if (latticePairs) {
        // The vertex under the camera, left by the pairs, from the exact shader as it is: the mesh kept (camPlane.z), it
        // computes only the vertices without terrain. The camera stands on the same ground as on the exact mesh.
        std::memcpy(mNadirConstants, mConstants, sizeof(FrameConstants));
        mNadirConstants->camPlane.z = 1.0f;
        auto pairsWritten = CD3DX12_RESOURCE_BARRIER::UAV(mFaceVertexBuffer.Get());
        mCommandList->ResourceBarrier(1, &pairsWritten);
        mCommandList->SetPipelineState(mComputePSO.Get());
        mCommandList->SetComputeRootConstantBufferView(0, mNadirConstantBuffer->GetGPUVirtualAddress());
        mCommandList->Dispatch(meshGroups, 1, 1);
        mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
    }
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 35);
    // The march toward the sun, into the same vertices: the terrain's horizon, for its cast shadow, and the shadow height,
    // for the air (Shadows.hlsli).
    auto terrainWritten = CD3DX12_RESOURCE_BARRIER::UAV(mFaceVertexBuffer.Get());
    mCommandList->ResourceBarrier(1, &terrainWritten);
    mCommandList->SetPipelineState(airless?mAirlessHorizonPSO.Get():mHorizonPSO.Get());
    if (!sameTerrain) mCommandList->Dispatch((vertexCount + 63) / 64, 1, 1);
    auto toRead = CD3DX12_RESOURCE_BARRIER::Transition(mFaceVertexBuffer.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
        D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_COPY_SOURCE);
    mCommandList->ResourceBarrier(1, &toRead);

    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 36);
    // The fine grid (docs/spec-rendu-lointain.md, step 2): positions, then normals, away from the ground only.
    if (fineWeight > 0.0f)
    {
        auto fineToWrite = CD3DX12_RESOURCE_BARRIER::Transition(mFinePositions.Get(), D3D12_RESOURCE_STATE_COMMON,
            D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        mCommandList->ResourceBarrier(1, &fineToWrite);
        mCommandList->SetPipelineState(airless?mAirlessFinePSO.Get():mFineTerrainPSO.Get());
        gpuStage(L"Terrain fine grid");
        mCommandList->SetComputeRootUnorderedAccessView(1, mFinePositions->GetGPUVirtualAddress());
        // By 8 x 8 tiles of samples (FineTerrain.hlsl).
        if (!sameTerrain) mCommandList->Dispatch((FaceCells * FineSubdivision + 8) / 8, (FaceCells * FineSubdivision + 8) / 8, 1);
        mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 37);
        auto fineToRead = CD3DX12_RESOURCE_BARRIER::Transition(mFinePositions.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
        auto normalsToWrite = CD3DX12_RESOURCE_BARRIER::Transition(mFineNormals.Get(), D3D12_RESOURCE_STATE_COMMON,
            D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        const D3D12_RESOURCE_BARRIER fineBarriers[] = { fineToRead, normalsToWrite };
        mCommandList->ResourceBarrier(2, fineBarriers);
        mCommandList->SetComputeRootSignature(mFineRootSignature.Get());
        mCommandList->SetPipelineState(mFineNormalsPSO.Get());
        mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
        mCommandList->SetComputeRootShaderResourceView(1, mFinePositions->GetGPUVirtualAddress());
        mCommandList->SetComputeRootUnorderedAccessView(2, mFineNormals->GetGPUVirtualAddress());
        if (!sameTerrain) mCommandList->Dispatch((FineVertexCount + 63) / 64, 1, 1);
        auto normalsToRead = CD3DX12_RESOURCE_BARRIER::Transition(mFineNormals.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE);
        mCommandList->ResourceBarrier(1, &normalsToRead);
    }
    else mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 37);
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 38);
    // Ground, river geometry and finish retain the same two physical ray queries in smaller kernels.
    gpuStage(L"Screen relief");
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 22);
    {
        const UINT across = (UINT)mConstants->screenRelief.x, down = (UINT)mConstants->screenRelief.y;
        const bool on = mConstants->screenRelief.z > 0.0f;
        const ScreenInputs screenInputs = { mConstants->faceX, mConstants->faceY, mConstants->faceZ,
            { mConstants->nadir[0], mConstants->nadir[1], mConstants->nadir[2], mConstants->nadir[3] },
            { mConstants->camPlane.x, mConstants->camPlane.y, mConstants->faceParams.y, mConstants->faceParams.z },
            mConstants->camRight, mConstants->camUp, mConstants->camForward,
            { mConstants->taa.w, 0.0f, 0.0f, 0.0f }, mConstants->screenRelief, mConstants->erosionMode };
        const bool sameScreen = mScreenKept && std::memcmp(&screenInputs, &mScreenInputs, sizeof(ScreenInputs)) == 0;
        mScreenUpdated = on && !sameScreen;
        mScreenInputs = screenInputs;
        mScreenKept = on;
        auto toWrite = CD3DX12_RESOURCE_BARRIER::Transition(mScreenPositions.Get(), D3D12_RESOURCE_STATE_COMMON,
            D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
        mCommandList->ResourceBarrier(1, &toWrite);
        if (on && !sameScreen) {
            if(airless) {
                mCommandList->SetComputeRootSignature(mScreenRootSignature.Get());
                mCommandList->SetComputeRootConstantBufferView(0,mConstantBuffer->GetGPUVirtualAddress());
                mCommandList->SetComputeRootUnorderedAccessView(1,mScreenPositions->GetGPUVirtualAddress());
                mCommandList->SetPipelineState(mAirlessScreenPSO.Get());
                mCommandList->Dispatch((across+7)/8,(down+7)/8,1);
                for(UINT stamp=23;stamp<35;++stamp)mCommandList->EndQuery(mTimestampHeap.Get(),D3D12_QUERY_TYPE_TIMESTAMP,stamp);
            } else {

            // Allocate only the current view's work, not a full 4K scratch buffer for every window.
            // The previous frame has completed before recording this one.
            if (across * down > mScreenWorkTexels) {
                mScreenWorkTexels = across * down;
                mScreenWork = CreateBuffer(md3dDevice.Get(), ScreenWorkBytes * mScreenWorkTexels, D3D12_HEAP_TYPE_DEFAULT,
                    D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
                auto scratch = [&](UINT64 bytes) {
                    return CreateBuffer(md3dDevice.Get(), bytes, D3D12_HEAP_TYPE_DEFAULT,
                        D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
                };
                mScreenRiverCounter = scratch(4); // the wide queries (ScreenRiverTexel.hlsl)
                mScreenRiverDispatch = scratch(12); // their dispatch's arguments
                mScreenRiverFallback = scratch(4ull * mScreenWorkTexels);
            }
            auto workToWrite = CD3DX12_RESOURCE_BARRIER::Transition(mScreenWork.Get(), D3D12_RESOURCE_STATE_COMMON,
                D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
            mCommandList->ResourceBarrier(1, &workToWrite);
            mCommandList->SetComputeRootSignature(mScreenRootSignature.Get());
            mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
            mCommandList->SetComputeRootUnorderedAccessView(1, mScreenPositions->GetGPUVirtualAddress());
            mCommandList->SetComputeRootDescriptorTable(2, GpuDescriptor(TectonicSrv));
            mCommandList->SetComputeRootUnorderedAccessView(3, mScreenWork->GetGPUVirtualAddress());
            mCommandList->SetComputeRootUnorderedAccessView(5, mScreenRiverCounter->GetGPUVirtualAddress());
            mCommandList->SetComputeRootUnorderedAccessView(6, mScreenRiverDispatch->GetGPUVirtualAddress());
            mCommandList->SetComputeRootUnorderedAccessView(7, mScreenRiverFallback->GetGPUVirtualAddress());
            const auto workWritten = CD3DX12_RESOURCE_BARRIER::UAV(mScreenWork.Get());
            const auto screenWritten = CD3DX12_RESOURCE_BARRIER::UAV(mScreenPositions.Get());
            const auto allWritten = CD3DX12_RESOURCE_BARRIER::UAV(nullptr);
            // Every footprint reads the rivers' map, or no river is drawn: both rays in the ground pass, finished there,
            // without the river passes (ScreenRelief.hlsl). The nearest ground is the nadir's, the highest summit up;
            // a texel's river radius is twice its footprint (ScreenBandwidth), the map alone from sqrt 2 of its cells.
            const double mapCell = mErosionSize > 8 ? 2.0 * PlanetRadius / double(mErosionSize - 8) : 1e30;
            const bool direct = mErosionMode < 2 || (mErosionRiverMap
                && 2.0 * (camAltitude - 10e3) * double(mConstants->taa.w) * double(mConstants->screenRelief.w) >= 1.4143 * mapCell);
            if (direct) {
                mCommandList->SetComputeRoot32BitConstant(4, 2u, 0);
                mCommandList->SetPipelineState(mScreenReliefPSO.Get());
                gpuStage(L"Screen ground, direct");
                mCommandList->Dispatch((across + 7) / 8, (down + 7) / 8, 1);
                mCommandList->ResourceBarrier(1, &screenWritten);
                for (UINT stamp = 23; stamp != 35; ++stamp)
                    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, stamp);
            }
            for (UINT pass = 0; pass != (direct ? 0u : 2u); ++pass) {
                // At full weight, one river query per texel: the first pass only places the ground for the parallax;
                // the second evaluates its rivers, at the raised point or at the kept sea-level one (ScreenRelief.hlsl).
                const bool rivers = pass != 0 || mConstants->screenRelief.z < 1.0f;
                // Without them, the first ray's ground is finished in its own pass (ScreenRelief.hlsl, bit 2).
                const bool finished = !rivers;
                mCommandList->SetComputeRoot32BitConstant(4, finished ? 4u : pass, 0);
                mCommandList->SetPipelineState(mScreenReliefPSO.Get());
                gpuStage(L"Screen ground");
                mCommandList->Dispatch((across + 7) / 8, (down + 7) / 8, 1);
                mCommandList->ResourceBarrier(1, &allWritten);
                mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 23 + 6 * pass);
                // One river query per texel in a kernel of its own; the wide ones, at the limb, a wave each.
                if (rivers) {
                    mCommandList->SetPipelineState(mScreenRiverTexelPSO.Get());
                    gpuStage(L"Screen rivers, per texel");
                    mCommandList->Dispatch((across + 7) / 8, (down + 7) / 8, 1);
                    mCommandList->ResourceBarrier(1, &allWritten);
                }
                mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 24 + 6 * pass);
                if (rivers) {
                    mCommandList->SetPipelineState(mScreenRiverArgsPSO.Get());
                    mCommandList->Dispatch(1, 1, 1);
                    auto argsToRead = CD3DX12_RESOURCE_BARRIER::Transition(mScreenRiverDispatch.Get(),
                        D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT);
                    mCommandList->ResourceBarrier(1, &argsToRead);
                }
                mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 25 + 6 * pass);
                if (rivers) {
                    mCommandList->SetPipelineState(mScreenRiversPSO.Get());
                    gpuStage(L"Screen river fallback");
                    mCommandList->ExecuteIndirect(mObjectDispatchSignature.Get(), 1, mScreenRiverDispatch.Get(), 0, nullptr, 0);
                    mCommandList->ResourceBarrier(1, &workWritten);
                    auto argsToWrite = CD3DX12_RESOURCE_BARRIER::Transition(mScreenRiverDispatch.Get(),
                        D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
                    mCommandList->ResourceBarrier(1, &argsToWrite);
                }
                mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 26 + 6 * pass);
                mCommandList->ResourceBarrier(1, &screenWritten);
                mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 27 + 6 * pass);
                // The next ground pass resets the counter.
                mCommandList->ResourceBarrier(1, &allWritten);
                mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 28 + 6 * pass);
            }
            auto workToCommon = CD3DX12_RESOURCE_BARRIER::Transition(mScreenWork.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                D3D12_RESOURCE_STATE_COMMON);
            mCommandList->ResourceBarrier(1, &workToCommon);
            }
        }
        auto toRead = CD3DX12_RESOURCE_BARRIER::Transition(mScreenPositions.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
        mCommandList->ResourceBarrier(1, &toRead);
    }
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 1);
    const UINT nadirIndex = (FaceCells / 2) * (FaceCells + 1) + FaceCells / 2;
    mCommandList->CopyBufferRegion(mReadbackBuffer.Get(), 0, mFaceVertexBuffer.Get(), nadirIndex * sizeof(FaceVertex),
        sizeof(FaceVertex));

    // Objects near the camera (docs/spec-objets-proximite.md): placed afresh every frame on the planet's lattice, in the
    // windows of cells around the camera, on the planes of the planet axes that can be the vertical's largest there.
    PlacementConstants placement = {};
    const Vec3d foot = up * bodyRadius;
    for (int i = 0; i < 3; ++i) {
        placement.cam[i] = (&bodyCamera.x)[i];
        placement.foot[i] = (&foot.x)[i];
    }
    placement.pixelAngle = 2.0f * std::tan(fovY * 0.5f) / float(mClientHeight);
    placement.flags = (mSettings.objectPop ? 1u : 0u) | (mSettings.objectCensus && mSettings.batch ? 2u : 0u);
    const double plantReach = 0.5 * PlanetPlantWindow * 32.0; // the plants' windows' half width (m): tiles of 32 m
    const double reach = 2.0 * plantReach / bodyRadius;
    for (int axis = 0; axis < 3; ++axis) {
        const double a = std::fabs((&up.x)[axis]);
        const double others = std::max(std::fabs((&up.x)[(axis + 1) % 3]), std::fabs((&up.x)[(axis + 2) % 3]));
        if (a + reach < others - reach) continue;
        INT32* plane = placement.planes[placement.planeCount++];
        plane[0] = axis;
        plane[1] = (&up.x)[axis] >= 0.0 ? 1 : -1;
        plane[2] = INT32(std::floor((&foot.x)[(axis + 1) % 3] / ObjectFinestCell));
        plane[3] = INT32(std::floor((&foot.x)[(axis + 2) % 3] / ObjectFinestCell));
    }
    const CD3DX12_RESOURCE_BARRIER countersToReset[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectCounters.Get(), D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_STATE_COPY_DEST),
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectDispatch.Get(), D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_STATE_COPY_DEST) };
    mCommandList->ResourceBarrier(2, countersToReset);
    mCommandList->CopyBufferRegion(mObjectCounters.Get(), 0, mObjectCountersReset.Get(), 0, ObjectCounters * sizeof(UINT));
    mCommandList->CopyBufferRegion(mObjectDispatch.Get(), 0, mObjectCountersReset.Get(), ObjectCounters * sizeof(UINT), 4 * sizeof(UINT));
    const CD3DX12_RESOURCE_BARRIER objectsToWrite[4] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectCounters.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectDispatch.Get(), D3D12_RESOURCE_STATE_COPY_DEST, D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectCandidates.Get(), D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_STATE_UNORDERED_ACCESS),
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectInstances.Get(), D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_STATE_UNORDERED_ACCESS) };
    mCommandList->ResourceBarrier(4, objectsToWrite);
    ID3D12DescriptorHeap* computeHeaps[] = { mSrvHeap.Get() };
    mCommandList->SetDescriptorHeaps(1, computeHeaps);
    mCommandList->SetComputeRootSignature(mObjectRootSignature.Get());
    mCommandList->SetPipelineState(airless?mAirlessObjectCandidatesPSO.Get():mObjectCandidatesPSO.Get());
    mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetComputeRootShaderResourceView(1, mFaceVertexBuffer->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(2, mObjectInstances->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(3, mObjectCounters->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(4, GpuDescriptor(MaterialSrv));
    mCommandList->SetComputeRoot32BitConstants(5, sizeof(PlacementConstants) / 4, &placement, 0);
    mCommandList->SetComputeRootUnorderedAccessView(6, mObjectCandidates->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(7, mObjectDispatch->GetGPUVirtualAddress());
    mCommandList->SetComputeRootShaderResourceView(8, mObjectCandidates->GetGPUVirtualAddress());
    mCommandList->SetComputeRootShaderResourceView(9, mObjectDispatch->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(10, GpuDescriptor(PlanetMapSrv));
    mCommandList->SetComputeRootDescriptorTable(18, GpuDescriptor(TectonicSrv));
    mCommandList->Dispatch(ObjectWindow / 8, ObjectWindow / 8, ObjectSlices * placement.planeCount);
    const CD3DX12_RESOURCE_BARRIER candidatesToRead[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectDispatch.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectCandidates.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE) };
    mCommandList->ResourceBarrier(2, candidatesToRead);
    mCommandList->SetPipelineState(airless?mAirlessObjectPlacementPSO.Get():mObjectPlacementPSO.Get());
    mCommandList->ExecuteIndirect(mObjectDispatchSignature.Get(), 1, mObjectDispatch.Get(), 0, nullptr, 0);
    if (mSettings.batch) mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 12);
    // The plants, in windows of their own (docs/recherche-vegetation.md): their slices after the stones' and the tufts'.
    // None can be in reach from higher than their windows' half width.
    if (earthDetailed && mPlanetFoliage.Enabled() && clearance < plantReach && !mSettings.noPlants) {
        placement.sliceBase = ObjectSlices;
        mPlanetPlantPlacement.Run(mCommandList.Get(), mObjectRootSignature.Get(), mObjectDispatchSignature.Get(),
            mConstantBuffer->GetGPUVirtualAddress(), mFaceVertexBuffer.Get(), mObjectInstances.Get(), mObjectCounters.Get(),
            GpuDescriptor(MaterialSrv), GpuDescriptor(PlanetMapSrv), GpuDescriptor(TectonicSrv), &placement,
            sizeof(PlacementConstants) / 4, placement.planeCount);
    }
    if (mSettings.batch) mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 13);
    const CD3DX12_RESOURCE_BARRIER objectsToRead[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectCounters.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT | D3D12_RESOURCE_STATE_COPY_SOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mObjectInstances.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
            D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_COPY_SOURCE) };
    mCommandList->ResourceBarrier(2, objectsToRead);
    mCommandList->CopyBufferRegion(mObjectReadback.Get(), 0, mObjectCounters.Get(), 0, ObjectCounters * sizeof(UINT));
    if (mObjectInstancesReadback)
        mCommandList->CopyBufferRegion(mObjectInstancesReadback.Get(), 0, mObjectInstances.Get(), 0, sizeof(ObjectInstance) * ObjectCapacity);
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 8);
    if(earthDetailed)mPlanetFoliage.Classify(mCommandList.Get(), mConstantBuffer->GetGPUVirtualAddress(), mObjectInstances.Get(), mObjectCounters.Get());
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 9);
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 3);

    } else {
        mTerrainKept=false;mScreenUpdated=false;
        for(UINT query:{1u,3u,8u,9u,22u,35u,36u,37u,38u})mCommandList->EndQuery(mTimestampHeap.Get(),D3D12_QUERY_TYPE_TIMESTAMP,query);
        if(mSettings.batch)for(UINT query:{12u,13u})mCommandList->EndQuery(mTimestampHeap.Get(),D3D12_QUERY_TYPE_TIMESTAMP,query);
    }

    // 2. Draw the face, in linear light, into the HDR image (render target since the end of the last frame).
    CD3DX12_CPU_DESCRIPTOR_HANDLE hdrRtv(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), HdrRtv, mRtvDescriptorSize);
    D3D12_CPU_DESCRIPTOR_HANDLE dsvHandle = mDsvHeap->GetCPUDescriptorHandleForHeapStart();
    const CD3DX12_CPU_DESCRIPTOR_HANDLE sunRtv(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), SunRtv, mRtvDescriptorSize);
    const D3D12_CPU_DESCRIPTOR_HANDLE sceneRtvs[2] = { hdrRtv, sunRtv };
    ID3D12DescriptorHeap* shipHeaps[] = { mSrvHeap.Get() };
    mCommandList->SetDescriptorHeaps(1, shipHeaps);
    const Ship::Tables shipTables = { mConstantBuffer->GetGPUVirtualAddress(), mCloudConstantBuffer->GetGPUVirtualAddress(),
        mFaceVertexBuffer->GetGPUVirtualAddress(), GpuDescriptor(LutSrv), GpuDescriptor(PlanetMapSrv), GpuDescriptor(CompositeSrv),
        GpuDescriptor(CloudSrv) };
    if (shipDrawn) mShip.DrawShadows(mCommandList.Get(), shipTables);
    mCity.DrawShadows(mCommandList.Get(),mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->OMSetRenderTargets(2, sceneRtvs, FALSE, &dsvHandle);
    mCommandList->ClearRenderTargetView(hdrRtv, kClearColor, 0, nullptr);
    mCommandList->ClearRenderTargetView(sunRtv, kClearColor, 0, nullptr);
    mCommandList->ClearDepthStencilView(dsvHandle, D3D12_CLEAR_FLAG_DEPTH, 0.0f, 0, 0, nullptr);

    CD3DX12_VIEWPORT viewport(0.0f, 0.0f, float(mClientWidth), float(mClientHeight));
    CD3DX12_RECT scissor(0, 0, LONG(mClientWidth), LONG(mClientHeight));
    mCommandList->RSSetViewports(1, &viewport);
    mCommandList->RSSetScissorRects(1, &scissor);
    if (shipDrawn)
        mShip.DrawOpaque(mCommandList.Get(), shipTables); // cockpit first; mirror skins need the world behind them
    mCity.Draw(mCommandList.Get(),mConstantBuffer->GetGPUVirtualAddress(),GpuDescriptor(LutSrv),GpuDescriptor(PlanetMapSrv));

    ID3D12DescriptorHeap* heaps[] = { mSrvHeap.Get() };
    const auto bindTerrain = [&](ID3D12PipelineState* pso) {
        mCommandList->SetGraphicsRootSignature(mRootSignature.Get());
        mCommandList->SetPipelineState(pso);
        mCommandList->SetGraphicsRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
        mCommandList->SetGraphicsRootShaderResourceView(1, mFaceVertexBuffer->GetGPUVirtualAddress());
        mCommandList->SetDescriptorHeaps(1, heaps);
        mCommandList->SetGraphicsRootDescriptorTable(2, GpuDescriptor(LutSrv));
        mCommandList->SetGraphicsRootShaderResourceView(3, mFaceVertexBuffer->GetGPUVirtualAddress());
        mCommandList->SetGraphicsRootDescriptorTable(4, GpuDescriptor(MaterialSrv));
        mCommandList->SetGraphicsRootShaderResourceView(5, mFineNormals->GetGPUVirtualAddress());
        mCommandList->SetGraphicsRootShaderResourceView(12, mScreenPositions->GetGPUVirtualAddress());
        mCommandList->SetGraphicsRootDescriptorTable(7, GpuDescriptor(airless?AirlessMaterialSrv+unsigned(mActiveMoon):PlanetMapSrv));
        mCommandList->SetGraphicsRootConstantBufferView(8,mOcean->ConstantsAddress());
        mCommandList->SetGraphicsRootDescriptorTable(9,GpuDescriptor(OceanSrv));
        mCommandList->SetGraphicsRootDescriptorTable(10, mShip.SunMapSrv());
        mCommandList->SetGraphicsRootDescriptorTable(11, GpuDescriptor(TectonicSrv));
        mCommandList->SetGraphicsRootDescriptorTable(13,mCity.Ready()?mCity.ShadowSrv():mShip.SunMapSrv());
        mCommandList->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        mCommandList->IASetIndexBuffer(&mIndexBufferView);
    };
    const auto drawTerrain = [&](ID3D12PipelineState* pso) {
        bindTerrain(pso);
        mCommandList->DrawIndexedInstanced(indexCount, 1, 0, 0, 0);
    };
    // The terrain's depth alone (docs/optimisation.md, round 2): its colour waits for the plants, below. The wireframe, at once.
    const bool terrainDepthFirst = surfaceDetailed && !mWireframe;
    if (terrainDepthFirst) {
        mCommandList->OMSetRenderTargets(0, nullptr, FALSE, &dsvHandle);
        drawTerrain(airless?mAirlessDepthPSO.Get():mTerrainDepthPSO.Get());
        mCommandList->OMSetRenderTargets(2, sceneRtvs, FALSE, &dsvHandle);
    } else if(surfaceDetailed)
        drawTerrain(airless?mAirlessWirePSO.Get():mWirePSO.Get());
    // The objects, over the ground, but in the materials' diagnostic views.
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 4);
    mCommandList->IASetIndexBuffer(&mShapeIndexView);
    if (surfaceDetailed && (mDiagnosticView == 0.0f || mDiagnosticView == ObjectsView || mDiagnosticView >= HeightView)) {
        mCommandList->SetPipelineState(airless?mAirlessObjectPSO.Get():mObjectPSO.Get());
        mCommandList->SetGraphicsRootShaderResourceView(1, mObjectInstances->GetGPUVirtualAddress());
        mCommandList->SetGraphicsRootShaderResourceView(6, mShapeVertices->GetGPUVirtualAddress());
        mCommandList->ExecuteIndirect(mObjectCommandSignature.Get(), 1, mObjectCounters.Get(), 0, nullptr, 0);
        if(!airless) {
        mCommandList->SetPipelineState(mTuftPSO.Get());
        mCommandList->SetGraphicsRootShaderResourceView(1, mObjectInstances->GetGPUVirtualAddress() + sizeof(ObjectInstance) * ObjectClassCapacity);
        mCommandList->SetGraphicsRootShaderResourceView(6, mShapeVertices->GetGPUVirtualAddress() + mTuftShapeOffset);
        mCommandList->ExecuteIndirect(mObjectCommandSignature.Get(), 1, mObjectCounters.Get(), TuftArguments * sizeof(UINT), nullptr, 0);
        }
    }
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 5);
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 10);
    // The plants: the near ones' meshes, the depth pyramid they leave, then the far ones' impostors it does not hide
    // (docs/vegetation-hiz.md); in the diagnostic views, all of them.
    const bool usePlantHiZ = earthDetailed && mPlanetFoliage.Enabled() && mDiagnosticView == 0.0f;
    if (usePlantHiZ) {
        mPlanetFoliage.DrawOccluders(mCommandList.Get(), mConstantBuffer->GetGPUVirtualAddress(), GpuDescriptor(LutSrv), GpuDescriptor(PlanetMapSrv));
        mCommandList->OMSetRenderTargets(0, nullptr, FALSE, nullptr);
        if (mSettings.batch) mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 14);
        mFoliageHiZ.Build(mCommandList.Get(), mDepthStencilBuffer.Get());
        if (mSettings.batch) mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 15);
        if (mSettings.batch) mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 16);
        mPlanetFoliage.CullOccluded(mCommandList.Get(), mConstantBuffer->GetGPUVirtualAddress(), mFoliageHiZ.Srv(),
            mFoliageHiZ.Width(), mFoliageHiZ.Height(), mFoliageHiZ.MipCount(), mClientWidth, mClientHeight);
        if (mSettings.batch) mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 17);
        // Both colour attachments belong to the same visible surface, also after HiZ.
        mCommandList->OMSetRenderTargets(2, sceneRtvs, FALSE, &dsvHandle);
        mPlanetFoliage.DrawRemaining(mCommandList.Get(), mConstantBuffer->GetGPUVirtualAddress(), GpuDescriptor(LutSrv), GpuDescriptor(PlanetMapSrv));
    } else {
        if (mSettings.batch) for (UINT query = 14; query < 18; ++query)
            mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, query);
        if(earthDetailed)mPlanetFoliage.Draw(mCommandList.Get(), mConstantBuffer->GetGPUVirtualAddress(), GpuDescriptor(LutSrv), GpuDescriptor(PlanetMapSrv));
    }
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 11);
    // The terrain's colour, on the pixels its depth still holds: those neither the plants, the objects nor the terrain
    // itself hide.
    if (terrainDepthFirst) {
        mCommandList->OMSetRenderTargets(2, sceneRtvs, FALSE, &dsvHandle);
        mCommandList->RSSetViewports(1, &viewport);
        mCommandList->RSSetScissorRects(1, &scissor);
        if (airless)
            drawTerrain(mAirlessShadePSO.Get());
        else {
            // Under the screen relief at full weight, no pixel refines its contour (PixelShaderScreen.hlsl). Elsewhere the face's
            // cells where none may refine take that shader too, the others and the rings the whole one (TerrainContourCells.hlsl).
            // Near the ground, both with the rock's near detail (PixelShaderNear.hlsl).
            const bool nearDetail = clearance < NearDetailClearance;
            ID3D12PipelineState* const shadePso = nearDetail ? mTerrainShadeNearPSO.Get() : mTerrainShadePSO.Get();
            ID3D12PipelineState* const screenPso = nearDetail ? mTerrainShadeScreenNearPSO.Get() : mTerrainShadeScreenPSO.Get();
            if (mConstants->screenRelief.z >= 1.0f)
                drawTerrain(screenPso);
            else {
                const UINT faceIndices = 6 * FaceCells * FaceCells;
                const CD3DX12_RESOURCE_BARRIER toSort[2] = {
                    CD3DX12_RESOURCE_BARRIER::Transition(mContourCellArgs.Get(), D3D12_RESOURCE_STATE_COMMON, D3D12_RESOURCE_STATE_COPY_DEST),
                    CD3DX12_RESOURCE_BARRIER::Transition(mContourCellLists.Get(), D3D12_RESOURCE_STATE_COMMON,
                        D3D12_RESOURCE_STATE_UNORDERED_ACCESS) };
                mCommandList->ResourceBarrier(2, toSort);
                mCommandList->CopyBufferRegion(mContourCellArgs.Get(), 0, mContourCellArgsStart.Get(), 0,
                    2 * sizeof(D3D12_DRAW_INDEXED_ARGUMENTS));
                const auto argsToWrite = CD3DX12_RESOURCE_BARRIER::Transition(mContourCellArgs.Get(), D3D12_RESOURCE_STATE_COPY_DEST,
                    D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
                mCommandList->ResourceBarrier(1, &argsToWrite);
                mCommandList->SetComputeRootSignature(mContourCellsRootSignature.Get());
                mCommandList->SetPipelineState(mContourCellsPSO.Get());
                mCommandList->SetComputeRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
                mCommandList->SetComputeRootShaderResourceView(1, mFaceVertexBuffer->GetGPUVirtualAddress());
                mCommandList->SetComputeRootShaderResourceView(2, mFineNormals->GetGPUVirtualAddress());
                mCommandList->SetComputeRootUnorderedAccessView(3, mContourCellLists->GetGPUVirtualAddress());
                mCommandList->SetComputeRootUnorderedAccessView(4, mContourCellArgs->GetGPUVirtualAddress());
                mCommandList->Dispatch((FaceCells * FaceCells + 63) / 64, 1, 1);
                const CD3DX12_RESOURCE_BARRIER toDraw[2] = {
                    CD3DX12_RESOURCE_BARRIER::Transition(mContourCellArgs.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                        D3D12_RESOURCE_STATE_INDIRECT_ARGUMENT),
                    CD3DX12_RESOURCE_BARRIER::Transition(mContourCellLists.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS,
                        D3D12_RESOURCE_STATE_INDEX_BUFFER) };
                mCommandList->ResourceBarrier(2, toDraw);
                bindTerrain(shadePso);
                if (indexCount > faceIndices) // the rings, from the mesh's own indices
                    mCommandList->DrawIndexedInstanced(indexCount - faceIndices, 1, faceIndices, 0, 0);
                mCommandList->IASetIndexBuffer(&mContourCellView);
                mCommandList->ExecuteIndirect(mObjectCommandSignature.Get(), 1, mContourCellArgs.Get(), 0, nullptr, 0);
                mCommandList->SetPipelineState(screenPso);
                mCommandList->ExecuteIndirect(mObjectCommandSignature.Get(), 1, mContourCellArgs.Get(),
                    sizeof(D3D12_DRAW_INDEXED_ARGUMENTS), nullptr, 0);
                mCommandList->IASetIndexBuffer(&mIndexBufferView);
            }
        }
    }
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 21);

    // Finite bodies share depth with the world: a foreground moon can occult the planet, and its finite distance
    // reaches the cloud clipping and temporal reprojection paths. Solar alpha identifies local bright-disc adaptation.
    if(mDiagnosticView==0.0f) {
        mCommandList->OMSetRenderTargets(2,sceneRtvs,FALSE,&dsvHandle);
        mCommandList->RSSetViewports(1,&viewport); mCommandList->RSSetScissorRects(1,&scissor);
        mCommandList->SetGraphicsRootSignature(mCelestialRoot.Get());
        mCommandList->SetGraphicsRootConstantBufferView(0,mConstantBuffer->GetGPUVirtualAddress());
        mCommandList->SetGraphicsRootDescriptorTable(3,GpuDescriptor(AirlessMaterialSrv));
        mCommandList->SetGraphicsRootDescriptorTable(5,GpuDescriptor(PlanetMapSrv));
        mCommandList->SetGraphicsRootDescriptorTable(6,GpuDescriptor(TectonicSrv+2));
        mCommandList->SetPipelineState(mCelestialBodiesPSO.Get());
        mCommandList->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
        for(unsigned body=0;body<8;++body) {
            if((int(body)==mMoonMesh) || (body==7 && earthProxy==0))continue;
            const Vec3d centre=body==7?Vec3d{}:Vec3d{celestialBodies[body].position.x*1000,celestialBodies[body].position.y*1000,celestialBodies[body].position.z*1000};
            const double radius=body==7?PlanetRadius+(earthDetailed?kMaxElevation:0):celestialBodies[body].radius*1000;
            D3D12_RECT bounds;
            if(!CelestialRect(centre,radius,bounds))continue;
            if(body<Celestial::MoonCount)mCommandList->SetGraphicsRootDescriptorTable(3,GpuDescriptor(AirlessMaterialSrv+body));
            if(body==7 && earthDetailed)mCommandList->SetPipelineState(mEarthProxyBlendPSO.Get());
            mCommandList->RSSetScissorRects(1,&bounds);
            const unsigned selected[]={body,body==7 && earthDetailed?unsigned(kMaxElevation):0u};
            mCommandList->SetGraphicsRoot32BitConstants(4,2,selected,0);
            const float opacity=body==7?earthProxy:1.0f,blend[]={opacity,opacity,opacity,opacity};
            mCommandList->OMSetBlendFactor(blend);
            mCommandList->DrawInstanced(3,1,0,0);
        }
        mCommandList->RSSetScissorRects(1,&scissor);

    }

    // 3. The atmosphere over the scene, into the composite image.
    const D3D12_RESOURCE_STATES sceneRead = D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE | D3D12_RESOURCE_STATE_NON_PIXEL_SHADER_RESOURCE;
    const CD3DX12_RESOURCE_BARRIER sceneToRead[2] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mHdrTarget.Get(), D3D12_RESOURCE_STATE_RENDER_TARGET, sceneRead),
        CD3DX12_RESOURCE_BARRIER::Transition(mSunPart.Get(), D3D12_RESOURCE_STATE_RENDER_TARGET, sceneRead) };
    mCommandList->ResourceBarrier(2, sceneToRead);
    ApplyLocalContacts();
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 18);
    CD3DX12_CPU_DESCRIPTOR_HANDLE compositeRtv(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), CompositeRtv, mRtvDescriptorSize);
    const CD3DX12_CPU_DESCRIPTOR_HANDLE skyTransportRtv(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), SkyTransportRtv, mRtvDescriptorSize);
    const D3D12_CPU_DESCRIPTOR_HANDLE atmosphereTargets[2] = {compositeRtv, skyTransportRtv};
    mCommandList->OMSetRenderTargets(2, atmosphereTargets, FALSE, nullptr);
    mCommandList->SetGraphicsRootSignature(mPostRootSignature.Get());
    mCommandList->SetPipelineState(mAtmospherePSO.Get());
    mCommandList->SetGraphicsRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetGraphicsRootDescriptorTable(1, GpuDescriptor(HdrSrv));
    mCommandList->SetGraphicsRootShaderResourceView(2, mFaceVertexBuffer->GetGPUVirtualAddress());
    mCommandList->SetGraphicsRootDescriptorTable(3, GpuDescriptor(SunSrv));
    mCommandList->SetGraphicsRootConstantBufferView(4, mCloudConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetGraphicsRootDescriptorTable(5, GpuDescriptor(CloudSrv));
    mCommandList->SetGraphicsRootDescriptorTable(6, GpuDescriptor(PlanetMapSrv));
    if (cloudTemporal) {
        // The clouds over time (CloudsTemporal.hlsli): one pixel per 4x4 tile traced into the fresh images, one per
        // 2x2 quad where the history has drifted, then the full-resolution resolve, into the composite and the other history.
        const UINT read = mCloudHistoryIndex, write = 1 - read;
        auto rtv = [&](UINT i) { return CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), i, mRtvDescriptorSize); };
        mCommandList->SetGraphicsRootDescriptorTable(7, GpuDescriptor(CloudTemporalSrv + 7 * read));
        const D3D12_CPU_DESCRIPTOR_HANDLE freshRtvs[2] = { rtv(CloudFreshRtv), rtv(CloudFreshRtv + 1) };
        mCommandList->OMSetRenderTargets(2, freshRtvs, FALSE, nullptr);
        const UINT tileWidth = (mClientWidth + CloudTileX - 1) / CloudTileX, tileHeight = (mClientHeight + CloudTileY - 1) / CloudTileY;
        const CD3DX12_VIEWPORT tileViewport(0.0f, 0.0f, float(tileWidth), float(tileHeight));
        const CD3DX12_RECT tileScissor(0, 0, LONG(tileWidth), LONG(tileHeight));
        mCommandList->RSSetViewports(1, &tileViewport);
        mCommandList->RSSetScissorRects(1, &tileScissor);
        mCommandList->SetPipelineState(mCloudTracePSO.Get());
        mCommandList->DrawInstanced(3, 1, 0, 0);
        // The drifted pixels, one per 2x2 quad below 14 km (CloudTemporalHalfOn);
        // above, the resolve does not read them.
        if (mConstants->camVertical.w <= 14.0f) {
            const D3D12_CPU_DESCRIPTOR_HANDLE halfRtvs[2] = { rtv(CloudHalfRtv), rtv(CloudHalfRtv + 1) };
            mCommandList->OMSetRenderTargets(2, halfRtvs, FALSE, nullptr);
            const UINT halfWidth = (mClientWidth + 1) / 2, halfHeight = (mClientHeight + 1) / 2;
            const CD3DX12_VIEWPORT halfViewport(0.0f, 0.0f, float(halfWidth), float(halfHeight));
            const CD3DX12_RECT halfScissor(0, 0, LONG(halfWidth), LONG(halfHeight));
            mCommandList->RSSetViewports(1, &halfViewport);
            mCommandList->RSSetScissorRects(1, &halfScissor);
            mCommandList->SetPipelineState(mCloudHalfPSO.Get());
            mCommandList->DrawInstanced(3, 1, 0, 0);
        }
        mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 20);
        mCommandList->RSSetViewports(1, &viewport);
        mCommandList->RSSetScissorRects(1, &scissor);
        CD3DX12_RESOURCE_BARRIER freshToRead[4];
        for (UINT i = 0; i < 4; ++i)
            freshToRead[i] = CD3DX12_RESOURCE_BARRIER::Transition(mCloudFresh[i].Get(), D3D12_RESOURCE_STATE_RENDER_TARGET,
                D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
        mCommandList->ResourceBarrier(4, freshToRead);
        const D3D12_CPU_DESCRIPTOR_HANDLE resolveTargets[5] = { compositeRtv, rtv(CloudHistoryRtv + 3 * write),
            rtv(CloudHistoryRtv + 3 * write + 1), rtv(CloudHistoryRtv + 3 * write + 2), skyTransportRtv };
        mCommandList->OMSetRenderTargets(5, resolveTargets, FALSE, nullptr);
        mCommandList->SetPipelineState(mCloudResolvePSO.Get());
        mCommandList->DrawInstanced(3, 1, 0, 0);
        CD3DX12_RESOURCE_BARRIER afterClouds[10];
        for (UINT i = 0; i < 2; ++i) {
            afterClouds[i] = CD3DX12_RESOURCE_BARRIER::Transition(mCloudFresh[i].Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,
                D3D12_RESOURCE_STATE_RENDER_TARGET);
            afterClouds[8 + i] = CD3DX12_RESOURCE_BARRIER::Transition(mCloudFresh[2 + i].Get(),
                D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_RENDER_TARGET);
        }
        for (UINT i = 0; i < 3; ++i) {
            afterClouds[2 + i] = CD3DX12_RESOURCE_BARRIER::Transition(mCloudHistory[write][i].Get(),
                D3D12_RESOURCE_STATE_RENDER_TARGET, D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
            afterClouds[5 + i] = CD3DX12_RESOURCE_BARRIER::Transition(mCloudHistory[read][i].Get(),
                D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_RENDER_TARGET);
        }
        mCommandList->ResourceBarrier(10, afterClouds);
        mCloudHistoryIndex = write;
    } else {
        mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 20);
        mCommandList->DrawInstanced(3, 1, 0, 0);
    }
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 19);
    // Physical optics, read from the composite and added by the tone map: stellar visibility reads the sky without it.
    const bool glareDrawn = mSettings.glare && mDiagnosticView == 0.0f;
    if (glareDrawn) mGlare.Draw(mCommandList.Get(), mSrvHeap.Get());

    // 4. Temporal smoothing and tone map: the composite and the previous result, to the screen and to the
    // other history image.
    const UINT next = 1 - mHistoryIndex;
    CD3DX12_RESOURCE_BARRIER toResolve[] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mComposite.Get(), D3D12_RESOURCE_STATE_RENDER_TARGET,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mRenderTargets[mFrameIndex].Get(), D3D12_RESOURCE_STATE_PRESENT,
            D3D12_RESOURCE_STATE_RENDER_TARGET),
        CD3DX12_RESOURCE_BARRIER::Transition(mSkyTransport.Get(), D3D12_RESOURCE_STATE_RENDER_TARGET,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE) };
    mCommandList->ResourceBarrier(_countof(toResolve), toResolve);
    // Diffuse galactic light and point images share the exact resolved atmospheric/cloud transport.
    const CD3DX12_CPU_DESCRIPTOR_HANDLE celestialRtv(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), CelestialRtv, mRtvDescriptorSize);
    mCommandList->OMSetRenderTargets(1,&celestialRtv,FALSE,nullptr);
    mCommandList->SetGraphicsRootSignature(mCelestialRoot.Get());
    mCommandList->SetGraphicsRootConstantBufferView(0,mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetGraphicsRootDescriptorTable(1,GpuDescriptor(CompositeSrv));
    mCommandList->SetGraphicsRootDescriptorTable(2,GpuDescriptor(SkyTransportSrv));
    mCommandList->SetPipelineState(mGalaxyPSO.Get());
    mCommandList->DrawInstanced(3,1,0,0);
    if(mDiagnosticView<0.5f) {
        mCommandList->SetPipelineState(mStarsPSO.Get());
        mCommandList->DrawInstanced(6,Celestial::StarCount+6,0,0);
    }
    const auto celestialToRead=CD3DX12_RESOURCE_BARRIER::Transition(mCelestialTarget.Get(),
        D3D12_RESOURCE_STATE_RENDER_TARGET,D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE);
    mCommandList->ResourceBarrier(1,&celestialToRead);
    // The ship's glass, over the composite read as an image, into the overlay the tone map applies after the smoothing.
    mShip.ClearOverlay(mCommandList.Get());
    if (shipDrawn) {
        *mShipCloudConstants = *mCloudConstants;
        mShipCloudConstants->cameraKm[0] = mShipPos.x * 0.001;
        mShipCloudConstants->cameraKm[1] = mShipPos.y * 0.001;
        mShipCloudConstants->cameraKm[2] = mShipPos.z * 0.001;
        Ship::Tables weatherTables = shipTables;
        weatherTables.cloudFrame = mShipCloudConstantBuffer->GetGPUVirtualAddress();
        mShip.UpdateWeather(mCommandList.Get(), weatherTables);
        mCommandList->RSSetViewports(1, &viewport);
        mCommandList->RSSetScissorRects(1, &scissor);
        mShip.DrawGlass(mCommandList.Get(), shipTables, dsvHandle);
    }
    mShip.OverlayToRead(mCommandList.Get());
    {   // The local adaptation: its first level with the tone map's bindings, then its pyramid (Adaptation.h).
        const D3D12_CPU_DESCRIPTOR_HANDLE seedRtv = mAdaptation.SeedTarget();
        const CD3DX12_VIEWPORT seedViewport(0.0f, 0.0f, float(mAdaptation.SeedWidth()), float(mAdaptation.SeedHeight()));
        const CD3DX12_RECT seedScissor(0, 0, LONG(mAdaptation.SeedWidth()), LONG(mAdaptation.SeedHeight()));
        mCommandList->RSSetViewports(1, &seedViewport);
        mCommandList->RSSetScissorRects(1, &seedScissor);
        mCommandList->OMSetRenderTargets(1, &seedRtv, FALSE, nullptr);
        mCommandList->SetGraphicsRootSignature(mResolveRootSignature.Get());
        mCommandList->SetPipelineState(mAdaptSeedPSO.Get());
        mCommandList->SetGraphicsRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
        mCommandList->SetGraphicsRootDescriptorTable(1, GpuDescriptor(CompositeSrv));
        mCommandList->SetGraphicsRootDescriptorTable(3, GpuDescriptor(LutSrv));
        mCommandList->SetGraphicsRootDescriptorTable(6, GpuDescriptor(glareDrawn ? GlareSrv : GlareSrv + 1));
        mCommandList->DrawInstanced(3, 1, 0, 0);
        mAdaptation.Downsample(mCommandList.Get(), mSrvHeap.Get());
    }
    const D3D12_CPU_DESCRIPTOR_HANDLE resolveRtvs[2] = {
        CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), mFrameIndex, mRtvDescriptorSize),
        CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), HistoryRtv + next, mRtvDescriptorSize) };
    mCommandList->OMSetRenderTargets(2, resolveRtvs, FALSE, nullptr);
    mCommandList->SetGraphicsRootSignature(mResolveRootSignature.Get());
    mCommandList->SetPipelineState(mToneMapPSO.Get());
    mCommandList->SetGraphicsRootConstantBufferView(0, mConstantBuffer->GetGPUVirtualAddress());
    mCommandList->SetGraphicsRootDescriptorTable(1, GpuDescriptor(CompositeSrv));
    mCommandList->SetGraphicsRootDescriptorTable(2, GpuDescriptor(HistorySrv + mHistoryIndex));
    mCommandList->SetGraphicsRootDescriptorTable(3, GpuDescriptor(LutSrv));
    mCommandList->SetGraphicsRootDescriptorTable(4, mShip.OverlaySrv());
    mCommandList->SetGraphicsRootDescriptorTable(5, GpuDescriptor(SkyTransportSrv));
    mCommandList->SetGraphicsRootDescriptorTable(6, GpuDescriptor(glareDrawn ? GlareSrv : GlareSrv + 1));
    mCommandList->SetGraphicsRootDescriptorTable(7, GpuDescriptor(AdaptationSrv));
    mCommandList->DrawInstanced(3, 1, 0, 0);
    if (glareDrawn) mGlare.Release(mCommandList.Get());
    mAdaptation.Release(mCommandList.Get());
    mShip.OverlayToTarget(mCommandList.Get());
    CD3DX12_RESOURCE_BARRIER afterResolve[] = {
        CD3DX12_RESOURCE_BARRIER::Transition(mSkyTransport.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_RENDER_TARGET),
        CD3DX12_RESOURCE_BARRIER::Transition(mCelestialTarget.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, D3D12_RESOURCE_STATE_RENDER_TARGET),
        CD3DX12_RESOURCE_BARRIER::Transition(mHdrTarget.Get(), sceneRead, D3D12_RESOURCE_STATE_RENDER_TARGET),
        CD3DX12_RESOURCE_BARRIER::Transition(mSunPart.Get(), sceneRead, D3D12_RESOURCE_STATE_RENDER_TARGET),
        CD3DX12_RESOURCE_BARRIER::Transition(mComposite.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,
            D3D12_RESOURCE_STATE_RENDER_TARGET),
        CD3DX12_RESOURCE_BARRIER::Transition(mHistory[next].Get(), D3D12_RESOURCE_STATE_RENDER_TARGET,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE),
        CD3DX12_RESOURCE_BARRIER::Transition(mHistory[mHistoryIndex].Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,
            D3D12_RESOURCE_STATE_RENDER_TARGET) };
    mCommandList->ResourceBarrier(_countof(afterResolve), afterResolve);
    mHistoryIndex = next;
    mHistoryValid = true;

    const UINT trembleIndex = trembleTest ? mFrameNumber - TrembleWarmup : 0;
    const bool batchCapture = !mBatch.empty() && mBatchFrame == BatchCaptureFrame();
    const bool capture = (!mSettings.capturePath.empty() && mFrameNumber == mSettings.captureFrame)
                       || (trembleIndex >= 1 && trembleIndex <= mSettings.trembleFrames)
                       || batchCapture || (!mCine.empty() && mCineLead == 0 && mCineIndex >= mSettings.cineFirst);
    const D3D12_RESOURCE_STATES afterDraw = capture ? D3D12_RESOURCE_STATE_COPY_SOURCE : D3D12_RESOURCE_STATE_PRESENT;
    auto toPresent = CD3DX12_RESOURCE_BARRIER::Transition(mRenderTargets[mFrameIndex].Get(),
        D3D12_RESOURCE_STATE_RENDER_TARGET, afterDraw);
    mCommandList->ResourceBarrier(1, &toPresent);
    mCommandList->EndQuery(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 2);
    mCommandList->ResolveQueryData(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 0, mSettings.batch ? 18 : 12, mTimestampBuffer.Get(), 0);
    mCommandList->ResolveQueryData(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 18, 5, mTimestampBuffer.Get(), 18 * sizeof(UINT64));
    if (mScreenUpdated) mCommandList->ResolveQueryData(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 23, 12,
        mTimestampBuffer.Get(), 23 * sizeof(UINT64));
    mCommandList->ResolveQueryData(mTimestampHeap.Get(), D3D12_QUERY_TYPE_TIMESTAMP, 35, 4,
        mTimestampBuffer.Get(), 35 * sizeof(UINT64));
    if (capture && mScreenCaptureBuffer && mConstants->screenRelief.z > 0.0f) {
        auto screenToCopy = CD3DX12_RESOURCE_BARRIER::Transition(mScreenPositions.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,
            D3D12_RESOURCE_STATE_COPY_SOURCE);
        mCommandList->ResourceBarrier(1, &screenToCopy);
        const UINT64 bytes = UINT64(ScreenSampleBytes) * UINT(mConstants->screenRelief.x) * UINT(mConstants->screenRelief.y);
        mCommandList->CopyBufferRegion(mScreenCaptureBuffer.Get(), 0, mScreenPositions.Get(), 0, bytes);
    }
    if (capture) {
        CD3DX12_TEXTURE_COPY_LOCATION dst(mCaptureBuffer.Get(), mCaptureFootprint);
        CD3DX12_TEXTURE_COPY_LOCATION src(mRenderTargets[mFrameIndex].Get(), 0);
        mCommandList->CopyTextureRegion(&dst, 0, 0, 0, &src, nullptr);
        auto copyToPresent = CD3DX12_RESOURCE_BARRIER::Transition(mRenderTargets[mFrameIndex].Get(),
            D3D12_RESOURCE_STATE_COPY_SOURCE, D3D12_RESOURCE_STATE_PRESENT);
        mCommandList->ResourceBarrier(1, &copyToPresent);
    }
    mCommandList->Close();
    QueryPerformanceCounter(&cpuMarks[2]);

    ID3D12CommandList* lists[] = { mCommandList.Get() };
    mCommandQueue->ExecuteCommandLists(_countof(lists), lists);
    const UINT presentFlags=!mSettings.vsync && mAllowTearing ? DXGI_PRESENT_ALLOW_TEARING : 0;
    if (FAILED(mSwapChain->Present(mSettings.vsync ? 1 : 0, presentFlags))) { // say why the GPU gave up, rather than freeze or vanish
        if (mGpuBreadcrumbs) {
            ComPtr<ID3D12DeviceRemovedExtendedData1> dred;
            D3D12_DRED_AUTO_BREADCRUMBS_OUTPUT1 output = {};
            if (SUCCEEDED(md3dDevice.As(&dred)) && SUCCEEDED(dred->GetAutoBreadcrumbsOutput1(&output))) {
                for (auto node = output.pHeadAutoBreadcrumbNode; node; node = node->pNext) {
                    const UINT last = node->pLastBreadcrumbValue ? *node->pLastBreadcrumbValue : 0;
                    fprintf(stderr, "DRED command list: %u / %u completed\n", last, node->BreadcrumbCount);
                    for (UINT i = last > 12 ? last - 12 : 0; i < std::min(last + 12, node->BreadcrumbCount); ++i)
                        fprintf(stderr, "  operation %u = %u\n", i, UINT(node->pCommandHistory[i]));
                    for (UINT i = 0; i < node->BreadcrumbContextsCount; ++i)
                        fprintf(stderr, "  context %u: %ls\n", node->pBreadcrumbContexts[i].BreadcrumbIndex, node->pBreadcrumbContexts[i].pContextString);
                }
            }
        }
        char reason[96];
        sprintf_s(reason, "GPU lost (device removed reason 0x%08X).", (unsigned)md3dDevice->GetDeviceRemovedReason());
        throw std::runtime_error(reason);
    }
    QueryPerformanceCounter(&cpuMarks[3]);
    WaitForPreviousFrame();
    QueryPerformanceCounter(&cpuMarks[4]);

    ReadGpuTimes();
    mPlanetFoliage.ReadStats();
    SumBatchTimes(cpuMarks, usePlantHiZ);
    UpdateTitle(dt, NearMoon(mCamPos)?std::max(.01,SurfaceAltitude(mCamPos)-mGroundHeight):clearance, halfWidth, ringCount);

    if (capture) SaveCapture(batchCapture, trembleIndex);
    if (!mCine.empty()) EndCineFrame();
}

// Adds this frame's GPU times, from the timestamps resolved at the end of the frame.
void D3DApp::ReadGpuTimes() {
    UINT64* ticks = nullptr;
    CD3DX12_RANGE readRange(0, ScreenTimestampCount * sizeof(UINT64));
    if (FAILED(mTimestampBuffer->Map(0, &readRange, reinterpret_cast<void**>(&ticks)))) return;
    const double ms = 1000.0 / double(mTimestampFrequency);
    const double placement = ms * double(ticks[3] - ticks[1]), objects = ms * double(ticks[5] - ticks[4]);
    mFoliagePlaceMs = ms * double(ticks[9] - ticks[8]);
    mFoliageDrawMs = ms * double(ticks[11] - ticks[10]);
    mFrameGpuMs = ms * double(ticks[2] - ticks[0]);
    mPlantPlacementMs = mSettings.batch ? ms * double(ticks[13] - ticks[12]) : 0.0;
    mHiZBuildMs = mSettings.batch ? ms * double(ticks[15] - ticks[14]) : 0.0;
    mHiZCullMs = mSettings.batch ? ms * double(ticks[17] - ticks[16]) : 0.0;
    mComputeMs += ms * double(ticks[1] - ticks[0]);
    mPerfScreenLast = ms * double(ticks[1] - ticks[22]);
    for (UINT i = 0; i < 4; ++i)
        mPerfTerrainParts[i] = ms * double(ticks[35 + i] - ticks[i == 0 ? 7 : 34 + i]);
    for (UINT i = 0; i < 6; ++i) mPerfScreenParts[i] = mScreenUpdated
        ? ms * double((ticks[23 + i] - ticks[22 + i]) + (ticks[29 + i] - ticks[28 + i])) : 0.0;
    mScreenReliefMs += mPerfScreenLast;
    mDrawMs += ms * double(ticks[2] - ticks[1]) - placement - objects;
    mObjectMs += placement;
    mObjectDrawMs += objects;
    mGpuFrameLastMs = ms * double(ticks[2] - ticks[0]);
    mCloudPassLastMs = ms * double(ticks[19] - ticks[18]);
    mCloudPassMs += mCloudPassLastMs;
    mDrawMinMs = std::min(mDrawMinMs, ms * double(ticks[2] - ticks[1]) - placement - objects);
    mOceanMs += ms * double(ticks[7] - ticks[6]);
    if (mSettings.batch) { // in the order of the frame; tools/banc_perf.py names them
        const UINT marks[PerfGpu][2] = { { 6, 7 }, { 0, 1 }, { 1, 12 }, { 12, 13 }, { 13, 8 }, { 8, 9 }, { 3, 4 }, { 4, 5 },
                                            { 5, 11 }, { 11, 18 }, { 18, 20 }, { 18, 19 }, { 19, 2 }, { 0, 2 } };
        for (UINT i = 0; i < PerfGpu; ++i) mPerfLast[i] = ms * double(INT64(ticks[marks[i][1]] - ticks[marks[i][0]]));
        mPerfLast[PerfGpu + 5] = mPerfGpuEnd ? ms * double(INT64(ticks[0] - mPerfGpuEnd)) : 0.0; // idle since the last frame
        mPerfGpuEnd = ticks[2];
        mPerfLast[1] -= mPerfLast[0]; // the terrain's compute, less the sea's
        const double terrainShade = ms * double(INT64(ticks[21] - ticks[11])); // the terrain's colour, after the plants
        mPerfLast[6] += terrainShade;
        mPerfLast[9] -= terrainShade;
    }
    CD3DX12_RANGE noWrite(0, 0);
    mTimestampBuffer->Unmap(0, &noWrite);
    UINT* counters = nullptr;
    CD3DX12_RANGE countersRange(0, ObjectCounters * sizeof(UINT));
    if (SUCCEEDED(mObjectReadback->Map(0, &countersRange, reinterpret_cast<void**>(&counters)))) {
        std::copy(counters, counters + ObjectCounters, mObjectStats);
        mObjectReadback->Unmap(0, &noWrite);
    }
}

void D3DApp::UpdateTitle(float dt, double clearance, double halfWidth, UINT ringCount) {
    mTitleTimer += dt;
    ++mTitleFrames;
    if (mTitleTimer < 0.25f) return;

    wchar_t title[2048];
    swprintf_s(title, L"MyPlanetEngine | hauteur %s | sol %s | face \u00B1%s (k=%g) | %u anneaux | vitesse x%.2f"
        L" | GPU calcul %.1f ms (FFT %.2f, ecran %.1f), rendu %.2f ms (min %.2f), objets %.2f + %.2f ms | %.0f fps%s",
        FormatDistance(clearance).c_str(), FormatDistance(mGroundHeight).c_str(), FormatDistance(halfWidth).c_str(),
        mFaceFactor, ringCount, mSpeedFactor, mComputeMs / mTitleFrames, mOceanMs / mTitleFrames, mScreenReliefMs / mTitleFrames, mDrawMs / mTitleFrames, mDrawMinMs, mObjectMs / mTitleFrames,
        mObjectDrawMs / mTitleFrames,
        mTitleFrames / mTitleTimer, mWireframe ? L" | fil de fer" : L"");
    wchar_t cloudTimes[64];
    swprintf_s(cloudTimes, L" | nuages+air %.2f ms", mCloudPassMs / mTitleFrames);
    wcscat_s(title, cloudTimes);
    if (mMeshFrozen) wcscat_s(title, L" | MAILLAGE FIG\u00C9 (G)");
    if (mFaceted) wcscat_s(title, L" | facettes (R)");
    if (!TemporalAA()) wcscat_s(title, L" | sans lissage (T)");
    if (mView == View::Walk) {
        wchar_t walk[128];
        swprintf_s(walk,L" | marche %.2f m/s | J : vaisseau | Maj : courir | Ctrl : accroupir | H : balancement",Length(mWalkVelocity));
        wcscat_s(title,walk);
    } else if (mView != View::Free) {
        wchar_t ship[80];
        swprintf_s(ship, L" | %s : %s, %.0f m/s (Tab)", mShip.Profile().name, mView == View::Cockpit ? L"cockpit" : mView == View::Chase ? L"poursuite" : L"sans vaisseau", Length(mShipVelocity));
        wcscat_s(title, ship);
    } else if (!mSettings.Automated()) {
        const wchar_t* camera = mCameraMode == CameraMode::Horizon ? L" | Cam\u00e9ra horizon (D\u00e9but)"
            : mCameraMode == CameraMode::FixedAltitude ? L" | Cam\u00e9ra altitude fixe (D\u00e9but)"
            : L" | Cam\u00e9ra libre (D\u00e9but)";
        wcscat_s(title, camera);
        if (mCameraMode != CameraMode::Free) {
            if (mCameraBody == Celestial::Exolune) wcscat_s(title, L" Exolune");
            else {
                wchar_t target[32];
                const bool lunar = mCameraBody < int(Celestial::MoonCount);
                swprintf_s(target, L" %s %d", lunar ? L"Lune" : L"Plan\u00e8te",
                    lunar ? mCameraBody + 1 : mCameraBody - int(Celestial::MoonCount) + 1);
                wcscat_s(title, target);
            }
        }
    }
    // The camera as the command line takes it: altitude, latitude, longitude, pitch down, heading.
    const Vec3d up = Normalize(mCamPos);
    const double lat = std::atan2(up.y, std::hypot(up.x, up.z)), lon = std::atan2(up.z, up.x);
    const Vec3d east = { -std::sin(lon), 0.0, std::cos(lon) }, north = Cross(east, up);
    const double toDegrees = 180.0 / XM_PI;
    wchar_t position[96];
    swprintf_s(position, L" | position %.1f %.5f %.5f %.1f %.1f", Length(mCamPos) - PlanetRadius, lat * toDegrees,
        lon * toDegrees, -std::asin(std::min(std::max(Dot(mCamForward, up), -1.0), 1.0)) * toDegrees,
        std::atan2(Dot(mCamForward, east), Dot(mCamForward, north)) * toDegrees);
    wcscat_s(title, position);
    wchar_t clouds[160];
    swprintf_s(clouds, L" | nuages | %s (C) | N : nuages %s | B : silhouette | Espace : pause | V : x5 | 1 : \u00E9rosion %s",
        mCloudsReference ? L"R\u00E9f\u00E9rence" : L"\u00C9co", mCloudsOn ? L"oui" : L"non",
        mErosionMode == 2 ? L"compl\u00E8te" : mErosionMode == 1 ? L"ravines" : L"sans");
    wcscat_s(title, clouds);
    if (!mLabel.empty()) { wcscat_s(title, L" | "); wcscat_s(title, mLabel.c_str()); }
    wchar_t weather[64];
    swprintf_s(weather, L" | meteo %.1f s %s x%.0f", mWeatherTime, mWeatherPaused ? L"pause" : L"", mWeatherRate);
    wcscat_s(title, weather);
    if (!mTestLabel.empty()) { wcscat_s(title, L" | test : "); wcscat_s(title, mTestLabel.c_str()); }
    wchar_t display[128];
    swprintf_s(display,L" | %ux%u %s | VSync %s%s",mClientWidth,mClientHeight,
        mFullscreen ? L"plein ecran" : L"fenetre",mSettings.vsync ? L"oui" : L"non",
        !mSettings.vsync && mAllowTearing ? L" (tearing autorise)" : L"");
    wcscat_s(title,display);
    wchar_t tectonics[320];
    swprintf_s(tectonics, L" | tectonique %.0f ms, %.0f Mo, %u volcans en %.0f ms | climat %.0f ms, %.1f Mo | meteo %.0f ms | erosion %.0f ms (reseau %.0f, couloirs %.0f, carte %.0f), %.0f Mo",
        mTectonicMs, mTectonicMb, mVolcanoCount, mVolcanoMs, mClimateMs, mClimateMb, mWeatherMapMs, mErosionMs, mErosionBuildMs, mErosionCoursesMs,
        mErosionRiverMapMs, mErosionMb);
    wcscat_s(title, tectonics);
    if (!mGpuName.empty()) { wcscat_s(title,L" | "); wcscat_s(title,mGpuName.c_str()); }
    mTitle = title;
    if (mPlanetFoliage.Enabled()) {
        wchar_t timings[96];
        swprintf_s(timings, L" | arbres GPU tri %.2f ms, dessin %.2f ms", mFoliagePlaceMs, mFoliageDrawMs);
        mTitle += timings;
        mTitle += mPlanetFoliage.StatsText();
        wchar_t overflow[128];
        swprintf_s(overflow, L" | pertes tuiles %u, plantes %u/%u", mObjectStats[37], mObjectStats[38], mObjectStats[39]);
        mTitle += overflow;
    }
    const std::wstring full = mTitle + ObjectStatsText();
    SetWindowText(mhMainWnd, full.c_str());
    if (!mSettings.capturePath.empty()) { // for the benches: the title, UTF-8, at <capture>.txt
        char utf8[2048];
        const int length = WideCharToMultiByte(CP_UTF8, 0, full.c_str(), -1, utf8, sizeof(utf8), nullptr, nullptr);
        FILE* f = nullptr;
        if (length > 0 && _wfopen_s(&f, (mSettings.capturePath + L".txt").c_str(), L"wb") == 0 && f) {
            fwrite(utf8, 1, length - 1, f);
            fclose(f);
        }
    }
    mTitleTimer = 0.0f;
    mTitleFrames = 0;
    mComputeMs = mDrawMs = mObjectMs = mObjectDrawMs = mCloudPassMs = mOceanMs = 0.0;
    mScreenReliefMs = 0.0;
    mCloudPassLastMs = mGpuFrameLastMs = 0.0;
    mDrawMinMs = 1e9;
}

// The objects of the last frame, and the gap between their feet and the ground the mesh draws.
std::wstring D3DApp::ObjectStatsText() const {
    const UINT* s = mObjectStats;
    wchar_t text[512];
    swprintf_s(text, L" | objets %u pierres, %u touffes sur %u candidats | \u00E9cart au sol : moyen %.2f mm, sous un pied %.1f mm"
        L" (%.0f %% de l'enfouissement, %u flottent), dessus %.1f mm (%.0f %% du visible), %.2f px au plus"
        L" | plantes %u + %u lointaines, %u flottent, de %.2f px au plus",
        s[DrawInstances], s[TuftInstances], s[Evaluated], s[Measured] ? 0.01 * s[GapSum] / s[Measured] : 0.0, 0.01 * s[GapBelow], 0.1 * s[FloatRatio],
        s[Floating], 0.01 * s[GapAbove], 0.1 * s[SinkRatio], 0.01 * s[GapPixels], s[PlantsPlaced], s[PlantsCoarse], s[PlantFloating], 0.01 * s[PlantGap]);
    return text;
}

D3D12_GPU_DESCRIPTOR_HANDLE D3DApp::GpuDescriptor(UINT index) const {
    const UINT size = md3dDevice->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    return CD3DX12_GPU_DESCRIPTOR_HANDLE(mSrvHeap->GetGPUDescriptorHandleForHeapStart(), index, size);
}

void D3DApp::WaitForPreviousFrame() {
    mFenceValue++;
    mCommandQueue->Signal(mFence.Get(), mFenceValue);

    if (mFence->GetCompletedValue() < mFenceValue) {
        mFence->SetEventOnCompletion(mFenceValue, mFenceEvent);
        WaitForSingleObject(mFenceEvent, INFINITE);
    }

    mFrameIndex = mSwapChain->GetCurrentBackBufferIndex();
}

LRESULT CALLBACK D3DApp::WindowProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    D3DApp* app = nullptr;
    if (msg == WM_NCCREATE) {
        app = static_cast<D3DApp*>(reinterpret_cast<CREATESTRUCT*>(lParam)->lpCreateParams);
        SetWindowLongPtr(hwnd, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(app));
    }
    else {
        app = reinterpret_cast<D3DApp*>(GetWindowLongPtr(hwnd, GWLP_USERDATA));
    }

    if (app) return app->MsgProc(hwnd, msg, wParam, lParam);
    else return DefWindowProc(hwnd, msg, wParam, lParam);
}

LRESULT D3DApp::MsgProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (!mCine.empty() && (msg == WM_INPUT || (msg >= WM_KEYFIRST && msg <= WM_KEYLAST) ||
        (msg >= WM_MOUSEFIRST && msg <= WM_MOUSELAST))) return DefWindowProc(hwnd, msg, wParam, lParam);
    switch (msg) {
    case WM_LBUTTONUP: {
        // The same pixel rectangles as ActionOverlay. Alt or M releases the raw FPS mouse to click them.
        if (!mSettings.Automated() && !mMouseHeld) {
            const int s=std::min(std::max(int(mClientWidth/640),1),3), x=GET_X_LPARAM(lParam), y=GET_Y_LPARAM(lParam);
            if (y>=12*s && y<33*s) {
                if (x>=12*s && x<114*s) { ToggleWalking(); return 0; }
                if (x>=118*s && x<220*s) { ToggleAudio(); return 0; }
            }
        }
        break;
    }
    case WM_INPUT: { // raw mouse motion, for the ship's views
        RAWINPUT input;
        UINT size = sizeof(input);
        if (GetRawInputData(reinterpret_cast<HRAWINPUT>(lParam), RID_INPUT, &input, &size, sizeof(RAWINPUTHEADER)) != UINT(-1)
            && input.header.dwType == RIM_TYPEMOUSE && !(input.data.mouse.usFlags & MOUSE_MOVE_ABSOLUTE) && mMouseHeld) {
            mRawDx += input.data.mouse.lLastX;
            mRawDy += input.data.mouse.lLastY;
        }
        break;
    }
    case WM_ACTIVATE: // the mouse is let go when another window takes the focus, held again when it comes back
        HoldMouse(LOWORD(wParam) != WA_INACTIVE && mView != View::Free);
        break;
    case WM_SYSKEYDOWN: // Alt held lets the cursor go, to reach the tests' palette; not the window menu's key
        if (wParam==VK_F10 && !(lParam & (1u<<29))) {
            if (!(lParam & (1u<<30)) && mTests.size()>9) GoToTest(9);
            return 0;
        }
        if (wParam==VK_RETURN && (lParam & (1u<<29)) && !(lParam & (1u<<30))) { ToggleFullscreen(); return 0; }
        if (wParam == VK_MENU) { HoldMouse(false); return 0; }
        break;
    case WM_SYSKEYUP:
        if (wParam == VK_F10) return 0;
        if (wParam == VK_MENU) { HoldMouse(mView != View::Free && GetForegroundWindow() == hwnd); return 0; }
        break;
    case WM_SYSCOMMAND:
        if ((wParam & 0xfff0u)==SC_KEYMENU) return 0; // Alt releases the mouse; F10 belongs to the route, not a modal menu
        break;
    case WM_RBUTTONDOWN:
        mLooking = true;
        mHeadFree = false;
        mLastMouse = { GET_X_LPARAM(lParam), GET_Y_LPARAM(lParam) };
        if (mView == View::Free) SetCapture(hwnd);
        return 0;
    case WM_RBUTTONUP:
        mLooking = false;
        mHeadKept = true; // released, the head stays where it looks and the mouse flies again; R brings it back
        if (mView == View::Free) ReleaseCapture();
        return 0;
    case WM_MOUSEMOVE:
        if (mLooking && mView == View::Free) {
            const POINT p = { GET_X_LPARAM(lParam), GET_Y_LPARAM(lParam) };
            mMouseDx += p.x - mLastMouse.x;
            mMouseDy += p.y - mLastMouse.y;
            mLastMouse = p;
        }
        return 0;
    case WM_MOUSEWHEEL:
        if (mView == View::Walk) return 0;
        if (mView != View::Free) { // the ship's gas, notch by notch; it stays where it is left
            mThrottle = std::min(std::max(mThrottle + GET_WHEEL_DELTA_WPARAM(wParam) / double(WHEEL_DELTA), 0.0), 30.0);
            return 0;
        }
        mSpeedFactor *= std::pow(1.5, GET_WHEEL_DELTA_WPARAM(wParam) / double(WHEEL_DELTA)); // smooth wheels send small deltas
        mSpeedFactor = std::min(std::max(mSpeedFactor, 0.01), 100.0);
        return 0;
    case WM_KEYDOWN:
        if (lParam & (1 << 30)) break; // ignore auto-repeat
        if (wParam == VK_HOME && mView == View::Free) {
            mCameraMode = FlightFrame::NextCameraMode(mCameraMode);
            if (mCameraMode == CameraMode::Horizon) {
                mCameraBody = -1; // acquire the local horizon once, then keep it when changing to fixed altitude
                mHistoryValid = mCloudHistoryValid = false;
            }
        }
        if (wParam == 'J') ToggleWalking();
        if (wParam == 'Y') ToggleAudio();
        if (wParam == VK_SPACE && mView == View::Walk) mWalkJump = true;
        if (wParam == 'H' && mView == View::Walk) mWalkBob = !mWalkBob;
        if (wParam == 'F') mWireframe = !mWireframe;
        if (wParam == 'G') mMeshFrozen = !mMeshFrozen; // diagnostic: the mesh stops following the camera
        if (wParam == 'R' && mView == View::Free) mFaceted = !mFaceted; // compare with the faceted shading
        if (wParam == 'R' && mView != View::Free) mHeadFree = mHeadKept = false; // the head back to rest
        if (wParam == 'T') mTaa = !mTaa;
        if (wParam == 'H' && mView == View::Free) // compare the trees' fade at the impostor-mesh relay with the hard switch;
            mFoliageFade = !mFoliageFade;          // in the ship's views H is the head's
        if (wParam == 'B') { // the ground's view under the clouds: their silhouette
            mDiagnosticView = mDiagnosticView > 0.5f ? 0.0f : 14.0f;
            mHistoryValid = false;
        }
        if (wParam == VK_SPACE && mView == View::Free) mWeatherPaused = !mWeatherPaused; // the ship climbs
        if (wParam == 'H' && mView != View::Free && mView != View::Walk) { // the mouse to the head and back; the head then stays put
            mHeadFree = !mHeadFree;
            mHeadKept = !mHeadFree;
        }
        if (wParam == 'U') mHud = !mHud; // the green head-up display
        if (wParam == 'I') mCoordinates = !mCoordinates;
        if (wParam == 'M' && mView != View::Free) { // the cursor to Windows and back, for a screenshot
            mMouseFree = !mMouseFree;
            HoldMouse(GetForegroundWindow() == hwnd);
        }
        if (wParam == 'V') mWeatherRate = mWeatherRate == 1.0 ? 5.0 : 1.0;
        if (wParam == 'N') mCloudsOn = !mCloudsOn;
        if (wParam == '1') { // the erosion shown, to compare in flight: full, ravines only, none. The mesh's kept vertices,
            // keyed on the view (TerrainInputs), and the plants' kept ground are computed afresh: kept, they showed the
            // previous erosion up close, where only the per-pixel water followed the switch.
            mErosionMode = (mErosionMode + 2u) % 3u;
            mTerrainKept = false;
            mPlanetPlantPlacement.Reset();
            mPlanetFoliageSamples.clear();
            mHistoryValid = false;
        }
        if (wParam == 'C') mCloudsReference = !mCloudsReference;
        if (wParam == 'K' || wParam == VK_SUBTRACT) mFaceFactor = std::max(mFaceFactor / 2.0, 0.25);
        if (wParam == 'L' || wParam == VK_ADD) mFaceFactor = std::min(mFaceFactor * 2.0, 64.0);
        if (wParam >= VK_F1 && wParam <= VK_F12 && size_t(wParam - VK_F1) < mTests.size()) GoToTest(wParam - VK_F1);
        if (wParam == VK_TAB && mShip.Ready()) // the cockpit, the chase view, the ship hidden
            SetView(mView == View::Cockpit ? View::Chase : mView == View::Chase ? View::Bare
                : mShip.Profile().cockpit ? View::Cockpit : View::Chase);
        if (wParam == VK_BACK && mShip.Ready()) // independent free camera and back to the cockpit
            SetView(mView == View::Free ? (mShip.Profile().cockpit ? View::Cockpit : View::Chase) : View::Free);
        if (wParam == VK_ESCAPE) { if (mFullscreen) ToggleFullscreen(); else DestroyWindow(hwnd); }
        return 0;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProc(hwnd, msg, wParam, lParam);
}
