// The cinema's frames piped to ffmpeg, encoded on the GPU (NVENC), instead of one BMP file per frame: no disk, no
// separate encoding, so a whole route renders in one run. A writer thread and two buffers: the next frame renders while
// the previous one is written. Fragmented MP4: a file cut short by a crash stays readable up to its last fragment.
#pragma once
#include <windows.h>
#include <condition_variable>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

class CineVideo {
public:
    CineVideo(const std::wstring& path, UINT width, UINT height, double fps) : mWidth(width), mHeight(height) {
        // A keyframe and a fragment every second: after a crash the file holds whole seconds, and the render resumes there.
        wchar_t cmd[4096];
        swprintf_s(cmd, L"ffmpeg -v error -y -f rawvideo -pix_fmt rgb0 -s %ux%u -r %.6g -i - -c:v hevc_nvenc -preset p7 "
            L"-tune hq -rc vbr -cq 12 -b:v 0 -g %u -bf 0 -movflags +frag_keyframe+empty_moov+default_base_moof \"%s\"",
            width, height, fps, UINT(fps + 0.5), path.c_str());
        mPipe = _wpopen(cmd, L"wb");
        if (!mPipe) throw std::runtime_error("Cannot start ffmpeg for MYPLANETENGINE_CINE_VIDEO.");
        for (auto& b : mBuffers) b.resize(size_t(width) * height * 4);
        mThread = std::thread([this] { Write(); });
    }
    ~CineVideo() { try { Close(); } catch (...) {} }
    CineVideo(const CineVideo&) = delete;
    CineVideo& operator=(const CineVideo&) = delete;

    // Copies the frame (RGBA rows, rowPitch apart) and returns; waits only while both buffers are still being written.
    void Push(const BYTE* rgba, UINT rowPitch) {
        std::unique_lock<std::mutex> lock(mMutex);
        mCv.wait(lock, [&] { return mQueued < 2 || mFailed; });
        if (mFailed) throw std::runtime_error("ffmpeg stopped (MYPLANETENGINE_CINE_VIDEO).");
        std::vector<BYTE>& b = mBuffers[(mHead + mQueued) % 2];
        lock.unlock();
        const size_t row = size_t(mWidth) * 4;
        for (UINT y = 0; y < mHeight; ++y) memcpy(b.data() + y * row, rgba + size_t(y) * rowPitch, row);
        lock.lock();
        ++mQueued;
        mCv.notify_all();
    }

    // Writes what is queued, then waits for ffmpeg to finish the file.
    void Close() {
        if (!mPipe) return;
        { std::lock_guard<std::mutex> lock(mMutex); mDone = true; }
        mCv.notify_all();
        if (mThread.joinable()) mThread.join();
        const int code = _pclose(mPipe);
        mPipe = nullptr;
        if (code != 0 || mFailed) throw std::runtime_error("ffmpeg failed (MYPLANETENGINE_CINE_VIDEO).");
    }

private:
    void Write() {
        for (;;) {
            std::unique_lock<std::mutex> lock(mMutex);
            mCv.wait(lock, [&] { return mQueued > 0 || mDone; });
            if (mQueued == 0) return;
            const std::vector<BYTE>& b = mBuffers[mHead];
            lock.unlock();
            const bool ok = fwrite(b.data(), 1, b.size(), mPipe) == b.size();
            lock.lock();
            if (!ok) { mFailed = true; mCv.notify_all(); return; }
            mHead ^= 1; --mQueued;
            mCv.notify_all();
        }
    }

    UINT mWidth, mHeight;
    FILE* mPipe = nullptr;
    std::vector<BYTE> mBuffers[2];
    UINT mHead = 0, mQueued = 0;
    bool mDone = false, mFailed = false;
    std::mutex mMutex;
    std::condition_variable mCv;
    std::thread mThread;
};
