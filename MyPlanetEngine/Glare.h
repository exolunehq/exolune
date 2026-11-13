// Glare.h - the lens's glare (GlareDown.hlsl, GlareUp.hlsl; docs/recherche-halo.md): the composite image halved level
// after level, then summed back up; the tone map spreads the finest level over the image (ToneMap.hlsl). The composite
// itself is left untouched, so stellar visibility reads the sky without the veil. Its own descriptor heaps: an SRV and an
// RTV per level, the composite's SRV last. Normal rendering; MYPLANETENGINE_GLARE=0 disables it for inspection.
#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <wrl.h>
#include <d3d12.h>

class Glare {
public:
    // One level per octave of angle, from half the screen down to a pixel or two.
    void Initialize(ID3D12Device* device, UINT width, UINT height, DXGI_FORMAT format, ID3D12Resource* composite);
    // From the composite image, a render target before and after; `heap`, the frame's descriptor heap, is bound again.
    // The levels are left readable for the tone map; Release returns them to render targets after it.
    void Draw(ID3D12GraphicsCommandList* list, ID3D12DescriptorHeap* heap);
    void Release(ID3D12GraphicsCommandList* list);
    // The finest level, summed with all coarser ones, as a shader resource in another heap (the tone map's t8).
    void CreateSummedSrv(ID3D12Device* device, D3D12_CPU_DESCRIPTOR_HANDLE destination) const;
private:
    Microsoft::WRL::ComPtr<ID3D12Resource> mGlare, mComposite;
    Microsoft::WRL::ComPtr<ID3D12DescriptorHeap> mSrvHeap, mRtvHeap;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mRootSignature;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mDownPSO, mUpPSO;
    UINT mLevels = 0, mWidth = 0, mHeight = 0, mSrvSize = 0, mRtvSize = 0;
    DXGI_FORMAT mFormat = DXGI_FORMAT_UNKNOWN;
};
