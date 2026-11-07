// Offline cinema: absolute poses and time; only the GPU ground clamp may adjust them.
#include "D3DApp.h"
#include "GpuHelpers.h"
#include "Ocean.h"
#include <algorithm>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <limits>
#include <cstdio>

void D3DApp::ReadCine() {
    if (mSettings.cinePath.empty()) return;
    std::ifstream file(mSettings.cinePath.c_str());
    if (!file) throw std::runtime_error("Cannot open CINE path.");
    bool fps = false;
    UINT lineNumber = 0;
    for (std::string line; std::getline(file, line);) {
        ++lineNumber;
        if (lineNumber == 1 && line.compare(0, 3, "\xEF\xBB\xBF") == 0) line.erase(0, 3);
        line = line.substr(0, line.find('#'));
        std::istringstream in(line); in.imbue(std::locale::classic());
        std::string token, extra;
        if (!(in >> token)) continue;
        bool valid = true;
        if (!fps) {
            valid = token == "fps" && bool(in >> mCineFps) && std::isfinite(mCineFps) && mCineFps >= 1 && mCineFps <= 240;
            fps = valid;
        } else {
            CineFrame f = {}; std::string view;
            valid = token == std::to_string(mCine.size()) && bool(in >> view)
                && (view == "exterieur" || view == "cockpit" || view == "pleine");
            f.cockpit = view == "cockpit";
            f.bare = view == "pleine";
            for (double& x : f.nav) valid = bool(in >> x) && std::isfinite(x) && valid;
            for (double& x : f.cam) valid = bool(in >> x) && std::isfinite(x) && valid;
            valid = bool(in >> f.fov >> f.weather) && valid && std::isfinite(f.fov) && std::isfinite(f.weather)
                && f.fov >= 5 && f.fov <= 150 && f.weather >= 0;
            for (const double* p : { f.nav, f.cam })
                valid = valid && std::abs(p[0]) <= 90 && std::abs(p[1]) <= 180 && p[2] > -PlanetRadius;
            if (valid) mCine.push_back(f);
        }
        if (!valid || (in >> extra)) throw std::runtime_error("Invalid CINE line " + std::to_string(lineNumber));
    }
    if (!fps || mCine.empty() || mSettings.cineFirst >= mCine.size()) throw std::runtime_error("Empty CINE or first frame outside path.");
    const size_t end = mSettings.cineCount ? size_t(mSettings.cineFirst) + mSettings.cineCount : mCine.size();
    if (end > mCine.size()) throw std::runtime_error("CINE range exceeds path.");
    mCineEnd = (UINT)end;
    mCineIndex = mSettings.cineFirst - std::min(mSettings.cineFirst, mSettings.cineWarm);
    mCineLead = mSettings.cineWarm - std::min(mSettings.cineFirst, mSettings.cineWarm);
    // The caller creates the output folder: a misspelt path must fail before rendering.
    const DWORD attr = GetFileAttributesW(mSettings.cineOut.c_str());
    if (attr == INVALID_FILE_ATTRIBUTES || !(attr & FILE_ATTRIBUTE_DIRECTORY)) throw std::runtime_error("CINE output folder does not exist.");
    LogCine("debut");
}

void D3DApp::LogCine(const char* message) const {
    FILE* out = nullptr;
    if (_wfopen_s(&out, (mSettings.cineOut + L"\\cine.log").c_str(), L"a") || !out)
        throw std::runtime_error("Cannot write CINE log.");
    fprintf(out, "image %u chauffe %u : %s\n", mCineIndex, mCineLead, message);
    fclose(out);
}

void D3DApp::InitCine(D3D12_GPU_DESCRIPTOR_HANDLE tectonics) {
    if (mCine.empty()) return;
    if (!mShip.Ready()) throw std::runtime_error("CINE requires the ship package.");
    mCineTectonics = tectonics;
    const auto cs = LoadShader(L"CineGround.cso");
    D3D12_COMPUTE_PIPELINE_STATE_DESC desc = {};
    desc.pRootSignature = mComputeRootSignature.Get(); desc.CS = CD3DX12_SHADER_BYTECODE(cs.Get());
    Check(md3dDevice->CreateComputePipelineState(&desc, IID_PPV_ARGS(&mCineGroundPSO)), "Cine ground PSO failed.");
    mCinePoints = CreateBuffer(md3dDevice.Get(), 256, D3D12_HEAP_TYPE_UPLOAD, D3D12_RESOURCE_STATE_GENERIC_READ);
    mCineGround = CreateBuffer(md3dDevice.Get(), 8, D3D12_HEAP_TYPE_DEFAULT, D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_FLAG_ALLOW_UNORDERED_ACCESS);
    mCineGroundReadback = CreateBuffer(md3dDevice.Get(), 8, D3D12_HEAP_TYPE_READBACK, D3D12_RESOURCE_STATE_COPY_DEST);
    if (!mSettings.cineVideo.empty())
        mCineVideo = std::make_unique<CineVideo>(mSettings.cineVideo, mClientWidth, mClientHeight, mCineFps);
}

