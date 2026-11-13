// Adaptation.h - the eye's local adaptation (AdaptSeed.hlsl, ToneMap.hlsl; docs/recherche-tons-exposition.md): a pyramid of
// the image's light, in stops from the grey card under the global exposure, weighted where it counts, from a quarter of
// the screen's resolution down. D3DApp seeds its first level with the frame's bindings; Downsample averages the others
// (GlareDown.hlsl); the tone map reads the whole pyramid at t9. Its own descriptor heaps: an RTV and an SRV per level.
#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <wrl.h>
#include <d3d12.h>

class Adaptation {
public:
    static const DXGI_FORMAT Format = DXGI_FORMAT_R16G16_FLOAT; // the weighted sum of stops, the sum of weights
    void Initialize(ID3D12Device* device, UINT width, UINT height);
    // The first level, a render target for the seed pass, and its size.
    D3D12_CPU_DESCRIPTOR_HANDLE SeedTarget() const;
    UINT SeedWidth() const { return mSeedWidth; }
    UINT SeedHeight() const { return mSeedHeight; }
    // Averages each level from the previous one; leaves the pyramid readable, the full screen's viewport and `heap` bound.
    void Downsample(ID3D12GraphicsCommandList* list, ID3D12DescriptorHeap* heap);
    // Back to render targets, after the tone map.
    void Release(ID3D12GraphicsCommandList* list);
    // The whole pyramid, as a shader resource in another heap (the tone map's t9).
    void CreateSrv(ID3D12Device* device, D3D12_CPU_DESCRIPTOR_HANDLE destination) const;
private:
    Microsoft::WRL::ComPtr<ID3D12Resource> mPyramid;
    Microsoft::WRL::ComPtr<ID3D12DescriptorHeap> mSrvHeap, mRtvHeap;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mRootSignature;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mDownPSO;
    UINT mLevels = 0, mWidth = 0, mHeight = 0, mSeedWidth = 0, mSeedHeight = 0, mSrvSize = 0, mRtvSize = 0;
};
