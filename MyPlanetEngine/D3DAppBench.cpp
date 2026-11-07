// D3DAppBench.cpp - D3DApp's benches (D3DApp.h, tools/banc_*.py): the batch's jobs and their camera, the measures, the
// captures and the files written beside them.
#include "D3DApp.h"
#include "GpuHelpers.h"
#include <algorithm>
#include <cstdio>
#include <fstream>
#include <sstream>

namespace
{
    // Writes an RGBA8 image as a 32-bit BMP.
    void SaveBmp(const std::wstring& path, const BYTE* rgba, UINT width, UINT height, UINT rowPitch)
    {
        std::vector<BYTE> bgra(size_t(width) * height * 4);
        for (UINT y = 0; y < height; ++y)
            for (UINT x = 0; x < width; ++x) {
                const BYTE* in = rgba + size_t(y) * rowPitch + x * 4;
                BYTE* out = &bgra[(size_t(y) * width + x) * 4];
                out[0] = in[2]; out[1] = in[1]; out[2] = in[0]; out[3] = 255;
            }
        BITMAPINFOHEADER info = {};
        info.biSize = sizeof(info);
        info.biWidth = LONG(width);
        info.biHeight = -LONG(height); // top-down
        info.biPlanes = 1;
        info.biBitCount = 32;
        info.biCompression = BI_RGB;
        BITMAPFILEHEADER file = {};
        file.bfType = 0x4D42; // "BM"
        file.bfOffBits = sizeof(file) + sizeof(info);
        file.bfSize = DWORD(file.bfOffBits + bgra.size());
        FILE* f = nullptr;
        if (_wfopen_s(&f, path.c_str(), L"wb") != 0 || !f) throw std::runtime_error("Cannot open BMP output.");
        const bool ok = fwrite(&file, sizeof(file), 1, f) == 1 && fwrite(&info, sizeof(info), 1, f) == 1
            && fwrite(bgra.data(), 1, bgra.size(), f) == bgra.size();
        const int closed = fclose(f);
        if (!ok || closed) throw std::runtime_error("Cannot write BMP output (disk full?).");
    }
}

// The batch's jobs, MYPLANETENGINE_BATCH, one per line. A job that gives no face factor takes mFaceFactor's.
void D3DApp::ReadBatch() {
    if (!mSettings.batch) return;
    std::wifstream jobs(mSettings.batchPath.c_str());
    for (std::wstring line; std::getline(jobs, line);) {
        std::wistringstream fields(line);
        BatchJob job;
        std::wstring name;
        if (fields >> job.path >> name >> job.height >> job.latitude >> job.longitude >> job.pitchDown >> job.heading) {
            if (!(fields >> job.faceFactor)) job.faceFactor = mFaceFactor;
            else fields.clear();
            double extra0 = 0.0, extra1 = 0.0, extra2 = 0.0;
            if (fields >> extra0) {
                if (fields >> extra1) {
                    if (fields >> extra2) {
                        job.weatherTime = extra0;
                        job.sunLatitude = extra1;
                        job.sunLongitude = extra2;
                        job.sun = true;
                    }
                    else {
                        job.sunLatitude = extra0;
                        job.sunLongitude = extra1;
                        job.sun = true;
                    }
                }
                else {
                    fields.clear();
                    job.weatherTime = extra0;
                }
            }
            job.view = DiagnosticView(name.c_str());
            mBatch.push_back(job);
        }
    }
}

// The job's frame that is captured: after the settling, the plants' warm-up and samples, or the smoothing's.
UINT D3DApp::BatchCaptureFrame() const {
    return BatchSettle + (mPlanetFoliage.Enabled() ? mSettings.foliageWarm + mSettings.foliageSamples : mTaa ? BatchWarm : 2);
}