bool D3DApp::BeginCineFrame() {
    if (mCine.empty()) return true;
    if (mCineIndex >= mCineEnd) { DestroyWindow(mhMainWnd); return false; }
    const CineFrame& f = mCine[mCineIndex];
    const View view = f.cockpit ? View::Cockpit : f.bare ? View::Bare : View::Chase;
    if (view != mView) { mHistoryValid = mCloudHistoryValid = false; }
    mView = view;
    const Vec3d previous = mShipPos;
    // Positive pitch lifts the nose; positive roll banks right. No PlaceCamera here: it resets the waves.
    auto pose = [](const double* p, Vec3d& pos, Vec3d& forward, Vec3d& up) {
        const double rad = XM_PI / 180.0, lat = p[0] * rad, lon = p[1] * rad;
        const Vec3d vertical = { std::cos(lat)*std::cos(lon), std::sin(lat), std::cos(lat)*std::sin(lon) };
        const Vec3d north = { -std::sin(lat)*std::cos(lon), std::cos(lat), -std::sin(lat)*std::sin(lon) };
        const Vec3d east = { -std::sin(lon), 0, std::cos(lon) };
        const Vec3d level = north * std::cos(p[3]*rad) + east * std::sin(p[3]*rad);
        forward = Normalize(level * std::cos(p[4]*rad) + vertical * std::sin(p[4]*rad));
        up = Rotate(vertical * std::cos(p[4]*rad) - level * std::sin(p[4]*rad), forward, -p[5]*rad);
        pos = vertical * (PlanetRadius + p[2]);
    };
    pose(f.nav, mShipPos, mShipForward, mShipUp);
    mShipVelocity = (mShipPos - previous) * mCineFps;
    if (!mHistoryValid && mFrameNumber == 1) mShipVelocity = {};
    mThrottle = Length(mShipVelocity) > 0.1 ? 18.0 : 0.0;
    mPlume = mThrottle / 30.0;
    if (f.cockpit) {
        // Same eye and resting head as UpdateShip, without interactive head inertia.
        mCamPos = mShipPos + mShipForward * 0.9192 + mShipUp * mShip.Profile().eyeUp;
        const Vec3d right = Normalize(Cross(mShipUp, mShipForward));
        mCamForward = Rotate(mShipForward, right, 0.08);
        mCamUp = Rotate(mShipUp, right, 0.08);
    } else pose(f.cam, mCamPos, mCamForward, mCamUp);
    mCineFov = f.fov;
    mWeatherTime = f.weather;
    if (mCineLead && mCine.size() > 1)
        mWeatherTime = std::max(0.0, f.weather - mCineLead * (mCine[1].weather - mCine[0].weather));
    const double time = (double(mCineIndex) - mCineLead) / mCineFps;
    mClock = time - 1.0 / mCineFps; // Draw advances the common clock once
    mSeaTime = mSettings.seaTime + (time - 1.0/mCineFps) * mSeaTimeRate;
    // Global sampling phase also at chunk boundaries; warm-up before frame 0 repeats its pose.
    mFrameNumber = mCineIndex + 1;
    const long long phase = static_cast<long long>(mCineIndex) - mCineLead;
    mCloudFrame = static_cast<UINT>((phase % 576 + 576) % 576); // 16 pixels x 36 samples
    mFoliageFadeFrame = mCloudFrame; // same global 64-frame dither at a chunk boundary
    ClampCine();
    return true;
}

