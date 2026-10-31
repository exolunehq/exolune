#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <d3d12.h>
#include <DirectXMath.h>
#include <wrl.h>
#include <array>
#include <string>

// Experimental local ocean. Kept independent of the terrain and of the former analytic ocean.
class Ocean {
public:
    static constexpr UINT DescriptorCount = 256;
    static constexpr UINT N = 256, Cascades = 4, Mips = 9, FoamN = 512, FoamMips = 10;
    void Initialize(ID3D12Device*, ID3D12DescriptorHeap*, UINT descriptorBase);
    void Update(ID3D12GraphicsCommandList*, double originX, double originY, double time, float dt, bool reset, float elevation);
    float SurfaceHeight() const;
    void SetWind(float speed, float directionDegrees, float swellHs);
    D3D12_GPU_VIRTUAL_ADDRESS ConstantsAddress() const { return mConstantsBuffer->GetGPUVirtualAddress(); }
private:
    using Resource = Microsoft::WRL::ComPtr<ID3D12Resource>;
    struct Constants {
        DirectX::XMFLOAT4 lengths, kmin, kmax, wind, swell, settings, time;
        DirectX::XMFLOAT4 origin[4], foamOrigin[2], foamGrid[2];
        DirectX::XMINT4 foamSnap[2];
        DirectX::XMFLOAT4 foamParams, render, poreOrigin, streakOrigin;
    };
    struct Image { Resource resource; UINT size, layers, mips; };
    ID3D12Device* mDevice = nullptr;
    ID3D12DescriptorHeap* mHeap = nullptr;
    UINT mBase = 0, mStride = 0, mActive = 0;
    Resource mConstantsBuffer, mH0, mSpectrum[2], mRows[2], mHeight, mHeightReadback;
    DirectX::XMFLOAT4* mHeightValues=nullptr;
    Constants* mConstants = nullptr;
    Image mImages[6]; // displacement, derivatives, slope moments, pores, foam ping 0 and 1
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mRoot;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mInit, mEvolve, mFftRows, mFftColumns,
        mMipWaves, mPores, mFoamUpdate, mMipSingle, mCameraHeight;
    bool mFirst = true, mSpectrumDirty = true;
    DirectX::XMINT2 mSnap[2] = {};
    D3D12_CPU_DESCRIPTOR_HANDLE Cpu(UINT) const;
    D3D12_GPU_DESCRIPTOR_HANDLE Gpu(UINT) const;
    UINT SrvMip(UINT group, UINT mip) const { return 6 + 60 * group + 3 * mip; }
    UINT UavMip(UINT group, UINT mip) const { return 36 + 60 * group + 3 * mip; }
    void Mipmaps(ID3D12GraphicsCommandList*, UINT group);
    void TransitionMip(ID3D12GraphicsCommandList*, UINT image, UINT mip,
        D3D12_RESOURCE_STATES before, D3D12_RESOURCE_STATES after);
};