// Batch capture, as the frame starts: the job's view; its camera re-placed above the ground under it while that ground
// settles, from the previous job's and the mesh's coarser cells; then the smoothing starts afresh. False when the
// batch is over: the window is closed.
bool D3DApp::BeginBatchFrame() {
    if (mSettings.batch && mBatch.empty()) {
        DestroyWindow(mhMainWnd);
        return false;
    }
    if (!mBatch.empty()) {
        const BatchJob& job = mBatch[mBatchIndex];
        const double* motion = mSettings.batchMotion;
        if (job.weatherTime >= 0.0) mWeatherTime = job.weatherTime;
        if (mBatchFrame == 0) {
            mFoliageFadeFrame=0; // identical capture frames use the same temporal dither, regardless of preceding jobs
            mPlanetPlantPlacement.Reset(); // a new place: the plants' kept ground starts again
            mPlanetFoliageSamples.clear();
            mDiagnosticView = job.view;
            mFaceFactor = job.faceFactor;
            mSunDir = job.sun ? LatLonToDir(job.sunLatitude, job.sunLongitude) : mStartSunDir;
            mTaa = mSettings.taa;
        }
        if (mBatchFrame < BatchSettle)
            PlaceCamera(job.latitude, job.longitude, job.pitchDown, job.heading, mGroundHeight + job.height);
        else if (motion[0] != 0.0 || motion[1] != 0.0 || motion[2] != 0.0 || motion[3] > 1.0 || motion[5] != 0.0) {
            // The motion check (docs/optimisation.md): the camera reaches the job's pose, turning, flying north and
            // descending, and the weather runs up to the job's time, then holds still until the capture; what is
            // temporal is then captured in motion, or as it settles.
            const UINT capture = BatchCaptureFrame();
            const double left = std::max(double(capture) - motion[4] - double(mBatchFrame + 1), 0.0);
            const double height = job.height * std::pow(std::max(motion[3], 1.0), left);
            // Flying north by degrees, or at a share of the height, as the app's speed (UpdateCamera).
            const double north = motion[1] + motion[5] * job.height / PlanetRadius * 180.0 / XM_PI;
            PlaceCamera(job.latitude - north * left, job.longitude, job.pitchDown,
                job.heading - motion[0] * left, mGroundHeight + height);
            mWeatherTime = std::max(job.weatherTime, 0.0) - motion[2] * left;
        }
        if (mBatchFrame == 0 || mBatchFrame == BatchSettle)
            mHistoryValid = false;
        ++mBatchFrame;
    }
    return true;
}

// The batch's measures, as the frame ends: the CPU's (D3DApp.h, PerfPasses), then every pass's summed over the job's
// samples, after the settling and the plants' warm-up.
void D3DApp::SumBatchTimes(const LARGE_INTEGER (&cpuMarks)[5], bool usePlantHiZ) {
    if (mSettings.batch) {
        auto cpuMs = [&](LARGE_INTEGER a, LARGE_INTEGER b) { return 1000.0 * double(b.QuadPart - a.QuadPart) / mFrequency.QuadPart; };
        for (UINT i = 0; i < 4; ++i) mPerfLast[PerfGpu + i] = cpuMs(cpuMarks[i], cpuMarks[i + 1]);
        mPerfLast[PerfGpu + 4] = mPerfPresent.QuadPart ? cpuMs(mPerfPresent, cpuMarks[3]) : 0.0;
        mPerfPresent = cpuMarks[3];
    }
    if (mPlanetFoliage.Enabled() && !mBatch.empty() && mBatchFrame > BatchSettle + mSettings.foliageWarm)
        mPlanetFoliageSamples.push_back({ mFoliagePlaceMs, mFoliageDrawMs, mFrameGpuMs, mPlantPlacementMs, mHiZBuildMs, mHiZCullMs, usePlantHiZ });
    if (!mBatch.empty() && mBatchFrame == 1) {
        std::fill_n(mPerfSum, PerfPasses, 0.0);
        mPerfFrames = 0;
        mPerfSamples.clear();
        mPerfSamples.reserve(mSettings.foliageSamples);
    }
    if (!mBatch.empty() && mBatchFrame > BatchSettle + mSettings.foliageWarm) {
        for (UINT i = 0; i < PerfPasses; ++i) mPerfSum[i] += mPerfLast[i];
        std::array<double, PerfPasses + 11> row;
        std::copy_n(mPerfLast, PerfPasses, row.begin());
        row[PerfPasses] = mPerfScreenLast;
        std::copy_n(mPerfScreenParts, 6, row.begin() + PerfPasses + 1);
        std::copy_n(mPerfTerrainParts, 4, row.begin() + PerfPasses + 7);
        mPerfSamples.push_back(row);
        ++mPerfFrames;
    }
}

