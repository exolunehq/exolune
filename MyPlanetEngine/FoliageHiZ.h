#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <d3d12.h>
#include <wrl.h>

// Current-frame reversed-Z depth pyramid. The caller owns the shader-visible heap.
class FoliageHiZ {
public:
    // Depth SRV, full pyramid SRV, then one SRV and one UAV per mip.
    static UINT DescriptorCount(UINT width, UINT height);
    void Initialize(ID3D12Device* device, UINT width, UINT height, ID3D12Resource* depth,
                    D3D12_CPU_DESCRIPTOR_HANDLE cpu, D3D12_GPU_DESCRIPTOR_HANDLE gpu);
    // The source must be in DEPTH_WRITE. Both the source and every pyramid mip
    // return in DEPTH_WRITE and NON_PIXEL_SHADER_RESOURCE respectively.
    // The caller must have bound the heap supplied to Initialize.
    void Build(ID3D12GraphicsCommandList* list, ID3D12Resource* depth);
    D3D12_GPU_DESCRIPTOR_HANDLE Srv() const { return mFullSrv; }
    UINT Width() const { return mWidth; } // padded width
    UINT Height() const { return mHeight; } // padded height
    UINT MipCount() const { return mMipCount; }
private:
    static constexpr UINT MaxMips = 15; // D3D12 2D texture limit: 16384
    Microsoft::WRL::ComPtr<ID3D12Resource> mTexture, mDepth;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mRoot;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mCopy, mReduce;
    D3D12_GPU_DESCRIPTOR_HANDLE mDepthSrv = {}, mFullSrv = {};
    D3D12_GPU_DESCRIPTOR_HANDLE mMipSrv[MaxMips] = {}, mMipUav[MaxMips] = {};
    UINT mSourceWidth = 0, mSourceHeight = 0, mWidth = 0, mHeight = 0, mMipCount = 0;
    bool mBuilt = false;
};
