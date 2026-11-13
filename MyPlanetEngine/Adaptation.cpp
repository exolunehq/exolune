// Adaptation.cpp - see Adaptation.h.
#include "Adaptation.h"
#include "GpuHelpers.h"
#include <algorithm>

using Microsoft::WRL::ComPtr;

void Adaptation::Initialize(ID3D12Device* device, UINT width, UINT height) {
    mWidth = width;
    mHeight = height;
    mSeedWidth = std::max(width / 4, 1u);
    mSeedHeight = std::max(height / 4, 1u);
    mLevels = 0;
    for (UINT side = std::min(mSeedWidth, mSeedHeight); side > 1 && mLevels < 6; side /= 2) ++mLevels;
    mLevels = std::max(mLevels, 1u);

    CD3DX12_HEAP_PROPERTIES heapProps(D3D12_HEAP_TYPE_DEFAULT);
    const CD3DX12_RESOURCE_DESC desc = CD3DX12_RESOURCE_DESC::Tex2D(Format, mSeedWidth, mSeedHeight, 1, UINT16(mLevels),
        1, 0, D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET);
    Check(device->CreateCommittedResource(&heapProps, D3D12_HEAP_FLAG_NONE, &desc, D3D12_RESOURCE_STATE_RENDER_TARGET,
        nullptr, IID_PPV_ARGS(&mPyramid)), "Adaptation pyramid creation failed.");
    D3D12_DESCRIPTOR_HEAP_DESC heapDesc = { D3D12_DESCRIPTOR_HEAP_TYPE_RTV, mLevels };
    Check(device->CreateDescriptorHeap(&heapDesc, IID_PPV_ARGS(&mRtvHeap)), "Adaptation RTV heap creation failed.");
    heapDesc = { D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, mLevels, D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE };
    Check(device->CreateDescriptorHeap(&heapDesc, IID_PPV_ARGS(&mSrvHeap)), "Adaptation SRV heap creation failed.");
    mSrvSize = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV);
    mRtvSize = device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV);
    for (UINT i = 0; i < mLevels; ++i) {
        D3D12_RENDER_TARGET_VIEW_DESC rtv = {};
        rtv.Format = Format;
        rtv.ViewDimension = D3D12_RTV_DIMENSION_TEXTURE2D;
        rtv.Texture2D.MipSlice = i;
        device->CreateRenderTargetView(mPyramid.Get(), &rtv,
            CD3DX12_CPU_DESCRIPTOR_HANDLE(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), i, mRtvSize));
        D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
        srv.Format = Format;
        srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
        srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
        srv.Texture2D.MostDetailedMip = i;
        srv.Texture2D.MipLevels = 1;
        device->CreateShaderResourceView(mPyramid.Get(), &srv,
            CD3DX12_CPU_DESCRIPTOR_HANDLE(mSrvHeap->GetCPUDescriptorHandleForHeapStart(), i, mSrvSize));
    }

    // Glare's signature and its 13-tap halving, on two channels: the pass's constants, its source.
    CD3DX12_DESCRIPTOR_RANGE source(D3D12_DESCRIPTOR_RANGE_TYPE_SRV, 1, 0);
    CD3DX12_ROOT_PARAMETER params[2];
    params[0].InitAsConstants(3, 0, 0, D3D12_SHADER_VISIBILITY_PIXEL);
    params[1].InitAsDescriptorTable(1, &source, D3D12_SHADER_VISIBILITY_PIXEL);
    const CD3DX12_STATIC_SAMPLER_DESC linearClamp(0, D3D12_FILTER_MIN_MAG_MIP_LINEAR, D3D12_TEXTURE_ADDRESS_MODE_CLAMP,
        D3D12_TEXTURE_ADDRESS_MODE_CLAMP, D3D12_TEXTURE_ADDRESS_MODE_CLAMP);
    mRootSignature = CreateRootSignature(device, CD3DX12_ROOT_SIGNATURE_DESC(2, params, 1, &linearClamp));
    ComPtr<ID3DBlob> fullscreen = LoadShader(L"Fullscreen.cso"), down = LoadShader(L"GlareDown.cso");
    D3D12_GRAPHICS_PIPELINE_STATE_DESC pso = {};
    pso.pRootSignature = mRootSignature.Get();
    pso.VS = CD3DX12_SHADER_BYTECODE(fullscreen.Get());
    pso.PS = CD3DX12_SHADER_BYTECODE(down.Get());
    pso.RasterizerState = CD3DX12_RASTERIZER_DESC(D3D12_DEFAULT);
    pso.BlendState = CD3DX12_BLEND_DESC(D3D12_DEFAULT);
    pso.DepthStencilState.DepthEnable = FALSE;
    pso.SampleMask = UINT_MAX;
    pso.PrimitiveTopologyType = D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
    pso.NumRenderTargets = 1;
    pso.RTVFormats[0] = Format;
    pso.SampleDesc.Count = 1;
    Check(device->CreateGraphicsPipelineState(&pso, IID_PPV_ARGS(&mDownPSO)), "Adaptation PSO creation failed.");
}