// The frame captured, once it has run: the image, and for a batch job the files the benches read beside it; then the
// next job, or the window closed.
void D3DApp::SaveCapture(bool batchCapture, UINT trembleIndex) {
    BYTE* pixels = nullptr;
    // The last row need not include its pitch padding in GetCopyableFootprints' allocation.
    // Mapping pitch * height could exceed the buffer for window widths not aligned to 64 pixels.
    CD3DX12_RANGE captureRange(0, SIZE_T(mCaptureBuffer->GetDesc().Width));
    if (!mCine.empty()) {
        Check(mCaptureBuffer->Map(0, &captureRange, reinterpret_cast<void**>(&pixels)), "Cine capture map failed.");
        wchar_t name[64]; swprintf_s(name, L"\\frame_%05u.bmp", mCineIndex);
        try {
            if (mCineVideo) mCineVideo->Push(pixels + mCaptureFootprint.Offset, mCaptureFootprint.Footprint.RowPitch);
            else SaveBmp(mSettings.cineOut + name, pixels + mCaptureFootprint.Offset, mClientWidth, mClientHeight, mCaptureFootprint.Footprint.RowPitch);
        } catch (...) { const CD3DX12_RANGE noWrite(0,0); mCaptureBuffer->Unmap(0, &noWrite); throw; }
        const CD3DX12_RANGE noWrite(0,0); mCaptureBuffer->Unmap(0, &noWrite);
        return;
    }
    if (SUCCEEDED(mCaptureBuffer->Map(0, &captureRange, reinterpret_cast<void**>(&pixels)))) {
        std::wstring path = batchCapture ? mBatch[mBatchIndex].path : mSettings.capturePath;
        if (trembleIndex) {
            wchar_t suffix[16];
            swprintf_s(suffix, L"_%03u.bmp", trembleIndex);
            path = mSettings.tremblePath + suffix;
        }
        SaveBmp(path, pixels + mCaptureFootprint.Offset, mClientWidth, mClientHeight,
            mCaptureFootprint.Footprint.RowPitch);
        if (mScreenCaptureBuffer && mConstants->screenRelief.z > 0.0f) {
            const UINT dimensions[] = { UINT(mConstants->screenRelief.x), UINT(mConstants->screenRelief.y), 16u };
            const SIZE_T bytes = SIZE_T(ScreenSampleBytes) * dimensions[0] * dimensions[1];
            void* fields = nullptr;
            const CD3DX12_RANGE range(0, bytes), noWrite(0, 0);
            Check(mScreenCaptureBuffer->Map(0, &range, &fields), "Screen field capture map failed.");
            FILE* file = nullptr;
            if (_wfopen_s(&file, (path + L".screen").c_str(), L"wb") == 0 && file) {
                fwrite(dimensions, sizeof(UINT), 3, file);
                fwrite(fields, 1, bytes, file);
                fclose(file);
            }
            mScreenCaptureBuffer->Unmap(0, &noWrite);
        }
        mPlanetFoliage.SaveStats(path, mFoliagePlaceMs, mFoliageDrawMs, mFrameGpuMs, mPlanetFoliageSamples);
        {
            FILE* contactFile=nullptr;
            if (_wfopen_s(&contactFile,(path+L".local-contacts.json").c_str(),L"wb")==0 && contactFile) {
                const bool active=mLocalContactsEnabled && mDiagnosticView<=0.5f && !mWireframe;
                fprintf(contactFile,"{\"enabled\":%s,\"half_width\":%d,\"half_height\":%d,\"radius_m\":1.2,\"sun_ray_m\":1.28,\"range_m\":192,\"history\":false}\n",active?"true":"false",(mClientWidth+1)/2,(mClientHeight+1)/2);
                fclose(contactFile);
            }
            FILE* filterFile=nullptr;
            if (_wfopen_s(&filterFile,(path+L".foliage-filter.json").c_str(),L"wb")==0 && filterFile) {
                fprintf(filterFile,"{\"temporal_aa\":%s,\"temporal_weight\":%.6f,\"coverage_frames\":%u,\"coverage_sequence\":\"%s\",\"observer_canopy\":%.8f}\n",TemporalAA()?"true":"false",mConstants->taa.x,TemporalAA()?64u:1u,mSettings.foliageWhiteNoise?"white-control":"sobol3",mConstants->camPlane.w);
                fclose(filterFile);
            }
        }
        if (batchCapture) { // the title and this frame's objects, for the benches, at <capture>.txt
            char utf8[2048];
            std::wstring batchSidecar = mTitle + ObjectStatsText();
            wchar_t gpuSummary[128];
            swprintf_s(gpuSummary, L"\r\nGPU frame %.2f ms | GPU nuages+air %.2f ms", mGpuFrameLastMs, mCloudPassLastMs);
            batchSidecar += gpuSummary;
            const int length = WideCharToMultiByte(CP_UTF8, 0, batchSidecar.c_str(), -1, utf8, sizeof(utf8),
                                                   nullptr, nullptr);
            FILE* f = nullptr;
            if (length > 0 && _wfopen_s(&f, (path + L".txt").c_str(), L"wb") == 0 && f) {
                fwrite(utf8, 1, length - 1, f);
                fclose(f);
            }
            // Each pass's mean time over the job's samples, ms, at <capture>.perf (tools/banc_perf.py).
            if (_wfopen_s(&f, (path + L".perf").c_str(), L"wb") == 0 && f) {
                for (UINT i = 0; i < PerfPasses; ++i) fprintf(f, "%.4f ", mPerfSum[i] / std::max(mPerfFrames, 1u));
                fprintf(f, "%u\n", mPerfFrames);
                fclose(f);
            }
            // Keep every measured frame: an average conceals stalls. Buffer in memory; write only after sampling.
            if (_wfopen_s(&f, (path + L".frames.csv").c_str(), L"wb") == 0 && f) {
                fprintf(f, "mer_fft,terrain_calc,objets_place,plantes_place,copies,feuillage_tri,terrain_dessin,"
                    "objets_dessin,feuillage_dessin,nuages_aux,nuages_trace,atmosphere,post,total,"
                    "cpu_prep,cpu_liste,cpu_present,cpu_attente,cadence,gpu_inactif,relief_ecran,"
                    "ecran_sol,ecran_rivieres,ecran_args,ecran_repli,ecran_fin,ecran_reste,"
                    "terrain_maillage,terrain_horizon,terrain_fin,terrain_normales\n");
                for (const auto& row : mPerfSamples) {
                    for (UINT i = 0; i < row.size(); ++i) fprintf(f, i ? ",%.6f" : "%.6f", row[i]);
                    fprintf(f, "\n");
                }
                fclose(f);
            }
            // Each object drawn, stones then tufts: its seed, which names it, its width on screen (px) and its place on
            // screen (-1 to 1), at <capture>.objets, four floats each. In the census, every candidate's record as it
            // is, at <capture>.recensement.
            ObjectInstance* objects = nullptr;
            const UINT count = mSettings.objectCensus ? std::min(mObjectStats[Evaluated], ObjectCandidates) : ObjectCapacity;
            CD3DX12_RANGE objectsRange(0, sizeof(ObjectInstance) * count);
            if (mObjectInstancesReadback && SUCCEEDED(mObjectInstancesReadback->Map(0, &objectsRange, reinterpret_cast<void**>(&objects)))) {
                std::vector<float> rows;
                const float pixelAngle = 2.0f * std::tan(XMConvertToRadians(60.0f) * 0.5f) / float(mClientHeight);
                std::vector<UINT> drawn;
                for (UINT i = 0; i < std::min(mObjectStats[DrawInstances], ObjectClassCapacity); ++i) drawn.push_back(i);
                for (UINT i = 0; i < std::min(mObjectStats[TuftInstances], ObjectClassCapacity); ++i) drawn.push_back(ObjectClassCapacity + i);
                for (const UINT i : drawn) {
                    const ObjectInstance& o = objects[i];
                    const XMVECTOR p = XMLoadFloat3(&o.pos);
                    XMFLOAT2 screen;
                    XMStoreFloat2(&screen, XMVector3TransformCoord(p, mPrevViewProj));
                    float seed;
                    memcpy(&seed, &o.seed, sizeof(seed));
                    rows.insert(rows.end(), { seed, o.size / (XMVectorGetX(XMVector3Length(p)) * pixelAngle), screen.x, screen.y });
                }
                if (mSettings.objectCensus && _wfopen_s(&f, (path + L".recensement").c_str(), L"wb") == 0 && f) {
                    fwrite(objects, sizeof(ObjectInstance), count, f);
                    fclose(f);
                }
                else if (!mSettings.objectCensus && _wfopen_s(&f, (path + L".objets").c_str(), L"wb") == 0 && f) {
                    fwrite(rows.data(), sizeof(float), rows.size(), f);
                    fclose(f);
                }
                // And the plants, before they are sorted by model, at <capture>.plantes: their seed and place.
                if (!mSettings.objectCensus && mPlanetFoliage.Enabled() && mSettings.objectList &&
                    _wfopen_s(&f, (path + L".plantes").c_str(), L"wb") == 0 && f) {
                    const UINT counts[2] = { std::min(mObjectStats[PlantInstances], ObjectClassCapacity),
                                             std::min(mObjectStats[PlantCoarseInstances], ObjectClassCapacity) };
                    struct PlantRecord { UINT seed; XMFLOAT3 pos; };
                    static_assert(sizeof(PlantRecord) == 16, "Unexpected plant export layout.");
                    std::vector<PlantRecord> plants; plants.reserve(size_t(counts[0]) + counts[1]);
                    for (UINT group = 0; group < 2; ++group) for (UINT i = 0; i < counts[group]; ++i) {
                        const ObjectInstance& plant = objects[(2 + group) * ObjectClassCapacity + i];
                        plants.push_back({ plant.seed, plant.pos });
                    }
                    fwrite("FOLPLN01", 1, 8, f);
                    fwrite(counts, sizeof(UINT), 2, f);
                    fwrite(plants.data(), sizeof(PlantRecord), plants.size(), f);
                    fclose(f);
                    // Optional full deformation witness, batch only. Keep the
                    // compact public position stream unchanged.
                    if (GetEnvironmentVariableW(L"MYPLANETENGINE_PLANT_INSTANCES", nullptr, 0) > 0 &&
                        _wfopen_s(&f, (path + L".plant-instances").c_str(), L"wb") == 0 && f) {
                        static_assert(sizeof(ObjectInstance) == 64, "Unexpected plant instance layout.");
                        const XMFLOAT4 planetOffset = { mConstants->camPlane.x, mConstants->camPlane.y,
                            mConstants->faceParams.y + mConstants->faceParams.z, pixelAngle };
                        XMFLOAT4X4 projection;
                        XMStoreFloat4x4(&projection, mPrevViewProj);
                        fwrite("FOLPLC01", 1, 8, f);
                        fwrite(counts, sizeof(UINT), 2, f);
                        fwrite(&planetOffset, sizeof(planetOffset), 1, f);
                        fwrite(&projection, sizeof(projection), 1, f);
                        for (UINT group = 0; group < 2; ++group) for (UINT i = 0; i < counts[group]; ++i)
                            fwrite(&objects[(2 + group) * ObjectClassCapacity + i], sizeof(ObjectInstance), 1, f);
                        fclose(f);
                    }
                }
                const CD3DX12_RANGE nothing(0, 0);
                mObjectInstancesReadback->Unmap(0, &nothing);
            }
        }
        CD3DX12_RANGE noWrite(0, 0);
        mCaptureBuffer->Unmap(0, &noWrite);
    }
    if (batchCapture) {
        mBatchFrame = 0;
        if (++mBatchIndex == mBatch.size()) DestroyWindow(mhMainWnd);
    }
    else if (!trembleIndex || trembleIndex == mSettings.trembleFrames) DestroyWindow(mhMainWnd);
}