void D3DApp::ClampCine() {
    // Query the CURRENT terrain at both poses, independent of the camera mesh and its previous nadir.
    double* points = nullptr; CD3DX12_RANGE noRead(0, 0);
    Check(mCinePoints->Map(0, &noRead, reinterpret_cast<void**>(&points)), "Cine points map failed.");
    const Vec3d dirs[2] = { Normalize(mCamPos), Normalize(mShipPos) };
    for (int k=0; k<2; ++k) { points[4*k]=dirs[k].x; points[4*k+1]=dirs[k].y; points[4*k+2]=dirs[k].z; points[4*k+3]=0; }
    mCinePoints->Unmap(0, nullptr);
    Check(mCommandAllocator->Reset(), "Cine allocator reset failed.");
    Check(mCommandList->Reset(mCommandAllocator.Get(), mCineGroundPSO.Get()), "Cine list reset failed.");
    ID3D12DescriptorHeap* heaps[] = { mSrvHeap.Get() }; mCommandList->SetDescriptorHeaps(1, heaps);
    mCommandList->SetComputeRootSignature(mComputeRootSignature.Get());
    mCommandList->SetComputeRootConstantBufferView(0, mCinePoints->GetGPUVirtualAddress());
    mCommandList->SetComputeRootUnorderedAccessView(1, mCineGround->GetGPUVirtualAddress());
    mCommandList->SetComputeRootDescriptorTable(2, mCineTectonics);
    mCommandList->Dispatch(1,1,1);
    auto toCopy = CD3DX12_RESOURCE_BARRIER::Transition(mCineGround.Get(), D3D12_RESOURCE_STATE_UNORDERED_ACCESS, D3D12_RESOURCE_STATE_COPY_SOURCE);
    mCommandList->ResourceBarrier(1, &toCopy);
    mCommandList->CopyBufferRegion(mCineGroundReadback.Get(), 0, mCineGround.Get(), 0, 8);
    auto toWrite = CD3DX12_RESOURCE_BARRIER::Transition(mCineGround.Get(), D3D12_RESOURCE_STATE_COPY_SOURCE, D3D12_RESOURCE_STATE_UNORDERED_ACCESS);
    mCommandList->ResourceBarrier(1, &toWrite);
    Check(mCommandList->Close(), "Cine ground close failed.");
    ID3D12CommandList* lists[] = { mCommandList.Get() }; mCommandQueue->ExecuteCommandLists(1, lists); WaitForPreviousFrame();
    float* ground = nullptr; CD3DX12_RANGE read(0,8);
    Check(mCineGroundReadback->Map(0, &read, reinterpret_cast<void**>(&ground)), "Cine ground read failed.");
    const double heights[2] = { ground[0], ground[1] }; mCineGroundReadback->Unmap(0, &noRead);
    mCineShipGround = std::max(heights[1], 0.0);
    mCineClamped = false;
    auto clamp = [&](Vec3d& pos, double height, double margin, const char* label) {
        if (!std::isfinite(height)) throw std::runtime_error("Cine ground is not finite.");
        double floor = std::max(height, 0.0);
        if (height <= 0 && mOcean && !mWaveReset) floor = std::max(floor, double(mOcean->SurfaceHeight()));
        const double minimum = PlanetRadius + floor + margin;
        if (Length(pos) < minimum) { pos = Normalize(pos) * minimum; mCineClamped = true; LogCine(label); }
    };
    const Vec3d before = mShipPos;
    clamp(mShipPos, heights[1], 2.5, "pince vaisseau");
    if (mView == View::Cockpit) mCamPos = mCamPos + (mShipPos - before);
    clamp(mCamPos, heights[0], 1.0, "pince camera");
    mGroundHeight = std::max(heights[0], 0.0); mOceanElevation = (float)heights[0];
}

void D3DApp::EndCineFrame() {
    LARGE_INTEGER now; QueryPerformanceCounter(&now);
    if (mCineMark.QuadPart) { mCineWallMs += 1000.0 * double(now.QuadPart - mCineMark.QuadPart) / mFrequency.QuadPart; mCineGpuMs += mGpuFrameLastMs; ++mCineTimed; }
    mCineMark = now;
    if (mCineLead) --mCineLead;
    else ++mCineIndex;
    if (mCineIndex == mCineEnd) { if (mCineVideo) mCineVideo->Close();
        char line[96]; sprintf_s(line, "fin, %.1f ms par image dont GPU %.1f ms", mCineWallMs / std::max(mCineTimed, 1u), mCineGpuMs / std::max(mCineTimed, 1u));
        LogCine(line); DestroyWindow(mhMainWnd); }
}