D3D12_CPU_DESCRIPTOR_HANDLE Adaptation::SeedTarget() const {
    return mRtvHeap->GetCPUDescriptorHandleForHeapStart();
}

void Adaptation::CreateSrv(ID3D12Device* device, D3D12_CPU_DESCRIPTOR_HANDLE destination) const {
    D3D12_SHADER_RESOURCE_VIEW_DESC srv = {};
    srv.Format = Format;
    srv.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
    srv.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;
    srv.Texture2D.MipLevels = mLevels;
    device->CreateShaderResourceView(mPyramid.Get(), &srv, destination);
}

void Adaptation::Release(ID3D12GraphicsCommandList* list) {
    const auto b = CD3DX12_RESOURCE_BARRIER::Transition(mPyramid.Get(), D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE,
        D3D12_RESOURCE_STATE_RENDER_TARGET);
    list->ResourceBarrier(1, &b);
}

void Adaptation::Downsample(ID3D12GraphicsCommandList* list, ID3D12DescriptorHeap* heap) {
    auto barrier = [&](UINT level) {
        const auto b = CD3DX12_RESOURCE_BARRIER::Transition(mPyramid.Get(), D3D12_RESOURCE_STATE_RENDER_TARGET,
            D3D12_RESOURCE_STATE_PIXEL_SHADER_RESOURCE, level);
        list->ResourceBarrier(1, &b);
    };
    ID3D12DescriptorHeap* own[] = { mSrvHeap.Get() };
    list->SetDescriptorHeaps(1, own);
    list->SetGraphicsRootSignature(mRootSignature.Get());
    list->SetPipelineState(mDownPSO.Get());
    barrier(0);
    for (UINT i = 1; i < mLevels; ++i) {
        const UINT width = std::max(mSeedWidth >> i, 1u), height = std::max(mSeedHeight >> i, 1u);
        const float constants[3] = { 1.0f / width, 1.0f / height, 0.0f };
        const CD3DX12_VIEWPORT viewport(0.0f, 0.0f, float(width), float(height));
        const CD3DX12_RECT scissor(0, 0, LONG(width), LONG(height));
        const CD3DX12_CPU_DESCRIPTOR_HANDLE target(mRtvHeap->GetCPUDescriptorHandleForHeapStart(), i, mRtvSize);
        list->RSSetViewports(1, &viewport);
        list->RSSetScissorRects(1, &scissor);
        list->OMSetRenderTargets(1, &target, FALSE, nullptr);
        list->SetGraphicsRoot32BitConstants(0, 3, constants, 0);
        list->SetGraphicsRootDescriptorTable(1,
            CD3DX12_GPU_DESCRIPTOR_HANDLE(mSrvHeap->GetGPUDescriptorHandleForHeapStart(), i - 1, mSrvSize));
        list->DrawInstanced(3, 1, 0, 0);
        barrier(i);
    }
    const CD3DX12_VIEWPORT viewport(0.0f, 0.0f, float(mWidth), float(mHeight));
    const CD3DX12_RECT scissor(0, 0, LONG(mWidth), LONG(mHeight));
    list->RSSetViewports(1, &viewport);
    list->RSSetScissorRects(1, &scissor);
    ID3D12DescriptorHeap* mainHeap[] = { heap };
    list->SetDescriptorHeaps(1, mainHeap);
}
