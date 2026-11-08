// Glare.h - the lens's glare (GlareDown.hlsl, GlareUp.hlsl; docs/recherche-halo.md): the composite image halved level
// after level, then summed back up and spread over it, before the temporal smoothing. Its own descriptor heaps: an SRV
// and an RTV per level, the composite's SRV last. Normal rendering; MYPLANETENGINE_GLARE=0 disables it for inspection.
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
    // Over the composite image, a render target before and after; `heap`, the frame's descriptor heap, is bound again.
    void Draw(ID3D12GraphicsCommandList* list, D3D12_CPU_DESCRIPTOR_HANDLE compositeRtv, ID3D12DescriptorHeap* heap);
private:
    Microsoft::WRL::ComPtr<ID3D12Resource> mGlare, mComposite;
    Microsoft::WRL::ComPtr<ID3D12DescriptorHeap> mSrvHeap, mRtvHeap;
    Microsoft::WRL::ComPtr<ID3D12RootSignature> mRootSignature;
    Microsoft::WRL::ComPtr<ID3D12PipelineState> mDownPSO, mUpPSO, mApplyPSO;
    UINT mLevels = 0, mWidth = 0, mHeight = 0, mSrvSize = 0, mRtvSize = 0;
};
